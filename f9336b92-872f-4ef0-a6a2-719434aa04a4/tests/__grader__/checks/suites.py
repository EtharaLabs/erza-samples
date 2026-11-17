"""C06, C07, and C09 from suite reports and signature records.

A suite report is one strict JSON object ``grade.py suite-report`` wrote from pytest's own junit
file, a separate collection pass, and the run's exit status (see ``checks/junit.py``), or
``{"invalid": reason}``. The shipped baseline (the shipped suite run against the shipped library
when the image was built) names the shipped node ids and the ones that passed there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Never

from canonical import CanonicalError, JSONValue, parse_json

OUTCOMES: Final = frozenset({"passed", "failed", "skipped", "error", "xfailed", "xpassed"})
FAILING: Final = frozenset({"failed", "error"})
MAX_REPORT: Final = 32 * 1024 * 1024
MAX_IDS: Final = 200_000


class ReportError(ValueError):
    """A pytest report or signature record breaks its schema."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason: Final = reason


@dataclass(frozen=True, slots=True)
class Report:
    exit: int
    collected: frozenset[str]
    outcomes: dict[str, str]
    collect_errors: frozenset[str]

    def failed_on(self, node: str) -> bool:
        """The test failed or errored, or its module failed to collect."""
        if node in self.outcomes:
            return self.outcomes[node] in FAILING
        module = node.split("::", 1)[0]
        return any(error == module or error.startswith(module + "::") for error in self.collect_errors)


def _bad(reason: str) -> Never:
    raise ReportError(reason)


def _strings(value: JSONValue, where: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_IDS or not all(isinstance(v, str) for v in value):
        _bad(f"{where} must be a list of strings")
    return [str(v) for v in value]


def parse_report(raw: bytes) -> Report:
    """One ``grade.py suite-report`` record, strictly."""
    if len(raw) > MAX_REPORT or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        _bad("a report is one bounded JSON line")
    try:
        value = parse_json(raw)
    except CanonicalError as error:
        _bad(error.reason)
    if isinstance(value, dict) and set(value) == {"invalid"}:
        _bad(f"invalid run: {value['invalid']}")
    if not isinstance(value, dict) or set(value) != {"exit", "collected", "outcomes", "collect_errors"}:
        _bad("report keys differ")
    code, outcomes = value["exit"], value["outcomes"]
    if not isinstance(code, int) or isinstance(code, bool):
        _bad("exit must be an integer")
    if not isinstance(outcomes, dict) or not all(isinstance(v, str) and v in OUTCOMES for v in outcomes.values()):
        _bad("outcomes must map node ids to known outcomes")
    return Report(
        code,
        frozenset(_strings(value["collected"], "collected")),
        {str(k): str(v) for k, v in outcomes.items()},
        frozenset(_strings(value["collect_errors"], "collect_errors")),
    )


def parse_signatures(raw: bytes) -> dict[str, str]:
    """One ``sigs.py`` record: names to signature text."""
    if len(raw) > MAX_REPORT:
        _bad("signature record too large")
    try:
        value = parse_json(raw)
    except CanonicalError as error:
        _bad(error.reason)
    if not isinstance(value, dict) or not value or not all(isinstance(v, str) for v in value.values()):
        _bad("signatures must map names to strings")
    return {str(k): str(v) for k, v in value.items()}


@dataclass(frozen=True, slots=True)
class Baseline:
    """The shipped suite on the shipped library: every node id, and those that passed."""

    shipped: frozenset[str]
    passing: frozenset[str]

    @staticmethod
    def of(report: Report) -> Baseline:
        passing = frozenset(node for node, outcome in report.outcomes.items() if outcome == "passed")
        return Baseline(report.collected | frozenset(report.outcomes), passing)


def still_passing(baseline: Baseline, report: Report) -> list[str]:
    """Shipped node ids that passed on the shipped library but do not pass in ``report``."""
    return sorted(node for node in baseline.passing if report.outcomes.get(node) != "passed")


def regression_tests(baseline: Baseline, on_submission: Report, on_shipped: Report) -> list[str]:
    """New node ids that pass on the submission and fail on the pristine shipped library."""
    fresh = (node for node, outcome in on_submission.outcomes.items() if outcome == "passed" and node not in baseline.shipped)
    return sorted(node for node in fresh if on_shipped.failed_on(node))
