#!/usr/bin/env python3
"""The phone's TouchOSC layout, headless -- ref/device/phone.md. No phone, ~1 s.

    python3 test/gate/touchosc-assert.py [-v] [--keep]     (run it as touchosc-assert.sh)

Two halves, two tallies. First, by reading: the committed layout is build.py's output, every
control has a name of its own (a script finds a control by its name, and TouchOSC returns the
first of two), and what the layout's buttons send is what u_net routes and c_steps takes, the
two ends of the inbound vocabulary, which deploy by different routes and can drift. Then the
layout's own scripts, unpacked from it and run under test/gate/lua/lib_touchosc.lua's stand-in
for TouchOSC by test/gate/lua/touchosc_test.lua: the tabs and the mode, test mode, and each
screen, driven as u_net and a finger would.
"""
import importlib.util
import os
import re
import shutil
import sys
import xml.dom.minidom
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                   # noqa: E402
import lib_scratch as S                                         # noqa: E402

ROOT = S.ROOT
KEEP = "--keep" in sys.argv
LAYOUT = os.path.join(ROOT, "tools", "touchosc", "CutIt.tosc")
BUILD = os.path.join(ROOT, "tools", "touchosc", "build.py")
UNET = os.path.join(ROOT, "Cut It", "u_net.pd")
STEPS_LUA = os.path.join(ROOT, "Cut It", "c_steps.lua")

spec = importlib.util.spec_from_file_location("build_touchosc", BUILD)
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


# ------------------------------------------------------------------ contrast, WCAG AA
# What TouchOSC draws, measured on the Mac (2026-11-04, ~/Sites/!reference/touchosc.md): a
# control's resting fill at 26% of its color over black, its pressed or lit fill at full color.
DIM = 66 / 255          # a resting fill's share of its color
LARGE = 24              # text size, in points, from which 3:1 is enough


def lin(c):
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(c):
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def over(c, a, bg):
    return tuple(c[i] * a + bg[i] * (1 - a) for i in range(3))


def props(n):
    out = {}
    for p in n.getElementsByTagName("properties")[0].childNodes:
        k = p.getElementsByTagName("key")[0].firstChild.data
        v = p.getElementsByTagName("value")[0]
        t = p.getAttribute("type")
        if t == "c":
            out[k] = tuple(float(v.getElementsByTagName(x)[0].firstChild.data) for x in "rgba")
        elif t == "r":
            out[k] = tuple(float(v.getElementsByTagName(x)[0].firstChild.data) for x in "xywh")
        else:
            out[k] = v.firstChild.data if v.firstChild is not None and hasattr(v.firstChild, "data") else ""
    vals = {}
    for v in n.getElementsByTagName("values")[0].childNodes:
        k = v.getElementsByTagName("key")[0].firstChild.data
        d = v.getElementsByTagName("default")[0].firstChild
        vals[k] = d.data if d is not None else ""
    return out, vals


def walk(n, ox=0, oy=0, out=None, page=None, pager=False):
    """[(type, name, absolute frame, props, values, page)] for every node, in drawing order;
    page is the pager page it is on, since only one of those shows at a time."""
    out = [] if out is None else out
    p, v = props(n)
    f = p.get("frame", (0, 0, 0, 0))
    a = (ox + f[0], oy + f[1], f[2], f[3])
    if pager:
        page = p.get("name")
    out.append((n.getAttribute("type"), p.get("name"), a, p, v, page))
    for c in n.childNodes:
        if c.nodeName == "children":
            for k in c.childNodes:
                if k.nodeName == "node":
                    walk(k, a[0], a[1], out, page, n.getAttribute("type") == "PAGER")
    return out


def inside(f, x, y):
    return f[0] <= x <= f[0] + f[2] and f[1] <= y <= f[1] + f[3]


def under(nodes, i, x, y):
    """The color drawn at (x, y) before node i: the last filled control there, over black."""
    bg = (0.0, 0.0, 0.0)
    here = nodes[i][5]
    for t, name, f, p, v, page in nodes[:i]:
        if page not in (None, here) or not inside(f, x, y) or p.get("visible") == "0":
            continue
        col = p.get("color")
        if t == "BOX":
            bg = over(col, col[3], bg)
        elif t == "BUTTON" and p.get("background") != "0":
            on = float(v.get("x") or 0) >= 0.5
            bg = over(col, 1.0 if on else DIM * col[3], bg)
        elif t == "RADIO":
            steps = int(p.get("steps") or 1)
            seg = int((x - f[0]) / (f[2] / steps)) if p.get("orientation") == "1" else 0
            bg = over(col, 1.0 if seg == int(float(v.get("x") or 0)) else DIM, bg)
        elif t in ("LABEL", "TEXT") and p.get("background") == "1":
            bg = over(col, DIM * col[3], bg)
    return bg


