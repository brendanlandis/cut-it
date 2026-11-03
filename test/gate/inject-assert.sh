#!/bin/sh
# u_inject's headless gate -- test/checklists/README.md, Send lines. No eyes, no
# hardware, ~8 s.
#
#   ./test/gate/inject-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/inject-assert.sh -v       and the detail behind every check
#   ./test/gate/inject-assert.sh --keep   leave the scratch dir, driver and capture
#
# The oracle is Pd's console: a print on every bus a Send line could name, and
# the lines sent through tools/send.sh itself.
exec python3 "$(dirname "$0")/inject-assert.py" "$@"
