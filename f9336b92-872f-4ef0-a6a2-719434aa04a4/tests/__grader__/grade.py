"""Grader-side entry point: ``python3 -I -B /opt/grader/grade.py <command> ...``.

Every command here runs as the grader uid and may import the reference; none imports the
submitted library. The sandboxed child lives in ``runner/`` and is never imported from here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main  # noqa: E402 - the grader root must be importable first

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
