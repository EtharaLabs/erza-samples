"""Runs one sandboxed grading step under a CPU-time limit on its whole process tree and charges
the step's CPU time to the run's CPU budget. Run by root from test.sh; prints one outcome token.

The guard is a child subreaper, so every descendant of the step stays in its tree. While the step
runs it samples a lower bound on the tree's CPU time: the CPU of descendants it has reaped
(RUSAGE_CHILDREN), plus user and system time, including reaped children, of every live descendant,
read parents before children so that a process reaped mid-sample is missed, never counted twice.
The step is killed once that lower bound exceeds its limit, the smaller of its cap and what is left
of the run budget. When the step ends, every descendant is killed and reaped, and the exact CPU
time of the whole tree is read from RUSAGE_CHILDREN; the outcome is decided from that number.

Outcome tokens: 0 (exited 0), exit:N, signal:N, cpu (exceeded its cap), budget (exceeded what was
left of the run budget, or none was left), backstop (ended by the wall-clock bound with its CPU
time under its limit, or a previous step was), collision (the run's sandbox uid had a process the
run did not start, or a previous step found one). The first backstop outcome latches the run: every
later step reports backstop without running, so the run spends at most one backstop interval. A
collision latches the same way, and test.sh then writes no reward.

Fork limit: submitted code runs as a uid allocated for this verifier run alone (--allocate-uid),
under RLIMIT_NPROC. The kernel counts that limit over every process of the uid on the host, so the
uid must have no other process: allocation draws it at random from 2^24 to 2^31 - 1 and keeps it only
when a probe finds it unused, and every step probes it again before it runs.
"""

import argparse
import ctypes
import json
import math
import os
import resource
import secrets
import signal
import sys
import time

PR_SET_CHILD_SUBREAPER = 36
TICK = os.sysconf("SC_CLK_TCK")
SAMPLE_SECONDS = 0.05
UID_LOW, UID_HIGH = 20000, 60000


def uid_unused(uid):
    """Whether no process runs as uid: a child takes the uid under RLIMIT_NPROC 2 and forks once,
    which the kernel allows only while the child is the uid's one process."""
    child = os.fork()
    if child == 0:
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (2, 2))
            os.setgroups([])
            os.setgid(uid)
            os.setuid(uid)
            grandchild = os.fork()
            if grandchild == 0:
                os._exit(0)
            os.waitpid(grandchild, 0)
            os._exit(0)
        except OSError:
            os._exit(1)
        finally:
            os._exit(1)
    return os.waitpid(child, 0)[1] == 0


def allocate_uid():
    for _ in range(32):
        uid = UID_LOW + secrets.randbelow(UID_HIGH - UID_LOW)
        if uid_unused(uid):
            return uid
    return None


