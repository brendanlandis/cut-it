#!/usr/bin/env python3
"""The phone link's headless gate -- ref/device/phone.md. No eyes, no phone, no hardware.

Binds the UDP port FIRST, then launches Pd with phone-assert-drive.pd, then
reasons about the datagrams that actually arrived.

Why binding first is not optional: measured in Step 0, a UDP connect to a port
with nothing listening survives exactly ONE datagram. The ICMP port-unreachable
that comes back tears the socket down, and every later send is discarded in
silence. So the analyser owns the lifecycle -- there is no window in which the
driver can start before the listener is up.

This is the part that asserts what the phone is actually being told. Pd cannot
ask a phone what it is displaying, but the bytes u_net emits are completely
knowable, and that is the right level to test our own code at.
"""
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⛔ ONE DECODER. test/runner/ judges phone steps from the same datagrams,
# so the decode lives in lib_osc.py rather than here -- two copies is how a
# fix reaches one caller and not the other.
import lib_osc                                                  # noqa: E402

decode = lib_osc.decode

PORT = 9995
PD = os.environ.get(
    "PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))       # test/gate/ -> the repo root
DRIVE = os.path.join(HERE, "phone-assert-drive.pd")
UNET = os.path.join(ROOT, "Cut It", "u_net.pd")
GOLED = os.path.join(ROOT, "Cut It", "g_oled.pd")

# The coalescer's target. u_net flushes on a 50 ms tick, so a window of T
# seconds can hold at most 20*T packets per distinct name, plus edge effects.
LIMIT_HZ = 20.0
HB_HZ = 2.0
ADDRS = {"/cutit/param", "/cutit/status", "/cutit/hb", "/cutit/alert",
         "/cutit/ack", "/mark",
         # the driver's taps -- what the INBOUND half did. re-wire leaves on the
         # presence bus and a test note leaves through a cord, so neither is on
         # the wire at all without them.
         "/probe/presence", "/probe/volca", "/probe/p404"}
SCENE = os.path.join(ROOT, "tools", "pdparty-scene", "CutItRemote", "_main.pd")
# every selector g_oled routes that is NOT a parameter. u_net matches all of
# them and leaves them unconnected; if one ever reaches the wire as a parameter
# name, the reserved branch is broken.
RESERVED = {"in-l", "in-r", "led", "grid", "modal", "modal-off", "alert",
            "status", "diag"}


# ------------------------------------------------------------------- collection
def collect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", PORT))
    sock.settimeout(0.25)

    packets, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            packets.append((time.time(), data))

    th = threading.Thread(target=reader, daemon=True)
    th.start()

    if not os.path.exists(DRIVE):
        print("missing %s -- run phone-assert-drive-gen.py" % DRIVE)
        sys.exit(2)
    print("listening on 127.0.0.1:%d, launching pd ..." % PORT)
    proc = subprocess.run(
        [PD, "-nogui", "-noaudio", "-nomidi",
         "-path", os.path.join(ROOT, "mac-stubs"), DRIVE],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    time.sleep(0.4)          # drain anything still in flight
    stop.set()
    th.join(timeout=2)
    sock.close()
    return packets, proc.stdout.decode("utf-8", "replace")


# ----------------------------------------------------------------------- checks
class Checks:
    def __init__(self):
        self.rows = []

    def __call__(self, ok, name, detail=""):
        self.rows.append((bool(ok), name, detail))

    def report(self):
        bad = [r for r in self.rows if not r[0]]
        for ok, name, detail in self.rows:
            print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                                  ("   -- " + detail) if detail else ""))
        print("\n%d checks, %d failed" % (len(self.rows), len(bad)))
        return 1 if bad else 0


def windows(packets):
    """Split the stream into [(mark, [(t, addr, args), ...]), ...]."""
    out, cur, name = [], [], None
    for t, data in packets:
        m = decode(data)
        if m is None:
            continue
        addr, args = m
        if addr == "/mark":
            if name is not None:
                out.append((name, cur))
            name, cur = (args[0] if args else "?"), []
        else:
            cur.append((t, addr, args))
    if name is not None:
        out.append((name, cur))
    return out


