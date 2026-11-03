#!/usr/bin/env python3
"""u_inject's headless gate -- test/checklists/README.md, Send lines. No eyes, no
hardware, ~8 s.

    python3 test/gate/inject-assert.py [-v] [--keep]     (run it as inject-assert.sh)

Writes a driver that makes u_inject and a tap on every bus a Send line could
name, launches Pd, and sends the lines through tools/send.sh itself, so the
splitting the tool does is under test with the patch. -v prints the detail
behind every check; --keep leaves the driver and Pd's console behind.
"""
import atexit
import os
import re
import shutil
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_scratch as S                                         # noqa: E402

ROOT = S.ROOT
KEEP = "--keep" in sys.argv
WORK = S.work_dir("inject")
DRIVE = os.path.join(WORK, "drive.pd")
SEND = os.path.join(ROOT, "tools", "send.sh")
PDSEND = os.path.join(os.path.dirname(S.PD), "pdsend")
# The suite hands every gate its own u_net port; by hand this one keeps a number
# of its own, so main-dev.pd open in Pd (9002, and so 11002) cannot hold it.
INPORT = int(os.environ.get("CUTIT_INPORT") or 9993)
PORT = INPORT + 2000

ALLOWED = ["disp", "err", "mode", "panic", "param", "start", "stop", "tempo"]
# The rest of C-2's global names: reachable by a control, never by a Send line.
REFUSED = ["clock", "state", "presence", "recover"]

# What each allowed bus must receive, in this order, from one Send line.
LINE = ("disp chop-size 43 %; err warn u_root test-warn; mode compose mode-1; "
        "panic bang; param og-knob-1 0; start bang; stop bang; tempo 120")
WANT = ["got-disp: chop-size 43 %", "got-err: warn u_root test-warn",
        "got-mode: compose mode-1", "got-panic: bang", "got-param: og-knob-1 0",
        "got-start: bang", "got-stop: bang", "got-tempo: 120"]
# pd quit first: if it got through, nothing after it would arrive.
REFUSE_LINE = ("pd quit; pd dsp 1; clock 1; state section-1-drums 0; "
               "presence lost m_nano; recover bang; foo bar")
AFTER = "disp after-refused 1"


def driver():
    """u_inject under test, one with no argument, and a print on every bus."""
    B, C = [], []

    def box(kind, x, y, s):
        B.append("#X %s %d %d %s;" % (kind, x, y, s))
        return len(B) - 1

    box("text", 20, 20, "inject-assert-drive -- the driver half of u_inject's gate. "
        "test/gate/inject-assert.py sends the lines and reads these prints., f 60")
    box("obj", 20, 120, "u_inject %d" % INPORT)
    box("obj", 300, 120, "u_inject")
    lb = box("obj", 600, 120, "loadbang")
    dl = box("obj", 600, 170, "del 7000")
    q = box("msg", 600, 220, "\\; pd quit")
    C += ["#X connect %d 0 %d 0;" % (lb, dl), "#X connect %d 0 %d 0;" % (dl, q)]
    for i, bus in enumerate(ALLOWED + REFUSED):
        r = box("obj", 20 + 160 * (i % 6), 320 + 120 * (i // 6), "r %s" % bus)
        p = box("obj", 20 + 160 * (i % 6), 360 + 120 * (i // 6), "print got-%s" % bus)
        C.append("#X connect %d 0 %d 0;" % (r, p))
    with open(DRIVE, "w") as fh:
        fh.write("#N canvas 20 20 1000 700 12;\n" + "\n".join(B + C) + "\n")


def bound():
    """lsof's NAME for the port, polled until Pd binds it: '' if it never does."""
    end = time.time() + 12
    while time.time() < end:
        out = subprocess.run(["lsof", "-nP", "-iUDP:%d" % PORT], capture_output=True,
                             text=True).stdout
        names = [ln.split()[-1] for ln in out.splitlines()[1:] if ln.strip()]
        if names:
            return names
        time.sleep(0.2)
    return []


def send(line):
    env = dict(os.environ, HOST="mac", PORT=str(PORT), PDSEND=PDSEND)
    return subprocess.run(["sh", SEND, line], env=env, capture_output=True, text=True)


def main():
    S.require_pd()
    if not os.path.isfile(PDSEND):
        S.fail("FAIL: no pdsend beside the Mac's Pd, at %s." % PDSEND)
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    if not KEEP:
        atexit.register(shutil.rmtree, WORK, True)
    driver()

    seen = {}

    def sender():
        seen["names"] = bound()
        if not seen["names"]:
            return
        seen["sent"] = send(LINE)
        time.sleep(0.3)
        seen["refused"] = send(REFUSE_LINE)
        time.sleep(0.3)
        seen["after"] = send(AFTER)

    th = threading.Thread(target=sender, daemon=True)
    th.start()
    print("u_inject on 127.0.0.1:%d, launching pd ..." % PORT)
    cap = os.path.join(WORK, "capture.txt")
    S.run(cap, 30, "-nogui", "-noaudio", "-nomidi", "-path", "Cut It", DRIVE)
    th.join(timeout=15)
    lines = [ln.strip() for ln in open(cap, encoding="utf-8", errors="replace")
             if ln.strip()]
    got = [ln for ln in lines if ln.startswith("got-")]

    names = seen.get("names", [])
    A.check("it listens on 127.0.0.1 alone", names and all(
        n == "127.0.0.1:%d" % PORT for n in names), names or "never bound")
    for key in ("sent", "refused", "after"):
        r = seen.get(key)
        A.check("send.sh delivers the %s line" % key, r is not None and r.returncode == 0,
                "never ran" if r is None else (r.stderr.strip() or r.returncode))

    missing = "got-err: fail u_inject inport-missing"
    flow = [ln for ln in got if ln != missing]
    A.check("each of the eight buses gets its message, in order, from one Send line",
            flow[:len(WANT)] == WANT, flow[:len(WANT)])
    leaked = [ln for ln in got if re.match(r"got-(%s):" % "|".join(REFUSED), ln)]
    A.check("clock, state, presence and recover are refused", not leaked, leaked)
    A.check("pd and an unknown name are refused, and Pd is still there after pd quit",
            flow[len(WANT):] == ["got-disp: after-refused 1"], flow[len(WANT):])
    A.check("a missing port says fail u_inject inport-missing, once",
            got.count(missing) == 1, got)
    rest = [ln for ln in lines if not ln.startswith("got-")]
    A.check("nothing else reaches Pd's console", not rest, rest)
    sys.exit(1 if A.report() else 0)


if __name__ == "__main__":
    main()
