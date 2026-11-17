"""Structured rule specifications, their RRULE text and dateutil keyword forms, and case records.

A ``Spec`` is rendered twice: as RFC 5545 RECUR text for ``rrulestr`` and as the keyword set of
the equivalent ``rrule(...)`` call. A ``Case`` is one grading input; it never carries an
expected value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

from canonical import JSONValue

FREQS: Final = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY")
DAYS: Final = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_DTSTART: Final = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|\[([A-Za-z_]+(?:/[A-Za-z_]+)*)\])?")

type DayNum = tuple[int | None, str]


class UnsupportedZoneError(TypeError):
    """A DTSTART tzinfo that is neither UTC nor an IANA ZoneInfo."""

    def __init__(self, tzinfo: str) -> None:
        super().__init__(f"unsupported DTSTART tzinfo {tzinfo}")
        self.tzinfo: Final = tzinfo


class MalformedTextError(ValueError):
    """A DTSTART or bound string outside the case grammar."""

    def __init__(self, text: str) -> None:
        super().__init__(f"malformed value {text!r}")
        self.text: Final = text


@dataclass(frozen=True, slots=True)
class Spec:
    """One RECUR value; an empty tuple or ``None`` means the part is absent."""

    freq: str
    interval: int | None = None
    count: int | None = None
    until: datetime | None = None
    wkst: str | None = None
    bysetpos: tuple[int, ...] = ()
    bymonth: tuple[int, ...] = ()
    bymonthday: tuple[int, ...] = ()
    byyearday: tuple[int, ...] = ()
    byweekno: tuple[int, ...] = ()
    byday: tuple[DayNum, ...] = ()
    byhour: tuple[int, ...] = ()
    byminute: tuple[int, ...] = ()
    bysecond: tuple[int, ...] = ()

    def core(self) -> Spec:
        """The same rule without COUNT and UNTIL."""
        return replace(self, count=None, until=None)


def _ints(values: tuple[int, ...]) -> str:
    return ",".join(str(v) for v in values)


def _day(day: DayNum) -> str:
    ordinal, name = day
    return name if ordinal is None else f"{ordinal}{name}"


def until_text(until: datetime) -> str:
    """RFC 5545 UNTIL: UTC ``Z`` form for an aware value, local form for a naive one."""
    if until.tzinfo is None:
        return until.strftime("%Y%m%dT%H%M%S")
    return until.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def until_iso(until: datetime) -> str:
    """The UNTIL keyword value as the case carries it: ISO, ``Z`` when aware."""
    if until.tzinfo is None:
        return until.isoformat()
    return until.astimezone(UTC).replace(tzinfo=None).isoformat() + "Z"


def rule_text(spec: Spec) -> str:
    """RECUR text in a fixed part order."""
    parts = [f"FREQ={spec.freq}"]
    if spec.interval is not None:
        parts.append(f"INTERVAL={spec.interval}")
    if spec.count is not None:
        parts.append(f"COUNT={spec.count}")
    if spec.until is not None:
        parts.append(f"UNTIL={until_text(spec.until)}")
    lists = (
        ("BYMONTH", spec.bymonth),
        ("BYWEEKNO", spec.byweekno),
        ("BYYEARDAY", spec.byyearday),
        ("BYMONTHDAY", spec.bymonthday),
    )
    parts.extend(f"{name}={_ints(values)}" for name, values in lists if values)
    if spec.byday:
        parts.append("BYDAY=" + ",".join(_day(d) for d in spec.byday))
    times = (("BYHOUR", spec.byhour), ("BYMINUTE", spec.byminute), ("BYSECOND", spec.bysecond))
    parts.extend(f"{name}={_ints(values)}" for name, values in times if values)
    if spec.bysetpos:
        parts.append(f"BYSETPOS={_ints(spec.bysetpos)}")
    if spec.wkst is not None:
        parts.append(f"WKST={spec.wkst}")
    return ";".join(parts)


def rule_kwargs(spec: Spec) -> dict[str, JSONValue]:
    """The keyword arguments of the equivalent ``rrule(...)`` call, present parts only."""
    out: dict[str, JSONValue] = {"freq": spec.freq}
    scalars = (("interval", spec.interval), ("count", spec.count))
    out.update({name: value for name, value in scalars if value is not None})
    if spec.until is not None:
        out["until"] = until_iso(spec.until)
    if spec.wkst is not None:
        out["wkst"] = spec.wkst
    lists = (
        ("bysetpos", spec.bysetpos),
        ("bymonth", spec.bymonth),
        ("bymonthday", spec.bymonthday),
        ("byyearday", spec.byyearday),
        ("byweekno", spec.byweekno),
        ("byhour", spec.byhour),
        ("byminute", spec.byminute),
        ("bysecond", spec.bysecond),
    )
    out.update({name: list(values) for name, values in lists if values})
    if spec.byday:
        out["byweekday"] = [[name, ordinal] for ordinal, name in spec.byday]
    return out


def format_dtstart(value: datetime) -> str:
    """``YYYY-MM-DDTHH:MM:SS`` plus ``Z`` (UTC) or ``[Zone/Name]`` (IANA zone)."""
    wall = value.replace(tzinfo=None, fold=0).isoformat()
    match value.tzinfo:
        case None:
            return wall
        case ZoneInfo() as zone:
            return f"{wall}[{zone.key}]"
        case timezone() as fixed if not fixed.utcoffset(None):
            return f"{wall}Z"
        case other:
            raise UnsupportedZoneError(repr(other))


def parse_dtstart(text: str) -> datetime:
    """Inverse of :func:`format_dtstart`."""
    match = _DTSTART.fullmatch(text)
    if match is None:
        raise MalformedTextError(text)
    wall = datetime.fromisoformat(match.group(1))
    if match.group(2) is None:
        return wall
    if match.group(2) == "Z":
        return wall.replace(tzinfo=UTC)
    return wall.replace(tzinfo=ZoneInfo(match.group(3)))


def parse_bound(text: str) -> datetime:
    """A window or pivot bound: naive ISO, or ISO with ``Z`` for UTC."""
    if text.endswith("Z"):
        return datetime.fromisoformat(text[:-1]).replace(tzinfo=UTC)
    return datetime.fromisoformat(text)


def format_bound(value: datetime) -> str:
    """Inverse of :func:`parse_bound`; aware values are written in UTC."""
    if value.tzinfo is None:
        return value.isoformat()
    return value.astimezone(UTC).replace(tzinfo=None).isoformat() + "Z"


@dataclass(frozen=True, slots=True)
class Probe:
    """An ``after``/``before`` pivot, or a ``between`` window when ``end`` is set."""

    start: str
    inc: bool
    end: str | None = None


@dataclass(frozen=True, slots=True)
class Case:
    """One grading input: a rule, its DTSTART, the instance limit, and which API probes run."""

    id: str
    rule: str
    dtstart: str
    limit: int
    kw: dict[str, JSONValue] | None
    count: bool
    window: Probe | None
    after: Probe | None
    before: Probe | None

    def to_json(self) -> dict[str, JSONValue]:
        """The JSON line the child and the scorer read."""

        def probe(p: Probe | None, *, window: bool) -> JSONValue:
            if p is None:
                return None
            if window:
                return {"start": p.start, "end": p.end, "inc": p.inc}
            return {"at": p.start, "inc": p.inc}

        return {
            "id": self.id,
            "rule": self.rule,
            "dtstart": self.dtstart,
            "limit": self.limit,
            "kw": self.kw,
            "count": self.count,
            "window": probe(self.window, window=True),
            "after": probe(self.after, window=False),
            "before": probe(self.before, window=False),
        }


_DAYNUM: Final = re.compile(r"([+-]?\d{1,2})?([A-Z]{2})")
_UNTIL: Final = re.compile(r"(\d{8}T\d{6})(Z?)")


def spec_from_text(text: str) -> Spec:
    """Inverse of :func:`rule_text` for the texts the generators write."""
    parts = dict(part.split("=", 1) for part in text.split(";"))

    def ints(name: str) -> tuple[int, ...]:
        return tuple(int(v) for v in parts[name].split(",")) if name in parts else ()

    days: list[DayNum] = []
    for item in parts.get("BYDAY", "").split(",") if "BYDAY" in parts else []:
        match = _DAYNUM.fullmatch(item)
        if match is None:
            raise MalformedTextError(item)
        days.append((int(match.group(1)) if match.group(1) else None, match.group(2)))
    until = None
    if "UNTIL" in parts:
        match = _UNTIL.fullmatch(parts["UNTIL"])
        if match is None:
            raise MalformedTextError(parts["UNTIL"])
        until = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")
        until = until.replace(tzinfo=UTC) if match.group(2) else until
    single = {name: int(parts[name]) if name in parts else None for name in ("INTERVAL", "COUNT")}
    return Spec(
        parts["FREQ"], interval=single["INTERVAL"], count=single["COUNT"], until=until, wkst=parts.get("WKST"),
        bysetpos=ints("BYSETPOS"), bymonth=ints("BYMONTH"), bymonthday=ints("BYMONTHDAY"),
        byyearday=ints("BYYEARDAY"), byweekno=ints("BYWEEKNO"), byday=tuple(days),
        byhour=ints("BYHOUR"), byminute=ints("BYMINUTE"), bysecond=ints("BYSECOND"),
    )
