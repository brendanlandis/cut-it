#!/bin/sh
# Turn DSP on or off in a running Pd that has tools/dsp-toggle.pd loaded.
#
#     ./tools/dsp.sh 0        # audio engine off
#     ./tools/dsp.sh 1        # audio engine on
#     HOST=192.168.1.15 ./tools/dsp.sh 0
#
# Python, not netcat, which sends nothing here (the Organelle's Reference page,
# Sending the device a UDP datagram). With DSP off the patch is silent and the
# clock stops: expected, not a fault (tools/README.md).
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
