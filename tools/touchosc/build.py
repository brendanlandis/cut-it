#!/usr/bin/env python3
"""Builds the phone's TouchOSC layout, CutIt.tosc: every screen Cut It shows on the phone.

    python3 tools/touchosc/build.py           write it
    python3 tools/touchosc/build.py --check   exit 1 if the committed copy is stale

Each Launchpad mode has its own row of tabs along the top, and the last tab of every mode is the
checklist page (Brendan, 2026-11-04). Mode 1 has the drum screen and the checklists; every other
mode, the remote screen and the checklists. The tabs follow the mode u_net sends; test mode coming
on brings up the checklist tab, and going off, the mode's first tab.

It speaks u_net's OSC (ref/device/phone.md): it sends /cutit <command> ... to the Organelle's 9001
and shows what comes back to its 8000. Each control sends from a script of its own; the root's
script takes everything that comes in, and the checklist page's buttons, which it answers itself.

A .tosc file is zlib-compressed XML (~/Sites/!reference/touchosc.md). The checklist page carries
test/checklists/ as data, so a checklist edited means a rebuild, and push.sh puts the result on the
phone.
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

W, H = 896, 414         # an iPhone 11 in landscape, in points
RIGHT, FOOT = 44, 34    # kept clear: the notch on the right, the home indicator at the bottom
TAB_H = 30              # the tab bar along the top
# The screens are drawn in the units the PdParty scenes used, 426 by 190, and scaled into what
# the tab bar leaves, centered across the width.
S = (H - TAB_H - 4 - FOOT) / 190
X0 = round((W - RIGHT - 426 * S) / 2)
Y0 = TAB_H + 4


def rgb(r, g, b, a=1.0):
    return (r / 255, g / 255, b / 255, a)


INK, PAPER, BTN, LIT = rgb(24, 24, 24), rgb(232, 232, 232), rgb(252, 252, 252), rgb(140, 210, 140)
DOWN, AMBER, TABOFF = rgb(232, 140, 140), rgb(248, 208, 112), rgb(90, 90, 90)
GROUND = rgb(40, 40, 40)
PRESS = rgb(255, 255, 255, 0.35)
# A pad: following the global last step, with its own, selected, selected with its own.
PADS = [(rgb(200, 200, 200), rgb(40, 40, 40)), (rgb(248, 208, 112), rgb(60, 40, 0)),
        (rgb(60, 60, 60), rgb(255, 255, 255)), (rgb(150, 100, 20), rgb(255, 255, 255))]

# The tabs each mode has, the last always the checklists, and what each tab says.
TABS = {"mode-1": ["drums", "checks"]}
DEFAULT_TABS = ["remote", "checks"]
TAB_LABELS = {"drums": "drums", "remote": "remote", "checks": "checklists"}
TABMAX = 4
SCREENS = ["remote", "drums", "checks"]

# The remote screen's four commands: the cell that is pressed, and what it sends after /cutit.
REMOTE = [("rewire", "re-wire", ["re-wire"]), ("clear", "clear-alert", ["clear-alert"]),
          ("tvolca", "test-volca", ["test-note", "m_volca"]),
          ("t404", "test-404", ["test-note", "m_404"])]
# What each acknowledgment u_net sends lights: /cutit/ack <what> [<which>] -> the cell, and the
# color it flashes. test-off is a Send refused while test mode is off.
ACKS = {"re-wire": ("rewire", LIT), "clear-alert": ("clear", LIT),
        "test-note m_volca": ("tvolca", LIT), "test-note m_404": ("t404", LIT),
        "drums sync": ("sync", LIT), "drums snap": ("snap", LIT),
        "send": ("csend", LIT), "test-off": ("csend", DOWN), "result": ("verdict", LIT)}


# ------------------------------------------------------------------ the checklists
LINES = 9           # text lines on one page of a step
WIDTH = 55          # characters on a line
TITLE_WIDTH = 46
PAGES = 3           # at most, per step
# The buses u_inject takes (test/checklists/README.md, Send lines).
BUSES = {"disp", "err", "mode", "panic", "param", "start", "stop", "tempo"}
FIELDS = ("Need", "Send", "Do", "Check", "Pass if")   # Note stays on the Mac


def order():
    """The checklists, in the README's table order."""
    names = re.findall(r"^\| \[(\w+)\]\(\w+[.]md\) \|",
                       open(os.path.join(CHECKLISTS, "README.md"), encoding="utf-8").read(), re.M)
    if not names:
        sys.exit("build: no checklist table in test/checklists/README.md")
    return names


