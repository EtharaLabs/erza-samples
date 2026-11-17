package harness

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
