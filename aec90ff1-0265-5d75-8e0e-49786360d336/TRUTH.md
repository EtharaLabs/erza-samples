# TRUTH.md — ISDA-2006 day-count & accrued-interest (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it evaluates
to**. Derived from `oracle/solve.sh` (the reference solution) with every value
stripped out — it describes the *method*, never a year fraction, an accrued
figure, or an instrument's dates.

**How to read this file.** It is method, not arithmetic. A reader who follows every
step faithfully lands on the oracle's answer; a reader who has the rules can still
get the wrong number by reading the calendar carelessly, which is the point.

---

## Step 0 — Read the worksheet

**Do:** Open `/root/data/instruments.json` and read the `instruments` array. Note
the fields carried by every row (`id`, `day_count_basis`, `start_date`,
`end_date`, `annual_coupon_rate`, `notional`) and the three fields carried **only**
by `ACT/ACT ICMA` rows (`reference_period_start`, `reference_period_end`,
`coupon_frequency`). Note the six distinct basis names present.

**Why:** The convention to apply is data-driven — it is the `day_count_basis`
string on each row, not a global setting. Missing the ICMA-only fields means the
ICMA denominator cannot be formed at all.

**Do not:** Assume every row has the same fields, or hard-code an instrument list.

## Step 1 — Plan the whole chain before writing code

**Do:** Name the shape end to end: for each instrument, dispatch on
`day_count_basis`, compute the year fraction under *that* convention's ISDA-2006
Section 4.16 rule, form the accrued interest, then emit the output contract.
Work with the **standard library only** — QuantLib and every finance / day-count
package (`financepy`, `isda`, `python-dateutil` day-count helpers, `pandas`
offset utilities) are absent from the runtime image, forbidden by the task, and
unnecessary: the six rules are recalled and hand-implemented.

**Why:** The task is built to measure recall of the six conventions. Reaching for
a library both fails at runtime (none is installed) and sidesteps the thing being
measured.

**Do not:** Write a single formula and hope it covers every basis — the six rules
genuinely disagree.

## Step 2 — Fix the accrued-interest relation

**Do:** For every instrument, `accrued_interest = notional × annual_coupon_rate ×
year_fraction`. It is the same relation for all six conventions; only the year
fraction changes.

**Why:** Accrued interest is a graded value in its own right at a tight tolerance.
Its only moving part is the year fraction, so an error in the day count propagates
straight into it.

**Do not:** Rescale the coupon by anything (no /100, no period proration) — the
rate and notional are used as given.

## Step 3 — 30/360 US (Bond Basis): the end-of-month cascade

**Do:** Adjust the two day-of-month numbers in this **order**, then combine:
(1) if *both* endpoints are the last day of February, set the end day to 30;
(2) if the *start* is the last day of February, set the start day to 30;
(3) if the end day is 31 and the (possibly adjusted) start day is ≥ 30, set the
end day to 30; (4) if the start day is 31, set it to 30. Combine as
`(360·Δyears + 30·Δmonths + (endDay − startDay)) / 360`.

**Why:** The order is load-bearing — the February rule feeds the 31→30 rule, and a
different order changes month-end stubs. A wrong version still returns a plausible
fraction and passes casual inspection.

**Do not:** Drop the February special-casing — dropping it *is* the 30E/360 rule,
which the oracle scores as wrong for a 30/360-US instrument.

## Step 4 — 30E/360 (Eurobond): unconditional 31→30

**Do:** Map day 31 to 30 on **both** endpoints unconditionally, with **no**
February special case, then combine with the same
`(360·Δyears + 30·Δmonths + (endDay − startDay)) / 360`.

**Why:** 30E/360 diverges from 30/360 US precisely on 31st and end-of-February
stubs. Applying either variant's rule to the other's instruments lands outside
tolerance.

**Do not:** Carry the February rule over from Step 3 — that would collapse the two
30/360 variants into one.

## Step 5 — ACT/360 and ACT/365F: keep the fixed denominators apart

