#!/usr/bin/env python3
"""The synths' analyzer -- ref/module/synths.md. Reads a capture on stdin.

    python3 test/gate/synths-assert.py [-v] --state <dir> < capture.txt

The nanoKEY plays the chosen synth and only that one, whichever page is up; a switch while a
key is held releases the key on the synth that started it; a page-3 pad and the phone's
command both switch; the phone's velocity switch, off, sends every note-on at 127 on either
synth and leaves releases at 0; the choice and the switch come back from the state store and go
into it; and panic reaches the Streichfett's channel. The run boots with strings and velocity
off saved, so a default left in force by a restore that never landed would play the Volca at the
key's own velocity and fail the first window.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

FM, STRINGS = 49, 33            # the Volca's and the Streichfett's Pd channels, args 5 and 4
WINDOWS = 20


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def run_asserts(cap, state):
    print("\n=== c_synth, m_nanokey and m_streich ===")
    order, by = A.windows(cap, "SYNTHS", WINDOWS)
    W = lambda k: by.get(k, [])
    notes = lambda k: [tuple(int(x) for x in e[1]) for e in W(k) if e[0] == "NOTEOUT"]
    puts = lambda k: [e[1] for e in W(k) if e[0] == "STATE" and e[1][:3] == ["put", "auto", "synth"]]
    vputs = lambda k: [e[1] for e in W(k) if e[0] == "STATE"
                       and e[1][:3] == ["put", "auto", "velocity"]]
    errs = lambda k: [e[1] for e in W(k) if e[0] == "ERR"]

    pre = [e[1] for e in W("PRE") if e[0] == "STATE" and "synth" in e[1][:3]]
    restored = ["restore", "synth", "strings"] in pre
    A.check("the saved choice is restored at load, and put straight back",
            restored and pre.index(["restore", "synth", "strings"]) < len(pre) - 1
            and pre[-1] == ["put", "auto", "synth", "strings"],
            "the state bus before the first window: %s" % pre)

    vpre = [e[1] for e in W("PRE") if e[0] == "STATE" and "velocity" in e[1][:3]]
    A.check("the saved velocity switch, off, is restored at load, and put straight back",
            ["restore", "velocity", "off"] in vpre
            and vpre.index(["restore", "velocity", "off"]) < len(vpre) - 1
            and vpre[-1] == ["put", "auto", "velocity", "off"],
            "the state bus before the first window: %s" % vpre)
    A.check("⛔ strings and velocity off came back: the first key plays the Streichfett alone, "
            "at 127", notes("KEY-RESTORED") == [(60, 127, STRINGS)],
            "wanted noteout 60 127 %d, got %s -- 60 100 is the velocity switch left on, and "
            "channel %d fm, the boot defaults, left in force by a restore that never reached "
            "c_synth" % (STRINGS, notes("KEY-RESTORED"), FM))
    A.check("... and its release goes there", notes("KEY-RESTORED-OFF") == [(60, 0, STRINGS)],
            notes("KEY-RESTORED-OFF"))

    A.check("the phone's velocity on is put, and plays nothing",
            vputs("PHONE-VEL-ON") == [["put", "auto", "velocity", "on"]]
            and not notes("PHONE-VEL-ON") and not errs("PHONE-VEL-ON"),
            "state %s noteout %s err %s" % (vputs("PHONE-VEL-ON"), notes("PHONE-VEL-ON"),
                                            errs("PHONE-VEL-ON")))
    A.check("⛔ FM's page-3 pad chooses fm, once: a press, and its release says nothing",
            puts("PAD-FM") == [["put", "auto", "synth", "fm"]] and not errs("PAD-FM"),
            "state %s err %s" % (puts("PAD-FM"), errs("PAD-FM")))
    A.check("a key on any channel of the nanoKEY's port, 50, plays the Volca alone",
            notes("KEY-FM") == [(62, 100, FM)], notes("KEY-FM"))
    A.check("... and its release", notes("KEY-FM-OFF") == [(62, 0, FM)], notes("KEY-FM-OFF"))

    A.check("a key held on fm sounds on fm", notes("HOLD") == [(64, 100, FM)], notes("HOLD"))
    A.check("⛔ the phone's synth strings switches, and plays nothing itself",
            puts("PHONE-STRINGS") == [["put", "auto", "synth", "strings"]]
            and not notes("PHONE-STRINGS"),
            "state %s noteout %s -- without it the phone's buttons do nothing"
            % (puts("PHONE-STRINGS"), notes("PHONE-STRINGS")))
    A.check("⛔ the held key releases on the synth that started it, fm, not the one chosen now",
            notes("HOLD-OFF") == [(64, 0, FM)],
            "wanted noteout 64 0 %d alone, got %s -- a release sent to the synth chosen now "
            "leaves the Volca's note sounding until a panic" % (FM, notes("HOLD-OFF")))
    A.check("a key pressed after the switch plays the Streichfett, and releases there",
            notes("KEY-STRINGS") == [(65, 100, STRINGS), (65, 0, STRINGS)], notes("KEY-STRINGS"))

    A.check("the phone's velocity off is put", vputs("PHONE-VEL-OFF") ==
            [["put", "auto", "velocity", "off"]] and not notes("PHONE-VEL-OFF"),
            "state %s noteout %s" % (vputs("PHONE-VEL-OFF"), notes("PHONE-VEL-OFF")))
    A.check("strings' pad with strings chosen changes nothing and says nothing",
            not puts("PAD-SAME") and not notes("PAD-SAME") and not errs("PAD-SAME"),
            W("PAD-SAME"))
    A.check("⛔ only a press chooses: FM down, STRINGS down, FM up, STRINGS up ends on strings",
            puts("TWO-PADS") == [["put", "auto", "synth", "fm"],
                                 ["put", "auto", "synth", "strings"]],
            "wanted fm then strings, got %s -- a release that chose would put fm last, and a "
            "pad let go late would undo the one pressed after it" % puts("TWO-PADS"))
    A.check("⛔ notes on the nano's port, the Streichfett's own, port 3's last channel and a "
            "fifth port's first play nothing", not notes("OTHER-PORTS"), notes("OTHER-PORTS"))

    A.check("on page 1 the synth pads mean nothing", not puts("PAD-OFF-PAGE"),
            puts("PAD-OFF-PAGE"))
    A.check("⛔ ... and the nanoKEY still plays the choice there, a soft key at 127 with the "
            "velocity switch off, and its release at 0",
            notes("KEY-OFF-PAGE") == [(69, 127, STRINGS), (69, 0, STRINGS)],
            "wanted 69 127 then 69 0 on %d, got %s -- 69 20 is the key's own velocity, the "
            "switch ignored" % (STRINGS, notes("KEY-OFF-PAGE")))

    A.check("a synth c_synth does not know, from the phone, is fail c_synth bad-synth, and a "
            "velocity setting bad-velocity",
            errs("BAD") == [["fail", "c_synth", "bad-synth"], ["fail", "c_synth", "bad-velocity"]]
            and not puts("BAD") and not vputs("BAD"),
            "err %s state %s %s" % (errs("BAD"), puts("BAD"), vputs("BAD")))

    pan = [e[1] for e in W("PANIC") if e[0] == "CTLOUT" and e[1][-1] == STRINGS]
    A.check("⛔ panic sends All Notes Off -- CC 123 -- on the Streichfett's channel",
            pan == [[0.0, 123.0, float(STRINGS)]],
            "wanted one ctlout 0 123 %d, got %s. The note path bypasses makenote, so this is "
            "the only thing that can silence a stuck note" % (STRINGS, pan))

    stray = [n for k in order for n in notes(k) if n[2] not in (FM, STRINGS)]
    A.check("nothing leaves either synth's layer on another channel", not stray, stray)
    other = [e for k in order if k != "BAD" for e in errs(k)]
    A.check("nothing else reaches err", not other, other)

    path = os.path.join(state, "cut-it-auto.txt")
    lines = open(path).read().splitlines() if os.path.exists(path) else []
    saved = [ln.split() for ln in lines if ln.split()[:1] == ["synth"]]
    A.check("⛔ the choice is in the state file, so a reload brings it back: synth strings",
            saved == [["synth", "strings"]], "%s holds %s" % (path, lines))
    vsaved = [ln.split() for ln in lines if ln.split()[:1] == ["velocity"]]
    A.check("⛔ and the velocity switch, so a reload brings it back: velocity off",
            vsaved == [["velocity", "off"]], "%s holds %s" % (path, lines))


if __name__ == "__main__":
    state = arg("--state")
    if not state:
        sys.exit("usage: synths-assert.py [-v] --state <dir> < capture.txt")
    run_asserts(A.require_capture(sys.stdin.read()), state)
    sys.exit(1 if A.report() else 0)
