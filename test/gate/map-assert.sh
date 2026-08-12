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

# The gate's own rows, APPENDED so the shipped rows stay under test too. The
# static lint checks the SHIPPED file; these give the run a destination that
# exists and one that does not.
#
# ⛔ gk-diag IS HERE BECAUSE NO SHIPPED ROW NAMES diag YET. The destination
# and its handler exist on u_map's route -- which is what the static lint
# above reads -- but which physical control summons the diagnostic screen is
# a decision about the panel that has not been made. A gate row is what keeps
# the path EXERCISED in the meantime, so the day a row is added it is a line
# of a text file rather than a line of Pd nobody has ever run.
#
# ⛔ og-knob-2 AND og-knob-3 ARE HERE FOR PICKUP, and they must be DISTINCT CC
# numbers. Both windows below send two values to a knob and count what comes out
# -- one expects exactly one event and the other expects two -- so a leak between
# them has to be visible as a different controller, not as a duplicate.
gate_rows() {
    echo "mode-1 gk-cc volca-cc 41"
    echo "mode-1 gk-bad no-such-destination 0"
    echo "mode-1 og-knob-2 volca-cc 42"
    echo "mode-1 og-knob-3 volca-cc 43"
    echo "mode-1 og-knob-4 volca-cc 44"
    echo "mode-1 gk-diag diag 0"
}

# ⛔ THE GATE RUNS TWICE, AND THE ONLY DIFFERENCE IS ONE FILE. Pickup arms a knob
# because mother replayed a SAVED position; it must NOT arm when mother pushed
# the knob's LIVE position, which is what happens when no Save has ever run.
# u_map tells the two apart by reading knobs.txt at load, so the branch is
# selected here by creating that file or not -- the real path either way, on both
# machines, with no stub answering for it. Item 239.
#
# ⚠️ TWO WORK DIRS, NOT ONE REUSED. u_state restores at about 3.5 s from the
# state directory the run before it wrote, and that is item 232 -- a mode left
# behind changes what the map does mid-run and half the windows go quiet.
build_run() {
    # $1 = work dir, $2 = "save" (a knobs.txt exists) or "nosave", $3 = capture
    _w=$1
    scratch_make "$_w"
    scratch_state_dir "$_w"
    gate_rows | scratch_map_rows "$_w"
    midi_rewrite "$_w" > "$_w/inventory.txt" || {
        cat "$_w/inventory.txt"
        return 2
    }
    [ "$2" = "save" ] && printf '0.0957967 0.5 0.5 0.5;\n' > "$_w/patch/knobs.txt"

    scratch_drive test/gate/map-assert-drive-gen.py "$_w/drive.pd"
    scratch_run "$3" 40 -nogui -noaudio -nomidi -path "$_w/patch" \
        "$_w/patch/main-dev.pd" "$_w/drive.pd"
}

CAP="$WORK/save/capture.txt"
CAP2="$WORK/nosave/capture.txt"

build_run "$WORK/save" save "$CAP" || { [ "$KEEP" = "1" ] && echo "kept $WORK"; exit 2; }
cat "$WORK/save/inventory.txt"
build_run "$WORK/nosave" nosave "$CAP2" || { [ "$KEEP" = "1" ] && echo "kept $WORK"; exit 2; }

python3 test/gate/map-assert.py $ARGS --nosave "$CAP2" < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "captures kept at $CAP and $CAP2"
else
    rm -rf "$WORK"
fi
exit $rc
