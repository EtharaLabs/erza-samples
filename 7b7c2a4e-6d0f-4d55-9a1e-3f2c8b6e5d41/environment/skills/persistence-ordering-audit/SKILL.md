---
name: persistence-ordering-audit
description: Audit a replicated-state library for side effects that run ahead of the durable or observed state they depend on, such as messages sent before a write, acknowledgements counted for the wrong thing, or progress reported early.
---

# Auditing persistence and ordering

Consensus and replication libraries are correct only if every side effect waits for the state it vouches for. The bugs that survive review are almost never in the algorithm's core rules. They sit in the plumbing that decides when something may leave the process, or when progress may be reported.

## Inventory the promises

For each outgoing message, response, or reported index, write down:

1. **What it promises.** "I have stored entries up to i." "I am a candidate in term t and voted for myself." "Entries up to i are applied." "This read was confirmed by a quorum after it arrived."
2. **What must be true before it leaves.** Which writes must be durable, and which earlier work must have completed.
3. **Where the gate is.** Find the code that holds it back until then, and every path that bypasses that code.

Check every branch, not only the main one. Look at fast paths for "nothing new to write", retransmissions and duplicates, self-addressed messages, and the first message after a term change.

## Independent queues do not order each other

When work is split across threads or queues (for example, one for writes and one for applying), FIFO order within each queue says nothing about order between them. For any operation that replaces state another queue is still producing or consuming, ask what stops it from overtaking that queue. Then check that the condition it waits on is reported exactly: an index that counts work merely handed out, rather than work completed, silently disables the wait.

## Quorum evidence must be fresh

A count toward a quorum is valid only if each vote or acknowledgement was produced after the thing it is counted for. When a response of one kind is reused as evidence for something else, check when it could have been sent. A delayed or reordered message must never confirm a request that arrived after it was sent.

## Confirm with schedules

Every suspicion becomes a short script: the exact sequence of deliveries, crashes, and queue steps that turns the broken promise into a visible property violation. Discard suspicions no script can confirm. Keep each confirming script as a regression test. After each fix, rerun all of them, because several bugs often break one rule in different places.
