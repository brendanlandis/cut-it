#!/bin/sh
# The Organelle front panel's headless gate -- ref/device/organelle.md.
# No eyes, no hardware.
#
#   ./test/gate/organelle-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/organelle-assert.sh -v       and show the detail behind every check
#   ./test/gate/organelle-assert.sh --keep   leave the scratch dir and capture behind
#
# m_organelle's whole input is five [r] boxes on mother's own names, so it needs
# no stub, no DSP and no MIDI.
exec python3 "$(dirname "$0")/scratch-gates.py" organelle "$@"
