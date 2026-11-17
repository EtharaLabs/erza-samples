#!/bin/bash
# Grades a submitted regress src/ tree. Root only prepares directories, drops privilege, and kills
# leftover processes. The submission is built and run as uid 1001 (sandbox) with an empty
# environment; uid 1000 (grader) decides admissibility, compares outputs, and writes the reward.
# No process that ran agent code writes the reward or reads the expected results. Root never opens,
# copies, or changes a path that uid 1001 can write: every file root writes while sandbox code may
# have run lives in $STATE/io, a directory only root can enter.
set -uo pipefail
# Judge model. judge.toml names Fable 5.1 (Anthropic). With no Anthropic key but an OpenAI key, Reward Kit
# judges the same rubric with an OpenAI model instead (REWARDKIT_JUDGE); with neither key the no-judge path
# applies and the reward is the compiled score alone.
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"; export OPENAI_BASE_URL
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then export REWARDKIT_JUDGE=openai/gpt-6-astra; else export REWARDKIT_JUDGE=; fi
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt /logs/verifier/reward-details.json \
  /logs/verifier/judge-details.json /logs/verifier/judge_unavailable
# Fail closed: whatever ends this script, a run that wrote no reward scores 0.
# reward.txt carries the same number as the reward key of reward.json.
write_reward_files() {
  [ -s /logs/verifier/reward.json ] || echo "{\"reward\": 0.0}" > /logs/verifier/reward.json
  python3 -c 'import json, sys; print(float(json.load(open(sys.argv[1]))["reward"]))' /logs/verifier/reward.json \
    > /logs/verifier/reward.txt 2>/dev/null \
    || { echo "{\"reward\": 0.0}" > /logs/verifier/reward.json; echo 0.0 > /logs/verifier/reward.txt; }
}
trap write_reward_files EXIT
chown 1000:1000 /logs/verifier && chmod 0755 /logs/verifier

G=/opt/grader
SUB=/workspace/regress
STATE=/var/grade
rm -rf "$STATE"
install -d -o 0 -g 0 -m 0755 "$STATE" "$STATE/build"
install -d -o 1000 -g 1000 -m 0755 "$STATE/results"
install -d -o 0 -g 0 -m 0700 "$STATE/io"
# Root's own here-documents go to $STATE/io, never to /tmp, which uid 1001 can write; children keep their default.
TMPDIR="$STATE/io"; export -n TMPDIR
install -d -o 1001 -g 1001 -m 0700 "$STATE/sandbox" "$STATE/sandbox/cargo-home" "$STATE/sandbox/target" "$STATE/sandbox/tmp"
# Before any submitted code runs, the artifact trees belong to the grader and no other uid may write them:
# Harbor recreates each artifact directory, and their parent, with mode 0777.
[ -d /workspace ] && [ ! -L /workspace ] && chmod go-w /workspace
for path in /workspace/output "$SUB"; do
  [ -e "$path" ] || [ -L "$path" ] || continue
  chown -R -P -h 1000:1000 "$path"
  find -P "$path" -type d -exec chmod a+rx,go-w {} +
  find -P "$path" -type f -exec chmod a+r,go-w {} +
done

as_grader() { setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all "$@"; }
as_sandbox() {
  setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
    env -i PATH=/opt/rust/bin:/usr/bin:/bin HOME="$STATE/sandbox" TMPDIR="$STATE/sandbox/tmp" \
    CARGO_HOME="$STATE/sandbox/cargo-home" CARGO_TARGET_DIR="$STATE/sandbox/target" CARGO_NET_OFFLINE=true "$@"
}
# Kills every uid-1001 process and confirms none remain; fails when one survives five seconds of rounds.
kill_sandbox() {
  local round
  for round in $(seq 1 50); do
    pkill -KILL -u 1001 2>/dev/null
    pgrep -u 1001 > /dev/null || return 0
    sleep 0.1
  done
  return 1
}
survivor=0
kill_sandbox || survivor=1

# 1. Admissibility, decided by the grader without executing submitted code.
as_grader python3 "$G/refuse.py" "$SUB" "$G" > "$STATE/results/verdict.json.tmp" 2>/dev/null \
  || echo '{"refused": true, "reasons": ["refusal check failed"], "changed": false, "src_present": false}' > "$STATE/results/verdict.json.tmp"
mv "$STATE/results/verdict.json.tmp" "$STATE/results/verdict.json"; chown 1000:1000 "$STATE/results/verdict.json"
refused=$(python3 -c "import json;print(int(json.load(open('$STATE/results/verdict.json'))['refused']))")

