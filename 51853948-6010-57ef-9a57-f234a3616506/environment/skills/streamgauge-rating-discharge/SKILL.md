---
name: streamgauge-rating-discharge
description: >-
  Convert a recorded stage (gage height) hydrograph into discharge using a gauge's
  own expanded shift-adjusted stage-discharge rating table, and reduce the result to
  time-weighted means over reporting intervals. Use when a task supplies gage heights
  and asks for discharge or for a mean or total flow over a period. Do not use when
  the discharge series is itself supplied, when the quantity wanted is a stage or a
  volume-to-elevation storage relation, or when the site is a controlled structure
  rated by a weir or flume equation rather than by a measured stage-discharge table.
---

# Discharge from a stage record

A streamgauge does not measure discharge. It measures **stage** - the water-surface
elevation above an arbitrary local datum, called gage height. Discharge is inferred
from stage through the gauge's **rating**: a table built by making direct discharge
measurements across the range of flows at that site and fitting the stage-discharge
relation those measurements trace out.

The rating belongs to the gauge, not to the river and not to the method. Channel
geometry, bed material, slope and the location of the hydraulic control all enter it.
Two gauges reading an identical gage height routinely differ by an order of magnitude
in discharge. A rating is also revised whenever the control changes - after a flood
scours the bed, when a sandbar builds, when vegetation grows in - so a gauge carries a
rating number and a date, and older records were computed against an older rating.

Because of this, discharge cannot be recovered from a stage record by any formula.
The rating table for the specific gauge is required, and nothing substitutes for it.

## What is in a rating table

The tables in `references/` are **expanded shift-adjusted** ratings, one file per
gauge, tab-separated with a comment header. The expanded form and its step are
defined by the U.S. Geological Survey NWIS rating service
(`https://waterdata.usgs.gov/nwisweb/get_ratings`, `file_type=exsa`):

    gage_height_ft    shift_ft    discharge_cfs

- `gage_height_ft` - the tabulated stage, at a 0.01 ft step.
- `shift_ft` - the shift in effect at that stage. A shift is a temporary correction
  that carries a moved control without rebuilding the whole rating.
- `discharge_cfs` - the discharge for that gage height.

**The discharge column already carries the shift.** This is the single most common
error in applying one of these tables: the shift is reported so that the record is
auditable, not so that it can be applied again. Look an observed gage height up
directly against `gage_height_ft` and read `discharge_cfs`. Adding `shift_ft` to the
stage before the lookup double-counts the correction and biases every value.

## Procedure

1. **Load the gauge's own table.** Match on the gauge label. Never apply one gauge's
   rating to another's stage, and never fit a power law to one table and reuse it
   elsewhere - the tables are not interchangeable and are not well approximated by a
   single exponent across their whole range.

2. **Rate each reported instant.** For a gage height `h`, find the bracketing rows
   and interpolate `discharge_cfs` linearly in gage height:

       Q = q0 + (q1 - q0) * (h - h0) / (h1 - h0)

   At the 0.01 ft step of an expanded table a reported stage usually lands exactly on
   a row, and the interpolation returns that row unchanged. Where a stage falls
   between rows, linear interpolation and the log-log form used to build the rating
   (Kennedy 1984, USGS TWRI Book 3 Chapter A10,
   `https://pubs.usgs.gov/twri/twri3-a10/`) agree far inside any reasonable
   reporting precision.

3. **Reduce over the interval.** A gauge's reporting interval is not guaranteed
   uniform - it tightens during a rise and relaxes at steady flow. So a plain
   arithmetic mean of the samples is wrong: it weights a densely reported hour the
   same as a sparsely reported one. Integrate in time and divide by the elapsed span:

       mean = [ sum over consecutive pairs of (Q_i + Q_i+1)/2 * (t_i+1 - t_i) ]
              / (t_last - t_first)

   taken over the samples inside the interval, with both endpoints included. On a
   perfectly uniform interval this reduces to the trapezoidal average and differs
   from the arithmetic mean only in the end weights; on an uneven one the difference
   is real.

## Traps

- **Scaling a single recent measurement.** A published measurement from days earlier
  is one point on a curve. Extrapolating it by `Q ~ h^2`, or linearly in `h`, or
  carrying it forward unchanged, are all badly wrong away from the stage at which it
  was taken - a rating is strongly non-linear and its exponent varies along it.
- **Re-applying the shift.** Covered above; it biases the whole series one way.
- **Averaging the samples instead of the time.** Correct only for a strictly uniform
  reporting interval.
- **Extrapolating past the table.** A rating is defined only over its tabulated
  range. Outside it the relation is unknown, not merely uncertain.

## Check values

Read directly off the shipped tables, for orientation while wiring up the lookup:

| gauge | gage height (ft) | discharge (cfs) |
|---|---|---|
| GS-A | 9.50 | 13931.76 |
| GS-B | 20.00 | 193051.32 |
| GS-C | 7.00 | 14662.71 |

These stages are outside the record supplied with the task; they exercise the lookup,
not the answer.

## Provenance of the tables

The three tables are real expanded shift-adjusted ratings published by the U.S.
Geological Survey through the National Water Information System, retrieved
2026-07-27 from the NWIS rating service
(`https://waterdata.usgs.gov/nwisweb/get_ratings?site_no=<site>&file_type=exsa`).
USGS data are public domain under 17 U.S.C. 105. The gauges are relabelled GS-A,
GS-B and GS-C here and the site numbers, names and coordinates are withheld, so the
tables travel with the task rather than being looked up from the site index. See
`references/method.md` for the field basis of the stage-discharge relation.