def plain(text):
    """Markdown to the text the phone shows."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.replace("**", "").replace("`", "")


def steps(name):
    """[(n, title, {field: text}, [send message, ...])] for one checklist."""
    md = open(os.path.join(CHECKLISTS, name + ".md"), encoding="utf-8").read()
    out = []
    for block in re.split(r"\n- \[ \] ", md)[1:]:
        head = re.match(r"\*\*(\d+)\. (.+?)\*\*", block)
        if not head:
            sys.exit("build: %s: a step with no **<n>. <title>**" % (name + ".md"))
        fields = dict(re.findall(r"^\s+- \*\*([\w ]+):\*\* (.*)$", block, re.M))
        sends = []
        if "Send" in fields:
            line = re.search(r"`([^`]+)`", fields["Send"])
            if not line:
                sys.exit("build: %s step %s: a Send with no `line`" % (name + ".md", head.group(1)))
            sends = [m.strip() for m in line.group(1).split(";") if m.strip()]
        out.append((int(head.group(1)), plain(head.group(2)), fields, sends))
    return out


def checklists():
    """[{name, steps: [{n, title, pages, sends}]}], and the problems that make one unfit."""
    lists, bad = [], []
    for name in order():
        st = []
        for i, (n, title, fields, sends) in enumerate(steps(name)):
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
            for m in sends:
                if m.split()[0] not in BUSES:
                    bad.append("%s %d: Send names %s, which u_inject refuses" % (name, n, m.split()[0]))
            t = "%d. %s" % (n, title)
            if len(t) > TITLE_WIDTH:
                t = t[:TITLE_WIDTH - 1] + "…"
            st.append({"n": n, "title": t, "pages": pages, "sends": sends})
        lists.append({"name": name, "steps": st})
    return lists, bad


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
}
LEFT = 1    # textAlignH: 2, the editor's default, centers


def node(kind, name, frame, children=(), text=None, **over):
    props = dict(COMMON)
    props.update(KINDS.get(kind, {}))
    props["name"] = ("s", name)
    props["frame"] = ("r", tuple(int(round(v)) for v in frame))
    for k, v in over.items():
        props[k] = (props[k][0] if k in props else ("s" if k == "script" else "b"), v)
    vals = []
    if kind in ("BUTTON", "FADER"):
        vals.append(value("x", 0))
    if kind == "LABEL":
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


def at(x, y, w, h):
    """The screens' units as points, below the tab bar."""
    return (X0 + x * S, Y0 + y * S, w * S, h * S)


# TouchOSC draws a label's or a button's background faint and a box at full strength
# (~/Sites/!reference/touchosc.md), so a colored cell is a box, <name>bg, under a label with no
# background, <name>, which holds the text.
def cell(name, frame, text, size, fill=PAPER, ink=INK, align=2):
    return [node("BOX", name + "bg", frame, color=fill),
            node("LABEL", name, frame, text=text, background=False, textColor=ink,
                 textSize=round(size), textAlignH=align)]


def words(name, frame, text, size, ink=PAPER, align=2):
    """Text straight on the screen."""
    return node("LABEL", name, frame, text=text, background=False, textColor=ink,
                textSize=round(size), textAlignH=align)


def sends(args):
    """The script of a touch that sends /cutit <args> on its press."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 then sendOSC('/cutit', %s) end\n"
            "end\n" % ", ".join(lua(a) for a in args))


def tells(what, which):
    """The script of a touch the root answers: root:notify(what, which) on its press."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 then root:notify(%s, %s) end\n"
            "end\n" % (lua(what), lua(which)))


def touch(name, frame, script):
    """The touch over a cell: no background, so the cell shows through, a flash while pressed."""
    return node("BUTTON", name, frame, background=False, outline=False, color=PRESS,
                script=script)