if [ "$refused" = 0 ] && [ "$survivor" = 0 ]; then
  # 2. A fresh root-owned build tree: the shipped manifest, lock and tests, the submitted src/, the harness.
  install -d -m 0755 "$STATE/build/regress"
  cp -R "$G/shipped/." "$STATE/build/regress/"
  rm -rf "$STATE/build/regress/src"
  cp -R --no-dereference "$SUB/src" "$STATE/build/regress/src"
  cp -R "$G/harness" "$STATE/build/harness"
  chown -R 0:0 "$STATE/build"; chmod -R a+rX,go-w "$STATE/build"
  as_sandbox cp "$G/cargo-config.toml" "$STATE/sandbox/cargo-home/config.toml"

  # 3. Build and run the harness as the sandbox user, one process per item.
  as_sandbox cargo build --offline --frozen --quiet --manifest-path "$STATE/build/harness/Cargo.toml" < /dev/null > "$STATE/io/build.log" 2>&1
  build=$?
  echo "$build" > "$STATE/results/build.exit"; chown 1000:1000 "$STATE/results/build.exit"
  kill_sandbox || survivor=1
  if [ "$build" = 0 ] && [ "$survivor" = 0 ]; then
    for cases in "$G"/cases/*.tsv; do
      item=$(basename "$cases" .tsv)
      # A crash guard, far above the reference's run time; a hung item records no output and fails.
      # Result lines go to fd 3 alone, so output the submitted library prints never reaches them.
      # Root creates each case and result file fresh in $STATE/io and opens fd 0 and fd 3 on them before
      # dropping privilege, so the harness holds no descriptor under $G; every uid-1001 process is killed
      # before the result file is read and before the next item starts.
      install -o 0 -g 0 -m 0600 "$cases" "$STATE/io/$item.in"
      install -o 0 -g 0 -m 0600 /dev/null "$STATE/io/$item.raw"
      timeout -s KILL 600 setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
        env -i PATH=/usr/bin:/bin HOME="$STATE/sandbox" "$STATE/sandbox/target/debug/grader-harness" \
        < "$STATE/io/$item.in" 3>> "$STATE/io/$item.raw" > /dev/null 2>/dev/null
      kill_sandbox || { survivor=1; break; }
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$item.raw" "$STATE/results/$item.tsv"
    done
  fi
  kill_sandbox || survivor=1
  # 4. The shipped tests (C09), as the sandbox user, with a cargo home, target and temporary directory
  # created fresh under root-owned $STATE after every uid-1001 process was killed. cargo builds the test
  # executables; root copies each into a root-owned directory no test can write; then each shipped test
  # named in shipped_tests.json runs alone with --exact in its own process and passes only on exit 0
  # with libtest's own "1 passed" result. A test the submission adds is never run.
  install -d -o 1001 -g 1001 -m 0700 "$STATE/test-home" "$STATE/test-target" "$STATE/test-tmp"
  install -o 1001 -g 1001 -m 0600 "$G/cargo-config.toml" "$STATE/test-home/config.toml"
  install -d -o 0 -g 0 -m 0755 "$STATE/test-bin"
  as_tester() {
    ( cd "$STATE/build/regress" && timeout -s KILL "$1" setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
      env -i PATH=/opt/rust/bin:/usr/bin:/bin HOME="$STATE/test-home" TMPDIR="$STATE/test-tmp" \
      CARGO_HOME="$STATE/test-home" CARGO_TARGET_DIR="$STATE/test-target" CARGO_NET_OFFLINE=true "${@:2}" )
  }
  as_tester 1200 cargo test --offline --frozen --no-run --message-format=json --manifest-path "$STATE/build/regress/Cargo.toml" \
    < /dev/null > "$STATE/io/test-build.json" 2> "$STATE/io/test.log"
  c09=$?
  kill_sandbox || survivor=1
  [ "$survivor" = 0 ] || c09=1
  if [ "$c09" = 0 ]; then
    python3 -P - "$G/shipped_tests.json" "$STATE/io/test-build.json" "$STATE/test-target" "$STATE/test-bin" > "$STATE/io/test-plan.tsv" <<'PLAN' || c09=1
import json, os, shutil, sys
shipped, build, target, bindir = sys.argv[1:5]
record = json.load(open(shipped))
exes = {}
for line in open(build):
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    if msg.get("reason") == "compiler-artifact" and msg.get("profile", {}).get("test") and msg.get("executable"):
        exes[(msg["target"]["kind"][0], msg["target"]["name"])] = msg["executable"]
for n, t in enumerate(record["targets"]):
    exe = exes.get((t["kind"], t["name"]))
    if not exe or os.path.islink(exe) or not os.path.isfile(exe) or not os.path.realpath(exe).startswith(target.rstrip("/") + "/"):
        sys.exit(f"no test executable for {t['kind']} {t['name']}")
    dest = os.path.join(bindir, str(n))
    shutil.copyfile(exe, dest)
    os.chmod(dest, 0o555)
    for name in t["tests"]:
        print(f"{dest}\t{name}")
for name in record["doc"]:
    print(f"doc\t{name}")
PLAN
  fi
  # Doctests first, so the only cargo run that executes submitted code reads a configuration and a target
  # that only cargo wrote. rustdoc splits each test argument on whitespace and edition-2024 doctests are
  # merged into one process, so no single doctest can be selected: they run once, and each shipped
  # doctest must report its own ok line; one that failed reports FAILED, so an early exit cannot stand in.
  if [ "$c09" = 0 ] && grep -q $'^doc\t' "$STATE/io/test-plan.tsv"; then
    out="$STATE/io/test-doc.out"
    as_tester 600 cargo test --offline --frozen --doc --manifest-path "$STATE/build/regress/Cargo.toml" -- --test-threads 1 \
      < /dev/null > "$out" 2>&1
    rc=$?
    kill_sandbox || { survivor=1; c09=1; }
    results=$(grep -cE '^test result: ' "$out")
    { [ "$rc" = 0 ] && [ "$results" -gt 0 ] && [ "$results" = "$(grep -cE '^test result: ok\. [0-9]+ passed; 0 failed;' "$out")" ]; } || c09=1
    # A doctest is named by file, item and source line; a repair that moves lines renames it, so each is
    # matched by file, item and its order among that item's doctests.
    python3 -P - "$STATE/io/test-plan.tsv" "$out" >> "$STATE/io/test.log" <<'DOCS' || c09=1
import re, sys
NAME = re.compile(r"(?P<file>\S+) - (?P<item>.*?) ?\(line (?P<line>\d+)\)")
def keys(names):
    groups = {}
    for name in names:
        m = NAME.fullmatch(name)
        if m is None:
            return None
        groups.setdefault((m["file"], m["item"]), []).append(int(m["line"]))
    return {(f, i, n) for (f, i), lines in groups.items() for n in range(len(lines))}
shipped = [l.rstrip("\n").split("\t", 1)[1] for l in open(sys.argv[1]) if l.startswith("doc\t")]
ran_ok = [m[1] for m in re.finditer(r"(?m)^test (.*) \.\.\. ok$", open(sys.argv[2], errors="replace").read())]
want, got = keys(shipped), keys(ran_ok)
missing = sorted(want - got) if want is not None and got is not None else ["unparsable doctest names"]
for key in missing:
    print("failed: doctest", key)
sys.exit(1 if missing else 0)
DOCS
  fi
  # Then each unit and integration test alone, from the root-owned copies, with no cargo involved.
  i=0
  while [ "$c09" = 0 ] && IFS=$'\t' read -r bin name; do
    [ "$bin" = doc ] && continue
    i=$((i + 1))
    out="$STATE/io/test-$i.out"
    as_tester 300 "$bin" --exact "$name" --test-threads 1 < /dev/null > "$out" 2>&1
    rc=$?
    kill_sandbox || { survivor=1; c09=1; }
    if [ "$rc" != 0 ] \
      || [ "$(grep -cxF "test $name ... ok" "$out")" != 1 ] \
      || [ "$(grep -cE '^test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured;' "$out")" != 1 ] \
      || [ "$(grep -cE '^test result: ' "$out")" != 1 ]; then
      echo "failed: $name (exit $rc)" >> "$STATE/io/test.log"
      c09=1
    fi
  done < "$STATE/io/test-plan.tsv"
  [ "$c09" != 0 ] || [ "$i" -gt 0 ] || c09=1
  echo "$c09" > "$STATE/results/C09.exit"
  kill_sandbox || survivor=1
  chown 1000:1000 "$STATE/results/C09.exit"
fi
if [ "$survivor" != 0 ] || pgrep -u 1001 > /dev/null; then
  echo '{"refused": true, "reasons": ["a sandbox process survived"], "changed": false, "src_present": false}' > "$STATE/results/verdict.json"
  refused=1
fi
chmod -R go-w "$STATE/results"

# 5. Scoring as the grader. The judge reads the note only when the submission is admissible, the
# library changed and built, at least one of C01 to C08 passes, and the note is a regular, non-empty
# file inside a real /workspace/output; otherwise, or when the judge leaves no reward file, the
# fallback scores the compiled group as usual and the judged group at 0, and names why the judge did
# not score, in this precedence: refused, unchanged, build-failed, unrepaired, note-missing,
# judge-unavailable, note-unsupported. A run the judge could not score also leaves the
# judge_unavailable marker.
changed=$(python3 -c "import json;print(int(json.load(open('$STATE/results/verdict.json')).get('changed') is True))")
note=/workspace/output/ROOT_CAUSE.md
build_exit=$(cat "$STATE/results/build.exit" 2>/dev/null || echo missing)
cause=""
if [ "$refused" != 0 ]; then cause=refused
elif [ "$changed" != 1 ]; then cause=unchanged
elif [ "$build_exit" != 0 ]; then cause=build-failed
elif ! as_grader env GRADE_RESULTS="$STATE/results" python3 /tests/test_output.py; then cause=unrepaired
elif [ -L /workspace/output ] || [ -L "$note" ] || [ ! -f "$note" ] || [ ! -s "$note" ]; then cause=note-missing
else
  as_grader env GRADE_RESULTS="$STATE/results" rewardkit /tests --workspace /workspace --output /logs/verifier/reward.json
  if [ ! -s /logs/verifier/reward.json ] || ! as_grader python3 - /logs/verifier/reward-details.json <<'JUDGED'
import json, sys
def rows(node):
    if isinstance(node, dict):
        if isinstance(node.get("criteria"), list):
            yield from node["criteria"]
        for value in node.values():
            yield from rows(value)
    elif isinstance(node, list):
        for value in node:
            yield from rows(value)
judged = [r for r in rows(json.load(open(sys.argv[1]))) if str(r.get("name", "")).startswith("J")]
sys.exit(0 if judged and not any(r.get("error") for r in judged) else 1)
JUDGED
  then
    cause=judge-unavailable
    [ -f /logs/verifier/reward-details.json ] && as_grader mv /logs/verifier/reward-details.json /logs/verifier/judge-details.json
    rm -f /logs/verifier/reward.json
    echo "the LLM judge returned no result; the reward is the compiled dimension alone" > /logs/verifier/judge_unavailable
  # J10 credits the absence of a rejected claim, so it counts only for a note that earns one of J01 to J09.
  elif ! as_grader python3 - /logs/verifier/reward-details.json <<'GATE'
import json, sys
def rows(node):
    if isinstance(node, dict):
        if isinstance(node.get("criteria"), list):
            yield from node["criteria"]
        for value in node.values():
            yield from rows(value)
    elif isinstance(node, list):
        for value in node:
            yield from rows(value)
earned = [r for r in rows(json.load(open(sys.argv[1]))) if str(r.get("name", "")) in {f"J0{i}" for i in range(1, 10)}]
sys.exit(0 if any(r.get("value", 0) > 0 for r in earned) else 1)
GATE
  then
    as_grader mv /logs/verifier/reward-details.json /logs/verifier/judge-details.json
    rm -f /logs/verifier/reward.json
    cause=note-unsupported
  fi
fi
if [ ! -s /logs/verifier/reward.json ]; then
  fb="$G/fallback"; [ "$cause" = judge-unavailable ] && fb="$G/nojudge"
  as_grader env GRADE_RESULTS="$STATE/results" GRADE_FALLBACK_CAUSE="$cause" rewardkit "$fb" --workspace /workspace --output /logs/verifier/reward.json
fi
# The admissibility verdict and the fallback cause are exported beside the reward, so every zero names its reason.
as_grader python3 - "$STATE/results" "$cause" /logs/verifier/verdict.json <<'EXPORT'
import json, pathlib, sys
results, cause, out = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
verdict = json.loads((results / "verdict.json").read_text())
def code(name):
    try:
        return int((results / name).read_text().strip())
    except (OSError, ValueError):
        return None
verdict.update(fallback_cause=cause or None, build_exit=code("build.exit"), shipped_tests_exit=code("C09.exit"))
json.dump(verdict, open(out, "w"), sort_keys=True)
EXPORT
