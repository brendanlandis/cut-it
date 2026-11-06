#!/usr/bin/env python3
"""The voices' and the controls in play's analyzer -- ref/module/voices.md. Reads a capture on stdin.

    python3 test/gate/voices-assert.py [-v] --state <dir> < capture.txt

What each rule answers is u_voices_test.lua's and u_perform_test.lua's. Here, that the cords carry it:
a press through the map to the page on the mode bus, the voices to the song's draft and to the
engines, the phone's commands through u_net, a physical control in play through the map's route to
its destination and to the engine it belongs to, and a section's list to its start and to the Launchpad.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

TAG = "VOICES"
WINDOWS = ["LOADED", "LEFT-2", "LEFT-2-AGAIN", "LEFT-EMPTY", "RIGHT-5", "RIGHT-5-AGAIN", "AUX", "AUX-AGAIN",
           "SETUP", "SETUP-AGAIN", "METHOD", "TOO-MANY", "ON-PAGE", "PLAY", "PLAY-AGAIN", "STOP",
           "BACK-PERFORM", "ARM", "HEARD", "BIND", "BOUND", "MOVE", "ON-ROW-2", "ARM-2", "HEARD-2",
           "BIND-2", "ON-ROW-5", "ACTIVE-2", "ON-PERFORM", "PLAYED-2", "LAMP-2", "NEW", "SECTION-2",
           "HELD", "CAUGHT", "TAP", "SECTION-NONE", "FLUSHED"]
SEED = ["drums", "drums", "kit", "chords", "harmony", "strings", "melody", "melody", "fm"]
BLANK = ["-"] * 15


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def run_asserts(cap, state):
    order, by = A.windows(cap, TAG, len(WINDOWS))
    W = lambda k: by.get(k, [])
    pages = lambda k: [e[1] for e in W(k) if e[0] == "MODE"]
    states = lambda k: [e[1] for e in W(k) if e[0] == "STATE"]
    puts = lambda k, *head: [s for s in states(k) if s[:len(head)] == list(head)]
    tempos = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    errs = lambda k: [e[1] for e in W(k) if e[0] == "ERR"]
    frames = G.parse(cap.splitlines(), TAG)

    def last_frame(*marks):
        fs = [f for f in frames if f.whole and f.mark in marks]
        return fs[-1] if fs else None

    print("\n--- the song's voices, and the page ---")
    pre = W("PRE") + W("LOADED")
    seeds = [e[1] for e in pre if e[0] == "STATE" and e[1][:3] == ["put", "seed", "voices"]]
    A.check("⛔ a song with none is seeded, as a seed, once, with the song store's load",
            seeds == [["put", "seed", "voices"] + SEED + BLANK], seeds)
    A.check("⛔ ... and the page says so: the performance page",
            [e[1] for e in pre if e[0] == "MODE"] == [["perform"]],
            [e[1] for e in pre if e[0] == "MODE"])
    A.check("⛔ a left button, through the table: its method's page, once for a press and release",
            pages("LEFT-2") == [["harmony"]], pages("LEFT-2"))
    A.check("... and the page is saved in the auto file's key, its kind and row",
            puts("LEFT-2", "put", "auto", "page") == [["put", "auto", "page", "voice", "2"]],
            puts("LEFT-2", "put", "auto", "page"))
    A.check("⛔ the lit one again: the performance page", pages("LEFT-2-AGAIN") == [["perform"]],
            pages("LEFT-2-AGAIN"))
    A.check("⛔ a left button with no voice does nothing", not pages("LEFT-EMPTY"), pages("LEFT-EMPTY"))
    A.check("⛔ an unused right button: a new voice the song holds, and its setup page",
            pages("RIGHT-5") == [["sound"]] and puts("RIGHT-5", "put", "song", "voices") ==
            [["put", "song", "voices"] + SEED + ["-"] * 3 + ["voice_5", "keys", "sine"] + ["-"] * 9],
            "%s, %s" % (pages("RIGHT-5"), puts("RIGHT-5", "put", "song", "voices")))
    A.check("the lit one again: back", pages("RIGHT-5-AGAIN") == [["perform"]], pages("RIGHT-5-AGAIN"))
    A.check("⛔ aux, through the table: the songs page, and aux again back",
            (pages("AUX"), pages("AUX-AGAIN")) == ([["songs"]], [["perform"]]),
            "%s %s" % (pages("AUX"), pages("AUX-AGAIN")))
    A.check("⛔ Setup: the diagnostics page, and Setup again back",
            (pages("SETUP"), pages("SETUP-AGAIN")) == ([["diag"]], [["perform"]]),
            "%s %s" % (pages("SETUP"), pages("SETUP-AGAIN")))

    print("\n--- from the phone ---")
    v = puts("METHOD", "put", "song", "voices")
    A.check("⛔ a voice's method and name, through u_net: row 5 a harmony voice, second_chords",
            v[-1:] == [["put", "song", "voices"] + SEED + ["-"] * 3 + ["second_chords", "harmony", "sine"]
                       + ["-"] * 9], v)
    A.check("⛔ a third harmony voice and a second drum voice warn, and change nothing",
            [e for e in errs("TOO-MANY") if e[:2] == ["warn", "u_voices"]]
            == [["warn", "u_voices", "too-many-harmony"], ["warn", "u_voices", "too-many-drums"]]
            and not puts("TOO-MANY", "put", "song", "voices"), errs("TOO-MANY"))

    print("\n--- PLAY ---")
    A.check("⛔ PLAY, on a voice's page: the performance page", pages("PLAY") == [["perform"]], pages("PLAY"))
    A.check("⛔ a start while it runs is no PLAY: the page stays on a voice's",
            pages("PLAY-AGAIN") == [["harmony"]], pages("PLAY-AGAIN"))

    print("\n--- a control into play ---")
    A.check("⛔ REC, a control heard and a physical control: nothing moves as it's taken",
            not tempos("BIND"), tempos("BIND"))
    A.check("... the control heard moved in its own way: knob 1 through 120, 103 BPM",
            any(abs(t - 103) < 1.5 for t in tempos("HEARD")), tempos("HEARD"))
    bound = puts("BOUND", "put", "section", "perform") + puts("BIND", "put", "section", "perform")
    A.check("⛔ the section holds it: slider-1, its address and row, at where it is",
            bound and bound[-1][3:7] == ["slider-1", "tempo", "0", "0"]
            and abs(float(bound[-1][7]) - 64 / 127) < 0.001, bound)
    A.check("⛔ moved, through the map's route, it sets the tempo: the top of its range, 250",
            tempos("MOVE") == [250.0], tempos("MOVE"))

    print("\n--- a generator's control, and the two engines ---")
    # A roll is a save, once its chords have rolled: what's put is under the engine's own key.
    melody = lambda *ks: [s[2] for k in ks for s in puts(k, "put", "section") if s[2] in ("melody", "melody-2")]
    A.check("⛔ a pad on row 5's harmony page is heard by the second engine alone: melody-2's part changes",
            "melody-2" in melody("ACTIVE-2") and "melody" not in melody("ACTIVE-2"), melody("ACTIVE-2"))
    A.check("⛔ a button in play rolls row 2's engine from the performance page, by the name of its engine",
            "melody" in melody("PLAYED-2") and "melody-2" not in melody("PLAYED-2"), melody("PLAYED-2"))
    A.check("⛔ a Launchpad bottom-row button is the same button on the performance page",
            "melody" in melody("LAMP-2") and "melody-2" not in melody("LAMP-2"), melody("LAMP-2"))

    print("\n--- the Launchpad's columns and lights ---")
    f = last_frame("BIND", "BOUND")
    # On the performance page with slider-1 bound at 64 of 127, just over half: five of eight.
    A.check("the frame to read is the performance page", f is not None)
    if f:
        A.check("⛔ a fader in play, on its column: its level from the bottom, green up, live",
                [f.color(10 * r + 1) for r in range(1, 7)] == [(0, 127, 32), (0, 127, 32), (0, 127, 32),
                                                                (64, 127, 16), (127, 110, 0), 0],
                [f.color(10 * r + 1) for r in range(1, 7)])
    f = last_frame("PLAYED-2", "LAMP-2")
    if f:
        A.check("⛔ a button in play lights in its voice's color, row 2's cyan: dim off, bright on",
                f.color(101) in (G.VOICE_DIM[1], G.VOICE_FULL[1]), f.color(101))

    print("\n--- a new section ---")
    start = [s for s in states("SECTION-2") if s[:2] == ["restore", "perform"]]
    A.check("⛔ a new section copies the list, and starting says it",
            len(start) == 1 and "slider-1" in start[0] and "btn-a-1" in start[0], start)
    f = last_frame("SECTION-2")
    if f:
        A.check("⛔ ... and its column shows it waiting, dimmer", f.color(11) == (0, 31, 8), f.color(11))
    A.check("⛔ the fader's first move after it is held: nothing moves", not tempos("HELD"), tempos("HELD"))
    A.check("⛔ turned through its value, it's caught", tempos("CAUGHT") == [250.0], tempos("CAUGHT"))
    A.check("⛔ a tap on its column sets it too, row 4 of 8: 145 BPM", tempos("TAP") == [145.0], tempos("TAP"))

    print("\n--- what the song holds ---")
    path = os.path.join(state, "cut-it-song-draft.txt")
    lines = open(path).read().splitlines() if os.path.exists(path) else []
    head = lines[1].split() if len(lines) > 1 else []
    A.check("⛔ the song's voices, between its name and its first section, as the phone left them",
            head[:1] == ["voices"] and "second_chords" in head, lines[:2])
    perform = [ln.split() for ln in lines if ln.split()[:1] == ["perform"]]
    A.check("⛔ and each section's list, the two of them", len(perform) == 2 and all("slider-1" in p for p in perform),
            perform)
    other = [e for k in order if k != "TOO-MANY" for e in errs(k) if e[:1] == ["fail"]]
    A.check("nothing fails on err", not other, other)


if __name__ == "__main__":
    state = arg("--state")
    if not state:
        sys.exit("usage: voices-assert.py [-v] --state <dir> < capture.txt")
    run_asserts(A.require_capture(sys.stdin.read()), state)
    sys.exit(1 if A.report() else 0)
