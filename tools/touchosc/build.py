#!/usr/bin/env python3
"""Builds the phone's TouchOSC layout, CutIt.tosc: every screen Cut It shows on the phone.

    python3 tools/touchosc/build.py           write it
    python3 tools/touchosc/build.py --check   exit 1 if the committed copy is stale

The design is Brendan's, iterated from mockups on 2026-11-04: TouchOSC's own controls and its own
tab bar, black, with bright red the lead accent and teal the second, monospaced type for every
value and TouchOSC's default font for every label, and every pairing at WCAG AA, which
test/gate/touchosc-assert.py audits from this file.

The tab bar holds the mode's screen: the drum screen in mode 1, the remote screen in every other
mode, following the mode u_net sends. The checklist page is a page of its own, not a tab: test mode,
a tap on the Launchpad's Setup, puts it in place of the tabs, and going off, or choosing a mode,
takes it away (Brendan, 2026-11-04). It carries the line check alone, test/checklists/linecheck.md:
the development checklists are run with the Mac at hand, which sends their Send lines.

It speaks u_net's OSC (ref/device/phone.md): it sends /cutit <command> ... to the Organelle's 9001
and shows what comes back to its 8000. Each control sends from a script of its own; the root's
script takes everything that comes in, and the checklist page's buttons, which it answers itself.
A button that the Organelle answers flashes teal by its color, never its value, so an answer can't
send anything again; a knob or a time signature box takes a value from Cut It without sending it
back.

A .tosc file is zlib-compressed XML (~/Sites/!reference/touchosc.md). The checklist page carries
the line check as data, so an edit to it means a rebuild, and push.sh puts the result on the phone.
"""
import json
import os
import re
import sys
import textwrap
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "CutIt.tosc")
CHECKLISTS = os.path.join(ROOT, "test", "checklists")

W, H, TAB = 896, 414, 44    # an iPhone 11 in landscape, in points, and the tab bar
L, R = 14, 44               # kept clear: the left edge, the notch on the right
TOP = TAB + 10              # where a page's content starts, from the top of the screen


def rgb(r, g, b, a=1.0):
    return (r / 255, g / 255, b / 255, a)


RED, TEAL = rgb(255, 31, 63), rgb(52, 200, 190)
WHITE, GREY, BLACK = rgb(240, 240, 240), rgb(140, 140, 140), rgb(0, 0, 0)
TABOFF = rgb(34, 34, 34)
INK, BTN = BLACK, RED       # the XML's defaults

# The first tab's screen in each mode; every other mode has the remote screen.
MAIN = {"mode-1": "drums"}

# The remote screen's four commands: the button, its label, and what it sends after /cutit.
REMOTE = [("rewire", "re-wire", ["re-wire"]), ("clear", "clear alert", ["clear-alert"]),
          ("tvolca", "test Volca", ["test-note", "m_volca"]),
          ("t404", "test 404", ["test-note", "m_404"])]
# What each acknowledgment u_net sends flashes: /cutit/ack <what> [<which>] -> the button, and
# the color. result is the verdict just given, and flashes Pass or Fail, whichever it was.
ACKS = {"re-wire": ("rewire", TEAL), "clear-alert": ("clear", TEAL),
        "test-note m_volca": ("tvolca", TEAL), "test-note m_404": ("t404", TEAL),
        "drums sync": ("sync", TEAL), "drums snap": ("snap", TEAL),
        "result": ("verdict", WHITE)}
DENS = [1, 2, 4, 8, 16]     # c_steps.lua's R.DENS
MAX_NUM = 32                # c_steps.lua's R.MAX_NUM


# ------------------------------------------------------------------ the checklists
LINES = 11          # text lines on one page of a step
WIDTH = 64          # characters on a line
TITLE_WIDTH = 50
PAGES = 3           # at most, per step
LIST = "linecheck"  # the checklist the page carries: test/checklists/linecheck.md
FIELDS = ("Need", "Do", "Check", "Pass if")   # Note stays on the Mac, and the line check has
                                              # no Send lines: the phone sends none


