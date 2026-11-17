---
name: raft-safety-simulation
description: Find and fix safety bugs in a Raft library by driving it with a deterministic, adversarial simulator instead of reading code against the paper alone.
---

# Testing a Raft library for safety

Raft safety bugs rarely show up in unit tests or in a happy-path cluster. They need a particular order of crashes, delayed or duplicated messages, and storage completions. Reading the code finds candidates. Only a schedule that makes the library break a property confirms one, and only the same schedule passing afterwards confirms a fix.

## Build a deterministic simulator first

- Drive each node through the library's public API (`RawNode`, `Ready`, `Step`, `Tick`, `Campaign`, `Propose`, `ReadIndex`), with one durable store per node that you implement yourself.
- Model durability exactly as the library documents it. Persist what a `Ready` says must be persisted before the messages it allows to leave. With asynchronous storage, keep a queue per local thread and process it only when the schedule says so. A crash discards every queue entry not yet processed.
- Keep a network queue you control: deliver any message in any order, duplicate, drop, partition.
- Make every choice from one seeded random source, and drive elections with explicit campaigns, so a failing seed replays exactly.

## Check properties, not outputs

- Record the leader of each term and flag a second one.
- Keep a global map from log index to the entry first applied there, and flag any node that applies something else at that index.
- Track each node's applied sequence and flag repeats, gaps, and snapshots that move it backwards.
- When a read is issued, record the highest index applied anywhere. Flag a returned read index below it.
- End every schedule with a benign phase (all nodes up, connected, queues drained) and require a new write to be applied everywhere. A repair that stops making progress is not a repair.

## Search, then script

- Random schedules find the common bugs. Weight them toward the rare events: slow storage threads, crashes right after a message leaves, retransmissions, compaction while a follower lags.
- When a property fails, shrink the schedule to the shortest script that still fails. That script is your regression test.
- For each kind of message, ask what state it promises the receiver is durable or current, and script the case where that promise is broken just before a crash or a leadership change.

## Repair and report

- Fix the cause, not the schedule. After each fix, rerun every script and a large random sweep, because one fix can expose another bug.
- Faults that break the same rule in different places tend to come together. When you fix one, look for the others.
- Keep the library's own unit tests passing. Data-driven traces that only record message order may change when ordering legitimately changes.