def audit(doc):
    nodes = walk(doc.getElementsByTagName("node")[0])
    bad, n = [], 0
    for i, (t, name, f, p, v, _page) in enumerate(nodes):
        if t in ("LABEL", "TEXT") and (v.get("text") or "").strip():
            cx, cy = f[0] + f[2] / 2, f[1] + f[3] / 2
            bg = under(nodes, i, cx, cy)
            if p.get("background") == "1":
                bg = over(p["color"], DIM * p["color"][3], bg)
            r = ratio(p["textColor"], bg)
            need = 3.0 if float(p.get("textSize") or 15) >= LARGE else 4.5
            n += 1
            if r < need:
                bad.append("text %-10s %-24r %.2f < %.1f" % (name, v.get("text")[:24], r, need))
        if t in ("BUTTON", "RADIO", "RADIAL", "FADER") and p.get("interactive") == "1":
            bg = under(nodes, i, f[0] + 1, f[1] + 1)
            # the edge is the full color only where a whole outline is drawn; corner marks
            # leave the resting fill to show where the control ends
            full = p.get("outline") == "1" and p.get("outlineStyle") == "0"
            r = ratio(p["color"] if full else over(p["color"], DIM, bg), bg)
            n += 1
            if r < 3.0:
                bad.append("edge %-10s %.2f < 3.0" % (name, r))
        if t == "GROUP" and "tabLabel" in p:
            for state in ("On", "Off"):
                r = ratio(p["textColor" + state], p["tabColor" + state])
                n += 1
                if r < 4.5:
                    bad.append("tab  %-10s text %s %.2f < 4.5" % (name, state, r))
            # a tab is told by its text; its state, active or not, must differ by 3:1
            r = ratio(p["tabColorOn"], p["tabColorOff"])
            n += 1
            if r < 3.0:
                bad.append("tab  %-10s active against inactive %.2f < 3.0" % (name, r))
    return n, bad




def route_of(path, first):
    """The arguments of the one `route <first> ...` box in a file, or None."""
    want = re.compile(r"^#X obj -?\d+ -?\d+ route (" + re.escape(first) + r"(?: [^;]*)?);$")
    hits = [m.group(1) for m in (want.match(r) for r in lib_pd.read(path)) if m]
    return hits[0].split() if len(hits) == 1 else None


def steps_cmds():
    """The commands c_steps takes on its inlet: the keys of c_steps.lua's R.presses."""
    src = open(STEPS_LUA, encoding="utf-8").read()
    m = re.search(r"^R\.presses = \{\n(.*?)^\}", src, re.M | re.S)
    if not m:
        return None
    keys = re.findall(r'^  (?:\["([\w-]+)"\]|(\w+)) = function', m.group(1), re.M)
    return sorted(a or b for a, b in keys)


def controls(doc):
    """[(name, type, visible, script, text)] for every node, in the file's order."""
    out = []
    for n in doc.getElementsByTagName("node"):
        props = {}
        for p in n.getElementsByTagName("properties")[0].childNodes:
            k = p.getElementsByTagName("key")[0].firstChild.data
            v = p.getElementsByTagName("value")[0]
            first = v.firstChild
            props[k] = first.data if first is not None and hasattr(first, "data") else ""
        text, x = None, None
        for v in n.getElementsByTagName("values")[0].childNodes:
            key = v.getElementsByTagName("key")[0].firstChild.data
            d = v.getElementsByTagName("default")[0].firstChild
            if key == "text":
                text = d.data if d is not None else ""
            if key == "x" and d is not None:
                x = float(d.data)
        col = [p for p in n.getElementsByTagName("properties")[0].childNodes
               if p.getElementsByTagName("key")[0].firstChild.data == "color"]
        color = (tuple(float(col[0].getElementsByTagName(c)[0].firstChild.data) for c in "rgba")
                 if col else None)
        out.append((props.get("name"), n.getAttribute("type"), props.get("visible") == "1",
                    props.get("script"), text, x, color, props.get("tabLabel")))
    return out


