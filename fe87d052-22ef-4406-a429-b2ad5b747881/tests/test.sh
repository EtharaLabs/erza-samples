#!/bin/bash
# Grades the collected fast_float tree: the compiled items offline, then the judged items through the
# LLM judge, combined into one reward. Root only prepares directories, opens the probe's input and
# output descriptors, drops privilege, and kills leftover processes. Agent code is compiled and run as
# a uid allocated for this run alone with an empty environment; uid 1000 (grader) generates the cases,
# decides admissibility, compares every record with the rational oracle, scores the items, and writes
# the reward. No process that ran agent code writes a result the grader reads without root first
# copying it out of a directory the sandbox cannot reach.
set -uo pipefail
# Judge model. judge.toml names Fable 5.1 (Anthropic). With no Anthropic key but an OpenAI key, Reward Kit
# judges the same rubric with an OpenAI model instead (REWARDKIT_JUDGE); with neither key the no-judge path
# applies and the reward is the compiled score alone.
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"; export OPENAI_BASE_URL
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then export REWARDKIT_JUDGE=openai/gpt-6-astra; else export REWARDKIT_JUDGE=; fi
# Every sandboxed step runs under $G/cpu_guard.py, which caps the CPU time of the step's whole
# process tree (the compiler driver, cc1plus, as, and collect2 share one allowance) and charges it
# to one CPU budget for the whole run. A step over its cap fails with reason cpu; once the budget
# is spent, every remaining step fails with reason budget without running. Both are decided from
# CPU time, never from wall-clock time. Each cap is ceil(20 x the oracle's largest measured tree
# CPU time for that step across linux/amd64 and linux/arm64); the regression tests the report
# names run under the limits instruction.md states for them. Submitted code runs as a uid this
# run allocates for itself (random in 2^24 to 2^31 - 1, kept only when no process holds it, and
# probed again before every step) under RLIMIT_NPROC: 1 for the runs, so they cannot create a
# process or a thread, and 4 for the unmodified compiler (driver, collect2, ld). BACKSTOP is a
# wall-clock bound that only ends a step whose CPU time stays under its cap; the first such step
# latches the run, and every later step fails with reason backstop without running.
CAP_PROBE_BUILD=124
CAP_KEPT_BUILD=115
CAP_KEPT_RUN=4
declare -A CAP_CATEGORY=([C1]=2 [C2]=2 [C3]=3 [C4]=2 [C5]=3 [C6]=4 [C7]=2 [C8]=3)
CAP_SHIPPED_RUN=2
# One callgrind count of the meter on one cost corpus: ceil(20 x the reference's largest).
CAP_COST_RUN=34
# The limits instruction.md states for each regression test the report names (CPU seconds).
CAP_NAMED_BUILD=120
CAP_NAMED_RUN=10
MAX_NAMED=16
RUN_BUDGET=2022
BACKSTOP=600
NPROC_RUN=1
NPROC_BUILD=4
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt /logs/verifier/reward-details.json \
  /logs/verifier/judge_unavailable /logs/verifier/verifier_refused
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
# The sandbox uid belongs to this run alone; without one the verifier refuses to grade, scores 0 and
# leaves the verifier_refused marker so the run is recognisable as an infrastructure failure.
if ! SUID=$(python3 "$G/cpu_guard.py" --allocate-uid); then
  echo "verifier: no unused sandbox uid could be allocated; refusing to grade" >&2
  echo "no unused sandbox uid" > /logs/verifier/verifier_refused
  exit 2
