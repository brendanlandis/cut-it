#!/usr/bin/env python3
"""The boot sequence's analyser -- ref/module/boot.md. Reads a capture on stdin.

⛔ ref/module/boot.md USED TO DECLARE `Gate: test/run.sh` -- the whole runner --
which is the only page in the repository that named something that is not a gate.
It was honest about there being no per-module coverage and dishonest about what
was covering it: every gate loads the patch, so every gate proves the boot does
not ERROR, and not one of them proved it happens in the right ORDER.

⛔ THE STRONG ASSERTIONS HERE ARE ORDERS AND COUNTS, NOT MILLISECONDS. The stage
timings are guesses with evidence rather than measurements (item 266), and a gate
that pinned 1500 and 3000 would go red the first time somebody lengthened a delay
for a real reason -- which is a test asserting the implementation back at itself.
What must hold is the sequence, that the MIDI gating really is sent twice, and
that the restore lands after the layers that receive it exist.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS init-assert-drive-gen.py's SEQ OPENS.
MARKS = 5

# ref/module/boot.md, "The stage sequence". The screen is the only thing every
# stage touches, so this is the sequence in the form a test can see.
STAGES = ["modal booting", "modal wiring", "modal launchpad", "modal-off",
          "status v0.3-ready"]

# What the gate seeds into the two state files, one line each. The restore
# replays manual first and auto second -- the trigger's right outlet fires first.
SEEDED = [["restore", "init-mprobe", "7"], ["restore", "init-probe", "42"]]

_STAGE = re.compile(r"^DISP:\s+(modal booting|modal wiring|modal launchpad"
                    r"|modal-off|status v0\.3-ready)\s*$")


def run_asserts(cap):
    lines = [ln.strip() for ln in cap.splitlines()]
    order, by = A.windows(cap, "INIT", MARKS)
    W = lambda k: by.get(k, [])
    kind = lambda k, lab: [v for lb, v in W(k) if lb == lab]

    def first_index(pred):
        return next((i for i, ln in enumerate(lines) if pred(ln)), None)

    # ---- ⛔ THE SEQUENCE, READ OFF THE ONE BUS EVERY STAGE TOUCHES --------
    # Each stage reports to disp as it is REACHED. Nothing here is acknowledged
    # by any device, so a stage name on screen means the sequence got that far --
    # not that the hardware answered. Boot sticking on one name still tells you
    # where to look, and that is only true if the names arrive in order.
    print("--- the stage sequence ---")
    stages = [m.group(1) for m in (_STAGE.match(ln) for ln in lines) if m]
    A.check("⛔ every stage reports, once, in order",
            stages == STAGES,
            "the screen saw %s\n            wanted %s" % (stages, STAGES))

    # ⚠️ AND THE VERSION STRING IS PART OF IT. ref/module/boot.md and
    # ref/module/display.md both said v0.2-ready while the patch had been sending
    # v0.3-ready for a release; nothing compared them until this line existed.
    A.check("the footer's version string is the one the patch actually sends",
            "DISP: status v0.3-ready" in lines,
            "no `status v0.3-ready` anywhere in the capture")

    # ---- ⛔ MOTHER'S MIDI MAPPING IS SHUT OFF TWICE -----------------------
    # mother.pd runs [ctlin 21]..[ctlin 26] OMNI and loads a new PATCH on any
    # program change -- so the nanoKONTROL's top row pressed AUX and slammed knob
    # 1 from 500 BPM to 10. The mother BINARY then pushes its own midiInGate 1
    # about half a second after the patch loads, which overwrites the value sent
    # at loadbang. Hence twice, and the second is the one that works.
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
    # ⚠️ midiOutGate GOES TWICE TOO, and ref/module/boot.md said it went once
    # until this check was written. One message box feeds BOTH sends, and that
    # box is banged at loadbang and again at 2000 ms -- so the second copy of
    # each is what survives. Nothing was wrong with the patch; the table was
    # describing a two-send chain as if only one of its two consumers were on it.
    gate_out = [v for k in ("PRE",) + tuple(order) for v in kind(k, "MIDIOUTGATE")]
    A.check("⛔ midiOutGate 0 goes TWICE as well -- one message box feeds both",
            gate_out == [["0"], ["0"]],
            "saw %s. The two sends share a message box, so a count that differs "
            "from midiInGate's means one of them has been re-wired" % gate_out)

    # ---- ⛔ ALL FOUR .sh SCRIPTS, AND THIS GATE IS THE ONLY THING THAT SEES
    # THEM. Every one runs through [shell] exactly once per patch load, never per
    # event, and until this stub existed nothing anywhere under test/ executed or
    # even observed one -- phone-ip.sh had zero references of any kind.
    #
    # ⚠️ IT ASSERTS THE INVOCATION, NOT THE EFFECT. What these scripts DO cannot
    # be tested on a Mac: [shell] does not exist here and the real one wires ALSA,
    # rolls a log on /sdcard and reads a dnsmasq lease file. That half is declared
    # uncovered on ref/module/boot.md, honestly, with what it would need. This
    # half -- that the boot invokes each of them once -- is real coverage and it
    # is the half that catches a script dropped from the sequence.
    print("\n--- the four shell scripts, once each, at load ---")
    shell = [ln.split()[2] for ln in lines if ln.startswith("SHELL: sh ")]
    want = ["logroll.sh", "phone-ip.sh", "state-dir.sh", "wire.sh"]
    A.check("⛔ every one of the four is invoked, exactly once, per load",
            sorted(shell) == want,
            "the shell stub saw %s, wanted one each of %s. Running one per event "
            "rather than per load is the failure this ordering prevents"
            % (sorted(shell), want))
    # ⛔ wire.sh RUNS IN THE `modal wiring` STAGE, AFTER THE SCREEN SAYS SO, and
    # ref/module/boot.md's table said 0 ms until this check was written -- while
    # the paragraph directly under that table said 1500, citing the feasibility
    # probe the number came from. The patch is right and it is the sensible
    # order: loadbang fires before ALSA is up, so wiring at 0 ms would go
    # nowhere, and a stage name means the sequence REACHED it, not that the
    # hardware answered.
    i_wire = first_index(lambda ln: ln.startswith("SHELL: sh wire.sh"))
    i_wiring = first_index(lambda ln: ln == "DISP: modal wiring")
    i_lp_stage = first_index(lambda ln: ln == "DISP: modal launchpad")
    A.check("⛔ wire.sh runs INSIDE the wiring stage, not at loadbang",
            None not in (i_wire, i_wiring, i_lp_stage)
            and i_wiring < i_wire < i_lp_stage,
            "`modal wiring` at line %s, wire.sh at line %s, `modal launchpad` at "
            "line %s. loadbang fires before ALSA exists, so wiring there goes "
            "nowhere -- item 266" % (i_wiring, i_wire, i_lp_stage))

    # ---- ⛔ OUTLET 1: THE LAUNCHPAD STAGE ---------------------------------
    # u_init decides WHEN the Launchpad is initialised and no longer knows HOW,
    # so the outlet itself is invisible from a bus -- but its consequence is not.
    # m_launchpad sends Programmer Mode when it fires, and that reaches [midiout].
    print("\n--- outlet 1: when the Launchpad is initialised ---")
    i_lp = first_index(lambda ln: ln == "DISP: modal launchpad")
    i_sysex = first_index(lambda ln: ln.startswith("MIDIOUT: 240 "))
    A.check("the Launchpad was initialised at all", i_sysex is not None,
            "no SysEx anywhere -- outlet 1 never fired, or it fired into nothing")
    A.check("⛔ ...only AFTER the launchpad stage is reached",
            i_lp is not None and i_sysex is not None and i_lp < i_sysex,
            "the first SysEx is at line %s and the stage is at line %s. Initialising "
            "before ALSA is up is what the whole timed sequence exists to avoid"
            % (i_sysex, i_lp))

    # ---- ⛔ OUTLET 2: THE RESTORE, AND WHERE IT SITS ----------------------
    # It fires at the LAST stage, which is the earliest moment every m_ layer and
    # u_map exist to receive what comes back. Earlier and a restore publishes into
    # nothing. It also fires FIRST of the three at that stage -- before modal-off
    # and the footer -- so the screen settles after the state does.
    print("\n--- outlet 2: restoring the saved state ---")
    # ⚠️ FILTERED TO `restore`, BECAUSE THE BUS CARRIES BOTH DIRECTIONS. u_map
    # puts its own mode onto it at load -- `put auto mode compose mode-1` -- and
    # that traffic is u_state's business rather than u_init's. One name, three
    # selectors, disjoint per side, and this outlet only owns one of them.
    restores = [v for k in ("PRE",) + tuple(order) for v in kind(k, "STATE")
                if v[:1] == ["restore"]]
    A.check("⛔ the restore replays every saved line, manual first",
            restores == SEEDED,
            "the state bus carried %s, wanted %s" % (restores, SEEDED))
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

    # ---- ⛔ AND THE TWO OUTLETS ARE NOT INTERCHANGEABLE --------------------
    # u_init.pd warns that the restore outlet HAD to be placed to the right of
    # the launchpad one, because Pd orders outlets by X COORDINATE rather than by
    # creation order -- so a box dragged left silently swaps them and NOTHING
    # ERRORS. It does not even stop working: m_launchpad and u_state both take a
    # bare bang on their inlet, so the instrument still boots and still restores,
    # 500 ms out of order, with no error anywhere.
    #
    # ⚠️ THIS CHECK EXISTS BECAUSE THE GATE FAILED TO CATCH IT. Moving that box
    # to x=700 passed all fourteen checks: every other assertion here is of the
    # form "after the launchpad STAGE", and the stage name reaches disp before
    # either outlet fires, so both orderings satisfy it. The discriminator is
    # that the two outlets belong to DIFFERENT stages 500 ms apart, so the
    # Launchpad's SysEx must land between the stage name and the restore.
    A.check("⛔ the Launchpad is initialised BEFORE the state is restored",
            None not in (i_sysex, i_restore) and i_sysex < i_restore,
            "SysEx at line %s, restore at line %s. Swapped, the instrument still "
            "boots and still restores -- both inlets take a bare bang -- so the "
            "only symptom is a restore that publishes into a Launchpad which has "
            "not been initialised yet" % (i_sysex, i_restore))

    # ⚠️ AND THE WHOLE TIMELINE AT ONCE, which is the check that would have
    # caught the outlet swap on its own. Each of the individual assertions above
    # gives a better failure message; this one gives no gaps between them.
    timeline = [
        ("modal booting", first_index(lambda ln: ln == "DISP: modal booting")),
        ("modal wiring", i_wiring),
        ("wire.sh", i_wire),
        ("modal launchpad", i_lp),
        ("Launchpad SysEx", i_sysex),
        ("state restore", i_restore),
        ("modal-off", i_off),
        ("status", first_index(lambda ln: ln == "DISP: status v0.3-ready")),
    ]
    idx = [i for _, i in timeline]
    A.check("⛔ the whole boot, in one order, with nothing out of place",
            None not in idx and idx == sorted(idx),
            "the run went %s" % [n for n, _ in sorted(timeline,
                                                      key=lambda t: (t[1] is None, t[1]))])

    # ---- and then it stops -------------------------------------------------
    # ⚠️ A SEQUENCE THAT KEEPS GOING IS A SEQUENCE NOBODY BOUNDED. u_tempo takes
    # the footer at 4 s and that is deliberately after this file is done; a stage
    # still arriving at 7 s would silently be fighting it.
    print("\n--- and then the sequence is over ---")
    A.check("no boot stage arrives after the sequence has settled",
            not [v for v in kind("QUIET", "DISP") if v[:1] in (["modal"], ["modal-off"])],
            "still reporting stages at 7 s: %s" % kind("QUIET", "DISP"))

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