def sent(script):
    """What a script sends after /cutit, where its arguments are written out: each call's
    literal strings and numbers, up to the first that is not one."""
    out = []
    for m in re.finditer(r"sendOSC\('/cutit', ([^)]*)\)", script or ""):
        atoms = []
        for a in [x.strip() for x in m.group(1).split(",")]:
            lit = re.fullmatch(r"'([^']*)'|\"([^\"]*)\"|(-?\d+(?:\.\d+)?)", a)
            if not lit:
                break
            atoms.append(lit.group(1) or lit.group(2) or lit.group(3))
        out.append(" ".join(atoms))
    return out


def lua(v):
    return B.lua(v)


def longest():
    """The checklist the gate runs the page on: the line check's steps may all fit one page, so
    the first development checklist with a step on more than one page, not its last, stands in
    for it. The page holds any checklist the same way; only the data differs."""
    for f in sorted(os.listdir(B.CHECKLISTS)):
        name = f[:-3]
        if not f.endswith(".md") or name in ("README", B.LIST):
            continue
        check, bad = B.checklist(name)
        if not bad and any(len(s["pages"]) > 1 for s in check["steps"][:-1]):
            return check
    return None


def expect(check):
    """What the Lua test needs to know about the checklist the page carries, worked out here
    from the same data: its first step, and a step on more than one page that is not its last."""
    si, s = next((i, s) for i, s in enumerate(check["steps"])
                 if len(s["pages"]) > 1 and i + 1 < len(check["steps"]))
    e = {"name": check["name"], "steps": len(check["steps"]), "title": check["steps"][0]["title"],
         "pass": "%s-1-pass" % check["name"],
         "multi": {"si": si + 1, "pages": len(s["pages"]),
                   "verdict": "%s-%d-fail" % (check["name"], s["n"])}}
    return "return " + lua(e) + "\n"


