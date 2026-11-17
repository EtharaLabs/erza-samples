"""Seeded drawing primitives shared by the category generators.

Every function takes the category's ``random.Random`` and nothing else that varies, so a fixed
seed reproduces the same draws in the same order.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from random import Random
from typing import Final

from gen.spec import DAYS, Spec

STEP: Final = {
    "YEARLY": timedelta(days=366),
    "MONTHLY": timedelta(days=31),
    "WEEKLY": timedelta(days=7),
    "DAILY": timedelta(days=1),
    "HOURLY": timedelta(hours=1),
    "MINUTELY": timedelta(minutes=1),
    "SECONDLY": timedelta(seconds=1),
}


class GenerationExhaustedError(RuntimeError):
    """A generator drew its attempt ceiling without reaching the case count."""

    def __init__(self, category: str, made: int, wanted: int) -> None:
        super().__init__(f"{category}: {made} of {wanted} cases after the attempt ceiling")
        self.category: Final = category


def attempts_ceiling(wanted: int) -> int:
    """A generous but finite number of drafts per category."""
    return wanted * 60


def wall_time(rng: Random) -> tuple[int, int, int]:
    """An hour, minute, and second, biased to round values."""
    return rng.randint(0, 23), rng.choice((0, 0, 0, 15, 30, 45, rng.randint(0, 59))), rng.choice((0, 0, 0, 30))


def anchor(rng: Random, first_year: int = 1995, last_year: int = 2035) -> datetime:
    """A naive wall time on a random day."""
    hour, minute, second = wall_time(rng)
    return datetime(rng.randint(first_year, last_year), rng.randint(1, 12), rng.randint(1, 28), hour, minute, second)


def month_day(year: int, month: int, day: int) -> date | None:
    """The date a BYMONTHDAY value names in one month, if it exists."""
    length = calendar.monthrange(year, month)[1]
    number = day if day > 0 else length + day + 1
    return date(year, month, number) if 1 <= number <= length else None


def pick(rng: Random, pool: Sequence[int], low: int, high: int) -> tuple[int, ...]:
    """Between ``low`` and ``high`` distinct values from ``pool``, in draw order."""
    return tuple(rng.sample(list(pool), rng.randint(low, high)))


def plain_days(rng: Random, low: int, high: int) -> tuple[tuple[int | None, str], ...]:
    """Distinct weekdays without ordinals, in calendar order."""
    chosen = sorted(rng.sample(range(7), rng.randint(low, high)))
    return tuple((None, DAYS[i]) for i in chosen)


def ordinal_days(rng: Random, ordinals: list[int], low: int, high: int) -> tuple[tuple[int | None, str], ...]:
    """Weekdays with ordinals, each pair distinct."""
    wanted = rng.randint(low, high)
    seen: list[tuple[int | None, str]] = []
    while len(seen) < wanted:
        item: tuple[int | None, str] = (rng.choice(ordinals), rng.choice(DAYS))
        if item not in seen:
            seen.append(item)
    return tuple(seen)


def small_ordinals(limit: int) -> list[int]:
    """Signed ordinals in ``1..limit`` with small magnitudes weighted up."""
    values = [o for o in range(-limit, limit + 1) if o]
    common = [o for o in values if abs(o) <= 5]
    return values + common * 4


def until_after(rng: Random, spec: Spec, dtstart: datetime, limit: int) -> datetime:
    """An UNTIL some way into the expansion; UTC when DTSTART is aware."""
    span = STEP[spec.freq] * (spec.interval or 1) * rng.uniform(0.5, max(1.0, limit * 1.2))
    if dtstart.tzinfo is None:
        return (dtstart + span).replace(microsecond=0)
    return (dtstart.astimezone(UTC) + span).replace(microsecond=0)


def bound(rng: Random, spec: Spec, dtstart: datetime, limit: int) -> Spec:
    """Add COUNT, UNTIL, or neither to a core rule."""
    kind = rng.randrange(3)
    if kind == 0:
        return replace(spec, count=rng.randint(1, limit))
    if kind == 1:
        return replace(spec, until=until_after(rng, spec, dtstart, limit))
    return spec


def maybe_utc(rng: Random, value: datetime, share: float) -> datetime:
    """The same wall time as UTC with probability ``share``, otherwise floating."""
    return value.replace(tzinfo=UTC) if rng.random() < share else value
