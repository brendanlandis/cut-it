#!/bin/sh
# c_clock's headless gate -- ref/module/tempo.md. No eyes, no hardware, ~17 s.
#
#   ./test/gate/clock-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/clock-assert.sh -v       and show the detail behind every check
#   ./test/gate/clock-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ THE RATIO ARGUMENT WAS ONLY EVER HUMAN-READ OFF A BENCH PRINT. tempo-assert
# covers u_tempo and names c_clock in a comment; ref/module/tempo.md declares one
# gate for a page whose Files line holds two abstractions. This is the second.
#
# ⛔ IT LOADS A HARNESS RATHER THAN main-dev.pd, and that is the whole shape of
# it: c_clock publishes on no bus -- its output is four outlets -- so there is
# nothing to tap, and only a [print] wired to an outlet can see it. Three
# instances, no instrument around them, nothing else running.
#
# ⚠️ IT NEEDS DSP, so -noaudio is deliberately absent. The beat is threshold~ on a
# wrap~ of a phasor~: without DSP nothing ticks and every count comes back 0.
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

scratch_require "Cut It/c_clock.pd"

WORK=${TMPDIR:-/tmp}/cutit-clock-$$
scratch_make "$WORK"

# ⚠️ NO scratch_state_dir AND NO midi_rewrite HERE, and both omissions are
# deliberate rather than forgotten. Nothing in this run loads u_state or any m_
# layer -- the harness instantiates c_clock and nothing else -- so there is no
# state file to own and no MIDI object anywhere to rewrite. Adding either would
# be ceremony that implies a coupling this gate does not have.

scratch_drive test/gate/clock-assert-drive-gen.py "$WORK/drive.pd" "$WORK/harness.pd"

# ⛔ scratch_drive ONLY CHECKS ITS FIRST OUTPUT. This generator writes two files
# and a missing harness is the worst kind of failure: Pd loads a driver that
# talks to nothing, every count comes back 0, and the gate reports a stopped
# clock with total confidence.
[ -f "$WORK/harness.pd" ] || {
    echo "FAIL: the generator wrote no harness to $WORK/harness.pd." >&2
    echo "      Without it the driver drives nothing, every count is 0, and" >&2
    echo "      the gate would report a dead clock rather than a broken test." >&2
    exit 2
}

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -nomidi -path "$WORK/patch" \
    "$WORK/harness.pd" "$WORK/drive.pd"

python3 test/gate/clock-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
