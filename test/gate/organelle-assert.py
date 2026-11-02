#!/usr/bin/env python3
"""The Organelle front panel's analyser -- ref/device/organelle.md. Capture on stdin.

m_organelle turns mother's knobs and keys into named controls on param, and aux
into the keyboard's modifier; what a control does is u_map's. This asserts on
what m_organelle adds: the og- prefix, the change filter, the shift layer, and
which bus each control reaches.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The number of windows organelle-assert-drive-gen.py's SEQ opens.
MARKS = 20


def run_asserts(cap):
    order, by = A.windows(cap, "ORG", MARKS)
    W = lambda k: by.get(k, [])
    param = lambda k: [v for kind, v in W(k) if kind == "PARAM"]
    disp = lambda k: [v for kind, v in W(k) if kind == "DISP"]

    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ the aux button publishes NO control name",
            param("EARLY") == [],
            "aux reached param as %s. A modifier is not a control: a name here "
            "could be bound in the map, and an unmapped one would draw a raw "
            "row on the OLED every time you reached for a shifted key"
            % param("EARLY"))

    # og- because m_nano already publishes knob-1 to knob-9.
    print("\n--- the four knobs, and the og- prefix ---")
    for mark, want in (("KNOB1", ["og-knob-1", "0.25"]),
                       ("KNOB1-NEW", ["og-knob-1", "0.5"]),
                       ("KNOB4-ZERO", ["og-knob-4", "0"])):
        A.check("%s publishes %s" % (mark, " ".join(want)),
                param(mark) == [want], "got %s" % param(mark))
    A.check("KNOB23 publishes og-knob-2 and og-knob-3, in that order",
            param("KNOB23") == [["og-knob-2", "0.1"], ["og-knob-3", "0.2"]],
            "got %s" % param("KNOB23"))

    print("\n--- change -1 on every knob ---")
    A.check("the same value twice publishes ONCE",
            not param("KNOB1-SAME"),
            "a repeat got through as %s -- [change] is not filtering"
            % param("KNOB1-SAME"))

    # A bare [change] starts life holding 0 (ref/device/organelle.md).
    A.check("⛔ a knob parked at ZERO still publishes -- the -1 in [change -1]",
            param("KNOB4-ZERO") == [["og-knob-4", "0"]],
            "got %s. A bare [change] swallows this and the failure is a control "
            "that silently does nothing (item 237)" % param("KNOB4-ZERO"))

    # "No og-knob row", not "no disp row": knob 1 is mapped to tempo, so u_map
    # does put its value on the screen.
    print("\n--- item 242: the knobs do not report, and aux says shift ---")
    A.check("a mapped knob does put something on the screen",
            bool(disp("KNOB1")),
            "nothing reached disp when knob 1 moved -- without this the next "
            "check has no liveness witness and passes on a dead run")
    raw = [d for d in disp("KNOB1") if d and d[0].startswith("og-knob-")]
    A.check("⛔ ...but never the knob's RAW position", not raw,
            "the screen got %s where the mapped value belongs (item 242)" % raw)
    A.check("⛔ holding aux says `shift` on the screen",
            ["modal", "shift"] in disp("AUX-PRESS"),
            "the screen got %s" % disp("AUX-PRESS"))
    A.check("⛔ ...and letting go clears it",
            ["modal-off"] in disp("AUX-RELEASE"),
            "the screen got %s. A missed release leaves the word up for the "
            "30 s safety TTL, which is what that TTL is for" % disp("AUX-RELEASE"))

    print("\n--- the aux button publishes no control, on either edge ---")
    A.check("neither edge puts a control on param",
            not param("AUX-PRESS") and not param("AUX-RELEASE"),
            "press %s, release %s" % (param("AUX-PRESS"), param("AUX-RELEASE")))

    print("\n--- the shift layer ---")
    A.check("⛔ a key held under aux publishes og-shift-NN, not og-key-NN",
            param("SHIFT-KEY") == [["og-shift-72", "100"], ["og-shift-72", "0"]],
            "got %s" % param("SHIFT-KEY"))
    A.check("...and the layer drops the moment aux is let go",
            param("AFTER-SHIFT") == [["og-key-72", "100"]],
            "got %s" % param("AFTER-SHIFT"))

    # The straddle: pressed under the modifier, released after it. A release
    # read from the live modifier strands the shifted note (a stuck Volca note
    # in mode 1).
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

    A.check("⛔ a release publishes too, as velocity 0 -- NOT press-only",
            param("KEY-OFF") == [["og-key-60", "0"]],
            "wanted one og-key-60 0, got %s. A key that publishes its press and "
            "not its release leaves every note sounding forever"
            % param("KEY-OFF"))

    # Note 60 alone passes a decode that hardcodes the lowest key.
    A.check("the pitch really comes from the message -- the top key is og-key-84",
            param("KEY-TOP") == [["og-key-84", "40"]],
            "wanted one og-key-84 40, got %s" % param("KEY-TOP"))

    # og-key rows, not silence: disp is shared, and u_net's net-link-down
    # landed in these windows one run in three when this asked for silence.
    stray = [r for k in ("KEY-ON", "KEY-OFF", "KEY-TOP") for r in disp(k)
             if r and str(r[0]).startswith("og-key")]
    A.check("⛔ the keys reach param and NOT disp", not stray,
            "a key wrote to disp: %s" % stray)

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
