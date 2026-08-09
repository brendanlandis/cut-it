#!/bin/sh
# The nanoKONTROL's headless gate -- ref/device/nanokontrol.md. No eyes, no
# hardware, ~17 s.
#
#   ./test/gate/nano-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/nano-assert.sh -v       and show the detail behind every check
#   ./test/gate/nano-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ IT IS THE FIRST GATE THAT COULD NOT EXIST BEFORE t_ctlin. m_nano is the main
# control surface of the instrument and it had no headless coverage at all,
# because every one of its paths sits behind [ctlin] and there is no bus behind a
# MIDI input. lib-scratch.sh carried a ⬜ naming that stub as the blocker.
#
# ⚠️ NO DSP. Nothing here needs a clock: every assertion is about decoding a
# controller number into a name and putting it on two buses.
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

# ⛔ m_404 AND m_launchpad ARE REQUIRED HERE TOO, and not by accident: the last
# two windows drive their channel blocks through the same t-ctlin, which is what
# gives "the nano's channel produces nothing of theirs" a liveness witness.
scratch_require "Cut It/m_nano.pd" "Cut It/m_404.pd" "Cut It/m_launchpad.pd" \
                "test/stubs/t_ctlin.pd"

WORK=${TMPDIR:-/tmp}/cutit-nano-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/nano-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/nano-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
