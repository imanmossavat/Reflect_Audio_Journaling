from datetime import datetime

import pytest

from app.services.temporal import DateRange, parse_temporal_range

# Wednesday 2026-06-03 12:00 (weekday=2). Monday of this week is 2026-06-01.
NOW = datetime(2026, 6, 3, 12, 0, 0)


@pytest.mark.parametrize(
    "question,start,end",
    [
        ("what did I do today", datetime(2026, 6, 3), datetime(2026, 6, 4)),
        ("anything yesterday?", datetime(2026, 6, 2), datetime(2026, 6, 3)),
        ("notes from this week", datetime(2026, 6, 1), datetime(2026, 6, 8)),
        ("what happened last week", datetime(2026, 5, 25), datetime(2026, 6, 1)),
        ("this month so far", datetime(2026, 6, 1), datetime(2026, 7, 1)),
        ("recap last month", datetime(2026, 5, 1), datetime(2026, 6, 1)),
        ("this year goals", datetime(2026, 1, 1), datetime(2027, 1, 1)),
        ("last year review", datetime(2025, 1, 1), datetime(2026, 1, 1)),
        ("the last 3 days", datetime(2026, 5, 31, 12), NOW),
        ("past 2 weeks", datetime(2026, 5, 20, 12), NOW),
        ("last 2 months", datetime(2026, 4, 3, 12), NOW),
        ("last 1 year", datetime(2025, 6, 3, 12), NOW),
        ("what about March 2024", datetime(2024, 3, 1), datetime(2024, 4, 1)),
        ("in march", datetime(2026, 3, 1), datetime(2026, 4, 1)),
        ("anything from 2024", datetime(2024, 1, 1), datetime(2025, 1, 1)),
    ],
)
def test_hard_ranges(question, start, end):
    dr = parse_temporal_range(question, NOW)
    assert dr == DateRange(start, end, hard=True)


def test_recently_is_soft():
    dr = parse_temporal_range("how have I felt recently", NOW)
    assert dr is not None
    assert dr.hard is False
    assert dr.start == datetime(2026, 5, 4, 12)
    assert dr.end == NOW


@pytest.mark.parametrize(
    "question",
    [
        "what makes me happy",
        "tell me about my work stress",
        "I may go to the gym",  # bare "may" is the modal verb, not the month
        "",
        "summarize everything",
    ],
)
def test_no_temporal_phrase(question):
    assert parse_temporal_range(question, NOW) is None


def test_zero_count_is_ignored():
    assert parse_temporal_range("last 0 days", NOW) is None
