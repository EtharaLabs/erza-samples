"""Compiled items C01 to C11. This process reads harness output files only; it never loads agent code."""

import functools
import json
import os
import re
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

RESULTS = Path(os.environ.get("GRADE_RESULTS", "/var/grade/results"))
EXPECTED = Path("/opt/grader/expected.json")


@functools.cache
def _verdict():
    try:
        return json.loads((RESULTS / "verdict.json").read_text())
    except (OSError, ValueError):
        return {"refused": True}


@functools.cache
def _expected():
    return json.loads(EXPECTED.read_text())


def _admissible():
    v = _verdict()
    # Every item needs a changed library: the shipped engine trivially keeps its own behaviour.
    return v.get("refused") is False and v.get("changed") is True


# One result line as the harness writes it to descriptor 3 (stdout never reaches the results):
# case id, a tab, the result. Leading indentation, a bracketed timestamp, a module-path prefix
# and a #NN ordinal after the id are tolerated. A line that does not match this grammar is ignored;
# every expected case id must appear exactly once, and a duplicate or unknown id fails the item.
RESULT_LINE = re.compile(
    r"\s*(?:\[[^\]\t]*\]\s*)?(?:[A-Za-z_]\w*::)*(?P<id>C\d{2}-\d{4})(?:#\d+)?\t(?P<result>[^\t]*)"
)


@functools.cache
def _item_ok(item):
    if not _admissible():
        return False
    want = {k: v for k, v in _expected().items() if k.startswith(item + "-")}
    got = {}
    try:
        for line in (RESULTS / f"{item}.tsv").read_text().splitlines():
            m = RESULT_LINE.fullmatch(line)
            if m is None:
                continue
            if m["id"] in got or m["id"] not in want:
                return False
            got[m["id"]] = m["result"]
    except (OSError, UnicodeDecodeError):
        return False
    return bool(want) and got == want


REPAIR_ITEMS = ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08")
KEPT_ITEMS = ("C10", "C11")


@functools.cache
def _repaired():
    # The kept properties (C09 to C11) score only for a library that repairs something, so a
    # change that leaves every fault in place keeps the shipped behaviour and earns nothing.
    return any(_item_ok(item) for item in REPAIR_ITEMS)


@criterion
def conforms(workspace: Path, item: str) -> bool:
    if item in KEPT_ITEMS and not _repaired():
        return False
    return _item_ok(item)


@criterion
def shipped_tests_pass(workspace: Path, item: str) -> bool:
    if not _admissible() or not _repaired():
        return False
    try:
        return (RESULTS / "C09.exit").read_text().strip() == "0"
    except OSError:
        return False


rk.conforms("C01", weight=5, name="C01")
rk.conforms("C02", weight=5, name="C02")
rk.conforms("C03", weight=5, name="C03")
rk.conforms("C04", weight=5, name="C04")
rk.conforms("C05", weight=1, name="C05")
rk.conforms("C06", weight=3, name="C06")
rk.conforms("C07", weight=3, name="C07")
rk.conforms("C08", weight=1, name="C08")
rk.shipped_tests_pass("C09", weight=1, name="C09")
rk.conforms("C10", weight=1, name="C10")
rk.conforms("C11", weight=1, name="C11")

if __name__ == "__main__":
    # test.sh asks this before the judge runs: exit 0 only when at least one of C01 to C08 passes.
    import sys

    sys.exit(0 if _repaired() else 1)
