package raft

import (
	"google.golang.org/protobuf/proto"
	"testing"

	"github.com/stretchr/testify/require"
	pb "go.etcd.io/raft/v3/raftpb"
)

func regressionNode(t *testing.T, id uint64, async, prevote, check bool, s *MemoryStorage) *RawNode {
	t.Helper()
	c := newTestConfig(id, 10, 1, s)
	c.AsyncStorageWrites, c.PreVote, c.CheckQuorum, c.StepDownOnRemoval = async, prevote, check, true
	n, err := NewRawNode(c)
	require.NoError(t, err)
	return n
}

func regressionPersist(t *testing.T, s *MemoryStorage, rd Ready) {
	t.Helper()
	if !IsEmptySnap(rd.Snapshot) {
		require.NoError(t, s.ApplySnapshot(rd.Snapshot))
	}
	require.NoError(t, s.Append(rd.Entries))
	if !IsEmptyHardState(rd.HardState) {
		require.NoError(t, s.SetHardState(rd.HardState))
	}
}

func regressionSync(t *testing.T, n *RawNode, s *MemoryStorage) (msgs []*pb.Message, applied []*pb.Entry) {
	t.Helper()
	for i := 0; n.HasReady(); i++ {
		require.Less(t, i, 30)
		rd := n.Ready()
		regressionPersist(t, s, rd)
		msgs = append(msgs, rd.Messages...)
		applied = append(applied, rd.CommittedEntries...)
		n.Advance(rd)
	}
	return
}

func regressionStorage(t *testing.T, n *RawNode, s *MemoryStorage, m *pb.Message) (remote []*pb.Message) {
	t.Helper()
	require.Equal(t, pb.MsgStorageAppend, m.GetType())
	regressionPersist(t, s, Ready{Entries: m.GetEntries(), Snapshot: m.GetSnapshot(), HardState: &pb.HardState{Term: m.Term, Vote: m.Vote, Commit: m.Commit}})
	for _, r := range m.GetResponses() {
		if r.GetTo() == n.raft.id {
			require.NoError(t, n.Step(r))
		} else {
			remote = append(remote, r)
		}
	}
	return
}

func regressionFind(ms []*pb.Message, typ pb.MessageType, to uint64) *pb.Message {
	for _, m := range ms {
		if m.GetType() == typ && m.GetTo() == to {
			return m
		}
	}
	return nil
}

// A repeated grant must wait behind the first, still unprocessed vote write.
// Otherwise two candidates each collect a majority in term 1 across a crash.
func TestRegressionDuplicateVoteAcrossCrash(t *testing.T) {
	for _, check := range []bool{false, true} {
		t.Run(map[bool]string{false: "plain", true: "quorum"}[check], func(t *testing.T) {
			s := newTestMemoryStorage(withPeers(1, 2, 3))
			voter := regressionNode(t, 1, true, false, check, s)
			sa, sb := newTestMemoryStorage(withPeers(1, 2, 3)), newTestMemoryStorage(withPeers(1, 2, 3))
			a, b := regressionNode(t, 2, false, false, check, sa), regressionNode(t, 3, false, false, check, sb)
			require.NoError(t, a.Campaign())
			am, _ := regressionSync(t, a, sa)
			require.NoError(t, b.Campaign())
			bm, _ := regressionSync(t, b, sb)
			av, bv := regressionFind(am, pb.MsgVote, 1), regressionFind(bm, pb.MsgVote, 1)
			require.NotNil(t, av)
			require.NotNil(t, bv)
			require.NoError(t, voter.Step(av))
			_ = voter.Ready() // append thread is paused
			require.NoError(t, voter.Step(av))
			rd := voter.Ready()
			for _, m := range rd.Messages {
				if m.GetTo() == 2 {
					require.NoError(t, a.Step(m))
				}
			}
			regressionSync(t, a, sa)
			// Crash: discard every unprocessed local storage message.
			voter = regressionNode(t, 1, true, false, check, s)
			require.NoError(t, voter.Step(bv))
			rd = voter.Ready()
			for _, m := range rd.Messages {
				if m.GetType() == pb.MsgStorageAppend {
					for _, r := range regressionStorage(t, voter, s, m) {
						require.NoError(t, b.Step(r))
					}
				}
			}
			regressionSync(t, b, sb)
			require.False(t, a.raft.state == StateLeader && b.raft.state == StateLeader, "two leaders in term 1")
		})
	}
}

