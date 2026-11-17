package raft

import (
	"fmt"
	"math/rand"
	"testing"

	"github.com/stretchr/testify/require"
	pb "go.etcd.io/raft/v3/raftpb"
	"google.golang.org/protobuf/proto"
)

// A deterministic driver. Storage contains only completed durable writes;
// taking Ready never completes either local thread. Local responses belong to
// an incarnation and are discarded on restart, unlike packets on the network.
type safetyNode struct {
	rn                         *RawNode
	disk                       *MemoryStorage
	appendQ, applyQ, responses []*pb.Message
	applied                    uint64
	async, preVote, check      bool
}
type safetySim struct {
	t       *testing.T
	nodes   []*safetyNode
	net     []*pb.Message
	leaders map[uint64]uint64
	entries map[uint64]string
	reads   map[string]uint64
	rng     *rand.Rand
}

func newSafetySim(t *testing.T, async, preVote, check bool) *safetySim {
	s := &safetySim{rng: rand.New(rand.NewSource(0)), t: t, nodes: make([]*safetyNode, 4), leaders: map[uint64]uint64{}, entries: map[uint64]string{}, reads: map[string]uint64{}}
	for id := uint64(1); id <= 3; id++ {
		d := NewMemoryStorage()
		require.NoError(t, d.ApplySnapshot(&pb.Snapshot{Metadata: &pb.SnapshotMetadata{Index: new(uint64(1)), Term: new(uint64(1)), ConfState: &pb.ConfState{Voters: []uint64{1, 2, 3}}}}))
		require.NoError(t, d.SetHardState(&pb.HardState{Term: new(uint64(1)), Commit: new(uint64(1))}))
		s.nodes[id] = &safetyNode{disk: d, applied: 1, async: async, preVote: preVote, check: check}
		s.start(id)
	}
	return s
}
func (s *safetySim) start(id uint64) {
	n := s.nodes[id]
	c := &Config{ID: id, ElectionTick: 10, HeartbeatTick: 1, Storage: n.disk, MaxSizePerMsg: 4096, MaxInflightMsgs: 256, AsyncStorageWrites: n.async, PreVote: n.preVote, CheckQuorum: n.check, StepDownOnRemoval: true, Logger: discardLogger}
	var err error
	n.rn, err = NewRawNode(c)
	require.NoError(s.t, err)
	snap, err := n.disk.Snapshot()
	require.NoError(s.t, err)
	n.applied = snap.GetMetadata().GetIndex()
	n.rn.raft.randomizedElectionTimeout = 10 + s.rng.Intn(10)
}
func (s *safetySim) crash(id uint64) {
	n := s.nodes[id]
	n.rn = nil
	n.appendQ = nil
	n.applyQ = nil
	n.responses = nil
	s.start(id)
}
func (s *safetySim) checkLeader(id uint64) {
	s.nodes[id].rn.raft.randomizedElectionTimeout = 10 + s.rng.Intn(10)
	b := s.nodes[id].rn.BasicStatus()
	if b.RaftState == StateLeader {
		old := s.leaders[b.GetTerm()]
		require.True(s.t, old == 0 || old == id, "two leaders in term %d: %d and %d", b.GetTerm(), old, id)
		s.leaders[b.GetTerm()] = id
	}
}
func (s *safetySim) apply(id uint64, ents []*pb.Entry) {
	n := s.nodes[id]
	for _, e := range ents {
		require.Equal(s.t, n.applied+1, e.GetIndex(), "node %d applies duplicate, gap, or reversal", id)
		value := fmt.Sprintf("%d/%d/%x", e.GetTerm(), e.GetType(), e.GetData())
		if old, ok := s.entries[e.GetIndex()]; ok {
			require.Equal(s.t, old, value, "conflicting application at %d", e.GetIndex())
		}
		s.entries[e.GetIndex()] = value
		n.applied = e.GetIndex()
	}
}
func (s *safetySim) snapshot(id uint64, snap *pb.Snapshot) {
	if IsEmptySnap(snap) {
		return
	}
	require.Greater(s.t, snap.GetMetadata().GetIndex(), s.nodes[id].applied, "snapshot repeats applied state")
	require.NoError(s.t, s.nodes[id].disk.ApplySnapshot(snap))
	s.nodes[id].applied = snap.GetMetadata().GetIndex()
}
func (s *safetySim) collect(id uint64) bool {
	n := s.nodes[id]
	if !n.rn.HasReady() {
		return false
	}
	rd := n.rn.Ready()
	for _, rs := range rd.ReadStates {
		require.GreaterOrEqual(s.t, rs.Index, s.reads[string(rs.RequestCtx)], "stale read %q", rs.RequestCtx)
	}
	if !n.async {
		s.snapshot(id, rd.Snapshot)
		require.NoError(s.t, n.disk.Append(rd.Entries))
		if !IsEmptyHardState(rd.HardState) {
			require.NoError(s.t, n.disk.SetHardState(rd.HardState))
		}
		s.apply(id, rd.CommittedEntries)
	}
	for _, m := range rd.Messages {
		m = proto.Clone(m).(*pb.Message)
		switch m.GetTo() {
		case LocalAppendThread:
			n.appendQ = append(n.appendQ, m)
		case LocalApplyThread:
			n.applyQ = append(n.applyQ, m)
		default:
			s.net = append(s.net, m)
		}
	}
	if !n.async {
		n.rn.Advance(rd)
	}
	s.checkLeader(id)
	return true
}
func (s *safetySim) thread(id uint64, appendThread bool) bool {
	n := s.nodes[id]
	q := &n.applyQ
	if appendThread {
		q = &n.appendQ
	}
	if len(*q) == 0 {
		return false
	}
	m := (*q)[0]
	*q = (*q)[1:]
	if appendThread {
		s.snapshot(id, m.GetSnapshot())
		require.NoError(s.t, n.disk.Append(m.GetEntries()))
		hs := &pb.HardState{Term: m.Term, Vote: m.Vote, Commit: m.Commit}
		if !IsEmptyHardState(hs) {
			require.NoError(s.t, n.disk.SetHardState(hs))
		}
	} else {
		s.apply(id, m.GetEntries())
	}
	for _, r := range m.GetResponses() {
		if r.GetTo() == id {
			n.responses = append(n.responses, r)
		} else {
			s.net = append(s.net, r)
		}
	}
	return true
}
func (s *safetySim) respond(id uint64) bool {
	n := s.nodes[id]
	if len(n.responses) == 0 {
		return false
	}
	m := n.responses[0]
	n.responses = n.responses[1:]
	require.NoError(s.t, n.rn.Step(m))
	s.checkLeader(id)
	return true
}
func (s *safetySim) deliver(m *pb.Message) {
	err := s.nodes[m.GetTo()].rn.Step(proto.Clone(m).(*pb.Message))
	if err != ErrProposalDropped {
		require.NoError(s.t, err)
	}
	s.checkLeader(m.GetTo())
	if m.GetType() == pb.MsgSnap {
		s.nodes[m.GetFrom()].rn.ReportSnapshot(m.GetTo(), SnapshotFinish)
	}
}
func (s *safetySim) take(from, to uint64, typ pb.MessageType) *pb.Message {
	for i, m := range s.net {
		if m.GetFrom() == from && m.GetTo() == to && m.GetType() == typ {
			s.net = append(s.net[:i], s.net[i+1:]...)
			return m
		}
	}
	return nil
}
func (s *safetySim) drain() {
	for k := 0; k < 10000; k++ {
		work := false
		for id := uint64(1); id <= 3; id++ {
			if s.collect(id) {
				work = true
			}
			if s.thread(id, true) {
				work = true
			}
			if s.thread(id, false) {
				work = true
			}
			if s.respond(id) {
				work = true
			}
		}
		if len(s.net) > 0 {
			m := s.net[0]
			s.net = s.net[1:]
			s.deliver(m)
			work = true
		}
		if !work {
			return
		}
	}
	s.t.Fatal("driver failed to quiesce")
}
func (s *safetySim) campaign(id uint64) {
	require.NoError(s.t, s.nodes[id].rn.Campaign())
	s.checkLeader(id)
}
func (s *safetySim) elect(id uint64) {
	s.campaign(id)
	s.drain()
	require.Equal(s.t, StateLeader, s.nodes[id].rn.BasicStatus().RaftState)
}
func (s *safetySim) read(id uint64, ctx string) {
	for _, n := range s.nodes[1:] {
		s.reads[ctx] = max(s.reads[ctx], n.applied)
	}
	s.nodes[id].rn.ReadIndex([]byte(ctx))
	s.collect(id)
}
func (s *safetySim) progress() {
	s.net = nil
	for id := uint64(1); id <= 3; id++ {
		s.crash(id)
	}
	s.drain()
	for round := 0; round < 300; round++ {
		for id := uint64(1); id <= 3; id++ {
			s.nodes[id].rn.Tick()
		}
		s.drain()
		if round < 100 {
			continue
		}
		for id := uint64(1); id <= 3; id++ {
			if s.nodes[id].rn.BasicStatus().RaftState == StateLeader {
				before := s.nodes[id].applied
				require.NoError(s.t, s.nodes[id].rn.Propose([]byte("recovery")))
				s.drain()
				for tick := 0; tick < 10; tick++ {
					for peer := uint64(1); peer <= 3; peer++ {
						s.nodes[peer].rn.Tick()
					}
					s.drain()
				}
				caughtUp := true
				for _, n := range s.nodes[1:] {
					if n.applied <= before || n.applied != s.nodes[id].applied {
						caughtUp = false
					}
				}
				if caughtUp {
					return
				}
				// A stale leader may step down when these packets arrive;
				// give the succeeding election time to finish before retrying.
				break
			}
		}
	}
	for id := uint64(1); id <= 3; id++ {
		s.t.Logf("node %d: %s status %+v queues %d/%d/%d", id, s.nodes[id].rn.raft.raftLog, s.nodes[id].rn.BasicStatus(), len(s.nodes[id].appendQ), len(s.nodes[id].applyQ), len(s.nodes[id].responses))
	}
	s.t.Fatal("no leader after recovery")
}

