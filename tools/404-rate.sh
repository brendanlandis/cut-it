#!/bin/sh
# Set the 404 rate-sweep driver's trigger interval, from the Mac.
#
#   ./tools/404-rate.sh 100     100 ms interval  = 10 triggers/sec
#   ./tools/404-rate.sh stop
#
# ⚠️ PYTHON'S SOCKET SEND, NOT NETCAT -- on macOS `nc -u -w0` exits before the
# datagram is flushed and silently sends nothing. tools/go.sh carries the same
# warning, and it looks exactly like a dead patch.
set -eu
A=${1:?usage: 404-rate.sh <interval-ms|stop|sweep [seconds]>}
HOST=${HOST:-organelle.local}
SECS=${2:-8}

# SWEEP: ramp the trigger rate EXPONENTIALLY from 4/s to 500/s and back.
# Exponential because pitch is logarithmic -- a linear ramp in interval spends
# almost all its time at the slow end and rushes the part worth hearing.
# ⚠️ 500/s is the useful ceiling: above it Pd's 64-sample scheduler tick means
# several events fall due in one block and are emitted together, so the stream
# gets ragged without getting faster. Measured, item 208.
if [ "$A" = "sweep" ]; then
  python3 - "$HOST" "$SECS" <<'PYS'
import socket, sys, time, math
host, secs = sys.argv[1], float(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
LO, HI, STEP = 4.0, 500.0, 0.025
def send(rate):
    s.sendto(("ms %.3f;\n" % (1000.0 / rate)).encode(), (host, 9995))
n = int(secs / STEP)
for direction in (1, -1):
    for i in range(n):
        f = i / float(n)
        if direction < 0:
            f = 1.0 - f
        send(LO * (HI / LO) ** f)
        time.sleep(STEP)
send(LO)
print("sweep complete: %g/s -> %g/s -> %g/s over %gs" % (LO, HI, LO, secs * 2))
PYS
  exit 0
fi
python3 - "$A" "$HOST" <<'PY'
import socket, sys
a, host = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg = "stop;\n" if a == "stop" else ("ms %s;\n" % a)
s.sendto(msg.encode(), (host, 9995))
if a != "stop":
    print("interval %s ms  ->  %.1f triggers/sec" % (a, 1000.0/float(a)))
else:
    print("stopped")
PY
