"""Tests for the thin-turn detection utility."""
import pytest
from app.services.thin_turn import is_thin_turn


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "ok",
    "okay",
    "yes",
    "no",
    "hmm",
    "idk",
    "maybe",
    "not sure",
    "I don't know",
    "fine.",
    "sure!",
    "Yeah",
    "OK.",
])
def test_thin_turn_detected(text):
    assert is_thin_turn(text) is True


@pytest.mark.parametrize("text", [
    "my team disagreed",                     # 3 words — still thin by word count
])
def test_three_word_is_thin(text):
    assert is_thin_turn(text) is True


@pytest.mark.parametrize("text", [
    "I felt very overwhelmed during the presentation",
    "The project went well overall but the timeline was rushed",
    "I noticed I kept avoiding the harder conversations",
    "We had a conflict about responsibilities in week three",
])
def test_substantive_turn_not_thin(text):
    assert is_thin_turn(text) is False


def test_four_words_not_thin():
    assert is_thin_turn("I felt quite nervous") is False