def main():
    print("\n=== A. the layout, checked by READING -- no TouchOSC involved ===")
    A.check("the committed layout is build.py's output",
            os.path.exists(LAYOUT) and B.strip_ids(zlib.decompress(open(LAYOUT, "rb").read())
                                                   .decode("utf-8")) == B.strip_ids(B.build()),
            "run tools/touchosc/build.py")
    doc = xml.dom.minidom.parseString(zlib.decompress(open(LAYOUT, "rb").read()))
    nodes = controls(doc)
    names = [r[0] for r in nodes]
    dupes = sorted({n for n in names if names.count(n) > 1})
    A.check("⛔ every control has a name of its own", not dupes and None not in names,
            "named twice: %s" % dupes)
    A.note("%d controls, %d with a script" % (len(nodes), sum(1 for x in nodes if x[3])))

    msgs = [m for r in nodes for m in sent(r[3])]
    ucmd, udev = route_of(UNET, "re-wire"), route_of(UNET, "m_volca")
    uacks = route_of(UNET, "sync")
    takes = steps_cmds()
    A.check("u_net's route boxes and c_steps' commands are all readable",
            ucmd is not None and udev is not None and uacks is not None and takes is not None,
            "u_net: %r / %r / %r  c_steps: %r" % (ucmd, udev, uacks, takes))
    if ucmd and udev and uacks and takes:
        lcmd = sorted({m.split()[0] for m in msgs})
        ldev = sorted({m.split()[1] for m in msgs if m.split()[0] == "test-note"})
        ldrums = sorted({m.split()[1] for m in msgs if m.split()[0] == "drums"})
        A.check("⛔ the layout sends EXACTLY the commands u_net routes",
                lcmd == sorted(ucmd),
                "the layout sends %s, u_net routes %s -- whichever side is short is a button "
                "that does nothing at all" % (" ".join(lcmd), " ".join(ucmd)))
        A.check("⛔ it names EXACTLY the devices u_net routes", ldev == sorted(udev),
                "the layout names %s, u_net routes %s" % (" ".join(ldev), " ".join(udev)))
        A.check("⛔ every drums action it sends is one c_steps takes",
                ldrums and set(ldrums) <= set(takes),
                "the layout sends drums %s, c_steps takes %s" % (" ".join(ldrums), takes))
        A.check("... and the drum screen's sixteen pads select tracks 1 to 16",
                sorted(m for m in msgs if m.startswith("drums select ")) ==
                sorted("drums select %d" % n for n in range(1, 17)),
                [m for m in msgs if m.startswith("drums select ")])
        # Every acknowledgment u_net sends has a cell to light, but select's: a pad's
        # selection shows in the state that comes back.
        acked = ([c for c in ucmd if c not in ("test-note", "drums")]
                 + ["test-note " + d for d in udev]
                 + ["drums " + a for a in uacks if a != "select"])
        A.check("every acknowledgment u_net sends lights a cell",
                sorted(acked) == sorted(B.ACKS),
                "u_net acknowledges %s, the layout lights %s" % (sorted(acked), sorted(B.ACKS)))

    pairs, low = audit(doc)
    A.check("⛔ every text and control meets WCAG AA contrast, as TouchOSC draws it",
            pairs > 50 and not low, "%d pairs; below AA:\n    %s" % (pairs, "\n    ".join(low)))
    A.note("%d pairs at AA" % pairs)

    # The phone's pads sit as the Launchpad's do, read here from the drum page's file on its
    # own: a pad's column and its row from the bottom, ranked, against its cell's.
    cells = {int(m.group(3)): (int(m.group(1)), int(m.group(2))) for m in
             re.finditer(r"^(\d)(\d) pad (\d+)\s*$",
                         open(os.path.join(ROOT, "Cut It", "cut-it-drum-page.txt"),
                              encoding="utf-8").read(), re.M)}
    frames = {name: f for _t, name, f, _p, _v, _pg in walk(doc.getElementsByTagName("node")[0])
              if name and re.fullmatch(r"pad\d+", name)}
    xs = sorted({f[0] for f in frames.values()})
    ys = sorted({f[1] for f in frames.values()}, reverse=True)
    phone = {int(n[3:]): (ys.index(f[1]) + 1, xs.index(f[0]) + 1) for n, f in frames.items()}
    rows = sorted({r for r, _ in cells.values()})
    cols = sorted({c for _, c in cells.values()})
    pad = {n: (rows.index(r) + 1, cols.index(c) + 1) for n, (r, c) in cells.items()}
    A.check("⛔ the phone's sixteen pads sit as the drum page's do: pad 1 bottom left",
            len(pad) == 16 and phone == pad,
            "pad 1: phone row %s, Launchpad row %s (rows from the bottom)"
            % (phone.get(1, ("?",))[0], pad.get(1, ("?",))[0]))

    lc = open(os.path.join(B.CHECKLISTS, B.LIST + ".md"), encoding="utf-8").read()
    A.check("⛔ the line check, the page's checklist, has no Send line: the phone sends none",
            "**Send:**" not in lc, "%s has a Send line" % (B.LIST + ".md"))

    print("\n=== B. its scripts, run under a stand-in for TouchOSC ===")
    # The page on a checklist with a step on two pages, so paging through one is driven too.
    check = longest()
    A.check("a development checklist has a step on more than one page, to drive the page with",
            check is not None, "none has: the Lua test can't page through a step")
    if check is None:
        return 1
    nodes = controls(xml.dom.minidom.parseString(B.build(check["name"])))
    A.note("the page's scripts run on %s" % (check["name"] + ".md"))
    work = S.work_dir("touchosc")
    os.makedirs(work, exist_ok=True)
    rows = []
    for n, t, v, s, text, x, color, tab in nodes:
        if s:
            with open(os.path.join(work, n + ".lua"), "w", encoding="utf-8") as fh:
                fh.write(s)
        row = {"name": n, "type": t, "visible": v, "script": bool(s), "text": text or ""}
        if x is not None:
            row["x"] = x
        if color:
            row["color"] = list(color)
        if tab:
            row["tabLabel"] = tab
        rows.append(row)
    with open(os.path.join(work, "controls.lua"), "w", encoding="utf-8") as fh:
        fh.write("return " + lua(rows) + "\n")
    with open(os.path.join(work, "expect.lua"), "w", encoding="utf-8") as fh:
        fh.write(expect(check))
    rc_lua = S.lua("test/gate/lua/touchosc_test.lua", work, *[a for a in sys.argv[1:]
                                                              if a == "-v"])
    if not KEEP:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if (A.report() or rc_lua) else 0


if __name__ == "__main__":
    sys.exit(main())
