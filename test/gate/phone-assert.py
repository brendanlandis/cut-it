#!/usr/bin/env python3
"""The phone link's headless gate -- ref/device/phone.md. No eyes, no phone, no hardware.

    python3 test/gate/phone-assert.py [-v] [--keep]     (run it as phone-assert.sh)

Generates its driver into its own scratch directory, binds the UDP port, then
launches Pd and reasons about the datagrams that arrived. -v also prints every
decoded datagram; --keep leaves the driver and Pd's console behind.

The port is bound before Pd starts: a UDP connect to a port with nothing
listening survives exactly one datagram (item 114), and the rest are dropped in
silence.
"""
import atexit
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_osc                                                  # noqa: E402
import lib_pd                                                   # noqa: E402
import lib_scratch as S                                         # noqa: E402

decode = lib_osc.decode

PORT = 9995
ROOT = S.ROOT
UNET = os.path.join(ROOT, "Cut It", "u_net.pd")
GOLED = os.path.join(ROOT, "Cut It", "g_oled.pd")
KEEP = "--keep" in sys.argv
WORK = S.work_dir("phone")
DRIVE = os.path.join(WORK, "drive.pd")

# The coalescer's target. u_net flushes on a 50 ms tick, so a window of T
# seconds can hold at most 20*T packets per distinct name, plus edge effects.
LIMIT_HZ = 20.0
HB_HZ = 2.0
ADDRS = {"/cutit/param", "/cutit/status", "/cutit/hb", "/cutit/alert",
         "/cutit/ack", "/mark",
         # the driver's taps for the inbound half: re-wire leaves on the
         # presence bus and a test note through a cord, neither on the wire.
         "/probe/presence", "/probe/volca",
         # and the checklist page's: test mode and a result report on err.
         "/probe/err",
         # and the two drum buttons: out a cord to c_steps.
         "/probe/drums",
         # and what the drum screen shows: the mode, and c_steps' state.
         "/cutit/mode", "/cutit/drums"}
# The drum screen's settings: u_net does not acknowledge them, since the state
# the drum screen shows says each.
DRUMS_QUIET = ["num", "den", "drunk", "skip", "move"]
# Every selector g_oled routes that is not a parameter. u_net leaves them
# unconnected, so one on the wire as a parameter name means the branch broke.
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

    print("listening on 127.0.0.1:%d, launching pd ..." % PORT)
    cap = os.path.join(WORK, "capture.txt")
    S.run(cap, 90, "-nogui", "-noaudio", "-nomidi", "-path", "mac-stubs",
          "-path", "Cut It", DRIVE)
    time.sleep(0.4)          # drain anything still in flight
    stop.set()
    th.join(timeout=2)
    sock.close()
    return packets, open(cap, encoding="utf-8", errors="replace").read()


# ----------------------------------------------------------------------- checks
MARK_T = {}     # each window's mark, when it arrived


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
            MARK_T[name] = t
        else:
            cur.append((t, addr, args))
    if name is not None:
        out.append((name, cur))
    return out


def _route_args(path):
    """The arguments of the one `route in-l ...` box in a file, or None."""
    try:
        recs = lib_pd.read(path)
    except OSError:
        return None
    hits = [m.group(1) for m in (re.match(r"^#X obj \d+ \d+ route (in-l .*);$", r)
                                 for r in recs) if m]
    return hits[0].split() if len(hits) == 1 else None


def unet_route():
    return _route_args(UNET)


def goled_route():
    return _route_args(GOLED)


