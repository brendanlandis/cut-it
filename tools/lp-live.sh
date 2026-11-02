#!/bin/sh
# Return the Launchpad to Live Mode WITHOUT Pd -- the rescue for a stranded grid.
#
#     ./tools/lp-live.sh                 # on the device, over ssh
#     HOST=root@192.168.1.15 ./tools/lp-live.sh
#     LOCAL=1 ./tools/lp-live.sh         # run it ON the device itself
#
# Any end of a session but mother's `quitting` (killall pd, a crash, power loss)
# leaves the Launchpad in Programmer Mode, whose Settings menu is locked out:
# tools/README.md. The port is looked up by name: amidi's hw:N shifts as devices
# come and go.
set -eu

HOST=${HOST:-root@organelle.local}
LIVE='F0 00 20 29 02 0E 0E 00 F7'      # Programmer Mode off = Live Mode

run() {
    if [ "${LOCAL:-}" = "1" ]; then sh -c "$1"; else ssh "$HOST" "$1"; fi
}

PORT=$(run "amidi -l 2>/dev/null | awk '/Launchpad Pro MK3 MIDI 1/{print \$2; exit}'")

if [ -z "$PORT" ]; then
    echo "lp-live: no Launchpad found in amidi -l" >&2
    echo "         is it plugged in? is it powered?" >&2
    exit 1
fi

run "amidi -p $PORT -S '$LIVE'"
echo "lp-live: Live Mode sent to $PORT -- the device should show its own layout again"
