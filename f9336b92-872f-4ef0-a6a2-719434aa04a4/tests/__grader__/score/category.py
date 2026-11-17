"""Score one category: every case's answer must equal the reference's, probe by probe.

All or nothing: the category passes only when the output parses strictly, answers every case
exactly once, names no unknown case, and every probe matches. The result never stores the
expected values, only counts and up to five failing case ids.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from refload import Reference
from score.expected import CaseInput, expected
from score.outputs import Answer, Broken, Failed, MalformedOutputError, parse_file

FIRST_FAILURES: Final = 5


@dataclass(frozen=True, slots=True)
class CategoryResult:
    passed: bool
    cases: int
    failures: int
    first_failures: tuple[str, ...]
    kind: str
    detail: str

    def to_json(self) -> dict[str, bool | int | str | list[str]]:
        """The strict results-file entry; ``detail`` goes to the diagnostics file only.

        ``reason`` is one of ``ok``, ``mismatch``, ``malformed``, or ``budget``.
        """
        return {
            "passed": self.passed,
            "cases": self.cases,
            "failures": self.failures,
            "first_failures": list(self.first_failures),
            "reason": self.kind,
        }


def over_budget(cases: list[CaseInput], detail: str) -> CategoryResult:
    """A category whose child a guard stopped: every case fails, reason ``budget``."""
    every = tuple(case.id for case in cases)
    return CategoryResult(False, len(cases), len(cases), every[:FIRST_FAILURES], "budget", detail)


def read_cases(path: Path) -> list[CaseInput]:
    """The grader's own case file for one category."""
    cases: list[CaseInput] = []
    for line in path.read_text(encoding="ascii").splitlines():
        raw = json.loads(line)
        window, after, before = raw["window"], raw["after"], raw["before"]
        cases.append(
            CaseInput(
                id=str(raw["id"]),
                rule=str(raw["rule"]),
                dtstart=str(raw["dtstart"]),
                limit=int(raw["limit"]),
                kw=raw["kw"] is not None,
                count=bool(raw["count"]),
                window=None if window is None else (str(window["start"]), str(window["end"]), bool(window["inc"])),
                after=None if after is None else (str(after["at"]), bool(after["inc"])),
                before=None if before is None else (str(before["at"]), bool(before["inc"])),
            )
        )
    return cases


def score(ref: Reference, cases: list[CaseInput], output: bytes) -> CategoryResult:
    """Compare the child's output for one category with the reference."""
    every = tuple(case.id for case in cases)
    try:
        answers = parse_file(output)
    except MalformedOutputError as error:
        return CategoryResult(False, len(cases), len(cases), every[:FIRST_FAILURES], "malformed", error.reason)
    unknown = sorted(set(answers) - set(every))
    if unknown:
        return CategoryResult(False, len(cases), len(cases), every[:FIRST_FAILURES], "malformed", f"unknown case ids {unknown[:3]}")
    failing: list[str] = []
    budget = False
    for case in cases:
        answer = answers.get(case.id)
        if not isinstance(answer, Answer) or answer.probes != expected(ref, case):
            failing.append(case.id)
            budget = budget or _over_budget(answer)
    kind = "ok" if not failing else "budget" if budget else "mismatch"
    detail = f"{len(failing)} failing cases"
    return CategoryResult(not failing and bool(cases), len(cases), len(failing), tuple(failing[:FIRST_FAILURES]), kind, detail)


def _over_budget(answer: Answer | Broken | None) -> bool:
    if isinstance(answer, Broken):
        return answer.reason == "exhausted"
    return answer is not None and any(isinstance(r, Failed) and r.error == "budget" for r in answer.probes.values())