fi
LIB=/workspace/fast_float
STATE=/var/grade
rm -rf "$STATE"
install -d -o 0 -g 0 -m 0755 "$STATE" "$STATE/build" "$STATE/bin"
install -d -o 1000 -g 1000 -m 0755 "$STATE/results"
install -d -o 0 -g 0 -m 0700 "$STATE/io"
TMPDIR="$STATE/io"; export -n TMPDIR
install -d -o "$SUID" -g "$SUID" -m 0700 "$STATE/sandbox" "$STATE/sandbox/tmp" "$STATE/sandbox/out"
# Harbor recreates each artifact directory with mode 0777; before any submitted code runs, the
# collected trees belong to the grader and no other uid may write them.
for path in /workspace "$LIB" /workspace/spec /workspace/output; do
  [ -e "$path" ] || [ -L "$path" ] || continue
  chown -R -P -h 1000:1000 "$path"
  find -P "$path" -type d -exec chmod a+rx,go-w {} +
  find -P "$path" -type f -exec chmod a+r,go-w {} +
done

as_grader() { setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 GRADE_RESULTS="$STATE/results" "$@"; }
SANDBOX=(setpriv --reuid="$SUID" --regid="$SUID" --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all
         env -i PATH=/usr/bin:/bin HOME="$STATE/sandbox" TMPDIR="$STATE/sandbox/tmp")
echo "{\"budget\": $RUN_BUDGET, \"used\": 0, \"blocked\": null}" > "$STATE/io/cpu_ledger.json"
: > "$STATE/io/steps.jsonl"
guard() { python3 "$G/cpu_guard.py" --ledger "$STATE/io/cpu_ledger.json" --record "$STATE/io/steps.jsonl" --backstop "$BACKSTOP" --uid "$SUID" --cwd "$STATE/sandbox" "$@"; }
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

# 1. Admissibility and edit scope, decided by the grader without executing submitted code.
as_grader python3 "$G/inspect_submission.py" "$G" "$STATE/results" 2>/dev/null \
  || echo '{"refused": true, "reasons": ["inspection failed"], "changed": false}' > "$STATE/results/verdict.json"
refused=$(python3 -c "import json;print(int(json.load(open('$STATE/results/verdict.json')).get('refused', True)))" 2>/dev/null || echo 1)

# 2. The grader writes every category's cases before any agent code runs.
for c in C1 C2 C3 C4 C5 C6 C7 C8; do
  as_grader python3 "$G/cases.py" "$c" "$STATE/results/$c.in" || refused=1
done
as_grader python3 "$G/cost_cases.py" "$STATE/results/cost" || refused=1
install -d -o 1000 -g 1000 -m 0755 "$STATE/results/cost_sub" "$STATE/results/cost_ref"
# The report's Reproduction lines and named regression tests, read by the grader without running code.
as_grader python3 "$G/report_items.py" "$G" "$STATE/results" || refused=1

