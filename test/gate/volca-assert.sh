#!/bin/sh
# The Volca's headless gate -- ref/device/volca.md. No eyes, no hardware, ~5 s.
#
#   ./test/gate/volca-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/volca-assert.sh -v       and show the detail behind every check
#   ./test/gate/volca-assert.sh --keep   leave the scratch dir and capture behind
#
# It is the smallest gate here because m_volca is the smallest m_ layer: three
# destinations onto one channel. ⛔ The one place it is not obvious is pgmout,
# which is 1-based on its inlet and 0-based on the wire -- item 228.
exec python3 "$(dirname "$0")/scratch-gates.py" volca "$@"
