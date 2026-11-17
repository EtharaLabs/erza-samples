# Repair report

The library as received violated three of the stated properties through five causes. Every claim below is marked. A claim marked "verified" was checked by running code: each named regression test fails against the library as received and passes against the repair. Claims marked "inferred" were reasoned from the code without a separate run.

## Cause 1: vote requests sent before the candidate's state is durable

With `AsyncStorageWrites`, `raft.send` queued vote and append responses until the append thread had written the state they depend on, but sent a candidate's own `MsgVote` at once, before its new term and self-vote were durable (inferred from the code; the sequence below confirms its effect).

- Violated property: state machine safety (verified); election safety by the same mechanism (inferred).
- Sequence (verified): A campaigns and its vote requests reach B and C while A's append thread still holds the new term and vote. A wins, replicates `x` at index 2 to B, and crashes before its append thread runs. A restarts at its old term, campaigns into the same term again, wins with C, and writes `y` at index 2. B applies `x` while A and C apply `y` at index 2.
- Regression test: `TestVoteDurableRegression` (verified: it fails against the library as received and passes against the repair).
- Repair: `MsgVote` is queued with the messages sent after the durable append (verified: the regression test above passes with it).

## Cause 2: a snapshot handed to the append thread while earlier entries are being applied

With `AsyncStorageWrites`, a follower that received a snapshot while committed entries before it were still queued on its apply thread handed the snapshot to the append thread at once (inferred from the code; the sequence below confirms its effect).

- Violated property: applied once, in order (verified).
- Sequence (verified): follower B has committed entries queued on its apply thread. Leader A compacts its log and sends a snapshot covering them. B's append thread installs the snapshot, and the apply thread then applies the older entries again.
- Regression test: `TestSnapshotOrderRegression` (verified: it fails against the library as received and passes against the repair).
- Repair: nothing is handed to the append thread while a snapshot waits for the entries handed out before it to be applied (verified: the regression test above passes with it).

## Cause 3: responses released by a Ready with nothing to write

`needStorageAppendMsg` did not count pending after-append messages, and a Ready with no entries, hard state, or snapshot sent those messages directly. A response that depended on an earlier write still in the append thread left before that write was durable (inferred from the code; the sequence below confirms its effect).

- Violated property: state machine safety (verified).
- Sequence (verified): B receives `x` at index 2 and its append thread has not run. A retransmits the same append, and B's next Ready, with nothing to write, sends the acknowledgement directly. A commits and applies `x`. B crashes and loses `x`, and B and C elect C, whose no-op is written at index 2.
- Regression test: `TestEmptyReadyBarrierRegression` (verified: it fails against the library as received and passes against the repair).
- Repair: pending after-append messages always travel through the append thread (verified: the regression test above passes with it).

## Cause 4: apply responses that mark every queued batch applied

The `MsgStorageApplyResp` handler set the applied index to everything handed to the apply thread so far, not to the last entry of the batch the response reports (inferred from the code; the sequence below confirms its effect).

- Violated property: applied once, in order (verified).
- Sequence (verified): two batches are queued on B's apply thread. The first is applied, and its response marks the second applied too. A snapshot then passes the hold that waits for earlier entries, is installed, and the second batch is applied after it.
- Regression test: `TestApplyBoundaryRegression` (verified: it fails against the library as received and passes against the repair).
- Repair: the applied index advances to the last entry of the reported batch (verified: the regression test above passes with it).

## Cause 5: append responses counted as read confirmations

A leader with pending `ReadOnlySafe` reads counted any accepted append response as an acknowledgement of its newest read position, although the response may have been sent before the read arrived (inferred from the code; the sequence below confirms its effect).

- Violated property: linearizable reads (verified, in both modes).
- Sequence (verified): A replicates `b` to B, and B's append response is delayed. A is partitioned, and B and C elect B, which commits and applies `W` at index 5. A read reaches A, the delayed append response arrives and confirms it, and A answers index 2.
- Regression test: `TestStaleAckReadRegression` (verified: it fails against the library as received and passes against the repair).
- Repair: only heartbeat responses carrying the read's context confirm reads (verified: the regression test above passes with it).

## Which causes must be repaired together

- Causes 1 and 3 must be repaired together (verified): both send a message before the state it depends on is durable, and either repair alone leaves the asynchronous-durability violations.
- Causes 2 and 4 must be repaired together (verified): the hold on snapshots is defeated while the applied index is overstated, and the boundary repair alone leaves the snapshot overtaking queued entries.
- Cause 5 is independent of the others (verified by repairing it alone).

## Checks

- The library's unit tests pass (verified). The data-driven traces in `testdata/async_storage_writes.txt` and `testdata/async_storage_writes_append_aba_race.txt` were regenerated, because vote requests now leave after the durable append (verified).
