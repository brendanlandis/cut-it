#!/bin/sh
# The OLED's headless gate -- ref/module/display.md. No eyes, no hardware, ~21 s.
#
#   ./test/gate/oled-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/oled-assert.sh -v       and show the detail behind every check
#   ./test/gate/oled-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ g_oled IS THE DENSEST FILE IN THE PATCH AND ITS ENTIRE COVERAGE WAS THAT THE
# FILE EXISTS. 783 lines, four layers with priorities and time-to-live, a
# five-row parameter store with its own aging -- all of it judged by eye off a
# panel until now.
#
# ⚠️ WHAT MADE IT TESTABLE IS THE TAP ON oscOut. Pd cannot ask a screen what it is
# showing, but every byte sent to it is knowable. u_mother-stub has decoded that
# same stream into eight preview rows since Phase 3, so the arithmetic was
# already debugged; the analyser reimplements the parse in Python.
#
# ⚠️ NO DSP. The frame clock is a [metro 100] and every layer is messages. The
# meters have nothing to say without audio, which costs this gate nothing --
# their geometry is the one part of the page a person still has to judge.
exec python3 "$(dirname "$0")/scratch-gates.py" oled "$@"
