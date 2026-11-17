# RFC 5545 recurrence repairs

This audit repaired two causes; it does not establish conformance for all inputs or complete the requested range-validation audit.

## Negative BYSETPOS ordering

RFC 5545 §3.3.10: “BYSETPOS operates on a set of recurrence instances in one interval of the recurrence rule” and “this indicates the nth occurrence”. The last occurrence of a daily interval containing 09:00 and 18:00 is 18:00.

Location: src/dateutil/rrule.py, rrule._iter, candidate collection for BYSETPOS. Reverse traversal reversed days but not times. Reverse times as well.

Run before repair: DAILY, DTSTART=2024-01-01T18:00, BYHOUR=9,18, BYSETPOS=-1, COUNT=3 returned January 2, 3, 4 at 09:00. Expected and regression-tested after repair: January 1, 2, 3 at 18:00. The expected list is derived from the clause above. The regression also covers rrulestr.

## UNTIL comparison during a repeated hour

RFC 5545 §3.3.10: “The UNTIL rule part defines a DATE or DATE-TIME value that bounds the recurrence rule in an inclusive manner” and “the UNTIL rule part MUST be specified as a date with UTC time.” Section 3.3.5: “If, based on the definition of the referenced time zone, the local time described occurs more than once ... the DATE-TIME value refers to the first occurrence”.

Location: src/dateutil/rrule.py, rrule._iter, conversion of UNTIL and both output comparisons. Converting UNTIL to DTSTART's zone caused Python's same-zone comparison to compare wall times. Keep UNTIL intact and convert aware candidates to UTC for comparison.

Regression rule: America/New_York DTSTART=2024-11-03T00:30, FREQ=MINUTELY, INTERVAL=30, UNTIL=20241103T060000Z. Expected after repair: 00:30, 01:00, 01:30 (all first occurrences, same tzinfo). Before repair the wall-time comparison implies only 00:30 and 01:00; this specific before list was inferred from code, not run. After list is exercised by the regression test. A preliminary hourly probe was run before repair but did not expose this defect.

## Interaction

The defects act independently on the isolated examples. A rule using negative BYSETPOS with multiple times per day and an aware UNTIL during a repeated hour can encounter both. Repairing ordering alone leaves wall-time truncation; repairing comparison alone leaves the wrong positional selection. This combined behavior is inferred, not separately run. No input requiring both repairs has been established experimentally.
