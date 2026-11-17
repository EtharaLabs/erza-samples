#!/bin/bash
# Verifier for the repaired python-dateutil, in the separate verifier image; only the LLM judge uses the network.
# Root only prepares directories, locks the collected artifacts, copies root-owned build trees,
# supervises sandbox children, and moves their outputs once every uid-1001 process is gone.
# Submitted code runs only as uid 1001 (sandbox) with an empty environment. uid 1000 (grader)
# recomputes the expected results with the reference, scores, and runs Reward Kit, which writes the
# reward. No process that ran submitted code reads the reference or writes a reward.
#
# Termination. Grading outcomes come from exact comparisons and the deterministic sys.monitoring
# step budgets of runner/budget.py. Infrastructure guards only ever turn a run into a failure
# with reason "budget": prlimit resource limits (CPU seconds per child, address space,
# processes, open files, file size, core) and supervise.py's starvation watchdog, whole-run
# CPU budget, and per-child wall-clock ceiling. The constants are listed below and in REPORT.md.
# The 13 children below have CPU limits summing to 1460 CPU-s, so the whole-run CPU ceiling is
# min(RUN_BUDGET 1500, 1460) = 1460 CPU-s, below 1800 (half the 3600 s verifier timeout). Each
# child's wall ceiling is min(limit / 0.05, 200 s), which is 200 s for every child here, so the
# children together run at most 2600 s of wall time. A child whose CPU limit exceeds the CPU it can
# burn in 200 s (K3, the suite runs) is stopped by the wall ceiling first; both end in "budget".
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
install -d -o 1000 -g 1000 -m 0755 /logs/verifier

G=/opt/grader
R=/opt/runner
SUB=/workspace/dateutil
NOTE=/workspace/output/NOTES.md
STATE=/var/grade
B=$STATE/build
# Python's zone data for every process here: the tzdata 2026.5 wheel (IANA 2026e, main form), the same
# TZPATH the agent image sets. The Dockerfile resolves and checks this path at build time. Suite runs
# also get the agent image's local zone, TZ=America/New_York; the child, the signature probe and the
# grader run with TZ=UTC.
TZPATH_PY=/usr/local/lib/python3.12/site-packages/tzdata/zoneinfo
SUITE_TZ=America/New_York
# RLIMIT_CPU per sandbox child, in CPU seconds: at least 10x the oracle's CPU measured under the same
# parallel load as the image runs (five containers at once on 10 CPUs, arm64; REPORT.md). Oracle
# maxima over those runs, default cases: K1 3.66, K2 8.89, K3 13.65, K4 3.92, K5 1.56, K6 8.68,
# sigs 0.11, collect 2.88, suite 19.25. Limits are 13x to 16x these (sigs 90x).
CPU_K1=50 CPU_K2=120 CPU_K3=180 CPU_K4=55 CPU_K5=25 CPU_K6=120
CPU_SIGS=10 CPU_COLLECT=40 CPU_SUITE=260
rm -rf "$STATE"
install -d -o 0 -g 0 -m 0755 "$STATE" "$B"
install -d -o 1000 -g 1000 -m 0750 "$STATE/results"
install -d -o 0 -g 0 -m 0700 "$STATE/io"
echo 0 > "$STATE/io/cpu-ledger"
TMPDIR="$STATE/io"; export -n TMPDIR

# 1. Root first: the collected artifacts belong to the grader and nobody else may write them.
# Harbor recreates each artifact directory, and their parent, with mode 0777.
[ -d /workspace ] && [ ! -L /workspace ] && chown 0:0 /workspace && chmod 0755 /workspace
for path in "$SUB" /workspace/output; do
  [ -e "$path" ] || [ -L "$path" ] || continue
  chown -R -P -h 1000:1000 "$path"
  find -P "$path" -type d -exec chmod a+rx,go-w {} +
  find -P "$path" -type f -exec chmod a+r,go-w {} +
