"""Run one sandboxed child under the infrastructure guards, as root, and record how it ended.

Usage (root, from ``test.sh``)::

    python3 -I -B /opt/grader/supervise.py --cpu <seconds> --ledger <file> --status <file> -- <command...>

Guards, which only ever turn a run into a failure:

* ``RLIMIT_CPU``: the command itself is run under ``prlimit --cpu=<seconds>``; a child killed by
  SIGXCPU, or by SIGKILL at or past that CPU time, ends ``cpu-limit``.
* Starvation: every ``SAMPLE`` seconds the CPU time of all uid-1001 processes is sampled; once
  ``WINDOW`` seconds have passed, the run is killed when that CPU time advanced by less than
  ``STARVED_SHARE`` of one CPU over the last ``WINDOW`` seconds (sleeping, blocked, or stuck in a
  call that burns no CPU). It ends ``starved``.
* Run budget: the CPU seconds of every supervised child are summed in the root-owned ``--ledger``;
  a child is not started once the sum reaches ``RUN_BUDGET``, and is killed when it would pass it.
  It ends ``run-budget``.
* Wall clock: a child still running after ``wall_ceiling(cpu)`` seconds, that is its CPU limit
  divided by ``STARVED_SHARE`` but at most ``WALL_CAP``, is killed. This bounds a child that
  burns just over ``STARVED_SHARE`` of one CPU forever, which neither starves nor reaches its CPU
  limit quickly. It ends ``wall-limit``.

The status file is
``{"status": ok|cpu-limit|starved|run-budget|wall-limit, "exit": int|null, "cpu": float}``.
Every status but ``ok`` makes the grader fail that category or suite with reason ``budget``.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Final

SANDBOX_UID: Final = 1001
SAMPLE: Final = 1.0
WINDOW: Final = 60.0
STARVED_SHARE: Final = 0.05
RUN_BUDGET: Final = 1500.0
# The 13 children test.sh supervises each get min(limit / STARVED_SHARE, WALL_CAP); every limit
# there is at least 10 CPU-s, so each ceiling is 200 s and their sum 2600 s, below 3000 s.
WALL_CAP: Final = 200.0
_TICK: Final = os.sysconf("SC_CLK_TCK")


def _sandbox_procs() -> list[tuple[int, str, list[str]]]:
    """``(pid, state, stat fields after the state)`` of every uid-1001 process."""
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            status = Path(f"/proc/{entry}/status").read_text()
            stat = Path(f"/proc/{entry}/stat").read_text()
        except OSError:
            continue
        uid_line = next((line for line in status.splitlines() if line.startswith("Uid:")), "")
        if uid_line.split()[1:2] != [str(SANDBOX_UID)]:
            continue
        fields = stat[stat.rindex(")") + 2 :].split()
        found.append((int(entry), fields[0], fields[1:]))
    return found


def sandbox_cpu() -> float:
    """CPU seconds (user + system, own + reaped children) of every uid-1001 process."""
    return sum(sum(int(rest[i]) for i in (10, 11, 12, 13)) for _, _, rest in _sandbox_procs()) / _TICK


def kill_sandbox() -> None:
    """SIGKILL every live uid-1001 process until none is left; zombies cannot run and are skipped."""
    while live := [pid for pid, state, _ in _sandbox_procs() if state not in ("Z", "X")]:
        for pid in live:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        os.sched_yield()


def wall_ceiling(cpu_limit: float) -> float:
    """Wall seconds a child with ``cpu_limit`` CPU seconds may run before ``wall-limit``."""
    return min(cpu_limit / STARVED_SHARE, WALL_CAP)


def _read_ledger(path: Path) -> float:
    try:
        return float(path.read_text().strip() or "0")
    except (OSError, ValueError):
        return 0.0


def supervise(command: list[str], cpu_limit: float, ledger: Path) -> dict[str, object]:
    """Run ``command`` to completion or until a guard fires."""
    spent = _read_ledger(ledger)
    if spent >= RUN_BUDGET:
        return {"status": "run-budget", "exit": None, "cpu": 0.0}
    fds = (3,) if _fd_open(3) else ()
    child = subprocess.Popen(command, pass_fds=fds)  # noqa: S603 - argv built by test.sh
    window: deque[tuple[float, float]] = deque()
    started = time.monotonic()
    ceiling = wall_ceiling(cpu_limit)
    verdict = "ok"
    while True:
        pid, wait_status, usage = os.wait4(child.pid, os.WNOHANG)
        if pid:
            break
        now, cpu = time.monotonic(), sandbox_cpu()
        window.append((now, cpu))
        while window and now - window[0][0] > WINDOW:
            window.popleft()
        if spent + cpu > RUN_BUDGET:
            verdict = "run-budget"
        elif now - started >= WINDOW and window and cpu - window[0][1] < STARVED_SHARE * WINDOW:
            verdict = "starved"
        elif now - started >= ceiling:
            verdict = "wall-limit"
        if verdict != "ok":
            kill_sandbox()
            pid, wait_status, usage = os.wait4(child.pid, 0)
            break
        time.sleep(SAMPLE)
    cpu = max(usage.ru_utime + usage.ru_stime, window[-1][1] if window else 0.0)
    code = os.waitstatus_to_exitcode(wait_status)
    killed = {-signal.SIGKILL, 128 + signal.SIGKILL}
    if verdict == "ok" and (code in {-signal.SIGXCPU, 128 + signal.SIGXCPU} or (code in killed and cpu >= cpu_limit - 1)):
        verdict = "cpu-limit"
    ledger.write_text(f"{spent + cpu:.3f}\n")
    kill_sandbox()
    return {"status": verdict, "exit": code, "cpu": round(cpu, 3)}


def _fd_open(fd: int) -> bool:
    try:
        os.fstat(fd)
    except OSError:
        return False
    return True


def main(argv: list[str]) -> int:
    """Supervise one command and write its status, or with ``--kill`` only clear the sandbox; exit 0."""
    if argv == ["--kill"]:
        kill_sandbox()
        return 0
    parser = argparse.ArgumentParser(prog="supervise")
    parser.add_argument("--cpu", type=float, required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    record = supervise(command, args.cpu, Path(args.ledger))
    Path(args.status).write_text(json.dumps(record, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
