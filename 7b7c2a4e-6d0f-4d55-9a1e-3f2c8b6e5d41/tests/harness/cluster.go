package harness

import (
	"fmt"
	"math/rand"
	"strings"

	"google.golang.org/protobuf/proto"

	"go.etcd.io/raft/v3"
	"go.etcd.io/raft/v3/tracker"
	pb "go.etcd.io/raft/v3/raftpb"
)

type rec struct {
	idx, term uint64
	data      string
}

type node struct {
	id      uint64
	rn      *raft.RawNode
	d       *disk
	up      bool
	sm      []rec // the applied state machine; durable
	floor   uint64
	cs      *pb.ConfState
	appendQ []*pb.Message
	applyQ  []*pb.Message
	localQ  []*pb.Message
	pending *raft.Ready // loose ordering: a Ready whose messages left before its entries were written
}

// cluster is one simulated raft group driven step by step.
type cluster struct {
	p       profile
	rng     *rand.Rand
	nodes   []*node
	net     []*pb.Message
	group   []int
	global  map[uint64]rec
	leaders map[uint64]uint64
	reads   map[string]uint64
	viol    []string
	nextW   int
	nextR   int
	drained int
	loose   bool
}

func newCluster(p profile, seed int64) *cluster {
	c := &cluster{p: p, rng: rand.New(rand.NewSource(seed)), global: map[uint64]rec{}, leaders: map[uint64]uint64{}, reads: map[string]uint64{}}
	cs := &pb.ConfState{}
	for i := 1; i <= p.n; i++ {
		cs.Voters = append(cs.Voters, uint64(i))
	}
	c.group = make([]int, p.n)
	c.loose = readyOrder == "loose" && !p.async
	for i := 1; i <= p.n; i++ {
		n := &node{id: uint64(i), d: newDisk(cs)}
		c.nodes = append(c.nodes, n)
		c.start(n)
	}
	return c
}

func (c *cluster) violate(format string, a ...any) {
	if len(c.viol) < 8 {
		c.viol = append(c.viol, fmt.Sprintf(format, a...))
	}
}

func (c *cluster) config(n *node, applied uint64) *raft.Config {
	return &raft.Config{
		ID:                       n.id,
		ElectionTick:             1 << 20,
		HeartbeatTick:            1,
		Storage:                  n.d,
		Applied:                  applied,
		AsyncStorageWrites:       c.p.async,
		MaxSizePerMsg:            c.p.maxSize,
		MaxInflightMsgs:          c.p.inflight,
		MaxCommittedSizePerReady: 1 << 30,
		CheckQuorum:              c.p.checkQuorum,
		PreVote:                  c.p.preVote,
		ReadOnlyOption:           raft.ReadOnlySafe,
		Logger:                   discard{},
		StepDownOnRemoval:        true,
	}
}

func (c *cluster) start(n *node) {
	applied := uint64(0)
	if len(n.sm) > 0 {
		applied = n.sm[len(n.sm)-1].idx
	}
	if cm := n.d.hs.GetCommit(); applied > cm {
		applied = cm
	}
	if si := n.d.snap.GetMetadata().GetIndex(); applied < si {
		applied = si
	}
	rn, err := raft.NewRawNode(c.config(n, applied))
	if err != nil {
		panic(fmt.Sprintf("restart node %d: %v", n.id, err))
	}
	n.rn = rn
	n.up = true
	_, n.cs, _ = n.d.InitialState()
	n.floor = 0
	if len(n.sm) > 0 {
		n.floor = n.sm[len(n.sm)-1].idx
	}
}

func (c *cluster) crash(n *node) {
	n.up = false
	n.rn = nil
	n.appendQ, n.applyQ, n.localQ = nil, nil, nil
	n.pending = nil
}

func encodeSM(sm []rec) []byte {
	var b strings.Builder
	for _, r := range sm {
		fmt.Fprintf(&b, "%d:%d:%s;", r.idx, r.term, r.data)
	}
	return []byte(b.String())
}

func decodeSM(data []byte) []rec {
	var out []rec
	for _, part := range strings.Split(string(data), ";") {
		if part == "" {
			continue
		}
		var r rec
		f := strings.SplitN(part, ":", 3)
		if len(f) != 3 {
			continue
		}
		fmt.Sscan(f[0], &r.idx)
		fmt.Sscan(f[1], &r.term)
		r.data = f[2]
		out = append(out, r)
	}
	return out
}

// record checks that no two nodes apply different entries at one index.
func (c *cluster) record(n *node, r rec) {
	if g, ok := c.global[r.idx]; ok {
		if g != r {
			c.violate("state machine safety: node %d applied (index %d, term %d, %q), another node applied (term %d, %q)", n.id, r.idx, r.term, r.data, g.term, g.data)
		}
	} else {
		c.global[r.idx] = r
	}
}

