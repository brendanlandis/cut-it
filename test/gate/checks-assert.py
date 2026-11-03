#!/usr/bin/env python3
"""The phone's checklist page, headless -- test/checklists/README.md. No phone, ~8 s.

    python3 test/gate/checks-assert.py [-v] [--keep]     (run it as checks-assert.sh)

The page, tools/pdparty-scene/CutItChecks, is generated from the checklists, so
this holds the committed copy to a fresh build first. Then it opens the page in
the Mac's Pd beside a driver that presses its buttons and plays the Organelle's
side of the link into #osc-in, and reads what the page draws and sends: every
label arrives on a ck-<name>-in receive name, and every command on #osc-out.
"""
import atexit
import importlib.util
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                   # noqa: E402
import lib_scratch as S                                         # noqa: E402

ROOT = S.ROOT
KEEP = "--keep" in sys.argv
WORK = S.work_dir("checks")
SCENE_DIR = os.path.join(ROOT, "tools", "pdparty-scene", "CutItChecks")
BUILD = os.path.join(ROOT, "tools", "pdparty-scene", "build-checks.py")
NBSP = " "

spec = importlib.util.spec_from_file_location("build_checks", BUILD)
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def label(sym):
    return sym.replace(NBSP, " ")


def plan():
    """The presses, worked out from the data so the gate follows the checklists:
    (mark, [action, ...]) where an action is ("press", name) or ("osc", atoms)."""
    data, _ = B.build_data()
    names = [ln.split()[0] for ln in data["lists.txt"].splitlines()]
    titles = [ln.rstrip(";").split(" ") for ln in data["titles.txt"].splitlines()]
    # the first step in the first checklist with two pages, and one with no Send
    multi = next((int(t[0]), int(t[1])) for t in titles if int(t[2]) > 1)
    sends = {}
    for ln in data["sends.txt"].splitlines():
        c, i, *rest = ln.rstrip(";").split(" ")
        sends.setdefault((int(c), int(i)), []).append(" ".join(rest))
    nosend = next((c, i) for (c, i) in [(int(t[0]), int(t[1])) for t in titles]
                  if c == 0 and (c, i) not in sends)
    many = next(k for k, v in sends.items() if k[0] == 0 and len(v) > 1)
    seq = [("start", [])]
    seq.append(("next", [("press", "next")]))                     # display 2
    seq.append(("send", [("press", "send")]))
    seq.append(("pass", [("press", "pass")]))                     # -> display 3
    seq.append(("back", [("press", "back")]))                     # -> display 2, passed
    seq.append(("fail", [("press", "fail")]))                     # -> display 3
    seq.append(("back2", [("press", "back")]))                    # -> display 2, failed
    # to the step with several Send messages
    for _ in range(many[1] - 1):
        seq.append(("walk", [("press", "next")]))
    seq.append(("many", [("press", "send")]))
    # back to the first step, and a step with no Send at all
    for _ in range(many[1]):
        seq.append(("walk", [("press", "back")]))
    for _ in range(nosend[1]):
        seq.append(("walk", [("press", "next")]))
    seq.append(("nosend", [("press", "send")]))
    seq.append(("wrap", [("press", "cprev")]))                     # -> the last checklist
    seq.append(("cnext", [("press", "cnext")]))                    # -> the first again
    for _ in range(multi[0]):
        seq.append(("walk", [("press", "cnext")]))
    for _ in range(multi[1]):
        seq.append(("walk", [("press", "next")]))
    seq.append(("page2", [("press", "next")]))
    seq.append(("page2back", [("press", "back")]))
    # the Organelle's side
    seq.append(("hbon", [("osc", "cutit hb 7 1")]))
    seq.append(("hboff", [("osc", "cutit hb 8 0")]))
    seq.append(("ack", [("osc", "cutit ack send")]))
    seq.append(("silence", []))                                    # the link times out
    seq.append(("relink", [("osc", "cutit hb 9 0")]))
    seq.append(("done", []))
    return seq, data, names, titles, sends, multi, nosend, many


