#!/bin/sh
# The error bus's headless gate -- ref/module/error.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/err-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/err-assert.sh -v       and show the detail behind every check
#   ./test/gate/err-assert.sh --keep   leave the scratch dir and capture behind
#
# Its claim: every warn and fail is drawn, on every page, and nothing in u_err
# reads the mode; a filter there fails silent, and nothing on the instrument
# would report it. No DSP and no MIDI; the analyzer's first half is a static
# lint of every error message box (C-12) and of u_err itself.
exec python3 "$(dirname "$0")/scratch-gates.py" err "$@"
