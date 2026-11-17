package raft_test

// A deterministic cluster simulator for the safety regression tests: one durable
// store per node, a controlled network, explicit append and apply threads with
// AsyncStorageWrites, and crashes that lose every unprocessed storage message.

import (
	"errors"
	"fmt"
	"math/rand"
	"strings"

	"google.golang.org/protobuf/proto"

	"go.etcd.io/raft/v3"
	pb "go.etcd.io/raft/v3/raftpb"
	"go.etcd.io/raft/v3/tracker"
)

// From the grader-independent simulator (storage.go).
// disk is the grader's own durable store; it survives crashes. It implements
// raft.Storage without touching the library's MemoryStorage.
type disk struct {
	hs   *pb.HardState
	snap *pb.Snapshot
	ents []*pb.Entry // ents[0] is a dummy at snap index
}

func newDisk(cs *pb.ConfState) *disk {
	s := pb.EnsureSnapshot(nil)
	s.Metadata.ConfState = proto.Clone(cs).(*pb.ConfState)
	s.Metadata.Index = new(uint64(0))
	s.Metadata.Term = new(uint64(0))
	return &disk{
		hs:   &pb.HardState{Term: new(uint64(0)), Vote: new(uint64(0)), Commit: new(uint64(0))},
		snap: s,
		ents: []*pb.Entry{{Index: new(uint64(0)), Term: new(uint64(0))}},
	}
}

func (d *disk) InitialState() (*pb.HardState, *pb.ConfState, error) {
	return proto.Clone(d.hs).(*pb.HardState), proto.Clone(d.snap.GetMetadata().GetConfState()).(*pb.ConfState), nil
}

func (d *disk) offset() uint64 { return d.ents[0].GetIndex() }

func (d *disk) FirstIndex() (uint64, error) { return d.offset() + 1, nil }
func (d *disk) LastIndex() (uint64, error)  { return d.offset() + uint64(len(d.ents)) - 1, nil }

func (d *disk) Term(i uint64) (uint64, error) {
	off := d.offset()
	if i < off {
		return 0, raft.ErrCompacted
	}
	if int(i-off) >= len(d.ents) {
		return 0, raft.ErrUnavailable
	}
	return d.ents[i-off].GetTerm(), nil
}

func (d *disk) Entries(lo, hi, maxSize uint64) ([]*pb.Entry, error) {
	off := d.offset()
	if lo <= off {
		return nil, raft.ErrCompacted
	}
	last, _ := d.LastIndex()
	if hi > last+1 {
		return nil, errors.New("entries hi out of bound")
	}
	var out []*pb.Entry
	var size uint64
	for i := lo; i < hi; i++ {
		e := proto.Clone(d.ents[i-off]).(*pb.Entry)
		size += uint64(proto.Size(e))
		if len(out) > 0 && size > maxSize {
			break
		}
		out = append(out, e)
	}
	return out, nil
}

func (d *disk) Snapshot() (*pb.Snapshot, error) { return proto.Clone(d.snap).(*pb.Snapshot), nil }

func (d *disk) setHardState(st *pb.HardState) { d.hs = proto.Clone(st).(*pb.HardState) }

func (d *disk) applySnapshot(s *pb.Snapshot) error {
	if s.GetMetadata().GetIndex() <= d.snap.GetMetadata().GetIndex() {
		return raft.ErrSnapOutOfDate
	}
	d.snap = proto.Clone(s).(*pb.Snapshot)
	d.ents = []*pb.Entry{{Index: new(s.GetMetadata().GetIndex()), Term: new(s.GetMetadata().GetTerm())}}
	return nil
}

func (d *disk) append(es []*pb.Entry) error {
	if len(es) == 0 {
		return nil
	}
	first, _ := d.FirstIndex()
	last := es[0].GetIndex() + uint64(len(es)) - 1
	if last < first {
		return nil
	}
	if first > es[0].GetIndex() {
		es = es[first-es[0].GetIndex():]
	}
	off := es[0].GetIndex() - d.offset()
	switch {
	case uint64(len(d.ents)) > off:
		d.ents = append([]*pb.Entry{}, d.ents[:off]...)
	case uint64(len(d.ents)) == off:
	default:
		return errors.New("missing log entry in append")
	}
	for _, e := range es {
		d.ents = append(d.ents, proto.Clone(e).(*pb.Entry))
	}
	return nil
}

