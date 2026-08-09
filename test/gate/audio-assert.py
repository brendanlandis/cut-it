#!/usr/bin/env python3
"""The audio path's analyser -- ref/module/audio.md. Reads a SOUNDFILE, not stdin.

    audio-assert.py OUT.wav [CAPTURE.txt] [-v]

⛔ THE FIRST SIGNAL-DOMAIN GATE IN THIS PROJECT, and the only analyser here that
does not read a capture on stdin: its subject is a file of samples. Everything
else asserts on messages, which is why ref/module/audio.md declared `Gate: none`
honestly for as long as it did -- a broken rewiring of the four cords at the end
of u_root.pd is completely silent, and would surface as no sound at a venue.

THREE CLAIMS, and the middle one is the reason this exists:

    1. the output is not silent
    2. ⛔ L and R are NOT SWAPPED -- the TRS Y-cable makes L the SP-404's drums
       and R its fx, and adc~ 1 is the tip (item 11). Amplitude cannot see a
       swap, because both channels carry the same level; the FREQUENCIES can
    3. the passthrough is unity, not attenuated -- there is no gain anywhere in
       u_root's audio path and there must not be one

⚠️ NO numpy. The standard library reads a WAV and the arithmetic is a sum, a
count of sign changes and a comparison. A dependency for that would be a
dependency this project's one measuring rig had and nothing else did.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE SEGMENT TABLE IS LOADED FROM THE GENERATOR, NOT RETYPED. Two copies of a
# schedule is how a gate comes to measure the wrong span of a file and report it
# with total confidence. It is loaded through importlib rather than imported
# outright because the generator's name has a hyphen, which is not a legal
# Python identifier -- the same reason lib_assert and lib_drive have underscores
# and every script beside them does not. The bench tooling does this too.
import importlib.util                                          # noqa: E402

_gen = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "audio-assert-drive-gen.py")
_spec = importlib.util.spec_from_file_location("audio_drive_gen", _gen)
_ns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ns)
AMP, SEGMENTS, GUARD = _ns.AMP, _ns.SEGMENTS, _ns.GUARD

# A sine of amplitude a has RMS a/sqrt(2). This is what "unity" is measured
# against -- the input is known exactly, so the output can be too.
WANT_RMS = AMP / (2 ** 0.5)

# 2% on the level. Wide enough for 16-bit quantisation and a partial cycle at
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

    # ---- 2. ⛔ L AND R ARE NOT SWAPPED ------------------------------------
    # ⛔ MEASURED BY FREQUENCY, WHICH IS THE ONLY THING THAT CAN SEE IT. Both
    # channels carry the same level by construction, so a swap is invisible to
    # any amplitude check -- and a swap is the failure that matters most here:
    # the TRS Y-cable makes L the SP-404's drums and R its fx, so a swapped
    # passthrough puts the drums through the fx chain and nothing errors.
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
    # ⚠️ THE TWO ONE-SIDED SEGMENTS ARE THE OTHER HALF OF THE SWAP CHECK. Both
    # channels being right when both are driven does not prove they are
    # independent -- a chain that summed L and R into both would pass the
    # frequency checks above on neither, and one that copied L into both would
    # fail them; only a silent channel proves the cords do not cross.
    for name, silent_chan in (("left", 1), ("right", 0)):
        l, r, _ = seg(name)
        loud, quiet = ((l, r) if silent_chan else (r, l))
        A.check("with only %s driven, the other channel is SILENT" % name,
                rms(loud) > SILENT and rms(quiet) < SILENT,
                "driven %.4f, other %.4f" % (rms(loud), rms(quiet)))

    # ---- 3. the passthrough is unity --------------------------------------
    # There is no gain anywhere in u_root's audio path -- r~ straight into
    # throw~, with the level taps hanging off as a signal fan-out that reads and
    # does not alter. So the output must equal the input, and the input is known.
    print("\n--- 3. the passthrough is unity ---")
    l, r, _ = seg("both")
    for name, got in (("left", rms(l)), ("right", rms(r))):
        A.check("the %s channel comes out at unity -- rms %.4f" % (name, WANT_RMS),
                abs(got - WANT_RMS) < RMS_TOL,
                "rms %.4f against %.4f. throw~/catch~ SUMS, so a doubled value "
                "means something is throwing twice; a halved one means a gain "
                "has appeared where there is meant to be none" % (got, WANT_RMS))

    # ---- silence in, silence out ------------------------------------------
    # ⚠️ THE ONE ASSERTION THAT CANNOT PASS VACUOUSLY BY THE FILE BEING EMPTY,
    # because everything above has already proved the file is not.
    print("\n--- and nothing arrives unasked ---")
    for name in ("silence", "tail"):
        l, r, _ = seg(name)
        A.check("%s: nothing is driven and nothing comes out" % name,
                rms(l) < SILENT and rms(r) < SILENT,
                "L %.4f R %.4f -- something is generating on its own" % (rms(l), rms(r)))

    # ---- u_level, which shares the page -----------------------------------
    # ⚠️ THE ONE MESSAGE-DOMAIN CHECK HERE, and it belongs to this page: u_level
    # is the other file on ref/module/audio.md's Files line. env~ reports RMS on
    # a 0-100 dB scale with a measured noise floor of 18-19, so a tone must put
    # it well clear of that.
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