done
# The harness scripts hold no answer, but uid 1001 has no reason to read them: grader and root only.
chown -R 0:1000 /tests 2>/dev/null && chmod -R u+rwX,g+rX,g-w,o-rwx /tests 2>/dev/null

as_grader() {
  setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
    env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/grader TZ=UTC PYTHONTZPATH="$TZPATH_PY" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True "$@"
}
# sandbox NAME CPU CMD...: one fresh home, the command as uid 1001 under prlimit, supervised by
# root's supervise.py, which writes $STATE/io/NAME.status.json. fds 0, 1 and 3 are opened by root.
sandbox() {
  local name=$1 cpu=$2 home="$STATE/sandbox-$1"; shift 2
  install -d -o 1001 -g 1001 -m 0700 "$home" "$home/tmp"
  ( cd "$home" && python3 -I -B "$G/supervise.py" --cpu "$cpu" --ledger "$STATE/io/cpu-ledger" \
      --status "$STATE/io/$name.status.json" -- \
      setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
      prlimit --cpu="$cpu" --as=4294967296 --nproc=256 --nofile=1024 --fsize=268435456 --core=0 \
      env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$home" TMPDIR="$home/tmp" TZ="${CHILD_TZ:-UTC}" LANG=C.UTF-8 \
      PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONTZPATH="$TZPATH_PY" "$@" )
}
# SIGKILL every live uid-1001 process until none is left (zombies, which cannot run, are skipped).
kill_sandbox() { python3 -I -B "$G/supervise.py" --kill; }
collect() { install -o 1000 -g 1000 -m 0640 "$STATE/io/$1" "$STATE/results/$2"; }
fresh() { install -o 0 -g 0 -m 0600 /dev/null "$STATE/io/$1"; }
missing_status() { echo '{"cpu": 0, "exit": null, "status": "not-run"}' > "$STATE/io/$1.status.json"; }
kill_sandbox

# 2. Root-owned build trees: the submitted library (src/dateutil only, symbolic links dropped),
# the shipped library, and two suites that share the pristine pytest configuration.
install -d -m 0755 "$B/own-lib" "$B/shipped-lib" "$B/suite-shipped" "$B/suite-own"
if [ -d "$SUB/src/dateutil" ] && [ ! -L "$SUB" ] && [ ! -L "$SUB/src" ] && [ ! -L "$SUB/src/dateutil" ]; then
  cp -R --no-dereference "$SUB/src/dateutil" "$B/own-lib/dateutil"
fi
if [ -d "$SUB/tests" ] && [ ! -L "$SUB/tests" ]; then
  cp -R --no-dereference "$SUB/tests" "$B/suite-own/tests"
fi
cp -R "$G/shipped/src/dateutil" "$B/shipped-lib/dateutil"
cp -R "$G/shipped/tests" "$B/suite-shipped/tests"
cp "$G/shipped/pyproject.toml" "$B/suite-shipped/pyproject.toml"
cp "$G/shipped/pyproject.toml" "$B/suite-own/pyproject.toml"
find -P "$B" -type l -delete
find -P "$B" \( -name __pycache__ -o -name .pytest_cache -o -name .hypothesis \) -prune -exec rm -rf {} +
# The agent image installs the workspace editable as python-dateutil 4.0.0, so every process there,
# subprocesses included, imports the workspace library and reads that distribution metadata. Each
# library root gets the same metadata here, and the suite runs get PYTHONPATH=<library root>.
for lib in "$B/own-lib" "$B/shipped-lib"; do
  install -d -m 0755 "$lib/python_dateutil-4.0.0.dist-info"
  printf 'Metadata-Version: 2.1\nName: python-dateutil\nVersion: 4.0.0\n' > "$lib/python_dateutil-4.0.0.dist-info/METADATA"
done
chown -R 0:0 "$B"; chmod -R a+rX,go-w "$B"

# 3. The submitted library through dateutil's public API, one child per category.
for cases in "$G"/cases/K?.jsonl; do
  k=$(basename "$cases" .jsonl); cpu_var="CPU_$k"
  install -o 0 -g 0 -m 0600 "$cases" "$STATE/io/$k.in"
  fresh "$k.raw"
  if [ -f "$B/own-lib/dateutil/__init__.py" ]; then
    sandbox "child-$k" "${!cpu_var}" python3 -I -B "$R/child.py" "$B/own-lib" \
      < "$STATE/io/$k.in" 3>> "$STATE/io/$k.raw" > /dev/null 2>&1
  else
    missing_status "child-$k"
  fi
  kill_sandbox
  collect "$k.raw" "$k.raw"
  collect "child-$k.status.json" "$k.status.json"
done

# 4. Public signatures.
fresh own-sigs.json
sandbox own-sigs "$CPU_SIGS" python3 -I -B "$R/sigs.py" "$B/own-lib" 3>> "$STATE/io/own-sigs.json" < /dev/null > /dev/null 2>&1
kill_sandbox
collect own-sigs.json own-sigs.json
collect own-sigs.status.json own-sigs.status.json

# 5. Three suite runs, each in its own process with no grader code but a launcher that puts the
# library first: the pristine shipped suite on the submitted library (C06), the submission's own
# tests on the submitted library (C07, C09), and on the shipped library (C07). Each is a separate
# --collect-only pass plus a run writing pytest's own junit file into a root-made directory
# (owner grader, mode 0733: uid 1001 may create, never list or read back). Root copies that file
# into the grader's results only after every uid-1001 process is gone, and only when it is a
# regular, single-link file owned by uid 1001 and at most 32 MiB.
PYARGS=(-p no:cacheprovider -o addopts= -o junit_family=xunit1 -W ignore::pytest.PytestUnknownMarkWarning
  --hypothesis-profile=ci --continue-on-collection-errors -q)
suite_run() {
  local name=$1 lib=$2 suite=$3 dir="$STATE/junit-$1" xml
  local args=(-c "$suite/pyproject.toml" --rootdir "$suite" "${PYARGS[@]}" "$suite/tests")
  fresh "$name.collect"
  if [ -d "$suite/tests" ]; then
    CHILD_TZ=$SUITE_TZ sandbox "$name-collect" "$CPU_COLLECT" env PYTHONPATH="$lib" python3 -I -B "$R/pytest_launch.py" "$lib" "${args[@]}" --collect-only \
      < /dev/null > "$STATE/io/$name.collect" 2> /dev/null
    kill_sandbox
    install -d -o 1000 -g 1000 -m 0733 "$dir"
    CHILD_TZ=$SUITE_TZ sandbox "$name" "$CPU_SUITE" env PYTHONPATH="$lib" python3 -I -B "$R/pytest_launch.py" "$lib" "${args[@]}" --junitxml="$dir/report.xml" \
      < /dev/null > /dev/null 2>&1
    kill_sandbox
  else
    missing_status "$name-collect"; missing_status "$name"
  fi
  xml="$dir/report.xml"
  if [ -f "$xml" ] && [ ! -L "$xml" ] && [ "$(stat -c %u:%h "$xml")" = 1001:1 ] && [ "$(stat -c %s "$xml")" -le 33554432 ]; then
    install -o 1000 -g 1000 -m 0640 "$xml" "$STATE/results/$name.xml"
  fi
  collect "$name.collect" "$name.collect"
  collect "$name-collect.status.json" "$name-collect.status.json"
  collect "$name.status.json" "$name.status.json"
}
suite_run shipped-suite "$B/own-lib" "$B/suite-shipped"
suite_run own-suite "$B/own-lib" "$B/suite-own"
suite_run own-on-shipped "$B/shipped-lib" "$B/suite-own"
kill_sandbox
install -o 1000 -g 1000 -m 0640 "$STATE/io/cpu-ledger" "$STATE/results/cpu-ledger"

# 6. Scoring as the grader: expected results come from the reference now, never from a file.
grade() { as_grader python3 -I -B "$G/grade.py" "$@"; }
for name in shipped-suite own-suite own-on-shipped; do
  grade suite-report --junit "$STATE/results/$name.xml" --collect "$STATE/results/$name.collect" \
    --collect-status "$STATE/results/$name-collect.status.json" --status "$STATE/results/$name.status.json" \
    --out "$STATE/results/$name.json"
done
grade score --cases "$G/cases" --raw "$STATE/results" --status "$STATE/results" \
  --out "$STATE/results/categories.json" --diagnostics "$STATE/results/score-diagnostics.json"
grade assemble --categories "$STATE/results/categories.json" --baseline "$G/shipped_baseline.json" \
  --shipped-suite "$STATE/results/shipped-suite.json" --own-suite "$STATE/results/own-suite.json" \
  --own-on-shipped "$STATE/results/own-on-shipped.json" --shipped-sigs "$G/shipped_sigs.json" \
  --own-sigs "$STATE/results/own-sigs.json" --manifest "$G/shipped_manifest.json" --workspace "$SUB" \
  --out "$STATE/results/results.json" --diagnostics "$STATE/results/check-diagnostics.json"

# 7. Reward Kit over the compiled and the judged criteria. A gate inside the compiled criteria scores
# every criterion 0 when none of C01 to C05 passes; the judge runs only when one of them passes and
# /workspace/output/NOTES.md is a regular, non-empty UTF-8 file of at most 64 KiB. Otherwise, or when
# the judge returns no result, Reward Kit scores the compiled criteria as usual and the judged ones at
# 0, and the cause is exported. A run the judge could not score also leaves the judge_unavailable marker.
cause=""
if ! as_grader env GRADE_RESULTS="$STATE/results/results.json" python3 -I -B /tests/test_output.py; then cause=unrepaired
elif [ -L /workspace/output ] || [ -L "$NOTE" ] || [ ! -f "$NOTE" ] \
  || ! as_grader python3 -I -B -c 'import sys
raw = open(sys.argv[1], "rb").read(64 * 1024 + 1)
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    sys.exit(1)
sys.exit(0 if len(raw) <= 64 * 1024 and text.strip() else 1)' "$NOTE"; then
  cause=note-missing
else
  as_grader env GRADE_RESULTS="$STATE/results/results.json" OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_BASE_URL="$OPENAI_BASE_URL" REWARDKIT_JUDGE="$REWARDKIT_JUDGE" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    ANTHROPIC_API_BASE="${ANTHROPIC_API_BASE:-}" rewardkit /tests --workspace /workspace --output /logs/verifier/reward.json
  if [ ! -s /logs/verifier/reward.json ] || ! as_grader python3 -I -B - /logs/verifier/reward-details.json <<'JUDGED'
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
    [ -f /logs/verifier/reward-details.json ] && mv /logs/verifier/reward-details.json /logs/verifier/judge-details.json
    rm -f /logs/verifier/reward.json
    echo "the LLM judge returned no result; the reward is the compiled criteria alone" > /logs/verifier/judge_unavailable
  fi
fi
if [ ! -s /logs/verifier/reward.json ]; then
  fb=/opt/grader/fallback; [ "$cause" = judge-unavailable ] && fb=/opt/grader/nojudge
  as_grader env GRADE_RESULTS="$STATE/results/results.json" GRADE_FALLBACK_CAUSE="$cause" \
    rewardkit "$fb" --workspace /workspace --output /logs/verifier/reward.json
fi
echo "{\"fallback_cause\": \"${cause}\"}" > /logs/verifier/fallback_cause.json

# 8. The grader's results beside the reward.
for name in results.json check-diagnostics.json score-diagnostics.json cpu-ledger \
    own-sigs.status.json K1.status.json K2.status.json K3.status.json K4.status.json K5.status.json K6.status.json \
    shipped-suite.status.json own-suite.status.json own-on-shipped.status.json \
    shipped-suite-collect.status.json own-suite-collect.status.json own-on-shipped-collect.status.json; do
  [ -f "$STATE/results/$name" ] && install -o 1000 -g 1000 -m 0644 "$STATE/results/$name" "/logs/verifier/$name"
done
exit 0
