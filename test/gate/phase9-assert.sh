#!/bin/sh
# Headless gate for the map and the output devices. No eyes, no hardware, ~8 s.
#
#   ./test/gate/phase9-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/phase9-assert.sh -v       and show the detail behind every check
#   ./test/gate/phase9-assert.sh --keep   leave the scratch dir and capture behind
#
# WHAT IT PROVES that the other gates do not: the mode table and its allowlist
# guard, both output device layers, m_404 in BOTH directions, and the rate limit.
#
# The scratch copy, the stub rewrite and its exact count, the private state
# directory, the driver generator's status check and the watchdog all live in
# lib-scratch.sh now -- this file was where most of that was written, and the
# rest of the suite has been brought up to it rather than the other way round.
set -u
# job control off, or the shell announces the watchdog's death on stderr --
# stray output is exactly what this project's other gates fail on
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

scratch_require "Cut It/u_map.pd" "Cut It/m_volca.pd" "Cut It/m_404.pd" \
                "Cut It/cut-it-map.txt"

WORK=${TMPDIR:-/tmp}/cutit-phase9-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# --- the gate's own mapping rows --------------------------------------------
# Appended rather than replacing the shipped map, so the shipped rows stay under
# test too. The static lint checks the SHIPPED file; these give the run full
# coverage of every destination and all sixteen pads.
{
    echo "mode-1 gk-cc volca-cc 41"
    echo "mode-1 gk-note volca-note 48"
    echo "mode-1 gk-prog volca-prog 5"
    n=1; while [ $n -le 16 ]; do echo "mode-1 gk-p$n 404-pad $n"; n=$((n + 1)); done
    echo "mode-1 gk-pc1 404-pad 33"
    echo "mode-1 gk-bad no-such-destination 0"
} | scratch_map_rows "$WORK"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/phase9-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
# The run is ~6 s of patch time; 40 s is generous and still bounded.
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

python3 test/gate/phase9-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
