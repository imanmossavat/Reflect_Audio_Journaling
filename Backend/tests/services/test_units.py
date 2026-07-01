"""Tests for Document B §8's per-unit addressing scheme."""
from app.services.units import compute_units


def test_typed_entry_splits_on_paragraph_boundaries():
    text = "First paragraph, some thoughts.\n\nSecond paragraph, more thoughts.\n\nThird one."
    units = compute_units(text, None)
    assert [u["unit_id"] for u in units] == ["p0", "p1", "p2"]
    assert units[0]["text"] == "First paragraph, some thoughts."
    assert units[1]["text"] == "Second paragraph, more thoughts."


def test_typed_entry_ignores_blank_paragraphs():
    text = "One.\n\n\n\nTwo.\n\n   \n\nThree."
    units = compute_units(text, None)
    assert [u["text"] for u in units] == ["One.", "Two.", "Three."]


def test_typed_entry_single_paragraph():
    units = compute_units("Just one block of text, no blank lines.", None)
    assert len(units) == 1
    assert units[0]["unit_id"] == "p0"


def test_empty_text_produces_no_units():
    assert compute_units("", None) == []
    assert compute_units(None, None) == []


def test_transcript_segments_produce_stable_indexed_units():
    segments = [
        {"text": "First thing I said.", "start_s": 0.0, "end_s": 2.1},
        {"text": "Second thing.", "start_s": 2.1, "end_s": 4.0},
    ]
    units = compute_units("First thing I said. Second thing.", segments)
    assert [u["unit_id"] for u in units] == ["s0", "s1"]
    assert units[0]["text"] == "First thing I said."


def test_transcript_segments_skip_blank_entries():
    segments = [{"text": "  "}, {"text": "real content"}]
    units = compute_units("real content", segments)
    assert len(units) == 1
    assert units[0]["unit_id"] == "s1"  # index preserved, not renumbered
    assert units[0]["text"] == "real content"


def test_transcript_segments_take_precedence_over_paragraph_split():
    # Even if the flattened text happens to contain blank lines, audio sources
    # use segment boundaries, not paragraph splitting.
    segments = [{"text": "a"}, {"text": "b"}]
    units = compute_units("a\n\nb", segments)
    assert [u["unit_id"] for u in units] == ["s0", "s1"]
