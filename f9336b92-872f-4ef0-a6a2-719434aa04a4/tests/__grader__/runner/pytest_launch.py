"""Start pytest on one suite with one dateutil library first on ``sys.path``; nothing else.

Usage, as the sandbox uid with a scrubbed environment::

    python3 -I -B /opt/runner/pytest_launch.py <library root> <pytest arguments...>

No plugin and no reporter of the grader's is loaded into this process: outcomes come only from
pytest's own ``--junitxml`` file and the exit status, read by the grader after every sandbox
process is gone. Exit 99 means the library root holds no importable ``dateutil``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from origin import require_root  # noqa: E402 - runner modules load before the library path

sys.path.pop(0)
NO_LIBRARY: Final = 99


def main(argv: list[str]) -> int:
    """Put the library first, refuse a dateutil from elsewhere, then hand over to pytest."""
    library = argv[1]
    sys.path.insert(0, library)
    try:
        __import__("dateutil")
        require_root(library)
    except Exception:  # noqa: BLE001 - any failure to import the submitted package ends the run
        return NO_LIBRARY
    import pytest  # noqa: PLC0415 - after the library path is in place

    return int(pytest.main(argv[2:]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
