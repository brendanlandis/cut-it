#!/usr/bin/env python3
"""The Organelle front panel's analyser -- ref/device/organelle.md. Capture on stdin.

m_organelle is the same layer as m_nano and keeps the same silence about meaning:
mother publishes aux and the four knobs on reserved names, this turns them into
named controls on param, and what any of them DOES is u_map's business.

⚠️ IT ASSERTS ON THE MAPPING LAYER, NOT ON THE HARDWARE. What the knobs and the
aux button physically send is mother's, measured and written down on the page;
this gate is about the four things m_organelle adds -- the og- prefix, the change
filter, press-only, and which of the two buses each control reaches.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS organelle-assert-drive-gen.py's SEQ OPENS.
MARKS = 12


def run_asserts(cap):
    order, by = A.windows(cap, "ORG", MARKS)
    W = lambda k: by.get(k, [])
    param = lambda k: [v for kind, v in W(k) if kind == "PARAM"]
    disp = lambda k: [v for kind, v in W(k) if kind == "DISP"]

    # ---- before the boot sequence has finished ----------------------------
    print("\n--- before the boot sequence has finished ---")
    # ⛔ AUX PUBLISHES NO CONTROL AT ALL. It is the keyboard's modifier, so it
    # must not occupy a name the map could bind and must not report itself raw
    # on disp the way an unmapped control would. What it must still do is say
    # mother spoke -- see the presence check below.
    A.check("⛔ the aux button publishes NO control name",
            param("EARLY") == [],
            "aux reached param as %s. A modifier is not a control: a name here "
            "could be bound in the map, and an unmapped one would draw a raw "
            "row on the OLED every time you reached for a shifted key"
            % param("EARLY"))

    # ---- the og- prefix ---------------------------------------------------
    # ⚠️ IT IS NOT DECORATION. m_nano already publishes knob-1 to knob-9, and a
    # single hyphen is not a distinction anyone can be trusted to read inside a
    # route box, so the two surfaces carry names that cannot be confused.
    print("\n--- the four knobs, and the og- prefix ---")
    for mark, want in (("KNOB1", ["og-knob-1", "0.25"]),
                       ("KNOB1-NEW", ["og-knob-1", "0.5"]),
                       ("KNOB4-ZERO", ["og-knob-4", "0"])):
        A.check("%s publishes %s" % (mark, " ".join(want)),
                param(mark) == [want], "got %s" % param(mark))
    A.check("KNOB23 publishes og-knob-2 and og-knob-3, in that order",
            param("KNOB23") == [["og-knob-2", "0.1"], ["og-knob-3", "0.2"]],
            "got %s" % param("KNOB23"))

    # ---- the change filter ------------------------------------------------
    # ✅ MOTHER PUSHES ONCE AT LOAD AND THEN SAYS NOTHING -- measured on the
    # device, one KNOB1 print in twelve seconds with nobody touching it, item
    # 237. Parameter pickup in u_map depends on that: if mother streamed, the
    # first value would be spent on its own reading and pickup would never arm.
    print("\n--- change -1 on every knob ---")
    A.check("the same value twice publishes ONCE",
            not param("KNOB1-SAME"),
            "a repeat got through as %s -- [change] is not filtering"
            % param("KNOB1-SAME"))

    # ⛔ AND THE -1 IS LOAD-BEARING, which is the whole reason this window uses
    # knob 4 at a bare 0. A plain [change] starts life holding 0, so a knob
    # physically parked at zero would never publish at all and whatever it feeds
    # would sit at its default forever. -1 cannot be a real value, because
    # mother's knobs are 0 to 1.
    A.check("⛔ a knob parked at ZERO still publishes -- the -1 in [change -1]",
            param("KNOB4-ZERO") == [["og-knob-4", "0"]],
            "got %s. A bare [change] swallows this and the failure is a control "
            "that silently does nothing (item 237)" % param("KNOB4-ZERO"))

    # ---- ⛔ WHICH BUSES EACH CONTROL REACHES (item 242) -------------------
    # A knob's RAW 0-to-1 position is not a readable parameter row: the screen
    # said og-knob-1 0.245 where a BPM belonged, and the param layer replaces the
    # footer, so the tempo it was mapped to vanished while you turned it. u_map
    # reports the value instead, because it is the only file that knows what a
    # control MEANS.
    #
    # ⚠️ THE CHECK IS "NO og-knob ROW", NOT "NO disp ROW", and the difference is
    # the whole point. The screen SHOULD light up when knob 1 moves -- knob 1 is
    # mapped to tempo -- so an empty-disp assertion would be asserting the bug
    # this fix removed. What must never appear is the raw control name.
    print("\n--- item 242: the knobs do not report, and og-aux does ---")
    A.check("a mapped knob does put something on the screen",
            bool(disp("KNOB1")),
            "nothing reached disp when knob 1 moved -- without this the next "
            "check has no liveness witness and passes on a dead run")
    raw = [d for d in disp("KNOB1") if d and d[0].startswith("og-knob-")]
    A.check("⛔ ...but never the knob's RAW position", not raw,
            "the screen got %s where the mapped value belongs (item 242)" % raw)
    # ⛔ AND THE MODIFIER SAYS SO ON THE SCREEN. A modifier with no feedback is
    # a mystery -- holding aux puts `shift` up as a modal, and letting go clears
    # it. A modal is priority 2 and diag is 3, so a shifted key that summons the
    # roster still draws over the word.
    A.check("⛔ holding aux says `shift` on the screen",
            ["modal", "shift"] in disp("AUX-PRESS"),
            "the screen got %s" % disp("AUX-PRESS"))
    A.check("⛔ ...and letting go clears it",
            ["modal-off"] in disp("AUX-RELEASE"),
            "the screen got %s. A missed release leaves the word up for the "
            "30 s safety TTL, which is what that TTL is for" % disp("AUX-RELEASE"))

    # ---- press only -------------------------------------------------------
    # aux is momentary 1 then 0, so [select 1] takes the press and its reject --
    # which carries the RELEASED 0, not a bang -- goes nowhere on purpose.
    print("\n--- the aux button publishes no control, on either edge ---")
    A.check("neither edge puts a control on param",
            not param("AUX-PRESS") and not param("AUX-RELEASE"),
            "press %s, release %s" % (param("AUX-PRESS"), param("AUX-RELEASE")))

    # ---- ⛔ THE KEYBOARD ---------------------------------------------------
    # mother packs it into ONE two-float list, pitch then velocity, and param
    # carries one value per control -- so the PITCH rides in the control NAME and
    # the velocity is the value. 25 keys, note 60 at the bottom.
    # ---- ⛔ THE SHIFT LAYER ------------------------------------------------
    print("\n--- the shift layer ---")
    A.check("⛔ a key held under aux publishes og-shift-NN, not og-key-NN",
            param("SHIFT-KEY") == [["og-shift-72", "100"], ["og-shift-72", "0"]],
            "got %s" % param("SHIFT-KEY"))
    A.check("...and the layer drops the moment aux is let go",
            param("AFTER-SHIFT") == [["og-key-72", "100"]],
            "got %s" % param("AFTER-SHIFT"))

    # ⛔ THE STRADDLE, AND IT IS THE ONE THAT STRANDS A NOTE. The press happened
    # under the modifier and the release did not. Reading the layer at release
    # time publishes og-key-65 for a note nothing ever started -- the shifted
    # control never sees its note-off, and in mode 1 that is a stuck note on the
    # Volca that nothing anywhere reports.
    A.check("⛔ a shifted press publishes og-shift-NN",
            param("STRADDLE-KEY") == [["og-shift-65", "100"]],
            "got %s" % param("STRADDLE-KEY"))
    A.check("⛔ ...and its release carries THE SAME NAME after aux is released",
            param("STRADDLE-OFF") == [["og-shift-65", "0"]],
            "got %s. The layer is latched per key AT PRESS TIME, in a "
            "25-element array -- a release read from the live modifier would "
            "say og-key-65 here and hang the note it never turned off"
            % param("STRADDLE-OFF"))

    print("\n--- the keyboard: one control per key ---")
    A.check("a key press publishes og-key-<note> carrying its velocity",
            param("KEY-ON") == [["og-key-60", "100"]],
            "wanted one og-key-60 100, got %s" % param("KEY-ON"))

    # ⛔ THE RELEASE IS THE HALF THAT MATTERS AND IT IS THE EASY ONE TO LOSE.
    # og-aux is press-only, and copying that here would give the Volca a note-on
    # with no note-off -- a held key that never stops, which is exactly the
    # droning `makenote` protects against everywhere else.
    A.check("⛔ a release publishes too, as velocity 0 -- NOT press-only",
            param("KEY-OFF") == [["og-key-60", "0"]],
            "wanted one og-key-60 0, got %s. A key that publishes its press and "
            "not its release leaves every note sounding forever"
            % param("KEY-OFF"))

    # ⚠️ THE TOP KEY, because note 60 alone is satisfied by a decode that ignores
    # the pitch and hardcodes the lowest key.
    A.check("the pitch really comes from the message -- the top key is og-key-84",
            param("KEY-TOP") == [["og-key-84", "40"]],
            "wanted one og-key-84 40, got %s" % param("KEY-TOP"))

    # ⛔ AND NOT ON disp. g_oled holds five parameter rows, so a two-handed chord
    # would evict everything else on the screen twice per note -- once on the
    # press and once on the release.
    # ⛔ AND IT ASKS ABOUT KEY ROWS, NOT ABOUT SILENCE ON disp. It used to demand
    # the whole window be empty, and disp is a SHARED bus -- u_err puts every
    # alert on it. With no phone in the room u_net warns `net-link-down`
    # eventually, and whether that lands inside the KEY-TOP window is a race:
    # measured red on one run in three, with the evidence line reading
    # `a key wrote to disp: [['alert', 'warn', 'u_net', 'net-link-down']]`.
    # ⚠️ A GATE THAT FAILS ON ANOTHER MODULE'S TRAFFIC IS A GATE NOBODY TRUSTS,
    # and the claim never needed it: a key reaching disp arrives as an og-key row
    # and nothing else here can produce one.
    stray = [r for k in ("KEY-ON", "KEY-OFF", "KEY-TOP") for r in disp(k)
             if r and str(r[0]).startswith("og-key")]
    A.check("⛔ the keys reach param and NOT disp", not stray,
            "a key wrote to disp: %s" % stray)

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