func TestRegressionDuplicateAppendDurability(t *testing.T) {
	s := newTestMemoryStorage(withPeers(1, 2, 3))
	n := regressionNode(t, 1, true, false, false, s)
	m := &pb.Message{Type: pb.MsgApp.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(1)), Entries: []*pb.Entry{{Index: new(uint64(1)), Term: new(uint64(1)), Data: []byte("x")}}}
	require.NoError(t, n.Step(m))
	first := n.Ready()
	require.NoError(t, n.Step(m))
	second := n.Ready()
	require.Nil(t, regressionFind(second.Messages, pb.MsgAppResp, 2), "acknowledged an entry whose append thread is paused")
	// Both responses eventually emerge, in order, after the durable write.
	var responses []*pb.Message
	for _, rd := range []Ready{first, second} {
		for _, msg := range rd.Messages {
			if msg.GetType() == pb.MsgStorageAppend {
				responses = append(responses, regressionStorage(t, n, s, msg)...)
			}
		}
	}
	require.Len(t, responses, 2)
	last, err := s.LastIndex()
	require.NoError(t, err)
	require.Equal(t, uint64(1), last)
}

func TestRegressionAsyncSingletonPreVote(t *testing.T) {
	s := newTestMemoryStorage(withPeers(1))
	n := regressionNode(t, 1, true, true, true, s)
	require.NoError(t, n.Campaign())
	for i := 0; n.HasReady() && i < 20; i++ {
		rd := n.Ready()
		for _, m := range rd.Messages {
			if m.GetType() == pb.MsgStorageAppend {
				regressionStorage(t, n, s, m)
			} else if m.GetType() == pb.MsgStorageApply {
				for _, r := range m.GetResponses() {
					require.NoError(t, n.Step(r))
				}
			}
		}
	}
	require.Equal(t, StateLeader, n.raft.state)
	require.NoError(t, n.Propose([]byte("live")))
	for i := 0; n.HasReady() && i < 20; i++ {
		rd := n.Ready()
		for _, m := range rd.Messages {
			if m.GetType() == pb.MsgStorageAppend {
				regressionStorage(t, n, s, m)
			} else if m.GetType() == pb.MsgStorageApply {
				for _, r := range m.GetResponses() {
					require.NoError(t, n.Step(r))
				}
			}
		}
	}
	require.Equal(t, uint64(2), n.raft.raftLog.applied)
}

func regressionApplyBacklog(t *testing.T, conf bool) (*RawNode, *MemoryStorage, []*pb.Message) {
	t.Helper()
	s := newTestMemoryStorage(withPeers(1, 2, 3))
	n := regressionNode(t, 1, true, false, false, s)
	var apply []*pb.Message
	for i := uint64(1); i <= 2; i++ {
		m := &pb.Message{Type: pb.MsgApp.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(1)), Index: new(i - 1), Commit: new(i), Entries: []*pb.Entry{{Index: new(i), Term: new(uint64(1)), Data: []byte{byte(i)}}}}
		if i > 1 {
			m.LogTerm = new(uint64(1))
		}
		if conf && i == 2 {
			m.Entries[0].Type = pb.EntryConfChange.Enum()
			data, err := proto.Marshal(&pb.ConfChange{Type: pb.ConfChangeAddNode.Enum(), NodeId: new(uint64(4))})
			require.NoError(t, err)
			m.Entries[0].Data = data
		}
		require.NoError(t, n.Step(m))
		for j := 0; n.HasReady(); j++ {
			require.Less(t, j, 10)
			rd := n.Ready()
			for _, msg := range rd.Messages {
				if msg.GetType() == pb.MsgStorageAppend {
					regressionStorage(t, n, s, msg)
				} else if msg.GetType() == pb.MsgStorageApply {
					apply = append(apply, msg)
				}
			}
		}
	}
	require.Len(t, apply, 2)
	return n, s, apply
}

func TestRegressionApplyResponseOnlyAcknowledgesItsBatch(t *testing.T) {
	n, _, apply := regressionApplyBacklog(t, false)
	require.NoError(t, n.Step(apply[0].GetResponses()[0]))
	require.Equal(t, uint64(1), n.raft.raftLog.applied, "second batch has not run")
	require.NoError(t, n.Step(apply[1].GetResponses()[0]))
	require.Equal(t, uint64(2), n.raft.raftLog.applied)
}

