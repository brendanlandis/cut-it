#!/bin/sh
# The phone link's headless gate -- ref/device/phone.md. No eyes, no phone, no
# hardware, ~25 s.
#
#   ./test/gate/phone-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/phone-assert.sh -v       and dump every decoded datagram
#
# Regenerates the driver first, because phone-assert-drive.pd is an OUTPUT --
# edit phone-assert-drive-gen.py, never the .pd.
#
# THE ORACLE IS A REAL SOCKET, so unlike the MIDI gates there is no scratch copy
# and nothing is rewritten. [midiout] is a built-in class with no side channel,
# so reading what the patch sent a device means swapping the object out in a
# throwaway copy; u_net already emits to a socket, so this gate simply points it
# at 127.0.0.1 and reads what arrives. "Cut It/" is never touched either way.
set -eu

cd "$(dirname "$0")/../.."

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
export PD

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD="; exit 2; }

if [ ! -f "Cut It/u_net.pd" ]; then
    echo "Cut It/u_net.pd does not exist yet."
    echo "That is a real failure, not a skip: the gate is meant to be built"
    echo "BEFORE the abstraction, so that its first run fails for a known reason."
    exit 2
fi

python3 test/gate/phone-assert-drive-gen.py
exec python3 test/gate/phone-assert.py "$@"
