#!/bin/sh
# The OLED's headless gate -- ref/module/display.md. No eyes, no hardware, ~21 s.
#
#   ./test/gate/oled-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/oled-assert.sh -v       and show the detail behind every check
#   ./test/gate/oled-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ g_oled IS THE DENSEST FILE IN THE PATCH AND ITS ENTIRE COVERAGE WAS THAT THE
# FILE EXISTS. 783 lines, four layers with priorities and time-to-live, a
# five-row parameter store with its own ageing -- all of it judged by eye off a
# panel until now.
#
# ⚠️ WHAT MADE IT TESTABLE IS THE TAP ON oscOut. Pd cannot ask a screen what it is
# showing, but every byte sent to it is knowable. u_mother-stub has decoded that
# same stream into eight preview rows since Phase 3, so the arithmetic was
# already debugged; the analyser reimplements the parse in Python.
#
# ⚠️ NO DSP. The frame clock is a [metro 100] and every layer is messages. The
# meters have nothing to say without audio, which costs this gate nothing --
# their geometry is the one part of the page a person still has to judge.
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

scratch_require "Cut It/g_oled.pd"

WORK=${TMPDIR:-/tmp}/cutit-oled-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# ⚠️ THE REWRITE IS NOT FOR THIS GATE'S BENEFIT -- g_oled emits no MIDI.
# It runs because every scratch-copy gate enforces the whole inventory, so a new
# emitter cannot be added anywhere without some gate going red.
if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/oled-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 55 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/oled-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