func TestAsyncDuplicateVoteDurabilityRegression(t *testing.T) {
	s := newSafetySim(t, true, false, false)
	s.campaign(1)
	s.collect(1)
	s.thread(1, true)
	for s.respond(1) {
	}
	s.collect(1)
	vote := s.take(1, 2, pb.MsgVote)
	require.NotNil(t, vote)
	s.deliver(vote)
	s.collect(2) // the vote write is now queued, not durable
	s.deliver(vote)
	s.collect(2) // duplicate must wait behind that write
	if escaped := s.take(2, 1, pb.MsgVoteResp); escaped != nil {
		s.deliver(escaped)
		s.collect(1)
	}
	s.crash(2)
	s.net = nil
	s.campaign(3)
	s.collect(3)
	s.thread(3, true)
	for s.respond(3) {
	}
	s.collect(3)
	v := s.take(3, 2, pb.MsgVote)
	require.NotNil(t, v)
	s.deliver(v)
	s.collect(2)
	s.thread(2, true)
	v = s.take(2, 3, pb.MsgVoteResp)
	require.NotNil(t, v)
	s.deliver(v)
	s.progress()
}

func TestAsyncDuplicateAppendDurabilityRegression(t *testing.T) {
	s := newSafetySim(t, true, false, false)
	s.elect(1)
	require.NoError(t, s.nodes[1].rn.Propose([]byte("lost")))
	s.collect(1)
	app := s.take(1, 2, pb.MsgApp)
	require.NotNil(t, app)
	s.deliver(app)
	s.collect(2)
	s.deliver(app)
	s.collect(2)
	// Node 1's local append is also not durable. Only an escaped duplicate
	// acknowledgement can let it commit and apply this proposal.
	s.thread(1, true)
	for s.respond(1) {
	}
	s.collect(1)
	if ack := s.take(2, 1, pb.MsgAppResp); ack != nil {
		s.deliver(ack)
		s.collect(1)
		for s.thread(1, true) {
		}
		for s.respond(1) {
		}
		s.collect(1)
		for s.thread(1, false) {
		}
		for s.respond(1) {
		}
	}
	// Lose the follower's queued write. The other majority can elect a
	// leader with no proposal at index 3, whose no-op conflicts with "lost".
	s.crash(2)
	s.net = nil
	s.campaign(3)
	s.majorityDrain()
	require.Equal(t, StateLeader, s.nodes[3].rn.BasicStatus().RaftState)
	s.progress()
}

