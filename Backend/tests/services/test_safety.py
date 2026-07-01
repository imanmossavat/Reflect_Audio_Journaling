"""Tests for the Llama Guard category -> wellbeing-kind mapping.

Regression coverage for docs/ISSUES.md #19: S6 ("Specialized Advice") is not
a wellbeing signal and must never trigger the support card on its own — it
false-positived on ordinary planning/strategy conversation.
"""
from app.services.safety import _kind_for, _parse


def test_s6_alone_is_not_flagged():
    assert _kind_for(["S6"]) is None


def test_s11_maps_to_self_harm():
    assert _kind_for(["S11"]) == "self_harm"


def test_s1_and_s2_map_to_support():
    assert _kind_for(["S1"]) == "support"
    assert _kind_for(["S2"]) == "support"


def test_s6_combined_with_a_real_category_does_not_change_the_outcome():
    # S6 riding along with S1 shouldn't upgrade or otherwise alter the verdict —
    # the S1 hit alone already determines "support".
    assert _kind_for(["S6", "S1"]) == "support"


def test_unknown_or_irrelevant_categories_are_not_flagged():
    assert _kind_for(["S6", "S9"]) is None
    assert _kind_for([]) is None


def test_self_harm_wins_priority_over_support():
    assert _kind_for(["S1", "S11"]) == "self_harm"


def test_parse_extracts_categories_from_raw_verdict():
    is_unsafe, categories = _parse("unsafe\nS1,S11")
    assert is_unsafe is True
    assert categories == ["S1", "S11"]


def test_parse_safe_verdict():
    is_unsafe, categories = _parse("safe")
    assert is_unsafe is False
    assert categories == []
