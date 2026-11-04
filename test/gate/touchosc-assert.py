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
        text = None
        for v in n.getElementsByTagName("values")[0].childNodes:
            if v.getElementsByTagName("key")[0].firstChild.data == "text":
                d = v.getElementsByTagName("default")[0].firstChild
                text = d.data if d is not None else ""
        out.append((props.get("name"), n.getAttribute("type"), props.get("visible") == "1",
                    props.get("script"), text))
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


def expect(lists):
    """What the Lua test needs to know about the checklists, worked out here from the same
    data the layout carries: a step with a Send line that is not its checklist's last, and a
    step on more than one page that is not either."""
    names = [{"name": c["name"], "steps": len(c["steps"])} for c in lists]
    send = next((ci, si, s) for ci, c in enumerate(lists) for si, s in enumerate(c["steps"])
                if s["sends"] and si + 1 < len(c["steps"]))
    multi = next((ci, si, s) for ci, c in enumerate(lists) for si, s in enumerate(c["steps"])
                 if len(s["pages"]) > 1 and si + 1 < len(c["steps"]))
    ci, si, s = send
    msgs = [["/cutit", "send"] + [float(t) if re.fullmatch(r"-?\d+(\.\d+)?", t) else t
                                  for t in m.split()] for m in s["sends"]]
    e = {"lists": names,
         "send": {"ci": ci + 1, "si": si + 1, "title": s["title"], "sent": msgs,
                  "verdict": "%s-%d-pass" % (lists[ci]["name"], s["n"])}}
    ci, si, s = multi
    e["multi"] = {"ci": ci + 1, "si": si + 1, "steps": len(lists[ci]["steps"]),
                  "pages": len(s["pages"]), "verdict": "%s-%d-fail" % (lists[ci]["name"], s["n"])}
    return "return " + lua(e) + "\n"


def main():
    print("\n=== A. the layout, checked by READING -- no TouchOSC involved ===")
    A.check("the committed layout is build.py's output",
            os.path.exists(LAYOUT) and B.strip_ids(zlib.decompress(open(LAYOUT, "rb").read())
                                                   .decode("utf-8")) == B.strip_ids(B.build()),
            "run tools/touchosc/build.py")
    doc = xml.dom.minidom.parseString(zlib.decompress(open(LAYOUT, "rb").read()))
    nodes = controls(doc)
    names = [n for n, _t, _v, _s, _x in nodes]
    dupes = sorted({n for n in names if names.count(n) > 1})
    A.check("⛔ every control has a name of its own", not dupes and None not in names,
            "named twice: %s" % dupes)
    A.note("%d controls, %d with a script" % (len(nodes), sum(1 for x in nodes if x[3])))

    msgs = [m for _n, _t, _v, s, _x in nodes for m in sent(s)]
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
        acked = ([c for c in ucmd if c not in ("test-note", "drums", "send")]
                 + ["test-note " + d for d in udev] + ["send", "test-off"]
                 + ["drums " + a for a in uacks if a != "select"])
        A.check("every acknowledgment u_net sends lights a cell",
                sorted(acked) == sorted(B.ACKS),
                "u_net acknowledges %s, the layout lights %s" % (sorted(acked), sorted(B.ACKS)))

    print("\n=== B. its scripts, run under a stand-in for TouchOSC ===")
    work = S.work_dir("touchosc")
    os.makedirs(work, exist_ok=True)
    rows = []
    for n, t, v, s, x in nodes:
        if s:
            with open(os.path.join(work, n + ".lua"), "w", encoding="utf-8") as fh:
                fh.write(s)
        rows.append({"name": n, "type": t, "visible": v, "script": bool(s), "text": x or ""})
    with open(os.path.join(work, "controls.lua"), "w", encoding="utf-8") as fh:
        fh.write("return " + lua(rows) + "\n")
    lists, _bad = B.checklists()
    with open(os.path.join(work, "expect.lua"), "w", encoding="utf-8") as fh:
        fh.write(expect(lists))
    rc_lua = S.lua("test/gate/lua/touchosc_test.lua", work, *[a for a in sys.argv[1:]
                                                              if a == "-v"])
    if not KEEP:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if (A.report() or rc_lua) else 0


if __name__ == "__main__":
    sys.exit(main())