def plain(text):
    """Markdown to the text the phone shows."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.replace("**", "").replace("`", "")


def steps(name):
    """[(n, title, {field: text})] for one checklist."""
    md = open(os.path.join(CHECKLISTS, name + ".md"), encoding="utf-8").read()
    out = []
    for block in re.split(r"\n- \[ \] ", md)[1:]:
        head = re.match(r"\*\*(\d+)\. (.+?)\*\*", block)
        if not head:
            sys.exit("build: %s: a step with no **<n>. <title>**" % (name + ".md"))
        fields = dict(re.findall(r"^\s+- \*\*([\w ]+):\*\* (.*)$", block, re.M))
        out.append((int(head.group(1)), plain(head.group(2)), fields))
    return out


def checklist(name=LIST):
    """{name, steps: [{n, title, pages}]}, and the problems that make it unfit for the page."""
    st, bad = [], []
    for i, (n, title, fields) in enumerate(steps(name)):
        if n != i + 1:
            bad.append("%s: step %d is numbered %d" % (name, i + 1, n))
        lines = []
        for f in FIELDS:
            if f in fields:
                lines += textwrap.wrap("%s: %s" % (f, plain(fields[f])), WIDTH,
                                       break_on_hyphens=False)
        pages = [lines[k:k + LINES] for k in range(0, max(1, len(lines)), LINES)]
        if len(pages) > PAGES:
            bad.append("%s %d: %d lines, more than %d pages" % (name, n, len(lines), PAGES))
        for v in ("pass", "fail"):
            if len("%s-%d-%s" % (name, n, v)) > 21:
                bad.append("%s %d: its verdict is over the 21 characters an err text may be"
                           % (name, n))
        t = "%d. %s" % (n, title)
        if len(t) > TITLE_WIDTH:
            t = t[:TITLE_WIDTH - 1] + "…"
        st.append({"n": n, "title": t, "pages": pages})
    return {"name": name, "steps": st}, bad


def lua(v):
    """A Python value as a Lua literal: lists to arrays, dicts to tables, strings quoted."""
    if isinstance(v, dict):
        return "{ " + ", ".join("[%s] = %s" % (lua(k), lua(x)) for k, x in v.items()) + " }"
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(lua(x) for x in v) + " }"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return "%g" % v
    return json.dumps(v, ensure_ascii=False)


# ------------------------------------------------------------------ the XML
def prop(kind, key, value):
    if kind == "c":
        v = "<r>%g</r><g>%g</g><b>%g</b><a>%g</a>" % value
    elif kind == "r":
        v = "<x>%d</x><y>%d</y><w>%d</w><h>%d</h>" % value
    elif kind == "s":
        v = "<![CDATA[%s]]>" % value
    elif kind == "b":
        v = "1" if value else "0"
    else:
        v = "%g" % value
    return ('<property type="%s"><key><![CDATA[%s]]></key><value>%s</value></property>'
            % (kind, key, v))


def value(key, default, locked_default=0):
    return ("<value><key><![CDATA[%s]]></key><locked>0</locked><lockedDefaultCurrent>%d"
            "</lockedDefaultCurrent><default><![CDATA[%s]]></default><defaultPull>0</defaultPull>"
            "</value>" % (key, locked_default, default))


# What every control has, as TouchOSC's editor saved them (its Reference page).
COMMON = {"background": ("b", True), "color": ("c", BTN), "cornerRadius": ("f", 1),
          "grabFocus": ("b", True), "interactive": ("b", False), "locked": ("b", False),
          "orientation": ("i", 0), "outline": ("b", False), "outlineStyle": ("i", 1),
          "pointerPriority": ("i", 0), "shape": ("i", 1), "visible": ("b", True)}
KINDS = {
    "LABEL": {"font": ("i", 0), "textAlignH": ("i", 2), "textAlignV": ("i", 2),
              "textClip": ("b", True), "textColor": ("c", INK), "textLength": ("i", 0),
              "textSize": ("i", 15)},
    "BUTTON": {"buttonType": ("i", 0), "interactive": ("b", True), "outline": ("b", True),
               "press": ("b", True), "release": ("b", True), "valuePosition": ("b", False)},
    "FADER": {"bar": ("b", True), "barDisplay": ("i", 0), "centered": ("b", False),
              "cursor": ("b", True), "cursorDisplay": ("i", 0), "grid": ("b", False),
              "gridColor": ("c", rgb(0, 0, 0, 0.25)), "gridSteps": ("i", 10),
              "interactive": ("b", True), "outline": ("b", True), "response": ("i", 0),
              "responseFactor": ("i", 100)},
    "RADIO": {"interactive": ("b", True), "outline": ("b", True), "radioType": ("i", 0),
              "steps": ("i", 5)},
    "PAGER": {"interactive": ("b", True), "outlineStyle": ("i", 0), "tabLabels": ("b", True),
              "tabbar": ("b", True), "tabbarDoubleTap": ("b", False), "tabbarSize": ("i", 40),
              "textSizeOff": ("i", 14), "textSizeOn": ("i", 14)},
}
KINDS["RADIAL"] = dict(KINDS["FADER"])
KINDS["TEXT"] = dict(KINDS["LABEL"], textWrap=("b", True))


def kind_of(v):
    """A property's type in the file, from its value: what node() writes for a key the kind
    doesn't list (a pager page's tabLabel and tab colors, a script)."""
    if isinstance(v, bool):
        return "b"
    if isinstance(v, int):
        return "i"
    if isinstance(v, float):
        return "f"
    if isinstance(v, tuple):
        return "c" if all(isinstance(c, float) and 0 <= c <= 1 for c in v) else "r"
    return "s"
LEFT = 1    # textAlignH: 2, the editor's default, centers


def node(kind, name, frame, children=(), text=None, x=0, **over):
    props = dict(COMMON)
    props.update(KINDS.get(kind, {}))
    props["name"] = ("s", name)
    props["frame"] = ("r", tuple(int(round(v)) for v in frame))
    for k, v in over.items():
        props[k] = (props[k][0] if k in props else kind_of(v), v)
    vals = []
    if kind in ("BUTTON", "FADER", "RADIAL", "RADIO"):
        vals.append(value("x", x))
    if kind == "PAGER":
        vals.append(value("page", 0))
    if kind in ("LABEL", "TEXT"):
        vals.append(value("text", text if text is not None else name, 1))
    vals.append(value("touch", "false"))
    out = ['<node ID="%s" type="%s">' % (uuid.uuid4(), kind)]
    if kind == "GROUP" and name == "root":
        out.append("<includes/>")
    out.append("<properties>" + "".join(prop(t, k, v) for k, (t, v) in sorted(props.items()))
               + "</properties>")
    out.append("<values>" + "".join(vals) + "</values>")
    if children:
        out.append("<children>" + "".join(children) + "</children>")
    out.append("</node>")
    return "".join(out)


def y(v):
    """A y on the screen as a page's own, since a page starts under the tab bar."""
    return v - TAB


