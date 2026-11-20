#!/bin/sh
# The Cut It app's commands, read against the patch's -- ref/device/phone.md. No Pd, no phone.
#
#   ./test/gate/app-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/app-assert.sh -v       and the detail behind every check
#
# The oracle is the patch's own vocabulary: u_net's routes, u_map's destinations and the Lua's
# command tables, loaded under Lua 5.4, against every command the Swift sends.
exec python3 "$(dirname "$0")/app-assert.py" "$@"
