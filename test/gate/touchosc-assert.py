#!/usr/bin/env python3
"""The phone's TouchOSC layout, headless -- ref/device/phone.md. No phone, ~1 s.

    python3 test/gate/touchosc-assert.py [-v] [--keep]     (run it as touchosc-assert.sh)

Two halves, two tallies. First, by reading: the committed layout is build.py's output, every
control has a name of its own (a script finds a control by its name, and TouchOSC returns the
first of two), every screen is a page of a pager with nothing hidden, so TouchOSC's editor reaches
each by its tab, and what the layout's buttons send is what u_net routes and c_steps, c_synth and
u_tempo take, the two ends of the inbound vocabulary, which deploy by different routes and can
drift. Then the layout's own scripts, unpacked from it and run under
test/gate/lua/lib_touchosc.lua's stand-in for TouchOSC by test/gate/lua/touchosc_test.lua: the
pages and the mode, test mode, and each screen, driven as u_net and a finger would.
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
SYNTH_LUA = os.path.join(ROOT, "Cut It", "c_synth.lua")
MAP_LUA = os.path.join(ROOT, "Cut It", "u_map.lua")
SONG_LUA = os.path.join(ROOT, "Cut It", "u_song.lua")
# The Launchpad's pages and what each is (Brendan, 2026-11-04, ref/module/map.md, The pages):
# each one's tab on the phone, named for it.
TABS = ["arrangement", "drums", "synths", "page 4", "page 5", "page 6", "sections", "songs"]
# A page's own tabs: one, named for the page, but the synths page's four, the generator's harmony,
# rhythm and melody and the nanoKEY's keyboard, the sections page's two, its sections and the name
# a section is given, and the songs page's three, its songs, its setlists and the name either is
# given (Brendan, 2026-11-05).
OWN_TABS = {"synths": ["harmony", "rhythm", "melody", "notes", "keyboard"],
            "sections": ["sections", "name"], "songs": ["songs", "setlists", "name"]}

spec = importlib.util.spec_from_file_location("build_touchosc", BUILD)
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


# ------------------------------------------------------------------ contrast, WCAG AA
# What TouchOSC draws, measured on the Mac (2026-11-04, ~/Sites/!reference/touchosc.md): a
# control's resting fill at 26% of its color over black, its pressed or lit fill at full color.
DIM = 66 / 255          # a resting fill's share of its color
LARGE = 24              # text size, in points, from which 3:1 is enough
# ⛔ ONE EXCEPTION, named control by control: the dash in an empty chord box on the harmony tab, gray
# on the box's resting teal, 4.03:1. An empty box does nothing to a finger, the root finding no chord
# for it, and WCAG excuses an inactive control's text. A chord's own words are white or black.
EMPTY_BOX = {"cbox%d%s" % (n, part) for n in range(1, 9) for part in "nsr"}


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


def segment(f, p, x, y):
    """The segment of a radio at (x, y), 0 the first: across from the left when horizontal
    (orientation 1); down from the top when its orientation is 2, south, and up from the bottom
    when 0, north, as a fader's value runs (~/Sites/!reference/touchosc.md, The file)."""
    steps = int(p.get("steps") or 1)
    o = p.get("orientation")
    if o == "1":
        return min(steps - 1, int((x - f[0]) / (f[2] / steps)))
    k = min(steps - 1, int((y - f[1]) / (f[3] / steps)))
    return k if o == "2" else steps - 1 - k


def under(nodes, i, x, y, group_of=None):
    """The color drawn at (x, y) before node i: the last filled control there, over black. An
    effect's controls (group_of: name -> the effect radio's choice) are drawn only over their own
    effect's or the screen's, since the root shows one effect's at a time, as a pager one page:
    in the file every one shows, for the editor, and they share one place."""
    bg = (0.0, 0.0, 0.0)
    here = nodes[i][5]
    group_of = group_of or {}
    mine = group_of.get(nodes[i][1])
    for t, name, f, p, v, page in nodes[:i]:
        if page not in (None, here) or not inside(f, x, y) or p.get("visible") == "0":
            continue
        if mine is not None and group_of.get(name) not in (None, mine):
            continue
        col = p.get("color")
        if t == "BOX":
            bg = over(col, col[3], bg)
        elif t == "BUTTON" and p.get("background") != "0":
            on = float(v.get("x") or 0) >= 0.5
            bg = over(col, (1.0 if on else DIM) * col[3], bg)
        elif t == "RADIO":
            bg = over(col, 1.0 if segment(f, p, x, y) == int(float(v.get("x") or 0)) else DIM, bg)
        elif t in ("LABEL", "TEXT") and p.get("background") == "1":
            bg = over(col, DIM * col[3], bg)
    return bg


