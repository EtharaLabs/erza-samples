package harness

import (
	"fmt"

	"google.golang.org/protobuf/proto"

	"go.etcd.io/raft/v3"
	pb "go.etcd.io/raft/v3/raftpb"
)

// A template is a scripted schedule. Each instance assigns the roles a, b, c
// to a permutation of the nodes of a three-node cluster and first commits
// `pre` writes under another leader, so the scripted part runs at varying
// terms, indexes, and node identities.
type template struct {
	name    string
	profile string
	run     func(c *cluster, a, b, cc *node)
}

var perms = [][3]int{{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}}

const preMax = 4

func (t template) instances() int { return len(perms) * preMax }

func (t template) instance(i int) *cluster {
	c := newCluster(profiles[t.profile], int64(i))
	perm := perms[i%len(perms)]
	pre := i / len(perms)
	a, b, cc := c.nodes[perm[0]], c.nodes[perm[1]], c.nodes[perm[2]]
	func() {
		defer func() {
			if r := recover(); r != nil {
				c.violate("library panic: %v", r)
			}
		}()
		if pre > 0 {
			_ = cc.rn.Campaign()
			c.stabilize()
			for k := 0; k < pre; k++ {
				_ = cc.rn.Propose([]byte(fmt.Sprintf("p%d", k)))
				c.stabilize()
			}
		}
		t.run(c, a, b, cc)
	}()
	return c
}

func (c *cluster) stabilize() {
	for round := 0; round < 100; round++ {
		for _, n := range c.nodes {
			c.settle(n)
		}
		if len(c.net) == 0 {
			return
		}
		net := c.net
		c.net = nil
		for _, m := range net {
			to := c.nodes[m.GetTo()-1]
			if to.up && c.connected(m.GetFrom(), m.GetTo()) {
				_ = to.rn.Step(m)
			}
		}
	}
}

// deliverTo steps every queued message of type t addressed to `to`; with keep
// a copy stays queued (a duplicate in flight).
func (c *cluster) deliverTo(t pb.MessageType, to *node, keep bool) int {
	k := 0
	var rest []*pb.Message
	for _, m := range c.net {
		if m.GetType() == t && m.GetTo() == to.id {
			if keep {
				rest = append(rest, m)
				m = proto.Clone(m).(*pb.Message)
			}
			if to.up {
				_ = to.rn.Step(m)
			}
			k++
			continue
		}
		rest = append(rest, m)
	}
	c.net = rest
	return k
}

func (c *cluster) dropTo(to *node) {
	var rest []*pb.Message
	for _, m := range c.net {
		if m.GetTo() != to.id {
			rest = append(rest, m)
		}
	}
	c.net = rest
}

func (c *cluster) hold(t pb.MessageType, to *node) []*pb.Message {
	var held, rest []*pb.Message
	for _, m := range c.net {
		if m.GetType() == t && m.GetTo() == to.id {
			held = append(held, m)
		} else {
			rest = append(rest, m)
		}
	}
	c.net = rest
	return held
}

func hasType(ms []*pb.Message, t pb.MessageType) bool {
	for _, m := range ms {
		if m.GetType() == t {
			return true
		}
	}
	return false
}

func (c *cluster) isolate(n *node) {
	for i := range c.group {
		c.group[i] = 0
	}
	c.group[n.id-1] = 1
}

func (c *cluster) heal() {
	for i := range c.group {
		c.group[i] = 0
	}
}

func (c *cluster) drainAppend(n *node) {
	for len(n.appendQ) > 0 {
		c.appendThread(n)
	}
	for len(n.localQ) > 0 {
		c.local(n)
	}
}

// candidateCrash: a candidate wins on its peers' votes, replicates to one
// follower while its own append thread stalls, crashes, and campaigns again.
func candidateCrash(c *cluster, a, b, cc *node) {
	_ = a.rn.Campaign()
	c.handleReady(a)
	c.deliverTo(pb.MsgVote, b, false)
	c.deliverTo(pb.MsgVote, cc, false)
	c.settle(b)
	c.settle(cc)
	c.deliverTo(pb.MsgVoteResp, a, false)
	c.handleReady(a)
	if a.rn.BasicStatus().RaftState != raft.StateLeader {
		c.appendThread(a)
		for len(a.localQ) > 0 {
			c.local(a)
		}
		c.handleReady(a)
	}
	c.handleReady(a)
	c.deliverTo(pb.MsgApp, b, false)
	c.settle(b)
	c.deliverTo(pb.MsgAppResp, a, false)
	c.handleReady(a)
	_ = a.rn.Propose([]byte("x"))
	c.handleReady(a)
	c.deliverTo(pb.MsgApp, b, false)
	c.settle(b)
	c.deliverTo(pb.MsgAppResp, a, false)
	c.handleReady(a)
	c.crash(a)
	c.net = nil
	c.start(a)
	_ = a.rn.Campaign()
	c.stabilize()
	if a.rn.BasicStatus().RaftState == raft.StateLeader {
		_ = a.rn.Propose([]byte("y"))
	}
	c.stabilize()
}

