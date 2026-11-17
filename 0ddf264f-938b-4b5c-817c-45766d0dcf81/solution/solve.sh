#!/bin/bash
set -euo pipefail
cd /app/repo
# Apply /solution/fix.patch with python3 (no patch binary in the image).
# Strict: every hunk's context and removed lines must match exactly, else exit 1.
python3 - /solution/fix.patch <<'PYEOF'
import re, sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(keepends=True)
i, files = 0, []
while i < len(lines):
    if lines[i].startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
        target = lines[i + 1][4:].split("\t")[0].strip()
        target = target.split("/", 1)[1]
        i += 2
        hunks = []
        while i < len(lines) and lines[i].startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", lines[i])
            start = int(m.group(1))
            i += 1
            old, new = [], []
            while i < len(lines) and lines[i][:1] in (" ", "-", "+", "\\"):
                tag, body = lines[i][:1], lines[i][1:]
                if tag in (" ", "-"):
                    old.append(body)
                if tag in (" ", "+"):
                    new.append(body)
                i += 1
            hunks.append((start, old, new))
        files.append((target, hunks))
    else:
        i += 1
if not files:
    sys.exit("fix.patch holds no file diff")
for target, hunks in files:
    path = Path(target)
    text = path.read_text(encoding="utf-8").splitlines(keepends=True)
    offset = 0
    for start, old, new in hunks:
        at = start - 1 + offset
        if text[at:at + len(old)] != old:
            sys.exit(f"hunk at line {start} of {target} does not match")
        text[at:at + len(old)] = new
        offset += len(new) - len(old)
    path.write_text("".join(text), encoding="utf-8")
    print(f"patched {target}")
PYEOF
# The written deliverable: the reference root-cause note, which the judge grades.
mkdir -p /app/output
cp /solution/reference_note.md /app/output/note.md
