"""Compiled criteria C01 to C09. Reads the grader's results file only; never loads submitted code."""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Final

import rewardkit as rk
from rewardkit import criterion

RESULTS: Final = Path(os.environ.get("GRADE_RESULTS", "/var/grade/results/results.json"))
CATEGORY_KEYS: Final = frozenset({"passed", "cases", "failures", "first_failures", "reason"})
REPAIR: Final = {"C01": "K1", "C02": "K2", "C03": "K3", "C04": "K4", "C05": "K5"}
SHAPES: Final = {
    "C06": frozenset({"passed", "suite_failures", "first_suite_failures"}),
    "C07": frozenset({"passed", "new_tests", "required"}),
    "C08": frozenset({"violated", "changed"}),
    "C09": frozenset({"violated", "signatures_equal", "lost_tests", "first_lost_tests"}),
}


@functools.cache
def _results() -> dict[str, dict[str, object]]:
    """The results file, only when every entry has exactly its expected keys; else empty."""
    try:
        value = json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict) or set(value) != {f"K{i}" for i in range(1, 7)} | set(SHAPES):
        return {}
    for key, entry in value.items():
        if not isinstance(entry, dict) or set(entry) != SHAPES.get(key, CATEGORY_KEYS):
            return {}
    return value


def _flag(entry: str, field: str) -> bool:
    return _results().get(entry, {}).get(field) is True


@functools.cache
def _gate() -> bool:
    """At least one of C01 to C05 passes; otherwise every criterion scores 0."""
    return any(_flag(category, "passed") for category in REPAIR.values())


@criterion(description="{item}: every case of its category matches the reference")
def category_matches(workspace: Path, item: str) -> bool:
    return _gate() and _flag(REPAIR[item], "passed")


@criterion(description="{item}: the check passes")
def check_passes(workspace: Path, item: str) -> bool:
    return _gate() and _flag(item, "passed")


@criterion(description="{item}: the prohibited change is absent")
def violation_absent(workspace: Path, item: str) -> bool:
    return _gate() and _results().get(item, {}).get("violated") is False


rk.category_matches("C01", weight=5, name="C01")
rk.category_matches("C02", weight=5, name="C02")
rk.category_matches("C03", weight=5, name="C03")
rk.category_matches("C04", weight=5, name="C04")
rk.category_matches("C05", weight=5, name="C05")
rk.check_passes("C06", weight=5, name="C06")
rk.check_passes("C07", weight=3, name="C07")
rk.violation_absent("C08", weight=3, name="C08")
rk.violation_absent("C09", weight=3, name="C09")


if __name__ == "__main__":
    import sys

    # Exit 0 when at least one of C01 to C05 passes; test.sh runs the judge only then.
    sys.exit(0 if _gate() else 1)
