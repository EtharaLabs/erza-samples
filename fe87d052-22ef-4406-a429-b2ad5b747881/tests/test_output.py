"""Compiled items K1 to K26 as Reward Kit criteria. This process reads grading result files only;
it never loads or runs agent code. Each item reads the outcome of one pytest test in
/opt/grader/test_categories.py from the JUnit report the grader wrote."""

import functools
import json
import os
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

RESULTS = Path(os.environ.get("GRADE_RESULTS", "/var/grade/results"))
TESTS = {
    "K1": "test_category[C1]",
    "K2": "test_category[C2]",
    "K3": "test_category[C3]",
    "K4": "test_category[C4]",
    "K5": "test_category[C5]",
    "K6": "test_category[C6]",
    "K7": "test_C7",
    "K8": "test_K8_scope",
    "K9": "test_K9_no_external_conversion",
    "K10": "test_K10_reproductions",
    "K11": "test_K11_regression_tests",
    "K12": "test_category[C8]",
    "K13": "test_cost_ratio[ties_double]",
    "K14": "test_cost_ratio[ties_float]",
    "K15": "test_cost_ratio[fast_path]",
    "K16": "test_cost_ratio[near_overflow]",
    "K17": "test_cost_ratio[scaled_ties]",
    "K18": "test_cost_ratio[long_char_double]",
    "K19": "test_cost_ratio[long_char16_double]",
    "K20": "test_cost_ratio[long_char32_double]",
    "K21": "test_cost_growth[char_double]",
    "K22": "test_cost_growth[char_float]",
    "K23": "test_cost_growth[char16_double]",
    "K24": "test_cost_growth[char16_float]",
    "K25": "test_cost_growth[char32_double]",
    "K26": "test_cost_growth[char32_float]",
}
# K5 and K6 pass on the library as shipped, so only K1 to K4 show that a seeded cause was repaired.
REPAIR_ITEMS = ("K1", "K2", "K3", "K4")


@functools.cache
def _admissible():
    try:
        verdict = json.loads((RESULTS / "verdict.json").read_text())
    except (OSError, ValueError):
        return False
    return verdict.get("refused") is False and verdict.get("changed") is True


@functools.cache
def _passed():
    """The names of the pytest tests that passed, from one well-formed JUnit report."""
    try:
        root = ElementTree.parse(RESULTS / "junit.xml").getroot()
    except (OSError, ElementTree.ParseError):
        return frozenset()
    names, seen = set(), []
    for case in root.iter("testcase"):
        name = case.get("name", "")
        seen.append(name)
        if not any(child.tag in {"failure", "error", "skipped"} for child in case):
            names.add(name)
    if len(seen) != len(set(seen)) or set(seen) != set(TESTS.values()):
        return frozenset()
    return frozenset(names)


@functools.cache
def _repaired():
    # Every item but the first six categories scores only for a library that repairs at least one
    # of them, so the unmodified copy, which keeps every fault, earns nothing.
    return _admissible() and any(TESTS[item] in _passed() for item in REPAIR_ITEMS)


def _score(item: str) -> bool:
    if not _admissible():
        return False
    if item not in REPAIR_ITEMS and not _repaired():
        return False
    return TESTS[item] in _passed()


@criterion
def conforms(workspace: Path, item: str) -> bool:
    return _score(item)


rk.conforms("K1", weight=5, name="K1")
rk.conforms("K2", weight=5, name="K2")
rk.conforms("K3", weight=5, name="K3")
rk.conforms("K4", weight=5, name="K4")
# No shipped fault reaches C5 or C6; each guards against a repair that breaks them.
rk.conforms("K5", weight=1, name="K5")
rk.conforms("K6", weight=1, name="K6")
rk.conforms("K7", weight=5, name="K7")
# K8 and K9 are prohibitions (negate true in the rubric): each scores 1 when its prohibited act,
# a change outside the allowed paths or a delegated parse, is absent.
rk.conforms("K8", weight=3, name="K8")
rk.conforms("K9", weight=3, name="K9")
rk.conforms("K10", weight=5, name="K10")
rk.conforms("K11", weight=3, name="K11")
rk.conforms("K12", weight=5, name="K12")
# K13 to K26: conversion cost, the ratio categories then the linear-growth categories.
rk.conforms("K13", weight=5, name="K13")
rk.conforms("K14", weight=5, name="K14")
rk.conforms("K15", weight=5, name="K15")
rk.conforms("K16", weight=5, name="K16")
rk.conforms("K17", weight=5, name="K17")
rk.conforms("K18", weight=5, name="K18")
rk.conforms("K19", weight=5, name="K19")
rk.conforms("K20", weight=5, name="K20")
rk.conforms("K21", weight=5, name="K21")
rk.conforms("K22", weight=5, name="K22")
rk.conforms("K23", weight=5, name="K23")
rk.conforms("K24", weight=5, name="K24")
rk.conforms("K25", weight=5, name="K25")
rk.conforms("K26", weight=5, name="K26")

if __name__ == "__main__":
    import sys

    # Exit 0 when the library repairs at least one of K1 to K4; test.sh runs the judge only then.
    sys.exit(0 if _repaired() else 1)
