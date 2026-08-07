#!/bin/sh
# Phase 9's headless gate. No eyes, no hardware, ~8 s.
#
#   ./test/gate/phase9-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/phase9-assert.sh -v       and show the detail behind every check
#   ./test/gate/phase9-assert.sh --keep   leave the scratch dir and capture behind
#
# WHAT IT PROVES that the other three do not: the mode table and its allowlist
# guard, both output device layers, m_404 in BOTH directions, and the rate limit.
#
# It follows phase6-assert.sh's shape -- a scratch copy of "Cut It/" with the
# MIDI objects rewritten to printing stubs -- because a built-in class has no
# side channel and Pd resolves the class table before it looks for a file.
# "Cut It/" is never touched.
#
# ⛔ THREE THINGS PHASE 6's GATE GETS WRONG, AND THIS ONE MUST NOT:
#
#   1. It rewrites [midiout] ONLY. m_volca and m_404 emit through noteout,
#      ctlout and pgmout, so phase 6's rewrite finds nothing in them and every
#      assertion about them would pass VACUOUSLY.
#   2. Its regex is ANCHORED so the class name must end the line, which silently
#      skips any box carrying creation arguments. The patch has one:
#      [ctlout 123 33] in u_tempo. This one takes a trailing argument list.
#   3. It only checks that the rewrite count is non-zero. Its own comment claims
#      five where the patch has six -- the count drifted and nothing noticed.
#      This one asserts an EXACT count per class.
#
# ⛔ AND ONE THING NO GATE HERE HAD DONE BEFORE: IT OWNS ITS STATE DIRECTORY.
# main-dev.pd passes /tmp, which every run on the machine shares, and u_init
# restores saved state at about 3.5 s. A previous test that changed mode leaves
# it in that file, the restore republishes it mid-run, and every row keyed to
# another mode stops matching from that instant. That cost a wrong diagnosis
# once already -- item 232.
set -u
# job control off, or the shell announces the watchdog's death on stderr --
# stray output is exactly what this project's other gates fail on
set +m 2>/dev/null || true

cd "$(dirname "$0")/../.."

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

for f in "Cut It/u_map.pd" "Cut It/m_volca.pd" "Cut It/m_404.pd" "Cut It/cut-it-map.txt"; do
    if [ ! -f "$f" ]; then
        echo "$f does not exist yet."
        echo "That is a real failure, not a skip: the gate is meant to be built"
        echo "BEFORE the abstraction, so its first run fails for a known reason."
        exit 2
    fi
done

WORK=${TMPDIR:-/tmp}/cutit-phase9-$$
mkdir -p "$WORK/state"
cp -R "Cut It" "$WORK/patch"
cp test/stubs/t_noteout.pd test/stubs/t_ctlout.pd \
   test/stubs/t_pgmout.pd test/stubs/t_notein.pd "$WORK/patch/"
cp mac-stubs/*.pd "$WORK/patch/" 2>/dev/null || true

# state-dir.sh runs through [shell], which is a no-op stub on the Mac, so the
# two files have to be made here or u_state prints on every run.
: > "$WORK/state/cut-it-auto.txt"
: > "$WORK/state/cut-it-manual.txt"

# --- point the scratch copy at a PRIVATE, EMPTY state directory --------------
sed -i '' "s|u_root 17 1 /tmp |u_root 17 1 $WORK/state |" "$WORK/patch/main-dev.pd"
grep -q "u_root 17 1 $WORK/state " "$WORK/patch/main-dev.pd" || {
    echo "FAIL: could not repoint main-dev.pd's state directory." >&2
    echo "      Without that, a previous run's saved mode changes what the map" >&2
    echo "      does at 3.5 s and half the windows go silent -- item 232." >&2
    exit 2
}

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
} >> "$WORK/patch/cut-it-map.txt"

# --- rewrite the MIDI objects, ARGUMENTS AND ALL -----------------------------
EXPECT="noteout:2 ctlout:2 pgmout:1 notein:2"
rc=0
for spec in $EXPECT; do
    cls=${spec%%:*}; want=${spec##*:}
    got=0
    for f in "$WORK"/patch/*.pd; do
        case "$(basename "$f")" in t_*) continue ;; esac
        c=$(grep -cE "^#X obj [0-9]+ [0-9]+ $cls( [^;]*)?;$" "$f" 2>/dev/null || true)
        [ "$c" = "0" ] && continue
        sed -i '' "s/^\(#X obj [0-9]* [0-9]*\) $cls\( [^;]*\)\{0,1\};\$/\1 t_$cls\2;/" "$f"
        got=$((got + c))
    done
    if [ "$got" != "$want" ]; then
        echo "FAIL: expected $want [$cls] box(es), found $got." >&2
        echo "      A LOWER count means assertions have gone vacuous; a HIGHER one" >&2
        echo "      means a new MIDI emitter the gate does not know about." >&2
        echo "      Update EXPECT in this script deliberately, never silently." >&2
        rc=2
    else
        echo "   $got [$cls] -> [t_$cls]"
    fi
done
[ "$rc" = "0" ] || { [ "$KEEP" = "1" ] && echo "kept $WORK"; exit $rc; }

# ⛔ CHECK THE GENERATOR SUCCEEDED. It was not checked once, and the failure mode
# is the worst kind: the driver is never written, Pd loads a file that does not
# exist, the "; pd quit" that lives in that file never fires, and the gate HANGS
# FOREVER instead of failing. A gate that hangs is worse than one that fails.
if ! python3 test/gate/phase9-assert-drive-gen.py "$WORK/drive.pd" >/dev/null; then
    echo "FAIL: the driver generator errored -- see the traceback above." >&2
    [ "$KEEP" = "1" ] && echo "kept $WORK"
    exit 2
fi
[ -f "$WORK/drive.pd" ] || { echo "FAIL: no driver was written." >&2; exit 2; }

CAP="$WORK/capture.txt"
# ... and a watchdog, so that no future variant of the same mistake can hang.
# The run is ~6 s of patch time; 40 s is generous and still bounded.
"$PD" -nogui -noaudio -nomidi -path "$WORK/patch" \
      "$WORK/patch/main-dev.pd" "$WORK/drive.pd" > "$CAP" 2>&1 &
PDPID=$!
( sleep 40; kill -9 "$PDPID" 2>/dev/null ) 2>/dev/null &
DOG=$!
wait "$PDPID" 2>/dev/null || true
kill "$DOG" 2>/dev/null || true
wait "$DOG" 2>/dev/null || true

python3 test/gate/phase9-assert.py $ARGS < "$CAP"
rc=$?

if [ "$KEEP" = "1" ]; then
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
