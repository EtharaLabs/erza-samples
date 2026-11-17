# Make this Raft library safe

`/workspace/raft` holds a copy of the Go Raft library `go.etcd.io/raft/v3`. Applications drive it through `RawNode`, `Ready`, and a `Storage` they implement. Its documentation in `doc.go` and on the exported API states how an application must persist state, send messages, and apply entries, both in the default mode and with `Config.AsyncStorageWrites`.

Bring the library into conformance with the contract below, then report what you found.

## Behaviour contract

Take any cluster of raft nodes whose application honours the documented contract in either mode, configured with any combination of `PreVote` and `CheckQuorum`. `ReadOnlyOption` is `ReadOnlySafe` and `StepDownOnRemoval` is true. In the default mode, the application writes each `Ready`'s `HardState` and entries durably before it sends that `Ready`'s messages. The application may compact its log and send snapshots. Under every schedule of the events below, these properties must hold:

1. **Election safety.** At most one node becomes leader in any term.
2. **State machine safety.** No two nodes apply different entries at the same log index.
3. **Applied once, in order.** Between restarts, a node never applies an index it has already applied, and it applies indexes in increasing order without gaps. A snapshot counts as applying every index it covers. After a restart, an index the node had applied may be delivered again only with the same entry.
4. **Linearizable reads.** A `ReadState` returned for a `ReadIndex` request carries an index at least as high as every index any node had applied when the request was issued.

The events are:

- Messages may be delayed, delivered in any order, delivered more than once, or lost.
- The network may partition and heal.
- A node may crash at any point and restart from its `Storage`. A crash loses everything the documented contract does not require to have been written durably by then. In particular, with `AsyncStorageWrites` it loses every storage message its append and apply threads have not yet processed.
- With `AsyncStorageWrites`, the application processes each local thread's messages in order, but the two threads, and the delivery of their responses, may interleave in any way.
- Campaigns may start at any node at any time.

Once every node is up, the network is connected, messages are delivered in order, and storage work is completed, the cluster must elect a leader and apply new proposals on every node.

## Rules

- Keep the exported API and the module definition (`go.mod`, `go.sum`) as they are. Do not make the library ignore `AsyncStorageWrites` or any other option.
- The library's Go unit tests must keep passing. The data-driven interaction traces under `/workspace/raft/testdata/` record exact message sequences. You may regenerate any of them (`go test -run TestInteraction -rewrite`) when a change alters a sequence. They are not part of what must pass.
- Outside test files, the module must not import a package the library as shipped does not import, use `os`, `syscall`, `unsafe`, `runtime`, or `reflect` identifiers more often than the library as shipped does, or add a package `init` function, a `go:linkname` directive, or non-Go source files.
- The environment has no network. The Go toolchain and every dependency of the module are already installed.

## Deliverables

1. **The repaired library** in place at `/workspace/raft`.
2. **Regression tests.** Add them as Go test functions in new files under `/workspace/raft` whose names end in `_regression_test.go`. Each named test must fail against the library as you received it and pass against your repair. Each must build within 120 seconds and run within 10 seconds of CPU time. Name at most 16.
3. **A report** at `/workspace/output/REPAIR_REPORT.md`. For each cause of a violation you found, give:
   - the property it violates;
   - a sequence of message deliveries, crashes, or storage-thread steps under which the library as you received it violates that property;
   - the name of the regression test that reproduces it.

   Mark each claim as verified by running code or as inferred without running code. State which causes must be repaired together for a property to hold.
