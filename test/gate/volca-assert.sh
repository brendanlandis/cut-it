#!/bin/sh
# The Volca's headless gate -- ref/device/volca.md. No eyes, no hardware, ~5 s.
#
#   ./test/gate/volca-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/volca-assert.sh -v       and show the detail behind every check
#   ./test/gate/volca-assert.sh --keep   leave the scratch dir and capture behind
#
# It is the smallest gate here because m_volca is the smallest m_ layer: three
# destinations onto one channel. ⛔ The one place it is not obvious is pgmout,
# which is 1-based on its inlet and 0-based on the wire -- item 228.
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

scratch_require "Cut It/m_volca.pd" "Cut It/cut-it-map.txt"

WORK=${TMPDIR:-/tmp}/cutit-volca-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

{
    echo "mode-1 gk-cc volca-cc 41"
    echo "mode-1 gk-note volca-note 48"
    echo "mode-1 gk-prog volca-prog 5"
    echo "mode-1 gk-key volca-key 60"
} | scratch_map_rows "$WORK"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/volca-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/volca-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