def fader(name, x, y, w, h):
    """A slider, 0 to 100, its percent beside it. It sends whole percents when its value moves
    off the last one it knows, its own or one the root hands it from Cut It's state with
    notify('state'), so a value from Cut It is never sent back; and it tells the root it was
    touched, so the root leaves it alone for a second."""
    script = ("local known\n"
              "function onReceiveNotify(key, value)\n"
              "  if key == 'state' then\n"
              "    known = value\n"
              "    self.values.x = value / 100\n"
              "  end\n"
              "end\n"
              "function onValueChanged(key)\n"
              "  if key ~= 'x' then return end\n"
              "  local v = math.floor(self.values.x * 100 + 0.5)\n"
              "  if v == known then return end\n"
              "  known = v\n"
              "  sendOSC('/cutit', 'drums', '%s', v)\n"
              "  root:notify('touched', '%s')\n"
              "end\n" % (name, name))
    lw = 46
    return [words(name + "v", at(x, y, lw, h), name + " 0%", 10 * S),
            node("FADER", name, at(x + lw, y, w - lw, h), color=LIT, orientation=1,
                 script=script)]


def group(name, children, visible):
    return node("GROUP", name, (0, 0, W, H), children, background=False, visible=visible)


# ------------------------------------------------------------------ the screens
def tab_bar():
    """TABMAX tab slots and the mode's name; the root labels and shows them per mode."""
    c, tw, gap = [], 150, 6
    for i in range(1, TABMAX + 1):
        f = (8 + (i - 1) * (tw + gap), 2, tw, TAB_H - 2)
        c += cell("tab%d" % i, f, "-", 15, TABOFF, PAPER)
        c.append(touch("tab%dt" % i, f, tells("tab", i)))
    c.append(words("mode", (W - RIGHT - 160, 2, 160, TAB_H - 2), "-", 13))
    return c


def remote_screen():
    """Left: the last parameter's name and value, the status, the alert and the link. Right: the
    four commands, each cell flashing on the Organelle's answer."""
    c = []
    for name, y, h, text, size in (("rname", 4, 32, "READY", 18), ("rvalue", 38, 60, "-", 40),
                                   ("rstatus", 100, 28, "-", 16)):
        c += cell(name, at(4, y, 250, h), text, size * S)
    c += cell("ralvl", at(4, 130, 82, 26), "-", 12 * S)
    c += cell("ralert", at(90, 130, 164, 26), "no-alerts", 12 * S)
    c += cell("rlink", at(4, 158, 250, 32), "NO-LINK", 16 * S, DOWN)
    for k, (name, text, args) in enumerate(REMOTE):
        f = at(262, 4 + 47 * k, 160, 44)
        c += cell(name, f, text, 14 * S, BTN)
        c.append(touch(name + "t", f, sends(args)))
    return c


PAD, PITCH = 33, 35
BX, BW, BH = 304, 118, 34


def drum_screen():
    c = []
    # down the left: the transport, the tempo, the global last step, the alert and the link
    for name, y, h, text, size in (("play", 4, 30, "stopped", 14), ("status", 38, 44, "-", 20),
                                   ("glob", 86, 34, "last 16", 16),
                                   ("alert", 124, 28, "no-alerts", 12),
                                   ("link", 156, 32, "NO-LINK", 16)):
        c += cell(name, at(4, y, 146, h), text, size * S, DOWN if name == "link" else PAPER)
    # the pads, as the Launchpad lays them out, pad 1 at the top left: the cell shows the
    # track's last step and its state, the touch over it selects the track
    for n in range(1, 17):
        r, k = (n - 1) // 4, (n - 1) % 4
        f = at(156 + k * PITCH, 4 + r * PITCH, PAD, PAD)
        c += cell("pad%d" % n, f, "16", 14 * S, PADS[0][0], PADS[0][1])
        c.append(touch("tap%d" % n, f, sends(["drums", "select", n])))
    # the selected track's chances under the pads
    for name, y in (("skip", 146), ("move", 170)):
        c += fader(name, 156, y, 3 * PITCH + PAD, 20)
    # down the right: sync and snap, the line saying one waits, the time signature, drunk
    for name, y, text in (("sync", 4, "sync first steps"), ("snap", 42, "snap to global")):
        f = at(BX, y, BW, BH)
        c += cell(name, f, text, 12 * S, BTN)
        c.append(touch(name + "t", f, sends(["drums", name])))
    c.append(words("pending", at(BX, 78, BW, 14), "", 9 * S))
    for name, y in (("num", 95), ("den", 127)):
        f = at(BX, y, 28, 28)
        c += cell(name + "m", f, "−", 16 * S, BTN)
        c.append(touch(name + "mt", f, sends(["drums", name, -1])))
        c += cell(name, at(BX + 32, y, 54, 28), "4", 16 * S)
        f = at(BX + 90, y, 28, 28)
        c += cell(name + "p", f, "+", 16 * S, BTN)
        c.append(touch(name + "pt", f, sends(["drums", name, 1])))
    c += fader("drunk", BX, 160, BW, 30)
    return c


