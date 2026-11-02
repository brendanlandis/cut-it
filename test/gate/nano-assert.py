#!/usr/bin/env python3
"""The nanoKONTROL's analyzer -- ref/device/nanokontrol.md. Reads a capture on stdin.

It asserts on the decode, not the device: which channels m_nano admits, which
names it builds, what it refuses to emit, and what it says when it recognizes
nothing. What the device sends is item 31.

The channels under test, 17 and 18, are main-dev.pd's first argument; another
argument makes every channel check here wrong.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The number of windows nano-assert-drive-gen.py's SEQ opens.
MARKS = 17

# The five name families m_nano builds from the div 10 kind.
FAMILIES = ("slider-", "knob-", "btn-t-", "btn-b-", "xport-")

# What the other two devices' [ctlin] boxes build. One t-ctlin reaches all three.
FOREIGN = ("sp-cc-", "lp-cc-")

# Every window whose messages are addressed to the nanoKONTROL's own channels.
NANO_WINDOWS = ("EARLY", "CH-16", "CH-17", "CH-18", "CH-19", "SLIDER", "KNOB",
                "BTN-T", "BTN-B", "XPORT", "PRESS-RELEASE", "UNMAPPED",
                "STALE-CONT", "STALE-BTN")


def run_asserts(cap):
    order, by = A.windows(cap, "NANO", MARKS)
    W = lambda k: by.get(k, [])
    param = lambda k: [v for kind, v in W(k) if kind == "PARAM"]
    disp = lambda k: [v for kind, v in W(k) if kind == "DISP"]
    err = lambda k: [v for kind, v in W(k) if kind == "ERR"]

    # ---- before the boot sequence has finished ----------------------------
    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ a control moved at 300 ms already decodes",
            param("EARLY") == [["slider-1", "64"]],
            "wanted one slider-1 64, got %s" % param("EARLY"))

    # ---- the channel gate -------------------------------------------------
    # The two positives are the two negatives' liveness witness.
    print("\n--- the channel gate: 17 and 18, and nothing else ---")
    A.check("Pd channel 17 is admitted", param("CH-17") == [["slider-2", "11"]],
            "wanted one slider-2 11, got %s" % param("CH-17"))
    A.check("Pd channel 18 -- the transport row's channel -- is admitted too",
            param("CH-18") == [["slider-2", "12"]],
            "wanted one slider-2 12, got %s" % param("CH-18"))
    A.check("⛔ Pd channel 16 is refused", not param("CH-16"),
            "the block below the nano leaked: %s. The Launchpad sits 16 below "
            "this one" % param("CH-16"))
    A.check("⛔ Pd channel 19 is refused", not param("CH-19"),
            "the block above the nano leaked: %s. The SP-404 sits 16 above "
            "this one" % param("CH-19"))

    # ---- div 10 / mod 10, and the five name families ----------------------
    # Exact names, not patterns: an off-by-one in div 10 or mod 10 still makes
    # a well-formed name.
    print("\n--- the five name families ---")
    for mark, want in (("SLIDER", ["slider-3", "21"]),
                       ("KNOB", ["knob-5", "22"]),
                       ("BTN-T", ["btn-t-2", "1"]),
                       ("BTN-B", ["btn-b-4", "1"]),
                       ("XPORT", ["xport-3", "1"])):
        A.check("%s decodes to %s" % (mark, " ".join(want)),
                param(mark) == [want], "got %s" % param(mark))

    # Buttons emit 1, not the 127 sent: Pd owns all button state. The transport
    # row gets this by being kind 4, on the >= 2 path.
    A.check("⛔ the transport row is treated as a BUTTON, not as a value",
            param("XPORT") == [["xport-3", "1"]],
            "kind 4 must inherit the >= 2 button path; got %s" % param("XPORT"))

    # ---- press only -------------------------------------------------------
    print("\n--- buttons emit on press only ---")
    A.check("⛔ a press emits and the release that follows it does NOT",
            param("PRESS-RELEASE") == [["btn-t-4", "1"]],
            "wanted exactly one btn-t-4 1 from a 127-then-0 pair, got %s"
            % param("PRESS-RELEASE"))

    # ---- an unmapped CC ---------------------------------------------------
    print("\n--- a CC that decodes to no known kind ---")
    A.check("an unmapped CC raises warn m_nano cc-55-unmapped",
            err("UNMAPPED") == [["warn", "m_nano", "cc-55-unmapped"]],
            "got %s" % err("UNMAPPED"))
    A.check("...and emits nothing on param", not param("UNMAPPED"),
            "an unrecognised controller reached the instrument as %s"
            % param("UNMAPPED"))

    # ---- the stale-flag trap ----------------------------------------------
    # Only the is-btn clear is load-bearing, measured by deleting both: an
    # unmapped CC has kind >= 2, so decode-name has already cleared is-cont
    # before route rejects it. STALE-CONT asserts what is reachable instead: an
    # unrecognized controller leaves the continuous path shut.
    print("\n--- the flag clears behind the unmapped path ---")
    A.check("⛔ a stale is-btn cannot leak a second press under the last name",
            param("STALE-BTN") == [["btn-t-6", "1"]],
            "wanted exactly one btn-t-6 1; a second entry means CC 56 was emitted "
            "as btn-t-6 -- the previous control's name. Got %s" % param("STALE-BTN"))
    A.check("an unmapped CC after a continuous control emits nothing of its own",
            param("STALE-CONT") == [["slider-7", "30"]],
            "wanted exactly one slider-7 30; a second entry means CC 55's value "
            "reached the instrument. Got %s" % param("STALE-CONT"))

    # ---- one bus, and one row per control ---------------------------------
    # What a control draws is u_map's alone (item 317). Rows are counted by
    # name, exactly: g_oled redraws a row in place by name, so a duplicate is
    # invisible on screen. Two lean on the shipped map: slider-3 has no mode-1
    # row, and slider-1 is volca-cc 41 there.
    print("\n--- param only, and ONE row per control ---")
    rows = lambda k, *names: [d for d in disp(k) if d[:1] and d[0] in names]
    kinds = [k for k, _ in W("SLIDER")]
    A.check("⛔ param goes out BEFORE anything reacts to it",
            kinds[:1] == ["PARAM"],
            "the window opens with %s -- nothing may reach disp before the control "
            "reaches param, which is where u_map hears it" % (kinds[:1] or "nothing"))
    A.check("⛔ an UNMAPPED slider draws ONE row -- u_map's slider-3 21, and none from m_nano",
            rows("SLIDER", "slider-3") == [["slider-3", "21"]],
            "rows for slider-3: %s. Two identical rows means an m_ layer is posting "
            "its own again (item 317); none means slider-3 gained a mode-1 row in "
            "cut-it-map.txt" % rows("SLIDER", "slider-3"))
    A.check("⛔ a MAPPED fader draws ONE row, the destination's -- volca-cc41 64 and no slider-1",
            rows("EARLY", "slider-1", "volca-cc41") == [["volca-cc41", "64"]],
            "rows for slider-1 and volca-cc41 at 300 ms: %s. A slider-1 row is the "
            "double row this gate exists to keep out; no volca-cc41 row means the "
            "shipped mode-1 slider-1 volca-cc 41 row moved"
            % rows("EARLY", "slider-1", "volca-cc41"))

    # The other two [ctlin] layers, through the same stub.
    A.check("⛔ the 404's CTRL knob draws ONE row too -- u_map's sp-cc-20 77",
            rows("CH-404", "sp-cc-20") == [["sp-cc-20", "77"]],
            "rows for sp-cc-20: %s" % rows("CH-404", "sp-cc-20"))
    A.check("⛔ ... and so does a Launchpad ring button -- lp-cc-20 55",
            rows("CH-LP", "lp-cc-20") == [["lp-cc-20", "55"]],
            "rows for lp-cc-20: %s" % rows("CH-LP", "lp-cc-20"))

    # ---- cross-talk between the three channel blocks ----------------------
    # One t-ctlin reaches all three rewritten [ctlin] boxes; these two are the
    # liveness witness for the checks after them.
    print("\n--- the other two channel blocks, through the same stub ---")
    A.check("the SP-404's block admits its own channel",
            param("CH-404") == [["sp-cc-20", "77"]],
            "wanted one sp-cc-20 77 on channel 33, got %s. Without this the "
            "cross-talk checks below have no liveness witness" % param("CH-404"))
    lp = [v for v in param("CH-LP") if v and v[0].startswith("lp-cc-")]
    A.check("the Launchpad's block admits its own channel",
            len(lp) == 1 and lp[0][0] == "lp-cc-20",
            "wanted one lp-cc-20 on channel 1, got %s" % param("CH-LP"))

    strays = [(m, v) for m in NANO_WINDOWS for v in param(m) + disp(m)
              if v and v[0].startswith(FOREIGN)]
    A.check("⛔ nothing on the nano's channels reaches the other two devices",
            not strays, "%d foreign emit(s): %s" % (len(strays), strays[:4]))

    invaders = [(m, v) for m in ("CH-404", "CH-LP") for v in param(m) + disp(m)
                if v and v[0].startswith(FAMILIES)]
    A.check("⛔ nothing on the other two channels reaches m_nano",
            not invaders, "%d nano emit(s) from a foreign channel: %s"
            % (len(invaders), invaders[:4]))

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
