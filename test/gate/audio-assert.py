#!/usr/bin/env python3
"""The audio path's analyzer -- ref/module/audio.md. Reads a soundfile, not stdin.

    audio-assert.py OUT.wav [CAPTURE.txt] [-v]

Five claims:

    1. the output is not silent
    2. L and R are not swapped: L is the tip, the mic's (item 11). Both
       channels carry the same level, so only the frequencies can see a swap
    3. the passthrough is unity: u_root's audio path has no gain
    4. the drums reach the left output, and only the left, at their own level
    5. the meters read the OUTPUT: everything Cut It sends out leaves through
       u_root's two throw~, each u_level is fed exactly what its throw~ is, and
       out-l moves with the drums while the input is silent

Standard library only: a WAV, a sum and a count of sign changes need no numpy.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                  # noqa: E402

# The segment table is the generator's, never retyped. Loaded by path because a
# hyphen is not legal in a module name.
import importlib.util                                          # noqa: E402

_gen = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "audio-assert-drive-gen.py")
_spec = importlib.util.spec_from_file_location("audio_drive_gen", _gen)
_ns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ns)
AMP, SEGMENTS, GUARD = _ns.AMP, _ns.SEGMENTS, _ns.GUARD
DRUM_HZ = _ns.DRUM_HZ

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATCH = os.path.join(ROOT, "Cut It")

# The driver's windows, in order: AUDIO's MARKs.
MARKS = ["DSP", "REC", "BOTH", "LEFT", "RIGHT", "PAGE-2", "DRUMS", "TAIL", "STOP", "DONE"]

# u_level's scale is env~'s 0-100. The input's noise floor was 18-19 at the
# factory's gain (item 11); a tone at AMP reads in the 80s. A meter that reads
# the output clears 40 on the drums alone, and stays under 20 on a silent side.
CLEAR, FLOOR = 40, 20

# A sine of amplitude a has RMS a/sqrt(2).
WANT_RMS = AMP / (2 ** 0.5)

# 2% on the level. Wide enough for 16-bit quantization and a partial cycle at
# the window edges, far tighter than any gain error worth having.
RMS_TOL = 0.02

# Below this a segment is silence. The file is 16-bit, so one LSB is 1/32768;
# this is about 60 dB down from the tone and cannot be reached by dither.
SILENT = 0.001

FREQ_TOL = 0.05

# The device's rate, its .pdsettings' `rate: 44100`. writesf~ stamps the file
# with the rate Pd runs at, so this is what proves lib_scratch's -r reached Pd:
# 0.56 made 48000 the default, and a gate's Pd reads no preferences.
DEVICE_RATE = 44100


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


def top_boxes(path):
    """{index: record} of a patch's top-level boxes, and its top-level cords."""
    boxes, cons, depth, n = {}, [], 0, 0
    for r in lib_pd.read(path):
        if r.startswith("#N canvas"):
            depth += 1
            continue
        if r.startswith("#X restore"):
            depth -= 1
            if depth == 1:
                boxes[n] = r; n += 1
            continue
        if depth != 1:
            continue
        if r.startswith(("#X obj", "#X msg", "#X text", "#X floatatom", "#X symbolatom")):
            boxes[n] = r; n += 1
        elif r.startswith("#X connect"):
            cons.append(tuple(int(x) for x in r[:-1].split()[2:6]))
    return boxes, cons