def driver(seq):
    """Each window: a MARK print, then its actions, 120 ms apart; the silence
    window waits out the page's 1500 ms link timer."""
    b, c = [], []

    def box(s):
        b.append(s)
        return len(b) - 1

    lb = box("#X obj 20 20 loadbang;")
    t = 300
    for k, (mark, actions) in enumerate(seq):
        t += 1700 if mark == "relink" else 120     # the link times out in between
        d = box("#X obj %d 80 del %d;" % (20 + k * 10, t))
        c.append("#X connect %d 0 %d 0;" % (lb, d))
        body = ["\\; ck-mark %s" % mark]
        for kind, arg in actions:
            body.append("\\; ck-%s-press bang" % arg if kind == "press"
                        else "\\; #osc-in %s" % arg)     # cutit as the selector, as PdParty sends it
        m = box("#X msg %d 120 %s;" % (20 + k * 10, " ".join(body)))
        c.append("#X connect %d 0 %d 0;" % (d, m))
    q = box("#X obj 20 200 del %d;" % (t + 400))
    qm = box("#X msg 20 240 \\; pd quit;")
    c += ["#X connect %d 0 %d 0;" % (lb, q), "#X connect %d 0 %d 0;" % (q, qm)]
    taps = ["mark"] + ["%s-in" % n for n in ("name", "pos", "mark", "pill", "title", "btn-send")] \
        + ["l%d-in" % (k + 1) for k in range(B.LINES)]
    for k, n in enumerate(taps):
        r = box("#X obj %d 400 r ck-%s;" % (20 + k * 120, n))
        p = box("#X obj %d 440 print %s;" % (20 + k * 120, n))
        c.append("#X connect %d 0 %d 0;" % (r, p))
    r = box("#X obj 20 600 r #osc-out;")
    o = box("#X obj 20 640 oscparse;")
    p = box("#X obj 20 680 print osc;")
    c += ["#X connect %d 0 %d 0;" % (r, o), "#X connect %d 0 %d 0;" % (o, p)]
    path = os.path.join(WORK, "drive.pd")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#N canvas 20 20 2600 800 12;\n" + "\n".join(b + c) + "\n")
    return path


def windows(cap):
    """{mark: [(tap, text)]}, in order, and the order."""
    out, order, cur = {}, [], None
    for ln in cap.splitlines():
        m = re.match(r"^([\w-]+): (.*)$", ln.strip())
        if not m:
            continue
        tap, text = m.groups()
        if tap == "mark":
            cur = text.strip()
            order.append(cur)
            out.setdefault(cur, [])
            continue
        if cur is not None:
            out[cur].append((tap, text))
    return out, order


