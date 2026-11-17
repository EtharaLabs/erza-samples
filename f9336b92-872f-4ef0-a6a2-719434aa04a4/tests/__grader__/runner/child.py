"""Expand every case through the SUBMITTED dateutil and write one JSON line per case to fd 3.

Usage (as the sandbox uid, scrubbed environment, ``PYTHONHASHSEED=0``)::

    python3 -I -B /opt/runner/child.py <library root> [<steps per probe> [<steps per category>]] < cases.jsonl 3> out.jsonl

``<library root>`` holds only the ``dateutil`` package and goes first on ``sys.path``. The
runner's own modules are imported before it is added, so nothing the submission ships can
shadow them. This process never imports the reference expander or any grader code.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from budget import CATEGORY_BUDGET, STEP_BUDGET, Budget, StepBudgetExceeded  # noqa: E402 - runner modules load before the library path
from origin import require_root  # noqa: E402
from probes import CaseIn, Pivot, RuleLike, Window, run_case  # noqa: E402
from wire import error_name, parse_bound, parse_dtstart  # noqa: E402

sys.path.pop(0)
OUT_FD: Final = 3
MAX_LINE: Final = 256 * 1024


def _kw_builder(module: ModuleType, kw: dict[str, str | int | list[int] | list[list[str | int | None]]], dtstart: datetime) -> Callable[[], RuleLike]:
    def build() -> RuleLike:
        args: dict[str, object] = {"dtstart": dtstart}
        for key, value in kw.items():
            match key, value:
                case ("freq" | "wkst"), str(name):
                    args[key] = getattr(module, name)
                case "until", str(text):
                    args[key] = parse_bound(text)
                case ("interval" | "count"), int(number):
                    args[key] = number
                case "byweekday", list(days):
                    args[key] = tuple(_weekday(module, day) for day in days)
                case _, list(numbers):
                    args[key] = tuple(numbers)
                case _:
                    raise TypeError(key)
        freq = args.pop("freq")
        made: RuleLike = module.rrule(freq, **args)
        return made

    return build


def _weekday(module: ModuleType, day: int | list[str | int | None]) -> object:
    match day:
        case [str(name), None]:
            return getattr(module, name)
        case [str(name), int(ordinal)]:
            return getattr(module, name)(ordinal)
        case _:
            raise TypeError(day)


def _pivot(value: dict[str, str | bool] | None) -> Pivot | None:
    return None if value is None else Pivot(parse_bound(str(value["at"])), bool(value["inc"]))


def _case(module: ModuleType, line: str) -> CaseIn:
    raw = json.loads(line)
    dtstart = parse_dtstart(raw["dtstart"])
    text = raw["rule"]

    def build() -> RuleLike:
        made: RuleLike = module.rrulestr(text, dtstart=dtstart)
        return made

    window = raw["window"]
    return CaseIn(
        id=raw["id"],
        limit=int(raw["limit"]),
        build=build,
        build_kw=None if raw["kw"] is None else _kw_builder(module, raw["kw"], dtstart),
        count=bool(raw["count"]),
        window=None if window is None else Window(parse_bound(window["start"]), parse_bound(window["end"]), bool(window["inc"])),
        after=_pivot(raw["after"]),
        before=_pivot(raw["before"]),
    )


def _emit(record: dict[str, object]) -> None:
    data = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"
    if len(data) > MAX_LINE:
        data = json.dumps({"id": record["id"], "oversize": True}, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    view = memoryview(data)
    while view:
        view = view[os.write(OUT_FD, view) :]


def main(argv: list[str]) -> int:
    """Read cases from stdin, write results to fd 3; exit 0 once every case is answered."""
    library = argv[1]
    sys.path.insert(0, library)
    budget = Budget(int(argv[2]) if len(argv) > 2 else STEP_BUDGET)  # noqa: PLR2004
    category = int(argv[3]) if len(argv) > 3 else CATEGORY_BUDGET  # noqa: PLR2004
    try:
        module: ModuleType = budget.run(lambda: __import__("dateutil.rrule", fromlist=["rrule"]))
        require_root(library)
    except StepBudgetExceeded:
        module, failure = ModuleType("absent"), "budget"
    except Exception as error:  # noqa: BLE001 - an unimportable submission is recorded per case
        module, failure = ModuleType("absent"), error_name(error)
    else:
        failure = ""
    for line in sys.stdin:
        if not line.strip():
            continue
        case = _case(module, line)
        if failure:
            _emit({"id": case.id, "import_error": failure})
            continue
        if budget.total > category:
            _emit({"id": case.id, "exhausted": True})
            continue
        _emit(run_case(budget, case))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
