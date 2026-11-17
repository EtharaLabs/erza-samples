#!/bin/bash
# Verifier entry point for the Pagecraft chain-repair task.
# Order: clear stale reward files -> change set of /app/repo vs the pristine
# defective tree (before any restore) -> graded copy with agent pytest config
# and conftest.py removed -> byte-exact restore of protected files, sha256
# verified -> reward gate on the note -> Reward Kit (no --output, so it writes
# /logs/verifier/reward.json and reward-details.json) -> reward gate on c01-c11, k1, k2.
# The gate only ever lowers the reward to 0 with a named reason; when it stays
# open, reward.json and reward-details.json are left exactly as Reward Kit wrote them.
set -euo pipefail
# Judge model. judge.toml names Fable 5.1 (Anthropic). With no Anthropic key but an OpenAI key, Reward Kit
# judges the same rubric with an OpenAI model instead (REWARDKIT_JUDGE); with neither key the no-judge path
# applies and the reward is the compiled score alone.
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"; export OPENAI_BASE_URL
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then export REWARDKIT_JUDGE=openai/gpt-6-astra; else export REWARDKIT_JUDGE=; fi

TESTS_DIR="${TESTS_DIR:-/tests}"
APP_DIR="${APP_DIR:-/app}"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
export PAGECRAFT_VERIFIER_STATE="${PAGECRAFT_VERIFIER_STATE:-/tmp/pagecraft-verifier}"
STATE="$PAGECRAFT_VERIFIER_STATE"
PY="${VERIFIER_PYTHON:-python3}"

mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR/reward.txt" "$LOG_DIR/reward.json" "$LOG_DIR/reward-details.json" \
      "$LOG_DIR/judge-details.json" "$LOG_DIR/judge_unavailable"
# Fail closed: whatever ends this script, set -e included, a run that wrote no reward scores 0.
# reward.txt carries the same number as the reward key of reward.json.
write_reward_files() {
    [ -s "$LOG_DIR/reward.json" ] || echo "{\"reward\": 0.0}" > "$LOG_DIR/reward.json"
    "$PY" -c 'import json, sys; print(float(json.load(open(sys.argv[1]))["reward"]))' "$LOG_DIR/reward.json" \
        > "$LOG_DIR/reward.txt" 2>/dev/null \
        || { echo "{\"reward\": 0.0}" > "$LOG_DIR/reward.json"; echo 0.0 > "$LOG_DIR/reward.txt"; }
}
trap write_reward_files EXIT
rm -rf "$STATE"
mkdir -p "$STATE"

fail_closed() {
    # Restore or preparation failure: reward 0 with the reason named.
    "$PY" - "$LOG_DIR" "$1" <<'PYEOF'
import json, sys
from pathlib import Path
log, reason = Path(sys.argv[1]), sys.argv[2]
(log / "reward.json").write_text(json.dumps({"reward": 0.0}, indent=2))
(log / "reward-details.json").write_text(json.dumps({"reward": {"score": 0.0, "fail_closed": reason}}, indent=2))
PYEOF
    echo "verifier failed closed: $1" >&2
    exit 0
}

[ -d "$APP_DIR/repo" ] && [ ! -L "$APP_DIR/repo" ] || fail_closed "missing or non-directory $APP_DIR/repo"

# Pristine defective tree (shipped as a tarball so Reward Kit discovery never imports its .py files).
mkdir -p "$STATE/pristine"
tar -xf "$TESTS_DIR/pristine_defective/repo.tar" -C "$STATE/pristine" || fail_closed "cannot unpack pristine tree"

# 1. Change set of /app/repo against the pristine tree, computed before anything is restored.
"$PY" - "$STATE/pristine/repo" "$APP_DIR/repo" "$STATE/changeset.json" <<'PYEOF' || fail_closed "change set computation failed"
import difflib, fnmatch, hashlib, json, os, stat, sys
from pathlib import Path

pristine, live, out = (Path(a) for a in sys.argv[1:4])
# Build and tool by-products named by the vendored .gitignore; never counted as a change.
IGNORED_DIRS = {"_site", ".pagecraft", "__pycache__", ".pytest_cache", ".venv", "venv", "env",
                "dist", "build", ".eggs", ".git", ".idea", ".vscode", ".mypy_cache", ".ruff_cache"}
IGNORED_GLOBS = ("*.pyc", "*.egg-info", ".DS_Store", "*.swp", "*.swo", "*~")

def ignored(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in IGNORED_DIRS for p in parts) or any(fnmatch.fnmatch(p, g) for p in parts for g in IGNORED_GLOBS)

