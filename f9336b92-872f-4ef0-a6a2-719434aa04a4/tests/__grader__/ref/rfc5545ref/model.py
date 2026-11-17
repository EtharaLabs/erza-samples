"""Typed value objects for an RFC 5545 RECUR value (section 3.3.10).

Line numbers in docstrings refer to rfc5545.txt
(sha256 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum
from typing import Final


class InvalidRule(ValueError):
    """A RECUR value or a RECUR/DTSTART combination that RFC 5545 forbids.

    ``reason`` is a human-readable statement of the violated requirement and
    ``rfc_line`` the line of rfc5545.txt that states it (0 when the
    requirement is the grammar of lines 2116-2213 as a whole).
    """

    def __init__(self, reason: str, rfc_line: int) -> None:
        super().__init__(f"{reason} (RFC 5545 line {rfc_line})")
        self.reason: Final = reason
        self.rfc_line: Final = rfc_line

class HorizonError(ValueError):
    """DTSTART outside the supported years ``MIN_YEAR..MAX_YEAR``.

    Not an RFC rule: the expander works on ``datetime`` and keeps one year of
    slack at each end of its range for week arithmetic.
    """

    def __init__(self, year: int) -> None:
        super().__init__(f"DTSTART year {year} outside {MIN_YEAR}..{MAX_YEAR}")
        self.year: Final = year


MIN_YEAR: Final = 2
MAX_YEAR: Final = 9998


class Freq(StrEnum):
    """FREQ values, grammar lines 2153-2154."""

    SECONDLY = "SECONDLY"
    MINUTELY = "MINUTELY"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Weekday(IntEnum):
    """Weekdays, grammar line 2180; values equal ``date.weekday()``."""

    MO = 0
    TU = 1
    WE = 2
    TH = 3
    FR = 4
    SA = 5
    SU = 6


@dataclass(frozen=True, slots=True)
class WeekdayNum:
    """One BYDAY element ``[[plus / minus] ordwk] weekday`` (line 2172).

    ``ordinal`` is ``None`` when no integer modifier is present ("all days of
    this type within the specified frequency", lines 2309-2311); otherwise it
    is a signed value with 1 <= abs(ordinal) <= 53.
    """

    weekday: Weekday
    ordinal: int | None


@dataclass(frozen=True, slots=True)
class Rule:
    """A parsed RECUR value.

    ``until`` keeps the exact value form of the enddate (line 2156): a
    ``date`` (DATE form), a naive ``datetime`` (local-time form), or a
    ``datetime`` whose tzinfo is ``datetime.timezone.utc`` (UTC "Z" form).
    Every BYxxx tuple is empty when the rule part is absent. ``interval`` is
    1 when INTERVAL is absent (line 2248); ``wkst`` is MO when WKST is absent
    (line 2362).
    """

    freq: Freq
    until: date | datetime | None = None
    count: int | None = None
    interval: int = 1
    bysecond: tuple[int, ...] = ()
    byminute: tuple[int, ...] = ()
    byhour: tuple[int, ...] = ()
    byday: tuple[WeekdayNum, ...] = ()
    bymonthday: tuple[int, ...] = ()
    byyearday: tuple[int, ...] = ()
    byweekno: tuple[int, ...] = ()
    bymonth: tuple[int, ...] = ()
    bysetpos: tuple[int, ...] = ()
    wkst: Weekday = Weekday.MO

    def has_any_byxxx(self) -> bool:
        """Whether any BYxxx part other than BYSETPOS is present (line 2371)."""
        return bool(
            self.bysecond
            or self.byminute
            or self.byhour
            or self.byday
            or self.bymonthday
            or self.byyearday
            or self.byweekno
            or self.bymonth
        )