# The labels that show a value, anything Cut It's state changes: monospaced. The rest, the
# captions and button names, take TouchOSC's default font (Brendan, 2026-11-04).
VALUES = {"tempo", "play", "glob", "link", "alert", "pending", "num", "den", "drunkv", "skipv",
          "movev", "pname", "pvalue", "rstatus", "ralert", "rlink", "cpos", "tmode"}
MONO = 1


def label(name, f, text, size, ink=WHITE, align=2):
    mono = name in VALUES or re.fullmatch(r"pad\d+l", name) is not None
    return node("LABEL", name, f, text=text, background=False, textColor=ink, textSize=size,
                textAlignH=align, font=MONO if mono else 0)


def button(name, f, col, script=None, x=0):
    """A native button with a whole outline, so where it ends reads at 3:1 whatever its fill."""
    over = {"script": script} if script else {}
    return node("BUTTON", name, f, color=col, x=x, outlineStyle=0, **over)


def led(name, f, col, on=0):
    """A lamp: a button no finger moves, lit by its value."""
    return node("BUTTON", name, f, color=col, x=on, interactive=False, outline=False, shape=2)


def sends(args):
    """The script of a button that sends /cutit <args> on its press."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 then sendOSC('/cutit', %s) end\n"
            "end\n" % ", ".join(lua(a) for a in args))


def pad_script(n):
    """A drum pad: a press selects its track, and the state lights the one selected with
    notify('lit'), which a lit pad never answers. When it did, four pads pressed at once lit in
    turn on the phone, each selecting itself again, and the selection bounced between Cut It and
    the phone for as long as they were held (Brendan, 2026-11-04)."""
    return ("local lit = 0\n"
            "function onReceiveNotify(key, value)\n"
            "  if key == 'lit' then\n"
            "    lit = value\n"
            "    self.values.x = value\n"
            "  end\n"
            "end\n"
            "function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 and lit ~= 1 then\n"
            "    sendOSC('/cutit', 'drums', 'select', %d)\n"
            "  end\n"
            "end\n" % n)


def tells(what, which):
    """The script of a button the root answers: root:notify(what, which) on its press."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 then root:notify(%s, %s) end\n"
            "end\n" % (lua(what), lua(which)))


