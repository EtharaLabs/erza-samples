"""Canonical JSON bytes: RFC 8785 serialization plus one LF.

It renders validated JSON values only; parsing rejects duplicate keys and non-finite numbers.
"""

from __future__ import annotations

import json
import math
from typing import Final, Never

type JSONScalar = bool | int | float | str | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]

_MAX_SAFE: Final = (1 << 53) - 1
_SHORT: Final = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


class CanonicalError(ValueError):
    """A value or document with no canonical JSON form."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason: Final = reason


def _string(value: str) -> str:
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise CanonicalError("lone surrogate in string")
    out = ['"']
    for ch in value:
        short = _SHORT.get(ch)
        if short is not None:
            out.append(short)
        elif ord(ch) <= 0x1F:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise CanonicalError("non-finite number")
    if value == 0.0:
        return "0"
    rendered = repr(value)
    sign = "-" if rendered.startswith("-") else ""
    rendered = rendered.lstrip("-")
    mantissa, sep, exp_text = rendered.partition("e")
    exponent = int(exp_text) if sep else 0
    whole, point, fraction = mantissa.partition(".")
    digits = whole + fraction if point else whole
    leading = len(digits) - len(digits.lstrip("0"))
    digits = digits.lstrip("0").rstrip("0")
    position = len(whole) + exponent - leading
    if 0 < position <= 21:
        if len(digits) <= position:
            return sign + digits + "0" * (position - len(digits))
        return sign + digits[:position] + "." + digits[position:]
    if -6 < position <= 0:
        return sign + "0." + "0" * -position + digits
    significand = digits[0] if len(digits) == 1 else f"{digits[0]}.{digits[1:]}"
    power = position - 1
    return f"{sign}{significand}e{'+' if power >= 0 else ''}{power}"


def _render(value: JSONValue) -> str:
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case str():
            return _string(value)
        case int():
            if abs(value) > _MAX_SAFE:
                raise CanonicalError("integer outside the binary64 safe range")
            return _number(float(value))
        case float():
            return _number(value)
        case list():
            return "[" + ",".join(_render(item) for item in value) + "]"
        case dict():
            keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
            return "{" + ",".join(f"{_string(key)}:{_render(value[key])}" for key in keys) + "}"


def canonicalize(value: JSONValue) -> bytes:
    """Canonical UTF-8 JSON with exactly one terminating LF."""
    return f"{_render(value)}\n".encode()


def _pairs(pairs: list[tuple[str, JSONValue]]) -> dict[str, JSONValue]:
    out: dict[str, JSONValue] = {}
    for key, item in pairs:
        if key in out:
            raise CanonicalError(f"duplicate key {key!r}")
        out[key] = item
    return out


def _constant(token: str) -> Never:
    raise CanonicalError(f"non-finite constant {token}")


def parse_json(raw: bytes) -> JSONValue:
    """One strict JSON document: UTF-8, no duplicate keys, no NaN or Infinity."""
    try:
        text = raw.decode("utf-8")
        parsed: JSONValue = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise CanonicalError(f"not strict JSON: {error}") from None
    return parsed
