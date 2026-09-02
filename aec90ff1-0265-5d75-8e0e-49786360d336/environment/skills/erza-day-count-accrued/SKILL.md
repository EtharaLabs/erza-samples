---
name: erza-day-count-accrued
description: Compute fixed-income day-count year fractions and accrued interest under the ISDA 2006 conventions - 30/360 US (Bond Basis) with its last-day-of-February and 31->30 adjustment cascade, 30E/360 (Eurobond) unconditional 31->30, ACT/360, ACT/365 Fixed, ACT/ACT ISDA with its leap-day-splitting denominator, and ACT/ACT ICMA with its period-based denominator. Use when a task names day-count bases and asks for year fractions and accrued interest to high precision. Not for a naive days/365 approximation, a plain 30/360 without the end-of-month rules, an ACT/ACT ISDA collapsed to Actual/365 Fixed, or an ACT/ACT with a calendar-year 365/366 denominator.
license: MIT
---

# ISDA 2006 day-count fractions and accrued interest

Day-count year fractions look like trivial date arithmetic, but each convention
has an exact rule set and the differences are not negligible: on the same pair of
dates, 30/360 US, 30E/360, ACT/360, ACT/365 Fixed, ACT/ACT ISDA, and ACT/ACT ICMA
can all give different fractions. A general implementation that reaches for
`(end - start).days / 365`, or a plain 30/360 formula without the end-of-month
adjustments, or an ACT/ACT with a calendar-year denominator, is wrong by amounts
that dwarf any tight tolerance. Implement each rule literally; do not approximate
and do not import a finance library.

Accrued interest, once the year fraction is known, is uniform across conventions:

```
accrued_interest = notional * annual_coupon_rate * year_fraction
```

## The `30/360` family day formula

All 30/360-style conventions first adjust the day-of-month numbers, then apply the
same signed day count:

```
days = 360 * (Y2 - Y1) + 30 * (M2 - M1) + (day2 - day1)
year_fraction = days / 360
```

The conventions differ only in HOW `day1` and `day2` are adjusted first.

### 30/360 US (Bond Basis)

Apply these adjustments IN THIS ORDER; they cascade, so a later rule reads the
value a previous rule may have set:

1. If both `D1` and `D2` are the last day of February, set `day2 = 30`.
2. If `D1` is the last day of February, set `day1 = 30`.
3. If `day2 == 31` and `day1 >= 30`, set `day2 = 30`.
4. If `day1 == 31`, set `day1 = 30`.

Rule 3 is the reason order matters: after rule 2 has pushed a February-end `day1`
up to 30, a `day2 == 31` then collapses to 30 as well. Skipping the February
rules (a very common default) changes the count whenever a period starts on a
February month-end.

```python
def last_of_feb(d):
    return d.month == 2 and (d + timedelta(days=1)).month == 3

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
    days = 360*(d2.year-d1.year) + 30*(d2.month-d1.month) + (day2-day1)
    return days / 360
```

### 30E/360 (Eurobond)

Unconditional end-of-month-31 adjustment, and NO February rule:

```python
def yf_30e_360(d1, d2):
    day1 = 30 if d1.day == 31 else d1.day
    day2 = 30 if d2.day == 31 else d2.day
    days = 360*(d2.year-d1.year) + 30*(d2.month-d1.month) + (day2-day1)
    return days / 360
```

Because 30E/360 leaves a February 28/29 unchanged while 30/360 US rewrites it to
30, the two give different fractions for a February month-end start. Keep them
distinct even when the same dates appear under both bases.

## The actual/actual and actual/fixed conventions

Let `actual_days(a, b)` be the true calendar-day difference `(b - a).days`, with
leap days counted (Python `datetime.date` subtraction already does this).

### ACT/360

```python
year_fraction = actual_days(d1, d2) / 360
```

### ACT/365 Fixed

```python
year_fraction = actual_days(d1, d2) / 365
```

The 365 denominator is fixed even across a leap year, so a full leap-year period
exceeds 1. Do not switch to 366; that is a different convention.

### ACT/ACT ISDA

This convention splits the accrual period at calendar-year boundaries: days that
fall in a leap year are divided by 366, days that fall in a non-leap year by 365,
and the parts are summed. It is NOT `actual_days / 365` and NOT the ICMA
period-based formula; conflating ACT/ACT ISDA with either is the most common error.

```python
def is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

def yf_actact_isda(d1, d2):
    if d1 == d2:
        return 0.0
    y1, y2 = d1.year, d2.year
    if y1 == y2:
        return (d2 - d1).days / (366.0 if is_leap(y1) else 365.0)
    # partial first year: d1 .. Jan 1 of the next year
    frac = (date(y1 + 1, 1, 1) - d1).days / (366.0 if is_leap(y1) else 365.0)
    # each whole intermediate calendar year contributes exactly 1
    frac += (y2 - y1 - 1)
    # partial last year: Jan 1 of y2 .. d2
    frac += (d2 - date(y2, 1, 1)).days / (366.0 if is_leap(y2) else 365.0)
    return frac
```

A full intermediate calendar year contributes exactly 1 because its day count
equals its own denominator (365/365 or 366/366). Only the two partial end-years
carry the leap/non-leap denominator split.

### ACT/ACT ICMA

Here the denominator is a coupon-period quantity, not a calendar year. For an
accrual period lying within one regular coupon (reference) period:

```python
year_fraction = actual_days(start, end) / (frequency * actual_days(ref_start, ref_end))
```

where `frequency` is the number of coupons per year and `[ref_start, ref_end]` is
the regular coupon period that contains the accrual period. A semiannual bond has
`frequency = 2` and a roughly six-month reference period; a quarterly bond has
`frequency = 4` and a roughly three-month reference period. The denominator is
`frequency * (days in that reference period)`, close to but not equal to a
calendar year - the difference is exactly what a calendar-year denominator gets
wrong. Never substitute 365 or 366 for `frequency * days-in-reference-period`, and
never use the ISDA leap-splitting rule here.

## Sanity checks

- For 30/360 US vs 30E/360 on a February month-end start, the two fractions should
  DIFFER. If they are identical you have dropped the 30/360 US February rules.
- ACT/ACT ISDA, ACT/365 Fixed, and ACT/ACT ICMA on the same dates should generally
  DIFFER. If your ACT/ACT ISDA equals `days/365` you dropped the leap-day split; if
  it equals the ICMA number you used the wrong denominator entirely.
- An ACT/ACT ISDA period straddling a year boundary into or out of a leap year must
  blend a `/365` part and a `/366` part; a single fixed denominator is wrong.
- An ACT/ACT ICMA fraction for a sub-period of a semiannual coupon should use a
  denominator near `2 * (days in that coupon period)`, i.e. near 364, not 365/366.
- A full one-year ACT/365 Fixed period that spans a leap day gives slightly MORE
  than 1, because the numerator counts the extra actual day while the denominator
  stays fixed at 365; if it equals exactly 1 you divided by the actual day count.
- Compute year fractions as exact rationals in floating point (integer day counts
  over integer denominators); do not round intermediate day counts.
