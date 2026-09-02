#!/bin/bash
# Reference solution: ISDA-2006 day-count year fractions + accrued interest (DAY1-H).
# Pure standard-library Python; NO QuantLib, NO finance library, NO network.
# Hand-implements the ISDA 4.16 rules (incl. ACT/ACT ISDA leap-day-splitting and
# ACT/ACT ICMA period denominator) and reproduces the QuantLib-baked golden
# (verifier/expected_values.json) to within 1e-10 / 1e-8.
set -e
python3 << 'PY'
import json
import datetime as dt
from pathlib import Path

D = lambda s: dt.date.fromisoformat(s)
data = json.loads(Path("/root/data/instruments.json").read_text())


def is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def last_of_feb(d):
    return d.month == 2 and (d + dt.timedelta(days=1)).month == 3


def yf_30_360_us(d1, d2):
    day1, day2 = d1.day, d2.day
    if last_of_feb(d1) and last_of_feb(d2):
        day2 = 30
    if last_of_feb(d1):
        day1 = 30
    if day2 == 31 and day1 >= 30:
        day2 = 30
    if day1 == 31:
        day1 = 30
    days = 360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (day2 - day1)
    return days / 360.0


def yf_30e_360(d1, d2):
    day1 = 30 if d1.day == 31 else d1.day
    day2 = 30 if d2.day == 31 else d2.day
    days = 360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (day2 - day1)
    return days / 360.0


def yf_act_360(d1, d2):
    return (d2 - d1).days / 360.0


def yf_act_365f(d1, d2):
    return (d2 - d1).days / 365.0


def yf_actact_isda(d1, d2):
    if d1 == d2:
        return 0.0
    y1, y2 = d1.year, d2.year
    if y1 == y2:
        return (d2 - d1).days / (366.0 if is_leap(y1) else 365.0)
    frac = (dt.date(y1 + 1, 1, 1) - d1).days / (366.0 if is_leap(y1) else 365.0)
    frac += (y2 - y1 - 1)
    frac += (d2 - dt.date(y2, 1, 1)).days / (366.0 if is_leap(y2) else 365.0)
    return frac


def yf_actact_icma(d1, d2, rs, re, freq):
    return (d2 - d1).days / (freq * (re - rs).days)


results = {}
for inst in data["instruments"]:
    d1, d2 = D(inst["start_date"]), D(inst["end_date"])
    basis = inst["day_count_basis"]
    if basis == "30/360 US":
        yf = yf_30_360_us(d1, d2)
    elif basis == "30E/360":
        yf = yf_30e_360(d1, d2)
    elif basis == "ACT/360":
        yf = yf_act_360(d1, d2)
    elif basis == "ACT/365F":
        yf = yf_act_365f(d1, d2)
    elif basis == "ACT/ACT ISDA":
        yf = yf_actact_isda(d1, d2)
    elif basis == "ACT/ACT ICMA":
        yf = yf_actact_icma(d1, d2, D(inst["reference_period_start"]),
                            D(inst["reference_period_end"]), inst["coupon_frequency"])
    else:
        raise ValueError(basis)
    acc = inst["notional"] * inst["annual_coupon_rate"] * yf
    results[inst["id"]] = {"year_fraction": yf, "accrued_interest": acc}

Path("/root/results.json").write_text(json.dumps({"results": results}, indent=2) + "\n")
print("wrote /root/results.json with", len(results), "instruments")
PY
