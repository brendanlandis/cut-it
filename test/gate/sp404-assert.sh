#!/bin/sh
# The SP-404's headless gate -- ref/device/sp404.md. No eyes, no hardware, ~7 s.
#
#   ./test/gate/sp404-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/sp404-assert.sh -v       and show the detail behind every check
#   ./test/gate/sp404-assert.sh --keep   leave the scratch dir and capture behind
#
# Both directions: m_404's receive side sits behind [notein], which no bus
# reaches, so the scratch copy has t_notein and the driver sends `t-notein`.
exec python3 "$(dirname "$0")/scratch-gates.py" sp404 "$@"
