"""The retrieve -> Ask -> Update turn loop, Document B §4-§7.

Phase 2a scope (per docs/lexical-spinning-kahn.md plan): built and testable
against an in-memory `ReflectionState` and a whole-source retrieval stub —
no `reflection_state` DB table, no route, no guard wired in yet. Those are
Phase 2b/2c. The `retrieve()` signature is the seam Phase 3 swaps behind
(de-risking seam #1 in the plan) — callers here never change.
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


# ---- Retrieval (de-risking seam #1 — Phase 2a stub, Phase 3 swaps this) -

def whole_source_units(sources: list[dict]) -> list[SourceUnit]:
    """Build one SourceUnit per included source from its whole text.
    Stand-in for real per-unit chunking (Document B §8), which doesn't
    exist yet — `unit_id` is always "full" until Phase 3."""
    return [
        SourceUnit(source_id=str(s["source_id"]), unit_id="full", text=s.get("text") or "")
        for s in sources
        if s.get("text")
    ]


def retrieve(
    query: str,
    chat_id: str,
    units: list[SourceUnit],
    token_budget: int = 250,
) -> list[SourceUnit]:
    """Phase 2a retrieval stand-in: caps combined unit text to ~token_budget
    tokens (approximated as 4 chars/token), no similarity search. `query`
    and `chat_id` are accepted now, unused, so Phase 3's real per-unit
    embedding retrieval can drop in behind this exact signature without
    touching any caller."""
    del query, chat_id  # unused in the stub; kept for interface parity with Phase 3
    budget_chars = token_budget * 4
    capped: list[SourceUnit] = []
    used = 0
    for unit in units:
        remaining = budget_chars - used
        if remaining <= 0:
            break
        text = unit.text if len(unit.text) <= remaining else unit.text[:remaining]
        capped.append(SourceUnit(source_id=unit.source_id, unit_id=unit.unit_id, text=text))
        used += len(text)
    return capped


# ---- Ask -----------------------------------------------------------------

def run_ask(
    state: ReflectionState,
    student_message: str | None,
    retrieved: list[SourceUnit],
    *,
    is_session_start: bool,
    chat_model: str | None = None,
) -> str:
    messages = build_ask_messages(
        state.focus.value,
        state.gist.text,
        state.open_thread.text,
        retrieved,
        student_message,
        is_session_start=is_session_start,
    )
    model = chat_model or get_setting("chat_model")
    response = ollama.chat(model=model, messages=messages, options={"num_ctx": chat_num_ctx()})
    return (response.get("message", {}).get("content") or "").strip()


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
    chat_model: str | None = None,
) -> tuple[Gist, OpenThread, str | None]:
    """Runs the extraction call. On parse/validation failure, keeps the
    prior gist/open_thread unchanged and logs — never raises (§6/§10)."""
    messages = build_update_messages(
        state.gist.text, state.open_thread.text, student_message, facilitator_reply, retrieved
    )
    model = chat_model or get_setting("chat_model")
    response = ollama.chat(
        model=model, messages=messages, format="json", options={"num_ctx": chat_num_ctx()}
    )
    raw = response.get("message", {}).get("content") or ""
    try:
        result = _parse_update_response(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("[reflectionLoop] Update parse/validation failed: %s", exc)
        log_extraction_failure(student_message, raw)
        return state.gist, state.open_thread, None

    new_open_thread = OpenThread(text=result.open_thread.next, source_ref=result.open_thread.source_ref)
    return result.gist, new_open_thread, result.focus_shift_suggested


# ---- Full turn ---------------------------------------------------------

def run_turn(
    state: ReflectionState,
    student_message: str,
    included_sources: list[dict],
    *,
    chat_model: str | None = None,
) -> TurnResult:
    """Document B §4's loop: retrieve -> Ask -> thin-turn gate -> Update."""
    is_session_start = not state.gist.text and state.open_thread.text is None
    units = whole_source_units(included_sources)
    query_text = (
        f"{state.focus.value} {student_message}"
        if is_session_start
        else f"{state.open_thread.text or ''} {student_message}"
    )
    retrieved = retrieve(query_text, state.chat_id, units)

    reply = run_ask(state, student_message, retrieved, is_session_start=is_session_start, chat_model=chat_model)

    if is_thin_turn(student_message):
        return TurnResult(reply=reply, state=state, retrieved=retrieved, updated=False)

    new_gist, new_open_thread, focus_shift = run_update(
        state, student_message, reply, retrieved, chat_model=chat_model
    )
    new_state = state.model_copy(update={"gist": new_gist, "open_thread": new_open_thread})
    return TurnResult(
        reply=reply, state=new_state, retrieved=retrieved, updated=True, focus_shift_suggested=focus_shift
    )
