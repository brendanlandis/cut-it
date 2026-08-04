#!/bin/sh
# Headless regression gate for Phase 6. Asserts on what the patch ACTUALLY emits
# to the Launchpad, with no hardware and nobody watching.
#
#     ./tools/phase6-assert.sh            # run it
#     ./tools/phase6-assert.sh --keep     # and leave the capture behind to read
#
# HOW IT SEES THE BYTES. Pd resolves a class name against its built-in table
# before it looks for an abstraction, so a midiout.pd on the search path is
# simply ignored -- measured both ways, and it is why mac-stubs/ works for
# [shell] (an external absent on the Mac) but could never work here. So this
# copies the patch to a scratch directory and rewrites the [midiout] OBJECT
# BOXES to [t_midiout], which prints every byte with its port.
#
# NOTHING IN "Cut It/" IS TOUCHED. The copy is thrown away unless --keep.
#
# Exits non-zero if any assertion fails.
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
WORK=${TMPDIR:-/tmp}/cutit-assert-$$
KEEP=0
[ "$1" = "--keep" ] && KEEP=1

[ -x "$PD" ] || { echo "no Pd at $PD -- set PD=..." >&2; exit 2; }

mkdir -p "$WORK"
cp -R "$ROOT/Cut It" "$WORK/patch"
cp "$ROOT/tools/test-stubs/t_midiout.pd" "$WORK/patch/"
cp "$ROOT/mac-stubs/"*.pd "$WORK/patch/" 2>/dev/null || true

# rewrite the object boxes, and count them so a silent miss cannot pass for a
# clean run -- five is what the patch has today
n=0
for f in "$WORK"/patch/*.pd; do
    c=$(grep -c '^#X obj .* midiout;$' "$f" 2>/dev/null || true)
    [ "$c" = "0" ] && continue
    sed -i '' 's/^\(#X obj [0-9]* [0-9]*\) midiout;$/\1 t_midiout;/' "$f"
    n=$((n + c))
    echo "   rewrote $c [midiout] in $(basename "$f")"
done
if [ "$n" -eq 0 ]; then
    echo "FAIL: no [midiout] object boxes found to rewrite -- every assertion" >&2
    echo "      would pass vacuously, which is worse than failing." >&2
    exit 2
fi
echo "   $n [midiout] boxes rewritten to [t_midiout]"

CAP="$WORK/capture.txt"
echo "   running (about 45 s -- DSP is on, the beat row needs it) ..."
"$PD" -nogui -path "$WORK/patch" \
      "$WORK/patch/main-dev.pd" "$ROOT/tools/phase6-assert-drive.pd" \
      > "$CAP" 2>&1 || true

echo
python3 "$ROOT/tools/phase6-assert.py" < "$CAP"
rc=$?

if [ "$KEEP" -eq 1 ]; then
    echo
    echo "capture kept at $CAP"
else
    rm -rf "$WORK"
fi
exit $rc
