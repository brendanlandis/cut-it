#!/usr/bin/env python3
"""Generates the timed driver for the sequencer gate, into the scratch path given.

It plays the drum page the way a hand would, on param, as m_launchpad publishes
it: first the time signature from the phone, over OSC, 9/8 and 3/4, which set
the page's rows, a press on a row and one past it, and back to the seed's 7/8;
then a velocity button, steps on two tracks, a pad, the step rule's three cases,
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

c_steps holds a change's put back for up to 100 ms, so a drag on the phone saves ten times a
second rather than sixty (ref/module/sequencer.md), and u_song asks for it at once with sync on
the state bus before anything that needs it. The driver does what u_song does: every message is
followed 15 ms later by `state sync`, so each change's put lands in its own window, as each
check expects. DRAG alone sends none: three drunkenness values over OSC, 20 ms apart, make one
put, of the last, when the clock comes.
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
    # The time signature over OSC, as the phone sends it, on the seed's pattern: 7/8 up two to
    # 9/8, rows of 8 and a blue step every 9, wrapping across the rows; then down six to 3/8 and
    # the bottom number up to 3/4, rows of 6 and a blue step every 3. At 3/4 a press on the
    # second row's first cell is step 7, and on the top row's seventh cell, past the row,
    # nothing. Then back to the seed's 7/8, up four and the bottom number up one.
    (4500, "NINE", ["\\; seqgate-osc drums num 1"] * 2, GAP),
    (4700, "THREE", ["\\; seqgate-osc drums num -1"] * 6 + ["\\; seqgate-osc drums den -1"],
     GAP),
    (5000, "ROW-PRESS", [P("pad-71")], GAP),                      # row 2, cell 1: step 7
    (5200, "ROW-DARK", [P("pad-87")], GAP),                       # row 1, cell 7: past the row
    (5400, "SEVEN", ["\\; seqgate-osc drums num 1"] * 4 + ["\\; seqgate-osc drums den 1"],
     GAP),
    (5700, "VEL-2", [P("pad-26")], GAP),                          # level 2: 32
    (5900, "STEPS-T1", [P("pad-81"), P("pad-85")], GAP),          # track 1, steps 1 and 5
    (6100, "PAD-2", [P("pad-12", 90)], GAP),                      # plays pad 2, selects it
    (6300, "STEP-T2", [P("pad-81")], GAP),                        # track 2, step 1
    (6500, "VEL-6", [P("pad-16")], GAP),                          # level 6: 95
    # The step rule on track 2's step 12, all three cases: the second row's fifth
    # cell, at 7/8.
    (6700, "RULE-ON", [P("pad-75")], GAP),                        # off: takes 95
    (6900, "RULE-SAME", [P("pad-75")], GAP),                      # 95 again: off
    (7100, "RULE-ON-AGAIN", [P("pad-75")], GAP),                  # off: 95
    (7300, "VEL-2-AGAIN", [P("pad-26")], GAP),                    # level 2: 32
    (7500, "RULE-OTHER", [P("pad-75")], GAP),                     # 95, another: off
    # The second row of the right 4x4 is in no row of the layout table.
    (7600, "FREE-ROW", [P("pad-36")], GAP),
    # The drum page is page 2's: on page 1, which held it until 2026-11-04, a
    # step pad is an unmapped control.
    (7700, "PAGE-1", [P("lp-cc-80", 127), P("lp-cc-80", 0)], GAP),
    (7900, "OTHER-PAGE", [P("pad-81")], GAP),
    # The tempo is set, not assumed: the analyzer counts the steps in PLAY.
    (8100, "PAGE-2", [P("lp-cc-70", 127), P("lp-cc-70", 0), "\\; tempo 120"], GAP),
    (8400, "PLAY", ["\\; start bang"], GAP),
    (11000, "STOP", ["\\; stop bang"], GAP),
    (11500, "STOPPED", [], GAP),
    # Knob 2 is the last step, held at 16 until turned through it, and at the
    # seed's 7/8 a full turn is 28: 0.2 is step 6, held; 0.6 is 17, through it;
    # 0.07 is 3. PLAY again walks 1 to 3, and 3 is not a divisor of 16, so loops
    # parked for sixteen steps would show.
    (11600, "KNOB2-HELD", ["\\; param og-knob-2 0.2"], GAP),
    (11700, "LAST-3", ["\\; param og-knob-2 0.6", "\\; param og-knob-2 0.07"], GAP),
    (12000, "REPLAY", ["\\; start bang"], GAP),
    # A step fires on its boundary: PLAY goes 20 ms after the mark, as every action does, and
    # step 1 within two blocks of it, before RE-SOON; step 3, the next with a note, 250 ms after
    # it, inside RE-STEP3. A twelfth of a step late, 10 ms at 120 BPM, puts each in the window
    # after.
    (12025, "RE-SOON", [], GAP),
    (12266, "RE-STEP3", [], GAP),
    (12276, "RE-WALK", [], GAP),
    (12600, "PANIC", ["\\; panic bang"], GAP),
    (12900, "AFTER-PANIC", [], GAP),
    # Knob 3 is track 2's own last step, held at its last step, 3: 0.2 is 6, held;
    # 0.0 is 1, through it; 0.17 is 6. Then the second row's first cell, at 7/8
    # step 8, past it, is dark and deaf.
    # After the panic's one-second red, so the page is back to read.
    (13800, "KNOB3", ["\\; param og-knob-3 0.2", "\\; param og-knob-3 0",
                      "\\; param og-knob-3 0.17"], GAP),
    (14000, "PAST-LAST", [P("pad-71")], GAP),
    # Track 1 loops every 3, track 2 every 6, for nine steps.
    (14200, "POLY", ["\\; start bang"], GAP),
    (15300, "POLY-STOP", ["\\; stop bang"], GAP),
    # The drum screen's snap, as the phone sends it: stopped, it waits for PLAY.
    # DONE leaves u_state its two seconds to write the snap's put.
    (15500, "SNAP", ["\\; seqgate-osc drums snap"], GAP),
    (15700, "SNAP-PLAY", ["\\; start bang"], GAP),
    (16200, "SNAP-STOP", ["\\; stop bang"], GAP),
    # Knob 4 is swing, 50% to 75%, held at 50% until turned to it: 0.6 is 65%,
    # held; 0 is 50%, the knob's bottom, which releases it; 1 is 75%. PLAY, 20 ms
    # after its mark, then plays step 1 before SW-SOON, as REPLAY's does but with
    # threshold~ still to re-arm, since this PLAY lands early in a step, and puts
    # step 2 three quarters of the way through the pair: at 120 BPM, 187.5 ms
    # after step 1 rather than 125, so it paints in SW-LATE, not SW-GAP; step 3
    # lands on the beat, 250 ms after step 1, and paints in SW-ON.
    (16300, "SWING", ["\\; param og-knob-4 0.6", "\\; param og-knob-4 0",
                      "\\; param og-knob-4 1"], GAP),
    (16500, "SW-PLAY", ["\\; start bang"], GAP),
    (16525, "SW-SOON", [], GAP),
    (16600, "SW-GAP", [], GAP),
    (16690, "SW-LATE", [], GAP),
    (16760, "SW-ON", [], GAP),
    (16900, "SW-STOP", ["\\; stop bang", "\\; param og-knob-4 0"], GAP),
    # Repeat pad 1, the top left of the right 4x4, held after step 3: the
    # playhead stays on 3 and track 1's step 3 plays on every step; let go, the
    # loop goes on from where it would have been, 2 then 3, not from 1. PLAY
    # goes at 17020, so a step every 125 ms from it: the press, at 17340, comes
    # after step 3 at 17270, and REP-HELD holds the four from 17395 to 17770.
    (17000, "REP-PLAY", ["\\; start bang"], GAP),
    (17320, "REP-PRESS", [P("pad-45")], GAP),
    (17390, "REP-HELD", [], GAP),
    (17800, "REP-OFF", [P("pad-45", 0)], GAP),
    (18100, "REP-STOP", ["\\; stop bang"], GAP),
    # The drum screen's pads, over OSC as the phone sends them: track 2's
    # volume and pitch, which go to c_kit and are saved; then track 1 at full
    # randomness for nine steps, every step a coin, and back to 0.
    (18200, "SOUND", ["\\; seqgate-osc drums vol 2 -6", "\\; seqgate-osc drums pitch 2 7"],
     GAP),
    (18400, "RAND", ["\\; seqgate-osc drums randomness 1 100"], GAP),
    (18500, "RA-PLAY", ["\\; start bang"], GAP),
    (19600, "RA-STOP", ["\\; stop bang", "\\; seqgate-osc drums randomness 1 0"], GAP),
    # Drunkenness at its top, from the drum screen over OSC, then 96 windows a
    # sixteenth wide, each holding one step when sober. At the top every step
    # strays, by up to two steps, so most windows hold none or two or more.
    (19800, "DRUNK", ["\\; seqgate-osc drums drunk 100"], GAP),
    (19900, "DR-PLAY", ["\\; start bang"], GAP),
] + [(19980 + 125 * k, "DR-%d" % (k + 1), [], GAP) for k in range(96)] + [
    (31980, "DR-STOP", ["\\; stop bang"], GAP),
    # A drag on the drum screen, as the phone sends one: no sync, so c_steps' clock puts once,
    # about 100 ms after the first, ending where it was, at 100.
    (32050, "DRAG", ["\\; seqgate-osc drums drunk 50", "\\; seqgate-osc drums drunk 70",
                     "\\; seqgate-osc drums drunk 100"], GAP),
    (32350, "DONE", [], GAP),
]

# Every window but DRAG: each message, then state sync 15 ms after it (see the top).
SYNC_AFTER = 15
SEQ = [(ms, mark, bodies if mark == "DRAG" else
        [b for j, body in enumerate(bodies)
         for off, text in [body if isinstance(body, tuple) else (j * gap, body)]
         for b in ((off, text), (off + SYNC_AFTER, "\\; state sync"))], gap)
       for ms, mark, bodies, gap in SEQ]
QUIT_MS = 32700

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
         "not edit this file. It plays page 2's drum page on param: the time signature "
         "over OSC and a press on a row \\, a velocity \\, "
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
