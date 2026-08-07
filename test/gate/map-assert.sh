#!/bin/sh
# The map's headless gate -- ref/module/map.md. No eyes, no hardware, ~7 s.
#
#   ./test/gate/map-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/map-assert.sh -v       and show the detail behind every check
#   ./test/gate/map-assert.sh --keep   leave the scratch dir and capture behind
#
# HALF OF IT NEEDS NO Pd AT ALL -- the static lint reads cut-it-map.txt against
# the literal route box in u_map.pd, in about 200 ms, and that is the strongest
# check in the suite. The driven half tests the LOOKUP: that a control maps at
# load, that the same control maps differently in another mode, and that a row
# naming a destination off the route is silent and says why.
#
# ⚠️ WHAT A DESTINATION DOES WITH THE VALUE IS NOT TESTED HERE. That belongs to
# volca-assert.sh and sp404-assert.sh. This gate uses volca-cc only because a
# lookup has to land somewhere.
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

scratch_require "Cut It/u_map.pd" "Cut It/cut-it-map.txt"

WORK=${TMPDIR:-/tmp}/cutit-map-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# The gate's own rows, APPENDED so the shipped rows stay under test too. The
# static lint checks the SHIPPED file; these give the run a destination that
# exists and one that does not.
{
    echo "mode-1 gk-cc volca-cc 41"
    echo "mode-1 gk-bad no-such-destination 0"
} | scratch_map_rows "$WORK"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/map-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/map-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