func (n *node) applyConf(e *pb.Entry) {
	switch e.GetType() {
	case pb.EntryConfChange:
		cc := &pb.ConfChange{}
		_ = proto.Unmarshal(e.GetData(), cc)
		n.cs = n.rn.ApplyConfChange(cc)
	case pb.EntryConfChangeV2:
		cc := &pb.ConfChangeV2{}
		_ = proto.Unmarshal(e.GetData(), cc)
		n.cs = n.rn.ApplyConfChange(cc)
	}
}

func (c *cluster) applyEntry(n *node, e *pb.Entry) {
	r := rec{idx: e.GetIndex(), term: e.GetTerm(), data: string(e.GetData())}
	if e.GetType() != pb.EntryNormal {
		r.data = "cc"
	}
	n.applyConf(e)
	last := uint64(0)
	if len(n.sm) > 0 {
		last = n.sm[len(n.sm)-1].idx
	}
	if r.idx <= last {
		if r.idx <= n.floor {
			for _, x := range n.sm {
				if x.idx == r.idx && x != r {
					c.violate("state machine safety: node %d replayed index %d with a different entry after restart", n.id, r.idx)
				}
			}
			return
		}
		c.violate("applied once: node %d applied index %d again after applying up to %d", n.id, r.idx, last)
		return
	}
	if last != 0 && r.idx != last+1 {
		c.violate("applied in order: node %d applied index %d after %d", n.id, r.idx, last)
	}
	n.sm = append(n.sm, r)
	c.record(n, r)
}

func (c *cluster) installSnap(n *node, snap *pb.Snapshot) {
	n.cs = proto.Clone(snap.GetMetadata().GetConfState()).(*pb.ConfState)
	si := snap.GetMetadata().GetIndex()
	last := uint64(0)
	if len(n.sm) > 0 {
		last = n.sm[len(n.sm)-1].idx
	}
	if si < last {
		c.violate("applied once: node %d installed a snapshot at %d behind applied index %d", n.id, si, last)
		return
	}
	sm := decodeSM(snap.GetData())
	for _, r := range sm {
		c.record(n, r)
	}
	n.sm = sm
	n.floor = 0
}

func (c *cluster) send(from *node, m *pb.Message) {
	switch m.GetTo() {
	case raft.LocalAppendThread:
		from.appendQ = append(from.appendQ, m)
	case raft.LocalApplyThread:
		from.applyQ = append(from.applyQ, m)
	case from.id:
		from.localQ = append(from.localQ, m)
	default:
		c.net = append(c.net, m)
	}
}

func (c *cluster) handleReady(n *node) {
	if !n.up {
		return
	}
	if n.pending != nil {
		c.finishReady(n)
		return
	}
	if !n.rn.HasReady() {
		return
	}
	rd := n.rn.Ready()
	if rd.SoftState != nil && rd.RaftState == raft.StateLeader {
		t := n.rn.BasicStatus().GetTerm()
		if l, ok := c.leaders[t]; ok && l != n.id {
			c.violate("election safety: nodes %d and %d both lead term %d", l, n.id, t)
		}
		c.leaders[t] = n.id
	}
	for _, rs := range rd.ReadStates {
		ctx := string(rs.RequestCtx)
		if w, ok := c.reads[ctx]; ok && rs.Index < w {
			c.violate("linearizable read: read %s at node %d answered index %d, but index %d was applied before it was issued", ctx, n.id, rs.Index, w)
		}
	}
	if c.p.async {
		for _, m := range rd.Messages {
			c.send(n, m)
		}
		return
	}
	if c.loose {
		// The ordering doc.go permits: messages leave once the HardState is
		// written, while this batch's entries are still being written.
		if rd.HardState != nil && !raft.IsEmptyHardState(rd.HardState) {
			n.d.setHardState(rd.HardState)
		}
		for _, m := range rd.Messages {
			c.send(n, m)
		}
		n.pending = &rd
		return
	}
	if !raft.IsEmptySnap(rd.Snapshot) {
		if err := n.d.applySnapshot(rd.Snapshot); err == nil {
			c.installSnap(n, rd.Snapshot)
		}
	}
	if err := n.d.append(rd.Entries); err != nil {
		c.violate("storage: node %d: %v", n.id, err)
	}
	if rd.HardState != nil && !raft.IsEmptyHardState(rd.HardState) {
		n.d.setHardState(rd.HardState)
	}
	for _, m := range rd.Messages {
		c.send(n, m)
	}
	for _, e := range rd.CommittedEntries {
		c.applyEntry(n, e)
	}
	n.rn.Advance(rd)
}

