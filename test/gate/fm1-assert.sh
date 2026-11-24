#!/bin/sh
# The FM-1's headless gate -- ref/device/fm1.md. No eyes, no hardware.
#
#   ./test/gate/fm1-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/fm1-assert.sh -v       and show the detail behind every check
#   ./test/gate/fm1-assert.sh --keep   leave the scratch dir and capture behind
#
# The traps: pgmout is 1-based on its inlet and 0-based on the wire (item 228),
# controllers go out one channel up, and panic is note-offs, not CC 123.
exec python3 "$(dirname "$0")/scratch-gates.py" fm1 "$@"
