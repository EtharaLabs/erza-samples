"""Turn one sandboxed pytest run into a strict report, read only after every sandbox process exited.

Inputs: pytest's own ``--junitxml`` file (``junit_family=xunit1``), the stdout of a separate
``--collect-only -q`` pass over the same suite and library, the run's exit status, and the
supervisor's status record. Any of these missing, oversize, malformed, or inconsistent makes
the whole run invalid; nothing is inferred from a partial run.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # noqa: N817 - the conventional alias
from dataclasses import dataclass
from typing import Final, Never

MAX_JUNIT: Final = 32 * 1024 * 1024
MAX_COLLECT: Final = 16 * 1024 * 1024
MAX_IDS: Final = 200_000
NODE: Final = re.compile(r"tests/[A-Za-z0-9_./-]+\.py::\S.*")
FILE: Final = re.compile(r"tests/[A-Za-z0-9_./-]+\.py")


class InvalidRunError(ValueError):
    """The run cannot be read; ``reason`` names why."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason: Final = reason


def _bad(reason: str) -> Never:
    raise InvalidRunError(reason)


@dataclass(frozen=True, slots=True)
class Run:
    """Collected node ids, one outcome per id, and files that failed to collect."""

    exit: int
    collected: frozenset[str]
    outcomes: dict[str, str]
    collect_errors: frozenset[str]


def parse_collect(raw: bytes) -> frozenset[str]:
    """Node ids from ``pytest --collect-only -q``: one per line up to the summary line."""
    if len(raw) > MAX_COLLECT:
        _bad("collect output too large")
    ids: list[str] = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            break
        if NODE.fullmatch(line) is None:
            _bad(f"unexpected collect line {line[:80]!r}")
        ids.append(line)
    if len(ids) != len(set(ids)) or len(ids) > MAX_IDS:
        _bad("collect output repeats a node id or is too long")
    return frozenset(ids)


def _node(case: ET.Element) -> str:
    file, classname, name = case.get("file"), case.get("classname"), case.get("name")
    if not file or name is None or classname is None or FILE.fullmatch(file) is None:
        _bad("a testcase lacks file, classname, or name")
    module = file[:-3].replace("/", ".")
    if classname == module:
        return f"{file}::{name}"
    if not classname.startswith(module + "."):
        _bad(f"classname {classname!r} is outside {file!r}")
    return f"{file}::{classname[len(module) + 1 :].replace('.', '::')}::{name}"


def _outcome(case: ET.Element) -> str:
    tags = [child.tag for child in case if child.tag in ("failure", "error", "skipped")]
    if "failure" in tags or "error" in tags:
        return "failed"
    if "skipped" in tags:
        return "skipped"
    return "passed"


def parse_junit(raw: bytes) -> tuple[dict[str, str], frozenset[str]]:
    """Outcomes by node id, and the files reported as collection errors."""
    if len(raw) > MAX_JUNIT:
        _bad("junit file too large")
    if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        _bad("junit file declares a DTD or entity")
    try:
        root = ET.fromstring(raw)  # noqa: S314 - bounded, DTD-free input
    except ET.ParseError as error:
        _bad(f"junit file is not XML: {error}")
    suites = [root] if root.tag == "testsuite" else list(root) if root.tag == "testsuites" else []
    if len(suites) != 1 or suites[0].tag != "testsuite":
        _bad("junit file must hold exactly one testsuite")
    suite = suites[0]
    outcomes: dict[str, str] = {}
    errors: set[str] = set()
    cases = [child for child in suite if child.tag == "testcase"]
    for case in cases:
        if case.get("classname") == "" and FILE.fullmatch(case.get("file") or "") and _outcome(case) == "failed":
            errors.add(str(case.get("file")))
            continue
        node = _node(case)
        if node in outcomes:
            _bad(f"junit file repeats {node}")
        outcomes[node] = _outcome(case)
    counts = {key: int(suite.get(key, "-1")) for key in ("tests", "failures", "errors", "skipped")}
    failed = sum(1 for case in cases if any(c.tag == "failure" for c in case))
    errored = sum(1 for case in cases if any(c.tag == "error" for c in case))
    skipped = sum(1 for case in cases if any(c.tag == "skipped" for c in case))
    if counts != {"tests": len(cases), "failures": failed, "errors": errored, "skipped": skipped}:
        _bad("junit testsuite counts disagree with its testcases")
    return outcomes, frozenset(errors)


def build_run(junit: bytes, collect: bytes, exit_code: int) -> Run:
    """A consistent run: every collected id has one outcome and the exit status agrees."""
    collected = parse_collect(collect)
    outcomes, errors = parse_junit(junit)
    if set(outcomes) != collected:
        _bad("junit node ids differ from the separate collection pass")
    any_failed = bool(errors) or any(outcome == "failed" for outcome in outcomes.values())
    if (exit_code, any_failed) not in ((0, False), (1, True)):
        _bad(f"exit status {exit_code} disagrees with the junit outcomes")
    return Run(exit_code, collected, outcomes, errors)
