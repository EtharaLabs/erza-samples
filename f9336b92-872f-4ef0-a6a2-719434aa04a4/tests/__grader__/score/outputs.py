"""Strict parsing of the child's output lines into typed records.

Every line must be one JSON object with exactly the keys the grammar allows, every instance a
canonical ISO 8601 string with ``#<fold>``, every error name an identifier. Anything else marks
the whole file malformed: the scorer never guesses at what a line meant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Never

from canonical import CanonicalError, JSONValue, parse_json

MAX_LINE: Final = 256 * 1024
MAX_FILE: Final = 64 * 1024 * 1024
MAX_INSTANCES: Final = 1001
INSTANCE: Final = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6})?(?:[+-]\d{2}:\d{2}(?::\d{2}(?:\.\d{6})?)?)?#[01]"
)
ERROR: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{0,99}")
CASE_ID: Final = re.compile(r"K[1-6]-\d{5}")
PROBES: Final = ("rule", "kw", "count", "between", "after", "before")


class MalformedOutputError(ValueError):
    """The child's output breaks the grammar; ``reason`` names the first violation."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason: Final = reason


@dataclass(frozen=True, slots=True)
class Failed:
    """A probe that raised: ``ValueError`` or another qualified type name."""

    error: str


@dataclass(frozen=True, slots=True)
class Listing:
    instances: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Number:
    value: int


@dataclass(frozen=True, slots=True)
class Point:
    instance: str | None


type Result = Failed | Listing | Number | Point


@dataclass(frozen=True, slots=True)
class Answer:
    """Every probe of one case; ``None`` where the case asked for no such probe."""

    id: str
    probes: dict[str, Result | None]


@dataclass(frozen=True, slots=True)
class Broken:
    """A line the child wrote when it could not run the case at all."""

    id: str
    reason: str


def _bad(reason: str) -> Never:
    raise MalformedOutputError(reason)


def _instance(value: JSONValue) -> str:
    if not isinstance(value, str) or INSTANCE.fullmatch(value) is None:
        _bad(f"non-ISO instance {str(value)[:60]!r}")
    return value


def _result(probe: str, value: JSONValue) -> Result:
    if not isinstance(value, dict) or len(value) != 1:
        _bad(f"{probe} must be an object with one key")
    (key, item), = value.items()
    match key, item:
        case "error", str(name) if ERROR.fullmatch(name):
            return Failed(name)
        case "instances", list(items) if probe in ("rule", "kw", "between") and len(items) <= MAX_INSTANCES:
            return Listing(tuple(_instance(i) for i in items))
        case "value", int(number) if probe == "count" and not isinstance(number, bool) and 0 <= number < 1 << 31:
            return Number(number)
        case "instance", None if probe in ("after", "before"):
            return Point(None)
        case "instance", str() if probe in ("after", "before"):
            return Point(_instance(item))
        case _:
            _bad(f"{probe} carries an unexpected {key!r}")


def parse_line(raw: bytes) -> Answer | Broken:
    """One output line, strictly."""
    if len(raw) > MAX_LINE:
        _bad("line exceeds the size limit")
    try:
        value = parse_json(raw)
    except CanonicalError as error:
        _bad(error.reason)
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or CASE_ID.fullmatch(str(value["id"])) is None:
        _bad("line lacks a valid case id")
    case_id = str(value["id"])
    keys = set(value)
    if keys == {"id", "import_error"} and isinstance(value["import_error"], str):
        return Broken(case_id, "import_error")
    if keys == {"id", "oversize"} and value["oversize"] is True:
        return Broken(case_id, "oversize")
    if keys == {"id", "exhausted"} and value["exhausted"] is True:
        return Broken(case_id, "exhausted")
    if keys != {"id", *PROBES}:
        _bad(f"{case_id} carries keys {sorted(keys)}")
    return Answer(case_id, {p: None if value[p] is None else _result(p, value[p]) for p in PROBES})


def parse_file(data: bytes) -> dict[str, Answer | Broken]:
    """Every line of one category file; a repeated case id is malformed."""
    if len(data) > MAX_FILE:
        _bad("output file exceeds the size limit")
    if data and not data.endswith(b"\n"):
        _bad("output does not end with a newline")
    found: dict[str, Answer | Broken] = {}
    for raw in data.split(b"\n")[:-1] if data else []:
        record = parse_line(raw)
        if record.id in found:
            _bad(f"{record.id} answered twice")
        found[record.id] = record
    return found

