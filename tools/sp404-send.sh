#!/bin/sh
# Fire notes at the SP-404 through a running tools/sp404-notes.pd.
#
#   ./tools/sp404-send.sh 48          note 48 on the current channel
#   ./tools/sp404-send.sh 48 2        set channel 2 first, then note 48
#   REPEAT=20 GAP=0.25 ./tools/sp404-send.sh 48    fire it 20 times, 4/sec
#
# WHY A SCRIPT AND NOT A MESSAGE BOX. The 404 has to be watched while the note
# is fired, and a message box needs a hand on the laptop at the same moment --
# the same reason the benches stopped driving themselves on a timer.
#
# ⚠️ FIRE FAST FOR A VISUAL TEST. With no audio connected a pad is judged by
# its LED, and a flash at 3-5 per second is far easier to catch than one blink
# every two seconds. That is what REPEAT and GAP are for.
#
# ⚠️ PYTHON'S SOCKET SEND, NOT NETCAT. On macOS `nc -u -w0` exits before the
# datagram is flushed and SILENTLY sends nothing -- measured on this project,
# and it looks exactly like a dead patch. tools/go.sh carries the same warning.
set -eu

NOTE=${1:?usage: sp404-send.sh <note> [channel]}
CHAN=${2:-}
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-9997}
REPEAT=${REPEAT:-1}
GAP=${GAP:-0.5}

python3 - "$NOTE" "$CHAN" "$HOST" "$PORT" "$REPEAT" "$GAP" <<'EOF'
import socket, sys, time
note, chan, host, port, repeat, gap = sys.argv[1:7]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
addr = (host, int(port))
if chan:
    # channel goes into noteout's right inlet and STAYS there, so it is set
    # once rather than with every note
    s.sendto(("chan %s;\n" % chan).encode(), addr)
    time.sleep(0.1)
    print("channel set to %s" % chan)
n = int(repeat)
for i in range(n):
    s.sendto(("note %s;\n" % note).encode(), addr)
    if i < n - 1:
        time.sleep(float(gap))
print("sent note %s x%d to %s:%s" % (note, n, host, port))
EOF
