#!/bin/sh
# The drum kit's headless gate -- ref/module/sequencer.md, The kit. No eyes, no hardware.
#
#   ./test/gate/kit-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/kit-assert.sh -v       and show the detail behind every check
#   ./test/gate/kit-assert.sh --keep   leave the scratch dir, the capture and the wav
#
# A harness holding c_kit alone, five samples written into the scratch copy, and a
# recording of what it throws to outL: levels, silences and a retrigger, read
# back from the signal. And u_root's cord from c_steps, read from the file.
exec python3 "$(dirname "$0")/scratch-gates.py" kit "$@"
