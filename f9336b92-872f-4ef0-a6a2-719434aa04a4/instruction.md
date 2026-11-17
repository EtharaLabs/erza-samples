# Make python-dateutil's recurrence expansion conform to RFC 5545

`/workspace/dateutil` is the source of python-dateutil 4.0.0, and our scheduling service builds every recurring event through its `dateutil.rrule` module. That module must expand recurrence rules exactly as RFC 5545 specifies, and RFC 5545 is normative for every behaviour below. The specification is at `/workspace/spec/rfc5545.txt`. The governing text is section 3.3.5 (Date-Time); section 3.3.10 (Recurrence Rule), including the table of how each BYxxx rule part expands or limits each FREQ value and the notes under that table; and section 3.8.5.3 (Recurrence Rule property), including its examples. Where the library and those sections disagree, the sections win.

## Required behaviour

Only the public API matters: the instances it returns must equal the instances RFC 5545 determines for the same rule:

- `dateutil.rrule.rrule`, with the frequency constants `YEARLY`, `MONTHLY`, `WEEKLY`, `DAILY`, `HOURLY`, `MINUTELY`, and `SECONDLY`, and the weekday constants `MO`, `TU`, `WE`, `TH`, `FR`, `SA`, and `SU`, including their ordinal form such as `MO(+2)` or `FR(-1)`.
- `dateutil.rrule.rrulestr`, which parses an RRULE value written in the section 3.3.10 syntax and expands it from the `dtstart` it is given exactly as the equivalent `rrule(...)` call would.
- `dateutil.rrule.rruleset`.
- The methods `__iter__`, `count`, `between`, `after`, `before`, `xafter`, and `replace`, with the meaning their docstrings already give them.

The conventions of each entry point are fixed and must stay as they are:

- `dtstart` is either naive, a floating local time, or aware, carrying a time zone; every instance is a `datetime` with `dtstart`'s `tzinfo`.
- For an aware `dtstart`, `until` is given in UTC, as section 3.3.10 requires, and it bounds the set by instant.
- For a naive `dtstart`, `until` is naive and bounds the set by wall time.
- Generated instances at a nonexistent local time are ignored and not counted, as section 3.3.10 requires.
- Every rule is used with a `dtstart` that is itself an instance of the rule, so the set always begins at `dtstart`.
- A rule part value outside the ranges section 3.3.10 allows raises `ValueError` from both `rrule(...)` and `rrulestr(...)`.

## Rules for your changes

- Change files only under `/workspace/dateutil/src/dateutil/` and `/workspace/dateutil/tests/`, and write your note under `/workspace/output/`. Nothing else may change.
- Keep the public signatures of `rrule`, `rruleset`, `rrulestr`, and their methods exactly as they are.
- Do not delete, skip, or weaken any existing test. The existing suite must still pass: `cd /workspace/dateutil && python -m pytest tests`.
- For every cause you repair, add at least one regression test under `/workspace/dateutil/tests/` that fails on the library as you received it and passes on yours.

## The note

Write `/workspace/output/NOTES.md`. For each cause you found, give:

1. the RFC 5545 clause it breaks, by section and quoted wording;
2. where in the code it lives;
3. the evidence: a rule that shows it, with the instances the library returned before your change and after it;
4. for each claim, whether you verified it by running something or inferred it without running anything.

Then say how the causes you found interact: which inputs are wrong only because more than one cause acts on them, and what repairing just one of them would leave.

Python 3.12, pytest, pytest-xdist, hypothesis, freezegun, and attrs are installed. There is no network access.
