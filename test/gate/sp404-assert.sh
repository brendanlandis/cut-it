#!/bin/sh
# The SP-404's headless gate -- ref/device/sp404.md. No eyes, no hardware, ~7 s.
#
#   ./test/gate/sp404-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/sp404-assert.sh -v       and show the detail behind every check
#   ./test/gate/sp404-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ THE ONLY GATE HERE THAT TESTS A DEVICE IN BOTH DIRECTIONS. Every output path
# can be driven from a bus, but m_404's whole receive side sits behind [notein]
# and NO BUS REACHES A MIDI INPUT -- which is why t_notein exists and why the
# driver sends bare `t-notein` messages into the scratch copy.
exec python3 "$(dirname "$0")/scratch-gates.py" sp404 "$@"