def walk(root: Path) -> dict:
    entries = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in dirnames + filenames:
            path = base / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            kind = "link" if stat.S_ISLNK(mode) else ("file" if stat.S_ISREG(mode) else "other")
            if kind == "link":
                digest = "link:" + os.readlink(path)
            elif kind == "file":
                try:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    # Unreadable agent file (e.g. mode 0600 owned by the agent):
                    # it cannot equal the pristine bytes, so count it as changed.
                    digest = "unreadable"
            else:
                digest = "other"
            entries[rel] = (kind, digest)
    return entries

def text(path: Path) -> list[str]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
            return []
        return path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []

before, after = walk(pristine), walk(live)
rows = []
for rel in sorted(before.keys() | after.keys()):
    a, b = before.get(rel), after.get(rel)
    if a == b:
        continue
    if a is None:
        status = "added"
    elif b is None:
        status = "deleted"
    elif a[0] != b[0]:
        status = "type_changed"
    else:
        status = "modified"
    added = []
    if status in {"added", "modified"} and b[0] == "file":
        old = text(pristine / rel) if status == "modified" else []
        added = [l[1:] for l in difflib.unified_diff(old, text(live / rel), lineterm="", n=0)
                 if l.startswith("+") and not l.startswith("+++")]
    unreadable = b is not None and b[1] == "unreadable"
    rows.append({"path": rel, "status": status, "ignored": ignored(rel), "unreadable": unreadable,
                 "added_text": "\n".join(added)[:200_000]})
out.write_text(json.dumps({"entries": rows}, indent=2, sort_keys=True))
print(f"change set: {sum(1 for r in rows if not r['ignored'])} tracked, {sum(1 for r in rows if r['ignored'])} ignored")
PYEOF

# 2. Graded copy: the repository as the agent left it, minus build by-products.
mkdir -p "$STATE/graded"
"$PY" - "$APP_DIR/repo" "$STATE/graded/repo" <<'PYEOF' || fail_closed "cannot copy graded tree"
import shutil, sys

def copy_readable(src, dst):
    # An agent file the verifier cannot read is left out of the graded copy;
    # the change set above already counts it as changed.
    try:
        return shutil.copy2(src, dst)
    except PermissionError:
        print(f"skipped unreadable {src}", file=sys.stderr)
        return dst

shutil.copytree(sys.argv[1], sys.argv[2], symlinks=True, copy_function=copy_readable,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "_site", ".pagecraft", ".venv", ".git"))
PYEOF
GRADED="$STATE/graded/repo"

# Remove agent-written conftest.py files and pytest config overrides from the graded copy.
find "$GRADED" \( -name conftest.py -o -name pytest.ini -o -name .pytest.ini -o -name tox.ini -o -name setup.cfg \) \
    \( -type f -o -type l \) -print -delete || fail_closed "cannot remove pytest overrides"

# 3. Byte-exact restore of protected files from the pristine copy, verified by sha256.
"$PY" - "$STATE/pristine/repo" "$GRADED" "$TESTS_DIR/pristine_defective/PROTECTED.sha256" <<'PYEOF' || fail_closed "protected restore failed or sha256 mismatch"
import hashlib, shutil, sys
from pathlib import Path
pristine, graded, sums = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
expected = {}
for line in sums.read_text().splitlines():
    digest, rel = line.split("  ", 1)
    expected[rel] = digest
tests = graded / "tests"
if tests.is_symlink() or (tests.exists() and not tests.is_dir()):
    tests.unlink()
elif tests.is_dir():
    shutil.rmtree(tests)
for rel, digest in sorted(expected.items()):
    src, dst = pristine / rel, graded / rel
    if hashlib.sha256(src.read_bytes()).hexdigest() != digest:
        sys.exit(f"pristine copy of {rel} does not match its recorded sha256")
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    elif dst.is_dir():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    if dst.is_symlink() or not dst.is_file() or hashlib.sha256(dst.read_bytes()).hexdigest() != digest:
        sys.exit(f"restored {rel} failed sha256 verification")
restored = sorted(p.relative_to(graded).as_posix() for p in tests.rglob("*") if p.is_file())
if restored != sorted(r for r in expected if r.startswith("tests/")):
    sys.exit("restored tests/ tree differs from the pristine protected set")
print(f"restored {len(expected)} protected files")
PYEOF

# 4. Reward gate, note half: a missing, non-regular or whitespace-only note closes
# the gate before Reward Kit runs, so the judge is never called on it.
NOTE="$APP_DIR/output/note.md"
note_ok=0
if [ -f "$NOTE" ] && [ ! -L "$NOTE" ]; then
    "$PY" - "$NOTE" <<'PYEOF' && note_ok=1
