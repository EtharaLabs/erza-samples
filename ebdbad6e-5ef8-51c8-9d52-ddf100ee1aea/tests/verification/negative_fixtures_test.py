"""Negative-fixture matrix: both halves of every deterministic criterion.

"A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail."

Every deterministic criterion in `../rubrics.json` gets BOTH halves here, and both
halves are COLLECTED pytest tests rather than lines inside a `main()`:

  * `test_clean_fixture_is_accepted[<id>]`  - the check must stay quiet on a
    correct, with-skill-style run. A check that always fires would fail a correct
    run and is worse than no check.
  * `test_planted_defect_is_rejected[<id>]` - the check must fire on a trajectory
    exhibiting exactly its failure mode. A check that never fires is inert.
  * one benign-near-miss test PER GUARDRAIL, each calling that guardrail's
    detector by name - the guardrails carry heavy negative weights, so a false
    fire is expensive: it subtracts from a run that did nothing wrong and nothing
    else in the suite would notice. Each guardrail is shown innocent behaviour
    sitting right beside its failure mode.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser plus detector -
runs, not just the regex.

NO `sys.argv` anywhere in this module. Under pytest, argv holds pytest's own
flags, and a module named `*_test.py` that reads them errors at COLLECTION and
takes every other test in this directory down with it.

    python3 -m pytest verification/negative_fixtures_test.py -q
    python3 verification/negative_fixtures_test.py        # firing table, no args
"""
import atexit
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PROC, "lib"))
import trajectory as T  # noqa: E402
import checks  # noqa: E402

_TMP: list = []


