#!/usr/bin/env python3
"""Generates the timed driver for the map gate, into the scratch path it is given.

It pushes onto `param` and `mode` exactly as the m_ layers would. It asserts
nothing about any DEVICE -- it uses volca-cc only because a lookup has to land
somewhere, and what that destination then does with the value is
volca-assert's business.

⛔ 300 ms IS THE POINT OF THIS DRIVER, not a detail of it. Every window in the
gate this was split out of started at 2400 ms, and the comment said why: u_map
read its table at 2000. A schedule derived from the implementation cannot
falsify it -- so the gate had 23 green checks and could not see the boot race
that the hardware found. mother pushes knobs.txt at BOOT, the table and the mode
key were both still unset, the restored tempo was silently dropped, and the
instrument came up at 120 instead of the saved 57. Item 234.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 20

SEQ = [
    # ⛔ BEFORE u_map reads its table. The map must work from load.
    # ⛔ AND IT IS ALSO KNOB 1's FIRST VALUE EVER, inside u_map's boot window, so
    # pickup must TAKE it and arm against it. If pickup ever swallows this the
    # instrument boots at u_tempo's fallback 120 -- item 234's exact symptom.
    (300, "EARLY", ["\\; param og-knob-1 0.0958"], GAP),
    # Knob 2's first value, also inside the boot window. Armed independently.
    (400, "EARLY-2", ["\\; param og-knob-2 0.5"], GAP),
    # Knob 4's first value is 0 -- its target lands ON the bottom rail. See
    # RAIL-UP below for what that costs without an equality release.
    (500, "RAIL-ARM", ["\\; param og-knob-4 0"], GAP),
    # ⛔ ARMED AT 0.0958 AND MOVED WITHOUT CROSSING -- nothing may reach tempo.
    # gk-cc rides along as the LIVENESS WITNESS: without it "no tempo here" is
    # answered by a dead driver rather than by a fact.
    (2400, "SUPPRESS", ["\\; param og-knob-1 0.5", "\\; param gk-cc 64"], GAP),
    (2600, "MAPPED", ["\\; param gk-cc 64"], GAP),
    # Further away is still not a crossing. Same witness.
    (2800, "AWAY", ["\\; param og-knob-1 0.9", "\\; param gk-cc 64"], GAP),
    # THROUGH it from above. 0.02 is 20 bpm.
    (3000, "CROSS", ["\\; param og-knob-1 0.02"], GAP),
    # ... and it tracks normally from then on. 0.3 is 157 bpm.
    (3200, "LIVE", ["\\; param og-knob-1 0.3"], GAP),
    # ⛔ og-aux IS A BUTTON AND NEVER PICKS UP. Two presses, two transport
    # events. A latched aux would be silent on the second.
    (3400, "AUX-1", ["\\; param og-aux 1"], GAP),
    (3600, "AUX-2", ["\\; param og-aux 1"], GAP),
    # ⛔ STATE IS PER KNOB. Knob 2 armed at 400 ms and knob 1 has long since gone
    # live, so knob 2 is still held: EXACTLY ONE cc 42, from its first value.
    # ⛔ AND AN UNMAPPED KNOB SAYS NOTHING. Knob 2 is held, and the held row is
    # built in the pickup machine rather than at the destination -- so without a
    # slot gate every armed knob announced itself as a bpm on the OLED. gk-cc is
    # the witness: the window has to be alive for "no bpm row here" to mean
    # anything. Item 240.
    (4000, "KNOB-2", ["\\; param og-knob-2 0.9", "\\; param gk-cc 64"], GAP),
    # ⛔ THE NO-SAVE CASE, and the mirror image of KNOB-2. Knob 3's FIRST value
    # arrives long after the boot window, so it was a hand rather than a restore
    # -- it must go straight to LIVE and its second value must pass too. TWO
    # cc 43 events. mother pushes knobs.txt only if a Save has ever happened, so
    # this is a fresh install or any deploy.sh --clean.
    (4200, "LATE-KNOB", ["\\; param og-knob-3 0.5", "\\; param og-knob-3 0.9"], GAP),
    # ⛔ BEFORE the mode switch. The bad row is keyed mode-1, so testing it after
    # switching to mode-4 makes it a LOOKUP MISS -- correctly silent, and nothing
    # to do with the guard it is meant to exercise.
    (4400, "BAD-DEST", ["\\; param gk-bad 100"], GAP),
    # ⛔ A TARGET ON A RAIL, AND IT IS A DEAD KNOB WITHOUT THE EQUALITY RELEASE.
    # Knob 4 arms at 0 inside the boot window. The release test is a side FLIP,
    # and a knob armed ABOVE a target of 0 waits for value < 0 -- unreachable
    # however far it is turned down. Reachable on knob 1, which is master tempo:
    # Save with it at the bottom and the tempo knob is dead for the session.
    # RAIL-BACK returns to the target EXACTLY and must hand over. Item 241.
    (4600, "RAIL-UP", ["\\; param og-knob-4 0.5", "\\; param gk-cc 64"], GAP),
    (4800, "RAIL-BACK", ["\\; param og-knob-4 0"], GAP),
    # ⚠️ AFTER 3.5 s ON PURPOSE. u_init restores saved state around then and
    # republishes mode; a switch before that is overwritten mid-run and the
    # mode-dependence check reads as broken when it is not. Item 232's other half.
    (5000, "MODE-4", ["\\; param xport-4 1"], GAP),
    (5200, "MODE-DEP", ["\\; param gk-cc 64"], GAP),
    # ⛔ HELD AND UNMAPPED AT THE SAME TIME, which is the case that shipped wrong.
    # Knob 2 armed at 400 ms and has never crossed, and its row is keyed mode-1 so
    # in mode-4 it maps to nothing. It must still say what it IS: a control that
    # does nothing and reports nothing cannot be told from a broken one. The
    # lookup runs for a held knob now -- only the emission is gated. Item 242.
    (5400, "UNMAPPED", ["\\; param og-knob-2 0.75"], GAP),
]
QUIT_MS = 6200

BLURB = ("map-assert-drive -- GENERATED by map-assert-drive-gen.py. Do not edit this "
         "file. It drives the mode table: the lookup at load \\, a mapped control "
         "reaching its destination \\, the same control in another mode doing nothing \\, "
         "and a row naming a destination that is not on u_map's route.")

NOTES = [
    "⚠️ RUN IT THROUGH test/gate/map-assert.sh \\, never by hand. The gate appends its "
    "own rows to the mapping table in a SCRATCH COPY and rewrites the MIDI objects to "
    "printing stubs. Loaded on its own against the real patch it would emit real MIDI "
    "to whatever is plugged in \\, and half the windows would find no mapping at all.",

    "⚠️ THE STATE DIRECTORY IS THE GATE'S OWN AND MUST BE EMPTY. main-dev.pd passes "
    "/tmp \\, which every run on the machine shares -- and u_init restores saved state at "
    "about 3.5 s. A previous test that changed mode leaves mode in that file \\, the "
    "restore republishes it mid-run \\, and every row keyed to another mode stops matching "
    "from that instant. It cost a wrong diagnosis once already: item 232.",
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: map-assert-drive-gen.py OUT.pd  "
                 "(run it through test/gate/map-assert.sh, which passes a scratch path)")
    w, b, c = D.build(sys.argv[1], SEQ, tag="MAP",
                      taps=["param", "err", "tempo", "start", "stop", "disp"], quit_ms=QUIT_MS,
                      blurb=BLURB, notes=NOTES)
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b, c))
