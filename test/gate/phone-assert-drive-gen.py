# Generates the timed driver for the phone link's headless assertion run, into
# the gate's scratch directory:
#
#     python3 test/gate/phone-assert-drive-gen.py <out.pd>
#
# phone-assert.py runs it on every run. It instantiates u_net pointed at
# localhost, feeds its inlets as u_root's cords would, sends it the phone's
# commands, and puts the OLED's traffic on disp to show u_net no longer reads
# it; no scratch copy is needed, since u_net already emits to a socket.
#
# Each window's MARK is a datagram to the same port, so it arrives in true order
# with the data around it. Every delay hangs off the one loadbang with an
# absolute time.
#
# No "#X declare": phone-assert.py puts "Cut It" on the path. Should one come
# back, it belongs in the header string, not in B: it takes no box index, and in
# B it would shift every connect by one.
#
# Layout: the loadbang and the del row are a band across the top; below it, the
# left column (x < 1000) and the window columns (x >= 1200) never meet.
import sys

if len(sys.argv) < 2:
    sys.exit("usage: phone-assert-drive-gen.py <out.pd>")

PORT = 9995
# u_net's own listening port, a gate-only number: the device's 9001 and
# main-dev.pd's 9002 are held by whatever patch is open.
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
qd = obj(20, 120, "del 65600")
qm = msg(20, 170, "\\; pd quit")
con(lb, 0, qd, 0)
con(qd, 0, qm, 0)

# ------------------------------------------------------------- the left column
txt(20, 260,
    "phone-assert-drive -- the driver half of the phone link's headless gate. It "
    "instantiates u_net pointed at 127.0.0.1 and pushes synthetic traffic onto disp \\, "
    "as the rest of the instrument would. Nothing in the deployed patch is touched.", 70)
txt(20, 400,
    "Run it through test/gate/phone-assert.sh: the analyzer must be bound to the port "
    "before u_net connects. A UDP connect to a port with nothing listening survives one "
    "datagram (item 114) \\, which by hand looks like a broken rate limiter.", 70)
txt(20, 600,
    "It tests u_net alone: the contract is that u_net sends the phone the state its inlets "
    "hand it \\, rate-limits the tempo \\, and passes the phone's commands out of its "
    "outlets. The real u_tempo would make the tempo windows depend on u_map's rounding.", 70)

unet = obj(20, 780, "u_net 127.0.0.1 %d %d" % (PORT, INPORT))
tap_d = obj(20, 880, "s \\$0-tap-drums")
con(unet, 0, tap_d, 0)
tap_s = obj(300, 880, "s \\$0-tap-synth")
con(unet, 1, tap_s, 0)
tap_t = obj(560, 880, "s \\$0-tap-tempo")
con(unet, 2, tap_t, 0)
tap_n = obj(820, 880, "s \\$0-tap-sections")
con(unet, 3, tap_n, 0)
# u_song's state for the sections page arrives by name, as its cord would bring it in u_root.
ss_r = obj(1080, 720, "r \\$0-ss")
con(ss_r, 0, unet, 4)
# u_tempo's BPM arrives by name, as its cord would bring it in u_root.
tp_r = obj(820, 720, "r \\$0-tp")
con(tp_r, 0, unet, 3)
# c_synth's choice arrives by name, as its cord would bring it in u_root.
sy_r = obj(560, 720, "r \\$0-sy")
con(sy_r, 0, unet, 2)
# c_steps' drum screen state arrives by name, as its cord would bring it in u_root.
ds_r = obj(300, 720, "r \\$0-ds")
con(ds_r, 0, unet, 1)
# test mode's flip arrives by name, as u_map's cord would bring it in u_root.
tm_r = obj(20, 720, "r \\$0-tm")
con(tm_r, 0, unet, 0)
txt(560, 600,
    "The abstraction under test. Args: the phone's host and port \\, then this end's "
    "inbound port. Its four outlets are c_steps \\, c_synth \\, u_tempo and u_song \\, sent on by name so no "
    "cord runs the length of the canvas.", 40)

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
    "list append before oscformat: a message box holding one word sends it as a selector \\, "
    "and oscformat wants a list.", 70)

nlb = obj(560, 1390, "loadbang")
nd = obj(560, 1440, "del 300")
nm = msg(560, 1490, "connect 127.0.0.1 %d" % PORT)
net_o = obj(20, 1550, "netsend -u -b")
con(nlb, 0, nd, 0)
con(nd, 0, nm, 0)
con(nm, 0, net_o, 0)
con(mark_m, 0, net_o, 0)
# the three probes converge here by name, as the marks do.
prb_r = obj(300, 1390, "r \\$0-probebytes")
prb_p = obj(300, 1440, "list prepend send")
prb_t = obj(300, 1490, "list trim")
con(prb_r, 0, prb_p, 0)
con(prb_p, 0, prb_t, 0)
con(prb_t, 0, net_o, 0)
txt(20, 1610,
    "This netsend connects at 300 ms and u_net's at 1500 \\, so the first mark is in the "
    "stream before u_net says anything. Both use one port \\, told apart by OSC address.", 70)

