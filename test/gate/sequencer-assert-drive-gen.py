#!/usr/bin/env python3
"""Generates the timed driver for the sequencer gate, into the scratch path given.

It plays the drum page the way a hand would, on param, as m_launchpad publishes
it: a velocity button, steps on two tracks, a pad, the step rule's three cases,
a press on the free corner, a press in another mode. Then the transport: PLAY,
STOP, knob 2 held at 16 and then setting the last step to 3, PLAY again, panic.
Then knob 3 giving track 2 its own last step of 6, a press past it, the two
tracks looping on their own, and the drum screen's snap, sent to u_net over OSC
as the phone sends it, landing at PLAY. Then swing, a repeat pad, the drum
screen's pads (a track's volume, pitch and randomness, over OSC too) and
drunkenness.

The state directory holds a seeded pattern (scratch-gates.py), so the restore at
~3.5 s is under test too. RESTORE opens a second before it and closes a second
after; every edit comes after it, since a restore replaces the pattern.

DSP goes on at 300 ms: the steps are cut from a phasor~.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 20
P = lambda name, v=100: "\\; param %s %d" % (name, v)

SEQ = [
    # Before the restore, and before anything else in the run: page 2's key,
    # since the boot page is page 1 and the drum page is page 2's, then a pad
    # plays now.
    (300, "EARLY", ["\\; pd dsp 1", P("lp-cc-70", 127), P("lp-cc-70", 0), P("pad-11", 90)], GAP),
    (2500, "RESTORE", [], GAP),
    (4500, "VEL-2", [P("pad-26")], GAP),                          # level 2: 32
    (4700, "STEPS-T1", [P("pad-81"), P("pad-85")], GAP),          # track 1, steps 1 and 5
    (4900, "PAD-2", [P("pad-12", 90)], GAP),                      # plays pad 2, selects it
    (5100, "STEP-T2", [P("pad-81")], GAP),                        # track 2, step 1
    (5300, "VEL-6", [P("pad-16")], GAP),                          # level 6: 95
    # The step rule on track 2's step 13, all three cases.
    (5500, "RULE-ON", [P("pad-75")], GAP),                        # off: takes 95
    (5700, "RULE-SAME", [P("pad-75")], GAP),                      # 95 again: off
    (5900, "RULE-ON-AGAIN", [P("pad-75")], GAP),                  # off: 95
    (6100, "VEL-2-AGAIN", [P("pad-26")], GAP),                    # level 2: 32
    (6300, "RULE-OTHER", [P("pad-75")], GAP),                     # 95, another: off
    # The second row of the right 4x4 is in no row of the layout table.
    (6400, "FREE-ROW", [P("pad-36")], GAP),
    # The drum page is page 2's: on page 1, which held it until 2026-11-04, a
    # step pad is an unmapped control.
    (6500, "PAGE-1", [P("lp-cc-80", 127), P("lp-cc-80", 0)], GAP),
    (6700, "OTHER-PAGE", [P("pad-81")], GAP),
    # The tempo is set, not assumed: the analyzer counts the steps in PLAY.
    (6900, "PAGE-2", [P("lp-cc-70", 127), P("lp-cc-70", 0), "\\; tempo 120"], GAP),
    (7200, "PLAY", ["\\; start bang"], GAP),
    (9800, "STOP", ["\\; stop bang"], GAP),
    (10300, "STOPPED", [], GAP),
    # Knob 2 is the last step, held at 16 until turned through it: 0.2 is step 7,
    # held; 0.5 is 17, through it; 0.07 is 3. PLAY again walks 1 to 3, and 3 is
    # not a divisor of 16, so loops parked for sixteen steps would show.
    (10400, "KNOB2-HELD", ["\\; param og-knob-2 0.2"], GAP),
    (10500, "LAST-3", ["\\; param og-knob-2 0.5", "\\; param og-knob-2 0.07"], GAP),
    (10800, "REPLAY", ["\\; start bang"], GAP),
    (11400, "PANIC", ["\\; panic bang"], GAP),
    (11700, "AFTER-PANIC", [], GAP),
    # Knob 3 is track 2's own last step, held at its last step, 3: 0.2 is 7, held;
    # 0.0 is 1, through it; 0.17 is 6. Then step 9, past it, is dark and deaf.
    # After the panic's one-second red, so the page is back to read.
    (12600, "KNOB3", ["\\; param og-knob-3 0.2", "\\; param og-knob-3 0",
                      "\\; param og-knob-3 0.17"], GAP),
    (12800, "PAST-LAST", [P("pad-71")], GAP),
    # Track 1 loops every 3, track 2 every 6, for nine steps.
    (13000, "POLY", ["\\; start bang"], GAP),
    (14100, "POLY-STOP", ["\\; stop bang"], GAP),
    # The drum screen's snap, as the phone sends it: stopped, it waits for PLAY.
    # DONE leaves u_state its two seconds to write the snap's put.
    (14300, "SNAP", ["\\; seqgate-osc drums snap"], GAP),
    (14500, "SNAP-PLAY", ["\\; start bang"], GAP),
    (15000, "SNAP-STOP", ["\\; stop bang"], GAP),
    # Knob 4 is swing, 50% to 75%, held at 50% until turned to it: 0.6 is 65%,
    # held; 0 is 50%, the knob's bottom, which releases it; 1 is 75%. PLAY then
    # puts step 2 three quarters of the way through the pair: at 120 BPM, about
    # 198 ms after step 1 rather than 125, so it paints in SW-LATE, not SW-GAP;
    # step 3 lands on the beat, 260 ms in.
    (15100, "SWING", ["\\; param og-knob-4 0.6", "\\; param og-knob-4 0",
                      "\\; param og-knob-4 1"], GAP),
    (15300, "SW-PLAY", ["\\; start bang"], GAP),
    (15400, "SW-GAP", [], GAP),
    (15490, "SW-LATE", [], GAP),
    (15560, "SW-ON", [], GAP),
    (15700, "SW-STOP", ["\\; stop bang", "\\; param og-knob-4 0"], GAP),
    # Repeat pad 1, the top left of the right 4x4, held after step 3: the
    # playhead stays on 3 and track 1's step 3 plays on every step; let go, the
    # loop goes on from where it would have been, 2 then 3, not from 1.
    (15800, "REP-PLAY", ["\\; start bang"], GAP),
    (16120, "REP-PRESS", [P("pad-45")], GAP),
    (16200, "REP-HELD", [], GAP),
    (16600, "REP-OFF", [P("pad-45", 0)], GAP),
    (16900, "REP-STOP", ["\\; stop bang"], GAP),
    # The drum screen's pads, over OSC as the phone sends them: track 2's
    # volume and pitch, which go to c_kit and are saved; then track 1 at full
    # randomness for nine steps, every step a coin, and back to 0.
    (17000, "SOUND", ["\\; seqgate-osc drums vol 2 -6", "\\; seqgate-osc drums pitch 2 7"],
     GAP),
    (17200, "RAND", ["\\; seqgate-osc drums randomness 1 100"], GAP),
    (17300, "RA-PLAY", ["\\; start bang"], GAP),
    (18400, "RA-STOP", ["\\; stop bang", "\\; seqgate-osc drums randomness 1 0"], GAP),
    # Drunkenness at its top, from the drum screen over OSC, then 96 windows a
    # sixteenth wide, each holding one step when sober. At the top every step
    # strays, by up to two steps, so most windows hold none or two or more.
    (18600, "DRUNK", ["\\; seqgate-osc drums drunk 100"], GAP),
    (18700, "DR-PLAY", ["\\; start bang"], GAP),
] + [(18780 + 125 * k, "DR-%d" % (k + 1), [], GAP) for k in range(96)] + [
    (30780, "DR-STOP", ["\\; stop bang"], GAP),
    (31000, "DONE", [], GAP),
]
QUIT_MS = 31500

# The phone's way in: OSC to u_net's own port, which the gate runner hands each
# gate in CUTIT_INPORT (lib_scratch's state_dir does the same), connected after
# u_net listens at 2000 ms.
INPORT = int(os.environ.get("CUTIT_INPORT") or 9002)
OSC = [
    "#X obj 3800 1000 r seqgate-osc;",
    "#X obj 3800 1050 list append;",
    "#X obj 3800 1100 oscformat cutit;",
    "#X obj 3800 1150 list prepend send;",
    "#X obj 3800 1200 list trim;",
    "#X obj 3800 1300 netsend -u -b;",
    "#X obj 4100 1000 loadbang;",
    "#X obj 4100 1050 del 2600;",
    "#X msg 4100 1100 connect 127.0.0.1 %d;" % INPORT,
]

BLURB = ("sequencer-assert-drive -- GENERATED by sequencer-assert-drive-gen.py. Do "
         "not edit this file. It plays page 2's drum page on param: a velocity \\, "
         "steps on two tracks \\, a pad \\, the step rule's three cases \\, a press on "
         "the free corner \\, a press on another page \\, then PLAY \\, STOP \\, knob 2 "
         "at the last step 3 \\, PLAY again and panic \\, then knob 3 \\, two tracks "
         "looping on their own \\, and the drum screen's snap over OSC.")

NOTES = [
    "Run it through test/gate/sequencer-assert.sh: it rewrites the MIDI objects to "
    "printing stubs in a scratch copy and seeds the state directory with a pattern. "
    "Against the real patch it would send real MIDI.",

    "It needs DSP: c_steps cuts its steps from c_clock's phasor~. -noaudio leaves "
    "DSP running (item 280).",
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: sequencer-assert-drive-gen.py OUT.pd  "
                 "(run it through test/gate/sequencer-assert.sh, which passes a scratch path)")
    w, b, c = D.build(sys.argv[1], SEQ, tag="SEQ",
                      taps=["state", "disp", "err", "mode"], quit_ms=QUIT_MS,
                      blurb=BLURB, notes=NOTES)
    # The OSC sender, after the built boxes: index b is its first.
    with open(sys.argv[1]) as fh:
        lines = fh.read().rstrip("\n").split("\n")
    k = next(i for i, l in enumerate(lines) if l.startswith("#X connect"))
    lines[k:k] = OSC
    lines += ["#X connect %d 0 %d 0;" % (b + i, b + i + 1) for i in range(4)]
    lines += ["#X connect %d 0 %d 0;" % (b + 4, b + 5),
              "#X connect %d 0 %d 0;" % (b + 6, b + 7),
              "#X connect %d 0 %d 0;" % (b + 7, b + 8),
              "#X connect %d 0 %d 0;" % (b + 8, b + 5)]
    with open(sys.argv[1], "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b + len(OSC), c + 8))
