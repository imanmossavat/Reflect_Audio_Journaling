"""Tests for state.py. No Ollama. Run: python harness/test_state.py  (or pytest)."""
import state
from state import (
    ContextUpdate,
    ExtractionDelta,
    Fact,
    GoalUpdate,
    NewFact,
    NewQuestion,
    OpenQuestion,
    SessionState,
    STAGE_NAMES,
    apply_delta,
    check_advance_confirmation,
    check_stage_completion,
    handle_extraction_failure,
    handle_thin_turn,
    is_duplicate_fact,
    is_thin_turn,
    maybe_advance,
    new_session,
    parse_extraction_response,
    prepare_turn,
)


def _delta(**kw) -> ExtractionDelta:
    kw.setdefault("last_turn_summary", "the student described their project clearly")
    return ExtractionDelta(**kw)


def _run_turn(state_, turn: int, user_message: str, delta) -> SessionState:
    """Deterministic spine of a turn, same order Backend will use."""
    prepare_turn(state_, user_message)
    if is_thin_turn(user_message):
        handle_thin_turn(state_, user_message, turn)
    elif delta is None:
        handle_extraction_failure(state_, user_message, turn)
    else:
        apply_delta(state_, delta, turn)
    maybe_advance(state_)
    return state_


def test_new_session_defaults():
    s = new_session("abc")
    assert s.session_id == "abc"
    assert s.version == 1
    assert s.flow.current_stage == "Description"
    assert s.flow.completed_stages == []
    assert s.facts == []
    assert set(s.stage_summaries) == set(STAGE_NAMES)
    assert all(v is None for v in s.stage_summaries.values())
    assert s.session_complete is False


def test_is_thin_turn():
    assert is_thin_turn("yes")
    assert is_thin_turn("I don't know")
    assert is_thin_turn("ok.")
    assert is_thin_turn("my team disagreed")  # <=3 words counts as thin
    assert not is_thin_turn("we built a mobile app over four sprints")


def test_check_advance_confirmation():
    assert check_advance_confirmation("yes")
    assert check_advance_confirmation("ok let's move on")
    assert check_advance_confirmation("sure, go ahead")
    assert not check_advance_confirmation("no not yet")
    assert not check_advance_confirmation("I felt anxious about it")


def test_description_completion_requires_context_and_two_facts():
    s = new_session()
    assert not check_stage_completion(s)
    s.context.domain = "software"
    s.context.project_type = "mobile app"
    s.context.stakeholders = ["teammates"]
    s.facts.append(Fact(id="fact-001", stage="Description", text="we built an app", turn=1))
    assert not check_stage_completion(s)
    s.facts.append(Fact(id="fact-002", stage="Description", text="four people", turn=1))
    assert check_stage_completion(s)


def test_feelings_completion_needs_emotional_keyword():
    s = new_session()
    s.flow.current_stage = "Feelings"
    s.facts.append(Fact(id="fact-001", stage="Feelings", text="it was a tuesday", turn=1))
    assert not check_stage_completion(s)
    s.facts.append(Fact(id="fact-002", stage="Feelings", text="I felt frustrated", turn=2))
    assert check_stage_completion(s)


def test_evaluation_needs_both_polarities():
    s = new_session()
    s.flow.current_stage = "Evaluation"
    s.facts.append(Fact(id="fact-001", stage="Evaluation", text="the planning went well", turn=1))
    assert not check_stage_completion(s)
    s.facts.append(Fact(id="fact-002", stage="Evaluation", text="the deadline was difficult", turn=2))
    assert check_stage_completion(s)


def test_action_orientation_needs_specific_target():
    s = new_session()
    s.flow.current_stage = "Action Orientation"
    s.goal.two_week_target = "do better"
    assert not check_stage_completion(s)
    s.goal.two_week_target = "set up a testing checklist for the team"
    assert check_stage_completion(s)


def test_apply_delta_appends_facts_with_sequential_ids():
    s = new_session()
    apply_delta(s, _delta(new_facts=[
        NewFact(stage="Description", text="we built a mobile app"),
        NewFact(stage="Description", text="the team had four people"),
    ]), turn=1)
    assert [f.id for f in s.facts] == ["fact-001", "fact-002"]
    assert s.facts[0].turn == 1
    assert s.version == 2
    assert s.flow.turns_in_stage == 1


def test_is_duplicate_fact_substring_both_ways_same_stage_only():
    facts = [Fact(id="fact-001", stage="Description", text="we built a mobile app", turn=1)]
    assert is_duplicate_fact("we built a mobile app", facts, "Description")
    assert is_duplicate_fact("a mobile app", facts, "Description")
    assert is_duplicate_fact("we built a mobile app for the client", facts, "Description")
    assert not is_duplicate_fact("we built a mobile app", facts, "Feelings")
    assert not is_duplicate_fact("the deadline slipped", facts, "Description")


def test_apply_delta_dedups():
    s = new_session()
    apply_delta(s, _delta(new_facts=[NewFact(stage="Description", text="we built a mobile app")]), turn=1)
    apply_delta(s, _delta(new_facts=[NewFact(stage="Description", text="we built a mobile app")]), turn=2)
    assert len(s.facts) == 1


def test_context_merge_never_blanks_existing():
    s = new_session()
    s.context.domain = "software"
    apply_delta(s, _delta(context_updates=ContextUpdate(project_type="mobile app")), turn=1)
    assert s.context.domain == "software"
    assert s.context.project_type == "mobile app"


