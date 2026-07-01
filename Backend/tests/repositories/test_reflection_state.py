"""Tests for the reflection_state repository/service bridge (Phase 2b):
one row per chat_id, upsert semantics, and Focus's simplified construction
from the existing goal-capture field rather than a new mode picker."""
from database.models import Chat
from app.repositories import reflectionStateRepository
from app.services import reflectionStateService
from app.services.reflectionLoop import Gist, OpenThread, ReflectionState, SourceUnit


def _chat(session, goal=None) -> Chat:
    chat = Chat(title="Test", reflection_goal=goal)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def test_get_by_chat_id_returns_none_when_absent(session):
    assert reflectionStateRepository.get_by_chat_id(session, 999) is None


def test_upsert_creates_then_updates_same_row(session):
    chat = _chat(session)
    reflectionStateRepository.upsert(
        session, chat.id, sources=[], focus={"value": "x", "set_by": "student", "set_at_turn": 0},
        gist={"text": "", "citations": []}, open_thread={"text": None, "source_ref": None},
    )
    row = reflectionStateRepository.get_by_chat_id(session, chat.id)
    assert row.focus["value"] == "x"

    reflectionStateRepository.upsert(
        session, chat.id, sources=[], focus={"value": "y", "set_by": "student", "set_at_turn": 0},
        gist={"text": "updated", "citations": []}, open_thread={"text": None, "source_ref": None},
    )
    row = reflectionStateRepository.get_by_chat_id(session, chat.id)
    assert row.focus["value"] == "y"
    assert row.gist["text"] == "updated"
    # Still one row for this chat, not two.
    assert reflectionStateRepository.get_by_chat_id(session, chat.id).chat_id == chat.id


def test_ensure_state_uses_reflection_goal_as_focus_value(session):
    chat = _chat(session, goal="explore why the deadline slipped")
    state = reflectionStateService.ensure_state(session, chat, [{"source_id": "1", "text": "journal text"}])

    assert state.focus.value == "explore why the deadline slipped"
    assert state.focus.set_by == "student"
    assert state.focus.set_at_turn == 0
    assert state.sources == [SourceUnit(source_id="1", unit_id="full", text="journal text")]
    assert state.gist.text == ""
    assert state.open_thread.text is None


def test_ensure_state_falls_back_when_no_goal_set(session):
    chat = _chat(session, goal=None)
    state = reflectionStateService.ensure_state(session, chat, [])
    assert state.focus.value  # non-empty fallback, not blank


def test_ensure_state_is_idempotent_after_first_creation(session):
    chat = _chat(session, goal="my goal")
    first = reflectionStateService.ensure_state(session, chat, [{"source_id": "1", "text": "a"}])

    # Simulate a turn having updated the persisted Gist.
    reflectionStateService.save_state(
        session, chat.id,
        ReflectionState(chat_id=str(chat.id), sources=first.sources, focus=first.focus,
                         gist=Gist(text="something happened"), open_thread=OpenThread(text="a thread")),
    )

    second = reflectionStateService.ensure_state(session, chat, [{"source_id": "1", "text": "a"}])
    assert second.gist.text == "something happened"
    assert second.open_thread.text == "a thread"


def test_load_state_round_trips_through_save(session):
    chat = _chat(session, goal="g")
    state = reflectionStateService.ensure_state(session, chat, [])
    reflectionStateService.save_state(session, chat.id, state.model_copy(update={"gist": Gist(text="hi")}))

    loaded = reflectionStateService.load_state(session, chat.id)
    assert loaded.gist.text == "hi"
    assert loaded.chat_id == str(chat.id)
