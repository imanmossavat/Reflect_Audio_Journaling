from datetime import datetime

import pytest

from app.utils.filename_dates import parse_datetime_from_filename


@pytest.mark.parametrize(
    "filename,expected",
    [
        # Year-first with full time (stakeholder format)
        ("2024_03_15_09_30_00.mp3", datetime(2024, 3, 15, 9, 30, 0)),
        # Doubled separators
        ("2024_03__15__09_30_00.mp3", datetime(2024, 3, 15, 9, 30, 0)),
        # Year-first, date only -> midnight
        ("2024_03_15.mp3", datetime(2024, 3, 15, 0, 0, 0)),
        # ISO-ish with T separator and dashes/colons
        ("2024-03-15T09:30:00.wav", datetime(2024, 3, 15, 9, 30, 0)),
        # Date embedded after other text
        ("recording 2024-03-15.m4a", datetime(2024, 3, 15, 0, 0, 0)),
    ],
)
def test_year_first_is_unambiguous(filename, expected):
    # Year-first ignores the date_format setting.
    assert parse_datetime_from_filename(filename, "mdy") == expected
    assert parse_datetime_from_filename(filename, "dmy") == expected


def test_day_first_respects_dmy():
    assert parse_datetime_from_filename("15-03-2024.mp3", "dmy") == datetime(2024, 3, 15)


def test_month_first_respects_mdy():
    assert parse_datetime_from_filename("03-15-2024.mp3", "mdy") == datetime(2024, 3, 15)


def test_no_silent_swap_on_invalid_interpretation():
    # "15" can't be a month, and we never guess -> None instead of swapping.
    assert parse_datetime_from_filename("15-03-2024.mp3", "mdy") is None


@pytest.mark.parametrize(
    "filename",
    [
        "meeting notes.mp3",
        "voice memo.m4a",
        "",
        None,
        "track-01.wav",
    ],
)
def test_no_date_returns_none(filename):
    assert parse_datetime_from_filename(filename, "dmy") is None
