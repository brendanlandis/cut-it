#!/bin/sh
# Send GO to a bench running on the Organelle.
#
#     ./tools/go.sh              one GO
#     ./tools/go.sh -n 3         three, half a second apart
#     HOST=192.168.1.15 ./tools/go.sh
#
# WHY THIS EXISTS RATHER THAN A netcat ONE-LINER. The benches document
# `echo "go;" | nc -u -w0 organelle.local 9998`, and on macOS that silently does
# nothing: BSD nc with -w0 exits before the datagram is flushed, and -w1 was
# measured to fail here too. The port IS bound -- `netstat -lun` on the device
# shows udp 0.0.0.0:9998 -- so the failure is entirely on the sending side and
# looks exactly like a dead bench. Python's socket send is deterministic.
#
# The device cannot send to itself either: busybox here has no `nc` at all, so
# the "from an SSH window on the device" advice never worked. Run this from the
# Mac.
#
# GO IS THE ONLY WAY TO DRIVE A BENCH ON THE ORGANELLE. The encoder click drives
# it on the Mac only -- mother forwards encbut just to patches that have sent
# /enableEncoder, and nothing in Cut It ever does. See test/bench/bench-gen.py.
set -eu

HOST=${HOST:-organelle.local}
PORT=${PORT:-9998}
N=1
[ "${1:-}" = "-n" ] && N=$2

i=1
while [ "$i" -le "$N" ]; do
    python3 -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b'go;\n', ('$HOST', $PORT))
" || { echo "go.sh: send failed -- is $HOST reachable?" >&2; exit 1; }
    echo "GO -> $HOST:$PORT"
    [ "$i" -lt "$N" ] && sleep 0.5
    i=$((i + 1))
done
