"""The retrieve -> Ask -> Update turn loop, Document B §4-§7.

Phase 2a built this against an in-memory `ReflectionState` and a
whole-source retrieval stub. Phase 2b wired in: the guard on every Ask
call, and a `resolve_hint` the "Answer & next"/"finish" lever can set to
feed the student's explicit confirmation into Update's judgment on whether
to settle the Open Thread — a hint, not a code-level override; Document B
§6 is explicit that "settled" stays a model judgment call, not a threshold.
Phase 3 swapped `retrieve()`'s stub for real per-unit similarity search
(de-risking seam #1) — Ask/Update never changed across that swap.
"""
from __future__ import annotations

import json
from typing import Literal

import ollama
from pydantic import BaseModel, ValidationError

from app import logging_config
from app.logging_config import LOGS_DIR
from app.prompts.reflection_ask_prompt import build_ask_messages
from app.prompts.reflection_update_prompt import build_update_messages
from app.services import reflection_guard
from app.services import retrieval
from app.services.settings_service import chat_num_ctx, get_setting
from app.services.thin_turn import is_thin_turn

logger = logging_config.logger

FAILURE_LOG = f"{LOGS_DIR}/reflection_extraction_failures.log"


# ---- Document B §2 types -----------------------------------------------

class SourceUnit(BaseModel):
    source_id: str
    unit_id: str
    text: str


class Citation(BaseModel):
    source_id: str
    unit_id: str


class Focus(BaseModel):
    value: str
    set_by: Literal["student"] = "student"
    set_at_turn: int = 0


class Gist(BaseModel):
    text: str = ""
    citations: list[Citation] = []


class OpenThread(BaseModel):
    text: str | None = None
    source_ref: Citation | None = None


class ReflectionState(BaseModel):
    chat_id: str
    sources: list[SourceUnit] = []
    focus: Focus
    gist: Gist = Gist()
    open_thread: OpenThread = OpenThread()


# ---- Update's strict JSON output shape (§6) -----------------------------

class _UpdateOpenThread(BaseModel):
    settled: bool
    next: str | None = None
    source_ref: Citation | None = None


class UpdateResult(BaseModel):
    gist: Gist
    open_thread: _UpdateOpenThread
    focus_shift_suggested: str | None = None


class TurnResult(BaseModel):
    reply: str
    state: ReflectionState
    retrieved: list[SourceUnit]
    updated: bool
    focus_shift_suggested: str | None = None


# ---- Retrieval (de-risking seam #1 — real per-unit search as of Phase 3) --

def retrieve(
    query: str,
    chat_id: str,
    source_ids: list[str],
    token_budget: int = 250,
) -> list[SourceUnit]:
    """Contract §4's RETRIEVE step: real per-unit similarity search
    (`retrieval.retrieve_units`), hard-scoped to `source_ids` (the
    reflection session's included sources), capped to ~token_budget tokens
    (approximated as 4 chars/token) combined (§5's budget table).

    `chat_id` isn't used for Chroma scoping — see `retrieve_units`'s
    docstring for why — kept in this signature for interface stability.
    Zero results (e.g. a source ingested before Phase 3, not yet
    backfilled) isn't an error: Ask proceeds on Focus/Gist/Open Thread
    alone, per Contract §10's failure-handling table."""
    del chat_id
    nodes = retrieval.retrieve_units(query, source_ids, top_k=5)
    serialized = retrieval.serialize_unit_nodes(nodes)

    budget_chars = token_budget * 4
    capped: list[SourceUnit] = []
    used = 0
    for item in serialized:
        remaining = budget_chars - used
        if remaining <= 0:
            break
        text = item["text"] if len(item["text"]) <= remaining else item["text"][:remaining]
        capped.append(SourceUnit(source_id=item["source_id"], unit_id=item["unit_id"], text=text))
        used += len(text)
    return capped


# ---- Ask -----------------------------------------------------------------

def _call_ask_model(messages: list[dict], model: str) -> str:
    response = ollama.chat(model=model, messages=messages, options={"num_ctx": chat_num_ctx()})
    return (response.get("message", {}).get("content") or "").strip()


def run_ask(
    state: ReflectionState,
    student_message: str | None,
    retrieved: list[SourceUnit],
    *,
    is_session_start: bool,
    chat_model: str | None = None,
) -> str:
    """Ask (generation), guarded: an obvious injection attempt short-circuits
    to a fixed redirect before any model call; a reply that leaks scaffolding,
    breaks format, or asks more than one question gets one repair attempt,
    then a fixed fallback if it still violates (Phase 2b, guard ported from
    the eval harness — see reflection_guard.py)."""
    model = chat_model or get_setting("chat_model")
    has_context = bool(retrieved) or bool(state.gist.text)

    if student_message:
        intent = reflection_guard.injection_intent(student_message)
        if intent:
            logger.info("[reflectionLoop] input guard tripped (%s) — short-circuiting", intent)
            return reflection_guard.injection_redirect(has_context=has_context)

    messages = build_ask_messages(
        state.focus.value,
        state.gist.text,
        state.open_thread.text,
        retrieved,
        student_message,
        is_session_start=is_session_start,
    )
    reply = _call_ask_model(messages, model)

    violations = reflection_guard.output_violations(reply, student_message or "")
    if violations:
        logger.info("[reflectionLoop] output guard violations, repairing once: %s", violations)
        repaired_messages = reflection_guard.repair_messages(messages, reply, violations)
        reply = _call_ask_model(repaired_messages, model)
        violations = reflection_guard.output_violations(reply, student_message or "")
        if violations:
            logger.warning(
                "[reflectionLoop] output guard violations persisted after repair, falling back: %s",
                violations,
            )
            reply = reflection_guard.safe_fallback(has_context=has_context)

    return reply