// retransmitAck: a follower answers a retransmitted append while the original
// entries are still in its append thread, then crashes.
func retransmitAck(c *cluster, a, b, cc *node) {
	_ = a.rn.Campaign()
	c.stabilize()
	if a.rn.BasicStatus().RaftState != raft.StateLeader {
		return
	}
	_ = a.rn.Propose([]byte("x"))
	c.settle(a)
	c.dropTo(cc)
	c.deliverTo(pb.MsgApp, b, true)
	c.handleReady(b)
	c.deliverTo(pb.MsgApp, b, false)
	c.handleReady(b)
	c.deliverTo(pb.MsgAppResp, a, false)
	c.settle(a)
	c.crash(b)
	c.start(b)
	c.isolate(a)
	c.net = nil
	_ = cc.rn.Campaign()
	c.stabilize()
	_ = cc.rn.Propose([]byte("y"))
	c.stabilize()
	c.heal()
	c.stabilize()
}

// snapshotDuringApply: a follower's apply thread holds committed entries in
// one or two batches when a snapshot covering them arrives.
func snapshotDuringApply(batches int, applyFirst bool) func(c *cluster, a, b, cc *node) {
	return func(c *cluster, a, b, cc *node) {
		_ = a.rn.Campaign()
		c.stabilize()
		if a.rn.BasicStatus().RaftState != raft.StateLeader {
			return
		}
		_ = a.rn.Propose([]byte("a"))
		c.stabilize()
		for k := 0; k < batches; k++ {
			_ = a.rn.Propose([]byte(fmt.Sprintf("b%d", k)))
			for i := 0; i < 4; i++ {
				c.settle(a)
				c.settle(cc)
				c.deliverTo(pb.MsgApp, cc, false)
				c.deliverTo(pb.MsgAppResp, a, false)
				c.deliverTo(pb.MsgApp, b, false)
				c.handleReady(b)
				c.drainAppend(b)
				c.handleReady(b)
				c.deliverTo(pb.MsgAppResp, a, false)
				c.deliverTo(pb.MsgHeartbeatResp, a, false)
				a.rn.Tick()
				c.settle(a)
				c.deliverTo(pb.MsgHeartbeat, b, false)
				c.deliverTo(pb.MsgHeartbeat, cc, false)
				c.handleReady(b)
			}
		}
		if applyFirst && len(b.applyQ) > 1 {
			c.applyThread(b)
			for len(b.localQ) > 0 {
				c.local(b)
			}
		}
		c.dropTo(b)
		for _, w := range []string{"d", "e"} {
			_ = a.rn.Propose([]byte(w))
			for i := 0; i < 4; i++ {
				c.settle(a)
				c.dropTo(b)
				c.deliverTo(pb.MsgApp, cc, false)
				c.settle(cc)
				c.deliverTo(pb.MsgAppResp, a, false)
			}
		}
		c.settle(a)
		c.compact(a)
		c.dropTo(b)
		a.rn.Tick()
		c.settle(a)
		c.deliverTo(pb.MsgHeartbeat, b, false)
		c.handleReady(b)
		c.deliverTo(pb.MsgHeartbeatResp, a, false)
		c.settle(a)
		for i := 0; i < 6 && !hasType(c.net, pb.MsgSnap); i++ {
			c.deliverTo(pb.MsgApp, b, false)
			c.handleReady(b)
			c.drainAppend(b)
			c.handleReady(b)
			c.deliverTo(pb.MsgAppResp, a, false)
			c.settle(a)
		}
		c.deliverTo(pb.MsgSnap, b, false)
		c.deliverTo(pb.MsgApp, b, false)
		c.handleReady(b)
		for len(b.appendQ) > 0 {
			c.appendThread(b)
		}
		for len(b.applyQ) > 0 {
			c.applyThread(b)
		}
		c.stabilize()
	}
}

// staleAckRead: an append acknowledgement delayed in the network reaches a
// deposed leader after a read arrives there.
func staleAckRead(c *cluster, a, b, cc *node) {
	_ = a.rn.Campaign()
	c.stabilize()
	if a.rn.BasicStatus().RaftState != raft.StateLeader {
		return
	}
	_ = a.rn.Propose([]byte("a"))
	c.stabilize()
	_ = a.rn.Propose([]byte("b"))
	c.settle(a)
	c.deliverTo(pb.MsgApp, b, false)
	c.settle(b)
	held := c.hold(pb.MsgAppResp, a)
	c.isolate(a)
	_ = b.rn.Campaign()
	c.stabilize()
	_ = b.rn.Propose([]byte("W"))
	c.stabilize()
	c.read(a)
	c.settle(a)
	for _, m := range held {
		_ = a.rn.Step(m)
	}
	c.settle(a)
	c.heal()
	c.stabilize()
}

var templates = map[string]template{
	"candidate-crash":         {name: "candidate-crash", profile: "async", run: candidateCrash},
	"retransmit-ack":          {name: "retransmit-ack", profile: "async", run: retransmitAck},
	"snapshot-during-apply":   {name: "snapshot-during-apply", profile: "asyncsnap", run: snapshotDuringApply(1, false)},
	"snapshot-after-batch":    {name: "snapshot-after-batch", profile: "asyncsnap", run: snapshotDuringApply(2, true)},
	"stale-ack-read":          {name: "stale-ack-read", profile: "reads", run: staleAckRead},
	"stale-ack-read-async":    {name: "stale-ack-read-async", profile: "async", run: staleAckRead},
}
