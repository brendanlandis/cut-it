#!/bin/sh
# The sequencer's headless gate -- ref/module/sequencer.md. No eyes, no
# hardware, ~14 s.
#
#   ./test/gate/sequencer-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/sequencer-assert.sh -v       and show the detail behind every check
#   ./test/gate/sequencer-assert.sh --keep   leave the scratch dir and capture behind
#
# It plays page 2's drum page on param, as m_launchpad publishes it, and reads
# what leaves: the pads for c_kit, the grid's frames, the state bus and the file.
# It needs DSP, since c_steps cuts its steps from c_clock's phasor~, and the
# state directory is seeded with a pattern, so the restore is under test too.
exec python3 "$(dirname "$0")/scratch-gates.py" sequencer "$@"
