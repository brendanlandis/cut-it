#!/bin/sh
# Panic's second tier -- ref/module/map.md and ref/module/boot.md..
#
#   ./test/gate/recover-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/recover-assert.sh -v       and show the detail behind every check
#   ./test/gate/recover-assert.sh --keep   leave the scratch dirs and captures
#
# [shell] is stubbed, so the reload itself is a checklist step: this proves the
# command was formed and forked, in order, behind the silence, plus a static
# lint of recover.sh. What it cannot claim is in recover-assert.py's header.
#
# Two runs in two scratch trees, differing only in what is on disk: A boots
# clean and drives the button, B boots with a breadcrumb already there. No DSP.
exec python3 "$(dirname "$0")/scratch-gates.py" recover "$@"
