#!/usr/bin/env python3
"""The song store's analyzer -- ref/module/songs.md. Reads the first run's capture on stdin.

    song-assert.py [-v] --seed SONG --state DIR --after DIR --reload CAPTURE
                   --legacy DIR --legacy-seed LINE  < capture

It asserts on what leaves the patch and what lands on disk: the state bus, where a section starting
restores its parts; the tempo bus; the program changes, as the synths' layers send them; the
Launchpad's frames, for the top row and the save and revert lamps; and the song's two files.

  the play run    a song of three sections saved, booted on page 2: section 1 starts at load;
                  stopped, a top-row button starts its section at once, programs and all; a
                  change lights save and revert; revert and save; playing, a section with a
                  length hands over by itself on its own step 1; a section pressed is queued,
                  blinks, and starts when the pattern comes round; the arrows; a dark button
  the reload      what the first run left: the draft comes back, unsaved; revert
  the legacy run  a state directory from before sections: the auto file's pattern and synth
                  become section 1's, and the auto file lets the old keys go
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

TAG = "SONG"
WINDOWS = ["LOADED", "PRESS-STOPPED", "EDIT", "REVERT", "EDIT-2", "SAVE", "PLAY", "HANDOVER",
           "QUEUE", "AT-LOOP", "STOP", "FORWARD", "BACK", "EMPTY-BUTTON", "FINAL-EDIT", "FLUSHED"]
RELOAD_WINDOWS = ["LOADED", "REVERT", "FLUSHED"]
FM, STRINGS = 49, 33            # the Volca's and the Streichfett's Pd channels, args 5 and 4
PARTS = ["drums", "programs", "synth", "tempo", "velocity"]
# The top row's eight, as g_grid paints them: dark, an arrow (palette 1), a section, the one
# playing.
DARK, ARROW, SEC, ON = 0, 1, G.SECTION_DIM, G.SECTION_ON


def args():
    p = argparse.ArgumentParser()
    for k in ("--seed", "--state", "--after", "--reload", "--legacy", "--legacy-seed"):
        p.add_argument(k, required=True)
    p.add_argument("-v", action="store_true")
    return p.parse_args()


def song(path):
    """A song file as [(name, length, {key: [atoms]})], or None."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except IOError:
        return None
    out = []
    for ln in lines:
        w = ln.split()
        if not w:
            continue
        if w[0] == "section":
            out.append((" ".join(w[3:]), int(w[2]), {}))
        elif w[0] != "song" and out:
            out[-1][2][w[0]] = w[1:]
    return out


def restores(evs):
    return [e[1][1:] for e in evs if e[0] == "STATE" and e[1][:1] == ["restore"]]


def section_keys(evs):
    """The keys of the restores a section starting sent: the song's, never u_state's mode."""
    return [r[0] for r in restores(evs) if r[0] in PARTS]


def tempos(evs):
    return [float(e[1][0]) for e in evs if e[0] == "TEMPO" and e[1]]


def programs(evs):
    return [(int(e[1][0]), int(e[1][1])) for e in evs if e[0] == "PGMOUT"]


def errs(evs):
    return [e[1] for e in evs if e[0] == "ERR"]


def edges(frames, k):
    """The edge cells of the last whole frame painted by the end of window k."""
    upto = WINDOWS[:WINDOWS.index(k) + 1] if k in WINDOWS else [k]
    last = [f for f in frames if f.mark in ["(none)"] + upto and f.whole]
    return G.edges(last[-1]) if last else {}


def top(e):
    return [e.get(i) for i in G.TOP]


def lamps(e):
    return (e.get(G.SAVE), e.get(G.REVERT))