echo '{}' > "$STATE/io/kept.json"
echo '{}' > "$STATE/io/named.json"
: > "$STATE/io/shipped.raw"
echo none > "$STATE/io/shipped.exit"
echo '{"readable": false, "undefined": []}' > "$STATE/io/symbols.json"
if [ "$refused" = 0 ] && [ "$survivor" = 0 ]; then
  # 3. A root-owned copy of the submitted headers: regular files only, never through a link.
  install -d -m 0755 "$STATE/build/include"
  cp -R --no-dereference "$LIB/include/." "$STATE/build/include/"
  find "$STATE/build/include" -type l -delete
  chown -R 0:0 "$STATE/build"; chmod -R a+rX,go-w "$STATE/build"

  # 4. Compile the verifier's probe against the submitted headers as the sandbox user.
  build=$(guard --step probe_build --cap "$CAP_PROBE_BUILD" --nproc "$NPROC_BUILD" --stdout "$STATE/io/build.log" --stderr "$STATE/io/build.log" \
    -- "${SANDBOX[@]}" g++ -std=c++17 -O2 -I "$STATE/build/include" "$G/probe.cpp" -o "$STATE/sandbox/out/probe")
  kill_sandbox || survivor=1
  if [ "$build" = 0 ] && [ "$survivor" = 0 ] && [ -f "$STATE/sandbox/out/probe" ] && [ ! -L "$STATE/sandbox/out/probe" ]; then
    install -o 0 -g 0 -m 0555 "$STATE/sandbox/out/probe" "$STATE/bin/probe"
    # The probe's undefined dynamic symbols, read by root from the root-owned copy.
    nm -D --undefined-only "$STATE/bin/probe" 2>/dev/null | awk '{print $NF}' \
      | python3 -c "import json,sys;print(json.dumps({'readable': True, 'undefined': sorted(set(l.strip() for l in sys.stdin if l.strip()))}))" \
      > "$STATE/io/symbols.json"
    # 5. Run each category as the sandbox user; records go to fd 3, opened by root.
    for c in C1 C2 C3 C4 C5 C6 C7 C8; do
      install -o 0 -g 0 -m 0600 "$STATE/results/$c.in" "$STATE/io/$c.in"
      install -o 0 -g 0 -m 0600 /dev/null "$STATE/io/$c.raw"
      guard --step "$c" --cap "${CAP_CATEGORY[$c]}" --nproc "$NPROC_RUN" --stdin "$STATE/io/$c.in" --fd3 "$STATE/io/$c.raw" \
        -- "${SANDBOX[@]}" "$STATE/bin/probe" > "$STATE/io/$c.exit"
      kill_sandbox || { survivor=1; break; }
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$c.exit" "$STATE/results/$c.exit"
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$c.raw" "$STATE/results/$c.out"
    done
  else
    for c in C1 C2 C3 C4 C5 C6 C7 C8; do
      echo "probe_build:${build:-none}" > "$STATE/io/$c.exit"
      install -o 1000 -g 1000 -m 0644 "$STATE/io/$c.exit" "$STATE/results/$c.exit"
    done
  fi
  kill_sandbox || survivor=1

  # 5b. Conversion cost. The verifier's meter, built against the submitted headers as the sandbox
  # user, is counted by callgrind on each cost corpus as the sandbox user; the meter built into the
  # image against fast_float 8.3.3 as released is counted on the same corpus in this run by the grader.
  mbuild=$(guard --step meter_build --cap "$CAP_PROBE_BUILD" --nproc "$NPROC_BUILD" --stdout "$STATE/io/meter_build.log" --stderr "$STATE/io/meter_build.log" \
    -- "${SANDBOX[@]}" g++ -std=c++17 -O2 -I "$STATE/build/include" "$G/meter.cpp" -o "$STATE/sandbox/out/meter")
  kill_sandbox || survivor=1
  for c in $(ls "$STATE/results/cost" | sed 's/[.]in$//'); do
    echo "meter_build:${mbuild:-none}" > "$STATE/io/cost.exit"
    : > "$STATE/io/cost.hash"; : > "$STATE/io/cost.cg"
    if [ "$mbuild" = 0 ] && [ "$survivor" = 0 ] && [ -f "$STATE/sandbox/out/meter" ] && [ ! -L "$STATE/sandbox/out/meter" ]; then
      install -o 0 -g 0 -m 0555 "$STATE/sandbox/out/meter" "$STATE/bin/meter"
      install -o 0 -g 0 -m 0600 "$STATE/results/cost/$c.in" "$STATE/io/cost.in"
      rm -f "$STATE/sandbox/out/cost.cg"
      guard --step "cost:$c" --cap "$CAP_COST_RUN" --nproc "$NPROC_RUN" --stdin "$STATE/io/cost.in" --stdout "$STATE/io/cost.hash" \
        -- "${SANDBOX[@]}" valgrind --tool=callgrind "--toggle-collect=convert_all*" --callgrind-out-file="$STATE/sandbox/out/cost.cg" "$STATE/bin/meter" \
        > "$STATE/io/cost.exit"
      kill_sandbox || survivor=1
      [ -f "$STATE/sandbox/out/cost.cg" ] && [ ! -L "$STATE/sandbox/out/cost.cg" ] && cp --no-dereference "$STATE/sandbox/out/cost.cg" "$STATE/io/cost.cg"
    fi
    for f in exit hash cg; do install -o 1000 -g 1000 -m 0644 "$STATE/io/cost.$f" "$STATE/results/cost_sub/$c.$f"; done
    as_grader valgrind --tool=callgrind "--toggle-collect=convert_all*" --callgrind-out-file="$STATE/results/cost_ref/$c.cg" \
      "$G/bin/reference_meter" < "$STATE/results/cost/$c.in" > "$STATE/results/cost_ref/$c.hash" 2>/dev/null
  done

  # 6. The kept upstream tests, from the verifier's own pristine sources, built and run one at
  # a time as the sandbox user against the submitted headers.
  CAP_KEPT_BUILD="$CAP_KEPT_BUILD" CAP_KEPT_RUN="$CAP_KEPT_RUN" BACKSTOP="$BACKSTOP" SUID="$SUID" NPROC_RUN="$NPROC_RUN" NPROC_BUILD="$NPROC_BUILD" \
    python3 - "$G" "$STATE" "${SANDBOX[@]}" <<'KEPT' || true
