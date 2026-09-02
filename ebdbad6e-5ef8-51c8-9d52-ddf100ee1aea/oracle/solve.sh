#!/bin/bash
# Reference solution. Converts every ledger row with the heat content published
# for that fuel, that consuming sector and that year, then writes
# /root/results.json.
set -euo pipefail
python3 /oracle/solve.py
test -s /root/results.json
