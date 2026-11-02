#!/bin/sh
# The data store's headless gate -- ref/module/state.md. No eyes, no hardware,
# no socket, ~12 s.
#
#   ./test/gate/state-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/state-assert.sh -v       and show the detail behind every check
#   ./test/gate/state-assert.sh --keep   leave the scratch dir, driver and captures
#
# u_state writes files, so this reads what landed on disk, with nothing
# rewritten. The driver is generated into the gate's own scratch directory,
# where u_state writes too: edit state-assert-drive-gen.py, never a .pd.
exec python3 "$(dirname "$0")/state-assert.py" "$@"