# ---- Update ----------------------------------------------------------------

def log_extraction_failure(user_message: str, raw_response: str) -> None:
    """Document B §10 — log and move on, never retry."""
    import datetime as _dt

    entry = {
        "timestamp": _dt.datetime.utcnow().isoformat(),
        "user_message": (user_message or "")[:200],
        "raw_response": (raw_response or "")[:500],
    }
    with open(FAILURE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _parse_update_response(raw: str) -> UpdateResult:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text)
    return UpdateResult.model_validate(parsed)


def run_update(
    state: ReflectionState,
    student_message: str,
    facilitator_reply: str,
    retrieved: list[SourceUnit],
    *,
    resolve_hint: bool = False,
    chat_model: str | None = None,
) -> tuple[Gist, OpenThread, str | None]:
    """Runs the extraction call. Never raises (§6/§10) — on parse/validation
    failure, or any other failure (e.g. the model call itself erroring —
    §6 only explicitly names JSON/validation failures, but the same "keep
    prior state, Ask's reply still goes through" rule has to extend to any
    Update failure, not just a malformed response, or a caller several
    layers up ends up discarding an already-generated Ask reply over an
    Update-only problem), keeps the prior gist/open_thread unchanged and
    logs."""
    messages = build_update_messages(
        state.gist.text, state.open_thread.text, student_message, facilitator_reply, retrieved,
        resolve_hint=resolve_hint,
    )
    model = chat_model or get_setting("chat_model")
    try:
        response = ollama.chat(
            model=model, messages=messages, format="json", options={"num_ctx": chat_num_ctx()}
        )
        raw = response.get("message", {}).get("content") or ""
        result = _parse_update_response(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("[reflectionLoop] Update parse/validation failed: %s", exc)
        log_extraction_failure(student_message, raw)
        return state.gist, state.open_thread, None
    except Exception as exc:
        logger.error("[reflectionLoop] Update call failed unexpectedly: %s", exc, exc_info=True)
        log_extraction_failure(student_message, str(exc))
        return state.gist, state.open_thread, None

    new_open_thread = OpenThread(text=result.open_thread.next, source_ref=result.open_thread.source_ref)
    return result.gist, new_open_thread, result.focus_shift_suggested


# ---- Full turn ---------------------------------------------------------

def run_turn(
    state: ReflectionState,
    student_message: str,
    included_sources: list[dict],
    *,
    resolve_hint: bool = False,
    chat_model: str | None = None,
) -> TurnResult:
    """Document B §4's loop: retrieve -> Ask -> thin-turn gate -> Update.

    `resolve_hint` — see `run_update` — is set when the caller fired via the
    "Answer & next/finish" lever."""
    is_session_start = not state.gist.text and state.open_thread.text is None
    source_ids = [str(s["source_id"]) for s in included_sources if s.get("source_id") is not None]
    query_text = (
        f"{state.focus.value} {student_message}"
        if is_session_start
        else f"{state.open_thread.text or ''} {student_message}"
    )
    retrieved = retrieve(query_text, state.chat_id, source_ids)

    reply = run_ask(state, student_message, retrieved, is_session_start=is_session_start, chat_model=chat_model)

    if is_thin_turn(student_message):
        return TurnResult(reply=reply, state=state, retrieved=retrieved, updated=False)

    new_gist, new_open_thread, focus_shift = run_update(
        state, student_message, reply, retrieved, resolve_hint=resolve_hint, chat_model=chat_model
    )
    new_state = state.model_copy(update={"gist": new_gist, "open_thread": new_open_thread})
    return TurnResult(
        reply=reply, state=new_state, retrieved=retrieved, updated=True, focus_shift_suggested=focus_shift
    )


_NO_REPLY_PLACEHOLDER = (
    "(no facilitator reply — the student recorded an answer without prompting a new question)"
)


def run_reflect_only(
    state: ReflectionState,
    student_message: str,
    included_sources: list[dict],
    *,
    chat_model: str | None = None,
) -> TurnResult:
    """The "Answer" lever (onReflect): record the message and run Update only
    — no Ask call, no guard, no facilitator reply shown. Document B's Update
    prompt still expects "the exchange that just happened"; a fixed
    placeholder stands in for the missing facilitator turn."""
    source_ids = [str(s["source_id"]) for s in included_sources if s.get("source_id") is not None]
    query_text = f"{state.open_thread.text or state.focus.value} {student_message}"
    retrieved = retrieve(query_text, state.chat_id, source_ids)

    if is_thin_turn(student_message):
        return TurnResult(reply="", state=state, retrieved=retrieved, updated=False)

    new_gist, new_open_thread, focus_shift = run_update(
        state, student_message, _NO_REPLY_PLACEHOLDER, retrieved, chat_model=chat_model
    )
    new_state = state.model_copy(update={"gist": new_gist, "open_thread": new_open_thread})
    return TurnResult(
        reply="", state=new_state, retrieved=retrieved, updated=True, focus_shift_suggested=focus_shift
    )
