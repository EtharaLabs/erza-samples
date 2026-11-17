"""Parser for the RECUR value grammar of RFC 5545 section 3.3.10."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Final

from .model import Freq, InvalidRule, Rule, Weekday, WeekdayNum

_GRAMMAR: Final = 2116
_DIGITS: Final = re.compile(r"[0-9]+")
_SIGNED: Final = re.compile(r"([+-]?)([0-9]+)")
_WEEKDAYNUM: Final = re.compile(r"(?:([+-]?)([0-9]{1,2}))?([A-Za-z]{2})")
_ENDDATE: Final = re.compile(r"([0-9]{4})([0-9]{2})([0-9]{2})(?:[Tt]([0-9]{2})([0-9]{2})([0-9]{2})([Zz]?))?")
_PARTS: Final = frozenset({
    "FREQ", "UNTIL", "COUNT", "INTERVAL", "BYSECOND", "BYMINUTE", "BYHOUR", "BYDAY",
    "BYMONTHDAY", "BYYEARDAY", "BYWEEKNO", "BYMONTH", "BYSETPOS", "WKST",
})


def parse_rrule(text: str) -> Rule:
    """Parse a RECUR value (grammar lines 2116-2213) into a :class:`Rule`.

    Rule parts may come in any order (lines 2118-2119, 2220-2221); FREQ is
    required and no part may repeat (lines 2121-2122, 2135-2136, 2219-2220);
    UNTIL and COUNT must not both occur (lines 2124-2125). Part names and
    enumerated values are matched case-insensitively (lines 591-592; quoted
    ABNF literals are case-insensitive per RFC 5234). A leading ``RRULE:``
    property name is accepted and stripped as a convenience. Every numeric
    field is checked against its grammar width and stated range; INTERVAL 0
    is rejected because INTERVAL is "a positive integer" (line 2247).
    """
    body = text.strip()
    if body[:6].upper() == "RRULE:":
        body = body[6:]
    seen: dict[str, str] = {}
    for part in body.split(";"):
        name, sep, value = part.partition("=")
        key = name.upper()
        if not sep or not value:
            raise InvalidRule(f"malformed rule part {part!r}", _GRAMMAR)
        if key not in _PARTS:
            raise InvalidRule(f"unknown rule part {name!r}", 2138)
        if key in seen:
            raise InvalidRule(f"rule part {key} occurs more than once", 2219)
        seen[key] = value
    if "FREQ" not in seen:
        raise InvalidRule("FREQ rule part is required", 2121)
    if "UNTIL" in seen and "COUNT" in seen:
        raise InvalidRule("UNTIL and COUNT must not occur in the same recur", 2124)
    return Rule(
        freq=_freq(seen["FREQ"]),
        until=_enddate(seen["UNTIL"]) if "UNTIL" in seen else None,
        count=_unsigned(seen["COUNT"], 0, None, None, 2140) if "COUNT" in seen else None,
        interval=_unsigned(seen.get("INTERVAL", "1"), 1, None, None, 2247),
        bysecond=_ulist(seen.get("BYSECOND"), 0, 60, 2, 2160),
        byminute=_ulist(seen.get("BYMINUTE"), 0, 59, 2, 2164),
        byhour=_ulist(seen.get("BYHOUR"), 0, 23, 2, 2168),
        byday=_bydaylist(seen.get("BYDAY")),
        bymonthday=_slist(seen.get("BYMONTHDAY"), 31, 2, 2319),
        byyearday=_slist(seen.get("BYYEARDAY"), 366, 3, 2325),
        byweekno=_slist(seen.get("BYWEEKNO"), 53, 2, 2332),
        bymonth=_ulist(seen.get("BYMONTH"), 1, 12, 2, 2209),
        bysetpos=_slist(seen.get("BYSETPOS"), 366, 3, 2370),
        wkst=_weekday(seen.get("WKST", "MO")),
    )


def _freq(value: str) -> Freq:
    try:
        return Freq(value.upper())
    except ValueError:
        raise InvalidRule(f"unknown FREQ value {value!r}", 2153) from None


def _weekday(value: str) -> Weekday:
    try:
        return Weekday[value.upper()]
    except KeyError:
        raise InvalidRule(f"unknown weekday {value!r}", 2180) from None


def _unsigned(token: str, low: int, high: int | None, width: int | None, line: int) -> int:
    """Parse ``1*<width>DIGIT`` and check ``low <= n (<= high)``."""
    if _DIGITS.fullmatch(token) is None or (width is not None and len(token) > width):
        raise InvalidRule(f"malformed number {token!r}", line)
    number = int(token)
    if number < low or (high is not None and number > high):
        raise InvalidRule(f"value {number} outside {low}..{high}", line)
    return number


def _signed(token: str, high: int, width: int, line: int) -> int:
    """Parse ``[plus / minus] 1*<width>DIGIT`` with 1 <= abs(n) <= high."""
    match = _SIGNED.fullmatch(token)
    if match is None or len(match.group(2)) > width:
        raise InvalidRule(f"malformed signed number {token!r}", line)
    magnitude = int(match.group(2))
    if not 1 <= magnitude <= high:
        raise InvalidRule(f"value {token} outside 1..{high} or -{high}..-1", line)
    return -magnitude if match.group(1) == "-" else magnitude


def _items(value: str, line: int) -> list[str]:
    items = value.split(",")
    if any(not item for item in items):
        raise InvalidRule(f"empty list element in {value!r}", line)
    return items


def _ulist(value: str | None, low: int, high: int, width: int, line: int) -> tuple[int, ...]:
    if value is None:
        return ()
    return tuple(_unsigned(item, low, high, width, line) for item in _items(value, line))


def _slist(value: str | None, high: int, width: int, line: int) -> tuple[int, ...]:
    if value is None:
        return ()
    return tuple(_signed(item, high, width, line) for item in _items(value, line))


def _bydaylist(value: str | None) -> tuple[WeekdayNum, ...]:
    if value is None:
        return ()
    result: list[WeekdayNum] = []
    for item in _items(value, 2170):
        match = _WEEKDAYNUM.fullmatch(item)
        if match is None:
            raise InvalidRule(f"malformed BYDAY element {item!r}", 2172)
        sign, digits, name = match.groups()
        ordinal: int | None = None
        if digits:
            ordinal = _signed(f"{sign}{digits}", 53, 2, 2178)
        result.append(WeekdayNum(_weekday(name), ordinal))
    return tuple(result)


def _enddate(value: str) -> date | datetime:
    """Parse ``enddate = date / date-time`` (lines 2156, 1764-1767, 2593-2600).

    A second value of 60 (a positive leap second) is read as 59, as lines
    1916-1917 recommend for implementations without leap-second support.
    """
    match = _ENDDATE.fullmatch(value)
    if match is None:
        raise InvalidRule(f"malformed UNTIL value {value!r}", 2156)
    year, month, mday, hour, minute, second, zulu = match.groups()
    try:
        day = date(int(year), int(month), int(mday))
    except ValueError:
        raise InvalidRule(f"UNTIL date {value!r} does not exist", 1767) from None
    if hour is None or minute is None or second is None:
        return day
    h, m, s = int(hour), int(minute), int(second)
    if h > 23 or m > 59 or s > 60:  # noqa: PLR2004 - ranges of lines 2595-2597
        raise InvalidRule(f"UNTIL time {value!r} out of range", 2595)
    stamp = datetime(day.year, day.month, day.day, h, m, min(s, 59))
    return stamp.replace(tzinfo=UTC) if zulu else stamp
