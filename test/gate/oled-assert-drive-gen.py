#!/usr/bin/env python3
"""Generates the timed driver for the OLED gate, into the scratch path given.

⛔ g_oled IS THE DENSEST FILE IN THE PATCH -- 783 lines, four layers, a five-row
store with its own ageing -- AND UNTIL NOW ITS ENTIRE COVERAGE WAS THAT THE FILE
EXISTS. Everything else about it has been judged by eye off a panel.

⚠️ WHAT MAKES IT TESTABLE IS THE TAP ON oscOut. Pd cannot ask a screen what it is
showing, but every byte sent to it is knowable -- and u_mother-stub has decoded
that same stream into eight preview rows since Phase 3, so the arithmetic is
already debugged. This gate reimplements the parse in Python and asserts on the
gPrintln text, which is the level our own code works at.

⛔ EVERY WINDOW IS AT LEAST 700 ms LONG, AND THAT IS THE FRAME CLOCK'S DOING.
g_oled repaints on a [metro 100], so a window shorter than a few frames can miss
the repaint entirely and report a blank screen with total confidence. The TTL
windows are longer still, because what they assert is that something has GONE.

THE TIMINGS THAT ARE NOT FREE, all from ref/module/display.md:

    param   1200 ms, retriggered by any parameter
    alert   2000 ms for a warn, 4000 ms for a fail
    modal   until modal-off, or a 30 s safety TTL

Windows straddle each of those, and the fail window is checked twice: once where
a warn would already be gone, and once after its own longer TTL.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 40

SEQ = [
    # ⛔ NOTHING STARTS BEFORE 4500 ms, AND THAT IS NOT PADDING. u_init puts its
    # own MODAL on the screen at loadbang and does not send modal-off until about
    # 3500 ms -- so every window before that is asserting against `booting`, and
    # the first draft of this gate did exactly that. The boot owns the screen
    # until it says otherwise, which is the whole point of a modal.
    (4500, "HOME", ["\\; disp status gate-home"], GAP),

    # --- a parameter, and its 1200 ms TTL ---------------------------------
    # ⛔ THE "IT IS UP" WINDOW MUST BE SHORTER THAN THE TTL IT IS ASSERTING, and
    # the first draft of this gate got that backwards: a 1.7 s window around a
    # 1.2 s parameter ends with the parameter already gone, so the check that it
    # was ever drawn failed against a screen that had drawn it correctly and
    # then correctly cleared it. Up in 800 ms, gone in the next window.
    (5500, "PARAM", ["\\; disp gate-p1 11"], GAP),
    (6300, "PARAM-GONE", [], GAP),

    # ⛔ AND IT MUST NOT COME BACK. The store ages entries at 13 frames while
    # the layer flag clears at 1200 ms, so the store deliberately outlives the
    # flag by one frame -- if the ageing were broken, a new parameter would raise
    # the layer again and redraw the OLD one beside it.
    (8200, "PARAM-AGAIN", ["\\; disp gate-p2 22"], GAP),

    # ⚠️ A WINDOW WHOSE ONLY JOB IS TO LET THE STORE AGE OUT. 13 frames is 1.3 s
    # and the layer clears at 1.2 s, so anything sooner than about 1.8 s leaves
    # the previous parameter still holding a row -- and then it is the FIFTH of
    # the five below that gets refused rather than the sixth. Measured exactly
    # that on the first run, and it looked like a store that had lost an entry.
    (9000, "PARAM-AGED", [], GAP),

    # --- the five-row store, and the sixth that must be refused -----------
    (10800, "FIVE", ["\\; disp gate-a 1", "\\; disp gate-b 2", "\\; disp gate-c 3",
                     "\\; disp gate-d 4", "\\; disp gate-e 5"], GAP),
    (11400, "SIXTH", ["\\; disp gate-f 6"], GAP),

    # ⛔ RE-TOUCHED IN REVERSE ORDER, WHICH IS THE ONLY VERSION OF THIS TEST THAT
    # DISCRIMINATES. Re-touching one row and checking it stayed put fails for the
    # wrong reason -- the other four age out from under it in 1.3 s and there is
    # nothing left to hold a place among. Re-touching all five e,d,c,b,a keeps
    # every row alive AND makes the answer unambiguous: a stable store still
    # draws a,b,c,d,e, and a store that reorders on update draws e,d,c,b,a.
    (11900, "IN-PLACE", ["\\; disp gate-e 55", "\\; disp gate-d 44",
                         "\\; disp gate-c 33", "\\; disp gate-b 22",
                         "\\; disp gate-a 99"], GAP),

    # --- modal outranks param ---------------------------------------------
    (12600, "MODAL", ["\\; disp modal gate-modal"], GAP),
    (13600, "MODAL-PARAM", ["\\; disp gate-p9 99"], GAP),

    # --- alert outranks modal, and gives it back --------------------------
    # ⚠️ THIS WINDOW IS LONGER THAN THE ALERT IT RAISES, deliberately. The first
    # frame proves the alert won the surface and the last proves it gave it back,
    # which is one window doing the work of two -- the same shape display-assert
    # uses for the grid's alert.
    (14600, "ALERT", ["\\; err warn u_gate gate-alert"], GAP),
    (17600, "ALERT-GONE", [], GAP),

    # ⛔ A fail LASTS TWICE AS LONG AS A warn, and the two windows below are what
    # separates "the TTL works" from "the TTL is 2 s whatever you asked for".
    (18400, "FAIL", ["\\; err fail u_gate gate-fail"], GAP),
    (20900, "FAIL-STILL", [], GAP),
    (23200, "FAIL-GONE", [], GAP),

    # --- and the modal is cleared explicitly ------------------------------
    (24000, "MODAL-OFF", ["\\; disp modal-off"], GAP),

    # --- ⛔ THE TWO RESERVED SELECTORS THAT ARE NOT THE OLED'S ------------
    # g_oled routes led and grid and throws them away. Everything it does not
    # recognise is a parameter BY DEFINITION, so without those two arguments on
    # the route an LED request would draw as a nonsense parameter row.
    (24800, "RESERVED", ["\\; disp led running", "\\; disp grid modal 45"], GAP),

    # --- the diag layer, and the roster it draws ---------------------------
    # ⛔ SUMMONED ONCE AND ONLY ONCE. A layer holds STATE, so every presence
    # change below appears on the next repaint with no second summon -- and
    # that is also what makes the TTL windows at the end mean anything: they
    # measure from HERE.
    #
    # ⚠️ THE BOOT STATE IS FREE AND IT IS THE STRONGEST ROW IN THIS BLOCK. Every
    # active device is absent on a Mac by definition, so all three have already
    # been declared lost by their own c_presence around 10 s -- and if a `lost`
    # for a device that never answered were allowed to write GONE, this first
    # window would say so.
    (26600, "DIAG", ["\\; disp diag"], GAP),

    # ⚠️ knob1 IS NOT DECORATION. m_organelle is the PASSIVE layer: it publishes
    # `seen` on every decode and nothing else in the patch has ever read it.
    # Moving a knob is the only way to make that happen on a Mac, and it is what
    # proves the passive publisher reaches this screen at all.
    (27600, "DIAG-SEEN", ["\\; presence seen m_nano", "\\; knob1 0.5"], GAP),
    (28600, "DIAG-GONE", ["\\; presence lost m_nano"], GAP),

    # ⛔ THE DISCRIMINATING NEGATIVE. m_launchpad has never answered, so this
    # `lost` must leave it NEVER SEEN rather than move it to GONE. Without the
    # per-source ever-heard bit the two are identical on the bus.
    (29600, "DIAG-NEVER", ["\\; presence lost m_launchpad"], GAP),

    # ⛔ AND AN ALERT COVERS IT. A layer that always wins passes every positive
    # test above, so the cascade has to be asserted in the direction that
    # matters. A warn is 2 s, so the next window gets the screen back with the
    # diag layer's own 8 s TTL still running.
    (30600, "DIAG-ALERT", ["\\; err warn u_gate gate-diagx"], GAP),
    (33000, "DIAG-BACK", [], GAP),
    (35200, "DIAG-TTL", [], GAP),

    (36200, "DONE", [], GAP),
]
QUIT_MS = 37000

BLURB = ("oled-assert-drive -- GENERATED by oled-assert-drive-gen.py. Do not edit "
         "this file. It drives g_oled's five layers over the disp bus: a parameter "
         "and its TTL \\, five rows and a refused sixth \\, a modal \\, an alert "
         "outranking it \\, the longer fail TTL \\, the two reserved selectors \\, "
         "and the diag roster with an alert drawn over the top of it.")

NOTES = [
    "⚠️ RUN IT THROUGH test/gate/oled-assert.sh \\, never by hand. The gate taps "
    "oscOut \\, which is how g_oled draws -- without it the capture holds no drawing "
    "at all and every assertion here is answered by an empty list.",

    "⛔ THE TAP DOES NOT BREAK C-5. One owner per display surface governs WRITING \\, "
    "and Pd delivers a message to EVERY receiver of a name \\, so listening cannot "
    "change what the screen is told. Nothing built from lib_drive.TAP_LABELS ever "
    "writes.",
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: oled-assert-drive-gen.py OUT.pd  "
                 "(run it through test/gate/oled-assert.sh, which passes a scratch path)")
    w, b, c = D.build(sys.argv[1], SEQ, tag="OLED",
                      taps=["oscOut", "disp", "err", "presence"], quit_ms=QUIT_MS,
                      blurb=BLURB, notes=NOTES)
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b, c))