def audit(doc):
    nodes = walk(doc.getElementsByTagName("node")[0])
    group_of = {name: k for k, g in enumerate(B.fx_groups() if hasattr(B, "fx_groups") else [])
                for name in g}
    # The rhythm grid's cells: in the file every one sits at the grid's top left, for the editor, and
    # the root moves each to its place. So a chord's cell and its word are drawn over one blue band
    # at most, the first standing in for them all, and never over another chord's.
    for k in range(2, 17):
        group_of["rsub%d" % k] = "rsub%d" % k
    for k in range(1, 9):
        group_of["rmark%d" % k] = group_of["rmark%dl" % k] = "rmark%d" % k
    group_of["rhere"] = "rhere"
    bad, n = [], 0
    for i, (t, name, f, p, v, _page) in enumerate(nodes):
        if t in ("LABEL", "TEXT") and (v.get("text") or "").strip():
            cx, cy = f[0] + f[2] / 2, f[1] + f[3] / 2
            bg = under(nodes, i, cx, cy, group_of)
            if p.get("background") == "1":
                bg = over(p["color"], DIM * p["color"][3], bg)
            r = ratio(p["textColor"], bg)
            need = 3.0 if float(p.get("textSize") or 15) >= LARGE else 4.5
            n += 1
            if r < need and not (name in EMPTY_BOX and v.get("text") == "-"):
                bad.append("text %-10s %-24r %.2f < %.1f" % (name, v.get("text")[:24], r, need))
        if t in ("BUTTON", "RADIO", "RADIAL", "FADER") and p.get("interactive") == "1":
            bg = under(nodes, i, f[0] + 1, f[1] + 1, group_of)
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


def synths():
    """The synths c_synth takes: c_synth.lua's R.SYNTHS, in order."""
    m = re.search(r"^R\.SYNTHS = \{([^}]*)\}", open(SYNTH_LUA, encoding="utf-8").read(), re.M)
    return re.findall(r'"([\w-]+)"', m.group(1)) if m else None


def on_pages(doc):
    """(page, name, type, frame, props) for every control on a page, its frame its own (relative
    to the page): the children of each pager's page. Pagers and pages themselves are TouchOSC's
    to size, from the phone's screen, and are left out."""
    out = []
    for pager in doc.getElementsByTagName("node"):
        if pager.getAttribute("type") != "PAGER":
            continue
        for kids in [c for c in pager.childNodes if c.nodeName == "children"]:
            for page in [k for k in kids.childNodes if k.nodeName == "node"]:
                pname = props(page)[0].get("name")
                for pk in [c for c in page.childNodes if c.nodeName == "children"]:
                    for n in [k for k in pk.childNodes if k.nodeName == "node"]:
                        t = n.getAttribute("type")
                        if t in ("PAGER", "GROUP"):
                            continue
                        p, _v = props(n)
                        out.append((pname, p.get("name"), t, p.get("frame", (0, 0, 0, 0)), p))
    return out


