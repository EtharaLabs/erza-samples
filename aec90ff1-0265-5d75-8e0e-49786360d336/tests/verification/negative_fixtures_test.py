"""Negative fixtures: a synthetic run for every deterministic criterion, each SEEN
to fire; plus a correct run proving the positives stay green and the guardrails
stay quiet (Stage-7 false-negative AND guardrail-specificity checks).

A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail. This file exercises both halves.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser + detector - runs,
not just the regex.

    python3 verification/negative_fixtures_test.py     # human-readable firing table
    python3 -m pytest verification/negative_fixtures_test.py -q
"""
import atexit
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PROC, "lib"))
import trajectory as T  # noqa: E402
import checks  # noqa: E402

_TMP: list[str] = []


def _mk(file_writes=(), commands=(), prose=""):
    """Build a synthetic run dir and load it into a normalised Trajectory."""
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
    d = tempfile.mkdtemp(prefix="ndc-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as f:
        f.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


# A correct, convention-dispatching solver: every positive detector should pass on
# this and every guardrail should stay quiet.
CORRECT_SOLVER = """
import json, datetime as dt
from pathlib import Path
D = lambda s: dt.date.fromisoformat(s)
data = json.loads(Path("/root/data/instruments.json").read_text())

def is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

def last_of_feb(d):
    return d.month == 2 and (d + dt.timedelta(days=1)).month == 3

def yf_30_360_us(d1, d2):
    a, b = d1.day, d2.day
    if last_of_feb(d1) and last_of_feb(d2): b = 30
    if last_of_feb(d1): a = 30
    if b == 31 and a >= 30: b = 30
    if a == 31: a = 30
    return (360*(d2.year-d1.year)+30*(d2.month-d1.month)+(b-a))/360.0

def yf_30e_360(d1, d2):
    a = 30 if d1.day == 31 else d1.day
    b = 30 if d2.day == 31 else d2.day
    return (360*(d2.year-d1.year)+30*(d2.month-d1.month)+(b-a))/360.0

def yf_actact_isda(d1, d2):
    y1, y2 = d1.year, d2.year
    if y1 == y2:
        return (d2-d1).days / (366.0 if is_leap(y1) else 365.0)
    f = (dt.date(y1+1,1,1)-d1).days / (366.0 if is_leap(y1) else 365.0)
    f += (y2-y1-1)
    f += (d2-dt.date(y2,1,1)).days / (366.0 if is_leap(y2) else 365.0)
    return f

out = {}
for inst in data["instruments"]:
    d1, d2 = D(inst["start_date"]), D(inst["end_date"])
    basis = inst["day_count_basis"]
    if basis == "30/360 US":
        yf = yf_30_360_us(d1, d2)
    elif basis == "30E/360":
        yf = yf_30e_360(d1, d2)
    elif basis == "ACT/360":
        yf = (d2-d1).days / 360.0
    elif basis == "ACT/365F":
        yf = (d2-d1).days / 365.0
    elif basis == "ACT/ACT ISDA":
        yf = yf_actact_isda(d1, d2)
    elif basis == "ACT/ACT ICMA":
        rs, re = D(inst["reference_period_start"]), D(inst["reference_period_end"])
        yf = (d2-d1).days / (inst["coupon_frequency"] * (re-rs).days)
    accrued_interest = inst["notional"] * inst["annual_coupon_rate"] * yf
    out[inst["id"]] = {"year_fraction": yf, "accrued_interest": accrued_interest}
Path("/root/results.json").write_text(json.dumps({"results": out}))
"""


def correct_run():
    return _mk(file_writes=[("solver.py", CORRECT_SOLVER)],
               commands=["python3 solver.py"],
               prose="Dispatch on day_count_basis; each ISDA 4.16 rule by hand.")


# ---- one negative fixture per positive deterministic criterion ----
NEGATIVE = {
    "R3": lambda: _mk(
        file_writes=[("solver.py", "yf = (d2 - d1).days / 365.0\nprint(yf)")],
        commands=["python3 solver.py"]),
    "R4": lambda: _mk(
        file_writes=[("notes.md", "plan: eyeball the day counts and type numbers")],
        commands=["cat /root/data/instruments.json"]),
    "R5": lambda: _mk(
        file_writes=[("solver.py", CORRECT_SOLVER)],
        commands=["cat /root/data/instruments.json"]),
    "R6": lambda: _mk(
        file_writes=[("solver.py",
                      "for i in data['instruments']:\n"
                      "    year_fraction = (D(i['end_date'])-D(i['start_date'])).days/360.0\n"
                      "    out[i['id']] = {'year_fraction': year_fraction}")],
        commands=["python3 solver.py"]),
    "R7": lambda: _mk(
        file_writes=[("solver.py",
                      'if basis == "30/360 US":\n'
                      "    yf = (360*(d2.year-d1.year)+30*(d2.month-d1.month)+(d2.day-d1.day))/360.0")],
        commands=["python3 solver.py"]),
    "R8": lambda: _mk(
        file_writes=[("solver.py",
                      'if basis == "30/360 US":\n'
                      "    a, b = d1.day, d2.day\n"
                      "    if b == 31 and a >= 30: b = 30\n"
                      "    if a == 31: a = 30\n"
                      "    if d1.month == 2: a = 30\n"
                      "    yf = (360*(d2.year-d1.year)+30*(d2.month-d1.month)+(b-a))/360.0")],
        commands=["python3 solver.py"]),
    "R9": lambda: _mk(
        file_writes=[("solver.py",
                      'if basis == "ACT/360":\n'
                      "    yf = (d2-d1).days/360.0\n"
                      'if basis == "ACT/365F":\n'
                      "    yf = (d2-d1).days/360.0")],
        commands=["python3 solver.py"]),
    "R10": lambda: _mk(
        file_writes=[("solver.py",
                      'if basis == "ACT/ACT ISDA":\n'
                      "    yf = (d2-d1).days/365.0")],
        commands=["python3 solver.py"]),
    "R11": lambda: _mk(
        file_writes=[("solver.py",
                      'if basis == "ACT/ACT ICMA":\n'
                      "    yf = (d2-d1).days/365.0")],
        commands=["python3 solver.py"]),
    "R12": lambda: _mk(
        file_writes=[("solver.py",
                      "open('/root/out.txt','w').write(str(yf))")],
        commands=["python3 solver.py"]),
}

# ---- one failure fixture per guardrail (the failure mode DID occur) ----
GUARDRAIL_FAIL = {
    "R13": lambda: _mk(
        file_writes=[("solver.py",
                      "for i in data['instruments']:\n"
                      "    out[i['id']] = (D(i['end_date'])-D(i['start_date'])).days/365.0")],
        commands=["python3 solver.py"]),
    "R14": lambda: _mk(
        file_writes=[("solver.py",
                      "import QuantLib as ql\n"
                      "yf = ql.Actual360().yearFraction(a, b)")],
        commands=["python3 solver.py"]),
}


@pytest.mark.parametrize("cid", list(NEGATIVE))
def test_positive_detector_fires_on_negative_fixture(cid):
    traj = NEGATIVE[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is False, \
        f"{cid}: detector did NOT fire on its negative fixture (false negative)"


@pytest.mark.parametrize("cid", list(GUARDRAIL_FAIL))
def test_guardrail_fires_on_failure_fixture(cid):
    traj = GUARDRAIL_FAIL[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is True, \
        f"{cid}: guardrail did NOT detect the failure mode it names"


def test_correct_run_positives_all_quiet():
    traj = correct_run()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if not is_guard:
            assert det(traj) is True, f"{cid}: false negative on a fully correct run"


def test_guardrails_quiet_on_correct_run():
    traj = correct_run()
    assert checks.failure_uniform_naive(traj) is False, \
        "uniform-naive guardrail fired on a correct convention-dispatching run"
    assert checks.failure_forbidden_library(traj) is False, \
        "forbidden-library guardrail fired on a stdlib-only run"


def test_forbidden_library_near_miss_stays_quiet():
    # merely NAMING QuantLib in prose while importing nothing forbidden is innocent
    traj = _mk(file_writes=[("solver.py", CORRECT_SOLVER)],
               commands=["python3 solver.py"],
               prose="We deliberately avoid QuantLib and hand-implement ISDA 4.16.")
    assert checks.failure_forbidden_library(traj) is False


# A table-driven solver that reaches the right answer through ONE expression,
# `(d2-d1).days / DENOM[basis]`. This is the near-miss for the uniform-naive
# guardrail: it has the exact surface shape the guardrail is looking for -- a
# single division applied to every instrument, no per-basis branches -- while
# being correct, because the dispatch has moved into the lookup table. A
# guardrail that fires here is punishing style, not error, and would score a
# competent run as a naive one.
TABLE_DISPATCH_SOLVER = """
import json, datetime as dt
from pathlib import Path
D = lambda s: dt.date.fromisoformat(s)
data = json.loads(Path("/root/data/instruments.json").read_text())

# Actual/N conventions differ only in the denominator, so the dispatch is data.
DENOM = {"ACT/360": 360.0, "ACT/365F": 365.0}

out = {}
for inst in data["instruments"]:
    d1, d2 = D(inst["start_date"]), D(inst["end_date"])
    basis = inst["day_count_basis"]
    yf = (d2 - d1).days / DENOM[basis]
    out[inst["id"]] = {"year_fraction": yf,
                       "accrued_interest": inst["notional"] * inst["annual_coupon_rate"] * yf}
Path("/root/results.json").write_text(json.dumps({"results": out}))
"""


def test_uniform_naive_near_miss_stays_quiet():
    """A correct table-driven dispatch must not read as 'one uniform formula'.

    This is the half of the guardrail contract that was never exercised. The
    suite proved `R13` FIRES on a genuinely naive run; nothing
    proved it stays QUIET on a run that merely looks naive. Without this, a
    guardrail that returned True unconditionally would have passed every test
    in the file while silently subtracting 3 points from correct work.
    """
    traj = _mk(file_writes=[("solver.py", TABLE_DISPATCH_SOLVER)],
               commands=["python3 solver.py"],
               prose="ACT/360 and ACT/365F differ only in the denominator; "
                     "dispatch through a table rather than branches.")
    assert checks.failure_uniform_naive(traj) is False, \
        "uniform-naive guardrail fired on a correct table-dispatching solver"


def main():
    print("negative fixtures - every deterministic criterion SEEN to fire:\n")
    ok = True
    for cid in NEGATIVE:
        fired = checks.DETECTORS[cid][0](NEGATIVE[cid]()) is False
        ok &= fired
        print(f"  {cid:<28} test FIRES on its negative fixture   {'OK' if fired else 'MISS'}")
    for cid in GUARDRAIL_FAIL:
        fired = checks.DETECTORS[cid][0](GUARDRAIL_FAIL[cid]()) is True
        ok &= fired
        print(f"  {cid:<28} guardrail DETECTS the failure mode   {'OK' if fired else 'MISS'}")
    print("\ncorrect run - positives green, guardrails quiet:")
    traj = correct_run()
    pos_ok = all(det(traj) for cid, (det, g) in checks.DETECTORS.items() if not g)
    guard_quiet = (not checks.failure_uniform_naive(traj)) and (not checks.failure_forbidden_library(traj))
    ok &= pos_ok and guard_quiet
    print(f"  positives all satisfied on correct run             {'OK' if pos_ok else 'MISS'}")
    print(f"  guardrails stay quiet on correct run               {'OK' if guard_quiet else 'MISS'}")
    print(f"\nALL FIXTURES BEHAVE AS SPECIFIED : {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