**Do:** Take the actual calendar days between start and end, and divide by a fixed
**360** for `ACT/360` and a fixed **365** for `ACT/365F`.

**Why:** These two are identical except for the denominator. A /360-for-/365 (or
reverse) swap is a one-character error that misses tolerance.

**Do not:** Use a leap-aware or period-aware denominator here — both are fixed.

## Step 6 — ACT/ACT ISDA: split by leap-year membership  ·  CRUX

**Do:** Split the actual days by the calendar year they fall in. Days lying in a
leap year are divided by 366; days lying in a non-leap year are divided by 365;
sum the contributions across the partial start-year segment, any whole intervening
years, and the partial end-year segment.

**Why:** *Everything before this is bookkeeping; this is one of the two steps the
task exists to measure.* Two wrong routes both read as "an Actual/Actual" and pass
every cheap check: collapsing to actual-days/365 (that is ACT/365F, Step 5), and
dividing total days by a single calendar-year denominator. Both miss the tolerance
by orders of magnitude on periods that straddle a year or leap boundary.

**Do not:** Divide the total actual days by 365, or by one year's denominator.

## Step 7 — ACT/ACT ICMA: the period denominator  ·  CRUX

**Do:** Form the denominator as `coupon_frequency × (days in the reference coupon
period [reference_period_start, reference_period_end))`, and the numerator as the
actual days in the accrual period `[start_date, end_date)`; the year fraction is
their ratio.

**Why:** *This is the second load-bearing step.* ICMA is period-based, not
calendar-based: the denominator comes from the supplied reference period and
frequency, never from 365 or 366. Reusing a calendar-year denominator here is the
single most common ICMA error, and short (quarterly) versus long (semiannual)
periods make the gap large.

**Do not:** Substitute 365/366, and do not confuse this with the ISDA rule of
Step 6 — same family name, different denominator entirely.

## Step 8 — Assemble and emit the output contract

**Do:** Write `/root/results.json` as `{"results": {<instrument_id>:
{"year_fraction": …, "accrued_interest": …}}}`, with every id from the worksheet
present exactly once and both fields on each.

**Why:** The outcome verifier keys on the ids and reads both fields; a missing id
or a malformed shape fails before any tolerance check runs.

**Do not:** Add, drop, rename, or duplicate ids; do not nest the two values under
a different shape.

## Step 9 — Verify without the forbidden library

**Do:** Sanity-check against something that can actually disagree. The table below
separates checks that discriminate from checks that cannot.

| Check | Discriminates a wrong convention? |
|---|---|
| Every id present; fractions finite and in a sane range | No — a wrong convention still yields finite, in-range fractions |
| Re-run your own solver and get the same numbers | No — it faithfully reproduces its own convention error |
| Recompute one day count by hand from the calendar and compare | Yes |
| Two *different* bases on the *same* dates give *different* fractions | Yes — a single uniform denominator makes them collide |
| A leap/year-straddling ISDA period differs from its actual-days/365 value | Yes — catches ISDA collapsed to ACT/365F |
| An ICMA fraction changes when the reference period / frequency changes | Yes — catches a calendar-year denominator |

**Why:** The failure pattern is a wrong convention that maps every date correctly,
produces in-range values, and round-trips through its own inverse. The run's
*confidence* is not evidence; only a check that could disagree is.

**Do not:** Claim verification on the strength of re-running the same code, or of
"the numbers look reasonable".

---

## What a finished run must have produced

- `/root/results.json` exists and parses, shaped `{"results": {id: {year_fraction,
  accrued_interest}}}`.
- Every instrument id from `instruments.json` appears exactly once; no extras.
- Each year fraction was produced by the convention named on its row — the six
  rules applied *differentially*, not one formula for all.
- Each accrued interest equals `notional × annual_coupon_rate × year_fraction`.
- The inputs under `/root/data` were read, not modified.

The numeric ground truth lives in `verifier/expected_values.json` (the QuantLib-
baked golden ledger) and is **not reproduced here**. This document specifies the
path to it, not the values on it.
