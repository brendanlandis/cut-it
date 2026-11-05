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
KEEP = "--keep" in sys.argv
WORK = S.work_dir("phone")
DRIVE = os.path.join(WORK, "drive.pd")

# The coalescer's target. u_net flushes the tempo on a 50 ms tick, so a window of
# T seconds can hold at most 20*T packets, plus edge effects.
LIMIT_HZ = 20.0
HB_HZ = 2.0
ADDRS = {"/cutit/hb", "/cutit/ack", "/mark",
         # what the phone shows: the mode, c_steps' state, c_synth's choice and
         # velocity switch, the tempo, and u_song's sections and songs
         "/cutit/mode", "/cutit/drums", "/cutit/synth", "/cutit/velocity", "/cutit/tempo",
         "/cutit/sections", "/cutit/songs",
         # the driver's taps for the inbound half: u_net's four outlets, err,
         # and the presence bus, which re-wire once wrote and must not now
         "/probe/drums", "/probe/synth", "/probe/tempo", "/probe/sections", "/probe/err",
         "/probe/presence"}
# The state addresses, each sent on a change and again on every heartbeat.
STATE = ("/cutit/mode", "/cutit/drums", "/cutit/synth", "/cutit/velocity", "/cutit/tempo",
         "/cutit/sections", "/cutit/songs")
# The sections page's commands u_net acknowledges, a button's flash: the rest show in the state.
SECTIONS_ACKED = ["new", "up", "down", "delete", "name"]
# The songs page's, the same way: the rest show in the state, or u_song refuses them.
SONGS_ACKED = ["load", "new", "add", "delete", "up", "down", "new-set", "remove", "name",
               "set-name"]
# The OLED's mirror, gone (Brendan, 2026-11-04): u_net reads nothing on disp, so
# none of these may ever leave it.
GONE = ["/cutit/param", "/cutit/status", "/cutit/alert"]
# What u_net does not acknowledge: the screens' state shows each.
DRUMS_QUIET = ["num", "den", "drunk", "vol", "pitch", "set-track-last", "randomness",
               "set-swing", "set-last"]
WINDOWS = ["idle", "dispsweep", "dispother", "tempo", "tpsweep", "idle2", "cmdwire",
           "cmdclear", "cmdvolca", "cmdbogus", "sendoff", "tmon", "sendon", "result",
           "tmoff", "sendoff2", "tmtwice", "tmoff2", "cmdsync", "cmdsnap", "cmdselect",
           "cmdnum", "cmdden", "cmddrunk", "cmdvol", "cmdpitch", "cmdtracklast", "cmdrand",
           "cmdswing", "cmdlast",
           "cmddrumsnew", "cmdsynth", "cmdsynthnew", "cmdtempo", "cmdtemponew", "cmdvel",
           "cmdvelnew", "tmmodeon", "tmmode", "drumstate", "cmdsecsel", "cmdsecpage", "cmdsecnew",
           "cmdsecup", "cmdsecdown", "cmdseclen", "cmdsecdel", "cmdsecname", "cmdsecnew2",
           "secstate", "cmdsongs", "songstate", "done"]


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


