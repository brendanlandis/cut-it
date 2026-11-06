#!/bin/sh
# The display arbiter's headless gate -- ref/module/display.md. No eyes, no
# hardware.
#
#     ./test/gate/display-assert.sh            # run it
#     ./test/gate/display-assert.sh -v         # and show the detail behind every check
#     ./test/gate/display-assert.sh --keep     # and leave the capture behind to read
#
# It runs the painter's Lua tests first (test/gate/lua/g_grid_test.lua), then the
# patch. It needs DSP, since the beats that repaint an idle page hang off threshold~
# in c_clock, and -noaudio leaves DSP running (item 280). It asserts on the arbiter, not the
# device: what the Launchpad is told to switch itself to is launchpad-assert.sh's.
exec python3 "$(dirname "$0")/scratch-gates.py" display "$@"