func TestRegressionSnapshotWaitsForApply(t *testing.T) {
	n, s, apply := regressionApplyBacklog(t, false)
	snap := &pb.Snapshot{Metadata: &pb.SnapshotMetadata{Index: new(uint64(3)), Term: new(uint64(1)), ConfState: &pb.ConfState{Voters: []uint64{1, 2, 3}}}}
	require.NoError(t, n.Step(&pb.Message{Type: pb.MsgSnap.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(1)), Snapshot: snap}))
	var order []uint64
	install := func() {
		if !n.HasReady() {
			return
		}
		rd := n.Ready()
		for _, m := range rd.Messages {
			if m.GetType() == pb.MsgStorageAppend {
				if !IsEmptySnap(m.GetSnapshot()) {
					order = append(order, m.GetSnapshot().GetMetadata().GetIndex())
				}
				regressionStorage(t, n, s, m)
			}
		}
	}
	// Run the append thread first whenever work is available. Snapshot
	// installation counts as applying all indexes through 3.
	install()
	for _, m := range apply {
		for _, e := range m.GetEntries() {
			order = append(order, e.GetIndex())
		}
		require.NoError(t, n.Step(m.GetResponses()[0]))
		install()
	}
	require.Equal(t, []uint64{1, 2, 3}, order, "snapshot must follow all older entry application")
	require.Equal(t, uint64(3), n.raft.raftLog.applied)
}

func TestRegressionSnapshotConfigurationAfterQueuedConfChange(t *testing.T) {
	s := newTestMemoryStorage(withPeers(1, 2))
	n := regressionNode(t, 1, true, false, false, s)
	cc := &pb.ConfChange{Type: pb.ConfChangeAddNode.Enum(), NodeId: new(uint64(3))}
	data, err := proto.Marshal(cc)
	require.NoError(t, err)
	require.NoError(t, n.Step(&pb.Message{Type: pb.MsgApp.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(1)), Commit: new(uint64(1)), Entries: []*pb.Entry{{Index: new(uint64(1)), Term: new(uint64(1)), Type: pb.EntryConfChange.Enum(), Data: data}}}))
	rd := n.Ready()
	for _, m := range rd.Messages {
		if m.GetType() == pb.MsgStorageAppend {
			regressionStorage(t, n, s, m)
		}
	}
	rd = n.Ready()
	ap := regressionFind(rd.Messages, pb.MsgStorageApply, LocalApplyThread)
	require.NotNil(t, ap)
	// The leader has since removed 3; this snapshot includes both changes.
	snap := &pb.Snapshot{Metadata: &pb.SnapshotMetadata{Index: new(uint64(2)), Term: new(uint64(1)), ConfState: &pb.ConfState{Voters: []uint64{1, 2}}}}
	require.NoError(t, n.Step(&pb.Message{Type: pb.MsgSnap.Enum(), From: new(uint64(2)), To: new(uint64(1)), Term: new(uint64(1)), Snapshot: snap}))
	// Older application finishes after snapshot receipt.
	n.ApplyConfChange(cc)
	require.NoError(t, n.Step(ap.GetResponses()[0]))
	if n.HasReady() {
		rd = n.Ready()
		for _, m := range rd.Messages {
			if m.GetType() == pb.MsgStorageAppend {
				regressionStorage(t, n, s, m)
			}
		}
	}
	require.Equal(t, []uint64{1, 2}, n.raft.trk.VoterNodes())
}

func TestRegressionCampaignWaitsForQueuedConfiguration(t *testing.T) {
	n, _, apply := regressionApplyBacklog(t, true)
	require.NoError(t, n.Step(apply[0].GetResponses()[0]))
	// The add-node entry is dispatched, but the apply thread has not run it.
	require.NoError(t, n.Campaign())
	require.Equal(t, StateFollower, n.raft.state, "campaigned with an unapplied committed configuration")
}

// Drive a connected pair while dropping messages to the third node. Storage
// work runs to completion, including self-directed responses.
func regressionPair(t *testing.T, leader, follower *RawNode, ls, fs *MemoryStorage) (applied []*pb.Entry) {
	t.Helper()
	var queue []*pb.Message
	for i := 0; i < 100; i++ {
		progress := false
		if leader.HasReady() {
			ms, es := regressionSync(t, leader, ls)
			queue = append(queue, ms...)
			applied = append(applied, es...)
			progress = true
		}
		if follower.HasReady() {
			progress = true
			rd := follower.Ready()
			for _, m := range rd.Messages {
				switch m.GetType() {
				case pb.MsgStorageAppend:
					queue = append(queue, regressionStorage(t, follower, fs, m)...)
				case pb.MsgStorageApply:
					for _, r := range m.GetResponses() {
						require.NoError(t, follower.Step(r))
					}
				default:
					queue = append(queue, m)
				}
			}
		}
		ms := queue
		queue = nil
		for _, m := range ms {
			if m.GetTo() == leader.raft.id {
				require.NoError(t, leader.Step(m))
				progress = true
			} else if m.GetTo() == follower.raft.id {
				require.NoError(t, follower.Step(m))
				progress = true
			}
		}
		if !progress {
			return
		}
	}
	t.Fatal("pair failed to quiesce")
	return
}