# --------------------------------------------------------------- the inbound half
# A second socket, at u_net's own listening port, so the phone's buttons are
# testable with no phone. It connects at 2600 ms because u_net's `listen` arms
# at 2000 (so the syntax check quits before anything binds), and a connect to a
# port with nothing listening survives one datagram (item 114). Commands reach it
# by name, $0-cmdbytes, so no cord crosses from a window column to this one.
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
# What u_net passes on leaves through a cord, and a report on err, so none of
# it reaches the wire. Each is tapped and re-sent to the analyzer's port under
# its own /probe address, in order with the marks. The presence bus is tapped
# too: re-wire once put a message there, and must not now.
def probe(x, y, name, src):
    rc = obj(x, y, src)
    la = obj(x, y + 50, "list append")
    of = obj(x, y + 100, "oscformat probe %s" % name)
    sn = obj(x, y + 150, "s \\$0-probebytes")
    con(rc, 0, la, 0)
    con(la, 0, of, 0)
    con(of, 0, sn, 0)


probe(20, 1900, "presence", "r presence")
probe(400, 1900, "tempo", "r \\$0-tap-tempo")
probe(400, 2700, "err", "r err")
probe(700, 2700, "drums", "r \\$0-tap-drums")
probe(1000, 2700, "synth", "r \\$0-tap-synth")
probe(1300, 2700, "sections", "r \\$0-tap-sections")
txt(20, 2180,
    "u_net is the only abstraction in this run \\, so anything seen on presence came from the "
    "inbound path. The four cords are c_steps \\, c_synth \\, u_tempo and u_song \\, hence the "
    "taps.", 70)

# ------------------------------------------------------------------- the windows
# (absolute_ms, mark, [action, ...])
#   ("disp", "<message>")            one message onto disp, which u_net must ignore
#   ("sweep", (name, count, ms))     count+1 distinct values for one name on disp
#   ("tpsweep", (count, ms))         count+1 BPMs into u_net's fourth inlet
#   ("cmd", (root, "<text>"))        one OSC datagram INTO u_net's own port
#   ("tm", None)                     a bang into u_net's inlet: flip test mode
#   ("ds", "<88 numbers>")           c_steps' state, into u_net's second inlet
#   ("sy", "synth <choice>")         c_synth's choice or velocity switch, into its third
#   ("tp", "<bpm>")                  u_tempo's BPM, into its fourth
#   ("ss", "<22 atoms>")             u_song's sections page, into its fifth, and
#   ("ss", "songs <47 atoms>")         its songs page, the same way
#   ("bus", (name, "<message>"))     one message onto a bus, as the mode bus
#
# Playing, last step 12, track 2 selected, a sync pending, the sixteen last
# steps, track 2's its own, then 7/8, drunk 30 and swing 62, then the sixteen
# volumes, pitches and randomnesses, track 2's -6 dB, 7 semitones and 40%.
DRUM_STATE = " ".join(str(v) for v in [1, 12, 2, 1, 16, 5] + [16] * 14 + [0, 1] + [0] * 14
                      + [7, 8, 30, 62] + [0, -6] + [0] * 14 + [0, 7] + [0] * 14
                      + [0, 40] + [0] * 14)
# u_song's sections page: the song, three sections, the second selected, page 1 of 1, its name
# and length, then the five rows, the last two empty.
SECTION_STATE = ("song\\ 1 3 2 1 1 verse\\ 2 8 1 intro 0 2 verse\\ 2 8 3 chorus 0 "
                 "0 - 0 0 - 0")
# u_song's songs page: three songs, night drive selected, page 1 of 1, then six rows of number,
# name and words; then the setlist chosen, 1 of 2, gig, page 1 of 1, three entries, the first
# selected, its song and how it starts, then five rows of key, song and starts.
SONGS_STATE = ("songs 3 1 1 1 night\\ drive 1 night\\ drive loaded 2 lantern - 3 hollow\\ bell "
               "next\\ bar 0 - - 0 - - 0 - - 1 2 gig 1 1 3 1 lantern silence 1 lantern silence "
               "2 hollow\\ bell next-bar 3 night\\ drive go 0 - - 0 - -")
# The songs page's commands as the phone sends them, all in one window, in order: its songs tab,
# its setlists tab, and the name tab's done from each; one u_song will refuse among them.
SONGS_CMDS = ["select 2", "page 1", "load", "new", "name hollow\\ bell", "add", "delete",
              "entry 3", "set -1", "up", "down", "starts go", "new-set", "remove",
              "set-name friday", "shuffle"]
