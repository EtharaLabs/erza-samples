"""K2: BYDAY lists under MONTHLY and YEARLY.

Shapes cycle through plain weekdays, ordinal weekdays, mixed plain and ordinal lists, and YEARLY
rules whose only BYxxx part is an ordinal BYDAY. The first three shapes are crossed with no
filter, BYMONTH, BYMONTHDAY, and both.
"""

from __future__ import annotations

from random import Random
from typing import Final

from gen import draw
from gen.accept import Builder
from gen.spec import Case, DayNum, Spec
from refload import Reference

SEED: Final = 0x5545_0002
SHAPES: Final = ("plain", "ordinal", "mixed", "yearly-ordinal-only")
FILTERS: Final = ("none", "bymonth", "bymonthday", "both")
LIMITS: Final = {"MONTHLY": 30, "YEARLY": 25}
MONTHLY_ORDINALS: Final = draw.small_ordinals(5)
YEARLY_ORDINALS: Final = draw.small_ordinals(53)


def _byday(rng: Random, shape: str, ordinals: list[int]) -> tuple[DayNum, ...]:
    if shape == "plain":
        return draw.plain_days(rng, 1, 3)
    if shape == "mixed":
        plain = draw.plain_days(rng, 1, 2)
        numbered = draw.ordinal_days(rng, ordinals, 1, 2)
        merged = list(plain + numbered)
        rng.shuffle(merged)
        return tuple(merged)
    return draw.ordinal_days(rng, ordinals, 1, 3)


def _core(rng: Random, attempt: int) -> Spec:
    shape = SHAPES[attempt % len(SHAPES)]
    if shape == "yearly-ordinal-only":
        return Spec("YEARLY", interval=rng.choice((None, None, 2)), byday=_byday(rng, shape, YEARLY_ORDINALS))
    freq = ("MONTHLY", "YEARLY")[(attempt // len(SHAPES)) % 2]
    selector = FILTERS[(attempt // (2 * len(SHAPES))) % len(FILTERS)]
    months = tuple(sorted(draw.pick(rng, range(1, 13), 1, 4))) if selector in ("bymonth", "both") else ()
    days = draw.pick(rng, [d for d in range(-31, 32) if d], 1, 4) if selector in ("bymonthday", "both") else ()
    interval = rng.choice((None, None, 1, 2, 3))
    return Spec(freq, interval=interval, bymonth=months, bymonthday=days, byday=_byday(rng, shape, YEARLY_ORDINALS if freq == "YEARLY" and not months else MONTHLY_ORDINALS))


def generate(ref: Reference, wanted: int, exclude: frozenset[str] = frozenset()) -> list[Case]:
    """``wanted`` K2 cases, deterministic for ``SEED``."""
    rng = Random(SEED)
    builder = Builder(ref, "K2", rng, exclude)
    for attempt in range(draw.attempts_ceiling(wanted)):
        if len(builder.cases) >= wanted:
            break
        core = _core(rng, attempt)
        limit = LIMITS[core.freq]
        dtstart = builder.first_instance(core, draw.maybe_utc(rng, draw.anchor(rng), 0.15))
        if dtstart is not None:
            builder.add_valid(draw.bound(rng, core, dtstart, limit), dtstart, limit)
    if len(builder.cases) < wanted:
        raise draw.GenerationExhaustedError("K2", len(builder.cases), wanted)
    return builder.cases[:wanted]
