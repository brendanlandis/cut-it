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
    A.note("%d rows, %d distinct controls" % (len(rows), len({f[1] for _, f in rows if len(f) > 1})))


# --------------------------------------------------------------- run assertions
def run_asserts(cap):
    print("\n=== B. the lookup, driven ===")
    order, by = A.windows(cap, "MAP", len(["EARLY", "EARLY-2", "SUPPRESS", "MAPPED",
                                           "AWAY", "CROSS", "LIVE", "AUX-1", "AUX-2",
                                           "KNOB-2", "LATE-KNOB",
                                           "BAD-DEST", "MODE-4", "MODE-DEP"]))
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
    A.check("⛔ a knob first seen AFTER the boot window never arms -- both values pass",
            len(cc("LATE-KNOB", 43)) == 2,
            "cc 43 in that window: %s -- expected two, the no-Save case"
            % cc("LATE-KNOB", 43))


if __name__ == "__main__":
    static_lint()
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
