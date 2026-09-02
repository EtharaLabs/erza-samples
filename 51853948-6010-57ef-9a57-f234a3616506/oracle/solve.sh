#!/bin/bash
set -e
# Reference solver: rates every gage height, averages each block, writes /root/results.json.
python3 /oracle/solve.py
