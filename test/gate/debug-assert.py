#!/usr/bin/env python3
"""Reads debug-assert.sh's capture. What the debug patch draws, and what it fires.

    python3 test/gate/debug-assert.py [-v] < capture.txt

The patch has no bus, so the five rows it writes to mother are what is
asserted. It repaints at about 3.3 Hz, so every check asks whether a row
appeared, never how often.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                          # noqa: E402

# The windows debug-assert-drive-gen.py fires, in order.
WINDOWS = ["EARLY", "BOOTED", "LP-LOW", "LP-HIGH", "NANO", "SP404", "UNO",
           "HELP", "ERRLOG", "NETWORK", "REWIRE-SCREEN", "TESTOUT",
           "VOLCA", "SP404-PROBE", "REWIRE-KEY", "REWIRE-VIEW", "UNBOUND",
           "EXIT", "DONE"]


def rows(by, win, label):
    """Every value drawn on one screen row inside one window."""
    return [" ".join(v) for k, v in by.get(win, []) if k == label]


def drew(by, win, label, text):
    return any(r == "symbol " + text for r in rows(by, win, label))


def main():
    cap = A.require_capture(sys.stdin.read())
    order, by = A.windows(cap, "DBG", len(WINDOWS))

    # Loading any patch drops Pd's ALSA connections, so without this fork the
    # patch would report silence as no MIDI arriving.
    shell = [l.strip() for l in cap.splitlines() if l.strip().startswith("SHELL:")]
    forks = {c: shell.count("SHELL: sh " + c)
             for c in ("wire.sh", "err-tail.sh", "net-probe.sh")}
    A.check("it forks wire.sh at load",
            shell[:1] == ["SHELL: sh wire.sh"],
            "the first thing it ran was: %s" % (shell[:1] or "nothing at all"))

    # Exact, because a fork hung off the draw chain runs 3.3 times a second and
    # "did it fork" passes that (ref/module/debug.md). The driver selects each
    # screen once, and wire.sh runs at boot and from k17.
    A.check("wire.sh runs twice -- once at boot, once from k17",
            forks["wire.sh"] == 2, "%d forks" % forks["wire.sh"])
    A.check("err-tail.sh runs once per selection, not once per repaint",
            forks["err-tail.sh"] == 1, "%d forks" % forks["err-tail.sh"])
    A.check("net-probe.sh runs once per selection too",
            forks["net-probe.sh"] == 1, "%d forks" % forks["net-probe.sh"])
    A.check("and it forks nothing else at all",
            len(shell) == sum(forks.values()),
            "unexpected: %s" % [l for l in shell
                                if l.replace("SHELL: sh ", "") not in forks])

    # The presence bus lives in the Pd instance this patch's load killed, so a
    # re-wire asked for there would do nothing.
    A.check("it never asks the presence bus for a re-wire",
            not any(k == "PRESENCE" for w in by for k, _ in by[w]),
            "presence traffic in the capture")

    A.check("it comes up on the MIDI screen",
            drew(by, "BOOTED", "SL1", "1-MIDI-IN"),
            "SL1 in BOOTED: %s" % rows(by, "BOOTED", "SL1")[:2])
    A.check("and it is drawing before the wire fork returns",
            bool(rows(by, "EARLY", "SL1")),
            "SL1 in EARLY: %s" % rows(by, "EARLY", "SL1")[:2])

    # 16 and 17: an off-by-one in (channel-1)/16 shows only at a boundary.
    A.check("channel 1 counts as the Launchpad",
            drew(by, "LP-LOW", "SL2", "lp-1"),
            "SL2: %s" % rows(by, "LP-LOW", "SL2")[:2])
    A.check("channel 16 is still the Launchpad, not the nano",
            drew(by, "LP-HIGH", "SL2", "lp-2")
            and drew(by, "LP-HIGH", "SL3", "nano-0"),
            "SL2 %s  SL3 %s" % (rows(by, "LP-HIGH", "SL2")[:1],
                                rows(by, "LP-HIGH", "SL3")[:1]))
    A.check("channel 17 is the nanoKONTROL",
            drew(by, "NANO", "SL3", "nano-1"),
            "SL3: %s" % rows(by, "NANO", "SL3")[:2])
    A.check("and the Launchpad's count did not move with it",
            drew(by, "NANO", "SL2", "lp-2"),
            "SL2: %s" % rows(by, "NANO", "SL2")[:2])
    A.check("channel 33 is the SP-404",
            drew(by, "SP404", "SL4", "sp404-1"),
            "SL4: %s" % rows(by, "SP404", "SL4")[:2])

    # The Uno block has no counter (its Volca is receive-only), so its traffic
    # must show on the channel row.
    A.check("port 4 traffic still shows up, as a channel",
            drew(by, "UNO", "SL5", "ch-49"),
            "SL5: %s" % rows(by, "UNO", "SL5")[:2])
    A.check("and it incremented no device counter",
            drew(by, "UNO", "SL2", "lp-2") and drew(by, "UNO", "SL3", "nano-1")
            and drew(by, "UNO", "SL4", "sp404-1"),
            "SL2 %s SL3 %s SL4 %s" % (rows(by, "UNO", "SL2")[:1],
                                      rows(by, "UNO", "SL3")[:1],
                                      rows(by, "UNO", "SL4")[:1]))

    for win, title in (("HELP", "6-HELP"), ("ERRLOG", "3-ERR-LOG"),
                       ("NETWORK", "4-NETWORK"), ("REWIRE-SCREEN", "5-RE-WIRE"),
                       ("TESTOUT", "2-TEST-OUT")):
        A.check("the key for %s selects it" % title,
                drew(by, win, "SL1", title),
                "SL1 in %s: %s" % (win, rows(by, win, "SL1")[:2]))

    # A draw chain that wrote four rows would leave the fifth showing the
    # previous screen's text.
    A.check("the help screen names the way out",
            drew(by, "HELP", "SL2", "k1-exits-to-menu"),
            "SL2: %s" % rows(by, "HELP", "SL2")[:2])
    A.check("and it fills all five rows",
            all(rows(by, "HELP", "SL%d" % n) for n in range(1, 6)),
            "empty rows: %s" % [n for n in range(1, 6)
                                if not rows(by, "HELP", "SL%d" % n)])
    A.check("the test screen warns that pad A1 may loop",
            drew(by, "TESTOUT", "SL5", "A1-may-LOOP"),
            "SL5: %s" % rows(by, "TESTOUT", "SL5")[:2])

    # The probes are the phone's (item 306), and the notes are the assertion: a
    # probe with the wrong note is a noise nobody can identify.
    volca = [v for k, v in by.get("VOLCA", []) if k == "NOTEOUT"]
    A.check("k13 plays the Volca middle C on channel 49",
            [60.0, 100.0, 49.0] in volca, "NOTEOUT: %s" % volca)
    A.check("and it releases the note",
            [60.0, 0.0, 49.0] in volca, "NOTEOUT: %s" % volca)
    sp = [v for k, v in by.get("SP404-PROBE", []) if k == "NOTEOUT"]
    A.check("k15 fires SP-404 bank A pad 1, which is note 48 on channel 33",
            [48.0, 100.0, 33.0] in sp, "NOTEOUT: %s" % sp)
    A.check("and it releases that note too",
            [48.0, 0.0, 33.0] in sp, "NOTEOUT: %s" % sp)

    # Every key in the driver is released at velocity 0; without the velocity
    # gate one press would count, and play, twice.
    A.check("one press fires one probe, not two",
            drew(by, "SP404-PROBE", "SL4", "sent-2"),
            "SL4 after two probes: %s" % rows(by, "SP404-PROBE", "SL4")[:2])

    # k17 does not change screen, so the count is read on screen 5 afterwards.
    A.check("k17 does not move you off the screen you were on",
            drew(by, "REWIRE-KEY", "SL1", "2-TEST-OUT"),
            "SL1: %s" % rows(by, "REWIRE-KEY", "SL1")[:2])
    A.check("the re-wire screen counts the runs",
            drew(by, "REWIRE-VIEW", "SL4", "runs-2"),
            "SL4: %s" % rows(by, "REWIRE-VIEW", "SL4")[:2])

    # t_shell emits nothing, so wire.sh's "N connections" never arrives and the
    # store keeps its dash: the parse is covered only on the rig.
    A.check("the link count is a dash with no shell output to parse",
            drew(by, "REWIRE-VIEW", "SL3", "-"),
            "SL3: %s" % rows(by, "REWIRE-VIEW", "SL3")[:2])

    A.check("a key it does not bind changes nothing",
            drew(by, "UNBOUND", "SL1", "5-RE-WIRE")
            and not any(k == "GOHOME" for k, _ in by.get("UNBOUND", [])),
            "SL1 %s" % rows(by, "UNBOUND", "SL1")[:2])
    A.check("k1 leaves through goHome",
            any(k == "GOHOME" for k, _ in by.get("EXIT", [])),
            "goHome traffic in EXIT: %s"
            % [v for k, v in by.get("EXIT", []) if k == "GOHOME"])
    A.check("and nothing sent goHome before it was asked to",
            not any(k == "GOHOME" for w in WINDOWS[:WINDOWS.index("EXIT")]
                    for k, _ in by.get(w, [])),
            "early goHome in: %s" % [w for w in WINDOWS[:WINDOWS.index("EXIT")]
                                     if any(k == "GOHOME" for k, _ in by.get(w, []))])

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
