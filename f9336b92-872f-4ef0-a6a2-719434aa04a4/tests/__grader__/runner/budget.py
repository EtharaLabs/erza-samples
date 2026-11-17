"""A deterministic step budget for code the sandbox runs, counted with ``sys.monitoring``.

Every Python function start and every jump (loop back-edge or branch) costs one step. No clock
is read. The first step past the budget raises :class:`StepBudgetExceeded`, a ``BaseException``
so ``except Exception`` in the code under test does not swallow it. Code that swallows it anyway
is marked exceeded all the same, and if it keeps running to ``HARD_FACTOR`` times the budget the
process exits at once with ``RUNAWAY_EXIT``, writing nothing more. ``PYTHONHASHSEED`` is fixed by
the caller, so the count depends only on the code and its input.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from types import CodeType
from typing import Final

STEP_BUDGET: Final = 8_000_000
CATEGORY_BUDGET: Final = 400_000_000
HARD_FACTOR: Final = 2
RUNAWAY_EXIT: Final = 86
_TOOL: Final = sys.monitoring.PROFILER_ID
_EVENTS: Final = sys.monitoring.events.PY_START | sys.monitoring.events.JUMP


class StepBudgetExceeded(BaseException):  # noqa: N818 - reported as the error token "budget"
    """The monitored code ran more steps than its budget allows."""


class Budget:
    """Counts the steps of one monitored stretch at a time; nested ``start`` calls share it.

    Mutable by design: it is the counter the monitoring callbacks advance. ``peak`` is the most
    steps any finished stretch used, and ``total`` the steps of every finished stretch together.
    """

    def __init__(self, steps: int = STEP_BUDGET) -> None:
        self._cap = steps
        self._used = 0
        self._depth = 0
        self.exceeded = False
        self.peak = 0
        self.total = 0
        sys.monitoring.use_tool_id(_TOOL, "grader-budget")
        sys.monitoring.register_callback(_TOOL, sys.monitoring.events.PY_START, self._tick)
        sys.monitoring.register_callback(_TOOL, sys.monitoring.events.JUMP, self._tick)

    def _tick(self, _code: CodeType, *_offsets: int) -> None:
        self._used += 1
        if self._used == self._cap + 1:
            self.exceeded = True
            raise StepBudgetExceeded
        if self._used > self._cap * HARD_FACTOR:
            os._exit(RUNAWAY_EXIT)

    def start(self) -> None:
        """Begin a stretch; the outermost start resets the count and turns events on."""
        if self._depth == 0:
            self._used = 0
            self.exceeded = False
            sys.monitoring.set_events(_TOOL, _EVENTS)
        self._depth += 1

    def stop(self) -> None:
        """End a stretch; the outermost stop turns events off."""
        self._depth -= 1
        if self._depth == 0:
            sys.monitoring.set_events(_TOOL, 0)
            self.peak = max(self.peak, self._used)
            self.total += self._used

    def run[T](self, probe: Callable[[], T]) -> T:
        """``probe()`` under a fresh budget; exceeded even if the probe swallowed the signal."""
        self.start()
        try:
            result = probe()
        finally:
            self.stop()
        if self.exceeded:
            raise StepBudgetExceeded
        return result