func TestDelayedAppendCannotConfirmReadRegression(t *testing.T) {
	for _, async := range []bool{false, true} {
		t.Run(fmt.Sprint(async), func(t *testing.T) {
			s := newSafetySim(t, async, false, false)
			s.elect(1)
			// Capture a genuine response before the read exists.
			s.nodes[1].rn.Tick()
			s.collect(1)
			hb := s.take(1, 2, pb.MsgHeartbeat)
			require.NotNil(t, hb)
			s.deliver(hb)
			s.collect(2)
			// A proposal provides an append response from the old leader's term.
			require.NoError(t, s.nodes[1].rn.Propose([]byte("old")))
			s.collect(1)
			app := s.take(1, 2, pb.MsgApp)
			require.NotNil(t, app)
			s.deliver(app)
			s.collect(2)
			if async {
				s.thread(2, true)
			}
			ack := s.take(2, 1, pb.MsgAppResp)
			require.NotNil(t, ack)
			// Bring 3 up to date, without returning its acknowledgement to 1.
			app3 := proto.Clone(app).(*pb.Message)
			app3.To = new(uint64(3))
			s.deliver(app3)
			s.collect(3)
			if async {
				s.thread(3, true)
				for s.respond(3) {
				}
				s.collect(3)
			}
			// Isolate 1. The remaining majority elects 3 and applies newer entries.
			s.net = nil
			s.campaign(3)
			s.majorityDrain()
			require.Equal(t, StateLeader, s.nodes[3].rn.BasicStatus().RaftState)
			require.Greater(t, s.nodes[3].applied, s.nodes[1].applied)
			s.read(1, "after-new-leader")
			s.deliver(ack)
			s.collect(1)
			s.progress()
		})
	}
}