# The checklist page's buttons: name, text, x, y, w, h, in the screens' units.
CHECK_BUTTONS = [("cprev", "◀", 4, 3, 30, 22), ("cnext", "▶", 136, 3, 30, 22),
                 ("csend", "Send", 316, 28, 106, 50),
                 ("cpass", "Pass", 316, 83, 50, 50), ("cfail", "Fail", 372, 83, 50, 50),
                 ("cback", "Back", 316, 138, 50, 50), ("cnext2", "Next", 372, 138, 50, 50)]


def checks_screen():
    """A checklist, a step at a time: its title, its Need, Send, Do, Check and Pass if, and
    Send, Pass, Fail, Back and Next. The pill says whether the link is up and test mode on."""
    c = []
    c += cell("cname", at(38, 3, 96, 22), "-", 12 * S)
    c += cell("cpos", at(170, 3, 92, 22), "-", 10 * S)
    c += cell("cmark", at(264, 3, 46, 22), "", 10 * S)
    c += cell("pill", at(314, 1, 112, 24), "no link", 12 * S, DOWN)
    c += cell("ctitle", at(4, 28, 306, 18), "-", 11 * S, align=LEFT)
    for k in range(1, LINES + 1):
        c.append(words("cl%d" % k, at(4, 48 + 15 * (k - 1), 306, 15), "", 9 * S, align=LEFT))
    for name, text, x, y, w, h in CHECK_BUTTONS:
        f = at(x, y, w, h)
        c += cell(name, f, text, (16 if len(text) == 1 else 13) * S, BTN)
        c.append(touch(name + "t", f, tells("press", name)))
    return c