// finishReady completes a Ready under the loose ordering: write its snapshot
// and entries, apply its committed entries, and advance.
func (c *cluster) finishReady(n *node) {
	rd := *n.pending
	n.pending = nil
	if !raft.IsEmptySnap(rd.Snapshot) {
		if err := n.d.applySnapshot(rd.Snapshot); err == nil {
			c.installSnap(n, rd.Snapshot)
		}
	}
	if err := n.d.append(rd.Entries); err != nil {
		c.violate("storage: node %d: %v", n.id, err)
	}
	for _, e := range rd.CommittedEntries {
		c.applyEntry(n, e)
	}
	n.rn.Advance(rd)
}

func (c *cluster) appendThread(n *node) {
	if !n.up || len(n.appendQ) == 0 {
		return
	}
	m := n.appendQ[0]
	n.appendQ = n.appendQ[1:]
	if m.Term != nil || m.Vote != nil || m.Commit != nil {
		st := &pb.HardState{Term: new(m.GetTerm()), Vote: new(m.GetVote()), Commit: new(m.GetCommit())}
		if !raft.IsEmptyHardState(st) {
			n.d.setHardState(st)
		}
	}
	if snap := m.GetSnapshot(); snap != nil && !raft.IsEmptySnap(snap) {
		if err := n.d.applySnapshot(snap); err == nil {
			c.installSnap(n, snap)
		}
	}
	if err := n.d.append(m.GetEntries()); err != nil {
		c.violate("storage: node %d: %v", n.id, err)
	}
	for _, r := range m.GetResponses() {
		c.send(n, r)
	}
}

func (c *cluster) applyThread(n *node) {
	if !n.up || len(n.applyQ) == 0 {
		return
	}
	m := n.applyQ[0]
	n.applyQ = n.applyQ[1:]
	for _, e := range m.GetEntries() {
		c.applyEntry(n, e)
	}
	for _, r := range m.GetResponses() {
		c.send(n, r)
	}
}

func (c *cluster) local(n *node) {
	if !n.up || len(n.localQ) == 0 {
		return
	}
	m := n.localQ[0]
	n.localQ = n.localQ[1:]
	_ = n.rn.Step(m)
}

func (c *cluster) connected(a, b uint64) bool { return c.group[a-1] == c.group[b-1] }

func (c *cluster) deliverRandom() {
	if len(c.net) == 0 {
		return
	}
	i := 0
	if c.rng.Float64() < c.p.reorder {
		i = c.rng.Intn(len(c.net))
	}
	m := c.net[i]
	dup := c.rng.Float64() < c.p.dup
	if !dup {
		c.net = append(c.net[:i], c.net[i+1:]...)
	}
	if c.rng.Float64() < c.p.drop {
		return
	}
	to := c.nodes[m.GetTo()-1]
	if !to.up || !c.connected(m.GetFrom(), m.GetTo()) {
		return
	}
	if dup {
		m = proto.Clone(m).(*pb.Message)
	}
	_ = to.rn.Step(m)
}

func (c *cluster) propose(n *node) {
	if !n.up {
		return
	}
	c.nextW++
	_ = n.rn.Propose([]byte(fmt.Sprintf("w%d", c.nextW)))
}

func (c *cluster) maxApplied() uint64 {
	var m uint64
	for _, n := range c.nodes {
		if len(n.sm) > 0 && n.sm[len(n.sm)-1].idx > m {
			m = n.sm[len(n.sm)-1].idx
		}
	}
	return m
}

func (c *cluster) read(n *node) {
	if !n.up {
		return
	}
	c.nextR++
	ctx := fmt.Sprintf("r%d", c.nextR)
	c.reads[ctx] = c.maxApplied()
	n.rn.ReadIndex([]byte(ctx))
}

// compact snapshots a node's log at the highest index that is applied in its
// state machine, durably committed, and reported applied by raft.
func (c *cluster) compact(n *node) {
	if !n.up || len(n.sm) == 0 {
		return
	}
	last := n.sm[len(n.sm)-1].idx
	if cm := n.d.hs.GetCommit(); last > cm {
		last = cm
	}
	if a := n.rn.Status().Applied; last > a {
		last = a
	}
	if last <= n.d.offset()+1 {
		return
	}
	var upto []rec
	for _, r := range n.sm {
		if r.idx <= last {
			upto = append(upto, r)
		}
	}
	_ = n.d.compact(last, n.cs, encodeSM(upto))
}

func (c *cluster) partition() {
	for i := range c.group {
		c.group[i] = 0
		if c.rng.Float64() < 0.4 {
			c.group[i] = 1
		}
	}
}

