#!/bin/sh
# The voices and the controls in play's headless gate -- ref/module/voices.md. No eyes, no hardware.
#
#   ./test/gate/voices-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/voices-assert.sh -v       and show the detail behind every check
#   ./test/gate/voices-assert.sh --keep   leave the scratch dir and capture behind
#
# The trap is a control that only works on the page it was taken from: in play it has to reach its
# own engine from anywhere, and wait for its physical control after a section starts.
exec python3 "$(dirname "$0")/scratch-gates.py" voices "$@"
