#!/bin/sh
# Phase 8's headless gate. No eyes, no hardware, no socket, ~12 s.
#
#   ./tools/phase8-assert.sh          run it, exit non-zero on any failure
#   ./tools/phase8-assert.sh -v       and show the detail behind every check
#
# Regenerates the driver first, because phase8-assert-drive.pd is an OUTPUT --
# edit phase8-assert-drive-gen.py, never the .pd.
#
# THE CHEAPEST OF THE THREE GATES. Phase 6 had to rewrite [midiout] in a scratch
# copy, because a built-in class has no side channel. Phase 7 pointed u_net at
# 127.0.0.1 and read datagrams. u_state writes a FILE, so this one just reads
# what landed on disk. "Cut It/" is never touched and nothing is rewritten.
#
# It works entirely inside /tmp/cut-it-phase8-gate, which it wipes between
# phases -- it never touches /sdcard/cut-it-state, and never the device.
set -eu

cd "$(dirname "$0")/.."

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
export PD

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD="; exit 2; }

for f in "Cut It/u_state.pd" "Cut It/u_store.pd"; do
    if [ ! -f "$f" ]; then
        echo "$f does not exist yet."
        echo "That is a real failure, not a skip: the gate is meant to be built"
        echo "BEFORE the abstraction, so its first run fails for a known reason."
        exit 2
    fi
done

python3 tools/phase8-assert-drive-gen.py tools/phase8-assert-drive.pd /tmp/cut-it-phase8-gate
exec python3 tools/phase8-assert.py "$@"
