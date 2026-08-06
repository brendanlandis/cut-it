#!/bin/sh
# Drive the clock-contention test: set tempo and trigger interval remotely.
#   ./tools/404-contend.sh tempo 600
#   ./tools/404-contend.sh rate 4        interval in ms -> 250 triggers/sec
#   ./tools/404-contend.sh go | stop
set -eu
K=${1:?usage: 404-contend.sh <tempo|rate|go|stop> [value]}
V=${2:-}
python3 - "$K" "$V" "${HOST:-organelle.local}" <<'PY'
import socket, sys
k, v, host = sys.argv[1], sys.argv[2], sys.argv[3]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg = ("%s %s;\n" % (k, v)) if v else ("%s;\n" % k)
s.sendto(msg.encode(), (host, 9995))
if k == "rate" and v:
    print("interval %s ms -> %.0f triggers/sec" % (v, 1000.0/float(v)))
else:
    print("%s %s" % (k, v))
PY
