"""Bridges the persisted `reflection_state` row (database.models.ReflectionState)
and the in-memory Pydantic type the turn loop works with
(app.services.reflectionLoop.ReflectionState) — Phase 2b wiring the Phase 2a
loop logic to a real chat, per docs/lexical-spinning-kahn.md.
"""
from sqlmodel import Session

from app.repositories import reflectionStateRepository
from app.services.reflectionLoop import Focus, Gist, OpenThread, ReflectionState, SourceUnit
from database.models import Chat


def _row_to_state(row, chat_id: int) -> ReflectionState:
    return ReflectionState(
        chat_id=str(chat_id),
        sources=[SourceUnit(**s) for s in (row.sources or [])],
        focus=Focus(**row.focus) if row.focus else Focus(value=""),
        gist=Gist(**row.gist) if row.gist else Gist(),
        open_thread=OpenThread(**row.open_thread) if row.open_thread else OpenThread(),
    )


def load_state(session: Session, chat_id: int) -> ReflectionState | None:
    row = reflectionStateRepository.get_by_chat_id(session, chat_id)
    if row is None:
        return None
    return _row_to_state(row, chat_id)


def save_state(session: Session, chat_id: int, state: ReflectionState) -> None:
    reflectionStateRepository.upsert(
        session,
        chat_id,
        sources=[s.model_dump() for s in state.sources],
        focus=state.focus.model_dump(),
        gist=state.gist.model_dump(),
        open_thread=state.open_thread.model_dump(),
    )


def ensure_state(session: Session, chat: Chat, included_sources: list[dict]) -> ReflectionState:
    """Load the existing row for this chat, or create one.

    `Focus`, simplified per direct instruction (see the plan): `value` is the
    existing goal-capture text as-is — no new mode-picker UI — `set_by` is
    fixed "student" (goal is already always student-entered today), and
    `set_at_turn` is recorded as 0 here, automatically, the first time a
    reflection turn runs for this chat.
    """
    existing = load_state(session, chat.id)
    if existing is not None:
        return existing

    focus_value = (chat.reflection_goal or "").strip() or "reflect on this entry"
    units = [
        SourceUnit(source_id=str(s["source_id"]), unit_id="full", text=s.get("text") or "")
        for s in included_sources
        if s.get("text")
    ]
    state = ReflectionState(
        chat_id=str(chat.id),
        sources=units,
        focus=Focus(value=focus_value, set_at_turn=0),
    )
    save_state(session, chat.id, state)
    return state
