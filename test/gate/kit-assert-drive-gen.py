#!/usr/bin/env python3
"""Generates the driver, the harness and the five samples for the kit gate.

    kit-assert-drive-gen.py OUT-DRIVE.pd OUT-HARNESS.pd PATCHDIR WAVPATH

The harness holds c_kit alone and records its outlet~; the samples go where
c_voice reads them, samples/drums/ in the scratch copy of the patch, which
lib_scratch makes without the Mac's own samples. Pads 1, 5, 7, 9 and 10 only, so
the count c_kit reports is a number no other run could give, and a pad with no
sample is there to be silent. Pad 5's is a quarter of the others' level, so the
distortion's scaling to a sample's peak shows, and 441 Hz, a hundred samples a
cycle, so a sound held at a rate of its own, the crush, shows as one that no
longer repeats. Pad 9's is a click and pad 10's a burst of pink noise, for the
reverb.

One recording, cut by time: each hit lands at a known instant after the
recording starts, and the analyzer reads a window inside each sample. The last
four windows of the first eight set a track's volume or pitch first, as c_steps does, then hit
it; the rest set its effects the same way: the distortion on pad 1, a delay on pad 7 at a tempo
of 240 off the tempo bus, and a delay with feedback on pad 1 whose level goes to 0 once its hit has
gone into it, so its echoes ring out; then the distortion again, pad 1 at half the drive, and
pad 5 through each of its four characters; then the reverb, each of its three types in turn, the
plate, gigaverb and freeverb (Brendan, 2026-11-05): pad 10's send into it, a burst of pink noise,
whose tail is weighed as the research weighed the types' levels on Brendan's drums, then pad 9's,
a click, whose reverb is heard alone, so when it starts tells the engine; then the plate left for
freeverb while its tail rings, and a burst after; and last, a send of 0.
"""
import math
import os
import random
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 40
RATE = 44100

# The samples: a tone each on pads 1, 5 and 7, so the analyzer can tell them apart by pitch, pad
# 5's at a quarter of the others' level; a click on pad 9, one sample CLICK_S into silence, past
# c_voice's 2 ms dip and 1 ms rise, so what follows it is the reverb alone; and on pad 10 BURST_S
# of pink noise from there, its spectrum near enough a drum kit's that the reverb's types are as
# loud on it as on Brendan's drums, where a click or a tone is not: a click's flat top end makes
# gigaverb 2 to 3 dB quieter, a tone's tail rises and falls with the room's modes.
AMP = 0.25
SAMPLE_S = 0.3
SAMPLES = {1: 440.0, 5: 441.0, 7: 660.0, 9: "click", 10: "pink"}
AMPS = {5: AMP / 4}
CLICK_S, CLICK_AMP = 0.01, 0.5
BURST_S, BURST_SEED = 0.1, 20261105

# The driver's times, absolute from load. c_kit reports its count at 2 s.
DSP_MS = 300
REC_MS = 2800
# writesf~ starts on the window's second body: 20 ms, then one GAP later.
REC_START_MS = REC_MS + 20 + GAP

