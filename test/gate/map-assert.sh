#!/bin/sh
# The map's headless gate -- ref/module/map.md. No eyes, no hardware.
#
#   ./test/gate/map-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/map-assert.sh -v       and show the detail behind every check
#   ./test/gate/map-assert.sh --keep   leave the scratch dir and capture behind
#
# Half of it needs no Pd: the Lua tests run the map's rules (u_map.lua) with
# lua.org's interpreter, and the static lint reads cut-it-map.txt against the
# literal route box in u_map.pd, in ~200 ms. The driven half tests the lookup.
# What a destination does with the value is volca-assert.sh's, sequencer-assert.sh's
# and recover-assert.sh's; volca-cc is only where a lookup lands.
exec python3 "$(dirname "$0")/scratch-gates.py" map "$@"
