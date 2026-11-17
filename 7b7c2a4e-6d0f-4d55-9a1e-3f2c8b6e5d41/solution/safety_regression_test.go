package raft_test

import "testing"

// runTemplate runs every instance of a scripted schedule and requires no
// safety violation and a final write applied on every node afterwards.
func runTemplate(t *testing.T, name string) {
	t.Helper()
	tp := templates[name]
	for i := 0; i < tp.instances(); i++ {
		c := tp.instance(i)
		if len(c.viol) == 0 && c.drain(860) == 0 {
			t.Fatalf("%s #%d: the final write was not applied on every node", name, i)
		}
		if len(c.viol) > 0 {
			t.Fatalf("%s #%d: %s", name, i, c.viol[0])
		}
	}
}

// Cause 1: a candidate's vote requests leave before its term and vote are durable.
func TestVoteDurableRegression(t *testing.T) { runTemplate(t, "candidate-crash") }

// Cause 3: a Ready with nothing to write releases responses before the write they depend on.
func TestEmptyReadyBarrierRegression(t *testing.T) { runTemplate(t, "retransmit-ack") }

// Cause 2: a snapshot overtakes committed entries still queued on the apply thread.
func TestSnapshotOrderRegression(t *testing.T) { runTemplate(t, "snapshot-during-apply") }

// Cause 4: an apply response marks batches still queued as applied.
func TestApplyBoundaryRegression(t *testing.T) { runTemplate(t, "snapshot-after-batch") }

// Cause 5: a delayed append response confirms a read at a deposed leader.
func TestStaleAckReadRegression(t *testing.T) {
	runTemplate(t, "stale-ack-read")
	runTemplate(t, "stale-ack-read-async")
}
