"""Print the public signatures of ``rrule``, ``rruleset``, and ``rrulestr`` as one JSON line on fd 3.

Usage: ``python3 -I -B /opt/runner/sigs.py <library root> 3> sigs.json``. Run as the sandbox
uid, because importing the library runs its code. The grader compares the mapping with the
one recorded for the shipped library when the image was built.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from budget import Budget  # noqa: E402 - runner modules load before the library path
from origin import require_root  # noqa: E402

sys.path.pop(0)

OUT_FD: Final = 3
TARGETS: Final = ("rrule", "rruleset", "rrulestr")


def _signature(target: Callable[..., object]) -> str:
    try:
        return str(inspect.signature(target))
    except (TypeError, ValueError) as error:
        return f"<no signature: {type(error).__name__}>"


def signatures(module: object) -> dict[str, str]:
    """``name`` and ``name.method`` to the text of each public callable's signature."""
    found: dict[str, str] = {}
    for name in TARGETS:
        target = getattr(module, name, None)
        if target is None or not callable(target):
            found[name] = "<missing>"
            continue
        found[name] = _signature(target)
        owner = target if inspect.isclass(target) else type(target)
        for attr, member in inspect.getmembers(owner):
            if attr.startswith("_") or not callable(member):
                continue
            found[f"{name}.{attr}"] = _signature(member)
    return found


def main(argv: list[str]) -> int:
    """Import ``dateutil.rrule`` from the library root and write its signatures."""
    sys.path.insert(0, argv[1])

    def probe() -> dict[str, str]:
        module = __import__("dateutil.rrule", fromlist=["rrule"])
        require_root(argv[1])
        return signatures(module)

    # Importing and inspecting run submitted code, so both run under the step budget; on any
    # failure, budget included, no record is written and the grader treats the signatures as changed.
    data = json.dumps(Budget().run(probe), sort_keys=True, separators=(",", ":")).encode() + b"\n"
    os.write(OUT_FD, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