SEQ = [
    (3000,  "idle",     []),
    # -- the OLED's traffic: u_net mirrored it once (/cutit/param, /status,
    #    /alert); it reads nothing on disp now (Brendan, 2026-11-04)
    (5000,  "dispsweep", [("sweep", ("grain", 400, 5))]),
    (8000,  "dispother", [("disp", "alert fail u_bench boom"),
                          ("disp", "chop-size 43 %"), ("disp", "diag")]),
    # -- the tempo: one BPM, then a sweep, which is coalesced
    (9500,  "tempo",    [("tp", "120")]),
    (11000, "tpsweep",  [("tpsweep", (400, 5))]),
    (14000, "idle2",    []),
    # -- the diagnostic commands, gone with the remote screen: each must reach
    #    nothing at all, one per window so a stray effect can't be blamed on
    #    the wrong one
    (16000, "cmdwire",  [("cmd", ("cutit", "re-wire"))]),
    (17400, "cmdclear", [("cmd", ("cutit", "clear-alert"))]),
    (18800, "cmdvolca", [("cmd", ("cutit", "test-note m_volca"))]),
    # Six more wrong commands, each of which must reach nothing; the heartbeat
    # in this window is the witness that the link was live.
    (20200, "cmdbogus", [("cmd", ("cutit", "panic")),
                         ("cmd", ("cutit", "reload")),
                         ("cmd", ("cutit", "test-note m_launchpad")),
                         ("cmd", ("cutit", "test-note m_404")),
                         ("cmd", ("cutit", "test-note 404")),
                         ("cmd", ("other", "tempo 99"))]),
    # -- send, a command no longer (Brendan, 2026-11-04: the line check sends
    #    nothing), with test mode off, on and off again; result; and test mode
    #    between them.
    (21600, "sendoff",  [("cmd", ("cutit", "send disp chop-size 43 %"))]),
    (23000, "tmon",     [("tm", None)]),
    (24400, "sendon",   [("cmd", ("cutit", "send disp chop-size 43 %")),
                         ("cmd", ("cutit", "send tempo 120"))]),
    (25800, "result",   [("cmd", ("cutit", "result tempo-2-pass"))]),
    (27200, "tmoff",    [("tm", None)]),
    (28600, "sendoff2", [("cmd", ("cutit", "send disp grain 12"))]),
    # one press of the key can arrive twice, 5 ms apart: the second flip is
    # dropped, so two in one window leave test mode on, and one more turns it off
    (30000, "tmtwice",  [("tm", None), ("tm", None)]),
    (31400, "tmoff2",   [("tm", None)]),
    # -- the drum screen's buttons and pad, out the first outlet to c_steps
    (32800, "cmdsync",  [("cmd", ("cutit", "drums sync"))]),
    (34200, "cmdsnap",  [("cmd", ("cutit", "drums snap"))]),
    (35600, "cmdselect", [("cmd", ("cutit", "drums select 3"))]),
    # -- the arrangement screen's time signature, drunkenness, swing and last
    #    step, and the drum screen's pads dragged, as the phone sends them
    (37000, "cmdnum",   [("cmd", ("cutit", "drums num 1"))]),
    (38400, "cmdden",   [("cmd", ("cutit", "drums den -1"))]),
    (39800, "cmddrunk", [("cmd", ("cutit", "drums drunk 30"))]),
    (41200, "cmdvol",   [("cmd", ("cutit", "drums vol 3 -6"))]),
    (41900, "cmdpitch", [("cmd", ("cutit", "drums pitch 3 7"))]),
    (42600, "cmdtracklast", [("cmd", ("cutit", "drums set-track-last 3 9"))]),
    (43300, "cmdrand",  [("cmd", ("cutit", "drums randomness 3 40"))]),
    (44000, "cmdswing", [("cmd", ("cutit", "drums set-swing 62"))]),
    (45400, "cmdlast",  [("cmd", ("cutit", "drums set-last 12"))]),
    # -- a track's distortion character, as the drum screen's radio sends it (Brendan, 2026-11-05)
    (46100, "cmdchar",  [("cmd", ("cutit", "drums char 3 2"))]),
    # A drums command u_net has never heard of still goes to c_steps, which
    # refuses what it doesn't know: u_net passes drums on whole.
    (46800, "cmddrumsnew", [("cmd", ("cutit", "drums reload 2"))]),
    # -- the synth choice, out the second outlet to c_synth, a known one and one
    #    c_synth will refuse: u_net passes synth on whole, as it does drums
    (48200, "cmdsynth", [("cmd", ("cutit", "synth strings"))]),
    (48900, "cmdsynthnew", [("cmd", ("cutit", "synth organ"))]),
    # -- the tempo, out the third outlet to u_tempo, and one it will refuse
    (49600, "cmdtempo", [("cmd", ("cutit", "tempo 133"))]),
    (50300, "cmdtemponew", [("cmd", ("cutit", "tempo fast"))]),
    # -- the velocity switch, out the second outlet to c_synth, and one it
    #    will refuse
    (51000, "cmdvel",   [("cmd", ("cutit", "velocity off"))]),
    (51700, "cmdvelnew", [("cmd", ("cutit", "velocity loud"))]),
    # -- a mode chosen in test mode ends it, so a mode button brings its page
    #    back on the phone
    (52400, "tmmodeon", [("tm", None)]),
    (53800, "tmmode",   [("bus", ("mode", "mode-2"))]),
    (55200, "drumstate", [("ds", DRUM_STATE), ("bus", ("mode", "mode-2")),
                          ("sy", "synth fm"), ("sy", "velocity off")]),
    # -- the sections page, out the fourth outlet to u_song: each command passed on whole,
    #    one u_song will refuse among them, and a name with a space, as the phone sends it,
    #    one OSC string
    (56600, "cmdsecsel", [("cmd", ("cutit", "sections select 2"))]),
    (57100, "cmdsecpage", [("cmd", ("cutit", "sections page 1"))]),
    (57600, "cmdsecnew", [("cmd", ("cutit", "sections new"))]),
    (58100, "cmdsecup", [("cmd", ("cutit", "sections up"))]),
    (58600, "cmdsecdown", [("cmd", ("cutit", "sections down"))]),
    (59100, "cmdseclen", [("cmd", ("cutit", "sections length 8"))]),
    (59600, "cmdsecdel", [("cmd", ("cutit", "sections delete"))]),
    (60100, "cmdsecname", [("cmd", ("cutit", "sections name verse\\ 2"))]),
    (60600, "cmdsecnew2", [("cmd", ("cutit", "sections shuffle"))]),
    (61100, "secstate", [("ss", SECTION_STATE)]),
    # -- the songs page: each command out the fourth outlet as it came, songs in front, and
    #    its state as /cutit/songs, sections' left alone
    (61600, "cmdsongs", [("cmd", ("cutit", "songs " + c)) for c in SONGS_CMDS]),
    (62100, "songstate", [("ss", SONGS_STATE)]),
    (63600, "done",     []),
]

