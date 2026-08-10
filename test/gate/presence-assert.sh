#!/bin/sh
# Device presence and the bounded re-wire -- ref/module/presence.md. No eyes, no
# hardware.
#
#   ./test/gate/presence-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/presence-assert.sh -v       and show the detail behind every check
#   ./test/gate/presence-assert.sh --keep   leave the scratch dirs and captures behind
#
# ⛔ IT IS THE ONLY GATE WHOSE STIMULUS IS A SILENCE. Every other gate here pushes
# something in and reads something out. This one withholds the device-inquiry
# reply and asserts on what the patch does about it -- which is the absent-at-load
# case of item 235, the one the Launchpad watchdog was built unable to handle.
#
# ⛔ AND IT IS TWO Pd RUNS, ONE TALLY. The first is the schedule at the shipped
# tick. The second scales u_present's settle and tick by ten -- and NOT its
# counts -- so the eighth attempt and the give-up actually happen, inside nine
# seconds instead of seventy-two. One analyser reads both captures, because two
# would print two `N checks` lines and that number is what proves no assertion
# went missing.
#
# ⚠️ A SILENCE IS ALSO WHAT A BROKEN SCRATCH COPY PRODUCES, so the analyser opens
# with two liveness witnesses -- u_init's own four shell forks, and the fact that
# anything reached [midiout] at all -- and refuses to score the run without them.
#
# ⚠️ NO DSP. g_grid's frame clock is a plain [metro 20] and every stage of the
# watchdog is a message on a timer, so nothing here needs audio.
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

# g_grid is required and not by accident: it is the only readable evidence of
# surface OWNERSHIP. m_launchpad keeps that in a $0- send, so the one way to see
# it from outside is that the grid does or does not paint.
scratch_require "Cut It/m_launchpad.pd" "Cut It/g_grid.pd" "Cut It/wire.sh" \
                "test/stubs/t_shell.pd" "test/stubs/t_sysexin.pd"

WORK=${TMPDIR:-/tmp}/cutit-presence-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"
# ⛔ THE HEARTBEAT FIRES EVERY TICK IN THIS COPY, so "it runs while nothing is
# lost" is observable in every window rather than wherever 16 s happens to
# land in a 40 s run. The SHIPPED interval is asserted statically below.
scratch_watch_fast "$WORK"

# ⛔ THE COUNTING SHELL STUB, COPIED UNDER THE NAME PD WILL LOOK FOR -- the same
# trick init-assert.sh uses, and for the same reason. [shell] is an EXTERNAL, so
# it resolves from the search path and a file of that name simply wins.
# scratch_make has already put mac-stubs/shell.pd here, which SWALLOWS the
# command so a syntax check stays silent; this one reports it so the gate can
# count the re-wires, which are the entire subject.
cp test/stubs/t_shell.pd "$WORK/patch/shell.pd" || {
    echo "FAIL: could not install the counting shell stub." >&2
    echo "      Without it mac-stubs/shell.pd swallows the command and every" >&2
    echo "      re-wire assertion is answered by silence -- which is also what" >&2
    echo "      the bug looks like." >&2
    exit 2
}

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/presence-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
echo "   running the schedule (about 38 s -- the three re-wires are at 14 s, 22 s and 30 s) ..."
scratch_run "$CAP" 60 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/patch/main-dev.pd" "$WORK/drive.pd"

# ---------------------------------------------------------------------------
# ⛔ THE SECOND RUN, AND IT IS THE ONLY ONE THAT REACHES THE BOUND. The run above
# proves the INTERVAL and the COALESCING inside 38 s; it never sees tick 33,
# because at the shipped tick the give-up is 72 seconds away. So "eight attempts
# and then it stops" was arithmetic read off [moses 33] rather than anything a
# gate had watched happen.
#
# ⛔ A SECOND SCRATCH COPY, NOT THE FIRST ONE REWRITTEN. Two reasons, and the
# first is enough on its own: scaling u_root.pd would change the patch the run
# above is still being judged against. The second is item 232 -- the run above
# sets a mode, u_state flushes it, and u_init would restore it into this run at
# what is now the middle of the recovery.
WORK2=${TMPDIR:-/tmp}/cutit-presence-bound-$$
scratch_make "$WORK2"
scratch_state_dir "$WORK2"
scratch_scale_present "$WORK2"

cp test/stubs/t_shell.pd "$WORK2/patch/shell.pd" || {
    echo "FAIL: could not install the counting shell stub for the bound run." >&2
    exit 2
}

# ⚠️ THE FULL REWRITE, EVEN THOUGH THIS RUN DRIVES NO MIDI AT ALL. It costs
# nothing -- a stub only prints -- and it means the second copy enforces
# MIDI_EXPECT exactly like the first, so a new emitter cannot slip in behind a
# gate that happens to make two copies.
if ! midi_rewrite "$WORK2"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK $WORK2"
    exit 2
fi

scratch_drive test/gate/presence-bound-drive-gen.py "$WORK2/drive.pd"

CAP2="$WORK2/capture.txt"
echo "   running the bound (about 9 s -- the eighth fork is at 7 s and the give-up at 7.2) ..."
scratch_run "$CAP2" 30 -nogui -noaudio -nomidi -path "$WORK2/patch" \
    "$WORK2/patch/main-dev.pd" "$WORK2/drive.pd"

echo
python3 test/gate/presence-assert.py $ARGS --bound "$CAP2" < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "captures kept at $CAP and $CAP2"
else
    rm -rf "$WORK" "$WORK2"
fi
exit $rc
