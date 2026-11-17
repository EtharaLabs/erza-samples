"""Calendar arithmetic: WKST week numbering and positional day indexes."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from .model import Weekday


def week_start(day: date, wkst: Weekday) -> date:
    """First day of the WKST-started week containing ``day`` (lines 2334-2336)."""
    return day - timedelta(days=(day.weekday() - wkst) % 7)


def week_one_start(year: int, wkst: Weekday) -> date:
    """First day of week number one of ``year``.

    "A week is defined as a seven day period, starting on the day of the
    week defined to be the week start (see WKST). Week number one of the
    calendar year is the first week that contains at least four (4) days in
    that calendar year." (lines 2334-2338)
    """
    jan1 = date(year, 1, 1)
    first = week_start(jan1, wkst)
    days_in_year = 7 - (jan1 - first).days
    return first if days_in_year >= 4 else first + timedelta(days=7)  # noqa: PLR2004 - line 2337


def weeks_in_year(year: int, wkst: Weekday) -> int:
    """Number of numbered weeks (52 or 53) of ``year`` under ``wkst``.

    Week N+1 of a year would be week one of the next year, so the count is
    the distance between consecutive week-one starts. For WKST=MO this
    reproduces the note of lines 2342-2344.
    """
    return (week_one_start(year + 1, wkst) - week_one_start(year, wkst)).days // 7

def week_year(day: date, wkst: Weekday) -> int:
    """The year whose numbered weeks (lines 2334-2338) contain ``day``.

    Equal to ``day.year`` except for up to three days at each end of the
    calendar year that belong to the last week of the previous year or to
    week one of the next year.
    """
    if day >= week_one_start(day.year + 1, wkst):
        return day.year + 1
    if day < week_one_start(day.year, wkst):
        return day.year - 1
    return day.year


def week_days(year: int, weekno: int, wkst: Weekday) -> list[date]:
    """The seven days of BYWEEKNO value ``weekno`` of ``year``.

    Valid values are 1 to 53 or -53 to -1 (lines 2332-2333); a negative
    value counts back from the last week of the year (-1 is the last week),
    mirroring the negative conventions of BYMONTHDAY (line 2320) and
    BYYEARDAY (lines 2326-2328). A week number the year does not have (53 in
    a 52-week year) selects nothing.
    """
    count = weeks_in_year(year, wkst)
    number = weekno if weekno > 0 else count + weekno + 1
    if not 1 <= number <= count:
        return []
    first = week_one_start(year, wkst) + timedelta(days=7 * (number - 1))
    return [first + timedelta(days=offset) for offset in range(7)]


def year_length(year: int) -> int:
    """Days in ``year``."""
    return 366 if calendar.isleap(year) else 365


def month_length(year: int, month: int) -> int:
    """Days in ``month`` of ``year``."""
    return calendar.monthrange(year, month)[1]


def yearday_indexes(day: date) -> tuple[int, int]:
    """(positive, negative) BYYEARDAY indexes of ``day``; -1 is December 31 (line 2326)."""
    position = day.timetuple().tm_yday
    return position, position - year_length(day.year) - 1


def monthday_indexes(day: date) -> tuple[int, int]:
    """(positive, negative) BYMONTHDAY indexes of ``day``; -1 is the last day (line 2320)."""
    return day.day, day.day - month_length(day.year, day.month) - 1


def nth_in_month(day: date) -> tuple[int, int]:
    """(n, -m): ``day`` is the n-th and the m-th-to-last of its weekday in its month."""
    return (day.day - 1) // 7 + 1, -((month_length(day.year, day.month) - day.day) // 7 + 1)


def nth_in_year(day: date) -> tuple[int, int]:
    """(n, -m): ``day`` is the n-th and the m-th-to-last of its weekday in its year."""
    position, negative = yearday_indexes(day)
    return (position - 1) // 7 + 1, -((-negative - 1) // 7 + 1)
