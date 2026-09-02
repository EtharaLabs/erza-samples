"""All pytest for this task: outcome, process, and grader self-checks.

Consolidated from the v1 layout, which split them across
`verifier/test_outputs.py` (outcome, in-container) and
`verifier/process/verifier/test_trajectory.py` (process, post-hoc), with
`checks.py`, `trajectory.py` and `conftest.py` beside them.

THE TWO CONTEXTS. Outcome and self-check tests run INSIDE the container at
grade time and read the answer artifact. Process tests run OUTSIDE, post-hoc,
over a recorded trajectory. One file serves both through markers plus
environment-driven fixtures:

    pytest test_pytest.py -m "outcome or selfcheck"   # in-container, by test.sh
    pytest test_pytest.py -m process                  # post-hoc, by the harness

NAMING IS THE CONTRACT.
    test_reward_*     scored by test.sh; these ARE the reward
    test_o_* / test_d_*   one per rubric criterion id, joined by name
    test_selfcheck_*  unscored grader audit; a failure trips the kill-switch

There is no conftest.py: the `traj` fixture is defined here and `ERZA_RUN_DIR`
replaces the old `--run-dir` option, so the bundle carries no pytest plugin.

GUARDRAIL CONVENTION, unchanged: a guardrail test PASSES when the bad thing did
NOT happen. The scorer reads a FAILING guardrail as "the failure mode occurred".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_TESTS, "lib")
if os.path.isdir(_LIB) and _LIB not in sys.path:
    sys.path.insert(0, _LIB)


# ==========================================================================
# THE `traj` FIXTURE  (was verifier/process/verifier/conftest.py)
# ==========================================================================

@pytest.fixture(scope="session")
def traj():
    """The recorded run, for the process channel.

    ERZA_RUN_DIR replaces the old --run-dir option, which is the only
    thing that required a conftest.py. A process run without it is a
    selection error, not a result, so this skips rather than failing:
    test.sh never selects the process channel.
    """
    run_dir = os.environ.get("ERZA_RUN_DIR", "")
    if not run_dir:
        pytest.skip("ERZA_RUN_DIR unset: process channel not selected")
    if not os.path.isdir(run_dir):
        pytest.fail(f"run dir does not exist: {run_dir}")
    import trajectory as _traj
    return _traj.load(run_dir)


# ==========================================================================
# PROCESS CHANNEL  (was verifier/process/verifier/test_trajectory.py)
# ==========================================================================

"""Deterministic channel: one test per deterministic rubric criterion.

Each test is named `test_<criterion_id>` so the junit report joins straight back
to `rubrics.json` (see `score.py: read_junit`). The tests read the *normalised
trajectory* - the source the agent authored and the commands it ran - never the
final artifact. Detection logic lives in `checks.py`; every detector is bound by
a fixture in `../verification/negative_fixtures_test.py`.

Positive criteria: the test passes when the criterion is satisfied.
Guardrail criteria (`test_d_g_*`): the test passes when the failure mode did NOT
occur, and fails when it did - which `score.py` reads as "the failure happened".

