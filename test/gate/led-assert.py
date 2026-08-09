#!/usr/bin/env python3
"""The aux LED's analyser -- ref/device/organelle.md. Reads a capture on stdin.

g_led owns the one display surface in the rig that is not a screen. Callers send
a STATE on the disp bus -- `led running` -- and never a colour, so the whole
subject of this gate is the four-row translation table and what happens to a row
that is not in it.

⛔ IT ASSERTS ON WHAT MOTHER IS TOLD, NOT ON WHAT LIGHTS UP. Pd cannot ask an LED
what colour it is, and the permutation from the patch-facing 0..7 to the
hardware's RGB bitmask happens inside mother.pd, which is not here. The value
sent to `led` is completely knowable, and it is the level our own code works at.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS led-assert-drive-gen.py's SEQ OPENS. Update it when
# that table changes, deliberately.
MARKS = 8

# ref/device/organelle.md, "What Cut It puts on the LED". Four states, four
# mother values, and NOT ONE OF THEM IS SHARED -- which is the point.
STATES = (("OFF", "off", "0"),
          ("STOPPED", "stopped", "5"),
          ("RUNNING", "running", "3"),
          ("PANIC", "panic", "1"))


def run_asserts(cap):
    order, by = A.windows(cap, "LED", MARKS)
    W = lambda k: by.get(k, [])
    led = lambda k: [v for kind, v in W(k) if kind == "LED"]
    err = lambda k: [v for kind, v in W(k) if kind == "ERR"]
    disp = lambda k: [v for kind, v in W(k) if kind == "DISP"]

    # ---- before the boot sequence has finished ----------------------------
    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ a state set at 300 ms already reaches the LED",
            led("EARLY") == [["3"]],
            "wanted one led 3, got %s. g_led needs neither the map nor the "
            "restore, so it must answer from the first millisecond" % led("EARLY"))

    # ---- the four states --------------------------------------------------
    # ⚠️ EXACT VALUES, ONE WINDOW EACH. The four are asserted separately rather
    # than as a set because the failure that matters is a SWAP -- two states
    # sharing a value, or two values swapped between states, both of which a set
    # comparison would pass.
    print("\n--- the four states, and the four values they mean ---")
    for mark, state, want in STATES:
        A.check("led %s is mother value %s" % (state, want),
                led(mark) == [[want]], "got %s" % led(mark))

    # ⛔ AND stopped IS LIT. This is the one row where a plausible-looking value
    # would defeat the purpose of the state existing: a patch that is up but not
    # running must not look identical to a patch that has died, and nothing else
    # in the rig reports the difference -- the OLED goes dark for both.
    A.check("⛔ stopped is LIT, not dark -- a stopped patch must not look dead",
            led("STOPPED") == [["5"]] and led("STOPPED") != led("OFF"),
            "stopped sent %s and off sent %s" % (led("STOPPED"), led("OFF")))

    # ⚠️ ALL FOUR DISTINCT, stated once rather than implied four times. Three
    # states that agreed would still pass every row above if the table were
    # written with the same value twice.
    vals = [led(m)[0][0] if led(m) else None for m, _, _ in STATES]
    A.check("the four states carry four DIFFERENT values",
            len(set(vals)) == 4 and None not in vals,
            "values in state order were %s" % vals)

    # ---- a state g_led does not know --------------------------------------
    print("\n--- a state it does not recognise ---")
    A.check("an unknown state raises warn g_led unknown-led-state",
            err("UNKNOWN") == [["warn", "g_led", "unknown-led-state"]],
            "got %s" % err("UNKNOWN"))
    A.check("⛔ ...and LEAVES THE LED ALONE", not led("UNKNOWN"),
            "the LED was driven to %s by a state that does not exist. A typo "
            "must not be able to blank the only non-screen indicator in the rig"
            % led("UNKNOWN"))

    # ---- a disp message that is not the LED's -----------------------------
    # g_led shares disp with g_oled, g_grid and u_net, and Pd delivers every
    # message to every receiver, so ignoring what is not its own is behaviour
    # rather than a formality.
    print("\n--- a disp selector that is not its own ---")
    A.check("the driver's non-led message did reach the bus",
            disp("NOT-LED") == [["status", "v0-test"]],
            "wanted status v0-test on disp, got %s -- without this the next "
            "check has no liveness witness" % disp("NOT-LED"))
    A.check("a disp message that is not led drives nothing and warns nothing",
            not led("NOT-LED") and not err("NOT-LED"),
            "led %s, err %s" % (led("NOT-LED"), err("NOT-LED")))

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
