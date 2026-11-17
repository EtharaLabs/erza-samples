---
name: rfc5545-recurrence-derivation
description: Derive the exact instance list of an RFC 5545 recurrence rule from the specification text alone, and use that derivation to test and repair a recurrence engine. Use when a library's RRULE expansion must be checked or fixed against RFC 5545 sections 3.3.5, 3.3.10, and 3.8.5.3.
---

# Deriving RFC 5545 recurrence sets by hand

A recurrence engine is only as right as the instance lists you can derive without it. Derive first, then compare, then read the engine's code. Never take the engine's own output, or another engine's, as the authority: the specification text is the authority, and its worked examples in section 3.8.5.3 are your calibration set.

## 1. Read the rule the way the RFC evaluates it

Section 3.3.10 gives one table that says, for each FREQ, whether each BYxxx rule part expands the set (adds instances) or limits it (removes instances). Write the table out once and keep it beside you. Then evaluate a rule in the RFC's order:

1. Start from one interval of the frequency: one year, one month, one week (starting on WKST), one day, one hour, one minute, or one second, stepping by INTERVAL.
2. Apply BYMONTH, BYWEEKNO, BYYEARDAY, BYMONTHDAY, BYDAY, BYHOUR, BYMINUTE, and BYSECOND in that order, each as expand or limit according to the table for this FREQ.
3. Apply BYSETPOS last, to the ordered set of instances that one interval produced, never to the whole recurrence.
4. Drop instances that are invalid dates or nonexistent local times, and never count them.
5. Stop at COUNT emitted instances or at UNTIL, whichever the rule names.

Information the rule does not carry comes from DTSTART. Work out, for each FREQ and each combination of BYxxx parts, which fields DTSTART supplies, and check that against the examples before you trust it.

## 2. Weeks are counted from WKST

Week numbering in section 3.3.10 depends on WKST. Week 1 of a year is the first week, starting on WKST, that holds at least four days of that year. Days before week 1 belong to the previous year's last week, and days after the last week belong to the next year's week 1. Negative week numbers count back from the year's last week, and a year has either 52 or 53 weeks depending on its first weekday, its length, and WKST. Derive the week table for the year you test, and for its neighbours, under the WKST you test, instead of assuming ISO weeks.

## 3. Weekday values select independently

Each BYDAY value is its own selector. A plain weekday means every such day in the interval the table assigns. An ordinal weekday means the nth such day, counted from the start or, if negative, from the end of the month or year the frequency and BYMONTH determine. Derive each value's days separately, then decide from the table how they combine with the other parts.

## 4. Local time follows two different clauses

Section 3.3.5 says how a DATE-TIME value itself is read when its local time occurs twice or not at all. Section 3.3.10 says what happens to a generated instance whose local time does not exist. These are different rules for different values: test a DTSTART inside a gap or a repeated hour separately from instances that land there. Compare UNTIL as an absolute instant, and remember that an aware DTSTART requires UNTIL in UTC.

## 5. Build a differential check

1. Transcribe every example of section 3.8.5.3 with its DTSTART and printed instances into a test file first. Run the engine on all of them before changing anything, and keep the failures as your first evidence.
2. For each rule part you touch, write small rules that isolate it, derive their instances by hand, and assert them. Vary one parameter at a time: the year (leap and common, every first weekday), WKST, the sign of a value, the frequency, and the number of times of day in an interval.
3. When one input is wrong, ask which stages of section 1 it passes through. A wrong instance list is often the product of more than one stage, so repair the stage the specification contradicts, then re-run every isolating test, not only the one that first failed.
4. Keep every repair as narrow as the clause it implements, and keep the existing test suite green after each one.

## 6. Report what you know and how you know it

For every cause, state the clause by section and wording, the code location, a reproducing rule with the instances before and after the change, and whether you ran it or reasoned it. Say which wrong inputs needed more than one repair.
