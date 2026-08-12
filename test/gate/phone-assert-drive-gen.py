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
# ⚠️ u_net's OWN listening port, and it is a gate-only number. The device uses
# 9001 and main-dev.pd 9002 -- both are held for a whole session by a patch
# somebody has open, and only one process on a machine can hold a UDP port.
# A gate that reused either would go red because the dev patch was running.
INPORT = 9994

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
qd = obj(20, 120, "del 31500")
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

unet = obj(20, 780, "u_net 127.0.0.1 %d %d" % (PORT, INPORT))
tap_v = obj(20, 880, "s \\$0-tap-volca")
tap_4 = obj(300, 880, "s \\$0-tap-p404")
con(unet, 0, tap_v, 0)
con(unet, 1, tap_4, 0)
txt(560, 600,
    "THE ABSTRACTION UNDER TEST. Creation args are the phone's host and port and then THIS "
    "end's inbound port \\, so pointing all three at the analyser costs nothing and exercises "
    "exactly the code path the phone gets. ITS TWO OUTLETS ARE THE VOLCA AND THE SP-404 \\, "
    "and they leave here by NAME so no cord has to be drawn the length of the canvas.", 40)

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
# the three probes converge here rather than each drawing its own cord the
# height of the canvas -- same reason the marks travel by $0-mark.
prb_r = obj(300, 1390, "r \\$0-probebytes")
prb_p = obj(300, 1440, "list prepend send")
prb_t = obj(300, 1490, "list trim")
con(prb_r, 0, prb_p, 0)
con(prb_p, 0, prb_t, 0)
con(prb_t, 0, net_o, 0)
txt(20, 1610,
    "THE DRIVER'S OWN NETSEND CONNECTS AT 300 ms \\, u_net's at 1500 -- so the first mark "
    "is already in the stream before the thing being measured has said anything. Both "
    "point at the same port \\, and the analyser tells them apart by OSC address.", 70)

# --------------------------------------------------------------- the INBOUND half
# A second socket, pointed at u_net's own listening port, which is what makes the
# phone's buttons testable with no phone.
#
# ⛔ IT CONNECTS AT 2600 ms AND NOT EARLIER. u_net arms its `listen` at 2000 --
# deliberately, so the syntax check and tools/deploy.sh quit before anything binds
# -- and item 114 says a UDP connect to a port with NOTHING LISTENING survives
# exactly one datagram before ICMP tears the socket down. Connect at 300 like the
# outbound one and every command in this run would be discarded in silence, which
# looks exactly like an inbound path that was never built.
#
# ⚠️ AND THE COMMANDS REACH IT BY NAME, NOT BY CORD -- $0-cmdbytes, exactly as the
# marks reach the outbound socket through $0-mark. A cord from a window column
# back to the left column would be drawn straight through everything between
# them, which is the one thing this file's layout rule forbids.
ilb = obj(20, 2400, "loadbang")
idl = obj(20, 2450, "del 2600")
imm = msg(20, 2500, "connect 127.0.0.1 %d" % INPORT)
in_o = obj(20, 2620, "netsend -u -b")
icr = obj(300, 2450, "r \\$0-cmdbytes")
icp = obj(300, 2500, "list prepend send")
ict = obj(300, 2550, "list trim")
con(ilb, 0, idl, 0)
con(idl, 0, imm, 0)
con(imm, 0, in_o, 0)
con(icr, 0, icp, 0)
con(icp, 0, ict, 0)
con(ict, 0, in_o, 0)

