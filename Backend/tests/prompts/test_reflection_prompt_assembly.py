"""Tests for Document B §5/§6 prompt assembly: slot presence, the session-
start branch, and that no stage name/step number leaks into either prompt
(Document B §9's hard deletions)."""
from app.prompts.reflection_ask_prompt import build_ask_messages
from app.prompts.reflection_update_prompt import build_update_messages
from app.services.reflectionLoop import SourceUnit


def test_ask_session_start_has_no_user_message():
    units = [SourceUnit(source_id="1", unit_id="full", text="journal text")]
    messages = build_ask_messages(
        "explore why", "", None, units, None, is_session_start=True
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "system"
    assert "opening turn" in messages[0]["content"].lower()


def test_ask_normal_turn_includes_student_message():
    units = [SourceUnit(source_id="1", unit_id="full", text="journal text")]
    messages = build_ask_messages(
        "explore why", "prior gist", "open thread text", units, "here's my answer",
        is_session_start=False,
    )
    assert messages[-1] == {"role": "user", "content": "here's my answer"}


def test_ask_prompt_has_no_stage_or_step_language():
    units = [SourceUnit(source_id="1", unit_id="full", text="journal text")]
    messages = build_ask_messages("explore why", "", None, units, None, is_session_start=True)
    content = messages[0]["content"].lower()
    assert "stage" not in content
    assert "step" not in content
    assert "gibbs" not in content


def test_ask_includes_citation_format_instruction():
    messages = build_ask_messages("explore why", "", None, [], None, is_session_start=True)
    assert "{source_id:unit_id}" in messages[0]["content"]


def test_update_prompt_includes_strict_json_schema():
    units = [SourceUnit(source_id="1", unit_id="full", text="journal text")]
    messages = build_update_messages("prior gist", "prior open thread", "student said x", "facilitator replied y", units)
    content = messages[0]["content"]
    assert '"settled"' in content
    assert '"focus_shift_suggested"' in content
    assert "student said x" in content
    assert "facilitator replied y" in content


def test_update_prompt_has_no_stage_or_step_language():
    messages = build_update_messages("", None, "hi", "hello", [])
    content = messages[0]["content"].lower()
    assert "stage" not in content
    assert "step" not in content
