#!/usr/bin/env python3
"""Generates test/gate/phase9-assert-drive.pd -- the timed driver for Phase 9's gate.

⛔ THE .pd IS AN OUTPUT. Edit this file, never the .pd.

It pushes onto the input buses -- param, mode, panic -- exactly as the m_ layers
would, and drives t_notein directly because THERE IS NO BUS BEHIND A MIDI INPUT
and m_404's whole receive side sits behind one.

EVERY DELAY HANGS OFF THE ONE loadbang WITH AN ABSOLUTE TIME. Chaining them
would make each window wait the SUM of everything before it, so one slow window
would silently shift every window after it -- phase6-assert-drive-gen.py's rule,
and the reason its windows are absolute too.

⚠️ THE MARK FIRES ON THE HIGHEST OUTLET so it lands in the capture BEFORE the
actions it labels. Triggers fire right to left.

⚠️ 2400 ms IS THE EARLIEST ANY WINDOW MAY START. u_map reads its table at 2000 ms
(behind deploy.sh's output gate), and a lookup before that finds an empty table
and is silent -- which looks exactly like an unmapped control.
"""
import sys

ACTION_GAP = 20                   # default ms between actions inside one window

# (absolute_ms, mark, [message-box bodies])   -- a body is raw Pd, already escaped
SEQ = [
    # ⛔ 300 ms -- DELIBERATELY EARLY, and the regression test for item 234. Every
    # other window starts at 2400 ms because the table used to be read at 2000. That
    # convention is exactly why the gate could not see the bug the hardware found:
    # mother pushes knobs.txt at BOOT, the table and the mode key were both still
    # unset, and the restored tempo was silently dropped. The map must work from load.
    (300, "EARLY", ["\\; param og-knob-1 0.0958"], ACTION_GAP),
    (2400, "TEMPO", ["\\; param og-knob-1 0.5"], ACTION_GAP),
    (2600, "VOLCA-CC", ["\\; param gk-cc 64"], ACTION_GAP),
    (2700, "VOLCA-NOTE", ["\\; param gk-note 100"], ACTION_GAP),
    (2800, "VOLCA-PROG", ["\\; param gk-prog 100"], ACTION_GAP),
    # all sixteen pads of bank A, spaced well clear of the 5 ms limiter.
    # ⚠️ The next window must leave room for the LAST note-off, 200 ms behind
    # the last note-on, or it is counted against the wrong window.
    (2900, "PADS-A", ["\\; param gk-p%d 100" % n for n in range(1, 17)], ACTION_GAP),
    (3600, "PADS-C", ["\\; param gk-pc1 100"], ACTION_GAP),
    # the receive side, which only t_notein can reach
    (4000, "RX-B5", ["\\; t-notein 44 90 34"], ACTION_GAP),
    (4100, "RX-RELEASE", ["\\; t-notein 44 0 34"], ACTION_GAP),
    (4200, "RX-A1", ["\\; t-notein 48 77 33"], ACTION_GAP),
    (4300, "RX-REJECT", ["\\; t-notein 44 90 20"], ACTION_GAP),
    # ⛔ BEFORE the mode switch. The bad row is keyed mode-1, so testing it after
    # switching to mode-4 makes it a LOOKUP MISS -- correctly silent, and nothing
    # to do with the guard it is meant to exercise.
    (4400, "BAD-DEST", ["\\; param gk-bad 100"], ACTION_GAP),
    # ⛔ TWO TRIGGERS 2 ms APART -- the ONLY window that can see a DISARMED limiter.
    # The BURST window cannot: [del 0] still defers to the next scheduler tick, so
    # inside one logical instant the gate never reopens whatever the interval is,
    # and a disarmed limiter passes that test. This one straddles the 5 ms gate.
    (4800, "PAIR", ["\\; param gk-p1 100", "\\; param gk-p2 100"], 2),
    (5000, "MODE-4", ["\\; param xport-4 1"], ACTION_GAP),
    (5200, "MODE-DEP", ["\\; param gk-cc 64"], ACTION_GAP),
    (5400, "PANIC", ["\\; panic bang"], ACTION_GAP),
]
BURST_MS, BURST_N = 4600, 20      # fired in ONE logical instant, via [until]
QUIT_MS = 6000


