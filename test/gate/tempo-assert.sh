#!/bin/sh
# The tempo reference's headless gate -- ref/module/tempo.md. No eyes, no
# hardware, ~16 s.
#
#     ./test/gate/tempo-assert.sh            # run it
#     ./test/gate/tempo-assert.sh --keep     # and leave the capture behind to read
#
# ⚠️ DSP IS ON AND THERE IS NO -noaudio, for the same reason display-assert needs
# it: u_tempo's pulse is a [phasor~] read by a [threshold~], so the clock lives
# in the audio domain. A silent run counts zero pulses at every tempo, which
# reads exactly like a dead clock rather than a missing flag.
#
# WHAT IT PROVES that nothing else did: u_tempo's most important output is not a
# message but a RATE on a wire, and no other gate reads a wire back. A clock at
# half speed, or on one port instead of two, or one that stopped when the
# transport did, would be silent on the Mac and obvious only at a gig.
set -e

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
WORK=${TMPDIR:-/tmp}/cutit-tempo-$$
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

scratch_require "Cut It/u_tempo.pd" "Cut It/main-dev.pd"

scratch_make "$WORK"
scratch_state_dir "$WORK"
midi_rewrite "$WORK"

scratch_drive test/gate/tempo-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
echo "   running (about 16 s -- DSP is on, the clock is a phasor~) ..."
scratch_run "$CAP" 60 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

echo
set +e
python3 test/gate/tempo-assert.py < "$CAP"
rc=$?
set -e

if [ "$KEEP" -eq 1 ]; then
    echo
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
