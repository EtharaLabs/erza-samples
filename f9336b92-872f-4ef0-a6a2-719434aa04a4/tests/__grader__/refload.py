"""Load the RFC 5545 reference expander from a fixed directory, as the grader alone does.

The verifier image holds the package at ``/opt/grader/ref/rfc5545ref``. Only grader-side
processes (case generation and scoring) import it; the sandboxed child never does.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Protocol

DEFAULT_ROOT: Final = Path("/opt/grader/ref")


class Rule(Protocol):
    """The parsed rule; only ``count`` is read outside the reference."""

    @property
    def count(self) -> int | None: ...


class Expand(Protocol):
    def __call__(
        self, rule: Rule, dtstart: datetime, *, limit: int, until_cap: datetime | None = None
    ) -> list[datetime]: ...


@dataclass(frozen=True, slots=True)
class Reference:
    """The reference API the harness relies on, bound from the imported package."""

    invalid: type[ValueError]
    parse_rrule: Callable[[str], Rule]
    validate: Callable[[Rule, datetime], None]
    synchronized: Callable[[Rule, datetime], bool]
    expand: Expand


class ReferenceMissingError(ImportError):
    """The reference package is absent, misplaced, or lacks part of its API."""

    def __init__(self, root: Path, missing: str) -> None:
        super().__init__(f"rfc5545ref under {root} lacks {missing}")
        self.root: Final = root


def load_reference(root: Path = DEFAULT_ROOT) -> Reference:
    """Import ``rfc5545ref`` from ``root`` and bind the API the harness uses."""
    entry = str(root.resolve())
    if entry not in sys.path:
        sys.path.insert(0, entry)
    module = importlib.import_module("rfc5545ref")
    origin = Path(str(module.__file__)).resolve()
    if not origin.is_relative_to(root.resolve()):
        raise ReferenceMissingError(root, f"a package loaded from it (got {origin})")
    names = ("InvalidRule", "parse_rrule", "validate", "synchronized", "expand")
    missing = [name for name in names if not hasattr(module, name)]
    if missing:
        raise ReferenceMissingError(root, ", ".join(missing))
    invalid = module.InvalidRule
    if not (isinstance(invalid, type) and issubclass(invalid, ValueError)):
        raise ReferenceMissingError(root, "an InvalidRule subclass of ValueError")
    return Reference(invalid, module.parse_rrule, module.validate, module.synchronized, module.expand)
