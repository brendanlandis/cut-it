# Generates test/gate/phone-assert-drive.pd -- the timed driver for the phone link's headless
# assertion run. It instantiates u_net POINTED AT LOCALHOST and pushes synthetic
# traffic onto disp, exactly as the m_ layers and u_err would.
#
# Unlike Phase 6's gate this needs NO scratch copy and NO source rewriting.
# [midiout] is a built-in class with no side channel, so Phase 6 had to rewrite
# boxes in a throwaway copy of the patch. u_net already emits to a socket -- so
# the gate just points it at 127.0.0.1 and reads the real datagrams.
#
# The MARK that separates one window from the next is itself sent as a datagram,
# to the SAME port, through the driver's own netsend. That is deliberate: a mark
# on stdout would have to be correlated with socket timestamps after the fact,
# whereas a mark in the stream arrives in true order with the data around it.
#
# Every delay hangs off the ONE loadbang with an absolute time. Chaining them
# would make each wait the SUM of everything before it, which is the kind of
# arithmetic that silently drifts as steps are added.
#
# NOTE: "#X declare" does NOT occupy a box index, so it lives in the header
# string rather than in B. Putting it in B would shift every connect by one --
# the exact failure pd-layout-check.py exists to catch.
#
# LAYOUT: the loadbang and the row of del boxes sit in a clear band across the
# TOP, so the fan-out from one loadbang to eight windows is never drawn through
# anything. Everything else is either the left column (x < 1000) or a window
# column (x >= 1200), and the two never meet.
PORT = 9995

B, C = [], []


def obj(x, y, s):
    B.append("#X obj %d %d %s;" % (x, y, s))
    return len(B) - 1


def msg(x, y, s):
    B.append("#X msg %d %d %s;" % (x, y, s))
    return len(B) - 1


def txt(x, y, s, f=90):
    B.append("#X text %d %d %s, f %d;" % (x, y, s, f))
    return len(B) - 1


def con(a, ao, b, bi):
    C.append("#X connect %d %d %d %d;" % (a, ao, b, bi))


# --------------------------------------------------- the band across the top
lb = obj(20, 60, "loadbang")
qd = obj(20, 120, "del 23000")
qm = msg(20, 170, "\\; pd quit")
con(lb, 0, qd, 0)
con(qd, 0, qm, 0)

# ------------------------------------------------------------- the left column
txt(20, 260,
    "phone-assert-drive -- the driver half of the phone link's headless assertion run. It "
    "instantiates u_net pointed at 127.0.0.1 and pushes synthetic traffic onto disp \\, "
    "exactly as m_nano \\, m_organelle and u_err would. Nothing in the deployed patch is "
    "touched or rewritten.", 70)
txt(20, 400,
    "RUN IT THROUGH test/gate/phone-assert.sh \\, never by hand -- the analyser has to be "
    "bound to the port BEFORE u_net connects. Measured in Step 0: a UDP connect to a port "
    "with nothing listening survives exactly ONE datagram \\, then ICMP kills the socket "
    "and every later send is discarded in silence. Start this by hand and you get one "
    "packet and then nothing \\, which looks exactly like a broken rate limiter.", 70)
txt(20, 600,
    "IT TESTS u_net IN ISOLATION \\, not the whole instrument. The declare at the top of "
    "the file is what finds the abstraction from test/gate/. Driving the real u_tempo would "
    "make the status window depend on rounding that belongs to u_map \\, and the contract "
    "under test here is only that u_net consumes disp and rate-limits what leaves.", 70)

unet = obj(20, 780, "u_net 127.0.0.1 %d" % PORT)
txt(20, 830,
    "THE ABSTRACTION UNDER TEST. Creation args are host and port \\, so pointing it at the "
    "analyser costs nothing and exercises exactly the code path the phone gets.", 70)

# the mark path, and the driver's own socket
mark_r = obj(20, 960, "r \\$0-mark")
mark_t = obj(20, 1010, "t a a")
mark_p = obj(240, 1060, "print MARK")
mark_l = obj(20, 1060, "list append")
mark_o = obj(20, 1110, "oscformat mark")
mark_s = obj(20, 1160, "list prepend send")
mark_m = obj(20, 1210, "list trim")
con(mark_r, 0, mark_t, 0)
con(mark_t, 1, mark_p, 0)
con(mark_t, 0, mark_l, 0)
con(mark_l, 0, mark_o, 0)
con(mark_o, 0, mark_s, 0)
con(mark_s, 0, mark_m, 0)
txt(560, 1180,
    "list append BEFORE oscformat: a message box holding one word sends that word as a "
    "SELECTOR \\, and oscformat wants a list. The same trap every branch out of g_oled's "
    "route has to dodge.", 70)

