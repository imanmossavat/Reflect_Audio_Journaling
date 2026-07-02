from app.utils.strip_thinking import strip_thinking


def test_no_think_block_returned_unchanged():
    assert strip_thinking("The entry describes a quiet morning.") == "The entry describes a quiet morning."


def test_well_formed_block_is_removed():
    raw = "<think>Hmm, the user wants a summary...</think>The entry describes a quiet morning."
    assert strip_thinking(raw) == "The entry describes a quiet morning."


def test_well_formed_block_with_surrounding_whitespace():
    raw = "<think>reasoning here</think>\n\nThe entry describes a quiet morning."
    assert strip_thinking(raw) == "The entry describes a quiet morning."


def test_unclosed_block_strips_to_end():
    raw = "<think>Hmm, the user wants me to act as a neutral summarization assistant..."
    assert strip_thinking(raw) == ""


def test_dangling_close_with_no_opening_tag_strips_reasoning_prefix():
    # Observed in practice from qwen3:30b via /api/chat with think=false: no literal
    # "<think>" ever appears in message.content, only a "</think>" once reasoning ends.
    raw = (
        "Hmm, the user wants me to act as a neutral summarization assistant...\n"
        "I'll keep it neutral.\n</think>\n\nThe entry describes the writer struggling."
    )
    assert strip_thinking(raw) == "The entry describes the writer struggling."


def test_dangling_close_only_strips_first_occurrence():
    raw = "reasoning</think>The answer mentions </think> as a literal word once."
    assert strip_thinking(raw) == "The answer mentions </think> as a literal word once."


def test_empty_string_returned_as_is():
    assert strip_thinking("") == ""


def test_none_like_falsy_input_returned_as_is():
    assert strip_thinking(None) is None
