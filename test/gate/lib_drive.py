#!/usr/bin/env python3
"""Builds a timed driver patch from a window table. Imported, never run.

    import lib_drive as D
    D.build(path, SEQ, tag="MAP", taps=["param", "err"], burst=(4600, 20, body),
            blurb="...")

A WINDOW is `(absolute_ms, MARK, [message bodies], gap_ms)`. The driver prints
the MARK, then fires each body on its own delay, and the analyser reads the
capture back one window at a time.

⛔ EVERY DELAY HANGS OFF THE ONE loadbang WITH AN ABSOLUTE TIME. Chaining them
would make each window wait the SUM of everything before it, so one slow window
silently shifts every window after it and the failure looks like the LAST window
misbehaving.

⛔ EACH ACTION INSIDE A WINDOW GETS ITS OWN DELAY TOO. Firing a window's actions
off one trigger puts them all in a SINGLE LOGICAL INSTANT, and m_404's rate
limiter then correctly collapses sixteen pads to one -- which reads exactly like
a broken pad map. ⚠️ That inner delay is RELATIVE: it is banged at `ms` by the
window trigger, so its argument is the offset from there. Writing the absolute
time fires it at ms+ms and lands the action in a LATER window.

⚠️ THE MARK FIRES ON THE HIGHEST OUTLET so it prints BEFORE the actions it
labels. Triggers fire right to left.

⚠️ THE TAPS ARE NOT OPTIONAL. Without a [print] on each bus the capture holds
MIDI only, and every assertion about param, disp or err is answered by an empty
list rather than by a fact -- a pass, and a meaningless one.
"""

TAP_LABELS = {"param": "PARAM", "disp": "DISP", "err": "ERR", "tempo": "TEMPO"}


def build(path, seq, tag, taps, quit_ms, blurb, burst=None, notes=()):
    """Write the driver. Returns (windows, boxes, connects).

    burst, if given, is (ms, n, body) -- n triggers of one body inside a SINGLE
    logical instant, via [until]. ⚠️ That proves a limiter DROPS rather than
    queues and NOTHING MORE: [del 0] still defers to the next scheduler tick, so
    the gate never reopens inside one instant and a disarmed limiter passes it.
    Two triggers a real millisecond or two apart is what tests an interval.
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
