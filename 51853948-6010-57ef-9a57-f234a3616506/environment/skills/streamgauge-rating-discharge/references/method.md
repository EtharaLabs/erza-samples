# The stage-discharge relation and how a rating is maintained

Background for the procedure in `SKILL.md`. Nothing here is specific to any one
task instance.

## Why a rating exists

Continuous discharge records are not measured continuously. Measuring discharge
directly - wading a section with a current meter, or working from a cableway or boat
with an acoustic profiler - takes a crew and a large part of a day. Stage, by
contrast, is cheap to record every few minutes with a float, a bubbler or a pressure
transducer.

So the record is built indirectly. A crew makes discharge measurements spread across
the flow range over months and years, each one pairing a measured discharge with the
gage height at the time. The curve those pairs trace out is the **rating**. Once it
exists, the continuously recorded stage is put through it to give continuous
discharge.

The consequence that matters: **the rating is the entire empirical content of the
record.** Stage alone carries no discharge information. A gage height of 6 ft is a
number about a particular staff at a particular site.

## What sets the shape of the curve

At the low end a rating is usually governed by a **section control** - a riffle, a
rock ledge, an artificial weir - and behaves close to a power law in the head over
that control, `Q = C (h - e)^b`, where `e` is the stage of zero flow. The exponent
`b` typically runs about 1.5 for a broad section to 2.5 or higher for a narrow one
(Kennedy 1984, USGS TWRI Book 3 Chapter A10, `https://pubs.usgs.gov/twri/twri3-a10/`;
Rantz and others 1982, USGS WSP 2175, `https://pubs.usgs.gov/wsp/wsp2175/`).

At higher stages the control usually drowns out and the reach itself takes over as a
**channel control**, where slope and roughness govern and the exponent falls. Many
ratings show a distinct break where this transition happens, and some sites have a
third segment once the flow leaves the banks onto a floodplain, where a large rise in
stage buys comparatively little discharge.

This is why fitting one exponent across a whole rating is unsound, and why a power
law anchored on a single measurement extrapolates badly: the measurement may sit on
one segment and the target stage on another.

## Shifts and rating revisions

Channel controls move. A flood scours the bed, a bar builds during a recession,
vegetation grows through a summer, ice forms a backwater. When the control shifts but
the shape of the relation survives, the record is corrected with a **shift** - a
stage offset that slides the measured stage onto the existing curve - rather than by
rebuilding the rating.

A published expanded table folds the shift in effect into its discharge column and
reports the shift alongside for audit. That is why the discharge column is read
directly and the shift is not applied a second time.

When the control changes enough that no single offset fits, a new rating is issued
with a new number. Both facts - the rating number and the shift history - are why a
discharge value is only meaningful with respect to a stated rating at a stated time,
and why a discharge published for an earlier date may not equal what the current
table returns for the same gage height.

## Reducing an instantaneous series to a period mean

Discharge records are reported on an interval that is not guaranteed uniform: many
gauges tighten the interval during a rise and relax it at steady flow, and telemetry
gaps leave uneven spacing. A period mean must therefore weight each sample by the
time it represents, which the trapezoidal integral over the timestamps does directly.
An arithmetic mean of the samples is a special case that is correct only when the
spacing is uniform, and it biases the result toward whatever part of the period was
sampled most densely - typically the steepest part of the hydrograph.

## Sources

- U.S. Geological Survey, National Water Information System, rating service:
  `https://waterdata.usgs.gov/nwisweb/get_ratings` (`file_type=exsa` returns the
  expanded shift-adjusted table).
- Kennedy, E.J., 1984, *Discharge Ratings at Gaging Stations*: U.S. Geological Survey
  Techniques of Water-Resources Investigations, Book 3, Chapter A10.
  `https://pubs.usgs.gov/twri/twri3-a10/`
- Rantz, S.E., and others, 1982, *Measurement and Computation of Streamflow*: U.S.
  Geological Survey Water-Supply Paper 2175, volumes 1-2.
  `https://pubs.usgs.gov/wsp/wsp2175/`

USGS data and publications are public domain under 17 U.S.C. 105.
