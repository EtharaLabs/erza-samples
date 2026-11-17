"""K6: ordinary rules whose behaviour a repair must preserve.

Every FREQ, INTERVAL above one, COUNT and UNTIL, naive and aware DTSTART in zones without
daylight saving, with plain BYDAY only below MONTHLY, BYMONTH, BYYEARDAY, and time-of-day lists.
The K1 to K5 families (BYMONTHDAY lists, BYDAY under MONTHLY or YEARLY, BYWEEKNO, BYSETPOS,
daylight-saving transitions) are excluded, except for these named families: WEEKLY BYSETPOS from
a partial first week, YEARLY rules whose only BYxxx is BYMONTHDAY, INTERVAL rejection, and
BYWEEKNO 52 and 53 with one weekday.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from random import Random
from typing import Final
from zoneinfo import ZoneInfo

from gen import draw
from gen.accept import Builder
from gen.spec import DAYS, Case, Spec
from refload import Reference

SEED: Final = 0x5545_0006
FREQS: Final = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY")
LIMITS: Final = {"YEARLY": 20, "MONTHLY": 24, "WEEKLY": 24, "DAILY": 30, "HOURLY": 30, "MINUTELY": 25, "SECONDLY": 25}
FAMILIES: Final = ("ordinary",) * 14 + ("weekly-setpos", "weekly-setpos", "yearly-monthday", "interval-zero", "weekno-edge")
STEADY_ZONES: Final = ("Asia/Tokyo", "Asia/Kolkata", "UTC")


def _start(rng: Random) -> datetime:
    wall = draw.anchor(rng)
    match rng.randrange(3):
        case 0:
            return wall
        case 1:
            return draw.maybe_utc(rng, wall, 1.0)
        case _:
            return wall.replace(tzinfo=ZoneInfo(rng.choice(STEADY_ZONES)))


def _ordinary(rng: Random) -> Spec:
    freq = rng.choice(FREQS)
    sub_daily = freq in ("HOURLY", "MINUTELY", "SECONDLY")
    spec = Spec(freq, interval=rng.choice((None, 1, 2, 2, 3, 4, 7)))
    if rng.random() < 0.3:
        spec = replace(spec, bymonth=tuple(sorted(draw.pick(rng, range(1, 13), 1, 6))))
    if freq not in ("MONTHLY", "YEARLY") and rng.random() < 0.4:
        spec = replace(spec, byday=draw.plain_days(rng, 1, 5))
    if freq == "YEARLY" and rng.random() < 0.25:
        spec = replace(spec, byyearday=tuple(sorted(draw.pick(rng, range(1, 366), 1, 3))))
    if freq in ("YEARLY", "MONTHLY", "WEEKLY", "DAILY") and rng.random() < 0.3:
        spec = replace(spec, byhour=tuple(sorted(draw.pick(rng, range(24), 1, 3))))
    if not sub_daily and rng.random() < 0.2:
        spec = replace(spec, byminute=tuple(sorted(draw.pick(rng, range(0, 60, 5), 1, 2))))
    if freq == "SECONDLY" or (freq == "MINUTELY" and rng.random() < 0.3):
        spec = replace(spec, bysecond=tuple(sorted(draw.pick(rng, range(0, 60, 10), 1, 3))))
    return spec


def _weekly_setpos(rng: Random) -> tuple[Spec, datetime]:
    spec = Spec("WEEKLY", byday=draw.plain_days(rng, 2, 4), bysetpos=draw.pick(rng, (1, 2, 3, -1, -2, -3), 1, 2))
    wall = draw.anchor(rng)
    middle = wall + timedelta(days=(rng.randint(2, 5) - wall.weekday()) % 7)
    return replace(spec, wkst=rng.choice((None, "MO", "SU"))), middle


def _yearly_monthday(rng: Random) -> Spec:
    return Spec("YEARLY", interval=rng.choice((None, 1, 2)), bymonthday=draw.pick(rng, range(1, 29), 1, 2))


def _weekno_edge(rng: Random) -> Spec:
    return Spec("YEARLY", byweekno=(rng.choice((52, 53)),), byday=((None, rng.choice(DAYS)),))


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K6 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K6", rng, exclude)
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        family = FAMILIES[attempt % len(FAMILIES)]
        start = _start(rng)
        match family:
            case "interval-zero":
                spec = Spec(rng.choice(FREQS[:4]), interval=rng.choice((0, 0, -1, -2)))
                builder.add_error(spec, start, 10)
                continue
            case "weekly-setpos":
                core, wall = _weekly_setpos(rng)
                start = wall.replace(tzinfo=start.tzinfo)
            case "yearly-monthday":
                core = _yearly_monthday(rng)
            case "weekno-edge":
                core = _weekno_edge(rng)
            case _:
                core = _ordinary(rng)
        limit = LIMITS[core.freq]
        dtstart = builder.first_instance(core, start)
        if dtstart is not None:
            builder.add_valid(draw.bound(rng, core, dtstart, limit), dtstart, limit)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K6", len(builder.cases), wanted)
    return builder.cases[:wanted]