def main():
    opt = args()
    cap = A.require_capture(sys.stdin.read())
    seed = song(opt.seed)
    A.check("the seed is a song of three sections: intro, verse of two loops, chorus",
            seed and [(n, l) for n, l, _p in seed] == [("intro", 0), ("verse", 2), ("chorus", 0)],
            seed and [(n, l) for n, l, _p in seed])
    order, by = A.windows(cap, TAG, len(WINDOWS))
    W = lambda k: by.get(k, [])
    frames = G.parse(cap.splitlines(), TAG)
    lay = G.drum_layout()

    print("\n--- the load: section 1 starts ---")
    A.check("⛔ at load, after u_state's restore, section 1 starts: every part it holds restored, "
            "in the keys' order", section_keys(W("PRE")) == PARTS,
            "the song's restores before the first window: %s" % section_keys(W("PRE")))
    A.check("... intro's tempo, 200, reaches the tempo bus", tempos(W("PRE"))[-1:] == [200.0],
            tempos(W("PRE")))
    A.check("... and its programs, none, send nothing", not programs(W("PRE")), programs(W("PRE")))
    e = edges(frames, "LOADED")
    A.check("⛔ the top row: section 1 playing on button 3, 2 and 3 lit as sections, the forward "
            "arrow lit and the back arrow dark", top(e) == [DARK, ARROW, ON, SEC, SEC, DARK, DARK,
                                                            DARK], top(e))
    A.check("⛔ ... and save and revert dark: the song is as saved", lamps(e) == (0, 0), lamps(e))
    page2 = [f for f in frames if f.whole and f.mark in WINDOWS]
    bad = [f for f in page2 if G.drum_page(f, lay)[0]]
    A.check("every frame from the first window is the drum page with the edges' colors, nothing "
            "else lit", page2 and not bad, bad and G.drum_page(bad[0], lay)[0])

    print("\n--- stopped, a section starts at once ---")
    A.check("⛔ button 4, stopped: verse starts at once, every part restored",
            section_keys(W("PRESS-STOPPED")) == PARTS, section_keys(W("PRESS-STOPPED")))
    got = [r for r in restores(W("PRESS-STOPPED")) if r[0] in ("synth", "velocity")]
    A.check("... its synth strings and velocity off among them", got == [["synth", "strings"],
                                                                         ["velocity", "off"]], got)
    A.check("... its tempo, 240, on the bus", tempos(W("PRESS-STOPPED")) == [240.0],
            tempos(W("PRESS-STOPPED")))
    A.check("⛔ its programs go out as it starts: the Volca's 20 and the Streichfett's 5, the "
            "Volca first, once each", programs(W("PRESS-STOPPED")) == [(21, FM), (6, STRINGS)],
            "%s (pgmout is given the number plus one)" % programs(W("PRESS-STOPPED")))
    e = edges(frames, "PRESS-STOPPED")
    A.check("... and the top row shows it: verse playing on button 4, both arrows lit",
            top(e) == [ARROW, ARROW, SEC, ON, SEC, DARK, DARK, DARK], top(e))

    print("\n--- save and revert ---")
    A.check("⛔ a change, the tempo 150, lights save red and revert gray",
            lamps(edges(frames, "EDIT")) == (G.SAVE_ON, G.REVERT_ON), lamps(edges(frames, "EDIT")))
    A.check("⛔ revert: verse as saved, at once: its tempo 240 and its programs again",
            tempos(W("REVERT")) == [240.0] and programs(W("REVERT")) == [(21, FM), (6, STRINGS)],
            "tempo %s, programs %s" % (tempos(W("REVERT")), programs(W("REVERT"))))
    A.check("... and the lamps go dark, and the log says so",
            lamps(edges(frames, "REVERT")) == (0, 0)
            and ["info", "u_song", "reverted"] in errs(W("REVERT")),
            "%s, err %s" % (lamps(edges(frames, "REVERT")), errs(W("REVERT"))))
    A.check("another change, the tempo 160, lights them again",
            lamps(edges(frames, "EDIT-2")) == (G.SAVE_ON, G.REVERT_ON),
            lamps(edges(frames, "EDIT-2")))
    A.check("⛔ save: the lamps go dark, nothing restarts, and the log says so",
            lamps(edges(frames, "SAVE")) == (0, 0) and not restores(W("SAVE"))
            and ["info", "u_song", "saved"] in errs(W("SAVE")),
            "%s, restores %s, err %s" % (lamps(edges(frames, "SAVE")), restores(W("SAVE")),
                                         errs(W("SAVE"))))

    print("\n--- playing: a length, and a queue ---")
    A.check("PLAY: verse plays its first loop, and nothing starts", not section_keys(W("PLAY")),
            section_keys(W("PLAY")))
    A.check("⛔ its length played, two loops, chorus starts by itself",
            section_keys(W("HANDOVER")) == PARTS and tempos(W("HANDOVER")) == [180.0],
            "restores %s, tempo %s" % (section_keys(W("HANDOVER")), tempos(W("HANDOVER"))))
    A.check("... its program, the Volca's 7, and none for the Streichfett",
            programs(W("HANDOVER")) == [(8, FM)], programs(W("HANDOVER")))
    # The playhead, track 1's step on the drum page, in each frame of the window once chorus's
    # lamp is lit: verse's last step, 8, where it handed over, then chorus's own step 1.
    heads = []
    for f in frames:
        if f.mark != "HANDOVER" or not f.whole or f.color(95) != ON:
            continue
        steps = G.drum_page(f, lay)[2]["step"]
        h = next((s for s, c in steps.items() if c == G.PLAYHEAD), None)
        if h is not None and (not heads or heads[-1] != h):
            heads.append(h)
    walk = heads[1:] if heads[:1] == [8] else heads
    A.check("⛔ ... on its own step 1: the playhead goes from verse's last step to 1, not on to 9",
            walk[:3] == [1, 2, 3], "playhead steps once chorus is lit: %s" % heads[:6])
    e = edges(frames, "HANDOVER")
    A.check("... and the top row shows chorus playing", top(e) == [ARROW, DARK, SEC, SEC, ON,
                                                                  DARK, DARK, DARK], top(e))
    A.check("⛔ button 3 while playing queues intro: nothing starts while chorus's loop plays on",
            not section_keys(W("QUEUE")), section_keys(W("QUEUE")))
    q = [f.color(93) for f in frames if f.mark == "QUEUE" and f.whole]
    p = [f.color(95) for f in frames if f.mark == "QUEUE" and f.whole]
    A.check("⛔ ... and blinks: button 3 full and dark by turns, on the beat, never dim",
            len(q) >= 3 and set(q) == {ON, DARK}, q)
    A.check("... while button 5, chorus, stays lit, playing", p and set(p) == {ON}, set(p))
    A.check("⛔ intro starts when the pattern comes round to its step 1: its parts and its tempo",
            section_keys(W("AT-LOOP")) == PARTS and tempos(W("AT-LOOP")) == [200.0],
            "restores %s, tempo %s" % (section_keys(W("AT-LOOP")), tempos(W("AT-LOOP"))))
    e = edges(frames, "AT-LOOP")
    A.check("... and lit solid, chorus dim", top(e) == [DARK, ARROW, ON, SEC, SEC, DARK, DARK, DARK],
            top(e))

    print("\n--- stopped again: the arrows, and a button with no section ---")
    A.check("forward, stopped: verse at once, at its saved tempo 160",
            section_keys(W("FORWARD")) == PARTS and tempos(W("FORWARD")) == [160.0],
            "restores %s, tempo %s" % (section_keys(W("FORWARD")), tempos(W("FORWARD"))))
    A.check("back: intro again, 200", tempos(W("BACK")) == [200.0], tempos(W("BACK")))
    A.check("button 7, which shows no section, does nothing",
            not restores(W("EMPTY-BUTTON")) and not errs(W("EMPTY-BUTTON")),
            "restores %s, err %s" % (restores(W("EMPTY-BUTTON")), errs(W("EMPTY-BUTTON"))))
    A.check("the last change, the tempo 170, lights the lamps",
            lamps(edges(frames, "FINAL-EDIT")) == (G.SAVE_ON, G.REVERT_ON),
            lamps(edges(frames, "FINAL-EDIT")))
    other = [x for k in order for x in errs(W(k)) if x[:1] != ["info"]]
    A.check("nothing else on err", not other, other)

    print("\n--- the files ---")
    saved = song(os.path.join(opt.after, "cut-it-song.txt"))
    draft = song(os.path.join(opt.after, "cut-it-song-draft.txt"))
    want = [(n, l, dict(ps)) for n, l, ps in seed]
    want[1][2]["tempo"] = ["160"]
    A.check("⛔ the saved song is the save's: the three sections, verse at 160",
            saved == want, "%s" % [(n, l, ps.get("tempo")) for n, l, ps in saved or []])
    want_d = [(n, l, dict(ps)) for n, l, ps in want]
    want_d[0][2]["tempo"] = ["170"]
    A.check("⛔ the draft, written as it changes, holds the change after it: intro at 170",
            draft == want_d, "%s" % [(n, l, ps.get("tempo")) for n, l, ps in draft or []])

    print("\n--- a reload ---")
    cap2 = open(opt.reload, encoding="utf-8", errors="replace").read()
    order2, by2 = A.parse(cap2, TAG)
    A.check("the reload's driver reached every window", order2 == RELOAD_WINDOWS, order2)
    R2 = lambda k: by2.get(k, [])
    frames2 = G.parse(cap2.splitlines(), TAG)
    A.check("⛔ the draft comes back: intro starts at load at its tempo 170, not the saved 200",
            section_keys(R2("PRE")) == PARTS and tempos(R2("PRE"))[-1:] == [170.0],
            "restores %s, tempo %s" % (section_keys(R2("PRE")), tempos(R2("PRE"))))

    def last_edges(k):
        fs = [f for f in frames2 if f.whole and f.mark in ("(none)", "PRE", "LOADED", k)]
        return G.edges(fs[-1]) if fs else {}
    A.check("⛔ ... unsaved: save and revert lit from the load",
            lamps(last_edges("LOADED")) == (G.SAVE_ON, G.REVERT_ON), lamps(last_edges("LOADED")))
    A.check("revert: the saved 200, the lamps dark", tempos(R2("REVERT")) == [200.0]
            and lamps(G.edges([f for f in frames2 if f.whole][-1])) == (0, 0),
            "tempo %s" % tempos(R2("REVERT")))
    after = song(os.path.join(opt.state, "cut-it-song-draft.txt"))
    A.check("... and the draft on disk is the saved song again", after == want and
            song(os.path.join(opt.state, "cut-it-song.txt")) == want,
            [(n, ps.get("tempo")) for n, _l, ps in after or []])

    print("\n--- a first load after the update, from the auto file ---")
    legacy = open(opt.legacy_seed, encoding="utf-8").read().split()
    first = song(os.path.join(opt.legacy, "cut-it-song.txt"))
    fdraft = song(os.path.join(opt.legacy, "cut-it-song-draft.txt"))
    one = first[0][2] if first and len(first) == 1 else {}
    A.check("⛔ the pattern the auto file held is section 1's drums, the swing and the global last "
            "step in force after it: 579 and 50 and 16",
            one.get("drums") == legacy[1:] + ["50", "16"],
            "section 1's drums: %s" % (len(one.get("drums") or []) or one.get("drums")))
    A.check("... and the synth choice and the velocity switch it held: strings, off",
            one.get("synth") == ["strings"] and one.get("velocity") == ["off"],
            "synth %s, velocity %s" % (one.get("synth"), one.get("velocity")))
    A.check("... saved as the song, one section, the draft the same", first and len(first) == 1
            and fdraft == first, "%d section(s)" % len(first or []))
    auto = [ln.split()[0] for ln in open(os.path.join(opt.legacy, "cut-it-auto.txt"))
            if ln.split()]
    A.check("... and the auto file lets the old keys go: mode alone", auto == ["mode"], auto)
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
