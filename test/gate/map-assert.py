#!/usr/bin/env python3
"""The map's analyser -- ref/module/map.md. Two halves, and the FIRST NEEDS NO Pd.

  1. THE STATIC LINT reads Cut It/cut-it-map.txt and the literal route box in
     Cut It/u_map.pd and checks that every destination a row can name exists as
     an argument on that route. THAT IS THE ALLOWLIST GUARD, ENFORCED BY READING
     -- the same way the project audits its global sends. It is the cheapest and
     strongest check here, ~200 ms, and it is the one that stays true as the
     table grows. The gate skill says to reach for this before reaching for a
     driver; this is the example it is drawn from.

  2. THE RUN ASSERTIONS read a capture from map-assert.sh. They test the LOOKUP
     -- that a control maps at all, that it maps to a different thing in a
     different mode, and that a row naming a destination off the route emits
     nothing and says so. What each destination then DOES with the value belongs
     to that device's gate, not here.

Reads the capture on stdin. Exits non-zero on any failure.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

MAP = "Cut It/cut-it-map.txt"
UMAP = "Cut It/u_map.pd"
MODES = ["mode-%d" % n for n in range(1, 7)]


# --------------------------------------------------------------- static lint
def route_destinations():
    """The literal allowlist: the arguments of u_map's destination route box."""
    for line in open(UMAP):
        m = re.match(r"^#X obj \d+ \d+ route (tempo .*);$", line.strip())
        if m:
            return m.group(1).split()
    return None


def static_lint():
    print("\n=== A. the map, checked by READING -- no Pd involved ===")
    dests = route_destinations()
    A.check("u_map still has a literal destination route box", dests is not None,
            "expected a box starting 'route tempo ...' in " + UMAP)
    if dests is None:
        return
    A.note("allowlist is %d destinations: %s" % (len(dests), " ".join(dests)))

    rows, bad_width, bad_dest, bad_mode = [], [], [], []
    for n, raw in enumerate(open(MAP), 1):
        line = raw.strip()
        if not line:
            continue
        f = line.split()
        rows.append((n, f))
        if len(f) != 4:
            bad_width.append((n, line))
            continue
        if f[2] not in dests:
            bad_dest.append((n, f[2]))
        if f[0] not in MODES:
            bad_mode.append((n, f[0]))

    A.check("every row is exactly 4 atoms", not bad_width,
            "; ".join("line %d: %r" % b for b in bad_width))
    A.check("⛔ every destination exists on u_map's route (THE GUARD)", not bad_dest,
            "; ".join("line %d names %r" % b for b in bad_dest))
    A.check("every mode is one of the six", not bad_mode,
            "; ".join("line %d: %r" % b for b in bad_mode))

    seen, dupes = {}, []
    for n, f in rows:
        if len(f) < 2:
            continue
        key = (f[0], f[1])
        if key in seen:
            dupes.append((n, key, seen[key]))
        else:
            seen[key] = n
    A.check("no duplicate (mode, control) pair", not dupes,
            "; ".join("line %d repeats %s from line %d" % (n, " ".join(k), o)
                      for n, k, o in dupes))
    if dupes:
        A.note("text search returns only the FIRST match, so a repeat is DEAD and silent -- item 229")
    # ⛔ NOTHING ON THE RIG MAY BE BOUND TO panic. It is a destination on u_map's
    # route -- the bench reaches it and u_err's own tests need it -- but a
    # CONTROL wired to it means a finger on a fader can silence the instrument
    # mid-set with no way back but a reload. ⚠️ THE MAP IS THE ONLY THING THAT
    # COULD BIND ONE, which is what makes this readable rather than something a
    # person has to go looking for: the midi bench asked "nothing on the rig can
    # raise panic and nothing is meant to" with no action and nothing to see,
    # and a claim about a text file is not a thing eyes can answer. What the
    # bench keeps is the half fingers can -- that no control anybody would reach
    # for turns the aux LED red.
    panic_rows = [(n, " ".join(f)) for n, f in rows if len(f) > 2 and f[2] == "panic"]
    A.check("⛔ no map row binds a control to panic", not panic_rows,
            "; ".join("line %d: %r" % b for b in panic_rows))
    A.note("%d rows, %d distinct controls" % (len(rows), len({f[1] for _, f in rows if len(f) > 1})))