def test_stage_ready_is_code_authoritative_not_model():
    s = new_session()
    apply_delta(s, _delta(new_facts=[NewFact(stage="Description", text="we built an app")],
                          stage_ready=True), turn=1)
    assert s.flow.stage_ready is False


def test_resolve_and_add_questions():
    s = new_session()
    s.open_questions.append(OpenQuestion(id="q-001", text="who was involved?", stage="Description"))
    apply_delta(s, _delta(resolved_question_ids=["q-001"],
                          new_open_questions=[NewQuestion(text="what changed?", stage="Description")]), turn=1)
    assert s.open_questions[0].resolved is True
    assert s.open_questions[1].id == "q-002"
    assert s.open_questions[1].resolved is False


def test_parse_good_json():
    raw = '{"new_facts": [], "last_turn_summary": "the student described the project"}'
    delta = parse_extraction_response(raw)
    assert isinstance(delta, ExtractionDelta)
    assert delta.last_turn_summary == "the student described the project"


def test_parse_strips_markdown_fence():
    raw = '```json\n{"last_turn_summary": "the student described the project"}\n```'
    assert parse_extraction_response(raw) is not None


def test_parse_returns_none_on_bad_json():
    assert parse_extraction_response("{not valid json") is None


def test_parse_returns_none_on_schema_violation():
    assert parse_extraction_response('{"last_turn_summary": "x"}') is None  # too short
    assert parse_extraction_response('{"new_facts": []}') is None           # missing summary
    assert parse_extraction_response(
        '{"new_facts": [{"stage": "Nope", "text": "hello there"}], '
        '"last_turn_summary": "a perfectly valid summary line"}') is None    # invalid stage


def test_handle_thin_turn_records_without_facts():
    s = new_session()
    v0 = s.version
    handle_thin_turn(s, "yes", turn=1)
    assert s.facts == []
    assert s.version == v0 + 1
    assert s.flow.turns_in_stage == 1
    assert "brief response" in s.last_turn_summary


def test_handle_extraction_failure_keeps_prior_state():
    s = new_session()
    s.facts.append(Fact(id="fact-001", stage="Description", text="we built an app", turn=1))
    v0 = s.version
    handle_extraction_failure(s, "some rambling reply", turn=2, raw_response="not json")
    assert len(s.facts) == 1
    assert s.version == v0 + 1
    assert "extraction failed" in s.last_turn_summary


def test_full_session_walks_all_stages_with_confirmation():
    s = new_session("session-1")

    _run_turn(s, 1, "we built a mobile app with a team of four", _delta(
        new_facts=[NewFact(stage="Description", text="we built a mobile app"),
                   NewFact(stage="Description", text="the team had four people")],
        context_updates=ContextUpdate(domain="software", project_type="mobile app",
                                      stakeholders=["teammates"])))
    assert s.flow.current_stage == "Description"  # needs explicit confirm
    assert s.flow.stage_ready is True
    _run_turn(s, 2, "yes", None)  # thin confirm must advance
    assert s.flow.current_stage == "Feelings"
    assert "Description" in s.flow.completed_stages
    assert "mobile app" in s.stage_summaries["Description"]
    assert s.flow.turns_in_stage == 0

    _run_turn(s, 3, "I felt frustrated when we kept slipping", _delta(
        new_facts=[NewFact(stage="Feelings", text="I felt frustrated when we slipped")]))
    _run_turn(s, 4, "sure", None)
    assert s.flow.current_stage == "Evaluation"

    _run_turn(s, 5, "the planning went well but the deadline was difficult", _delta(
        new_facts=[NewFact(stage="Evaluation", text="the planning went well"),
                   NewFact(stage="Evaluation", text="the deadline was difficult")]))
    _run_turn(s, 6, "ready", None)
    assert s.flow.current_stage == "Analysis"

    _run_turn(s, 7, "we missed it because we underestimated testing", _delta(
        new_facts=[NewFact(stage="Analysis", text="we missed the deadline because we underestimated testing")]))
    _run_turn(s, 8, "let's move on", None)
    assert s.flow.current_stage == "Conclusion"

    _run_turn(s, 9, "I learned to plan testing earlier", _delta(
        new_facts=[NewFact(stage="Conclusion", text="I learned to plan testing earlier")]))
    _run_turn(s, 10, "go ahead", None)
    assert s.flow.current_stage == "Action Orientation"

    _run_turn(s, 11, "I want to set up a shared testing checklist for the team", _delta(
        goal_updates=GoalUpdate(two_week_target="set up a shared testing checklist for the team")))
    assert s.flow.stage_ready is True
    _run_turn(s, 12, "yes", None)

    assert s.session_complete is True
    assert s.flow.completed_stages == STAGE_NAMES


def test_early_yes_cannot_skip_a_stage():
    s = new_session()
    _run_turn(s, 1, "yes", None)
    assert s.flow.current_stage == "Description"
    assert s.flow.completed_stages == []


def test_stage_names_match_production_prompt():
    try:
        import _bootstrap  # noqa: F401
        from app.prompts.gibbs_facilitator_prompt import STAGES
    except Exception as e:
        print(f"  (skipped lock-step check: {e})")
        return
    production = [STAGES[i]["name"] for i in sorted(STAGES)]
    assert production == STAGE_NAMES, f"stage drift: {production} != {STAGE_NAMES}"


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
