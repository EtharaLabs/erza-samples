"""Compiled items K1 to K7. Each test reads the evidence test.sh collected under GRADE_RESULTS and
passes only when the item's criterion holds; no test runs submitted code."""

import json
import os
from pathlib import Path

import pytest

RESULTS = Path(os.environ["GRADE_RESULTS"])
GRADER = Path(os.environ["GRADER_DIR"])
SPEC = json.loads((GRADER / "categories.json").read_text())


def admitted():
    admission = json.loads((RESULTS / "admission.json").read_text())
    assert not admission["refused"], "edit rules: " + "; ".join(admission["reasons"])


def category(cat):
    """Every expected schedule ran exactly once in this run and none shows a violation."""
    admitted()
    outcome = (RESULTS / f"{cat}.exit").read_text().strip()
    nonce = (RESULTS / "nonce").read_text()
    spec = SPEC["categories"][cat]
    expected = {(f"template:{t}", i) for t in spec["templates"] for i in range(SPEC["template_instances"])}
    seeds = int((RESULTS / "seeds").read_text())
    expected |= {(f"random:{r}", s) for r in spec["random"] for s in range(1, seeds + 1)}
    seen, failures = set(), []
    for line in (RESULTS / f"{cat}.jsonl").read_text().splitlines():
        record = json.loads(line)
        assert record["nonce"] == nonce and record["category"] == cat, "a record from another run or category"
        key = (record["family"], record["instance"])
        assert key in expected and key not in seen, f"unexpected or repeated record {key}"
        seen.add(key)
        if record["verdict"] != "pass":
            failures.append(f"{record['family']} #{record['instance']}: {record['violation']}")
    assert not failures, failures[0]
    assert outcome == "0", f"harness step outcome {outcome}"
    assert seen == expected, f"{len(expected - seen)} schedules have no record"


def test_K1():
    category("CA")


def test_K2():
    category("CB")


def test_K3():
    category("CRA")


def test_K4():
    category("CR")


def test_K5():
    category("CS")


def test_K6():
    admitted()
    assert (RESULTS / "ck.exit").read_text().strip() == "0", "upstream tests did not all pass"


def test_K7():
    admitted()
    named = json.loads((RESULTS / "named.json").read_text())
    outcomes = json.loads((RESULTS / "named_outcomes.json").read_text())
    assert named["report"], "no report"
    assert 0 < named["count"] <= 16, f"{named['count']} named regression tests"
    for tests in named["named"].values():
        for test in tests:
            got = outcomes.get(test, {})
            assert got.get("submitted") == "0", f"{test} on the submitted library: {got.get('submitted')}"
            assert str(got.get("shipped", "")).startswith("exit:"), f"{test} on the library as shipped: {got.get('shipped')}"
