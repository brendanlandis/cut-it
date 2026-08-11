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
    A.check("⛔ the aux button pressed at 300 ms already publishes",
            param("EARLY") == [["og-aux", "1"]],
            "wanted one og-aux 1, got %s" % param("EARLY"))

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
    A.check("⛔ og-aux DOES keep its own report -- the transport is not a value",
            [d for d in disp("AUX-PRESS") if d == ["og-aux", "1"]] == [["og-aux", "1"]],
            "og-aux reached param as %s but the screen got %s"
            % (param("AUX-PRESS"), disp("AUX-PRESS")))

    # ---- press only -------------------------------------------------------
    # aux is momentary 1 then 0, so [select 1] takes the press and its reject --
    # which carries the RELEASED 0, not a bang -- goes nowhere on purpose.
    print("\n--- the aux button, on press only ---")
    A.check("a press publishes og-aux 1",
            param("AUX-PRESS") == [["og-aux", "1"]],
            "got %s" % param("AUX-PRESS"))
    A.check("⛔ the release publishes NOTHING",
            not param("AUX-RELEASE") and not disp("AUX-RELEASE"),
            "the released 0 leaked: param %s, disp %s"
            % (param("AUX-RELEASE"), disp("AUX-RELEASE")))

    # ---- ⛔ THE KEYBOARD ---------------------------------------------------
    # mother packs it into ONE two-float list, pitch then velocity, and param
    # carries one value per control -- so the PITCH rides in the control NAME and
    # the velocity is the value. 25 keys, note 60 at the bottom.
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
