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
MARKS = 22


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

    # What was on show at the last power-off, row 1's left page, set at the boot and never again: a
    # first painted frame without it means it was dropped, or the grid painted a default of its own.
    lay = G.drum_layout()
    painted = [f for f in ok_len if f.mark in ("(none)", "idle-dsp-off", "dsp-on", "settling")]
    A.check("the grid painted before the first window that asks", bool(painted))
    if painted:
        problem, lamp, _page = G.drum_page(painted[-1], lay)
        A.check("⛔ a page saved at power-off survives the boot: the frames before any press are its",
                problem is None and lamp == G.LEFT[0], problem or "lamp %s, wanted %d" % (lamp, G.LEFT[0]))
    fs = window("home-restored")
    if A.check("home-restored: the grid repainted", bool(fs), "no frame in the window"):
        problem, lamp, _page = G.drum_page(fs[-1], lay)
        A.check("home-restored: the drum page, and nothing lit outside it and the lamps",
                problem is None, problem or "")
        A.check("⛔ home-restored: the repeat pads and pad-35 the brightest purple, pad-38 dim blue, "
                "and pad-36 and pad-37 between them dark", [fs[-1].color(i) for i in (45, 48, 35, 38,
                                                                                     36, 37)]
                == [G.REP_DIM, G.REP_DIM, G.REP_DIM, G.RECALL_DIM, 0, 0],
                "cells 45 48 35 38 36 37: %s" % [fs[-1].color(i) for i in (45, 48, 35, 38, 36, 37)])
        A.check("⛔ home-restored: its left button full, the seed's three rows dim, the others dark",
                [fs[-1].color(i) for i in G.LEFT + G.RIGHT] == [
                    G.VOICE_FULL[0], G.VOICE_DIM[1], G.VOICE_DIM[2], 0, 0, 0, 0, 0,
                    G.VOICE_DIM[0], G.VOICE_DIM[1], G.VOICE_DIM[2], 0, 0, 0, 0, 0],
                [fs[-1].color(i) for i in G.LEFT + G.RIGHT])

    # The other pages through the map, the voices and the frame clock, from a press. What each
    # cell shows is g_grid_test.lua's; here, that the page came, and from where.
    def last(mark):
        fs = window(mark)
        return fs[-1] if A.check("%s: the grid repainted" % mark, bool(fs), "no frame in the window") else None

    # Row 2's left button: the harmony page, in its color, the generator's state having reached it.
    f = last("harmony")
    if f:
        cells = {10 * r + c for r in range(1, 9) for c in range(1, 9)} | set(range(101, 106))
        problem, lamp = G.page_shape(f, cells)
        A.check("⛔ harmony: row 2's left button full, nothing lit but the page and the edges",
                problem is None and lamp == G.LEFT[1], problem or "lamp %s" % lamp)
        rows = [f.color(80 + c) for c in range(1, 9)]
        A.check("⛔ harmony: the top row its chords, c_melody's, in the voice's color",
                rows[0] in (G.VOICE_FULL[1], G.VOICE_DIM[1]) and f.color(101) in (G.VOICE_FULL[1], G.VOICE_DIM[1]),
                rows)
    # The lit one again: back to the performance page, with nothing in play yet.
    f = last("harmony-again")
    if f:
        problem, lamp = G.page_shape(f)
        A.check("⛔ the lit button again: the performance page, every lamp dim and nothing else lit",
                problem is None and lamp is None, problem or "lamp %s" % lamp)
    # Row 3's: the melody page, its notes from the generator: the pitch pads light with no note.
    f = last("melody")
    if f:
        cells = {10 * r + c for r in range(1, 9) for c in range(1, 9)} | set(range(101, 104))
        problem, lamp = G.page_shape(f, cells)
        A.check("⛔ melody: row 3's left button full, nothing lit but the page and the edges",
                problem is None and lamp == G.LEFT[2], problem or "lamp %s" % lamp)
        A.check("⛔ melody: the rows of pitch lit, from the generator's notes",
                all(f.color(10 * r + c) != 0 for r in range(1, 5) for c in range(1, 9)),
                [f.color(10 + c) for c in range(1, 9)])
    # Row 3's right button: its setup page: its parameters on rows 3 to 8, its patches on 2, notes on 1.
    SOUND_CELLS = [10 * r + c for r in range(1, 9) for c in range(1, 9)]
    f = last("sound")
    if f:
        problem, lamp = G.page_shape(f, lit=SOUND_CELLS)
        A.check("⛔ sound: row 3's right button full, and nothing else lit",
                problem is None and lamp == G.RIGHT[2], problem or "lamp %s" % lamp)
    # An unused row's right button: a new voice, and its setup page.
    f = last("new-voice")
    if f:
        problem, lamp = G.page_shape(f, lit=SOUND_CELLS)
        A.check("⛔ new-voice: row 5's right button starts a voice: it lights, full, and its left, dim",
                problem is None and lamp == G.RIGHT[4] and f.color(G.LEFT[4]) == G.VOICE_DIM[4],
                problem or "lamp %s, left %s" % (lamp, f.color(G.LEFT[4])))
    # Aux: the songs page, from anywhere; and back to where it was.
    f = last("aux")
    if f:
        problem, lamp = G.page_shape(f)
        A.check("⛔ aux: the songs page: no cells of its own, every lamp dim",
                problem is None and lamp is None, problem or "lamp %s" % lamp)
    f = last("aux-again")
    if f:
        A.check("⛔ aux again: back where it was, row 5's setup page", G.page_shape(f, lit=SOUND_CELLS) == (None, G.RIGHT[4]),
                G.page_shape(f))
    # Setup: the diagnostics page, the same way.
    f = last("setup")
    if f:
        problem, lamp = G.page_shape(f, (81, 82))
        A.check("⛔ setup: the diagnostics page: its two pads lit, every lamp dim",
                problem is None and lamp is None and f.color(81) and f.color(82),
                problem or "cells %s %s" % (f.color(81), f.color(82)))
    f = last("setup-again")
    if f:
        A.check("⛔ setup again: back where it was", G.page_shape(f, lit=SOUND_CELLS) == (None, G.RIGHT[4]), G.page_shape(f))
    f = last("drums")
    if f:
        problem, lamp, _page = G.drum_page(f, lay)
        A.check("⛔ row 1's left button: the drum page", problem is None and lamp == G.LEFT[0],
                problem or "lamp %s" % lamp)

    fs = window("modal-45")
    if A.check("modal-45: the grid repainted", bool(fs), "no frame in the window"):
        A.check("modal-45: all %d specs are palette %d" % (G.NSPEC, MODAL),
                set(fs[-1].colors()) == {MODAL},
                "colors present: %s" % sorted(set(fs[-1].colors()))[:6])

    # "A warn changed nothing" and "nothing happened" are the same capture, so
    # the window has to have repainted first.
    fs = window("warn-ignored")
    if A.check("warn-ignored: the grid repainted", bool(fs),
               "no frame in the window -- the beats should be driving a repaint "
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

    # Under the layers it was the drum page, and the modal's going brings it back.
    f = last("home-again")
    if f:
        problem, lamp, _page = G.drum_page(f, lay)
        A.check("⛔ home-again: the page under the modal comes back", problem is None
                and lamp == G.LEFT[0], problem or "lamp %s" % lamp)

    # PLAY: the performance page comes up by itself, and the clock keeps it repainted.
    fs = window("play")
    if A.check("play: the grid repainted", bool(fs), "no frames -- is DSP on?"):
        bad = [G.page_shape(f) for f in fs[1:]]
        bad = [b for b in bad if b[0] or b[1] is not None]
        A.check("⛔ play: the performance page, every lamp dim, in every frame after the first",
                not bad and len(fs) > 1, bad[:1] or len(fs))

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
