#!/bin/bash
# Reference repair: restore the durable-append ordering of vote requests and of responses on a
# Ready with nothing to write, hold a snapshot until earlier entries are applied, advance the
# applied index per reported batch, confirm reads only by their own heartbeat round; add the
# regression tests and the report.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd /workspace/raft
git apply -p2 "$here/reference.diff"
cp "$here/sim_regression_test.go" "$here/safety_regression_test.go" /workspace/raft/
mkdir -p /workspace/output
cp "$here/REPAIR_REPORT.md" /workspace/output/REPAIR_REPORT.md
