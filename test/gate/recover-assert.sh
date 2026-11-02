#!/bin/sh
# Panic's second tier -- ref/module/map.md and ref/module/boot.md. ~20 s.
#
#   ./test/gate/recover-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/recover-assert.sh -v       and show the detail behind every check
#   ./test/gate/recover-assert.sh --keep   leave the scratch dirs and captures
#
# ⛔ ITS CORE IS UNTESTABLE ON A MAC, AND SAYING SO IS PART OF THE GATE. [shell]
# is stubbed here, so nothing is sent to mother and no patch is loaded. What this
# proves is that the right command was FORMED, in the right order, behind the
# silence -- plus a static lint of recover.sh that needs no Pd at all and is the
# strongest half. THE RELOAD ITSELF IS A BENCH STEP. See recover-assert.py's
# header for the three things it deliberately cannot claim.
#
# ⛔ TWO RUNS, TWO SCRATCH TREES, AND THE ONLY DIFFERENCE IS WHAT IS ON DISK.
# Run A boots clean and drives the button. Run B boots with a breadcrumb already
# there -- the state the next boot after a real recover is in.
#
# ⚠️ TWO WORK DIRS, NEVER ONE REUSED. u_state restores at about 3.5 s from the
# state directory the previous run wrote, and a leftover mode changes what the
# map does mid-run. Item 232.
#
# ⚠️ DSP is not needed -- every path here is a message on a timer.
exec python3 "$(dirname "$0")/scratch-gates.py" recover "$@"
