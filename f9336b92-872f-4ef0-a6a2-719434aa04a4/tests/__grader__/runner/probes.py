"""The dateutil calls one case makes, each under its own step budget.

Every probe returns a JSON-ready mapping: ``{"instances": [...]}``, ``{"value": n}``,
``{"instance": text-or-null}``, or ``{"error": name}``. The submitted library is reached only
through its public API: ``rrulestr``, ``rrule``, and the ``count``/``between``/``after``/
``before`` methods.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from typing import Final, Protocol

from budget import Budget, StepBudgetExceeded
from wire import error_name, instance_text

type Out = dict[str, str | int | list[str] | None]
BETWEEN_CAP: Final = 1000


class RuleLike(Protocol):
    def __iter__(self) -> Iterator[datetime]: ...
    def count(self) -> int: ...
    def between(self, after: datetime, before: datetime, inc: bool = False) -> list[datetime]: ...
    def after(self, dt: datetime, inc: bool = False) -> datetime | None: ...
    def before(self, dt: datetime, inc: bool = False) -> datetime | None: ...


@dataclass(frozen=True, slots=True)
class Pivot:
    at: datetime
    inc: bool


@dataclass(frozen=True, slots=True)
class Window:
    start: datetime
    end: datetime
    inc: bool


@dataclass(frozen=True, slots=True)
class CaseIn:
    """One case as the child reads it; ``build`` and ``build_kw`` construct the rule."""

    id: str
    limit: int
    build: Callable[[], RuleLike]
    build_kw: Callable[[], RuleLike] | None
    count: bool
    window: Window | None
    after: Pivot | None
    before: Pivot | None


class NotADatetimeError(TypeError):
    """The library returned something other than a ``datetime`` where one was required."""


def _texts(values: Iterator[datetime] | list[datetime], cap: int) -> list[str]:
    out: list[str] = []
    for value in values:
        if not isinstance(value, datetime):
            raise NotADatetimeError
        out.append(instance_text(value))
        if len(out) > cap:
            break
    return out


def _guard(budget: Budget, probe: Callable[[], Out]) -> Out:
    try:
        return budget.run(probe)
    except StepBudgetExceeded:
        return {"error": "budget"}
    except Exception as error:  # noqa: BLE001 - code under test may raise anything; it is recorded
        return {"error": error_name(error)}


def _listing(make: Callable[[], RuleLike], limit: int) -> Callable[[], Out]:
    return lambda: {"instances": _texts(islice(iter(make()), limit), limit)}


def _pivot(make: Callable[[], RuleLike], name: str, pivot: Pivot) -> Callable[[], Out]:
    def probe() -> Out:
        rule = make()
        found = rule.after(pivot.at, inc=pivot.inc) if name == "after" else rule.before(pivot.at, inc=pivot.inc)
        if found is None:
            return {"instance": None}
        if not isinstance(found, datetime):
            raise NotADatetimeError
        return {"instance": instance_text(found)}

    return probe


def run_case(budget: Budget, case: CaseIn) -> dict[str, str | Out | None]:
    """All probes of one case, in a fixed order."""
    out: dict[str, str | Out | None] = {"id": case.id, "rule": _guard(budget, _listing(case.build, case.limit))}
    out["kw"] = None if case.build_kw is None else _guard(budget, _listing(case.build_kw, case.limit))
    out["count"] = _guard(budget, lambda: {"value": int(case.build().count())}) if case.count else None
    window = case.window
    out["between"] = None
    if window is not None:
        out["between"] = _guard(
            budget,
            lambda: {"instances": _texts(case.build().between(window.start, window.end, inc=window.inc), BETWEEN_CAP)},
        )
    out["after"] = None if case.after is None else _guard(budget, _pivot(case.build, "after", case.after))
    out["before"] = None if case.before is None else _guard(budget, _pivot(case.build, "before", case.before))
    return out
