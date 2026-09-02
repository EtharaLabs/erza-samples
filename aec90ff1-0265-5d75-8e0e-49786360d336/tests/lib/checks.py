"""Deterministic detections over a normalised trajectory.

Each function is a *hypothesis about the arithmetic a correct run performs*. The
channel is pattern-matching over the source the agent authored (`agent_code`) and
the commands it ran - weaker than executing the agent's solver, and the largest
source of false negatives on unseen runs (see README). The matchers are
deliberately multi-spelling; every one is bound by a negative fixture in
`verification/negative_fixtures_test.py` that has been *seen to fire*.

ROUTE INDEPENDENCE (REQUIREMENT 2). A detector grades whether the run reached the
answer by a sound METHOD, never which of several correct ROUTES it took. The
day-count conventions in this task are named in the input file, so the earlier
matchers keyed on the convention NAME ("ACT/ACT ISDA" appearing in the source).
That is spelling-bound: a solver that labels its instruments by worksheet id -
`YF["INST09"] = yf_isda` - or that dispatches through a table keyed on the
instrument rather than on the basis string implements exactly the same arithmetic
and never spells the name. Every convention detector below is therefore bound to
the ARITHMETIC that distinguishes the convention, with the convention name kept
only as one accepted route among several.

Convention: positive detectors return True when the criterion is SATISFIED.
Guardrail detectors are named `failure_*` and return True when the FAILURE MODE
OCCURRED; the scored test then asserts the failure did NOT occur.

The single argument is any object exposing `.agent_code`, `.commands`,
`.agent_prose` and `.file_writes` - a real `trajectory.Trajectory` in production,
or one loaded from a synthetic run directory in the fixtures.
"""
from __future__ import annotations

import ast
import re

BASIS_STRINGS = [
    "30/360 US", "30E/360", "ACT/360", "ACT/365F", "ACT/ACT ISDA", "ACT/ACT ICMA",
]


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

    This path is the one that RUNS: `agent_code` concatenates every authored
    file with every command, so it essentially never parses whole (measured: 0
    of 54 recorded runs), and the fallback's precision is what decides every
    criterion read off `code`.

    The previous fallback was one regex applied with `sub`: it matched from ANY
    triple quote that OPENED a line to the next one that CLOSED a line. The
    closing delimiter of a multi-line data literal sits at column 0, so a run
    that embeds a table, a heredoc body or any block constant as a
    triple-quoted literal had everything between that closing quote and the
    next function docstring DELETED from the graded view - real code, silently
    missing from every criterion. Measured across this dataset's runs, that
    removed up to 27% of the non-whitespace source. Carrying reference data as
    a literal is ordinary practice, so the bug fell hardest on exactly the
    route the shipped reference data invites.

    Delimiters are now PAIRED in source order, so an opening quote is matched
    with its own closing quote, and a pair counts as prose only when its
    opening delimiter starts a logical line - a literal assigned to a name is
    left standing, as this module's contract promises. Line geometry is
    preserved.
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


def _code(traj) -> str:
    return _strip_comments(traj.agent_code or "")


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


# --------------------------- shared arithmetic signatures ---------------------------

# An actual day count: the elapsed-days term every ACT/* convention divides.
_ACTUAL_DAYS = r"\.days\b|days\s*\(|day_count|daysdiff|days_between|toordinal|timedelta"

# The end-of-month / February branch that separates 30/360 US from 30E/360. The
# rule can be spelled by naming February, by testing the month number, by asking
# the calendar for the last day of the month, or by stepping one day forward and
# seeing the month roll over - all the same test.
_FEB_EOM = (
    r"last_?of_?feb|last[^\n]{0,12}february|islastoffebruary|"
    r"\.month\s*==\s*2|month\s*==\s*2|\bfebruary\b|\bfeb\b|"
    r"monthrange|last_?day|end_?of_?month|\beom\b|is_?ultimo|"
    r"timedelta\s*\(\s*(?:days\s*=\s*)?1\s*\)[^\n]{0,20}\.month"
)


def _day_clamps_to_30(code: str) -> int:
    """How many times a day-of-month is pushed down to 30 with NO extra condition.

    This is what separates the two 30/360 families arithmetically. 30/360 US
    clamps D1 unconditionally but D2 only when D1 has already reached 30 (`if D2
    == 31 and D1 >= 30`); 30E/360 clamps BOTH ends unconditionally. Counting
    unguarded clamps therefore reads the Eurobond rule off the arithmetic without
    the source ever spelling "30E/360" - a solver that dispatches on worksheet id
    still shows two unguarded clamps, and a solver that only ever implemented the
    US rule shows exactly one.

    `min(day, 30)` is the same clamp written as a function call and counts too.
    """
    n = 0
    for m in re.finditer(r"([\w.\[\]'\"]+)\s*(?:==\s*31|>\s*30|>=\s*31)([^\n]*)", code):
        if re.search(r"\band\b|&&|month|feb", m.group(2), re.I):
            continue
        n += 1
    n += len(re.findall(r"\bmin\s*\(\s*[^,()\n]+,\s*30\s*\)", code))
    n += len(re.findall(r"\bminimum\s*\(\s*[^,()\n]+,\s*30\s*\)", code))
    return n


