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

"""Deterministic channel: one test per deterministic criterion in rubrics.json.

Each test name is `test_` + the criterion id. They read the *trajectory* - the code
the agent authored and the commands it ran - not the final artifact.

GUARDRAIL CONVENTION: a guardrail test PASSES when the bad thing did NOT happen. The
scorer treats a FAILING guardrail as "the failure mode occurred" and subtracts.
"""

import ast
import re

import pytest


def _strip_comments(src: str) -> str:
    """Blank out `#` comments AND docstrings, keeping line geometry.

    A regex over `#` alone leaves docstrings standing, so a run that DOCUMENTS
    its restraint - "the verifier deliberately does NOT import
    verifier/independent_energy.py" - trips the very guardrail that restraint
    satisfies, and a run that merely explains a convention in a docstring is
    credited for prose. Docstrings are bare string-expression statements:
    prose by construction, never operands.

    String literals used as VALUES are deliberately left alone.
    `open("/verifier/golden.json")` is access, not commentary, and must stay
    visible to the guardrails; `"observations.csv"` is the input the run read.

    Parsed with `ast` when the blob parses (`agent_code` concatenates every
    authored file, so it often does not); otherwise a triple-quoted block that
    OPENS a logical line is treated as prose - what a docstring looks like
    without a parser.
    """
    src = _strip_docstrings(src)
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


_TRIPLE_OPEN = re.compile("[rRuUbBfF]{0,2}(\"\"\"|''')")


def _blank_prose_blocks(src: str) -> str:
    """Fallback docstring blanking for source the parser cannot read.

    The previous fallback was one regex applied with `sub`: it matched from ANY
    triple quote that OPENED a line to the next one that CLOSED a line. The
    closing delimiter of a multi-line data literal sits at column 0, so a run that
    embeds a table, a heredoc body or any block constant as a triple-quoted
    literal had everything between that closing quote and the next function
    docstring DELETED from the graded view - real code, silently missing from
    every criterion decided on `code`. Carrying reference data as a literal is
    ordinary practice, so the bug fell hardest on runs that did that.

    Delimiters are now PAIRED in source order, so an opening quote is matched with
    its own closing quote, and a pair counts as prose only when its opening
    delimiter starts a logical line - a literal assigned to a name is left
    standing, as this module's contract promises. Line geometry is preserved.
    """
    marks = list(_TRIPLE_OPEN.finditer(src))
    spans, k = [], 0
    while k + 1 < len(marks):
        opener, closer = marks[k], marks[k + 1]
        if opener.group(1) != closer.group(1):
            k += 1                       # unpaired style: resynchronise
            continue
        line_start = src.rfind("\n", 0, opener.start()) + 1
        if not src[line_start:opener.start()].strip():
            spans.append((opener.start(), closer.end()))
        k += 2
    if not spans:
        return src
    out = list(src)
    for lo, hi in spans:
        for i in range(lo, hi):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def _strip_docstrings(src: str) -> str:
    spans = _docstring_spans(src)
    if spans is None:
        return _blank_prose_blocks(src)
    out = src.splitlines(True)
    for lo, hi in spans:                      # 1-based, inclusive
        for i in range(lo - 1, min(hi, len(out))):
            out[i] = "\n" if out[i].endswith("\n") else ""
    return "".join(out)