def main():
    S.require_pd()
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    if not KEEP:
        atexit.register(shutil.rmtree, WORK, True)

    # -- the committed page is the one the checklists build ------------------
    r = subprocess.run([sys.executable, BUILD, "--check"], capture_output=True, text=True)
    A.check("the committed page is what the checklists build", r.returncode == 0,
            (r.stdout + r.stderr).strip())
    data, bad = B.build_data()
    A.check("every step fits the page and sends only to u_inject's eight buses",
            not bad, bad)

    # -- the face, read statically --------------------------------------------
    recs = lib_pd.read(os.path.join(SCENE_DIR, "_main.pd"))
    top = []
    for rec in recs:
        if rec.startswith("#N canvas") and top:
            break
        top.append(rec)
    guis = [re.match(r"^#X obj (\d+) (\d+) (cnv|bng) (.*);$", r) for r in top]
    guis = [g for g in guis if g]
    sizes = []
    for g in guis:
        x, y, kind, a = int(g.group(1)), int(g.group(2)), g.group(3), g.group(4).split()
        w, h = (int(a[1]), int(a[2])) if kind == "cnv" else (int(a[0]), int(a[0]))
        snd, rcv = (a[3], a[4]) if kind == "cnv" else (a[4], a[5])
        sizes.append((kind, x, y, w, h, snd, rcv))
    A.check("every iemgui has both a send and a receive name, or PdParty draws nothing",
            sizes and all(s not in ("empty", "-") and r not in ("empty", "-")
                          for *_, s, r in sizes), sizes)
    A.check("nothing under the notch: 22 units clear on the right, 17 at the bottom",
            all(x + w <= 448 - 22 and y + h <= 207 - 17 for _, x, y, w, h, _, _ in sizes),
            [(k, x, y, w, h) for k, x, y, w, h, _, _ in sizes if x + w > 426 or y + h > 190])
    # a bng draws a circle, so each button is a rectangle drawn after (over) the
    # bngs that take its touch: every bng sits inside the rectangle of its name
    order = [(k, kind, x, y, w, h, snd) for k, (kind, x, y, w, h, snd, _r) in enumerate(sizes)]
    rects = {snd[len("ck-btn-"):-len("-out")]: (k, x, y, w, h) for k, kind, x, y, w, h, snd in order
             if kind == "cnv" and snd.startswith("ck-btn-")}
    bngs = [(k, x, y, w, snd[len("ck-"):-len("-press")]) for k, kind, x, y, w, h, snd in order
            if kind == "bng"]
    covered = [b for b in bngs if b[4] in rects
               and rects[b[4]][0] > b[0]
               and rects[b[4]][1] <= b[1] and b[1] + b[3] <= rects[b[4]][1] + rects[b[4]][3]
               and rects[b[4]][2] <= b[2] and b[2] + b[3] <= rects[b[4]][2] + rects[b[4]][4]]
    A.check("seven buttons, each a rectangle drawn over the Pd buttons that take its touch",
            len(rects) == 7 and len(bngs) == 8 and covered == bngs
            and {b[4] for b in bngs} == set(rects),
            "%d rectangles, %d bngs, uncovered: %s" % (len(rects), len(bngs),
                                                       [b for b in bngs if b not in covered]))

    # -- the page, driven --------------------------------------------------------
    seq, data, names, titles, sends, multi, nosend, many = plan()
    drv = driver(seq)
    cap = os.path.join(WORK, "capture.txt")
    with open(cap, "wb") as fh:
        subprocess.run([S.PD] + list(S.RATE) + ["-nogui", "-noaudio", "-nomidi",
                       "-open", os.path.join(SCENE_DIR, "_main.pd"), "-open", drv],
                       stdout=fh, stderr=subprocess.STDOUT, cwd=SCENE_DIR, timeout=60)
    log = open(cap, encoding="utf-8", errors="replace").read()
    win, order = windows(log)
    marks = [m for m, _ in seq]
    A.check("every window ran", order == marks, "%d of %d" % (len(order), len(marks)))
    stray = [ln for ln in log.splitlines() if ln.strip() and not re.match(r"^[\w-]+: ", ln)]
    A.check("Pd said nothing else", not stray, stray[:5])

    def lab(w, tap):
        got = [t for k, t in win.get(w, []) if k == tap and t.startswith("label ")]
        return label(got[-1][len("label "):]) if got else None

    def osc(w):
        return [t for k, t in win.get(w, []) if k == "osc"]

    def title_of(c, i):
        t = next(t for t in titles if int(t[0]) == c and int(t[1]) == i)
        return label(t[-1])

    def line1(c, i, p=0):
        ln = next(ln for ln in data["lines.txt"].splitlines()
                  if ln.split(" ")[:3] == [str(c), str(i), str(p)])
        return label(ln.rstrip(";").split(" ")[3])

    A.check("next: the second step, its title, position and first line",
            (lab("next", "title-in"), lab("next", "pos-in"), lab("next", "l1-in"))
            == (title_of(0, 1), "2 of %d" % int(data["lists.txt"].split()[1].rstrip(";")), line1(0, 1)),
            (lab("next", "title-in"), lab("next", "pos-in"), lab("next", "l1-in")))
    A.check("send: the step's Send line goes out as send <bus> <message>",
            osc("send") == ["list cutit send %s" % m for m in sends[(0, 1)]], osc("send"))
    A.check("pass: logged as result <checklist>-<n>-pass, and on to the next step",
            osc("pass") == ["list cutit result %s-2-pass" % names[0]]
            and lab("pass", "title-in") == title_of(0, 2), (osc("pass"), lab("pass", "title-in")))
    A.check("back: the step that passed says so", lab("back", "mark-in") == "passed",
            lab("back", "mark-in"))
    A.check("fail: logged as result <checklist>-<n>-fail",
            osc("fail") == ["list cutit result %s-2-fail" % names[0]], osc("fail"))
    A.check("and the mark follows the latest verdict", lab("back2", "mark-in") == "failed",
            lab("back2", "mark-in"))
    A.check("a Send line of several messages goes out whole, in order, one command each",
            osc("many") == ["list cutit send %s" % m for m in sends[many]], osc("many"))
    A.check("a step with no Send line sends nothing", osc("nosend") == [], osc("nosend"))
    A.check("the checklist before the first is the last",
            lab("wrap", "name-in") == names[-1] and lab("wrap", "title-in") == title_of(len(names) - 1, 0),
            (lab("wrap", "name-in"), lab("wrap", "title-in")))
    A.check("the checklist after the last is the first",
            lab("cnext", "name-in") == names[0], lab("cnext", "name-in"))
    A.check("next walks a long step's second page before the next step",
            lab("page2", "title-in") == title_of(*multi)
            and lab("page2", "l1-in") == line1(multi[0], multi[1], 1)
            and lab("page2", "pos-in").endswith("2/%s" % next(t[2] for t in titles
                                                             if (int(t[0]), int(t[1])) == multi)),
            (lab("page2", "title-in"), lab("page2", "pos-in"), lab("page2", "l1-in")))
    A.check("and back returns to its first page",
            lab("page2back", "l1-in") == line1(*multi), lab("page2back", "l1-in"))
    A.check("the heartbeat's test mode on draws the pill on",
            lab("hbon", "pill-in") == "test mode on", lab("hbon", "pill-in"))
    A.check("and off draws it off", lab("hboff", "pill-in") == "test mode off",
            lab("hboff", "pill-in"))
    A.check("ack send turns Send green",
            [t for k, t in win.get("ack", []) if k == "btn-send-in"]
            == ["color %d %d" % (B.GREEN, B.INK)], win.get("ack"))
    A.check("a press darkens its button",
            ("btn-send-in", "color %d %d" % (B.PRESS, B.INK)) in win.get("send", []),
            win.get("send"))
    A.check("1.5 s with nothing heard says no link",
            lab("silence", "pill-in") == "no link", win.get("silence"))
    A.check("and the next heartbeat restores the state, though it did not change",
            lab("relink", "pill-in") == "test mode off", win.get("relink"))
    rc = 1 if A.report() else 0
    if rc:
        print("\n--- pd output ---\n" + log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
