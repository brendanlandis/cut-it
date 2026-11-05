#!/usr/bin/env python3
"""The kit's analyzer -- ref/module/sequencer.md, The kit. Reads the capture on
stdin and the recording.

    kit-assert.py OUT.wav [-v] < capture

Five claims:

    1. u_root sends the sequencer's pads to c_kit, and to nothing else, and
       c_kit's outlet~ to the left output
    2. c_kit reports how many samples it found, exactly
    3. a hit plays its pad's own sample, at its velocity's level
    4. no sample, a pad past 16 and velocity 0 are silent
    5. a hit cuts the one before: a retrigger restarts the sample, never doubles it

Standard library only.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                  # noqa: E402

import importlib.util                                          # noqa: E402

_gen = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit-assert-drive-gen.py")
_spec = importlib.util.spec_from_file_location("kit_drive_gen", _gen)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A tone of amplitude a has RMS a/sqrt(2).
TONE_RMS = G.AMP / (2 ** 0.5)
# c_voice's velocity: 30 dB of range, even in dB, 127 at 0 dB.
def level_db(v):
    return 30.0 * (v / 127.0 - 1.0)

RMS_TOL = 0.05
SILENT = 0.001
FREQ_TOL = 0.05


def top_boxes(path):
    """{index: text} of a patch's top-level boxes, and its top-level connects."""
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


def find(boxes, cls):
    return [i for i, r in boxes.items()
            if r.startswith("#X obj") and r[:-1].split()[4:5] == [cls]]


def read_wav(path):
    with wave.open(path, "rb") as w:
        rate, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    return rate, ch, struct.unpack("<%dh" % (n * ch), raw)[0::ch]


def rms(xs):
    return (sum(float(x) * x for x in xs) / len(xs)) ** 0.5 / 32768.0 if xs else 0.0


def peak(xs):
    return max((abs(x) for x in xs), default=0) / 32768.0


