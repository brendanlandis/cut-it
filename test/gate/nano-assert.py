#!/usr/bin/env python3
"""The nanoKONTROL's analyser -- ref/device/nanokontrol.md. Reads a capture on stdin.

WHAT THIS IS FOR. m_nano is the main control surface of the instrument and it had
no headless coverage at all, because every path in it sits behind [ctlin] and
there is no bus behind a MIDI input. test/stubs/t_ctlin.pd is what changed that.

⚠️ IT ASSERTS ON THE DECODE, NOT ON THE DEVICE. What a nanoKONTROL actually
transmits is measured on hardware and written down in the page's Facts table
(item 31); this gate is about what m_nano DOES with those numbers -- which
channels it admits, which names it builds, which events it refuses to emit for,
and what it says when it recognises nothing.

⛔ THE CHANNEL BLOCK IS PD'S INPUT SLOT, not the device's place in the system MIDI
list. main-dev.pd passes 17, so the two channels under test are 17 and 18. Drive
this against a patch instantiated with a different first argument and every
channel check here is asserting the wrong thing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS nano-assert-drive-gen.py's SEQ OPENS. Update it when
# that table changes, deliberately -- it is what stops a driver that died early
# from answering every "this window is empty" assertion with an empty list.
MARKS = 17

# The five name families m_nano's route builds, from the div 10 kind. Written out
# rather than pattern-matched, because the whole subject of this gate is that the
# right name comes out.
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
    # ⛔ m_nano NEEDS NEITHER THE MAP NOR THE RESTORE, so it must decode from the
    # first millisecond. u_map reads its table at loadbang and u_state restores at
    # ~3.5 s; a control that works at 5 s and is dropped at 300 ms is exactly the
    # shape of item 234, and every other window here is too late to see it.
    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ a control moved at 300 ms already decodes",
            param("EARLY") == [["slider-1", "64"]],
            "wanted one slider-1 64, got %s" % param("EARLY"))

    # ---- the channel gate -------------------------------------------------
    # The offset is 0 for the control groups and 1 for the transport row, so the
    # gate is 0 <= offset < 2. The two positives below are the two negatives'
    # liveness witness: without them "channel 16 emitted nothing" is also what a
    # dead run says.
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
    # ⚠️ EXACT NAMES, NOT PATTERNS. The whole decode is one arithmetic idiom --
    # kind = div 10, which = mod 10 -- so an off-by-one in either direction still
    # produces a well-formed name from the right family.
    print("\n--- the five name families ---")
    for mark, want in (("SLIDER", ["slider-3", "21"]),
                       ("KNOB", ["knob-5", "22"]),
                       ("BTN-T", ["btn-t-2", "1"]),
                       ("BTN-B", ["btn-b-4", "1"]),
                       ("XPORT", ["xport-3", "1"])):
        A.check("%s decodes to %s" % (mark, " ".join(want)),
                param(mark) == [want], "got %s" % param(mark))

    # ⛔ THE THREE BUTTON FAMILIES EMIT 1, NOT THE 127 THEY WERE SENT. Pd owns
    # every toggle state because the mk1 has no host-controllable LEDs, so a
    # button that reported its raw value would put device-side state on a bus
    # that has none. The transport row inherits this by being kind 4, which is
    # >= 2 -- folding it in deleted a whole subpatch, and this is what proves the
    # fold was right.
    A.check("⛔ the transport row is treated as a BUTTON, not as a value",
            param("XPORT") == [["xport-3", "1"]],
            "kind 4 must inherit the >= 2 button path; got %s" % param("XPORT"))

    # ---- press only -------------------------------------------------------
    # ⚠️ ONE WINDOW, BOTH HALVES. A release-only window would pass on a dead run;
    # this one fails on nothing emitted and fails on two emitted.
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

    # ---- ⛔ THE STALE-FLAG TRAP -------------------------------------------
    # The unmapped path clears is-cont and is-btn FIRST, off the rightmost
    # outlets, and sends the error last. Without those clears the unmapped CC's
    # own value is emitted under the PREVIOUS control's name -- plausible, wrong
    # and silent, which is why m_nano has a subpatch for it.
    #
    # ⚠️ ONLY THE is-btn ARM IS LOAD-BEARING, AND THAT WAS MEASURED HERE RATHER
    # THAN READ OFF THE CANVAS. Deleting BOTH clears reddens STALE-BTN and leaves
    # STALE-CONT green, because decode-name writes both flags from the kind
    # before route ever rejects: an unmapped CC has kind >= 2 by definition -- a
    # kind below 2 is 0 or 1 and route accepts both -- so `>= 2` has already set
    # is-btn and `< 2` has already cleared is-cont. The is-cont clear is
    # belt-and-braces over a path that cannot currently be reached.
    #
    # ⛔ SO THE SECOND WINDOW IS NOT A SECOND ARM OF THE SAME CLAIM. It asserts
    # the thing that IS reachable at a non-127 value: an unrecognised controller
    # must leave the continuous path shut, whatever it was carrying and whatever
    # ran before it.
    print("\n--- the flag clears behind the unmapped path ---")
    A.check("⛔ a stale is-btn cannot leak a second press under the last name",
            param("STALE-BTN") == [["btn-t-6", "1"]],
            "wanted exactly one btn-t-6 1; a second entry means CC 56 was emitted "
            "as btn-t-6 -- the previous control's name. Got %s" % param("STALE-BTN"))
    A.check("an unmapped CC after a continuous control emits nothing of its own",
            param("STALE-CONT") == [["slider-7", "30"]],
            "wanted exactly one slider-7 30; a second entry means CC 55's value "
            "reached the instrument. Got %s" % param("STALE-CONT"))

    # ---- two buses off one trigger, in that order -------------------------
    # param is the control CHANGING; disp is a request to SHOW it. The action
    # goes out of the trigger's right outlet first and the report second -- the
    # same order u_init uses for its stages, and the reason this file needs no
    # delay object anywhere.
    #
    # ⚠️ THE WINDOW HOLDS MORE DISP ROWS THAN m_nano SENDS, and that is correct.
    # u_map posts its own raw-value row for a control on the way past, so the
    # screen can tell a control that does nothing from a broken one -- u_map.pd
    # says so beside the box, and says m_nano's row lands AFTER it and wins,
    # because g_oled updates a row in place by name. So the assertion here is
    # about CONTENT rather than count: whoever posted them, every row in this
    # window must agree with param. Counting them instead would make this gate go
    # red whenever cut-it-map.txt changed, which is the map gate's business.
    print("\n--- param first, disp second ---")
    kinds = [k for k, _ in W("SLIDER")]
    A.check("⛔ param goes out BEFORE anything reacts to it",
            kinds[:1] == ["PARAM"],
            "the window opens with %s. m_nano's trigger must fire the action out "
            "of its right outlet and the report out of its left" % (kinds[:1] or "nothing"))
    ds = disp("SLIDER")
    A.check("every disp row for the control agrees with param",
            bool(ds) and all(d == param("SLIDER")[0] for d in ds),
            "param %s vs disp %s" % (param("SLIDER"), ds))
    A.note("%d disp row(s) for one slider move -- u_map posts one and m_nano "
           "posts one, and g_oled merges them by name" % len(ds))

    # ---- ⛔ CROSS-TALK BETWEEN THE THREE CHANNEL BLOCKS -------------------
    # One t-ctlin reaches all three rewritten [ctlin] boxes, so every message in
    # this run is offered to m_404 and m_launchpad too. That makes the three
    # channel gates assertable against each other instead of each being trusted
    # alone -- and the two windows below are the liveness witness: without them,
    # "no sp-cc anywhere" is also what a stub that reached nothing would say.
    print("\n--- the other two channel blocks, through the same stub ---")
    A.check("the SP-404's block admits its own channel",
            param("CH-404") == [["sp-cc-20", "77"]],
            "wanted one sp-cc-20 77 on channel 33, got %s. Without this the "
            "cross-talk checks below have no liveness witness" % param("CH-404"))
    lp = [v for v in param("CH-LP") if v and v[0].startswith("lp-cc-")]
    A.check("the Launchpad's block admits its own channel",
            len(lp) == 1 and lp[0][0] == "lp-cc-30",
            "wanted one lp-cc-30 on channel 1, got %s" % param("CH-LP"))

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
