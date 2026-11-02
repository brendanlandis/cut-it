#!/bin/sh
# The display arbiter's headless gate -- ref/module/display.md. No eyes, no
# hardware, ~46 s.
#
#     ./test/gate/display-assert.sh            # run it
#     ./test/gate/display-assert.sh -v         # and show the detail behind every check
#     ./test/gate/display-assert.sh --keep     # and leave the capture behind to read
#
# ⚠️ IT NEEDS DSP, AND -noaudio DOES NOT TAKE IT AWAY -- that disables the audio
# DEVICE, not the graph (item 280). The beat row hangs off threshold~ in c_clock,
# so a silent run would assert on a grid that never moves. That is the whole
# reason this one costs 46 s where most cost under ten.
#
# ⚠️ IT ASSERTS ON THE ARBITER, NOT ON THE DEVICE -- which layer owns the surface
# and what happens when one gives it up. What the Launchpad is told to switch
# itself to is launchpad-assert.sh's, and that gate needs neither DSP nor 46 s.
exec python3 "$(dirname "$0")/scratch-gates.py" display "$@"