import json, os, subprocess, sys
G, STATE, sandbox = sys.argv[1], sys.argv[2], sys.argv[3:]
names = json.load(open(f"{G}/kept_tests.json"))
suid = os.environ["SUID"]
guard = ["python3", f"{G}/cpu_guard.py", "--ledger", f"{STATE}/io/cpu_ledger.json", "--record", f"{STATE}/io/steps.jsonl",
         "--backstop", os.environ["BACKSTOP"], "--uid", suid, "--cwd", f"{STATE}/sandbox"]
result = {}
for name in names:
    exe = f"{STATE}/sandbox/out/kept-{name}"
    build = subprocess.run([*guard, "--step", f"kept_build:{name}", "--cap", os.environ["CAP_KEPT_BUILD"], "--nproc", os.environ["NPROC_BUILD"], "--", *sandbox,
                            "g++", "-std=c++17", "-O2", "-I", f"{STATE}/build/include", f"{G}/upstream_tests/{name}.cpp", "-o", exe],
                           capture_output=True, text=True).stdout.strip()
    subprocess.run(["pkill", "-KILL", "-u", suid])
    if build != "0" or os.path.islink(exe) or not os.path.isfile(exe):
        result[name] = f"build:{build}"
        continue
    safe = f"{STATE}/bin/kept-{name}"
    subprocess.run(["install", "-o", "0", "-g", "0", "-m", "0555", exe, safe], check=True)
    run = subprocess.run([*guard, "--step", f"kept_run:{name}", "--cap", os.environ["CAP_KEPT_RUN"], "--nproc", os.environ["NPROC_RUN"], "--", *sandbox, safe],
                         capture_output=True, text=True).stdout.strip()
    subprocess.run(["pkill", "-KILL", "-u", suid])
    result[name] = 0 if run == "0" else run
json.dump(result, open(f"{STATE}/io/kept.json", "w"), sort_keys=True)
KEPT
  kill_sandbox || survivor=1

  # 7. K10: the input of every well-formed Reproduction line through the library as shipped, by
  # the verifier's own probe built into the image from the shipped headers, as the sandbox user.
  install -o 0 -g 0 -m 0600 "$STATE/results/shipped.in" "$STATE/io/shipped.in"
  guard --step shipped_probe --cap "$CAP_SHIPPED_RUN" --nproc "$NPROC_RUN" --stdin "$STATE/io/shipped.in" --fd3 "$STATE/io/shipped.raw" \
    -- "${SANDBOX[@]}" "$G/bin/shipped_probe" > "$STATE/io/shipped.exit"
  kill_sandbox || survivor=1

  # 8. K11: every regression test the report names, built with the stated command against the
  # submitted headers and against the shipped headers, and run, as the sandbox user.
  CAP_NAMED_BUILD="$CAP_NAMED_BUILD" CAP_NAMED_RUN="$CAP_NAMED_RUN" MAX_NAMED="$MAX_NAMED" BACKSTOP="$BACKSTOP" SUID="$SUID" \
    NPROC_RUN="$NPROC_RUN" NPROC_BUILD="$NPROC_BUILD" python3 - "$G" "$STATE" "$LIB" "${SANDBOX[@]}" <<'NAMED' || true
