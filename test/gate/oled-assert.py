#!/usr/bin/env python3
"""The OLED's analyser -- ref/module/display.md. Reads a capture on stdin.

⛔ g_oled IS 783 LINES AND ITS ENTIRE COVERAGE WAS THAT THE FILE EXISTS. Four
layers with priorities and time-to-live, a five-row parameter store with its own
ageing, three type sizes -- every bit of it judged by eye off a panel until now.

⚠️ IT ASSERTS ON WHAT THE SCREEN WAS TOLD, NOT ON WHAT IT LOOKS LIKE. Pd cannot
ask a screen what it is showing, but every byte sent to it is knowable, and that
is the level our own code works at. What a person still has to judge is the part
this cannot reach: whether 24px is legible at arm's length, and whether the
meters read as meters. That is what test/bench/display-bench.pd is for.

THE MESSAGE, read off a real capture rather than assumed:

    sendtyped /oled/gPrintln iiiiis 3 2 12 24 1 43
                             ^tag   ^s ^x ^y ^sz ^col ^words...

A FRAME is everything between two gFlips. ⛔ ASSERT ON THE RIGHT ONE: a layer
raised inside a window does not appear until the NEXT repaint, so the first frame
of a window still shows what came before it -- and a layer with a TTL shorter
than the window has already expired by the last. display-assert learned the same
lesson; here it is both ways round in one file.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS oled-assert-drive-gen.py's SEQ OPENS.
MARKS = 18

# The five rows the store holds, in the order they are first touched.
FIVE = ["gate-a", "gate-b", "gate-c", "gate-d", "gate-e"]

# The alert layer's border, read off g_oled.pd rather than guessed.
BORDER = ["sendtyped", "/oled/gBox", "iiiiii", "3", "0", "0", "127", "63", "1"]

_FLIP = ["sendtyped", "/oled/gFlip"]


def run_asserts(cap):
    order, by = A.windows(cap, "OLED", MARKS)
    W = lambda k: by.get(k, [])

    def frames(mark):
        """Complete frames in the window -- gFlip closes one.

        ⚠️ THE LEADING PARTIAL IS DROPPED. A window opens mid-frame, so its first
        few messages belong to a repaint that started before the mark and would
        report the previous window's content as this one's.
        """
        out, cur, started = [], [], False
        for lab, v in W(mark):
            if lab != "OLED":
                continue
            if v[:2] == _FLIP:
                if started:
                    out.append(cur)
                started, cur = True, []
            else:
                cur.append(v)
        return out

    def rows(frame):
        """-> [(y, size, [words])] for every gPrintln, top of the screen first."""
        out = []
        for v in frame:
            if v[:2] != ["sendtyped", "/oled/gPrintln"] or len(v) < 9:
                continue
            try:
                out.append((int(v[5]), int(v[6]), v[8:]))
            except ValueError:
                continue
        return sorted(out)

    def words(frame):
        return [w for _, _, ws in rows(frame) for w in ws]

    def last(mark):
        fs = frames(mark)
        return fs[-1] if fs else []

    def first(mark):
        fs = frames(mark)
        return fs[0] if fs else []

    def live(mark):
        """Every window's own liveness witness: the screen repainted at all."""
        return A.check("%s: the screen repainted" % mark, bool(frames(mark)),
                       "no complete frame in the window -- the 10 Hz clock is "
                       "the only thing that draws, so silence here means the run "
                       "died rather than that the layer was empty")

    # ---- home, which is never cleared and has no TTL ----------------------
    print("--- home ---")
    if live("HOME"):
        A.check("the footer carries the status it was given",
                "gate-home" in words(last("HOME")),
                "drew %s" % words(last("HOME")))

    # ---- a parameter, and its 1200 ms TTL ---------------------------------
    print("\n--- the param layer, and its TTL ---")
    # ⚠️ ONE MOVER IS A TWO-LINE LAYOUT, NOT A ROW. Type size follows how many
    # controls are moving: alone, a parameter gets its name at 8px on the top
    # line and its value at 24px below -- the biggest thing on the screen,
    # because with one hand on one control that is what you are looking at.
    # Three to five share a line each at 8px. Asserting the geometry rather than
    # just the words is what makes this a check on the layout at all.
    if live("PARAM"):
        A.check("a lone parameter draws name 8px at y=0 and value 24px at y=12",
                rows(last("PARAM")) == [(0, 8, ["gate-p1"]), (12, 24, ["11"])],
                "drew %s" % rows(last("PARAM")))
    if live("PARAM-GONE"):
        A.check("⛔ ...and 1.2 s after the hands stop, it is gone",
                "gate-p1" not in words(last("PARAM-GONE")),
                "still drawing %s. The TTL is one retriggered [delay], so a "
                "parameter that never expires means the screen keeps a stale "
                "value under a moving control" % words(last("PARAM-GONE")))
        A.check("...and the home layer is showing again",
                "gate-home" in words(last("PARAM-GONE")),
                "drew %s -- home is priority 0 and is never cleared, so it must "
                "be what is left" % words(last("PARAM-GONE")))

    # ⛔ AND THE STORE AGED OUT TOO, NOT JUST THE LAYER. The two are separate:
    # `pd layers` clears the param flag on a 1200 ms delay while the store drops
    # entries 13 frames behind. If the ageing were broken the flag would be
    # raised again by the NEW parameter and the OLD one would be redrawn beside
    # it -- a value under no one's hand, which is worse than a blank row.
    if live("PARAM-AGAIN"):
        drawn = words(last("PARAM-AGAIN"))
        A.check("a new parameter draws", "gate-p2" in drawn, "drew %s" % drawn)
        A.check("⛔ ...and the expired one does NOT come back with it",
                "gate-p1" not in drawn,
                "drew %s -- the store aged the layer out but kept the row" % drawn)
    if live("PARAM-AGED"):
        A.check("and it ages out of the STORE too, not only off the screen",
                not [w for w in ("gate-p1", "gate-p2")
                     if w in words(last("PARAM-AGED"))],
                "drew %s" % words(last("PARAM-AGED")))

    # ---- five rows, and the sixth that is refused -------------------------
    print("\n--- the store holds five, and refuses a sixth ---")
    if live("FIVE"):
        got = [ws[0] for _, _, ws in rows(last("FIVE")) if ws]
        A.check("five controls moving at once give five rows, in touch order",
                got == FIVE, "drew %s" % got)
        # ⚠️ AND AT 8px ON THE DOCUMENTED PITCH. The param area is y=0..46 and
        # the meter strips at y=48 and y=56 are untouched throughout -- a row
        # pitch that drifted would push the fifth row into the meters, where it
        # would overlap rather than error.
        A.check("...at 8px, on the y=0 9 18 27 36 pitch, clear of the meters",
                [(y, sz) for y, sz, _ in rows(last("FIVE"))]
                == [(0, 8), (9, 8), (18, 8), (27, 8), (36, 8)],
                "drew %s" % [(y, sz) for y, sz, _ in rows(last("FIVE"))])
    if live("SIXTH"):
        got = [ws[0] for _, _, ws in rows(last("SIXTH")) if ws]
        A.check("⛔ a SIXTH is refused, and the five keep their rows",
                got == FIVE,
                "drew %s. The sixth must wait for a row to free up rather than "
                "push one out -- with 18 continuous controls, moving two faders "
                "together is ordinary use" % got)

    # ⛔ ROWS ARE STABLE, AND THIS IS WHY THE STORE IS A LIST RATHER THAN A
    # QUEUE. A store that reordered on update would move a re-touched control to
    # the bottom, so a row would jump under your hand mid-performance -- the
    # value would be right and the screen would be unreadable.
    if live("IN-PLACE"):
        drawn = [ws for _, _, ws in rows(last("IN-PLACE"))]
        got = [ws[0] for ws in drawn if ws]
        A.check("⛔ re-touching all five in REVERSE order changes no row's place",
                got == FIVE,
                "drew %s. Driven e,d,c,b,a, a store that reordered on update "
                "would answer e,d,c,b,a -- so this is the one arrangement where "
                "the right answer and the wrong one cannot be confused" % got)
        A.check("...and every value did change",
                drawn == [["gate-a", "99"], ["gate-b", "22"], ["gate-c", "33"],
                          ["gate-d", "44"], ["gate-e", "55"]],
                "drew %s" % drawn)

    # ---- modal outranks param ---------------------------------------------
    print("\n--- layer priority: modal over param ---")
    if live("MODAL"):
        A.check("a modal claims the screen",
                "gate-modal" in words(last("MODAL")),
                "drew %s" % words(last("MODAL")))
    if live("MODAL-PARAM"):
        drawn = words(last("MODAL-PARAM"))
        A.check("⛔ a parameter moving UNDER a modal does not reach the screen",
                "gate-p9" not in drawn and "gate-modal" in drawn,
                "drew %s. Priority is a [select 1] cascade, so it reads top to "
                "bottom in exactly priority order" % drawn)

    # ---- alert outranks modal, and hands it back --------------------------
    # ⚠️ FIRST FRAME AND LAST FRAME OF THE SAME WINDOW. The window is longer than
    # the 2 s warn TTL on purpose: the first frame proves the alert won the
    # surface and the last proves it gave it back, which is one window doing the
    # work of two.
    print("\n--- layer priority: alert over modal, and the TTL ---")
    if live("ALERT"):
        drawn = words(first("ALERT"))
        A.check("an alert outranks the modal",
                "gate-alert" in drawn and "gate-modal" not in drawn,
                "drew %s" % drawn)
        A.check("...with its level and its source, not just the text",
                "warn" in drawn and "u_gate" in drawn, "drew %s" % drawn)
        A.check("...and a border around the whole screen",
                BORDER in first("ALERT"),
                "no %s in the frame" % " ".join(BORDER[1:2] + BORDER[3:]))
        A.check("⛔ a warn expires inside its own 2 s and gives the modal back",
                "gate-modal" in words(last("ALERT")),
                "the last frame of a 3 s window drew %s -- the TTL never fired "
                "and an alert would cover the screen forever" % words(last("ALERT")))
    if live("ALERT-GONE"):
        A.check("...and stays given back",
                "gate-modal" in words(last("ALERT-GONE"))
                and "gate-alert" not in words(last("ALERT-GONE")),
                "drew %s" % words(last("ALERT-GONE")))

    # ⛔ A fail LASTS TWICE AS LONG AS A warn, and without this window the two
    # TTLs are indistinguishable: a file that used 2 s for both would pass every
    # alert check above.
    print("\n--- and a fail lasts twice as long ---")
    if live("FAIL"):
        A.check("a fail claims the screen too",
                "gate-fail" in words(first("FAIL")),
                "drew %s" % words(first("FAIL")))
    if live("FAIL-STILL"):
        A.check("⛔ still up 2.5 s later -- where a warn would already be gone",
                "gate-fail" in words(first("FAIL-STILL")),
                "drew %s. warn is 2 s and fail is 4 s; one value for both means "
                "the errors that matter most are the ones you get least time to "
                "read" % words(first("FAIL-STILL")))
    if live("FAIL-GONE"):
        A.check("...and gone by 4.8 s",
                "gate-fail" not in words(last("FAIL-GONE")),
                "drew %s" % words(last("FAIL-GONE")))

    # ---- modal-off ---------------------------------------------------------
    print("\n--- modal-off, and the two reserved selectors ---")
    if live("MODAL-OFF"):
        drawn = words(last("MODAL-OFF"))
        A.check("modal-off clears the modal and home comes back",
                "gate-modal" not in drawn and "gate-home" in drawn,
                "drew %s" % drawn)

    # ⛔ led AND grid ARE ROUTED AND THROWN AWAY. Everything g_oled does not
    # recognise is a parameter BY DEFINITION -- that is what lets a new control
    # need no change to any display -- so without those two arguments on the
    # route an LED request would draw as a nonsense parameter row.
    if live("RESERVED"):
        drawn = words(last("RESERVED"))
        strays = [w for w in ("led", "running", "grid", "45") if w in drawn]
        A.check("⛔ `led` and `grid` never draw as parameters",
                not strays,
                "drew %s. They belong to g_led and g_grid; g_oled matches them "
                "only to discard them" % strays)
        A.check("...and the screen is still live while ignoring them",
                "gate-home" in drawn,
                "drew %s -- without this, ignoring them is indistinguishable "
                "from a dead screen" % drawn)

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
