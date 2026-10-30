"""Compiled items C01 to C11. This process reads harness output files only; it never loads agent code."""

import functools
import json
import os
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


@functools.cache
def _item_ok(item):
    if not _admissible():
        return False
    want = {k: v for k, v in _expected().items() if k.startswith(item + "-")}
    got = {}
    try:
        for line in (RESULTS / f"{item}.tsv").read_text().splitlines():
            parts = line.split("\t")
            if len(parts) != 2 or parts[0] in got or parts[0] not in want:
                return False
            got[parts[0]] = parts[1]
    except (OSError, UnicodeDecodeError):
        return False
    return bool(want) and got == want


@criterion
def conforms(workspace: Path, item: str) -> bool:
    return _item_ok(item)


@criterion
def shipped_tests_pass(workspace: Path, item: str) -> bool:
    if not _admissible():
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
