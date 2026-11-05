#!/usr/bin/env python3
"""Builds the phone's TouchOSC layout, CutIt.tosc: every screen Cut It shows on the phone.

    python3 tools/touchosc/build.py           write it
    python3 tools/touchosc/build.py --check   exit 1 if the committed copy is stale
    python3 tools/touchosc/build.py --force   write it over a copy saved from TouchOSC's editor

The design is Brendan's, iterated from mockups on 2026-11-04: TouchOSC's own controls and its own
tab bar, black, with bright red the lead accent and teal the second, monospaced type for every
value and TouchOSC's default font for every label, and every pairing at WCAG AA, which
test/gate/touchosc-assert.py audits from this file.

The phone controls the Launchpad's current page (Brendan, 2026-11-04): one page of an outer pager
per Launchpad page, 1 the arrangement, 2 the drums, 3 the synths, 4 to 7 nothing yet, 8 the songs,
each holding a pager of its own whose tabs are that page's (one tab each, for now). The root's
script turns the outer pager to the page /cutit/mode names and hides its tab bar, so the phone
shows the page's own tabs; the phone never turns the Launchpad's page. The outer bar is shown in the
file, so TouchOSC's editor, where no script runs, reaches every page by its tab. The checklist page
is the outer pager's last page: test mode, a tap on the Launchpad's Setup, turns to it, and going
off, or choosing a mode, turns back (Brendan, 2026-11-04). It carries the line check alone,
test/checklists/linecheck.md: the development checklists are run with the Mac at hand, which sends
their Send lines.

It speaks u_net's OSC (ref/device/phone.md): it sends /cutit <command> ... to the Organelle's 9001
and shows what comes back to its 8000. Each control sends from a script of its own; the root's
script takes everything that comes in, and the checklist page's buttons, which it answers itself.
A button that the Organelle answers flashes teal by its color, never its value, so an answer can't
send anything again; a knob or a box takes a value from Cut It without sending it back, and a drum
pad, a synth button or the velocity switch is lit by Cut It's state, which a lit one never answers.
The OLED is not copied here (Brendan, 2026-11-04): it has the alerts, the levels and the name of a
control as it moves.

A .tosc file is zlib-compressed XML (~/Sites/!reference/touchosc.md). The checklist page carries
the line check as data, so an edit to it means a rebuild, and push.sh puts the result on the phone.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "CutIt.tosc")
STAMP = os.path.join(HERE, ".built")   # what the last build wrote, untracked
CHECKLISTS = os.path.join(ROOT, "test", "checklists")
DRUM_PAGE = os.path.join(ROOT, "Cut It", "cut-it-drum-page.txt")

W, H, TAB = 896, 414, 40    # an iPhone 11 in landscape, in points, and the tab bar, two steps
R = 44                      # kept clear on the right: the notch

# The grid. TouchOSC's editor grid is 20 points and snaps (editor.grid.step in its app.cfg), so
# every control sits on it: its x, y, width and height are whole steps, and a control moved in
# the editor lands where a build would put it (Brendan, 2026-11-04: "The TouchOSC designs should
# make use of the existing grid"). A page's coordinates are its own, from under its tab bar.
G = 20
X0, X1 = G, 840             # content's left and right edges: a step in, and clear of the notch
Y0, Y1 = G, 320             # its top, a step under the tab bar, and its bottom
PANEL = 300                 # the left panel's width, X0 to 320
COL = (340, 600)            # the right panel's two columns' left edges, a step after the panel
CW = 240                    # a column's width, so the two meet at the gutter and end at X1
STATUS = 300                # the bottom row: a lamp and its words, the same place on every page


def rgb(r, g, b, a=1.0):
    return (r / 255, g / 255, b / 255, a)


RED, TEAL = rgb(255, 31, 63), rgb(52, 200, 190)
WHITE, GREY, BLACK = rgb(240, 240, 240), rgb(140, 140, 140), rgb(0, 0, 0)
TABOFF = rgb(34, 34, 34)
INK, BTN = BLACK, RED       # the XML's defaults

# The Launchpad's pages, the mode bus's mode-1 to mode-8, in order: each one's tab label, and its
# screen (Brendan, 2026-11-04: 1 the arrangement, 2 the drums, 3 the synths, 8 the songs, 4 to 7
# nothing yet). A page with no screen is blank under its tab.
LAUNCHPAD = [("arrangement", "arrangement"), ("drums", "drums"), ("synths", "synths"),
         ("page4", "page 4"), ("page5", "page 5"), ("page6", "page 6"), ("page7", "page 7"),
         ("songs", "songs")]

# The synths c_synth chooses between, c_synth.lua's R.SYNTHS, and each one's button label: fm is
# the Volca, strings the Streichfett. The synths screen and the checklist page each have a button
# per synth, and the chosen one is lit (Brendan, 2026-11-04).
SYNTHS = [("fm", "FM"), ("strings", "STRINGS")]

# What each acknowledgment u_net sends flashes: /cutit/ack <what> [<which>] -> the button, and
# the color. result is the verdict just given, and flashes Pass or Fail, whichever it was.
ACKS = {"drums sync": ("sync", TEAL), "drums snap": ("snap", TEAL),
        "velocity on": ("svel", TEAL), "velocity off": ("svel", TEAL),
        "result": ("verdict", WHITE)}
TEMPO = (5, 600)            # u_tempo's legal range, its [clip 5 600]
# The tap rules, read from u_tempo.lua, so the phone's taps and page 1's pad can't disagree: the ms
# after which tapping starts over, and how many intervals are averaged.
_TEMPO_LUA = open(os.path.join(ROOT, "Cut It", "u_tempo.lua"), encoding="utf-8").read()
TAP_RESET = int(re.search(r"^R\.GAP = (\d+)", _TEMPO_LUA, re.M).group(1))
TAP_INTERVALS = int(re.search(r"^R\.KEEP = (\d+)", _TEMPO_LUA, re.M).group(1))
SWING = (25, 75)            # c_steps.lua's R.SWING_MIN and R.SWING_MAX
STEPS = 32                  # c_steps.lua's R.STEPS, the last step's range from 1
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


def pad_cells():
    """{pad: (row, column)} on the Launchpad, from the drum page's own layout file, rows
    counted from the bottom: the phone's pads sit as the Launchpad's do."""
    cells = {}
    for line in open(DRUM_PAGE, encoding="utf-8"):
        m = re.match(r"^(\d)(\d) pad (\d+)\s*$", line)
        if m:
            cells[int(m.group(3))] = (int(m.group(1)), int(m.group(2)))
    if sorted(cells) != list(range(1, 17)):
        sys.exit("build: %s has pads %s, not 1 to 16" % (os.path.relpath(DRUM_PAGE, ROOT),
                                                         sorted(cells)))
    return cells


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
KINDS["RADIAL"] = dict(KINDS["FADER"], inverted=("b", False))   # the editor writes it
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
    # Every control's name is its own (touchosc-assert holds it), so its ID comes from its name:
    # the same layout builds to the same bytes, and git shows only what really changed.
    out = ['<node ID="%s" type="%s">' % (uuid.uuid5(uuid.NAMESPACE_URL, "cut-it/" + name), kind)]
    if kind == "GROUP" and name == "root":
        out.append("<includes/>")
    out.append("<properties>" + "".join(prop(t, k, v) for k, (t, v) in sorted(props.items()))
               + "</properties>")
    out.append("<values>" + "".join(vals) + "</values>")
    if children:
        out.append("<children>" + "".join(children) + "</children>")
    out.append("</node>")
    return "".join(out)


# The labels that show a value, anything Cut It's state changes: monospaced. The rest, the
# captions and button names, take TouchOSC's default font (Brendan, 2026-11-04).
VALUES = {"tempo", "play", "link", "dlink", "slink", "pending", "num", "den", "last", "drunkv",
          "swingv", "skipv", "movev", "cpos", "tmode"}
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


def synth_script(choice):
    """A synth's button: a tap chooses it, and Cut It's /cutit/synth lights the one chosen with
    notify('lit'), which a lit button never answers, as a drum pad does: so the state can't send
    the choice again, and a tap on the chosen one sends nothing."""
    return ("local lit = 0\n"
            "function onReceiveNotify(key, value)\n"
            "  if key == 'lit' then\n"
            "    lit = value\n"
            "    self.values.x = value\n"
            "  end\n"
            "end\n"
            "function onValueChanged(key)\n"
            "  if key == 'x' and self.values.x == 1 and lit ~= 1 then\n"
            "    sendOSC('/cutit', 'synth', %s)\n"
            "  end\n"
            "end\n" % lua(choice))


def tap_script():
    """The phone's tap tempo (Brendan, 2026-11-04). The phone times the taps itself, as the finger
    lands, and sends the tempo they make: Cut It's own clock would time them as they arrive, and
    WiFi delivers unevenly (ref/device/phone.md). The same rules as page 1's tap pad (u_tempo.lua):
    the first tap only starts the count, a gap over two seconds starts over, the last four
    intervals are averaged, a zero interval doesn't count, and the result is a whole BPM within
    u_tempo's range, sent as the tempo box sends one."""
    return ("local taps = {}\n"
            "function onValueChanged(key)\n"
            "  if key ~= 'x' or self.values.x ~= 1 then return end\n"
            "  local now = getMillis()\n"
            "  local last = taps[#taps]\n"
            "  if last and now - last > %d then taps = {} end\n"
            "  if last and now == last then return end\n"
            "  taps[#taps + 1] = now\n"
            "  while #taps > %d do table.remove(taps, 1) end\n"
            "  if #taps < 2 then return end\n"
            "  local bpm = math.floor(60000 * (#taps - 1) / (taps[#taps] - taps[1]) + 0.5)\n"
            "  sendOSC('/cutit', 'tempo', math.max(%d, math.min(%d, bpm)))\n"
            "end\n" % (TAP_RESET, TAP_INTERVALS + 1, TEMPO[0], TEMPO[1]))


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


