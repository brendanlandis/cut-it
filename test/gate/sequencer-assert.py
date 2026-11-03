#!/usr/bin/env python3
"""The sequencer's analyser -- ref/module/sequencer.md. Reads a capture on stdin.

    sequencer-assert.py --seed SEED --state DIR [-v]  < capture

It asserts on what leaves the patch: the 404's notes, the grid's frames, the
state bus and the file u_state writes. Nothing inside c_steps is read.

  the restore    the seeded pattern comes back, is put straight back, and shows
  editing        a velocity, steps on two tracks, a pad that plays and selects,
                 the step rule's three cases, nothing on the free row, and nothing
                 at all in another mode
  the transport  every step plays exactly its tracks, from step 1, on PLAY and
                 on PLAY again; STOP and panic stop it
  the disk       the pattern reaches cut-it-auto.txt as one line

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

KEY = "section-1-drums"
BANK_A = 33
# The 404's pad map (ref/device/sp404.md): track n plays pad n of bank A.
PAD_NOTE = [48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39]
WINDOWS = ["EARLY", "RESTORE", "VEL-2", "STEPS-T1", "PAD-2", "STEP-T2", "VEL-6",
           "RULE-ON", "RULE-SAME", "RULE-ON-AGAIN", "VEL-2-AGAIN", "RULE-OTHER",
           "FREE-ROW", "MODE-2", "OTHER-MODE", "MODE-1", "PLAY", "STOP", "STOPPED",
           "REPLAY", "PANIC", "AFTER-PANIC", "DONE"]
EDITS = ["VEL-2", "STEPS-T1", "PAD-2", "STEP-T2", "VEL-6", "RULE-ON", "RULE-SAME",
         "RULE-ON-AGAIN", "VEL-2-AGAIN", "RULE-OTHER"]

MARK = re.compile(r"^SEQ:\s+MARK\s+(\S+)$")
NOTE = re.compile(r"^NOTEOUT:\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)$")


def level(n):
    """A velocity button's velocity: 127n/8, rounded."""
    return int(127 * n / 8 + 0.5)


def idx(track, step):
    return (track - 1) * 16 + (step - 1)


def args():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("-v", action="store_true")
    return p.parse_args()


def read_key(path):
    """The section-1-drums line of a state file, as ints, or None."""
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
                if f.is_lighting and len(buf) == G.FRAME_LEN:
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
        _prob, _lamp, page = G.drum_page(x, lay)
        heads = [n for n, c in page["step"].items() if c == G.PLAYHEAD]
        head = heads[0] if len(heads) == 1 else None
        if pending or not out or out[-1][0] != head:
            out.append((head, sorted(pending)))
            pending = []
    if pending:
        out.append(("unpainted", sorted(pending)))
    return out


def page_check(frame, lay, pat, track, lvl, head=None):
    """-> None if the frame is the drum page for this pattern, track and level
    (and playhead, if given), else what differs."""
    problem, lamp, page = G.drum_page(frame, lay)
    if problem:
        return problem
    if lamp != G.LAMPS[0]:
        return "lit mode lamp is %s, not mode 1's %d" % (lamp, G.LAMPS[0])
    want = [G.step_color(pat[idx(track, s)]) for s in range(1, 17)]
    if head:
        want[head - 1] = G.PLAYHEAD
    got = [page["step"].get(s) for s in range(1, 17)]
    if got != want:
        return "track %d's steps: want %s got %s" % (track, want, got)
    lit = lambda role: sorted(n for n, c in page[role].items() if c == G.PICKED)
    if lit("vel") != [lvl]:
        return "velocity buttons lit %s, want [%d]" % (lit("vel"), lvl)
    if lit("pad") != [track]:
        return "pads lit %s, want [%d]" % (lit("pad"), track)
    return None