def reads_disp():
    """u_net's receives of disp, by record: a [r disp] or [receive disp] box."""
    return [r for r in lib_pd.read(UNET)
            if re.match(r"^#X obj -?\d+ -?\d+ (r|receive) disp;$", r)]


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

    # -- the OLED's mirror is gone (Brendan, 2026-11-04) ---------------------
    A.check("⛔ u_net reads nothing on disp: the OLED's traffic is not the phone's",
            not reads_disp(), "u_net still has %s" % reads_disp())
    gone = sorted({a for _, rowset in wins for _, a, _ in rowset if a in GONE})
    A.check("⛔ NOTHING ever leaves as /cutit/param, /cutit/status or /cutit/alert",
            not gone, "saw %s -- the phone copying the OLED again" % gone)

    # -- shape ---------------------------------------------------------------
    seen = sorted({a for _, rowset in wins for _, a, _ in rowset})
    A.check("shape: only known OSC addresses", all(a in ADDRS for a in seen),
            "saw " + ", ".join(seen))
    A.check("shape: all %d windows arrived" % len(WINDOWS),
            [n for n, _ in wins] == WINDOWS, ", ".join(n for n, _ in wins))

    hbs = [g[0] for _, rowset in wins for _, a, g in rowset
           if a == "/cutit/hb" and g]
    A.check("heartbeat counter is strictly monotonic",
            hbs == sorted(hbs) and len(set(hbs)) == len(hbs),
            "%d beats" % len(hbs))

    def args(win, addr):
        return [g for _, a, g in rows(win, addr) if a == addr]

    # -- idle: the heartbeat, and the empty tempo store ------------------------
    for win in ("idle", "idle2"):
        n_hb = len(rows(win, "/cutit/hb"))
        t = span(win) or 2.0
        A.check("%s: heartbeat at ~2 Hz" % win, abs(n_hb / t - HB_HZ) < 0.9,
                "%d beats in %.1f s" % (n_hb, t))
    early = args("idle", "/cutit/tempo")
    A.check("idle: before any BPM the tempo's repeat carries nothing, on every heartbeat",
            len(early) >= 2 and all(g == [] for g in early), early[:4])

    # -- what the OLED is told reaches nothing ---------------------------------
    for win in ("dispsweep", "dispother"):
        extra = sorted({a for _, a, _ in rows(win)} - {"/cutit/hb"} - set(STATE))
        A.check("⛔ %s: disp traffic puts nothing on the wire but the heartbeat's repeats" % win,
                not extra and all(g == [] for g in args(win, "/cutit/tempo")),
                "saw %s, tempo %s" % (extra, args(win, "/cutit/tempo")[:3]))

    # -- the tempo -------------------------------------------------------------
    first = next((t for t, a, g in got.get("tempo", []) if a == "/cutit/tempo" and g == [120.0]),
                 None)
    A.check("tempo: u_tempo's 120 leaves as /cutit/tempo 120 within a tick",
            first is not None and first - MARK_T["tempo"] < 0.12,
            "%s ms after it went in" % (None if first is None
                                        else round((first - MARK_T["tempo"]) * 1000)))
    A.check("tempo: and again on every heartbeat, 120 each time",
            len(args("tempo", "/cutit/tempo")) >= 3
            and all(g == [120.0] for g in args("tempo", "/cutit/tempo")),
            args("tempo", "/cutit/tempo")[:5])
    sw = args("tpsweep", "/cutit/tempo")
    A.check("tpsweep: the sweep reached the wire", len(sw) >= 15, "%d packets" % len(sw))
    A.check("⛔ tpsweep: 401 BPMs coalesced to <= ~20 Hz", len(sw) <= LIMIT_HZ * 2.0 + 20,
            "%d packets for 401 BPMs -- a knob-1 sweep is some 200 a second" % len(sw))
    A.check("tpsweep: TRAILING EDGE -- the last tempo is 400",
            bool(sw) and sw[-1] == [400.0], "got %s" % (sw[-1] if sw else None))
    rep = args("idle2", "/cutit/tempo")
    A.check("idle2: the tempo repeats on the heartbeat, the last value and no other",
            2 <= len(rep) <= 6 and all(g == [400.0] for g in rep), rep)

    # -- the inbound half, window by window -----------------------------------
    # Exact counts: "at least one ack" passes a route that fires every branch.
    def one(win, addr, want, label):
        got_ = args(win, addr)
        A.check("%s: %s" % (win, label), len(got_) == 1 and got_[0] == want,
                "wanted exactly one %s %s, got %s" % (addr, want, got_))

    def none_of(win, addrs, label):
        got_ = {a: args(win, a) for a in addrs}
        A.check("%s: %s" % (win, label), not any(got_.values()),
                "; ".join("%s %s" % (a, v) for a, v in got_.items() if v) or "(silent)")

    CMD = ["/probe/presence", "/probe/drums", "/probe/synth", "/probe/tempo", "/probe/sections",
           "/cutit/ack"]

    for win, cmd in (("cmdwire", "re-wire"), ("cmdclear", "clear-alert"),
                     ("cmdvolca", "test-note m_volca")):
        none_of(win, CMD, "⛔ %s, a remote-screen button no longer, REACHES NOTHING -- no ack, "
                "no bus, no outlet (Brendan, 2026-11-04)" % cmd)
        A.check("%s: the link was LIVE while it was ignored" % win,
                len(args(win, "/cutit/hb")) >= 2,
                "%d heartbeats in that window" % len(args(win, "/cutit/hb")))
    held = [g for w in ("cmdclear", "cmdvolca") for g in args(w, "/cutit/tempo")]
    A.check("the held state rides through them: the tempo still repeats 400",
            held and all(g == [400.0] for g in held), held[:3])

    # Six malformed commands: two selectors off the list, the test notes of
    # three devices, a bare `404` (route reads it as a float), and a well-formed
    # tempo under another OSC root.
    none_of("cmdbogus", CMD,
            "⛔ SIX WRONG COMMANDS REACH NOTHING AT ALL -- no ack, no bus, no outlet")
    A.check("cmdbogus: the link was LIVE while they were ignored",
            len(args("cmdbogus", "/cutit/hb")) >= 2,
            "%d heartbeats in that window" % len(args("cmdbogus", "/cutit/hb")))

    one("cmddrumsnew", "/probe/drums", ["reload", 2.0],
        "⛔ a drums command u_net has never heard of goes to c_steps whole, to refuse")
    none_of("cmddrumsnew", ["/cutit/ack", "/probe/synth", "/probe/tempo", "/probe/presence"],
            "and is not acknowledged, and reaches nothing else")

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
    A.check("⛔ tmmode: a mode chosen in test mode turns it off, so its page comes back",
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
    state = [float(v) for v in [1, 12, 2, 1, 16, 5] + [16] * 14 + [0, 1] + [0] * 14
             + [7, 8, 30, 62] + [0, -6] + [0] * 14 + [0, 7] + [0] * 14 + [0, 40] + [0] * 14]
    sent = args("drumstate", "/cutit/drums")
    A.check("drumstate: c_steps' 88 numbers leave as /cutit/drums, at once and on the heartbeat",
            len(sent) >= 2 and all(g == state for g in sent),
            "%d sent: %s" % (len(sent), sent[:1]))
    sent = args("drumstate", "/cutit/mode")
    A.check("drumstate: the page leaves alone as /cutit/mode, at once and on the heartbeat",
            len(sent) >= 2 and all(g == ["mode-2"] for g in sent), sent[:3])
    sent = args("drumstate", "/cutit/synth")
    A.check("⛔ drumstate: c_synth's choice leaves as /cutit/synth fm, at once and on the heartbeat",
            len(sent) >= 2 and all(g == ["fm"] for g in sent), sent[:3])
    sent = args("drumstate", "/cutit/velocity")
    A.check("⛔ drumstate: its velocity switch leaves as /cutit/velocity off, at once and on the "
            "heartbeat", len(sent) >= 2 and all(g == ["off"] for g in sent), sent[:3])
    A.check("done: all seven still repeat, so a phone that comes back late catches up",
            min(len(args("done", a)) for a in STATE) >= 2,
            ", ".join("%d" % len(args("done", a)) for a in STATE))
    early = [g for w in ("idle", "cmdwire", "tmmode") for a in ("/cutit/synth", "/cutit/velocity")
             for g in args(w, a)]
    A.check("before c_synth says anything, the repeats carry no choice and no switch",
            early and all(g == [] for g in early), early[:3])

    # -- the sections page (ref/module/songs.md) -------------------------------
    sec = ["song 1", 3.0, 2.0, 1.0, 1.0, "verse 2", 8.0, 1.0, "intro", 0.0, 2.0, "verse 2", 8.0,
           3.0, "chorus", 0.0, 0.0, "-", 0.0, 0.0, "-", 0.0]
    sent = args("secstate", "/cutit/sections")
    A.check("⛔ secstate: u_song's 22 atoms leave as /cutit/sections, at once and on the "
            "heartbeat, a name with a space one string", len(sent) >= 2 and all(g == sec for g in sent),
            "%d sent: %s" % (len(sent), sent[:1]))
    early = [g for w in ("idle", "cmdwire", "drumstate") for g in args(w, "/cutit/sections")]
    A.check("before u_song says anything, the repeats carry no sections",
            early and all(g == [] for g in early), early[:3])
    for win, cmd, rest in (("cmdsecsel", "select", [2.0]), ("cmdsecpage", "page", [1.0]),
                           ("cmdsecnew", "new", []), ("cmdsecup", "up", []),
                           ("cmdsecdown", "down", []), ("cmdseclen", "length", [8.0]),
                           ("cmdsecdel", "delete", []), ("cmdsecname", "name", ["verse 2"]),
                           ("cmdsecnew2", "shuffle", [])):
        said = " ".join([cmd] + ["%s" % (("%g" % v) if isinstance(v, float) else v)
                                 for v in rest])
        one(win, "/probe/sections", [cmd] + rest,
            "⛔ sections %s leaves for u_song as %s" % (said, said)
            if cmd in ("name", "shuffle") else "sections %s leaves for u_song" % said)
        if cmd in SECTIONS_ACKED:
            one(win, "/cutit/ack", ["sections", cmd], "and is acknowledged")
        else:
            none_of(win, ["/cutit/ack"], "and is not acknowledged: the state says it, or u_song "
                    "refuses it" if cmd == "shuffle" else "and is not acknowledged: the state says it")
        none_of(win, ["/probe/drums", "/probe/synth", "/probe/tempo", "/probe/presence"],
                "and reaches nothing else")

    # -- the songs page (ref/module/songs.md) ----------------------------------
    cmds = [["songs", "select", 2.0], ["songs", "page", 1.0], ["songs", "load"], ["songs", "new"],
            ["songs", "name", "hollow bell"], ["songs", "add"], ["songs", "delete"],
            ["songs", "entry", 3.0], ["songs", "set", -1.0], ["songs", "up"], ["songs", "down"],
            ["songs", "starts", "go"], ["songs", "new-set"], ["songs", "remove"],
            ["songs", "set-name", "friday"], ["songs", "shuffle"]]
    heard = args("cmdsongs", "/probe/sections")
    A.check("⛔ cmdsongs: each songs command leaves for u_song as it came, songs in front, in "
            "order, a name with a space one string", heard == cmds,
            "wanted %d, got %d: %s" % (len(cmds), len(heard), heard[:4]))
    acks = args("cmdsongs", "/cutit/ack")
    A.check("⛔ ... and the ten a button shows are acknowledged, ack songs <action>, the rest not",
            acks == [["songs", c[1]] for c in cmds if c[1] in SONGS_ACKED], acks)
    none_of("cmdsongs", ["/probe/drums", "/probe/synth", "/probe/tempo", "/probe/presence"],
            "and they reach nothing else")
    songs_ = (["songs"] + [3.0, 1.0, 1.0, 1.0, "night drive", 1.0, "night drive", "loaded", 2.0,
               "lantern", "-", 3.0, "hollow bell", "next bar", 0.0, "-", "-", 0.0, "-", "-", 0.0,
               "-", "-", 1.0, 2.0, "gig", 1.0, 1.0, 3.0, 1.0, "lantern", "silence", 1.0,
               "lantern", "silence", 2.0, "hollow bell", "next-bar", 3.0, "night drive", "go",
               0.0, "-", "-", 0.0, "-", "-"])[1:]
    sent = args("songstate", "/cutit/songs")
    A.check("⛔ songstate: u_song's songs page, its 47 atoms, leaves as /cutit/songs, at once and "
            "on the heartbeat", len(sent) >= 2 and all(g == songs_ for g in sent),
            "%d sent: %s" % (len(sent), sent[:1]))
    A.check("⛔ ... and /cutit/sections goes on saying the sections page, untouched by it",
            args("songstate", "/cutit/sections") and
            all(g == sec for g in args("songstate", "/cutit/sections")),
            args("songstate", "/cutit/sections")[:1])
    early = [g for w in ("idle", "secstate") for g in args(w, "/cutit/songs")]
    A.check("before u_song says anything of its songs, the repeats carry none",
            early and all(g == [] for g in early), early[:3])

    one("cmdsynth", "/probe/synth", ["synth", "strings"], "synth strings leaves for c_synth")
    one("cmdsynth", "/cutit/ack", ["synth", "strings"], "and is acknowledged")
    none_of("cmdsynth", ["/probe/drums", "/probe/tempo", "/probe/presence"],
            "and reaches nothing else")
    one("cmdsynthnew", "/probe/synth", ["synth", "organ"],
        "⛔ a synth u_net has never heard of goes to c_synth whole, to refuse")
    none_of("cmdsynthnew", ["/cutit/ack"], "and is not acknowledged")

    one("cmdtempo", "/probe/tempo", ["tempo", 133.0], "⛔ tempo 133 leaves for u_tempo")
    none_of("cmdtempo", ["/cutit/ack", "/probe/drums", "/probe/synth", "/probe/presence"],
            "and is not acknowledged -- the tempo that comes back says it -- and reaches "
            "nothing else")
    one("cmdtemponew", "/probe/tempo", ["tempo", "fast"],
        "a tempo that is no number goes to u_tempo whole, to refuse as bad-tempo")
    none_of("cmdtemponew", ["/cutit/ack"], "and is not acknowledged")

    one("cmdvel", "/probe/synth", ["velocity", "off"], "⛔ velocity off leaves for c_synth")
    one("cmdvel", "/cutit/ack", ["velocity", "off"], "and is acknowledged")
    none_of("cmdvel", ["/probe/drums", "/probe/tempo", "/probe/presence"],
            "and reaches nothing else")
    one("cmdvelnew", "/probe/synth", ["velocity", "loud"],
        "a setting u_net has never heard of goes to c_synth whole, to refuse as bad-velocity")
    none_of("cmdvelnew", ["/cutit/ack"], "and is not acknowledged")

    for win, cmd, rest in (("cmdsync", "sync", []), ("cmdsnap", "snap", []),
                           ("cmdnum", "num", [1.0]), ("cmdden", "den", [-1.0]),
                           ("cmddrunk", "drunk", [30.0]), ("cmdvol", "vol", [3.0, -6.0]),
                           ("cmdpitch", "pitch", [3.0, 7.0]),
                           ("cmdtracklast", "set-track-last", [3.0, 9.0]),
                           ("cmdrand", "randomness", [3.0, 40.0]),
                           ("cmdswing", "set-swing", [62.0]),
                           ("cmdlast", "set-last", [12.0])):
        said = " ".join([cmd] + ["%g" % v for v in rest])
        one(win, "/probe/drums", [cmd] + rest, "drums %s leaves for c_steps as %s" % (said, said))
        if cmd in DRUMS_QUIET:
            none_of(win, ["/cutit/ack"], "and is not acknowledged: the screens' state says it")
        else:
            one(win, "/cutit/ack", ["drums", cmd], "and is acknowledged")
        none_of(win, ["/probe/synth", "/probe/tempo", "/probe/presence"],
                "and reaches nothing else")

    rc = 1 if A.report() else 0
    if rc:
        print("\n--- pd output ---\n" + log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
