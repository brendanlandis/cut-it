#!/usr/bin/env python3
"""The audio path's analyzer -- ref/module/audio.md. Reads a soundfile, not stdin.

    audio-assert.py OUT.wav [CAPTURE.txt] [-v]

Three claims:

    1. the output is not silent
    2. L and R are not swapped: L is the SP-404's drums (item 11). Both
       channels carry the same level, so only the frequencies can see a swap
    3. the passthrough is unity: u_root's audio path has no gain

Standard library only: a WAV, a sum and a count of sign changes need no numpy.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The segment table is the generator's, never retyped. Loaded by path because a
# hyphen is not legal in a module name.
import importlib.util                                          # noqa: E402

_gen = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "audio-assert-drive-gen.py")
_spec = importlib.util.spec_from_file_location("audio_drive_gen", _gen)
_ns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ns)
AMP, SEGMENTS, GUARD = _ns.AMP, _ns.SEGMENTS, _ns.GUARD

# A sine of amplitude a has RMS a/sqrt(2).
WANT_RMS = AMP / (2 ** 0.5)

# 2% on the level. Wide enough for 16-bit quantization and a partial cycle at
# the window edges, far tighter than any gain error worth having.
RMS_TOL = 0.02

# Below this a segment is silence. The file is 16-bit, so one LSB is 1/32768;
# this is about 60 dB down from the tone and cannot be reached by dither.
SILENT = 0.001

FREQ_TOL = 0.05


def read_wav(path):
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 2 or w.getsampwidth() != 2:
            return None, None, "%d channel(s) at %d bytes/sample -- wanted stereo 16-bit" \
                % (w.getnchannels(), w.getsampwidth())
        rate, n = w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    vals = struct.unpack("<%dh" % (n * 2), raw)
    return rate, (vals[0::2], vals[1::2]), None


def rms(xs):
    if not xs:
        return 0.0
    return (sum(float(x) * x for x in xs) / len(xs)) ** 0.5 / 32768.0


def crossings(xs):
    """Sign changes -- 2 per cycle for anything that crosses zero once a half."""
    n, prev = 0, 0
    for x in xs:
        s = 1 if x > 0 else (-1 if x < 0 else 0)
        if s and prev and s != prev:
            n += 1
        if s:
            prev = s
    return n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.exit("usage: audio-assert.py OUT.wav [CAPTURE.txt]")
    path = args[0]

    if not os.path.exists(path):
        A.check("writesf~ wrote a soundfile at all", False,
                "no file at %s -- the recording never started, and every "
                "assertion below would otherwise be answered by an empty list "
                "rather than by a fact" % path)
        return A.report()

    rate, chans, why = read_wav(path)
    if why:
        A.check("the soundfile is stereo 16-bit", False, why)
        return A.report()
    left, right = chans
    dur = len(left) / float(rate)

    print("--- the recording ---")
    want_dur = SEGMENTS[-1][2]
    A.check("the recording is about %.0f s of stereo at %d Hz" % (want_dur, rate),
            abs(dur - want_dur) < 0.5,
            "got %.2f s. A short file means writesf~ was killed before its stop "
            "and the header length is a lie" % dur)

    def seg(name):
        for n, a, b in SEGMENTS:
            if n == name:
                lo = int((a + GUARD) * rate)
                hi = int((b - GUARD) * rate)
                return left[lo:hi], right[lo:hi], (b - GUARD) - (a + GUARD)
        raise KeyError(name)

    # ---- 1. the output is not silent --------------------------------------
    print("\n--- 1. the output is not silent ---")
    l, r, _ = seg("both")
    A.check("both channels carry signal when both are driven",
            rms(l) > SILENT and rms(r) > SILENT,
            "L rms %.4f, R rms %.4f. u_root's audio path is four cords and no "
            "gain; silence here means one of them is gone" % (rms(l), rms(r)))

    # ---- 2. L and R are not swapped ---------------------------------------
    print("\n--- 2. L and R are not swapped ---")
    for name, chan, want in (("left", 0, 220.0), ("right", 1, 330.0)):
        l, r, span = seg("both")
        xs = (l, r)[chan]
        f = crossings(xs) / 2.0 / span
        A.check("the %s channel carries %.0f Hz" % (name, want),
                abs(f - want) / want < FREQ_TOL,
                "measured %.1f Hz over %.2f s. 220 goes in the left send and 330 "
                "the right, so this is what a swapped pair looks like" % (f, span))

    # ---- ...and there is no bleed between them ----------------------------
    # Right frequencies with both driven do not prove the channels independent;
    # only a silent channel proves the cords do not cross.
    for name, silent_chan in (("left", 1), ("right", 0)):
        l, r, _ = seg(name)
        loud, quiet = ((l, r) if silent_chan else (r, l))
        A.check("with only %s driven, the other channel is SILENT" % name,
                rms(loud) > SILENT and rms(quiet) < SILENT,
                "driven %.4f, other %.4f" % (rms(loud), rms(quiet)))

    # ---- 3. the passthrough is unity --------------------------------------
    print("\n--- 3. the passthrough is unity ---")
    l, r, _ = seg("both")
    for name, got in (("left", rms(l)), ("right", rms(r))):
        A.check("the %s channel comes out at unity -- rms %.4f" % (name, WANT_RMS),
                abs(got - WANT_RMS) < RMS_TOL,
                "rms %.4f against %.4f. throw~/catch~ SUMS, so a doubled value "
                "means something is throwing twice; a halved one means a gain "
                "has appeared where there is meant to be none" % (got, WANT_RMS))

    # ---- silence in, silence out ------------------------------------------
    # Cannot pass on an empty file: everything above proved it is not.
    print("\n--- and nothing arrives unasked ---")
    for name in ("silence", "tail"):
        l, r, _ = seg(name)
        A.check("%s: nothing is driven and nothing comes out" % name,
                rms(l) < SILENT and rms(r) < SILENT,
                "L %.4f R %.4f -- something is generating on its own" % (rms(l), rms(r)))

    # ---- u_level, which shares the page -----------------------------------
    # u_level is the page's other file. Its noise floor is 18-19 on the 0-100
    # scale (ref/module/audio.md), so a tone must clear it.
    if len(args) > 1 and os.path.exists(args[1]):
        print("\n--- u_level, on the disp bus ---")
        with open(args[1]) as fh:
            lines = [ln.strip() for ln in fh]
        levels = {}
        for ln in lines:
            if not ln.startswith("DISP: in-"):
                continue
            bits = ln.split()
            if len(bits) >= 3:
                levels.setdefault(bits[1], []).append(float(bits[2]))
        for name in ("in-l", "in-r"):
            xs = levels.get(name, [])
            A.check("u_level reports %s, and a tone puts it clear of the floor"
                    % name, bool(xs) and max(xs) > 40,
                    "saw %d report(s), peak %s. The measured noise floor is 18-19 "
                    "(item 11)" % (len(xs), max(xs) if xs else "none"))

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