def _docstring_spans(src):
    """[(first_line, last_line)] for every bare string-expression statement, or
    None when the blob does not parse as Python."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    spans = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            # `Lambda.body` and `IfExp.body` are EXPRESSIONS, not statement
            # lists; iterating them raises TypeError on perfectly ordinary
            # source. Only statement blocks can hold a docstring.
            if not isinstance(block, list):
                continue
            for stmt in block:
                if (isinstance(stmt, ast.Expr)
                        and isinstance(getattr(stmt, "value", None), ast.Constant)
                        and isinstance(stmt.value.value, str)):
                    spans.append((stmt.lineno,
                                  getattr(stmt, "end_lineno", None) or stmt.lineno))
    return spans


@pytest.fixture(scope="session")
def code(traj):
    return _strip_comments(traj.agent_code)


def _blank_string_literals(src: str) -> str:
    """Replace the BODY of every quoted literal with spaces, keeping the quotes.

    Used only by checks whose failure mode is an OPERATION. A run that prints or
    documents the trap it is avoiding - `print("do not add shift_ft to the gage
    height")` - has not performed it, and charging the run for the sentence
    punishes exactly the care the criterion wants. Checks whose failure mode is an
    ACCESS (a path, a URL) keep their literals: there the string IS the operand.
    """
    def _sub(m):
        q = m.group(1)
        return q + " " * (len(m.group(0)) - 2 * len(q)) + q
    src = re.sub(r"('''|\"\"\")(.*?)\1", _sub, src, flags=re.S)
    return re.sub(r"(['\"])((?:\\.|[^\\\n])*?)\1", _sub, src)


def _has_rating_table(code: str) -> bool:
    """A rating table was loaded and used as a lookup, not just named in prose.

    Route-independent. The earlier matcher wanted the gauge label baked into the
    file name (`rating_GS-A`) or the literal column header. A run that keeps the
    reference directory in a constant and joins the gauge id onto it, or that
    reads the columns positionally by index, loads exactly the same table and
    spelled none of those. Any of: a rating/stage-discharge artifact by name, one
    of the table's own column names, the expanded-table format tag, or a
    rating-loading helper.
    """
    return bool(re.search(
        r"\brating\w*\b|\bexsa\b|stage[\s_\-]*discharge|shift_ft|"
        # the table's own column names, but NOT the output-contract key
        # `block_mean_discharge_cfs`, which every run writes and which says
        # nothing about where the numbers came from
        r"(?<![_\w])discharge_cfs|(?<![_\w])gage_height_ft",
        code, re.I))


def _has_lookup(code: str) -> bool:
    """The observed stage was looked up against the table.

    Previously this named the library calls (`np.interp`, `bisect`, ...), which is
    library-bound: the skill's own procedure writes the interpolation out as
    `Q = q0 + (q1 - q0) * (h - h0) / (h1 - h0)`, and a hand-rolled bracket-and-
    interpolate loop is the same arithmetic. Worse, the shipped tables have a
    0.01 ft step and EVERY sampled gage height in this record lands exactly on a
    tabulated row (the bundle's own precision note says so), so a plain dict or
    index lookup keyed on the rounded stage is not merely acceptable, it is the
    route the data invites. All three are now accepted.
    """
    library = (r"np\.interp|numpy\.interp|\binterp\s*\(|interp1d|scipy\.interpolate|"
               r"CubicSpline|Pchip|Akima|bisect|searchsorted|idxmin|merge_asof|"
               r"reindex[^\n]*nearest|\.lookup\s*\(|get_indexer")
    # q0 + (q1 - q0) * (h - h0) / (h1 - h0), in any variable names
    handrolled = (r"\(\s*[\w.\[\]]+\s*-\s*[\w.\[\]]+\s*\)\s*\*\s*"
                  r"\(\s*[\w.\[\]]+\s*-\s*[\w.\[\]]+\s*\)\s*/\s*"
                  r"\(\s*[\w.\[\]]+\s*-\s*[\w.\[\]]+\s*\)")
    # exact-key lookup against the 0.01 ft table: a dict, or an index computed
    # from the stage
    exact = (r"dict\s*\(\s*zip|\bzip\s*\(\s*[\w.]*(?:h|hs|stage|gage)\w*\s*,|"
             r"\{[^{}\n]*(?:h|stage|gage)\w*\s*:\s*[^{}\n]*\bfor\b|"
             r"\[\s*round\s*\(|\.get\s*\(\s*round\s*\(|\[\s*int\s*\(\s*round|"
             # a subscript on a table variable, written with no space before the
             # bracket so that prose - `decoy rating  [NOT reliable]` inside a
             # print - cannot be read as an indexing expression
             r"\b(?:table|ratings?|rating_\w+|q_?by_?h|lookup|curve)\[[^\]\n]{1,30}\]")
    return bool(re.search(r"%s|%s|%s" % (library, handrolled, exact), code, re.I))


def _has_time_weighting(code: str) -> bool:
    """The block value was integrated in time, not taken as a bare sample mean.

    The earlier matcher accepted three spellings mined from the with-skill runs -
    `trapz`, the INDEXED midpoint `(a[i] + a[i+1])/2`, and `np.diff(t` / `dt *`.
    That is in-sample-bound: the vectorised SLICE midpoint `(q[:-1] + q[1:])/2` is
    the same average, `np.average(q, weights=dt)` is the same weighted sum,
    `scipy.integrate.simpson` is a strictly higher-order quadrature over the same
    samples, and a pandas time resample is the same reduction expressed on a
    DatetimeIndex. All of them now satisfy the criterion, as does dividing an
    accumulated integral by the elapsed span - a run only divides by a DURATION
    when the numerator is an integral.

    What is still rejected is the bare arithmetic mean of the samples with no time
    axis anywhere (`sum(Q) / len(Q)`), which is the failure mode this criterion
    exists to catch. That exclusion is arithmetic, not stylistic: the sampling is
    nominally 15-minute, but the closed blocks do not all carry the same number of
    samples, and on GS-B b1 the arithmetic mean lands 265.7 cfs from the reference
    against a 235.3 cfs tolerance - it is a different number, not another spelling
    of the same one. A run whose aggregation shows any weighting by the time each
    sample represents passes, whatever it is called.
    """
    quadrature = (r"trapz|trapezoid|cumtrapz|\bsimps\b|simpson|\bromb\b|"
                  r"\bquad\s*\(|integrate\s*\(|\.integral\s*\(")
    # midpoint average of consecutive samples, indexed OR sliced
    indexed_mid = r"\(\s*\w+\[\w+\]\s*\+\s*\w+\[\w+\s*\+\s*1\s*\]\s*\)\s*/\s*2"
    sliced_mid = (r"\w+\s*\[\s*:\s*-\s*1\s*\][^\n]{0,24}\+[^\n]{0,24}\w+\s*\[\s*1\s*:\s*\]|"
                  r"\w+\s*\[\s*1\s*:\s*\][^\n]{0,24}\+[^\n]{0,24}\w+\s*\[\s*:\s*-\s*1\s*\]")
    # explicit per-sample weights
    # explicit per-sample weights (a bare `np.average(q)` is NOT a weighting, so
    # the weights argument itself has to be there)
    weighted = (r"weights\s*=|\bdt\s*\*|\*\s*\bdt\b|\bdt\s*\[|"
                r"\bw\s*\*\s*\w+\s*\)\s*/\s*(?:np\.)?sum")
    # a spacing taken off the timestamps themselves
    spacing = (r"(?:np|numpy|pd)?\.?diff\s*\(\s*[\w.\[\]]*"
               r"(?:t|ts|time|times|secs|seconds|epoch|stamp|idx)\b")
    # an accumulated integral normalised by the elapsed span: only a DIVISION by a
    # duration counts, so merely computing one for a log line proves nothing
    elapsed = (r"/\s*\(?\s*[\w.]*\[\s*-\s*1\s*\][^\n]{0,20}-[^\n]{0,20}\[\s*0\s*\]|"
               r"/\s*[\w.]*(?:total_seconds\s*\(|elapsed|\bspan\b|duration)|"
               r"/\s*\(\s*(?:end|t_end|stop|last)\w*\s*-\s*"
               r"(?:start|t_start|begin|first)\w*\s*\)")
    # a time-indexed reduction
    pandas_time = (r"\.resample\s*\(|\.rolling\s*\(|\.asfreq\s*\(|"
                   r"interpolate\s*\([^\n]*time|\.between_time\s*\(")
    return bool(re.search(
        "|".join((quadrature, indexed_mid, sliced_mid, weighted, spacing, elapsed,
                  pandas_time)), code, re.I))


# ------------------------------- positive criteria ------------------------------- #

@pytest.mark.process
def test_R3(traj):
    """The recorded stage series was read.

    The file may be named outright or reached through the shipped data directory
    (`cd /root/data` then a glob, or a directory constant joined with the name);
    both are the same read. A run that never touches the record at all still
    fails.
    """
    blob = traj.agent_code + " " + " ".join(traj.commands)
    named = "stage_series" in blob
    via_dir = bool(re.search(r"/root/data", blob)
                   and re.search(r"\.csv\b|read_csv|DictReader|csv\.reader|glob", blob))
    assert named or via_dir, "never referenced /root/data/stage_series.csv"


@pytest.mark.process
def test_R4(traj):
    wrote = bool(traj.file_writes)
    heredoc = any("<<" in c and "python" in c.lower() for c in traj.commands)
    inline = any(
        re.search(r"python3?\s+-c\b", c) and ("import" in c or "def " in c or c.count("\n") >= 1)
        for c in traj.commands
    )
    assert wrote or heredoc or inline, "no solver source authored"


@pytest.mark.process
def test_R5(traj):
    assert re.search(r"\bpython3?\b", "\n".join(traj.commands)), "solver was never executed"


@pytest.mark.process
def test_R6(traj, code):
    """THE crux (gate). Discharge came from a per-gauge rating table, not from the decoy."""
    blob = code + " " + " ".join(traj.commands)
    assert _has_rating_table(blob) and _has_lookup(code), (
        "no rating-table lookup: discharge was not obtained from a per-gauge "
        "stage-discharge table")


@pytest.mark.process
def test_R7(traj, code):
    """A distinct table per gauge, not one table reused across all three.

    Two accepted routes, and the second is now spelling-free. Either every gauge
    label appears (the table paths were written out), or the table PATH is
    parameterised by the gauge - an f-string, a `%s`, a `+ gid +`, an
    `os.path.join(ref, gid ...)`, a glob over the rating files, or a
    `load_rating(gid)` helper. It is deliberately the path that must be
    parameterised and not merely a loop over gauges: a run that loads ONE table
    and then iterates the gauges through it has the loop but reuses the table,
    which is exactly the failure mode.
    """
    blob = code + " " + " ".join(traj.commands)
    labels = set(re.findall(r"GS-([A-Z])", blob))
    gauge_var = r"(?:gid|gauge\w*|g_?id|site\w*|station\w*|\bg\b|\bgg\b)"
    templated = bool(re.search(
        r"rating[_\-][^\"'\s]*%s|rating[_\-]?\{|rating[_\-]?.*format\(|"
        r"f[\"'][^\"'\n]*rating[^\"'\n]*\{|"
        r"[\"'][^\"'\n]*rating[^\"'\n]*[\"']\s*%\s*" + gauge_var + r"|"
        r"rating[^\"'\n]{0,20}[\"']\s*\+\s*" + gauge_var + r"|"
        r"join\s*\([^)\n]*" + gauge_var + r"[^)\n]*\)|"
        r"glob[^\n]*rating|load_rating\s*\(|"
        r"rating\w*\s*=\s*\{[^{}\n]*for\s+" + gauge_var,
        blob, re.I))
    assert len(labels) >= 3 or templated, (
        "did not load a separate rating table per gauge")


@pytest.mark.process
def test_R8(code):
    """The shift column must not be added to the stage before lookup.

    The failure mode is an OPERATION on the stage, so string literals are blanked
    before matching. The skill names this as its single most common error, and a
    run that warns about it in a printed message or a column header - `print("the
    discharge column already carries shift_ft; gage_height + shift_ft would
    double count")` - has done the opposite of the failure mode. Charging it 3
    points for the sentence would make explaining the trap more expensive than
    ignoring it.
    """
    scanned = _blank_string_literals(code)
    bad = re.search(r"(gage_height|stage|\bh\b|height)\s*\+\s*(shift|\bs\b)\b"
                    r"|shift\s*\+\s*(gage_height|stage|\bh\b|height)\b", scanned, re.I)
    assert not bad, "the shift was added to the gage height before lookup (double counted)"


@pytest.mark.process
def test_R9(code):
    assert _has_time_weighting(code), (
        "block value was not integrated in time (bare sample mean)")


@pytest.mark.process
def test_R10(traj):
    blob = traj.agent_code + " " + traj.agent_prose + " " + " ".join(traj.commands)
    assert "block_mean_discharge_cfs" in blob, (
        "did not emit the block_mean_discharge_cfs contract key")


# ------------------------------- guardrails ------------------------------- #

@pytest.mark.process
def test_R11(traj):
    """PASSES when the answer path was NOT touched.

    Judges what the run DID, not what it mentioned. Comments are stripped, and a
    match must sit beside a read verb: a careful agent that writes
    "I will not open /verifier/expected_values.json" is describing restraint, and
    charging -5 for saying so punishes exactly the behaviour we want.
    """
    code = _strip_comments(traj.agent_code)
    blob = " ".join(traj.commands) + " " + code
    paths = r"/oracle\b|/verifier\b|expected_values\.json|golden\.json|truth\.md"
    verbs = r"cat|less|head|tail|open\s*\(|read_text|read_bytes|json\.load|grep|ls|find|cp|mv"
    hit = (re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (verbs, paths), blob)
           or re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (paths, verbs), blob))
    assert not hit, "GUARDRAIL FIRED: read the answer path (%s)" % (
        hit.group(0)[:60] if hit else "")


@pytest.mark.process
def test_R12(traj):
    """PASSES when no test surface was edited.

    Only a write that can REACH the grader counts. /verifier is in
    sandbox_locked_paths, so a conftest.py the agent drops in its own scratch
    directory cannot affect scoring - and agents legitimately use pytest on their
    own sanity checks. Fire on the grading surface, not on the filename.
    """
    surface = r"/verifier/|/app/|site-packages"
    # A conftest.py only bites if pytest will COLLECT it: at the working root the
    # grader runs from, or on the grading surface itself. One the agent drops deep
    # in its own scratch tree cannot reach the grader (/verifier is locked), and
    # agents legitimately run pytest on their own sanity checks.
    collected = r"^(?:\./)?conftest\.py$|^/root/conftest\.py$"
    bad_writes = [p for p, _c in traj.file_writes
                  if re.search(surface, p) or re.fullmatch(collected, p.strip())]
    cmds = " ".join(traj.commands)
    # The write must TARGET the surface: a redirect's target token, or an
    # argument of the same cp/mv/install command (never across a `|`, `;` or
    # `&` boundary) - `... >/dev/null | grep -v site-packages` is not a write.
    cmd_hit = (re.search(r"(?:>|>>)\s*\S*(?:%s)" % surface, cmds)
               or re.search(r"\b(?:cp|mv|install)\s+[^\n|;&]*(?:%s)" % surface, cmds)
               # `echo ... > conftest.py` creates it at the working root
               or re.search(r"(?:>|>>)\s*(?:\./)?conftest\.py\b", cmds)
               or re.search(r"(?:>|>>)\s*/root/conftest\.py\b", cmds))
    assert not (bad_writes or cmd_hit), (
        "GUARDRAIL FIRED: wrote onto the verifier surface (%s)"
        % (bad_writes[0] if bad_writes else cmd_hit.group(0)[:60]))


@pytest.mark.process
def test_R13(traj):
    """PASSES when no fetch of the withheld tables was attempted.

    Judges the OUTBOUND CALL, not the host name. The earlier matcher fired on the
    bare tokens `waterdata`, `waterservices` and `nwis` anywhere in the
    transcript - but the shipped tables carry their own provenance line, and the
    skill's procedure cites `https://waterdata.usgs.gov/nwisweb/get_ratings` as
    the definition of the expanded format. A solver that quotes that line in a
    header comment, or prints it as the source of its numbers, was charged -3 for
    documenting where the local file came from. Egress needs a verb, and every
    verb is still caught; comments and docstrings are stripped from the authored
    source for the same reason.
    """
    blob = " ".join(traj.commands) + " " + _strip_comments(traj.agent_code)
    hit = re.search(
        r"\bcurl\b|\bwget\b|\baria2c?\b|\bhttpie\b|\bnc\b\s+\S|\bftp\b\s|"
        r"urllib\.request|urlopen|requests\.(?:get|post|Session|request)|"
        r"\bhttpx\b|http\.client|aiohttp|urllib3|socket\.(?:create_connection|socket)|"
        r"pip\s+install|pip3\s+install|conda\s+install|apt-get\s+install|"
        r"fetch\s*\(\s*[\"']https?://",
        blob, re.I)
    assert not hit, "GUARDRAIL FIRED: attempted network egress (%s)" % (
        hit.group(0) if hit else "")


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
    return ""

_ANSWER_NAME = "results.json"


def _frozen_cases(cfg):
    return {"%s-%s" % (it["gauge_id"], it["blockkey"]):
            (float(it["ref_mean_discharge_cfs"]), float(it["tolerance_cfs"]))
            for it in cfg["items"]}


def _submitted_cases(ans, cfg):
    out = {}
    for it in cfg["items"]:
        v = _o_num(_o_dig(ans, "block_mean_discharge_cfs",
                          it["gauge_id"], it["blockkey"]))
        if v is not None:
            out["%s-%s" % (it["gauge_id"], it["blockkey"])] = v
    return out


# ==========================================================================
# OUTCOME CHANNEL + GRADER SELF-CHECKS  (was verifier/test_outputs.py)
# ==========================================================================

"""Outcome verifier for gauge-rating-block-discharge.

Deterministic. Grades /root/results.json against the frozen golden. The scored tests
are test_block_mean[...] - one per gauge and block. The remaining tests are grader
self-checks and are excluded from the reward by test.sh.
"""

import csv
import datetime as dt
import json
import math
import os
import sys

import pytest

VER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VER)
from rating import load_rating, discharge_at, block_mean  # noqa: E402

EXP = json.load(open(os.path.join(VER, "expected_values.json")))
ITEMS = EXP["items"]
RESULTS_PATH = os.environ.get("RESULTS_PATH", "/root/results.json")
DATA = os.environ.get("DATA_DIR", "/root/data")


def _epoch(iso):
    return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc).timestamp()


def _load_results():
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
    try:
        with open(RESULTS_PATH) as fh:
            data = json.load(fh)
    except Exception as exc:
        pytest.fail("results.json is not valid JSON: %s" % exc)
    assert isinstance(data, dict) and "block_mean_discharge_cfs" in data, \
        "results.json must have a 'block_mean_discharge_cfs' object"
    return data["block_mean_discharge_cfs"]


def _recompute():
    """Live recompute of every block mean from the shipped data and rating tables."""
    series = {}
    with open(os.path.join(DATA, "stage_series.csv")) as fh:
        for row in csv.DictReader(fh):
            series.setdefault(row["gauge_id"], []).append(
                (_epoch(row["datetime_utc"]), float(row["gage_height_ft"])))
    out = {}
    for gauge, points in series.items():
        points.sort()
        rows = load_rating(os.path.join(_LIB, "ratings", "rating_%s.tsv" % gauge))
        times = [p[0] for p in points]
        q = [discharge_at(rows, p[1]) for p in points]
        out[gauge] = (times, q)
    live = {}
    for item in ITEMS:
        times, q = out[item["gauge_id"]]
        live[(item["gauge_id"], item["blockkey"])] = block_mean(
            times, q, _epoch(item["start_utc"]), _epoch(item["end_utc"]))
    return live


@pytest.mark.outcome
@pytest.mark.parametrize("item", ITEMS,
                         ids=["%s-%s" % (it["gauge_id"], it["blockkey"]) for it in ITEMS])
def test_reward_block_mean(item):
    results = _load_results()
    gauge, block = item["gauge_id"], item["blockkey"]
    assert gauge in results, "gauge %s missing from results" % gauge
    assert block in results[gauge], "block %s missing for gauge %s" % (block, gauge)
    value = results[gauge][block]
    assert isinstance(value, (int, float)) and not isinstance(value, bool), \
        "mean discharge must be a number"
    got = float(value)
    assert not math.isnan(got) and not math.isinf(got), \
        "mean discharge must be finite (not NaN/Infinity)"
    ref, tol = item["ref_mean_discharge_cfs"], item["tolerance_cfs"]
    assert abs(got - ref) <= tol, \
        "%s %s: got %.4f cfs, expected %.4f cfs (tol %.4f cfs)" % (gauge, block, got, ref, tol)


# ---- grader self-checks (NOT scored; excluded from the reward by test.sh) ----

@pytest.mark.selfcheck
def test_selfcheck_frozen_golden_matches_live_recompute():
    """V-01: the cached reference values reproduce from the shipped data, not a stored key."""
    live = _recompute()
    for item in ITEMS:
        got = live[(item["gauge_id"], item["blockkey"])]
        ref = item["ref_mean_discharge_cfs"]
        assert abs(got - ref) <= 1e-06, \
            "freeze drift at %s %s" % (item["gauge_id"], item["blockkey"])


@pytest.mark.selfcheck
def test_selfcheck_plausibility_and_guess_resistance():
    """V-08: the supplied recent measurement, and a round-number guess, both fail everywhere."""
    with open(os.path.join(DATA, "question.json")) as fh:
        decoys = json.load(fh)["decoy_reference"]["recent_discharge_measurement"]
    passes = sum(1 for it in ITEMS
                 if abs(decoys[it["gauge_id"]]["discharge_cfs"]
                        - it["ref_mean_discharge_cfs"]) <= it["tolerance_cfs"])
    assert passes == 0, "the supplied recent measurement passes %d block(s)" % passes

    # a plausible round-number guess per gauge cannot sweep that gauge's blocks
    for gauge in {it["gauge_id"] for it in ITEMS}:
        blocks = [it for it in ITEMS if it["gauge_id"] == gauge]
        guess = round(sum(b["ref_mean_discharge_cfs"] for b in blocks) / len(blocks), -2)
        hit = sum(1 for b in blocks
                  if abs(guess - b["ref_mean_discharge_cfs"]) <= b["tolerance_cfs"])
        assert hit < len(blocks), "a single round guess passes every block at %s" % gauge


@pytest.mark.selfcheck
def test_selfcheck_isomorphic_invariance_under_rescale():
    """V-09: the reference is a property of the data, not of memorised surface values.

    Rescaling a gauge's whole discharge column by k must rescale every block mean for
    that gauge by exactly k. A verifier keyed to remembered numbers would not survive
    this; one that recomputes does.
    """
    k = 3.7
    series = {}
    with open(os.path.join(DATA, "stage_series.csv")) as fh:
        for row in csv.DictReader(fh):
            series.setdefault(row["gauge_id"], []).append(
                (_epoch(row["datetime_utc"]), float(row["gage_height_ft"])))
    for gauge, points in series.items():
        points.sort()
        rows = load_rating(os.path.join(_LIB, "ratings", "rating_%s.tsv" % gauge))
        scaled = [(h, s, q * k) for h, s, q in rows]
        times = [p[0] for p in points]
        q_scaled = [discharge_at(scaled, p[1]) for p in points]
        for item in [it for it in ITEMS if it["gauge_id"] == gauge]:
            got = block_mean(times, q_scaled, _epoch(item["start_utc"]),
                             _epoch(item["end_utc"]))
            assert abs(got - k * item["ref_mean_discharge_cfs"]) <= 1e-06 * k, \
                "relabel/rescale invariance broken at %s %s" % (gauge, item["blockkey"])


@pytest.mark.selfcheck
def test_selfcheck_tolerances_are_positive_and_bind():
    """V-02: every tolerance is a real, finite, positive band tied to its reference."""
    assert len(ITEMS) == 12, "item set malformed"
    keys = set()
    for it in ITEMS:
        assert it["tolerance_cfs"] > 0, "non-positive tolerance"
        assert math.isfinite(it["ref_mean_discharge_cfs"])
        keys.add((it["gauge_id"], it["blockkey"]))
        assert "ref_%s_%s_mean_discharge_cfs" % (it["gauge_id"], it["blockkey"]) in EXP
    assert len(keys) == 12, "duplicate item keys"
