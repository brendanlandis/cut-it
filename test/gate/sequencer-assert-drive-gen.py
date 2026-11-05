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
screen's pads (a track's volume, pitch and randomness, over OSC too), a repeat
pad held over four tracks at full randomness, track 1 muted and then soloed as
well, over OSC, track 4's distortion made fold, over OSC too, drunkenness, and
the reverb made gigaverb, over OSC. Last a repeat pad as c_kit hears of it, the
500 BPM repeat and the saved tempo, each with knob 1 turned after it, and a
track's random pitch, over OSC.

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
    # A repeat over random tracks plays exactly what was played, the coins as they fell that
    # time (Brendan, 2026-11-05): tracks 1 to 4 at full randomness, every step of theirs a
    # coin, and repeat pad 2 held after step 3 for three steps, which replay steps 2, 3 and 2;
    # let go, the loop of 3 goes on from where it would have been, 1 then 2, not 3 then 2. Four
    # tracks, so a repeat that rolled its coins again would match all eight of their replayed
    # steps about once in 600,000 runs. PLAY goes at 19920 and a step every 125 ms from it: the
    # press, at 20220, comes after step 3 at 20170; RR-HELD holds 20295, 20420 and 20545; the
    # release, at 20600, comes before 20670; and STOP, at 20850, before 20920.
    (19700, "RR", ["\\; seqgate-osc drums randomness %d 100" % t for t in range(1, 5)], GAP),
    (19900, "RR-PLAY", ["\\; start bang"], GAP),
    (20200, "RR-PRESS", [P("pad-46")], GAP),                      # repeat pad 2
    (20250, "RR-HELD", [], GAP),
    (20580, "RR-OFF", [P("pad-46", 0)], GAP),
    (20830, "RR-STOP", ["\\; stop bang"]
     + ["\\; seqgate-osc drums randomness %d 0" % t for t in range(1, 5)], GAP),
    # The drum screen's mute and solo, over OSC as the phone sends them (Brendan, 2026-11-05):
    # track 1 muted for six steps, sober, of the global loop of 3, while track 2 plays its step
    # 1; then track 1 soloed as well, mutes ignored, for six more, while track 2 plays nothing.
    # Both stay, so the song's draft, written every 2 s, holds them at the end.
    (21000, "MUTE", ["\\; seqgate-osc drums mute 1 1"], GAP),
    (21150, "MU-PLAY", ["\\; start bang"], GAP),
    (21850, "MU-STOP", ["\\; stop bang"], GAP),
    (21950, "SOLO", ["\\; seqgate-osc drums solo 1 1"], GAP),
    (22100, "SO-PLAY", ["\\; start bang"], GAP),
    (22800, "SO-STOP", ["\\; stop bang"], GAP),
    # Track 4's distortion made fold, over OSC as the phone sends it (Brendan, 2026-11-05): put
    # with the pattern, its character after the mutes and solos, and told to c_kit.
    (22850, "CHAR", ["\\; seqgate-osc drums char 4 3"], GAP),
    # Drunkenness at its top, from the drum screen over OSC, then 96 windows a
    # sixteenth wide, each holding one step when sober. At the top every step
    # strays, by up to two steps, so most windows hold none or two or more.
    (22900, "DRUNK", ["\\; seqgate-osc drums drunk 100"], GAP),
    # The reverb's type, over OSC as the phone sends it: gigaverb, 1, where the seed has the plate.
    (22950, "VTYPE", ["\\; seqgate-osc drums verb-type 1"], GAP),
    (23000, "DR-PLAY", ["\\; start bang"], GAP),
] + [(23080 + 125 * k, "DR-%d" % (k + 1), [], GAP) for k in range(96)] + [
    (35080, "DR-STOP", ["\\; stop bang"], GAP),
    # A drag on the drum screen, as the phone sends one: no sync, so c_steps' clock puts once,
    # about 100 ms after the first, ending where it was, at 100.
    (35150, "DRAG", ["\\; seqgate-osc drums drunk 50", "\\; seqgate-osc drums drunk 70",
                     "\\; seqgate-osc drums drunk 100"], GAP),
    # A held repeat's tails, as c_kit is told them, sober: repeat pad 1 after step 3 at 100 BPM, a
    # tempo of its own, so one step's 150 ms is the tempo bus's and no default.
    # PLAY at 35620 and a step every 150 ms: the press, at 35940, comes after step 3 at 35920, and
    # the replay begins at 36070.
    (35500, "TF-SOBER", ["\\; seqgate-osc drums drunk 0", "\\; tempo 100"], GAP),
    (35600, "TF-PLAY", ["\\; start bang"], GAP),
    (35920, "TF-PRESS", [P("pad-45")], GAP),
    (36050, "TF-HELD", [], GAP),
    (36300, "TF-OFF", [P("pad-45", 0)], GAP),
    (36500, "TF-STOP", ["\\; stop bang", "\\; tempo 120"], GAP),
    # The 500 BPM repeat, pad-35: PLAY at 36620, the press at 36900 after step 3 at 36870. Knob 1
    # is held at 500 through it, and at 120 after it, and the loop of 3 goes on from step 3.
    (36600, "FAST-PLAY", ["\\; start bang"], GAP),
    (36880, "FAST-PRESS", [P("pad-35")], GAP),
    (36960, "FAST-HELD", [], GAP),
    (37100, "FAST-KNOB", ["\\; param og-knob-1 0.5"], GAP),
    (37300, "FAST-OFF", [P("pad-35", 0)], GAP),
    (37360, "FAST-KNOB2", ["\\; param og-knob-1 0.55"], GAP),
    (37700, "FAST-STOP", ["\\; stop bang"], GAP),
    # The saved tempo, pad-38: saved at 120, moved to 200, and back at the press.
    (37800, "RC-SAVE", [P("lp-cc-108", 127), P("lp-cc-108", 0)], GAP),
    (37900, "RC-MOVE", ["\\; tempo 200"], GAP),
    (38000, "RC-PRESS", [P("pad-38")], GAP),
    (38200, "RC-OFF", [P("pad-38", 0)], GAP),
    (38300, "RC-KNOB", ["\\; param og-knob-1 0.6"], GAP),
    # A track's random pitch, over OSC as the phone sends it: track 1, soloed since SOLO, at full
    # randomness for sixteen steps, a coin on each, so no hit in them is about one run in 65,000;
    # then with no randomness, every hit back at its set pitch. It stays on, for the draft.
    (38500, "ROLL", ["\\; seqgate-osc drums rnd-pitch 1 1",
                     "\\; seqgate-osc drums randomness 1 100"], GAP),
    (38650, "RO-PLAY", ["\\; start bang"], GAP),
    (40700, "RO-STOP", ["\\; stop bang", "\\; seqgate-osc drums randomness 1 0"], GAP),
    (40900, "RO-BACK", ["\\; start bang"], GAP),
    (41300, "RO-END", ["\\; stop bang"], GAP),
    # The saved-tempo pad restarts at once: steps at 41420 and each 125 ms, so its press, at 41750,
    # falls between 41670 and 41795, and a note before RX-SOON can only be the restart's step 1.
    (41400, "RX-PLAY", ["\\; start bang"], GAP),
    (41730, "RX-PRESS", [P("pad-38")], GAP),
    (41755, "RX-SOON", [], GAP),
    (41900, "RX-OFF", [P("pad-38", 0), "\\; stop bang"], GAP),
    # u_song's draft goes out every 2 s, so past the last change's turn.
    (43700, "DONE", [], GAP),
]

# Every window but DRAG: each message, then state sync 15 ms after it (see the top).
SYNC_AFTER = 15
SEQ = [(ms, mark, bodies if mark == "DRAG" else
        [b for j, body in enumerate(bodies)
         for off, text in [body if isinstance(body, tuple) else (j * gap, body)]
         for b in ((off, text), (off + SYNC_AFTER, "\\; state sync"))], gap)
       for ms, mark, bodies, gap in SEQ]
QUIT_MS = 43900

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
    # Not a real netsend: gates run under -batch, which polls no socket (lib_scratch.net_direct).
    "#X obj 3800 1300 route send;",
    "#X obj 4100 1000 loadbang;",
    "#X obj 4100 1050 del 2600;",
    "#X msg 4100 1100 connect 127.0.0.1 %d;" % INPORT,
    "#X obj 3800 1350 s gate-net;",
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
                      taps=["state", "disp", "err", "mode", "tempo"], quit_ms=QUIT_MS,
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
              "#X connect %d 0 %d 0;" % (b + 8, b + 5),
              "#X connect %d 0 %d 0;" % (b + 5, b + 9)]
    with open(sys.argv[1], "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b + len(OSC), c + 9))
