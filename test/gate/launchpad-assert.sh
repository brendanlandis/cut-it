#!/bin/sh
# The Launchpad's headless gate -- ref/device/launchpad.md. No eyes, no hardware,
# ~4 s.
#
#     ./test/gate/launchpad-assert.sh            # run it
#     ./test/gate/launchpad-assert.sh -v         # and show the detail behind every check
#     ./test/gate/launchpad-assert.sh --keep     # and leave the capture behind
#
# ⚠️ NO DSP AND NO 46 SECONDS. It asserts on two SysEx messages -- the mode switch
# at boot and the one on panic -- and on the ORDER between them and the painted
# frames. None of that needs a clock. It shared a gate with the display arbiter
# for no better reason than that both watch [midiout], and paid that gate's DSP
# bill for two checks.
#
# ⚠️ WHAT THE ARBITER DOES WITH THE SURFACE IS NOT TESTED HERE. That is
# display-assert.sh's, next door.
exec python3 "$(dirname "$0")/scratch-gates.py" launchpad "$@"