def lint():
    """The meters read what is thrown, read off the patch rather than run."""
    print("--- 5. the meters read the OUTPUT, by reading the patch ---")
    throws = {}
    for name in sorted(os.listdir(PATCH)):
        if not name.endswith(".pd"):
            continue
        for r in lib_pd.read(os.path.join(PATCH, name)):
            f = r[:-1].split()
            if r.startswith("#X obj") and f[4:5] == ["throw~"]:
                throws.setdefault(" ".join(f[5:]), []).append(name)
    A.check("⛔ everything Cut It sends out leaves through u_root: one throw~ outL and one "
            "throw~ outR in the whole patch, both there",
            throws == {"outL": ["u_root.pd"], "outR": ["u_root.pd"]},
            "throw~ by name: %s. A throw~ in another file reaches mother's catch~ "
            "around u_root's, so no meter there can see it -- c_kit's drums did, "
            "until 2026-11-04" % throws)

    boxes, cons = top_boxes(os.path.join(PATCH, "u_root.pd"))

    def named(cls, arg):
        return [i for i, r in boxes.items() if r.startswith("#X obj")
                and r[:-1].split()[4:] == [cls, arg]]

    levels = sorted(" ".join(r[:-1].split()[5:]) for r in boxes.values()
                    if r.startswith("#X obj") and r[:-1].split()[4:5] == ["u_level"])
    A.check("u_root holds two u_level, out-l and out-r, and no other",
            levels == ["out-l", "out-r"],
            "u_level boxes: %s. in-l and in-r metered the input until 2026-11-04"
            % levels)
    for side, out, lvl in (("left", "outL", "out-l"), ("right", "outR", "out-r")):
        t, m = named("throw~", out), named("u_level", lvl)
        if len(t) != 1 or len(m) != 1:
            A.check("u_level %s is fed what throw~ %s is" % (lvl, out), False,
                    "throw~ %s %s, u_level %s %s" % (out, t, lvl, m))
            continue
        into = lambda b: sorted((a, o) for a, o, bb, i in cons if bb == b)
        A.check("⛔ the %s meter, u_level %s, is fed exactly what throw~ %s is"
                % (side, lvl, out),
                into(t[0]) and into(t[0]) == into(m[0]),
                "throw~ %s from %s, u_level %s from %s. A stage put in front of the "
                "throw~ and not the meter makes the meter read something that is not "
                "sent" % (out, into(t[0]), lvl, into(m[0])))


def meters(path):
    """-> {window: {name: [dB, ...]}} for u_level's reports, by AUDIO window."""
    with open(path) as fh:
        order, by = A.windows(fh.read(), "AUDIO", len(MARKS))
    out = {}
    for w in order:
        for kind, v in by.get(w, []):
            if kind == "DISP" and len(v) >= 2 and v[0] in ("out-l", "out-r", "in-l", "in-r"):
                out.setdefault(w, {}).setdefault(v[0], []).append(float(v[1]))
    return order, out


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
            abs(dur - want_dur) < 0.5 and rate == DEVICE_RATE,
            "got %.2f s at %d Hz, wanted %d Hz. A short file means writesf~ was "
            "killed before its stop and the header length is a lie; another rate "
            "means Pd ran without -r 44100" % (dur, rate, DEVICE_RATE))

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

    # ---- 4. the drums, with the input silent -------------------------------
    print("\n--- 4. the drums reach the left output alone ---")
    l, r, span = seg("drums")
    f = crossings(l) / 2.0 / span
    A.check("pad 1, pressed on page 2, comes out of the LEFT at %.0f Hz" % DRUM_HZ,
            abs(f - DRUM_HZ) / DRUM_HZ < FREQ_TOL,
            "measured %.1f Hz over %.2f s, L rms %.4f. Silence here means c_kit's "
            "outlet~ reaches nothing that is thrown" % (f, span, rms(l)))
    A.check("...at its own level, once -- rms %.4f" % WANT_RMS,
            abs(rms(l) - WANT_RMS) < RMS_TOL,
            "rms %.4f against %.4f. Double is the drums summed twice, by a second "
            "cord or a second throw~" % (rms(l), WANT_RMS))
    A.check("...and the RIGHT stays silent", rms(r) < SILENT,
            "R rms %.4f with only the drums playing" % rms(r))

    # ---- 5. the meters read what goes out ---------------------------------
    lint()
    if len(args) > 1 and os.path.exists(args[1]):
        print("\n--- 5. ...and by the signal, on the disp bus ---")
        order, lv = meters(args[1])
        both = lv.get("BOTH", {})
        for name in ("out-l", "out-r"):
            xs = both.get(name, [])
            A.check("u_level reports %s, and both inputs put it clear of %d"
                    % (name, CLEAR), bool(xs) and max(xs) > CLEAR,
                    "saw %d report(s), peak %s in BOTH" % (len(xs), max(xs) if xs else "none"))
        drums = lv.get("DRUMS", {})
        xs = drums.get("out-l", [])
        A.check("⛔ out-l moves with the DRUMS while the input is silent -- it reads "
                "the output", bool(xs) and max(xs) > CLEAR,
                "out-l in DRUMS: %s. A meter on the input reads nothing here: the "
                "drums never reach the input" % xs)
        last = None
        for w in order[:order.index("DRUMS") + 1] if "DRUMS" in order else []:
            last = (lv.get(w, {}).get("out-r") or [last])[-1]
        A.check("...and out-r falls to silence beside it -- the meters are not swapped",
                last is not None and last < FLOOR,
                "out-r's last report by the end of DRUMS: %s" % last)

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
