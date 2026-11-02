#!/bin/sh
# c_clock's headless gate -- ref/module/tempo.md. No eyes, no hardware, ~17 s.
#
#   ./test/gate/clock-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/clock-assert.sh -v       and show the detail behind every check
#   ./test/gate/clock-assert.sh --keep   leave the scratch dir and capture behind
#
# It loads a harness rather than main-dev.pd: c_clock publishes on no bus, so
# only a [print] wired to an outlet can see it. It needs DSP, since the beat is
# threshold~ on a phasor~, and -noaudio leaves DSP running (item 280).
exec python3 "$(dirname "$0")/scratch-gates.py" clock "$@"