def knob(name, x, y_, text, lo=0, hi=100, cmd=None, d=5 * G):
    """A ring knob, lo to hi, its value in its middle and its name over it, flush left. It sends drums <cmd>
    <value>, the knob's name unless told otherwise."""
    span = hi - lo
    script = (KNOWS % ("(value - %d) / %d" % (lo, span))) + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = %d + math.floor(self.values.x * %d + 0.5)\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', 'drums', '%s', v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (lo, span, cmd or name, name))
    f = (x, y_ + G, d, d)
    return [caption(name + "c", x, y_, d, text),
            node("RADIAL", name, f, color=RED, outlineStyle=0, script=script),
            label(name + "v", f, "%d%%" % lo, 14)]


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


def setbox(name, f, lo, hi, args, factor):
    """A box for a value set as it stands, lo to hi, as the time signature's are dragged: the
    tempo, a BPM at a time, and the global last step. It sends /cutit <args> <value> once the
    value it shows moves off the one it knows, its own or the state's; the state hands it a
    whole number, so a value from Cut It is never sent back."""
    steps = hi - lo + 1
    script = (KNOWS % ("(value - %d + 0.5) / %d" % (lo, steps))) + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.max(%d, math.min(%d, %d + math.floor(self.values.x * %d)))\n"
        "  if known == nil then known = v return end\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', %s, v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (lo, hi, lo, steps, ", ".join(lua(a) for a in args), name))
    return node("FADER", name, f, color=RED, outlineStyle=0, bar=False, cursor=False,
                response=1, responseFactor=factor, script=script)


