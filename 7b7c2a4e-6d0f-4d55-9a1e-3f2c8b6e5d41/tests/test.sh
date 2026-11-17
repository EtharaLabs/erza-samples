#!/bin/bash
# Grades the collected raft module: the compiled items offline, then the judged items through the LLM
# judge, combined into one reward.
# Root prepares directories, opens every step's input and output files, drops privilege, and
# kills leftover processes. Submitted code is compiled and run only as a uid allocated for this
# run alone, under an empty environment, a CPU cap on its whole process tree, a whole-run CPU
# budget, and RLIMIT_NPROC. Uid 1000 (grader) inspects the submission, reads the report, scores
# the compiled items with pytest, and runs Reward Kit, which writes the reward. Root copies every
# file a sandboxed step wrote out of the sandbox before the grader reads it.
set -uo pipefail
# Judge model. judge.toml names Fable 5.1 (Anthropic). With no Anthropic key but an OpenAI key, Reward Kit
# judges the same rubric with an OpenAI model instead (REWARDKIT_JUDGE); with neither key the no-judge path
# applies and the reward is the compiled score alone.
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"; export OPENAI_BASE_URL
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then export REWARDKIT_JUDGE=openai/gpt-6-astra; else export REWARDKIT_JUDGE=; fi
# Caps are ceil(20 x the reference's largest measured tree CPU time per step across linux/amd64
# and linux/arm64); the named regression tests run under the limits instruction.md states.
declare -A CAP=([harness_build]=130 [CA]=122 [CB]=45 [CRA]=28 [CR]=77 [CS]=144 [ck]=444 [named_build]=120 [named_run]=10)
MAX_NAMED=16
RUN_BUDGET=1345
BACKSTOP=600
NPROC_RUN=8
NPROC_BUILD=24
SEEDS=1000
# GRADER_SEEDS overrides the seed count for local measurements only; graded runs use 1000.
[ -n "${GRADER_SEEDS:-}" ] && SEEDS="$GRADER_SEEDS"
CATEGORIES=(CA CB CRA CR CS)

OUT=/logs/verifier
rm -f "$OUT/reward.json" "$OUT/reward.txt" "$OUT/reward-details.json" "$OUT/judge-details.json" \
  "$OUT/judge_unavailable" "$OUT/verifier_refused"
# Fail closed: whatever ends this script, a run that wrote no reward scores 0.
# reward.txt carries the same number as the reward key of reward.json.
write_reward_files() {
  [ -s /logs/verifier/reward.json ] || echo "{\"reward\": 0.0}" > /logs/verifier/reward.json
  python3 -c 'import json, sys; print(float(json.load(open(sys.argv[1]))["reward"]))' /logs/verifier/reward.json \
    > /logs/verifier/reward.txt 2>/dev/null \
    || { echo "{\"reward\": 0.0}" > /logs/verifier/reward.json; echo 0.0 > /logs/verifier/reward.txt; }
}
trap write_reward_files EXIT
G=/opt/grader
if ! SUID=$(python3 "$G/cpu_guard.py" --allocate-uid); then
  echo "verifier: no unused sandbox uid could be allocated; refusing to grade" >&2
  echo "no unused sandbox uid" > "$OUT/verifier_refused"
  exit 2
fi
SUB=/workspace/raft
STATE=/var/grade
rm -rf "$STATE"
install -d -o 0 -g 0 -m 0755 "$STATE" "$STATE/src" "$STATE/bin"
install -d -o 1000 -g 1000 -m 0755 "$STATE/results"
install -d -o 0 -g 0 -m 0700 "$STATE/io"
install -d -o "$SUID" -g "$SUID" -m 0700 "$STATE/sandbox" "$STATE/sandbox/tmp" "$STATE/sandbox/out"
cp -R /opt/gocache "$STATE/sandbox/cache" && chown -R "$SUID:$SUID" "$STATE/sandbox/cache"
# Harbor recreates each artifact directory with mode 0777; the collected trees belong to the
# grader before any submitted code runs, and no other uid may write them.
for path in /workspace "$SUB" /workspace/output; do
  [ -e "$path" ] || [ -L "$path" ] || continue
  chown -R -P -h 1000:1000 "$path"
  find -P "$path" -type d -exec chmod a+rx,go-w {} +
  find -P "$path" -type f -exec chmod a+r,go-w {} +
done
chown 1000:1000 "$OUT" && chmod 0755 "$OUT"

