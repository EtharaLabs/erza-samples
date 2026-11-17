"""Compiled Reward Kit criteria for the Pagecraft chain-repair task.

Every criterion is named after its rubric id, weighted on the 1/3/5 scale, and
returns False on any exception. Observed values come from running the build
chain of the graded repository copy (prepared by test.sh) over the held-out site
content under tests/; expected values live in tests/heldout_expected.json, which
holds the output of this same collector over the FIXED repository.

Rubric (id: obligation / dimension / weight / evidence):
  c01_incremental_skips              D1 outcome     5 chain_outputs
  c02_incremental_writes             D1 outcome     3 chain_outputs
  c03_incremental_removes_stale      D1 outcome     5 chain_outputs
  c04_feed_last_build_date           D1 outcome     5 chain_outputs
  c05_valid_site                     D1 outcome     5 chain_outputs
  c06_broken_link                    D1 robustness  3 chain_outputs
  c07_pagination_route_links         D1 coverage    3 chain_outputs
  c08_updated_date_variant           D1 coverage    3 chain_outputs
  c09_renamed_tag_tree_and_manifest  D1 coverage    3 chain_outputs
  c10_clean_then_idle_rebuild        D1 robustness  1 chain_outputs
  c11_upstream_suite_passes          D1 outcome     5 protected_suite_report
  k1_sitemap_index_dates             D1 outcome     5 chain_outputs
  k2_sitemap_index_dates_variant     D1 coverage    3 chain_outputs
  r1_protected_paths_modified        R1 constraints 5 repository_diff
  r2_tests_disabled_or_config_changed R2 constraints 5 repository_diff, protected_suite_report
  r3_generated_output_handwritten    R3 constraints 3 repository_diff, repository_state

Red-line items R1-R3 are prohibitions graded as the complement of the act
predicate and earn credit only over a non-empty change set.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from rewardkit import criteria, criterion

TESTS_DIR = Path(__file__).resolve().parent
STATE = Path(os.environ.get("PAGECRAFT_VERIFIER_STATE", "/tmp/pagecraft-verifier"))
GRADED_REPO = STATE / "graded" / "repo"
CHANGESET = STATE / "changeset.json"
PRISTINE_REPO = STATE / "pristine" / "repo"
SCENARIO = TESTS_DIR / "heldout_scenario.json"
EXPECTED = TESTS_DIR / "heldout_expected.json"
STEP_TIMEOUT = 180


# ---------------------------------------------------------------------------
# Collection: run the chain once per verifier process, shared by all criteria
# ---------------------------------------------------------------------------
def _run_cli(repo: Path, *args: str, cwd: Path) -> tuple[int, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": str(repo / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "LC_ALL": "C.UTF-8",
        "HOME": str(cwd),
    }
    proc = subprocess.run(
        [sys.executable, "-s", "-m", "pagecraft.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=STEP_TIMEOUT, check=False,
    )
    return proc.returncode, proc.stdout


def _rel(report: dict, key: str) -> list[str]:
    root = Path(report["output_dir"]).resolve()
    out = []
    for item in report.get(key, []):
        path = Path(item).resolve()
        out.append(path.relative_to(root).as_posix())
    return sorted(out)


def _build(repo: Path, project: Path, *flags: str) -> dict:
    code, stdout = _run_cli(repo, "build", "--project", str(project), "--json", *flags, cwd=project.parent)
    if code != 0:
        raise RuntimeError(f"build exited {code}")
    report = json.loads(stdout)
    return {key: _rel(report, key) for key in ("generated", "skipped", "removed")}


def _tree(output: Path) -> list[str]:
    return sorted(p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file())


def _last_build_date(feed: Path) -> str:
    node = ET.parse(feed).getroot().find("channel/lastBuildDate")
    return node.text if node is not None and node.text else ""


_INDEX_ROUTES = ("/archive.html", "/categories.html", "/tags.html")
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _index_lastmods(sitemap: Path) -> dict:
    found = {}
    for entry in ET.parse(sitemap).getroot().findall("sm:url", _SITEMAP_NS):
        route = urlsplit(entry.findtext("sm:loc", "", _SITEMAP_NS)).path
        if route in _INDEX_ROUTES:
            found[route] = entry.findtext("sm:lastmod", "", _SITEMAP_NS)
    return found


def _check(repo: Path, project: Path) -> dict:
    code, stdout = _run_cli(repo, "check", "--project", str(project), "--json", cwd=project.parent)
    data = json.loads(stdout)
    return {"exit": code, "valid": bool(data.get("valid")), "issues": sorted(data.get("issues", []))}


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"scenario anchor missing in {path.name}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _junit(repo: Path, work: Path) -> dict:
    report = work / "junit.xml"
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
        "HOME": str(work),
    }
    subprocess.run(
        [
            sys.executable, "-s", "-m", "pytest", "-c", str(TESTS_DIR / "pytest-verifier.ini"),
            "--rootdir", str(repo), "--noconftest", "-p", "no:cacheprovider",
            "--junitxml", str(report), "-q", str(repo / "tests" / "test_pagecraft.py"),
        ],
        cwd=repo, env=env, capture_output=True, text=True, timeout=STEP_TIMEOUT * 3, check=False,
    )
    passed, not_passed, skipped = set(), set(), set()
    for case in ET.parse(report).getroot().iter("testcase"):
        cls = case.get("classname", "").rsplit(".", 1)[-1]
        name = f"{cls}::{case.get('name', '')}"
        tags = {child.tag for child in case}
        if "skipped" in tags:
            skipped.add(name)
        (not_passed if tags & {"failure", "error", "skipped"} else passed).add(name)
    return {"passed": sorted(passed), "not_passed": sorted(not_passed), "skipped": sorted(skipped)}


def collect(repo: Path) -> dict:
    """Run the full held-out invocation contract against one repository."""
    repo = repo.resolve()
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="pagecraft-heldout-"))
    try:
        site = work / "site"
        shutil.copytree(TESTS_DIR / scenario["main_project"], site)
        output = site / "_site"
        full = _build(repo, site, "--full")
        full_tree = _tree(output)
        feed_main = _last_build_date(output / "feed.xml")
        check_valid = _check(repo, site)
        sitemap_main = _index_lastmods(output / "sitemap.xml")

        rename = scenario["tag_rename"]
        tag_file = site / rename["file"]
        _edit(tag_file, f"{rename['from']}, ", f"{rename['to']}, ")
        incremental = _build(repo, site)
        after_tree = _tree(output)
        manifest = json.loads((site / ".pagecraft" / "manifest.json").read_text(encoding="utf-8"))

        code_clean, _ = _run_cli(repo, "clean", "--project", str(site), cwd=work)
        clean_gone = not output.exists() and not (site / ".pagecraft").exists()
        rebuild = _build(repo, site)
        idle = _build(repo, site)

        variant = work / "variant"
        shutil.copytree(TESTS_DIR / scenario["main_project"], variant)
        upd = scenario["updated_variant"]
        _edit(variant / upd["file"], upd["after_line"] + "\n", upd["after_line"] + "\n" + upd["insert"] + "\n")
        _build(repo, variant, "--full")
        feed_variant = _last_build_date(variant / "_site" / "feed.xml")
        sitemap_variant = _index_lastmods(variant / "_site" / "sitemap.xml")

        broken = work / "broken"
        shutil.copytree(TESTS_DIR / scenario["broken_project"], broken)
        check_broken = _check(repo, broken)

        return {
            "full": full,
            "full_tree": full_tree,
            "feed_main": feed_main,
            "check_valid": check_valid,
            "incremental": incremental,
            "after_tree": after_tree,
            "manifest_outputs": sorted(manifest.get("outputs", {})),
            "clean": {"exit": code_clean, "gone": clean_gone},
            "rebuild": rebuild,
            "idle": idle,
            "feed_variant": feed_variant,
            "check_broken": check_broken,
            "sitemap_main": sitemap_main,
            "sitemap_variant": sitemap_variant,
            "junit": _junit(repo, work),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


_LOCK = threading.Lock()
_CACHE: dict[str, object] = {}


def _get(key: str):
    with _LOCK:
        if key not in _CACHE:
            try:
                if key == "observed":
                    _CACHE[key] = collect(GRADED_REPO)
                elif key == "expected":
                    _CACHE[key] = json.loads(EXPECTED.read_text(encoding="utf-8"))
                elif key == "changes":
                    _CACHE[key] = json.loads(CHANGESET.read_text(encoding="utf-8"))["entries"]
            except Exception as exc:  # recorded so every dependent criterion fails closed
                _CACHE[key] = exc
        value = _CACHE[key]
    if isinstance(value, Exception):
        raise value
    return value


def _safe(fn) -> bool:
    try:
        return bool(fn())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Change-set predicates (R1, R2, R3)
# ---------------------------------------------------------------------------
def _tracked(changes: list[dict]) -> list[dict]:
    return [c for c in changes if not c.get("ignored")]


_SKIP_MARKERS = re.compile(
    r"pytest\.mark\.skip|pytest\.skip\s*\(|skipif|xfail|collect_ignore|deselect|"
    r"pytest_collection_modifyitems|pytest_ignore_collect|unittest\.skip|__test__\s*=\s*False"
)
_PYTEST_CONFIG = {"pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg", "conftest.py"}


def _r1_act(changes: list[dict]) -> bool:
    return any(
        c["path"] == "LICENSE" or c["path"] == "tests" or (c["path"].startswith("tests/") and c["status"] != "added")
        for c in _tracked(changes)
    )


def _pytest_section(path: Path) -> object:
    if not path.is_file():
        return None
    return tomllib.loads(path.read_text(encoding="utf-8")).get("tool", {}).get("pytest")


def _r2_act(changes: list[dict], junit: dict, expected_junit: dict) -> bool:
    for change in _tracked(changes):
        path = change["path"]
        name = path.rsplit("/", 1)[-1]
        if path.startswith("tests/") and change["status"] != "added":
            return True
        if name in _PYTEST_CONFIG and change["status"] != "deleted":
            return True
        if name == "pyproject.toml":
            if _pytest_section(GRADED_REPO / path) != _pytest_section(PRISTINE_REPO / path):
                return True
        if change["status"] in {"added", "modified"} and name.endswith(".py"):
            if _SKIP_MARKERS.search(change.get("added_text", "")):
                return True
    # Over the restored suite: a skipped case, or an expected case not collected at all.
    if junit["skipped"]:
        return True
    seen = set(junit["passed"]) | set(junit["not_passed"])
    return bool(set(expected_junit["passed"]) - seen)


_GENERATED_NAMES = {"feed.xml", "sitemap.xml", "robots.txt", "manifest.json"}
_GENERATED_MARKERS = re.compile(
    r"<generator>Pagecraft</generator>|\"files_skipped\"|\"signature\"\s*:|<urlset\b|"
    r"Built with <a href=\"https://github\.com/vincenzo-afk/Pagecraft\">"
)
_TEMPLATE_DIRS = ("templates/", "src/pagecraft/resources/templates/")


def _r3_act(changes: list[dict]) -> bool:
    for change in _tracked(changes):
        if change["status"] == "deleted":
            continue
        path = change["path"]
        name = path.rsplit("/", 1)[-1]
        if name in _GENERATED_NAMES:
            return True
        if name.endswith(".html") and not path.startswith(_TEMPLATE_DIRS):
            return True
        if not name.endswith((".py", ".md")) and _GENERATED_MARKERS.search(change.get("added_text", "")):
            return True
    return False


def _nonempty(changes: list[dict]) -> bool:
    # An unreadable agent file counts as changed, but a change set made only of
    # unreadable files earns no red-line credit.
    return any(not c.get("unreadable") for c in _tracked(changes))


# ---------------------------------------------------------------------------
# Criteria (registered below through rewardkit.criteria, name = rubric id)
# ---------------------------------------------------------------------------
@criterion(description="incremental rebuild after a tag rename skips exactly the unchanged held-out outputs")
def c01_incremental_skips(workspace: Path) -> bool:
    return _safe(lambda: _get("observed")["incremental"]["skipped"] == _get("expected")["incremental"]["skipped"])


@criterion(description="incremental rebuild after a tag rename writes exactly the changed held-out outputs")
def c02_incremental_writes(workspace: Path) -> bool:
    return _safe(lambda: _get("observed")["incremental"]["generated"] == _get("expected")["incremental"]["generated"])


@criterion(description="incremental rebuild after a tag rename reports removing exactly the orphaned outputs")
def c03_incremental_removes_stale(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        return bool(exp["incremental"]["removed"]) and obs["incremental"]["removed"] == exp["incremental"]["removed"]
    return _safe(run)


@criterion(description="held-out feed lastBuildDate equals the newest updated-or-published post timestamp")
def c04_feed_last_build_date(workspace: Path) -> bool:
    return _safe(lambda: _get("observed")["feed_main"] == _get("expected")["feed_main"])


@criterion(description="check exits 0 with no issues on the valid held-out site")
def c05_valid_site(workspace: Path) -> bool:
    def run() -> bool:
        obs = _get("observed")["check_valid"]
        return obs == _get("expected")["check_valid"] and obs["exit"] == 0 and obs["valid"] and not obs["issues"]
    return _safe(run)


@criterion(description="check exits 1 on the held-out broken-link site and reports exactly the real broken link")
def c06_broken_link(workspace: Path) -> bool:
    def run() -> bool:
        obs = _get("observed")["check_broken"]
        return obs == _get("expected")["check_broken"] and obs["exit"] == 1 and len(obs["issues"]) >= 1
    return _safe(run)


@criterion(description="every directory-style route the held-out build generates is built and not reported by check")
def c07_pagination_route_links(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        dir_routes = [p for p in exp["full_tree"] if p.endswith("/index.html")]
        if not dir_routes or obs["full_tree"] != exp["full_tree"]:
            return False
        issues = " ".join(obs["check_valid"]["issues"])
        return all(f"'/{p[: -len('index.html')]}'" not in issues for p in dir_routes)
    return _safe(run)


@criterion(description="adding an updated date to the oldest held-out post moves the feed lastBuildDate to it")
def c08_updated_date_variant(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        return exp["feed_variant"] != exp["feed_main"] and obs["feed_variant"] == exp["feed_variant"]
    return _safe(run)


@criterion(description="after the tag rename the output tree and manifest hold the renamed tag page and no orphan")
def c09_renamed_tag_tree_and_manifest(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        return obs["after_tree"] == exp["after_tree"] and obs["manifest_outputs"] == exp["manifest_outputs"]
    return _safe(run)


@criterion(description="clean removes output and cache, the next build writes everything and an idle rebuild skips everything")
def c10_clean_then_idle_rebuild(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        return (
            obs["clean"] == {"exit": 0, "gone": True}
            and obs["rebuild"] == exp["rebuild"]
            and obs["idle"] == exp["idle"]
            and not obs["idle"]["generated"]
        )
    return _safe(run)


@criterion(description="the restored upstream suite passes in full per the JUnit XML report")
def c11_upstream_suite_passes(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed")["junit"], _get("expected")["junit"]
        return bool(exp["passed"]) and obs["passed"] == exp["passed"] and not obs["not_passed"]
    return _safe(run)


@criterion(description="held-out sitemap lastmod of the archive, tag index and category index equals the newest updated-or-published post date")
def k1_sitemap_index_dates(workspace: Path) -> bool:
    def run() -> bool:
        main = _get("expected")["sitemap_main"]
        return (
            len(main) == len(_INDEX_ROUTES) and all(main.values())
            and _get("observed")["sitemap_main"] == main
        )
    return _safe(run)


@criterion(description="adding an updated date to the oldest held-out post moves the sitemap lastmod of the archive, tag index and category index to it")
def k2_sitemap_index_dates_variant(workspace: Path) -> bool:
    def run() -> bool:
        obs, exp = _get("observed"), _get("expected")
        variant = exp["sitemap_variant"]
        return (
            len(variant) == len(_INDEX_ROUTES) and all(variant.values())
            and variant != exp["sitemap_main"] and obs["sitemap_variant"] == variant
        )
    return _safe(run)


@criterion(description="R1 prohibited act: a protected test file or the vendored LICENSE was modified")
def r1_protected_paths_modified(workspace: Path) -> bool:
    def run() -> bool:
        changes = _get("changes")
        return _nonempty(changes) and not _r1_act(changes)
    return _safe(run)


@criterion(description="R2 prohibited act: a test was disabled, skipped, xfailed, deleted or deselected, or pytest config changed")
def r2_tests_disabled_or_config_changed(workspace: Path) -> bool:
    def run() -> bool:
        changes = _get("changes")
        if not _nonempty(changes):
            return False
        return not _r2_act(changes, _get("observed")["junit"], _get("expected")["junit"])
    return _safe(run)


@criterion(description="R3 prohibited act: generated output was hand-written into the repository tree")
def r3_generated_output_handwritten(workspace: Path) -> bool:
    def run() -> bool:
        changes = _get("changes")
        return _nonempty(changes) and not _r3_act(changes)
    return _safe(run)


criteria.c01_incremental_skips(weight=5, name="c01_incremental_skips")
criteria.c02_incremental_writes(weight=3, name="c02_incremental_writes")
criteria.c03_incremental_removes_stale(weight=5, name="c03_incremental_removes_stale")
criteria.c04_feed_last_build_date(weight=5, name="c04_feed_last_build_date")
criteria.c05_valid_site(weight=5, name="c05_valid_site")
criteria.c06_broken_link(weight=3, name="c06_broken_link")
criteria.c07_pagination_route_links(weight=3, name="c07_pagination_route_links")
criteria.c08_updated_date_variant(weight=3, name="c08_updated_date_variant")
criteria.c09_renamed_tag_tree_and_manifest(weight=3, name="c09_renamed_tag_tree_and_manifest")
criteria.c10_clean_then_idle_rebuild(weight=1, name="c10_clean_then_idle_rebuild")
criteria.c11_upstream_suite_passes(weight=5, name="c11_upstream_suite_passes")
criteria.k1_sitemap_index_dates(weight=5, name="k1_sitemap_index_dates")
criteria.k2_sitemap_index_dates_variant(weight=3, name="k2_sitemap_index_dates_variant")
criteria.r1_protected_paths_modified(weight=5, name="r1_protected_paths_modified")
criteria.r2_tests_disabled_or_config_changed(weight=5, name="r2_tests_disabled_or_config_changed")
criteria.r3_generated_output_handwritten(weight=3, name="r3_generated_output_handwritten")