# A value Cut It's state hands a control with notify('state', v) is the one it knows, so setting
# it sends nothing; a value a finger moves it to sends, and tells the root it was touched, so the
# root leaves it alone for a second while Cut It catches up.
KNOWS = ("local known\n"
         "function onReceiveNotify(key, value)\n"
         "  if key == 'state' then\n"
         "    known = value\n"
         "    self.values.x = %s\n"
         "  end\n"
         "end\n")


def knob(name, cx, cy, d, caption):
    """A ring knob, 0 to 100, its value in its middle and its name under it."""
    script = (KNOWS % "value / 100") + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.floor(self.values.x * 100 + 0.5)\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', 'drums', '%s', v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (name, name))
    f = (cx - d / 2, cy - d / 2, d, d)
    return [node("RADIAL", name, f, color=RED, outlineStyle=0, script=script),
            label(name + "v", f, "0%", 14),
            label(name + "c", (cx - 60, cy + d / 2 + 2, 120, 20), caption, 14, GREY)]


def box(name, f, steps, cmd, factor):
    """A time signature box: a native fader with no bar, dragged up or down, one step at a time.
    c_steps takes the time signature a step at a time, num or den <-1 or 1>, so a drag across n
    steps sends n of them; the state hands it back its step, 1 to steps."""
    script = (KNOWS % ("(value - 0.5) / %d" % steps)) + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local i = math.max(1, math.min(%d, math.floor(self.values.x * %d) + 1))\n"
        "  if known == nil then known = i return end\n"
        "  local d = i - known\n"
        "  if d == 0 then return end\n"
        "  known = i\n"
        "  for _ = 1, math.abs(d) do sendOSC('/cutit', 'drums', '%s', d > 0 and 1 or -1) end\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (steps, steps, cmd, name))
    # response 1 is relative, and responseFactor scales the drag: at 100 one box's height
    # moves the whole range, which made the top number's 32 steps 2 points each (Brendan,
    # 2026-11-04: hard to settle on one number)
    return node("FADER", name, f, color=RED, outlineStyle=0, bar=False, cursor=False,
                response=1, responseFactor=factor, script=script)


def group(name, kids, visible=True):
    return node("GROUP", name, (0, 0, W, H - TAB), kids, background=False, visible=visible)


def page(name, tab, kids):
    return node("GROUP", name, (0, TAB, W, H - TAB), kids, color=rgb(0, 0, 0, 0.0),
                tabLabel=tab, tabColorOff=TABOFF, tabColorOn=RED, textColorOff=WHITE,
                textColorOn=BLACK)


