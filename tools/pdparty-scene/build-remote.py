#!/usr/bin/env python3
"""Builds the phone's remote scene, CutItRemote/_main.pd, from remote-template.pd.

    python3 tools/pdparty-scene/build-remote.py           write it
    python3 tools/pdparty-scene/build-remote.py --check   exit 1 if it is stale

The template is the remote screen, written by hand: the readouts, the four
utility buttons and the guts that talk to u_net. This adds the drum screen,
which the phone shows while the Launchpad is in mode 1 (Brendan, 2026-11-03):
whether it plays, the tempo, the global last step, the alert and the link down
the left; the sixteen pads as the Launchpad lays them out, each showing its
last step, amber with a last step of its own, dark when selected, and a tap
selects it, with the selected track's skip and move chances under them; sync
first steps and snap to global on the right, with a line saying one is waiting
for the global loop's step 1, then the time signature, two numbers with a minus
and a plus each, and the drunkenness (Brendan, from a mockup, 2026-11-04).

The two screens sit side by side in one scene, the drum screen 500 units to the
right, and PdParty shows the one under its ViewPort canvas: the mode moves it
(the PdParty Reference page, The ViewPort canvas). What the drum screen shows
comes from u_net as /cutit/drums, c_steps' 41 numbers (ref/device/phone.md).

The pads', buttons' and sliders' commands are message boxes in [pd guts],
corded to its one [oscformat cutit], so the phone gate reads them off the graph
as it reads the remote's; their display logic is a [pd drums] of its own. A
slider sends whole percents, only when they change, and for a second after a
touch it ignores the state coming back, which would pull it back to where it
was while the Organelle catches up.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "remote-template.pd")
OUT = os.path.join(HERE, "CutItRemote", "_main.pd")

NBSP = " "
X0 = 500            # the drum screen's left edge; the remote screen is 0 to 448
VIEW = 448          # one screen, half the iPhone 11's landscape points
HEIGHT = 207
NOTCH = 22          # kept clear on the right (rig-faces-away-from-the-mac)
FOOT = 17           # kept clear at the bottom: the home indicator (the PdParty Reference page)


# Pd's iemgui colors as a saved file holds them, six bits a channel, and as a
# color message takes them, eight bits a channel (the checklist page's
# build-checks.py, which found the difference on the phone).
def col(r, g, b):
    return -(((r >> 2) << 12) | ((g >> 2) << 6) | (b >> 2)) - 1


def mcol(r, g, b):
    return -((r << 16) | (g << 8) | b) - 1


INK, PAPER, BTN, LIT, EDGE = (24, 24, 24), (232, 232, 232), (252, 252, 252), (140, 210, 140), \
    (96, 96, 96)
# A pad: following the global last step, with its own, selected, selected with its own.
PADS = [((200, 200, 200), (40, 40, 40)), ((248, 208, 112), (60, 40, 0)),
       ((60, 60, 60), (255, 255, 255)), ((150, 100, 20), (255, 255, 255))]


class Canvas:
    """Boxes and cords for one canvas; indices are local to it."""

    def __init__(self, first=0):
        self.b, self.c, self.first = [], [], first

    def add(self, rec):
        self.b.append(rec)
        return self.first + len(self.b) - 1

    def obj(self, x, y, s):
        return self.add("#X obj %d %d %s;" % (x, y, s))

    def msg(self, x, y, s):
        return self.add("#X msg %d %d %s;" % (x, y, s))

    def txt(self, x, y, s, f=60):
        return self.add("#X text %d %d %s, f %d;" % (x, y, s, f))

    def con(self, a, ao, b, bi=0):
        self.c.append("#X connect %d %d %d %d;" % (a, ao, b, bi))


def cnv(x, y, w, h, out, inn, label, fs, bg, fg=INK, xoff=6):
    return "#X obj %d %d cnv 1 %d %d %s %s %s %d %d 0 %d %d %d 0;" % (
        x, y, w, h, out, inn, label, xoff, h // 2, fs, col(*bg), col(*fg))


def bng(x, y, size, name):
    """The touch under a pad or a button: it sends on <name>-press and receives
    on a name nothing writes, since a bng whose two names differ re-sends what it
    receives (the remote's loop guard)."""
    return "#X obj %d %d bng %d 250 50 0 %s-press %s-nc empty 0 -8 0 10 %d %d %d;" % (
        x, y, size, name, name, col(*PAPER), col(*INK), col(*INK))


def centered(w, text, fs):
    return max(2, int(w / 2 - len(text) * fs * 0.3))


PAD, PITCH, PAD_Y = 33, 35, 4


def pad_xy(n):
    """Pad n, 1 to 16, laid out as the Launchpad's drum pads: 1 at the top left."""
    r, c = (n - 1) // 4, (n - 1) % 4
    return X0 + 156 + c * PITCH, PAD_Y + r * PITCH


def hsl(x, y, w, h, name, label):
    """A slider, 0 to 100, that jumps to the touch: it sends on <name>-press and
    takes set and label on <name>-in."""
    return "#X obj %d %d hsl %d %d 0 100 0 0 %s-press %s-in %s 5 %d 0 11 %d %d %d 0 0;" % (
        x, y, w, h, name, name, label, h // 2, col(*BTN), col(*INK), col(*INK))


BUTTONS = [("sync", "sync" + NBSP + "first" + NBSP + "steps", 4),
           ("snap", "snap" + NBSP + "to" + NBSP + "global", 42)]
BX, BW, BH = X0 + 304, 118, 34
# What the drum screen sends after "drums", which u_net passes to c_steps whole, and c_steps'
# state's length.
ACTIONS = ["sync", "snap", "select", "num", "den", "drunk", "skip", "move"]
# The ones u_net acknowledges: the rest show in the state that comes back.
ACKED = ACTIONS[:3]
STATE = 41
# The sliders: the selected track's chances under the pads, the drunkenness on the right.
SLIDERS = [("skip", X0 + 156, 146, 3 * PITCH + PAD, 20),
           ("move", X0 + 156, 170, 3 * PITCH + PAD, 20),
           ("drunk", BX, 160, BW, 30)]
# The time signature: a row each for the top and bottom numbers, a minus, the number, a plus.
SIG = [("num", 95), ("den", 127)]
STEP, NUM_W = 28, 54
MINUS = "\u2212"


def face():
    """The drum screen's widgets, for the main canvas: no cords, only names."""
    w, rects = [], []

    def put(rec, x, y, wd, h):
        w.append(rec)
        rects.append((x, y, wd, h))

    # down the left: the transport, the tempo (u_net's status), the global last
    # step, the alert and the link, the last three sharing the remote's names
    for y, h, out, inn, label, fs in (
            (4, 30, "dr-play-out", "dr-play-in", "stopped", 14),
            (38, 44, "\\$0-status2-out", "\\$0-status-in", "-", 20),
            (86, 34, "dr-glob-out", "dr-glob-in", "last" + NBSP + "16", 16),
            (124, 28, "\\$0-atxt2-out", "\\$0-atxt-in", "no-alerts", 12),
            (156, 32, "\\$0-link2-out", "\\$0-link-in", "NO-LINK", 16)):
        put(cnv(X0 + 4, y, 146, h, out, inn, label, fs, PAPER), X0 + 4, y, 146, h)
    # the pads: a bng each, and the cell drawn over it, which the touch passes through
    for n in range(1, 17):
        x, y = pad_xy(n)
        put(bng(x, y, PAD, "dr-p%d" % n), x, y, PAD, PAD)
        put(cnv(x, y, PAD, PAD, "dr-p%d-out" % n, "dr-p%d-in" % n, "16",
                14, PADS[0][0], PADS[0][1], centered(PAD, "16", 14)),
            x, y, PAD, PAD)
    for name, x, y, wd, h in SLIDERS:
        put(hsl(x, y, wd, h, "dr-" + name, name + NBSP + "0%"), x, y, wd, h)
    # the buttons: an edge, bngs across the whole width inside it, and the face
    # over them. Two at the ends left the middle, under the label, dead (Brendan,
    # 2026-11-03), so as many as it takes to cover it.
    for name, label, y in BUTTONS:
        put(cnv(BX, y, BW, BH, "dr-edge-%s-out" % name, "dr-edge-%s-in" % name, "empty", 10,
                EDGE), BX, y, BW, BH)
        side, span = BH - 4, BW - 4
        k = -(-span // side)
        for i in range(k):
            put(bng(BX + 2 + i * (span - side) // (k - 1), y + 2, side, "dr-%s" % name),
                BX + 2, y + 2, side, side)
        put(cnv(BX + 2, y + 2, span, side, "dr-btn-%s-out" % name, "dr-btn-%s-in" % name,
                label, 11, BTN, INK, centered(span, label, 11)), BX + 2, y + 2, span, side)
    put(cnv(BX, 78, BW, 14, "dr-pend-out", "dr-pend-in", NBSP, 10, PAPER), BX, 78, BW, 14)
    # the time signature: the top number over a rule, as a fraction, and the bottom one
    for name, y in SIG:
        for side, x, label in (("down", BX, MINUS), ("up", BX + BW - STEP, "+")):
            put(cnv(x, y, STEP, STEP, "dr-edge-%s-%s-out" % (name, side),
                    "dr-edge-%s-%s-in" % (name, side), "empty", 10, EDGE), x, y, STEP, STEP)
            put(bng(x + 2, y + 2, STEP - 4, "dr-%s-%s" % (name, side)), x + 2, y + 2,
                STEP - 4, STEP - 4)
            put(cnv(x + 2, y + 2, STEP - 4, STEP - 4, "dr-%s-%s-face-out" % (name, side),
                    "dr-%s-%s-face-in" % (name, side), label, 16, BTN, INK,
                    centered(STEP - 4, "+", 16)), x + 2, y + 2, STEP - 4, STEP - 4)
        h = STEP - 2 if name == "num" else STEP
        put(cnv(BX + 32, y, NUM_W, h, "dr-%s-out" % name, "dr-%s-in" % name, "4", 20, PAPER,
                INK, centered(NUM_W, "4", 20)), BX + 32, y, NUM_W, h)
    put(cnv(BX + 32, SIG[0][1] + STEP - 2, NUM_W, 2, "dr-rule-out", "dr-rule-in", "empty", 10,
            INK), BX + 32, SIG[0][1] + STEP - 2, NUM_W, 2)
    for x, y, wd, h in rects:
        assert x + wd <= X0 + VIEW - NOTCH and y + h <= HEIGHT - FOOT, (x, y, wd, h)
    return w


def drums():
    """[pd drums]: the mode moves the ViewPort, and c_steps' state redraws the screen."""
    g = Canvas()
    g.txt(20, 20, "The drum screen's logic. GENERATED by build-remote.py -- edit that "
          "\\, not this. The mode puts the ViewPort over the drum screen in mode 1 and over "
          "the remote screen otherwise \\, once per change: u_net repeats it twice a second.", 70)
    # -- the mode
    rm = g.obj(20, 160, "r dr-mode-in")
    la = g.obj(20, 200, "list append")
    sp = g.obj(20, 240, "list split 1")
    tr = g.obj(120, 280, "list trim")
    ro = g.obj(120, 320, "route mode-1")
    m1 = g.msg(120, 360, "1")
    m0 = g.msg(220, 360, "0")
    ch = g.obj(120, 400, "change -1")
    se = g.obj(120, 440, "select 1 0")
    # vis_size first: PdParty keeps the viewport's size when it moves it, and that
    # size starts at zero, so pos alone scales the scene out of sight.
    pd = g.msg(120, 480, "vis_size %d %d \\, pos %d 0" % (VIEW, HEIGHT, X0))
    pr = g.msg(220, 480, "vis_size %d %d \\, pos 0 0" % (VIEW, HEIGHT))
    sv = g.obj(120, 530, "s ViewPort")
    for a, ao, b in ((rm, 0, la), (la, 0, sp), (sp, 1, tr), (tr, 0, ro), (ro, 0, m1),
                     (ro, 1, m0), (m1, 0, ch), (m0, 0, ch), (ch, 0, se), (se, 0, pd),
                     (se, 1, pr), (pd, 0, sv), (pr, 0, sv)):
        g.con(a, ao, b)
    # -- c_steps' state: playing, global, track, pending, 16 lasts, 16 owns, num, den,
    #    drunk, skip, move
    g.txt(600, 20, "The state: playing \\, the global last step \\, the selected track \\, "
          "a pending sync or snap \\, then each track's last step and whether it is its own \\, "
          "then the time signature \\, the drunkenness and the selected track's skip and move. "
          "list split 41 drops anything short \\, as the empty repeat before the first state. "
          "t b a a: the arrays first \\, then the header \\, which gives expr the track \\, "
          "then the sixteen cells.", 60)
    rs = g.obj(600, 160, "r dr-state-in")
    ls = g.obj(500, 200, "list split %d" % STATE)
    t3 = g.obj(600, 240, "t b a a")
    s4 = g.obj(900, 280, "list split 4")
    s16 = g.obj(900, 320, "list split 16")
    al = g.obj(900, 360, "array set \\$0-dl")
    ao_ = g.obj(1060, 360, "array set \\$0-do")
    dl = g.obj(900, 400, "array define \\$0-dl 16")
    do = g.obj(1100, 400, "array define \\$0-do 16")
    h4 = g.obj(750, 280, "list split 4")
    un = g.obj(750, 320, "unpack f f f f")
    so = g.obj(1060, 320, "list split 16")
    tail = g.obj(1300, 360, "unpack f f f f f")
    for a, ao, b in ((rs, 0, ls), (ls, 0, t3), (t3, 2, s4), (s4, 1, s16), (s16, 0, al),
                     (s16, 1, so), (so, 0, ao_), (so, 1, tail), (t3, 1, h4), (h4, 0, un)):
        g.con(a, ao, b)
    # -- the time signature: each number as its readout's label, centered for one
    #    digit or two
    g.txt(1700, 20, "The time signature's numbers: the label \\, and its x for one digit or two. "
          "A slider takes the state with set \\, so it sends nothing back \\, and sets the "
          "change its touches go through \\, so a touch to the value it had still sends. A "
          "touch shuts the spigot for a second: the state coming back meanwhile is the old "
          "value \\, and would pull the slider back from under the finger.", 60)
    for k, name in enumerate(("num", "den")):
        x = 1700 + k * 320
        ch_ = g.obj(x, 600, "change -1")
        t_ = g.obj(x, 640, "t f f")
        mf_ = g.obj(x, 680, "makefilename %d")
        lp_ = g.obj(x, 720, "list prepend label")
        lt_ = g.obj(x, 760, "list trim")
        mo = g.obj(x + 120, 680, "moses 10")
        h = STEP - 2 if name == "num" else STEP
        p1 = g.msg(x + 120, 720, "label_pos %d %d" % (centered(NUM_W, "4", 20), h // 2))
        p2 = g.msg(x + 200, 760, "label_pos %d %d" % (centered(NUM_W, "16", 20), h // 2))
        sn_ = g.obj(x, 820, "s dr-%s-in" % name)
        for a, ao, b in ((tail, k, ch_), (ch_, 0, t_), (t_, 1, mo), (mo, 0, p1), (mo, 1, p2),
                         (p1, 0, sn_), (p2, 0, sn_), (t_, 0, mf_), (mf_, 0, lp_), (lp_, 0, lt_),
                         (lt_, 0, sn_)):
            g.con(a, ao, b)
    # -- the sliders: drunk, skip, move, outlets 2 to 4 of the tail
    for k, name in enumerate(("drunk", "skip", "move")):
        x = 2400 + k * 420
        sp_ = g.obj(x, 600, "spigot 1")
        t_ = g.obj(x, 640, "t f f f")
        ms_ = g.msg(x + 200, 680, "set \\$1")
        mc_ = g.msg(x + 100, 680, "set \\$1")
        mf_ = g.obj(x, 860, "makefilename %s%s%%d%%%%" % (name, NBSP))
        lp_ = g.obj(x, 900, "list prepend label")
        lt_ = g.obj(x, 940, "list trim")
        sn_ = g.obj(x, 1000, "s dr-%s-in" % name)
        rp = g.obj(x + 100, 460, "r dr-%s-press" % name)
        tb = g.obj(x + 100, 500, "t f b")
        tg = g.obj(x + 260, 540, "t b b")
        z_ = g.msg(x + 340, 580, "0")
        dl_ = g.obj(x + 260, 580, "del 1000")
        o_ = g.msg(x + 260, 620, "1")
        hf = g.obj(x + 100, 560, "+ 0.5")
        i_ = g.obj(x + 100, 600, "i")
        ch_ = g.obj(x + 100, 760, "change -1")
        t2 = g.obj(x + 100, 800, "t f f")
        ss = g.obj(x + 200, 860, "s dr-%s-send" % name)
        for a, ao, b, bi in ((tail, 2 + k, sp_, 0), (sp_, 0, t_, 0), (t_, 2, ms_, 0),
                             (ms_, 0, sn_, 0), (t_, 1, mc_, 0), (mc_, 0, ch_, 0), (t_, 0, mf_, 0),
                             (mf_, 0, lp_, 0), (lp_, 0, lt_, 0), (lt_, 0, sn_, 0),
                             (rp, 0, tb, 0), (tb, 1, tg, 0), (tg, 1, z_, 0), (z_, 0, sp_, 1),
                             (tg, 0, dl_, 0), (dl_, 0, o_, 0), (o_, 0, sp_, 1), (tb, 0, hf, 0),
                             (hf, 0, i_, 0), (i_, 0, ch_, 0), (ch_, 0, t2, 0), (t2, 1, mf_, 0),
                             (t2, 0, ss, 0)):
            g.con(a, ao, b, bi)
    # playing
    cp = g.obj(600, 600, "change -1")
    sp1 = g.obj(600, 640, "select 0 1")
    ms = g.msg(600, 680, "label stopped")
    mp = g.msg(720, 680, "label playing")
    sp2 = g.obj(600, 720, "s dr-play-in")
    for a, ao, b in ((un, 0, cp), (cp, 0, sp1), (sp1, 0, ms), (sp1, 1, mp), (ms, 0, sp2),
                     (mp, 0, sp2)):
        g.con(a, ao, b)
    # the global last step
    cg = g.obj(850, 600, "change -1")
    mf = g.obj(850, 640, "makefilename last" + NBSP + "%d")
    lp = g.obj(850, 680, "list prepend label")
    lt = g.obj(850, 720, "list trim")
    sg = g.obj(850, 760, "s dr-glob-in")
    for a, ao, b in ((un, 1, cg), (cg, 0, mf), (mf, 0, lp), (lp, 0, lt), (lt, 0, sg)):
        g.con(a, ao, b)
    # pending
    cn = g.obj(1100, 600, "change -1")
    sn = g.obj(1100, 640, "select 0 1 2")
    n0 = g.msg(1100, 680, "label " + NBSP)
    n1 = g.msg(1160, 720, "label syncing" + NBSP + "at" + NBSP + "step" + NBSP + "1")
    n2 = g.msg(1220, 760, "label snapping" + NBSP + "at" + NBSP + "step" + NBSP + "1")
    sd = g.obj(1100, 800, "s dr-pend-in")
    for a, ao, b in ((un, 3, cn), (cn, 0, sn), (sn, 0, n0), (sn, 1, n1), (sn, 2, n2),
                     (n0, 0, sd), (n1, 0, sd), (n2, 0, sd)):
        g.con(a, ao, b)
    # -- the sixteen cells: i from 0
    g.txt(20, 900, "Each cell: its last step as its label \\, and its color from own + 2 x "
          "selected. i goes to both list prepends first \\, so each message leaves as <i> "
          "label <n> or <i> color <bg> <fg> for the route.", 60)
    tl = g.obj(20, 960, "t b b")
    n16 = g.msg(20, 1000, "16")
    z = g.msg(120, 1000, "0")
    un_ = g.obj(20, 1040, "until")
    fi = g.obj(20, 1080, "f")
    inc = g.obj(120, 1080, "+ 1")
    ti = g.obj(20, 1120, "t f f f f")
    for a, ao, b in ((t3, 0, tl), (tl, 1, z), (tl, 0, n16), (n16, 0, un_), (un_, 0, fi),
                     (fi, 0, inc), (fi, 0, ti)):
        g.con(a, ao, b)
    g.con(inc, 0, fi, 1)
    g.con(z, 0, fi, 1)
    pl = g.obj(600, 1320, "list prepend")
    pc = g.obj(300, 1320, "list prepend")
    ex = g.obj(20, 1200, "expr $f3 + 2*($f1 + 1 == $f2)")
    ro_ = g.obj(20, 1400, "route " + " ".join(str(i) for i in range(16)))
    g.con(un, 2, ex, 1)                         # the track
    g.con(ti, 3, pl, 1)
    g.con(ti, 3, pc, 1)
    ow = g.obj(300, 1160, "tabread \\$0-do")
    g.con(ti, 2, ow)
    g.con(ow, 0, ex, 2)
    lr = g.obj(600, 1160, "tabread \\$0-dl")
    mk = g.obj(600, 1200, "makefilename %d")
    lb = g.obj(600, 1240, "list prepend label")
    g.con(ti, 1, lr)
    g.con(lr, 0, mk)
    g.con(mk, 0, lb)
    g.con(lb, 0, pl)
    g.con(ti, 0, ex)
    sel = g.obj(20, 1240, "select 0 1 2 3")
    g.con(ex, 0, sel)
    for k, (bg, fg) in enumerate(PADS):
        mm = g.msg(20 + k * 140, 1280, "color %d %d" % (mcol(*bg), mcol(*fg)))
        g.con(sel, k, mm)
        g.con(mm, 0, pc)
    g.con(pc, 0, ro_)
    g.con(pl, 0, ro_)
    for i in range(16):
        s = g.obj(20 + i * 110, 1460, "s dr-p%d-in" % (i + 1))
        g.con(ro_, i, s)
    # -- the buttons light on the Organelle's answer, as the remote's lamps do
    for k, name in enumerate(("sync", "snap")):
        x = 1300 + k * 260
        r = g.obj(x, 160, "r dr-ack-%s" % name)
        t = g.obj(x, 200, "t b b")
        on = g.msg(x, 280, "color %d %d" % (mcol(*LIT), mcol(*INK)))
        dl_ = g.obj(x + 120, 240, "del 250")
        off = g.msg(x + 120, 280, "color %d %d" % (mcol(*BTN), mcol(*INK)))
        sb = g.obj(x, 320, "s dr-btn-%s-in" % name)
        for a, ao, b in ((r, 0, t), (t, 1, on), (t, 0, dl_), (dl_, 0, off), (on, 0, sb),
                         (off, 0, sb)):
            g.con(a, ao, b)
    return g


def guts_part(first, append_at, ack_route):
    """What [pd guts] gains: each pad's and button's command, corded to its one
    [list append] before [oscformat cutit], and the drums acknowledgment."""
    g = Canvas(first)
    ra = g.obj(1730, 282, "route " + " ".join(ACKED))
    g.con(ack_route, 3, ra)
    for k, name in enumerate(("sync", "snap")):
        s = g.obj(1730 + k * 200, 342, "s dr-ack-%s" % name)
        g.con(ra, k, s)
    for k, name in enumerate(("sync", "snap")):
        r = g.obj(940 + k * 260, 1300, "r dr-%s-press" % name)
        m = g.msg(940 + k * 260, 1350, "drums %s" % name)
        g.con(r, 0, m)
        g.con(m, 0, append_at)
    for n in range(1, 17):
        x = 12 + (n - 1) * 130
        r = g.obj(x, 2200, "r dr-p%d-press" % n)
        m = g.msg(x, 2250, "drums select %d" % n)
        g.con(r, 0, m)
        g.con(m, 0, append_at)
    k = 0
    for name, _y in SIG:
        for side, d in (("down", -1), ("up", 1)):
            x = 12 + k * 200
            r = g.obj(x, 2400, "r dr-%s-%s-press" % (name, side))
            m = g.msg(x, 2450, "drums %s %d" % (name, d))
            g.con(r, 0, m)
            g.con(m, 0, append_at)
            k += 1
    for name, *_rest in SLIDERS:
        x = 12 + k * 200
        r = g.obj(x, 2400, "r dr-%s-send" % name)
        m = g.msg(x, 2450, "drums %s \\$1" % name)
        g.con(r, 0, m)
        g.con(m, 0, append_at)
        k += 1
    g.txt(12, 2520, "The drum screen's commands \\, GENERATED by build-remote.py: its two buttons "
          "\\, its sixteen pads \\, the time signature's minus and plus \\, and its three "
          "sliders \\, each a message box corded to the list append above \\, so the phone gate "
          "reads them off the graph with the remote's.", 80)
    return g


BOX = re.compile(r"#X (obj|msg|text|floatatom|symbolatom|listbox) ")


def build():
    lines = open(TEMPLATE, encoding="utf-8").read().rstrip("\n").split("\n")
    s = next(k for k, l in enumerate(lines) if l.startswith("#N canvas") and " guts " in l)
    e = next(k for k, l in enumerate(lines) if l.startswith("#X restore") and l.endswith("pd guts;"))
    inner = [l for l in lines[s + 1:e]]
    boxes = [l for l in inner if BOX.match(l)]
    append_at = boxes.index("#X obj 12 1420 list append;")
    ack_route = next(i for i, l in enumerate(boxes) if " route re-wire clear-alert " in l)
    gp = guts_part(len(boxes), append_at, ack_route)
    lines[e:e] = gp.b + gp.c
    d = drums()
    lines += ["#N canvas 560 140 1900 1600 drums 0;"] + d.b + d.c + ["#X restore 120 194 pd drums;"]
    lines += face()
    return "\n".join(lines) + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        have = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != text:
            sys.exit("CutItRemote/_main.pd is stale: run tools/pdparty-scene/build-remote.py")
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote " + os.path.relpath(OUT, os.getcwd()))


if __name__ == "__main__":
    main()
