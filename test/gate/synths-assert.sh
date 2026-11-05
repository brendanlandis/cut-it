#!/bin/sh
# The synths' headless gate -- ref/module/synths.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/synths-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/synths-assert.sh -v       and show the detail behind every check
#   ./test/gate/synths-assert.sh --keep   leave the scratch dir and capture behind
#
# The trap is a key held through a switch: its release must go to the synth that got
# its press, or the Volca's note sounds until a panic.
exec python3 "$(dirname "$0")/scratch-gates.py" synths "$@"
