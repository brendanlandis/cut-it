#!/bin/sh
# The error bus's headless gate -- ref/module/error.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/err-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/err-assert.sh -v       and show the detail behind every check
#   ./test/gate/err-assert.sh --keep   leave the scratch dir and capture behind
#
# Its claim: perform mode suppresses warn and never fail. That is one cord in
# u_err, and nothing on the instrument would report it wrong. No DSP and no
# MIDI; the analyzer's first half is a static lint of every error message box
# (C-12).
exec python3 "$(dirname "$0")/scratch-gates.py" err "$@"
