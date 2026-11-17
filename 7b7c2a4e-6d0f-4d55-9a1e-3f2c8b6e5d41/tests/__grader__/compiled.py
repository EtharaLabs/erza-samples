"""Compiled scoring: run the compiled items with pytest, then write their gated scores to
<results dir>/compiled.json for Reward Kit and verdict.json beside the reward.

Usage: python3 compiled.py <grader dir> <results dir> <verifier output dir>
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

COMPILED = {"K1": 5, "K2": 5, "K3": 5, "K4": 5, "K5": 1, "K6": 1, "K7": 3}
REPAIR = ("K1", "K2", "K3", "K4")


def compiled_scores(grader: Path, results: Path) -> tuple[dict, dict]:
    junit = results / "pytest.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}", str(grader / "test_outputs.py")],
        env={**os.environ, "GRADE_RESULTS": str(results), "GRADER_DIR": str(grader)},
        capture_output=True, text=True,
    )
    raw, messages = {k: 0 for k in COMPILED}, {}
    if junit.exists():
        for case in ET.parse(junit).getroot().iter("testcase"):
            item = case.get("name", "").removeprefix("test_")
            if item in raw:
                failed = case.find("failure") is not None or case.find("error") is not None or case.find("skipped") is not None
                raw[item] = 0 if failed else 1
                if failed:
                    node = case.find("failure") if case.find("failure") is not None else case.find("error")
                    messages[item] = (node.get("message") if node is not None else "skipped") or ""
    gate = any(raw[k] for k in REPAIR)
    scores = {k: (v if k in REPAIR or gate else 0) for k, v in raw.items()}
    return scores, messages


def main() -> int:
    grader, results, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    scores, messages = compiled_scores(grader, results)
    (results / "compiled.json").write_text(json.dumps(scores, sort_keys=True) + "\n")
    steps = [json.loads(l) for l in (results / "steps.jsonl").read_text().splitlines() if l.strip()]
    verdict = {
        "compiled": scores, "failures": messages,
        "admission": json.loads((results / "admission.json").read_text()),
        "named": json.loads((results / "named.json").read_text()),
        "named_outcomes": json.loads((results / "named_outcomes.json").read_text()),
        "steps": steps,
    }
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
