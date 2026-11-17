package harness

import (
	"errors"

	"google.golang.org/protobuf/proto"

	"go.etcd.io/raft/v3"
	pb "go.etcd.io/raft/v3/raftpb"
)

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
