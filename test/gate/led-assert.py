#!/usr/bin/env python3
"""The aux LED's analyser -- ref/device/organelle.md. Reads a capture on stdin.

Callers send g_led a state on the disp bus, `led running`, never a color, so the
subject is the four-row table and what happens to a state not in it. It asserts
on the value mother is sent: the mapping to the hardware's RGB bitmask happens
inside mother.pd, which is not here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The number of windows led-assert-drive-gen.py's SEQ opens.
MARKS = 8

# ref/device/organelle.md, "What Cut It puts on the LED".
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

    print("\n--- before the boot sequence has finished ---")
    A.check("⛔ a state set at 300 ms already reaches the LED",
            led("EARLY") == [["3"]],
            "wanted one led 3, got %s. g_led needs neither the map nor the "
            "restore, so it must answer from the first millisecond" % led("EARLY"))

    # One window each, not a set: a set comparison passes two values swapped
    # between states.
    print("\n--- the four states, and the four values they mean ---")
    for mark, state, want in STATES:
        A.check("led %s is mother value %s" % (state, want),
                led(mark) == [[want]], "got %s" % led(mark))

    # A stopped patch must not look dead: the OLED goes dark for both.
    A.check("⛔ stopped is LIT, not dark -- a stopped patch must not look dead",
            led("STOPPED") == [["5"]] and led("STOPPED") != led("OFF"),
            "stopped sent %s and off sent %s" % (led("STOPPED"), led("OFF")))

    # The rows above would pass if STATES itself held one value twice.
    vals = [led(m)[0][0] if led(m) else None for m, _, _ in STATES]
    A.check("the four states carry four DIFFERENT values",
            len(set(vals)) == 4 and None not in vals,
            "values in state order were %s" % vals)

    print("\n--- a state it does not recognize ---")
    A.check("an unknown state raises warn g_led unknown-led-state",
            err("UNKNOWN") == [["warn", "g_led", "unknown-led-state"]],
            "got %s" % err("UNKNOWN"))
    A.check("⛔ ...and LEAVES THE LED ALONE", not led("UNKNOWN"),
            "the LED was driven to %s by a state that does not exist. A typo "
            "must not be able to blank the only non-screen indicator in the rig"
            % led("UNKNOWN"))

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
