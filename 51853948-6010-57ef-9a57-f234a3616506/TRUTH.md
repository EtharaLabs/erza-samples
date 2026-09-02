# TRUTH — how this task is correctly worked

Answer-free by construction (P-02). No reference value, tolerance or golden appears
here. This file states the method and where it can break; it is shown to the human reviewer.

## The question

Three river gauges, labelled GS-A/GS-B/GS-C, each with one day of recorded stage
(gage height) at a reporting interval that is not guaranteed uniform. For each gauge
and each listed six-hour block, report the mean discharge over the closed interval.

## The crux

A gauge measures stage, not discharge. Converting one to the other requires **that
gauge's own stage-discharge rating** — an empirical table built from direct
measurements at that site. It is not a formula, it is not shared between gauges, and
it is revised when the channel control moves.

The task supplies, for orientation, one recent published discharge measurement per
gauge. That single point is the distractor. Extrapolating it — by a power law, by
linear scaling, or by carrying it forward unchanged — is the route available without
the table, and it is the route that fails.

**The crux is therefore: did the run obtain discharge from a per-gauge rating table,
or did it manufacture discharge from the supplied single measurement?**

## Steps

### Step 0 — Read the inputs. Open `stage_series.csv` and `question.json`. Work from
the shipped record, not from the prose description of it.

### Step 1 — Load each gauge's own rating table. One table per gauge, matched by
label. A table must never be reused across gauges.

### Step 2 — Rate every reported instant. Interpolate discharge linearly against gage
height between the bracketing rating rows. The discharge column of an expanded
shift-adjusted table already carries the shift in effect; the shift column is
reported for audit and must not be added to the stage before lookup.

### Step 3 — Reduce over each block. Integrate discharge in time across the samples
inside the closed interval, endpoints included, and divide by the elapsed span, so
that unevenly spaced samples are weighted by the time they represent rather than
counted equally.

### Step 4 — Emit the contract. Write the declared object at the declared path, one
number per gauge and block.

## Where it breaks

- **No table.** Discharge is invented from the distractor. This is the expected
  no-skill outcome and produces a well-formed but wrong answer.
- **Shift applied twice.** The stage is offset by the shift column before lookup,
  biasing the whole series one way.
- **Wrong table for the gauge.** One gauge's rating applied to another's stage.
- **Sample average instead of a time average.** Correct only when the reporting
  interval is strictly uniform. On this instance the intervals are nearly uniform, so
  this alone does not decide the answer — it is recorded, not treated as fatal.
- **Extrapolating past the tabulated range.** Outside the table the relation is
  unknown; the shipped series stay well inside it.

## What must never appear

Reading the oracle or verifier directory, editing or deleting a test, injecting a
conftest, or reaching the network. Any of these invalidates the run regardless of the
number produced.
