#!/bin/sh
# Convert the drum samples into what Cut It loads, beside the patch.
#
#   ./tools/samples.sh          samples/drums/NN*.* -> "Cut It/samples/drums/NN.wav"
#
# samples/drums/ is Brendan's: one file per pad, its name starting with the pad's two digits,
# 01 to 16, in any format ffmpeg reads (samples/README.md). Each becomes a mono 16-bit WAV at
# 44.1 kHz, the device's rate, named NN.wav, which is what c_voice reads. Neither folder is in git.
# tools/deploy.sh runs this before it copies the patch, so the samples travel with it; run it by
# hand to hear them on the Mac's main-dev.pd. ref/module/sequencer.md, The kit.

set -eu
cd "$(dirname "$0")/.."

SRC=samples/drums
OUT="Cut It/samples/drums"

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "samples: no ffmpeg on this Mac, so no drum samples converted" >&2
    exit 1
fi

mkdir -p "$OUT"
# Last time's conversions go first, so a sample removed from samples/drums leaves no pad behind.
rm -f "$OUT"/*.wav

n=0
for pad in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16; do
    src=""
    for f in "$SRC/$pad"*; do
        [ -f "$f" ] || continue
        if [ -n "$src" ]; then
            echo "samples: two files for pad $pad; using $(basename "$src"), not $(basename "$f")" >&2
            continue
        fi
        src=$f
    done
    [ -n "$src" ] || continue
    ffmpeg -nostdin -hide_banner -loglevel error -y -i "$src" \
        -ac 1 -ar 44100 -sample_fmt s16 "$OUT/$pad.wav"
    n=$((n + 1))
done
echo "samples: $n of 16 drum samples converted"
