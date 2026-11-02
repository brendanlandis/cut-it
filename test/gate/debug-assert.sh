#!/bin/sh
# The debug patch's headless gate -- ref/module/debug.md. No eyes, no hardware, ~13 s.
#
#   ./test/gate/debug-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/debug-assert.sh -v       and show the detail behind every check
#   ./test/gate/debug-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ IT IS THE ONLY GATE THAT TESTS THE SECOND DEPLOYABLE. Everything else here
# loads main-dev.pd; "Cut It Debug" is a separate patch with no u_mother-stub, no
# disp bus and no g_oled, so it is scratch-copied and driven on its own.
#
# ⛔ AND IT IS THE ONLY GATE WHOSE SUBJECT IS A SCREEN. The debug patch has no
# bus -- the five rows it writes to mother are the entire product -- so the rows
# are what is asserted. That is not a weaker oracle for a tool whose job is to
# display four numbers.
#
# ⚠️ NO DSP, NO AUDIO AND NO REAL MIDI. -noaudio disables the audio DEVICE and
# not the graph (item 280), and this patch has no signal objects at all.
exec python3 "$(dirname "$0")/scratch-gates.py" debug "$@"