as_grader() { setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all env -i PATH=/usr/local/go/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pydeps "$@"; }
SANDBOX=(setpriv --reuid="$SUID" --regid="$SUID" --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all
         env -i PATH=/usr/local/go/bin:/usr/bin:/bin HOME="$STATE/sandbox" TMPDIR="$STATE/sandbox/tmp"
         GOCACHE="$STATE/sandbox/cache" GOMODCACHE=/go/pkg/mod GOFLAGS=-mod=mod GOPROXY=off GOSUMDB=off
         GOTOOLCHAIN=local CGO_ENABLED=0 GOMAXPROCS=1 GOTELEMETRY=off)
echo "{\"budget\": $RUN_BUDGET, \"used\": 0, \"blocked\": null}" > "$STATE/io/cpu_ledger.json"
: > "$STATE/io/steps.jsonl"
guard() { python3 "$G/cpu_guard.py" --ledger "$STATE/io/cpu_ledger.json" --record "$STATE/io/steps.jsonl" --backstop "$BACKSTOP" --uid "$SUID" "$@"; }
kill_sandbox() {
  local round
  for round in $(seq 1 50); do
    pkill -KILL -u "$SUID" 2>/dev/null
    pgrep -u "$SUID" > /dev/null || return 0
    sleep 0.1
  done
  return 1
}
survivor=0
kill_sandbox || survivor=1

# 1. Edit rules and the report's named tests, decided by the grader without running submitted code.
as_grader python3 "$G/inspect_submission.py" "$G" "$SUB" "$STATE/results/admission.json" \
  || echo '{"refused": true, "reasons": ["inspection failed"]}' > "$STATE/results/admission.json"
as_grader python3 "$G/report_items.py" "$SUB" /workspace/output/REPAIR_REPORT.md "$STATE/results/named.json" \
  || echo '{"report": false, "named": {}, "count": 0, "too_many": false, "files": []}' > "$STATE/results/named.json"
refused=$(python3 -c "import json;print(int(json.load(open('$STATE/results/admission.json')).get('refused', True)))" 2>/dev/null || echo 1)

# 2. A root-owned copy of the submitted module (regular files only, never through a link), with
# the module definition as shipped, and a root-owned copy of the harness.
copy_tree() { rm -rf "$2"; install -d -m 0755 "$2"; cp -R --no-dereference "$1/." "$2/"; find "$2" -type l -delete; chown -R 0:0 "$2"; chmod -R a+rX,go-w "$2"; }
NONCE=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')
printf '%s' "$NONCE" > "$STATE/io/nonce"; chmod 0600 "$STATE/io/nonce"
printf '%s' "$NONCE" > "$STATE/results/nonce"; chown 1000:1000 "$STATE/results/nonce"
echo "$SEEDS" > "$STATE/results/seeds"
for c in "${CATEGORIES[@]}"; do echo none > "$STATE/results/$c.exit"; : > "$STATE/results/$c.jsonl"; done
echo none > "$STATE/results/ck.exit"
echo '{}' > "$STATE/results/named_outcomes.json"

