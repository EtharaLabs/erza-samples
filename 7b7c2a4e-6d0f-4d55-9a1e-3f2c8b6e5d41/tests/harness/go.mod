module raftgrader

go 1.26

require (
	go.etcd.io/raft/v3 v3.0.0
	google.golang.org/protobuf v1.36.12
)

replace go.etcd.io/raft/v3 => ../../raft