func TestRegressionSplitLeadersApplyAndRead(t *testing.T) {
	fs, as, bs := newTestMemoryStorage(withPeers(1, 2, 3)), newTestMemoryStorage(withPeers(1, 2, 3)), newTestMemoryStorage(withPeers(1, 2, 3))
	f := regressionNode(t, 1, true, false, false, fs)
	a, b := regressionNode(t, 2, false, false, false, as), regressionNode(t, 3, false, false, false, bs)
	require.NoError(t, a.Campaign())
	am, _ := regressionSync(t, a, as)
	require.NoError(t, b.Campaign())
	bm, _ := regressionSync(t, b, bs)
	av, bv := regressionFind(am, pb.MsgVote, 1), regressionFind(bm, pb.MsgVote, 1)
	require.NotNil(t, av)
	require.NotNil(t, bv)
	require.NoError(t, f.Step(av))
	_ = f.Ready()
	require.NoError(t, f.Step(av))
	rd := f.Ready()
	for _, m := range rd.Messages {
		if m.GetTo() == 2 {
			require.NoError(t, a.Step(m))
		}
	}
	regressionSync(t, a, as)
	f = regressionNode(t, 1, true, false, false, fs) // crash before either append write
	require.NoError(t, f.Step(bv))
	rd = f.Ready()
	for _, m := range rd.Messages {
		if m.GetType() == pb.MsgStorageAppend {
			for _, r := range regressionStorage(t, f, fs, m) {
				require.NoError(t, b.Step(r))
			}
		}
	}
	// B commits and applies Y at index 2 with F, while A is partitioned.
	regressionPair(t, b, f, bs, fs)
	require.NoError(t, b.Propose([]byte("Y")))
	appliedB := regressionPair(t, b, f, bs, fs)
	require.NotEmpty(t, appliedB)
	// A's same-term append is acknowledged at F's committed index, despite
	// having different data. On the repair A remains a candidate.
	err := a.Propose([]byte("X"))
	if err == ErrProposalDropped {
		require.NotEqual(t, StateLeader, a.raft.state)
		return
	}
	require.NoError(t, err)
	require.NoError(t, a.raft.Step(&pb.Message{Type: pb.MsgBeat.Enum()}))
	appliedA := regressionPair(t, a, f, as, fs)
	var x, y *pb.Entry
	for _, e := range appliedA {
		if string(e.GetData()) == "X" {
			x = e
		}
	}
	for _, e := range appliedB {
		if string(e.GetData()) == "Y" {
			y = e
		}
	}
	conflict := x != nil && y != nil && x.GetIndex() == y.GetIndex()
	// B advances once more. A still answers a safe ReadIndex with its stale
	// index using a heartbeat quorum {A,F}; isolate append traffic for the read.
	require.NoError(t, b.Propose([]byte("Z")))
	later := regressionPair(t, b, f, bs, fs)
	require.NotEmpty(t, later)
	high := later[len(later)-1].GetIndex()
	a.ReadIndex([]byte("after-Z"))
	rd = a.Ready()
	regressionPersist(t, as, rd)
	for _, m := range rd.Messages {
		if m.GetType() == pb.MsgHeartbeat && m.GetTo() == 1 {
			require.NoError(t, f.Step(m))
		}
	}
	a.Advance(rd)
	for f.HasReady() {
		fr := f.Ready()
		for _, m := range fr.Messages {
			if m.GetType() == pb.MsgHeartbeatResp && m.GetTo() == 2 {
				require.NoError(t, a.Step(m))
			} else if m.GetType() == pb.MsgStorageAppend {
				for _, r := range regressionStorage(t, f, fs, m) {
					if r.GetType() == pb.MsgHeartbeatResp && r.GetTo() == 2 {
						require.NoError(t, a.Step(r))
					}
				}
			}
		}
	}
	rd = a.Ready()
	regressionPersist(t, as, rd)
	a.Advance(rd)
	stale := false
	for _, rs := range rd.ReadStates {
		if rs.Index < high {
			stale = true
		}
	}
	require.False(t, conflict || stale, "different entries applied at one index: %v; stale ReadState: %v", conflict, stale)
}
