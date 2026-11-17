"""The child's input and output encodings, shared by nothing the grader imports.

The scorer re-implements the output grammar on its side; this module exists only inside the
sandbox runner so the child never reaches grader code.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Final
from zoneinfo import ZoneInfo

_DTSTART: Final = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|\[([A-Za-z_]+(?:/[A-Za-z_]+)*)\])?")
ERROR_NAME_LIMIT: Final = 100


class CaseFormatError(ValueError):
    """A case line the child cannot read."""

    def __init__(self, text: str) -> None:
        super().__init__(f"unreadable case value {text[:80]!r}")


def parse_dtstart(text: str) -> datetime:
    """``YYYY-MM-DDTHH:MM:SS`` with an optional ``Z`` or ``[Zone/Name]`` suffix."""
    match = _DTSTART.fullmatch(text)
    if match is None:
        raise CaseFormatError(text)
    wall = datetime.fromisoformat(match.group(1))
    if match.group(2) is None:
        return wall
    if match.group(2) == "Z":
        return wall.replace(tzinfo=UTC)
    return wall.replace(tzinfo=ZoneInfo(match.group(3)))


def parse_bound(text: str) -> datetime:
    """A pivot or window bound: naive ISO, or ISO with ``Z`` for UTC."""
    if text.endswith("Z"):
        return datetime.fromisoformat(text[:-1]).replace(tzinfo=UTC)
    return datetime.fromisoformat(text)


def instance_text(value: datetime) -> str:
    """ISO 8601 with the UTC offset when aware, then ``#`` and the fold."""
    return f"{value.isoformat()}#{value.fold}"


def error_name(error: BaseException) -> str:
    """``ValueError`` for any ValueError, otherwise the qualified class name, bounded."""
    if isinstance(error, ValueError):
        return "ValueError"
    kind = type(error)
    name = kind.__qualname__ if kind.__module__ == "builtins" else f"{kind.__module__}.{kind.__qualname__}"
    cleaned = re.sub(r"[^A-Za-z0-9_.]", "_", name)[:ERROR_NAME_LIMIT]
    return cleaned if re.match(r"[A-Za-z_]", cleaned) else "UnnamedError"
