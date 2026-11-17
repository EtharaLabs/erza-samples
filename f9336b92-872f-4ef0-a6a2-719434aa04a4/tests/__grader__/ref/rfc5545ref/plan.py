"""Normalized BYxxx constraints: the expand/limit table of RFC 5545 3.3.10."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import assert_never

from . import weeks
from .daymask import DayMask, build_mask
from .model import Freq, Rule, Weekday


@dataclass(frozen=True, slots=True)
class Plan:
    """A rule compiled against its DTSTART wall time.

    The expand/limit table (lines 2431-2459) and the BYxxx evaluation order
    (lines 2415-2420) are realized as one set semantics: the instances of an
    interval are the dates and times inside it that satisfy every present
    BYxxx part, where a "limit" part filters and an "expand" part, being a
    period shorter than FREQ, enumerates. Because each expand part is applied
    to the set produced by the parts before it, the result equals the
    intersection of the per-part conditions; only the defaults differ, and
    those are the anchors below ("Information, not contained in the rule ...
    are derived from ... DTSTART", lines 2388-2393, 2484-2490).

    ``anchor_month``/``anchor_mday``/``anchor_weekday`` are the DTSTART
    fields that fill a missing day specification; ``hours``/``minutes``/
    ``seconds`` are the sorted expansion lists (DTSTART's field when the
    part is absent). Parts that limit at this FREQ are tested against the
    rule's own lists in ``periods`` (with BYSECOND 60 read via ``seconds``).
    ``mask`` caches :func:`day_ok` per year type for DAILY and sub-daily
    rules that have day-level parts (see ``daymask``).
    """

    rule: Rule
    start: datetime
    months: frozenset[int]
    yeardays: frozenset[int]
    monthdays: frozenset[int]
    plain_days: frozenset[Weekday]
    nth_days: frozenset[tuple[Weekday, int]]
    nth_in_month: bool
    anchor_month: int | None
    anchor_mday: int | None
    anchor_weekday: Weekday | None
    hours: tuple[int, ...]
    minutes: tuple[int, ...]
    seconds: tuple[int, ...]
    mask: DayMask | None = None


def compile_plan(rule: Rule, start: datetime) -> Plan:
    """Compile ``rule`` for a DTSTART whose naive wall time is ``start``.

    Day defaults (lines 2388-2393, the note at lines 7130-7131, and the
    BYDAY notes 1 and 2 at lines 2453-2459):

    * YEARLY with none of BYWEEKNO, BYYEARDAY, BYMONTHDAY, BYDAY takes the
      day of month from DTSTART, and also its month when BYMONTH is absent;
      with BYWEEKNO but no other day part it takes DTSTART's weekday within
      each selected week.
    * MONTHLY with neither BYMONTHDAY nor BYDAY takes DTSTART's day of month.
    * WEEKLY without BYDAY takes DTSTART's weekday.

    BYDAY ordinals in a YEARLY rule count within the month when BYMONTH is
    present and within the year otherwise (lines 2305-2309, as corrected by
    note 2 at lines 2456-2459; see NOTES.md); in a MONTHLY rule they count
    within the month (lines 2303-2305).

    A BYSECOND value of 60 is read as 59 (lines 1916-1917).
    """
    freq = rule.freq
    has_day_part = bool(rule.byyearday or rule.bymonthday or rule.byday)
    anchor_month: int | None = None
    anchor_mday: int | None = None
    anchor_weekday: Weekday | None = None
    match freq:
        case Freq.YEARLY:
            if not has_day_part and not rule.byweekno:
                anchor_mday = start.day
                anchor_month = None if rule.bymonth else start.month
            elif not has_day_part:
                anchor_weekday = Weekday(start.weekday())
        case Freq.MONTHLY:
            if not (rule.bymonthday or rule.byday):
                anchor_mday = start.day
        case Freq.WEEKLY:
            if not rule.byday:
                anchor_weekday = Weekday(start.weekday())
        case Freq.DAILY | Freq.HOURLY | Freq.MINUTELY | Freq.SECONDLY:
            pass
        case unreachable:
            assert_never(unreachable)
    seconds = tuple(sorted({min(s, 59) for s in rule.bysecond})) or (start.second,)
    plan = Plan(
        rule=rule,
        start=start,
        months=frozenset(rule.bymonth),
        yeardays=frozenset(rule.byyearday),
        monthdays=frozenset(rule.bymonthday),
        plain_days=frozenset(d.weekday for d in rule.byday if d.ordinal is None),
        nth_days=frozenset((d.weekday, d.ordinal) for d in rule.byday if d.ordinal is not None),
        nth_in_month=freq is Freq.MONTHLY or bool(rule.bymonth),
        anchor_month=anchor_month,
        anchor_mday=anchor_mday,
        anchor_weekday=anchor_weekday,
        hours=tuple(sorted(set(rule.byhour))) or (start.hour,),
        minutes=tuple(sorted(set(rule.byminute))) or (start.minute,),
        seconds=seconds,
    )
    day_level = bool(rule.bymonth or rule.byyearday or rule.bymonthday or rule.byday)
    if day_level and freq in (Freq.DAILY, Freq.HOURLY, Freq.MINUTELY, Freq.SECONDLY):
        return replace(plan, mask=build_mask(lambda day: day_ok(plan, day)))
    return plan


def month_ok(plan: Plan, day: date) -> bool:
    """BYMONTH (limit, or expand for YEARLY) and the DTSTART month anchor."""
    if plan.months and day.month not in plan.months:
        return False
    return plan.anchor_month is None or day.month == plan.anchor_month


def day_ok(plan: Plan, day: date) -> bool:
    """Every day-level condition: BYMONTH, BYYEARDAY, BYMONTHDAY, BYDAY, anchors.

    BYWEEKNO is not tested here; it defines the YEARLY universe instead (see
    ``periods.year_days``).
    """
    if not month_ok(plan, day):
        return False
    if plan.yeardays and plan.yeardays.isdisjoint(weeks.yearday_indexes(day)):
        return False
    if plan.monthdays and plan.monthdays.isdisjoint(weeks.monthday_indexes(day)):
        return False
    if plan.anchor_mday is not None and day.day != plan.anchor_mday:
        return False
    weekday = Weekday(day.weekday())
    if plan.anchor_weekday is not None and weekday != plan.anchor_weekday:
        return False
    if not (plan.plain_days or plan.nth_days):
        return True
    if weekday in plan.plain_days:
        return True
    positions = weeks.nth_in_month(day) if plan.nth_in_month else weeks.nth_in_year(day)
    return any((weekday, n) in plan.nth_days for n in positions)


def day_times(plan: Plan) -> list[tuple[int, int, int]]:
    """Times of day for DAILY and longer frequencies (BYHOUR/BYMINUTE/BYSECOND expand)."""
    return [(h, m, s) for h in plan.hours for m in plan.minutes for s in plan.seconds]
