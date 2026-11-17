"""Decide, without running submitted code, whether the submission keeps the stated edit rules.

Usage: python3 inspect_submission.py <grader dir> <submission dir> <out json>

Refused when the module definition changed, when non-test library code imports a package the
library as shipped does not import, uses an os, syscall, unsafe, runtime, or reflect selector more
often than the library as shipped does, adds a package init function or a linkname directive, or
when a non-Go source file (assembly, C, object) appears. instruction.md states these rules.
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "testdata"}
FOREIGN_SOURCE = {".s", ".S", ".c", ".h", ".cc", ".cpp", ".syso", ".m"}
SELECTOR = re.compile(r"\b(os|syscall|unsafe|runtime|reflect)\.([A-Za-z_]\w*)")
IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)\)", re.S | re.M)
IMPORT_ONE = re.compile(r'^import\s+(?:[\w.]+\s+)?"([^"]+)"', re.M)
INIT = re.compile(r"^func\s+init\s*\(", re.M)
LINKNAME = re.compile(r"//go:linkname")


def scan(root: Path) -> dict:
    imports, selectors, inits, linknames, foreign = set(), Counter(), 0, 0, []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink():
                foreign.append(str(path.relative_to(root)))
                continue
            if path.suffix in FOREIGN_SOURCE:
                foreign.append(str(path.relative_to(root)))
                continue
            if not name.endswith(".go") or name.endswith("_test.go"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for block in IMPORT_BLOCK.finditer(text):
                imports.update(re.findall(r'"([^"]+)"', block.group(1)))
            imports.update(IMPORT_ONE.findall(text))
            selectors.update(m.group(0) for m in SELECTOR.finditer(text))
            inits += len(INIT.findall(text))
            linknames += len(LINKNAME.findall(text))
    return {"imports": imports, "selectors": selectors, "inits": inits, "linknames": linknames, "foreign": foreign}


def main() -> int:
    grader, submission, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    reasons = []
    if not submission.is_dir() or submission.is_symlink():
        reasons.append("no module at /workspace/raft")
    else:
        shipped = grader / "shipped"
        for name in ("go.mod", "go.sum"):
            mine = submission / name
            if mine.is_symlink() or not mine.is_file() or mine.read_bytes() != (shipped / name).read_bytes():
                reasons.append(f"{name} differs from the module as shipped")
        base, sub = scan(shipped), scan(submission)
        for path in sub["imports"] - base["imports"]:
            reasons.append(f"new import in library code: {path}")
        for sel, count in sorted(sub["selectors"].items()):
            if count > base["selectors"].get(sel, 0):
                reasons.append(f"library code uses {sel} {count} times, the library as shipped {base['selectors'].get(sel, 0)}")
        if sub["inits"] > base["inits"]:
            reasons.append("library code adds a package init function")
        if sub["linknames"] > base["linknames"]:
            reasons.append("library code adds a linkname directive")
        for path in sub["foreign"]:
            reasons.append(f"non-Go source or link in the module: {path}")
    out.write_text(json.dumps({"refused": bool(reasons), "reasons": sorted(reasons)}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
