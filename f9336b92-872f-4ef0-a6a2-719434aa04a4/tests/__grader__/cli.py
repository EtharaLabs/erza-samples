"""Subcommands of the grader entry point. Every one runs as the grader uid, never on submitted code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canonical import JSONValue
from refload import DEFAULT_ROOT, load_reference


def _write_json(path: Path, value: JSONValue) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def _gen(args: argparse.Namespace) -> int:
    from gen import GENERATORS, case_line  # noqa: PLC0415 - loaded per subcommand
    from gen.contested import CONTESTED  # noqa: PLC0415

    ref = load_reference(Path(args.ref))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    exclude = frozenset(args.exclude or ()) | (CONTESTED if args.exclude_contested else frozenset())
    for category in args.only or list(GENERATORS):
        cases = GENERATORS[category](ref, args.count, exclude)
        (out / f"{category}.jsonl").write_text("".join(case_line(c) + "\n" for c in cases), encoding="ascii")
        print(json.dumps({"category": category, "cases": len(cases)}))
    return 0


def _census(args: argparse.Namespace) -> int:
    from gen.contested import FAMILIES, classify  # noqa: PLC0415
    from gen.spec import parse_dtstart, spec_from_text  # noqa: PLC0415

    ref = load_reference(Path(args.ref))
    table: dict[str, JSONValue] = {}
    for path in sorted(Path(args.cases).glob("K?.jsonl")):
        counts = dict.fromkeys(FAMILIES, 0)
        lines = path.read_text(encoding="ascii").splitlines()
        clean = 0
        for line in lines:
            raw = json.loads(line)
            spec, dtstart = spec_from_text(raw["rule"]), parse_dtstart(raw["dtstart"])
            found = classify(ref, spec, dtstart, int(raw["limit"]), raw["rule"])
            clean += not found
            for name in found:
                counts[name] += 1
        table[path.stem] = {"cases": len(lines), "in_no_family": clean, "families": dict(counts)}
    print(json.dumps(table, indent=1, sort_keys=True))
    return 0


def _score(args: argparse.Namespace) -> int:
    from score.category import over_budget, read_cases, score  # noqa: PLC0415

    ref = load_reference(Path(args.ref))
    results: dict[str, JSONValue] = {}
    reasons: dict[str, JSONValue] = {}
    for category in ("K1", "K2", "K3", "K4", "K5", "K6"):
        cases = read_cases(Path(args.cases) / f"{category}.jsonl")
        raw_path = Path(args.raw) / f"{category}.raw"
        output = raw_path.read_bytes() if raw_path.is_file() and not raw_path.is_symlink() else b""
        status = _status(Path(args.status) / f"{category}.status.json") if args.status else "ok"
        result = score(ref, cases, output) if status in ("ok", "not-run") else over_budget(cases, status)
        results[category] = result.to_json()
        reasons[category] = result.detail
    _write_json(Path(args.out), results)
    _write_json(Path(args.diagnostics), reasons)
    return 0


def _status(path: Path) -> str:
    """A supervisor status record's ``status``; anything unreadable counts as a stopped child."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "missing-status"
    status = value.get("status") if isinstance(value, dict) else None
    return status if isinstance(status, str) else "missing-status"


def _suite_report(args: argparse.Namespace) -> int:
    from checks.junit import InvalidRunError, build_run  # noqa: PLC0415

    def read(path: str) -> bytes:
        target = Path(path)
        if not target.is_file() or target.is_symlink():
            raise InvalidRunError(f"{target.name} missing or not a regular file")
        return target.read_bytes()

    record: dict[str, JSONValue]
    try:
        for status_path in (args.collect_status, args.status):
            if (status := _status(Path(status_path))) != "ok":
                raise InvalidRunError(f"budget: {status}")
        code = json.loads(read(args.status))["exit"]
        if not isinstance(code, int) or isinstance(code, bool):
            raise InvalidRunError("the run has no exit status")
        run = build_run(read(args.junit), read(args.collect), code)
        record = {"exit": run.exit, "collected": sorted(run.collected), "outcomes": dict(sorted(run.outcomes.items())), "collect_errors": sorted(run.collect_errors)}
    except (InvalidRunError, ValueError) as error:
        record = {"invalid": str(error)}
    Path(args.out).write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


def _manifest(args: argparse.Namespace) -> int:
    from checks.manifest import manifest  # noqa: PLC0415

    found = manifest(Path(args.tree))
    _write_json(Path(args.out), dict(found))
    return 0


def _assemble(args: argparse.Namespace) -> int:
    from checks.assemble import Inputs, assemble  # noqa: PLC0415

    paths = Inputs(*(Path(getattr(args, field)) for field in Inputs.__dataclass_fields__))
    results, notes = assemble(paths)
    _write_json(Path(args.out), results)
    _write_json(Path(args.diagnostics), dict(notes))
    return 0


def main(argv: list[str]) -> int:
    """Dispatch one grader subcommand."""
    parser = argparse.ArgumentParser(prog="grade")
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("gen", help="write the K1..K6 case files")
    gen.add_argument("--ref", default=str(DEFAULT_ROOT))
    gen.add_argument("--out", required=True)
    gen.add_argument("--count", type=int, default=2000)
    gen.add_argument("--only", nargs="*", choices=["K1", "K2", "K3", "K4", "K5", "K6"])
    gen.add_argument("--exclude", nargs="*", help="contested families to leave out (gen/contested.py)")
    gen.add_argument("--exclude-contested", action="store_true", help="leave out every contested family")
    gen.set_defaults(handler=_gen)
    census = commands.add_parser("census", help="count the cases in each contested family")
    census.add_argument("--ref", default=str(DEFAULT_ROOT))
    census.add_argument("--cases", required=True)
    census.set_defaults(handler=_census)
    sc = commands.add_parser("score", help="score the child's raw output per category")
    sc.add_argument("--ref", default=str(DEFAULT_ROOT))
    for flag in ("--cases", "--raw", "--out", "--diagnostics"):
        sc.add_argument(flag, required=True)
    sc.add_argument("--status", help="directory of K?.status.json supervisor records")
    sc.set_defaults(handler=_score)
    sr = commands.add_parser("suite-report", help="turn one junit run into a strict suite report")
    for flag in ("--junit", "--collect", "--collect-status", "--status", "--out"):
        sr.add_argument(flag, required=True)
    sr.set_defaults(handler=_suite_report)
    mf = commands.add_parser("manifest", help="hash the shipped tree outside the allowed areas")
    mf.add_argument("--tree", required=True)
    mf.add_argument("--out", required=True)
    mf.set_defaults(handler=_manifest)
    asm = commands.add_parser("assemble", help="write the strict results file")
    for field in ("categories", "baseline", "shipped_suite", "own_suite", "own_on_shipped", "shipped_sigs", "own_sigs", "manifest", "workspace", "out", "diagnostics"):
        asm.add_argument("--" + field.replace("_", "-"), dest=field, required=True)
    asm.set_defaults(handler=_assemble)
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
