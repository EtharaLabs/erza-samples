Implemented causes
==================

1. Negative BYSETPOS candidate ordering, src/dateutil/rrule.py,
   rrule._iter candidate construction.
   RFC 5545 §3.3.10: "Each BYSETPOS value can include a positive (+n)
   or negative (-n) integer" and "the nth occurrence ... within the set".
   For DTSTART=20240101T170000, FREQ=DAILY;BYHOUR=9,17;BYSETPOS=-1;COUNT=2,
   the original code selects 09:00 within each reversed day, producing
   January 2 and 3 at 09:00 (inferred from original code).
   The repaired code returns January 1 and 2 at 17:00 (verified by regression).
   The cause was reversing days without reversing the times within each day.

2. Missing constructor range checks, src/dateutil/rrule.py, rrule.__init__.
   RFC 5545 §3.3.10: BYMONTH "Valid values are 1 to 12";
   BYMONTHDAY "Valid values are 1 to 31 or -31 to -1";
   BYYEARDAY "Valid values are 1 to 366 or -366 to -1";
   BYWEEKNO "Valid values are 1 to 53 or -53 to -1";
   BYHOUR "Valid values are 0 to 23"; BYMINUTE "Valid values are 0 to 59".
   Original DAILY rules with BYMONTH=13, BYMONTHDAY=0, BYYEARDAY=0 or 367,
   or BYWEEKNO=0 or 54 were accepted (inferred from constructor).
   BYMONTHDAY=0 acted as no filter; others could produce empty expansions.
   All now raise ValueError at construction, through both public entry
   points (verified by parametrized regression). Hour/minute checks also
   prevent normalization from silently discarding invalid values.

These causes are independent on valid input. Combining an invalid part
with negative BYSETPOS can mask the ordering error by producing an empty
set. Repairing ordering alone still accepts invalid parts; repairing
validation alone still selects the wrong time for valid negative positions.
These interaction claims are inferred from the code.

Scope: this records the causes repaired, not a proof of complete RFC
conformance. Regression tests: 9 passed. Full suite run separately.
