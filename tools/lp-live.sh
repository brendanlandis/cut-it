#!/bin/sh
# Return the Launchpad to Live Mode WITHOUT Pd -- the rescue for a stranded grid.
#
#     ./tools/lp-live.sh                 # on the device, over ssh
#     HOST=root@192.168.1.15 ./tools/lp-live.sh
#     LOCAL=1 ./tools/lp-live.sh         # run it ON the device itself
#
# WHY THIS EXISTS. Entering Programmer Mode by SysEx locks out the Launchpad's
# own Settings menu, so a device left in that state cannot be recovered from its
# front panel. m_launchpad's safe exit handles the ONE case it can: [r quitting],
# which mother.pd sends before it quits Pd, with a 100 ms budget. Pd 0.49 has no
# closebang, so that is the only shutdown hook there is.
#
# EVERY OTHER WAY OF ENDING A SESSION STRANDS THE DEVICE:
#   * `killall pd` over SSH -- which the by-hand console workflow in
#     ref/conventions.md does every single time
#   * a Pd crash
#   * power loss mid-session
# Measured 2026-08-03: killall left the grid frozen in Programmer Mode, and this
# script brought it back with no power cycle.
#
# tools/deploy.sh is NOT affected -- it loads through mother's /loadPatch, so `quitting`
# fires and the safe exit runs normally.
#
# THE PORT IS LOOKED UP BY NAME. amidi's hw:N numbering shifts as devices come and
# go, exactly like the ALSA client numbers wire.sh warns about.
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
