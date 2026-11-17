"""Families of inputs whose required behaviour is an interpretation, and a classifier for them.

Each family is a named predicate over one case (its rule, DTSTART, and limit). ``classify``
returns every family a case belongs to. Every generator refuses drafts in an
``ALWAYS_EXCLUDED`` family (operator ruling, no switch), and also refuses drafts in any family
it is given in ``exclude`` (empty in graded runs). ``STATED`` lists the families whose
behaviour instruction.md states outright; ``CONTESTED`` is every other family. Nothing here
decides which reading is right.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from gen.spec import DAYS, Spec, rule_text
from refload import Reference

FAMILIES: Final = (
    "yearly-monthday-nomonth", "dtstart-in-gap", "dtstart-ambiguous", "subdaily-fallback",
    "subdaily-springforward", "instance-in-gap", "instance-ambiguous", "count-zero", "setpos-alone",
    "unsynchronized-dtstart", "weekno-without-byday", "weekno-interval", "weekno-negative",
    "weekno-crosses-year", "yearly-ordinal-byday-nomonth", "yearly-ordinal-byday-bymonth",
    "leap-second", "until-floating-local", "until-utc-aware", "parse-case-or-prefix",
    "setpos-beyond-set", "setpos-dup-selection", "interval-negative", "interval-zero",
    "monthday-out-of-range", "monthly-day-29-31", "weekly-interval-wkst",
)
STATED: Final = frozenset({"until-utc-aware", "interval-zero", "monthday-out-of-range"})
# Excluded from every generator, with no switch (final operator ruling, CONTESTED.md).
ALWAYS_EXCLUDED: Final = frozenset({
    "dtstart-in-gap", "subdaily-fallback", "weekno-negative", "setpos-beyond-set", "count-zero",
    "setpos-alone", "weekno-without-byday", "weekno-interval", "leap-second", "parse-case-or-prefix",
})
CONTESTED: Final = frozenset(FAMILIES) - STATED
SUBDAILY: Final = frozenset({"HOURLY", "MINUTELY", "SECONDLY"})
WIDE_LIMIT: Final = 5000


class UnknownFamilyError(KeyError):
    """An exclusion names no family."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name: Final = name


def checked(names: frozenset[str]) -> frozenset[str]:
    """``names`` when every one is a known family."""
    for name in names:
        if name not in FAMILIES:
            raise UnknownFamilyError(name)
    return names


def _wall(value: datetime) -> datetime:
    return value.replace(tzinfo=None, fold=0)


def _exists(wall: datetime, zone: ZoneInfo) -> bool:
    return _wall(wall.replace(tzinfo=zone).astimezone(UTC).astimezone(zone)) == wall


def dtstart_in_gap(dtstart: datetime) -> bool:
    """A zoned DTSTART whose wall time does not exist (a DST gap)."""
    zone = dtstart.tzinfo
    return isinstance(zone, ZoneInfo) and not _exists(_wall(dtstart), zone)


def _ambiguous(wall: datetime, zone: ZoneInfo) -> bool:
    folds = {wall.replace(tzinfo=zone, fold=f).utcoffset() for f in (0, 1)}
    return _exists(wall, zone) and len(folds) == 2


def week_year(day: date, wkst: int) -> int:
    """The week-numbering year of ``day``: week 1 is the WKST week holding 4 January."""
    for year in (day.year + 1, day.year, day.year - 1):
        jan4 = date(year, 1, 4)
        if day >= jan4 - timedelta(days=(jan4.weekday() - wkst) % 7):
            return year
    return day.year - 1


