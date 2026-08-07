#!/bin/sh
# Headless regression gate for the Launchpad grid. Asserts on what the patch
# ACTUALLY emits, with no hardware and nobody watching. ~45 s.
#
#     ./test/gate/phase6-assert.sh            # run it
#     ./test/gate/phase6-assert.sh --keep     # and leave the capture behind to read
#
# ⚠️ DSP IS ON AND THERE IS NO -noaudio. The beat row hangs off threshold~, so a
# silent run would assert on a grid that never moves. That is the whole reason
# this gate costs 45 s where the others cost 8.
#
# Everything else -- the scratch copy, the stub rewrite and its exact count, the
# private state directory, the driver generator and the watchdog -- comes from
# lib-scratch.sh, which is shared with every other MIDI gate. ⛔ IT USED TO HAVE
# ITS OWN WEAKER COPY OF ALL OF THAT: an anchored regex that skipped boxes with
# creation arguments, a count checked only for being non-zero, a driver that was
# never regenerated so edits to its generator did nothing, and no state directory
# of its own. See lib-scratch.sh for what each of those cost.
set -e

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
WORK=${TMPDIR:-/tmp}/cutit-phase6-$$
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

scratch_require "Cut It/g_grid.pd" "Cut It/m_launchpad.pd" "Cut It/main-dev.pd"

scratch_make "$WORK"
scratch_state_dir "$WORK"
midi_rewrite "$WORK"

scratch_drive test/gate/phase6-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
echo "   running (about 45 s -- DSP is on, the beat row needs it) ..."
scratch_run "$CAP" 90 -nogui -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

echo
set +e
python3 test/gate/phase6-assert.py < "$CAP"
rc=$?
set -e

if [ "$KEEP" -eq 1 ]; then
    echo
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
