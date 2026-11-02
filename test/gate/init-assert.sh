#!/bin/sh
# The boot sequence's headless gate -- ref/module/boot.md. No eyes, no hardware, ~10 s.
#
#   ./test/gate/init-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/init-assert.sh -v       and show the detail behind every check
#   ./test/gate/init-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ ref/module/boot.md USED TO DECLARE `Gate: test/run.sh`, the whole runner --
# the only page naming something that is not a gate. It was honest that nothing
# covered u_init specifically and misleading about what was covering it: every
# gate loads the patch, so every gate proved the boot does not ERROR, and not one
# proved it happens in the right ORDER.
#
# ⚠️ NO DSP. Every stage is a message on a timer.
exec python3 "$(dirname "$0")/scratch-gates.py" init "$@"
