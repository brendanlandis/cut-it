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
import socket
import struct
import subprocess
import sys
import threading
import time

PORT = 9995
PD = os.environ.get(
    "PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")
HERE = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.join(HERE, "phone-assert-drive.pd")

# The coalescer's target. u_net flushes on a 50 ms tick, so a window of T
# seconds can hold at most 20*T packets per distinct name, plus edge effects.
LIMIT_HZ = 20.0
HB_HZ = 2.0
ADDRS = {"/cutit/param", "/cutit/status", "/cutit/hb", "/cutit/alert", "/mark"}
# every selector g_oled routes that is NOT a parameter. u_net matches all of
# them and leaves them unconnected; if one ever reaches the wire as a parameter
# name, the reserved branch is broken.
RESERVED = {"in-l", "in-r", "led", "grid", "modal", "modal-off", "alert", "status"}


# ----------------------------------------------------------------- OSC decoding
def _pad(n):
    return (n + 3) & ~3


def _string(buf, i):
    end = buf.index(b"\0", i)
    return buf[i:end].decode("ascii", "replace"), i + _pad(end - i + 1)


def decode(buf):
    """Return (address, [args]) or None if this is not an OSC message."""
    try:
        addr, i = _string(buf, 0)
        if not addr.startswith("/"):
            return None
        tags, i = _string(buf, i)
        if not tags.startswith(","):
            return None
        args = []
        for t in tags[1:]:
            if t == "f":
                args.append(struct.unpack_from(">f", buf, i)[0])
                i += 4
            elif t == "i":
                args.append(struct.unpack_from(">i", buf, i)[0])
                i += 4
            elif t == "s":
                s, i = _string(buf, i)
                args.append(s)
            elif t == "b":
                n = struct.unpack_from(">i", buf, i)[0]
                args.append(buf[i + 4:i + 4 + n])
                i += 4 + _pad(n)
            else:
                return None
        return addr, args
    except Exception:
        return None


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
         "-path", os.path.join(HERE, os.pardir, "mac-stubs"), DRIVE],
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

    # -- shape ---------------------------------------------------------------
    seen = sorted({a for _, rowset in wins for _, a, _ in rowset})
    ck(all(a in ADDRS for a in seen), "shape: only known OSC addresses",
       "saw " + ", ".join(seen))
    ck([n for n, _ in wins] == ["idle", "sweep1", "sweep2", "statussw",
                                "alert", "reserved", "idle2", "done"],
       "shape: all eight windows arrived",
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
       "reserved: in-l / in-r / grid / led / modal never become parameters",
       "param names in that window: " + (", ".join(sorted(res_names)) or "(none)"))
    ck(len(rows("reserved", "/cutit/param")) <= 3
       and len(rows("reserved", "/cutit/status")) <= 3,
       "reserved: six reserved messages produced no traffic beyond the repeat",
       "%d param, %d status" % (len(rows("reserved", "/cutit/param")),
                                len(rows("reserved", "/cutit/status"))))

    print()
    rc = ck.report()
    if rc:
        print("\n--- pd output ---\n" + log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