def _route_args(path):
    """The arguments of the one `route in-l ...` box in a file, or None."""
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    hits = re.findall(r"^#X obj \d+ \d+ route (in-l .*);$", src, re.M)
    return hits[0].split() if len(hits) == 1 else None


def unet_route():
    return _route_args(UNET)


def goled_route():
    return _route_args(GOLED)


# --------------------------------------------------------- the INBOUND vocabulary
# ⛔ THE PHONE IS THE ONLY SENDER THERE IS, so a command it spells differently from
# the way u_net routes it is dropped in silence and nothing anywhere says so. The
# two spellings live in two files that are deployed by two different mechanisms --
# tools/deploy.sh and a WebDAV copy -- so they can drift a long way apart. Reading
# both is the only thing that can notice.
def _route_of(path, first):
    """The arguments of the one `route <first> ...` box in a file, or None.

    Keyed on the FIRST argument rather than a position, exactly as docs-check.py's
    pd-route anchor is, because C-10 makes box indices move.
    """
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    hits = re.findall(r"^#X obj -?\d+ -?\d+ route (" + re.escape(first)
                      + r"(?: [^;]*)?);$", src, re.M)
    return hits[0].split() if len(hits) == 1 else None


def _guts(path):
    """The scene's `[pd guts]` subcanvas as (boxes, connects).

    boxes are (kind, text) in file order -- which is the index a connect names.
    """
    boxes, cons, depth, want, inside = [], [], 0, None, False
    for ln in open(path, encoding="utf-8").read().splitlines():
        if ln.startswith("#N canvas"):
            depth += 1
            if " guts " in ln and not inside:
                inside, want = True, depth
            continue
        if ln.startswith("#X restore"):
            if inside and depth == want:
                break
            depth -= 1
            continue
        if not inside:
            continue
        m = re.match(r"^#X (obj|msg|text) -?\d+ -?\d+ (.*);$", ln)
        if m:
            boxes.append((m.group(1), m.group(2)))
            continue
        m = re.match(r"^#X connect (\d+) (\d+) (\d+) (\d+);$", ln)
        if m:
            cons.append(tuple(int(g) for g in m.groups()))
    return boxes, cons


def scene_msgs():
    """Every message box in the scene that REACHES the shared [oscformat cutit].

    ⚠️ Read off the GRAPH rather than off a naming convention. "every msg box in
    the file" would also collect the two `label` messages the link row uses, and
    a convention like "the ones next to an [r ...-press]" is a fact about layout
    rather than about what can actually be sent.
    """
    boxes, cons = _guts(SCENE)
    tgt = [i for i, (k, t) in enumerate(boxes)
           if k == "obj" and t == "oscformat cutit"]
    if len(tgt) != 1:
        return None
    reach = set(tgt)
    for _ in range(4):
        reach |= {a for a, _ao, b, _bi in cons if b in reach}
    return sorted(boxes[i][1] for i in sorted(reach) if boxes[i][0] == "msg")


def scene_iemguis():
    """(send, receive) for every bng on the scene's MAIN canvas."""
    out = []
    for ln in open(SCENE, encoding="utf-8").read().splitlines():
        m = re.match(r"^#X obj -?\d+ -?\d+ bng \d+ \d+ \d+ \d+ (\S+) (\S+) ", ln)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def scene_names():
    """(names written by an [s ...], names read by an [r ...]) anywhere in the scene."""
    src = open(SCENE, encoding="utf-8").read()
    w = set(re.findall(r"^#X obj -?\d+ -?\d+ s (\S+);$", src, re.M))
    r = set(re.findall(r"^#X obj -?\d+ -?\d+ r (\S+);$", src, re.M))
    return w, r


