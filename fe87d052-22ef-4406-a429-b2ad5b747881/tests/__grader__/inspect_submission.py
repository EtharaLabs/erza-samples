"""Decide admissibility and edit scope from the collected trees, without executing agent code.

Usage: python inspect_submission.py <grader dir> <results dir>

Writes verdict.json (refused, reasons, changed) and scope.json (readable, violations). The
library tree is walked without following any symbolic link; a link, a special file, or an
oversized tree refuses the submission. The allowed edit paths are include/fast_float/ and
tests/ under /workspace/fast_float; everything else there, and all of /workspace/spec, must
equal the shipped bytes.
"""

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

LIBRARY = Path("/workspace/fast_float")
SPEC = Path("/workspace/spec")
ALLOWED = ("include/fast_float/", "tests/")
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 2000


def walk(root: Path):
    """(relative path, sha256) for every regular file; raises ValueError on a link or special file."""
    out, total, count = {}, 0, 0
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{root} is not a real directory")
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames):
            if (Path(dirpath) / name).is_symlink():
                raise ValueError(f"symbolic link {Path(dirpath, name).relative_to(root)}")
        for name in filenames:
            path = Path(dirpath) / name
            info = os.lstat(path)
            rel = path.relative_to(root).as_posix()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"not a regular file: {rel}")
            count += 1
            total += info.st_size
            if info.st_size > MAX_FILE or total > MAX_TOTAL or count > MAX_FILES:
                raise ValueError("the collected tree exceeds the size limits")
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def main() -> None:
    grader, results = Path(sys.argv[1]), Path(sys.argv[2])
    shipped = json.loads((grader / "shipped_manifest.json").read_text())
    spec_shipped = json.loads((grader / "spec_manifest.json").read_text())
    verdict = {"refused": False, "reasons": [], "changed": False}
    scope = {"readable": False, "violations": []}
    try:
        tree = walk(LIBRARY)
    except (OSError, ValueError) as error:
        verdict.update(refused=True, reasons=[str(error)])
        tree = None
    if tree is not None:
        if "include/fast_float/fast_float.h" not in tree:
            verdict.update(refused=True, reasons=["include/fast_float/fast_float.h is missing"])
        include_now = {k: v for k, v in tree.items() if k.startswith(ALLOWED[0])}
        include_then = {k: v for k, v in shipped.items() if k.startswith(ALLOWED[0])}
        verdict["changed"] = include_now != include_then
        violations = []
        for rel in sorted(set(tree) | set(shipped)):
            if rel.startswith(ALLOWED):
                continue
            if tree.get(rel) != shipped.get(rel):
                violations.append(f"fast_float/{rel}")
        try:
            spec_now = walk(SPEC)
        except (OSError, ValueError) as error:
            violations.append(f"spec: {error}")
            spec_now = None
        if spec_now is not None:
            violations += [f"spec/{rel}" for rel in sorted(set(spec_now) | set(spec_shipped)) if spec_now.get(rel) != spec_shipped.get(rel)]
        scope = {"readable": True, "violations": violations}
    (results / "verdict.json").write_text(json.dumps(verdict, sort_keys=True))
    (results / "scope.json").write_text(json.dumps(scope, sort_keys=True))


if __name__ == "__main__":
    main()
