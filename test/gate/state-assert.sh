#!/bin/sh
# The data store's headless gate -- ref/module/state.md. No eyes, no hardware,
# no socket, ~12 s.
#
#   ./test/gate/state-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/state-assert.sh -v       and show the detail behind every check
#   ./test/gate/state-assert.sh --keep   leave the scratch dir, driver and captures
#
# THE CHEAPEST ORACLE IN THE SUITE. The MIDI gates rewrite object boxes in a
# scratch copy, because a built-in class has no side channel. phone-assert
# points u_net at 127.0.0.1 and reads datagrams. u_state writes a FILE, so this
# one just reads what landed on disk. "Cut It/" is never touched and nothing is
# rewritten.
#
# The driver is generated into the gate's own scratch directory on every run,
# and u_state writes there too -- edit state-assert-drive-gen.py, never a .pd.
# It never touches /sdcard/cut-it-state, and never the device.
exec python3 "$(dirname "$0")/state-assert.py" "$@"
