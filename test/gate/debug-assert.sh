#!/bin/sh
# The debug patch's headless gate -- ref/module/debug.md. No eyes, no hardware, ~13 s.
#
#   ./test/gate/debug-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/debug-assert.sh -v       and show the detail behind every check
#   ./test/gate/debug-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ IT IS THE ONLY GATE THAT TESTS THE SECOND DEPLOYABLE. Everything else here
# loads main-dev.pd; "Cut It Debug" is a separate patch with no u_mother-stub, no
# disp bus and no g_oled, so it is scratch-copied and driven on its own.
#
# ⛔ AND IT IS THE ONLY GATE WHOSE SUBJECT IS A SCREEN. The debug patch has no
# bus -- the five rows it writes to mother are the entire product -- so the rows
# are what is asserted. That is not a weaker oracle for a tool whose job is to
# display four numbers.
#
# ⚠️ NO DSP, NO AUDIO AND NO REAL MIDI. -noaudio disables the audio DEVICE and
# not the graph (item 280), and this patch has no signal objects at all.
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

scratch_require "Cut It Debug/main.pd" "Cut It Debug/wire.sh" \
                "Cut It Debug/err-tail.sh" "Cut It Debug/net-probe.sh" \
                "Cut It/wire.sh"

rc=0

# ⛔ THE COPY IS CHECKED BEFORE ANY Pd RUNS, and this is the cheapest real check
# in the file. The debug patch carries its own wire.sh because at a venue the
# instrument's folder may have been moved or deleted -- that is literally step 5
# of the recover bench -- and the two menu directories are separate. But a second
# INDEPENDENT copy of nine aconnect lines is precisely the drift this project
# keeps removing, so the copy is allowed and the divergence is not.
echo "=== wire.sh is a copy, not a second implementation ==="
if cmp -s "Cut It/wire.sh" "Cut It Debug/wire.sh"; then
    echo "   identical to Cut It/wire.sh"
else
    echo "FAIL: Cut It Debug/wire.sh has diverged from Cut It/wire.sh." >&2
    echo "      The debug patch wires the rig with a COPY so it does not depend" >&2
    echo "      on the instrument's folder still existing. Two copies that differ" >&2
    echo "      is worse than either: the tool would report a rig wired one way" >&2
    echo "      while the instrument wires it another. Copy it across again:" >&2
    echo "          cp \"Cut It/wire.sh\" \"Cut It Debug/wire.sh\"" >&2
    diff "Cut It/wire.sh" "Cut It Debug/wire.sh" >&2
    rc=2
fi

WORK=${TMPDIR:-/tmp}/cutit-debug-$$
scratch_make "$WORK" "Cut It Debug"

# ⛔ THE DEBUG PATCH'S OWN THREE, NOT THE INSTRUMENT'S NINETEEN. Passing
# MIDI_EXPECT here would fail on every class the debug patch legitimately does
# not have, and dropping the count entirely would give back the "not zero" check
# that let the old phase 6 gate drift from five boxes to six in silence.
if ! midi_rewrite "$WORK" "$MIDI_DEBUG_EXPECT"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

# ⛔ t_shell IS COPIED OVER shell.pd, NOT BESIDE IT. [shell] is an EXTERNAL, so
# Pd loads it from a path and a file of that name simply wins -- which is what
# lets the fork be counted. scratch_make has already put mac-stubs/shell.pd here,
# and that one SWALLOWS the command, so without this overwrite the single most
# important assertion in the file -- that the patch wires itself -- would be
# answered by silence and pass as a failure to see anything.
cp test/stubs/t_shell.pd "$WORK/patch/shell.pd" || exit 2

scratch_drive test/gate/debug-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main.pd" "$WORK/drive.pd"

echo
python3 test/gate/debug-assert.py $ARGS < "$CAP" || rc=1

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
