#!/bin/sh
# Device presence and the bounded re-wire -- ref/module/presence.md. No eyes, no
# hardware.
#
#   ./test/gate/presence-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/presence-assert.sh -v       and show the detail behind every check
#   ./test/gate/presence-assert.sh --keep   leave the scratch dirs and captures behind
#
# The only gate whose stimulus is a silence: it withholds the device-inquiry
# reply (item 235's absent-at-load case), so the analyzer refuses to score a run
# without its liveness witnesses. Two Pd runs, one tally: test/README.md.
#
# No DSP: g_grid's frame clock is a [metro] and the watchdog is all timers.
exec python3 "$(dirname "$0")/scratch-gates.py" presence "$@"
