#!/bin/sh
# The phone's TouchOSC layout, headless -- ref/device/phone.md. No phone, ~1 s.
#
#   ./test/gate/touchosc-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/touchosc-assert.sh -v       and the detail behind every check
#   ./test/gate/touchosc-assert.sh --keep   leave the unpacked layout in the scratch dir
#
# The oracle is the layout itself, read, and its scripts run under a stand-in for TouchOSC.
exec python3 "$(dirname "$0")/touchosc-assert.py" "$@"
