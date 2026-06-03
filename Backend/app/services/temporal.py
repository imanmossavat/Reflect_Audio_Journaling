import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

SOFT_WINDOW_DAYS = 30


@dataclass(frozen=True)
class DateRange:
    start: datetime  # inclusive, naive UTC
    end: datetime    # exclusive, naive UTC
    hard: bool = True  # True => usable as a SQL pre-filter


_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_UNIT_TODAY = re.compile(r"\btoday\b")
_UNIT_YESTERDAY = re.compile(r"\byesterday\b")
_THIS_WEEK = re.compile(r"\bthis week\b")
_LAST_WEEK = re.compile(r"\blast week\b")
_THIS_MONTH = re.compile(r"\bthis month\b")
_LAST_MONTH = re.compile(r"\blast month\b")
_THIS_YEAR = re.compile(r"\bthis year\b")
_LAST_YEAR = re.compile(r"\blast year\b")
_LAST_N = re.compile(r"\b(?:last|past|previous)\s+(\d+)\s+(day|week|month|year)s?\b")
_SOFT = re.compile(r"\b(recently|lately)\b")
# "March", "in March", "March 2024" — the year group is optional.
_NAMED_MONTH = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b"
    r"(?:\s+(\d{4}))?"
)
_BARE_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(dt: datetime) -> datetime:
    d = _start_of_day(dt)
    return d - timedelta(days=d.weekday())


def _start_of_month(dt: datetime) -> datetime:
    return _start_of_day(dt).replace(day=1)


def _start_of_year(dt: datetime) -> datetime:
    return _start_of_day(dt).replace(month=1, day=1)


def _shift_months(dt: datetime, months: int) -> datetime:
    """Shift by whole months, clamping the day to the target month's length."""
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def parse_temporal_range(question: str, now: Optional[datetime] = None) -> Optional[DateRange]:
    """Return a naive-UTC ``[start, end)`` range if ``question`` carries a
    recognizable temporal phrase, else ``None``. ``now`` defaults to
    ``datetime.utcnow()`` and is injectable for tests."""
    if not question:
        return None
    now = now or datetime.utcnow()
    q = question.lower()

    if _UNIT_TODAY.search(q):
        start = _start_of_day(now)
        return DateRange(start, start + timedelta(days=1))

    if _UNIT_YESTERDAY.search(q):
        start = _start_of_day(now) - timedelta(days=1)
        return DateRange(start, start + timedelta(days=1))

    if _LAST_WEEK.search(q):
        this_week = _start_of_week(now)
        return DateRange(this_week - timedelta(weeks=1), this_week)
    if _THIS_WEEK.search(q):
        this_week = _start_of_week(now)
        return DateRange(this_week, this_week + timedelta(weeks=1))

    if _LAST_MONTH.search(q):
        this_month = _start_of_month(now)
        return DateRange(_shift_months(this_month, -1), this_month)
    if _THIS_MONTH.search(q):
        this_month = _start_of_month(now)
        return DateRange(this_month, _shift_months(this_month, 1))

    if _LAST_YEAR.search(q):
        this_year = _start_of_year(now)
        return DateRange(this_year.replace(year=this_year.year - 1), this_year)
    if _THIS_YEAR.search(q):
        this_year = _start_of_year(now)
        return DateRange(this_year, this_year.replace(year=this_year.year + 1))

    m = _LAST_N.search(q)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if n <= 0:
            return None
        if unit == "day":
            start = now - timedelta(days=n)
        elif unit == "week":
            start = now - timedelta(weeks=n)
        elif unit == "month":
            start = _shift_months(now, -n)
        else:  # year
            start = _shift_months(now, -n * 12)
        return DateRange(start, now)

    if _SOFT.search(q):
        return DateRange(now - timedelta(days=SOFT_WINDOW_DAYS), now, hard=False)

    m = _NAMED_MONTH.search(q)
    # Bare "may" is almost always the modal verb — only treat it as a month
    # when an explicit year disambiguates it.
    if m and not (m.group(1) == "may" and not m.group(2)):
        month = _MONTHS[m.group(1)]
        if m.group(2):
            year = int(m.group(2))
        else:
            # No year given: the most recent occurrence of that month, this year
            # if it has already started, otherwise last year.
            year = now.year if month <= now.month else now.year - 1
        start = datetime(year, month, 1)
        return DateRange(start, _shift_months(start, 1))

    m = _BARE_YEAR.search(q)
    if m:
        year = int(m.group(1))
        start = datetime(year, 1, 1)
        return DateRange(start, start.replace(year=year + 1))

    return None