// Follower receives two committed batches, while its apply thread is delayed.
func pendingSafetyBatches(t *testing.T) *safetySim {
	s := newSafetySim(t, true, false, false)
	for i := uint64(2); i <= 3; i++ {
		s.deliver(&pb.Message{Type: pb.MsgApp.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(2)), Index: new(i - 1), LogTerm: new(uint64(1 + (i - 2))), Commit: new(i), Entries: []*pb.Entry{{Index: new(i), Term: new(uint64(2)), Data: []byte(fmt.Sprint(i))}}})
		s.collect(1)
		s.thread(1, true)
		for s.respond(1) {
		}
		s.collect(1)
	}
	require.Len(t, s.nodes[1].applyQ, 2)
	return s
}
func safetySnapshot() *pb.Message {
	return &pb.Message{Type: pb.MsgSnap.Enum(), From: new(uint64(3)), To: new(uint64(1)), Term: new(uint64(3)), Snapshot: &pb.Snapshot{Metadata: &pb.SnapshotMetadata{Index: new(uint64(5)), Term: new(uint64(3)), ConfState: &pb.ConfState{Voters: []uint64{1, 2, 3}}}}}
}
func TestApplyResponseTracksCompletedBatchRegression(t *testing.T) {
	s := pendingSafetyBatches(t)
	s.thread(1, false)
	s.respond(1)
	require.Equal(t, uint64(2), s.nodes[1].rn.BasicStatus().Applied, "first completion acknowledged the second pending batch")
}
func TestSnapshotWaitsForApplyThreadRegression(t *testing.T) {
	s := pendingSafetyBatches(t)
	s.deliver(safetySnapshot())
	s.collect(1)
	s.thread(1, true)
	for s.thread(1, false) {
	}
	for s.respond(1) {
	}
	s.deliver(safetySnapshot())
	s.collect(1)
	s.thread(1, true)
	for s.respond(1) {
	}
	require.Equal(t, uint64(5), s.nodes[1].applied)
}
func TestSnapshotWaitsForExactApplyCompletionRegression(t *testing.T) {
	s := pendingSafetyBatches(t)
	s.thread(1, false)
	s.respond(1)
	s.deliver(safetySnapshot())
	s.collect(1)
	s.thread(1, true)
	for s.thread(1, false) {
	}
	for s.respond(1) {
	}
	s.deliver(safetySnapshot())
	s.collect(1)
	s.thread(1, true)
	for s.respond(1) {
	}
	require.Equal(t, uint64(5), s.nodes[1].applied)
}

