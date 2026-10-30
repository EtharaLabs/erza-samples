#!/bin/bash
# Grades a submitted regress src/ tree. Root only prepares directories, drops privilege, and kills
# leftover processes. The submission is built and run as uid 1001 (sandbox) with an empty
# environment; uid 1000 (grader) decides admissibility, compares outputs, and writes the reward.
# No process that ran agent code writes the reward or reads the expected results.
set -uo pipefail
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
chown 1000:1000 /logs/verifier && chmod 0755 /logs/verifier

G=/opt/grader
SUB=/workspace/regress
STATE=/var/grade
rm -rf "$STATE"
install -d -o 0 -g 0 -m 0755 "$STATE" "$STATE/build"
install -d -o 1000 -g 1000 -m 0755 "$STATE/results"
install -d -o 1001 -g 1001 -m 0700 "$STATE/sandbox" "$STATE/sandbox/out" "$STATE/sandbox/cargo-home" "$STATE/sandbox/target" "$STATE/sandbox/tmp"
for path in /workspace/output "$SUB"; do
  [ -e "$path" ] || continue
  find -P "$path" -type d -exec chmod a+rx {} +
  find -P "$path" -type f -exec chmod a+r {} +
done

as_grader() { setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all "$@"; }
as_sandbox() {
  setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
    env -i PATH=/opt/rust/bin:/usr/bin:/bin HOME="$STATE/sandbox" TMPDIR="$STATE/sandbox/tmp" \
    CARGO_HOME="$STATE/sandbox/cargo-home" CARGO_TARGET_DIR="$STATE/sandbox/target" CARGO_NET_OFFLINE=true "$@"
}
kill_sandbox() { pkill -9 -u 1001 2>/dev/null; sleep 1; pkill -9 -u 1001 2>/dev/null; true; }

# 1. Admissibility, decided by the grader without executing submitted code.
as_grader python3 "$G/refuse.py" "$SUB" "$G" > "$STATE/results/verdict.json.tmp" 2>/dev/null \
  || echo '{"refused": true, "reasons": ["refusal check failed"], "changed": false, "src_present": false}' > "$STATE/results/verdict.json.tmp"
mv "$STATE/results/verdict.json.tmp" "$STATE/results/verdict.json"; chown 1000:1000 "$STATE/results/verdict.json"
refused=$(python3 -c "import json;print(int(json.load(open('$STATE/results/verdict.json'))['refused']))")

if [ "$refused" = 0 ]; then
  # 2. A fresh root-owned build tree: the shipped manifest, lock and tests, the submitted src/, the harness.
  install -d -m 0755 "$STATE/build/regress"
  cp -R "$G/shipped/." "$STATE/build/regress/"
  rm -rf "$STATE/build/regress/src"
  cp -R --no-dereference "$SUB/src" "$STATE/build/regress/src"
  cp -R "$G/harness" "$STATE/build/harness"
  chown -R 0:0 "$STATE/build"; chmod -R a+rX,go-w "$STATE/build"
  cp "$G/cargo-config.toml" "$STATE/sandbox/cargo-home/config.toml"; chown 1001:1001 "$STATE/sandbox/cargo-home/config.toml"

  # 3. Build and run the harness as the sandbox user, one process per item.
  as_sandbox cargo build --offline --frozen --quiet --manifest-path "$STATE/build/harness/Cargo.toml" > "$STATE/sandbox/build.log" 2>&1
  build=$?
  echo "$build" > "$STATE/results/build.exit"; chown 1000:1000 "$STATE/results/build.exit"
  if [ "$build" = 0 ]; then
    for cases in "$G"/cases/*.tsv; do
      item=$(basename "$cases" .tsv)
      # A crash guard, far above the reference's run time; a hung item records no output and fails.
      # Result lines go to fd 3 alone, so output the submitted library prints never reaches them.
      timeout -s KILL 600 setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
        env -i PATH=/usr/bin:/bin HOME="$STATE/sandbox" "$STATE/sandbox/target/debug/grader-harness" \
        < "$cases" 3> "$STATE/sandbox/out/$item.raw" > /dev/null 2>/dev/null
      kill_sandbox
      [ -f "$STATE/sandbox/out/$item.raw" ] && install -o 1000 -g 1000 -m 0644 "$STATE/sandbox/out/$item.raw" "$STATE/results/$item.tsv"
    done
  fi
  kill_sandbox
  # 4. The shipped test suite against the submitted src/ (C09), as the sandbox user.
  timeout -s KILL 1200 setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
    env -i PATH=/opt/rust/bin:/usr/bin:/bin HOME="$STATE/sandbox" TMPDIR="$STATE/sandbox/tmp" \
    CARGO_HOME="$STATE/sandbox/cargo-home" CARGO_TARGET_DIR="$STATE/sandbox/target" CARGO_NET_OFFLINE=true \
    cargo test --offline --frozen --quiet --manifest-path "$STATE/build/regress/Cargo.toml" > "$STATE/sandbox/test.log" 2>&1
  echo $? > "$STATE/results/C09.exit"
  kill_sandbox
  chown 1000:1000 "$STATE/results/C09.exit"
fi
if pgrep -u 1001 > /dev/null; then
  echo '{"refused": true, "reasons": ["a sandbox process survived"], "changed": false, "src_present": false}' > "$STATE/results/verdict.json"
  refused=1
fi
chmod -R go-w "$STATE/results"

# 5. Scoring as the grader. The judge reads the note only when the submission is admissible, the
# library changed, and the note is a regular, non-empty file inside a real /workspace/output;
# otherwise, or when the judge leaves no reward file, the fallback scores the compiled group as
# usual and the judged group at 0, and names why the judge did not score.
changed=$(python3 -c "import json;print(int(json.load(open('$STATE/results/verdict.json')).get('changed') is True))")
note=/workspace/output/ROOT_CAUSE.md
cause=""
if [ "$refused" != 0 ]; then cause=refused
elif [ "$changed" != 1 ]; then cause=unchanged
elif [ -L /workspace/output ] || [ -L "$note" ] || [ ! -f "$note" ] || [ ! -s "$note" ]; then cause=note-missing
else
  as_grader env GRADE_RESULTS="$STATE/results" rewardkit /tests --workspace /workspace --output /logs/verifier/reward.json
  [ -s /logs/verifier/reward.json ] || cause=judge-unavailable
fi
if [ ! -s /logs/verifier/reward.json ]; then
  as_grader env GRADE_RESULTS="$STATE/results" GRADE_FALLBACK_CAUSE="$cause" rewardkit "$G/fallback" --workspace /workspace --output /logs/verifier/reward.json
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
