"""K1: BYMONTHDAY values, positive, negative, and out of range, under every FREQ that allows them.

WEEKLY is excluded because RFC 5545 forbids BYMONTHDAY with it. Each FREQ is drawn with and
without BYMONTH in turn. Roughly a fifth of drafts carry a zero or out-of-range value, which the
reference rejects, so the expected outcome there is ``ValueError``.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from random import Random
from typing import Final

from gen import draw
from gen.accept import Builder
from gen.spec import Case, Spec
from refload import Reference

SEED: Final = 0x5545_0001
FREQS: Final = ("YEARLY", "MONTHLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY")
LIMITS: Final = {"YEARLY": 24, "MONTHLY": 30, "DAILY": 30, "HOURLY": 30, "MINUTELY": 20, "SECONDLY": 20}
VALID: Final = tuple(d for d in range(-31, 32) if d)
INVALID: Final = (0, 32, 33, 40, 99, -32, -33, -40, -99)
ERROR_SHARE: Final = 0.2


def _interval(rng: Random, freq: str) -> int | None:
    if freq in ("YEARLY", "MONTHLY", "DAILY"):
        return rng.choice((None, None, 1, 2, 3))
    return rng.choice((None, None, None, 2))


def _anchor(rng: Random, days: tuple[int, ...], months: tuple[int, ...]) -> datetime | None:
    """A wall time on a day the rule names, so the first instance is near."""
    base = draw.anchor(rng)
    month = rng.choice(months) if months else base.month
    found = draw.month_day(base.year, month, days[0])
    if found is None:
        return None
    return datetime.combine(found, base.time())


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K1 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K1", rng, exclude)
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        freq = FREQS[attempt % len(FREQS)]
        months = draw.pick(rng, range(1, 13), 1, 3) if (attempt // len(FREQS)) % 2 == 0 else ()
        days = draw.pick(rng, VALID, 1, 3)
        core = Spec(freq, interval=_interval(rng, freq), bymonth=tuple(sorted(months)), bymonthday=days)
        limit = LIMITS[freq]
        if rng.random() < ERROR_SHARE:
            spot = rng.randrange(len(days))
            bad = days[:spot] + (rng.choice(INVALID),) + days[spot + 1 :]
            start = draw.anchor(rng)
            spec = draw.bound(rng, replace(core, bymonthday=bad), start, limit)
            builder.add_error(spec, start if spec.until is not None else draw.maybe_utc(rng, start, 0.2), limit)
            continue
        start = _anchor(rng, days, core.bymonth)
        if start is None:
            continue
        dtstart = builder.first_instance(core, draw.maybe_utc(rng, start, 0.2))
        if dtstart is not None:
            builder.add_valid(draw.bound(rng, core, dtstart, limit), dtstart, limit)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K1", len(builder.cases), wanted)
    return builder.cases[:wanted]