def velocity_script():
    """The velocity switch: lit by Cut It's /cutit/velocity through notify('lit'), never by its
    own value, and a finger on it asks for the other setting: on when it is out, off when lit. So
    the setting coming back, and its repeat on every heartbeat, cannot send it again."""
    return ("local lit = 0\n"
            "function onReceiveNotify(key, value)\n"
            "  if key == 'lit' then\n"
            "    lit = value\n"
            "    self.values.x = value\n"
            "  end\n"
            "end\n"
            "function onValueChanged(key)\n"
            "  if key == 'touch' and self.values.touch then\n"
            "    sendOSC('/cutit', 'velocity', lit == 1 and 'off' or 'on')\n"
            "  end\n"
            "end\n")


def page(name, tab, kids, h=H):
    """A pager's page, under its tab: a group the pager shows alone, named tab. h is the pager's
    height: TouchOSC sizes a page to its pager less the tab bar, and writes that size when the
    editor saves, so a page built any other size shows as a change in diff.py (2026-11-04)."""
    return node("GROUP", name, (0, TAB, W, h - TAB), kids, color=rgb(0, 0, 0, 0.0),
                tabLabel=tab, tabColorOff=TABOFF, tabColorOn=RED, textColorOff=WHITE,
                textColorOn=BLACK)


