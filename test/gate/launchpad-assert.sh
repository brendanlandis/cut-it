#!/bin/sh
# The Launchpad's headless gate -- ref/device/launchpad.md. No eyes, no hardware,
# ~4 s.
#
#     ./test/gate/launchpad-assert.sh            # run it
#     ./test/gate/launchpad-assert.sh --keep     # and leave the capture behind
#
# ⚠️ NO DSP AND NO 46 SECONDS. It asserts on two SysEx messages -- the mode switch
# at boot and the one on panic -- and on the ORDER between them and the painted
# frames. None of that needs a clock. It shared a gate with the display arbiter
# for no better reason than that both watch [midiout], and paid that gate's DSP
# bill for two checks.
#
# ⚠️ WHAT THE ARBITER DOES WITH THE SURFACE IS NOT TESTED HERE. That is
# display-assert.sh's, next door.
set -e

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
WORK=${TMPDIR:-/tmp}/cutit-launchpad-$$
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

scratch_require "Cut It/m_launchpad.pd" "Cut It/main-dev.pd"

scratch_make "$WORK"
scratch_state_dir "$WORK"
midi_rewrite "$WORK"

scratch_drive test/gate/launchpad-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

echo
set +e
python3 test/gate/launchpad-assert.py < "$CAP"
rc=$?
set -e

if [ "$KEEP" -eq 1 ]; then
    echo
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
