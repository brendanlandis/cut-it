#!/bin/sh
# Panic's second tier -- ref/module/map.md and ref/module/boot.md. ~20 s.
#
#   ./test/gate/recover-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/recover-assert.sh -v       and show the detail behind every check
#   ./test/gate/recover-assert.sh --keep   leave the scratch dirs and captures
#
# ⛔ ITS CORE IS UNTESTABLE ON A MAC, AND SAYING SO IS PART OF THE GATE. [shell]
# is stubbed here, so nothing is sent to mother and no patch is loaded. What this
# proves is that the right command was FORMED, in the right order, behind the
# silence -- plus a static lint of recover.sh that needs no Pd at all and is the
# strongest half. THE RELOAD ITSELF IS A BENCH STEP. See recover-assert.py's
# header for the three things it deliberately cannot claim.
#
# ⛔ TWO RUNS, TWO SCRATCH TREES, AND THE ONLY DIFFERENCE IS WHAT IS ON DISK.
# Run A boots clean and drives the button. Run B boots with a breadcrumb already
# there -- the state the next boot after a real recover is in.
#
# ⚠️ TWO WORK DIRS, NEVER ONE REUSED. u_state restores at about 3.5 s from the
# state directory the previous run wrote, and a leftover mode changes what the
# map does mid-run. Item 232.
#
# ⚠️ DSP is not needed -- every path here is a message on a timer.
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

scratch_require "Cut It/u_map.pd" "Cut It/u_init.pd" "Cut It/recover.sh" \
                "test/stubs/t_shell.pd"

WORK=${TMPDIR:-/tmp}/cutit-recover-$$

# $1 = work dir, $2 = a|b, $3 = capture path
build_run() {
    _w=$1
    scratch_make "$_w"
    scratch_state_dir "$_w"

    # ⛔ THE COUNTING SHELL STUB. [shell] is an EXTERNAL, so it resolves from the
    # search path and a file of that name simply wins -- no box rewriting needed.
    # scratch_make has already put mac-stubs/shell.pd here, which SWALLOWS the
    # command; this one reports it, which is the only way to see the fork at all.
    # ⚠️ The rename happens here and nowhere else: a file named shell.pd reaching
    # the patch folder on the device would shadow the real external and every
    # aconnect in wire.sh would silently stop happening.
    cp test/stubs/t_shell.pd "$_w/patch/shell.pd" || {
        echo "FAIL: could not install the counting shell stub." >&2
        echo "      Without it every fork assertion is answered by silence." >&2
        return 2
    }

    # state-dir.sh does not run on a Mac, so the files it would touch are made
    # by hand -- the same workaround every state-reading gate uses.
    : > "$_w/state/cut-it-auto.txt"
    : > "$_w/state/cut-it-manual.txt"

    if [ "$2" = "b" ]; then
        # ⛔ THE ONLY DIFFERENCE BETWEEN THE RUNS. An armed breadcrumb, and a
        # knobs.txt beside it so that pickup has something to arm -- without the
        # second file nothing would be held even without a breadcrumb, and the
        # override would be proved by a knob that was never captured.
        echo "recover 8123.4" > "$_w/state/cut-it-recover.txt"
        printf '0.0957967 0.5 0.5 0.5;\n' > "$_w/patch/knobs.txt"
    else
        : > "$_w/state/cut-it-recover.txt"
    fi

    midi_rewrite "$_w" > "$_w/inventory.txt" || {
        cat "$_w/inventory.txt"
        return 2
    }

    scratch_drive test/gate/recover-assert-drive-gen.py "$_w/drive.pd" "$2"
    scratch_run "$3" 40 -nogui -noaudio -nomidi -path "$_w/patch" \
        "$_w/patch/main-dev.pd" "$_w/drive.pd"
}

CAP_A="$WORK/a/capture.txt"
CAP_B="$WORK/b/capture.txt"

build_run "$WORK/a" a "$CAP_A" || { [ "$KEEP" = "1" ] && echo "kept $WORK"; exit 2; }
cat "$WORK/a/inventory.txt"
build_run "$WORK/b" b "$CAP_B" || { [ "$KEEP" = "1" ] && echo "kept $WORK"; exit 2; }

python3 test/gate/recover-assert.py $ARGS \
    --runb "$CAP_B" --crumb "$WORK/b/state/cut-it-recover.txt" \
    --crumb-a "$WORK/a/state/cut-it-recover.txt" < "$CAP_A"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "captures kept at $CAP_A and $CAP_B"
else
    rm -rf "$WORK"
fi
exit $rc