# ------------------------------------------------------------------ the drum screen (mode 1)
def drums():
    k = []
    # left: the tempo, the transport, the global last step, the link, the alert
    k.append(label("tempo", (L, y(TOP), 190, 70), "-", 64, RED, align=1))
    k.append(label("tempoc", (L + 2, y(TOP + 70), 190, 18), "bpm", 14, GREY, align=1))
    k.append(led("playled", (L, y(TOP + 108), 18, 18), TEAL))
    k.append(label("play", (L + 28, y(TOP + 104), 160, 26), "stopped", 18, WHITE, align=1))
    k.append(label("glob", (L, y(TOP + 146), 190, 44), "16", 36, WHITE, align=1))
    k.append(label("globc", (L + 2, y(TOP + 190), 190, 18), "last step", 14, GREY, align=1))
    k.append(led("linkled", (L, y(TOP + 232), 14, 14), TEAL))
    k.append(label("link", (L + 24, y(TOP + 226), 160, 26), "no link", 16, GREY, align=1))
    k.append(label("alert", (L, y(TOP + 262), 190, 40), "no alerts", 14, GREY, align=1))
    # middle: the sixteen pads as the Launchpad lays them out, pad 1 at the top left. Teal
    # with a dot has its own last step; the selected track is lit; each shows its last step.
    size, gap, x0 = 68, 8, 214
    for n in range(1, 17):
        r, c = (n - 1) // 4, (n - 1) % 4
        f = (x0 + c * (size + gap), y(TOP + r * (size + gap)), size, size)
        k.append(button("pad%d" % n, f, RED, pad_script(n)))
        k.append(label("pad%dl" % n, f, "16", 20))
    # right: sync and snap, the line saying one waits, three knobs, the time signature
    rx, rw = 536, W - R - 536
    for i, (name, text) in enumerate((("sync", "sync first steps"), ("snap", "snap to global"))):
        f = (rx + i * (rw / 2 + 4), y(TOP), rw / 2 - 4, 50)
        k.append(button(name, f, RED, sends(["drums", name])))
        k.append(label(name + "l", f, text, 15))
    k.append(label("pending", (rx, y(TOP + 54), rw, 18), "", 13, TEAL))
    d = 78
    for i, name in enumerate(("drunk", "skip", "move")):
        k += knob(name, rx + rw / 6 + i * rw / 3, y(TOP + 84 + d / 2), d, name)
    ty = TOP + 206
    k.append(label("timec", (rx, y(ty), 100, 18), "time", 14, GREY, align=1))
    bw, bh, by = 84, 64, ty + 26
    k.append(box("numbox", (rx + 20, y(by), bw, bh), MAX_NUM, "num", 10))
    k.append(label("num", (rx + 20, y(by), bw, bh), "4", 32))
    k.append(label("slash", (rx + 20 + bw, y(by), 56, bh), "/", 32, GREY))
    k.append(box("denbox", (rx + 76 + bw, y(by), bw, bh), len(DENS), "den", 50))
    k.append(label("den", (rx + 76 + bw, y(by), bw, bh), "4", 32))
    return group("drums", k, visible=False)


# ------------------------------------------------------------------ the remote screen (modes 2-6)
def remote():
    k = []
    k.append(label("pname", (L, y(TOP), 470, 30), "ready", 22, GREY, align=1))
    k.append(label("pvalue", (L, y(TOP + 30), 470, 110), "-", 96, RED, align=1))
    k.append(label("rstatus", (L, y(TOP + 160), 220, 44), "-", 30, WHITE, align=1))
    k.append(label("rstatusc", (L + 2, y(TOP + 204), 220, 18), "tempo", 14, GREY, align=1))
    k.append(led("ralertled", (L, y(TOP + 248), 16, 16), RED))
    k.append(label("ralert", (L + 26, y(TOP + 242), 440, 28), "no alerts", 18, GREY, align=1))
    k.append(led("rlinkled", (L, y(TOP + 288), 14, 14), TEAL))
    k.append(label("rlink", (L + 24, y(TOP + 282), 160, 26), "no link", 16, GREY, align=1))
    rx, rw = 500, W - R - 500
    bw, bh = rw / 2 - 6, 140
    for i, (name, text, args) in enumerate(REMOTE):
        r, c = i // 2, i % 2
        f = (rx + c * (bw + 12), y(TOP + r * (bh + 12)), bw, bh)
        k.append(button(name, f, RED, sends(args)))
        k.append(label(name + "l", f, text, 20))
    return group("remote", k)


