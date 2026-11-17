"""Refuse a ``dateutil`` imported from anywhere but the library root under test.

The image's site-packages carries an unrelated python-dateutil (a dependency of the grader's
own tooling). A submission without ``src/dateutil`` must not be graded against it.
"""

from __future__ import annotations

import sys
from pathlib import Path


class WrongLibraryError(ImportError):
    """``dateutil`` resolved outside the library root."""

    def __init__(self, origin: str) -> None:
        super().__init__(f"dateutil imported from {origin}")


def require_root(library: str) -> None:
    """Raise unless the imported ``dateutil`` package lives under ``library``."""
    module = sys.modules.get("dateutil")
    origin = str(getattr(module, "__file__", "") or "")
    if not origin or not Path(origin).resolve().is_relative_to(Path(library).resolve()):
        raise WrongLibraryError(origin or "<nowhere>")
