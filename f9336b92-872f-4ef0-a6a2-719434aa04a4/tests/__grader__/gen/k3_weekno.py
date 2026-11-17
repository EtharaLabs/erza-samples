"""K3: BYWEEKNO, positive and negative, under each WKST, across all 14 calendar-year types.

A calendar-year type is the weekday of 1 January together with leap or common. Drafts cycle the
14 types and, within them, the seven WKST values; DTSTART lies near the start of a year of the
drawn type and the expansion runs into the following year, so each case spans a consecutive
year pair. Boundary week numbers (1, 52, 53 and their negatives) are drawn most often; a draft
with a negative week number is refused (``weekno-negative`` is always excluded), so the cases
carry positive week numbers only.

Every rule carries a plain BYDAY list: with BYWEEKNO alone, the reference derives the weekday
from DTSTART while dateutil's own shipped tests expect the whole week, and K3 grades week
numbering, not that reading.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from random import Random
from typing import Final

from gen import draw
from gen.accept import Builder
from gen.spec import DAYS, Case, Spec
from refload import Reference

SEED: Final = 0x5545_0003
BOUNDARY: Final = (1, 2, 52, 53, -1, -2, -52, -53)
ANY_WEEK: Final = tuple(w for w in range(-53, 54) if w)
LIMIT: Final = 40


def year_types(first: int = 1971, last: int = 2070) -> list[list[int]]:
    """Years of each of the 14 types, in a fixed type order (weekday, then leap)."""
    table: list[list[int]] = [[] for _ in range(14)]
    for year in range(first, last + 1):
        table[date(year, 1, 1).weekday() * 2 + int(calendar.isleap(year))].append(year)
    return table


TYPES: Final = year_types()


def _weeks(rng: Random) -> tuple[int, ...]:
    first = rng.choice(BOUNDARY) if rng.random() < 0.7 else rng.choice(ANY_WEEK)
    if rng.random() < 0.6:
        return (first,)
    second = rng.choice(ANY_WEEK)
    return (first,) if second == first else (first, second)


def _until(rng: Random, year: int, dtstart: datetime) -> datetime:
    """The last second of the following year, in DTSTART's form."""
    end = datetime(year + 1, 12, 31, 23, 59, 59)
    return end.replace(tzinfo=dtstart.tzinfo) if dtstart.tzinfo is not None else end


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K3 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K3", rng, exclude)
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        year = rng.choice(TYPES[attempt % 14])
        wkst = DAYS[(attempt // 14) % 7]
        byday = draw.plain_days(rng, 1, 3)
        core = Spec("YEARLY", wkst=wkst, byweekno=_weeks(rng), byday=byday)
        hour, minute, second = draw.wall_time(rng)
        start = draw.maybe_utc(rng, datetime(year, 1, 1, hour, minute, second), 0.15)
        dtstart = builder.first_instance(core, start)
        if dtstart is None or dtstart.year > year + 1:
            continue
        match rng.randrange(3):
            case 0:
                spec = Spec(core.freq, wkst=wkst, byweekno=core.byweekno, byday=byday, until=_until(rng, year, dtstart))
            case 1:
                spec = Spec(core.freq, wkst=wkst, byweekno=core.byweekno, byday=byday, count=rng.randint(1, LIMIT))
            case _:
                spec = core
        builder.add_valid(spec, dtstart, LIMIT)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K3", len(builder.cases), wanted)
    return builder.cases[:wanted]