# ------------------------------------------------------------------ the checklist page
def checks():
    k = []
    k.append(label("cpos", (L, y(TOP), 340, 40), "-", 16, GREY, align=1))
    k.append(led("tled", (W - R - 170, y(TOP + 13), 14, 14), TEAL))
    k.append(label("tmode", (W - R - 148, y(TOP), 148, 40), "no link", 16, GREY, align=1))
    k.append(label("ctitle", (L, y(TOP + 52), 600, 30), "-", 22, WHITE, align=1))
    k.append(node("TEXT", "cbody", (L, y(TOP + 88), 600, 236), text="", background=False,
                  textColor=rgb(210, 210, 210), textSize=16, textAlignH=1, textAlignV=1))
    rx, rw = 640, W - R - 640
    hw = rw / 2 - 5
    for i, (name, text, col) in enumerate((("cpass", "Pass", TEAL), ("cfail", "Fail", RED))):
        f = (rx + i * (hw + 10), y(TOP + 52), hw, 140)
        k.append(button(name, f, col, tells("press", name)))
        k.append(label(name + "l", f, text, 22))
    for i, (name, text) in enumerate((("cback", "Back"), ("cfwd", "Next"))):
        f = (rx + i * (hw + 10), y(TOP + 204), hw, 102)
        k.append(button(name, f, GREY, tells("press", name)))
        k.append(label(name + "l", f, text, 20))
    return k