# Each hit, in seconds after REC_MS: (window, [(offset_ms, pad, velocity)]).
SET_MS = 10
# The reverb's types, e_verb's type 0 to 2 (Brendan, 2026-11-05), a window of each from VERB_S;
# and, in RING, when the type changes after its first hit, and its second hit, late enough that
# the plate's tail is heard first for longer than e_tail's 300 ms, which a switch~ turned off at
# the change would cut.
TYPES = ["PLATE", "GIGA", "FREE"]
VERB_S = 20.0
RING_CHANGE_MS, RING_AGAIN_MS = 400, 900
HITS = [
    ("FULL", 0.5, [(0, 1, 127)]),
    ("SOFT", 1.5, [(0, 7, 16)]),
    ("MISSING", 2.5, [(0, 3, 127)]),
    ("PAST", 3.0, [(0, 17, 127)]),
    ("ZERO", 3.5, [(0, 1, 0)]),
    ("RETRIG", 4.0, [(0, 1, 127), (50, 1, 127)]),
    ("VOL", 5.0, [(SET_MS, 1, 127)]),
    ("BOOST", 5.5, [(SET_MS, 1, 127)]),
    ("UP", 6.0, [(SET_MS, 7, 127)]),
    ("DOWN", 6.5, [(SET_MS, 7, 127)]),
    ("DIST", 7.5, [(SET_MS, 1, 127)]),
    ("DARK", 8.0, [(SET_MS, 1, 127)]),
    ("DRY", 8.5, [(SET_MS, 1, 127)]),
    ("ECHO", 9.0, [(SET_MS, 7, 127)]),
    ("TAIL", 10.5, [(SET_MS, 1, 127)]),
    ("HALF", 16.5, [(SET_MS, 1, 127)]),
    ("PEAK", 17.0, [(SET_MS, 5, 127)]),
    ("HARD", 17.5, [(SET_MS, 5, 127)]),
    ("FOLD", 18.0, [(SET_MS, 5, 127)]),
    ("CRUSH", 18.5, [(SET_MS, 5, 127)]),
    ("SOFT-AGAIN", 19.0, [(SET_MS, 5, 127)]),
] + [w for k, t in enumerate(TYPES) for w in (
    ("VERB-" + t, VERB_S + 2.0 * k, [(SET_MS, 10, 127)]),
    ("CLICK-" + t, VERB_S + 1.2 + 2.0 * k, [(SET_MS, 9, 127)]))] + [
    # the plate left for freeverb while it rings, a burst before the change and one after, and
    # freeverb's burst alone once the plate's tail has died and it has switched itself off
    ("RING", VERB_S + 6.0, [(SET_MS, 10, 127), (SET_MS + RING_AGAIN_MS, 10, 127)]),
    ("RING-REF", VERB_S + 11.0, [(SET_MS, 10, 127)]),
    ("VERB-OFF", VERB_S + 13.5, [(SET_MS, 10, 127)]),
]
# What a window sends c_kit before its hits, SET_MS before them: a track's volume
# in dB, -30 to +6, and its pitch in semitones, -12 to +12, as c_steps sends them.
SETS = {"VOL": ["vol 1 -6"], "BOOST": ["vol 1 6"], "UP": ["pitch 7 12"], "DOWN": ["pitch 7 -12"],
        # the distortion, as c_steps tells it (c_steps.lua's R.FX): driven all the way and mixed
        # all the way in, then darkened, then mixed out
        "DIST": ["vol 1 0", "drive 1 100", "dist 1 100"], "DARK": ["tone 1 0"],
        "DRY": ["dist 1 0"],
        # pad 7's delay: a half note, eight steps, at 240 BPM is 500 ms, at full level, one echo
        "ECHO": ["pitch 7 0", "delay-time 7 8", "feedback 7 0", "delay 7 100"],
        # pad 1's: the same half note, feedback 50, an echo each 500 ms at 0.475 of the last
        "TAIL": ["delay 7 0", "delay-time 1 8", "feedback 1 50", "delay 1 100"],
        # the distortion at half the drive on pad 1, its tone open again; then pad 5, a quarter
        # of pad 1's level, at the same drive and mix, soft as a track starts; then its
        # characters, as c_steps tells them: hard at drive 0, fold and crush at 50, and soft again
        "HALF": ["tone 1 100", "drive 1 50", "dist 1 100"],
        "PEAK": ["drive 5 50", "dist 5 100"], "HARD": ["char 5 2", "drive 5 0"],
        "FOLD": ["char 5 3", "drive 5 50"], "CRUSH": ["char 5 4"], "SOFT-AGAIN": ["char 5 1"],
        # each type at size 20, a decay of about 0.9 s, pad 9's send and pad 10's at 100
        "VERB-PLATE": ["verb-type 0", "size 20", "send 9 100", "send 10 100"],
        "VERB-GIGA": ["verb-type 1"], "VERB-FREE": ["verb-type 2"],
        # the plate at size 50, 2.2 s, so it is still ringing when the type changes to freeverb;
        # then freeverb alone at size 50, the level a hit after the change should have
        "RING": ["verb-type 0", "size 50"], "RING-REF": ["verb-type 2"],
        "VERB-OFF": ["send 9 0", "send 10 0", "size 20"]}
# What a window sends the tempo bus with its settings: 240 BPM, a step 62.5 ms.
TEMPO = {"ECHO": 240}
ECHO_BPM = 240
# What a window sends after its hit, (ms after the window, message): pad 1's level to 0 once its
# 0.3 s sample has gone into the delay, before the first echo.
AFTER = {"TAIL": [(SET_MS + 350, "delay 1 0")], "RING": [(SET_MS + RING_CHANGE_MS, "verb-type 2")]}
STOP_S = VERB_S + 15.0
DONE_S = VERB_S + 15.5


def hit_time(at_s, off_ms=0):
    """A hit's time in the recording, in seconds: its window's body fires 20 ms
    after the window, plus its offset (lib_drive)."""
    return (REC_MS + at_s * 1000 + 20 + off_ms - REC_START_MS) / 1000.0


def pink(n):
    """n samples of pink noise, peak 0.5, the same every run: Paul Kellet's economy filter on
    seeded white noise."""
    r = random.Random(BURST_SEED)
    b0 = b1 = b2 = 0.0
    out = []
    for _ in range(n):
        w = r.uniform(-1, 1)
        b0 = 0.99765 * b0 + w * 0.0990460
        b1 = 0.96300 * b1 + w * 0.2965164
        b2 = 0.57000 * b2 + w * 1.0526913
        out.append(b0 + b1 + b2 + w * 0.1848)
    top = max(abs(v) for v in out)
    return [0.5 * v / top for v in out]