def _denominators(code: str) -> set:
    """The fixed year-length denominators the source actually divides by.

    Read as division or as the value side of a lookup table, because
    `DENOM = {"ACT/360": 360.0}` then `days / DENOM[basis]` is the same
    arithmetic as `days / 360.0` with the dispatch moved into data.
    """
    out = set()
    for n in (360, 365, 366):
        if re.search(r"/\s*%d(?:\.0+)?\b" % n, code) or \
           re.search(r"\b%d\.0+\b" % n, code) or \
           re.search(r":\s*%d(?:\.0+)?\s*[,}]" % n, code):
            out.add(n)
    return out


def _paren_denominators(code: str) -> list:
    """Every parenthesised divisor `/ ( ... )`, with balanced parentheses.

    A compound denominator is the only way `days / (frequency * period_days)` can
    be written, and reading it structurally frees the check from having to guess
    what the run called its frequency variable.
    """
    out = []
    for m in re.finditer(r"/\s*\(", code):
        i, depth = m.end() - 1, 0
        for j in range(i, min(len(code), i + 400)):
            if code[j] == "(":
                depth += 1
            elif code[j] == ")":
                depth -= 1
                if depth == 0:
                    out.append(code[i + 1:j])
                    break
    return out


def _icma_period_denominator(code: str) -> bool:
    """The ACT/ACT ICMA denominator: coupon frequency x reference-period length.

    Route-independent: the frequency may be read from the instrument
    (`coupon_frequency`), called `freq`/`f`/`periods_per_year`, or written as the
    literal 2 or 4 for a semi-annual/quarterly bond; the period length may be a
    date difference (`(ref_end - ref_start).days`) or a named
    `reference_period_days`. What is invariant is that a frequency and a period
    LENGTH are combined multiplicatively into the denominator.
    """
    freq = (r"coupon_frequency|payment_frequency|\bfrequency\b|\bfreq\b|\bfrq\b|"
            r"periods?_per_year|payments?_per_year|coupons?_per_year")
    period = (r"reference_period|ref_?start|ref_?end|ref_?period|period_start|"
              r"period_end|period_days|period_len\w*|coupon_period|\brs\b|\bre_?\b")
    days = _ACTUAL_DAYS
    # 1. the denominator is literally a product that mentions a period length.
    #    Covers `days / (freq * (ref_end - ref_start).days)` and
    #    `days / (2 * period_days)` alike, whatever the frequency is called.
    for d in _paren_denominators(code):
        if "*" in d and re.search(r"%s|%s" % (days, period), d, re.I):
            return True
    # 2. the frequency and the period length combined on one line, in either order
    pats = [
        r"(?:%s)[^\n]{0,80}[*/][^\n]{0,80}(?:%s|%s)" % (freq, days, period),
        r"(?:%s|%s)[^\n]{0,80}[*/][^\n]{0,80}(?:%s)" % (days, period, freq),
    ]
    return any(re.search(p, code, re.I) for p in pats)


# --------------------------- positive detectors ---------------------------

def reads_inputs(traj) -> bool:
    """Read /root/data/instruments.json.

    Commands are searched as well as authored source: `cd /root/data` followed by
    a solver that opens `instruments.json` relatively is the same read.
    """
    blob = _code(traj) + "\n" + _cmds(traj)
    return bool(re.search(r"instruments\.json|/root/data\b", blob, re.I))


def writes_solver(traj) -> bool:
    """Authored a hand-written python solver (file or heredoc)."""
    if any(str(p).endswith(".py") for p, _ in traj.file_writes):
        return True
    code = _code(traj)
    return bool(re.search(r"\bimport\b", code)) and bool(
        re.search(r"\bdef\b|json\.|datetime|timedelta", code)
    )


def executes_solver(traj) -> bool:
    """Ran python to produce the results."""
    return bool(re.search(r"\bpython3?\b", _cmds(traj)))


def accrued_relation(traj) -> bool:
    """accrued = notional * annual_coupon_rate * year_fraction.

    The year fraction need not be called `year_fraction`: a solver that returns it
    from `yf_30_360_us(...)` straight into the product, or holds it in `t`, forms
    the same relation. What is required is the notional, the coupon rate and a
    product, with an accrual quantity present.
    """
    code = _code(traj)
    return (
        bool(re.search(r"notional|\bface\b|principal", code, re.I))
        and bool(re.search(r"coupon|\brate\b", code, re.I))
        and bool(re.search(r"year_fraction|\byf\b|frac|accru", code, re.I))
        and "*" in code
    )


