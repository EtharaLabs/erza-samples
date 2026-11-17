"""Precomputed day-level matches for DAILY and sub-daily rules (an optimization).

For these frequencies every day-level part is a limit (table lines
2431-2442) and no BYDAY ordinal is allowed (lines 2312-2314), so whether a
date matches depends only on its day of year and on its year's type: leap or
not, and the weekday of January 1. There are 14 year types; each gets the
sorted tuple of matching days of year, computed once from the exact
predicate. ``next_match`` then jumps straight to the next matching date, and
an all-empty mask proves that the rule has no instance at all.
"""

from __future__ import annotations

import calendar
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from .model import MAX_YEAR


def year_type(year: int) -> int:
    """Index 0..13: 7 * leap + weekday of January 1."""
    return 7 * calendar.isleap(year) + date(year, 1, 1).weekday()


@dataclass(frozen=True, slots=True)
class DayMask:
    """Matching days of year (1-based) for each of the 14 year types."""

    by_type: tuple[tuple[int, ...], ...]

    def empty(self) -> bool:
        """True when no date of any year matches."""
        return not any(self.by_type)

    def next_match(self, day: date) -> date | None:
        """First matching date on or after ``day``; None past MAX_YEAR."""
        year = day.year
        position = day.timetuple().tm_yday
        while year <= MAX_YEAR:
            ydays = self.by_type[year_type(year)]
            index = bisect_left(ydays, position)
            if index < len(ydays):
                return date(year, 1, 1) + timedelta(days=ydays[index] - 1)
            year += 1
            position = 1
        return None


def build_mask(matches: Callable[[date], bool]) -> DayMask:
    """Evaluate ``matches`` on one representative year of every type."""
    representative: dict[int, int] = {}
    year = 2001
    while len(representative) < 14:  # noqa: PLR2004 - 14 year types
        representative.setdefault(year_type(year), year)
        year += 1
    rows: list[tuple[int, ...]] = []
    for kind in range(14):
        first = date(representative[kind], 1, 1)
        length = 366 if kind >= 7 else 365  # noqa: PLR2004 - leap types are 7..13
        rows.append(tuple(n + 1 for n in range(length) if matches(first + timedelta(days=n))))
    return DayMask(tuple(rows))
