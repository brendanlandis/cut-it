#!/bin/sh
# The error bus's headless gate -- ref/module/error.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/err-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/err-assert.sh -v       and show the detail behind every check
#   ./test/gate/err-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ ITS CENTRAL CLAIM WAS BENCH PROSE ONLY: that perform mode suppresses warn and
# never suppresses fail. u_err's spigot is on the warn branch and fail is
# unspigoted -- one cord -- and nothing on the instrument would report it being
# wrong. The display would just go quiet, at a venue.
#
# ⚠️ NO DSP AND NO MIDI. The first half of the analyser needs no Pd at all: it is
# a static lint over every error message box in the patch, which is where C-12's
# 21-character limit actually lives.
exec python3 "$(dirname "$0")/scratch-gates.py" err "$@"
