#!/usr/bin/env python3
"""The sequencer's analyser -- ref/module/sequencer.md. Reads a capture on stdin.

    sequencer-assert.py --seed SEED --state DIR [-v]  < capture

It asserts on what leaves the patch: the drums sent to c_kit, the grid's frames, the
state bus and the song's draft, which u_song writes. Nothing inside c_steps is read.

  the restore    the seeded pattern comes back, is put straight back, and shows
  the time sig.  the top number over OSC sets the page's rows and blue steps, 9/8
                 and 3/4, a press lands on the step its row and column mean, and
                 one past the row does nothing
  editing        a velocity, steps on two tracks, a pad that plays and selects,
                 the step rule's three cases, nothing on the free row, and nothing
                 at all in another mode
  the transport  every step plays exactly its tracks, from step 1, on PLAY and
                 on PLAY again; STOP and panic stop it
  the last steps knob 2's, held at 16 until turned through it; knob 3's for the
                 selected track; two tracks looping on their own; the drum
                 screen's snap, over OSC through u_net, landing at PLAY
  the pads       a track's volume and pitch to c_kit, at the restore and from
                 the drum screen over OSC; a track at full randomness
  a repeat       held over four tracks at full randomness, it replays the coins
                 exactly as they fell
  mute and solo  a track muted and then soloed over OSC: its notes stop and
                 start, the others' do the opposite, the Launchpad dims the
                 pads that won't play, and both are put with the pattern
  a character    a track's distortion made fold over OSC: put with the pattern
  the reverb     its type made gigaverb over OSC: put with the pattern, last, and
                 told to c_kit
                 after the mutes and solos, and told to c_kit
  the disk       the pattern reaches the song's draft as one line, section 1's drums

A note's step is the playhead in the frame painted after it: c_steps sends a
step's notes and then its playhead in one logical instant, and the frame clock
paints at most 20 ms later, six times inside a sixteenth at 120 BPM.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

KEY = "drums"
WINDOWS = ["EARLY", "RESTORE", "NINE", "THREE", "ROW-PRESS", "ROW-DARK", "SEVEN", "VEL-2", "STEPS-T1", "PAD-2", "STEP-T2", "VEL-6",
           "RULE-ON", "RULE-SAME", "RULE-ON-AGAIN", "VEL-2-AGAIN", "RULE-OTHER",
           "FREE-ROW", "PAGE-1", "OTHER-PAGE", "PAGE-2", "PLAY", "STOP", "STOPPED",
           "KNOB2-HELD", "LAST-3", "REPLAY", "RE-SOON", "RE-STEP3", "RE-WALK", "PANIC", "AFTER-PANIC", "KNOB3",
           "PAST-LAST", "POLY", "POLY-STOP", "SNAP", "SNAP-PLAY", "SNAP-STOP",
           "SWING", "SW-PLAY", "SW-SOON", "SW-GAP", "SW-LATE", "SW-ON", "SW-STOP",
           "REP-PLAY", "REP-PRESS", "REP-HELD", "REP-OFF", "REP-STOP",
           "SOUND", "RAND", "RA-PLAY", "RA-STOP", "RR", "RR-PLAY",
           "RR-PRESS", "RR-HELD", "RR-OFF", "RR-STOP", "MUTE", "MU-PLAY", "MU-STOP", "SOLO",
           "SO-PLAY", "SO-STOP", "CHAR", "DRUNK", "VTYPE", "DR-PLAY"] + \
    ["DR-%d" % k for k in range(1, 97)] + ["DR-STOP", "DRAG", "DONE"]
EDITS = ["ROW-PRESS", "ROW-DARK", "VEL-2", "STEPS-T1", "PAD-2", "STEP-T2", "VEL-6", "RULE-ON", "RULE-SAME",
         "RULE-ON-AGAIN", "VEL-2-AGAIN", "RULE-OTHER"]

MARK = re.compile(r"^SEQ:\s+MARK\s+(\S+)$")
# t_kit, c_kit's stand-in, prints each hit c_steps sends: track n plays pad n.
NOTE = re.compile(r"^KITOUT:\s+(-?[\d.]+)\s+(-?[\d.]+)$")


CELLS = 16 * 32                 # then the 16 tracks' own last steps, their randomness, volumes
FXLESS = CELLS + 16 * 4 + 5     # and pitches, the time signature, the drunkenness, the swing
                                # and the global last step: 581
LINE = FXLESS + 8 * 16 + 2      # then each track's eight effects and the reverb's two: 711
FLAGGED = LINE + 2 * 16         # then each track's mute and each track's solo: 743
CHARRED = FLAGGED + 16          # then each track's character: 759
TYPED = CHARRED + 1             # then the reverb's type, once it is not the plate: 760
NUM, DRUNK, SWING, LAST = FXLESS - 5, FXLESS - 3, FXLESS - 2, FXLESS - 1   # NUM, then the bottom
RAND, VOL, PITCH = CELLS + 16, CELLS + 32, CELLS + 48    # where each track's are, track 1 first
LEVEL_VELS = [round(127 * n / 8 + 1e-9) for n in range(1, 9)]   # 16 32 48 64 79 95 111 127
# The seed's 7/8: rows of 7 steps on the page, a blue step every 7, each row's first. The windows
# that change the time signature have their own (c_steps.lua's R.row, ref/module/display.md).
EVERY, ROW = 7, 7
SIGS = {"NINE": (9, 8), "THREE": (3, 6), "ROW-PRESS": (3, 6), "ROW-DARK": (3, 6)}


def row_of(mark):
    return SIGS.get(mark, (EVERY, ROW))[1]


def idx(track, step):
    return (track - 1) * 32 + (step - 1)


def own(line, track):
    return line[CELLS + track - 1]


def args():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("-v", action="store_true")
    return p.parse_args()


def read_key(path):
    """The drums line of a song file, or the seed, as ints, or None."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except IOError:
        return None
    found = [l.split() for l in lines if l.split()[:1] == [KEY]]
    if len(found) != 1:
        return None
    return [int(float(v)) for v in found[0][1:]]


