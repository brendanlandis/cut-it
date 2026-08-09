#!/bin/sh
# The aux LED's headless gate -- ref/device/organelle.md. No eyes, no hardware, ~11 s.
#
#   ./test/gate/led-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/led-assert.sh -v       and show the detail behind every check
#   ./test/gate/led-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ g_led HAD ZERO REFERENCES ANYWHERE UNDER test/ BEFORE THIS FILE. Its page
# named display-assert.sh, which asserts on Launchpad SysEx and never touches the
# LED -- so the one display surface in the rig that is not a screen was the least
# covered thing in the patch while looking covered.
#
# ⚠️ NO DSP AND NO MIDI. g_led is 34 lines of route and four message boxes.
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

scratch_require "Cut It/g_led.pd"

WORK=${TMPDIR:-/tmp}/cutit-led-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# ⚠️ THE REWRITE IS NOT FOR THIS GATE'S BENEFIT -- g_led emits no MIDI at all.
# It runs because every scratch-copy gate enforces the whole inventory, so a new
# emitter cannot be added anywhere without some gate going red.
if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/led-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 30 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/led-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
