#!/bin/sh
# The boot sequence's headless gate -- ref/module/boot.md. No eyes, no hardware, ~10 s.
#
#   ./test/gate/init-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/init-assert.sh -v       and show the detail behind every check
#   ./test/gate/init-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ ref/module/boot.md USED TO DECLARE `Gate: test/run.sh`, the whole runner --
# the only page naming something that is not a gate. It was honest that nothing
# covered u_init specifically and misleading about what was covering it: every
# gate loads the patch, so every gate proved the boot does not ERROR, and not one
# proved it happens in the right ORDER.
#
# ⚠️ NO DSP. Every stage is a message on a timer.
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

scratch_require "Cut It/u_init.pd" "Cut It/wire.sh" "test/stubs/t_shell.pd"

WORK=${TMPDIR:-/tmp}/cutit-init-$$
scratch_make "$WORK"
scratch_state_dir "$WORK"

# ⛔ THE COUNTING SHELL STUB, COPIED UNDER THE NAME PD WILL LOOK FOR. [shell] is
# an EXTERNAL, not a built-in, so unlike ctlin and midiout it resolves from the
# search path and a file of that name simply wins -- no box rewriting needed.
# scratch_make has already put mac-stubs/shell.pd here, which deliberately
# SWALLOWS the command so a syntax check stays silent; this one reports it so the
# gate can count it.
#
# ⚠️ THE RENAME HAPPENS HERE AND NOWHERE ELSE. The repo copy stays t_shell.pd
# because a file named shell.pd anywhere is a live hazard: reaching the patch
# folder on the device it would shadow the real external and every aconnect in
# wire.sh would silently stop happening.
cp test/stubs/t_shell.pd "$WORK/patch/shell.pd" || {
    echo "FAIL: could not install the counting shell stub." >&2
    echo "      Without it mac-stubs/shell.pd swallows the command and the" >&2
    echo "      wire.sh assertions are answered by silence." >&2
    exit 2
}

# ⛔ SEED BOTH STATE FILES. The restore is u_init's last outlet, and against
# empty files it publishes nothing at all -- so "the restore fired" would be
# answered by silence, which is also what a restore that never fired looks like.
# ⚠️ manual FIRST in the analyser's expectation, because u_state replays the
# manual store before the auto one: the trigger's right outlet fires first.
echo "init-mprobe 7" > "$WORK/state/cut-it-manual.txt"
echo "init-probe 42" > "$WORK/state/cut-it-auto.txt"

if ! midi_rewrite "$WORK"; then
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi

scratch_drive test/gate/init-assert-drive-gen.py "$WORK/drive.pd"

CAP="$WORK/capture.txt"
# ⛔ THE DRIVER LOADS FIRST HERE, AND IT IS THE ONLY GATE THAT DOES. Pd opens
# these in order, so a driver named second has its [r disp] taps created AFTER
# main-dev.pd's loadbang has already fired -- and u_init's FIRST stage is at
# loadbang. Named second, this gate saw four stages instead of five and one
# midiInGate instead of two, and every one of those absences looked exactly like
# the patch not doing it. Every other gate gets away with the usual order because
# its first window opens at 300 ms and it drives what it asserts.
scratch_run "$CAP" 40 -nogui -noaudio -nomidi -path "$WORK/patch" \
    "$WORK/drive.pd" "$WORK/patch/main-dev.pd"

python3 test/gate/init-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
