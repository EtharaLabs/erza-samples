"""Stop Claude Code's Bun runtime from running a script the agent supplies.

Claude Code is one Bun binary. Bun reads the BUN_OPTIONS environment variable at startup, and
BUN_OPTIONS=--preload=<file> runs any JavaScript in it, including an ECMAScript RegExp that implements
section 22.2 in full (it matched 316 of the 317 hidden expected results). The only copy of the name
Bun reads is the entry in its runtime's table of environment variable names, between RES_OPTIONS and
BUN_TCC_OPTIONS; its first byte is set to NUL so no environment variable can match it. The copies
inside Claude Code's own JavaScript are left alone. Fails unless exactly one such entry is found.
Usage: python3 claude_no_preload.py <executable>
"""
import sys

path = sys.argv[1]
blob = bytearray(open(path, "rb").read())
marker = b"\0BUN_OPTIONS\0BUN_TCC_OPTIONS\0"
hits = []
start = 0
while (start := blob.find(marker, start)) >= 0:
    hits.append(start)
    start += 1
if len(hits) != 1:
    sys.exit(f"expected one BUN_OPTIONS entry in Bun's name table, found {len(hits)}")
blob[hits[0] + 1] = 0
open(path, "wb").write(blob)
print("BUN_OPTIONS disabled at offset", hits[0] + 1)
