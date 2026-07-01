"""Tests for generation_registry's reflection-Update hook after an 'Ask
sources' RAG turn (Phase 2b). Regression coverage for the bug found during
manual testing: an exception inside the Update call must never propagate
and turn an already-saved RAG answer into a reported failure."""
import pytest

from app.services import generation_registry as gr
from app.services.reflectionLoop import Focus, Gist, OpenThread, ReflectionState


def _state() -> ReflectionState:
    return ReflectionState(chat_id="4", focus=Focus(value="explore why"))


@pytest.mark.asyncio
async def test_update_hook_swallows_unexpected_exception(monkeypatch):
    """The primary regression case: run_update raising something other than
    JSON/validation errors (its own internal safety net) must not escape
    this function."""
    def boom(*a, **k):
        raise ConnectionError("ollama unreachable mid-call")

    monkeypatch.setattr(gr.reflectionLoop, "run_update", boom)

    # Must not raise.
    await gr._update_reflection_state_after_rag_turn(
        4, _state(), "what should I focus on", "some RAG answer", [], "gemma4:e4b"
    )


@pytest.mark.asyncio
async def test_update_hook_saves_state_on_success(monkeypatch):
    calls = {}

    def fake_run_update(state, question, answer, units, chat_model=None):
        return Gist(text="updated"), OpenThread(text="next"), None

    def fake_save_state(session, chat_id, state):
        calls["saved"] = (chat_id, state.gist.text, state.open_thread.text)

    monkeypatch.setattr(gr.reflectionLoop, "run_update", fake_run_update)
    monkeypatch.setattr(gr, "Session", lambda engine: __import__("contextlib").nullcontext(None))
    monkeypatch.setattr(gr.reflectionStateService, "save_state", fake_save_state)

    await gr._update_reflection_state_after_rag_turn(
        4, _state(), "what should I focus on", "some RAG answer", [], "gemma4:e4b"
    )

    assert calls["saved"] == (4, "updated", "next")


@pytest.mark.asyncio
async def test_update_hook_never_raises_even_on_save_failure(monkeypatch):
    def fake_run_update(state, question, answer, units, chat_model=None):
        return Gist(text="updated"), OpenThread(text="next"), None

    def boom_save(session, chat_id, state):
        raise RuntimeError("db write failed")

    monkeypatch.setattr(gr.reflectionLoop, "run_update", fake_run_update)
    monkeypatch.setattr(gr, "Session", lambda engine: __import__("contextlib").nullcontext(None))
    monkeypatch.setattr(gr.reflectionStateService, "save_state", boom_save)

    # Must not raise — a save failure here still shouldn't fail the RAG turn.
    await gr._update_reflection_state_after_rag_turn(
        4, _state(), "what should I focus on", "some RAG answer", [], "gemma4:e4b"
    )
