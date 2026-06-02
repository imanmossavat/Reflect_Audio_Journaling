"""Extract a recording date/time from an uploaded filename.

Year-first formats (e.g. ``2024_03_15_09_30_00.mp3``, ``2024-03-15``) are
unambiguous and always parsed. Day/month-first formats (e.g. ``15-03-2024``)
are governed by the ``date_format`` setting (``"dmy"`` or ``"mdy"``); we never
guess which of day or month comes first. Returns a naive ``datetime`` taken as
literal wall-clock time, or ``None`` when no valid date is found.
"""

import os
import re
from datetime import datetime
from typing import Optional

# Any run of these characters counts as a single separator. This covers the
# doubled-underscore case (``2024_03__15``) as well as ``-``, ``.``, ``/``,
# ``:`` and spaces. ``T``/``t`` is allowed only between the date and the time
# block (ISO 8601, e.g. ``2024-03-15T09:30:00``).
_SEP = r"[-_./: ]+"
_DATETIME_SEP = r"[-_./: tT]+"
_OPTIONAL_TIME = rf"(?:{_DATETIME_SEP}(\d{{1,2}}){_SEP}(\d{{1,2}})(?:{_SEP}(\d{{1,2}}))?)?"

_YEAR_FIRST = re.compile(rf"(\d{{4}}){_SEP}(\d{{1,2}}){_SEP}(\d{{1,2}}){_OPTIONAL_TIME}")
_OTHER_FIRST = re.compile(rf"(\d{{1,2}}){_SEP}(\d{{1,2}}){_SEP}(\d{{4}}){_OPTIONAL_TIME}")


def _build(year: int, month: int, day: int, groups: tuple) -> Optional[datetime]:
    """Build a datetime from date parts + the optional H/M/S groups, or None if invalid."""
    hour = int(groups[0]) if groups[0] else 0
    minute = int(groups[1]) if groups[1] else 0
    second = int(groups[2]) if groups[2] else 0
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def parse_datetime_from_filename(filename: Optional[str], date_format: str = "dmy") -> Optional[datetime]:
    """Parse a recording date from ``filename``. See module docstring.

    ``date_format`` selects how day/month-first names are read: ``"dmy"`` (day
    first) or ``"mdy"`` (month first). Year-first names ignore this setting.
    """
    if not filename:
        return None

    stem = os.path.splitext(os.path.basename(filename))[0]

    # Year-first is unambiguous — always try it first.
    match = _YEAR_FIRST.search(stem)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        result = _build(year, month, day, match.groups()[3:])
        if result is not None:
            return result

    # Day/month-first depends on the configured format. We never swap on our
    # own: if the chosen interpretation is invalid, we give up rather than guess.
    match = _OTHER_FIRST.search(stem)
    if match:
        first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if date_format == "mdy":
            month, day = first, second
        else:
            day, month = first, second
        result = _build(year, month, day, match.groups()[3:])
        if result is not None:
            return result

    return None