import sys
from pathlib import Path
try:
    body = Path(sys.argv[1]).read_bytes()
except OSError:
    sys.exit(1)
sys.exit(0 if body.decode("utf-8", errors="replace").strip() else 1)
PYEOF
fi
if [ "$note_ok" != 1 ]; then
    "$PY" - "$LOG_DIR" <<'PYEOF'
import json, sys
from pathlib import Path
log = Path(sys.argv[1])
(log / "reward.json").write_text(json.dumps({"reward": 0.0}, indent=2))
(log / "reward-details.json").write_text(json.dumps(
    {"reward": {"score": 0.0, "gate": {"closed": True, "reason": "note_missing_or_empty"}}}, indent=2))
PYEOF
    echo "reward gate closed: note_missing_or_empty" >&2
    exit 0
fi

# 5. Score. No --output: Reward Kit writes /logs/verifier/reward.json and reward-details.json.
# When the LLM judge returns no result (Reward Kit fails, writes no reward, or any j-criterion is
# missing or errored), the judge's details are kept as judge-details.json and the fallback scores
# the compiled group as usual and the judged group at 0.
FALLBACK_DIR="${FALLBACK_DIR:-/opt/grader/fallback}"
# Up to three judge attempts, so one transient error (a 429 or 5xx on one of the judge calls) does not
# zero the judged half; a later attempt runs only when the previous one returned no complete result.
judged_ok=0
for judge_attempt in 1 2 3; do
if rewardkit "$TESTS_DIR" && [ -s "$LOG_DIR/reward.json" ] && [ -s "$LOG_DIR/reward-details.json" ]; then
    "$PY" - "$LOG_DIR/reward-details.json" <<'PYEOF' && judged_ok=1
import json, re, sys
def rows(node):
    if isinstance(node, dict):
        if isinstance(node.get("criteria"), list):
            yield from node["criteria"]
        for value in node.values():
            yield from rows(value)
    elif isinstance(node, list):
        for value in node:
            yield from rows(value)
judged = [r for r in rows(json.load(open(sys.argv[1]))) if isinstance(r, dict) and re.match(r"j\d+_", str(r.get("name", "")))]
sys.exit(0 if judged and not any(r.get("error") for r in judged) else 1)
PYEOF
fi
[ "$judged_ok" = 1 ] && break
[ "$judge_attempt" -lt 3 ] && { rm -f "$LOG_DIR/reward.json" "$LOG_DIR/reward-details.json"; sleep $((20 * judge_attempt)); }
done
if [ "$judged_ok" != 1 ]; then
    [ -f "$LOG_DIR/reward-details.json" ] && mv "$LOG_DIR/reward-details.json" "$LOG_DIR/judge-details.json"
    rm -f "$LOG_DIR/reward.json"
    echo "the LLM judge returned no result; the reward is the compiled dimension alone" > "$LOG_DIR/judge_unavailable"
    rewardkit "${NOJUDGE_DIR:-/opt/grader/nojudge}" || fail_closed "no-judge rewardkit exited non-zero"
fi

# 6. Reward gate, outcome half: if no compiled outcome check c01-c11, k1, k2 passed, set
# the reward key to 0 and record the reason. r1-r3 never keep the gate open. A details
# file that cannot be read, or that names fewer than all of c01-c11, k1, k2, fails closed.
"$PY" - "$LOG_DIR" <<'PYEOF' || fail_closed "gate_input_unreadable"
import json, re, sys
from pathlib import Path
log = Path(sys.argv[1])
details = json.loads((log / "reward-details.json").read_text())
main = json.loads((log / "reward.json").read_text())
outcome = re.compile(r"(c(0[1-9]|1[01])|k[12])_")
seen = {}

def walk(node):
    if isinstance(node, dict):
        for c in node.get("criteria") or []:
            if isinstance(c, dict) and isinstance(c.get("name"), str) and outcome.match(c["name"]):
                seen[c["name"]] = float(c.get("value", 0.0))
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)

walk(details)
if len(seen) != 13 or "reward" not in main:
    sys.exit("reward-details.json does not name all of c01-c11, k1, k2, or reward.json has no reward key")
if not any(v > 0 for v in seen.values()):
    main["reward"] = 0.0
    details["gate"] = {"closed": True, "reason": "no_outcome_check_passed"}
    (log / "reward.json").write_text(json.dumps(main, indent=2))
    (log / "reward-details.json").write_text(json.dumps(details, indent=2))
    print("reward gate closed: no_outcome_check_passed", file=sys.stderr)
PYEOF