import json, os, subprocess, sys
G, STATE, LIB, sandbox = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
named = json.load(open(f"{STATE}/results/named_tests.json"))
suid = os.environ["SUID"]
guard = ["python3", f"{G}/cpu_guard.py", "--ledger", f"{STATE}/io/cpu_ledger.json", "--record", f"{STATE}/io/steps.jsonl",
         "--backstop", os.environ["BACKSTOP"], "--uid", suid, "--cwd", f"{STATE}/sandbox"]
result = {"count": len(named), "too_many": len(named) > int(os.environ["MAX_NAMED"]), "tests": {}}
for item in [] if result["too_many"] else named:
    name, row = item["name"], {}
    if not item["exists"]:
        result["tests"][name] = {"missing": True}
        continue
    for side, include in (("submitted", f"{STATE}/build/include"), ("shipped", f"{G}/shipped/include")):
        exe = f"{STATE}/sandbox/out/named-{side}-{name}"
        build = subprocess.run([*guard, "--step", f"named_build:{side}:{name}", "--cap", os.environ["CAP_NAMED_BUILD"], "--nproc", os.environ["NPROC_BUILD"],
                                "--", *sandbox, "g++", "-std=c++17", "-O2", "-I", include, f"{LIB}/tests/{name}.cpp", "-o", exe],
                               capture_output=True, text=True).stdout.strip()
        subprocess.run(["pkill", "-KILL", "-u", suid])
        if build != "0" or os.path.islink(exe) or not os.path.isfile(exe):
            row[side] = f"build:{build}"
            continue
        safe = f"{STATE}/bin/named-{side}-{name}"
        subprocess.run(["install", "-o", "0", "-g", "0", "-m", "0555", exe, safe], check=True)
        row[side] = subprocess.run([*guard, "--step", f"named_run:{side}:{name}", "--cap", os.environ["CAP_NAMED_RUN"], "--nproc", os.environ["NPROC_RUN"],
                                    "--", *sandbox, safe], capture_output=True, text=True).stdout.strip()
        subprocess.run(["pkill", "-KILL", "-u", suid])
    result["tests"][name] = row
json.dump(result, open(f"{STATE}/io/named.json", "w"), sort_keys=True)
NAMED
  kill_sandbox || survivor=1
fi
install -o 1000 -g 1000 -m 0644 "$STATE/io/kept.json" "$STATE/results/kept.json"
install -o 1000 -g 1000 -m 0644 "$STATE/io/named.json" "$STATE/results/named.json"
install -o 1000 -g 1000 -m 0644 "$STATE/io/shipped.raw" "$STATE/results/shipped.out"
install -o 1000 -g 1000 -m 0644 "$STATE/io/shipped.exit" "$STATE/results/shipped.exit"
install -o 1000 -g 1000 -m 0644 "$STATE/io/symbols.json" "$STATE/results/symbols.json"
install -o 1000 -g 1000 -m 0644 "$STATE/io/steps.jsonl" "$STATE/results/steps.jsonl"
if [ "$survivor" != 0 ] || pgrep -u "$SUID" > /dev/null; then
  echo '{"refused": true, "reasons": ["a sandbox process survived"], "changed": false}' > "$STATE/results/verdict.json"
