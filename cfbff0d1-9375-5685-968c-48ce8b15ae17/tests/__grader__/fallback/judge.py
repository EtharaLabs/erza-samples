import os
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

# test.sh names why the judge did not score: refused, unchanged, note-missing, or judge-unavailable.
CAUSE = os.environ.get("GRADE_FALLBACK_CAUSE") or "judge-unavailable"
REASONS = {
    "refused": "the submission was refused before scoring, so the judge did not run",
    "unchanged": "the library under src/ is unchanged, so the judge did not run",
    "note-missing": "/workspace/output/ROOT_CAUSE.md is missing, empty, or not a regular file, so the judge did not run",
    "judge-unavailable": "the LLM judge returned no result",
}


@criterion(description=f"{CAUSE}: {REASONS.get(CAUSE, REASONS['judge-unavailable'])}, so the judged dimension scores 0")
def judge_not_scored(workspace: Path) -> float:
    return 0.0


rk.judge_not_scored(name=CAUSE)