// compact makes a snapshot at index i with the given state and drops the log
// up to i.
func (d *disk) compact(i uint64, cs *pb.ConfState, data []byte) error {
	off := d.offset()
	last, _ := d.LastIndex()
	if i <= off || i > last {
		return nil
	}
	t := d.ents[i-off].GetTerm()
	s := pb.EnsureSnapshot(nil)
	s.Metadata.Index = new(i)
	s.Metadata.Term = new(t)
	s.Metadata.ConfState = proto.Clone(cs).(*pb.ConfState)
	s.Data = append([]byte{}, data...)
	d.snap = s
	d.ents = append([]*pb.Entry{{Index: new(i), Term: new(t)}}, d.ents[i-off+1:]...)
	return nil
}

// From the grader-independent simulator (cluster.go).
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

// From the grader-independent simulator (profiles.go).
// Weights, in order: deliver, ready, tick, campaign, propose, read,
// crash or restart, partition, append thread, apply thread, local response,
// compact, forget leader.
type profile struct {
	n                    int
	async                bool
	preVote, checkQuorum bool
	maxSize              uint64
	inflight             int
	reorder, dup, drop   float64
	w                    [13]float64
}

func (p profile) total() float64 { return sum(p.w[:]) }

// readyOrder selects the default-mode application ordering: "" writes each
// Ready's entries before sending its messages; "loose" sends them once the
// HardState is written. Read from READY_ORDER; graded runs leave it empty.
var readyOrder string

var profiles = map[string]profile{
	"repl":       {n: 3, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 2, 8, 0, 1, 1, 0, 0, 0, 0, 0}},
	"repl5":      {n: 5, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 3, 8, 0, 1.5, 1, 0, 0, 0, 0, 0}},
	"reads":      {n: 3, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 2, 6, 6, 1, 1, 0, 0, 0, 0, 0}},
	"reads5":     {n: 5, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 3, 6, 6, 1.5, 1.5, 0, 0, 0, 0, 0}},
	"snap":       {n: 3, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.1, w: [13]float64{40, 25, 6, 2, 8, 0, 1, 1, 0, 0, 0, 3, 0}},
	"prevote":    {n: 5, preVote: true, checkQuorum: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 3, 8, 3, 1.5, 1, 0, 0, 0, 0, 2}},
	"async":      {n: 3, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 2, 8, 2, 1, 1, 12, 12, 15, 0, 0}},
	"asynccrash": {n: 3, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 4, 4, 10, 0, 4, 1, 3, 6, 12, 0, 0}},
	"asyncslow":  {n: 3, async: true, maxSize: 64, inflight: 2, reorder: 0.3, dup: 0.1, drop: 0.05, w: [13]float64{40, 25, 12, 2, 8, 0, 3, 1, 2, 8, 15, 0, 0}},
	"async5":     {n: 5, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 3, 8, 2, 1.5, 1, 12, 12, 15, 0, 0}},
	"asyncsnap":  {n: 3, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.1, w: [13]float64{40, 25, 6, 2, 8, 0, 1, 1, 12, 12, 15, 3, 0}},
	"asyncsnap2": {n: 3, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.2, w: [13]float64{40, 25, 6, 2, 10, 0, 1, 2, 12, 2, 15, 8, 0}},
	"asyncreads": {n: 3, async: true, maxSize: 64, inflight: 4, reorder: 0.5, dup: 0.05, drop: 0.05, w: [13]float64{40, 25, 6, 2, 6, 6, 1.5, 1.5, 10, 10, 15, 0, 0}},
}

// A category is a fixed list of scripted templates and random families.
type category struct {
	templates []string
	random    []string
}

var categories = map[string]category{
	"CA":  {templates: []string{"candidate-crash", "retransmit-ack"}, random: []string{"async", "asynccrash", "asyncslow", "async5"}},
	"CB":  {templates: []string{"snapshot-during-apply", "snapshot-after-batch"}, random: []string{"asyncsnap", "asyncsnap2"}},
	"CRA": {templates: []string{"stale-ack-read-async"}, random: []string{"asyncreads"}},
	"CR":  {templates: []string{"stale-ack-read"}, random: []string{"reads", "reads5"}},
	"CS":  {random: []string{"repl", "repl5", "snap", "prevote"}},
}

// From the grader-independent simulator (templates.go).
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
