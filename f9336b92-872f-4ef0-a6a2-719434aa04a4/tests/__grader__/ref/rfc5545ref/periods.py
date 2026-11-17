"""Intervals of a rule ("the interval defined by the FREQ rule part", line 2369).

Interval ``k`` is the ``k``-th FREQ-sized period after the one that contains
DTSTART, stepping by INTERVAL (lines 2247-2253); interval 0 always contains
DTSTART. For YEARLY with BYWEEKNO the period is the week-numbering year
(the year whose weeks 1..52/53 contain the day, lines 2334-2338), so that
interval 0 still contains DTSTART when DTSTART lies in the last week of the
previous year or week one of the next. All arithmetic is on naive
wall-clock values: the instances of a zoned rule are computed as local
times and only then interpreted in the zone (lines 2492-2496).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Final, assert_never

from . import weeks
from .model import MAX_YEAR, Freq
from .plan import Plan, day_ok, day_times

_UNIT_SECONDS: Final = {Freq.HOURLY: 3600, Freq.MINUTELY: 60, Freq.SECONDLY: 1}
_CYCLE_UNITS: Final = {
    Freq.YEARLY: 400,
    Freq.MONTHLY: 4800,
    Freq.WEEKLY: 146097 // 7,
    Freq.DAILY: 146097,
    Freq.HOURLY: 146097 * 24,
    Freq.MINUTELY: 146097 * 1440,
    Freq.SECONDLY: 146097 * 86400,
}


def cycle_length(freq: Freq, interval: int) -> int:
    """Intervals after which the Gregorian pattern of interval starts repeats.

    The Gregorian calendar repeats every 400 years (146097 days, a whole
    number of weeks), so if this many consecutive intervals contain no
    candidate, none ever will. Used only to terminate impossible rules.
    """
    units = _CYCLE_UNITS[freq]
    return units // math.gcd(units, interval)


def _combine(days: list[date], plan: Plan) -> list[datetime]:
    times = day_times(plan)
    return [datetime(d.year, d.month, d.day, h, m, s) for d in days for (h, m, s) in times]


def year_days(plan: Plan, year: int) -> list[date]:
    """The candidate universe of a YEARLY interval, before day-level filtering.

    Without BYWEEKNO this is calendar year ``year`` (restricted to the months
    that can pass BYMONTH or the DTSTART month anchor). With BYWEEKNO it is
    the union of the selected WKST-started weeks of ``year`` (lines
    2331-2340), which may include days of the adjacent calendar years; see
    NOTES.md.
    """
    rule = plan.rule
    if rule.byweekno:
        found = {d for n in rule.byweekno for d in weeks.week_days(year, n, rule.wkst)}
        return sorted(found)
    if plan.anchor_month is not None:
        months: list[int] = [plan.anchor_month]
    else:
        months = sorted(plan.months) or list(range(1, 13))
    return [date(year, m, d) for m in months for d in range(1, weeks.month_length(year, m) + 1)]


def _span(start: date, count: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]


def _subdaily_base(plan: Plan) -> datetime:
    start = plan.start
    match plan.rule.freq:
        case Freq.HOURLY:
            return start.replace(minute=0, second=0)
        case Freq.MINUTELY:
            return start.replace(second=0)
        case Freq.SECONDLY:
            return start
        case Freq.YEARLY | Freq.MONTHLY | Freq.WEEKLY | Freq.DAILY:
            return start.replace(hour=0, minute=0, second=0)
        case unreachable:
            assert_never(unreachable)


def _step(plan: Plan) -> timedelta:
    rule = plan.rule
    if rule.freq is Freq.DAILY:
        return timedelta(days=rule.interval)
    return timedelta(seconds=rule.interval * _UNIT_SECONDS[rule.freq])


def interval_start(plan: Plan, k: int) -> datetime | None:
    """Start of interval ``k`` for DAILY and sub-daily rules; None past the horizon."""
    base = _subdaily_base(plan)
    step = _step(plan)
    limit = datetime(MAX_YEAR, 12, 31, 23, 59, 59)
    if k * step > limit - base:
        return None
    return base + k * step


def _subdaily_walls(plan: Plan, start: datetime) -> list[datetime]:
    """Candidates of one DAILY or sub-daily interval (table lines 2431-2451).

    Day-level parts limit for all of these frequencies. BYHOUR limits for
    HOURLY and shorter, BYMINUTE for MINUTELY and shorter, BYSECOND for
    SECONDLY; the remaining time parts expand.
    """
    rule = plan.rule
    if not day_ok(plan, start.date()):
        return []
    hour_ok = not rule.byhour or start.hour in rule.byhour
    minute_ok = not rule.byminute or start.minute in rule.byminute
    match rule.freq:
        case Freq.HOURLY:
            if not hour_ok:
                return []
            return [start.replace(minute=m, second=s) for m in plan.minutes for s in plan.seconds]
        case Freq.MINUTELY:
            if not (hour_ok and minute_ok):
                return []
            return [start.replace(second=s) for s in plan.seconds]
        case Freq.SECONDLY:
            second_ok = not rule.bysecond or start.second in plan.seconds
            return [start] if hour_ok and minute_ok and second_ok else []
        case Freq.YEARLY | Freq.MONTHLY | Freq.WEEKLY | Freq.DAILY:
            return _combine([start.date()], plan)
        case unreachable:
            assert_never(unreachable)


def interval_walls(plan: Plan, k: int) -> list[datetime] | None:
    """Sorted candidate wall times of interval ``k``; None past the horizon.

    Invalid dates (such as February 30) are never constructed, which is how
    they are "ignored and ... not counted" (lines 2382-2386).
    """
    rule = plan.rule
    start = plan.start
    match rule.freq:
        case Freq.YEARLY:
            first = weeks.week_year(start.date(), rule.wkst) if rule.byweekno else start.year
            year = first + k * rule.interval
            if year > MAX_YEAR:
                return None
            return _combine([d for d in year_days(plan, year) if day_ok(plan, d)], plan)
        case Freq.MONTHLY:
            year, month0 = divmod(start.year * 12 + start.month - 1 + k * rule.interval, 12)
            if year > MAX_YEAR:
                return None
            first = date(year, month0 + 1, 1)
            days = _span(first, weeks.month_length(year, month0 + 1))
            return _combine([d for d in days if day_ok(plan, d)], plan)
        case Freq.WEEKLY:
            ordinal = weeks.week_start(start.date(), rule.wkst).toordinal() + 7 * k * rule.interval
            if ordinal > date(MAX_YEAR, 12, 25).toordinal():
                return None
            days = _span(date.fromordinal(ordinal), 7)
            return _combine([d for d in days if day_ok(plan, d)], plan)
        case Freq.DAILY | Freq.HOURLY | Freq.MINUTELY | Freq.SECONDLY:
            at = interval_start(plan, k)
            return None if at is None else _subdaily_walls(plan, at)
        case unreachable:
            assert_never(unreachable)


def _first_index_at(plan: Plan, k: int, target: datetime) -> int:
    """Smallest interval index > k whose start is at or after ``target``."""
    base = _subdaily_base(plan)
    step = _step(plan)
    needed = -((base - target) // step)
    return max(k + 1, needed)


def next_live(plan: Plan, k: int) -> int | None:
    """Smallest index >= k not provably empty at month/day/hour/minute level.

    A pure optimization for DAILY and sub-daily rules; YEARLY, MONTHLY and
    WEEKLY indexes are returned unchanged. None means past the horizon.
    """
    rule = plan.rule
    if rule.freq in (Freq.YEARLY, Freq.MONTHLY, Freq.WEEKLY):
        return k
    while True:
        at = interval_start(plan, k)
        if at is None:
            return None
        day = at.date()
        match_day = day if plan.mask is None else plan.mask.next_match(day)
        if match_day is None:
            return None
        if match_day != day:
            k = _first_index_at(plan, k, datetime(match_day.year, match_day.month, match_day.day))
        elif rule.freq in (Freq.MINUTELY, Freq.SECONDLY) and rule.byhour and at.hour not in rule.byhour:
            k = _first_index_at(plan, k, at.replace(minute=0, second=0) + timedelta(hours=1))
        elif rule.freq is Freq.SECONDLY and rule.byminute and at.minute not in rule.byminute:
            k = _first_index_at(plan, k, at.replace(second=0) + timedelta(minutes=1))
        else:
            return k
