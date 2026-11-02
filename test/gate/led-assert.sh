#!/bin/sh
# The aux LED's headless gate -- ref/device/organelle.md. No eyes, no hardware, ~11 s.
#
#   ./test/gate/led-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/led-assert.sh -v       and show the detail behind every check
#   ./test/gate/led-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ g_led HAD ZERO REFERENCES ANYWHERE UNDER test/ BEFORE THIS FILE. Its page
# named display-assert.sh, which asserts on Launchpad SysEx and never touches the
# LED -- so the one display surface in the rig that is not a screen was the least
# covered thing in the patch while looking covered.
#
# ⚠️ NO DSP AND NO MIDI. g_led is 34 lines of route and four message boxes.
exec python3 "$(dirname "$0")/scratch-gates.py" led "$@"