def tabs(name, pages, frame=(0, 0, W, H - TAB), **over):
    """A pager whose tab bar is the page's own tabs."""
    style = dict(color=BLACK, background=False, tabbarSize=TAB, textSizeOff=22, textSizeOn=22)
    style.update(over)
    return node("PAGER", name, frame, pages, **style)


def caption(name, x, y_, w, text):
    """A control's name: a step tall, grey and small, flush left, just above the control at x."""
    return label(name, (x, y_, w, G), text, 14, GREY, align=1)


def status(led_name, name, x, text, w=CW - G):
    """A lamp and its words on the bottom row, the lamp first, the words flush left after it."""
    return [led(led_name, (x, STATUS, G, G), TEAL),
            label(name, (x + G, STATUS, w, G), text, 16, GREY, align=1)]


# ------------------------------------------------------------------ the arrangement screen (page 1)
def arrangement():
    """The global controls (Brendan, 2026-11-04): the tempo, large, dragged a BPM at a time, which
    lives on the phone alone, and tapped under it; playing or stopped; the time signature, the
    global last step, the swing and the drunkenness; and the link."""
    k = []
    # the left panel: the tempo, the tap under it, playing or stopped on the bottom row
    lo, hi = TEMPO
    k.append(caption("tempoc", X0, Y0, PANEL, "tempo"))
    k.append(setbox("tempobox", (X0, Y0 + G, PANEL, 6 * G), lo, hi, ["tempo"], 2))
    k.append(label("tempo", (X0, Y0 + G, PANEL, 6 * G), "-", 72, RED))
    # the tap's bottom edge is the knobs', across the gutter
    k.append(button("tap", (X0, 9 * G, PANEL, 3 * G), RED, tap_script()))
    k.append(label("tapl", (X0, 9 * G, PANEL, 3 * G), "tap", 22))
    k += status("playled", "play", X0, "stopped", PANEL - G)
    # the right panel: the time signature as [n] / [d], each box dragged a step at a time
    # (Brendan, 2026-11-04), about 21 points a step for the top number's 32 and the last step's,
    # 24 for the bottom number's 5; the swing and the drunkenness under them; the link
    a, b = COL
    k.append(caption("timec", a, Y0, CW, "time"))
    k.append(box("numbox", (a, Y0 + G, 4 * G, 3 * G), MAX_NUM, "num", 9))
    k.append(label("num", (a, Y0 + G, 4 * G, 3 * G), "4", 32))
    k.append(label("slash", (a + 4 * G, Y0 + G, 2 * G, 3 * G), "/", 32, GREY))
    k.append(box("denbox", (a + 6 * G, Y0 + G, 4 * G, 3 * G), len(DENS), "den", 50))
    k.append(label("den", (a + 6 * G, Y0 + G, 4 * G, 3 * G), "4", 32))
    k.append(caption("lastc", b, Y0, CW, "last step"))
    k.append(setbox("lastbox", (b, Y0 + G, 4 * G, 3 * G), 1, STEPS, ["drums", "set-last"], 9))
    k.append(label("last", (b, Y0 + G, 4 * G, 3 * G), "16", 32))
    k += knob("swing", a, 6 * G, "swing", SWING[0], SWING[1], "set-swing")
    k += knob("drunk", b, 6 * G, "drunk")
    k += status("linkled", "link", b, "no link")
    return k