def main(path):
    B, C = [], []

    def obj(x, y, s):
        B.append("#X obj %d %d %s;" % (x, y, s)); return len(B) - 1

    def msg(x, y, s):
        B.append("#X msg %d %d %s;" % (x, y, s)); return len(B) - 1

    def txt(x, y, s, w):
        B.append("#X text %d %d %s, f %d;" % (x, y, s, w)); return len(B) - 1

    lb = obj(20, 60, "loadbang")
    nwin = len(SEQ) + 2                                   # + burst + quit
    top = obj(20, 110, "t " + " ".join(["b"] * nwin))
    C.append((lb, 0, top, 0))

    x = 20
    for i, (ms, mark, bodies, gap) in enumerate(SEQ):
        d = obj(x, 180, "del %d" % ms)
        C.append((top, nwin - 1 - i, d, 0))
        # mark on the HIGHEST outlet so it prints before the actions
        t = obj(x, 230, "t " + " ".join(["b"] * (len(bodies) + 1)))
        C.append((d, 0, t, 0))
        mk = msg(x, 280, "\\; pd-msg MARK %s" % mark)     # replaced below
        B[mk] = "#X msg %d %d MARK %s;" % (x, 280, mark)
        pr = obj(x, 330, "print PH9")
        C.append((t, len(bodies), mk, 0)); C.append((mk, 0, pr, 0))
        for j, body in enumerate(bodies):
            # ⛔ EACH ACTION GETS ITS OWN DELAY. Firing a window's actions off one
            # trigger puts them all in a SINGLE LOGICAL INSTANT, and m_404's rate
            # limiter then correctly collapses sixteen pads to one -- which reads
            # exactly like a broken pad map. 20 ms is well clear of the 5 ms gate.
            # ⚠️ RELATIVE, not absolute. This del is banged AT ms by the window
            # trigger, so its argument is the offset from there. Writing the
            # absolute time here fires it at ms+ms and lands the action in a
            # LATER window, which reads as that window misbehaving.
            dj = obj(x + 20, 380 + j * 42, "del %d" % (20 + j * gap))
            m = msg(x + 110, 380 + j * 42, body)
            C.append((t, len(bodies) - 1 - j, dj, 0)); C.append((dj, 0, m, 0))
        x += 300

    # the burst: BURST_N triggers of one pad inside a single logical instant
    bd = obj(x, 180, "del %d" % BURST_MS)
    C.append((top, 1, bd, 0))
    bt = obj(x, 230, "t b b")
    C.append((bd, 0, bt, 0))
    bm = msg(x, 280, "MARK BURST")
    bp = obj(x, 330, "print PH9")
    C.append((bt, 1, bm, 0)); C.append((bm, 0, bp, 0))
    bn = msg(x + 40, 380, "%d" % BURST_N)
    bu = obj(x + 40, 430, "until")
    bx = msg(x + 40, 480, "\\; param gk-p1 100")
    C.append((bt, 0, bn, 0)); C.append((bn, 0, bu, 0)); C.append((bu, 0, bx, 0))
    x += 230

    qd = obj(x, 180, "del %d" % QUIT_MS)
    qm = msg(x, 230, "\\; pd quit")
    C.append((top, 0, qd, 0)); C.append((qd, 0, qm, 0))

    # the taps: without these the capture holds MIDI only, and every assertion
    # about param, disp or err is answered by an empty list rather than by a fact
    for k, (bus, label) in enumerate([("param", "PARAM"), ("disp", "DISP"),
                                      ("err", "ERR"), ("tempo", "TEMPO")]):
        r = obj(20 + k * 300, 1000, "r " + bus)
        pp = obj(20 + k * 300, 1050, "print " + label)
        C.append((r, 0, pp, 0))

    txt(20, 1120,
        "phase9-assert-drive -- GENERATED by phase9-assert-drive-gen.py. Do not edit "
        "this file. It drives Phase 9's gate: the mode table \\, both output devices \\, "
        "m_404 in both directions \\, the rate limiter and the allowlist guard.", 92)
    txt(20, 1200,
        "⚠️ RUN IT THROUGH test/gate/phase9-assert.sh \\, never by hand. The gate rewrites "
        "noteout \\, ctlout \\, pgmout and notein to printing stubs in a SCRATCH COPY \\, "
        "and appends its own rows to the mapping table. Loaded on its own against the real "
        "patch it would emit real MIDI to whatever is plugged in \\, and half the windows "
        "would find no mapping at all.", 92)
    txt(20, 1300,
        "⚠️ THE STATE DIRECTORY IS THE GATE'S OWN AND MUST BE EMPTY. main-dev.pd passes "
        "/tmp \\, which every run on the machine shares -- and u_init restores saved state at "
        "about 3.5 s. A previous test that changed mode leaves mode in that file \\, the "
        "restore republishes it mid-run \\, and every row keyed to another mode stops matching "
        "from that instant. It cost a wrong diagnosis once already: item 232.", 92)

    out = ["#N canvas 20 20 4200 1500 12;"] + B + \
          ["#X connect %d %d %d %d;" % c for c in C]
    open(path, "w").write("\n".join(out) + "\n")
    print("%s  %d windows  %d boxes  %d connects" % (path, len(SEQ) + 2, len(B), len(C)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test/gate/phase9-assert-drive.pd")
