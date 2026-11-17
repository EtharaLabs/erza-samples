"""Turn drafted rules into cases the reference accepts, with deterministic API probes.

A valid case is one the reference parses and validates and whose DTSTART is synchronized with
the rule. An error case is one the reference rejects as ``InvalidRule``; only categories that
grade rejection admit those. Probes (keyword call, ``count()``, ``between()``, ``after()``,
``before()``) are attached only where the reference can decide them within ``PROBE_CAP``
instances. Nothing here records an expected result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Final

from gen.contested import ALWAYS_EXCLUDED, checked, classify, dtstart_in_gap
from gen.spec import Case, Probe, Spec, format_bound, format_dtstart, rule_kwargs, rule_text
from refload import Reference, Rule

PROBE_CAP: Final = 1000
COUNT_PROBE_MAX: Final = 200
STEP_SECONDS: Final = {
    "YEARLY": 366 * 86400,
    "MONTHLY": 31 * 86400,
    "WEEKLY": 7 * 86400,
    "DAILY": 86400,
    "HOURLY": 3600,
    "MINUTELY": 60,
    "SECONDLY": 1,
}


@dataclass(frozen=True, slots=True)
class Rates:
    """How often each optional probe is attached to a valid case."""

    kw: float = 0.35
    count: float = 0.5
    window: float = 0.25
    after: float = 0.25
    before: float = 0.25


class Builder:
    """Accepts drafts for one category and numbers the resulting cases."""

    def __init__(self, ref: Reference, category: str, rng: Random, exclude: frozenset[str] = frozenset()) -> None:
        self._ref = ref
        self._category = category
        self._rng = rng
        self._rates = Rates()
        self._exclude = checked(exclude) | ALWAYS_EXCLUDED
        self.cases: list[Case] = []

    def _excluded(self, spec: Spec, dtstart: datetime, limit: int) -> bool:
        """Whether the draft falls in an excluded family.

        The ``ALWAYS_EXCLUDED`` families are refused in every generation (operator ruling), so
        every draft is classified; ``dtstart-in-gap`` is checked first because it is cheap.
        """
        if dtstart_in_gap(dtstart):
            return True
        return bool(classify(self._ref, spec, dtstart, limit) & self._exclude)

    def _parse(self, spec: Spec) -> Rule | None:
        try:
            return self._ref.parse_rrule(rule_text(spec))
        except self._ref.invalid:
            return None

    def first_instance(self, core: Spec, anchor: datetime) -> datetime | None:
        """The first instance at or after ``anchor``, if the rule is synchronized there."""
        rule = self._parse(core)
        if rule is None:
            return None
        try:
            found = self._ref.expand(rule, anchor, limit=1)
            if not found or not self._ref.synchronized(rule, found[0]):
                return None
        except self._ref.invalid:
            return None
        return found[0]

    def _next_id(self) -> str:
        return f"{self._category}-{len(self.cases) + 1:05d}"

    def add_error(self, spec: Spec, dtstart: datetime, limit: int) -> bool:
        """Add a case the reference must reject; refuse a draft it accepts."""
        try:
            rule = self._ref.parse_rrule(rule_text(spec))
            self._ref.validate(rule, dtstart)
        except self._ref.invalid:
            if self._excluded(spec, dtstart, limit):
                return False
            kw = rule_kwargs(spec) if self._rng.random() < 0.5 else None
            case = Case(self._next_id(), rule_text(spec), format_dtstart(dtstart), limit, kw, False, None, None, None)
            self.cases.append(case)
            return True
        return False

    def add_valid(self, spec: Spec, dtstart: datetime, limit: int) -> bool:
        """Add a synchronized, reference-valid case with its probes; refuse anything else."""
        rule = self._parse(spec)
        if rule is None:
            return False
        try:
            if not self._ref.synchronized(rule, dtstart) or not self._ref.expand(rule, dtstart, limit=limit):
                return False
            if self._excluded(spec, dtstart, limit):
                return False
            probes = self._probes(spec, rule, dtstart, limit)
        except self._ref.invalid:
            return False
        rates, roll = self._rates, self._rng.random
        kw = rule_kwargs(spec) if roll() < rates.kw else None
        count = spec.count is not None and spec.count <= COUNT_PROBE_MAX and roll() < rates.count
        window, after, before = probes
        case = Case(self._next_id(), rule_text(spec), format_dtstart(dtstart), limit, kw, count, window, after, before)
        self.cases.append(case)
        return True

    def _span(self, spec: Spec, low: float, high: float) -> timedelta:
        step = STEP_SECONDS[spec.freq] * (spec.interval or 1)
        return timedelta(seconds=int(step * self._rng.uniform(low, high)))

    def _pivot(self, spec: Spec, dtstart: datetime, limit: int) -> datetime:
        return _naive_or_utc(dtstart) + self._span(spec, 0.0, float(limit))

    def _probes(self, spec: Spec, rule: Rule, dtstart: datetime, limit: int) -> tuple[Probe | None, ...]:
        rates, roll = self._rates, self._rng.random
        window = after = before = None
        if roll() < rates.window:
            start = self._pivot(spec, dtstart, limit)
            end = start + self._span(spec, 1.0, max(2.0, limit / 2)) + timedelta(seconds=1)
            inside = self._ref.expand(rule, dtstart, limit=PROBE_CAP, until_cap=end)
            if len(inside) < PROBE_CAP:
                window = Probe(format_bound(start), roll() < 0.5, format_bound(end))
        if roll() < rates.after:
            pivot = self._pivot(spec, dtstart, limit)
            seen = self._ref.expand(rule, dtstart, limit=PROBE_CAP)
            if len(seen) < PROBE_CAP or any(_key(x) > _key(pivot) for x in seen):
                after = Probe(format_bound(pivot), roll() < 0.5)
        if roll() < rates.before:
            pivot = self._pivot(spec, dtstart, limit)
            if len(self._ref.expand(rule, dtstart, limit=PROBE_CAP, until_cap=pivot)) < PROBE_CAP:
                before = Probe(format_bound(pivot), roll() < 0.5)
        return window, after, before


def _naive_or_utc(value: datetime) -> datetime:
    return value if value.tzinfo is None else value.astimezone(UTC)


def _key(value: datetime) -> datetime:
    """Ordering by instant for aware values and by wall time for naive ones."""
    return _naive_or_utc(value)