def thirty_360_us_eom(traj) -> bool:
    """30/360 US Bond Basis with the February + 31->30 cascade.

    Previously required the source to SPELL "30/360 US" / "Bond Basis". A solver
    that dispatches on the worksheet id, or that names its function `yf_a`, runs
    exactly the ISDA 4.16(f) cascade and never writes the name. The criterion is
    now decided by the cascade itself: 30/360 arithmetic present, plus the
    February end-of-month branch (the thing that makes it the US rule rather than
    the Eurobond one), plus the 31->30 clamp.
    """
    code = _code(traj)
    named = bool(re.search(
        r"30/?360\s*US|bond\s*basis|thirty360[^\n]*usa|4\.16\s*\(?\s*f\s*\)?", code, re.I))
    arithmetic = bool(
        (re.search(r"360\s*\*", code) and re.search(r"\b30\s*\*", code))
        or re.search(r"/\s*360(?:\.0+)?\b", code))
    feb_rule = bool(re.search(_FEB_EOM, code, re.I))
    thirty_one = bool(re.search(r"\b31\b", code))
    return (named or arithmetic) and feb_rule and thirty_one


def thirty_e_360_rule(traj) -> bool:
    """30E/360 Eurobond: unconditional 31->30 at BOTH ends, no February rule.

    Previously required the literal "30E/360" or "Eurobond". The Eurobond rule is
    identifiable from the arithmetic alone: it is the only 30/360 variant that
    clamps both day numbers without a guard, so two unguarded 31->30 clamps in the
    source is the convention itself rather than one way of naming it. A run that
    only ever implemented the US cascade shows a single unguarded clamp (its D2
    clamp carries `and D1 >= 30`) and still fails.
    """
    code = _code(traj)
    named = bool(re.search(
        r"30E/?360|eurobond|thirty360[^\n]*europ|4\.16\s*\(?\s*g\s*\)?", code, re.I))
    thirty_one = bool(re.search(r"\b31\b|\bmin\s*\([^\n]*,\s*30\s*\)", code))
    return (named or _day_clamps_to_30(code) >= 2) and thirty_one


def _actual_days_over(code: str, n: int) -> bool:
    """An actual day count divided by the fixed denominator `n`.

    Three accepted routes: the division written out on one line; the denominator
    reached through a lookup table (`days / DENOM[basis]` with `n` among the
    table's values), which is the same arithmetic with the dispatch moved into
    data; or the denominator bound to a name that is then divided by.
    """
    inline = (re.search(r"(?:%s)[^\n]{0,50}/\s*%d(?:\.0+)?\b" % (_ACTUAL_DAYS, n),
                        code, re.I)
              or re.search(r"/\s*%d(?:\.0+)?\b[^\n]{0,50}(?:%s)" % (n, _ACTUAL_DAYS),
                           code, re.I))
    if inline:
        return True
    tabled = re.search(r":\s*%d(?:\.0+)?\s*[,}]" % n, code) or \
        re.search(r"=\s*%d(?:\.0+)?\s*$" % n, code, re.M)
    divides_by_name = re.search(r"/\s*[A-Za-z_]\w*\s*[\[(.]", code) or \
        re.search(r"/\s*[A-Za-z_]\w*\s*$", code, re.M)
    return bool(tabled) and bool(divides_by_name) and bool(
        re.search(_ACTUAL_DAYS, code, re.I))


def act_360_365_distinct(traj) -> bool:
    """ACT/360 and ACT/365F kept apart by their fixed denominators.

    Bound to the two denominators applied to an actual day count, not to the
    convention names: a worksheet-id dispatch, or a denominator lookup table
    (`DENOM = {...: 360.0, ...: 365.0}`), divides the same elapsed days by the
    same two constants without writing "ACT/360" anywhere. Requiring the division
    to reach an ACTUAL day count keeps the 360 borrowed from a 30/360 month
    formula and the 365 borrowed from an ISDA branch from satisfying it by
    accident.
    """
    code = _code(traj)
    return _actual_days_over(code, 360) and _actual_days_over(code, 365)


