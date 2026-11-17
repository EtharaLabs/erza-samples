"""Combination rules of RFC 5545 section 3.3.10 that the grammar cannot express."""

from __future__ import annotations

from datetime import datetime
from typing import assert_never

from .localtime import Floating, Utc, Zoned, form_of
from .model import Freq, InvalidRule, Rule


def validate(rule: Rule, dtstart: datetime) -> None:
    """Raise :class:`InvalidRule` if RFC 5545 forbids ``rule`` with ``dtstart``.

    Checks, with their sources in rfc5545.txt:

    * DTSTART is one of the three DATE-TIME forms (lines 1817-1899; the
      UTC-offset form is forbidden by lines 1819-1822);
    * BYWEEKNO only with FREQ=YEARLY (lines 2338-2339, table line 2436);
    * BYYEARDAY not with DAILY, WEEKLY or MONTHLY (lines 2328-2329, line 2438);
    * BYMONTHDAY not with WEEKLY (lines 2321-2322, line 2440);
    * a numeric BYDAY only with MONTHLY or YEARLY (lines 2312-2314), and not
      with YEARLY when BYWEEKNO is present (lines 2314-2316);
    * BYSETPOS only together with another BYxxx part (lines 2371-2372);
    * COUNT=0 is rejected: "The DTSTART property value always counts as the
      first occurrence" (lines 2272-2274), so no rule has zero occurrences;
    * UNTIL "MUST have the same value type as the DTSTART property"
      (lines 2259-2260), so a DATE UNTIL is invalid with a DATE-TIME DTSTART;
      with a floating DTSTART UNTIL must be local time (lines 2260-2263);
      with a UTC or zoned DTSTART it must be UTC time (lines 2263-2265).
    """
    form = form_of(dtstart)
    freq = rule.freq
    if rule.byweekno and freq is not Freq.YEARLY:
        raise InvalidRule("BYWEEKNO is only allowed with FREQ=YEARLY", 2338)
    if rule.byyearday and freq in (Freq.DAILY, Freq.WEEKLY, Freq.MONTHLY):
        raise InvalidRule(f"BYYEARDAY is not allowed with FREQ={freq}", 2328)
    if rule.bymonthday and freq is Freq.WEEKLY:
        raise InvalidRule("BYMONTHDAY is not allowed with FREQ=WEEKLY", 2321)
    if any(d.ordinal is not None for d in rule.byday):
        if freq not in (Freq.MONTHLY, Freq.YEARLY):
            raise InvalidRule(f"numeric BYDAY is not allowed with FREQ={freq}", 2312)
        if rule.byweekno:
            raise InvalidRule("numeric BYDAY is not allowed with YEARLY and BYWEEKNO", 2314)
    if rule.bysetpos and not rule.has_any_byxxx():
        raise InvalidRule("BYSETPOS requires another BYxxx rule part", 2371)
    if rule.count == 0:
        raise InvalidRule("COUNT=0 contradicts DTSTART counting as an occurrence", 2273)
    until = rule.until
    if until is None:
        return
    if not isinstance(until, datetime):
        raise InvalidRule("UNTIL is a DATE but DTSTART is a DATE-TIME", 2259)
    utc_until = until.tzinfo is not None
    match form:
        case Floating():
            if utc_until:
                raise InvalidRule("floating DTSTART requires a local-time UNTIL", 2261)
        case Utc() | Zoned():
            if not utc_until:
                raise InvalidRule("UTC or zoned DTSTART requires a UTC UNTIL", 2263)
        case unreachable:
            assert_never(unreachable)
