#!/usr/bin/env python3
"""Generates the timed driver for the map gate, into the scratch path it is given.

It pushes onto `param` and `mode` as the m_ layers would. volca-cc is only where
a lookup lands; what the destination does with the value is volca-assert's.

The first window is at 300 ms, before u_map reads its table, because mother
pushes knobs.txt at boot (item 234). Windows timed from when the code reads the
table could not see that race.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 20

SEQ = [
    # Before u_map reads its table. Also knob 1's first value, inside the boot
    # window, so pickup must take it and arm against it.
    (300, "EARLY", ["\\; param og-knob-1 0.0958"], GAP),
    # Knob 2's first value, also inside the boot window. Armed independently.
    (400, "EARLY-2", ["\\; param og-knob-2 0.5"], GAP),
    # Knob 4's first value is 0, a target on the bottom rail (RAIL-UP).
    (500, "RAIL-ARM", ["\\; param og-knob-4 0"], GAP),
    # Armed at 0.0958 and moved without crossing: nothing may reach tempo. gk-cc
    # is the liveness witness.
    (2400, "SUPPRESS", ["\\; param og-knob-1 0.5", "\\; param gk-cc 64"], GAP),
    (2600, "MAPPED", ["\\; param gk-cc 64"], GAP),
    # Further away is still not a crossing. Same witness.
    (2800, "AWAY", ["\\; param og-knob-1 0.9", "\\; param gk-cc 64"], GAP),
    # Through it from above. 0.02 is 20 bpm.
    (3000, "CROSS", ["\\; param og-knob-1 0.02"], GAP),
    # ... and it tracks normally from then on. 0.3 is 157 bpm.
    (3200, "LIVE", ["\\; param og-knob-1 0.3"], GAP),
    # The nano's PLAY and STOP (xport-2 and xport-5) are buttons and never pick
    # up: given a slot, the repeat would latch.
    (3400, "PLAY-1", ["\\; param xport-2 1"], GAP),
    (3600, "STOP-1", ["\\; param xport-5 1"], GAP),
    # start is not a toggle: PLAY twice starts twice.
    (3800, "PLAY-2", ["\\; param xport-2 1"], GAP),
    # State is per knob: knob 1 is live and knob 2 still held, so exactly one
    # cc 42, its first value. Held, it draws its own destination's row and never
    # a bpm (item 240); gk-cc is the witness.
    (4000, "KNOB-2", ["\\; param og-knob-2 0.9", "\\; param gk-cc 64"], GAP),
    # Knob 3's first value comes after the boot window: a hand, not a restore,
    # so it goes straight to live and both values pass. mother pushes knobs.txt
    # only after a Save, so this is a fresh install or tools/deploy.sh --clean.
    (4200, "LATE-KNOB", ["\\; param og-knob-3 0.5", "\\; param og-knob-3 0.9"], GAP),
    # Before the mode switch: the bad row is keyed mode-1, and in mode-4 it would
    # be a lookup miss, silent for the wrong reason.
    (4400, "BAD-DEST", ["\\; param gk-bad 100"], GAP),
    # A target on a rail (item 241): the release test is a side flip, so a knob
    # armed at 0 would wait for value < 0 forever without the equality release.
    # RAIL-BACK returns to the target exactly and must hand over.
    (4600, "RAIL-UP", ["\\; param og-knob-4 0.5", "\\; param gk-cc 64"], GAP),
    (4800, "RAIL-BACK", ["\\; param og-knob-4 0"], GAP),
    # After 3.5 s: u_init's restore republishes mode then and would overwrite an
    # earlier switch (item 232). 127, then 0 on release, is what a Launchpad CC
    # button sends.
    (5000, "MODE-4", ["\\; param lp-cc-50 127"], GAP),
    # The release must select nothing. A second selection is idempotent, so the
    # screen looks right while every mode message and state write doubles.
    (5100, "MODE-4-RELEASE", ["\\; param lp-cc-50 0"], GAP),
    (5200, "MODE-DEP", ["\\; param gk-cc 64"], GAP),
    # The top row's first button selected mode 1 until the modes moved to the
    # left column: it is free now, so it selects nothing and names itself.
    (5300, "TOP-ROW-FREE", ["\\; param lp-cc-91 127"], GAP),
    # Held and unmapped at once: knob 2 has never crossed, and its row is keyed
    # mode-1, so in mode-4 it maps to nothing and must still report (item 242).
    (5400, "UNMAPPED", ["\\; param og-knob-2 0.75"], GAP),
    # A mode the key-setter cannot use, as u_state replays a truncated
    # cut-it-auto.txt: one atom empties the lookup key, and every knob would
    # draw its raw row (item 294, fixed by 297). The static lint cannot see a
    # mode that arrives at runtime.
    (5600, "BAD-MODE", ["\\; mode compose"], GAP),
    # The key must survive: og-knob-1 is tempo in all six modes and long since
    # live, so 0.6 must still reach tempo as 304 bpm.
    (5800, "AFTER-BAD", ["\\; param og-knob-1 0.6"], GAP),
    # The shipped rows on the Organelle's shifted keys (og-shift-60..84, aux
    # held), the one panel that can never be the missing device.
    (6200, "DIAG-DEST", ["\\; param og-shift-60 100"], GAP),
    # A shifted key publishes both edges; the release must not summon it again.
    (6400, "DIAG-RELEASE", ["\\; param og-shift-60 0"], GAP),
    # With the nano unplugged, this is the only stop left.
    (6600, "SHIFT-STOP", ["\\; param og-shift-72 100"], GAP),
    # Back to mode-1, since every gate row is keyed mode-1. Press and release,
    # as the pad sends.
    (6800, "MODE-1", ["\\; param lp-cc-80 127", "\\; param lp-cc-80 0"], GAP),
    # Every value destination draws its mapped row. The shipped map reaches only
    # tempo and volca-cc, so note, pad and program go through gate rows
    # (scratch-gates.py). 64 in is 64 out for a 0-127 control.
    (7000, "ROW-CC", ["\\; param gk-cc 64"], GAP),
    (7200, "ROW-NOTE", ["\\; param gk-note 100"], GAP),
    (7400, "ROW-PAD", ["\\; param gk-pad 90"], GAP),
    (7600, "ROW-PROG", ["\\; param gk-prog 1"], GAP),
    # volca-key draws nothing (item 293).
    (7800, "ROW-KEY", ["\\; param og-key-60 100"], GAP),
    # Unmapped pressure draws no raw row (item 318); pad-15 is the witness and
    # proves the test is not too wide. It sits in the drum page's dark corner,
    # since mode 1 maps the page's 48 pads.
    (8000, "PRESSURE", ["\\; param pad-11-at 64", "\\; param pad-15 100"], GAP),
    # Mapped pressure still draws its row: a gate row maps pad-13-at to
    # volca-cc 45.
    (8200, "PRESSURE-MAPPED", ["\\; param pad-13-at 64"], GAP),
]
QUIT_MS = 8800

BLURB = ("map-assert-drive -- GENERATED by map-assert-drive-gen.py. Do not edit this "
         "file. It drives the mode table: the lookup at load \\, a mapped control "
         "reaching its destination \\, the same control in another mode doing nothing \\, "
         "and a row naming a destination that is not on u_map's route.")

NOTES = [
    "Run it through test/gate/map-assert.sh: the gate adds its own map rows in a "
    "scratch copy. Against the real patch it emits real MIDI and half the windows "
    "find no mapping.",
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: map-assert-drive-gen.py OUT.pd  "
                 "(run it through test/gate/map-assert.sh, which passes a scratch path)")
    w, b, c = D.build(sys.argv[1], SEQ, tag="MAP",
                      taps=["param", "err", "tempo", "start", "stop", "disp", "mode"],
                      quit_ms=QUIT_MS,
                      blurb=BLURB, notes=NOTES)
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b, c))
