# FORGE-CANARY-BEGIN
# FORGE-CANARY-SLOT-1: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-SLOT-2: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-SLOT-3: 0000000000000000000000000000000000000000000000000000000000000000
# FORGE-CANARY-END
# GENERATED SECTION. DO NOT HAND-EDIT.
"""Regenerate solution/TRUTH.md from solution/grounding.yaml. Run from the task directory."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 64


def canary():
    slots = "\n".join(f"<!-- FORGE-CANARY-SLOT-{n}: {ZERO} -->" for n in (1, 2, 3))
    return f"<!-- FORGE-CANARY-BEGIN -->\n{slots}\n<!-- FORGE-CANARY-END -->\n"


def truth(g):
    out = [canary(), "<!-- GENERATED SECTION. DO NOT HAND-EDIT. -->", "", "# TRUTH", "",
           "Golden trajectory through instruction.md. Each step names the established state and the",
           "checker identifiers it satisfies.", ""]
    for n, step in enumerate(g["steps"], start=1):
        faults = f" Faults: {', '.join(step['faults'])}." if step["faults"] else ""
        out.append(f"{n}. {step['title']}. {step['action']}.{faults} Checkers: {', '.join(step['checkers'])}.")
    out += ["", f"Reference repair: {g['reference_repair']}.", "", f"Specification: {g['specification']}.", "",
            "## Deliverables and red-lines", ""]
    for key, item in list(g["deliverables"].items()) + list(g["red_lines"].items()):
        surface = f" Surface: {item['surface']}." if "surface" in item else ""
        out.append(f"- {key}: {item['statement']}.{surface} Checkers: {', '.join(item['checkers'])}.")
    out += ["", "## Rejected routes", ""]
    for r in g["rejected_routes"]:
        out.append(f"- {r['route']}. Control: {r['control']}.")
    return "\n".join(out) + "\n"


g = yaml.safe_load((ROOT / "solution" / "grounding.yaml").read_text())
(ROOT / "solution" / "TRUTH.md").write_text(truth(g))