# ------------------------------------------------------------------ the drum screen (page 2)
def drums():
    """What is per track: the sixteen pads, sync first steps and snap to global, a track's skip
    and move; and the link. The tempo, the time signature and the drunkenness are the
    arrangement's (Brendan, 2026-11-04)."""
    k = []
    # the left panel: the sixteen pads where the drum page puts them on the Launchpad, pad 1 at
    # the bottom left (Brendan, 2026-11-04), three steps square and a step apart, so four fill
    # the panel's width and the page's height. Teal with a dot has its own last step; the
    # selected track is lit; each shows its last step.
    size, pitch = 3 * G, 4 * G
    cells = pad_cells()
    top, left = max(r for r, _ in cells.values()), min(c for _, c in cells.values())
    for n in range(1, 17):
        r, c = top - cells[n][0], cells[n][1] - left
        f = (X0 + c * pitch, Y0 + r * pitch, size, size)
        k.append(button("pad%d" % n, f, RED, pad_script(n)))
        k.append(label("pad%dl" % n, f, "16", 20))
    # the right panel: sync and snap, the line saying one waits, the selected track's two
    # knobs, the link
    a, b = COL
    for x, (name, text) in zip(COL, (("sync", "sync first steps"), ("snap", "snap to global"))):
        f = (x, Y0, CW, 3 * G)
        k.append(button(name, f, RED, sends(["drums", name])))
        k.append(label(name + "l", f, text, 16))
    k.append(label("pending", (a, 5 * G, X1 - a, G), "", 14, TEAL, align=1))
    k += knob("skip", a, 7 * G, "skip")
    k += knob("move", b, 7 * G, "move")
    k += status("dlinkled", "dlink", b, "no link")
    return k


# ------------------------------------------------------------------ the synths screen (page 3)
def synths():
    """Two large buttons, a synth each, the chosen one lit; the velocity switch, lit when on,
    under them (Brendan, 2026-11-04); and the link."""
    k = []
    half = (X1 - X0 - G) / 2
    for i, (choice, text) in enumerate(SYNTHS):
        f = (X0 + i * (half + G), Y0, half, 10 * G)
        k.append(button("s" + choice, f, RED, synth_script(choice)))
        k.append(label("s" + choice + "l", f, text, 48))
    f = (X0, 13 * G, CW, 3 * G)
    k.append(button("svel", f, RED, velocity_script()))
    k.append(label("svell", f, "velocity", 22))
    k += status("slinkled", "slink", COL[1], "no link")
    return k


