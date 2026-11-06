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
MARKS = 15


def run_asserts(cap):
    order, by = A.windows(cap, "ORG", MARKS)
    W = lambda k: by.get(k, [])
    param = lambda k: [v for kind, v in W(k) if kind == "PARAM"]
    disp = lambda k: [v for kind, v in W(k) if kind == "DISP"]

    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ aux is a press from the start: og-aux, the name the table gives to u_voices",
            param("EARLY") == [["og-aux", "1"]],
            "aux reached param as %s" % param("EARLY"))

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
    print("\n--- item 242: the knobs do not report ---")
    A.check("a mapped knob does put something on the screen",
            bool(disp("KNOB1")),
            "nothing reached disp when knob 1 moved -- without this the next "
            "check has no liveness witness and passes on a dead run")
    raw = [d for d in disp("KNOB1") if d and d[0].startswith("og-knob-")]
    A.check("⛔ ...but never the knob's RAW position", not raw,
            "the screen got %s where the mapped value belongs (item 242)" % raw)
    print("\n--- aux: a press, and no shift ---")
    # The modal it used to raise would sit on the screen for its 30 s safety TTL.
    A.check("⛔ aux's press publishes og-aux 1, once", param("AUX-PRESS") == [["og-aux", "1"]],
            "got %s" % param("AUX-PRESS"))
    A.check("⛔ ...and its release nothing", not param("AUX-RELEASE"), "got %s" % param("AUX-RELEASE"))
    A.check("...and neither edge raises a modal on the screen",
            not [d for k in ("AUX-PRESS", "AUX-RELEASE") for d in disp(k)
                 if d[:1] in (["modal"], ["modal-off"])],
            "the screen got %s and %s" % (disp("AUX-PRESS"), disp("AUX-RELEASE")))
    A.check("⛔ a key under aux is the same key: og-key, press and release",
            param("KEY-UNDER-AUX") == [["og-key-72", "100"], ["og-key-72", "0"]],
            "got %s" % param("KEY-UNDER-AUX"))

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

    # og-key rows, not silence: disp is shared, and under Pd 0.49 u_net's
    # net-link-down warning landed in these windows one run in three.
    stray = [r for k in ("KEY-ON", "KEY-OFF", "KEY-TOP") for r in disp(k)
             if r and str(r[0]).startswith("og-key")]
    A.check("⛔ the keys reach param and NOT disp", not stray,
            "a key wrote to disp: %s" % stray)

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
