#!/usr/bin/env python3
"""PRIVATE deterministic data generator for the DAY1-H day-count / accrued-interest task.

BUILD-TIME ASYMMETRY (legitimate): this generator uses QuantLib -- the authoritative
day-count library -- to compute the reference year-fractions and accrued interest, and
bakes them into the hidden golden ledger (verifier/expected_values.json) plus the
agent-visible input (environment/data/instruments.json). The RUNTIME image
(environment/Dockerfile) is python:3.11-slim with NO QuantLib and NO network, and the
task.md FORBIDS QuantLib / any finance library, so the agent must RECALL and hand-
implement the ISDA-2006 day-count rules where the convention gap bites.

HARDENING over DAY1 (dfed29e0): the task prompt now only NAMES the six ISDA-2006 bases;
the EOM/31->30 cascade, the ACT/ACT-ISDA leap-day-splitting rule (4.16(b)), and the
ACT/ACT-ICMA period-denominator formula (4.16(c)) are NOT spelled out in task.md and
must be recalled. The instrument set is adversarial: ACT/ACT-ISDA (easily confused with
ACT/ACT-ICMA and with ACT/365F), Feb-29 and 31st end-of-month stubs, short (quarterly)
vs long (semiannual) ICMA coupon periods, and accrual periods straddling year AND leap
boundaries.

There is NO randomness: the instrument set is fixed and curated, so regeneration is
byte-identical by construction.

Refs: ISDA 2006 Definitions, Section 4.16 Day Count Fractions:
  (b) ACT/ACT (ISDA), (c) ACT/ACT (ICMA), (d) ACT/360, (e) ACT/365 (Fixed),
  (f) 30/360 (Bond Basis), (g) 30E/360 (Eurobond). QuantLib day-counters:
  Thirty360(USA/European), Actual360, Actual365Fixed, ActualActual(ISDA / ISMA).

Run (build host, QuantLib installed):  python3 oracle/generate.py
"""
import datetime as dt
import json
from pathlib import Path

import QuantLib as ql

# Pinned so the instance and its golden ledger regenerate byte-identically.
# The generator is build-time only; it never runs inside the container.
SEED = 20260727

YF_TOL = 1e-10      # year-fraction absolute tolerance (verifier)
ACC_TOL = 1e-8      # accrued-interest absolute tolerance (verifier)


def D(s):
    return dt.date.fromisoformat(s)


# ---- fixed, curated instrument set (no RNG; deterministic by construction) ----
INSTRUMENTS = [
    # 30/360 US (Bond Basis) - Feb-EOM + 31->30 ordered cascade; leap Feb29, 31st stubs
    dict(id="INST01", basis="30/360 US", start="2020-02-29", end="2020-08-31",
         coupon=0.05, notional=1_000_000.0),
    dict(id="INST02", basis="30/360 US", start="2019-08-31", end="2020-02-29",
         coupon=0.045, notional=2_000_000.0),
    dict(id="INST03", basis="30/360 US", start="2021-01-31", end="2021-04-30",
         coupon=0.06, notional=500_000.0),
    # 30E/360 (Eurobond) - unconditional 31->30, NO Feb rule (diverges from 30/360 US)
    dict(id="INST04", basis="30E/360", start="2021-02-28", end="2021-08-31",
         coupon=0.04, notional=3_000_000.0),
    dict(id="INST05", basis="30E/360", start="2020-01-31", end="2020-07-31",
         coupon=0.05, notional=750_000.0),
    # ACT/360, ACT/365F
    dict(id="INST06", basis="ACT/360", start="2019-12-15", end="2020-06-15",
         coupon=0.055, notional=1_250_000.0),
    dict(id="INST07", basis="ACT/365F", start="2020-01-15", end="2021-01-15",
         coupon=0.05, notional=1_000_000.0),
    # ACT/ACT ISDA - leap-day-splitting; straddle year AND leap boundaries
    dict(id="INST08", basis="ACT/ACT ISDA", start="2019-11-01", end="2020-05-01",
         coupon=0.04, notional=2_500_000.0),
    dict(id="INST09", basis="ACT/ACT ISDA", start="2020-11-15", end="2021-02-15",
         coupon=0.035, notional=1_500_000.0),
    # ACT/ACT ICMA - short (quarterly) vs long (semiannual) coupon periods
    dict(id="INST10", basis="ACT/ACT ICMA", start="2019-11-30", end="2020-01-31",
         ref_start="2019-08-15", ref_end="2020-02-15", frequency=2,
         coupon=0.03, notional=800_000.0),
    dict(id="INST11", basis="ACT/ACT ICMA", start="2020-06-10", end="2020-07-20",
         ref_start="2020-05-15", ref_end="2020-08-15", frequency=4,
         coupon=0.045, notional=2_200_000.0),
]