# ------------------------------------------------------------------ the root's script
ROOT_LUA = r"""-- Cut It on the phone: the tabs each Launchpad mode has, and what u_net sends, onto the
-- screens (ref/device/phone.md). Generated by tools/touchosc/build.py.
local TABS = %(tabs)s
local DEFAULT_TABS = %(default_tabs)s
local TAB_LABELS = %(tab_labels)s
local SCREENS = %(screens)s
local TABMAX = %(tabmax)d
local ACKS = %(acks)s
local CHECKS = %(checks)s
local LINES = %(lines)d
local PADS = %(pads)s
local INK, PAPER, BTN, LIT = %(ink)s, %(paper)s, %(btn)s, %(lit)s
local DOWN, AMBER, TABOFF = %(down)s, %(amber)s, %(taboff)s
local unpack = table.unpack or unpack

local found, shown = {}, {}
local function get(name)
  local c = found[name]
  if not c then c = root:findByName(name, true); found[name] = c end
  return c
end
-- Set a text or a color only when it differs, since update() runs every frame.
local function text(name, t)
  if shown[name] ~= t then shown[name] = t; get(name).values.text = t end
end
local function paint(name, col)
  if shown[name .. ':c'] ~= col then shown[name .. ':c'] = col; get(name .. 'bg').color = col end
end
local function ink(name, col)
  if shown[name .. ':i'] ~= col then shown[name .. ':i'] = col; get(name).textColor = col end
end
local function arg(a, i)
  return a[i] and a[i].value or 0
end

-- ---------------------------------------------------------------- tabs, mode and test mode
local mode, tabs, tab, testOn = nil, DEFAULT_TABS, 1, nil

local function showTab(k)
  tab = k
  for _, s in ipairs(SCREENS) do get(s).visible = (s == tabs[k]) end
  for i = 1, TABMAX do
    local on = i <= #tabs
    get('tab' .. i .. 'bg').visible, get('tab' .. i).visible, get('tab' .. i .. 't').visible = on, on, on
    if on then
      text('tab' .. i, TAB_LABELS[tabs[i]])
      paint('tab' .. i, i == k and PAPER or TABOFF)
      ink('tab' .. i, i == k and INK or PAPER)
    end
  end
end

local function setMode(m)
  if m == mode then return end
  mode, tabs = m, TABS[m] or DEFAULT_TABS
  text('mode', m)
  showTab(testOn and #tabs or 1)
end

-- Test mode coming on brings up the checklists; going off, the mode's first tab.
local function setTest(on)
  local was = testOn
  if on == was then return end
  testOn = on
  if on then showTab(#tabs) elseif was then showTab(1) end
end

-- ---------------------------------------------------------------- flashes
local flash = {}
local BASE = { rewire = BTN, clear = BTN, tvolca = BTN, t404 = BTN, sync = BTN, snap = BTN,
               csend = BTN, cpass = BTN, cfail = BTN }
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

local function setFader(k, v)
  local f = get(k)
  if f.values.touch or getMillis() - (touchedAt[k] or -100000) < 1000 then return end
  f:notify('state', v)
end

-- c_steps' 41 numbers: playing, the global last step, the selected track, a pending sync or
-- snap (1, 2), the sixteen last steps, then 1 for each track with its own, then the time
-- signature, the drunkenness and the selected track's skip and move.
local function drums(a)
  if #a < 41 then return end
  local playing, track, pending = arg(a, 1) == 1, math.floor(arg(a, 3)), arg(a, 4)
  text('play', playing and 'playing' or 'stopped')
  paint('play', playing and LIT or PAPER)
  text('glob', 'last ' .. math.floor(arg(a, 2)))
  text('pending', pending == 2 and 'snap waits for step 1'
       or (pending == 1 and 'sync waits for step 1' or ''))
  for n = 1, 16 do
    local c = PADS[(n == track and 2 or 0) + (arg(a, 20 + n) == 1 and 1 or 0) + 1]
    paint('pad' .. n, c[1])
    ink('pad' .. n, c[2])
    text('pad' .. n, tostring(math.floor(arg(a, 4 + n))))
  end
  text('num', tostring(math.floor(arg(a, 37))))
  text('den', tostring(math.floor(arg(a, 38))))
  setFader('drunk', math.floor(arg(a, 39)))
  setFader('skip', math.floor(arg(a, 40)))
  setFader('move', math.floor(arg(a, 41)))
end

-- ---------------------------------------------------------------- the checklist page
local ci, si, pg = 1, 1, 1
local marks = {}

local function paintCheck()
  local list = CHECKS[ci]
  local st = list.steps[si]
  text('cname', list.name)
  local pos = si .. ' of ' .. #list.steps
  if #st.pages > 1 then pos = pos .. '  ' .. pg .. '/' .. #st.pages end
  text('cpos', pos)
  local m = marks[ci .. '-' .. si]
  text('cmark', m == 'pass' and 'passed' or (m == 'fail' and 'failed' or ''))
  paint('cmark', m == 'pass' and LIT or (m == 'fail' and DOWN or PAPER))
  text('ctitle', st.title)
  local lines = st.pages[pg] or {}
  for k = 1, LINES do text('cl' .. k, lines[k] or '') end
  text('csend', #st.sends > 0 and 'Send' or '')
end

local function nextStep()
  local st = CHECKS[ci].steps[si]
  if pg < #st.pages then pg = pg + 1
  elseif si < #CHECKS[ci].steps then si, pg = si + 1, 1 end
end

local PRESS = {
  cprev = function() ci, si, pg = (ci > 1 and ci - 1 or #CHECKS), 1, 1 end,
  cnext = function() ci, si, pg = ci %% #CHECKS + 1, 1, 1 end,
  cnext2 = nextStep,
  cback = function()
    if pg > 1 then pg = pg - 1 elseif si > 1 then si, pg = si - 1, 1 end
  end,
  csend = function()
    for _, m in ipairs(CHECKS[ci].steps[si].sends) do
      local args = {}
      for tok in m:gmatch('%%S+') do args[#args + 1] = tonumber(tok) or tok end
      sendOSC('/cutit', 'send', unpack(args))
    end
  end,
}
for _, v in ipairs({ 'pass', 'fail' }) do
  PRESS['c' .. v] = function()
    local list, st = CHECKS[ci], CHECKS[ci].steps[si]
    sendOSC('/cutit', 'result', list.name .. '-' .. st.n .. '-' .. v)
    marks[ci .. '-' .. si], verdict = v, 'c' .. v
    if si < #list.steps then si, pg = si + 1, 1 end
  end
end

-- ---------------------------------------------------------------- what comes in
local lastHb = -100000

function init()
  showTab(1)
  paintCheck()
  for _, k in ipairs({ 'skip', 'move', 'drunk' }) do
    if Orientation then get(k).orientation = Orientation.EAST end
  end
end

local function alert(a)
  local level = tostring(arg(a, 2))
  local t = level == 'none' and 'no-alerts' or tostring(arg(a, 4))
  text('alert', t)
  text('ralert', t)
  text('ralvl', level == 'none' and '-' or level)
  paint('ralvl', level == 'fail' and DOWN or (level == 'warn' and AMBER or PAPER))
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
    text('rname', tostring(arg(a, 1)))
    text('rvalue', (type(v) == 'number' and string.format('%%g', v) or tostring(v))
         .. ((unit ~= '-' and unit ~= '') and (' ' .. unit) or ''))
  elseif path == '/cutit/status' then
    text('status', tostring(arg(a, 1)))
    text('rstatus', tostring(arg(a, 1)))
  elseif path == '/cutit/alert' then
    alert(a)
  elseif path == '/cutit/ack' then
    ack(a)
  end
end

function onReceiveNotify(key, value)
  if key == 'touched' then
    touchedAt[value] = getMillis()
  elseif key == 'tab' then
    showTab(value)
  elseif key == 'press' and PRESS[value] then
    PRESS[value]()
    paintCheck()
  end
end

function update()
  local now = getMillis()
  local up = now - lastHb < 1500
  text('link', up and 'link' or 'NO-LINK')
  text('rlink', up and 'link' or 'NO-LINK')
  paint('link', up and LIT or DOWN)
  paint('rlink', up and LIT or DOWN)
  text('pill', not up and 'no link' or (testOn and 'test mode on' or 'test mode off'))
  paint('pill', not up and DOWN or (testOn and LIT or AMBER))
  for _, k in ipairs({ 'skip', 'move', 'drunk' }) do
    text(k .. 'v', k .. ' ' .. math.floor(get(k).values.x * 100 + 0.5) .. '%%')
  end
  for name, base in pairs(BASE) do
    local f = flash[name]
    paint(name, (f and now < f[1]) and f[2] or base)
  end
end
"""


