#!/bin/sh
# The OLED's headless gate -- ref/module/display.md. No eyes, no hardware.
#
#   ./test/gate/oled-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/oled-assert.sh -v       and show the detail behind every check
#   ./test/gate/oled-assert.sh --keep   leave the scratch dir and capture behind
#
# It taps oscOut, since Pd cannot ask a screen what it shows, and the analyzer
# parses that stream as u_mother-stub does. No DSP: the frame clock is a
# [metro 100], and the meters, silent here, are the display checklist's to judge.
exec python3 "$(dirname "$0")/scratch-gates.py" oled "$@"
