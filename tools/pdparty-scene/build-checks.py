#!/usr/bin/env python3
"""Build the phone's checklist page, CutItChecks, from test/checklists/.

    python3 tools/pdparty-scene/build-checks.py           write the scene
    python3 tools/pdparty-scene/build-checks.py --check   exit 1 if what is
                                                          committed is stale

Writes CutItChecks/_main.pd and its data, CutItChecks/checks/*.txt. Both are
generated and committed: edit a checklist or this file, never the output.
test/gate/checks-assert.sh runs --check, so a checklist edited without a rebuild
fails the suite. Upload it with tools/pdparty-upload.sh.

The page is landscape, 448x207 canvas units (PdParty draws them 2x on the
iPhone 11), with the camera notch on the RIGHT: 22 units clear there, and 17
at the bottom for the home indicator. PdParty renders only iemguis, so the
page is canvases and bangs, and the logic is in a subpatch.

Text reaches a label as one symbol per line, so the words are joined by a
no-break space, which Pd does not split on and the phone draws as a space.
"""
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "test", "checklists")
OUT = os.path.join(HERE, "CutItChecks")

NBSP = " "
LINES = 9           # text lines on one page
WIDTH = 55          # characters on a line, at font 9 (DejaVu Sans Mono, 0.6 em)
TITLE_WIDTH = 46    # at font 11
PAGES = 3           # at most, per step
SLOTS = 100         # results array: checklist * SLOTS + step
# The buses u_inject takes (test/checklists/README.md, Send lines).
BUSES = {"disp", "err", "mode", "panic", "param", "start", "stop", "tempo"}
FIELDS = ("Need", "Send", "Do", "Check", "Pass if")   # Note stays on the Mac


# ------------------------------------------------------------------ the data
def order():
    """The checklists, in the README's table order."""
    names = re.findall(r"^\| \[(\w+)\]\(\w+[.]md\) \|",
                       open(os.path.join(SRC, "README.md"), encoding="utf-8").read(), re.M)
    if not names:
        sys.exit("build-checks: no checklist table in test/checklists/README.md")
    return names