# --------------------------- QuantLib oracle (authoritative) ---------------------------
def _qld(d):
    return ql.Date(d.day, d.month, d.year)


def oracle_yf(inst):
    a, b = _qld(D(inst["start"])), _qld(D(inst["end"]))
    basis = inst["basis"]
    if basis == "30/360 US":
        return ql.Thirty360(ql.Thirty360.USA).yearFraction(a, b)
    if basis == "30E/360":
        return ql.Thirty360(ql.Thirty360.European).yearFraction(a, b)
    if basis == "ACT/360":
        return ql.Actual360().yearFraction(a, b)
    if basis == "ACT/365F":
        return ql.Actual365Fixed().yearFraction(a, b)
    if basis == "ACT/ACT ISDA":
        return ql.ActualActual(ql.ActualActual.ISDA).yearFraction(a, b)
    if basis == "ACT/ACT ICMA":
        aa = ql.ActualActual(ql.ActualActual.ISMA)
        return aa.yearFraction(a, b, _qld(D(inst["ref_start"])), _qld(D(inst["ref_end"])))
    raise ValueError(basis)


# --------------------------- plausible-default controls (gap ledger) -------------------
def _is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def naive_days_over_365(inst):
    return (D(inst["end"]) - D(inst["start"])).days / 365.0


def naive_30_360_no_special(inst):
    a, b = D(inst["start"]), D(inst["end"])
    days = 360 * (b.year - a.year) + 30 * (b.month - a.month) + (b.day - a.day)
    return days / 360.0


def naive_actact_calendar(inst):
    a, b = D(inst["start"]), D(inst["end"])
    denom = 366.0 if _is_leap(a.year) else 365.0
    return (b - a).days / denom


def naive_isda_as_365f(inst):
    return (D(inst["end"]) - D(inst["start"])).days / 365.0


def naive_360_for_365(inst):
    return (D(inst["end"]) - D(inst["start"])).days / 360.0


