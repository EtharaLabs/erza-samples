"""K4: BYSETPOS, positive and negative, over intervals with one or several times of day.

Several times of day come from BYHOUR and BYMINUTE lists. BYDAY lists include plain, ordinal,
and mixed plain and ordinal forms under MONTHLY and YEARLY, and plain lists under WEEKLY and
DAILY, where ordinals are not allowed. Set positions are drawn within an estimate of the
interval's set size, so most drafts select something in most intervals. A draft with a
position beyond some interval's set is refused (``setpos-beyond-set`` is always excluded).
"""

from __future__ import annotations

from random import Random
from typing import Final

from gen import draw
from gen.accept import Builder
from gen.spec import Case, DayNum, Spec
from refload import Reference

SEED: Final = 0x5545_0004
FREQS: Final = ("MONTHLY", "MONTHLY", "YEARLY", "WEEKLY", "DAILY")
LIMIT: Final = 30
POSITIONS: Final = (1, 2, 3, 4, 5, 7, 10, 20, 40)


def _byday(rng: Random, freq: str, months: tuple[int, ...]) -> tuple[DayNum, ...]:
    if freq in ("WEEKLY", "DAILY"):
        return draw.plain_days(rng, 2, 5)
    ordinals = draw.small_ordinals(4 if freq == "MONTHLY" or months else 52)
    match rng.randrange(3):
        case 0:
            return draw.plain_days(rng, 1, 3)
        case 1:
            return draw.ordinal_days(rng, ordinals, 2, 3)
        case _:
            merged = list(draw.plain_days(rng, 1, 2) + draw.ordinal_days(rng, ordinals, 1, 2))
            rng.shuffle(merged)
            return tuple(merged)


def _times(rng: Random, several: bool) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if not several:
        return (), ()
    hours = tuple(sorted(draw.pick(rng, range(24), 1, 3))) if rng.random() < 0.8 else ()
    minutes = tuple(sorted(draw.pick(rng, (0, 10, 15, 20, 30, 45, 50), 1, 3))) if rng.random() < 0.6 or not hours else ()
    if max(1, len(hours)) * max(1, len(minutes)) < 2:
        minutes = (0, 30)
    return hours, minutes


def set_size(spec: Spec) -> int:
    """A lower-end estimate of how many instances one interval holds before BYSETPOS."""
    times = max(1, len(spec.byhour)) * max(1, len(spec.byminute))
    plain = sum(1 for ordinal, _ in spec.byday if ordinal is None)
    numbered = len(spec.byday) - plain
    match spec.freq:
        case "MONTHLY":
            days = plain * 4 + numbered
        case "YEARLY":
            days = plain * (4 * len(spec.bymonth) if spec.bymonth else 52) + numbered
        case "WEEKLY":
            days = len(spec.byday)
        case _:
            days = 1
    return days * times


def _positions(rng: Random, size: int) -> tuple[int, ...]:
    pool = [sign * p for p in POSITIONS if p <= size for sign in (1, -1)]
    return draw.pick(rng, pool, 1, min(3, len(pool)))


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K4 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K4", rng, exclude)
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        freq = FREQS[attempt % len(FREQS)]
        hours, minutes = _times(rng, several=(attempt // len(FREQS)) % 2 == 1)
        months = tuple(sorted(draw.pick(rng, range(1, 13), 1, 3))) if freq == "YEARLY" and rng.random() < 0.5 else ()
        base = Spec(freq, interval=rng.choice((None, None, 1, 2)), bymonth=months, byday=_byday(rng, freq, months), byhour=hours, byminute=minutes)
        core = Spec(base.freq, interval=base.interval, bysetpos=_positions(rng, set_size(base)), bymonth=months, byday=base.byday, byhour=hours, byminute=minutes)
        dtstart = builder.first_instance(core, draw.maybe_utc(rng, draw.anchor(rng), 0.15))
        if dtstart is not None:
            builder.add_valid(draw.bound(rng, core, dtstart, LIMIT), dtstart, LIMIT)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K4", len(builder.cases), wanted)
    return builder.cases[:wanted]
