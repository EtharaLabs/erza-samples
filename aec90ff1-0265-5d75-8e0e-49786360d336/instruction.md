Task:
A fixed-income desk needs day-count year fractions and accrued interest computed
for eleven accrual periods, each under a named market day-count convention. Read
the worksheet at `/root/data/instruments.json` and, for every instrument, compute:

1. `year_fraction` - the day-count fraction of the accrual period
   `[start_date, end_date)` under that instrument's `day_count_basis`, following
   the **ISDA 2006 Definitions, Section 4.16**; and
2. `accrued_interest` = `notional * annual_coupon_rate * year_fraction`.

Report `year_fraction` accurate to `<= 1e-10` and `accrued_interest` to `<= 1e-8`.

## Conventions in scope

Each instrument's `day_count_basis` is one of the following six ISDA 2006 day-count
fractions, identified by its standard market name. Apply each convention exactly as
defined by ISDA 2006 Section 4.16; the definitions are not restated here.

- `30/360 US` (30/360, Bond Basis)
- `30E/360` (Eurobond basis)
- `ACT/360`
- `ACT/365F` (Actual/365 Fixed)
- `ACT/ACT ISDA` (Actual/Actual, ISDA)
- `ACT/ACT ICMA` (Actual/Actual, ICMA)

The three `ACT/ACT`-family and `ACT/365F` conventions are distinct and generally
produce different fractions for the same dates; the two `30/360` variants likewise
differ on some month-ends. For `ACT/ACT ICMA` instruments the worksheet additionally
supplies `reference_period_start`, `reference_period_end`, and `coupon_frequency`
(coupons per year), and each accrual period lies within its stated reference period.

## Forbidden

Do **not** use QuantLib, `python-dateutil` day-count helpers, `pandas` offset/
day-count utilities, `isda`/`financepy`/`quantlib`-style packages, or any other
finance or day-count library. Implement every convention by hand with the standard
library only. The runtime image has no such library and no network; a conforming
solution needs neither.

## Output

Write `/root/results.json` with a single `results` object keyed by instrument id:

```json
{
  "results": {
    "<instrument_id>": {"year_fraction": 0.1234567890, "accrued_interest": 987.65}
  }
}
```

Every instrument id in `instruments.json` must appear exactly once. The `<...>`
key and the numbers above illustrate the JSON shape only; they are placeholders,
not the answer for any instrument.