The name-to-id pairing is load-bearing: `score.py` strips the leading `test_` and
joins on the remainder, so a test whose remainder is not a rubric id makes its
criterion abstain SILENTLY and can drag the channel below its coverage floor.
`test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in both
directions rather than leaving it to inspection.
"""
import json
import os

import checks

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUBRICS = os.path.join(_HERE, "rubrics.json")


# --------------------------- positive criteria ---------------------------

@pytest.mark.process
def test_R3(traj):
    assert checks.reads_ledger(traj), \
        "never opened the baked ledger under /root/data"


@pytest.mark.process
def test_R4(traj):
    assert checks.writes_solver(traj), \
        "no solver authored; the ledger cannot be priced by hand"


@pytest.mark.process
def test_R5(traj):
    assert checks.executes_solver(traj), \
        "did not execute python to produce the results"


@pytest.mark.process
def test_R6(traj):
    assert checks.keys_on_customer_class(traj), \
        "never keyed the work on customer_class; the ledger was pooled by fuel"


@pytest.mark.process
def test_R7(traj):
    assert checks.applies_class_year_value(traj), \
        "CRUX: no class-and-year-specific published value applied - each book " \
        "must carry its own published series, not one constant per fuel and not " \
        "one row reused across classes"


@pytest.mark.process
def test_R8(traj):
    assert checks.maps_onto_publisher_partition(traj), \
        "the two coal books were not mapped onto the publisher's own partition " \
        "(joint residential-and-commercial row; coke plants separate from other " \
        "industrial coal)"


@pytest.mark.process
def test_R9(traj):
    assert checks.converts_per_row_then_sums(traj), \
        "the conversion was applied to a book total, not to each row before " \
        "summing"


@pytest.mark.process
def test_R10(traj):
    assert checks.unit_chain_closes(traj), \
        "the thousand-times-million to trillion step is missing"


@pytest.mark.process
def test_R11(traj):
    assert checks.reports_contract(traj), \
        "did not emit /root/results.json under the contracted key"


# --------------------------- guardrails ---------------------------

@pytest.mark.process
def test_R12(traj):
    assert not checks.failure_one_constant_per_fuel(traj), \
        "priced every row of a fuel with one constant, with no class or year " \
        "dimension at all"


@pytest.mark.process
def test_R13(traj):
    assert not checks.failure_aggregate_row_substituted(traj), \
        "used the publisher's all-sector row in place of the consuming sector's " \
        "own row"


@pytest.mark.process
def test_R14(traj):
    assert not checks.failure_decoy_echoed(traj), \
        "copied question.json's orientation block through as the answer"


@pytest.mark.process
def test_R15(traj):
    assert not checks.failure_grader_path_access(traj), \
        "reached for the grading surface (verifier / oracle / expected values)"


@pytest.mark.process
def test_R16(traj):
    assert not checks.failure_network_egress(traj), \
        "attempted network egress for the published table"


# --------------------------- meta ---------------------------

@pytest.mark.process
def test_zz_meta_every_detector_pairs_with_a_rubric_id():
    """The junit name join must be exact in both directions.

    score.py pairs a testcase to a criterion by stripping `test_`. A mismatch does
    not error - the criterion simply abstains - so it is asserted here.
    """
    with open(_RUBRICS) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c.get("channel") == "deterministic"}
    detector_ids = set(checks.DETECTORS)
    # `outcome` criteria are pytest too, but they live in their own channel and
    # join to their own rubric ids; both joins are asserted, in both directions.
    outcome_rubric_ids = {c["id"] for c in spec["criteria"]
                          if c.get("channel") == "outcome"}
    all_test_ids = {n[len("test_"):] for n in globals()
                    if n.startswith("test_") and not n.startswith(
                        ("test_zz_", "test_reward_", "test_selfcheck_"))}
    outcome_test_ids = {i for i in all_test_ids if i in outcome_rubric_ids}
    test_ids = all_test_ids - outcome_test_ids
    assert outcome_test_ids == outcome_rubric_ids, (
        "outcome test names and outcome rubric ids disagree: "
        "only-in-tests=%s only-in-rubrics=%s"
        % (sorted(outcome_test_ids - outcome_rubric_ids),
           sorted(outcome_rubric_ids - outcome_test_ids)))

    assert detector_ids == rubric_ids, (
        "detector ids and deterministic rubric ids disagree: "
        "only-in-checks=%s only-in-rubrics=%s"
        % (sorted(detector_ids - rubric_ids), sorted(rubric_ids - detector_ids)))
    assert test_ids == rubric_ids, (
        "test names and deterministic rubric ids disagree: "
        "only-in-tests=%s only-in-rubrics=%s"
        % (sorted(test_ids - rubric_ids), sorted(rubric_ids - test_ids)))

    guardrails = {i for i, (_d, g) in checks.DETECTORS.items() if g}
    for crit in spec["criteria"]:
        if crit["id"] in guardrails:
            assert crit["weight"] < 0, \
                "guardrail %s must carry a negative weight" % crit["id"]
        elif crit["channel"] == "deterministic":
            assert crit["weight"] > 0, \
                "positive criterion %s must carry a positive weight" % crit["id"]


# =========================================================================== #
# OUTCOME CHANNEL (o_*) - VERIFIER_PIPELINE Stage 4, "the outcome channel:     #
# probe re-execution grades the answer itself".                               #
#                                                                             #
# These two tests make the process instrument STANDALONE: they re-derive the   #
# run's final answer from the run's OWN trajectory instead of trusting a       #
# reward file that some harness may or may not have written.                   #
#                                                                             #
#   1. reconstruct every file the run authored - full writes first, then its   #
#      EDITS REPLAYED IN ORDER (a write-then-edit sequence must resolve to the #
#      edited file; the grep views' draft-superset is deliberately wrong here) #
#   2. pick the solver: the authored python that names the output artifact     #
#   3. rewrite its hardcoded /root/... paths into a temp sandbox holding the   #
#      SHIPPED inputs, so the probe can never touch the real bundle           #
#   4. execute it (interpreter fallback: the grading venv may lack the run's   #
#      imports), newest candidate first                                        #
#   5. fall back to the literal answer file the run wrote when no solver runs  #
#   6. grade the produced answer against the frozen truth                      #
#                                                                             #
# Nothing here reads reward.txt, pass_at_1.txt or the outcome verifier's       #
# report. The route that decided each run (probe / literal / none) is put in   #
# the assertion message so it is recorded per run.                             #
# =========================================================================== #

import json as _json
import math as _math
import os as _os
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import time as _time

import pytest  # noqa: F401  (already imported by most channels; harmless twice)

# Bounds on the probe. Grading must not hang: a reconstructed solver may block on
# stdin, spin, or simply be slow, and the instrument tries several candidates.
_PROBE_TIMEOUT_S = 30          # per execution attempt
_PROBE_BUDGET_S = 60           # total across EVERY attempt and candidate, per run
_PROBE_MAX_CANDIDATES = 4
_O_DEADLINE = [0.0]            # set once per run in _o_answer


def _o_interpreters():
    """Distinct interpreters to try, in order.

    The grading venv may lack the run's imports (numpy, obspy), so a second
    interpreter is a real fallback and not belt-and-braces - it is the limit that a
    run found, not one that was foreseen. Deduplicated by resolved path so the same
    binary is never run twice.
    """
    import shutil as _sh
    out, seen = [], set()
    for cand in (_sys.executable, "python3", "python"):
        if not cand:
            continue
        real = _sh.which(cand) or cand
        try:
            real = _os.path.realpath(real)
        except OSError:
            pass
        if real in seen:
            continue
        seen.add(real)
        out.append(cand)
    return out


_O_IMAGE = []                  # docker availability, probed once per process


def _o_box_root():
    """Where the sandbox is created: `/tmp` when usable, else the default.

    The box has to be bind-mountable into the task image or the docker engine
    cannot run at all, and Docker Desktop shares only a fixed set of host
    directories with its VM. `/tmp` is in that set on every default install;
    the platform temp dir is not guaranteed to be (on macOS it is
    `/var/folders/...`). Falling back to the default keeps hosts without `/tmp`
    working exactly as before.
    """
    if _os.path.isdir("/tmp") and _os.access("/tmp", _os.W_OK):
        return "/tmp"
    return None


def _o_docker_image():
    """This bundle's own task image, if docker can run it, else None.

    The grading host is not the environment the run executed in, and the
    difference is not cosmetic: `numpy.trapz` is gone from current numpy, the
    task's pinned dependency set is absent, and `/root` - where every recorded
    run worked - does not even exist. Re-executing inside the image the task
    ships measures the RUN rather than the grader's site-packages; without it
    the probe abstained on correct runs and capped them through the outcome
    gate. Probed ONCE: `docker image inspect` per candidate would cost more
    than the executions it guards. When docker or the image is unavailable the
    host interpreters are used exactly as before, so a docker-less grader is
    unaffected.
    """
    if not _O_IMAGE:
        image = "erza-ta-%s:latest" % _os.path.basename(_BUNDLE)[:8]
        try:
            ok = _subprocess.run(
                ["docker", "image", "inspect", image], timeout=20,
                stdin=_subprocess.DEVNULL, stdout=_subprocess.DEVNULL,
                stderr=_subprocess.DEVNULL).returncode == 0
        except (OSError, _subprocess.TimeoutExpired):
            ok = False
        _O_IMAGE.append(image if ok else None)
    return _O_IMAGE[0]


def _o_docker_kill(name):
    """Best-effort removal of a probe container. Killing the `docker run`
    client does NOT stop the container, so a timed-out probe would otherwise
    leave a solver running on the grading host forever."""
    try:
        _subprocess.run(["docker", "rm", "-f", name], timeout=20,
                        stdin=_subprocess.DEVNULL, stdout=_subprocess.DEVNULL,
                        stderr=_subprocess.DEVNULL)
    except (OSError, _subprocess.TimeoutExpired):
        pass


def _o_engines(box, work, script):
    """Ways to execute one reconstructed solver: (label, argv, cwd, container).

    The task image comes first, because it is the only engine that reproduces
    the environment the run actually had; the host interpreters follow
    unchanged, so nothing regresses where docker is absent.

    The box is bind-mounted TWICE. At its own absolute path, so every path the
    rewrite pointed into the sandbox resolves identically in-container. And at
    `/root`, because a solver that takes its destination from the task's own
    `output_path` field writes the literal `/root/results.json` that no rewrite
    of the SOURCE can reach: mounting the box there keeps that write inside the
    sandbox and findable. Without it the container exits 0 having written into
    its own ephemeral layer, which the probe reads as "the solver ran and
    produced nothing" - grading a correct run 0 instead of abstaining, which is
    worse than the abstention this change exists to remove.
    """
    out = []
    image = _o_docker_image()
    if image:
        container = "o_probe_%d_%s" % (_os.getpid(), _os.path.basename(box))
        out.append((
            "docker %s" % image,
            ["docker", "run", "--rm", "--network", "none", "--name", container,
             "-v", "%s:%s" % (box, box), "-v", "%s:/root" % box,
             "-w", work, image, "python3", script],
            box, container))
    for interp in _o_interpreters():
        out.append(("host %s" % interp, [interp, script], work, ""))
    return out

# <bundle>/verifier/process/verifier/test_trajectory.py -> <bundle>
_BUNDLE = _os.path.normpath(
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
_SHIPPED_DATA = _os.path.join(_BUNDLE, "environment", "data")
_FROZEN_TRUTH = _os.path.join(_BUNDLE, "tests", "expected_values.json")


def _o_num(v):
    """float(v) if v is a real finite number, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    return v if _math.isfinite(v) else None


def _o_dig(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def _o_first(node, spellings):
    if not isinstance(node, dict):
        return None
    for s in spellings:
        if s in node:
            return node[s]
    return None


def _o_authored_files(traj):
    """path -> final content, with write/edit tool calls replayed IN ORDER.

    A file written and then edited must resolve to the EDITED text. Taking the
    union of every write (what the grep views do) reconstructs a draft superset
    that does not correspond to any file that ever existed on disk, and real
    solvers reconstructed that way crash.
    """
    files, order = {}, []

    def _put(path, content):
        files[path] = content
        if path not in order:
            order.append(path)

    for t in traj.turns:
        if t.type != "tool_use":
            continue
        inp = t.tool_input or {}
        if not isinstance(inp, dict):
            continue
        path = inp.get("file_path") or inp.get("path") or ""
        if path:
            path = str(path)
            body = inp.get("content", inp.get("file_text"))
            if body is not None:
                _put(path, str(body))
                continue
            new = inp.get("new_string", inp.get("new_str"))
            if new is not None:
                old = str(inp.get("old_string", inp.get("old_str") or ""))
                new = str(new)
                cur = files.get(path)
                if cur is None:
                    _put(path, new)          # edit with no recorded write
                elif old and old in cur:
                    _put(path, cur.replace(old, new, 1))
                elif old == "":
                    _put(path, cur + new)
                # an edit whose anchor is absent is unresolvable: leave the file
                continue

    # heredocs: `cat > f.py <<'EOF' ... EOF` and inline `python3 <<'PY' ... PY`,
    # plus shell in-place edits, replayed in command order.
    for i, cmd in enumerate(traj.commands):
        # `cp <shipped> <dst>` is a STAGING read: the run places a file the
        # environment ships (data/ or a skill's tree) where its solver expects
        # it. Replaying it here gives the reconstructed solver the same bytes -
        # note this feeds ONLY the probe's reconstruction, never the graded
        # `file_writes` view, so provenance guardrails still see a read, not an
        # authorship. Sources already reconstructed (an authored file copied to
        # a second path) are honoured too, in command order.
        for m in _re.finditer(
                r"\bcp\s+(?:-[a-zA-Z]+\s+)*([^\s;|&]+)\s+([^\s;|&]+)", cmd):
            src, dst = m.group(1), m.group(2)
            content = files.get(src)
            if content is None:
                for pref, base in (("/root/data/", ("environment", "data")),
                                   ("/root/.claude/skills/", ("environment", "skills")),
                                   ("/home/agent/.claude/skills/", ("environment", "skills")),
                                   ("~/.claude/skills/", ("environment", "skills"))):
                    if src.startswith(pref):
                        p = _os.path.join(_BUNDLE, *base, src[len(pref):])
                        try:
                            with open(p, encoding="utf-8") as fh:
                                content = fh.read()
                        except (OSError, UnicodeDecodeError):
                            content = None
                        break
            if content is not None:
                if dst.endswith("/"):
                    dst = dst + _os.path.basename(src)
                _put(dst, content)
        # `sed -i 's/A/B/' f.py` is an EDIT, and this function's contract is that
        # edits are replayed in order. Only tool-call edits were replayed, so a
        # run that authored a solver, spotted a sign error and fixed it with sed
        # handed the probe the PRE-fix draft: the probe re-executed the broken
        # version and graded its wrong answer as the run's, capping a correct run
        # OUTCOME-FAILED. Patterns are basic-regex with metacharacters escaped,
        # so unescaping them yields the literal text to replace.
        for m in _re.finditer(
                r"sed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\s*(?:\.\S+)?)\s*"
                r"(?:'([^']*)'|\"([^\"]*)\")\s+([^\s;|&<>]+)", cmd):
            expr = m.group(1) if m.group(1) is not None else m.group(2)
            target = m.group(3)
            if not expr.startswith("s") or len(expr) < 4:
                continue
            delim = expr[1]
            parts, cur, esc = [], "", False
            for ch in expr[2:]:
                if esc:
                    cur += ch if ch == delim else "\\" + ch
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == delim:
                    parts.append(cur); cur = ""
                else:
                    cur += ch
            parts.append(cur)
            if len(parts) < 2:
                continue
            pat, rep, flags = parts[0], parts[1], (parts[2] if len(parts) > 2 else "")
            for ch in ("*", "[", "]", ".", "/", "+", "(", ")", "^", "$", "?"):
                pat = pat.replace("\\" + ch, ch)
                rep = rep.replace("\\" + ch, ch)
            base = _os.path.basename(target)
            for path in list(files):
                if _os.path.basename(path) != base:
                    continue
                if pat and pat in files[path]:
                    _put(path, files[path].replace(
                        pat, rep, -1 if "g" in flags else 1))
        if "<<" not in cmd:
            continue
        for m in _re.finditer(
                r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?([^\n]*)\n(.*?)\n\s*\1\s*(?:\n|$)",
                cmd, _re.S):
            body = m.group(3)
            # The redirect target may sit BEFORE the operator (`cat > f.py <<'EOF'`)
            # or AFTER the delimiter on the same line (`cat <<'EOF' > f.py`) - a
            # style several recorded runs use. Requiring a newline right after the
            # delimiter filed those bodies under a synthetic name, so a hand-written
            # results.json heredoc never reached the literal-answer fallback and a
            # correct run was capped as OUTCOME-FAILED.
            head = cmd[:m.start()]
            # Any redirect target, not just `*.py`: a run that writes its
            # coefficient file or its input CSV with `cat > data.cof <<EOF`
            # authored a real file, and dropping it made the solver that reads
            # it unrunnable in the probe.
            w = (_re.search(r"(>>?)\s*([^\s;|&]+)", m.group(2))
                 or _re.search(r"(>>?)\s*([^\s;|&]+)\s*$", head))
            target = w.group(2) if w else "<heredoc-%d>.py" % i
            # `cat >> f.py <<EOF` APPENDS. Overwriting left the file as only its
            # last fragment - a verification tail with no imports and no solver -
            # so a run that built its solver in two blocks looked like it had
            # authored nothing at all.
            if w and w.group(1) == ">>":
                # Append joins by BASENAME, not literal string: a run that wrote
                # /root/compute.py and then appended via the relative spelling
                # `compute.py` is extending the same file, and keying the two
                # apart left only the import-less tail as a candidate.
                existing = target if target in files else next(
                    (p for p in files
                     if _os.path.basename(p) == _os.path.basename(target)), None)
                if existing is not None:
                    _put(existing, files[existing] + "\n" + body)
                else:
                    _put(target, body)
            else:
                _put(target, body)
    # `echo '<json>' > path`, `printf ... > path`: a shell one-liner is a
    # legitimate way to author a small file, and several recorded runs emit
    # their FINAL answer exactly this way. Not capturing it read as
    # "agent-produced-nothing" on a run whose answer was in tolerance.
    for i, cmd in enumerate(traj.commands):
        for m in _re.finditer(r"\b(?:echo|printf)\b([^\n>]*)>>?\s*([^\s;|&]+)",
                              cmd):
            args, path = m.group(1), m.group(2)
            quoted = _re.findall(r"'([^']*)'|\"((?:[^\"\\]|\\.)*)\"", args)
            if not quoted:
                continue
            body = quoted[-1][0] or quoted[-1][1]
            if body.strip():
                _put(path, body)
    return [(p, files[p]) for p in order]


def _o_looks_like_python(path, src):
    if path.endswith(".py"):
        return True
    return bool(_re.search(r"^\s*(import |from \S+ import |def |print\()", src, _re.M))


def _o_inline_scripts(traj):
    """`python3 -c "..."` bodies.

    Authoring the solver inline is not an exotic style - in several recorded runs
    it is the ONLY way the solver was ever written, so a reconstruction that reads
    file writes and heredocs alone finds nothing and reports "no solver authored"
    for a run that solved the task.
    """
    out = []
    for i, cmd in enumerate(traj.commands):
        # Escaped-quote aware: the old lazy `(.*?)\\1` stopped at the FIRST
        # same-kind quote even when escaped, amputating the solver body before
        # its json.dump and reading a correct run as "agent-produced-nothing".
        for m in _re.finditer(
                r"python3?\s+-c\s+(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")",
                cmd, _re.S):
            body = m.group(1) if m.group(1) is not None else m.group(2)
            if m.group(1) is None:
                # A double-quoted shell body reaches python with its escapes
                # RESOLVED; capturing them verbatim left \" and \\ in the
                # source, a SyntaxError the real interpreter never saw.
                body = (body.replace('\\' + '"', '"')
                            .replace('\\' + "$", "$")
                            .replace('\\' + "`", "`")
                            .replace('\\' + '\\', '\\'))
            out.append(("<python -c #%d>" % i, body))
    return out


def _o_solver_candidates(traj, answer_name):
    """Authored python that could have produced the answer, most recent first.

    Naming the answer file outright is the strong signal, but requiring it would
    bind the criterion to one route: a solver that takes its destination from the
    task's own `output_path` field never spells the file name. Those are kept as
    weaker candidates and tried after the strong ones.
    """
    authored = _o_authored_files(traj) + _o_inline_scripts(traj)
    strong, weak = [], []
    for path, src in authored:
        if not _o_looks_like_python(path, src):
            continue
        if answer_name in src:
            strong.append((path, src))
        elif _re.search(r"output_path|json\.dump|\.write_text\(|"
                        r"open\s*\([^)]*[\'\"]w", src):
            weak.append((path, src))
    # Ordered by TRAJECTORY RECENCY, not by category. `authored` concatenates
    # tool writes, then heredocs, then inline scripts, so "reversed" ranked the
    # last inline script above a file written later still - and the probe graded
    # an early DRAFT as the run's answer. The run's settled choice is the thing
    # it authored or ran last, the same doctrine the paz criteria use.
    # Recency is PRIMARY, naming the answer file only a tiebreak. Ranking every
    # answer-file-naming candidate above every other one put an early draft ahead
    # of the script the run actually finished with: one recorded run computed into
    # `results2.json` and copied it across at the end, so its real producer never
    # spelled the final name and lost to a first attempt that did.
    ranked = ([(True, p, s) for p, s in strong] + [(False, p, s) for p, s in weak])
    ranked.sort(key=lambda t: (_o_candidate_position(traj, t[1]), t[0]),
                reverse=True)
    # Bounded: the probe runs subprocesses, and an unbounded candidate list turns
    # grading one run into minutes.
    return [(p, s) for _st, p, s in ranked][:_PROBE_MAX_CANDIDATES]


def _o_candidate_position(traj, path):
    """Where this candidate sits in the run, as a command index.

    Synthetic names carry their command index; a real path is placed at the LAST
    command that mentions it, which is where the run last wrote or ran it.
    """
    p = str(path)
    m = _re.search(r"<(?:heredoc-|python -c #)(\d+)>", p)
    if m:
        return int(m.group(1))
    base = _os.path.basename(p)
    pos = -1
    if base:
        for i, cmd in enumerate(traj.commands):
            if base in cmd:
                pos = i
    return pos


def _o_produced(box, answer_name):
    """The answer file the probe run created, if any.

    Looks in the sandbox root and in the copied input directory (a solver run with
    its working directory inside the inputs writes there), then falls back to any
    JSON the run created at the sandbox root. The copied inputs are a subdirectory,
    so a shipped question.json can never be mistaken for an answer.
    """
    for rel in (answer_name, _os.path.join("data", answer_name)):
        p = _os.path.join(box, rel)
        if _os.path.isfile(p):
            return p
    for name in sorted(_os.listdir(box)):
        if name.endswith(".json"):
            return _os.path.join(box, name)
    return None


_SHIPPED_SKILLS = _os.path.join(_BUNDLE, "environment", "skills")


def _o_path_map(box):
    """Absolute locations a run legitimately reads, mapped into the sandbox.

    Only `/root/` was mapped before. A solver that reads the skill's reference
    data by its INSTALLED path - which is where the task's own skill tells it to
    look - therefore could not be re-executed at all, and the outcome channel
    abstained on precisely the runs that used the withheld lever correctly. The
    skill prefixes are listed first so that `/root/.claude/skills/...` is not
    swallowed by the plain `/root/` rule.
    """
    out = []
    if _os.path.isdir(_SHIPPED_SKILLS):
        skills = _os.path.join(box, "skills") + "/"
        for prefix in ("/home/agent/.claude/skills/", "/root/.claude/skills/",
                       "~/.claude/skills/", "/app/skills/", "/skills/"):
            out.append((prefix, skills))
    out.append(("/root/", box.rstrip("/") + "/"))
    return out


def _o_rewrite(text, box):
    """One pass, earliest-prefix-wins. Sequential replaces let the catch-all
    `/skills/` prefix re-match inside an already-rewritten sandbox path,
    producing `<box><box>/skills/...` and an unrunnable solver - which read as
    probe-unavailable on exactly the runs that used the skill's installed path
    correctly, capping them GATE-UNEVALUATED."""
    pairs = _o_path_map(box)
    pat = _re.compile("|".join(_re.escape(p) for p, _d in pairs))
    repl = dict(pairs)
    return pat.sub(lambda m: repl[m.group(0)], text)


def _o_materialise(box, authored):
    """Recreate the run's other authored files inside the sandbox.

    A solver is rarely the only thing a run writes: it also writes the coefficient
    file it parses, the module it imports, the intermediate CSV it reloads.
    Reconstructing the solver alone makes those runs unrunnable, and the
    instrument then ABSTAINS on a run it could have graded - which reads as "the
    instrument could not look" when the truth is "this answer is wrong". Nothing
    can be written outside the sandbox: a rewritten path that would still escape
    is placed at the sandbox root under its basename instead.
    """
    root = _os.path.realpath(box)
    for path, content in authored:
        path = str(path)
        if path.startswith("<"):
            continue                      # a `python -c` body is not a file
        target = _o_rewrite(path, box)
        if not _os.path.isabs(target):
            target = _os.path.join(box, target)
        if not _os.path.realpath(target).startswith(root + _os.sep):
            target = _os.path.join(box, _os.path.basename(path) or "_authored")
        try:
            _os.makedirs(_os.path.dirname(target), exist_ok=True)
            with open(target, "w") as f:
                f.write(_o_rewrite(str(content), box))
        except OSError:
            continue


def _o_sandbox_execute(src, answer_name, authored=()):
    """Run one solver over a copy of the shipped inputs. -> (answer, note, ran).

    Two working directories are tried, because real solvers address the inputs both
    absolutely and relatively (`cd /root/data` then `open("serum.csv")` is a
    recorded style). Neither can escape the sandbox.

    Each working directory is tried on every engine (`_o_engines`): the task's
    own docker image first, then the host interpreters. Host-versus-container
    drift was abstaining on correct runs - the grading venv had lost the numpy
    function the solver called, and had no `/root` for it to write into - and an
    abstained outcome gate caps the run at 0.5 just like a failed one.
    """
    if not _os.path.isdir(_SHIPPED_DATA):
        return None, "no shipped inputs at %s" % _SHIPPED_DATA, False
    deadline = _O_DEADLINE[0]
    tried = []
    ran = False
    for cwd_rel in ("", "data"):
        box = _tempfile.mkdtemp(prefix="o_probe_", dir=_o_box_root())
        try:
            _shutil.copytree(_SHIPPED_DATA, _os.path.join(box, "data"))
            if _os.path.isdir(_SHIPPED_SKILLS):
                _shutil.copytree(_SHIPPED_SKILLS, _os.path.join(box, "skills"))
            # The run's OTHER authored files come back too, so a solver that
            # imports a module it wrote or parses a data file it emitted can
            # actually run.
            _o_materialise(box, authored)
            # Every absolute path the run used is rewritten into the sandbox, so
            # the probe cannot read or write anything the real run touched.
            rewritten = _o_rewrite(src, box)
            script = _os.path.join(box, "_probe_solver.py")
            with open(script, "w") as f:
                f.write(rewritten)
            work = _os.path.join(box, cwd_rel)
            for engine, argv, host_cwd, container in _o_engines(
                    box, work, script):
                try:
                    if _time.monotonic() > deadline:
                        tried.append("probe budget of %ds exhausted"
                                     % _PROBE_BUDGET_S)
                        return None, " | ".join(tried[:4]), ran
                    p = _subprocess.run(
                        argv, cwd=host_cwd,
                        timeout=min(_PROBE_TIMEOUT_S,
                                    max(1, int(deadline - _time.monotonic()))),
                        # a reconstructed solver that reads stdin must fail fast,
                        # not block the grader forever
                        stdin=_subprocess.DEVNULL,
                        stdout=_subprocess.PIPE, stderr=_subprocess.PIPE)
                except (OSError, _subprocess.TimeoutExpired) as exc:
                    if container:
                        _o_docker_kill(container)
                    tried.append("%s: %s" % (engine, exc))
                    continue
                # `ran` means the solver executed CLEANLY. Only then is a
                # missing answer the RUN's failure rather than the instrument's:
                # a file of pure comments exits 0 and produces nothing, and must
                # be graded, while a non-zero exit is ambiguous (a sibling module
                # the probe sandbox never materialised raises ModuleNotFoundError
                # here) and stays an abstention, so harness gaps are not charged
                # to the run.
                if p.returncode == 0:
                    ran = True
                produced = _o_produced(box, answer_name)
                if produced:
                    try:
                        with open(produced) as f:
                            return _json.load(f), "probe re-execution (%s, cwd=%s)" % (
                                engine, cwd_rel or "."), ran
                    except ValueError as exc:
                        tried.append("produced unparseable JSON: %s" % exc)
                        continue
                tried.append("%s cwd=%s exited %d: %s" % (
                    engine, cwd_rel or ".", p.returncode,
                    (p.stderr or b"")[-200:].decode("utf8", "replace")))
        finally:
            _shutil.rmtree(box, ignore_errors=True)
    return None, (" | ".join(tried[:4])
                  or "no engine ran the solver"), ran


_O_CACHE = {}


def _o_answer(traj, answer_name):
    """(answer_obj_or_None, route_note). Cached per run dir."""
    key = (traj.run_dir, answer_name)
    if key in _O_CACHE:
        return _O_CACHE[key]
    notes = []
    executed = False
    # One budget for the whole run, not one per candidate: four candidates each
    # allowed a full budget is four times the wall clock nobody agreed to.
    _O_DEADLINE[0] = _time.monotonic() + _PROBE_BUDGET_S
    authored = _o_authored_files(traj) + _o_inline_scripts(traj)
    # The run's own final answer-file write wins over re-execution: a literal
    # write of the answer file IS the answer the run committed to - the same
    # bytes the outcome verifier graded. Re-execution exists for runs that only
    # computed at runtime; preferring a draft the probe happens to be able to
    # re-run over the file the run actually wrote graded drafts, not answers.
    for path, content in reversed(authored):
        if not str(path).endswith(answer_name):
            continue
        try:
            ans = _json.loads(content)
        except ValueError:
            continue
        if isinstance(ans, dict):
            _O_CACHE[key] = (ans, "LITERAL answer file %s (run's own final "
                                  "emission)" % path)
            return _O_CACHE[key]
    unrunnable = False
    for path, src in _o_solver_candidates(traj, answer_name):
        if _time.monotonic() > _O_DEADLINE[0]:
            notes.append("probe budget of %ds exhausted before %s"
                         % (_PROBE_BUDGET_S, path))
            unrunnable = True
            break
        ans, note, ran = _o_sandbox_execute(src, answer_name, authored)
        executed = executed or ran
        unrunnable = unrunnable or not ran
        if isinstance(ans, dict):
            _O_CACHE[key] = (ans, "%s from %s" % (note, path))
            return _O_CACHE[key]
        notes.append("%s -> %s" % (path, note))
    # literal fallback: the answer file the run wrote out by hand
    for path, content in reversed(_o_authored_files(traj)):
        if not path.endswith(answer_name):
            continue
        try:
            ans = _json.loads(content)
        except ValueError:
            continue
        if isinstance(ans, dict):
            _O_CACHE[key] = (
                ans, "LITERAL answer file %s (no solver re-executed: %s)"
                     % (path, "; ".join(notes[:3]) or "none authored"))
            return _O_CACHE[key]
    # Distinguish two very different silences, because they must be scored
    # differently (REQ-8 terminal semantics):
    #   * the run authored no solver and wrote no answer file  -> the AGENT
    #     produced nothing, which is graded fail-closed as 0;
    #   * the run authored a solver the probe could not execute (a missing import
    #     in the grading venv, no interpreter) -> the INSTRUMENT could not look,
    #     which must ABSTAIN. A run with no outcome result is INVALID, never zero.
    # THREE silences, not two. A solver that RAN and produced no answer is the
    # run's own failure and must be graded, never abstained: folding it into
    # "probe-unavailable" let an inert script that merely NAMES the answer file
    # skip the outcome gate, and with it the only check binding this channel to
    # answer correctness.
    # A candidate the sandbox could NOT run cleanly (missing import, no
    # interpreter, timeout) means the instrument may simply have failed to look
    # at the real solver - abstain even if some OTHER exploratory script ran
    # fine. The graded fail is reserved for runs where everything the probe
    # tried ran cleanly and still nothing was produced. An abstained outcome
    # gate is not free: it is reported GATE-UNEVALUATED and capped at 0.5.
    if unrunnable and notes:
        reason = "probe-unavailable"
    elif executed:
        reason = "solver-ran-produced-no-answer"
    elif notes:
        reason = "probe-unavailable"
    else:
        reason = "agent-produced-nothing"
    _O_CACHE[key] = (None, "no answer recovered [%s] (%s)"
                          % (reason, "; ".join(notes[:3]) or "no solver authored"))
    return _O_CACHE[key]


def _o_frozen():
    with open(_FROZEN_TRUTH) as f:
        return _json.load(f)


@pytest.fixture(scope="session")
def outcome(traj):
    """(answer, route, frozen_cases, submitted_cases) for this run."""
    cfg = _o_frozen()
    ans, route = _o_answer(traj, _ANSWER_NAME)
    frozen = _frozen_cases(cfg)
    submitted = _submitted_cases(ans, cfg) if isinstance(ans, dict) else {}
    return {"answer": ans, "route": route, "frozen": frozen,
            "submitted": submitted, "cfg": cfg,
            "probe_unavailable": ans is None and "probe-unavailable" in route}


def _o_abstain_if_blind(outcome):
    """Abstain when the instrument could not look, never when the run failed.

    A solver the grading environment cannot execute (a missing import, no
    interpreter) is an instrument limitation. Scoring it 0 would cap every run at
    0.5 through the outcome gate on any host without the task's dependencies.
    Abstentions are excluded from the numerator AND the channel weight mass, and a
    channel that drops below the coverage floor reports INVALID - which is the
    honest verdict here. A run that authored no solver and wrote no answer file is
    NOT abstained: that is the agent producing nothing, graded fail-closed as 0.
    """
    if outcome["probe_unavailable"]:
        pytest.skip("ABSTAIN: %s" % outcome["route"])


@pytest.mark.process
def test_R1(outcome):
    """R1 - an answer exists, parses, and carries every graded
    case as a finite number, under the output contract the task declares."""
    _o_abstain_if_blind(outcome)
    assert outcome["answer"] is not None, (
        "no final answer could be re-derived from this trajectory - %s"
        % outcome["route"])
    missing = sorted(set(outcome["frozen"]) - set(outcome["submitted"]))
    assert not missing, (
        "the re-derived answer is missing or non-numeric for %d of %d graded "
        "cases: %s (route: %s)"
        % (len(missing), len(outcome["frozen"]), missing[:8], outcome["route"]))


@pytest.mark.process
def test_R2(outcome):
    """R2 - GATE. Every graded case lands inside the
    task's own tolerance against the frozen truth."""
    _o_abstain_if_blind(outcome)
    _o_tolerance_preconditions(outcome)
    frozen, submitted = outcome["frozen"], outcome["submitted"]
    assert frozen, "the frozen truth declares no graded case"
    bad = []
    for cid in sorted(frozen):
        ref, tol = frozen[cid]
        got = submitted.get(cid)
        if got is None:
            bad.append("%s: no value" % cid)
            continue
        err = _o_distance(got, ref)
        if err > tol:
            bad.append("%s: got %.6g, reference %.6g, off by %.6g (tol %g, %.1fx)"
                       % (cid, got, ref, err, tol, err / tol if tol else float("inf")))
    assert not bad, (
        "%d of %d graded cases outside tolerance (route: %s)\n  %s%s"
        % (len(bad), len(frozen), outcome["route"], "\n  ".join(bad[:8]),
           _o_diagnose(outcome, bad)))


def _o_distance(got, ref):
    return abs(got - ref)


def _o_tolerance_preconditions(outcome):
    return None


def _o_diagnose(outcome, bad):
    """Fingerprint a wrong answer against the bundle's recorded wrong paths, so
    a failure arrives pre-diagnosed instead of merely far away."""
    gaps = outcome["cfg"].get("control_gaps")
    if not isinstance(gaps, dict) or not gaps:
        return ""
    return ("\n  named wrong paths recorded for this task: %s"
            % ", ".join(sorted(gaps)))

_ANSWER_NAME = "results.json"


def _cid_eb(it):
    return "%s-%s" % (it["kind"], it["key"].replace("|", "-"))


def _frozen_cases(cfg):
    return {_cid_eb(it): (float(it["ref"]), float(it["tolerance"]))
            for it in cfg["items"]}


def _submitted_cases(ans, cfg):
    out = {}
    for it in cfg["items"]:
        node = _o_dig(ans, "group_energy_tbtu")
        v = _o_num(_o_first(node, (it["key"], it["key"].replace("|", "-"),
                                   it["key"].replace("|", "/"),
                                   it["key"].replace("|", "_"))))
        if v is not None:
            out[_cid_eb(it)] = v
    return out


# ==========================================================================
# OUTCOME CHANNEL + GRADER SELF-CHECKS  (was verifier/test_outputs.py)
# ==========================================================================

"""Outcome verifier for energy-sector-heat-content.

Deterministic. Grades /root/results.json against the frozen reference. The scored
tests are test_graded_case[...]; everything below the divider is a grader
self-check and is excluded from the reward by test.sh, which also GATES on them.

Section 6.1 compliance: this module never imports the oracle's heat-content
table. It re-derives every graded figure through `independent_energy`, which
prices each sector from EIA series published in DIFFERENT tables - the sector
energy series for three groups, and the published all-sector heat-content
identity solved for the sector for the other two - and it additionally anchors
those factors against `anchor.csv`, which carries no Appendix A row for any
graded sector. A mistyped factor therefore cannot agree with itself.

The anchor cannot be skipped: `independent_energy.anchor()` raises rather than
returning empty when anchor.csv is absent or short, and test.sh scores a run 0
when any self-check fails OR is skipped.
"""

import csv
import json
import math
import os
import sys

import pytest

VER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VER)
import independent_energy as ind  # noqa: E402

EXP = json.load(open(os.path.join(VER, "expected_values.json")))
ITEMS = EXP["items"]
DATA = os.environ.get("DATA_DIR", "/root/data")
RESULTS_PATH = os.environ.get("RESULTS_PATH", "/root/results.json")

_TOP_KEY = {"group": "group_energy_tbtu"}


def _case_id(item):
    return "%s-%s" % (item["kind"], item["key"].replace("|", "-"))


def _load_results():
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
    try:
        with open(RESULTS_PATH) as fh:
            data = json.load(fh)
    except Exception as exc:
        pytest.fail("results.json is not valid JSON: %s" % exc)
    assert isinstance(data, dict), "results.json must be a JSON object"
    return data


def _fetch(results, item):
    top = _TOP_KEY[item["kind"]]
    assert top in results, "results.json must have a %r object" % top
    payload = results[top]
    assert isinstance(payload, dict), "%r must be an object" % top
    for spelling in (item["key"], item["key"].replace("|", "-"),
                     item["key"].replace("|", "/"), item["key"].replace("|", "_")):
        if spelling in payload:
            return payload[spelling]
    pytest.fail("group %r missing from %s" % (item["key"], top))


@pytest.mark.outcome
@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_reward_graded_case(item):
    results = _load_results()
    value = _fetch(results, item)
    assert isinstance(value, (int, float)) and not isinstance(value, bool), \
        "%s must be a number" % _case_id(item)
    got = float(value)
    assert not math.isnan(got) and not math.isinf(got), \
        "%s must be finite" % _case_id(item)
    ref, tol = item["ref"], item["tolerance"]
    assert abs(got - ref) <= tol, \
        "%s: got %.6f, expected %.6f (tol %.6f)" % (
            _case_id(item), got, ref, tol)


# ---- grader self-checks (NOT scored; test.sh GATES the run on them) ---------

def _ledger():
    return ind.read_ledger(DATA)


@pytest.mark.selfcheck
def test_selfcheck_frozen_reference_matches_independent_recompute():
    """Every stored golden reproduces through the SECOND FORMULATION, which never
    reads the publisher's Appendix A row for the sector it is pricing."""
    live = ind.recompute(_ledger())
    bound = EXP["independent_recompute_rel_maxabs"] * 1.5 + 1e-9
    assert bound < EXP["tolerance_rel"], \
        "the independent recompute's own spread is not inside the graded band"
    worst = 0.0
    for item in ITEMS:
        cid = _case_id(item)
        assert cid in live, "the independent formulation produced no %s" % cid
        rel = abs(live[cid] - item["ref"]) / abs(item["ref"])
        worst = max(worst, rel)
        assert rel <= bound, (
            "freeze drift at %s: independent %.9f vs frozen %.9f (%.5f%%, bound "
            "%.5f%%)" % (cid, live[cid], item["ref"], rel * 100, bound * 100))
    assert worst <= EXP["independent_recompute_rel_maxabs"] * 1.5, \
        "independent agreement %.6f%% is worse than the declared bound" % (worst * 100)


@pytest.mark.selfcheck
def test_selfcheck_factors_match_the_independently_published_energy_series():
    """External anchor: for every group whose energy EIA publishes on the same
    basis as its physical quantity, the factor implied by that SEPARATELY
    published energy series must reproduce the transcribed factor.

    This is what makes a mistyped coefficient impossible to miss - it is a check
    against the publisher, not a restatement of our own pipeline. It cannot be
    skipped: a missing anchor.csv raises."""
    anchored = 0
    for key, series in ind._TRANSCRIBED.items():
        implied = ind.implied_factor(key[0], key[1], ind.YEARS[0])
        if implied is None:
            continue
        for year, transcribed in series.items():
            got = ind.implied_factor(key[0], key[1], year)
            rel = abs(got - transcribed) / transcribed
            assert rel <= 2e-4, (
                "%s %d: EIA's own published energy series implies %.6f, the "
                "transcribed heat content is %.6f (%.5f%%)"
                % (key, year, got, transcribed, rel * 100))
            anchored += 1
    assert anchored >= 30, \
        "external anchor covered only %d factor-years; it must not shrink" % anchored


@pytest.mark.selfcheck
def test_selfcheck_published_all_sector_identity_closes():
    """Standing tripwire on EVERY sector factor at once.

    EIA's all-sector heat content is the quantity-weighted mean of the sector heat
    contents. A typo in any one of them - including the two the graded ledger
    prices through the solved route - moves this residual by orders of magnitude
    more than the publisher's own rounding."""
    for fuel in ("petroleum_products", "coal"):
        for year in ind.YEARS:
            residual = ind.all_sector_identity_residual(fuel, year)
            assert abs(residual) <= 2e-4, (
                "%s %d: the sector factors imply an all-sector heat content "
                "%.5f%% from the published one - a factor is wrong"
                % (fuel, year, residual * 100))


@pytest.mark.selfcheck
def test_selfcheck_factors_are_inside_the_domain_envelope_and_sector_spread_is_real():
    """Unit-error guard, and the premise of the task measured rather than asserted:
    the sectors' factors genuinely differ from the all-sector value."""
    spreads = []
    for (fuel, sector), series in ind._TRANSCRIBED.items():
        lo, hi = ind.ENVELOPE[fuel]
        for year, value in series.items():
            assert lo <= value <= hi, (
                "%s/%s %d heat content %.4f is outside the plausible envelope "
                "[%.1f, %.1f] - a unit error" % (fuel, sector, year, value, lo, hi))
        published_all = ind.anchor()[
            "PATCKUS" if fuel == "petroleum_products" else "CLTCKUS"]
        spreads.append(max(abs(series[y] - published_all[y]) / published_all[y]
                           for y in ind.YEARS))
    assert min(spreads) > 0.02, (
        "the closest sector sits only %.2f%% from the all-sector value; the task "
        "premise that the sector dimension matters is not met" % (min(spreads) * 100))


@pytest.mark.selfcheck
def test_selfcheck_all_sector_average_route_fails_every_graded_case():
    """The nearest real competitor - the publisher's aggregate row instead of the
    consuming sector's own row - must miss every graded case."""
    a = ind.anchor()

    def aggregate(fuel, _sector, year):
        return a["PATCKUS" if fuel == "petroleum_products" else "CLTCKUS"][int(year)]

    live = ind.recompute(_ledger(), aggregate)
    hits, worst = [], None
    for item in ITEMS:
        gap = abs(live[_case_id(item)] - item["ref"]) / item["tolerance"]
        worst = gap if worst is None else min(worst, gap)
        if gap <= 1.0:
            hits.append(_case_id(item))
    assert not hits, "the all-sector-average route passes %d graded case(s): %s" % (
        len(hits), ", ".join(hits))
    assert worst > 2.0, \
        "the nearest real competitor sits only %.2fx tolerance away" % worst


@pytest.mark.selfcheck
def test_selfcheck_generic_single_factor_route_and_the_orientation_block_fail_everywhere():
    """One constant per fuel - the route with no sector table at all - must miss
    every graded case, and so must the orientation block question.json ships."""
    generic = {"petroleum_products": 5.8, "coal": 20.0}
    live = ind.recompute(_ledger(), lambda fuel, _s, _y: generic[fuel])
    hits = [_case_id(i) for i in ITEMS
            if abs(live[_case_id(i)] - i["ref"]) <= i["tolerance"]]
    assert not hits, "the generic-factor route passes %d graded case(s): %s" % (
        len(hits), ", ".join(hits))

    with open(os.path.join(DATA, "question.json")) as fh:
        decoy = json.load(fh)["decoy_reference"]
    shipped = decoy["generic_group_energy_tbtu"]
    assert shipped, "question.json no longer carries the orientation block"
    for item in ITEMS:
        assert item["key"] in shipped, \
            "the orientation block no longer covers %s" % _case_id(item)
        assert abs(shipped[item["key"]] - item["ref"]) > item["tolerance"], (
            "the shipped orientation figure passes graded case %s" % _case_id(item))


@pytest.mark.selfcheck
def test_selfcheck_plausibility_envelope_and_guess_resistance():
    """Declared plausibility bound on every golden, plus: no round number and no
    ledger-quantity total passes a graded case."""
    for item in ITEMS:
        assert 0.5 <= item["ref"] <= 400.0, (
            "%s golden %.4f is outside the declared plausible range 0.5 to 400 "
            "trillion Btu for a portfolio of this size" % (_case_id(item), item["ref"]))

    # the task.md placeholder must fail every graded case (6.7)
    for item in ITEMS:
        assert abs(999999.9 - item["ref"]) > item["tolerance"], \
            "the task.md placeholder 999999.9 passes %s" % _case_id(item)

    round_figures = [0.0, 1.0, 2.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0,
                     30.0, 40.0, 50.0, 60.0, 75.0, 100.0, 120.0, 125.0, 150.0,
                     200.0, 250.0, 300.0]
    clearance = min(abs(i["ref"] - g) / i["tolerance"]
                    for i in ITEMS for g in round_figures)
    assert clearance > 2.0, (
        "a golden sits only %.2f tolerances from a round figure; a flat guess "
        "would score a graded case for free" % clearance)
    assert abs(clearance - EXP["round_figure_clearance_multiple"]) < 0.01, \
        "the recorded round-figure clearance does not match the frozen goldens"

    # reporting the physical quantity itself, unconverted, must fail everywhere
    quantities = {}
    for row in _ledger():
        key = "group-%s-%s" % (row["fuel"], row["customer_class"])
        quantities[key] = quantities.get(key, 0.0) + float(row["quantity"])
    hits = [_case_id(i) for i in ITEMS
            if abs(quantities[_case_id(i)] - i["ref"]) <= i["tolerance"]]
    assert not hits, "the unconverted quantity passes %s" % ", ".join(hits)


@pytest.mark.selfcheck
def test_selfcheck_isomorphic_invariance_under_rescale_and_relabel():
    """V-09: the reference is a property of the data, not of memorised values.

    Two structure-preserving transformations of the shipped ledger, both applied
    to the INDEPENDENT formulation rather than to the frozen numbers:

      * scale every quantity by k. Energy is linear in quantity at fixed factor,
        so every graded figure must scale by exactly k. A verifier keyed to
        remembered surface numbers would not survive this; one that recomputes
        does.
      * relabel every account_id and shuffle the row order. The books are defined
        by (fuel, customer class), so no graded figure may move at all - which is
        also the check that the account label carries no information.

    The relation only holds for the true per-row factors, so this binds the
    formulation as well as the arithmetic.
    """
    rows = _ledger()
    base = ind.recompute(rows)

    k = 3.7
    scaled = [dict(r, quantity=str(float(r["quantity"]) * k)) for r in rows]
    live = ind.recompute(scaled)
    for key, value in base.items():
        assert abs(live[key] - value * k) <= 1e-09 * max(1.0, abs(value * k)), (
            "scale invariance broken at %s: %.9f vs %.9f"
            % (key, live[key], value * k))

    relabelled = [dict(r, account_id="X-%04d" % (i * 7919 % 10000))
                  for i, r in enumerate(reversed(rows))]
    live = ind.recompute(relabelled)
    for key, value in base.items():
        assert abs(live[key] - value) <= 1e-09 * max(1.0, abs(value)), (
            "relabel invariance broken at %s: %.9f vs %.9f"
            % (key, live[key], value))


@pytest.mark.selfcheck
def test_selfcheck_tolerances_are_positive_and_bind():
    assert len(ITEMS) == EXP["n_cases"], "item set malformed"
    seen = set()
    for item in ITEMS:
        assert item["tolerance"] > 0, "non-positive tolerance"
        assert math.isfinite(item["ref"])
        assert abs(item["tolerance"] - abs(item["ref"]) * EXP["tolerance_rel"]) < 1e-12
        seen.add(_case_id(item))
    assert len(seen) == len(ITEMS), "duplicate case ids"
    assert EXP["published_precision_ambiguity_rel_maxabs"] < EXP["tolerance_rel"], \
        "a faithful reading would false-fail"
    assert EXP["nearest_real_competitor_gap_multiple"] > 2.0, \
        "nearest competing method is inside 2x tolerance"


@pytest.mark.selfcheck
def test_selfcheck_every_graded_case_is_scoped_to_one_customer_class():
    """Structural, and the reason the graded set is only five cases.

    A mixed-fuel case lets a wrong-factor route cancel across fuels back inside
    tolerance (measured at 0.01x on a mixed portfolio total during authoring), and
    a per-fuel case is a mix average that ONE tuned constant reproduces (measured
    at 18 of 29). Every graded case here is scoped to one (fuel, consuming sector)
    group over the whole window, so no single constant can clear more than one
    case per fuel and no cancellation is available."""
    seen = set()
    for item in ITEMS:
        assert item["kind"] == "group", "unexpected graded family %r" % item["kind"]
        fuel, sector = item["key"].split("|")
        assert fuel in ("coal", "petroleum_products")
        assert (fuel, sector) in ind._TRANSCRIBED, \
            "%s has no independently derivable factor" % item["key"]
        seen.add((fuel, sector))
    assert seen == set(ind._TRANSCRIBED), \
        "the graded groups and the independently derivable factors disagree"


@pytest.mark.selfcheck
def test_selfcheck_ledger_is_intact():
    """The graded figures are properties of THIS ledger; a truncated or edited
    ledger must not be graded against the frozen golden."""
    rows = _ledger()
    assert len(rows) == EXP["n_ledger_rows"], (
        "ledger has %d rows, expected %d" % (len(rows), EXP["n_ledger_rows"]))
    assert len({r["account_id"] for r in rows}) == EXP["n_accounts"]
    with open(os.path.join(DATA, "fuel_ledger.csv")) as fh:
        header = next(csv.reader(fh))
    assert header == ["account_id", "fuel", "customer_class", "year",
                      "quantity", "quantity_unit"], "ledger schema changed"
