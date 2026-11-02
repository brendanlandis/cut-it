#!/bin/sh
# The tempo reference's headless gate -- ref/module/tempo.md. No eyes, no
# hardware, ~16 s.
#
#     ./test/gate/tempo-assert.sh            # run it
#     ./test/gate/tempo-assert.sh -v         # and show the detail behind every check
#     ./test/gate/tempo-assert.sh --keep     # and leave the capture behind to read
#
# ⚠️ IT NEEDS DSP, for the same reason display-assert does, and -noaudio does not
# take it away (item 280): u_tempo's pulse is a [phasor~] read by a [threshold~], so the clock lives
# in the audio domain. A silent run counts zero pulses at every tempo, which
# reads exactly like a dead clock rather than a missing flag.
#
# WHAT IT PROVES that nothing else did: u_tempo's most important output is not a
# message but a RATE on a wire, and no other gate reads a wire back. A clock at
# half speed, or on one port instead of two, or one that stopped when the
# transport did, would be silent on the Mac and obvious only at a gig.
exec python3 "$(dirname "$0")/scratch-gates.py" tempo "$@"
