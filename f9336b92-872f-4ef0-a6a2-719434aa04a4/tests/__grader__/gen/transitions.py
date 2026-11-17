"""UTC-offset transitions of an IANA zone, found from the zone data the image carries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class Transition:
    """One offset change: the first instant under the new offset and the wall times around it.

    ``wall`` is the local wall time at which the change happens under the old offset, for
    example 02:00 on a New York spring-forward day. ``shift`` is new offset minus old offset:
    positive for a gap (spring forward), negative for a repeated span (fall back).
    """

    zone: ZoneInfo
    instant: datetime
    wall: datetime
    shift: timedelta

    @property
    def day(self) -> date:
        return self.wall.date()

    @property
    def spring(self) -> bool:
        return self.shift > timedelta(0)

    def odd_span(self) -> tuple[datetime, datetime]:
        """Naive wall times ``[start, end)`` that are nonexistent (spring) or repeated (fall)."""
        if self.spring:
            return self.wall, self.wall + self.shift
        return self.wall + self.shift, self.wall


def _offset(zone: ZoneInfo, instant: datetime) -> timedelta:
    found = instant.astimezone(zone).utcoffset()
    return found if found is not None else timedelta(0)


def _locate(zone: ZoneInfo, low: datetime, high: datetime) -> datetime:
    """The first second in ``(low, high]`` whose offset differs from ``low``'s."""
    before = _offset(zone, low)
    lo, hi = 0, int((high - low).total_seconds())
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _offset(zone, low + timedelta(seconds=mid)) == before:
            lo = mid
        else:
            hi = mid
    return low + timedelta(seconds=hi)


def transitions(zone: ZoneInfo, first_year: int, last_year: int) -> list[Transition]:
    """Every offset change between 1 January ``first_year`` and 31 December ``last_year``."""
    found: list[Transition] = []
    probe = datetime(first_year, 1, 1, 12, tzinfo=UTC)
    stop = datetime(last_year, 12, 31, 12, tzinfo=UTC)
    while probe < stop:
        after = probe + timedelta(days=1)
        old, new = _offset(zone, probe), _offset(zone, after)
        if old != new:
            instant = _locate(zone, probe, after)
            wall = (instant + old).replace(tzinfo=None)
            found.append(Transition(zone, instant, wall, new - old))
        probe = after
    return found
