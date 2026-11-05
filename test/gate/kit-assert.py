#!/usr/bin/env python3
"""The kit's analyzer -- ref/module/sequencer.md, The kit. Reads the capture on
stdin and the recording.

    kit-assert.py OUT.wav [-v] < capture

Ten claims:

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
       0; and the reverb, each of its three types: a tail that dies away, as loud as the
       plate's, the engine told apart by when a click's reverb starts; one changed away
       from rings out and takes no more of the send; and a send of 0 gives no new hit
    8. the distortion's level and characters: more drive is never quieter, and never
       louder at its peak than the dry; a sample is driven by its own peak, so a quiet
       one as hard as a loud one; and soft, hard, fold and crush each a shape of its own
    9. each effect's DSP has a switch~, the crush stage one of its own, and each of the
       reverb's engines one, run by e_tail
   10. a held repeat's tails: a hit under a hold sends nothing and the live sound is muted
       while its engine rings on; the last steps loop at their place and level, follow
       the tempo in speed and pitch, and no sample jumps at the seam or either crossing
   11. rush: past the handoff the output is the frozen loop, at the rate asked, the live kit unheard,
       and the kit comes back after

Standard library only.
"""
import math
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
# The reverb's engines, by the driver's names for e_verb's types 0 to 2, and their files.
ENGINE = {"PLATE": "plate", "GIGA": "gigaverb", "FREE": "freeverb"}
ENGINES = ("e_plate", "e_gigaverb", "e_freeverb")
# How far apart the types' levels may be; and when each one's reverb starts after a click, the
# first sample over REFLECTION, in samples: gigaverb at once, the plate after its shortest path,
# the right half's first tap, 266 of the paper's samples at 29761 Hz, 394 here, and freeverb after
# its shortest comb, 1116 (25.3 ms). The voice's throw reaches e_verb a block late, 64 samples, as
# measured (ref/module/sequencer.md, The effects), and up to two blocks are allowed, so a change in
# the order Pd runs c_kit in moves none of them into another's range.
LEVEL_DB = 1.5
RING_DB = 1.5
REFLECTION = 0.002
FIRST = {name: (max(4, own - 4), own + 128 + 4) for name, own in (("PLATE", 394), ("GIGA", 0),
                                                           ("FREE", 1116))}


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


