"""K5: zoned DTSTART across spring-forward and fall-back days.

Zones are America/New_York, Europe/London, and Australia/Sydney. Kinds cycle: DAILY, WEEKLY,
and MONTHLY expansions whose wall time falls in the gap or repeated span on a transition day;
HOURLY expansions across the transition; DTSTART inside the repeated span (a DTSTART inside a gap is excluded by operator ruling); DAILY with
BYHOUR lists around the transition hour; and DAILY, WEEKLY, and MONTHLY at a daytime wall
time far from the transition, whose instances only change offset across it. Bounds are COUNT, or an UNTIL in UTC placed exactly at,
one second before, or one second after an instant on the transition day. A sub-daily draft
that steps across fall-back is refused (``subdaily-fallback`` is always excluded).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from random import Random
from typing import Final
from zoneinfo import ZoneInfo

from gen import draw
from gen.accept import Builder
from gen.spec import Case, Spec
from gen.transitions import Transition, transitions
from refload import Reference

SEED: Final = 0x5545_0005
ZONES: Final = ("America/New_York", "Europe/London", "Australia/Sydney")
KINDS: Final = ("daily", "weekly", "monthly", "hourly", "start-in-span", "byhour", "clear")
NUDGES: Final = (timedelta(0), timedelta(seconds=-1), timedelta(seconds=1))


def _span_time(rng: Random, change: Transition) -> time:
    start, end = change.odd_span()
    minutes = int((end - start).total_seconds() // 60)
    return (start + timedelta(minutes=rng.randrange(minutes))).time().replace(second=0)


def _zoned(wall: datetime, zone: ZoneInfo) -> datetime:
    return wall.replace(tzinfo=zone, fold=0)


def _draft(rng: Random, kind: str, change: Transition) -> tuple[Spec, datetime, int] | None:
    zone, day = change.zone, change.day
    match kind:
        case "daily":
            when = _span_time(rng, change)
            return Spec("DAILY"), _zoned(datetime.combine(day - timedelta(days=rng.randint(1, 10)), when), zone), 20
        case "weekly":
            when = _span_time(rng, change)
            return Spec("WEEKLY"), _zoned(datetime.combine(day - timedelta(weeks=rng.randint(1, 4)), when), zone), 12
        case "monthly":
            back = rng.randint(1, 3)
            month = (day.month - back - 1) % 12 + 1
            year = day.year - (1 if month > day.month else 0)
            start = draw.month_day(year, month, day.day)
            if start is None:
                return None
            return Spec("MONTHLY"), _zoned(datetime.combine(start, _span_time(rng, change)), zone), 8
        case "hourly":
            local = (change.instant - timedelta(hours=rng.randint(1, 8))).astimezone(zone)
            wall = local.replace(tzinfo=None, minute=rng.choice((0, 0, 30)), second=0)
            return Spec("HOURLY", interval=rng.choice((None, None, 2))), _zoned(wall, zone), 24
        case "start-in-span":
            freq = rng.choice(("DAILY", "HOURLY", "WEEKLY", "MONTHLY"))
            return Spec(freq), _zoned(datetime.combine(day, _span_time(rng, change)), zone), 20
        case "byhour":
            hour = change.odd_span()[0].hour
            hours = tuple(h for h in (hour - 1, hour, hour + 1) if 0 <= h <= 23)
            minutes = rng.choice(((0,), (0, 30), (15, 45)))
            wall = datetime.combine(day - timedelta(days=rng.randint(1, 5)), time(hours[0], minutes[0]))
            return Spec("DAILY", byhour=hours, byminute=minutes), _zoned(wall, zone), 30
        case "clear":
            freq = rng.choice(("DAILY", "WEEKLY", "MONTHLY"))
            when = time(rng.randint(8, 20), rng.choice((0, 15, 30, 45)))
            back = {"DAILY": timedelta(days=rng.randint(1, 10)), "WEEKLY": timedelta(weeks=rng.randint(1, 4))}
            start = day - back[freq] if freq in back else draw.month_day(day.year - (day.month == 1), (day.month - 2) % 12 + 1, day.day)
            if start is None:
                return None
            return Spec(freq), _zoned(datetime.combine(start, when), zone), 12
        case _:
            return None


def _bound(rng: Random, spec: Spec, dtstart: datetime, change: Transition, limit: int) -> Spec:
    match rng.randrange(4):
        case 0:
            return replace(spec, count=rng.randint(1, limit))
        case 1:
            return replace(spec, until=change.instant.astimezone(UTC) + rng.choice(NUDGES))
        case 2:
            local = _zoned(datetime.combine(change.day, dtstart.time()), change.zone)
            return replace(spec, until=local.astimezone(UTC) + rng.choice(NUDGES))
        case _:
            return spec


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K5 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K5", rng, exclude)
    changes = [t for name in ZONES for t in transitions(ZoneInfo(name), 2005, 2030)]
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        change = changes[attempt % len(changes)]
        drafted = _draft(rng, KINDS[(attempt // len(changes)) % len(KINDS)], change)
        if drafted is None:
            continue
        core, dtstart, limit = drafted
        builder.add_valid(_bound(rng, core, dtstart, change, limit), dtstart, limit)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K5", len(builder.cases), wanted)
    return builder.cases[:wanted]