# ------------------------------------------------------------------ the root's script
ROOT_LUA = r"""-- Cut It on the phone: the tabs, and what u_net sends, onto the screens
-- (ref/device/phone.md). Generated by tools/touchosc/build.py.
local MAIN = %(main)s
local ACKS = %(acks)s
local CHECK = %(check)s
local DENS = %(dens)s
local RED, TEAL, WHITE, GREY, BLACK = %(red)s, %(teal)s, %(white)s, %(grey)s, %(black)s

local found, shown = {}, {}
local function get(name)
  local c = found[name]
  if not c then c = root:findByName(name, true); found[name] = c end
  return c
end
-- Set a text, a color or a value only when it differs, since update() runs every frame.
local function text(name, t)
  if shown[name] ~= t then shown[name] = t; get(name).values.text = t end
end
local function color(name, c)
  if shown[name .. ':c'] ~= c then shown[name .. ':c'] = c; get(name).color = c end
end
local function ink(name, c)
  if shown[name .. ':i'] ~= c then shown[name .. ':i'] = c; get(name).textColor = c end
end
local function lit(name, on)
  local x = on and 1 or 0
  if get(name).values.x ~= x then get(name).values.x = x end
end
local function arg(a, i)
  return a[i] and a[i].value or 0
end

-- ---------------------------------------------------------------- the tabs and test mode
local mode, testOn = nil, nil

-- A mode fills the tab with its screen, and names it.
local function setMode(m)
  if m == mode then return end
  mode = m
  local main = MAIN[m] or 'remote'
  get('drums').visible = main == 'drums'
  get('remote').visible = main == 'remote'
  get('main').tabLabel = main
end

-- Test mode puts the checklist page in place of the tabs, and going off takes it away.
local function setTest(on)
  if on == testOn then return end
  testOn = on
  get('pager').visible = not on
  get('checkpager').visible = on
end

-- ---------------------------------------------------------------- flashes
local flash = {}
local BASE = { rewire = RED, clear = RED, tvolca = RED, t404 = RED, sync = RED, snap = RED,
               cpass = TEAL, cfail = RED }
local verdict = 'cpass'

local function ack(a)
  local what, which = tostring(arg(a, 1)), a[2] and tostring(a[2].value)
  local hit = (which and ACKS[what .. ' ' .. which]) or ACKS[what]
  if not hit then return end
  local name = hit[1] == 'verdict' and verdict or hit[1]
  flash[name] = { getMillis() + 300, hit[2] }
end

-- ---------------------------------------------------------------- the drum screen
local touchedAt = {}

-- A value from the state, to a control that knows it, unless a finger was just on it.
local function hand(name, v)
  local c = get(name)
  if c.values.touch or getMillis() - (touchedAt[name] or -100000) < 1000 then return end
  c:notify('state', v)
end

-- c_steps' 41 numbers: playing, the global last step, the selected track, a pending sync or
-- snap (1, 2), the sixteen last steps, then 1 for each track with its own, then the time
-- signature, the drunkenness and the selected track's skip and move.
local function drums(a)
  if #a < 41 then return end
  local playing, track, pending = arg(a, 1) == 1, math.floor(arg(a, 3)), arg(a, 4)
  text('play', playing and 'playing' or 'stopped')
  lit('playled', playing)
  text('glob', tostring(math.floor(arg(a, 2))))
  text('pending', pending == 2 and 'snap waits for step 1'
       or (pending == 1 and 'sync waits for step 1' or ''))
  for n = 1, 16 do
    local own, sel = arg(a, 20 + n) == 1, n == track
    color('pad' .. n, own and TEAL or RED)
    local want = sel and 1 or 0
    if get('pad' .. n).values.x ~= want then get('pad' .. n):notify('lit', want) end
    text('pad' .. n .. 'l', (own and '• ' or '') .. math.floor(arg(a, 4 + n)))
    ink('pad' .. n .. 'l', sel and BLACK or WHITE)
  end
  local num, den = math.floor(arg(a, 37)), math.floor(arg(a, 38))
  text('num', tostring(num))
  text('den', tostring(den))
  hand('numbox', num)
  for i, d in ipairs(DENS) do if d == den then hand('denbox', i) end end
  hand('drunk', math.floor(arg(a, 39)))
  hand('skip', math.floor(arg(a, 40)))
  hand('move', math.floor(arg(a, 41)))
end

-- ---------------------------------------------------------------- the checklist page
local si, pg = 1, 1
local marks = {}

local function paintCheck()
  local st = CHECK.steps[si]
  local pos = si .. ' of ' .. #CHECK.steps
  if #st.pages > 1 then pos = pos .. '   ' .. pg .. '/' .. #st.pages end
  local m = marks[si]
  if m then pos = pos .. '   ' .. (m == 'pass' and 'passed' or 'failed') end
  text('cpos', pos)
  text('ctitle', st.title)
  text('cbody', table.concat(st.pages[pg] or {}, '\n'))
end

local PRESS = {
  cfwd = function()
    local st = CHECK.steps[si]
    if pg < #st.pages then pg = pg + 1
    elseif si < #CHECK.steps then si, pg = si + 1, 1 end
  end,
  cback = function()
    if pg > 1 then pg = pg - 1 elseif si > 1 then si, pg = si - 1, 1 end
  end,
}
for _, v in ipairs({ 'pass', 'fail' }) do
  PRESS['c' .. v] = function()
    local st = CHECK.steps[si]
    sendOSC('/cutit', 'result', CHECK.name .. '-' .. st.n .. '-' .. v)
    marks[si], verdict = v, 'c' .. v
    if si < #CHECK.steps then si, pg = si + 1, 1 end
  end
end

-- ---------------------------------------------------------------- what comes in
local lastHb = -100000

function init()
  paintCheck()
end

local function alert(a)
  local level, t = tostring(arg(a, 2)), tostring(arg(a, 4))
  local none = level == 'none'
  text('alert', none and 'no alerts' or t)
  text('ralert', none and 'no alerts' or (level .. '  ' .. t))
  ink('alert', none and GREY or RED)
  ink('ralert', none and GREY or RED)
  lit('ralertled', not none)
end

function onReceiveOSC(message, connections)
  local path, a = message[1], message[2]
  if path == '/cutit/drums' then
    drums(a)
  elseif path == '/cutit/hb' then
    lastHb = getMillis()
    setTest(arg(a, 2) == 1)
  elseif path == '/cutit/mode' then
    setMode(tostring(arg(a, 2)))
  elseif path == '/cutit/param' then
    local unit = a[3] and tostring(a[3].value) or '-'
    local v = arg(a, 2)
    text('pname', tostring(arg(a, 1)))
    text('pvalue', (type(v) == 'number' and string.format('%%g', v) or tostring(v))
         .. ((unit ~= '-' and unit ~= '') and (' ' .. unit) or ''))
  elseif path == '/cutit/status' then
    -- u_tempo's status is <bpm>-bpm; anything else is shown as it came
    local s = tostring(arg(a, 1))
    local bpm = s:match('^([%%d.]+)%%-bpm$')
    text('tempo', bpm or s)
    text('rstatus', bpm and (bpm .. ' bpm') or s)
  elseif path == '/cutit/alert' then
    alert(a)
  elseif path == '/cutit/ack' then
    ack(a)
  end
end

function onReceiveNotify(key, value)
  if key == 'touched' then
    touchedAt[value] = getMillis()
  elseif key == 'press' and PRESS[value] then
    PRESS[value]()
    paintCheck()
  end
end

function update()
  local now = getMillis()
  local up = now - lastHb < 1500
  for _, k in ipairs({ 'link', 'rlink' }) do text(k, up and 'link' or 'no link') end
  lit('linkled', up)
  lit('rlinkled', up)
  lit('tled', up and testOn)
  text('tmode', not up and 'no link' or (testOn and 'test mode on' or 'test mode off'))
  ink('tmode', (up and testOn) and TEAL or GREY)
  for _, k in ipairs({ 'drunk', 'skip', 'move' }) do
    text(k .. 'v', math.floor(get(k).values.x * 100 + 0.5) .. '%%')
  end
  for name, base in pairs(BASE) do
    local f = flash[name]
    color(name, (f and now < f[1]) and f[2] or base)
  end
end
"""