# --------------------------------------------------------------------- the probes
# ⛔ WHAT THE INBOUND HALF DID IS NOT VISIBLE ON THE WIRE OTHERWISE. re-wire
# leaves on the presence bus and a test note leaves through a CORD, so both are
# invisible to an analyser that only reads datagrams. Each is tapped here and
# re-sent to the SAME analyser port under its own /probe address, so it arrives in
# true order with the marks around it -- the same argument that put the marks in
# the stream rather than on stdout.
def probe(x, y, name, src):
    rc = obj(x, y, src)
    la = obj(x, y + 50, "list append")
    of = obj(x, y + 100, "oscformat probe %s" % name)
    sn = obj(x, y + 150, "s \\$0-probebytes")
    con(rc, 0, la, 0)
    con(la, 0, of, 0)
    con(of, 0, sn, 0)


probe(20, 1900, "presence", "r presence")
probe(400, 1900, "volca", "r \\$0-tap-volca")
probe(700, 1900, "p404", "r \\$0-tap-p404")
txt(20, 2180,
    "u_net IS THE ONLY ABSTRACTION IN THIS RUN \\, so nothing else can write presence and a "
    "re-wire seen here came from the inbound path or from nowhere. The two cords are the "
    "output devices -- wired rather than bussed \\, per C-2 \\, which is exactly why they need "
    "a tap at all.", 70)

# ------------------------------------------------------------------- the windows
# (absolute_ms, mark, [action, ...])
#   ("disp", "<message>")            one message onto disp
#   ("sweep", (name, count, ms))     count+1 distinct values for one param name
#   ("statussweep", (count, ms))     the same, as status <n>-bpm symbols
#   ("cmd", (root, "<text>"))        one OSC datagram INTO u_net's own port
#
# ⛔ EVERY COMMAND WINDOW SITS AFTER idle2, AND THAT IS NOT ARBITRARY. clear-alert
# destroys the held alert, and idle2 is where "the alert PERSISTS as state" is
# asserted -- so a clear anywhere above would make that check pass or fail for a
# reason that has nothing to do with the repeat it is testing.
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
    # -- the inbound half. One command per window, so a stray effect cannot be
    #    attributed to the wrong button.
    (22000, "cmdwire",  [("cmd", ("cutit", "re-wire"))]),
    (23400, "cmdvolca", [("cmd", ("cutit", "test-note m_volca"))]),
    (24800, "cmd404",   [("cmd", ("cutit", "test-note m_404"))]),
    # ⛔ THE NEGATIVES, AND THEY MATTER MORE THAN THE POSITIVES HERE. Four ways of
    # being wrong: a command off the list, a second one, a DEVICE off its own list,
    # and a well-formed command under a different OSC root. Every one of them must
    # reach nothing at all -- and the heartbeat in this window is the witness that
    # the link was live while they were being ignored.
    (26200, "cmdbogus", [("cmd", ("cutit", "panic")),
                         ("cmd", ("cutit", "reload")),
                         ("cmd", ("cutit", "test-note m_launchpad")),
                         ("cmd", ("cutit", "test-note 404")),
                         ("cmd", ("other", "re-wire"))]),
    (28000, "cmdclear", [("cmd", ("cutit", "clear-alert"))]),
    (30500, "done",     []),
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
        if kind == "cmd":
            # exactly the shape the PdParty scene uses: one message box, a list
            # append to turn its selector into a list, and one oscformat. If the
            # two ever disagree this gate is testing something the phone cannot
            # send -- which is what the static parity check below refuses.
            root, text = item[1]
            cm = msg(bx, by, text)
            cla = obj(bx, by + 50, "list append")
            cof = obj(bx, by + 100, "oscformat %s" % root)
            csn = obj(bx, by + 150, "s \\$0-cmdbytes")
            con(tr, outlet, cm, 0)
            con(cm, 0, cla, 0)
            con(cla, 0, cof, 0)
            con(cof, 0, csn, 0)
            bx += 300
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
H = TOP + 2000
open("test/gate/phone-assert-drive.pd", "w").write(
    "#N canvas 20 20 %d %d 12;\n" % (W, H)
    + "#X declare -path ../../Cut\\ It;\n"
    + "\n".join(B + C) + "\n")
print("boxes", len(B), "connects", len(C), "port", PORT)
