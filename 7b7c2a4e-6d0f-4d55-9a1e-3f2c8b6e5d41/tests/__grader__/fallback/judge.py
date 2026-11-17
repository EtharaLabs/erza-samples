import os
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

# test.sh names why the judge did not score; only the criterion for that cause is registered.


@criterion(shared=True, description="unrepaired: none of K1 to K4 passed, so the judge did not run and the judged dimension scores 0")
def unrepaired(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="note-missing: /workspace/output/REPAIR_REPORT.md is missing, empty, or not a regular file, so the judge did not run and the judged dimension scores 0")
def note_missing(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="judge-unavailable: the LLM judge returned no result, so the judged dimension scores 0")
def judge_unavailable(workspace: Path) -> float:
    return 0.0


CAUSE = os.environ.get("GRADE_FALLBACK_CAUSE") or "judge-unavailable"
if CAUSE == "unrepaired":
    rk.unrepaired(name="unrepaired")
elif CAUSE == "note-missing":
    rk.note_missing(name="note-missing")
else:
    rk.judge_unavailable(name="judge-unavailable")