def controls(doc):
    """[(name, type, visible, script, text, x, color, tabLabel, tabbar, parent)] for every node,
    in the file's order."""
    out = []
    for n in doc.getElementsByTagName("node"):
        parent = n.parentNode.parentNode if n.parentNode.nodeName == "children" else None
        pname = None
        if parent is not None:
            for p in parent.getElementsByTagName("properties")[0].childNodes:
                if p.getElementsByTagName("key")[0].firstChild.data == "name":
                    pname = p.getElementsByTagName("value")[0].firstChild.data
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
                    props.get("script"), text, x, color, props.get("tabLabel"),
                    props.get("tabbar"), pname))
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
    from the same data: its first step, and a step on more than one page that is not its last;
    and how many steps a drum pad's whole travel holds, which this half holds to 20 points each."""
    si, s = next((i, s) for i, s in enumerate(check["steps"])
                 if len(s["pages"]) > 1 and i + 1 < len(check["steps"]))
    e = {"name": check["name"], "steps": len(check["steps"]), "title": check["steps"][0]["title"],
         "pad_steps": B.PAD_STEPS,
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

    # -- every screen a page, so the editor reaches it --------------------------
    # The editor runs no script, so a screen a script shows is one Brendan can't open there
    # (2026-11-04). Each Launchpad page is a page of the outer pager, its tab bar on in the
    # file, each holding a pager of its own whose tabs are that page's.
    kids = {}
    for r in nodes:
        kids.setdefault(r[9], []).append(r)
    by_name = {r[0]: r for r in nodes}
    hidden = [r[0] for r in nodes if not r[2]]
    A.check("⛔ nothing in the file is hidden: every screen shows in the editor", not hidden,
            "hidden: %s -- a screen a script has to show can't be opened in the editor" % hidden)
    outer = by_name.get("pages")
    A.check("⛔ the root holds one pager, its tab bar ON in the file: the editor's way to each page",
            [r[0] for r in kids.get("root", [])] == ["pages"] and outer and outer[1] == "PAGER"
            and outer[8] == "1", "root holds %s; pages: %s" % ([r[0] for r in kids.get("root", [])],
                                                             outer and outer[8]))
    m = re.search(r"^R\.PAGES = (\d+)$", open(MAP_LUA, encoding="utf-8").read(), re.M)
    A.check("the Launchpad has as many pages as u_map.lua's R.PAGES takes, and each its name",
            m is not None and int(m.group(1)) == len(TABS), "R.PAGES: %s" % (m and m.group(1)))
    want = ["p%d" % (i + 1) for i in range(len(TABS))] + ["pcheck"]
    tabs = TABS + ["line check"]
    got = [r[0] for r in kids.get("pages", [])]
    A.check("⛔ its pages are the Launchpad's eight, in order, then the checklist page",
            got == want and [r[7] for r in kids.get("pages", [])] == tabs,
            "pages %s, tabs %s" % (got, [r[7] for r in kids.get("pages", [])]))
    inner, bad = [], []
    for p, tab in zip(want, tabs):
        held = kids.get(p, [])
        if len(held) != 1 or held[0][1] != "PAGER" or held[0][8] != "1":
            bad.append("%s holds %s" % (p, [(r[0], r[1]) for r in held]))
            continue
        pg = kids.get(held[0][0], [])
        inner.append((p, [(r[0], r[7]) for r in pg]))
        if [r[7] for r in pg] != OWN_TABS.get(tab, [tab]):
            bad.append("%s's tabs are %s" % (p, [r[7] for r in pg]))
    A.check("⛔ each holds a pager of its own, its tabs shown: one tab, named for the page "
            "(Brendan, 2026-11-04), but the synths page's harmony, rhythm, melody, notes and keyboard, the "
            "sections page's sections and name and the songs page's songs, setlists and name "
            "(2026-11-05)",
            not bad, "; ".join(bad))
    blank = [p for p, pg in inner[3:6] if pg and kids.get(pg[0][0])]
    A.check("pages 4 to 6 are blank under their tab", not blank, "not blank: %s" % blank)
    stray = [r[0] for r in nodes if r[1] == "GROUP" and r[0] != "root" and not r[7]]
    A.check("every group is a pager's page: no screen is a group a script shows or hides",
            not stray, "groups that are no page: %s" % stray)

    msgs = [m for r in nodes for m in sent(r[3])]
    usec = route_of(UNET, "new")
    m = re.search(r"^R\.phone_cmds = \{\n(.*?)^\}", open(SONG_LUA, encoding="utf-8").read(),
                  re.M | re.S)
    song_takes = sorted(re.findall(r"^  (\w+) = function", m.group(1), re.M)) if m else None
    lsec = sorted({x.split()[1] for x in msgs if x.split()[0] == "sections"})
    A.check("⛔ every sections action the layout sends is one u_song takes, and it sends them all",
            song_takes is not None and lsec == song_takes,
            "the layout sends sections %s, u_song takes %s" % (" ".join(lsec), song_takes))
    A.check("⛔ ... and the name tab's done sends the name the sections page selected",
            "sections name" in msgs and "sections select" in msgs, sorted(set(msgs)))
    # The songs page's, after songs: u_song's R.songs_cmds, a key a word or a quoted word.
    m = re.search(r"^R\.songs_cmds = \{\n(.*?)^\}", open(SONG_LUA, encoding="utf-8").read(),
                  re.M | re.S)
    songs_takes = (sorted(a or b for a, b in re.findall(r'^  (?:\["([\w-]+)"\]|(\w+)) = function',
                                                          m.group(1), re.M)) if m else None)
    lsongs = sorted({x.split()[1] for x in msgs if x.split()[0] == "songs"})
    A.check("⛔ every songs action the layout sends is one u_song takes, and it sends them all",
            songs_takes is not None and lsongs == songs_takes,
            "the layout sends songs %s, u_song takes %s" % (" ".join(lsongs), songs_takes))
    A.check("⛔ ... the name tab's done names the song from the songs tab and the setlist from the "
            "setlists tab", "songs name" in msgs and "songs set-name" in msgs,
            sorted(m_ for m_ in set(msgs) if m_.startswith("songs")))
    ucmd = route_of(UNET, "result")
    uacks, usynth, uvel = route_of(UNET, "sync"), route_of(UNET, "fm"), route_of(UNET, "on")
    usongs = route_of(UNET, "load")
    takes, chooses = steps_cmds(), synths()
    A.check("u_net's route boxes, c_steps' commands and c_synth's synths are all readable",
            None not in (ucmd, uacks, usynth, uvel, takes, chooses),
            "u_net: %r / %r / %r / %r  c_steps: %r  c_synth: %r"
            % (ucmd, uacks, usynth, uvel, takes, chooses))
    if None not in (ucmd, uacks, usynth, uvel, takes, chooses):
        lcmd = sorted({m.split()[0] for m in msgs})
        ldrums = sorted({m.split()[1] for m in msgs if m.split()[0] == "drums"})
        A.check("⛔ the layout sends EXACTLY the commands u_net routes",
                lcmd == sorted(ucmd),
                "the layout sends %s, u_net routes %s -- whichever side is short is a button "
                "that does nothing at all" % (" ".join(lcmd), " ".join(ucmd)))
        gone = sorted({m.split()[0] for m in msgs} & {"re-wire", "clear-alert", "test-note"})
        A.check("⛔ no diagnostic command is left on the phone (Brendan, 2026-11-04)", not gone,
                "the layout still sends %s" % gone)
        vel = by_name.get("svel")
        said = sorted(set(re.findall(r"'(on|off)'", (vel and vel[3]) or "")))
        A.check("⛔ the velocity switch asks for EXACTLY the settings u_net acknowledges",
                said == sorted(uvel) == ["off", "on"],
                "the switch says %s, u_net acknowledges %s" % (said, uvel))
        A.check("⛔ every drums action it sends is one c_steps takes",
                ldrums and set(ldrums) <= set(takes),
                "the layout sends drums %s, c_steps takes %s" % (" ".join(ldrums), takes))
        lsynth = sorted({m.split()[1] for m in msgs if m.split()[0] == "synth"})
        A.check("⛔ it sends EXACTLY the synths c_synth takes",
                lsynth == sorted(chooses),
                "the layout sends synth %s, c_synth takes %s -- a synth with no button can't be "
                "chosen from the phone, a button for none fails bad-synth"
                % (" ".join(lsynth), " ".join(chooses)))
        A.check("... and u_net acknowledges exactly those", sorted(usynth) == sorted(chooses),
                "u_net acknowledges synth %s" % " ".join(usynth))
        A.check("... from the keyboard tab and the checklist page, a button each",
                sorted(m for m in msgs if m.startswith("synth ")) ==
                sorted("synth %s" % c for c in chooses for _ in (0, 1)),
                [m for m in msgs if m.startswith("synth ")])
        A.check("... and the drum screen's sixteen pads select tracks 1 to 16",
                sorted(m for m in msgs if m.startswith("drums select ")) ==
                sorted("drums select %d" % n for n in range(1, 17)),
                [m for m in msgs if m.startswith("drums select ")])
        # Each pad, dragged, changes what the pads show for its own track (Brendan, 2026-11-05):
        # the radio's four, each a command c_steps takes, which the check above holds.
        shown = [c for _w, c, _lo, _hi, _st in getattr(B, "SHOW", [])]
        dragged = sorted(m for m in msgs if len(m.split()) == 3 and m.split()[0] == "drums"
                         and m.split()[1] in shown)
        A.check("⛔ ... and each drags its own track's %s, the radio's four" % ", ".join(shown),
                shown == ["vol", "pitch", "set-track-last", "randomness"]
                and dragged == sorted("drums %s %d" % (c, n) for c in shown for n in range(1, 17)),
                "the radio shows %s; the pads send %s" % (shown, dragged[:8]))
        # Every acknowledgment u_net sends has a cell to flash, but select's and synth's: a
        # pad's selection and a synth's choice show in the state that comes back. tempo has
        # none: the tempo that comes back says it.
        acked = (["result"] + ["drums " + a for a in uacks if a != "select"]
                 + ["velocity " + v for v in uvel] + ["sections " + a for a in usec or []]
                 + ["songs " + a for a in usongs or []])
        A.check("every acknowledgment u_net sends lights a cell",
                sorted(acked) == sorted(B.ACKS),
                "u_net acknowledges %s, the layout lights %s" % (sorted(acked), sorted(B.ACKS)))

    pairs, low = audit(doc)
    A.check("⛔ every text and control meets WCAG AA contrast, as TouchOSC draws it, but an empty "
            "chord box's dash",
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

    # The grid (Brendan, 2026-11-04: "make use of the existing grid"): TouchOSC's editor snaps to
    # 20 points, anchored at the document's center, so a control off it moves the moment it is
    # touched in the editor. Its edges are on lines: x at OX and y at OY plus whole steps, and a
    # whole number of steps wide and tall.
    #
    # ⛔ ONE EXCEPTION, named control by control: the drum screen's sixteen pads and the M and S
    # under each (Brendan, 2026-11-05, his pick of three mockups). An M and an S under every pad
    # don't fit four rows of 20-point steps in the page's height, so this panel alone steps by
    # 10: pads 60 by 50, M and S 30 by 20 each directly under their pad, 10 points apart, the
    # block from 10 points above the top margin to the bottom one, 4 x (50 + 20) + 3 x 10 = 310.
    # It ends at the bottom margin because the page's frame is 334 points tall: 10 points lower,
    # the bottom row of M and S would be cut. Each pad is its fill, its fader and its number; each M
    # and S its button and its letter. Nothing else on this page or any other is excused: a new
    # control beside them is held to the 20-point grid and the margins like the rest.
    #
    # ⛔ A SECOND EXCEPTION, named control by control: the harmony tab's (2026-11-05). A chord box holds
    # three lines of words in its four steps; twelve keys, nine modes and five voices divide their
    # widths into whole segments, not whole steps, and the modes sit 4 points under the keys; and
    # four knobs across fourteen steps leave two of them on a half step.
    fine = {("drums", "%s%d%s" % (w, n, x)) for n in range(1, 17)
            for w, xs in (("pad", ("", "f", "l")), ("mute", ("", "l")), ("solo", ("", "l")))
            for x in xs}
    words = (["cbox%d%s" % (n, part) for n in range(1, 9) for part in "nsr"]
             + ["hkey", "hmode"] + ["hkey%dl" % n for n in range(1, 13)]
             + ["hmode%dl" % n for n in range(1, 10)] + ["vharm%dl" % n for n in range(1, 6)]
             + ["%s%s" % (knob, x) for knob in ("csmooth", "chome") for x in ("c", "", "v")])
    harmony = {("harmony", n) for n in words}
    FINE_STEP, FINE_ABOVE = 10, 10
    placed = on_pages(doc)

    def on_grid(f):
        return not ((f[0] - B.OX) % B.G or (f[1] - B.OY) % B.G or f[2] % B.G or f[3] % B.G)
    off = ["%s/%s %s" % (pg, n, " ".join("%g" % v for v in f)) for pg, n, t, f, p in placed
           if (pg, n) not in fine and (pg, n) not in harmony and not on_grid(f)]
    A.check("⛔ every control on a page sits on TouchOSC's %d-point editor grid, anchored at the "
            "document's center, but the drum screen's pads and their M and S, and the harmony tab's "
            "words, radios and two knobs" % B.G,
            len(placed) > 50 and not off, "%d placed; off the grid: %s" % (len(placed), off[:6]))
    needless = sorted(harmony - {(pg, n) for pg, n, t, f, p in placed if not on_grid(f)})
    A.check("⛔ ... and the harmony tab's %d all need it: each is there, and off the grid" % len(harmony),
            not needless, "named but on the grid, or gone: %s" % needless[:6])
    excused = [(n, f) for pg, n, t, f, p in placed if (pg, n) in fine]
    loose = ["%s %s" % (n, " ".join("%g" % v for v in f)) for n, f in excused
             if (f[0] - B.OX) % FINE_STEP or (f[1] - B.OY) % FINE_STEP or f[2] % FINE_STEP
             or f[3] % FINE_STEP]
    A.check("⛔ ... and those %d, every one of them on the drum screen, sit on a %d-point step of "
            "the same grid" % (len(fine), FINE_STEP),
            len(excused) == len(fine) and not loose,
            "%d of %d placed; off the %d-point step: %s"
            % (len(excused), len(fine), FINE_STEP, loose[:6]))
    out = ["%s/%s" % (pg, n) for pg, n, t, f, p in placed
           if f[0] < B.X0 or f[0] + f[2] > B.X1
           or f[1] < B.Y0 - (FINE_ABOVE if (pg, n) in fine else 0) or f[1] + f[3] > B.Y1]
    A.check("every control is inside its page: a step from the left and the top, clear of the "
            "notch on the right, above the bottom, the drum screen's pads and M and S no more "
            "than %d points above the top" % FINE_ABOVE, not out, "outside: %s" % out[:6])
    high = min([f[1] for _n, f in excused] or [0])
    low = max([f[1] + f[3] for _n, f in excused] or [0])
    frame = B.H - 2 * B.TAB
    A.check("⛔ ... and those reach %d points into the top margin and end on the bottom one, inside "
            "the page's %d-point frame, so the last row of M and S is whole" % (FINE_ABOVE, frame),
            high == B.Y0 - FINE_ABOVE and low == B.Y1 <= frame,
            "their top %g, bottom %g; the margins %g and %g; the frame %g"
            % (high, low, B.Y0, B.Y1, frame))
    # Under each pad its M and its S (Brendan, 2026-11-05): the pad 60 wide and 50 tall, M and S
    # 30 by 20 each directly under it, M on the left, red, and S on the right, teal, each a
    # button that sends its own track's mute or solo, as c_steps takes them.
    where = {n: (t, f, p) for pg, n, t, f, p in placed if pg == "drums"}
    bad = []
    for n in range(1, 17):
        pad = where.get("pad%d" % n)
        if not pad or pad[1][2:] != (60, 50):
            bad.append("pad%d %s" % (n, pad and pad[1]))
            continue
        x, y = pad[1][0], pad[1][1] + 50
        for which, dx, col, letter in (("mute", 0, B.RED, "M"), ("solo", 30, B.TEAL, "S")):
            got = where.get("%s%d" % (which, n))
            word = by_name.get("%s%dl" % (which, n))
            if (not got or got[0] != "BUTTON" or got[1] != (x + dx, y, 30, 20)
                    or tuple(round(c, 3) for c in got[2]["color"][:3])
                    != tuple(round(c, 3) for c in col[:3])
                    or sent(by_name["%s%d" % (which, n)][3]) != ["drums %s %d" % (which, n)]
                    or not word or word[4] != letter
                    or where.get("%s%dl" % (which, n), (0, 0))[1] != got[1]):
                bad.append("%s%d %s" % (which, n, got and got[1]))
    A.check("⛔ under each pad, 60 by 50, its M and S, 30 by 20 each, M red on the left and S teal "
            "on the right, each a button with its letter, sending its own track's drums mute or "
            "solo", not bad, "wrong: %s" % bad[:6])
    # A caption names the control under it: small, grey, flush left with it, just above it.
    grey = tuple(round(c, 3) for c in B.GREY[:3])
    # hlink, the harmony tab's link words beside their lamp, has a caption's size and is none.
    caps = [(pg, n, f) for pg, n, t, f, p in placed if t == "LABEL" and n != "hlink"
            and p.get("textAlignH") == "1"
            and float(p.get("textSize") or 0) == 14 and f[3] == B.G
            and tuple(round(c, 3) for c in p.get("textColor", (0, 0, 0))[:3]) == grey]
    loose = [(pg, n) for pg, n, f in caps
             if not any(q == pg and t != "LABEL" and g[0] == f[0] and g[1] == f[1] + f[3]
                        for q, m, t, g, p in placed)]
    A.check("every caption sits flush left over the control it names, a step above it",
            len(caps) >= 6 and not loose, "%d captions; not over a control: %s" % (len(caps), loose))

    # The drum screen's two radios (Brendan, 2026-11-05): TouchOSC's own, vertical, the first
    # segment on top (orientation 2, south), one for each of what the pads show, and one for each
    # effect whose controls show, each word over its segment, and neither sends anything: the
    # pads' drags and the effects' controls do.
    def vradio(name, want):
        radio = [(f, p) for pg, n, t, f, p in placed if pg == "drums" and n == name
                 and t == "RADIO"]
        words = sorted((f[1], f[0], by_name.get(n, [None] * 5)[4]) for pg, n, t, f, p in placed
                       if pg == "drums" and re.fullmatch(r"%s\d+l" % name, n or ""))
        seg = radio[0][0][3] / len(want) if radio and want else 0
        ok = (len(radio) == 1 and radio[0][1].get("orientation") == "2"
              and radio[0][1].get("steps") == str(len(want))
              and [w for _y, _x, w in words] == want
              and [(y, x) for y, x, _w in words] == [(radio[0][0][1] + i * seg, radio[0][0][0])
                                                    for i in range(len(want))])
        return ok, "radio %s, words %s" % ([(f, p.get("orientation"), p.get("steps"))
                                           for f, p in radio], words)
    show = getattr(B, "SHOW", [])
    ok, why = vradio("show", [w for w, _c, _lo, _hi, _st in show])
    A.check("⛔ the drum screen's radio is TouchOSC's own, VERTICAL, its first on top, a segment "
            "each for volume, pitch, last step and randomness, its word over it", ok, why)
    A.check("... and it sends nothing", by_name.get("show") is not None
            and not sent(by_name["show"][3]), sent(by_name.get("show", [None] * 4)[3]))
    ok, why = vradio("fx", ["distortion", "delay", "reverb"])
    A.check("⛔ a second vertical radio beside it chooses an effect: distortion, delay, reverb",
            ok, why)
    A.check("... and it sends nothing", by_name.get("fx") is not None
            and not sent(by_name["fx"][3]), sent(by_name.get("fx", [None] * 4)[3]))
    # The distortion's character (Brendan, 2026-11-05): a horizontal radio over its knobs, as the
    # delay's time is over its, a segment for each of c_steps.lua's R.CHARS, its word over it.
    m = re.search(r"^R\.CHARS = \{([^}]*)\}", open(STEPS_LUA, encoding="utf-8").read(), re.M)
    chars = re.findall(r'"([\w-]+)"', m.group(1)) if m else None
    radio = [(f, p) for pg, n, t, f, p in placed if pg == "drums" and n == "char" and t == "RADIO"]
    words = sorted((f[0], f[1], by_name.get(n, [None] * 5)[4]) for pg, n, t, f, p in placed
                   if pg == "drums" and re.fullmatch(r"char\d+l", n or ""))
    seg = radio[0][0][2] / len(chars) if radio and chars else 0
    knobs = [f for pg, n, t, f, p in placed if pg == "drums" and n in ("drive", "tone", "dist")]
    A.check("⛔ the distortion's character is TouchOSC's own radio, HORIZONTAL, a segment each for "
            "c_steps' R.CHARS, soft, hard, fold and crush, its word over it, above the knobs",
            chars and len(radio) == 1 and radio[0][1].get("orientation") == "1"
            and radio[0][1].get("steps") == str(len(chars))
            and [w for _x, _y, w in words] == chars
            and [(x, y) for x, y, _w in words] == [(radio[0][0][0] + i * seg, radio[0][0][1])
                                                  for i in range(len(chars))]
            and len(knobs) == 3 and all(k[1] > radio[0][0][1] + radio[0][0][3] for k in knobs),
            "R.CHARS %s; radio %s, words %s, knobs %s"
            % (chars, [(f, p.get("orientation"), p.get("steps")) for f, p in radio], words, knobs))
    # Each effect's controls (Brendan, 2026-11-05) sit to the right of the radios, every one in
    # the same place, shown in the file for the editor; the root shows the chosen effect's.
    groups = B.fx_groups() if hasattr(B, "fx_groups") else []
    fr = [f for pg, n, t, f, p in placed if pg == "drums" and n == "fx"]
    right = fr[0][0] + fr[0][2] if fr else 0
    where = {n: f for pg, n, t, f, p in placed if pg == "drums"}
    stray = [n for g in groups for n in g if n not in where or where[n][0] <= right]
    A.check("⛔ every effect's controls are on the drum screen, to the right of the radios",
            len(groups) == 3 and all(groups) and not stray, "groups %s; misplaced %s"
            % ([len(g) for g in groups], stray))
    sends_of = lambda names: sorted({m.split()[1] for n in names if n in by_name
                                     for m in sent(by_name[n][3])})
    A.check("⛔ ... and send what each is: char, drive, tone, dist; delay-note, delay-feel, "
            "feedback, delay; send, size, damping, verb-type",
            [sends_of(g) for g in groups] == [["char", "dist", "drive", "tone"],
                                              ["delay", "delay-feel", "delay-note", "feedback"],
                                              ["damping", "send", "size", "verb-type"]],
            [sends_of(g) for g in groups])
    # The reverb's type (Brendan, 2026-11-05): TouchOSC's own radio, horizontal, its first on the
    # left, a segment for each of c_steps' R.VERB_TYPES in their order, each word over its
    # segment, in the reverb's controls under its size and damping, a caption over it; it sends
    # drums verb-type and the segment, 0 the first, as c_steps numbers them.
    m = re.search(r"^R\.VERB_TYPES = \{(.*)\}$", open(STEPS_LUA, encoding="utf-8").read(), re.M)
    types = re.findall(r'"([^"]+)"', m.group(1)) if m else None
    radio = [(f, p) for pg, n, t, f, p in placed if pg == "drums" and n == "vtype"
             and t == "RADIO"]
    words = sorted((f[0], f[1], by_name.get(n, [None] * 5)[4]) for pg, n, t, f, p in placed
                   if pg == "drums" and re.fullmatch(r"vtype\d+l", n or ""))
    seg = radio[0][0][2] / len(types) if radio and types else 0
    knobs = [where[n] for n in ("size", "damping") if n in where]
    script = (by_name.get("vtype") or [None] * 4)[3] or ""
    A.check("⛔ the reverb's type is a horizontal radio of c_steps' R.VERB_TYPES, %s, each word "
            "over its segment, under the reverb's knobs, and sends drums verb-type with the "
            "segment, 0 the first" % (types and ", ".join(types)),
            types == ["plate", "gigaverb", "freeverb"] and len(radio) == 1
            and radio[0][1].get("orientation") == "1"
            and radio[0][1].get("steps") == str(len(types))
            and [w for _x, _y, w in words] == types
            and [(x, y) for x, y, _w in words] == [(radio[0][0][0] + i * seg, radio[0][0][1])
                                                  for i in range(len(types))]
            and len(knobs) == 2 and all(radio[0][0][1] >= k[1] + k[3] for k in knobs)
            and "vtype" in (groups[2] if len(groups) == 3 else [])
            and "sendOSC('/cutit', 'drums', 'verb-type', v)" in script
            and "math.floor(self.values.x + 0.5)" in script,
            "R.VERB_TYPES %s; radio %s, words %s, knobs %s" % (
                types, [(f, p.get("orientation"), p.get("steps")) for f, p in radio], words,
                knobs))
    # The selected track's random pitch (Brendan, 2026-11-05): a button right under the show radio,
    # as wide as it and a segment tall, its word over it, lit by the state with the shared LIT, so
    # it can't flicker; and the line a sync or a snap waits on, which sat there, on the grid
    # under them.
    show = where.get("show")
    rnd = where.get("rndpitch")
    word = where.get("rndpitchl")
    pend = where.get("pending")
    script = (by_name.get("rndpitch") or [None] * 4)[3] or ""
    A.check("⛔ a button, rnd pitch, sits directly under the show radio, its width and a segment tall",
            show and rnd and by_name["rndpitch"][1] == "BUTTON" and rnd[0] == show[0]
            and rnd[1] == show[1] + show[3] and rnd[2] == show[2]
            and rnd[3] == show[3] / len(B.SHOW) and word == rnd
            and by_name["rndpitchl"][4] == "rnd pitch",
            "show %s, rndpitch %s, its word %s, %s" % (show, rnd, word,
                                                       (by_name.get("rndpitchl") or [None] * 5)[4]))
    A.check("⛔ ... the show radio's last segment is random, which it adds to",
            B.SHOW[-1][0] == "random", "%s" % [s_[0] for s_ in B.SHOW])
    A.check("⛔ ... lit by the state with the shared script, so never by a finger, and asking the "
            "root for the opposite of what it shows", B.LIT in script
            and "root:notify('rolled', lit == 1 and 0 or 1)" in script, script[:200])
    A.check("⛔ ... the root sends it for the selected track, as c_steps takes it, and lights it from "
            "the state's last sixteen, 132 + the track",
            "sendOSC('/cutit', 'drums', 'rnd-pitch', math.floor(arg(state, 3)), v)" in B.ROOT_LUA
            and "arg(a, PHONE + math.floor(arg(a, 3)))" in B.ROOT_LUA
            and B.PHONE_ALL == 148 and B.PHONE == 132,
            "PHONE %s, PHONE_ALL %s" % (B.PHONE, B.PHONE_ALL))
    A.check("⛔ the pending line clear of it, under sync and snap, and a step tall on the grid",
            pend and pend[1] == B.Y0 + 3 * B.G and pend[3] == B.G and pend[0] == B.COL[0]
            and pend[1] + pend[3] <= show[1] and pend[1] + pend[3] <= rnd[1],
            "pending %s" % (pend,))
    # A pad's drag, a step at a time as the time signature's boxes are, about 20 points a step:
    # a relative fader's whole travel is its height times 100 over its responseFactor.
    faders = [(n, f, p) for pg, n, t, f, p in placed if pg == "drums" and re.fullmatch(r"pad\d+", n)]
    per = sorted({round(f[3] * 100 / float(p.get("responseFactor") or 1)
                        / getattr(B, "PAD_STEPS", 1), 1)
                  for n, f, p in faders if p.get("response") == "1"})
    A.check("⛔ the sixteen pads are relative faders, about 20 points of drag a step", len(faders) == 16
            and all(t == "FADER" for t in [by_name[n][1] for n, _f, _p in faders])
            and len(per) == 1 and 18 <= per[0] <= 22, "points a step: %s" % per)

    # TouchOSC's Lua is 5.1 with parts removed (~/Sites/!reference/touchosc.md): `//` is a syntax error
    # that stops a whole script loading, and pcall is nil. lua.org's 5.4 runs both, below, so a
    # script holding either passes every check there and is dead on the phone.
    unsafe = [r[0] for r in nodes if r[3] and ("//" in r[3] or "pcall" in r[3])]
    A.check("⛔ no script holds // or pcall, which TouchOSC's Lua has not", not unsafe,
            "in %s" % unsafe)

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
    for n, t, v, s, text, x, color, tab, bar, parent in nodes:
        if s:
            with open(os.path.join(work, n + ".lua"), "w", encoding="utf-8") as fh:
                fh.write(s)
        row = {"name": n, "type": t, "visible": v, "script": bool(s), "text": text or ""}
        if parent:
            row["parent"] = parent
        if bar is not None and t == "PAGER":
            row["tabbar"] = bar == "1"
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
