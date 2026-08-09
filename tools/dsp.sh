#!/bin/sh
# Turn DSP on or off in a running Pd that has tools/dsp-toggle.pd loaded.
#
#     ./tools/dsp.sh 0        # audio engine off
#     ./tools/dsp.sh 1        # audio engine on
#     HOST=192.168.1.15 ./tools/dsp.sh 0
#
# A Python socket send, and the reason is measured: see ref/device-os.md,
# macOS BSD netcat exits before the datagram is flushed at -w0, and -w1 was
# measured to fail too, while the port is bound and the patch is fine. It looks
# exactly like a dead receiver.
#
# ⚠️ WITH DSP OFF THE BEAT ROW FREEZES AND THE PATCH IS SILENT. c_clock is cut
# from a phasor, so the grid stops walking and the transport stops counting.
# Expected, not a fault. Turn it back on when the reading is taken.
set -eu

HOST=${HOST:-organelle.local}
PORT=${PORT:-9997}
STATE=${1:-}

case "$STATE" in
    0|1) ;;
    *) echo "usage: $0 0|1" >&2; exit 1 ;;
esac

python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b'dsp $STATE;\n', ('$HOST', $PORT))
" || { echo "dsp.sh: send failed -- is $HOST reachable?" >&2; exit 1; }
echo "dsp $STATE -> $HOST:$PORT"