# --------------------------------------------------------------- run assertions
def run_asserts(cap):
    print("\n=== B. the lookup, driven ===")
    order, by = A.windows(cap, "MAP", len(["EARLY", "EARLY-2", "RAIL-ARM",
                                           "SUPPRESS", "MAPPED", "AWAY", "CROSS",
                                           "LIVE", "AUX-1", "AUX-2", "KNOB-2",
                                           "LATE-KNOB", "BAD-DEST", "RAIL-UP",
                                           "RAIL-BACK", "MODE-4", "MODE-DEP",
                                           "UNMAPPED"]))
    W = lambda k: by.get(k, [])
    # ⛔ MIDIOUT IS DELIBERATELY NOT EVIDENCE HERE, and the reason is worth the
    # three lines. g_grid repaints the Launchpad off a [metro 100] that runs with
    # or without DSP and with or without anything being mapped, so there is
    # ALWAYS raw [midiout] traffic in every window. An assertion of the form
    # "this window emitted no MIDI" that counted it could never be true.
    # ⚠️ It only became visible when every gate started rewriting all five
    # classes: the gate this was split out of rewrote four, so the grid's frames
    # were invisible to it and the distinction never had to be made.
    # A mapped destination reaches a device through noteout, ctlout or pgmout.
    midi = lambda k: [e for e in W(k) if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT")]

    # ⛔ THE REGRESSION TEST FOR ITEM 234. mother pushes knobs.txt at BOOT, long
    # before any window in the old gate started, and the map has to be usable by
    # then -- both the table AND the lookup key's mode. It was not: the instrument
    # booted at u_tempo's own 120 instead of the saved 57, and NOTHING reported it.
    early = [e for e in W("EARLY") if e[0] == "TEMPO"]
    A.check("⛔ a control moved at 300 ms ALREADY MAPS -- table and mode key ready at load",
            any(abs(float(e[1][0]) - 57) < 1.5 for e in early if e[1]),
            "tempo in that window: %s" % [e[1] for e in early])
    A.check("a mapped control reaches its destination",
            any(e[0] == "CTLOUT" and e[1][1] == 41 for e in W("MAPPED")),
            repr(W("MAPPED")))
    A.check("⛔ the SAME control in another mode does NOTHING (mode-dependence)",
            not midi("MODE-DEP"), repr(midi("MODE-DEP")))
    # ⛔ AND THAT NEGATIVE NOW HAS A WITNESS IN ITS OWN WINDOW. An unmapped control
    # is silent on every BUS and says so on the SCREEN, so "no MIDI here" can no
    # longer be answered by a window that never happened.
    A.check("... and it reports its RAW value on disp -- the witness for the line above",
            any(d[:2] == ["gk-cc", "64"]
                for d in [e[1] for e in W("MODE-DEP") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("MODE-DEP") if e[0] == "DISP"])
    A.check("⛔ a row naming an unknown destination emits NO MIDI",
            not midi("BAD-DEST"), repr(midi("BAD-DEST")))
    A.check("⛔ ... and reports unknown-dest on err",
            any(e[0] == "ERR" and "unknown-dest" in " ".join(e[1]) for e in W("BAD-DEST")),
            repr(W("BAD-DEST")))

    # ------------------------------------------------------- parameter pickup
    # mother replays knobs.txt at boot, so the patch believes a knob is somewhere
    # the knob physically is not, and the first touch JUMPS -- measured at 443 BPM
    # on knob 1, which is master tempo. Pickup holds the control until its value
    # passes THROUGH the stored one. See ref/module/map.md.
    #
    # ⛔ EVERY NEGATIVE HERE CARRIES A LIVENESS WITNESS IN ITS OWN WINDOW. "This
    # window emitted no tempo" is also true of a window that never happened, and
    # A.windows only proves the MARK landed -- not that the actions after it did.
    print("\n=== C. parameter pickup ===")
    tempos = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    cc = lambda k, n: [e[1] for e in W(k) if e[0] == "CTLOUT" and e[1][1] == n]

    A.check("⛔ a knob that has NOT crossed its stored value moves nothing",
            not tempos("SUPPRESS"), "tempo in that window: %s" % tempos("SUPPRESS"))
    A.check("... and that window was LIVE -- another control reached its destination",
            len(cc("SUPPRESS", 41)) == 1, repr(W("SUPPRESS")))

    A.check("⛔ moving FURTHER AWAY does not hand over either",
            not tempos("AWAY"), "tempo in that window: %s" % tempos("AWAY"))
    A.check("... and that window was live too",
            len(cc("AWAY", 41)) == 1, repr(W("AWAY")))

    A.check("⛔ CROSSING the stored value hands over -- 0.02 is 20 bpm",
            any(abs(t - 20) < 1.5 for t in tempos("CROSS")),
            "tempo in that window: %s" % tempos("CROSS"))
    A.check("and it tracks normally from then on -- 0.3 is 157 bpm",
            any(abs(t - 157) < 1.5 for t in tempos("LIVE")),
            "tempo in that window: %s" % tempos("LIVE"))

    # og-aux is a BUTTON. If it were ever given a pickup slot the second press
    # would latch and vanish, and the transport would stick on.
    A.check("⛔ og-aux is a BUTTON and never picks up -- first press starts",
            any(e[0] == "START" for e in W("AUX-1")), repr(W("AUX-1")))
    A.check("⛔ ... and the SECOND press stops. A latched aux would be silent here",
            any(e[0] == "STOP" for e in W("AUX-2")), repr(W("AUX-2")))

    # ⛔ EXACT COUNTS, never "at least". Knob 2 armed at 400 ms inside the boot
    # window and has not crossed, so its second value is held. Knob 3's FIRST
    # value arrived at 4200 ms -- long after the window -- so it was a hand and
    # not a restore, and it must never arm at all.
    A.check("⛔ pickup state is PER KNOB -- knob 2 is still held while knob 1 is live",
            len(cc("KNOB-2", 42)) == 0, "cc 42 in that window: %s" % cc("KNOB-2", 42))
    A.check("... and knob 2's window was live -- its first value DID land at 400 ms",
            len(cc("EARLY-2", 42)) == 1, repr(W("EARLY-2")))
    # ⛔ THE SCREEN MUST SHOW THE MAPPED VALUE, NOT THE RAW POSITION. m_organelle
    # stopped reporting knobs to disp because a 0-to-1 number where a BPM belongs
    # is not feedback -- and the param layer REPLACES the footer, so the tempo
    # vanished while the knob was being turned. Item 238.
    disp = lambda k: [e[1] for e in W(k) if e[0] == "DISP"]
    A.check("⛔ while HELD the row carries BOTH numbers -- bpm <latched> (<knob>)",
            any(d[:2] == ["bpm", "57"] and d[2:] == ["(255)"] for d in disp("SUPPRESS")),
            "disp in that window: %s" % disp("SUPPRESS"))
    A.check("... and it follows the knob while still held -- 0.9 is 451",
            any(d[:2] == ["bpm", "57"] and d[2:] == ["(451)"] for d in disp("AWAY")),
            "disp in that window: %s" % disp("AWAY"))
    A.check("⛔ once LIVE the row is the mapped value alone -- no raw og-knob-1",
            any(d == ["bpm", "157"] for d in disp("LIVE"))
            and not any(d and d[0].startswith("og-knob") for d in disp("LIVE")),
            "disp in that window: %s" % disp("LIVE"))

    A.check("⛔ a knob first seen AFTER the boot window never arms -- both values pass",
            len(cc("LATE-KNOB", 43)) == 2,
            "cc 43 in that window: %s -- expected two, the no-Save case"
            % cc("LATE-KNOB", 43))

    # ⛔ THE HELD ROW IS BUILT IN THE PICKUP MACHINE, NOT AT THE DESTINATION,
    # because a held value never reaches the lookup -- so it cannot know what the
    # knob maps to and it is hardcoded to bpm. Every armed knob therefore
    # announced itself as a tempo on the OLED, including the three that are
    # mapped to nothing at all. Item 240.
    A.check("⛔ an UNMAPPED knob is held SILENTLY -- no bpm row for knob 2",
            not any(d[:1] == ["bpm"] for d in disp("KNOB-2")),
            "disp in that window: %s" % disp("KNOB-2"))
    A.check("... and that window was live -- another control reached its destination",
            len(cc("KNOB-2", 41)) == 1, repr(W("KNOB-2")))

    # ⛔ A TARGET ON A RAIL. Knob 4 armed at 0, so "crossed" -- a flip of
    # target <= value -- would need value < 0 and can never happen. EXACT counts:
    # the hold and the release are one event each, and a gate that accepted "at
    # least one" would pass whether or not the release ever came.
    A.check("⛔ a knob armed against a target of 0 is still HELD on the way up",
            len(cc("RAIL-UP", 44)) == 0, "cc 44 in that window: %s" % cc("RAIL-UP", 44))
    A.check("... and that window was live too",
            len(cc("RAIL-UP", 41)) == 1, repr(W("RAIL-UP")))
    # ⛔ HELD AND UNMAPPED AT ONCE. Knob 2 is still armed from 400 ms and its row is
    # mode-1, so in mode-4 it maps to nothing -- and it must still report. The gate
    # used to sit ABOVE the lookup, so a held knob never reached text search and an
    # unassigned knob could not be told from a broken one. Item 242.
    A.check("⛔ a HELD and UNMAPPED knob still reports its raw value",
            any(d[:2] == ["og-knob-2", "0.75"]
                for d in [e[1] for e in W("UNMAPPED") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("UNMAPPED") if e[0] == "DISP"])
    A.check("... and it is still silent on every bus -- the row above is the witness",
            not midi("UNMAPPED"), repr(midi("UNMAPPED")))

    A.check("⛔ ... and RETURNING TO the target releases it -- a rail has no beyond",
            len(cc("RAIL-BACK", 44)) == 1,
            "cc 44 in that window: %s -- a dead knob for the whole session"
            % cc("RAIL-BACK", 44))


# --------------------------------------------------------------- the no-Save run
def nosave_asserts(cap):
    """The SAME drive against a patch folder with NO knobs.txt.

    ⛔ THIS IS THE MIRROR IMAGE, AND THAT IS THE WHOLE POINT. mother pushes a
    knob value at boot either way -- the SAVED position when knobs.txt exists,
    the LIVE PHYSICAL position when it does not. Only the first is a desync, so
    only the first may arm. Every assertion below is a window the run above
    asserts the OPPOSITE of; if both expect the same thing, u_map is not reading
    the file and nothing here is testing anything. Item 239.
    """
    print("\n=== D. no knobs.txt -- nothing may be held ===")
    order, by = A.windows(cap, "MAP", len(["EARLY", "EARLY-2", "RAIL-ARM",
                                           "SUPPRESS", "MAPPED", "AWAY", "CROSS",
                                           "LIVE", "AUX-1", "AUX-2", "KNOB-2",
                                           "LATE-KNOB", "BAD-DEST", "RAIL-UP",
                                           "RAIL-BACK", "MODE-4", "MODE-DEP",
                                           "UNMAPPED"]))
    W = lambda k: by.get(k, [])
    tempos = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    cc = lambda k, n: [e[1] for e in W(k) if e[0] == "CTLOUT" and e[1][1] == n]

    # The value is still TAKEN. Both branches pass it through -- neither can
    # produce silence, which is what made item 234 expensive to find.
    A.check("⛔ the boot push is still TAKEN with no knobs.txt -- 0.0958 is 57 bpm",
            any(abs(t - 57) < 1.5 for t in tempos("EARLY")),
            "tempo in that window: %s" % tempos("EARLY"))
    A.check("⛔ ... and NOTHING is held -- knob 1 moves the tempo at 2400 ms, 0.5 is 255",
            any(abs(t - 255) < 1.5 for t in tempos("SUPPRESS")),
            "tempo in that window: %s -- armed against its own live position?"
            % tempos("SUPPRESS"))
    A.check("... and that window was live -- another control reached its destination",
            len(cc("SUPPRESS", 41)) == 1, repr(W("SUPPRESS")))
    A.check("⛔ knob 2 is live too -- exactly one cc 42, where the armed run has none",
            len(cc("KNOB-2", 42)) == 1, "cc 42 in that window: %s" % cc("KNOB-2", 42))


if __name__ == "__main__":
    static_lint()
    run_asserts(A.require_capture(sys.stdin.read()))
    if "--nosave" in sys.argv:
        nosave_asserts(A.require_capture(
            open(sys.argv[sys.argv.index("--nosave") + 1]).read()))
    sys.exit(1 if A.report() else 0)
