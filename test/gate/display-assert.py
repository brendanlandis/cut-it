#!/usr/bin/env python3
"""The display arbiter's analyser -- ref/module/display.md. Reads a capture on stdin.

Pd cannot ask the Launchpad what is lit, but the bytes the patch sends are
knowable. It asserts on the arbiter: which layer wins the surface, whether a
warn reaches it, whether an alert gives it back when its TTL expires, whether
the repaint is gated. What the Launchpad is told to switch itself to is
launchpad-assert's.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

MODAL = 45


# The number of windows display-assert-drive-gen.py's SEQ opens. Frames are
# grouped by mark with setdefault, so without this check a driver that died early
# would answer the negative assertions below with an empty list.
MARKS = 15


def main():
    # Read once: G.parse and A.windows both need the text, and a second read of
    # stdin would get nothing.
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "GRID")
    lighting = [f for f in frames if f.is_lighting]

    A.windows(cap, "GRID", MARKS)

    if not A.check("the run produced lighting frames at all", bool(lighting),
                   "no frame ever reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    # A spec is 3 bytes for a palette color and 5 for RGB, so a frame is read
    # spec by spec rather than by its length: 332 bytes when every cell is a
    # palette color, two more for each RGB one (the drum page's levels).
    bad = sorted({len(f.data) for f in lighting if not f.whole})
    A.check("every frame reads as %d whole specs" % G.NSPEC, not bad,
            "frames of these lengths did not: %s" % bad[:5])
    A.check("every frame ends with %d" % G.TERM,
            all(f.data[-1] == G.TERM for f in lighting), "a frame was not terminated")
    ok_len = [f for f in lighting if f.whole]
    A.check("every spec is static: type 0, a palette color, or 3, RGB",
            all(set(f.types()) <= {0, 3} for f in ok_len), "a spec flashed or pulsed")
    want = list(range(G.FIRST_INDEX, G.FIRST_INDEX + G.NSPEC))
    A.check("every frame spans LED index %d..%d" % (want[0], want[-1]),
            all(f.indices() == want for f in ok_len),
            "the painted span moved -- CC 1-8 must stay outside it")

    by = {}
    for f in ok_len:
        by.setdefault(f.mark, []).append(f)
    window = lambda name: by.get(name, [])

    # This window runs before "; pd dsp 1", so a correctly gated grid has nothing
    # to redraw.
    idle = window("idle-dsp-off")
    A.check("DSP off and idle: the grid stops repainting", not idle,
            "%d frames with no clock running -- the dirty flag is not gating"
            % len(idle))

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

    # mode-5 was set at 300 ms and never again: a first painted frame without it
    # means the mode was dropped or the grid painted a default of its own.
    fs = window("home-early-mode")
    if A.check("home-early-mode: the grid repainted", bool(fs), "no frame in the window"):
        _problem, lamp, _beat = G.home_shape(fs[-1])
        A.check("⛔ a mode set at 300 ms -- before the grid painted at all -- SURVIVES",
                lamp == G.LAMPS[4], "lit lamp was %s, wanted %d (mode-5)"
                % (lamp, G.LAMPS[4]))

    # Mode 1 is the drum page: the beat row gives way to it while the clock
    # still runs, so every frame of the window is asked, not only the last.
    fs = window("home-mode-1")
    if A.check("home-mode-1: the grid repainted", bool(fs), "no frame in the window"):
        problem, lamp, _page = G.drum_page(fs[-1], G.drum_layout())
        A.check("home-mode-1: the drum page, and nothing lit outside it and the lamps",
                problem is None, problem or "")
        A.check("home-mode-1: the lit mode lamp is index %d" % G.LAMPS[0],
                lamp == G.LAMPS[0], "lit lamp was %s" % lamp)
        beats = sorted({i for f in fs for i in range(G.BEAT_LO, G.BEAT_HI + 1)
                        if f.color(i) == G.BEAT_ON})
        A.check("⛔ home-mode-1: the beat row gives way -- no beat cell lit in %d frames"
                % len(fs), not beats, "beat cells lit: %s" % beats)

    for mark, expect_lamp in (("home-mode-4", G.LAMPS[3]), ("home-again", G.LAMPS[3])):
        fs = window(mark)
        if not A.check("%s: the grid repainted" % mark, bool(fs), "no frame in the window"):
            continue
        problem, lamp, _beat = G.home_shape(fs[-1])
        A.check("%s: nothing lit outside the lamp row and the beat row" % mark,
                problem is None, problem or "")
        A.check("%s: the lit mode lamp is index %d" % (mark, expect_lamp),
                lamp == expect_lamp, "lit lamp was %s" % lamp)

    fs = window("modal-45")
    if A.check("modal-45: the grid repainted", bool(fs), "no frame in the window"):
        A.check("modal-45: all %d specs are palette %d" % (G.NSPEC, MODAL),
                set(fs[-1].colors()) == {MODAL},
                "colors present: %s" % sorted(set(fs[-1].colors()))[:6])

    # "A warn changed nothing" and "nothing happened" are the same capture, so
    # the window has to have repainted first.
    fs = window("warn-ignored")
    if A.check("warn-ignored: the grid repainted", bool(fs),
               "no frame in the window -- the beat row should be driving a repaint "
               "here, so silence means the run died rather than that the warn was "
               "ignored"):
        A.check("a warn changes nothing -- the modal is still up",
                all(set(f.colors()) == {MODAL} for f in fs),
                "a warn repainted the surface")

    # The alert TTL is 2 s and this window is longer, so its last frame has
    # already expired back to the modal: assert on the first.
    fs = window("alert-red")
    if A.check("alert-red: the grid repainted", bool(fs), "no frame in the window"):
        A.check("alert-red: all %d specs are red (%d)" % (G.NSPEC, G.ALERT_RED),
                set(fs[0].colors()) == {G.ALERT_RED},
                "colors present: %s" % sorted(set(fs[0].colors()))[:6])
        A.check("alert-red: the alert expires inside its own window",
                set(fs[-1].colors()) != {G.ALERT_RED},
                "still red at the end of the window -- the TTL never fired")
    fs = window("alert-expired")
    if A.check("alert-expired: the grid repainted", bool(fs),
               "NO FRAME AFTER THE ALERT TTL -- the grid would stay red forever"):
        A.check("alert-expired: the surface returns to the MODAL underneath",
                set(fs[-1].colors()) == {MODAL},
                "expected %d everywhere, got %s"
                % (MODAL, sorted(set(fs[-1].colors()))[:6]))

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

    # The arbiter's side of panic (the device's is launchpad-assert's): g_grid
    # still owns the surface, so it keeps painting. A grid that gave the surface
    # up would leave the Launchpad flooding Pd with clock (item 250).
    fs = window("after-panic")
    A.check("⛔ the grid SURVIVES a panic -- it must keep painting", bool(fs),
            "no frames after panic. The surface is being surrendered again: "
            "silencing notes has nothing to do with giving the device back")

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
