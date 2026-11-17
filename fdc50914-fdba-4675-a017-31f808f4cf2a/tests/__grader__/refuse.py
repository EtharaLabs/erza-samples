"""Decide, without executing anything from the submission, whether it is admissible.

Usage: refuse.py <submitted regress tree> <grader dir>   (prints one JSON object)
A submission is refused when Cargo.toml or Cargo.lock differ from the shipped bytes, when any
build.rs or .cargo/ exists in the tree, or when src/ holds a symlink or a Rust file that reads
outside src/ at compile time: an invocation of include!, include_str!, include_bytes!, env! or
option_env! (by any path, std::env! included), a #[path] or #![path] attribute, or a use item that
renames one of those macros with `as`. Comments and the contents of string and character literals
are blanked first, so a name mentioned in a comment or a comparison such as `env != x` is not a use.
Changes outside src/ are otherwise ignored, because only src/ is copied into the build.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

MACROS = r"(?:env|option_env|include|include_str|include_bytes)"
INVOCATION = re.compile(r"\b" + MACROS + r"\s*!\s*[(\[{]")
PATH_ATTRIBUTE = re.compile(r"#\s*!?\s*\[\s*path\b")
USE_ITEM = re.compile(r"\buse\b([^;]*);")
# A use item that renames one of the macros with `as` would let it be invoked under another name; a plain import
# such as `use std::env;` grants nothing the prelude does not, and every invocation of the name is refused anyway.
RENAMED = re.compile(r"\b" + MACROS + r"\s+as\b")
RAW_STRING = re.compile(r'(?<![A-Za-z0-9_])b?r(#*)"')
CHAR_LITERAL = re.compile(r"b?'(?:\\(?:x[0-9A-Fa-f]{2}|u\{[0-9A-Fa-f_]{1,8}\}|.)|[^\\'\n])'")


def _blank(text):
    return re.sub(r"[^\n]", " ", text)


def code_only(source):
    """The source with comments and literal contents replaced by spaces; offsets and newlines are kept."""
    out, i, n = [], 0, len(source)
    while i < n:
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j < 0 else j
        elif source.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if source.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif source.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
        elif m := RAW_STRING.match(source, i):
            end = '"' + m[1]
            j = source.find(end, m.end())
            j = n if j < 0 else j + len(end)
        elif source[i] == '"':
            j = i + 1
            while j < n and source[j] != '"':
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
        elif m := CHAR_LITERAL.match(source, i):
            j = m.end()
        else:
            out.append(source[i])
            i += 1
            continue
        out.append(_blank(source[i:j]))
        i = j
    return "".join(out)


def reads_outside_src(source):
    code = code_only(source)
    if INVOCATION.search(code) or PATH_ATTRIBUTE.search(code):
        return True
    return any(RENAMED.search(item[1]) for item in USE_ITEM.finditer(code))


def main(tree, grader):
    reasons = []

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
                if path.suffix == ".rs" and reads_outside_src(data.decode("utf-8", "replace")):
                    reasons.append(f"{path.relative_to(tree)} reads outside src/ at compile time")
    shipped = json.loads((grader / "shipped_src_manifest.json").read_text())
    return {"refused": bool(reasons), "reasons": reasons, "changed": manifest != shipped, "src_present": bool(manifest)}


if __name__ == "__main__":
    print(json.dumps(main(Path(sys.argv[1]), Path(sys.argv[2]))))