fi
chown -R 1000:1000 "$STATE/results"; chmod -R go-w "$STATE/results"
# A step that found the run's uid held by a process it did not start voids the run: no reward.
if python3 -c "import json,sys; sys.exit(0 if json.load(open('$STATE/io/cpu_ledger.json')).get('collision') else 1)"; then
  echo "verifier: sandbox uid $SUID was held by a process this run did not start; refusing to grade" >&2
  echo "sandbox uid collision" > /logs/verifier/verifier_refused
  exit 2
fi

# 9. Score as the grader: the pytest categories, then Reward Kit. The judged items count only when the
# library repairs at least one of K1 to K4 and a regular, non-empty report was collected; otherwise,
# or when the judge returns no result, Reward Kit scores the compiled items as usual and the judged
# items at 0, and the cause is exported. A run the judge could not score also leaves the
# judge_unavailable marker.
as_grader python3 -m pytest -q -p no:cacheprovider "$G/test_categories.py" --junitxml="$STATE/results/junit.xml" \
  > "$STATE/results/pytest.log" 2>&1
note=/workspace/output/REPAIR_REPORT.md
cause=""
if ! as_grader python3 /tests/test_output.py; then cause=unrepaired
elif [ -L /workspace/output ] || [ -L "$note" ] || [ ! -f "$note" ] || [ ! -s "$note" ] \
  || ! as_grader python3 -c 'import sys; sys.exit(0 if open(sys.argv[1], "rb").read().decode("utf-8", "replace").strip() else 1)' "$note"; then
  cause=note-missing
else
  # The judge reads the report through Reward Kit, which skips an oversized file. Give it the same
  # per-line view the compiled items use: a line over 64 KiB is replaced by a marker naming its size.
  python3 - "$note" <<'CAP'
import sys
path = sys.argv[1]
with open(path, "rb") as f:
    lines = [l if len(l) <= 65536 else b"[line over 64 KiB omitted from the judged copy: %d bytes]\n" % len(l) for l in f]
with open(path, "wb") as f:
    f.writelines(lines)
CAP
  as_grader env OPENAI_API_KEY="${OPENAI_API_KEY:-}" OPENAI_BASE_URL="$OPENAI_BASE_URL" REWARDKIT_JUDGE="$REWARDKIT_JUDGE" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" ANTHROPIC_API_BASE="${ANTHROPIC_API_BASE:-}" LITELLM_LOCAL_MODEL_COST_MAP=True \
    rewardkit /tests --workspace /workspace --output /logs/verifier/reward.json
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
    [ -f /logs/verifier/reward-details.json ] && mv /logs/verifier/reward-details.json /logs/verifier/judge-details.json
    rm -f /logs/verifier/reward.json
    echo "the LLM judge returned no result; the reward is the compiled items alone" > /logs/verifier/judge_unavailable
  fi
fi
if [ ! -s /logs/verifier/reward.json ]; then
  fb="$G/fallback"; [ "$cause" = judge-unavailable ] && fb="$G/nojudge"
  as_grader env GRADE_FALLBACK_CAUSE="$cause" rewardkit "$fb" --workspace /workspace --output /logs/verifier/reward.json
fi
as_grader python3 - "$STATE/results" /logs/verifier/verdict.json "$cause" <<'EXPORT'
import json, pathlib, sys
results, out = pathlib.Path(sys.argv[1]), sys.argv[2]
verdict = json.loads((results / "verdict.json").read_text())
verdict["kept"] = json.loads((results / "kept.json").read_text())
verdict["category_exit"] = {c: (results / f"{c}.exit").read_text().strip() if (results / f"{c}.exit").exists() else None for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")}
verdict["named_tests"] = json.loads((results / "named.json").read_text())
verdict["reproductions"] = json.loads((results / "reproductions.json").read_text()) if (results / "reproductions.json").exists() else []
verdict["steps"] = [json.loads(line) for line in (results / "steps.jsonl").read_text().splitlines() if line.strip()]
verdict["fallback_cause"] = sys.argv[3] or None
json.dump(verdict, open(out, "w"), sort_keys=True)
EXPORT