nlb = obj(560, 1390, "loadbang")
nd = obj(560, 1440, "del 300")
nm = msg(560, 1490, "connect 127.0.0.1 %d" % PORT)
net_o = obj(20, 1550, "netsend -u -b")
con(nlb, 0, nd, 0)
con(nd, 0, nm, 0)
con(nm, 0, net_o, 0)
con(mark_m, 0, net_o, 0)
txt(20, 1610,
    "THE DRIVER'S OWN NETSEND CONNECTS AT 300 ms \\, u_net's at 1500 -- so the first mark "
    "is already in the stream before the thing being measured has said anything. Both "
    "point at the same port \\, and the analyser tells them apart by OSC address.", 70)

# ------------------------------------------------------------------- the windows
# (absolute_ms, mark, [action, ...])
#   ("disp", "<message>")            one message onto disp
#   ("sweep", (name, count, ms))     count+1 distinct values for one param name
#   ("statussweep", (count, ms))     the same, as status <n>-bpm symbols
SEQ = [
    (3000,  "idle",     []),
    (6000,  "sweep1",   [("sweep", ("grain", 400, 5))]),
    (9000,  "sweep2",   [("sweep", ("grain", 400, 5)),
                         ("sweep", ("speed", 400, 5))]),
    (12000, "statussw", [("statussweep", (400, 5))]),
    (15000, "alert",    [("disp", "alert fail u_bench boom")]),
    (17000, "reserved", [("disp", "in-l 42 dB"), ("disp", "in-r 7 dB"),
                         ("disp", "grid modal 45"), ("disp", "led running"),
                         ("disp", "modal hello"), ("disp", "modal-off"),
                         ("disp", "diag")]),
    (19000, "idle2",    []),
    (22000, "done",     []),
]

PITCH, TOP = 2000, 940
for i, (when, mark, actions) in enumerate(SEQ):
    x = 1200 + i * PITCH
    d = obj(x, 120, "del %d" % when)
    con(lb, 0, d, 0)
    items = [("MARK", mark)] + actions
    tr = obj(x, 860, "t " + " ".join(["b"] * len(items)))
    con(d, 0, tr, 0)
    # outlets fire right to left, so the MARK is on the highest outlet and is in
    # the stream before anything it describes happens. Items sit in a ROW at one
    # y, so the trigger's cords all run above them rather than across them.
    bx = x
    for j, item in enumerate(items):
        outlet = len(items) - 1 - j
        by = TOP
        kind = item[0]
        if kind == "MARK":
            mm = msg(bx, by, item[1])
            ms = obj(bx, by + 50, "s \\$0-mark")
            con(tr, outlet, mm, 0)
            con(mm, 0, ms, 0)
            bx += 240
            continue
        if kind == "disp":
            am = msg(bx, by, item[1])
            asnd = obj(bx, by + 50, "s disp")
            con(tr, outlet, am, 0)
            con(am, 0, asnd, 0)
            bx += 240
            continue
        # a ramp: metro-driven counter, one distinct value per tick, stopping
        # itself at count. Two of these run at once in the sweep2 window.
        name, count, period = (item[1] if kind == "sweep"
                               else (None, item[1][0], item[1][1]))
        # the stop travels by name, not by cord: a cord from the select back up
        # to the metro runs straight through the counter's own column, which is
        # the one thing pd-layout-check.py is loudest about
        sid = "\\$0-stop%d" % len(B)
        go = msg(bx, by, "1")
        rstop = obj(bx + 180, by, "r %s" % sid)
        mt = obj(bx, by + 50, "metro %d" % period)
        con(rstop, 0, mt, 0)
        f = obj(bx, by + 100, "f")
        tf = obj(bx, by + 150, "t f f f")
        pl = obj(bx + 400, by + 200, "+ 1")
        con(tr, outlet, go, 0)
        con(go, 0, mt, 0)
        con(mt, 0, f, 0)
        con(f, 0, tf, 0)
        # rightmost first: bump the store, then emit the value, then test the end
        con(tf, 2, pl, 0)
        con(pl, 0, f, 1)
        head = (obj(bx + 180, by + 200, "makefilename %g-bpm")
                if name is None else None)
        lp = obj(bx + 180, by + 250, "list prepend %s" % (name or "status"))
        lt = obj(bx + 180, by + 300, "list trim")
        sd = obj(bx + 180, by + 350, "s disp")
        con(tf, 1, lp if head is None else head, 0)
        if head is not None:
            con(head, 0, lp, 0)
        con(lp, 0, lt, 0)
        con(lt, 0, sd, 0)
        sel = obj(bx, by + 250, "select %d" % count)
        off = msg(bx, by + 300, "0")
        sstop = obj(bx, by + 350, "s %s" % sid)
        con(tf, 0, sel, 0)
        con(sel, 0, off, 0)
        con(off, 0, sstop, 0)
        bx += 560

W = 1200 + len(SEQ) * PITCH + 400
H = TOP + 900
open("test/gate/phone-assert-drive.pd", "w").write(
    "#N canvas 20 20 %d %d 12;\n" % (W, H)
    + "#X declare -path ../../Cut\\ It;\n"
    + "\n".join(B + C) + "\n")
print("boxes", len(B), "connects", len(C), "port", PORT)