def main():
    here = Path(__file__).resolve().parent.parent
    data_dir = here / "environment" / "data"
    ver_dir = here / "verifier"
    data_dir.mkdir(parents=True, exist_ok=True)
    ver_dir.mkdir(parents=True, exist_ok=True)

    golden = {}
    for inst in INSTRUMENTS:
        yf = float(oracle_yf(inst))
        acc = inst["notional"] * inst["coupon"] * yf
        golden[inst["id"]] = {"year_fraction": yf, "accrued_interest": acc}

    # ---- agent-visible input: instruments.json (NO answers, NO rule disclosure) ----
    pub_instruments = []
    for inst in INSTRUMENTS:
        row = {
            "id": inst["id"],
            "day_count_basis": inst["basis"],
            "start_date": inst["start"],
            "end_date": inst["end"],
            "annual_coupon_rate": inst["coupon"],
            "notional": inst["notional"],
        }
        if inst["basis"] == "ACT/ACT ICMA":
            row["reference_period_start"] = inst["ref_start"]
            row["reference_period_end"] = inst["ref_end"]
            row["coupon_frequency"] = inst["frequency"]
        pub_instruments.append(row)

    instruments_doc = {
        "description": (
            "Fixed-income day-count and accrued-interest worksheet. For each instrument "
            "compute the year fraction of the accrual period [start_date, end_date) under "
            "its stated day_count_basis per the ISDA 2006 Definitions, and the accrued "
            "interest accrued = notional * annual_coupon_rate * year_fraction."
        ),
        "day_count_bases_present": [
            "30/360 US", "30E/360", "ACT/360", "ACT/365F", "ACT/ACT ISDA", "ACT/ACT ICMA",
        ],
        "accrued_formula": "accrued_interest = notional * annual_coupon_rate * year_fraction",
        "instruments": pub_instruments,
        "output_path": "/root/results.json",
        "output_contract": {
            "shape": {"results": {"<instrument_id>": {"year_fraction": "float", "accrued_interest": "float"}}},
            "year_fraction": "the day-count year fraction for [start_date, end_date) under the stated basis",
            "accrued_interest": "notional * annual_coupon_rate * year_fraction, in currency units",
            "precision_target": "year_fraction to <=1e-10, accrued_interest to <=1e-8",
        },
    }
    (data_dir / "instruments.json").write_text(json.dumps(instruments_doc, indent=2) + "\n")

    # ---- hidden golden + control ledger: expected_values.json ----
    def control_gap(fn, applies):
        worst, worst_id = 0.0, None
        for inst in INSTRUMENTS:
            if inst["basis"] not in applies:
                continue
            ref = golden[inst["id"]]["year_fraction"]
            d = abs(ref - fn(inst))
            if d > worst:
                worst, worst_id = d, inst["id"]
        return {"worst_abs_yf_gap": round(worst, 10),
                "worst_abs_yf_gap_over_tol": round(worst / YF_TOL, 2),
                "on_instrument": worst_id}

    expected = {
        "tolerance_year_fraction_abs": YF_TOL,
        "tolerance_accrued_interest_abs": ACC_TOL,
        "reference_library": f"QuantLib {ql.__version__} (build-time oracle; forbidden at runtime)",
        "golden": golden,
        "control_gaps": {
            "naive_days_over_365": control_gap(
                naive_days_over_365, {"30/360 US", "30E/360", "ACT/360", "ACT/ACT ISDA", "ACT/ACT ICMA"}),
            "naive_30_360_no_eom_rules": control_gap(
                naive_30_360_no_special, {"30/360 US"}),
            "naive_actact_calendar_denom": control_gap(
                naive_actact_calendar, {"ACT/ACT ISDA", "ACT/ACT ICMA"}),
            "naive_isda_as_365f": control_gap(
                naive_isda_as_365f, {"ACT/ACT ISDA"}),
            "naive_360_for_365_mixup": control_gap(
                naive_360_for_365, {"ACT/365F"}),
        },
        "method": (
            "ISDA 2006 Sec 4.16 day-count fractions: 30/360 US Bond Basis (Feb-EOM + "
            "31->30 ordered cascade), 30E/360 (unconditional 31->30), ACT/360, ACT/365 "
            "Fixed, ACT/ACT ISDA (leap-day-splitting: days in leap years over 366 plus "
            "days in non-leap years over 365), ACT/ACT ICMA (period-based denominator = "
            "frequency * days-in-reference-period); accrued = notional * "
            "annual_coupon_rate * year_fraction"
        ),
    }
    (ver_dir / "expected_values.json").write_text(json.dumps(expected, indent=2) + "\n")

    # ---- validation report to stdout ----
    print(f"QuantLib {ql.__version__}  YF_TOL={YF_TOL:.0e}  ACC_TOL={ACC_TOL:.0e}")
    for inst in INSTRUMENTS:
        g = golden[inst["id"]]
        print(f"  {inst['id']}  {inst['basis']:<13} {inst['start']}->{inst['end']}  "
              f"yf={g['year_fraction']:.12f}  accrued={g['accrued_interest']:.8f}")
    print("control gaps (worst |d_yf|, x tolerance):")
    for k, v in expected["control_gaps"].items():
        print(f"  {k:<30} {v['worst_abs_yf_gap']:.6e}  ({v['worst_abs_yf_gap_over_tol']:.1f}x)  on {v['on_instrument']}")


if __name__ == "__main__":
    main()