def events(cap):
    """The capture in order -> [(mark, kind, payload)]: whole lighting frames and
    note events, interleaved as they happened."""
    out, mark, buf, collecting = [], "PRE", [], False
    for line in cap.splitlines():
        line = line.strip()
        m = MARK.match(line)
        if m:
            mark = m.group(1)
            continue
        m = NOTE.match(line)
        if m:
            out.append((mark, "NOTE", tuple(int(float(v)) for v in m.groups())))
            continue
        m = G.MIDI_RE.match(line)
        if not m:
            continue
        byte = int(m.group(1))
        if byte == 240:
            buf, collecting = [240], True
        elif collecting and byte < 248:
            buf.append(byte)
            if byte == G.TERM:
                f = G.Frame(buf, mark)
                if f.whole:
                    out.append((mark, "FRAME", f))
                buf, collecting = [], False
    return out


def played(evs, marks, lay):
    """[(step or None, sorted note-ons)] across the windows named: each run of
    note-ons belongs to the playhead of the frame painted next."""
    out, pending = [], []
    for mark, kind, x in evs:
        if mark not in marks:
            continue
        if kind == "NOTE":
            if x[1] > 0:
                pending.append(x)
            continue
        _prob, _lamp, page = G.drum_page(x, lay, row_of(mark))
        heads = [n for n, c in page["step"].items() if c == G.PLAYHEAD]
        head = heads[0] if len(heads) == 1 else None
        if pending or not out or out[-1][0] != head:
            out.append((head, sorted(pending)))
            pending = []
    if pending:
        out.append(("unpainted", sorted(pending)))
    return out


def page_check(frame, lay, pat, track, lvl, head=None, last=16, rep=0, sig=(EVERY, ROW)):
    """-> None if the frame is the drum page for this pattern, track, level and
    last step (and playhead and repeat pad held, if given), else what differs.
    sig is a blue step every so many and the steps in a row: the seed's 7/8 makes
    rows of 7, each row's first step blue when off, and each row's eighth cell
    dark, which drum_page holds it to."""
    every, row = sig
    problem, lamp, page = G.drum_page(frame, lay, row)
    if problem:
        return problem
    if lamp != G.LAMPS[1]:
        return "lit mode lamp is %s, not page 2's %d" % (lamp, G.LAMPS[1])
    steps = 4 * row
    want = [G.step_color(pat[idx(track, s)], s, last, every) for s in range(1, steps + 1)]
    if head:
        want[head - 1] = G.PLAYHEAD
    got = [page["step"].get(s) for s in range(1, steps + 1)]
    if got != want:
        return "track %d's steps: want %s got %s" % (track, want, got)
    vel = {n: c == G.LEVEL_RGB[n - 1] for n, c in page["vel"].items()}
    if sorted(n for n, full in vel.items() if full) != [lvl] or len(vel) != 8:
        return "velocity buttons at full %s, want [%d]" % (
            sorted(n for n, full in vel.items() if full), lvl)
    pads = {n: c for n, c in page["pad"].items() if c != G.PAD_DIM}
    if pads != {track: G.PAD_ON}:
        return "pads lit %s, want pad %d red, the rest bright pink" % (pads, track)
    reps = {n: G.REP_HELD if n == rep else G.REP_DIM for n in range(1, 5)}
    if page["rep"] != reps:
        return "repeat pads %s, want %s" % (page["rep"], reps)
    return None


