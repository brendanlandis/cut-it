#!/bin/sh
# The Organelle front panel's headless gate -- ref/device/organelle.md.
# No eyes, no hardware, ~12 s.
#
#   ./test/gate/organelle-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/organelle-assert.sh -v       and show the detail behind every check
#   ./test/gate/organelle-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ m_organelle HAD ZERO REFERENCES IN ANY GATE, and its page declared
# `Gate: none` honestly. It is the cheapest m_ layer to cover of the lot: five
# [r] boxes on mother's own names is the whole input surface, so unlike m_nano it
# needed no stub -- only somebody to write the driver.
#
# ⚠️ NO DSP AND NO MIDI. Nothing here needs a clock or a wire.
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

scratch_require "Cut It/m_organelle.pd"

WORK=${TMPDIR:-/tmp}/cutit-organelle-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# ⚠️ THE REWRITE IS NOT FOR THIS GATE'S BENEFIT -- m_organelle emits no MIDI.
# It runs because every scratch-copy gate enforces the whole inventory, so a new
# emitter cannot be added anywhere without some gate going red.
if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/organelle-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 30 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/organelle-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
