"""Read the two machine-checked parts of the repair report, as the grader, without running code.

Usage: python report_items.py <grader dir> <results dir>

Writes <results>/reproductions.json with every line that starts with "Reproduction:", parsed or
marked malformed, and <results>/shipped.in with one probe line per well-formed reproduction.
Writes <results>/named_tests.json with every tests/<name>.cpp the report names that the solver
added or changed, against the shipped tree's manifest. The report is read as a regular file, never
through a link, one line at a time: each line is kept up to MAX_LINE bytes, and a Reproduction line
longer than that is recorded as over the cap and is neither checked nor counted, so no length of the
report cuts off a later line.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

REPORT = Path("/workspace/output/REPAIR_REPORT.md")
TESTS = Path("/workspace/fast_float/tests")
MAX_LINE = 64 * 1024
LINE = re.compile(r"Reproduction: (char|char16_t|char32_t) (float|double) ([!-~]+) required 0x([0-9A-Fa-f]+) produced 0x([0-9A-Fa-f]+)[ \t]*")
NAME = re.compile(r"tests/([A-Za-z0-9_][A-Za-z0-9_.-]*)\.cpp")
KIND = {("char", "float"): "f", ("char", "double"): "d", ("char16_t", "float"): "a", ("char16_t", "double"): "b",
        ("char32_t", "float"): "p", ("char32_t", "double"): "q"}


def report_lines():
    """(text, over_cap) for each line of the report; text holds at most MAX_LINE bytes."""
    if REPORT.parent.is_symlink() or not REPORT.parent.is_dir() or REPORT.is_symlink() or not REPORT.is_file():
        return
    with REPORT.open("rb") as handle:
        while True:
            head = handle.readline(MAX_LINE + 1)
            if not head:
                return
            over = len(head) > MAX_LINE
            if over:
                while True:
                    rest = handle.readline(1 << 20)
                    if not rest or rest.endswith(b"\n"):
                        break
            yield head[:MAX_LINE].rstrip(b"\r\n").decode("utf-8", errors="replace"), over


def main():
    grader, results = Path(sys.argv[1]), Path(sys.argv[2])
    rows, kept = [], []
    for line, over in report_lines():
        if not over:
            kept.append(line)
        if not line.startswith("Reproduction:"):
            continue
        if over:
            rows.append({"line": line[:200], "malformed": False, "over_cap": True})
            continue
        match = LINE.fullmatch(line)
        if match is None:
            rows.append({"line": line[:200], "malformed": True})
            continue
        char, ftype, given, required, produced = match.groups()
        rows.append({"malformed": False, "kind": KIND[(char, ftype)], "input": given, "required": required.lower(), "produced": produced.lower()})
    (results / "reproductions.json").write_text(json.dumps(rows, sort_keys=True))
    (results / "shipped.in").write_text("".join(f"{r['kind']} {r['input']}\n" for r in rows if not r["malformed"] and not r.get("over_cap")))
    text = "\n".join(kept)

    shipped = json.loads((grader / "shipped_manifest.json").read_text())
    named, seen = [], set()
    for match in NAME.finditer(text):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        path = TESTS / f"{name}.cpp"
        if path.is_symlink() or not path.is_file():
            named.append({"name": name, "exists": False})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if shipped.get(f"tests/{name}.cpp") == digest:
            continue  # an upstream test the solver left unchanged is not a regression test
        named.append({"name": name, "exists": True})
    (results / "named_tests.json").write_text(json.dumps(named, sort_keys=True))


if __name__ == "__main__":
    main()