if [ "$refused" = 0 ] && [ "$survivor" = 0 ]; then
  copy_tree "$SUB" "$STATE/src/sub"
  cp "$G/shipped/go.mod" "$G/shipped/go.sum" "$STATE/src/sub/"
  copy_tree "$G/harness" "$STATE/src/harness"
  ( cd "$STATE/src/harness" && go mod edit -replace go.etcd.io/raft/v3="$STATE/src/sub" )

  # 3. Build the harness against the submitted module as the sandbox user.
  build=$(guard --step harness_build --cap "${CAP[harness_build]}" --nproc "$NPROC_BUILD" --cwd "$STATE/src/harness" \
    --stdout "$STATE/io/harness_build.log" --stderr "$STATE/io/harness_build.log" \
    -- "${SANDBOX[@]}" go test -p 1 -c -o "$STATE/sandbox/out/harness.test" .)
  kill_sandbox || survivor=1
  if [ "$build" = 0 ] && [ "$survivor" = 0 ] && [ -f "$STATE/sandbox/out/harness.test" ] && [ ! -L "$STATE/sandbox/out/harness.test" ]; then
    install -o 0 -g 0 -m 0555 "$STATE/sandbox/out/harness.test" "$STATE/bin/harness.test"
    # 4. One run per category as the sandbox user: the nonce on stdin, records on fd 3, both opened by root.
    for c in "${CATEGORIES[@]}"; do
      install -o 0 -g 0 -m 0600 /dev/null "$STATE/io/$c.raw"
      guard --step "$c" --cap "${CAP[$c]}" --nproc "$NPROC_RUN" --cwd "$STATE/sandbox" --stdin "$STATE/io/nonce" --fd3 "$STATE/io/$c.raw" \
        --stdout "$STATE/io/$c.log" --stderr "$STATE/io/$c.log" \
        -- "${SANDBOX[@]}" CATEGORY="$c" SEEDS="$SEEDS" "$STATE/bin/harness.test" -test.run '^TestCategory$' -test.count=1 > "$STATE/io/$c.exit"
      kill_sandbox || { survivor=1; break; }
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$c.exit" "$STATE/results/$c.exit"
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$c.raw" "$STATE/results/$c.jsonl"
    done
  else
    for c in "${CATEGORIES[@]}"; do echo "harness_build:${build:-none}" > "$STATE/results/$c.exit"; done
  fi

  # 5. CK: the verifier's pristine upstream tests over the submitted library code.
  if [ "$survivor" = 0 ]; then
    copy_tree "$STATE/src/sub" "$STATE/src/ck"
    find "$STATE/src/ck" -name '*_test.go' -delete
    find "$STATE/src/ck" -type d -name testdata -prune -exec rm -rf {} +
    cp -R "$G/pristine/." "$STATE/src/ck/"
    chown -R 0:0 "$STATE/src/ck"; chmod -R a+rX,go-w "$STATE/src/ck"
    guard --step ck --cap "${CAP[ck]}" --nproc "$NPROC_BUILD" --cwd "$STATE/src/ck" \
      --stdout "$STATE/io/ck.log" --stderr "$STATE/io/ck.log" \
      -- "${SANDBOX[@]}" go test -p 1 -count=1 -skip TestInteraction ./... > "$STATE/io/ck.exit"
    kill_sandbox || survivor=1
    install -o 1000 -g 1000 -m 0644 "$STATE/io/ck.exit" "$STATE/results/ck.exit"
  fi

  # 6. K7: each named regression test is built against the library as shipped and against the
  # submitted library, then run alone; it must fail on the first and pass on the second.
  if [ "$survivor" = 0 ]; then
    CAP_BUILD="${CAP[named_build]}" CAP_RUN="${CAP[named_run]}" NPROC_RUN="$NPROC_RUN" NPROC_BUILD="$NPROC_BUILD" \
    BACKSTOP="$BACKSTOP" SUID="$SUID" MAX_NAMED="$MAX_NAMED" \
      python3 - "$G" "$STATE" "${SANDBOX[@]}" <<'NAMED' || true
import json, os, shutil, subprocess, sys
G, STATE, sandbox = sys.argv[1], sys.argv[2], sys.argv[3:]
env = os.environ
named = json.load(open(f"{STATE}/results/named.json"))
outcomes = {}
guard = ["python3", f"{G}/cpu_guard.py", "--ledger", f"{STATE}/io/cpu_ledger.json", "--record", f"{STATE}/io/steps.jsonl",
         "--backstop", env["BACKSTOP"], "--uid", env["SUID"]]
if named.get("report") and 0 < named.get("count", 0) <= int(env["MAX_NAMED"]):
    shipped = f"{STATE}/src/named-shipped"
    shutil.rmtree(shipped, ignore_errors=True)
    shutil.copytree(f"{G}/shipped", shipped, symlinks=True)
    for rel in named["files"]:
        src = os.path.join(f"{STATE}/src/sub", rel)
        if os.path.isfile(src) and not os.path.islink(src):
            os.makedirs(os.path.dirname(os.path.join(shipped, rel)), exist_ok=True)
            shutil.copyfile(src, os.path.join(shipped, rel))
    subprocess.run(["chown", "-R", "0:0", shipped]); subprocess.run(["chmod", "-R", "a+rX,go-w", shipped])
    roots = {"shipped": shipped, "submitted": f"{STATE}/src/sub"}
    for pkg, tests in named["named"].items():
        for lib, root in roots.items():
            exe = f"{STATE}/sandbox/out/named-{lib}-{pkg.replace('/', '_')}.test"
            build = subprocess.run([*guard, "--step", f"named_build:{lib}:{pkg}", "--cap", env["CAP_BUILD"], "--nproc", env["NPROC_BUILD"],
                                    "--cwd", os.path.join(root, pkg), "--", *sandbox, "go", "test", "-p", "1", "-c", "-o", exe, "."],
                                   capture_output=True, text=True).stdout.strip()
            subprocess.run(["pkill", "-KILL", "-u", env["SUID"]])
            if build != "0" or os.path.islink(exe) or not os.path.isfile(exe):
                for test in tests:
                    outcomes.setdefault(test, {})[lib] = f"build:{build}"
                continue
            bin_exe = f"{STATE}/bin/{os.path.basename(exe)}"
            subprocess.run(["install", "-o", "0", "-g", "0", "-m", "0555", exe, bin_exe])
            for test in tests:
                run = subprocess.run([*guard, "--step", f"named_run:{lib}:{test}", "--cap", env["CAP_RUN"], "--nproc", env["NPROC_RUN"],
                                      "--cwd", os.path.join(root, pkg), "--", *sandbox, bin_exe, "-test.run", f"^{test}$", "-test.count=1"],
                                     capture_output=True, text=True).stdout.strip()
                subprocess.run(["pkill", "-KILL", "-u", env["SUID"]])
                outcomes.setdefault(test, {})[lib] = run
