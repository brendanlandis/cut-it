#!/usr/bin/env python3
"""The kit's analyzer -- ref/module/sequencer.md, The kit. Reads the capture on
stdin and the recording.

    kit-assert.py OUT.wav [-v] < capture

Six claims:

    1. u_root sends the sequencer's pads to c_kit, and to nothing else, and
       c_kit's outlet~ to the left output
    2. c_kit reports how many samples it found, exactly
    3. a hit plays its pad's own sample, at its velocity's level
    4. no sample, a pad past 16 and velocity 0 are silent
    5. a hit cuts the one before: a retrigger restarts the sample, never doubles it
    6. a track's volume and pitch reach its voice: the level in dB on top of the
       velocity's, the pitch as the read's rate, its length over the rate
    7. a track's effects: its distortion squares a sine off and darkens with its tone,
       and passes the dry sound untouched at mix 0; its delay echoes a note value later
       at the tempo the bus carries, at its level, and rings out once its level goes to
       0; and its send gives the reverb a tail, which a send of 0 gives no new hit

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

    # ---- 6. a track's volume and pitch ---------------------------------------
    print("\n--- 6. a track's volume and pitch reach its voice ---")
    for name, db in (("VOL", -6.0), ("BOOST", 6.0)):
        seg = inside(window(name), G.SET_MS)
        want = TONE_RMS * 10 ** (db / 20.0)
        got = rms(seg)
        A.check("⛔ %s: vol 1 %+g, then pad 1 at 127, plays at %+g dB" % (name, db, db),
                abs(got - want) / want < RMS_TOL,
                "rms %.5f, wanted %.5f: the track's volume adds its dB to the velocity's"
                % (got, want))
    for name, st in (("UP", 12), ("DOWN", -12)):
        t = G.hit_time(window(name), G.SET_MS)
        length = G.SAMPLE_S / 2 ** (st / 12.0)
        seg = span(t + 0.02, t + length - 0.03)
        # the pitch over what both an unpitched and a pitched sample would cover, so a
        # sample that stopped early cannot pass for a lower one
        tone = span(t + 0.02, t + min(length, G.SAMPLE_S) - 0.05)
        f = crossings(tone) / 2.0 / (len(tone) / float(rate)) if tone else 0
        hz = G.SAMPLES[7] * 2 ** (st / 12.0)
        A.check("⛔ %s: pitch 7 %+d, then pad 7, plays its sample an octave %s, %.0f Hz"
                % (name, st, "up" if st > 0 else "down", hz),
                abs(f - hz) / hz < FREQ_TOL, "measured %.1f Hz" % f)
        A.check("%s: at its own level -- pad 1's volume is not pad 7's" % name,
                abs(rms(seg) - TONE_RMS) / TONE_RMS < RMS_TOL,
                "rms %.5f, wanted %.5f" % (rms(seg), TONE_RMS))
        after = span(t + length + 0.02, t + length + 0.25)
        A.check("⛔ %s: and it lasts the sample's length over the rate, %.2f s, then stops"
                % (name, length), peak(after) < SILENT and rms(seg) > TONE_RMS * 0.9,
                "peak %.5f after %.2f s" % (peak(after), length))

    # ---- 7. a track's effects ---------------------------------------------------
    print("\n--- 7. a track's effects ---")

    def crest(xs):
        return peak(xs) / rms(xs) if rms(xs) else 0.0

    seg = inside(window("DIST"), G.SET_MS)
    # drive 100 is a gain of 100 into the clip, and the clip's output 1 over its root, 0.1
    A.check("⛔ DIST: drive 100 mixed all the way in squares pad 1's sine off: its crest factor "
            "near 1 where a sine's is 1.41", crest(seg) < 1.15,
            "crest %.3f, rms %.4f, peak %.4f" % (crest(seg), rms(seg), peak(seg)))
    A.check("DIST: ... at the clip's level, 1 over the root of the drive's gain of 100: 0.1",
            abs(peak(seg) - 0.1) < 0.012, "peak %.4f" % peak(seg))
    dark = inside(window("DARK"), G.SET_MS)
    # a one-pole low-pass at 300 Hz passes 0.57 of a 440 Hz fundamental and little of the rest
    A.check("DARK: tone 0, its low-pass at 300 Hz, rounds the square's edges off, a sine's crest "
            "again, and takes nearly half its level", rms(dark) < rms(seg) * 0.6
            and crest(dark) > 1.3, "rms %.4f against DIST's %.4f, crest %.3f"
            % (rms(dark), rms(seg), crest(dark)))
    dry = inside(window("DRY"), G.SET_MS)
    A.check("⛔ DRY: dist 0 passes the sine untouched -- its level and a sine's crest again",
            abs(rms(dry) - TONE_RMS) / TONE_RMS < RMS_TOL and abs(crest(dry) - 2 ** 0.5) < 0.05,
            "rms %.5f, wanted %.5f; crest %.3f" % (rms(dry), TONE_RMS, crest(dry)))

    def onset(a, b, thr=0.02):
        for i in range(max(0, int(a * rate)), min(len(x), int(b * rate))):
            if abs(x[i]) / 32768.0 > thr:
                return i
        return None

    t = G.hit_time(window("ECHO"), G.SET_MS)
    o1 = onset(t - 0.01, t + 0.05)
    want = int(round(8 * 15.0 / G.ECHO_BPM * rate))     # a half note, eight steps, at 240
    o2 = onset(t + G.SAMPLE_S + 0.02, t + 0.9)
    A.check("⛔ ECHO: a half note's delay on pad 7, at the tempo bus's 240 BPM, echoes it %d "
            "samples, 500 ms, after it, to the sample" % want,
            o1 is not None and o2 is not None and abs((o2 - o1) - want) <= 2,
            "dry at %s, echo at %s: %s samples apart" % (o1, o2, o2 - o1 if o1 and o2 else None))
    echo = span(t + 0.5 + 0.02, t + 0.5 + G.SAMPLE_S - 0.03)
    A.check("ECHO: ... at its level, 100, as loud as the hit", abs(rms(echo) - TONE_RMS) / TONE_RMS
            < RMS_TOL, "rms %.5f, wanted %.5f" % (rms(echo), TONE_RMS))
    after = span(t + 0.5 + G.SAMPLE_S + 0.02, t + 1.4)
    A.check("ECHO: ... and once only, at feedback 0", peak(after) < SILENT,
            "peak %.5f after the echo" % peak(after))
    t = G.hit_time(window("TAIL"), G.SET_MS)
    e1 = rms(span(t + 0.5 + 0.02, t + 0.5 + G.SAMPLE_S - 0.03))
    e2 = rms(span(t + 1.0 + 0.02, t + 1.0 + G.SAMPLE_S - 0.03))
    A.check("⛔ TAIL: pad 1's level set to 0 after its hit went in, its echoes ring out: the first "
            "at the hit's level, the second at feedback 50's 0.475 of it",
            abs(e1 - TONE_RMS) / TONE_RMS < RMS_TOL and abs(e2 / e1 - 0.475) < 0.03,
            "echoes at rms %.5f and %.5f, a ratio of %.3f" % (e1, e2, e2 / e1 if e1 else 0))
    t = G.hit_time(window("VERB"), G.SET_MS)
    tail = span(t + G.SAMPLE_S + 0.02, t + G.SAMPLE_S + 0.12)
    late = span(t + G.SAMPLE_S + 0.5, t + G.SAMPLE_S + 0.6)
    A.check("⛔ VERB: pad 7's send at 100 leaves a reverb tail after its sample ends, dying away",
            rms(tail) > 0.01 and rms(late) < rms(tail) / 3,
            "rms %.5f just after the sample, %.5f half a second on" % (rms(tail), rms(late)))
    t = G.hit_time(window("VERB-OFF"), G.SET_MS)
    off = span(t + G.SAMPLE_S + 0.02, t + G.SAMPLE_S + 0.3)
    A.check("VERB-OFF: at send 0 a hit leaves nothing after its sample ends",
            peak(off) < SILENT, "peak %.5f after the sample" % peak(off))

    # ---- 8. every effect switches itself off --------------------------------
    print("\n--- 8. each effect's DSP has a switch~, so an effect unused costs nothing ---")
    for name in ("e_drive", "e_delay", "e_verb"):
        boxes, _cons = top_boxes(os.path.join(ROOT, "Cut It", name + ".pd"))
        A.check("%s holds one switch~" % name, len(find(boxes, "switch~")) == 1,
                "switch~ boxes: %s" % find(boxes, "switch~"))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
