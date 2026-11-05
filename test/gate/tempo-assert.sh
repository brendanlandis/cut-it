#!/bin/sh
# The tempo reference's headless gate -- ref/module/tempo.md. No eyes, no
# hardware.
#
#     ./test/gate/tempo-assert.sh            # run it
#     ./test/gate/tempo-assert.sh -v         # and show the detail behind every check
#     ./test/gate/tempo-assert.sh --keep     # and leave the capture behind to read
#
# It needs DSP, since u_tempo's pulse is a [phasor~] read by a [threshold~], and
# -noaudio leaves DSP running (item 280). Its subject is a rate on a wire: a
# clock at half speed, on one port, or stopping with the transport would be
# silent on the Mac and obvious at a gig.
exec python3 "$(dirname "$0")/scratch-gates.py" tempo "$@"