def _period(freq: str, day: date, wkst: int) -> tuple[date, date]:
    """The calendar period of ``freq`` holding ``day``: its first day and the next period's."""
    match freq:
        case "YEARLY":
            return date(day.year, 1, 1), date(day.year + 1, 1, 1)
        case "MONTHLY":
            nxt = date(day.year + day.month // 12, day.month % 12 + 1, 1)
            return day.replace(day=1), nxt
        case "WEEKLY":
            start = day - timedelta(days=(day.weekday() - wkst) % 7)
            return start, start + timedelta(days=7)
        case _:
            return day, day + timedelta(days=1)


def _expand(ref: Reference, spec: Spec, start: datetime, limit: int, cap: datetime | None = None) -> list[datetime]:
    try:
        return ref.expand(ref.parse_rrule(rule_text(spec)), start, limit=limit, until_cap=cap)
    except ref.invalid:
        return []


def _setpos(ref: Reference, spec: Spec, dtstart: datetime, found: list[datetime]) -> set[str]:
    """Whether some interval up to the last instance has fewer members than a position, or two
    positions select the same member."""
    if not spec.bysetpos or not found or spec.freq in SUBDAILY:
        return set()
    wkst = DAYS.index(spec.wkst or "MO")
    first, _ = _period(spec.freq, _wall(dtstart).date(), wkst)
    _, end = _period(spec.freq, _wall(found[-1]).date(), wkst)
    whole = replace(
        spec.core(), bysetpos=(), byhour=spec.byhour or (dtstart.hour,),
        byminute=spec.byminute or (dtstart.minute,), bysecond=spec.bysecond or (dtstart.second,),
    )
    start = datetime.combine(first, datetime.min.time(), dtstart.tzinfo)
    cap = datetime.combine(end, datetime.min.time(), dtstart.tzinfo) - timedelta(seconds=1)
    groups: dict[date, int] = {}
    for value in _expand(ref, whole, start, WIDE_LIMIT, cap):
        key = _period(spec.freq, _wall(value).date(), wkst)[0]
        groups[key] = groups.get(key, 0) + 1
    out: set[str] = set()
    for size in groups.values():
        if any(abs(p) > size for p in spec.bysetpos):
            out.add("setpos-beyond-set")
        picks = [p - 1 if p > 0 else size + p for p in spec.bysetpos if abs(p) <= size]
        if len(set(picks)) < len(picks):
            out.add("setpos-dup-selection")
    return out


def _zoned(ref: Reference, spec: Spec, dtstart: datetime, found: list[datetime]) -> set[str]:
    zone = dtstart.tzinfo
    if not isinstance(zone, ZoneInfo) or not found:
        return set()
    out: set[str] = set()
    wall = _wall(dtstart)
    if not _exists(wall, zone):
        out.add("dtstart-in-gap")
    elif _ambiguous(wall, zone):
        out.add("dtstart-ambiguous")
    walls = _expand(ref, spec.core(), wall, len(found) * 3 + 10, _wall(found[-1]))
    if any(not _exists(w, zone) for w in walls):
        out.add("instance-in-gap")
    if any(_ambiguous(w, zone) for w in walls[1:]):
        out.add("instance-ambiguous")
    if spec.freq in SUBDAILY:
        offsets = [value.utcoffset() for value in found]
        pairs = list(zip(offsets, offsets[1:], strict=False))
        if any(b is not None and a is not None and b < a for a, b in pairs):
            out.add("subdaily-fallback")
        if any(b is not None and a is not None and b > a for a, b in pairs):
            out.add("subdaily-springforward")
    return out


def _static(spec: Spec, dtstart: datetime, text: str) -> set[str]:
    ordinal = any(o is not None for o, _ in spec.byday)
    others = (spec.bymonth, spec.bymonthday, spec.byyearday, spec.byweekno, spec.byday, spec.byhour, spec.byminute, spec.bysecond)
    interval = 1 if spec.interval is None else spec.interval
    flags = {
        "yearly-monthday-nomonth": spec.freq == "YEARLY" and bool(spec.bymonthday) and not (spec.bymonth or spec.byweekno or spec.byyearday),
        "count-zero": spec.count == 0,
        "setpos-alone": bool(spec.bysetpos) and not any(others),
        "weekno-without-byday": bool(spec.byweekno) and not spec.byday,
        "weekno-interval": bool(spec.byweekno) and interval > 1,
        "weekno-negative": any(w < 0 for w in spec.byweekno),
        "yearly-ordinal-byday-nomonth": spec.freq == "YEARLY" and ordinal and not spec.bymonth,
        "yearly-ordinal-byday-bymonth": spec.freq == "YEARLY" and ordinal and bool(spec.bymonth),
        "leap-second": 60 in spec.bysecond,  # noqa: PLR2004 - the leap second
        "until-floating-local": spec.until is not None and dtstart.tzinfo is None,
        "until-utc-aware": spec.until is not None and dtstart.tzinfo is not None,
        "parse-case-or-prefix": text != text.upper() or text.upper().startswith("RRULE:"),
        "interval-negative": interval < 0,
        "interval-zero": interval == 0,
        "monthday-out-of-range": any(d == 0 or abs(d) > 31 for d in spec.bymonthday),  # noqa: PLR2004
        "monthly-day-29-31": spec.freq == "MONTHLY" and not spec.bymonthday and not spec.byday and dtstart.day > 28,  # noqa: PLR2004
        "weekly-interval-wkst": spec.freq == "WEEKLY" and interval > 1,
    }
    return {name for name, hit in flags.items() if hit}


def classify(ref: Reference, spec: Spec, dtstart: datetime, limit: int, text: str | None = None) -> frozenset[str]:
    """Every family the case belongs to."""
    rule_string = rule_text(spec) if text is None else text
    out = _static(spec, dtstart, rule_string)
    try:
        rule = ref.parse_rrule(rule_string)
        if not ref.synchronized(rule, dtstart):
            out.add("unsynchronized-dtstart")
        found = ref.expand(rule, dtstart, limit=limit)
    except ref.invalid:
        return frozenset(out)
    if spec.byweekno:
        wkst = DAYS.index(spec.wkst or "MO")
        if any(week_year(_wall(v).date(), wkst) != _wall(v).year for v in found):
            out.add("weekno-crosses-year")
    out |= _zoned(ref, spec, dtstart, found) | _setpos(ref, spec, dtstart, found)
    return frozenset(out)