// The scripted failure above is also followed by seeded schedules across all
// mode combinations. Each choice is replayable; recovery verifies progress.
func TestAdversarialSchedulesRegression(t *testing.T) {
	for _, async := range []bool{false, true} {
		for _, pre := range []bool{false, true} {
			for _, check := range []bool{false, true} {
				for seed := int64(0); seed < 100; seed++ {
					t.Run(fmt.Sprintf("%t/%t/%t/%d", async, pre, check, seed), func(t *testing.T) {
						s := newSafetySim(t, async, pre, check)
						r := rand.New(rand.NewSource(seed))
						s.rng = r
						// Also cover peers with different election and storage options.
						for peer := uint64(2); peer <= 3; peer++ {
							n := s.nodes[peer]
							n.preVote = pre != (seed&(1<<(peer-2)) != 0)
							n.check = check != (seed&(1<<peer) != 0)
							n.async = async != (seed&(1<<(peer+2)) != 0)
							s.start(peer)
						}
						s.elect(1)
						for k := 0; k < 300; k++ {
							id := uint64(r.Intn(3) + 1)
							switch r.Intn(12) {
							case 0:
								s.campaign(id)
							case 1:
								s.crash(id)
							case 2:
								_ = s.nodes[id].rn.Propose([]byte(fmt.Sprintf("%d/%d", seed, k)))
							case 3:
								s.read(id, fmt.Sprintf("%d/%d", seed, k))
							case 4:
								s.thread(id, true)
							case 5:
								s.thread(id, false)
							case 6:
								s.respond(id)
							case 7:
								s.collect(id)
							default:
								if len(s.net) > 0 {
									i := r.Intn(len(s.net))
									m := s.net[i]
									if r.Intn(4) != 0 {
										s.net = append(s.net[:i], s.net[i+1:]...)
									}
									if r.Intn(5) != 0 {
										s.deliver(m)
									}
								}
							}
							s.collect(id)
						}
						s.progress()
					})
				}
			}
		}
	}
}

func (s *safetySim) majorityDrain() {
	for k := 0; k < 10000; k++ {
		work := false
		for _, id := range []uint64{2, 3} {
			if s.collect(id) {
				work = true
			}
			if s.thread(id, true) {
				work = true
			}
			if s.thread(id, false) {
				work = true
			}
			if s.respond(id) {
				work = true
			}
		}
		if len(s.net) > 0 {
			m := s.net[0]
			s.net = s.net[1:]
			if m.GetFrom() != 1 && m.GetTo() != 1 {
				s.deliver(m)
			}
			work = true
		}
		if !work {
			break
		}
	}
}