# ------------------------------------------------------------------ the checklist page
def checks():
    """The line check a step at a time: on the left where it is, the step's title and its text;
    on the right test mode's lamp, the synth choice, Pass and Fail, Back and Next."""
    k = []
    rx, half = 31 * G, 5 * G          # the right column, and a button's width in it
    # the top row: where the page is, and test mode's lamp and words
    k.append(label("cpos", (X0, Y0, rx - G - X0, G), "-", 16, GREY, align=1))
    k.append(led("tled", (rx, Y0, G, G), TEAL))
    k.append(label("tmode", (rx + G, Y0, X1 - rx - G, G), "no link", 16, GREY, align=1))
    # the step: its title, then its text, a page of it at a time
    k.append(label("ctitle", (X0, 3 * G, rx - G - X0, 2 * G), "-", 22, WHITE, align=1))
    k.append(node("TEXT", "cbody", (X0, 5 * G, rx - G - X0, 11 * G), text="", background=False,
                  textColor=rgb(210, 210, 210), textSize=16, textAlignH=1, textAlignV=1))
    # the synth choice, as on the synths screen, so the line check plays either synth without
    # leaving test mode (Brendan, 2026-11-04)
    for i, (choice, text) in enumerate(SYNTHS):
        f = (rx + i * (half + G), 3 * G, half, 2 * G)
        k.append(button("c" + choice, f, RED, synth_script(choice)))
        k.append(label("c" + choice + "l", f, text, 16))
    for i, (name, text, col) in enumerate((("cpass", "Pass", TEAL), ("cfail", "Fail", RED))):
        f = (rx + i * (half + G), 6 * G, half, 5 * G)
        k.append(button(name, f, col, tells("press", name)))
        k.append(label(name + "l", f, text, 22))
    for i, (name, text) in enumerate((("cback", "Back"), ("cfwd", "Next"))):
        f = (rx + i * (half + G), 12 * G, half, 4 * G)
        k.append(button(name, f, GREY, tells("press", name)))
        k.append(label(name + "l", f, text, 22))
    return k


