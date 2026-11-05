#!/bin/sh
# The nanoKONTROL's headless gate -- ref/device/nanokontrol.md. No eyes, no
# hardware.
#
#   ./test/gate/nano-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/nano-assert.sh -v       and show the detail behind every check
#   ./test/gate/nano-assert.sh --keep   leave the scratch dir and capture behind
#
# m_nano is reached through t_ctlin: every path in it sits behind [ctlin]. No
# DSP.
exec python3 "$(dirname "$0")/scratch-gates.py" nano "$@"
