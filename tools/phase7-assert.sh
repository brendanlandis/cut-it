#!/bin/sh
# Phase 7's headless gate. No eyes, no phone, no hardware, ~25 s.
#
#   ./tools/phase7-assert.sh          run it, exit non-zero on any failure
#   ./tools/phase7-assert.sh -v       and dump every decoded datagram
#
# Regenerates the driver first, because phase7-assert-drive.pd is an OUTPUT --
# edit phase7-assert-drive-gen.py, never the .pd.
#
# Unlike phase6-assert.sh there is no scratch copy and nothing is rewritten.
# [midiout] is a built-in class with no side channel, so Phase 6 had to swap it
# for a stand-in in a throwaway copy of the patch; u_net already emits to a
# socket, so the gate simply points it at 127.0.0.1 and reads what arrives.
# "Cut It/" is never touched either way.
set -eu

cd "$(dirname "$0")/.."

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
export PD

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD="; exit 2; }

if [ ! -f "Cut It/u_net.pd" ]; then
    echo "Cut It/u_net.pd does not exist yet."
    echo "That is a real failure, not a skip: the gate is meant to be built"
    echo "BEFORE the abstraction, so that its first run fails for a known reason."
    exit 2
fi

python3 tools/phase7-assert-drive-gen.py
exec python3 tools/phase7-assert.py "$@"
