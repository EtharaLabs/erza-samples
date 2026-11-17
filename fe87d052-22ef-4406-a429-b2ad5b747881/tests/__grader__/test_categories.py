"""The compiled categories as pytest tests. This process reads harness output files only and never
loads or runs agent code: the probe and the kept upstream tests already ran as the sandbox user,
and their records sit in GRADE_RESULTS. Each test is all-or-nothing over its whole case set."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle import agrees, expect, is_quiet_nan  # noqa: E402

RESULTS = Path(os.environ.get("GRADE_RESULTS", "/var/grade/results"))
KEPT = (
    "rcppfastfloat_test",
    "wide_char_test",
    "supported_chars_test",
    "example_test",
    "example_comma_test",
    "example_integer_times_pow10",
    "p2497",
    "fast_int",
    "json_fmt",
    "javascript_fmt",
    "fortran",
)
# Text-to-floating conversion routines outside the library; a probe that imports one has
# delegated the parse instead of computing it. Matched against undefined dynamic symbols.
# Besides the C and C++ conversion functions this covers the stream extraction of a
# floating-point value (istream::_M_extract<double|float|long double>, operator>>), the
# num_get facet, and a runtime lookup of any routine through the dynamic loader.
FORBIDDEN_SYMBOL_PARTS = (
    "strtod", "strtof", "strtold", "from_chars", "scanf", "atof", "stod", "stof",
    "_M_extractId", "_M_extractIf", "_M_extractIe", "rsERd", "rsERf", "rsERe",
    "num_get", "dlsym", "dlvsym", "dlopen",
)


def _verdict():
    try:
        return json.loads((RESULTS / "verdict.json").read_text())
    except (OSError, ValueError):
        return {"refused": True}


def _mismatches(category):
    inputs = (RESULTS / f"{category}.in").read_text(encoding="utf-8").splitlines()
    records = (RESULTS / f"{category}.out").read_text(encoding="ascii").splitlines()
    assert inputs, f"{category}: no cases"
    assert len(records) == len(inputs), f"{category}: {len(records)} records for {len(inputs)} cases"
    bad = []
    for line, record in zip(inputs, records):
        fields = record.split(" ")
        assert len(fields) == 4 and fields[0] == line[0], f"{category}: malformed record {record!r}"
        if not agrees(line[0], line[2:], (fields[1], int(fields[2]), int(fields[3]))):
            bad.append(line)
    return bad


def _check(category):
    assert _verdict().get("refused") is False, "the submission is not admissible"
    status = (RESULTS / f"{category}.exit").read_text().strip()
    assert status == "0", f"{category}: the probe did not finish normally ({status}; cpu: over its CPU-time cap, budget: the run's CPU budget is spent, backstop: ended by the wall-clock bound)"
    bad = _mismatches(category)
    assert not bad, f"{category}: {len(bad)} cases disagree with the contract, first: {bad[0]!r}"


@pytest.mark.parametrize("category", ["C1", "C2", "C3", "C4", "C5", "C6", "C8"])
def test_category(category):
    _check(category)


def test_C7():
    _check("C7")
    kept = json.loads((RESULTS / "kept.json").read_text())
    failing = {name: kept.get(name) for name in KEPT if kept.get(name) != 0}
    assert not failing, f"kept upstream tests failing: {failing}"


def test_K8_scope():
    scope = json.loads((RESULTS / "scope.json").read_text())
    assert scope.get("readable") is True, "the collected tree could not be read"
    assert not scope["violations"], f"changed outside the allowed paths: {scope['violations'][:5]}"


def test_K9_no_external_conversion():
    symbols = json.loads((RESULTS / "symbols.json").read_text())
    assert symbols.get("readable") is True, "the probe's symbols could not be read"
    hits = [s for s in symbols["undefined"] if any(part in s for part in FORBIDDEN_SYMBOL_PARTS)]
    assert not hits, f"the parse delegates to {hits[:5]}"


def test_K10_reproductions():
    assert _verdict().get("refused") is False, "the submission is not admissible"
    # A Reproduction line over report_items.MAX_LINE is recorded but neither checked nor counted.
    rows = [row for row in json.loads((RESULTS / "reproductions.json").read_text()) if not row.get("over_cap")]
    assert rows, "the report holds no Reproduction line within the per-line cap"
    malformed = [row["line"] for row in rows if row["malformed"]]
    assert not malformed, f"Reproduction lines not in the stated form: {malformed[:3]}"
    status = (RESULTS / "shipped.exit").read_text().strip()
    assert status == "0", f"the shipped library's probe did not finish normally ({status})"
    records = (RESULTS / "shipped.out").read_text(encoding="ascii").splitlines()
    assert len(records) == len(rows), f"{len(records)} shipped records for {len(rows)} Reproduction lines"
    false = []
    for row, record in zip(rows, records):
        shipped_bits = record.split(" ")[1]
        contract_bits = expect(row["kind"], row["input"])[0]
        required = int(row["required"], 16)
        if contract_bits == "qnan":
            required_true = is_quiet_nan(row["kind"], row["required"])
        else:
            required_true = required == int(contract_bits, 16)
        produced_true = int(row["produced"], 16) == int(shipped_bits, 16)
        if not (required_true and produced_true and required != int(row["produced"], 16)):
            false.append((row["kind"], row["input"][:60], row["required"], row["produced"], contract_bits, shipped_bits))
    assert not false, f"{len(false)} Reproduction lines are not true, first: {false[0]!r}"


def test_K11_regression_tests():
    assert _verdict().get("refused") is False, "the submission is not admissible"
    named = json.loads((RESULTS / "named.json").read_text())
    assert named.get("count", 0) >= 1, "the report names no added or changed test as tests/<name>.cpp"
    assert not named.get("too_many"), f"the report names {named['count']} tests, more than 16"
    bad = {}
    for name, row in named["tests"].items():
        shipped = str(row.get("shipped", ""))
        if row.get("missing") or row.get("submitted") != "0" or not shipped.startswith(("exit:", "signal:")):
            bad[name] = row
    assert not bad, f"named tests that do not pass on the submitted library and fail on the shipped one: {bad}"


# Conversion cost (instruction.md): callgrind instruction counts of the verifier's meter inside
# convert_all, for the submitted library and for fast_float 8.3.3 as released, on the same corpus
# in the same run. A category passes only when the submission's results on the corpus equal the
# reference's and its count stays within the stated bound.
COST_RATIO = ("ties_double", "ties_float", "fast_path", "near_overflow", "scaled_ties",
              "long_char_double", "long_char16_double", "long_char32_double")
COST_LINEAR = ("char_double", "char_float", "char16_double", "char16_float", "char32_double", "char32_float")
RATIO_LIMIT = 1.5
GROWTH_LIMIT = 5.0


def _counted(side, corpus):
    """(instructions, result hash) of one callgrind count; the submission's must have finished normally."""
    base = RESULTS / f"cost_{side}" / corpus
    if side == "sub":
        status = (base.with_suffix(".exit")).read_text().strip()
        assert status == "0", f"cost {corpus}: the meter did not finish normally ({status})"
    totals = [l for l in base.with_suffix(".cg").read_text(encoding="ascii", errors="replace").splitlines() if l.startswith("totals:")]
    assert len(totals) == 1, f"cost {corpus}: no single callgrind total"
    count = int(totals[0].split()[1])
    digest = base.with_suffix(".hash").read_text().strip()
    assert count > 0 and len(digest) == 16, f"cost {corpus}: malformed count"
    return count, digest


def _agreeing(corpus):
    assert _verdict().get("refused") is False, "the submission is not admissible"
    sub, ref = _counted("sub", corpus), _counted("ref", corpus)
    assert sub[1] == ref[1], f"cost {corpus}: the results differ from the contract's"
    return sub[0], ref[0]


@pytest.mark.parametrize("corpus", COST_RATIO)
def test_cost_ratio(corpus):
    sub, ref = _agreeing(corpus)
    assert sub <= RATIO_LIMIT * ref, f"cost {corpus}: {sub / ref:.2f} times fast_float 8.3.3's instructions, over {RATIO_LIMIT}"


@pytest.mark.parametrize("form", COST_LINEAR)
def test_cost_growth(form):
    short, _ = _agreeing(f"linear_{form}_2000")
    long, _ = _agreeing(f"linear_{form}_8000")
    assert long <= GROWTH_LIMIT * short, f"cost {form}: 4x the length costs {long / short:.2f}x the instructions, over {GROWTH_LIMIT}"
