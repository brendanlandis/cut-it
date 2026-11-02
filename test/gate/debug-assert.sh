#!/bin/sh
# The debug patch's headless gate -- ref/module/debug.md. No eyes, no hardware, ~13 s.
#
#   ./test/gate/debug-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/debug-assert.sh -v       and show the detail behind every check
#   ./test/gate/debug-assert.sh --keep   leave the scratch dir and capture behind
#
# "Cut It Debug" has no u_mother-stub, disp bus or g_oled, so it is
# scratch-copied and driven on its own, and the five rows it writes to mother,
# which are the whole product, are what is asserted.
exec python3 "$(dirname "$0")/scratch-gates.py" debug "$@"
