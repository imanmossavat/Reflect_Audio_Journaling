"""Tests for turn.py (extraction + merge spine) with a fake chat. No Ollama.
Run: python harness/test_turn.py  (or pytest)."""
import json

from state import STAGE_NAMES, new_session
from turn import ingest_turn, play_session


def _chat(responses):
    """Fake chat returning queued strings; raises if called more often than expected."""
    it = iter(responses)

    def chat(messages):
        try:
            return next(it)
        except StopIteration:
            raise AssertionError("chat called more times than expected")
    return chat


def _no_chat(messages):
    raise AssertionError("extraction must not run on a thin turn")


_DESC_DELTA = json.dumps({
    "new_facts": [{"stage": "Description", "text": "we built a mobile app"},
                  {"stage": "Description", "text": "the team had four people"}],
    "context_updates": {"domain": "software", "project_type": "mobile app",
                        "stakeholders": ["teammates"]},
    "last_turn_summary": "the user described building a mobile app with four teammates",
})


def test_substantive_turn_merges():
    s = new_session()
    ingest_turn(s, "we built a mobile app with four people", "what was your role?", 1, _chat([_DESC_DELTA]))
    assert len(s.facts) == 2
    assert s.context.domain == "software"
    assert s.flow.stage_ready is True   # criteria met -> code recomputed it
    assert s.flow.current_stage == "Description"  # no confirm yet


def test_thin_turn_skips_extraction():
    s = new_session()
    ingest_turn(s, "yes", "great, shall we continue?", 1, _no_chat)
    assert s.facts == []
    assert "brief response" in s.last_turn_summary


def test_bad_json_falls_back():
    s = new_session()
    ingest_turn(s, "a long rambling answer with plenty of words here", "ok", 1, _chat(["not json at all"]))
    assert s.facts == []
    assert "extraction failed" in s.last_turn_summary


def test_play_session_advances_on_confirm():
    s = new_session("sess")
    turns = [
        {"user": "we built a mobile app with four people", "assistant": "what was your role?"},
        {"user": "yes", "assistant": "let's move to how it felt"},
    ]
    play_session(s, turns, _chat([_DESC_DELTA]))   # only turn 1 calls extraction; turn 2 is thin
    assert s.flow.current_stage == "Feelings"
    assert "Description" in s.flow.completed_stages


def test_play_session_returns_snapshots():
    s = new_session("sess")
    turns = [{"user": "yes", "assistant": "ok"}, {"user": "sure", "assistant": "ok"}]
    snaps = play_session(s, turns, _no_chat)
    assert len(snaps) == 2
    assert snaps[0].version < snaps[1].version   # independent snapshots, not aliases


def _main() -> int:
    tests = sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failures += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