def actact_isda_leapsplit(traj) -> bool:
    """ACT/ACT ISDA: leap-year splitting (/366 and /365 across year segments).

    Previously gated on the literal "ACT/ACT ISDA". The distinguishing arithmetic
    is a leap-aware year length combined with a split at the calendar-year
    boundary - a run that keys its dispatch on the instrument id, or that names
    the function `yf_b` after ISDA 4.16(b), performs it identically. Both halves
    are still required, so a run that divides actual days by a single 365 (the
    recorded wrong path) still fails.
    """
    code = _code(traj)
    leap_aware = bool(
        re.search(r"\b366\b", code)
        or re.search(r"is_?leap|isleap|calendar\.isleap|\bleap\b", code, re.I)
        or re.search(r"year\s*%\s*4|%\s*400|%\s*100", code)
        or re.search(r"days_?in_?year|year_?length", code, re.I))
    _atom = r"[\w.\[\]'\"]+"
    year_split = bool(
        re.search(r"date\w*\(\s*%s\s*\+\s*1\s*,\s*1\s*,\s*1\s*\)" % _atom, code)
        or re.search(r"date\w*\(\s*%s\s*,\s*1\s*,\s*1\s*\)" % _atom, code)
        or re.search(r"\b(?:jan(?:uary)?)\D{0,4}1\b", code, re.I)
        or re.search(r"range\s*\(\s*%s?y\w*\s*[,+]" % _atom, code, re.I)
        or re.search(r"y2\s*-\s*y1|\.year\s*-\s*%s\.year|year\s*-\s*\w*year" % _atom, code))
    return leap_aware and year_split


def actact_icma_perioddenom(traj) -> bool:
    """ACT/ACT ICMA: period denominator = frequency * reference-period days.

    Previously gated on the literal "ACT/ACT ICMA" plus any mention of a
    frequency. The name carried the criterion, so a worksheet-id dispatch scored
    zero for arithmetic it had performed correctly. It is now decided by the
    denominator itself: a coupon frequency (named, or the bare literal for a
    semi-annual/quarterly bond) multiplied into a reference-period length. A run
    that divides by a plain 365 still fails.
    """
    return _icma_period_denominator(_code(traj))


def reports_contract(traj) -> bool:
    """Emitted /root/results.json keyed by id with both fields.

    The destination may be spelled literally, assembled from a directory and a
    name, or taken from the task's own output-path field; the two contract keys
    are the load-bearing part.
    """
    code = _code(traj)
    return (
        bool(re.search(r"results\.json|output_path|results_path", code, re.I))
        and bool(re.search(r"year_fraction", code))
        and bool(re.search(r"accrued_interest", code))
    )


# --------------------------- guardrail failure detectors ---------------------------

def failure_uniform_naive(traj) -> bool:
    """Failure: one uniform day-count formula for all instruments (no dispatch).

    Counting the convention NAMES in the source made this guardrail spelling-bound
    in the most expensive direction: a correct solver that dispatches on the
    worksheet id, and so never writes "ACT/360", was charged -3 for work it did
    right. Dispatch is now read from any of three independent signatures - the
    basis strings, the number of distinct year-length denominators the source
    divides by, or the number of branch arms - and the guardrail fires only when
    every one of them says a single formula was applied to everything.
    """
    code = _code(traj)
    n_basis = sum(1 for b in BASIS_STRINGS if b in code)
    n_denom = len(_denominators(code))
    if _icma_period_denominator(code):
        n_denom += 1
    n_branch = len(re.findall(r"\belif\b", code)) + len(re.findall(r"^\s*case\b", code, re.M))
    if n_branch:
        n_branch += 1                      # the leading `if` arm
    n_branch = max(n_branch, len(re.findall(r"\bdef\s+\w*(?:yf|year_frac|"
                                            r"day_?count|accru)\w*", code, re.I)))
    return max(n_basis, n_denom, n_branch) < 2


def failure_forbidden_library(traj) -> bool:
    """Failure: imported a forbidden finance / day-count library."""
    code = _code(traj)
    return bool(re.search(
        r"\bimport\s+quantlib\b|\bfrom\s+quantlib\b|\bimport\s+ql\b|"
        r"\bimport\s+financepy\b|\bfrom\s+financepy\b|"
        r"\bimport\s+isda\b|\bfrom\s+isda\b|"
        r"pandas\.tseries\.offsets|\bfrom\s+pandas\.tseries\b",
        code, re.I))


# id -> (detector, is_guardrail). The scored tests and the fixtures both read this.
DETECTORS = {
    "R3": (reads_inputs, False),
    "R4": (writes_solver, False),
    "R5": (executes_solver, False),
    "R6": (accrued_relation, False),
    "R7": (thirty_360_us_eom, False),
    "R8": (thirty_e_360_rule, False),
    "R9": (act_360_365_distinct, False),
    "R10": (actact_isda_leapsplit, False),
    "R11": (actact_icma_perioddenom, False),
    "R12": (reports_contract, False),
    "R13": (failure_uniform_naive, True),
    "R14": (failure_forbidden_library, True),
}
