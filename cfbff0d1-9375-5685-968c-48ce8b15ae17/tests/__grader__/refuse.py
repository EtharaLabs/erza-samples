"""Decide, without executing anything from the submission, whether it is admissible.

Usage: refuse.py <submitted regress tree> <grader dir>   (prints one JSON object)
A submission is refused when Cargo.toml or Cargo.lock differ from the shipped bytes, when any
build.rs or .cargo/ exists in the tree, or when src/ holds a symlink or a Rust file that reads
outside src/ at compile time (include!, include_str!, include_bytes!, #[path], env!, option_env!).
Changes outside src/ are otherwise ignored, because only src/ is copied into the build.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

tree, grader = Path(sys.argv[1]), Path(sys.argv[2])
reasons = []
FORBIDDEN = re.compile(r"\binclude(?:_str|_bytes)?\s*!|#\s*!?\s*\[\s*path\b|\b(?:option_)?env\s*!")


def same(name):
    path = tree / name
    if path.is_symlink() or not path.is_file():
        return False
    return path.read_bytes() == (grader / "shipped" / name).read_bytes()


for name in ("Cargo.toml", "Cargo.lock"):
    if not same(name):
        reasons.append(f"{name} differs from the shipped file")
if tree.is_dir():
    for dirpath, dirnames, filenames in os.walk(tree, followlinks=False):
        rel = Path(dirpath).relative_to(tree)
        if rel.parts[:1] == ("target",):
            dirnames[:] = []
            continue
        if ".cargo" in dirnames:
            reasons.append(f"{rel / '.cargo'} exists")
        if "build.rs" in filenames:
            reasons.append(f"{rel / 'build.rs'} exists")

src = tree / "src"
manifest = {}
if src.is_symlink():
    reasons.append("src is a symlink")
elif src.is_dir():
    for path in sorted(src.rglob("*")):
        if path.is_symlink():
            reasons.append(f"{path.relative_to(tree)} is a symlink")
        elif path.is_file():
            data = path.read_bytes()
            manifest[path.relative_to(src).as_posix()] = hashlib.sha256(data).hexdigest()
            if path.suffix == ".rs" and FORBIDDEN.search(data.decode("utf-8", "replace")):
                reasons.append(f"{path.relative_to(tree)} reads outside src/ at compile time")
shipped = json.loads((grader / "shipped_src_manifest.json").read_text())
print(json.dumps({"refused": bool(reasons), "reasons": reasons, "changed": manifest != shipped, "src_present": bool(manifest)}))