def main():
    packets, log = collect()
    wins = windows(packets)
    got = {n: rows for n, rows in wins}
    ck = Checks()

    print("\n%d datagrams, %d windows: %s\n"
          % (len(packets), len(wins), ", ".join(n for n, _ in wins)))

    if not any(a.startswith("/cutit/") for _, a, _ in
               [(t, a, g) for _, rows in wins for t, a, g in rows]):
        print("NO /cutit/* DATAGRAMS AT ALL -- u_net is absent, failed to")
        print("create, or never connected. Pd said:\n")
        print(log)
        return 2

    def rows(win, addr=None):
        r = got.get(win, [])
        return [x for x in r if addr is None or x[1] == addr]

    def span(win):
        r = got.get(win, [])
        return (r[-1][0] - r[0][0]) if len(r) > 1 else 0.0

    def last_by_name(win):
        """Last value seen per parameter name in a window."""
        d = {}
        for _, a, g in rows(win, "/cutit/param"):
            if len(g) >= 2:
                d[g[0]] = g[1]
        return d

    # -- ⛔ THE TWO disp CONSUMERS MUST MATCH, AND THIS NEEDS NO Pd AT ALL ----
    # A new selector costs one route argument in EVERY consumer that has a
    # fallthrough, because everything a consumer does not recognise is a
    # parameter by definition. There are two -- g_oled and u_net -- and the
    # only reliable way to keep them in step is to read both boxes.
    #
    # ⛔ THE DATAGRAM CHECKS BELOW CANNOT SEE THIS, AND THAT IS WHY THIS
    # EXISTS. `diag` carries no arguments, so on the reject it becomes the
    # two atoms `diag -` and dies on [list split 3]'s too-short outlet --
    # nothing reaches the wire whether the route argument is there or not.
    # Removing it from u_net was measured against the reserved window and
    # every check still passed. A selector that carries a value would leak;
    # this one would not, so the property has to be asserted where it lives.
    ck(unet_route() is not None and goled_route() is not None,
       "the two disp route boxes are both still readable",
       "u_net: %r  g_oled: %r" % (unet_route(), goled_route()))
    if unet_route() and goled_route():
        ck(unet_route() == goled_route(),
           "⛔ u_net routes EXACTLY the selectors g_oled routes",
           "u_net has %s, g_oled has %s -- whichever side is short lets that "
           "selector fall out of its reject and be treated as a parameter"
           % (" ".join(unet_route()), " ".join(goled_route())))

    # -- ⛔ THE INBOUND VOCABULARY, READ FROM BOTH ENDS, STILL NO Pd -----------
    # The strongest half of this gate. Everything below needs a driver, a socket
    # and 30 s; this needs none of them and catches the failure that costs the
    # most -- a button that spells its command differently from the way u_net
    # routes it, which is dropped in silence with the rig in front of you.
    ucmd, udev = _route_of(UNET, "re-wire"), _route_of(UNET, "m_volca")
    smsg = scene_msgs()
    ck(ucmd is not None and udev is not None and smsg is not None,
       "the inbound route boxes and the scene's commands are all readable",
       "u_net: %r / %r   scene: %r" % (ucmd, udev, smsg))
    if ucmd and udev and smsg is not None:
        scmd = sorted({m.split()[0] for m in smsg})
        sdev = sorted({m.split()[1] for m in smsg if len(m.split()) > 1})
        ck(scmd == sorted(ucmd),
           "⛔ the scene sends EXACTLY the commands u_net routes",
           "scene sends %s, u_net routes %s -- whichever side is short is a "
           "button that does nothing at all" % (" ".join(scmd), " ".join(ucmd)))
        ck(sdev == sorted(udev),
           "⛔ the scene names EXACTLY the devices u_net routes",
           "scene names %s, u_net routes %s" % (" ".join(sdev), " ".join(udev)))
        ck(len(smsg) == len(ucmd) - 1 + len(udev),
           "one button per command, and one per sounding device",
           "%d message boxes: %s" % (len(smsg), ", ".join(smsg)))
        # and the ack must be able to light every one of them
        ck(_route_of(SCENE, "re-wire") == ucmd,
           "the scene's ACK route covers every command u_net can acknowledge",
           "scene: %r" % (_route_of(SCENE, "re-wire"),))
        ck(_route_of(SCENE, "m_volca") == udev,
           "the scene's ACK route covers every device",
           "scene: %r" % (_route_of(SCENE, "m_volca"),))

    # -- ⛔ THE TWO TRAPS THE SCENE CANNOT REPORT ON ITSELF --------------------
    guis = scene_iemguis()
    writes, reads = scene_names()
    ck(len(guis) >= 8 and all(s not in ("empty", "-") and r not in ("empty", "-")
                              for s, r in guis),
       "⛔ every bng carries BOTH a send and a receive name",
       "PdParty renders no iemgui that is missing either -- it parses, "
       "instantiates, participates and is INVISIBLE. saw %d: %s"
       % (len(guis), guis))
    senders = [(s, r) for s, r in guis if s in reads]
    lamps = [(s, r) for s, r in guis if r in writes]
    ck(bool(senders) and bool(lamps),
       "the scene still has both transmitting buttons and lit lamps",
       "%d transmit, %d are lit" % (len(senders), len(lamps)))
    ck(not [b for b in senders if b[1] in writes],
       "⛔ NO bng BOTH TRANSMITS AND IS LIT -- the ack cannot re-fire the command",
       "a bng whose send and receive names differ RE-SENDS when it receives, so "
       "one that transmits and is also lit by the ack would ping-pong for ever: %s"
       % [b for b in senders if b[1] in writes])
    ck("print" not in [t.split()[0] for _k, t in _guts(SCENE)[0] if t],
       "no [print] anywhere in the scene",
       "PdParty transmits print as /pdparty/print OSC -- 138 packets in the "
       "time it takes to drag a fader once")

    # -- shape ---------------------------------------------------------------
    seen = sorted({a for _, rowset in wins for _, a, _ in rowset})
    ck(all(a in ADDRS for a in seen), "shape: only known OSC addresses",
       "saw " + ", ".join(seen))
    ck([n for n, _ in wins] == ["idle", "sweep1", "sweep2", "statussw",
                                "alert", "reserved", "idle2", "cmdwire",
                                "cmdvolca", "cmd404", "cmdbogus", "cmdclear",
                                "done"],
       "shape: all thirteen windows arrived",
       ", ".join(n for n, _ in wins))

    hbs = [g[0] for _, rowset in wins for _, a, g in rowset
           if a == "/cutit/hb" and g]
    ck(hbs == sorted(hbs) and len(set(hbs)) == len(hbs),
       "heartbeat counter is strictly monotonic",
       "%d beats" % len(hbs))

    # -- the property the reserved branch actually has to have -----------------
    # Asserted globally rather than per window. Counting packets in the reserved
    # window used to stand in for this, and stopped working the moment u_net
    # gained a 2 s repeat -- a count is a proxy, a name is the real thing.
    allnames = {g[0] for _, rowset in wins for _, a, g in rowset
                if a == "/cutit/param" and g}
    ck(not (allnames & RESERVED),
       "NO reserved selector EVER becomes a parameter name",
       "param names seen: " + (", ".join(sorted(allnames)) or "(none)"))

    # -- idle: the 2 s repeat, and nothing else -------------------------------
    for win in ("idle", "idle2"):
        n_hb = len(rows(win, "/cutit/hb"))
        t = span(win) or 3.0
        ck(abs(n_hb / t - HB_HZ) < 0.9, "%s: heartbeat at ~2 Hz" % win,
           "%d beats in %.1f s" % (n_hb, t))
        for addr, label in (("/cutit/param", "param"), ("/cutit/status", "status")):
            n = len(rows(win, addr))
            ck(n <= 3, "%s: %s traffic is the 2 s repeat and no more" % (win, label),
               "%d packets in %.1f s" % (n, t))

    # nothing has been sent yet in the first idle window, so the repeat fires
    # against an empty store -- measured as safe, and this is what proves it
    ck(all(len(g) == 0 for _, _, g in rows("idle", "/cutit/param")),
       "idle: the repeat carries NO arguments before anything has been sent",
       "%d packets, args %s" % (len(rows("idle", "/cutit/param")),
                                [len(g) for _, _, g in rows("idle", "/cutit/param")]))

    # by idle2 real parameters have gone out, so every repeat must be the SAME
    # value -- a repeat, not new data invented by the repeat path
    seen = {(g[0], g[1]) for _, _, g in rows("idle2", "/cutit/param") if len(g) >= 2}
    ck(len(seen) <= 1,
       "idle2: every repeat carries one identical value -- a repeat, not new data",
       "distinct values: %s" % sorted(seen))

    # -- sweep1: the rate limit and the trailing edge -------------------------
    n = len(rows("sweep1", "/cutit/param"))
    t = span("sweep1") or 3.0
    ck(n >= 15, "sweep1: the sweep reached the wire at all", "%d packets" % n)
    ck(n <= LIMIT_HZ * 2.0 + 20, "sweep1: 401 events coalesced to <= ~20 Hz",
       "%d packets for 401 disp messages" % n)
    lb = last_by_name("sweep1")
    ck(lb.get("grain") == 400, "sweep1: TRAILING EDGE -- last grain is 400",
       "got %s" % lb.get("grain"))
    ck(set(lb) == {"grain"}, "sweep1: only grain was sent",
       ", ".join(sorted(lb)))

    # -- sweep2: two names at once, the single-slot killer --------------------
    lb = last_by_name("sweep2")
    n = len(rows("sweep2", "/cutit/param"))
    ck(lb.get("grain") == 400 and lb.get("speed") == 400,
       "sweep2: BOTH names keep their own trailing edge",
       "grain=%s speed=%s" % (lb.get("grain"), lb.get("speed")))
    ck(n <= LIMIT_HZ * 2.0 * 2 + 30,
       "sweep2: two simultaneous sweeps stay bounded", "%d packets" % n)

    # -- status --------------------------------------------------------------
    st = rows("statussw", "/cutit/status")
    ck(len(st) >= 10, "statussw: status reached the wire", "%d" % len(st))
    ck(len(st) <= LIMIT_HZ * 2.0 + 20,
       "statussw: status is rate limited too", "%d packets" % len(st))
    ck(st and st[-1][2] and st[-1][2][0] == "400-bpm",
       "statussw: TRAILING EDGE -- last status is 400-bpm",
       "got %s" % (st[-1][2][0] if st and st[-1][2] else None))
    sw_names = {g[0] for _, _, g in rows("statussw", "/cutit/param") if g}
    ck(not any(n.endswith("-bpm") for n in sw_names),
       "statussw: status did not leak onto the param address",
       "param names in that window: " + (", ".join(sorted(sw_names)) or "(none)"))

    # -- alert is STATE, not an event ----------------------------------------
    al = rows("alert", "/cutit/alert")
    body = [g for _, _, g in al if len(g) >= 4 and g[1] != "none"]
    ck(bool(body), "alert: the alert reached the wire", "%d carried one" % len(body))
    if body:
        g = body[-1]
        ck(g[1] == "fail" and g[2] == "u_bench" and g[3] == "boom",
           "alert: level, source and text all survive", " ".join(map(str, g[1:])))
        ck(g[0] >= 1, "alert: the count incremented", "count=%s" % g[0])
    after = [g for _, _, g in rows("idle2", "/cutit/alert") if len(g) >= 4]
    ck(after and all(x[3] == "boom" for x in after),
       "alert: PERSISTS as state, repeated on later heartbeats",
       "%d repeats in idle2" % len(after))

    # -- the reserved selectors must be swallowed ----------------------------
    res_names = {g[0] for _, _, g in rows("reserved", "/cutit/param") if g}
    ck(not (res_names & RESERVED),
       "reserved: in-l / in-r / grid / led / modal / diag never become parameters",
       "param names in that window: " + (", ".join(sorted(res_names)) or "(none)"))
    ck(len(rows("reserved", "/cutit/param")) <= 3
       and len(rows("reserved", "/cutit/status")) <= 3,
       "reserved: seven reserved messages produced no traffic beyond the repeat",
       "%d param, %d status" % (len(rows("reserved", "/cutit/param")),
                                len(rows("reserved", "/cutit/status"))))

    # -- the inbound half, window by window -----------------------------------
    # ⚠️ EXACT COUNTS, NEVER non-zero. "at least one ack" is satisfied by a route
    # that fires every branch on every command, which is precisely the bug the
    # negatives below exist to catch.
    def args(win, addr):
        return [g for _, a, g in rows(win, addr) if a == addr]

    def one(win, addr, want, label):
        got = args(win, addr)
        ck(len(got) == 1 and got[0] == want, "%s: %s" % (win, label),
           "wanted exactly one %s %s, got %s" % (addr, want, got))

    def none_of(win, addrs, label):
        got = {a: args(win, a) for a in addrs}
        ck(not any(got.values()), "%s: %s" % (win, label),
           "; ".join("%s %s" % (a, v) for a, v in got.items() if v) or "(silent)")

    CMD = ["/probe/presence", "/probe/volca", "/probe/p404", "/cutit/ack"]

    one("cmdwire", "/cutit/ack", ["re-wire"], "re-wire is acknowledged")
    one("cmdwire", "/probe/presence", ["re-wire"],
        "re-wire reaches u_present ON THE BUS -- one owner of the recovery")
    none_of("cmdwire", ["/probe/volca", "/probe/p404"],
            "re-wire sounded nothing")

    one("cmdvolca", "/probe/volca", ["notes", 60.0, 100.0, 200.0],
        "test-note m_volca fires ONE note out the Volca's own outlet")
    one("cmdvolca", "/cutit/ack", ["test-note", "m_volca"],
        "and acknowledges the device it fired at")
    none_of("cmdvolca", ["/probe/p404", "/probe/presence"],
            "it touched neither the 404 nor the re-wire")

    one("cmd404", "/probe/p404", ["pad", 1.0, 100.0],
        "test-note m_404 fires ONE pad out the 404's own outlet")
    one("cmd404", "/cutit/ack", ["test-note", "m_404"],
        "and acknowledges the device it fired at")
    none_of("cmd404", ["/probe/volca", "/probe/presence"],
            "it touched neither the Volca nor the re-wire")

    # ⛔ THE NEGATIVES. Five malformed commands in one window: two selectors off
    # the list, a DEVICE off its own list, the bare `404` spelling that route
    # reads as a float and can never match, and a well-formed command under a
    # different OSC root.
    none_of("cmdbogus", CMD,
            "⛔ FIVE WRONG COMMANDS REACH NOTHING AT ALL -- no ack, no bus, "
            "neither outlet")
    # ⛔ AND THE WITNESS THAT THE LINK WAS LIVE WHILE THEY WERE BEING IGNORED.
    # Without it "nothing happened" is also satisfied by a patch that had died,
    # by a socket that was never bound, and by a window opened in the wrong place.
    ck(len(args("cmdbogus", "/cutit/hb")) >= 2,
       "cmdbogus: the link was LIVE while they were ignored",
       "%d heartbeats in that window" % len(args("cmdbogus", "/cutit/hb")))

    one("cmdclear", "/cutit/ack", ["clear-alert"], "clear-alert is acknowledged")
    before = [g for g in args("idle2", "/cutit/alert") if len(g) >= 4]
    after = [g for g in args("done", "/cutit/alert") if len(g) >= 4]
    ck(bool(before) and all(g[3] == "boom" for g in before),
       "clear-alert: the alert was still held on the repeat BEFORE the clear",
       "%d repeats carrying %s" % (len(before), {g[3] for g in before}))
    ck(bool(after) and all(g[1] == "none" and g[3] == "-" for g in after),
       "⛔ clear-alert: and the repeat carries the EMPTY alert afterwards",
       "%d repeats carrying %s" % (len(after), [g[1:] for g in after]))
    none_of("cmdclear", ["/probe/volca", "/probe/p404", "/probe/presence"],
            "clearing the alert sounded nothing and re-wired nothing")

    print()
    rc = ck.report()
    if rc:
        print("\n--- pd output ---\n" + log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
