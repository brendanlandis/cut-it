#!/bin/sh
# The Organelle front panel's headless gate -- ref/device/organelle.md.
# No eyes, no hardware, ~12 s.
#
#   ./test/gate/organelle-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/organelle-assert.sh -v       and show the detail behind every check
#   ./test/gate/organelle-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ m_organelle HAD ZERO REFERENCES IN ANY GATE, and its page declared
# `Gate: none` honestly. It is the cheapest m_ layer to cover of the lot: five
# [r] boxes on mother's own names is the whole input surface, so unlike m_nano it
# needed no stub -- only somebody to write the driver.
#
# ⚠️ NO DSP AND NO MIDI. Nothing here needs a clock or a wire.
exec python3 "$(dirname "$0")/scratch-gates.py" organelle "$@"