def hp_rms(xs, fc=300.0):
    """RMS after a one-pole high-pass at fc: the research's weighting of the reverb's types'
    levels, so a low end does not decide how loud a reverb sounds."""
    a = math.exp(-2 * math.pi * fc / 44100)
    y = px = py = acc = 0.0
    for v in xs:
        v = v / 32768.0
        y = a * (py + v - px)
        px, py = v, y
        acc += y * y
    return (acc / len(xs)) ** 0.5 if xs else 0.0


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
    A.check("exactly one report, warn c_kit samples-5 (pads 1, 5, 7, 9 and 10 of 16)",
            errs == [["warn", "c_kit", "samples-%d" % len(G.SAMPLES)]] and len(G.SAMPLES) == 5,
            "c_kit's err lines: %s. Five samples is a count no other run gives, so "
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
    # drive 100 drives the sample's peak a hundred times past the clip, soft as a track starts,
    # and the makeup holds at -8 dB, 0.4, times the peak and soft's trim of 0.9: 0.09
    A.check("⛔ DIST: drive 100 mixed all the way in squares pad 1's sine off: its crest factor "
            "near 1 where a sine's is 1.41", crest(seg) < 1.15,
            "crest %.3f, rms %.4f, peak %.4f" % (crest(seg), rms(seg), peak(seg)))
    A.check("DIST: ... at the makeup's floor, -8 dB, times the sample's peak and soft's trim: "
            "0.4 x 0.25 x 0.9, 0.09", abs(peak(seg) - 0.09) < 0.01, "peak %.4f" % peak(seg))
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
    t = G.hit_time(window("TAIL-1"), G.SET_MS)
    e1 = rms(span(t + 0.5 + 0.02, t + 0.5 + G.SAMPLE_S - 0.03))
    e2 = rms(span(t + 1.0 + 0.02, t + 1.0 + G.SAMPLE_S - 0.03))
    A.check("⛔ TAIL: pad 1's level set to 0 after its hit went in, its echoes ring out: the first "
            "at the hit's level, the second at feedback 50's 0.475 of it",
            abs(e1 - TONE_RMS) / TONE_RMS < RMS_TOL and abs(e2 / e1 - 0.475) < 0.03,
            "echoes at rms %.5f and %.5f, a ratio of %.3f" % (e1, e2, e2 / e1 if e1 else 0))
    # The reverb, each of its three types (Brendan, 2026-11-05): a tail that dies away, as loud
    # in each, and the engine's own first reflection after a click, which tells which one played.
    def after_end(name, a, b, off_ms=G.SET_MS):
        """From a to b seconds after the end of pad 10's burst, hit off_ms into the window."""
        t = G.hit_time(window(name), off_ms) + G.CLICK_S + G.BURST_S
        return span(t + a, t + b)

    def db(a, b):
        return 20 * math.log10(a / b) if a > 0 and b > 0 else float("-inf")

    level = {}
    for name in G.TYPES:
        tail = after_end("VERB-" + name, 0.02, 0.12)
        late = after_end("VERB-" + name, 0.5, 0.6)
        level[name] = hp_rms(after_end("VERB-" + name, 0.02, 0.42))
        A.check("⛔ VERB-%s: pad 10's send at 100 leaves the %s's tail after its burst ends, dying "
                "away" % (name, ENGINE[name]), rms(tail) > 0.005 and rms(late) < rms(tail) / 3,
                "rms %.5f just after the burst, %.5f half a second on" % (rms(tail), rms(late)))
    for name in G.TYPES[1:]:
        A.check("⛔ VERB-%s: ... as loud as the plate's, within %g dB, so changing the type does "
                "not jump" % (name, LEVEL_DB), abs(db(level[name], level["PLATE"])) < LEVEL_DB,
                "%+.2f dB: %.5f against the plate's %.5f, the tail's first 0.4 s high-passed at "
                "300 Hz, as the research weighed them" % (db(level[name], level["PLATE"]),
                                                          level[name], level["PLATE"]))
    for name in G.TYPES:
        t = G.hit_time(window("CLICK-" + name), G.SET_MS) + G.CLICK_S
        click = max(range(int((t - 0.005) * rate), int((t + 0.01) * rate)), key=lambda i: abs(x[i]))
        # past the click's own interpolation, three samples
        got = next((i - click for i in range(click + 4, click + int(0.05 * rate))
                    if abs(x[i]) / 32768.0 > REFLECTION), None)
        lo, hi = FIRST[name]
        A.check("⛔ CLICK-%s: its reverb starts %d to %d samples after the click, the %s's own first "
                "reflection, so it is the %s that plays" % (name, lo, hi, ENGINE[name],
                                                             ENGINE[name]),
                got is not None and lo <= got <= hi,
                "the click at sample %d, the reverb's first sample over %g %s later"
                % (click, REFLECTION, got))
    # The plate left for freeverb while its tail rings: it rings out, and a burst after the change
    # is heard through freeverb alone.
    t = G.hit_time(window("RING"), G.SET_MS) + G.CLICK_S + G.BURST_S
    change = G.hit_time(window("RING"), G.SET_MS + G.RING_CHANGE_MS)
    before = rms(span(t + 0.02, change - 0.01))
    rung = rms(span(change + 0.35, change + 0.45))
    A.check("⛔ RING: the type changed to freeverb while the plate rings, the plate rings out: its "
            "tail goes on past 300 ms after the change, not cut", rung > 0.002
            and rung > before / 10, "rms %.5f before the change, %.5f 0.35 to 0.45 s after it"
            % (before, rung))
    again = hp_rms(after_end("RING", 0.02, 0.22, G.SET_MS + G.RING_AGAIN_MS))
    alone = hp_rms(after_end("RING-REF", 0.02, 0.22))
    A.check("⛔ RING: a burst after the change is freeverb's alone, as loud as freeverb at the same "
            "size with nothing before it, within %g dB: the plate no longer takes the send"
            % RING_DB, abs(db(again, alone)) < RING_DB,
            "%+.2f dB: %.5f after the second burst, %.5f in RING-REF"
            % (db(again, alone), again, alone))
    off = after_end("VERB-OFF", 0.02, 0.3)
    A.check("VERB-OFF: at send 0 a hit leaves nothing after its burst ends",
            peak(off) < SILENT, "peak %.5f after the burst" % peak(off))

    # ---- 8. the distortion's level and characters ---------------------------
    print("\n--- 8. the distortion: louder with drive, by its sample's peak, four characters ---")

    def asym(xs):
        hi, lo = max(xs) / 32768.0, min(xs) / 32768.0
        return abs(hi + lo) / (hi - lo) if hi > lo else 0.0

    def per_cycle(xs, hz):
        return crossings(xs) / (len(xs) / float(rate) * hz)

    # 441 Hz is 100 samples a cycle: a shape that repeats differs from itself 100 samples on
    # by nothing; one held at a rate of its own does.
    def repeats(xs, n=100):
        d = [float(xs[i + n]) - xs[i] for i in range(len(xs) - n)]
        return (sum(v * v for v in d) / len(d)) ** 0.5 / 32768.0 / rms(xs) if d and rms(xs) else 9

    half = inside(window("HALF"), G.SET_MS)
    A.check("⛔ HALF: more drive is never quieter: pad 1 at drive 100 is at least as loud as at 50",
            rms(seg) >= rms(half) * 0.95, "rms %.4f at 100, %.4f at 50" % (rms(seg), rms(half)))
    A.check("⛔ ... and neither is louder at its peak than the dry sample, 0.25",
            max(peak(seg), peak(half)) <= G.AMP * 1.02,
            "peaks %.4f at 100 and %.4f at 50" % (peak(seg), peak(half)))
    A.check("... nor quieter than the dry by more than the makeup's floor and soft's trim allow",
            min(rms(seg), rms(half)) >= TONE_RMS * 0.4 * 0.9 * 0.95,
            "rms %.4f and %.4f against the dry's %.4f" % (rms(seg), rms(half), TONE_RMS))
    pk = inside(window("PEAK"), G.SET_MS)
    A.check("⛔ PEAK: pad 5's sample, a quarter of pad 1's level, is driven as hard at the same "
            "drive: c_voice tells e_drive its sample's peak", crest(pk) < 1.2
            and abs(crest(pk) - crest(half)) < 0.05,
            "crest %.3f against pad 1's %.3f; a sine's is 1.41" % (crest(pk), crest(half)))
    A.check("PEAK: ... and comes out a quarter as loud, its own peak's share",
            abs(rms(pk) / rms(half) - 0.25) < 0.0125 if rms(half) else False,
            "rms %.5f, pad 1's %.5f, a ratio of %.3f" % (rms(pk), rms(half),
                                                         rms(pk) / rms(half) if rms(half) else 0))
    hz = G.SAMPLES[5]
    hard = inside(window("HARD"), G.SET_MS)
    A.check("⛔ HARD: char 2 clips a sine lopsided, its two peaks apart, where soft's are level, "
            "and squarer than soft at drive 0, whose crest is a sine's",
            asym(hard) > 0.025 and asym(pk) < 0.01 and crest(hard) < 1.3,
            "lopsided %.3f against soft's %.3f, crest %.3f" % (asym(hard), asym(pk), crest(hard)))
    fold = inside(window("FOLD"), G.SET_MS)
    A.check("⛔ FOLD: char 3 folds the sine back on itself: at drive 50 it crosses 0 ten times a "
            "cycle, where soft and hard cross twice",
            per_cycle(fold, hz) > 6 and per_cycle(pk, hz) < 2.5 and per_cycle(hard, hz) < 2.5,
            "crossings a cycle: fold %.1f, soft %.1f, hard %.1f"
            % (per_cycle(fold, hz), per_cycle(pk, hz), per_cycle(hard, hz)))
    crush = inside(window("CRUSH"), G.SET_MS)
    A.check("⛔ CRUSH: char 4 holds the sound at a rate of its own, so it no longer repeats every "
            "cycle, where soft, hard and fold do",
            repeats(crush) > 0.15 and max(repeats(pk), repeats(hard), repeats(fold)) < 0.03,
            "off by %.3f a cycle, against soft %.3f, hard %.3f, fold %.3f"
            % (repeats(crush), repeats(pk), repeats(hard), repeats(fold)))
    again = inside(window("SOFT-AGAIN"), G.SET_MS)
    A.check("⛔ SOFT-AGAIN: char 1 again takes the crush stage out: the sound repeats and is "
            "soft's level again", repeats(again) < 0.03 and abs(rms(again) - rms(pk)) / rms(pk)
            < RMS_TOL if rms(pk) else False,
            "off by %.3f a cycle, rms %.5f against soft's %.5f" % (repeats(again), rms(again),
                                                                  rms(pk)))

    # ---- 9. every effect switches itself off --------------------------------
    print("\n--- 9. each effect's DSP has a switch~, so an effect unused costs nothing ---")
    for name in ("e_drive", "e_delay", "e_verb") + ENGINES:
        boxes, _cons = top_boxes(os.path.join(ROOT, "Cut It", name + ".pd"))
        A.check("%s holds one switch~" % name, len(find(boxes, "switch~")) == 1,
                "switch~ boxes: %s" % find(boxes, "switch~"))
    # Each engine its own switch~, run by e_tail, so only the chosen one runs, and one left rings
    # out first (Brendan, 2026-11-05).
    boxes, _cons = top_boxes(os.path.join(ROOT, "Cut It", "e_verb.pd"))
    A.check("e_verb holds each of its three engines once", [len(find(boxes, e)) for e in ENGINES]
            == [1, 1, 1], "%s" % {e: find(boxes, e) for e in ENGINES})
    for name in ENGINES:
        boxes, _cons = top_boxes(os.path.join(ROOT, "Cut It", name + ".pd"))
        A.check("%s's switch~ is run by one e_tail" % name, len(find(boxes, "e_tail")) == 1,
                "e_tail boxes: %s" % find(boxes, "e_tail"))
    crush_sub, inside_crush = [], False
    for r in lib_pd.read(os.path.join(ROOT, "Cut It", "e_drive.pd")):
        if r.startswith("#N canvas") and r[:-1].split()[-2:-1] == ["crush"]:
            inside_crush = True
        elif r.startswith("#X restore"):
            inside_crush = False
        elif inside_crush and r.startswith("#X obj"):
            crush_sub.append(r[:-1].split()[4])
    A.check("⛔ e_drive's crush stage is a subpatch with a switch~ of its own, off for every "
            "character but crush, so the other three don't pay for it",
            "switch~" in crush_sub and "samphold~" in crush_sub,
            "pd crush's objects: %s" % crush_sub)

    # ---- 10. a held repeat's tails ------------------------------------------
    print("\n--- 10. a held repeat's tails: no new wet, a loop in time, following the tempo ---")

    def freq(xs):
        return crossings(xs) / 2.0 / (len(xs) / float(rate)) if xs else 0.0

    def biggest_step(xs):
        """The largest jump between two samples, as a share of full scale: a click is one."""
        return max((abs(float(xs[i + 1]) - xs[i]) for i in range(len(xs) - 1)), default=0) / 32768.0

    # pad 7's tone at full level: the sample's own largest step between two samples, a little more
    # where a delay's echoes overlap by the block it takes off its time
    TONE_STEP = 2 * math.pi * G.SAMPLES[7] / rate * G.AMP
    FREEZE_S = 192.0 / rate
    t0 = G.hit_time(window("HOLD-HIT"))
    hit = t0 + G.SET_MS / 1000.0 + G.TAPE_HIT_MS / 1000.0
    freed = t0 + (G.SET_MS + G.TAPE_HOLD_MS) / 1000.0
    dry = span(hit + 0.02, hit + G.SAMPLE_S - 0.03)
    A.check("HOLD-HIT: a hit under a hold plays its dry sound as ever", abs(rms(dry) - TONE_RMS)
            / TONE_RMS < RMS_TOL, "rms %.5f, wanted %.5f" % (rms(dry), TONE_RMS))
    echo = span(hit + 0.5 - 0.01, hit + 0.5 + G.SAMPLE_S + 0.02)
    A.check("⛔ HOLD-HIT: and sends nothing: let go before its echo was due, no echo comes, ever",
            peak(echo) < SILENT and hit + 0.5 > freed + 0.01, "peak %.5f where its echo would be"
            % peak(echo))
    t = G.hit_time(window("HOLD-AFTER"), G.SET_MS)
    echo = span(t + 0.5 + 0.02, t + 0.5 + G.SAMPLE_S - 0.03)
    A.check("⛔ HOLD-AFTER: let go, the sends are back: the next hit echoes, at its level",
            abs(rms(echo) - TONE_RMS) / TONE_RMS < RMS_TOL, "rms %.5f, wanted %.5f"
            % (rms(echo), TONE_RMS))

    t = G.hit_time(window("RING-TAIL"), G.SET_MS)
    second = span(t + 1.0 + 0.02, t + 1.0 + G.SAMPLE_S - 0.03)
    A.check("⛔ RING-TAIL: held over the second echo, the live sound is muted: not a sample of it",
            peak(span(t + G.RING_HOLD_S + FREEZE_S + 0.012, t + G.RING_HOLD_S + G.RING_HOLD_FOR_S
                      - 0.002)) < SILENT and rms(second) < 0.001,
            "peak %.5f through the hold, rms %.5f where the second echo was"
            % (peak(span(t + G.RING_HOLD_S + FREEZE_S + 0.012, t + G.RING_HOLD_S
                         + G.RING_HOLD_FOR_S - 0.002)), rms(second)))
    third = rms(span(t + 1.5 + 0.02, t + 1.5 + G.SAMPLE_S - 0.03))
    A.check("⛔ RING-TAIL: the engine rang on under it, its tail dying as usual: let go, the third "
            "echo is 0.475 squared of the hit, no blast and no silence", abs(third / TONE_RMS
            - 0.475 ** 2) < 0.02 and peak(span(t + G.RING_HOLD_S, t + 2.8)) <= G.AMP * 1.02,
            "rms %.5f, %.3f of the hit, wanted %.3f; peak %.4f" % (third, third / TONE_RMS,
                                                                   0.475 ** 2, peak(span(
                t + G.RING_HOLD_S, t + 2.8))))

    t0 = G.hit_time(window("LOOP"), G.SET_MS)
    held = t0 + G.LOOP_S
    # the echo, a 0.3 s tone at 500 ms, sits 0.65 s into the 1000 ms of tape before the hold

    def burst(at, name, length, want_hz, level=TONE_RMS):
        """The loop's burst, the echo as it is on the tape, at seconds at into the recording:
        where it starts, and its level and its pitch inside it. Its place is good to 2 ms of tape,
        so more at a slower speed."""
        o = onset(at - 0.03, at + 0.03)
        seg = span(at + 0.015 * length / G.SAMPLE_S, at + length - 0.03 * length / G.SAMPLE_S)
        late = (o / float(rate) - at) * 1000 if o is not None else None
        within = 2.0 * max(1, length / G.SAMPLE_S)
        A.check("⛔ %s: the loop's burst comes %.3f s in, within %g ms" % (name, at - held, within),
                o is not None and abs(late) < within,
                "first sample over at %s ms from where it is due" % late)
        A.check("⛔ %s: ... at the recording's level" % name, abs(rms(seg) - level) / level < RMS_TOL * 2,
                "rms %.5f, wanted %.5f" % (rms(seg), level))
        A.check("⛔ %s: ... at %.0f Hz" % (name, want_hz), abs(freq(seg) - want_hz) / want_hz < FREQ_TOL,
                "measured %.1f Hz" % freq(seg))
        return o

    hz = G.SAMPLES[7]
    first = burst(held + 0.65, "LOOP", G.SAMPLE_S, hz)
    second = burst(held + 1.65, "LOOP, again", G.SAMPLE_S, hz)
    A.check("⛔ LOOP: the loop is the tape's 1000 ms, to the sample's few", first and second
            and abs(second - first - rate) <= 8, "%s samples from one to the next"
            % (second - first if first and second else None))
    quiet = span(held + 0.012 + FREEZE_S, held + 0.64)
    A.check("LOOP: ... with nothing where the tape has nothing", peak(quiet) < SILENT,
            "peak %.5f before the first burst" % peak(quiet))
    moved = G.hit_time(window("LOOP-240"))
    # 240 BPM: 500 ms a round. The tempo went at 1.99 s of tape, so 0.66 of a round to its burst.
    at = moved + (1.65 - 0.99 - 0.0) / 2 + (held + 1.99 - moved) / 2
    burst(at, "LOOP-240, the tempo doubled", G.SAMPLE_S / 2, hz * 2)
    burst(at + 0.5, "LOOP-240, again", G.SAMPLE_S / 2, hz * 2)
    moved = G.hit_time(window("LOOP-60"))
    at = moved + (1.65 - 0.99) * 2
    burst(at, "LOOP-60, the tempo halved", G.SAMPLE_S * 2, hz / 2)
    ended = G.hit_time(window("LOOP-END"), 100)
    after = span(ended + 0.012, G.hit_time(window("SEAM")) - 0.01)
    A.check("⛔ LOOP-END: let go, the loop stops: nothing after it", peak(after) < SILENT,
            "peak %.5f after the release" % peak(after))

    t = G.hit_time(window("SEAM"), G.SET_MS)
    a, b = t + G.SEAM_S - 0.05, t + G.SEAM_S + 1.2 + 0.1
    # (the second hold, below, is 150 ms after the first let go)
    seg = span(a, b)
    A.check("SEAM: a tone runs through the hold, so there is a seam to hear",
            min(rms(span(a + 0.03 + i * 0.1, a + 0.13 + i * 0.1)) for i in range(11)) > TONE_RMS * 0.3,
            "the least rms of its 100 ms stretches is %.5f" % min(
                rms(span(a + 0.03 + i * 0.1, a + 0.13 + i * 0.1)) for i in range(11)))
    own = biggest_step(span(t + 0.32, a))
    A.check("⛔ SEAM: going in, round the seam and coming out, no sample jumps further than the tone "
            "did before it: not a click", biggest_step(seg) < own * 1.1 and own < TONE_STEP * 1.4,
            "the largest step %.5f, the tone's own %.5f" % (biggest_step(seg), own))
    # Held again 150 ms after that, for 300 ms of tape: the loop runs over the place the recording
    # stopped and started, 150 ms back, which fades out and in rather than meeting in a jump.
    again = t + G.SEAM_S + 1.2 + G.SEAM_AGAIN_S
    seg = span(again - 0.01, again + G.SEAM_AGAIN_FOR_S + 0.03)
    A.check("⛔ SEAM: held again soon after, over where the recording stopped and started, no click "
            "there either", biggest_step(seg) < own * 1.1,
            "the largest step %.5f, the tone's own %.5f" % (biggest_step(seg), own))
    t = G.hit_time(window("TAIL"), G.SET_MS)
    held = t + G.TAIL_HOLD_S
    rec = rms(span(held - G.TAIL_SPAN / 1000.0, held))
    loop = rms(span(held + 0.05, held + 0.05 + G.TAIL_SPAN / 1000.0))
    A.check("⛔ TAIL: a reverb's tail, recorded after all those holds, comes back as loud as it was, "
            "where the live sound has moved on", rec > 0.005 and abs(loop - rec) / rec < 0.15,
            "rms %.5f in the recording, %.5f in the loop" % (rec, loop))
    late = rms(span(held + 0.05 + 2 * G.TAIL_SPAN / 1000.0, held + 0.05 + 3 * G.TAIL_SPAN / 1000.0))
    A.check("TAIL: ... each time round", abs(late - rec) / rec < 0.15,
            "rms %.5f, two rounds on" % late)

    # ---- 11. rush ------------------------------------------------------------
    print("\n--- 11. rush: one cycle of pad 7's tone, frozen, at the rate asked ---")
    t = G.hit_time(window("RUSH"), G.SET_MS) + G.RUSH_AT / 1000.0
    for k, hz in enumerate(G.RUSH_RATES):
        # past the crossing and the 20 ms ramp
        turn = t + k * G.RUSH_TURN / 1000.0
        seg = span(turn + 0.04, turn + G.RUSH_TURN / 1000.0)
        got = freq(seg)
        A.check("⛔ RUSH: looped at %d Hz, the output is at %d Hz, by its zero crossings" % (hz, hz),
                abs(got - hz) / hz < 0.02, "%.1f Hz" % got)
    first = span(t + 0.04, t + G.RUSH_HIT / 1000.0)
    A.check("⛔ RUSH: the loop is the tone's level, read from before the recorder's fade",
            abs(rms(first) - TONE_RMS) / TONE_RMS < 0.15, "rms %.5f, the tone's %.5f" % (rms(first), TONE_RMS))
    under = span(t + G.RUSH_HIT / 1000.0 + 0.02, t + G.RUSH_TURN / 1000.0)
    A.check("⛔ RUSH: a hit under it is unheard, the live kit muted",
            abs(rms(under) - rms(first)) / rms(first) < 0.05, "rms %.5f, %.5f before the hit" % (rms(under), rms(first)))
    end = t + len(G.RUSH_RATES) * G.RUSH_TURN / 1000.0
    A.check("RUSH: let go, the loop stops", peak(span(end + 0.02, end + 0.2)) < SILENT * 30,
            "peak %.5f" % peak(span(end + 0.02, end + 0.2)))
    back = inside(window("RUSH-BACK"), G.SET_MS)
    A.check("⛔ RUSH: and the kit is back, pad 7 at its own pitch and level",
            abs(freq(back) - G.SAMPLES[7]) < 5 and abs(rms(back) - TONE_RMS) / TONE_RMS < 0.1,
            "%.1f Hz, rms %.5f" % (freq(back), rms(back)))
    # The echo is the second of tape's last 250 ms. Rushed over from 850 to 1050 ms after the hit, its
    # player stopped 16 ms in, so it comes round that much later than 1500 ms: from 1684 to 1934.
    t = G.hit_time(window("RUSH-TAPE"), G.SET_MS)
    seg = span(t + 1.72, t + 1.90)
    A.check("⛔ RUSH: a tail loop under it goes on where it was, after",
            abs(freq(seg) - G.SAMPLES[7]) < 8 and abs(rms(seg) - TONE_RMS) / TONE_RMS < 0.3,
            "%.1f Hz, rms %.5f" % (freq(seg), rms(seg)))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