def main():
    opt = args()
    cap = A.require_capture(sys.stdin.read())
    lay = G.drum_layout()
    seed = read_key(opt.seed)
    if not A.check("the seed holds %s and 256 velocities" % KEY,
                   seed is not None and len(seed) == 256, "seed: %s" % seed):
        return A.report()

    order, by = A.windows(cap, "SEQ", len(WINDOWS))
    W = lambda k: by.get(k, [])
    evs = events(cap)
    frames = lambda k: [x for m, kind, x in evs if m == k and kind == "FRAME"]
    ons = lambda k: [tuple(int(v) for v in e[1]) for e in W(k)
                     if e[0] == "NOTEOUT" and e[1][1] > 0]
    puts = lambda k: [[int(float(v)) for v in e[1][3:]] for e in W(k)
                      if e[0] == "STATE" and e[1][:3] == ["put", "auto", KEY]]
    raw = lambda k: [e[1] for e in W(k)
                     if e[0] == "DISP" and e[1] and e[1][0].startswith("pad-")]

    # The pattern after each window, step by step through the driver's presses.
    pat = {"RESTORE": list(seed)}
    p = list(seed)
    for k, edits in (("VEL-2", {}), ("STEPS-T1", {(1, 1): 32, (1, 5): 32}), ("PAD-2", {}),
                     ("STEP-T2", {(2, 1): 32}), ("VEL-6", {}), ("RULE-ON", {(2, 13): 95}),
                     ("RULE-SAME", {(2, 13): 0}), ("RULE-ON-AGAIN", {(2, 13): 95}),
                     ("VEL-2-AGAIN", {}), ("RULE-OTHER", {(2, 13): 0})):
        for (t, s), v in edits.items():
            p[idx(t, s)] = v
        pat[k] = list(p)
    final = pat["RULE-OTHER"]
    track = {"RESTORE": 1, "VEL-2": 1, "STEPS-T1": 1}
    lvl = {"RESTORE": 6, "VEL-2": 2, "STEPS-T1": 2, "PAD-2": 2, "STEP-T2": 2,
           "VEL-6": 6, "RULE-ON": 6, "RULE-SAME": 6, "RULE-ON-AGAIN": 6,
           "VEL-2-AGAIN": 2, "RULE-OTHER": 2}

    def page_in(k, t=None):
        fs = frames(k)
        if not fs:
            return "no frame in the window"
        return page_check(fs[-1], lay, pat[k], t or track.get(k, 2), lvl[k])

    print("\n--- before the restore ---")
    A.check("a pad plays at 300 ms, before anything is restored -- 48 90 on "
            "channel %d and nothing else" % BANK_A,
            ons("EARLY") == [(48, 90, BANK_A)], "note-ons: %s" % ons("EARLY"))

    print("\n--- the restore ---")
    A.check("⛔ the restored pattern is put straight back -- once, the seeded 256 exactly",
            puts("RESTORE") == [seed],
            "%d put(s) of %s; the first holds %s values" % (
                len(puts("RESTORE")), KEY, len(puts("RESTORE")[0]) if puts("RESTORE") else 0))
    prob = page_in("RESTORE")
    A.check("... and the page shows it: track 1's seeded steps, level 6 and pad 1 lit",
            prob is None, prob)

    print("\n--- editing ---")
    prob = page_in("VEL-2")
    A.check("a velocity button selects its level -- level 2 lit, the steps as they were",
            prob is None and not puts("VEL-2"), prob or "puts: %d" % len(puts("VEL-2")))
    A.check("two step presses put the pattern with track 1's steps 1 and 5 at 32",
            puts("STEPS-T1")[-1:] == [pat["STEPS-T1"]] and len(puts("STEPS-T1")) == 2,
            "%d put(s)" % len(puts("STEPS-T1")))
    prob = page_in("STEPS-T1")
    A.check("... and the page lights them in 32's color beside the seed's", prob is None, prob)
    A.check("⛔ a drum pad plays NOW at its own velocity -- 49 90 on channel %d, once"
            % BANK_A, ons("PAD-2") == [(49, 90, BANK_A)], "note-ons: %s" % ons("PAD-2"))
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
        got = puts(k)[-1][idx(2, 13)] if puts(k) else None
        A.check("⛔ the step rule: %s" % what,
                puts(k)[-1:] == [pat[k]] and prob is None,
                prob or "track 2 step 13 put as %s, want %d" % (got, pat[k][idx(2, 13)]))

    quiet = [(k, ons(k)) for k in EDITS if k != "PAD-2" and ons(k)]
    A.check("no step or velocity press plays a note", not quiet, quiet)
    rows = [(k, raw(k)) for k in EDITS if raw(k)]
    A.check("⛔ no drum-page press draws a raw pad-NN row -- the grid is the feedback",
            not rows, rows)

    print("\n--- the free row ---")
    A.check("the row under the velocity buttons is not the drum page: no put and no note",
            not puts("FREE-ROW") and not ons("FREE-ROW"),
            "puts %d, note-ons %s" % (len(puts("FREE-ROW")), ons("FREE-ROW")))
    A.check("... and it names itself, as an unmapped control does -- pad-54 100",
            raw("FREE-ROW") == [["pad-54", "100"]], raw("FREE-ROW"))

    print("\n--- another mode ---")
    A.check("in mode 2 a step pad is not the drum page: no put and no note",
            not puts("OTHER-MODE") and not ons("OTHER-MODE"),
            "puts %d, note-ons %s" % (len(puts("OTHER-MODE")), ons("OTHER-MODE")))
    A.check("... and it names itself, as an unmapped control does -- pad-81 100",
            raw("OTHER-MODE") == [["pad-81", "100"]], raw("OTHER-MODE"))

    print("\n--- the transport ---")
    want = {s: sorted((PAD_NOTE[t - 1], final[idx(t, s)], BANK_A)
                      for t in range(1, 17) if final[idx(t, s)] > 0)
            for s in range(1, 17)}
    run = [r for r in played(evs, {"PLAY", "STOP"}, lay)
           if r[0] is not None or r[1]]
    A.check("⛔ PLAY starts at step 1 -- the first step heard is step 1's chord, "
            "pads 1 and 2 at 32", bool(run) and run[0] == (1, want[1]),
            "first: %s" % (run[:1],))
    bad = [(s, n, want.get(s)) for s, n in run if s not in want or n != want[s]]
    A.check("⛔ every step plays exactly its tracks -- channel, note and velocity, "
            "%d steps" % len(run), bool(run) and not bad, "wrong: %s" % bad[:4])
    # PLAY at 7220 ms and STOP at 9820, at 120 BPM: eight sixteenths a second
    # from about 10 ms in is 21 steps, with most of a step's margin either side.
    walk = [s for s, _n in run]
    A.check("⛔ sixteen steps to the bar, walking 1 to 16 and wrapping -- 21 in 2.6 s "
            "at 120 BPM", walk == list(range(1, 17)) + list(range(1, 6)),
            "steps %s" % walk)
    # A frame before the first step has no playhead yet; every other frame has
    # exactly one, over the pattern as it stands.
    shown, off = 0, []
    for f in frames("PLAY"):
        _p, _l, page = G.drum_page(f, lay)
        h = [n for n, c in page["step"].items() if c == G.PLAYHEAD]
        if h:
            shown += 1
            off.append(page_check(f, lay, final, 2, 2, h[0]))
    off = [o for o in off if o]
    A.check("the playhead is one white step over the pattern, in %d frames" % shown,
            shown >= 16 and not off, off[:2] or "only %d frames showed one" % shown)
    A.check("⛔ STOP stops it -- no note-on after STOP",
            not ons("STOPPED"), "note-ons: %s" % ons("STOPPED"))
    lit = [f for f in frames("STOPPED") if page_check(f, lay, final, 2, 2)]
    A.check("... and the playhead goes out", frames("STOPPED") and not lit,
            page_check(lit[0], lay, final, 2, 2) if lit else "no frame")
    again = [r for r in played(evs, {"REPLAY", "PANIC"}, lay) if r[0] is not None]
    A.check("⛔ PLAY again starts at step 1, not where STOP left it",
            bool(again) and again[0] == (1, want[1]), "first: %s" % (again[:1],))
    A.check("⛔ a panic stops it too -- no note-on after it",
            not ons("AFTER-PANIC") and not ons("DONE"),
            "note-ons: %s" % (ons("AFTER-PANIC") + ons("DONE")))

    print("\n--- the disk ---")
    disk = read_key(os.path.join(opt.state, "cut-it-auto.txt"))
    with open(os.path.join(opt.state, "cut-it-auto.txt"), encoding="utf-8") as fh:
        lines = [l for l in fh.read().splitlines() if l.split()[:1] == [KEY]]
    A.check("⛔ %s reaches cut-it-auto.txt as ONE line, the final 256 exactly" % KEY,
            disk == final and len(lines) == 1 and len(lines[0].split()) == 257,
            "on disk: %s" % (disk if disk is None else "%d values" % len(disk)))

    errs = [e[1] for k in order for e in W(k) if e[0] == "ERR"
            and ("c_steps" in e[1] or "layout-miss" in e[1] or "g_grid" in e[1])]
    A.check("nothing on err from c_steps, the layout or the page", not errs, errs)
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
