#!/usr/bin/env python3
"""The audio path's analyzer -- ref/module/audio.md. Reads a soundfile, not stdin.

    audio-assert.py OUT.wav [CAPTURE.txt] [-v]

Five claims:

    1. the output is not silent
    2. the input goes out on the right, and only the right (Brendan,
       2026-11-14): the tip, the mic's (item 11), and the ring each reach it,
       told apart by their frequencies, and the left carries none of either
    3. the passthrough is unity: u_root's audio path has no gain, and the
       right sums the two inputs once each
    4. the drums reach the left output, and only the left, at their own level
    5. the chain is u_root's wires, and the levels are mother's: everything Cut
       It sends out leaves through u_root's two throw~, and nothing reports a
       level on disp, since the info bar meters what mother catches

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
MARKS = ["DSP", "REC", "BOTH", "TIP", "RING", "PAGE-2", "DRUMS", "TAIL", "STOP", "DONE"]


# A sine of amplitude a has RMS a/sqrt(2). Two of different frequencies, each of
# amplitude a, sum to RMS a: the right output with both inputs driven.
WANT_RMS = AMP / (2 ** 0.5)
WANT_BOTH_RMS = AMP

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
    """The chain is wires in u_root, read off the patch rather than run."""
    print("--- 5. the chain is u_root's, and the levels are mother's ---")
    throws, private, catches, sends, receives = {}, {}, {}, {}, {}
    for name in sorted(os.listdir(PATCH)):
        if not name.endswith(".pd"):
            continue
        for r in lib_pd.read(os.path.join(PATCH, name)):
            f = r[:-1].split()
            # a private send~ or receive~, as a private throw~: mother's inL and inR are global
            if (r.startswith("#X obj") and f[4:5] in (["s~"], ["send~"], ["r~"], ["receive~"])
                    and "$" in " ".join(f[5:])):
                (sends if f[4] in ("s~", "send~") else receives).setdefault(
                    " ".join(f[5:]), []).append(name)
            if r.startswith("#X obj") and f[4:5] in (["throw~"], ["catch~"]):
                # a name with a $ in it is private to its abstraction and the ones it hands its
                # $0 to (C-1); a bare one is global, as mother's outL and outR are
                to = " ".join(f[5:])
                if f[4] == "throw~":
                    (private if "$" in to else throws).setdefault(to, []).append(name)
                elif "$" in to:
                    catches.setdefault(to, []).append(name)
    A.check("⛔ everything Cut It sends out leaves through u_root: one throw~ outL and one "
            "throw~ outR in the whole patch, both there",
            throws == {"outL": ["u_root.pd"], "outR": ["u_root.pd"]},
            "throw~ by global name: %s. A stage hands its sound up an outlet~ to u_root's "
            "sum, as c_kit does, so the audio path stays wires on one canvas; a throw~ "
            "of its own sums into mother's catch~ out of sight of it" % throws)
    # The drums' effects reach each other by throw~ and catch~ inside c_kit, under its $0
    # (ref/module/sequencer.md, The effects): voices to their delays and the reverb, the delays
    # and the reverb's three engines to c_kit's own catch~, which is c_kit's outlet~. Exactly
    # these, so a new throw~ is a decision and not a leak.
    kit = {"\\$2-verb": ["c_voice.pd"], "\\$2-d\\$1": ["c_voice.pd"],
           "\\$1-out": ["e_delay.pd", "e_freeverb.pd", "e_gigaverb.pd", "e_plate.pd"],
           "\\$1-verb": ["e_delay.pd"], "\\$0-verb": ["e_line.pd"]}
    kit_catch = {"\\$1-d\\$2": ["e_delay.pd"], "\\$1-verb": ["e_verb.pd"],
                 "\\$0-out": ["c_kit.pd", "e_line.pd"]}
    A.check("⛔ every other throw~ is private to a c_kit's or an e_line's \\$0, each caught inside it",
            private == kit and catches == kit_catch,
            "private throw~ %s, catch~ %s" % (private, catches))
    # The reverb's sends reach its engines by one send~ in e_verb, under its \$0, which each of its
    # three engines takes as its \$2 (Brendan, 2026-11-05: a choice of three). The only send~.
    A.check("⛔ the reverb's sends reach its three engines by one send~ in e_verb, and no other "
            "private send~ or receive~ is in the patch", sends == {"\\$0-in": ["e_verb.pd"]}
            and receives == {"\\$2-in": ["e_freeverb.pd", "e_gigaverb.pd", "e_plate.pd"]},
            "send~ %s, receive~ %s" % (sends, receives))


def levels(path):
    """-> every level report on disp, from any window: the meters' old names."""
    with open(path) as fh:
        order, by = A.windows(fh.read(), "AUDIO", len(MARKS))
    return [v for w in order for kind, v in by.get(w, [])
            if kind == "DISP" and v[:1] and v[0] in ("out-l", "out-r", "in-l", "in-r")]


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
    A.check("the right carries signal when the input is driven", rms(r) > SILENT,
            "R rms %.4f. u_root's input path is four cords and no gain; silence "
            "here means one of them is gone" % rms(r))

    # ---- 2. the input goes out on the right, and only the right -------------
    # The tip is the mic (item 11); it goes out with the synths, the drums alone on
    # the left (Brendan, 2026-11-14). Each input driven alone, the frequency on the
    # right says which reached it, and a silent left that nothing crossed over.
    print("\n--- 2. the input goes out on the right, and only the right ---")
    for name, want in (("tip", 220.0), ("ring", 330.0)):
        l, r, span = seg(name)
        f = crossings(r) / 2.0 / span
        A.check("with only the %s driven, the RIGHT carries its %.0f Hz" % (name, want),
                abs(f - want) / want < FREQ_TOL,
                "measured %.1f Hz over %.2f s, R rms %.4f. 220 goes in the tip and "
                "330 the ring; the other's frequency, or none, means the cords "
                "cross or one is gone" % (f, span, rms(r)))
    for name in ("tip", "ring", "both"):
        l, r, _ = seg(name)
        A.check("with the %s driven, the LEFT is SILENT: the drums are alone there"
                % ("input" if name == "both" else name), rms(l) < SILENT,
                "L rms %.4f, R rms %.4f. Anything of the input on the left is on "
                "the drums' mixer channel" % (rms(l), rms(r)))

    # ---- 3. the passthrough is unity --------------------------------------
    print("\n--- 3. the passthrough is unity ---")
    for name, want in (("tip", WANT_RMS), ("ring", WANT_RMS), ("both", WANT_BOTH_RMS)):
        l, r, _ = seg(name)
        A.check("with %s driven, the right comes out at unity -- rms %.4f"
                % ("both" if name == "both" else "only the " + name, want),
                abs(rms(r) - want) < RMS_TOL,
                "rms %.4f against %.4f. throw~/catch~ SUMS, so a doubled value "
                "means something is throwing twice; a halved one means a gain "
                "has appeared where there is meant to be none" % (rms(r), want))

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
    A.check("pad 1, pressed on the drum page, comes out of the LEFT at %.0f Hz" % DRUM_HZ,
            abs(f - DRUM_HZ) / DRUM_HZ < FREQ_TOL,
            "measured %.1f Hz over %.2f s, L rms %.4f. Silence here means c_kit's "
            "outlet~ reaches nothing that is thrown" % (f, span, rms(l)))
    A.check("...at its own level, once -- rms %.4f" % WANT_RMS,
            abs(rms(l) - WANT_RMS) < RMS_TOL,
            "rms %.4f against %.4f. Double is the drums summed twice, by a second "
            "cord or a second throw~" % (rms(l), WANT_RMS))
    A.check("...and the RIGHT stays silent", rms(r) < SILENT,
            "R rms %.4f with only the drums playing" % rms(r))

    # ---- 5. the chain, and the levels ------------------------------------
    lint()
    if len(args) > 1 and os.path.exists(args[1]):
        # The OLED's levels are mother's info bar since 2026-11-04 (Brendan), read
        # off her catch~ after the volume knob: nothing of Cut It's meters them.
        lv = levels(args[1])
        A.check("⛔ nothing reports a level on disp: the info bar is the meter",
                not lv, "%d level report(s), the first %s" % (len(lv), lv[:1]))

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