def cleanup():
    if KEEP:
        print("kept " + WORK)
    else:
        shutil.rmtree(WORK, ignore_errors=True)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    os.chdir(ROOT)
    S.require_pd()
    S.require("Cut It/u_net.pd")
    os.makedirs(WORK)
    atexit.register(cleanup)
    S.drive("test/gate/phone-assert-drive-gen.py", DRIVE)

    packets, log = collect()
    wins = windows(packets)
    got = {n: rows for n, rows in wins}

    print("\n%d datagrams, %d windows: %s\n"
          % (len(packets), len(wins), ", ".join(n for n, _ in wins)))
    if A.verbose:
        for name, rowset in wins:
            print("  -- %s" % name)
            for t, a, g in rowset:
                print("     %.3f  %s %s" % (t - packets[0][0], a, " ".join(map(str, g))))
        print()

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

    # -- the two disp consumers route the same selectors, no Pd -------------
    # Whatever a consumer doesn't route is a parameter, so g_oled and u_net must
    # agree. The datagram checks can't see it for `diag`: with no arguments it
    # dies on [list split 3]'s short outlet either way (measured: removing it
    # from u_net passed every datagram check).
    A.check("the two disp route boxes are both still readable",
            unet_route() is not None and goled_route() is not None,
            "u_net: %r  g_oled: %r" % (unet_route(), goled_route()))
    if unet_route() and goled_route():
        A.check("⛔ u_net routes EXACTLY the selectors g_oled routes",
                unet_route() == goled_route(),
                "u_net has %s, g_oled has %s -- whichever side is short lets that "
                "selector fall out of its reject and be treated as a parameter"
                % (" ".join(unet_route()), " ".join(goled_route())))

    # The inbound vocabulary's other end, what the phone's buttons send, is
    # touchosc-assert's: it reads the layout against u_net's route boxes.

    # -- shape ---------------------------------------------------------------
    seen = sorted({a for _, rowset in wins for _, a, _ in rowset})
    A.check("shape: only known OSC addresses", all(a in ADDRS for a in seen),
            "saw " + ", ".join(seen))
    A.check("shape: all thirty-three windows arrived",
            [n for n, _ in wins] == ["idle", "sweep1", "sweep2", "statussw",
                                     "alert", "reserved", "idle2", "cmdwire",
                                     "cmdvolca", "cmd404", "cmdbogus", "cmdclear",
                                     "sendoff", "tmon", "sendon", "result", "tmoff",
                                     "sendoff2", "tmtwice", "tmoff2", "cmdsync",
                                     "cmdsnap", "cmdselect", "cmdnum", "cmdden",
                                     "cmddrunk", "cmdskip", "cmdmove", "cmddrumsnew",
                                     "tmmodeon", "tmmode", "drumstate", "done"],
            ", ".join(n for n, _ in wins))

    hbs = [g[0] for _, rowset in wins for _, a, g in rowset
           if a == "/cutit/hb" and g]
    A.check("heartbeat counter is strictly monotonic",
            hbs == sorted(hbs) and len(set(hbs)) == len(hbs),
            "%d beats" % len(hbs))

    # -- the reserved branch, asserted by name over the whole run -----------
    allnames = {g[0] for _, rowset in wins for _, a, g in rowset
                if a == "/cutit/param" and g}
    A.check("NO reserved selector EVER becomes a parameter name",
            not (allnames & RESERVED),
            "param names seen: " + (", ".join(sorted(allnames)) or "(none)"))

    # -- idle: the 2 s repeat, and nothing else -------------------------------
    for win in ("idle", "idle2"):
        n_hb = len(rows(win, "/cutit/hb"))
        t = span(win) or 3.0
        A.check("%s: heartbeat at ~2 Hz" % win, abs(n_hb / t - HB_HZ) < 0.9,
                "%d beats in %.1f s" % (n_hb, t))
        for addr, label in (("/cutit/param", "param"), ("/cutit/status", "status")):
            n = len(rows(win, addr))
            A.check("%s: %s traffic is the 2 s repeat and no more" % (win, label), n <= 3,
                    "%d packets in %.1f s" % (n, t))

    # Nothing has been sent yet in the first idle window, so the repeat fires
    # against an empty store.
    A.check("idle: the repeat carries NO arguments before anything has been sent",
            all(len(g) == 0 for _, _, g in rows("idle", "/cutit/param")),
            "%d packets, args %s" % (len(rows("idle", "/cutit/param")),
                                     [len(g) for _, _, g in rows("idle", "/cutit/param")]))

    seen = {(g[0], g[1]) for _, _, g in rows("idle2", "/cutit/param") if len(g) >= 2}
    A.check("idle2: every repeat carries one identical value -- a repeat, not new data",
            len(seen) <= 1,
            "distinct values: %s" % sorted(seen))

    # -- sweep1: the rate limit and the trailing edge -------------------------
    n = len(rows("sweep1", "/cutit/param"))
    t = span("sweep1") or 3.0
    A.check("sweep1: the sweep reached the wire at all", n >= 15, "%d packets" % n)
    A.check("sweep1: 401 events coalesced to <= ~20 Hz", n <= LIMIT_HZ * 2.0 + 20,
            "%d packets for 401 disp messages" % n)
    lb = last_by_name("sweep1")
    A.check("sweep1: TRAILING EDGE -- last grain is 400", lb.get("grain") == 400,
            "got %s" % lb.get("grain"))
    A.check("sweep1: only grain was sent", set(lb) == {"grain"},
            ", ".join(sorted(lb)))

    # -- sweep2: two names at once, the single-slot killer --------------------
    lb = last_by_name("sweep2")
    n = len(rows("sweep2", "/cutit/param"))
    A.check("sweep2: BOTH names keep their own trailing edge",
            lb.get("grain") == 400 and lb.get("speed") == 400,
            "grain=%s speed=%s" % (lb.get("grain"), lb.get("speed")))
    A.check("sweep2: two simultaneous sweeps stay bounded",
            n <= LIMIT_HZ * 2.0 * 2 + 30, "%d packets" % n)

    # -- status --------------------------------------------------------------
    st = rows("statussw", "/cutit/status")
    A.check("statussw: status reached the wire", len(st) >= 10, "%d" % len(st))
    A.check("statussw: status is rate limited too",
            len(st) <= LIMIT_HZ * 2.0 + 20, "%d packets" % len(st))
    A.check("statussw: TRAILING EDGE -- last status is 400-bpm",
            st and st[-1][2] and st[-1][2][0] == "400-bpm",
            "got %s" % (st[-1][2][0] if st and st[-1][2] else None))
    sw_names = {g[0] for _, _, g in rows("statussw", "/cutit/param") if g}
    A.check("statussw: status did not leak onto the param address",
            not any(n.endswith("-bpm") for n in sw_names),
            "param names in that window: " + (", ".join(sorted(sw_names)) or "(none)"))

    # -- alert is STATE, not an event ----------------------------------------
    al = rows("alert", "/cutit/alert")
    body = [g for _, _, g in al if len(g) >= 4 and g[1] != "none"]
    A.check("alert: the alert reached the wire", bool(body), "%d carried one" % len(body))
    if body:
        g = body[-1]
        A.check("alert: level, source and text all survive",
                g[1] == "fail" and g[2] == "u_bench" and g[3] == "boom", " ".join(map(str, g[1:])))
        A.check("alert: the count incremented", g[0] >= 1, "count=%s" % g[0])
    after = [g for _, _, g in rows("idle2", "/cutit/alert") if len(g) >= 4]
    A.check("alert: PERSISTS as state, repeated on later heartbeats",
            after and all(x[3] == "boom" for x in after),
            "%d repeats in idle2" % len(after))

    # -- the reserved selectors must be swallowed ----------------------------
    res_names = {g[0] for _, _, g in rows("reserved", "/cutit/param") if g}
    A.check("reserved: in-l / in-r / grid / led / modal / diag never become parameters",
            not (res_names & RESERVED),
            "param names in that window: " + (", ".join(sorted(res_names)) or "(none)"))
    A.check("reserved: seven reserved messages produced no traffic beyond the repeat",
            len(rows("reserved", "/cutit/param")) <= 3
            and len(rows("reserved", "/cutit/status")) <= 3,
            "%d param, %d status" % (len(rows("reserved", "/cutit/param")),
                                     len(rows("reserved", "/cutit/status"))))

    # -- the inbound half, window by window -----------------------------------
    # Exact counts: "at least one ack" passes a route that fires every branch.
    def args(win, addr):
        return [g for _, a, g in rows(win, addr) if a == addr]

    def one(win, addr, want, label):
        got = args(win, addr)
        A.check("%s: %s" % (win, label), len(got) == 1 and got[0] == want,
                "wanted exactly one %s %s, got %s" % (addr, want, got))

    def none_of(win, addrs, label):
        got = {a: args(win, a) for a in addrs}
        A.check("%s: %s" % (win, label), not any(got.values()),
                "; ".join("%s %s" % (a, v) for a, v in got.items() if v) or "(silent)")

    CMD = ["/probe/presence", "/probe/volca", "/probe/drums", "/cutit/ack"]

    one("cmdwire", "/cutit/ack", ["re-wire"], "re-wire is acknowledged")
    one("cmdwire", "/probe/presence", ["re-wire"],
        "re-wire reaches u_present ON THE BUS -- one owner of the recovery")
    none_of("cmdwire", ["/probe/volca", "/probe/drums"],
            "re-wire left by neither outlet")

    one("cmdvolca", "/probe/volca", ["notes", 60.0, 100.0, 200.0],
        "test-note m_volca fires ONE note out the Volca's own outlet")
    one("cmdvolca", "/cutit/ack", ["test-note", "m_volca"],
        "and acknowledges the device it fired at")
    none_of("cmdvolca", ["/probe/drums", "/probe/presence"],
            "it touched neither c_steps nor the re-wire")

    # The SP-404 left the rig (2026-11-04), and its test note with it: u_net
    # routes one device now, so the old button's command is an unknown one.
    none_of("cmd404", CMD,
            "⛔ test-note m_404 REACHES NOTHING now the 404 is gone -- no ack, no bus, "
            "neither outlet")
    A.check("cmd404: the link was LIVE while it was ignored",
            len(args("cmd404", "/cutit/hb")) >= 2,
            "%d heartbeats in that window" % len(args("cmd404", "/cutit/hb")))

    # Five malformed commands: two selectors off the list, a device off its
    # list, a bare `404` (route reads it as a float and can never match), and a
    # well-formed command under another OSC root.
    none_of("cmdbogus", CMD,
            "⛔ FIVE WRONG COMMANDS REACH NOTHING AT ALL -- no ack, no bus, "
            "neither outlet")
    one("cmddrumsnew", "/probe/drums", ["reload", 2.0],
        "⛔ a drums command u_net has never heard of goes to c_steps whole, to refuse")
    none_of("cmddrumsnew", ["/cutit/ack"], "and is not acknowledged")
    none_of("cmddrumsnew", ["/probe/volca", "/probe/presence"],
            "and reaches nothing else")
    A.check("cmdbogus: the link was LIVE while they were ignored",
            len(args("cmdbogus", "/cutit/hb")) >= 2,
            "%d heartbeats in that window" % len(args("cmdbogus", "/cutit/hb")))

    one("cmdclear", "/cutit/ack", ["clear-alert"], "clear-alert is acknowledged")
    before = [g for g in args("idle2", "/cutit/alert") if len(g) >= 4]
    after = [g for g in args("done", "/cutit/alert") if len(g) >= 4]
    A.check("clear-alert: the alert was still held on the repeat BEFORE the clear",
            bool(before) and all(g[3] == "boom" for g in before),
            "%d repeats carrying %s" % (len(before), {g[3] for g in before}))
    A.check("⛔ clear-alert: and the repeat carries the EMPTY alert afterwards",
            bool(after) and all(g[1] == "none" and g[3] == "-" for g in after),
            "%d repeats carrying %s" % (len(after), [g[1:] for g in after]))
    none_of("cmdclear", ["/probe/volca", "/probe/drums", "/probe/presence"],
            "clearing the alert sounded nothing and re-wired nothing")

    # -- test mode, and the checklist page's two commands ---------------------
    def hb_flags(win):
        return [g[1] if len(g) > 1 else None for g in args(win, "/cutit/hb")]

    for win in ("idle", "cmdclear", "sendoff"):
        f = hb_flags(win)
        A.check("%s: the heartbeat says test mode is off" % win,
                f and all(v == 0 for v in f), f)
    none_of("sendoff", CMD, "⛔ send is no command now: with test mode off it reaches nothing, "
            "and nothing answers")

    one("tmon", "/probe/err", ["warn", "u_net", "test-mode-on"],
        "flipping test mode on warns, so the OLED and the log both say so")
    # A flip sends a heartbeat at once, so the phone turns to its checklists at the tap; the
    # 2 Hz beat alone left it waiting up to half a second.
    for win, flag in (("tmon", 1), ("tmoff", 0)):
        first = next((t for t, a, g in got.get(win, []) if a == "/cutit/hb"
                      and len(g) > 1 and g[1] == flag), None)
        A.check("%s: the heartbeat saying so arrives at once, not at the next beat" % win,
                first is not None and first - MARK_T[win] < 0.06,
                "%s ms after the flip" % (None if first is None
                                          else round((first - MARK_T[win]) * 1000)))
    f = hb_flags("tmmodeon")
    A.check("tmmodeon: test mode on again", f and all(v == 1 for v in f), f)
    f = hb_flags("tmmode")
    A.check("⛔ tmmode: a mode chosen in test mode turns it off, so its screen comes back",
            f and all(v == 0 for v in f), f)
    one("tmmode", "/probe/err", ["info", "u_net", "test-mode-off"], "and says so, as a flip does")
    for win in ("tmon", "sendon", "result"):
        f = hb_flags(win)
        A.check("%s: the heartbeat says test mode is on" % win,
                f and all(v == 1 for v in f), f)
    none_of("sendon", CMD, "⛔ nor with it on: nothing from the phone reaches the buses "
            "(Brendan, 2026-11-04)")

    one("result", "/probe/err", ["info", "phone", "tempo-2-pass"],
        "a result is logged as info phone <verdict>")
    one("result", "/cutit/ack", ["result"], "and acknowledged")

    one("tmoff", "/probe/err", ["info", "u_net", "test-mode-off"],
        "flipping it off is logged, and draws nothing")
    f = hb_flags("sendoff2")
    A.check("sendoff2: the heartbeat says test mode is off again",
            f and all(v == 0 for v in f), f)
    none_of("sendoff2", CMD, "and send still reaches nothing")

    one("tmtwice", "/probe/err", ["warn", "u_net", "test-mode-on"],
        "⛔ two flips at once are one: a doubled key press turns test mode on and leaves it")
    f = hb_flags("tmtwice")
    A.check("tmtwice: and the heartbeat says on", f and all(v == 1 for v in f), f)
    one("tmoff2", "/probe/err", ["info", "u_net", "test-mode-off"],
        "a flip after the 300 ms turns it off")
    f = hb_flags("done")
    A.check("done: the heartbeat says off", f and all(v == 0 for v in f), f)

    one("cmdselect", "/probe/drums", ["select", 3.0], "drums select 3 leaves for c_steps")
    one("cmdselect", "/cutit/ack", ["drums", "select"], "and is acknowledged")
    state = [float(v) for v in ("1 12 2 1 16 5 " + "16 " * 14 + "0 1 " + "0 " * 14
                                + "7 8 30 20 0").split()]
    sent = args("drumstate", "/cutit/drums")
    A.check("drumstate: c_steps' state leaves as /cutit/drums, at once and on the heartbeat",
            len(sent) >= 2 and all(g == state for g in sent),
            "%d sent: %s" % (len(sent), sent[:1]))
    sent = args("drumstate", "/cutit/mode")
    A.check("drumstate: the page leaves alone as /cutit/mode, at once and on the heartbeat",
            len(sent) >= 2 and all(g == ["mode-1"] for g in sent), sent[:3])

    A.check("done: both still repeat, so a phone that comes back late catches up",
            len(args("done", "/cutit/drums")) >= 2 and len(args("done", "/cutit/mode")) >= 2,
            "%d and %d" % (len(args("done", "/cutit/drums")), len(args("done", "/cutit/mode"))))

    for win, cmd, rest in (("cmdsync", "sync", []), ("cmdsnap", "snap", []),
                           ("cmdnum", "num", [1.0]), ("cmdden", "den", [-1.0]),
                           ("cmddrunk", "drunk", [30.0]), ("cmdskip", "skip", [20.0]),
                           ("cmdmove", "move", [0.0])):
        said = " ".join([cmd] + ["%g" % v for v in rest])
        one(win, "/probe/drums", [cmd] + rest, "drums %s leaves for c_steps as %s" % (said, said))
        if cmd in DRUMS_QUIET:
            none_of(win, ["/cutit/ack"], "and is not acknowledged: the drum screen's state says it")
        else:
            one(win, "/cutit/ack", ["drums", cmd], "and is acknowledged")
        none_of(win, ["/probe/volca", "/probe/presence"],
                "and reaches nothing else")

    rc = 1 if A.report() else 0
    if rc:
        print("\n--- pd output ---\n" + log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
