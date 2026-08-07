#!/bin/sh
# The SP-404's headless gate -- ref/device/sp404.md. No eyes, no hardware, ~7 s.
#
#   ./test/gate/sp404-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/sp404-assert.sh -v       and show the detail behind every check
#   ./test/gate/sp404-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ THE ONLY GATE HERE THAT TESTS A DEVICE IN BOTH DIRECTIONS. Every output path
# can be driven from a bus, but m_404's whole receive side sits behind [notein]
# and NO BUS REACHES A MIDI INPUT -- which is why t_notein exists and why the
# driver sends bare `t-notein` messages into the scratch copy.
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

scratch_require "Cut It/m_404.pd" "Cut It/cut-it-map.txt"

WORK=${TMPDIR:-/tmp}/cutit-sp404-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# All sixteen pads of bank A, plus one in bank C -- the bank is what chooses the
# channel, and a gate that only ever drove bank A could not see that.
{
    n=1; while [ $n -le 16 ]; do echo "mode-1 gk-p$n 404-pad $n"; n=$((n + 1)); done
    echo "mode-1 gk-pc1 404-pad 33"
} | scratch_map_rows "$WORK"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/sp404-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/sp404-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