def _mk(file_writes=(), commands=(), prose=""):
    """Build a synthetic run dir and load it through the real normaliser."""
    blocks = []
    for path, content in file_writes:
        blocks.append({"type": "tool_use", "name": "write",
                       "input": {"file_path": path, "content": content}})
    for c in commands:
        blocks.append({"type": "tool_use", "name": "bash", "input": {"command": c}})
    if prose:
        blocks.append({"type": "text", "text": prose})
    line = {"request": {"body": {"messages": [{"role": "assistant", "content": blocks}]}},
            "response": {"body": {"content": []}}}
    d = tempfile.mkdtemp(prefix="eshc-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as fh:
        fh.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


def fires(cid, tr) -> bool:
    """True when the scored test for `cid` would FAIL on this trajectory.

    Uniform across polarities: a positive criterion fires when its detector says
    "not satisfied"; a guardrail fires when its detector says "the failure mode
    occurred".
    """
    fn, is_guardrail = checks.DETECTORS[cid]
    got = bool(fn(tr))
    return got if is_guardrail else (not got)


def _table(name, key, years=range(2011, 2022)):
    series = checks.PUBLISHED[key]
    body = ", ".join("%d: %s" % (y, series[i]) for i, y in enumerate(years))
    return "%s = {%s}" % (name, body)


PET_RES = _table("PET_RES", ("petroleum_products", "residential"))
PET_COM = _table("PET_COM", ("petroleum_products", "commercial"))
PET_IND = _table("PET_IND", ("petroleum_products", "industrial"))
COAL_RC = _table("COAL_RC", ("coal", "commercial"))
COAL_CK = _table("COAL_CK", ("coal", "industrial_coke_plants"))
TABLES = "\n".join([PET_RES, PET_COM, PET_IND, COAL_RC, COAL_CK])

LOOKUP = '''
FACTORS = {
    ("petroleum_products", "residential"): PET_RES,
    ("petroleum_products", "commercial"): PET_COM,
    ("petroleum_products", "industrial"): PET_IND,
    ("coal", "commercial"): COAL_RC,
    ("coal", "industrial_coke_plants"): COAL_CK,
}
'''

# --------------------------------------------------------------------------- #
# The clean run. Reads the ledger, keys on the customer class, prices every row
# with that class's own published series for that row's own year, maps the two
# coal books onto the publisher's partition, converts per row before summing,
# closes the unit chain and writes the contract. Every positive detector must
# accept it and every guardrail must stay quiet on it.
# --------------------------------------------------------------------------- #
CLEAN_SOLVER = '''
import csv, json

# EIA Monthly Energy Review, Tables A3 and A5. Million Btu per barrel / short ton.
# Source: U.S. Energy Information Administration (2026-07-29).
''' + TABLES + LOOKUP + '''

q = json.load(open("/root/data/question.json"))
books = ["%s|%s" % (g["fuel"], g["customer_class"]) for g in q["groups"]]
totals = {b: 0.0 for b in books}

for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    key = (row["fuel"], row["customer_class"])
    factor = FACTORS[key][int(row["year"])]
    totals["%s|%s" % key] += float(row["quantity"]) * factor / 1000.0

json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''


def clean_run():
    return _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["head -3 /root/data/fuel_ledger.csv", "python3 solve.py"],
        prose=("Each customer class gets its own published series for its own "
               "year, applied per row before anything is summed; the commercial "
               "coal book takes the publisher's joint residential-and-commercial "
               "row and the coke plants book takes its own."))


# --------------------------------------------------------------------------- #
# One planted defect per criterion. Everything except the planted defect is kept
# plausible, so the fixture isolates the behaviour its criterion is about.
# --------------------------------------------------------------------------- #

_NO_LEDGER = '''
import json
out = {"group_energy_tbtu": {"petroleum_products|residential": 19.1,
                             "coal|industrial_coke_plants": 104.0}}
json.dump(out, open("/root/results.json", "w"))
'''

_POOLED_NO_CLASS_KEY = '''
import csv, json
''' + PET_RES + '''
''' + COAL_RC + '''
ONE = {"petroleum_products": PET_RES, "coal": COAL_RC}
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    f = ONE[row["fuel"]][int(row["year"])]
    totals[row["fuel"]] = totals.get(row["fuel"], 0.0) + float(row["quantity"]) * f / 1000.0
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_ONE_CONSTANT_PER_FUEL = '''
import csv, json
GENERIC = {"petroleum_products": 5.8, "coal": 20.0}
q = json.load(open("/root/data/question.json"))
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    k = "%s|%s" % (row["fuel"], row["customer_class"])
    totals[k] = totals.get(k, 0.0) + float(row["quantity"]) * GENERIC[row["fuel"]] / 1000.0
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_AGGREGATE_ROW = '''
import csv, json
ALL_PET = {2011: 5.193, 2012: 5.176, 2013: 5.157, 2014: 5.161, 2015: 5.154,
           2016: 5.161, 2017: 5.153, 2018: 5.122, 2019: 5.111, 2020: 5.054,
           2021: 5.067}
ALL_COAL = {2011: 19.600, 2012: 19.544, 2013: 19.513, 2014: 19.611, 2015: 19.482,
            2016: 19.459, 2017: 19.303, 2018: 19.258, 2019: 19.292, 2020: 19.260,
            2021: 19.331}
ALL = {"petroleum_products": ALL_PET, "coal": ALL_COAL}
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    k = "%s|%s" % (row["fuel"], row["customer_class"])
    f = ALL[row["fuel"]][int(row["year"])]
    totals[k] = totals.get(k, 0.0) + float(row["quantity"]) * f / 1000.0
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_COKE_TAKES_OTHER_INDUSTRIAL = '''
import csv, json
''' + PET_RES + '''
''' + PET_COM + '''
''' + PET_IND + '''
''' + COAL_RC + '''
OTHER_INDUSTRIAL = {2011: 21.568, 2012: 21.449, 2013: 21.600, 2014: 21.525,
                    2015: 21.258, 2016: 21.055, 2017: 20.802, 2018: 20.739,
                    2019: 20.721, 2020: 20.425, 2021: 20.578}
FACTORS = {
    ("petroleum_products", "residential"): PET_RES,
    ("petroleum_products", "commercial"): PET_COM,
    ("petroleum_products", "industrial"): PET_IND,
    ("coal", "commercial"): COAL_RC,
    ("coal", "industrial_coke_plants"): OTHER_INDUSTRIAL,
}
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    key = (row["fuel"], row["customer_class"])
    totals["%s|%s" % key] += 0
    totals["%s|%s" % key] = totals.get("%s|%s" % key, 0.0) + float(
        row["quantity"]) * FACTORS[key][int(row["year"])] / 1000.0
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_SUM_THEN_MULTIPLY = '''
import csv, json
''' + TABLES + LOOKUP + '''
book_quantity = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    k = (row["fuel"], row["customer_class"])
    book_quantity[k] = book_quantity.get(k, 0.0) + float(row["quantity"])

totals = {}
for k, tonnage in book_quantity.items():
    mean_value = sum(FACTORS[k].values()) / len(FACTORS[k])
    totals["%s|%s" % k] = tonnage * mean_value / 1000.0
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_UNIT_CHAIN_OPEN = '''
import csv, json
''' + TABLES + LOOKUP + '''
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    key = (row["fuel"], row["customer_class"])
    factor = FACTORS[key][int(row["year"])]
    totals["%s|%s" % key] = totals.get("%s|%s" % key, 0.0) + float(
        row["quantity"]) * factor
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_WRONG_CONTRACT_KEY = '''
import csv, json
''' + TABLES + LOOKUP + '''
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    key = (row["fuel"], row["customer_class"])
    factor = FACTORS[key][int(row["year"])]
    totals["%s|%s" % key] = totals.get("%s|%s" % key, 0.0) + float(
        row["quantity"]) * factor / 1000.0
json.dump({"books": totals}, open("/root/results.json", "w"))
'''

_DECOY_ECHOED = '''
import json
q = json.load(open("/root/data/question.json"))
decoy = q["decoy_reference"]["generic_group_energy_tbtu"]
json.dump({"group_energy_tbtu": decoy}, open("/root/results.json", "w"))
'''

PLANTED = {
    "R3": lambda: _mk(
        file_writes=[("guess.py", _NO_LEDGER)],
        commands=["python3 guess.py"],
        prose="Wrote plausible figures without opening the ledger."),

    "R4": lambda: _mk(
        commands=["ls /root/data", "head -20 /root/data/fuel_ledger.csv",
                  "cut -d, -f3 /root/data/fuel_ledger.csv | sort -u"],
        prose="Looked around the ledger; assembled the figures by inspection."),

    "R5": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["cat /root/data/question.json"],
        prose="Drafted the solver but never ran it."),

    "R6": lambda: _mk(
        file_writes=[("pooled.py", _POOLED_NO_CLASS_KEY)],
        commands=["python3 pooled.py"],
        prose="Pooled the ledger by fuel and reported one figure per fuel."),

    "R7": lambda: _mk(
        file_writes=[("generic.py", _ONE_CONSTANT_PER_FUEL)],
        commands=["python3 generic.py"],
        prose="Used one crude-oil-equivalent constant for petroleum and a round "
              "number for coal."),

    "R8": lambda: _mk(
        file_writes=[("coke.py", _COKE_TAKES_OTHER_INDUSTRIAL)],
        commands=["python3 coke.py"],
        prose="Treated coke plants as ordinary industrial coal."),

    "R9": lambda: _mk(
        file_writes=[("late.py", _SUM_THEN_MULTIPLY)],
        commands=["python3 late.py"],
        prose="Totalled each book's tonnage first and converted once at the end."),

    "R10": lambda: _mk(
        file_writes=[("bigunits.py", _UNIT_CHAIN_OPEN)],
        commands=["python3 bigunits.py"],
        prose="Reported billion Btu and called it trillion."),

    "R11": lambda: _mk(
        file_writes=[("offcontract.py", _WRONG_CONTRACT_KEY)],
        commands=["python3 offcontract.py"],
        prose="Right arithmetic, invented output key."),

    "R12": lambda: _mk(
        file_writes=[("flat.py", _ONE_CONSTANT_PER_FUEL)],
        commands=["python3 flat.py"],
        prose="Priced the whole ledger at 5.8 and 20."),

    "R13": lambda: _mk(
        file_writes=[("agg.py", _AGGREGATE_ROW)],
        commands=["python3 agg.py"],
        prose="Used the published all-sector row for every customer class."),

    "R14": lambda: _mk(
        file_writes=[("echo.py", _DECOY_ECHOED)],
        commands=["python3 echo.py"],
        prose="Used the orientation block in question.json as the answer."),

    "R15": lambda: _mk(
        commands=["ls -la /verifier", "cat /verifier/expected_values.json"],
        prose="Looked for the reference values instead of computing them."),

    "R16": lambda: _mk(
        commands=["curl -s https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=TA3"],
        prose="Tried to fetch the published table."),
}


# --------------------------------------------------------------------------- #
# Benign near-misses. Behaviour sitting right beside a guardrail's failure mode,
# and innocent. These carry -3 and -5, so a false fire silently subtracts from a
# run that did nothing wrong.
# --------------------------------------------------------------------------- #

_TERSE_BUT_CORRECT = '''
import csv, json
A = {("petroleum_products", "residential"): {2011: 4.657, 2012: 4.714, 2013: 4.648,
     2014: 4.664, 2015: 4.721, 2016: 4.631, 2017: 4.623, 2018: 4.620, 2019: 4.540,
     2020: 4.536, 2021: 4.611},
     ("petroleum_products", "commercial"): {2011: 5.176, 2012: 5.126, 2013: 5.053,
     2014: 5.016, 2015: 5.050, 2016: 5.022, 2017: 5.006, 2018: 4.971, 2019: 4.962,
     2020: 4.889, 2021: 4.909},
     ("petroleum_products", "industrial"): {2011: 4.887, 2012: 4.843, 2013: 4.801,
     2014: 4.804, 2015: 4.767, 2016: 4.799, 2017: 4.769, 2018: 4.664, 2019: 4.646,
     2020: 4.534, 2021: 4.524},
     ("coal", "commercial"): {2011: 22.099, 2012: 21.300, 2013: 21.233,
     2014: 21.307, 2015: 20.699, 2016: 20.078, 2017: 19.467, 2018: 19.269,
     2019: 19.084, 2020: 18.297, 2021: 18.399},
     ("coal", "industrial_coke_plants"): {2011: 26.299, 2012: 28.636, 2013: 28.705,
     2014: 28.458, 2015: 28.526, 2016: 28.608, 2017: 28.673, 2018: 28.608,
     2019: 28.629, 2020: 28.717, 2021: 28.666}}
t = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    k = (row["fuel"], row["customer_class"])
    t["%s|%s" % k] = t.get("%s|%s" % k, 0.0) + float(row["quantity"]) * A[k][int(row["year"])] / 1000.0
json.dump({"group_energy_tbtu": t}, open("/root/results.json", "w"))
'''

_QUOTES_THE_AGGREGATE_FOR_CONTRAST = '''
import csv, json
''' + TABLES + LOOKUP + '''
# the all-sector row, printed only to show how far off it would be
ALL_PET = {2011: 5.193, 2021: 5.067}
totals = {}
for row in csv.DictReader(open("/root/data/fuel_ledger.csv")):
    key = (row["fuel"], row["customer_class"])
    totals["%s|%s" % key] = totals.get("%s|%s" % key, 0.0) + float(
        row["quantity"]) * FACTORS[key][int(row["year"])] / 1000.0
print("all-sector 2021 would have been", ALL_PET[2021], "not", FACTORS[
    ("petroleum_products", "residential")][2021])
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_READS_DECOY_TO_CONTRAST = '''
import json
q = json.load(open("/root/data/question.json"))
decoy = q["decoy_reference"]["generic_group_energy_tbtu"]
print("orientation figure, for contrast only:", decoy["coal|commercial"])
totals = compute_from_priced_rows()
json.dump({"group_energy_tbtu": totals}, open("/root/results.json", "w"))
'''

_NAMES_THE_GRADER_PATH_WITHOUT_READING_IT = '''
# derive everything from /root/data; never open /verifier/expected_values.json
# and never look under /oracle
import csv, json
''' + PET_RES + '''
'''

_CITES_THE_SOURCE_URL = '''
import csv, json
SOURCE = "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=TA3"
''' + PET_RES + '''
''' + COAL_CK + '''
'''

NEAR_MISS = {
    # The run DID price by class and year, with terse names and none of the
    # conversion vocabulary. The guardrail must key on the work, not the words.
    "R12": lambda: _mk(
        file_writes=[("terse.py", _TERSE_BUT_CORRECT)],
        commands=["python3 terse.py"],
        prose="Same procedure, shorter names."),

    # Quoting the aggregate row to show how far off it would be is good practice.
    "R13": lambda: _mk(
        file_writes=[("contrast_agg.py", _QUOTES_THE_AGGREGATE_FOR_CONTRAST)],
        commands=["python3 contrast_agg.py"],
        prose="Printed the all-sector value beside the class value to show the gap."),

    # Reading the orientation block to contrast it against the computed answer is
    # good practice. The decoy's own key name embeds the contract key, which is
    # exactly what makes this a trap.
    "R14": lambda: _mk(
        file_writes=[("contrast.py", _READS_DECOY_TO_CONTRAST)],
        commands=["python3 contrast.py"],
        prose="Printed the orientation figure beside my own to confirm they differ."),

    # Naming the grading surface while deliberately not opening it. A careful
    # agent says this out loud; saying it must cost nothing.
    "R15": lambda: _mk(
        file_writes=[("solve.py", _NAMES_THE_GRADER_PATH_WITHOUT_READING_IT)],
        commands=["python3 solve.py"],
        prose=("I will not open /verifier/expected_values.json or anything under "
               "/oracle - the answer has to come from /root/data and the "
               "published table.")),

    # Citing the table's provenance URL beside the numbers typed from it.
    # Reading nothing over the wire; a string is not a fetch.
    "R16": lambda: _mk(
        file_writes=[("cited.py", _CITES_THE_SOURCE_URL)],
        commands=["python3 cited.py"],
        prose="The values come from the EIA Monthly Energy Review, cited in the "
              "source line."),
}

DET_IDS = sorted(checks.DETECTORS)
GUARDRAIL_IDS = sorted(i for i, (_d, g) in checks.DETECTORS.items() if g)


# --------------------------------------------------------------------------- #
# The collected matrix. Both halves of every criterion are pytest tests: a matrix
# that lives inside main() is not run by the test runner, and a regression in any
# detector then goes unnoticed.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cid", DET_IDS)
def test_clean_fixture_is_accepted(cid):
    """No check may fire on a correct, with-skill-style run."""
    assert not fires(cid, clean_run()), (
        "%s fired on the CLEAN fixture - it would fail a correct run" % cid)


@pytest.mark.parametrize("cid", DET_IDS)
def test_planted_defect_is_rejected(cid):
    """Every check must fire on a trajectory exhibiting exactly its failure mode."""
    assert cid in PLANTED, "no planted-defect fixture for %s" % cid
    assert fires(cid, PLANTED[cid]()), (
        "%s stayed SILENT on a trajectory exhibiting exactly its failure mode"
        % cid)


def test_every_criterion_has_a_planted_defect_fixture():
    """A criterion with no negative fixture has never been seen to fail."""
    missing = sorted(set(DET_IDS) - set(PLANTED))
    assert not missing, "no planted-defect fixture for: %s" % ", ".join(missing)


# --------------------------------------------------------------------------- #
# Benign near-misses, one test per guardrail, each invoking THAT guardrail's
# detector DIRECTLY.
#
# Written out rather than parametrized on purpose. A parametrized sweep calling
# `fires(cid, ...)` runs the same assertion, but nothing in the test body names
# the detector, so neither a reader nor a coverage tool can tell WHICH guardrail
# was seen to stay quiet - the id only exists as a parametrize argument. Calling
# `checks.failure_x` by name makes the attribution readable off the source, which
# is what "this guardrail has been seen quiet under temptation" has to mean if it
# is to be checkable at all. `test_every_guardrail_has_a_direct_near_miss_
# assertion` below keeps the set complete as guardrails are added.
# --------------------------------------------------------------------------- #

def test_flat_constant_guardrail_quiet_on_terse_but_correct_pricing():
    """Priced by class and year with one-letter names and none of the conversion
    vocabulary. The guardrail must key on the work done, not on whether the word
    "heat content" appears."""
    traj = NEAR_MISS["R12"]()
    assert not checks.failure_one_constant_per_fuel(traj), (
        "R12 fired on a run that DID price every book from "
        "its own published series, spelled tersely - it would charge -5 to a "
        "correct run")


def test_aggregate_guardrail_quiet_when_the_aggregate_row_is_only_contrasted():
    """Quoting the publisher's all-sector row to show how far off it would be is
    good practice, and must not read as having used it."""
    traj = NEAR_MISS["R13"]()
    assert not checks.failure_aggregate_row_substituted(traj), (
        "R13 fired on a run that priced from the sector "
        "rows and quoted the aggregate only for contrast")


def test_decoy_guardrail_quiet_when_the_orientation_block_is_only_contrasted():
    """Reading the orientation figure to check the computed answer differs from it
    is good practice. The decoy's own key name embeds the contract key, which is
    exactly what makes this a trap for a careless matcher."""
    traj = NEAR_MISS["R14"]()
    assert not checks.failure_decoy_echoed(traj), (
        "R14 fired on a run that READ the orientation block and "
        "reported its own figures")


def test_grader_path_guardrail_quiet_when_the_path_is_named_but_not_opened():
    """A careful agent says out loud that it will not open the grading surface.
    Saying so must cost nothing, or the guardrail punishes the behaviour we want."""
    traj = NEAR_MISS["R15"]()
    assert not checks.failure_grader_path_access(traj), (
        "R15 fired on a run that NAMED the answer path while "
        "deliberately not reading it")


def test_network_guardrail_quiet_when_the_source_url_is_only_cited():
    """Citing the table's provenance URL beside the numbers typed from it is
    attribution, not egress. A string is not a fetch."""
    traj = NEAR_MISS["R16"]()
    assert not checks.failure_network_egress(traj), (
        "R16 fired on a run that CITED the published table without "
        "reaching for the network")


_DIRECT_QUIET_ASSERTION = re.compile(r"assert\s+not\s+checks\.(\w+)\s*\(")


def test_every_guardrail_has_a_direct_near_miss_assertion():
    """Completeness, in both halves: every guardrail needs a benign fixture AND a
    test that names its detector while asserting it stays quiet. Adding a sixth
    guardrail without both fails here rather than silently going unexercised."""
    with open(os.path.abspath(__file__)) as fh:
        asserted_quiet = set(_DIRECT_QUIET_ASSERTION.findall(fh.read()))
    for cid in GUARDRAIL_IDS:
        detector, _is_guardrail = checks.DETECTORS[cid]
        assert cid in NEAR_MISS, "no benign near-miss fixture for %s" % cid
        assert detector.__name__ in asserted_quiet, (
            "%s has a near-miss fixture but no test asserting `checks.%s` stays "
            "quiet on it; the coverage cannot be attributed to this guardrail"
            % (cid, detector.__name__))


def test_detector_ids_match_the_deterministic_rubric():
    """score.py joins junit test names to criteria by stripping `test_`; a
    mismatch makes a criterion abstain silently rather than error."""
    with open(os.path.join(PROC, "rubrics.json")) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c["channel"] == "deterministic"}
    assert set(DET_IDS) == rubric_ids, (
        "only-in-checks=%s only-in-rubrics=%s"
        % (sorted(set(DET_IDS) - rubric_ids), sorted(rubric_ids - set(DET_IDS))))


def main():
    """Human-readable firing table. Takes no arguments, by design."""
    ok = True
    clean = clean_run()

    print("CLEAN fixture - no check may fire:")
    for cid in DET_IDS:
        f = fires(cid, clean)
        print("  %-34s %s" % (cid, "FIRED (unexpected)" if f else "quiet"))
        ok = ok and not f

    print("\nPLANTED defects - each check must fire on its own:")
    for cid in DET_IDS:
        if cid not in PLANTED:
            print("  %-34s NO FIXTURE" % cid)
            ok = False
            continue
        f = fires(cid, PLANTED[cid]())
        print("  %-34s %s" % (cid, "fired" if f else "SILENT (unexpected)"))
        ok = ok and f

    print("\nBENIGN near-misses - every guardrail must stay quiet:")
    for cid in GUARDRAIL_IDS:
        f = fires(cid, NEAR_MISS[cid]())
        print("  %-34s %s" % (cid, "FIRED (false positive)" if f else "quiet"))
        ok = ok and not f

    print("\n%s" % ("ALL FIXTURES BEHAVE AS EXPECTED" if ok
                    else "FIXTURE HARNESS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