def write_samples(patchdir):
    d = os.path.join(patchdir, "samples", "drums")
    os.makedirs(d, exist_ok=True)
    n = int(SAMPLE_S * RATE)
    for pad, hz in SAMPLES.items():
        if hz == "click":
            at = int(CLICK_S * RATE)
            frames = b"".join(struct.pack("<h", int(32767 * CLICK_AMP) if i == at else 0)
                              for i in range(n))
        elif hz == "pink":
            x = pink(int(BURST_S * RATE))
            at = int(CLICK_S * RATE)
            frames = b"".join(struct.pack("<h", int(32767 * x[i - at]) if 0 <= i - at < len(x)
                                          else 0) for i in range(n))
        else:
            amp = AMPS.get(pad, AMP)
            frames = b"".join(struct.pack("<h", int(32767 * amp * math.sin(2 * math.pi * hz * i
                                                                           / RATE)))
                              for i in range(n))
        with wave.open(os.path.join(d, "%02d.wav" % pad), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
            w.writeframes(frames)


def _seq(wav):
    at = lambda s: REC_MS + int(s * 1000)
    seq = [
        (DSP_MS, "DSP", ["\\; pd dsp 1"], GAP),
        # The open before the start: writesf~ writes nothing to a file it was never given.
        (REC_MS, "REC", ["\\; kit-cmd open %s" % wav, "\\; kit-cmd start"], GAP),
    ]
    for name, s, hits in HITS:
        seq.append((at(s), name, [(0, "\\; tempo %d" % TEMPO[n]) for n in [name] if n in TEMPO]
                    + [(0, "\\; kit-pad %s" % m) for m in SETS.get(name, [])]
                    + [(off, "\\; kit-pad pad %d %d" % (pad, vel)) for off, pad, vel in hits]
                    + [(off, "\\; kit-pad %s" % m) for off, m in AFTER.get(name, [])],
                    GAP))
    # Stop before quit: writesf~ fixes up the WAV header on stop.
    seq.append((at(STOP_S), "STOP", ["\\; kit-cmd stop"], GAP))
    seq.append((at(DONE_S), "DONE", [], GAP))
    return seq


BLURB = ("kit-assert-drive -- GENERATED by kit-assert-drive-gen.py. Do not edit this "
         "file. It plays c_kit in the harness beside it: a full hit \\, a soft hit \\, "
         "a pad with no sample \\, pad 17 \\, velocity 0 and a retrigger \\, then a "
         "track's volume down and up and its pitch up and down \\, then its distortion \\, "
         "a delay \\, a delay's tail \\, the distortion's drive and its characters \\, and "
         "the reverb \\, each of its three types \\, while the harness records c_kit's output.")

NOTES = [
    "Run it through test/gate/kit-assert.sh \\, which loads the harness beside it "
    "and writes the samples: on its own this drives receives nothing listens to.",
]

HARNESS_BLURB = (
    "kit-assert-harness -- GENERATED by kit-assert-drive-gen.py. Do not edit this "
    "file. It holds c_kit alone and records its outlet~. kit-pad and kit-cmd are "
    "bare globals outside the C-2 allowlist: this file exists only in a scratch "
    "directory.")


def write_harness(path):
    B, C = [], []

    def obj(x, y, s):
        B.append("#X obj %d %d %s;" % (x, y, s)); return len(B) - 1

    B.append("#X text 20 20 %s, f 92;" % HARNESS_BLURB)
    pad = obj(20, 260, "r kit-pad")
    kit = obj(20, 300, "c_kit")
    cmd = obj(600, 260, "r kit-cmd")
    wsf = obj(400, 340, "writesf~ 1")
    C += [(pad, 0, kit, 0), (kit, 0, wsf, 0), (cmd, 0, wsf, 0)]
    out = ["#N canvas 20 20 1200 600 12;"] + B + ["#X connect %d %d %d %d;" % t for t in C]
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")
    return len(B), len(C)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.exit("usage: kit-assert-drive-gen.py OUT-DRIVE.pd OUT-HARNESS.pd PATCHDIR "
                 "WAVPATH  (run it through test/gate/kit-assert.sh)")
    w, b, c = D.build(sys.argv[1], _seq(sys.argv[4]), tag="KIT", taps=["err"],
                      quit_ms=REC_MS + int((DONE_S + 0.5) * 1000), blurb=BLURB, notes=NOTES)
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b, c))
    hb, hc = write_harness(sys.argv[2])
    print("%s  c_kit + writesf~  %d boxes  %d connects" % (sys.argv[2], hb, hc))
    write_samples(sys.argv[3])
    print("samples for pads %s in %s" % (sorted(SAMPLES), sys.argv[3]))
