"""Assemble the strict results file from the category scores and the constraint checks.

A missing or malformed input fails its own check closed: C06 and C07 do not pass, C08 and C09
count as violated. Reasons go to a separate diagnostics mapping, never into the results file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from canonical import JSONValue
from checks.manifest import changed
from checks.suites import Baseline, Report, ReportError, parse_report, parse_signatures, regression_tests, still_passing

CATEGORIES: Final = ("K1", "K2", "K3", "K4", "K5", "K6")
REPAIR: Final = CATEGORIES[:5]
LISTED: Final = 5


@dataclass(frozen=True, slots=True)
class Inputs:
    categories: Path
    baseline: Path
    shipped_suite: Path
    own_suite: Path
    own_on_shipped: Path
    shipped_sigs: Path
    own_sigs: Path
    manifest: Path
    workspace: Path


def _report(path: Path, notes: dict[str, str], name: str) -> Report | None:
    try:
        return parse_report(path.read_bytes())
    except (OSError, ReportError) as error:
        notes[name] = f"{type(error).__name__}: {error}"
        return None


def _categories(path: Path, notes: dict[str, str]) -> dict[str, dict[str, JSONValue]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        notes["categories"] = str(error)
        value = {}
    out: dict[str, dict[str, JSONValue]] = {}
    for name in CATEGORIES:
        entry = value.get(name) if isinstance(value, dict) else None
        out[name] = entry if isinstance(entry, dict) else {"passed": False, "cases": 0, "failures": 0, "first_failures": [], "reason": "malformed"}
    return out


def assemble(paths: Inputs) -> tuple[dict[str, JSONValue], dict[str, str]]:
    """The results mapping and the diagnostics mapping."""
    notes: dict[str, str] = {}
    results = _categories(paths.categories, notes)
    repaired = sum(1 for name in REPAIR if results[name].get("passed") is True)
    k6 = results["K6"].get("passed") is True
    base_report = _report(paths.baseline, notes, "baseline")
    baseline = None if base_report is None else Baseline.of(base_report)
    shipped_suite = _report(paths.shipped_suite, notes, "shipped_suite")
    own = _report(paths.own_suite, notes, "own_suite")
    cross = _report(paths.own_on_shipped, notes, "own_on_shipped")

    lost_shipped = None if baseline is None or shipped_suite is None else still_passing(baseline, shipped_suite)
    results["C06"] = {
        "passed": lost_shipped == [] and k6,
        "suite_failures": -1 if lost_shipped is None else len(lost_shipped),
        "first_suite_failures": [] if lost_shipped is None else lost_shipped[:LISTED],
    }
    fresh = None if baseline is None or own is None or cross is None else regression_tests(baseline, own, cross)
    required = max(1, repaired)
    results["C07"] = {
        "passed": fresh is not None and len(fresh) >= required,
        "new_tests": -1 if fresh is None else len(fresh),
        "required": required,
    }
    try:
        shipped_manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
        outside = changed({str(k): str(v) for k, v in shipped_manifest.items()}, paths.workspace)
    except (OSError, ValueError, AttributeError) as error:
        notes["manifest"] = str(error)
        outside = ["<manifest unreadable>"]
    results["C08"] = {"violated": bool(outside), "changed": outside[:20]}
    try:
        signatures_equal = parse_signatures(paths.shipped_sigs.read_bytes()) == parse_signatures(paths.own_sigs.read_bytes())
    except (OSError, ReportError) as error:
        notes["signatures"] = str(error)
        signatures_equal = False
    lost_own = None if baseline is None or own is None else still_passing(baseline, own)
    results["C09"] = {
        "violated": not signatures_equal or lost_own != [],
        "signatures_equal": signatures_equal,
        "lost_tests": -1 if lost_own is None else len(lost_own),
        "first_lost_tests": [] if lost_own is None else lost_own[:LISTED],
    }
    return results, notes