def lua_color(c):
    return "Color(%g, %g, %g)" % c[:3]


def root_script(check):
    acks = "{ " + ", ".join("[%s] = { %s, %s }" % (lua(k), lua(v[0]), lua_color(v[1]))
                            for k, v in ACKS.items()) + " }"
    return ROOT_LUA % {
        "main": lua(MAIN), "acks": acks, "check": lua(check), "dens": lua(DENS),
        "red": lua_color(RED), "teal": lua_color(TEAL), "white": lua_color(WHITE),
        "grey": lua_color(GREY), "black": lua_color(BLACK)}


def build(name=LIST):
    """The layout, its checklist page carrying the checklist named, from test/checklists/: the
    line check, but for the gate, which runs the page on a longer checklist too."""
    check, bad = checklist(name)
    if bad:
        sys.exit("build: %s doesn't fit the page:\n  " % (name + ".md") + "\n  ".join(bad))
    tabs = dict(color=BLACK, background=False, tabbarSize=TAB, textSizeOff=22, textSizeOn=22)
    pager = node("PAGER", "pager", (0, 0, W, H), [page("main", "remote", [drums(), remote()])],
                 **tabs)
    # the checklist page, under its own one-tab bar, over the tabs in test mode
    checkpager = node("PAGER", "checkpager", (0, 0, W, H),
                      [page("checks", "line check", checks())], visible=False, **tabs)
    root = node("GROUP", "root", (0, 0, W, H), [pager, checkpager], color=BLACK,
                script=root_script(check))
    return '<?xml version="1.0" encoding="UTF-8"?><lexml version="6">' + root + "</lexml>"


def strip_ids(s):
    return re.sub(r'ID="[^"]+"', 'ID=""', s)


def main_():
    xml = build()
    if "--check" in sys.argv:
        try:
            old = zlib.decompress(open(OUT, "rb").read()).decode("utf-8")
        except OSError:
            sys.exit(1)
        sys.exit(0 if strip_ids(old) == strip_ids(xml) else 1)
    with open(OUT, "wb") as fh:
        fh.write(zlib.compress(xml.encode("utf-8"), 9))
    print("wrote %s (%d bytes of XML)" % (os.path.relpath(OUT), len(xml)))


if __name__ == "__main__":
    main_()
