#!/bin/sh
# The audio path's headless gate -- ref/module/audio.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/audio-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/audio-assert.sh -v       and show the detail behind every check
#   ./test/gate/audio-assert.sh --keep   leave the scratch dir, the capture and the wav
#
# ⛔ THE FIRST SIGNAL-DOMAIN GATE IN THIS PROJECT. Every other one asserts on
# MESSAGES and nothing had ever read a signal back, which is why
# ref/module/audio.md declared `Gate: none` honestly. The audio path is six boxes
# and four `#X connect` lines at the end of u_root.pd, a broken rewiring there is
# completely silent, and it would surface as no sound at a venue.
#
# ⛔ IT LOADS A HARNESS HOLDING u_root ALONE, NOT main-dev.pd. catch~ must be
# uniquely defined and u_mother-stub already holds catch~ outL and catch~ outR,
# so a second pair beside it would simply fail to create and the recording would
# be silent -- the worst possible failure, since silence is also what a broken
# audio path looks like.
#
# ⚠️ NO -noaudio, AND THAT IS THE WHOLE POINT. The subject is a signal.
set -u
set +m 2>/dev/null || true

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
KEEP=0
ARGS=""
for a in "$@"; do
    case "$a" in
        --keep) KEEP=1 ;;
        *) ARGS="$ARGS $a" ;;
    esac
done

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

scratch_require "Cut It/u_root.pd" "Cut It/u_level.pd"

WORK=${TMPDIR:-/tmp}/cutit-audio-$$
scratch_make "$WORK"

# ⚠️ NO scratch_state_dir HERE, and no midi_rewrite either. This gate does not
# load main-dev.pd, so there is no `u_root 17 1 /tmp` line to rewrite -- the
# harness is GENERATED and is handed the private directory as a creation
# argument instead. The MIDI rewrite is skipped because nothing in this run
# reads or asserts a MIDI byte; the inventory is enforced by six other gates.
mkdir -p "$WORK/state" || exit 2

WAV="$WORK/out.wav"
scratch_drive test/gate/audio-assert-drive-gen.py "$WORK/drive.pd" \
    "$WORK/harness.pd" "$WORK/state" "$WAV"

[ -f "$WORK/harness.pd" ] || {
    echo "FAIL: the generator wrote no harness to $WORK/harness.pd." >&2
    echo "      Without it nothing instantiates u_root, nothing records, and" >&2
    echo "      the gate would report a silent audio path rather than a" >&2
    echo "      broken test." >&2
    exit 2
}

CAP="$WORK/capture.txt"
scratch_run "$CAP" 45 -nogui -nomidi -path "$WORK/patch" \
    "$WORK/harness.pd" "$WORK/drive.pd"

# ⛔ THE ANALYSER READS THE WAV, NOT stdin. It is the only one here that does,
# because it is the only one whose subject is samples rather than messages. The
# capture goes with it so u_level's disp reports -- the other file on the page --
# can be asserted in the same run.
python3 test/gate/audio-assert.py "$WAV" "$CAP" $ARGS
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "kept $WORK (capture, harness and $WAV)"
else
    rm -rf "$WORK"
fi
exit $rc
