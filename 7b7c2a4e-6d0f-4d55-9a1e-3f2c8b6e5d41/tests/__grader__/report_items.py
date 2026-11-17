"""Read the regression tests the report names, without running code.

Usage: python3 report_items.py <submission dir> <report> <out json>

A named test is an identifier Test... that appears in the report and is declared as
func Name(t *testing.T) in a file of the submission whose name ends in _regression_test.go.
The output lists, per package directory, the named tests declared there.
"""

import json
import os
import re
import sys
from pathlib import Path

MAX_NAMED = 16
MAX_REPORT = 64 * 1024
DECL = re.compile(r"^func\s+(Test[A-Za-z0-9_]*)\s*\(\s*\w+\s+\*testing\.T\s*\)", re.M)
NAME = re.compile(r"\bTest[A-Za-z0-9_]+\b")


def main() -> int:
    submission, report, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    result = {"report": False, "named": {}, "count": 0, "too_many": False, "files": []}
    if report.is_file() and not report.is_symlink() and not report.parent.is_symlink():
        text = report.read_bytes()[:MAX_REPORT].decode("utf-8", errors="replace")
        result["report"] = bool(text.strip())
        mentioned = set(NAME.findall(text))
        named = {}
        if submission.is_dir() and not submission.is_symlink():
            for dirpath, dirnames, filenames in os.walk(submission):
                dirnames[:] = sorted(d for d in dirnames if d not in {".git", "testdata"})
                for name in sorted(filenames):
                    path = Path(dirpath) / name
                    if not name.endswith("_regression_test.go") or path.is_symlink() or not path.is_file():
                        continue
                    rel = str(Path(dirpath).relative_to(submission)) or "."
                    result["files"].append(str(path.relative_to(submission)))
                    for test in DECL.findall(path.read_text(encoding="utf-8", errors="replace")):
                        if test in mentioned:
                            named.setdefault(rel, set()).add(test)
        result["named"] = {k: sorted(v) for k, v in sorted(named.items())}
        result["count"] = sum(len(v) for v in named.values())
        result["too_many"] = result["count"] > MAX_NAMED
    out.write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
