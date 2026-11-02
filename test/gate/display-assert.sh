#!/bin/sh
# The display arbiter's headless gate -- ref/module/display.md. No eyes, no
# hardware, ~46 s.
#
#     ./test/gate/display-assert.sh            # run it
#     ./test/gate/display-assert.sh -v         # and show the detail behind every check
#     ./test/gate/display-assert.sh --keep     # and leave the capture behind to read
#
# It needs DSP, since the beat row hangs off threshold~ in c_clock, and -noaudio
# leaves DSP running (item 280). It asserts on the arbiter, not the device: what
# the Launchpad is told to switch itself to is launchpad-assert.sh's.
exec python3 "$(dirname "$0")/scratch-gates.py" display "$@"
