#!/usr/bin/env python3
"""Builds a timed driver patch from a window table. Imported, never run.

    import lib_drive as D
    D.build(path, SEQ, tag="MAP", taps=["param", "err"], burst=(4600, 20, body),
            blurb="...")

A WINDOW is `(absolute_ms, MARK, [message bodies], gap_ms)`. The driver prints
the MARK, then fires each body on its own delay, and the analyzer reads the
capture back one window at a time.

Every window's delay hangs off the one loadbang with an absolute time, so one
slow window cannot shift the rest. Each action inside a window gets its own
delay too: off one trigger they would share a logical instant, and m_404's rate
limiter would rightly collapse sixteen pads to one. ⚠️ That inner delay is
relative to the window's `ms`, which banged it; an absolute time there lands
the action in a later window.

The MARK fires on the trigger's highest outlet, so it prints before the actions
it labels (triggers fire right to left). A bus with no tap is a bus whose every
assertion is answered by an empty list.
"""
import re

# The bus -> print label map, and the one list of labels: lib_assert's _BUS and
# test/runner/predicates.py's _BUS_LINE are both built from TAP_LABEL_RE. `mode`
# is for test/bench/bench-tap.pd. `clock` is left out: a beat twice a second
# forever would bury every capture.
#
# Not every name is on the C-2 allowlist. led, oscOut, midiInGate, midiOutGate,
# screenLine1-5 and goHome are mother's, the only way to read what the LED, the
# OLED and the MIDI gating were told (screenLine and goHome are the debug
# patch's). Tapping a name never changes what its owner receives (C-5 governs
# writing), and nothing built from this map writes.
TAP_LABELS = {"param": "PARAM", "disp": "DISP", "err": "ERR", "tempo": "TEMPO",
              "start": "START", "stop": "STOP", "mode": "MODE",
              "led": "LED", "state": "STATE", "oscOut": "OLED",
              "midiInGate": "MIDIINGATE", "midiOutGate": "MIDIOUTGATE",
              "presence": "PRESENCE",
              "screenLine1": "SL1", "screenLine2": "SL2", "screenLine3": "SL3",
              "screenLine4": "SL4", "screenLine5": "SL5", "goHome": "GOHOME"}

# Every label as one regex alternation, for the parsers that read the taps back.
TAP_LABEL_RE = "|".join(re.escape(label) for label in TAP_LABELS.values())


def build(path, seq, tag, taps, quit_ms, blurb, burst=None, notes=()):
    """Write the driver. Returns (windows, boxes, connects).

    burst, if given, is (ms, n, body) -- n triggers of one body inside a single
    logical instant, via [until]. ⚠️ That proves a limiter drops rather than
    queues and nothing about its interval (the gate skill, `[del 0]`).
    """
    B, C = [], []

    def obj(x, y, s):
        B.append("#X obj %d %d %s;" % (x, y, s)); return len(B) - 1

    def msg(x, y, s):
        B.append("#X msg %d %d %s;" % (x, y, s)); return len(B) - 1

    def txt(x, y, s, w):
        B.append("#X text %d %d %s, f %d;" % (x, y, s, w)); return len(B) - 1

    lb = obj(20, 60, "loadbang")
    nwin = len(seq) + (1 if burst else 0) + 1          # + burst + quit
    top = obj(20, 110, "t " + " ".join(["b"] * nwin))
    C.append((lb, 0, top, 0))

    x = 20
    for i, (ms, mark, bodies, gap) in enumerate(seq):
        d = obj(x, 180, "del %d" % ms)
        C.append((top, nwin - 1 - i, d, 0))
        t = obj(x, 230, "t " + " ".join(["b"] * (len(bodies) + 1)))
        C.append((d, 0, t, 0))
        mk = msg(x, 280, "MARK %s" % mark)
        pr = obj(x, 330, "print %s" % tag)
        C.append((t, len(bodies), mk, 0)); C.append((mk, 0, pr, 0))
        for j, body in enumerate(bodies):
            dj = obj(x + 20, 380 + j * 42, "del %d" % (20 + j * gap))
            m = msg(x + 110, 380 + j * 42, body)
            C.append((t, len(bodies) - 1 - j, dj, 0)); C.append((dj, 0, m, 0))
        x += 300

    if burst:
        bms, bn, bbody = burst
        bd = obj(x, 180, "del %d" % bms)
        C.append((top, 1, bd, 0))
        bt = obj(x, 230, "t b b")
        C.append((bd, 0, bt, 0))
        bm = msg(x, 280, "MARK BURST")
        bp = obj(x, 330, "print %s" % tag)
        C.append((bt, 1, bm, 0)); C.append((bm, 0, bp, 0))
        cnt = msg(x + 40, 380, "%d" % bn)
        unt = obj(x + 40, 430, "until")
        bx = msg(x + 40, 480, bbody)
        C.append((bt, 0, cnt, 0)); C.append((cnt, 0, unt, 0)); C.append((unt, 0, bx, 0))
        x += 230

    qd = obj(x, 180, "del %d" % quit_ms)
    qm = msg(x, 230, "\\; pd quit")
    C.append((top, 0, qd, 0)); C.append((qd, 0, qm, 0))

    for k, bus in enumerate(taps):
        r = obj(20 + k * 300, 1000, "r " + bus)
        pp = obj(20 + k * 300, 1050, "print " + TAP_LABELS[bus])
        C.append((r, 0, pp, 0))

    txt(20, 1120, blurb, 92)
    for n, text in enumerate(notes):
        txt(20, 1220 + n * 110, text, 92)

    out = ["#N canvas 20 20 %d %d 12;" % (max(4200, x + 400), 1400 + len(notes) * 110)] \
        + B + ["#X connect %d %d %d %d;" % c for c in C]
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")
    return len(seq) + (1 if burst else 0), len(B), len(C)