def lua_color(c):
    return "Color(%g, %g, %g)" % c[:3]


def root_script(checks):
    lua_checks = [{"name": c["name"],
                   "steps": [{"n": s["n"], "title": s["title"], "pages": s["pages"],
                              "sends": s["sends"]} for s in c["steps"]]} for c in checks]
    acks = "{ " + ", ".join("[%s] = { %s, %s }" % (lua(k), lua(v[0]), lua_color(v[1]))
                            for k, v in ACKS.items()) + " }"
    return ROOT_LUA % {
        "tabs": lua(TABS), "default_tabs": lua(DEFAULT_TABS), "tab_labels": lua(TAB_LABELS),
        "screens": lua(SCREENS), "tabmax": TABMAX, "acks": acks, "checks": lua(lua_checks),
        "lines": LINES,
        "pads": "{ " + ", ".join("{ %s, %s }" % (lua_color(f), lua_color(t)) for f, t in PADS)
                + " }",
        "ink": lua_color(INK), "paper": lua_color(PAPER), "btn": lua_color(BTN),
        "lit": lua_color(LIT), "down": lua_color(DOWN), "amber": lua_color(AMBER),
        "taboff": lua_color(TABOFF)}


def build():
    checks, bad = checklists()
    if bad:
        sys.exit("build: the checklists don't fit the page:\n  " + "\n  ".join(bad))
    kids = tab_bar() + [group("remote", remote_screen(), True),
                        group("drums", drum_screen(), False),
                        group("checks", checks_screen(), False)]
    root = node("GROUP", "root", (0, 0, W, H), kids, color=GROUND, script=root_script(checks))
    return '<?xml version="1.0" encoding="UTF-8"?><lexml version="6">' + root + "</lexml>"


def strip_ids(s):
    return re.sub(r'ID="[^"]+"', 'ID=""', s)


def main():
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
    main()
