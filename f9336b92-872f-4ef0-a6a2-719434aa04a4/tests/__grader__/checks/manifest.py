"""C08: the shipped tree's file manifest, and the files a submission changed outside its scope.

The manifest maps every regular file's tree-relative POSIX path to its SHA-256. Files under
``src/dateutil/`` and ``tests/`` are the submission's to change and are left out of the
comparison. Version-control and tool caches are ignored on both sides. Walking never follows a
symbolic link; a link outside the allowed areas counts as a change.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ALLOWED: Final = ("src/dateutil/", "tests/")
IGNORED_DIRS: Final = frozenset(
    {".git", "__pycache__", ".pytest_cache", ".hypothesis", ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".venv", "venv"}
)
IGNORED_SUFFIXES: Final = (".pyc", ".pyo")
MAX_FILES: Final = 50_000


class ShippedTreeError(ValueError):
    """The shipped tree holds an entry a manifest cannot describe."""

    def __init__(self, paths: list[str]) -> None:
        super().__init__(f"shipped tree holds non-regular entries: {paths[:5]}")
        self.paths: Final = paths


@dataclass(frozen=True, slots=True)
class Entry:
    """One path: a file digest, or ``link``/``other`` for anything that is not a regular file."""

    kind: str
    digest: str


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def scan(root: Path, *, skip_allowed: bool) -> dict[str, Entry]:
    """Every non-ignored entry under ``root`` by relative path, without following links."""
    found: dict[str, Entry] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        here = Path(current)
        kept = []
        for name in sorted(dirs):
            child = here / name
            if name in IGNORED_DIRS or name.endswith(".egg-info"):
                continue
            if child.is_symlink():
                files.append(name)
                continue
            kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            if name.endswith(IGNORED_SUFFIXES):
                continue
            path = here / name
            relative = path.relative_to(root).as_posix()
            if skip_allowed and relative.startswith(ALLOWED):
                continue
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                found[relative] = Entry("file", _digest(path))
            elif stat.S_ISLNK(mode):
                found[relative] = Entry("link", os.readlink(path))
            else:
                found[relative] = Entry("other", "")
            if len(found) > MAX_FILES:
                found["<too many files>"] = Entry("other", "")
                return found
    return found


def manifest(root: Path) -> dict[str, str]:
    """The shipped tree's manifest outside the allowed areas: path to SHA-256."""
    entries = scan(root, skip_allowed=True)
    odd = sorted(path for path, entry in entries.items() if entry.kind != "file")
    if odd:
        raise ShippedTreeError(odd)
    return {path: entry.digest for path, entry in sorted(entries.items())}


def changed(shipped: dict[str, str], workspace: Path) -> list[str]:
    """Paths outside ``src/dateutil/`` and ``tests/`` that differ from the shipped manifest."""
    if not workspace.is_dir() or workspace.is_symlink():
        return ["<workspace tree missing>"]
    present = scan(workspace, skip_allowed=True)
    diffs = {path for path in shipped if path not in present}
    for path, entry in present.items():
        if entry.kind != "file" or shipped.get(path) != entry.digest:
            diffs.add(path)
    return sorted(diffs)
