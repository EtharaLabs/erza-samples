from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

# test.sh runs this fallback only when the LLM judge returned no result.


@criterion(shared=True, description="judge-unavailable: the LLM judge returned no result, so the judged dimension scores 0")
def judge_unavailable(workspace: Path) -> float:
    return 0.0


rk.judge_unavailable(name="judge-unavailable")