def main():
    opt = args()
    cap = A.require_capture(sys.stdin.read())
    lay = G.drum_layout()
    seed = read_key(opt.seed)
    if not A.check("the seed holds %s, 512 velocities, 16 last steps, randomnesses, volumes "
                   "and pitches, 7/8, sober, swing 50%% and the last step 16, and effects" % KEY, seed is not None and len(seed) == LINE,
                   "seed: %s" % seed):
        return A.report()

    order, by = A.windows(cap, "SEQ", len(WINDOWS))
    W = lambda k: by.get(k, [])
    evs = events(cap)
    frames = lambda k: [x for m, kind, x in evs if m == k and kind == "FRAME"]
    ons = lambda k: [tuple(int(v) for v in e[1]) for e in W(k)
                     if e[0] == "KITOUT" and e[1][1] > 0]
    puts = lambda k: [[int(float(v)) for v in e[1][3:]] for e in W(k)
                      if e[0] == "STATE" and e[1][:3] == ["put", "section", KEY]]
    raw = lambda k: [e[1] for e in W(k)
                     if e[0] == "DISP" and e[1] and e[1][0].startswith("pad-")]
    knob_rows = lambda k, name: [e[1] for e in W(k)
                                 if e[0] == "DISP" and e[1][:1] == [name]]
    kits = lambda k, kind: [[int(v) for v in e[1]] for e in W(k) if e[0] == kind]
    kitfx = lambda k: [e[1] for e in W(k) if e[0] == "KITFX"]

    # The pattern after each window, step by step through the driver's presses.
    pat = {"RESTORE": list(seed), "NINE": list(seed), "THREE": list(seed)}
    p = list(seed)
    for k, edits in (("ROW-PRESS", {(1, 7): 95}), ("ROW-DARK", {}), ("SEVEN", {}),
                     ("VEL-2", {}), ("STEPS-T1", {(1, 1): 32, (1, 5): 32}), ("PAD-2", {}),
                     ("STEP-T2", {(2, 1): 32}), ("VEL-6", {}), ("RULE-ON", {(2, 12): 95}),
                     ("RULE-SAME", {(2, 12): 0}), ("RULE-ON-AGAIN", {(2, 12): 95}),
                     ("VEL-2-AGAIN", {}), ("RULE-OTHER", {(2, 12): 0})):
        for (t, s), v in edits.items():
            p[idx(t, s)] = v
        pat[k] = list(p)
    final = pat["RULE-OTHER"]
    # The put at 3/4 holds that time signature; the pattern after it is the seed's 7/8 again.
    at34 = list(pat["ROW-PRESS"])
    at34[NUM], at34[NUM + 1] = 3, 4
    track = {"RESTORE": 1, "NINE": 1, "THREE": 1, "ROW-PRESS": 1, "ROW-DARK": 1, "SEVEN": 1,
             "VEL-2": 1, "STEPS-T1": 1}
    lvl = {"RESTORE": 6, "NINE": 6, "THREE": 6, "ROW-PRESS": 6, "ROW-DARK": 6, "SEVEN": 6,
           "VEL-2": 2, "STEPS-T1": 2, "PAD-2": 2, "STEP-T2": 2,
           "VEL-6": 6, "RULE-ON": 6, "RULE-SAME": 6, "RULE-ON-AGAIN": 6,
           "VEL-2-AGAIN": 2, "RULE-OTHER": 2}

    def page_in(k, t=None):
        fs = frames(k)
        if not fs:
            return "no frame in the window"
        return page_check(fs[-1], lay, pat[k], t or track.get(k, 2), lvl[k],
                          sig=SIGS.get(k, (EVERY, ROW)))

    print("\n--- before the restore ---")
    A.check("a pad plays at 300 ms, before anything is restored -- pad 1, the bottom-left, "
            "at 127 for a press at 90, and nothing else",
            ons("EARLY") == [(1, 127)], "note-ons: %s" % ons("EARLY"))

    print("\n--- the restore ---")
    A.check("⛔ the restored pattern is put straight back -- once, the seeded 711 exactly",
            puts("RESTORE") == [seed],
            "%d put(s) of %s; the first holds %s values" % (
                len(puts("RESTORE")), KEY, len(puts("RESTORE")[0]) if puts("RESTORE") else 0))
    prob = page_in("RESTORE")
    A.check("⛔ ... and the page shows it at its 7/8: rows of 7 steps, each row's first blue and "
            "its eighth cell dark, track 1's seeded steps, level 6 and pad 1 lit",
            prob is None, prob)
    want = [[t, seed[VOL + t - 1]] for t in range(1, 17)]
    A.check("⛔ ... and c_kit hears every track's volume, track 16's seeded %d dB among them"
            % seed[VOL + 15], kits("RESTORE", "KITVOL") == want and seed[VOL + 15] != 0,
            "KITVOL %s, want %s" % (kits("RESTORE", "KITVOL"), want))
    want = [[t, seed[PITCH + t - 1]] for t in range(1, 17)]
    A.check("⛔ ... and every track's pitch, track 3's seeded %+d semitones among them"
            % seed[PITCH + 2], kits("RESTORE", "KITPITCH") == want and seed[PITCH + 2] != 0,
            "KITPITCH %s, want %s" % (kits("RESTORE", "KITPITCH"), want))
    # c_kit was told every effect at its starting point at load, so the restore tells it the
    # seeded ones alone: track 2's mix, track 5's dotted quarter, six steps, and its level, track
    # 9's send and the reverb's size (scratch-gates.py's SEQ_FX).
    want = [["dist", "2", "40"], ["delay-time", "5", "6"], ["delay", "5", "30"],
            ["send", "9", "60"], ["size", "70"]]
    A.check("⛔ ... and the seeded effects, the ones that moved since load and no others: track 2's "
            "distortion, track 5's delay, track 9's send and the reverb's size",
            kitfx("RESTORE") == want, "KITFX %s, want %s" % (kitfx("RESTORE"), want))

    print("\n--- the time signature ---")
    sig = lambda k: [(l[NUM], l[NUM + 1]) for l in puts(k)]
    A.check("the top number up two over OSC, as the phone sends it, is put each step: 8/8, "
            "then 9/8", sig("NINE") == [(8, 8), (9, 8)], "time signatures put: %s" % sig("NINE"))
    prob = page_in("NINE")
    A.check("⛔ at 9/8 the rows are 8 steps and every 9th step is blue, wrapping across the rows: "
            "steps 1 and 10, the second row's second cell, under the last step, 16",
            prob is None, prob)
    A.check("down six and the bottom number down one: 3/4, put each step",
            len(sig("THREE")) == 7 and sig("THREE")[-2:] == [(3, 8), (3, 4)],
            "time signatures put: %s" % sig("THREE"))
    prob = page_in("THREE")
    A.check("⛔ at 3/4 the rows are 6 steps, every 3rd step blue, each row's first and fourth "
            "cells, and each row's last two cells dark", prob is None, prob)
    A.check("⛔ at 3/4 the second row's first cell is step 7: put with track 1's step 7 at 95",
            puts("ROW-PRESS") == [at34], "%d put(s); track 1's step 7 put as %s" % (
                len(puts("ROW-PRESS")),
                [l[idx(1, 7)] for l in puts("ROW-PRESS")]))
    prob = page_in("ROW-PRESS")
    A.check("... and the page lights it there", prob is None, prob)
    A.check("⛔ the top row's seventh cell, past a row of 6, does nothing: no put, no note",
            not puts("ROW-DARK") and not ons("ROW-DARK"),
            "puts %d, note-ons %s" % (len(puts("ROW-DARK")), ons("ROW-DARK")))
    A.check("back to 7/8, four up and the bottom number up one, put each step",
            len(sig("SEVEN")) == 5 and sig("SEVEN")[-1:] == [(7, 8)],
            "time signatures put: %s" % sig("SEVEN"))
    prob = page_in("SEVEN")
    A.check("... and the page is rows of 7 again", prob is None, prob)

    print("\n--- editing ---")
    prob = page_in("VEL-2")
    A.check("a velocity button selects its level -- level 2 lit, the steps as they were",
            prob is None and not puts("VEL-2"), prob or "puts: %d" % len(puts("VEL-2")))
    A.check("two step presses put the pattern with track 1's steps 1 and 5 at 32",
            puts("STEPS-T1")[-1:] == [pat["STEPS-T1"]] and len(puts("STEPS-T1")) == 2,
            "%d put(s)" % len(puts("STEPS-T1")))
    prob = page_in("STEPS-T1")
    A.check("... and the page lights them in 32's color beside the seed's", prob is None, prob)
    A.check("⛔ a drum pad plays NOW at full velocity -- pad 2 at 127 for a press at 90, once",
            ons("PAD-2") == [(2, 127)], "note-ons: %s" % ons("PAD-2"))
    prob = page_in("PAD-2")
    A.check("... and selects its track -- pad 2 lit, the steps shown are track 2's",
            prob is None and not puts("PAD-2"), prob or "puts: %d" % len(puts("PAD-2")))
    prob = page_in("STEP-T2")
    A.check("a step press edits the SELECTED track -- track 2's step 1, track 1 untouched",
            puts("STEP-T2") == [pat["STEP-T2"]] and prob is None,
            prob or "puts: %s" % len(puts("STEP-T2")))

    for k, what in (("RULE-ON", "an off step takes the selected velocity -- 95"),
                    ("RULE-SAME", "the selected velocity again turns it off -- 0"),
                    ("RULE-OTHER", "another velocity turns it off too -- 0, not 32")):
        prob = page_in(k)
        got = puts(k)[-1][idx(2, 12)] if puts(k) else None
        A.check("⛔ the step rule: %s" % what,
                puts(k)[-1:] == [pat[k]] and prob is None,
                prob or "track 2 step 12 put as %s, want %d" % (got, pat[k][idx(2, 12)]))

    quiet = [(k, ons(k)) for k in EDITS if k != "PAD-2" and ons(k)]
    A.check("no step or velocity press plays a note", not quiet, quiet)
    rows = [(k, raw(k)) for k in EDITS if raw(k)]
    A.check("⛔ no drum-page press draws a raw pad-NN row -- the grid is the feedback",
            not rows, rows)

    print("\n--- the free corner ---")
    A.check("the second row of the right 4x4 is not the drum page: no put and no note",
            not puts("FREE-ROW") and not ons("FREE-ROW"),
            "puts %d, note-ons %s" % (len(puts("FREE-ROW")), ons("FREE-ROW")))
    A.check("... and, unmapped, it draws nothing (Brendan, 2026-11-04) -- no pad-36 row",
            raw("FREE-ROW") == [], raw("FREE-ROW"))

    print("\n--- another page ---")
    A.check("⛔ on page 1, which held the drum page until 2026-11-04, a step pad is not "
            "the drum page: no put and no note",
            not puts("OTHER-PAGE") and not ons("OTHER-PAGE"),
            "puts %d, note-ons %s" % (len(puts("OTHER-PAGE")), ons("OTHER-PAGE")))
    A.check("... and, unmapped there, it draws nothing -- no pad-81 row",
            raw("OTHER-PAGE") == [], raw("OTHER-PAGE"))

    print("\n--- the transport ---")
    want = {s: sorted((t, final[idx(t, s)])
                      for t in range(1, 17) if final[idx(t, s)] > 0)
            for s in range(1, 17)}
    run = [r for r in played(evs, {"PLAY", "STOP"}, lay)
           if r[0] is not None or r[1]]
    A.check("⛔ PLAY starts at step 1 -- the first step heard is step 1's chord, "
            "pads 1 and 2 at 32", bool(run) and run[0] == (1, want[1]),
            "first: %s" % (run[:1],))
    bad = [(s, n, want.get(s)) for s, n in run if s not in want or n != want[s]]
    A.check("⛔ every step plays exactly its tracks -- pad and velocity, "
            "%d steps" % len(run), bool(run) and not bad, "wrong: %s" % bad[:4])
    # PLAY at 8420 ms and STOP at 11020, at 120 BPM: eight sixteenths a second
    # from about 10 ms in is 21 steps, with most of a step's margin either side.
    walk = [s for s, _n in run]
    A.check("⛔ sixteen steps to the bar, walking 1 to 16 and wrapping -- 21 in 2.6 s "
            "at 120 BPM", walk == list(range(1, 17)) + list(range(1, 6)),
            "steps %s" % walk)
    # A frame before the first step has no playhead yet; every other frame has
    # exactly one, over the pattern as it stands.
    shown, off = 0, []
    for f in frames("PLAY"):
        _p, _l, page = G.drum_page(f, lay, ROW)
        h = [n for n, c in page["step"].items() if c == G.PLAYHEAD]
        if h:
            shown += 1
            off.append(page_check(f, lay, final, 2, 2, h[0]))
    off = [o for o in off if o]
    A.check("the playhead is one green step over the pattern, in %d frames" % shown,
            shown >= 16 and not off, off[:2] or "only %d frames showed one" % shown)
    A.check("⛔ STOP stops it -- no note-on after STOP",
            not ons("STOPPED"), "note-ons: %s" % ons("STOPPED"))
    # STOP's own window ends with a frame painted after it; STOPPED may hold none.
    after = frames("STOP")[-1:] + frames("STOPPED")
    lit = [f for f in after if page_check(f, lay, final, 2, 2)]
    A.check("... and the playhead goes out", after and not lit,
            page_check(lit[0], lay, final, 2, 2) if lit else "no frame")
    print("\n--- the last step ---")
    rows = knob_rows("KNOB2-HELD", "last-step")
    A.check("⛔ knob 2 starts HELD at 16: at step 6 of 7/8's 28 it draws last-step 16 (6) and "
            "changes nothing", rows == [["last-step", "16", "(6)"]] and not puts("KNOB2-HELD"), rows)
    rows = knob_rows("LAST-3", "last-step")
    A.check("turned through 16 it is live -- last-step 17, then last-step 3",
            rows == [["last-step", "17"], ["last-step", "3"]], rows)
    prob = page_check(frames("LAST-3")[-1], lay, final, 2, 2, last=3) if frames("LAST-3") \
        else "no frame in the window"
    A.check("... the page darkens the empty steps past it, and the lit ones keep their color",
            prob is None, prob)
    got = [l[LAST] for l in puts("LAST-3")]
    A.check("... and it is saved, a section's, each time it changes: 17, then 3", got == [17, 3],
            "the global last step in the puts: %s" % got)
    again = [r for r in played(evs, {"REPLAY", "RE-SOON", "RE-STEP3", "RE-WALK", "PANIC"}, lay)
             if r[0] is not None]
    A.check("⛔ PLAY again starts at step 1, not where STOP left it",
            bool(again) and again[0] == (1, want[1]), "first: %s" % (again[:1],))
    walk = [s for s, _n in again]
    bad = [(s, n, want.get(s)) for s, n in again if n != want.get(s)]
    A.check("⛔ with the last step at 3 it walks 1 to 3 and wraps -- 1 2 3 1 2 in 0.6 s",
            walk == [1, 2, 3, 1, 2] and not bad, "steps %s, wrong %s" % (walk, bad[:3]))
    # On its boundary, not a twelfth of a step after it: PLAY's step 1 within two blocks, and
    # step 3 on the 250 ms it is due, to the block.
    A.check("⛔ PLAY's step 1 is heard at once -- its chord within 5 ms of PLAY",
            sorted(ons("REPLAY")) == want[1], "before 5 ms: %s, in the 240 after: %s"
            % (ons("REPLAY"), ons("RE-SOON")))
    A.check("⛔ ... and step 3 on its boundary, 250 ms after PLAY -- track 1's at 20, in the "
            "10 ms from 246, and nothing before it", want[3] == [(1, 20)] and
            sorted(ons("RE-STEP3")) == want[3] and not ons("RE-SOON"),
            "246 to 256: %s, 5 to 246: %s, after: %s"
            % (ons("RE-STEP3"), ons("RE-SOON"), ons("RE-WALK")[:2]))
    A.check("⛔ a panic stops it too -- no note-on after it",
            not ons("AFTER-PANIC"), "note-ons: %s" % ons("AFTER-PANIC"))

    print("\n--- knob 3, track 2's own last step ---")
    rows = knob_rows("KNOB3", "pad2-last")
    A.check("⛔ held at track 2's last step, 3, then turned through it -- 3 (6), then 1, then 6",
            rows == [["pad2-last", "3", "(6)"], ["pad2-last", "1"], ["pad2-last", "6"]], rows)
    got = [own(l, 2) for l in puts("KNOB3")]
    A.check("... and saved with the pattern, each time it changed -- 1, then 6", got == [1, 6],
            "track 2's own last step in the puts: %s" % got)
    prob = page_check(frames("KNOB3")[-1], lay, final, 2, 2, last=6) if frames("KNOB3") \
        else "no frame in the window"
    A.check("... and the page shows six steps, the rest dark", prob is None, prob)
    A.check("a press past the last step does nothing: no put, no note, no raw row",
            not puts("PAST-LAST") and not ons("PAST-LAST") and not raw("PAST-LAST"),
            "puts %d, note-ons %s, rows %s" % (len(puts("PAST-LAST")), ons("PAST-LAST"),
                                                raw("PAST-LAST")))

    print("\n--- the loops ---")
    # Every track loops on its own: the global last step is 3, track 2's is 6
    # and track 16's 24, as seeded. Steps k = 1, 2, ... from PLAY.
    lasts = {t: own(final, t) or 3 for t in range(1, 17)}
    lasts[2] = 6

    def tick(k):
        notes = sorted((t, final[idx(t, (k - 1) % lasts[t] + 1)])
                       for t in range(1, 17) if final[idx(t, (k - 1) % lasts[t] + 1)] > 0)
        return ((k - 1) % 6 + 1, notes)
    poly = [r for r in played(evs, {"POLY", "POLY-STOP"}, lay) if r[0] is not None]
    A.check("⛔ track 1 loops every 3 and track 2 every 6, the playhead track 2's -- "
            "the first nine steps", len(poly) >= 9 and poly[:9] == [tick(k) for k in range(1, 10)],
            "got %s, want %s" % (poly[:9], [tick(k) for k in range(1, 10)]))

    print("\n--- the drum screen's snap ---")
    A.check("snap, sent to u_net over OSC while stopped, waits: no put",
            not puts("SNAP"), "puts: %d" % len(puts("SNAP")))
    landed = puts("SNAP-PLAY")
    A.check("⛔ ... and lands at PLAY: every track on the global last step, saved",
            len(landed) == 1 and [own(landed[0], t) for t in range(1, 17)] == [0] * 16,
            "puts %s" % [[own(l, t) for t in range(1, 17)] for l in landed])
    snapped = [r for r in played(evs, {"SNAP-PLAY", "SNAP-STOP"}, lay) if r[0] is not None]
    A.check("... and track 2 then walks the global loop -- 1 2 3 1",
            [s for s, _n in snapped][:4] == [1, 2, 3, 1], "steps %s" % [s for s, _n in snapped])
    A.check("STOP stops it again", not ons("SWING"), "note-ons: %s" % ons("SWING"))

    # Each time the playhead moves, from the frames: [(window, step)].
    heads, last_head = [], None
    for mark, kind, x in evs:
        if kind != "FRAME":
            continue
        _p, _l, page = G.drum_page(x, lay, row_of(mark))
        h = [n for n, c in page["step"].items() if c == G.PLAYHEAD]
        h = h[0] if len(h) == 1 else None
        if h is not None and h != last_head:
            heads.append((mark, h))
        last_head = h
    moved = lambda *ks: [n for m, n in heads if m in ks]

    print("\n--- knob 4, swing ---")
    rows = knob_rows("SWING", "swing")
    A.check("⛔ knob 4 starts HELD at 50%: at 65% it draws swing 50 (65); turned down to 50%, "
            "its bottom, it is live, then swing 75 %",
            rows == [["swing", "50", "(65)"], ["swing", "50", "%"], ["swing", "75", "%"]], rows)
    got = [l[SWING] for l in puts("SWING")]
    A.check("... and it is saved, a section's, when it changes: 75 alone", got == [75],
            "the swing in the puts: %s" % got)
    A.check("⛔ at 75% step 2 waits three quarters of the pair: not painted by 190 ms, and "
            "painted by 260", moved("SW-PLAY", "SW-SOON", "SW-GAP") == [1] and moved("SW-LATE") == [2],
            "by window: %s" % [(m, n) for m, n in heads if m.startswith("SW-")])
    A.check("... and step 3 lands on the beat after it", moved("SW-ON") == [3],
            "SW-ON: %s" % moved("SW-ON"))
    A.check("⛔ PLAY's step 1 at once here too, early in a step, with threshold~ still to re-arm "
            "-- its chord within 5 ms", sorted(ons("SW-PLAY")) == want[1],
            "before 5 ms: %s, after: %s" % (ons("SW-PLAY"), ons("SW-SOON")[:2]))

    print("\n--- a repeat pad ---")
    A.check("PLAY walks 1 2 3 before the repeat pad", moved("REP-PLAY", "REP-PRESS") == [1, 2, 3],
            "steps %s" % moved("REP-PLAY", "REP-PRESS"))
    A.check("⛔ repeat pad 1 held: the playhead stays on 3 and track 1's step 3 plays on every "
            "step -- four times", moved("REP-HELD") == [] and
            ons("REP-HELD") == [(1, final[idx(1, 3)])] * 4,
            "steps %s, note-ons %s" % (moved("REP-HELD"), ons("REP-HELD")))
    A.check("⛔ let go, the loop goes on from where it would have been -- 2 then 3, not 1",
            moved("REP-OFF") == [2, 3], "steps %s" % moved("REP-OFF"))
    held = [G.drum_page(f, lay, ROW)[2]["rep"] for f in frames("REP-HELD")[-1:]]
    A.check("⛔ held, repeat pad 1 is bright purple and the other three dim",
            held == [{1: G.REP_HELD, 2: G.REP_DIM, 3: G.REP_DIM, 4: G.REP_DIM}], held)
    gone = [G.drum_page(f, lay, ROW)[2]["rep"] for f in frames("REP-OFF")[-1:]]
    A.check("... and let go, all four dim", gone == [{k: G.REP_DIM for k in range(1, 5)}], gone)

    print("\n--- the drum screen's pads ---")
    A.check("⛔ track 2's volume and pitch, sent over OSC as the phone sends them, go to c_kit "
            "for pad 2", kits("SOUND", "KITVOL") == [[2, -6]] and kits("SOUND", "KITPITCH") == [[2, 7]]
            and not ons("SOUND"),
            "KITVOL %s, KITPITCH %s, note-ons %s" % (kits("SOUND", "KITVOL"),
                                                     kits("SOUND", "KITPITCH"), ons("SOUND")))
    got = [(l[VOL + 1], l[PITCH + 1]) for l in puts("SOUND")]
    A.check("... and are saved with the pattern, each as it came", got == [(-6, 0), (-6, 7)],
            "track 2's volume and pitch in the puts: %s" % got)
    got = [l[RAND] for l in puts("RAND")] + [l[RAND] for l in puts("RA-STOP")]
    A.check("track 1's randomness, 100 and then 0 again, is saved", got == [100, 0],
            "track 1's randomness in the puts: %s" % got)
    # The global last step is 3 since LAST-3, and every track follows it since the snap.
    rand = [r for r in played(evs, {"RA-PLAY", "RA-STOP"}, lay) if r[0] is not None]
    t1 = [(s, sorted(v for p, v in n if p == 1)) for s, n in rand]
    rest = [(s, [(p, v) for p, v in n if p != 1]) for s, n in rand]
    written = [(s, [final[idx(1, s)]] if final[idx(1, s)] else []) for s, _n in rand]
    A.check("⛔ at 100, track 1 plays its coin, not its pattern: over %d steps not as written, "
            "and its step 3's 20, no level's, never" % len(rand),
            len(rand) >= 6 and t1 != written and not any(s == 3 and v == [20] for s, v in t1),
            "track 1 %s, written %s" % (t1, written))
    off = [v for _s, n in t1 for v in n if v not in LEVEL_VELS]
    A.check("... every hit it plays at one of the eight levels' velocities", not off,
            "off the levels: %s" % off)
    want = [(s, sorted((t, final[idx(t, s)]) for t in range(2, 17) if final[idx(t, s)] > 0))
            for s, _n in rand]
    A.check("⛔ ... and every other track plays as written beside it", rest == want,
            "got %s, want %s" % (rest, want))

    print("\n--- a repeat over random tracks ---")
    # Tracks 1 to 4 at full randomness, every step of theirs a coin, and repeat pad 2 held after
    # step 3 of the global loop of 3 (Brendan, 2026-11-05: a repeat plays exactly what was
    # played, what its randomness chose that time included).
    rr = [r for r in played(evs, {"RR-PLAY", "RR-PRESS", "RR-HELD", "RR-OFF"}, lay)
          if r[0] is not None]
    A.check("⛔ held, repeat pad 2 replays steps 2 3 2, each with exactly the hits and velocities "
            "its coins fell to when it was played", moved("RR-PLAY", "RR-PRESS") == [1, 2, 3]
            and moved("RR-HELD") == [2, 3, 2] and len(rr) >= 6
            and rr[3:6] == [rr[1], rr[2], rr[1]],
            "steps %s then %s, played %s" % (moved("RR-PLAY", "RR-PRESS"), moved("RR-HELD"), rr))
    A.check("⛔ let go, the loop goes on from where it would have been -- 1 then 2, not 3",
            moved("RR-OFF") == [1, 2], "steps %s" % moved("RR-OFF"))

    print("\n--- mute and solo ---")
    # Track 1 muted, then soloed as well, over OSC as the phone sends them (Brendan, 2026-11-05).
    # The global loop is 3 since LAST-3 and every track follows it since the snap; track 2 is
    # selected since PAD-2.
    flags = lambda l: (l[LINE:LINE + 16], l[LINE + 16:FLAGGED])
    one = [1] + [0] * 15
    got = puts("MUTE")
    A.check("⛔ mute 1 1, sent to u_net over OSC as the phone sends it, is put with the pattern: "
            "the line 743, track 1 muted and nothing soloed",
            [len(l) for l in got] == [FLAGGED] and flags(got[0]) == (one, [0] * 16),
            "puts of %s values, flags %s" % ([len(l) for l in got], [flags(l) for l in got]))
    pads = lambda k: (G.drum_page(frames(k)[-1], lay, ROW)[2]["pad"] if frames(k) else {})
    want = {n: G.PAD_DIM for n in range(1, 17)}
    want[1], want[2] = G.PAD_QUIET, G.PAD_ON
    A.check("⛔ ... and the Launchpad shows pad 1 dim pink, pad 2, selected, red, and the rest "
            "bright pink", pads("MUTE") == want, "pads %s" % pads("MUTE"))

    def steps_of(tracks, n=6):
        return [((k - 1) % 3 + 1, sorted((t, final[idx(t, (k - 1) % 3 + 1)]) for t in tracks
                                         if final[idx(t, (k - 1) % 3 + 1)] > 0))
                for k in range(1, n + 1)]
    muted = [r for r in played(evs, {"MU-PLAY", "MU-STOP"}, lay) if r[0] is not None]
    want = steps_of(range(2, 17))
    A.check("⛔ muted, track 1 plays nothing for six steps, and track 2 beside it plays its step 1 "
            "as written", muted[:6] == want and want[0][1] == [(2, 32)],
            "got %s, want %s" % (muted[:6], want))
    got = puts("SOLO")
    A.check("solo 1 1 is put: track 1 muted and soloed",
            [len(l) for l in got] == [FLAGGED] and flags(got[0]) == (one, one),
            "puts of %s values, flags %s" % ([len(l) for l in got], [flags(l) for l in got]))
    want = {n: G.PAD_QUIET for n in range(1, 17)}
    want[1], want[2] = G.PAD_DIM, G.PAD_ON_QUIET
    A.check("⛔ ... and the Launchpad shows pad 1 bright pink, since it plays, pad 2, selected and "
            "left out, dim red, and the rest dim pink", pads("SOLO") == want,
            "pads %s" % pads("SOLO"))
    solo = [r for r in played(evs, {"SO-PLAY", "SO-STOP"}, lay) if r[0] is not None]
    want = steps_of([1])
    A.check("⛔ soloed, track 1 plays though it is muted, the mutes ignored, and track 2 nothing: "
            "its steps 1 and 3", solo[:6] == want and want[0][1] == [(1, 32)]
            and want[2][1] == [(1, 20)], "got %s, want %s" % (solo[:6], want))

    print("\n--- a character ---")
    got = puts("CHAR")
    A.check("⛔ char 4 3, sent to u_net over OSC as the phone sends it, is put with the pattern: "
            "the line 759, track 4 fold after the mutes and solos, track 1 still muted and soloed",
            [len(l) for l in got] == [CHARRED] and got[0][FLAGGED:] == [1, 1, 1, 3] + [1] * 12
            and flags(got[0]) == (one, one),
            "puts of %s values, characters %s" % ([len(l) for l in got],
                                                  [l[FLAGGED:] for l in got]))
    A.check("⛔ ... and c_kit is told track 4's character, and nothing else",
            kitfx("CHAR") == [["char", "4", "3"]], "KITFX %s" % kitfx("CHAR"))

    print("\n--- the reverb's type ---")
    # gigaverb, 1, over OSC as the phone sends it (Brendan, 2026-11-05), after the character: the
    # line grows by the type alone, track 4 still fold and track 1 still muted and soloed.
    got = [(len(l), l[FLAGGED:CHARRED], l[TYPED - 1]) for l in puts("VTYPE")]
    A.check("⛔ verb-type 1, sent to u_net over OSC as the phone sends it, is put with the "
            "pattern: the line 760, gigaverb last, the characters before it as they were",
            got == [(TYPED, [1, 1, 1, 3] + [1] * 12, 1)], "length, characters and type: %s" % got)
    A.check("⛔ ... and goes to c_kit as verb-type 1, and nothing else does",
            kitfx("VTYPE") == [["verb-type", "1"]], "KITFX %s" % kitfx("VTYPE"))

    print("\n--- drunkenness ---")
    got = [l[DRUNK] for l in puts("DRUNK")]
    A.check("drunk 100, sent to u_net over OSC as the phone sends it, is saved", got == [100],
            "drunkenness in the puts: %s" % got)
    counts = [len(moved("DR-%d" % k)) for k in range(1, 97)]
    A.check("⛔ drunk, the steps leave the grid: sober, each of 96 windows a sixteenth "
            "wide holds one step", sum(counts) >= 24 and counts != [1] * 96,
            "steps per window: %s" % counts)
    # At the top every step strays, by up to two steps (Brendan, 2026-11-05):
    # simulated, 20 to 52 windows of the 96 hold one step; at a third straying
    # by up to one, as it was, 68 to 91.
    A.check("⛔ ... and at the top every step strays: at most 60 of the 96 windows hold "
            "exactly one", counts.count(1) <= 60,
            "%d hold one: %s" % (counts.count(1), counts))
    A.check("STOP stops it again", not ons("DRAG"), "note-ons: %s" % ons("DRAG"))

    print("\n--- a drag ---")
    # c_steps holds a change's put back up to 100 ms (ref/module/sequencer.md); every other
    # window is followed by sync, as u_song sends before it acts, but DRAG is not.
    got = [l[DRUNK] for l in puts("DRAG")]
    A.check("⛔ a drag, three drunkenness values over OSC 20 ms apart, is put once, the last, "
            "when c_steps' clock comes", got == [100], "drunkenness in the puts: %s" % got)

    print("\n--- the disk ---")
    draft = os.path.join(opt.state, "cut-it-song-draft.txt")
    disk = read_key(draft)
    with open(draft, encoding="utf-8") as fh:
        lines = [l for l in fh.read().splitlines() if l.split()[:1] == [KEY]]
    vol = list(seed[VOL:VOL + 16])
    pitch = list(seed[PITCH:PITCH + 16])
    vol[1], pitch[1] = -6, 7
    # the swing back at 50% (SW-STOP), the global last step at 3 since LAST-3, track 1 muted
    # and soloed since SOLO, track 4 fold since CHAR, and the reverb gigaverb since VTYPE
    snapped = (final[:CELLS] + [0] * 32 + vol + pitch + [7, 8, 100, 50, 3] + seed[FXLESS:]
               + one + one + [1, 1, 1, 3] + [1] * 12 + [1])
    A.check("⛔ the pattern reaches the song's draft as section 1's ONE drums line, the final "
            "760 exactly, its effects as seeded, track 1 muted and soloed, track 4 fold and the "
            "reverb gigaverb",
            disk == snapped and len(lines) == 1 and len(lines[0].split()) == TYPED + 1,
            "on disk: %s" % (disk if disk is None else "%d values" % len(disk)))

    errs = [e[1] for k in order for e in W(k) if e[0] == "ERR"
            and ("c_steps" in e[1] or "layout-miss" in e[1] or "g_grid" in e[1])]
    A.check("nothing on err from c_steps, the layout or the page", not errs, errs)
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