# ------------------------------------------------------------------ the root's script
ROOT_LUA = r"""-- Cut It on the phone: the Launchpad's page, and what u_net sends, onto the screens
-- (ref/device/phone.md). Generated by tools/touchosc/build.py.
local PAGES = %(pages)s
local CHECKPAGE = %(npages)s
local CHECK = %(check)s
local SYNTHS = %(synths)s
local ACKS = %(acks)s
local DENS = %(dens)s
local SWING = %(swing)s
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
-- Light a pad or a button from the state, by notify('lit'), which it never answers: when what it
-- was last told differs, or a finger let go of it since. A finger's release leaves a lit one out,
-- and its own lit flag set, so comparing the value alone left a button that was lit once deaf to
-- taps after the state had put it out.
local told = {}
local function light(name, want)
  if told[name] ~= want or get(name).values.x ~= want then
    told[name] = want
    get(name):notify('lit', want)
  end
end

-- ---------------------------------------------------------------- the pages and test mode
-- The outer pager holds a page per Launchpad page, then the checklist page. The mode turns it to
-- the Launchpad's page, and test mode to the checklist page in its place; the phone never turns
-- the Launchpad's.
local mode, testOn = nil, false

local function turn()
  local want = testOn and CHECKPAGE or ((PAGES[mode] or 1) - 1)
  local pages = get('pages')
  if pages.values.page ~= want then pages.values.page = want end
end

local function setMode(m)
  if m == mode then return end
  mode = m
  turn()
end

-- Test mode puts the checklist page in place of the Launchpad's, and going off takes it away.
local function setTest(on)
  if on == testOn then return end
  testOn = on
  turn()
end

-- ---------------------------------------------------------------- flashes
local flash = {}
local BASE = { sync = RED, snap = RED, svel = RED, cpass = TEAL, cfail = RED }
local verdict = 'cpass'

local function ack(a)
  local what, which = tostring(arg(a, 1)), a[2] and tostring(a[2].value)
  local hit = (which and ACKS[what .. ' ' .. which]) or ACKS[what]
  if not hit then return end
  local name = hit[1] == 'verdict' and verdict or hit[1]
  flash[name] = { getMillis() + 300, hit[2] }
end

-- ---------------------------------------------------------------- the knobs and boxes
local touchedAt = {}

-- A value from the state, to a control that knows it, unless a finger was just on it.
local function hand(name, v)
  local c = get(name)
  if c.values.touch or getMillis() - (touchedAt[name] or -100000) < 1000 then return end
  c:notify('state', v)
end

-- ---------------------------------------------------------------- the sequencer's state
-- c_steps' 42 numbers: playing, the global last step, the selected track, a pending sync or
-- snap (1, 2), the sixteen last steps, then 1 for each track with its own, then the time
-- signature, the drunkenness, the selected track's skip and move, and the swing. The drum
-- screen shows what is per track, the arrangement screen the rest.
local function drums(a)
  if #a < 42 then return end
  local playing, track, pending = arg(a, 1) == 1, math.floor(arg(a, 3)), arg(a, 4)
  local last = math.floor(arg(a, 2))
  text('play', playing and 'playing' or 'stopped')
  lit('playled', playing)
  text('last', tostring(last))
  hand('lastbox', last)
  text('pending', pending == 2 and 'snap waits for step 1'
       or (pending == 1 and 'sync waits for step 1' or ''))
  for n = 1, 16 do
    local own, sel = arg(a, 20 + n) == 1, n == track
    color('pad' .. n, own and TEAL or RED)
    light('pad' .. n, sel and 1 or 0)
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
  hand('swing', math.floor(arg(a, 42)))
end

-- ---------------------------------------------------------------- the tempo
-- u_tempo's BPM, the one in force, whoever set it: knob 1, the tap pad or this phone. The box is
-- handed it whole, so a value it was just given can't leave it again.
local function tempo(a)
  local v = a[1] and a[1].value
  if type(v) ~= 'number' then return end
  text('tempo', string.format('%%g', v))
  hand('tempobox', math.floor(v + 0.5))
end

-- ---------------------------------------------------------------- the synths
-- c_synth's choice lights its button on the synths screen and on the checklist page, and its
-- velocity switch the switch, by notify('lit'), which a lit button never answers; a lit one's
-- label goes black on its fill.
local function synth(a)
  local choice = tostring(arg(a, 1))
  for _, s in ipairs(SYNTHS) do
    for _, name in ipairs({ 's' .. s, 'c' .. s }) do
      local want = s == choice and 1 or 0
      light(name, want)
      ink(name .. 'l', want == 1 and BLACK or WHITE)
    end
  end
end

local function velocity(a)
  local v = tostring(arg(a, 1))
  if v ~= 'on' and v ~= 'off' then return end
  local want = v == 'on' and 1 or 0
  light('svel', want)
  ink('svell', want == 1 and BLACK or WHITE)
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

-- The outer pager's tab bar is the editor's way to every page, where no script runs; here it
-- goes, and the page's own tabs are the bar the phone shows.
function init()
  get('pages').tabbar = false
  paintCheck()
end

function onReceiveOSC(message, connections)
  local path, a = message[1], message[2]
  if path == '/cutit/drums' then
    drums(a)
  elseif path == '/cutit/hb' then
    lastHb = getMillis()
    setTest(arg(a, 2) == 1)
  elseif path == '/cutit/mode' then
    setMode(tostring(arg(a, 1)))
  elseif path == '/cutit/tempo' then
    tempo(a)
  elseif path == '/cutit/synth' then
    synth(a)
  elseif path == '/cutit/velocity' then
    velocity(a)
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
  for _, k in ipairs({ 'link', 'dlink', 'slink' }) do
    text(k, up and 'link' or 'no link')
    lit(k .. 'led', up)
  end
  lit('tled', up and testOn)
  text('tmode', not up and 'no link' or (testOn and 'test mode on' or 'test mode off'))
  ink('tmode', (up and testOn) and TEAL or GREY)
  for _, k in ipairs({ 'drunk', 'skip', 'move' }) do
    text(k .. 'v', math.floor(get(k).values.x * 100 + 0.5) .. '%%')
  end
  text('swingv', SWING[1] + math.floor(get('swing').values.x * (SWING[2] - SWING[1]) + 0.5) .. '%%')
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
        "pages": lua({"mode-%d" % (i + 1): i + 1 for i in range(len(LAUNCHPAD))}),
        "npages": len(LAUNCHPAD),
        "synths": lua([c for c, _ in SYNTHS]),
        "acks": acks, "check": lua(check), "dens": lua(DENS), "swing": lua(list(SWING)),
        "red": lua_color(RED), "teal": lua_color(TEAL), "white": lua_color(WHITE),
        "grey": lua_color(GREY), "black": lua_color(BLACK)}


SCREENS = {"arrangement": arrangement, "drums": drums, "synths": synths}


def build(name=LIST):
    """The layout, its checklist page carrying the checklist named, from test/checklists/: the
    line check, but for the gate, which runs the page on a longer checklist too."""
    check, bad = checklist(name)
    if bad:
        sys.exit("build: %s doesn't fit the page:\n  " % (name + ".md") + "\n  ".join(bad))
    # A page per Launchpad page, each holding its own tabs (one each, for now: Brendan,
    # 2026-11-04), then the checklist page under its own one-tab bar.
    outer = []
    for i, (screen, tab) in enumerate(LAUNCHPAD):
        kids = SCREENS[screen]() if screen in SCREENS else []
        inner = tabs("tabs%d" % (i + 1), [page(screen, tab, kids, H - TAB)])
        outer.append(page("p%d" % (i + 1), tab, [inner]))
    outer.append(page("pcheck", "line check", [tabs("checktabs", [page("checks", "line check",
                                                                          checks(), H - TAB)])]))
    # The outer bar: the editor's tabs, small enough for nine; the root's script hides it.
    pages = node("PAGER", "pages", (0, 0, W, H), outer, color=BLACK, background=False,
                 tabbarSize=TAB, textSizeOff=14, textSizeOn=14)
    root = node("GROUP", "root", (0, 0, W, H), [pages], color=BLACK, script=root_script(check))
    return '<?xml version="1.0" encoding="UTF-8"?><lexml version="6">' + root + "</lexml>"


def strip_ids(s):
    return re.sub(r'ID="[^"]+"', 'ID=""', s)


def digest(xml):
    return hashlib.sha256(strip_ids(xml).encode("utf-8")).hexdigest()


def saved_from_editor(new):
    """True when CutIt.tosc is none of what this build would write, what the last build wrote
    and what git holds: TouchOSC's editor saved it, and writing over it would lose the change."""
    try:
        cur = zlib.decompress(open(OUT, "rb").read()).decode("utf-8")
    except OSError:
        return False
    if strip_ids(cur) == strip_ids(new):
        return False
    try:
        if open(STAMP).read().strip() == digest(cur):
            return False
    except OSError:
        pass
    head = subprocess.run(["git", "-C", ROOT, "show", "HEAD:tools/touchosc/CutIt.tosc"],
                          capture_output=True).stdout
    try:
        return not head or strip_ids(zlib.decompress(head).decode("utf-8")) != strip_ids(cur)
    except zlib.error:
        return True


def main_():
    xml = build()
    if "--check" in sys.argv:
        try:
            old = zlib.decompress(open(OUT, "rb").read()).decode("utf-8")
        except OSError:
            sys.exit(1)
        sys.exit(0 if strip_ids(old) == strip_ids(xml) else 1)
    if saved_from_editor(xml) and "--force" not in sys.argv:
        sys.exit("build: CutIt.tosc was saved from TouchOSC's editor since the last build, and "
                 "writing it would lose that.\n  See what changed: python3 tools/touchosc/diff.py"
                 "\n  Put it in build.py and build again, or discard it with --force.")
    with open(OUT, "wb") as fh:
        fh.write(zlib.compress(xml.encode("utf-8"), 9))
    with open(STAMP, "w") as fh:
        fh.write(digest(xml) + "\n")
    print("wrote %s (%d bytes of XML)" % (os.path.relpath(OUT), len(xml)))


if __name__ == "__main__":
    main_()
