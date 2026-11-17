"""DATE-TIME forms and local-time resolution (RFC 5545 section 3.3.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import assert_never
from zoneinfo import ZoneInfo

from .model import InvalidRule


@dataclass(frozen=True, slots=True)
class Floating:
    """FORM #1, date with local time (lines 1824-1865): a naive datetime."""


@dataclass(frozen=True, slots=True)
class Utc:
    """FORM #2, date with UTC time (lines 1867-1877): tzinfo ``timezone.utc``."""


@dataclass(frozen=True, slots=True)
class Zoned:
    """FORM #3, local time with TZID reference (lines 1879-1899): a ZoneInfo."""

    zone: ZoneInfo


type TimeForm = Floating | Utc | Zoned


def form_of(value: datetime) -> TimeForm:
    """Classify a DTSTART value into one of the three forms of lines 1817-1899.

    Any other tzinfo (a fixed UTC offset other than zero, or a non-zoneinfo
    zone) is rejected: "The form of date and time with UTC offset MUST NOT be
    used" (lines 1819-1822). Sub-second values do not exist in the grammar
    ``time-hour time-minute time-second`` (line 2593) and are rejected too.
    """
    if value.microsecond:
        raise InvalidRule("DATE-TIME has no sub-second precision", 2593)
    tz = value.tzinfo
    match tz:
        case None:
            return Floating()
        case ZoneInfo():
            return Zoned(tz)
        case timezone() if tz.utcoffset(None) == timedelta(0):
            return Utc()
        case _:
            raise InvalidRule("UTC-offset or non-IANA tzinfo is not a DATE-TIME form", 1819)


def wall_clock(value: datetime) -> datetime:
    """The naive local date and time written in the DATE-TIME value.

    For a zoned value the ``fold`` attribute is discarded: a DATE-TIME names
    a wall time, and lines 1889-1892 fix which occurrence it denotes.
    """
    return value.replace(tzinfo=None, fold=0)


def localize(wall: datetime, form: TimeForm) -> datetime | None:
    """Attach ``form`` to a computed wall time; ``None`` if it does not exist.

    An ambiguous local time denotes its first occurrence (lines 1889-1894),
    represented with ``fold=0``. A local time inside a gap is a "nonexistent
    local time" and the instance "MUST be ignored and MUST NOT be counted"
    (lines 2382-2386), signalled here by ``None``.
    """
    match form:
        case Floating():
            return wall
        case Utc():
            return wall.replace(tzinfo=UTC)
        case Zoned(zone=zone):
            aware = wall.replace(tzinfo=zone, fold=0)
            if aware.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != wall:
                return None
            return aware
        case unreachable:
            assert_never(unreachable)


def localize_start(wall: datetime, form: TimeForm) -> datetime:
    """Resolve DTSTART itself, which always denotes an instant.

    A DTSTART that falls in a gap "is interpreted using the UTC offset before
    the gap" (lines 1894-1899): 02:30 on a 02:00->03:00 spring-forward day
    becomes 03:30 in the new offset. The result is normalized to that real
    wall time (``fold=0``) so that it compares equal, by wall time and by
    instant, to any other representation of the same moment.
    """
    resolved = localize(wall, form)
    if resolved is not None:
        return resolved
    match form:
        case Zoned(zone=zone):
            return wall.replace(tzinfo=zone, fold=0).astimezone(UTC).astimezone(zone)
        case Floating() | Utc():
            return wall
        case unreachable:
            assert_never(unreachable)


def instant(value: datetime) -> datetime:
    """Ordering key: absolute UTC instant for aware values, wall time otherwise."""
    return value if value.tzinfo is None else value.astimezone(UTC)