func (c *cluster) step() {
	n := c.nodes[c.rng.Intn(len(c.nodes))]
	x := c.rng.Float64() * c.p.total()
	w := c.p.w
	switch {
	case x < sum(w[:1]):
		c.deliverRandom()
	case x < sum(w[:2]):
		c.handleReady(n)
	case x < sum(w[:3]):
		if n.up {
			n.rn.Tick()
		}
	case x < sum(w[:4]):
		if n.up {
			_ = n.rn.Campaign()
		}
	case x < sum(w[:5]):
		c.propose(n)
	case x < sum(w[:6]):
		c.read(n)
	case x < sum(w[:7]):
		if n.up {
			c.crash(n)
		} else {
			c.start(n)
		}
	case x < sum(w[:8]):
		c.partition()
	case x < sum(w[:9]):
		c.appendThread(n)
	case x < sum(w[:10]):
		c.applyThread(n)
	case x < sum(w[:11]):
		c.local(n)
	case x < sum(w[:12]):
		c.compact(n)
	case x < sum(w[:13]):
		if n.up {
			_ = n.rn.ForgetLeader()
		}
	}
}

func sum(a []float64) float64 {
	t := 0.0
	for _, v := range a {
		t += v
	}
	return t
}

// settle drains one node's Ready and storage threads.
func (c *cluster) settle(n *node) {
	for i := 0; i < 50 && n.up; i++ {
		busy := false
		if n.pending != nil || n.rn.HasReady() {
			c.handleReady(n)
			busy = true
		}
		for len(n.appendQ) > 0 {
			c.appendThread(n)
			busy = true
		}
		for len(n.applyQ) > 0 {
			c.applyThread(n)
			busy = true
		}
		for len(n.localQ) > 0 {
			c.local(n)
			busy = true
		}
		if !busy {
			return
		}
	}
}

// drain is the benign end phase: every node up and connected, FIFO delivery,
// every storage thread drained each round. It returns the round at which the
// final write is applied on every node, or 0 if it is not within maxRounds.
func (c *cluster) drain(maxRounds int) int {
	for _, n := range c.nodes {
		if !n.up {
			c.start(n)
		}
	}
	for i := range c.group {
		c.group[i] = 0
	}
	target := ""
	leaderless := make([]int, len(c.nodes))
	for round := 0; round < maxRounds; round++ {
		for _, n := range c.nodes {
			c.settle(n)
		}
		for len(c.net) > 0 {
			m := c.net[0]
			c.net = c.net[1:]
			_ = c.nodes[m.GetTo()-1].rn.Step(m)
		}
		for _, n := range c.nodes {
			c.settle(n)
		}
		lead := uint64(0)
		for _, n := range c.nodes {
			bs := n.rn.BasicStatus()
			if bs.RaftState == raft.StateLeader {
				lead = n.id
			}
			if bs.Lead == raft.None {
				leaderless[n.id-1]++
			} else {
				leaderless[n.id-1] = 0
			}
		}
		if round%4 == 3 {
			for k := 0; k < len(c.nodes); k++ {
				i := (round/4 + k) % len(c.nodes)
				if leaderless[i] >= 4 {
					_ = c.nodes[i].rn.Campaign()
					leaderless[i] = 0
					break
				}
			}
		}
		if lead == 0 {
			if round%8 == 7 {
				for _, n := range c.nodes {
					if n.rn.BasicStatus().RaftState == raft.StateFollower {
						_ = n.rn.ForgetLeader()
					}
				}
			}
			for _, n := range c.nodes {
				n.rn.Tick()
			}
			continue
		}
		leader := c.nodes[lead-1]
		leader.rn.WithProgress(func(id uint64, _ raft.ProgressType, pr tracker.Progress) {
			if pr.State == tracker.StateSnapshot {
				leader.rn.ReportSnapshot(id, raft.SnapshotFailure)
			}
		})
		if target == "" && round > 2 {
			target = "final"
			_ = leader.rn.Propose([]byte(target))
		}
		for _, n := range c.nodes {
			n.rn.Tick()
		}
		if target != "" {
			done := true
			for _, n := range c.nodes {
				found := false
				for _, r := range n.sm {
					if r.data == target {
						found = true
						break
					}
				}
				if !found {
					done = false
					break
				}
			}
			if done {
				return round + 1
			}
			if round%40 == 39 {
				_ = leader.rn.Propose([]byte(target))
			}
		}
	}
	return 0
}

type discard struct{}

func (discard) Debug(...any)              {}
func (discard) Debugf(string, ...any)     {}
func (discard) Error(...any)              {}
func (discard) Errorf(string, ...any)     {}
func (discard) Info(...any)               {}
func (discard) Infof(string, ...any)      {}
func (discard) Warning(...any)            {}
func (discard) Warningf(string, ...any)   {}
func (discard) Fatal(v ...any)            { panic(fmt.Sprint(v...)) }
func (discard) Fatalf(f string, v ...any) { panic(fmt.Sprintf(f, v...)) }
func (discard) Panic(v ...any)            { panic(fmt.Sprint(v...)) }
func (discard) Panicf(f string, v ...any) { panic(fmt.Sprintf(f, v...)) }
