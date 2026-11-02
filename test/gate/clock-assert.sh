#!/bin/sh
# c_clock's headless gate -- ref/module/tempo.md. No eyes, no hardware, ~17 s.
#
#   ./test/gate/clock-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/clock-assert.sh -v       and show the detail behind every check
#   ./test/gate/clock-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ THE RATIO ARGUMENT WAS ONLY EVER HUMAN-READ OFF A BENCH PRINT. tempo-assert
# covers u_tempo and names c_clock in a comment; ref/module/tempo.md declares one
# gate for a page whose Files line holds two abstractions. This is the second.
#
# ⛔ IT LOADS A HARNESS RATHER THAN main-dev.pd, and that is the whole shape of
# it: c_clock publishes on no bus -- its output is four outlets -- so there is
# nothing to tap, and only a [print] wired to an outlet can see it. Three
# instances, no instrument around them, nothing else running.
#
# ⚠️ IT NEEDS DSP -- AND -noaudio DOES NOT TAKE DSP AWAY. The beat is threshold~ on
# a wrap~ of a phasor~, so without a running graph nothing ticks and every count
# comes back 0. That part is true and worth keeping. The conclusion this line used
# to draw from it was not: -noaudio disables the audio DEVICE, and Pd drives the
# same graph from its internal scheduler instead. Measured both ways 2026-08-10 --
# 22 checks, byte-identical output either way. Item 280.
exec python3 "$(dirname "$0")/scratch-gates.py" clock "$@"
