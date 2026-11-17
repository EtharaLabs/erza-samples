"""Deterministic case generators, one module per graded category (K1 to K6)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Final

from gen import k1_monthday, k2_weekday, k3_weekno, k4_setpos, k5_localtime, k6_preserve
from gen.spec import Case
from refload import Reference

CASES_PER_CATEGORY: Final = 2000
GENERATORS: Final[dict[str, Callable[[Reference, int], list[Case]]]] = {
    "K1": k1_monthday.generate,
    "K2": k2_weekday.generate,
    "K3": k3_weekno.generate,
    "K4": k4_setpos.generate,
    "K5": k5_localtime.generate,
    "K6": k6_preserve.generate,
}


def case_line(case: Case) -> str:
    """One case as a compact, key-sorted JSON line."""
    return json.dumps(case.to_json(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

