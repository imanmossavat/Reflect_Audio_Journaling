"""Llama Guard safety classifier — input/output guardrail for the chat flows.

A small, dedicated model (`llama-guard3:1b` by default) acts as a *guard* around the main
conversational model, which on its own is jailbreakable and can't be trusted to police
itself. We repurpose Llama Guard's MLCommons hazard taxonomy as a *wellbeing* signal: a
handful of categories map to a care `kind`, everything else is ignored. Acting on a kind
never blocks journaling — it surfaces an empathetic support card (see the frontend).

The guard is mandatory: a Llama Guard model must be installed or sending messages is
blocked upstream (see the preflight checks in `query` / `generation_registry`). There is
no disable switch — without the guard we can't ensure a safe environment.

Design rules: only map the few relevant categories and **fail open** on any runtime error
(a guard hiccup must never break the app).
"""
import asyncio
from dataclasses import dataclass, field

from ollama import AsyncClient

from app import logging_config
from app.services.llm_runtime import check_model_installed
from app.services.settings_service import get_setting

logger = logging_config.logger

# MLCommons / Llama Guard 3 hazard codes → the care pathway we respond with.
# S1 Violent Crimes, S2 Non-Violent Crimes, S11 Suicide & Self-Harm.
#
# S6 (Specialized Advice) was previously mapped to "support" too, and has been
# removed (docs/ISSUES.md #19): it flags content resembling unqualified
# professional advice (medical/legal/financial) — a misinformation/liability
# category, not a wellbeing signal. In practice it false-positived on ordinary
# planning/strategy conversation (career plans, project roadmaps) with a small
# 1B guard model, surfacing the "reach out" support card on completely benign
# exchanges. Keep only categories that actually correlate with the user's
# emotional state, not the topic being discussed.
CATEGORY_TO_KIND: dict[str, str] = {
    "S11": "self_harm",
    "S1": "support",
    "S2": "support",
}
# When several categories fire, the more urgent kind wins.
KIND_PRIORITY: list[str] = ["self_harm", "support"]


@dataclass
class SafetyVerdict:
    flagged: bool
    kind: str | None
    categories: list[str] = field(default_factory=list)
    raw: str = ""


_SAFE = SafetyVerdict(flagged=False, kind=None)


def _safety_model() -> str:
    return get_setting("safety_model")


def _ollama_host() -> str:
    return get_setting("ollama_host").rstrip("/")


def _parse(raw: str) -> tuple[bool, list[str]]:
    """Llama Guard returns `safe` or `unsafe\\nS1,S11`. Return (is_unsafe, category codes)."""
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        return False, []
    is_unsafe = lines[0].lower().startswith("unsafe")
    if not is_unsafe:
        return False, []
    codes: list[str] = []
    for ln in lines[1:]:
        for token in ln.replace(",", " ").split():
            token = token.strip().upper()
            if token:
                codes.append(token)
    return True, codes


def _kind_for(categories: list[str]) -> str | None:
    kinds = {CATEGORY_TO_KIND[c] for c in categories if c in CATEGORY_TO_KIND}
    for kind in KIND_PRIORITY:
        if kind in kinds:
            return kind
    return None


async def _classify(messages: list[dict]) -> SafetyVerdict:
    model = _safety_model()
    # Chat sends are blocked upstream when the guard model isn't installed (preflight). This
    # branch is a backstop for the journaling-only flows (no preflight); there we degrade
    # gracefully rather than break journaling.
    if not await asyncio.to_thread(check_model_installed, model):
        logger.warning("[safety] model %r not installed — guardrail skipped", model)
        return _SAFE
    try:
        logger.debug("[safety] classifying with model=%r, %d message(s)", model, len(messages))
        client = AsyncClient(host=_ollama_host())
        resp = await client.chat(
            model=model,
            messages=messages,
            stream=False,
            think=False,
            options={"temperature": 0.0},
        )
        raw = (resp.get("message", {}) or {}).get("content", "") or ""
        logger.debug("[safety] raw verdict: %r", raw)
    except asyncio.TimeoutError:
        # Guard service is reachable but timed out on this specific message.
        # Fail open so journaling continues; log at ERROR because timeouts are unexpected.
        logger.error("[safety] classify timed out (fail-open) — message passed without guard check")
        return _SAFE
    except ConnectionError as exc:
        # Ollama not reachable at all — treat as service unavailable, fail open.
        logger.warning("[safety] service unreachable (fail-open): %s", exc)
        return _SAFE
    except Exception as exc:
        # Unexpected error on a per-message call — fail open but log at ERROR
        # so it shows up clearly in the log file for debugging.
        logger.error("[safety] unexpected error during classify (fail-open): %s", exc, exc_info=True)
        return _SAFE
    is_unsafe, categories = _parse(raw)
    kind = _kind_for(categories) if is_unsafe else None
    verdict = SafetyVerdict(flagged=kind is not None, kind=kind, categories=categories, raw=raw.strip())
    if verdict.flagged:
        logger.warning("[safety] flagged — kind=%r categories=%s", kind, categories)
    else:
        logger.debug("[safety] verdict: safe")
    return verdict


async def classify_user_text(text: str) -> SafetyVerdict:
    """Classify a user turn (their journal answer or question)."""
    text = (text or "").strip()
    if not text:
        return _SAFE
    return await _classify([{"role": "user", "content": text}])


async def classify_ai_text(user_text: str, ai_text: str) -> SafetyVerdict:
    """Classify an assistant turn; Llama Guard judges the last (assistant) message."""
    ai_text = (ai_text or "").strip()
    if not ai_text:
        return _SAFE
    return await _classify(
        [
            {"role": "user", "content": (user_text or "").strip() or "(reflection)"},
            {"role": "assistant", "content": ai_text},
        ]
    )
