"""Static proofs that a valid rule has no instance at all (an optimization).

Valid rules can be empty: BYSETPOS=5 on a SECONDLY rule (each interval holds
at most one candidate), BYMONTH=2;BYMONTHDAY=30, or an HOURLY rule whose
INTERVAL never reaches a listed BYHOUR. Proving emptiness up front keeps
expand() from scanning to the horizon. Each proof is exact, never heuristic.
"""

from __future__ import annotations

import math
from typing import Final, assert_never

from .model import Freq
from .plan import Plan

_DAY_SECONDS: Final = 86400
_UNIT: Final = {Freq.HOURLY: 3600, Freq.MINUTELY: 60, Freq.SECONDLY: 1}


def _max_days(plan: Plan) -> int:
    """Upper bound on the number of distinct dates in one interval."""
    rule = plan.rule
    if plan.anchor_mday is not None:
        return 1 if plan.anchor_month is not None or rule.freq is Freq.MONTHLY else len(plan.months) or 12
    if plan.anchor_weekday is not None:
        return max(len(rule.byweekno), 1)
    match rule.freq:
        case Freq.YEARLY:
            bounds = [7 * len(rule.byweekno) if rule.byweekno else 366]
            if rule.byyearday:
                bounds.append(len(plan.yeardays))
            if rule.bymonthday:
                bounds.append(len(plan.monthdays) * (len(plan.months) or 12))
            if rule.byday and plan.nth_in_month:
                months = len(plan.months)
                bounds.append(months * (5 * len(plan.plain_days) + len(plan.nth_days)))
            elif rule.byday:
                bounds.append(53 * len(plan.plain_days) + len(plan.nth_days))
            return min(bounds)
        case Freq.MONTHLY:
            bounds = [len(plan.monthdays) or 31]
            if rule.byday:
                bounds.append(5 * len(plan.plain_days) + len(plan.nth_days))
            return min(bounds)
        case Freq.WEEKLY:
            return len(plan.plain_days) or 7
        case Freq.DAILY | Freq.HOURLY | Freq.MINUTELY | Freq.SECONDLY:
            return 1
        case unreachable:
            assert_never(unreachable)


def max_interval_size(plan: Plan) -> int:
    """Upper bound on the number of candidates in one interval."""
    times = len(plan.hours) * len(plan.minutes) * len(plan.seconds)
    match plan.rule.freq:
        case Freq.YEARLY | Freq.MONTHLY | Freq.WEEKLY | Freq.DAILY:
            return _max_days(plan) * times
        case Freq.HOURLY:
            return len(plan.minutes) * len(plan.seconds)
        case Freq.MINUTELY:
            return len(plan.seconds)
        case Freq.SECONDLY:
            return 1
        case unreachable:
            assert_never(unreachable)


def _time_reachable(plan: Plan) -> bool:
    """Whether some sub-daily interval start passes the time-of-day limits.

    Interval starts advance by a fixed number of wall-clock seconds, so their
    time of day cycles with period 86400 / gcd(86400, step).
    """
    rule = plan.rule
    step = rule.interval * _UNIT[rule.freq]
    start = plan.start
    base = start.hour * 3600 + start.minute * 60 + start.second
    match rule.freq:
        case Freq.HOURLY:
            base -= start.minute * 60 + start.second
        case Freq.MINUTELY:
            base -= start.second
        case Freq.SECONDLY:
            pass
        case Freq.YEARLY | Freq.MONTHLY | Freq.WEEKLY | Freq.DAILY:
            return True
        case unreachable:
            assert_never(unreachable)
    seconds_ok = set(plan.seconds) if rule.bysecond and rule.freq is Freq.SECONDLY else None
    minutes_ok = set(rule.byminute) if rule.byminute and rule.freq is not Freq.HOURLY else None
    hours_ok = set(rule.byhour) if rule.byhour else None
    for j in range(_DAY_SECONDS // math.gcd(_DAY_SECONDS, step)):
        hour, rest = divmod((base + j * step) % _DAY_SECONDS, 3600)
        minute, second = divmod(rest, 60)
        if (
            (hours_ok is None or hour in hours_ok)
            and (minutes_ok is None or minute in minutes_ok)
            and (seconds_ok is None or second in seconds_ok)
        ):
            return True
    return False


def never(plan: Plan) -> bool:
    """True only if the rule provably generates no candidate in any interval."""
    rule = plan.rule
    size = max_interval_size(plan)
    if rule.bysetpos and all(abs(n) > size for n in rule.bysetpos):
        return True
    if plan.mask is not None and plan.mask.empty():
        return True
    return rule.freq in _UNIT and not _time_reachable(plan)
