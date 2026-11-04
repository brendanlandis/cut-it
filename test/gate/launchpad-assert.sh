#!/bin/sh
# The Launchpad's headless gate -- ref/device/launchpad.md. No eyes, no hardware,
# ~4 s.
#
#     ./test/gate/launchpad-assert.sh            # run it
#     ./test/gate/launchpad-assert.sh -v         # and show the detail behind every check
#     ./test/gate/launchpad-assert.sh --keep     # and leave the capture behind
#
# No DSP: it asserts on the two mode switches, Programmer Mode at boot and Live
# Mode on quit, and their order against the painted frames, and on a tap on
# Setup told from the announcement every entry makes. What the arbiter does
# with the surface is display-assert.sh's.
exec python3 "$(dirname "$0")/scratch-gates.py" launchpad "$@"