json.dump(outcomes, open(f"{STATE}/io/named_outcomes.json", "w"), sort_keys=True)
NAMED
    [ -f "$STATE/io/named_outcomes.json" ] && install -o 1000 -g 1000 -m 0644 "$STATE/io/named_outcomes.json" "$STATE/results/named_outcomes.json"
  fi
fi
kill_sandbox || survivor=1
install -o 1000 -g 1000 -m 0644 "$STATE/io/steps.jsonl" "$STATE/results/steps.jsonl"
install -o 1000 -g 1000 -m 0644 "$STATE/io/cpu_ledger.json" "$STATE/results/cpu_ledger.json"
if [ "$survivor" = 1 ] || grep -q '"collision"' "$STATE/io/steps.jsonl"; then
  echo "verifier: a sandboxed process survived or the sandbox uid collided; refusing to grade" >&2
  echo "a sandboxed process survived or the sandbox uid collided" > "$OUT/verifier_refused"
  exit 2
fi

# 7. Score the compiled items with pytest, then Reward Kit. The judged items count only when one of K1
# to K4 passes and a regular, non-empty report was collected; otherwise, or when the judge returns no
# result, Reward Kit scores the compiled items as usual and the judged items at 0, and the cause is
# exported. A run the judge could not score also leaves the judge_unavailable marker.
as_grader python3 "$G/compiled.py" "$G" "$STATE/results" "$OUT"
RK=(env -u PYTHONPATH GRADE_RESULTS="$STATE/results" LITELLM_LOCAL_MODEL_COST_MAP=True)
note=/workspace/output/REPAIR_REPORT.md
cause=""
if ! as_grader "${RK[@]}" /opt/rewardkit/bin/python /tests/test_output.py; then cause=unrepaired
elif [ -L /workspace/output ] || [ -L "$note" ] || [ ! -f "$note" ] || [ ! -s "$note" ] \
  || ! as_grader python3 -c 'import sys; sys.exit(0 if open(sys.argv[1], "rb").read().decode("utf-8", "replace").strip() else 1)' "$note"; then
  cause=note-missing
else
  as_grader "${RK[@]}" OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_BASE_URL="$OPENAI_BASE_URL" REWARDKIT_JUDGE="$REWARDKIT_JUDGE" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" ANTHROPIC_API_BASE="${ANTHROPIC_API_BASE:-}" \
    /opt/rewardkit/bin/rewardkit /tests --workspace /workspace --output "$OUT/reward.json"
  if [ ! -s "$OUT/reward.json" ] || ! as_grader python3 - "$OUT/reward-details.json" <<'JUDGED'
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
    [ -f "$OUT/reward-details.json" ] && mv "$OUT/reward-details.json" "$OUT/judge-details.json"
    rm -f "$OUT/reward.json"
    echo "the LLM judge returned no result; the reward is the compiled items alone" > "$OUT/judge_unavailable"
  fi
fi
if [ ! -s "$OUT/reward.json" ]; then
  fb="$G/fallback"; [ "$cause" = judge-unavailable ] && fb="$G/nojudge"
  as_grader "${RK[@]}" GRADE_FALLBACK_CAUSE="$cause" /opt/rewardkit/bin/rewardkit "$fb" --workspace /workspace --output "$OUT/reward.json"
fi
echo "{\"fallback_cause\": \"${cause}\"}" > "$OUT/fallback_cause.json"
