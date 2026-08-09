#!/usr/bin/env python3
"""The display arbiter's analyser -- ref/module/display.md. Reads a capture on stdin.

WHAT THIS IS FOR. Everything else that tests the grid is an eyeball check, and
the bench used to say so in its own header: "there is no way to read back what
the LEDs are actually showing". That was too strong. Pd cannot ask the Launchpad
what is lit -- but the bytes the patch SENDS are completely knowable, and that is
the level a test of our own code should work at anyway.

⚠️ IT ASSERTS ON THE ARBITER, NOT ON THE DEVICE. Which layer wins the surface,
whether a warn is allowed to reach it, whether an alert gives it back when its
TTL expires, whether the repaint is gated at all. What the Launchpad is TOLD to
switch itself to is launchpad-assert's, next door.

This is the layer that would have caught the one-based beat bug in a single run.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

MODAL = 45


# ⛔ THE NUMBER OF WINDOWS display-assert-drive-gen.py's SEQ OPENS. Update it when
# that table changes, deliberately -- the same rule as MIDI_EXPECT and gates.py's
# EXPECT, and for the same reason: the check it feeds is what stops a driver that
# died early from answering every negative assertion below with an empty list.
MARKS = 15


def main():
    # ⛔ READ THE CAPTURE ONCE. G.parse reassembles SysEx frames out of it and
    # A.windows counts the MARK lines in the same text; handing sys.stdin to both
    # would leave the second one an exhausted stream and a silent "0 of 15".
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "GRID")
    lighting = [f for f in frames if f.is_lighting]

    # ⛔ THE BOOKKEEPING CHECK, AND THIS GATE WENT WITHOUT IT. It groups frames by
    # mark below with setdefault, which makes a window that NEVER ARRIVED
    # indistinguishable from one that arrived empty -- and two assertions here are
    # negative ("the grid stops repainting", "a warn changes nothing"), so a driver
    # that died at window three would have been ANSWERED BY THE EMPTY LIST rather
    # than by a fact. lib_assert.windows() exists precisely for this and every
    # other capture-reading gate already used it.
    A.windows(cap, "GRID", MARKS)

    if not A.check("the run produced lighting frames at all", bool(lighting),
                   "no frame ever reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    # ---- structure, on every lighting frame ------------------------------
    bad_len = [len(f.data) for f in lighting if len(f.data) != G.FRAME_LEN]
    A.check("every frame is %d bytes" % G.FRAME_LEN, not bad_len,
            "saw lengths %s" % sorted(set(bad_len))[:5])
    A.check("every frame ends with %d" % G.TERM,
            all(f.data[-1] == G.TERM for f in lighting), "a frame was not terminated")
    ok_len = [f for f in lighting if len(f.data) == G.FRAME_LEN]
    A.check("every spec is a static type byte 0",
            all(set(f.types()) == {0} for f in ok_len), "a spec had a non-zero type")
    want = list(range(G.FIRST_INDEX, G.FIRST_INDEX + G.NSPEC))
    A.check("every frame spans LED index %d..%d" % (want[0], want[-1]),
            all(f.indices() == want for f in ok_len),
            "the painted span moved -- CC 1-8 must stay outside it")

    by = {}
    for f in ok_len:
        by.setdefault(f.mark, []).append(f)
    window = lambda name: by.get(name, [])

    # ---- the dirty flag really does gate the repaint ----------------------
    # This window runs BEFORE "; pd dsp 1", so nothing is driving the beat row and
    # a correctly gated grid has nothing to redraw. It is the only assertion here
    # that tests the dirty flag rather than the arbiter.
    idle = window("idle-dsp-off")
    A.check("DSP off and idle: the grid stops repainting", not idle,
            "%d frames with no clock running -- the dirty flag is not gating"
            % len(idle))

    # ---- the boot frame, before any beat has arrived ----------------------
    boot = [f for f in ok_len if f.mark == "(none)"]
    if boot:
        problem, _lamp, _beat = G.home_shape(boot[0])
        if problem:
            A.note("the FIRST frame lights a cell outside every region: %s -- "
                   "g_grid's beat store starts at 0 and 0+10 is LED index 10, a "
                   "left-column ring button. Cosmetic and Mac-only: on the device "
                   "mother enables DSP at 200 ms so beats are already flowing by "
                   "the time ownership rises at ~3 s. Tracked in plan-v04.md"
                   % problem)

    # ---- state set BEFORE the grid owns the surface must survive -----------
    # ⛔ THE ONE CHECK HERE THAT LOOKS AT THE BOOT. mode-5 was set at 300 ms and
    # never again; if the first painted frame does not show it, then either the
    # mode was dropped on the floor or the grid is painting a default it invented.
    # Every other window in this run is seconds in and could not tell the difference.
    fs = window("home-early-mode")
    if A.check("home-early-mode: the grid repainted", bool(fs), "no frame in the window"):
        _problem, lamp, _beat = G.home_shape(fs[-1])
        A.check("⛔ a mode set at 300 ms -- before the grid painted at all -- SURVIVES",
                lamp == 95, "lit lamp was %s, wanted 95 (mode-5)" % lamp)

    # ---- home, and the mode lamp ------------------------------------------
    for mark, expect_lamp in (("home-mode-1", 91), ("home-mode-4", 94),
                              ("home-again", 94)):
        fs = window(mark)
        if not A.check("%s: the grid repainted" % mark, bool(fs), "no frame in the window"):
            continue
        problem, lamp, _beat = G.home_shape(fs[-1])
        A.check("%s: nothing lit outside the lamp row and the beat row" % mark,
                problem is None, problem or "")
        A.check("%s: the lit mode lamp is index %d" % (mark, expect_lamp),
                lamp == expect_lamp, "lit lamp was %s" % lamp)

    # ---- modal claims the whole surface -----------------------------------
    fs = window("modal-45")
    if A.check("modal-45: the grid repainted", bool(fs), "no frame in the window"):
        A.check("modal-45: all %d specs are palette %d" % (G.NSPEC, MODAL),
                set(fs[-1].colours()) == {MODAL},
                "colours present: %s" % sorted(set(fs[-1].colours()))[:6])

    # ---- a warn must never reach the grid ---------------------------------
    # ⛔ THE LIVENESS WITNESS IS NOT OPTIONAL, AND THIS ONE USED TO SAY `if fs else
    # True` -- an assertion that answered ITSELF with a pass whenever the window
    # was empty. "A warn changed nothing" and "nothing happened at all" are the
    # same capture, and only one of them is the fact being claimed. Every other
    # window on this page already guards itself this way.
    fs = window("warn-ignored")
    if A.check("warn-ignored: the grid repainted", bool(fs),
               "no frame in the window -- the beat row should be driving a repaint "
               "here, so silence means the run died rather than that the warn was "
               "ignored"):
        A.check("a warn changes nothing -- the modal is still up",
                all(set(f.colours()) == {MODAL} for f in fs),
                "a warn repainted the surface")

    # ---- alert outranks the modal, then gives it back ---------------------
    # The alert TTL is 2 s and this window is longer, so the LAST frame in it has
    # already expired back to the modal. Assert on the FIRST frame after the mark.
    fs = window("alert-red")
    if A.check("alert-red: the grid repainted", bool(fs), "no frame in the window"):
        A.check("alert-red: all %d specs are red (%d)" % (G.NSPEC, G.ALERT_RED),
                set(fs[0].colours()) == {G.ALERT_RED},
                "colours present: %s" % sorted(set(fs[0].colours()))[:6])
        A.check("alert-red: the alert expires inside its own window",
                set(fs[-1].colours()) != {G.ALERT_RED},
                "still red at the end of the window -- the TTL never fired")
    fs = window("alert-expired")
    if A.check("alert-expired: the grid repainted", bool(fs),
               "NO FRAME AFTER THE ALERT TTL -- the grid would stay red forever"):
        A.check("alert-expired: the surface returns to the MODAL underneath",
                set(fs[-1].colours()) == {MODAL},
                "expected %d everywhere, got %s"
                % (MODAL, sorted(set(fs[-1].colours()))[:6]))

    # ---- the beat row, which is where the one-based bug lived -------------
    fs = window("beat-row")
    if A.check("beat-row: the grid repainted", bool(fs),
               "no frames -- is DSP on? the beat row hangs off threshold~"):
        seen, strays = set(), []
        for f in fs:
            problem, _lamp, beat = G.home_shape(f)
            if problem:
                strays.append(problem)
            if beat is not None:
                seen.add(beat)
        A.check("beat-row: the lit cell never leaves index %d..%d"
                % (G.BEAT_LO, G.BEAT_HI), not strays, strays[0] if strays else "")
        A.check("beat-row: the beat walks -- at least 4 of the 8 cells were lit",
                len(seen) >= 4, "only saw %s" % sorted(seen))

    # ---- panic must NOT cost the grid --------------------------------------
    # ⚠️ THIS IS THE ARBITER'S SIDE OF PANIC, not the device's. What m_launchpad
    # tells the hardware is launchpad-assert's check; this one is that g_grid
    # KEEPS painting, because it still owns the surface.
    #
    # ⛔ THIS ASSERTION WAS INVERTED ON 2026-08-08, deliberately. It used to
    # require silence -- panic surrendered the surface, so the grid died until the
    # patch was reloaded, and in Live Mode the device then flooded Pd's Midi-In 1
    # with clock (item 250). A panic that makes the instrument worse at the moment
    # you need it is a bug, and this gate was faithfully protecting it.
    fs = window("after-panic")
    A.check("⛔ the grid SURVIVES a panic -- it must keep painting", bool(fs),
            "no frames after panic. The surface is being surrendered again: "
            "silencing notes has nothing to do with giving the device back")

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
