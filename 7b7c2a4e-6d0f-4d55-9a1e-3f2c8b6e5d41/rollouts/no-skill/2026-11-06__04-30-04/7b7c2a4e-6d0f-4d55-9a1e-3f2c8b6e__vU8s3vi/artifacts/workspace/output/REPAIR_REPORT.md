# Raft safety repair

The repair is in `/workspace/raft`. Production changes are confined to
`rawnode.go` and `raft.go`; eight named regression tests are in
`safety_regression_test.go`. The exported API, options, imports in production
code, `go.mod`, and `go.sum` are unchanged. Async storage remains asynchronous:
append and apply work can still be pipelined. Snapshot acceptance waits for
previously dispatched application to finish.

## Evidence and validation

**Verified by running code:** all eight named regressions fail against the
original production sources, preserved separately at `/workspace/raft-original`,
and pass against the repaired sources. The original run reports both
`different entries applied at one index: true` and `stale ReadState: true` in
the combined reproduction. The snapshot reproduction observes application order
`[3, 1, 2]` on the original and `[1, 2, 3]` on the repair.

**Verified by running code:** `go test ./... -count=1` and `go vet ./...` pass.
This includes the interaction tests; no trace regeneration was necessary.
Building the test executable took approximately 0.44 seconds wall time; running
all eight regressions together took approximately 0.0035 seconds CPU time.
These measurements use the installed toolchain and dependency/build caches.
Module files compare byte for byte with the original.

Logs: `original-regressions.log`, `repaired-tests.log`, `vet.log`,
`regression-build-time.log`, `regression-run-time.log`, and
`regression-run.log` in `/workspace/output`.

The finite tests verify the schedules and mechanisms described below. They are
not an exhaustive exploration or a formal proof of every possible schedule.
Where a further consequence was not executed, it is explicitly marked inferred.

## 1. Deferred responses escaped the append-thread durability barrier

**Properties:** election safety, state machine safety, linearizable reads; lost
acknowledged entries can also violate consistent replay after restart.

`needStorageAppendMsg` originally tested only for *new* entries, HardState, or a
snapshot. After one Ready had handed these to the append thread, a repeated
request could generate another response without generating new storage work.
The next Ready published that response directly even though the first write
was still queued.

**Verified schedule — election safety:**

1. In voters `{1,2,3}`, nodes 2 and 3 campaign for term 1 and durably record
   their own votes. Node 1 uses async storage.
2. Deliver node 2's vote request to node 1. Take its Ready, leaving the append
   thread paused before persisting the term and vote.
3. Deliver the same vote request again. The original library puts the repeated
   grant directly in the next Ready's network messages. Deliver it to node 2,
   which becomes leader with votes `{1,2}`.
4. Crash node 1, losing its unprocessed storage messages. Restart from its
   unchanged Storage, deliver node 3's term-1 vote request, persist this vote,
   and deliver the grant. Node 3 also becomes leader in term 1.

`TestRegressionDuplicateVoteAcrossCrash` executes this schedule with CheckQuorum
both disabled and enabled.

**Verified schedule — state machine safety and reads:**

Continue the split election with node 2 partitioned. Node 3 commits and applies
`Y` at index 2 with node 1. Node 2 proposes `X` at index 2, then exchanges a
heartbeat and append with node 1. Since node 1 has already committed index 2,
it acknowledges that index; node 2 commits and applies `X` there. Next node 3
commits and applies `Z` at index 3 with node 1. Issue a ReadIndex at node 2 and
deliver its heartbeat and node 1's response, withholding append traffic.
Node 2 returns index 2 although index 3 had been applied before the request.
`TestRegressionSplitLeadersApplyAndRead` executes these continuations and
observes both violations on the original.

**Verified mechanism — log acknowledgements:**
`TestRegressionDuplicateAppendDurability` queues an append of `x` at index 1,
pauses the append thread, and delivers that append again. The original emits an
acknowledgement before either storage message runs. The repair waits and
subsequently releases both acknowledgements after the durable write.

**Inferred without running the complete continuation:** after such an escaped
append acknowledgement, a leader can commit and apply `x` using that follower
as its quorum partner. Crash the follower before its write; isolate the old
leader; elect a third node with the restarted follower, and commit a different
entry at that index. This loses an already applied entry independently of the
split-election schedule above.

**Repair:** every nonempty `msgsAfterAppend` queue now requires an append-thread
message, including an otherwise empty barrier. Responses remain behind earlier
writes in that thread's ordered queue.

## 2. The same fast path discarded self-directed pre-vote responses

**Property:** eventual election and proposal application.