def _stat(pid):
    """(ppid, own plus reaped-children CPU seconds) of a live or zombie process, or None."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as handle:
            fields = handle.read().rsplit(b")", 1)[1].split()
    except (OSError, IndexError):
        return None
    return int(fields[1]), sum(int(x) for x in fields[11:15]) / TICK


def _descendants(root):
    """Descendants of root in breadth-first order, each with the parent it was found under."""
    children = {}
    for name in os.listdir("/proc"):
        if name.isdigit():
            found = _stat(int(name))
            if found:
                children.setdefault(found[0], []).append(int(name))
    order, queue = [], [root]
    while queue:
        parent = queue.pop(0)
        for pid in children.get(parent, ()):
            order.append((pid, parent))
            queue.append(pid)
    return order


def _reaped_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _lower_bound(me):
    total = _reaped_cpu()
    for pid, parent in _descendants(me):
        found = _stat(pid)
        if found and found[0] == parent:
            total += found[1]
    return total


def _reap(main, status):
    while True:
        try:
            pid, code = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return status, True
        if pid == 0:
            return status, False
        if pid == main:
            status = code


def _run(args, limit):
    ctypes.CDLL(None, use_errno=True).prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)
    me = os.getpid()
    main = os.fork()
    if main == 0:
        try:
            os.dup2(os.open(args.stdin, os.O_RDONLY), 0)
            out = os.open(args.stdout, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            os.dup2(out, 1)
            os.dup2(out if args.stderr == args.stdout else os.open(args.stderr, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), 2)
            if args.fd3:
                os.dup2(os.open(args.fd3, os.O_WRONLY | os.O_APPEND), 3)
            os.closerange(4, 1024)
            os.chdir(args.cwd)
            # Defence in depth: no single process may outlive the step's limit by more than 1 s.
            soft = math.ceil(limit) + 1
            resource.setrlimit(resource.RLIMIT_CPU, (soft, soft + 1))
            if args.nproc is not None:
                # Inherited across setuid and execve; counts every process of the run's uid.
                resource.setrlimit(resource.RLIMIT_NPROC, (args.nproc, args.nproc))
            os.execvp(args.command[0], args.command)
        finally:
            os._exit(127)
    start, status, ended, killed = time.monotonic(), None, False, None
    while status is None:
        status, _ = _reap(main, status)
        if status is not None:
            break
        if _lower_bound(me) > limit:
            killed = "limit"
            break
        if time.monotonic() - start > args.backstop:
            killed = "backstop"
            break
        time.sleep(SAMPLE_SECONDS)
    for _ in range(500):
        for pid, _parent in _descendants(me):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        status, ended = _reap(main, status)
        if ended and not _descendants(me):
            break
        time.sleep(0.01)
    return status, killed, ended, _reaped_cpu(), time.monotonic() - start


def main():
    if sys.argv[1:] == ["--allocate-uid"]:
        uid = allocate_uid()
        if uid is None:
            return 1
        print(uid)
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True)
    parser.add_argument("--cap", type=float, required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--backstop", type=float, required=True)
    parser.add_argument("--nproc", type=int)
    parser.add_argument("--uid", type=int, required=True)
    parser.add_argument("--stdin", default=os.devnull)
    parser.add_argument("--stdout", default=os.devnull)
    parser.add_argument("--stderr", default=os.devnull)
    parser.add_argument("--fd3")
    parser.add_argument("--cwd", default="/")
    parser.add_argument("command", nargs="+")
    args = parser.parse_args()

    with open(args.ledger) as handle:
        ledger = json.load(handle)
    remaining = ledger["budget"] - ledger["used"]
    record = {"step": args.step, "cap": args.cap, "budget_left": round(remaining, 3), "ran": False}
    if ledger.get("collision"):
        outcome = "collision"
        record["after"] = ledger["collision"]
    elif ledger.get("blocked"):
        outcome = "backstop"
        record["after"] = ledger["blocked"]
    elif not uid_unused(args.uid):
        outcome = "collision"
        ledger["collision"] = args.step
    elif remaining <= 0:
        outcome = "budget"
    else:
        limit = min(args.cap, remaining)
        bound = "cpu" if args.cap <= remaining else "budget"
        status, killed, ended, cpu, wall = _run(args, limit)
        record.update(ran=True, limit=round(limit, 3), cpu=round(cpu, 3), wall=round(wall, 3), all_reaped=ended)
        ledger["used"] += cpu
        if cpu > limit:
            outcome = bound
        elif killed == "backstop":
            outcome = "backstop"
            ledger["blocked"] = args.step
        elif killed == "limit":
            outcome = bound  # unreachable: the lower bound exceeded the limit, so the exact total does
        elif status is not None and os.WIFEXITED(status):
            outcome = "0" if os.WEXITSTATUS(status) == 0 else f"exit:{os.WEXITSTATUS(status)}"
        elif status is not None:
            outcome = f"signal:{os.WTERMSIG(status)}"
        else:
            outcome = "signal:9"
    record["outcome"] = outcome
    with open(args.ledger, "w") as handle:
        json.dump(ledger, handle)
    with open(args.record, "a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(outcome)


if __name__ == "__main__":
    sys.exit(main())
