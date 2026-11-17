package harness

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strconv"
	"testing"
	"testing/cryptotest"
)

type result struct {
	Nonce     string `json:"nonce"`
	Category  string `json:"category"`
	Family    string `json:"family"`
	Instance  int    `json:"instance"`
	Verdict   string `json:"verdict"`
	Violation string `json:"violation,omitempty"`
	Drain     int    `json:"drain_rounds"`
}

func envInt(name string, def int) int {
	if v, err := strconv.Atoi(os.Getenv(name)); err == nil && v > 0 {
		return v
	}
	return def
}

// readNonce reads the run's 32-character nonce from standard input, which the
// verifier opens on a root-owned file; a missing or short nonce fails.
func readNonce(t *testing.T) string {
	buf := make([]byte, 32)
	n, err := io.ReadFull(os.Stdin, buf)
	if err != nil || n != 32 {
		t.Fatalf("nonce: read %d bytes: %v", n, err)
	}
	return string(buf)
}

// run executes one schedule and its drain phase and returns its record.
func run(cat, family string, inst int, build func() *cluster, steps func(*cluster), bound int) (rec result) {
	rec = result{Category: cat, Family: family, Instance: inst, Verdict: "pass"}
	var c *cluster
	defer func() {
		if r := recover(); r != nil {
			rec.Verdict, rec.Violation = "fail", fmt.Sprintf("library panic: %v", r)
		}
	}()
	c = build()
	if steps != nil {
		func() {
			defer func() {
				if r := recover(); r != nil {
					c.violate("library panic: %v", r)
				}
			}()
			steps(c)
		}()
	}
	if len(c.viol) == 0 {
		rec.Drain = c.drain(bound)
		if len(c.viol) == 0 && rec.Drain == 0 {
			rec.Verdict, rec.Violation = "fail", fmt.Sprintf("progress floor: the final write was not applied on every node within %d drain rounds", bound)
		}
	}
	if len(c.viol) > 0 {
		rec.Verdict, rec.Violation = "fail", c.viol[0]
	}
	return rec
}

func TestCategory(t *testing.T) {
	cat := os.Getenv("CATEGORY")
	spec, ok := categories[cat]
	if !ok {
		t.Fatalf("unknown CATEGORY %q", cat)
	}
	seeds := envInt("SEEDS", 1000)
	steps := envInt("STEPS", 3000)
	bound := envInt("DRAIN_BOUND", 860)
	nonce := readNonce(t)
	readyOrder = os.Getenv("READY_ORDER")
	cryptotest.SetGlobalRandom(t, 20261103)
	// Records go to file descriptor 3, which the verifier opens on a root-owned file.
	out := os.NewFile(3, "results")
	if out == nil {
		t.Fatal("no result descriptor")
	}
	defer out.Close()
	enc := json.NewEncoder(out)
	fails := 0
	emit := func(r result) {
		r.Nonce = nonce
		if err := enc.Encode(r); err != nil {
			t.Fatalf("write result: %v", err)
		}
		if r.Verdict != "pass" {
			fails++
			if fails <= 5 {
				t.Errorf("%s %s #%d: %s", r.Category, r.Family, r.Instance, r.Violation)
			}
		}
	}
	for _, name := range spec.templates {
		tp := templates[name]
		for i := 0; i < tp.instances(); i++ {
			emit(run(cat, "template:"+name, i, func() *cluster { return tp.instance(i) }, nil, bound))
		}
	}
	for _, name := range spec.random {
		p := profiles[name]
		for sd := 1; sd <= seeds; sd++ {
			seed := int64(sd)
			emit(run(cat, "random:"+name, sd, func() *cluster { return newCluster(p, seed) }, func(c *cluster) {
				for i := 0; i < steps && len(c.viol) == 0; i++ {
					c.step()
				}
			}, bound))
		}
	}
}

