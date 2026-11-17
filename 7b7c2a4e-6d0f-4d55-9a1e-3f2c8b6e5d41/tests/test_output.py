"""Compiled items K1 to K7 as Reward Kit criteria. Reads the gated scores compiled.py wrote under
GRADE_RESULTS (K5 to K7 already score 0 unless one of K1 to K4 passed); never loads submitted code."""

import functools
import json
import os
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

RESULTS = Path(os.environ.get("GRADE_RESULTS", "/var/grade/results"))
ITEMS = {"K1": 5, "K2": 5, "K3": 5, "K4": 5, "K5": 1, "K6": 1, "K7": 3}
REPAIR = ("K1", "K2", "K3", "K4")


@functools.cache
def _scores() -> dict:
    """compiled.json, only when it carries exactly K1 to K7 with 0 or 1; else empty."""
    try:
        value = json.loads((RESULTS / "compiled.json").read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict) or set(value) != set(ITEMS) or any(value[k] not in (0, 1) for k in ITEMS):
        return {}
    return value


@criterion
def holds(workspace: Path, item: str) -> bool:
    return _scores().get(item) == 1


for _item, _weight in ITEMS.items():
    rk.holds(_item, weight=_weight, name=_item)


if __name__ == "__main__":
    import sys

    # Exit 0 when at least one of K1 to K4 passes; test.sh runs the judge only then.
    sys.exit(0 if any(_scores().get(k) == 1 for k in REPAIR) else 1)