// Exercise compaction, a library-generated snapshot, rejection while an apply
// is outstanding, and eventual retry without restarting the lagging follower.
func TestCompactedSnapshotRetryRegression(t *testing.T) {
	s := newSafetySim(t, true, false, false)
	s.elect(1)
	sawSnapshot, stopSnapshot := false, false
	pump := func(excludeTwo bool) {
		for k := 0; k < 10000; k++ {
			work := false
			for id := uint64(1); id <= 3; id++ {
				if s.collect(id) {
					work = true
				}
				if s.thread(id, true) {
					work = true
				}
				if id != 2 {
					if s.thread(id, false) {
						work = true
					}
				}
				if s.respond(id) {
					work = true
				}
			}
			if len(s.net) > 0 {
				m := s.net[0]
				s.net = s.net[1:]
				if !excludeTwo || (m.GetFrom() != 2 && m.GetTo() != 2) {
					s.deliver(m)
					if stopSnapshot && m.GetType() == pb.MsgSnap {
						s.collect(m.GetTo())
						s.thread(m.GetTo(), true)
						sawSnapshot = true
						return
					}
				}
				work = true
			}
			if !work {
				return
			}
		}
		t.Fatal("snapshot schedule did not quiesce")
	}
	require.NoError(t, s.nodes[1].rn.Propose([]byte("pending")))
	pump(false)
	require.Len(t, s.nodes[2].applyQ, 1)
	require.NoError(t, s.nodes[1].rn.Propose([]byte("snapshot")))
	pump(true)
	leader := s.nodes[1]
	index := leader.applied
	_, err := leader.disk.CreateSnapshot(index, &pb.ConfState{Voters: []uint64{1, 2, 3}}, nil)
	require.NoError(t, err)
	require.NoError(t, leader.disk.Compact(index))
	// Unpause the peer and let sendAppend discover that it needs a snapshot.
	stopSnapshot = true
	leader.rn.ReportUnreachable(2)
	for k := 0; k < 30 && !sawSnapshot; k++ {
		leader.rn.Tick()
		pump(false)
	}
	require.True(t, sawSnapshot, "leader did not send a snapshot")

	for s.thread(2, false) {
	}
	for s.respond(2) {
	}
	for k := 0; k < 30; k++ {
		leader.rn.Tick()
		s.drain()
	}
	require.Equal(t, index, s.nodes[2].applied)
	require.NoError(t, leader.rn.Propose([]byte("after snapshot")))
	s.drain()
	for k := 0; k < 5; k++ {
		leader.rn.Tick()
		s.drain()
	}
	for _, n := range s.nodes[1:] {
		require.Equal(t, index+1, n.applied)
	}
}

func TestAsyncSingletonPreVoteProgressRegression(t *testing.T) {
	s := newSafetySim(t, true, true, true)
	d := NewMemoryStorage()
	require.NoError(t, d.ApplySnapshot(&pb.Snapshot{Metadata: &pb.SnapshotMetadata{Index: new(uint64(1)), Term: new(uint64(1)), ConfState: &pb.ConfState{Voters: []uint64{1}}}}))
	require.NoError(t, d.SetHardState(&pb.HardState{Term: new(uint64(1)), Commit: new(uint64(1))}))
	s.nodes[1].disk = d
	s.start(1)
	s.elect(1)
	require.NoError(t, s.nodes[1].rn.Propose([]byte("singleton")))
	s.drain()
	require.Equal(t, uint64(3), s.nodes[1].applied)
}

func TestMixedElectionOptionsCatchUpRegression(t *testing.T) {
	for _, async := range []bool{false, true} {
		t.Run(fmt.Sprint(async), func(t *testing.T) {
			s := newSafetySim(t, async, false, true)
			s.nodes[3].check = false
			s.start(3)
			s.elect(1)
			// Isolated node 3 raises its term without CheckQuorum or PreVote. Nodes
			// 1 and 2 keep hearing from the old leader and reject disruptive votes.
			s.campaign(3)
			s.collect(3)
			if async {
				s.thread(3, true)
				for s.respond(3) {
				}
				s.collect(3)
			}
			s.net = nil
			for tick := 0; tick < 60; tick++ {
				for id := uint64(1); id <= 3; id++ {
					s.nodes[id].rn.Tick()
				}
				s.drain()
			}
			leader := uint64(0)
			for id := uint64(1); id <= 3; id++ {
				if s.nodes[id].rn.BasicStatus().RaftState == StateLeader {
					leader = id
				}
			}
			require.NotZero(t, leader)
			require.NoError(t, s.nodes[leader].rn.Propose([]byte("healed")))
			s.drain()
			for tick := 0; tick < 10; tick++ {
				for id := uint64(1); id <= 3; id++ {
					s.nodes[id].rn.Tick()
				}
				s.drain()
			}
			for _, n := range s.nodes[1:] {
				require.Equal(t, s.nodes[leader].applied, n.applied, "healed peer cannot catch up with mixed election options")
			}
		})
	}
}
