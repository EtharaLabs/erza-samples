# Reference answer

The shipped python-dateutil 4.0.0 copy has six causes that make `dateutil.rrule` disagree with RFC 5545. Code locations are in `src/dateutil/rrule.py` of the shipped copy.

## Causes

- C-B1. BYMONTHDAY=0 is accepted. RFC 5545 section 3.3.10 says the valid values are 1 to 31 or -31 to -1. The constructor's range check admits 0, and the later split into positive and negative month days drops it, so a rule whose only month day is 0 has no month-day filter and matches every day.
- C-B2. A BYDAY list that mixes plain weekdays and ordinal weekdays under MONTHLY or YEARLY is intersected instead of combined. Section 3.3.10 says each value selects days on its own (a plain weekday means all such days in the frequency, an ordinal means the nth occurrence), so the set is the union. The day filter in `rrule._iter` rejects a day that fails the plain-weekday test and also rejects a day that fails the ordinal test.
- C-P1. The week counts used for days at the boundary of the year under BYWEEKNO are computed as if the week started on Monday, ignoring WKST. Section 3.3.10 defines week 1 as the first week, starting on WKST, that holds at least four days of the year. Both the previous year's week count and the next year's week count in `_iterinfo.rebuild` use a Monday-start formula, so rules with another WKST misnumber boundary days and negative week numbers that name next year's week 1.
- C-P2. When every BYSETPOS value is negative and the interval has more than one time of day, the selection is wrong. Section 3.3.10 applies BYSETPOS to the ordered set of instances in one interval, counting negative values from the end. The candidate walk in `rrule._iter` reverses the days but not the times of day, so -1 picks the earliest time of the last day instead of the latest instance.
- C-P3. On aware rules, UNTIL is compared by wall time. Section 3.3.10 says UNTIL bounds the set inclusively and, for a zoned DTSTART, is given in UTC, so the bound is an instant. `rrule._iter` converts UNTIL into the rule's time zone, and Python then compares same-zone datetimes by wall time, so on a fall-back day an instance that is before UNTIL as an instant but later on the wall clock is dropped.
- C-P4. YEARLY rules with a positive ordinal BYDAY and no BYMONTH count the ordinal from DTSTART's month instead of from 1 January. Section 3.3.10 (Note 2 of the BYxxx table) and the "Every 20th Monday of the year" example in section 3.8.5.3 count within the year. The ordinal range in `_iterinfo.rebuild` starts at DTSTART's month.

## Interactions

- C-P2 with C-B2: for MONTHLY;BYDAY=MO,-1FR;BYHOUR=9,17;BYMINUTE=0;BYSETPOS=-1 the set is empty until C-B2 is repaired, and with only C-B2 repaired the right days come out at 09:00 instead of 17:00.
- C-P4 with C-B2: for YEARLY;BYDAY=FR,20MO the intersection hides C-P4 entirely; with only C-B2 repaired the 20th Monday is counted from DTSTART's month.
- C-P2 with the gap handling: on a spring-forward day the nonexistent local time is ignored before BYSETPOS indexes the set (section 3.3.10), which shortens the set and exposes C-P2 on rules where it is otherwise invisible.
- C-P1 sits in two separate week counts (previous year and next year); repairing one leaves rules that use the other wrong.
- C-P3 with the gap handling: a span containing both a spring-forward day and a fall-back UNTIL needs both to be right.

## Rejected claim classes

- R1. That RFC 5545 requires a YEARLY rule whose only BYxxx part is BYMONTHDAY to take its month from DTSTART. The BYxxx table marks BYMONTHDAY under YEARLY as Expand, so it expands into every month.
- R2. That a cause lives in the time-zone module (`dateutil.tz`) or in Python's `zoneinfo` rather than in `rrule.py`.
- R3. That the intersection of plain and ordinal BYDAY values is what RFC 5545 specifies.
- R4. That a cause is repaired when the note does not say what the code did wrong or what was changed, for example "Fixed BYDAY handling".
- R5. That a cause exists which none of the causes above describes.
