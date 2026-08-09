#!/bin/sh
# The error bus's headless gate -- ref/module/error.md. No eyes, no hardware, ~12 s.
#
#   ./test/gate/err-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/err-assert.sh -v       and show the detail behind every check
#   ./test/gate/err-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ ITS CENTRAL CLAIM WAS BENCH PROSE ONLY: that perform mode suppresses warn and
# never suppresses fail. u_err's spigot is on the warn branch and fail is
# unspigoted -- one cord -- and nothing on the instrument would report it being
# wrong. The display would just go quiet, at a venue.
#
# ⚠️ NO DSP AND NO MIDI. The first half of the analyser needs no Pd at all: it is
# a static lint over every error message box in the patch, which is where C-12's
# 21-character limit actually lives.
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

scratch_require "Cut It/u_err.pd"

WORK=${TMPDIR:-/tmp}/cutit-err-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# ⚠️ THE REWRITE IS NOT FOR THIS GATE'S BENEFIT -- u_err emits no MIDI.
# It runs because every scratch-copy gate enforces the whole inventory, so a new
# emitter cannot be added anywhere without some gate going red.
if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/err-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 30 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/err-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
