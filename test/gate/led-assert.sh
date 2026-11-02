#!/bin/sh
# The aux LED's headless gate -- ref/device/organelle.md. No eyes, no hardware, ~11 s.
#
#   ./test/gate/led-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/led-assert.sh -v       and show the detail behind every check
#   ./test/gate/led-assert.sh --keep   leave the scratch dir and capture behind
#
# No DSP and no MIDI: g_led is a route and four message boxes on the disp bus.
exec python3 "$(dirname "$0")/scratch-gates.py" led "$@"
