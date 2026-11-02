#!/bin/sh
# The audio path's headless gate -- ref/module/audio.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/audio-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/audio-assert.sh -v       and show the detail behind every check
#   ./test/gate/audio-assert.sh --keep   leave the scratch dir, the capture and the wav
#
# ⛔ THE FIRST SIGNAL-DOMAIN GATE IN THIS PROJECT. Every other one asserts on
# MESSAGES and nothing had ever read a signal back, which is why
# ref/module/audio.md declared `Gate: none` honestly. The audio path is six boxes
# and four `#X connect` lines at the end of u_root.pd, a broken rewiring there is
# completely silent, and it would surface as no sound at a venue.
#
# ⛔ IT LOADS A HARNESS HOLDING u_root ALONE, NOT main-dev.pd. catch~ must be
# uniquely defined and u_mother-stub already holds catch~ outL and catch~ outR,
# so a second pair beside it would simply fail to create and the recording would
# be silent -- the worst possible failure, since silence is also what a broken
# audio path looks like.
#
# ⚠️ -noaudio IS SAFE HERE, AND THIS LINE USED TO SAY THE OPPOSITE. It read "NO
# -noaudio, and that is the whole point -- the subject is a signal", which sounds
# obviously right and is wrong: -noaudio disables the audio DEVICE, not the DSP
# graph. Pd falls back to its internal scheduler, the graph still computes and
# writesf~ still writes. Measured both ways 2026-08-10 -- BYTE-IDENTICAL output,
# same peaks, same report counts. Item 280. Keeping it means the suite never
# opens a Mac audio device it has no use for.
exec python3 "$(dirname "$0")/scratch-gates.py" audio "$@"
