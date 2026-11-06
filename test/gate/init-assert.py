#!/usr/bin/env python3
"""The boot sequence's analyzer -- ref/module/boot.md. Reads a capture on stdin.

It asserts orders and counts, never the stage timings, which are guesses with
evidence (item 266): the sequence, the MIDI gating sent twice, and the restore
landing after the layers that receive it exist.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The number of windows init-assert-drive-gen.py's SEQ opens.
MARKS = 5

# ref/module/boot.md, "The stage sequence", as the screen sees it: the one
# thing every stage touches.
STAGES = ["modal booting", "modal wiring", "modal launchpad", "modal-off"]

# What the gate seeds into the two state files. The restore replays manual
# first: the trigger's right outlet fires first.
SEEDED = [["restore", "init-mprobe", "7"], ["restore", "init-probe", "42"]]
# What the playing section holds at a fresh load, each part's put since load: the keys u_song's
# load restores, sorted (ref/module/songs.md).
SECTION_PARTS = ["drums", "programs", "synth", "tempo", "velocity"]

_STAGE = re.compile(r"^DISP:\s+(modal booting|modal wiring|modal launchpad"
                    r"|modal-off)\s*$")


def run_asserts(cap):
    lines = [ln.strip() for ln in cap.splitlines()]
    order, by = A.windows(cap, "INIT", MARKS)
    W = lambda k: by.get(k, [])
    kind = lambda k, lab: [v for lb, v in W(k) if lb == lab]

    def first_index(pred):
        return next((i for i, ln in enumerate(lines) if pred(ln)), None)

    # ---- the sequence, read off the one bus every stage touches ----------
    print("--- the stage sequence ---")
    stages = [m.group(1) for m in (_STAGE.match(ln) for ln in lines) if m]
    A.check("⛔ every stage reports, once, in order",
            stages == STAGES,
            "the screen saw %s\n            wanted %s" % (stages, STAGES))

    # The boot left v0.3-ready in a footer, and u_tempo the BPM after it, until
    # 2026-11-04: nothing at rest is drawn now but the output's levels.
    status = [ln for ln in lines if ln.startswith("DISP: status")]
    A.check("⛔ the boot leaves nothing in a footer: no status on disp at all",
            not status, "disp carried %s" % status)

    # ---- mother's MIDI mapping is shut off twice --------------------------
    # mother's binary pushes its own midiInGate 1 about half a second in,
    # overwriting the loadbang send (ref/module/boot.md).
    print("\n--- mother's own MIDI mapping, shut off twice ---")
    gate_in = [v for k in ("PRE",) + tuple(order) for v in kind(k, "MIDIINGATE")]
    A.check("⛔ midiInGate 0 is sent TWICE", gate_in == [["0"], ["0"]],
            "saw %s. One is not enough: mother's binary overwrites the loadbang "
            "copy about half a second in" % gate_in)
    A.check("⛔ ...one at loadbang and one LATER, not two at once",
            len(kind("PRE", "MIDIINGATE")) == 1
            and len(kind("PRE", "MIDIINGATE")) != len(gate_in),
            "%d of the %d landed before the first window. Two sends in the same "
            "instant close the same window twice and leave mother's push "
            "uncovered" % (len(kind("PRE", "MIDIINGATE")), len(gate_in)))
    # One message box feeds both gates, so midiOutGate goes twice too.
    gate_out = [v for k in ("PRE",) + tuple(order) for v in kind(k, "MIDIOUTGATE")]
    A.check("⛔ midiOutGate 0 goes TWICE as well -- one message box feeds both",
            gate_out == [["0"], ["0"]],
            "saw %s. The two sends share a message box, so a count that differs "
            "from midiInGate's means one of them has been re-wired" % gate_out)

    # ---- the five load-time scripts --------------------------------------
    # The invocation, not the effect: what they do needs the device, and
    # ref/module/boot.md says so.
    print("\n--- the five shell scripts, once each, at load ---")
    shell = [ln.split()[2] for ln in lines if ln.startswith("SHELL: sh ")]
    want = ["codec-gain.sh", "logroll.sh", "phone-ip.sh", "state-dir.sh",
            "wire.sh"]
    A.check("⛔ every one of the five is invoked, exactly once, per load",
            sorted(shell) == want,
            "the shell stub saw %s, wanted one each of %s. Running one per event "
            "rather than per load is the failure this ordering prevents"
            % (sorted(shell), want))
    # wire.sh runs after `modal wiring` reaches the screen: at loadbang ALSA is
    # not up yet.
    i_wire = first_index(lambda ln: ln.startswith("SHELL: sh wire.sh"))
    i_wiring = first_index(lambda ln: ln == "DISP: modal wiring")
    i_lp_stage = first_index(lambda ln: ln == "DISP: modal launchpad")
    A.check("⛔ wire.sh runs INSIDE the wiring stage, not at loadbang",
            None not in (i_wire, i_wiring, i_lp_stage)
            and i_wiring < i_wire < i_lp_stage,
            "`modal wiring` at line %s, wire.sh at line %s, `modal launchpad` at "
            "line %s. loadbang fires before ALSA exists, so wiring there goes "
            "nowhere -- item 266" % (i_wiring, i_wire, i_lp_stage))

    # ---- outlet 1: the launchpad stage -----------------------------------
    # The outlet is on no bus, but m_launchpad's Programmer Mode SysEx is.
    print("\n--- outlet 1: when the Launchpad is initialized ---")
    i_lp = first_index(lambda ln: ln == "DISP: modal launchpad")
    i_sysex = first_index(lambda ln: ln.startswith("MIDIOUT: 240 "))
    A.check("the Launchpad was initialized at all", i_sysex is not None,
            "no SysEx anywhere -- outlet 1 never fired, or it fired into nothing")
    A.check("⛔ ...only AFTER the launchpad stage is reached",
            i_lp is not None and i_sysex is not None and i_lp < i_sysex,
            "the first SysEx is at line %s and the stage is at line %s. Initializing "
            "before ALSA is up is what the whole timed sequence exists to avoid"
            % (i_sysex, i_lp))

    # ---- outlet 2: the restore, and where it sits -------------------------
    print("\n--- outlet 2: restoring the saved state ---")
    # Filtered to `restore`: u_map puts its own mode on the same bus at load.
    restores = [v for k in ("PRE",) + tuple(order) for v in kind(k, "STATE")
                if v[:1] == ["restore"]]
    # The same bang loads the song store after u_state, through u_root's trigger, and its
    # first section starts: every part it holds, in the keys' order (ref/module/songs.md).
    seeded = [v for v in restores if v[1:2] in ([s[1]] for s in SEEDED)]
    A.check("⛔ the restore replays every saved line, manual first",
            seeded == SEEDED,
            "the state bus carried %s, wanted %s" % (seeded, SEEDED))
    song = [v[1] for v in restores if v not in SEEDED]
    # What the song holds for its sections first, voices before the rest, each said though it holds none;
    # then a section with no controls in play says so, and that its tweaks snap back.
    want = ["voices", "patches", "sounds", "kit", "perform", "tweaks"] + SECTION_PARTS
    A.check("⛔ ...and then the song store's first section starts: every part, in order",
            song == want and restores[:len(SEEDED)] == SEEDED,
            "after u_state's: %s, wanted %s after %s" % (song, want, SEEDED))
    i_restore = first_index(lambda ln: ln.startswith("STATE: restore "))
    i_off = first_index(lambda ln: ln == "DISP: modal-off")
    A.check("...after the launchpad stage, so the layers exist to receive it",
            i_lp is not None and i_restore is not None and i_lp < i_restore,
            "restore at line %s, launchpad stage at line %s" % (i_restore, i_lp))
    A.check("⛔ ...and BEFORE modal-off -- the screen settles after the state does",
            i_restore is not None and i_off is not None and i_restore < i_off,
            "restore at line %s, modal-off at line %s. The restore is the right "
            "outlet of that stage's trigger and fires first of the three"
            % (i_restore, i_off))

    # ---- and the two outlets are not interchangeable ----------------------
    # Outlets are numbered by x position, so dragging the restore's outlet left
    # swaps them silently: both inlets take a bare bang. The stage name reaches
    # disp before either outlet fires, so only SysEx-before-restore catches it.
    A.check("⛔ the Launchpad is initialized BEFORE the state is restored",
            None not in (i_sysex, i_restore) and i_sysex < i_restore,
            "SysEx at line %s, restore at line %s. Swapped, the instrument still "
            "boots and still restores -- both inlets take a bare bang -- so the "
            "only symptom is a restore that publishes into a Launchpad which has "
            "not been initialized yet" % (i_sysex, i_restore))

    # The whole timeline at once: the checks above give better messages, this
    # one leaves no gaps between them.
    timeline = [
        ("modal booting", first_index(lambda ln: ln == "DISP: modal booting")),
        ("modal wiring", i_wiring),
        ("wire.sh", i_wire),
        ("modal launchpad", i_lp),
        ("Launchpad SysEx", i_sysex),
        ("state restore", i_restore),
        ("modal-off", i_off),
    ]
    idx = [i for _, i in timeline]
    A.check("⛔ the whole boot, in one order, with nothing out of place",
            None not in idx and idx == sorted(idx),
            "the run went %s" % [n for n, _ in sorted(timeline,
                                                      key=lambda t: (t[1] is None, t[1]))])

    # ---- and then it stops -------------------------------------------------
    # The last stage is modal-off at 3.5 s, so a stage still arriving at 7 s is a
    # sequence that never settled.
    print("\n--- and then the sequence is over ---")
    A.check("no boot stage arrives after the sequence has settled",
            not [v for v in kind("QUIET", "DISP") if v[:1] in (["modal"], ["modal-off"])],
            "still reporting stages at 7 s: %s" % kind("QUIET", "DISP"))

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
