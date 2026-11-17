"""Expected results, recomputed from the reference expander at grading time and never stored.

For each probe the case asked for, the reference decides: the instance list, ``ValueError``
when the reference rejects the rule, the ``count()`` value, the ``between()`` window, and the
``after()``/``before()`` neighbours. Probes are only attached by the generator where the
reference decides them under ``PROBE_CAP``; a probe that reaches the cap here is a harness fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from gen.spec import parse_bound, parse_dtstart
from refload import Reference, Rule
from score.outputs import Failed, Listing, Number, Point, Result

PROBE_CAP: Final = 1000
REJECTED: Final = Failed("ValueError")


class ProbeUndecidedError(RuntimeError):
    """The reference could not decide a probe within ``PROBE_CAP`` instances."""

    def __init__(self, case_id: str, probe: str) -> None:
        super().__init__(f"{case_id}: {probe} reached the probe cap")
        self.case_id: Final = case_id


@dataclass(frozen=True, slots=True)
class CaseInput:
    """The fields of a case line the scorer reads."""

    id: str
    rule: str
    dtstart: str
    limit: int
    kw: bool
    count: bool
    window: tuple[str, str, bool] | None
    after: tuple[str, bool] | None
    before: tuple[str, bool] | None


def instance_text(value: datetime) -> str:
    """The grammar the child writes: ISO 8601 with the offset when aware, ``#``, the fold."""
    return f"{value.isoformat()}#{value.fold}"


def _key(value: datetime) -> datetime:
    return value if value.tzinfo is None else value.astimezone(UTC)


def _expand(ref: Reference, case: CaseInput, rule: Rule, dtstart: datetime, probe: str, cap: datetime | None = None) -> list[datetime]:
    found = ref.expand(rule, dtstart, limit=PROBE_CAP, until_cap=cap)
    if len(found) >= PROBE_CAP:
        raise ProbeUndecidedError(case.id, probe)
    return found


def _first_after(found: list[datetime], pivot: datetime, inc: bool) -> datetime | None:
    edge = _key(pivot)
    return next((x for x in found if _key(x) > edge or (inc and _key(x) == edge)), None)


def expected(ref: Reference, case: CaseInput) -> dict[str, Result | None]:
    """The reference's answer for every probe the case carries."""
    dtstart = parse_dtstart(case.dtstart)
    out: dict[str, Result | None] = dict.fromkeys(("rule", "kw", "count", "between", "after", "before"))
    try:
        rule = ref.parse_rrule(case.rule)
        ref.validate(rule, dtstart)
    except ref.invalid:
        out["rule"] = REJECTED
        out["kw"] = REJECTED if case.kw else None
        return out
    listing = Listing(tuple(instance_text(x) for x in ref.expand(rule, dtstart, limit=case.limit)))
    out["rule"] = listing
    out["kw"] = listing if case.kw else None
    if case.count and rule.count is not None:
        out["count"] = Number(len(ref.expand(rule, dtstart, limit=rule.count)))
    if case.window is not None:
        start, end, inc = parse_bound(case.window[0]), parse_bound(case.window[1]), case.window[2]
        low, high = _key(start), _key(end)
        inside = [
            x for x in _expand(ref, case, rule, dtstart, "between", end)
            if ((low <= _key(x) <= high) if inc else (low < _key(x) < high))
        ]
        out["between"] = Listing(tuple(instance_text(x) for x in inside))
    if case.after is not None:
        pivot = parse_bound(case.after[0])
        found = ref.expand(rule, dtstart, limit=PROBE_CAP)
        hit = _first_after(found, pivot, case.after[1])
        if hit is None and len(found) >= PROBE_CAP:
            raise ProbeUndecidedError(case.id, "after")
        out["after"] = Point(None if hit is None else instance_text(hit))
    if case.before is not None:
        pivot, inc = parse_bound(case.before[0]), case.before[1]
        edge = _key(pivot)
        below = [x for x in _expand(ref, case, rule, dtstart, "before", pivot) if _key(x) < edge or (inc and _key(x) == edge)]
        out["before"] = Point(instance_text(below[-1]) if below else None)
    return out
