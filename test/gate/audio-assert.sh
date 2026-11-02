#!/bin/sh
# The audio path's headless gate -- ref/module/audio.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/audio-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/audio-assert.sh -v       and show the detail behind every check
#   ./test/gate/audio-assert.sh --keep   leave the scratch dir, the capture and the wav
#
# The one gate that reads a signal back: it records u_root's output from a
# harness holding u_root alone, since u_mother-stub already holds the only
# catch~ outL and outR there can be. -noaudio leaves DSP running: measured both
# ways, the recording is byte-identical (item 280).
exec python3 "$(dirname "$0")/scratch-gates.py" audio "$@"
