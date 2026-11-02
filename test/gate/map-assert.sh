#!/bin/sh
# The map's headless gate -- ref/module/map.md. No eyes, no hardware, ~7 s.
#
#   ./test/gate/map-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/map-assert.sh -v       and show the detail behind every check
#   ./test/gate/map-assert.sh --keep   leave the scratch dir and capture behind
#
# HALF OF IT NEEDS NO Pd AT ALL -- the static lint reads cut-it-map.txt against
# the literal route box in u_map.pd, in about 200 ms, and that is the strongest
# check in the suite. The driven half tests the LOOKUP: that a control maps at
# load, that the same control maps differently in another mode, and that a row
# naming a destination off the route is silent and says why.
#
# ⚠️ WHAT A DESTINATION DOES WITH THE VALUE IS NOT TESTED HERE. That belongs to
# volca-assert.sh and sp404-assert.sh. This gate uses volca-cc only because a
# lookup has to land somewhere.
exec python3 "$(dirname "$0")/scratch-gates.py" map "$@"