def crossings(xs):
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
        sys.exit("usage: kit-assert.py OUT.wav < capture")
    cap = A.require_capture(sys.stdin.read())

    # ---- 1. the wiring, read rather than run --------------------------------
    print("--- 1. the sequencer's pads go to c_kit, and the kit to the output ---")
    boxes, cons = top_boxes(os.path.join(ROOT, "Cut It", "u_root.pd"))
    steps, kits = find(boxes, "c_steps"), find(boxes, "c_kit")
    A.check("u_root holds one c_steps and one c_kit",
            len(steps) == 1 and len(kits) == 1,
            "c_steps %s, c_kit %s" % (steps, kits))
    if len(steps) == 1 and len(kits) == 1:
        out0 = [(a, b, c, d) for a, b, c, d in cons if a == steps[0] and b == 0]
        A.check("c_steps' pad outlet is corded to c_kit",
                (steps[0], 0, kits[0], 0) in out0, "its cords: %s" % out0)
        # The SP-404 played them until 2026-11-04 and is gone: a drum leaving
        # the instrument as MIDI is a cord this gate exists to see.
        A.check("⛔ and to nothing else, so no drum leaves the instrument",
                out0 == [(steps[0], 0, kits[0], 0)], "its cords: %s" % out0)
        # The drums are a signal out of c_kit's outlet~ (2026-11-04), not a throw~
        # of its own: u_root sums them into the left output where the meter reads it.
        sig = [(a, b, c, d) for a, b, c, d in cons if a == kits[0]]
        throws = find(boxes, "throw~")
        to_l = [i for i in throws if boxes[i][:-1].split()[5:6] == ["outL"]]
        feeds = sig[0][2] if len(sig) == 1 else None
        A.check("⛔ c_kit's outlet~ goes to ONE box, and that box feeds throw~ outL",
                feeds is not None and len(to_l) == 1
                and (feeds, 0, to_l[0], 0) in cons,
                "c_kit's cords %s, throw~ outL %s. A second cord would play the drums "
                "twice; none, or into a box the output does not come from, plays them "
                "nowhere" % (sig, to_l))

    # ---- 2. the count -------------------------------------------------------
    print("\n--- 2. c_kit reports the samples it found ---")
    order, by = A.windows(cap, "KIT", len(G._seq("x")))
    errs = [v for w in by.values() for k, v in w if k == "ERR" and v[1:2] == ["c_kit"]]
    A.check("exactly one report, warn c_kit samples-2 (pads 1 and 7 of 16)",
            errs == [["warn", "c_kit", "samples-2"]],
            "c_kit's err lines: %s. Two samples is a count no other run gives, so "
            "a stale or a hard-coded count shows" % errs)

    # ---- the recording ------------------------------------------------------
    if not os.path.exists(args[0]):
        A.check("writesf~ wrote a soundfile", False, "no file at %s" % args[0])
        return A.report()
    rate, ch, x = read_wav(args[0])
    A.check("the recording is mono at 44100 Hz", ch == 1 and rate == G.RATE,
            "%d channel(s) at %d Hz" % (ch, rate))

    def span(a, b):
        return x[int(a * rate):int(b * rate)]

    # Inside a sample: from 20 ms after its hit (the 2 ms dip and the 1 ms rise
    # well past) to 30 ms before its end.
    def inside(at_s, off_ms=0):
        t = G.hit_time(at_s, off_ms)
        return span(t + 0.02, t + G.SAMPLE_S - 0.03)

    def window(name):
        for n, s, _ in G.HITS:
            if n == name:
                return s
        raise KeyError(name)

    # ---- 3. a hit plays its own sample, at its level ------------------------
    print("\n--- 3. a hit plays its pad's sample at its velocity ---")
    for name, pad, vel in (("FULL", 1, 127), ("SOFT", 7, 16)):
        seg = inside(window(name))
        want = TONE_RMS * 10 ** (level_db(vel) / 20.0)
        got = rms(seg)
        A.check("%s: pad %d at velocity %d plays at %.1f dB" % (name, pad, vel, level_db(vel)),
                abs(got - want) / want < RMS_TOL,
                "rms %.5f, wanted %.5f. Velocity is 30 dB of range, even in dB" % (got, want))
        f = crossings(seg) / 2.0 / (len(seg) / float(rate)) if seg else 0
        hz = G.SAMPLES[pad]
        A.check("%s: and it is pad %d's sample, %.0f Hz" % (name, pad, hz),
                abs(f - hz) / hz < FREQ_TOL, "measured %.1f Hz" % f)
    t = G.hit_time(window("FULL"))
    after = span(t + G.SAMPLE_S + 0.02, G.hit_time(window("SOFT")) - 0.02)
    A.check("FULL: the sample ends, and nothing follows it", peak(after) < SILENT,
            "peak %.5f after the sample's end" % peak(after))

    # ---- 4. silence where there should be ----------------------------------
    print("\n--- 4. what plays nothing ---")
    for name, why in (("MISSING", "pad 3 has no sample"),
                      ("PAST", "pad 17 is past the kit"),
                      ("ZERO", "velocity 0 is no hit")):
        t = G.hit_time(window(name))
        seg = span(t - 0.02, t + 0.45)
        A.check("%s: silent -- %s" % (name, why), peak(seg) < SILENT,
                "peak %.5f" % peak(seg))

    # ---- 5. a retrigger restarts --------------------------------------------
    print("\n--- 5. a hit cuts the one before ---")
    s = window("RETRIG")
    t1, t2 = G.hit_time(s), G.hit_time(s, 50)
    both = span(t1, t2 + G.SAMPLE_S)
    A.check("two hits 50 ms apart never sum: the peak stays one sample's",
            peak(both) < G.AMP * 1.05,
            "peak %.4f against one sample's %.4f" % (peak(both), G.AMP))
    late = span(t2 + G.SAMPLE_S + 0.02, t2 + G.SAMPLE_S + 0.3)
    A.check("and it ends one sample after the second hit, not the first's tail",
            peak(late) < SILENT and rms(span(t2 + 0.02, t2 + G.SAMPLE_S - 0.03)) > TONE_RMS * 0.9,
            "peak after %.5f, rms of the second hit %.4f" %
            (peak(late), rms(span(t2 + 0.02, t2 + G.SAMPLE_S - 0.03))))

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