**Verified schedule:** configure a singleton with AsyncStorageWrites and
PreVote. Campaign and consume its Ready. Pre-voting changes no persistent
state, so the original emits no append message. Its fallback filters out the
self-directed pre-vote response. Completing all emitted storage work cannot
advance the election; repeating campaigns repeats the failure.

`TestRegressionAsyncSingletonPreVote` reproduces the stall. With the repair it
elects a leader and applies both the initial entry and a new proposal, with
CheckQuorum enabled.

**Repair:** the barrier change in cause 1 also carries self-directed responses
to completion. No synchronous-storage fallback is used.

## 3. An apply response acknowledged work that had not run

**Properties:** configuration-dependent election/state machine safety; also a
necessary part of preserving snapshot/application order.

**Verified schedule:** dispatch apply batches ending at indexes 1 and 2, leave
the second batch queued, and deliver only the first batch's response. The
original sets `applied` to the current `applying` frontier, 2, rather than the
response's last entry, 1.
`TestRegressionApplyResponseOnlyAcknowledgesItsBatch` observes the wrong
frontier directly.

**Verified configuration consequence:** make index 2 a committed configuration
change. After only index 1 has run, start a campaign. Because the original
incorrectly considers index 2 applied, its unapplied-configuration guard allows
the campaign using the older configuration.
`TestRegressionCampaignWaitsForQueuedConfiguration` executes this sequence.
The repaired node stays a follower until the configuration has been applied.

**Inferred without running a complete configuration-fork continuation:**
electing with an obsolete configuration or allowing another configuration
proposal before the prior one has run invalidates the quorum assumptions used
to protect election and state machine safety. The tests above verify the
premature acknowledgement and the resulting guard bypass, rather than claiming
to execute every such downstream violation.

**Repair:** advance only through the last entry carried by the response.
Existing monotonic handling also tolerates a late response for an older batch.

## 4. Snapshot installation overtook outstanding application

**Property:** applied once, in increasing order.

**Verified schedule:** dispatch committed apply batches for indexes 1 and 2 but
pause the apply thread. Receive a snapshot covering index 3. The original
immediately restores it and emits a snapshot append message. Run the append
thread first, installing the snapshot, then run the queued apply batches.
The application sees snapshot index 3 followed by entries 1 and 2.

`TestRegressionSnapshotWaitsForApply` runs this schedule and records `[3,1,2]`
on the original. Snapshot installation counts as applying the covered indexes,
so both subsequent entries repeat indexes and go backwards.

**Repair:** retain the incoming snapshot until all dispatched application is
acknowledged. While waiting, async Ready production pauses. On completion of
the last apply batch, accept the snapshot and emit its storage work. The node
cannot campaign while it has a deferred snapshot. Entries following an accepted
snapshot remain blocked by the existing unstable-snapshot barrier until its
append response arrives.

## 5. Snapshot configuration restoration ran before older ApplyConfChange calls

**Properties:** configuration-dependent election/state machine safety and
progress.

**Verified schedule:** start with voters `{1,2}`. Dispatch the committed entry
at index 1 adding node 3, but pause its application. Receive a snapshot covering
index 2 whose configuration is `{1,2}` (node 3 was subsequently removed).
The original restores `{1,2}` immediately. Now run the older index-1
ApplyConfChange call: it resurrects node 3. Completing snapshot storage does not
restore the correct configuration again.

`TestRegressionSnapshotConfigurationAfterQueuedConfChange` executes this
sequence. The original ends with `{1,2,3}`; the repair ends with `{1,2}`.

**Inferred without running a full partition/election continuation:** voting,
commitment, and progress under a resurrected configuration can use incorrect
quorums. The regression verifies the configuration corruption itself.

**Repair:** defer *accepting/restoring* the snapshot, including its configuration,
until old application finishes. Delaying only the outgoing snapshot storage
message would fix the thread ordering in cause 4 but leave this corruption.

## Repairs that must hold together

- Election safety requires the durability barrier for grants (cause 1), correct
  acknowledgement of configuration application (cause 3), and ordered snapshot
  configuration restoration (cause 5).
- State machine safety and safe replay require both vote and append response
  barriers, plus correct configuration handling. Fixing only the escaped vote
  grants leaves the independent escaped-append failure.
- Linearizable reads rely on those election, log, and configuration invariants.
  The executed stale-read example is eliminated by repairing the split-election
  cause; changing the read algorithm alone would leave its premise broken.
- Snapshot/application ordering requires causes 3, 4, and 5 together. A snapshot
  gate based on the original, prematurely advanced `applied` frontier can open
  while a later apply batch is still queued. Deferring storage alone also leaves
  older ApplyConfChange calls able to overwrite the snapshot configuration.
- Async PreVote progress additionally requires delivering self-directed responses
  even when there is no new persistent state (cause 2).
