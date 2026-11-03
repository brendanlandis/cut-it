#!/bin/sh
# The phone's checklist page, headless -- test/checklists/README.md. No phone,
# ~8 s.
#
#   ./test/gate/checks-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/checks-assert.sh -v       and the detail behind every check
#   ./test/gate/checks-assert.sh --keep   leave the scratch dir, driver and capture
#
# The oracle is Pd's console: the page opened beside a driver that presses its
# buttons, with a print on every label and on #osc-out.
exec python3 "$(dirname "$0")/checks-assert.py" "$@"
