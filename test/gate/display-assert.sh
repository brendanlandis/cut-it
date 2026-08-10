#!/bin/sh
# The display arbiter's headless gate -- ref/module/display.md. No eyes, no
# hardware, ~46 s.
#
#     ./test/gate/display-assert.sh            # run it
#     ./test/gate/display-assert.sh --keep     # and leave the capture behind to read
#
# ⚠️ DSP IS ON AND THERE IS NO -noaudio, AND IT IS THE ONLY GATE HERE THAT NEEDS
# IT. The beat row hangs off threshold~ in c_clock, so a silent run would assert
# on a grid that never moves. That is the whole reason this one costs 46 s where
# the rest cost under ten.
#
# ⚠️ IT ASSERTS ON THE ARBITER, NOT ON THE DEVICE -- which layer owns the surface
# and what happens when one gives it up. What the Launchpad is told to switch
# itself to is launchpad-assert.sh's, and that gate needs neither DSP nor 46 s.
set -e

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
WORK=${TMPDIR:-/tmp}/cutit-display-$$
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

scratch_require "Cut It/g_grid.pd" "Cut It/g_oled.pd" "Cut It/main-dev.pd"

scratch_make "$WORK"
scratch_state_dir "$WORK"
midi_rewrite "$WORK"

scratch_drive test/gate/display-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
echo "   running (about 46 s -- DSP is on, the beat row needs it) ..."
scratch_run "$CAP" 90 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

echo
set +e
python3 test/gate/display-assert.py < "$CAP"
rc=$?
set -e

if [ "$KEEP" -eq 1 ]; then
    echo
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
