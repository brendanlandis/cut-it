#!/bin/sh
# The boot sequence's headless gate -- ref/module/boot.md. No eyes, no hardware, ~10 s.
#
#   ./test/gate/init-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/init-assert.sh -v       and show the detail behind every check
#   ./test/gate/init-assert.sh --keep   leave the scratch dir and capture behind
#
# Every gate proves the boot does not error; this one proves its order. No DSP.
exec python3 "$(dirname "$0")/scratch-gates.py" init "$@"
