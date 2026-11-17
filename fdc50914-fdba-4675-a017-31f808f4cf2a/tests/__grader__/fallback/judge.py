import os
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

# test.sh names why the judge did not score; only the criterion for that cause is registered.


@criterion(shared=True, description="refused: the submission was refused before scoring, so the judge did not run and the judged dimension scores 0")
def refused(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="unchanged: the library under src/ is unchanged, so the judge did not run and the judged dimension scores 0")
def unchanged(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="build-failed: the submitted library did not build, so no compiled item ran, the judge did not run and the judged dimension scores 0")
def build_failed(workspace: Path) -> float:
    return 0.0

@criterion(shared=True, description="unrepaired: none of C01 to C08 passed, so the library repairs nothing, the judge did not run and the judged dimension scores 0")
def unrepaired(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="note-unsupported: /workspace/output/ROOT_CAUSE.md earned none of J01 to J09, so J10 is not credited and the judged dimension scores 0")
def note_unsupported(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="note-missing: /workspace/output/ROOT_CAUSE.md is missing, empty, or not a regular file, so the judge did not run and the judged dimension scores 0")
def note_missing(workspace: Path) -> float:
    return 0.0


@criterion(shared=True, description="judge-unavailable: the LLM judge returned no result, so the judged dimension scores 0")
def judge_unavailable(workspace: Path) -> float:
    return 0.0


CAUSE = os.environ.get("GRADE_FALLBACK_CAUSE") or "judge-unavailable"
if CAUSE == "refused":
    rk.refused(name="refused")
elif CAUSE == "unchanged":
    rk.unchanged(name="unchanged")
elif CAUSE == "build-failed":
    rk.build_failed(name="build-failed")
elif CAUSE == "unrepaired":
    rk.unrepaired(name="unrepaired")
elif CAUSE == "note-unsupported":
    rk.note_unsupported(name="note-unsupported")
elif CAUSE == "note-missing":
    rk.note_missing(name="note-missing")
else:
    rk.judge_unavailable(name="judge-unavailable")