def plain(text):
    """Markdown to the text the phone shows."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.replace("**", "").replace("`", "")


def sym(text):
    """One Pd symbol that draws as the text: spaces to no-break spaces, and the
    characters Pd parses (, ; $ and the backslash) to look-alikes."""
    text = (text.replace(",", "‚").replace(";", ";")
            .replace("$", "＄").replace("\\", "∖"))
    text = text.replace(" ", NBSP) or NBSP
    try:
        float(text)
        text += NBSP            # a bare number would be read as a float
    except ValueError:
        pass
    return text


def steps(name):
    """[(n, title, {field: text}, [send message, ...])] for one checklist."""
    md = open(os.path.join(SRC, name + ".md"), encoding="utf-8").read()
    out = []
    for block in re.split(r"\n- \[ \] ", md)[1:]:
        head = re.match(r"\*\*(\d+)\. (.+?)\*\*", block)
        if not head:
            sys.exit("build-checks: %s: a step with no **<n>. <title>**" % (name + ".md"))
        fields = dict(re.findall(r"^\s+- \*\*([\w ]+):\*\* (.*)$", block, re.M))
        sends = []
        if "Send" in fields:
            line = re.search(r"`([^`]+)`", fields["Send"])
            if not line:
                sys.exit("build-checks: %s step %s: a Send with no `line`" % (name + ".md", head.group(1)))
            sends = [m.strip() for m in line.group(1).split(";") if m.strip()]
        out.append((int(head.group(1)), plain(head.group(2)), fields, sends))
    return out


def page_lines(fields):
    lines = []
    for f in FIELDS:
        if f in fields:
            lines += textwrap.wrap("%s: %s" % (f, plain(fields[f])), WIDTH,
                                   break_on_hyphens=False)
    return lines


def build_data():
    """{file: text}, and the problems that make a checklist unfit for the page."""
    lists, titles, lines_t, sends_t, bad = [], [], [], [], []
    for c, name in enumerate(order()):
        st = steps(name)
        lists.append("%s %d;" % (name, len(st)))
        for i, (n, title, fields, sends) in enumerate(st):
            if n != i + 1:
                bad.append("%s: step %d is numbered %d" % (name, i + 1, n))
            lines = page_lines(fields)
            pages = max(1, -(-len(lines) // LINES))
            if pages > PAGES:
                bad.append("%s %d: %d lines, more than %d pages" % (name, n, len(lines), PAGES))
            lines += [""] * (pages * LINES - len(lines))
            t = "%d. %s" % (n, title)
            if len(t) > TITLE_WIDTH:
                t = t[:TITLE_WIDTH - 1] + "…"
            pos = ["%d of %d" % (n, len(st)) + ("  %d/%d" % (p + 1, pages) if pages > 1 else "")
                   for p in range(PAGES)]
            verdicts = ["%s-%d-%s" % (name, n, v) for v in ("pass", "fail")]
            for v in verdicts:
                if len(v) > 21:
                    bad.append("%s: %s is over the 21 characters an err text may be" % (name, v))
            titles.append("%d %d %d %s %s %s %s %s %s;" % (
                c, i, pages, *(sym(x) for x in pos), *verdicts, sym(t)))
            for p in range(pages):
                lines_t.append("%d %d %d %s;" % (
                    c, i, p, " ".join(sym(x) for x in lines[p * LINES:(p + 1) * LINES])))
            for m in sends:
                if m.split()[0] not in BUSES:
                    bad.append("%s %d: Send names %s, which u_inject refuses" % (name, n, m.split()[0]))
                sends_t.append("%d %d %s;" % (c, i, m))
    data = {"lists.txt": lists, "titles.txt": titles, "lines.txt": lines_t, "sends.txt": sends_t}
    return {k: "\n".join(v) + "\n" for k, v in data.items()}, bad


# ----------------------------------------------------------------- the patch
class Canvas:
    """Boxes and cords for one canvas; indices are local to it."""

    def __init__(self):
        self.b, self.c = [], []

    def add(self, rec):
        self.b.append(rec)
        return len(self.b) - 1

    def obj(self, x, y, s):
        return self.add("#X obj %d %d %s;" % (x, y, s))

    def msg(self, x, y, s):
        # A comma in a saved message box is escaped, or the loader splits the
        # record there and sends the rest to the canvas.
        return self.add("#X msg %d %d %s;" % (x, y, s.replace(", ", " \\, ")))

    def txt(self, x, y, s, f=60):
        return self.add("#X text %d %d %s, f %d;" % (x, y, s, f))

    def con(self, a, ao, b, bi=0):
        self.c.append("#X connect %d %d %d %d;" % (a, ao, b, bi))

    def chain(self, x, y, *texts, kind="obj", step=40):
        """Boxes in a column, each corded to the next; returns their indices."""
        ids = []
        for k, t in enumerate(texts):
            if t.startswith("msg:"):
                ids.append(self.msg(x, y + k * step, t[4:]))
            else:
                ids.append(self.obj(x, y + k * step, t))
            if k:
                self.con(ids[-2], 0, ids[-1])
        return ids


# Pd's old iemgui colors: -(r6 << 12 | g6 << 6 | b6) - 1, six bits a channel.
def col(r, g, b):
    return -(((r >> 2) << 12) | ((g >> 2) << 6) | (b >> 2)) - 1


BG, INK, GREEN, GRAY, RED, LAMP = (col(224, 224, 224), col(64, 64, 64), col(160, 220, 160),
                                   col(200, 200, 200), col(240, 180, 180), col(0, 252, 64))


def cnv(x, y, w, h, name, label, fs, bg=BG, xoff=6):
    return "cnv 1 %d %d ck-%s-out ck-%s-in %s %d %d 0 %d %d %d 0" % (
        w, h, name, name, label, xoff, h // 2, fs, bg, INK)


def bng(size, name, label, fs=12, recv=None):
    """A button sends on ck-<name>-press and receives on a name nothing writes:
    a bng whose two names differ re-sends what it receives (the remote's loop
    guard). A lamp is the other way round: it receives the ack, and sends to a
    name nothing reads."""
    recv = recv or "ck-%s-nc" % name
    xoff = max(2, size // 2 - len(label) * fs * 3 // 10)
    return "bng %d 250 50 0 ck-%s-press %s %s %d %d 0 %d %d %d %d" % (
        size, name, recv, label, xoff, size // 2, fs, BG, INK, INK)


def build_patch():
    top, g = Canvas(), Canvas()
    # ---------------------------------------------------------- the face
    top.obj(4, 5, bng(18, "cprev", "‹", 14))
    top.obj(26, 4, cnv(26, 4, 96, 20, "name", "-", 12))
    top.obj(124, 5, bng(18, "cnext", "›", 14))
    top.obj(146, 4, cnv(146, 4, 100, 20, "pos", "-", 10))
    top.obj(248, 4, cnv(248, 4, 62, 20, "mark", NBSP, 10))
    top.obj(316, 4, cnv(316, 4, 110, 20, "pill", "no" + NBSP + "link", 10, bg=RED))
    top.obj(4, 28, cnv(4, 28, 306, 18, "title", "-", 11, xoff=4))
    for k in range(LINES):
        top.obj(4, 48 + 15 * k, cnv(4, 48 + 15 * k, 306, 15, "l%d" % (k + 1), NBSP, 9, xoff=4))
    top.obj(316, 28, bng(50, "send", "Send", 13))
    top.obj(372, 28, "bng 50 250 50 0 ck-ack-lamp ck-ack-in ack 16 25 0 11 %d %d %d" % (BG, LAMP, INK))
    top.obj(316, 84, bng(50, "pass", "Pass", 13))
    top.obj(372, 84, bng(50, "fail", "Fail", 13))
    top.obj(316, 140, bng(50, "back", "Back", 13))
    top.obj(372, 140, bng(50, "next", "Next", 13))

    # ---------------------------------------------------------- the guts
    # State is in [value]s, $0-local: c the checklist, i the step, p the page,
    # n the steps in c, np the pages in step i.
    g.txt(20, 20, "The checklist page's logic. Generated by tools/pdparty-scene/build-checks.py "
          "-- edit that \\, never this. NO print ANYWHERE: PdParty sends print as OSC.", 90)

    # load the data, then show the first step of the first checklist
    lb = g.obj(20, 120, "loadbang")
    t5 = g.obj(20, 160, "t b b b b b b")
    g.con(lb, 0, t5)
    for k, name in enumerate(("lists", "titles", "lines", "sends")):
        # no -c: the data ends each line with a semicolon, and -c would make
        # every newline a second, empty line.
        m = g.msg(160 + k * 220, 220, "read checks/%s.txt" % name)
        d = g.obj(160 + k * 220, 260, "text define ck-%s" % name)
        g.con(t5, 5 - k, m)
        g.con(m, 0, d)
    zero = g.msg(20, 220, "0")
    g.con(t5, 1, zero)
    for k, v in enumerate(("c", "i", "p")):
        s = g.obj(20 + k * 90, 300, "v \\$0-%s" % v)
        g.con(zero, 0, s)
    # the show is last, so the values are set before it reads them
    sh0 = g.obj(20, 340, "s \\$0-show")
    g.con(t5, 0, sh0)

    # ---- show: the name, the title and position, the lines, the mark
    x0, y0 = 20, 500
    r = g.obj(x0, y0, "r \\$0-show")
    tr = g.obj(x0, y0 + 40, "t b b b b")
    g.con(r, 0, tr)
    # 1: the checklist's name and its step count
    a = g.chain(x0 + 900, y0 + 100, "v \\$0-c", "text get ck-lists", "unpack s f")
    g.con(tr, 3, a[0])
    vn = g.obj(x0 + 1040, y0 + 220, "v \\$0-n")
    g.con(a[2], 1, vn)
    nl = g.chain(x0 + 900, y0 + 260, "list prepend label", "list trim", "s ck-name-in")
    g.con(a[2], 0, nl[0])
    # 2: the key c i, found in titles
    key = g.obj(x0 + 600, y0 + 100, "t b b")
    g.con(tr, 2, key)
    vc, vi = g.obj(x0 + 600, y0 + 140, "v \\$0-c"), g.obj(x0 + 700, y0 + 180, "v \\$0-i")
    g.con(key, 1, vi)
    g.con(key, 0, vc)
    pk = g.obj(x0 + 600, y0 + 220, "pack f f")
    g.con(vc, 0, pk, 0)
    g.con(vi, 0, pk, 1)
    tt = g.chain(x0 + 600, y0 + 260, "text search ck-titles 0 1", "text get ck-titles",
                 "list split 2", step=40)
    g.con(pk, 0, tt[0])
    up = g.obj(x0 + 600, y0 + 400, "unpack f s s s s s s")
    g.con(tt[2], 1, up)
    vnp = g.obj(x0 + 600, y0 + 460, "v \\$0-np")
    g.con(up, 0, vnp)
    # the position for this page: pos1, pos2 or pos3, chosen by p
    for k in range(PAGES):
        g.con(up, 1 + k, g.obj(x0 + 700 + k * 90, y0 + 520, "symbol"), 1)
    stores = g.b[-PAGES:]
    sts = [len(g.b) - PAGES + k for k in range(PAGES)]
    pv = g.chain(x0 + 400, y0 + 440, "v \\$0-p", "select 0 1 2")
    g.con(tr, 1, pv[0])
    for k in range(PAGES):
        g.con(pv[1], k, sts[k])
    pl = g.chain(x0 + 700, y0 + 600, "list prepend label", "list trim", "s ck-pos-in")
    for s_ in sts:
        g.con(s_, 0, pl[0])
    # the two verdicts, kept for Pass and Fail
    sp, sf = g.obj(x0 + 1000, y0 + 520, "symbol"), g.obj(x0 + 1100, y0 + 520, "symbol")
    g.con(up, 4, sp, 1)
    g.con(up, 5, sf, 1)
    rp, rf = g.obj(x0 + 1000, y0 + 460, "r \\$0-pass"), g.obj(x0 + 1100, y0 + 460, "r \\$0-fail")
    g.con(rp, 0, sp)
    g.con(rf, 0, sf)
    res = g.chain(x0 + 1000, y0 + 600, "list prepend result", "list trim", "s \\$0-osc")
    g.con(sp, 0, res[0])
    g.con(sf, 0, res[0])
    tl = g.chain(x0 + 1240, y0 + 520, "list prepend label", "list trim", "s ck-title-in")
    g.con(up, 6, tl[0])
    # the order matters: the title store first fills np, which nothing reads
    # here, then the position is chosen by p after the stores are full -- the
    # trigger's outlet 2 runs before outlet 1.
    # 3: the lines of page p
    k3 = g.obj(x0 + 200, y0 + 100, "t b b b")
    g.con(tr, 0, k3)
    v3 = [g.obj(x0 + 200 + k * 100, y0 + 140 + k * 40, "v \\$0-%s" % v) for k, v in enumerate("cip")]
    p3 = g.obj(x0 + 200, y0 + 280, "pack f f f")
    for k in range(3):
        g.con(k3, k, v3[k])     # c, the hot inlet, last
        g.con(v3[k], 0, p3, k)
    lt = g.chain(x0 + 200, y0 + 320, "text search ck-lines 0 1 2", "text get ck-lines",
                 "list split 3")
    g.con(p3, 0, lt[0])
    un = g.obj(x0 + 200, y0 + 460, "unpack " + " ".join(["s"] * LINES))
    g.con(lt[2], 1, un)
    for k in range(LINES):
        c3 = g.chain(x0 + 200 + k * 130, y0 + 700 + (k % 2) * 140,
                     "list prepend label", "list trim", "s ck-l%d-in" % (k + 1))
        g.con(un, k, c3[0])
    # 4: the mark this step was given, if any
    mk = g.chain(x0 + 1400, y0 + 100, "r \\$0-show", "t b b", step=40)
    mv = [g.obj(x0 + 1400, y0 + 180, "v \\$0-c"), g.obj(x0 + 1500, y0 + 220, "v \\$0-i")]
    g.con(mk[1], 1, mv[1])
    g.con(mk[1], 0, mv[0])
    ex = g.obj(x0 + 1400, y0 + 260, "expr $f1*%d+$f2" % SLOTS)
    g.con(mv[0], 0, ex, 0)
    g.con(mv[1], 0, ex, 1)
    rd = g.chain(x0 + 1400, y0 + 300, "tabread \\$0-res", "select 1 2")
    g.con(ex, 0, rd[0])
    m1, m2 = g.msg(x0 + 1400, y0 + 400, "label passed"), g.msg(x0 + 1500, y0 + 400, "label failed")
    m0 = g.msg(x0 + 1600, y0 + 400, "label " + NBSP)
    g.con(rd[1], 0, m1)
    g.con(rd[1], 1, m2)
    g.con(rd[1], 2, m0)
    ms = g.obj(x0 + 1400, y0 + 460, "s ck-mark-in")
    for m in (m1, m2, m0):
        g.con(m, 0, ms)
    g.obj(x0 + 1400, y0 + 520, "array define \\$0-res %d" % (SLOTS * 16))

    # ---- navigation
    y1 = 1600

    # next page, else next step
    rn = g.obj(20, y1, "r ck-next-press")
    g.con(rn, 0, g.obj(20, y1 + 40, "s \\$0-next"))
    nx = g.chain(20, y1 + 100, "r \\$0-next", "t b b b")
    vp_, vnp_ = g.obj(20, y1 + 180, "v \\$0-p"), g.obj(160, y1 + 180, "v \\$0-np")
    g.con(nx[1], 1, vnp_)
    g.con(nx[1], 0, vp_)
    inc = g.obj(20, y1 + 220, "+ 1")
    g.con(vp_, 0, inc)
    mo = g.obj(20, y1 + 260, "moses")
    g.con(vnp_, 0, mo, 1)
    g.con(inc, 0, mo)
    # a [value] stores a float and sends nothing on, so a trigger sets it and
    # then shows
    setp = g.obj(20, y1 + 300, "t b f")
    g.con(mo, 0, setp)
    g.con(setp, 1, g.obj(120, y1 + 340, "v \\$0-p"))
    g.con(setp, 0, g.obj(20, y1 + 380, "s \\$0-show"))
    nstep = g.obj(240, y1 + 300, "t b")
    g.con(mo, 1, nstep)
    g.con(nstep, 0, g.obj(240, y1 + 340, "s \\$0-nextstep"))
    # next step, else stay
    ns = g.chain(500, y1 + 100, "r \\$0-nextstep", "t b b")
    vi_, vn_ = g.obj(500, y1 + 180, "v \\$0-i"), g.obj(640, y1 + 180, "v \\$0-n")
    g.con(ns[1], 1, vn_)
    g.con(ns[1], 0, vi_)
    inc2 = g.obj(500, y1 + 220, "+ 1")
    g.con(vi_, 0, inc2)
    mo2 = g.obj(500, y1 + 260, "moses")
    g.con(vn_, 0, mo2, 1)
    g.con(inc2, 0, mo2)
    st2 = g.obj(500, y1 + 300, "t b f")
    g.con(mo2, 0, st2)
    g.con(st2, 1, g.obj(640, y1 + 340, "v \\$0-i"))
    z2 = g.msg(500, y1 + 340, "0")
    g.con(st2, 0, z2)
    zz = g.chain(500, y1 + 380, "t b f", step=40)
    g.con(z2, 0, zz[0])
    g.con(zz[0], 1, g.obj(640, y1 + 420, "v \\$0-p"))
    g.con(zz[0], 0, g.obj(500, y1 + 420, "s \\$0-show"))

    # back: the page before, else the step before at its first page
    rb = g.chain(1000, y1, "r ck-back-press", "t b b")
    vpb = g.obj(1000, y1 + 80, "v \\$0-p")
    g.con(rb[1], 0, vpb)
    mb = g.obj(1000, y1 + 120, "moses 1")
    g.con(vpb, 0, mb)
    # p >= 1: p - 1
    pm = g.chain(1150, y1 + 160, "- 1", "t b f")
    g.con(mb, 1, pm[0])
    g.con(pm[1], 1, g.obj(1250, y1 + 240, "v \\$0-p"))
    g.con(pm[1], 0, g.obj(1150, y1 + 240, "s \\$0-show"))
    # p == 0: i - 1, if there is one
    ib = g.obj(1000, y1 + 160, "t b")
    g.con(mb, 0, ib)
    vib = g.obj(1000, y1 + 200, "v \\$0-i")
    g.con(ib, 0, vib)
    mb2 = g.obj(1000, y1 + 240, "moses 1")
    g.con(vib, 0, mb2)
    im = g.chain(1150, y1 + 280, "- 1", "t b f")
    g.con(mb2, 1, im[0])
    g.con(im[1], 1, g.obj(1300, y1 + 320, "v \\$0-i"))
    z3 = g.chain(1150, y1 + 360, "msg:0", "t b f")
    g.con(im[1], 0, z3[0])
    g.con(z3[1], 1, g.obj(1300, y1 + 440, "v \\$0-p"))
    g.con(z3[1], 0, g.obj(1150, y1 + 440, "s \\$0-show"))

    # the checklist before or after, at its first step
    for k, (nm, d) in enumerate((("cprev", -1), ("cnext", 1))):
        x = 1600 + k * 400
        rc = g.chain(x, y1, "r ck-%s-press" % nm, "t b b")
        size = g.obj(x + 140, y1 + 80, "text size ck-lists")
        g.con(rc[1], 1, size)
        vcc = g.obj(x, y1 + 80, "v \\$0-c")
        g.con(rc[1], 0, vcc)
        e = g.obj(x, y1 + 120, "expr ($f1+%d+$f2)%%$f2" % d)
        g.con(size, 0, e, 1)
        g.con(vcc, 0, e)
        sc = g.obj(x, y1 + 160, "t b f")
        g.con(e, 0, sc)
        g.con(sc, 1, g.obj(x + 140, y1 + 200, "v \\$0-c"))
        z = g.chain(x, y1 + 200, "msg:0", "t b f f")
        g.con(sc, 0, z[0])
        g.con(z[1], 2, g.obj(x + 200, y1 + 280, "v \\$0-i"))
        g.con(z[1], 1, g.obj(x + 100, y1 + 300, "v \\$0-p"))
        g.con(z[1], 0, g.obj(x, y1 + 320, "s \\$0-show"))

    # pass and fail: log the verdict, mark the step, go on to the next step
    for k, (nm, v) in enumerate((("pass", 1), ("fail", 2))):
        x = 2500 + k * 500
        rc = g.chain(x, y1, "r ck-%s-press" % nm, "t b b b")
        g.con(rc[1], 2, g.obj(x + 300, y1 + 80, "s \\$0-%s" % nm))
        mt = g.obj(x + 150, y1 + 120, "t b b")
        g.con(rc[1], 1, mt)
        vv = [g.obj(x + 150, y1 + 160, "v \\$0-c"), g.obj(x + 250, y1 + 200, "v \\$0-i")]
        g.con(mt, 1, vv[1])
        g.con(mt, 0, vv[0])
        e = g.obj(x + 150, y1 + 240, "expr $f1*%d+$f2" % SLOTS)
        g.con(vv[0], 0, e, 0)
        g.con(vv[1], 0, e, 1)
        w = g.obj(x + 150, y1 + 320, "tabwrite \\$0-res")
        val = g.msg(x + 150, y1 + 280, str(v))
        ord_ = g.obj(x + 300, y1 + 280, "t b f")
        g.con(e, 0, ord_)
        g.con(ord_, 1, w, 1)
        g.con(ord_, 0, val)
        g.con(val, 0, w)
        g.con(rc[1], 0, g.obj(x, y1 + 380, "s \\$0-nextstep"))

    # Send: every line of sends.txt whose key is this step, in file order
    y2 = 2400
    rs = g.chain(20, y2, "r ck-send-press", "t b b")
    kk = g.obj(160, y2 + 80, "t b b")
    g.con(rs[1], 1, kk)
    kv = [g.obj(160, y2 + 120, "v \\$0-c"), g.obj(260, y2 + 160, "v \\$0-i")]
    g.con(kk, 1, kv[1])
    g.con(kk, 0, kv[0])
    ke = g.obj(160, y2 + 200, "expr $f1*%d+$f2" % SLOTS)
    g.con(kv[0], 0, ke, 0)
    g.con(kv[1], 0, ke, 1)
    want = g.obj(160, y2 + 240, "f")
    g.con(ke, 0, want, 1)
    sz = g.chain(20, y2 + 80, "text size ck-sends", "t b f", step=40)
    g.con(rs[1], 0, sz[0])
    unt = g.obj(20, y2 + 160, "until")
    g.con(sz[1], 1, unt)
    zr = g.msg(100, y2 + 160, "0")
    g.con(sz[1], 0, zr)
    cnt = g.obj(20, y2 + 280, "f")
    g.con(zr, 0, cnt, 1)
    g.con(unt, 0, cnt)
    cnt2 = g.obj(20, y2 + 320, "t f f")
    g.con(cnt, 0, cnt2)
    plus = g.obj(120, y2 + 320, "+ 1")
    g.con(cnt2, 1, plus)
    g.con(plus, 0, cnt, 1)
    get = g.obj(20, y2 + 360, "text get ck-sends")
    g.con(cnt2, 0, get)
    tl2 = g.obj(20, y2 + 400, "t l l")
    g.con(get, 0, tl2)
    # right first: is this line's key this step? that opens the spigot
    sk = g.chain(300, y2 + 440, "list split 2", "unpack f f", step=40)
    g.con(tl2, 1, sk[0])
    se = g.obj(300, y2 + 520, "expr $f1*%d+$f2" % SLOTS)
    g.con(sk[1], 0, se, 0)
    g.con(sk[1], 1, se, 1)
    eq = g.obj(300, y2 + 560, "==")
    g.con(se, 0, eq)
    g.con(want, 0, eq, 1)
    # want is banged into place by the key above before the loop starts
    g.con(kk, 0, want)
    sp2 = g.obj(20, y2 + 600, "spigot")
    g.con(eq, 0, sp2, 1)
    ls2 = g.obj(20, y2 + 440, "list split 2")
    g.con(tl2, 0, ls2)
    g.con(ls2, 1, sp2)
    out = g.chain(20, y2 + 640, "list prepend send", "list trim", "s \\$0-osc")
    g.con(sp2, 0, out[0])

    # ---- the link: OSC out, the heartbeat's test mode, the acks
    y3 = 3200
    ro = g.chain(20, y3, "r \\$0-osc", "list append", "oscformat cutit", "s #osc-out")
    # list trim: PdParty sends cutit as the selector, and a list would miss the route
    ri = g.chain(600, y3, "r #osc-in", "t a b")
    lt3 = g.obj(600, y3 + 40, "list trim")
    g.con(ri[1], 0, lt3)
    dl = g.obj(800, y3 + 80, "del 1500")
    g.con(ri[1], 1, dl)
    nl_ = g.msg(800, y3 + 120, "label no" + NBSP + "link, color %d %d" % (RED, INK))
    g.con(dl, 0, nl_)
    pill = g.obj(800, y3 + 400, "s ck-pill-in")
    g.con(nl_, 0, pill)
    rt = g.chain(600, y3 + 80, "route cutit", "route hb ack")
    g.con(lt3, 0, rt[0])
    hb = g.chain(600, y3 + 160, "list split 1", step=40)
    g.con(rt[1], 0, hb[0])
    ch = g.obj(600, y3 + 200, "change -1")
    g.con(hb[0], 1, ch)
    rs_ = g.msg(900, y3 + 160, "set -1")
    g.con(dl, 0, rs_)
    g.con(rs_, 0, ch)
    sel = g.obj(600, y3 + 240, "select 0 1")
    g.con(ch, 0, sel)
    off = g.msg(600, y3 + 300, "label test" + NBSP + "mode" + NBSP + "off, color %d %d" % (GRAY, INK))
    on = g.msg(700, y3 + 340, "label test" + NBSP + "mode" + NBSP + "on, color %d %d" % (GREEN, INK))
    g.con(sel, 0, off)
    g.con(sel, 1, on)
    g.con(off, 0, pill)
    g.con(on, 0, pill)
    ack = g.obj(1100, y3 + 160, "route send")
    g.con(rt[1], 1, ack)
    g.con(ack, 0, g.obj(1100, y3 + 200, "s ck-ack-in"))
    g.txt(20, y3 + 500, "The pill is the Organelle's own test mode \\, from the heartbeat's second "
          "argument \\, and says no link when 1500 ms pass with nothing heard. The change is "
          "reset by the no-link \\, so the state comes back when the link does. The ack lamp "
          "lights on ack send \\, the Organelle's answer \\, not on the press.", 90)

    top_txt = ["#N canvas 60 60 448 207 10;"] + top.b
    guts = ["#N canvas 520 120 3600 3800 guts 0;"] + g.b + g.c + ["#X restore 4 194 pd guts;"]
    return "\n".join(top_txt + guts + top.c) + "\n"


def outputs():
    data, bad = build_data()
    files = {os.path.join(OUT, "checks", k): v for k, v in data.items()}
    files[os.path.join(OUT, "_main.pd")] = build_patch()
    return files, bad


def main():
    files, bad = outputs()
    if bad:
        sys.exit("build-checks: a checklist the page cannot show:\n  " + "\n  ".join(bad))
    if "--check" in sys.argv:
        stale = [p for p, text in files.items()
                 if not os.path.isfile(p) or open(p, encoding="utf-8").read() != text]
        if stale:
            sys.exit("build-checks: stale, rebuild with python3 tools/pdparty-scene/build-checks.py:\n  "
                     + "\n  ".join(os.path.relpath(p, ROOT) for p in stale))
        return
    for p, text in files.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
    print("wrote %d files to %s" % (len(files), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