PITCH, TOP = 2000, 940
for i, (when, mark, actions) in enumerate(SEQ):
    x = 1200 + i * PITCH
    d = obj(x, 120, "del %d" % when)
    con(lb, 0, d, 0)
    items = [("MARK", mark)] + actions
    tr = obj(x, 860, "t " + " ".join(["b"] * len(items)))
    con(d, 0, tr, 0)
    # Outlets fire right to left, so the MARK, on the highest, goes first. Items
    # sit in a row at one y, so the trigger's cords run above them.
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
        if kind == "tm":
            ts = obj(bx, by, "s \\$0-tm")
            con(tr, outlet, ts, 0)
            bx += 240
            continue
        if kind in ("ds", "sy", "tp", "ss", "bus"):
            text, dest = ((item[1], "\\$0-" + kind) if kind in ("ds", "sy", "tp", "ss")
                          else (item[1][1], item[1][0]))
            dm = msg(bx, by, text)
            dsn = obj(bx, by + 50, "s %s" % dest)
            con(tr, outlet, dm, 0)
            con(dm, 0, dsn, 0)
            bx += 300
            continue
        if kind == "cmd":
            # A command as the phone sends it: /cutit and its atoms, through
            # oscformat. touchosc-assert holds the spellings to the layout's.
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
        # A ramp: a metro-driven counter, one value per tick, stopping at count:
        # a name's values onto disp, or BPMs into u_net's fourth inlet.
        name, count, period = (item[1] if kind == "sweep"
                               else (None, item[1][0], item[1][1]))
        # The stop travels by name: a cord back up to the metro would cross the
        # counter's own column.
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
        if name is None:
            sd = obj(bx + 180, by + 250, "s \\$0-tp")
            con(tf, 1, sd, 0)
        else:
            lp = obj(bx + 180, by + 250, "list prepend %s" % name)
            lt = obj(bx + 180, by + 300, "list trim")
            sd = obj(bx + 180, by + 350, "s disp")
            con(tf, 1, lp, 0)
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
open(sys.argv[1], "w").write(
    "#N canvas 20 20 %d %d 12;\n" % (W, H)
    + "\n".join(B + C) + "\n")
print("boxes", len(B), "connects", len(C), "port", PORT)
