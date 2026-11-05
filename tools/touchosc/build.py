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
per Launchpad page, 1 the arrangement, 2 the drums, 3 the synths, 4 to 6 nothing yet, 7 the
sections, 8 the songs, each holding a pager of its own whose tabs are that page's: one tab each,
but the sections page's two, its sections and the name a section is given, and the songs page's
three, its songs, its setlists and the name either is given (Brendan, 2026-11-05). The root's
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
send anything again; a knob, a box or a drum pad takes a value from Cut It without sending it back;
and a synth button or the velocity switch is lit by Cut It's state, which a lit one never answers,
as a drum pad's fill is, behind the pad a finger taps and drags.
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
# every control sits on it, its edges on grid lines, and a control moved in the editor lands where
# a build would put it (Brendan, 2026-11-04: "The TouchOSC designs should make use of the existing
# grid"). ⛔ The grid is anchored at the DOCUMENT'S CENTER, not its corner: a control dragged in
# the editor snapped to x 8, y 187 on its page, and the dots ran 8 and 7 points in from the page's
# corner (2026-11-04). So in a page's own coordinates, under the editor's two tab bars, the lines
# run at OX and OY plus whole steps.
G = 20
OX = (W // 2) % G           # 8: 448, the center, less whole steps
OY = (H // 2 - 2 * TAB) % G  # 7: 207 less the two tab bars, less whole steps
X0, X1 = OX + G, OX + 42 * G   # content's left and right edges, 28 and 848: a step in, and
                               # clear of the notch
Y0, Y1 = OY + G, OY + 16 * G   # its top, a step under the first line below the tab bar, and its
                               # bottom, 27 and 327
PANEL = 300                 # the left panel's width
CW = 240                    # a right column's width, so the two meet at the gutter and end at X1
COL = (X0 + PANEL + G, X0 + PANEL + G + CW + G)   # the right panel's two columns, 348 and 608
STATUS = Y1 - G             # the bottom row: a lamp and its words, the same place on every page


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
         ("page4", "page 4"), ("page5", "page 5"), ("page6", "page 6"), ("sections", "sections"),
         ("songs", "songs")]

# The synths c_synth chooses between, c_synth.lua's R.SYNTHS, and each one's button label: fm is
# the Volca, strings the Streichfett. The synths screen and the checklist page each have a button
# per synth, and the chosen one is lit (Brendan, 2026-11-04).
SYNTHS = [("fm", "FM"), ("strings", "STRINGS")]

# What each acknowledgment u_net sends flashes: /cutit/ack <what> [<which>] -> the button, and
# the color. result is the verdict just given, and flashes Pass or Fail, whichever it was.
ACKS = {"drums sync": ("sync", TEAL), "drums snap": ("snap", TEAL),
        "velocity on": ("svel", TEAL), "velocity off": ("svel", TEAL),
        "sections new": ("secnew", TEAL), "sections up": ("secup", TEAL),
        "sections down": ("secdown", TEAL), "sections delete": ("secdel", TEAL),
        "sections name": ("sndone", WHITE),
        "songs load": ("gload", TEAL), "songs new": ("gnew", TEAL), "songs add": ("gadd", TEAL),
        "songs delete": ("gdel", TEAL), "songs up": ("lup", TEAL), "songs down": ("ldown", TEAL),
        "songs new-set": ("lnewset", TEAL), "songs remove": ("lrem", TEAL),
        "songs name": ("gndone", WHITE), "songs set-name": ("gndone", WHITE),
        "result": ("verdict", WHITE)}
TEMPO = (5, 1000)           # u_tempo's legal range, its [clip 5 1000]
# The tap rules, read from u_tempo.lua, so the phone's taps and page 1's pad can't disagree: the ms
# after which tapping starts over, and how many intervals are averaged.
_TEMPO_LUA = open(os.path.join(ROOT, "Cut It", "u_tempo.lua"), encoding="utf-8").read()
TAP_RESET = int(re.search(r"^R\.GAP = (\d+)", _TEMPO_LUA, re.M).group(1))
TAP_INTERVALS = int(re.search(r"^R\.KEEP = (\d+)", _TEMPO_LUA, re.M).group(1))
# The swing's range, read from c_steps.lua, so the phone's knob and c_steps can't disagree: its
# R.SWING_MIN and R.SWING_MAX, 50% to 75% (Brendan, 2026-11-05).
_STEPS_LUA = open(os.path.join(ROOT, "Cut It", "c_steps.lua"), encoding="utf-8").read()
SWING = tuple(int(v) for v in re.search(r"^R\.SWING_MIN, R\.SWING_MAX = (\d+), (\d+)", _STEPS_LUA,
                                        re.M).groups())
STEPS = 32                  # c_steps.lua's R.STEPS, the last step's range from 1
# How far the global last step reaches, read from c_steps.lua as the swing is: four rows of the
# drum page's eight cells, each row as many groups of the top number as fit, or all eight when it
# is over 8 (R.ROW, R.ROWS and R.reach; Brendan, 2026-11-05). 24 at 3/4, 20 at 5/4, 32 at 4/4.
ROW, ROWS_OF_STEPS = (int(v) for v in re.search(r"^R\.ROW, R\.ROWS = (\d+), (\d+)", _STEPS_LUA,
                                                re.M).groups())
DENS = [1, 2, 4, 8, 16]     # c_steps.lua's R.DENS
MAX_NUM = 32                # c_steps.lua's R.MAX_NUM
# A track's volume in dB and pitch in semitones, read from c_steps.lua as the swing is.
VOL = tuple(int(v) for v in re.search(r"^R\.VOL_MIN, R\.VOL_MAX = (-?\d+), (-?\d+)", _STEPS_LUA,
                                      re.M).groups())
PITCH = tuple(int(v) for v in re.search(r"^R\.PITCH_MIN, R\.PITCH_MAX = (-?\d+), (-?\d+)",
                                        _STEPS_LUA, re.M).groups())
# What the drum screen's pads show, the radio's four in order (Brendan, 2026-11-05): each one's
# word on the radio, the command a pad's drag sends c_steps, its range, and its step. A step is
# about 20 points of drag, as the time signature's are; the randomness goes in fives, so its whole
# range is twenty steps and not a hundred. The radio starts on the first.
SHOW = [("volume", "vol", VOL[0], VOL[1], 1), ("pitch", "pitch", PITCH[0], PITCH[1], 1),
        ("last", "set-track-last", 1, STEPS, 1), ("random", "randomness", 0, 100, 5)]
# A pad's drag: a relative fader whose whole travel is 2500 points at responseFactor 2 (a pad's
# 50 points times 100 over 2), so 125 steps of 20 points, 62 from its middle to either end, more
# than any number the pads show needs from one end to the other.
PAD_FACTOR, PAD_STEPS = 2, 125
# Each track's effects and the reverb's (Brendan, 2026-11-05), read from c_steps.lua: R.FX's
# fields in the order R.phone sends the selected track's, and R.VERB's. A field's control on the
# drum screen is a knob with its name, but FX_CONTROL's, radios: the delay's note and feel, named
# dnote and dfeel, and the distortion's character, char; the command each sends is the field's,
# but the delay's two, delay-note and delay-feel.
_FX = re.search(r"^R\.FX = \{(.*?)\}\n", _STEPS_LUA, re.M | re.S).group(1)
FX_START = {n: int(v) for n, v in re.findall(r'\{ "(\w+)", \d+, \d+, (\d+) \}', _FX)}
FX = list(FX_START)
VERB = re.findall(r'\{ "(\w+)", \d+, \d+, \d+ \}',
                  re.search(r"^R\.VERB = \{(.*)\}$", _STEPS_LUA, re.M).group(1))
NOTE_NAMES = re.findall(r'"([^"]+)"', re.search(r"^R\.NOTE_NAMES = \{(.*)\}$", _STEPS_LUA,
                                                re.M).group(1))
FEEL_NAMES = re.findall(r'"([^"]+)"', re.search(r"^R\.FEEL_NAMES = \{(.*)\}$", _STEPS_LUA,
                                                re.M).group(1))
CHAR_NAMES = re.findall(r'"([^"]+)"', re.search(r"^R\.CHARS = \{(.*)\}$", _STEPS_LUA,
                                                re.M).group(1))
# The reverb's types, R.VERB_TYPES, in the order its radio shows them and c_steps numbers them
# from 0: verb-type <0-2>, the kit's, as its size and damping are (Brendan, 2026-11-05).
VERB_TYPES = re.findall(r'"([^"]+)"', re.search(r"^R\.VERB_TYPES = \{(.*)\}$", _STEPS_LUA,
                                                re.M).group(1))
FX_CONTROL = {"note": "dnote", "feel": "dfeel", "char": "char"}
FX_CMD = {"note": "delay-note", "feel": "delay-feel", "char": "char"}
# The phone's state: c_steps' R.phone, 88 numbers before the effects, then the selected track's
# and the reverb's, 99, then each track's mute and each track's solo, 131, then the reverb's type,
# 132, then each track's random pitch, 148.
PHONE_BASE = 88
# Where the pads show last steps, 1 from the first, the one a drag clips to the reach.
LAST_SHOW = 1 + [c for _w, c, _lo, _hi, _st in SHOW].index("set-track-last")
FX_END = PHONE_BASE + len(FX) + len(VERB)
FLAGS = ("mute", "solo")    # each track's, under its pad, and in the state after the effects
FLAGS_END = FX_END + len(FLAGS) * 16
PHONE = FLAGS_END + 1       # the reverb's type
PHONE_ALL = PHONE + 16      # each track's random pitch, last
# The effect radio's three, in order, each with what shows when it is chosen: its controls by
# name, captions and values too (fx_groups, below).
EFFECTS = ["distortion", "delay", "reverb"]

# The sections page (Brendan, 2026-11-05): the song's sections down the left, five rows a page,
# u_song.lua's R.ROWS; a section's length, 0 (loop) to R.MAX_LENGTH bars; a name, R.MAX_NAME
# characters at most, typed on a keyboard of buttons: A to Z, space, - and ', 0 to 9.
_SONG_LUA = open(os.path.join(ROOT, "Cut It", "u_song.lua"), encoding="utf-8").read()
ROWS = int(re.search(r"^R\.ROWS = (\d+)", _SONG_LUA, re.M).group(1))
MAX_LENGTH = int(re.search(r"^R\.MAX_LENGTH = (\d+)", _SONG_LUA, re.M).group(1))
MAX_NAME = int(re.search(r"^R\.MAX_NAME = (\d+)", _SONG_LUA, re.M).group(1))
# The keyboard's rows, each key its control's name and what it types; None is a gap.
KEYS = [[(c, c) for c in "abcdefghij"], [(c, c) for c in "klmnopqrst"],
        [(c, c) for c in "uvwxyz"] + [("space", " "), None, ("dash", "-"), ("apos", "'")],
        [(c, c) for c in "1234567890"]]
# The name tabs, each the name of something Cut It holds, typed here and sent when done: its
# prefix, the pager it is a tab of, which tab, and by the tab it was opened from, what it names
# and the command done sends; done turns back to that tab. The sections page's names the
# selected section; the songs page's the selected song, or the setlist when opened from the
# setlists tab (Brendan, 2026-11-05).
NAMERS = {"sn": {"pager": "tabs7", "tab": 1, "from": {0: ("section", ["sections", "name"])}},
          "gn": {"pager": "tabs8", "tab": 2, "from": {0: ("song", ["songs", "name"]),
                                                       1: ("setlist", ["songs", "set-name"])}}}
# The songs page (Brendan, 2026-11-05, approved from mockups): its songs tab six rows a page, its
# setlists tab five, u_song.lua's R.SONG_ROWS and R.SET_ROWS; how an entry starts, R.STARTS, each
# its word on the switch; and how long delete waits for its second tap.
SONG_ROWS, SET_ROWS = (int(v) for v in re.search(r"^R\.SONG_ROWS, R\.SET_ROWS = (\d+), (\d+)",
                                                  _SONG_LUA, re.M).groups())
STARTS = re.findall(r'"([\w-]+)"', re.search(r"^R\.STARTS = \{([^}]*)\}", _SONG_LUA, re.M).group(1))
STARTS_WORDS = {"silence": "silence", "next-bar": "next bar", "go": "go"}
SURE_MS = 3000


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
# A radio's orientation: 1 horizontal, its first segment on the left; vertical, 0 is north, its
# first segment at the bottom, as a fader's 0 is, and 2 south, its first at the top (TouchOSC's
# Reference page, The file).
SOUTH = 2


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
          "drivev", "tonev", "distv", "feedbackv", "delayv", "sendv", "sizev", "dampingv",
          "swingv", "cpos", "tmode", "seclink", "secpos", "seclen", "snfieldl", "glink", "llink",
          "gpos", "lpos", "gnfieldl"}
MONO = 1


def label(name, f, text, size, ink=WHITE, align=2):
    mono = (name in VALUES or re.fullmatch(r"pad\d+l|row\dnl|row\dlenl|(sn|gn)k\w+l|grow\dnl"
                                           r"|grow\dwl|lrow\dnl|lrow\dsl", name) is not None)
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
    """A drum pad: a native fader with no bar over the pad's fill, tapped or dragged (Brendan,
    2026-11-05). A tap, a finger down and up with no step between, selects its track, unless the
    state says it is the selected one. A drag up or down changes the number the pads show, the
    radio's choice, for this pad's track: a step every 20 points from where the finger landed,
    sent as it stands. The state hands the pad its value with notify('state'), which puts the
    fader back in its middle and sends nothing, and lights the fill behind it, never the pad
    itself: when a pad was lit by its value, four pads pressed at once lit in turn on the phone,
    each selecting itself again, and the selection bounced between Cut It and the phone for as
    long as they were held (2026-11-04). On last steps a drag reaches no further than the time
    signature lets a last step reach, which the root tells it with notify('reach') (c_steps.lua's
    R.reach), so the number it shows is the one c_steps keeps."""
    sends_ = "\n".join("  %s show == %d then sendOSC('/cutit', 'drums', %s, %d, v)"
                       % ("if" if i == 0 else "elseif", i + 1, lua(cmd), n)
                       for i, (_w, cmd, _lo, _hi, _st) in enumerate(SHOW))
    return ("local SHOW = %s\n"
            "local show, base, known, lit, moved = 1, nil, nil, 0, false\n"
            "-- how far a last step reaches at the time signature, which the root tells it\n"
            "local REACH, reach = %d, SHOW[%d][2]\n"
            "function onReceiveNotify(key, value)\n"
            "  if key == 'lit' then\n"
            "    lit = value\n"
            "  elseif key == 'reach' then\n"
            "    reach = value\n"
            "  elseif key == 'show' then\n"
            "    show, base, known = value, nil, nil\n"
            "  elseif key == 'state' then\n"
            "    base, known = value, value\n"
            "    self.values.x = 0.5\n"
            "  end\n"
            "end\n"
            "-- The steps a finger has moved from the middle, and the value they reach: the\n"
            "-- state's, a step on or back from it on the step's own grid, within the range.\n"
            "local function steps()\n"
            "  return math.floor((self.values.x - 0.5) * %d + 0.5)\n"
            "end\n"
            "local function reached(k)\n"
            "  local s = SHOW[show]\n"
            "  if k == 0 then return base end\n"
            "  local q = k > 0 and math.floor(base / s[3]) or math.ceil(base / s[3])\n"
            "  local hi = show == REACH and math.min(s[2], reach) or s[2]\n"
            "  return math.max(s[1], math.min(hi, (q + k) * s[3]))\n"
            "end\n"
            "function onValueChanged(key)\n"
            "  if key == 'touch' then\n"
            "    if self.values.touch then\n"
            "      moved = false\n"
            "    elseif not moved and lit ~= 1 then\n"
            "      sendOSC('/cutit', 'drums', 'select', %d)\n"
            "    end\n"
            "    return\n"
            "  end\n"
            "  if key ~= 'x' or base == nil then return end\n"
            "  local k = steps()\n"
            "  if k ~= 0 then moved = true end\n"
            "  local v = reached(k)\n"
            "  if v == known then return end\n"
            "  known = v\n"
            "%s\n"
            "  end\n"
            "  root:notify('touched', 'pad%d')\n"
            "end\n" % (lua([[lo, hi, st] for _w, _c, lo, hi, st in SHOW]), LAST_SHOW, LAST_SHOW,
                        PAD_STEPS, n, sends_, n))


# A button that shows Cut It's state, lit with notify('lit'): its look is the state's alone. A
# finger on a button sets its value, which TouchOSC draws, so pressed it lit, let go it went dark,
# and the state lit it again a moment later: on, off, on (Brendan, 2026-11-05: "they flicker on
# and off when I press them"). So every change of its value puts it straight back to what the
# state last said, before TouchOSC draws it, and the finger acts through touch instead.
LIT = ("local lit = 0\n"
       "local function show()\n"
       "  if self.values.x ~= lit then self.values.x = lit end\n"
       "end\n"
       "function onReceiveNotify(key, value)\n"
       "  if key == 'lit' then\n"
       "    lit = value\n"
       "    show()\n"
       "  end\n"
       "end\n")


def lit_script(act):
    """A button lit by the state alone (LIT): act is the Lua run when a finger lands on it."""
    return (LIT + "function onValueChanged(key)\n"
            "  if key == 'x' then return show() end\n"
            "  if key == 'touch' and self.values.touch then\n"
            "    " + act + "\n"
            "  end\n"
            "end\n")


def flag_script(which, n):
    """A track's mute or solo, under its pad (Brendan, 2026-11-05): lit by Cut It's state through
    notify('lit'), never by its own value, and a finger on it asks for the other setting, as the
    velocity switch does: drums <which> <track> 1 when it is out, 0 when lit. So the state coming
    back, and its repeat on every heartbeat, cannot send it again."""
    return lit_script("sendOSC('/cutit', 'drums', %s, %d, lit == 1 and 0 or 1)" % (lua(which), n))


def rolled_script():
    """The selected track's random pitch (Brendan, 2026-11-05): lit by Cut It's state through
    notify('lit'), and a finger on it asks the root, which knows the track, for the other setting,
    as a track's mute does its own."""
    return lit_script("root:notify('rolled', lit == 1 and 0 or 1)")


def show_script():
    """The drum screen's radio: which number the pads show. It sends nothing to Cut It, and
    tells the root, which draws the pads from the state it last had."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' then root:notify('show', self.values.x) end\n"
            "end\n")


def fx_script():
    """The drum screen's effect radio: which effect's controls show, for the selected track
    (Brendan, 2026-11-05). It sends nothing to Cut It, and tells the root, which shows the chosen
    effect's controls and hides the others'."""
    return ("function onValueChanged(key)\n"
            "  if key == 'x' then root:notify('fx', self.values.x) end\n"
            "end\n")


# A control for one of the selected track's effects: the root tells it the track with
# notify('track', n) as the state names it, and hands it the track's value with notify('state',
# v), which it knows, so the state is never sent back; a finger's value is sent for that track.
TRACK_KNOWS = ("local known, track = nil, 1\n"
               "function onReceiveNotify(key, value)\n"
               "  if key == 'track' then\n"
               "    track = value\n"
               "  elseif key == 'state' then\n"
               "    known = value\n"
               "    self.values.x = %s\n"
               "  end\n"
               "end\n")


def fxknob(name, x, y_, text, cmd=None, d=4 * G):
    """A ring knob, 0 to 100, for one of the selected track's effects: its value in its middle
    and its name over it, flush left, as knob()'s. It sends drums <cmd> <track> <value>."""
    script = (TRACK_KNOWS % "value / 100") + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.floor(self.values.x * 100 + 0.5)\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', 'drums', '%s', track, v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (cmd or name, name))
    f = (x, y_ + G, d, d)
    return [caption(name + "c", x, y_, d, text),
            node("RADIAL", name, f, color=RED, outlineStyle=0, script=script),
            label(name + "v", f, "0%", 14)]


def fxradio(name, f, words, cmd, at):
    """A radio for one of the selected track's effects, a step each, 1 to the words' count: the
    delay's note value or its feel. Its words sit over its segments, black on the chosen one. It
    sends drums <cmd> <track> <n>, n from 1, as fxknob does its value; at is the segment the file
    starts on."""
    script = (TRACK_KNOWS % "value - 1") + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.floor(self.values.x + 0.5) + 1\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', 'drums', '%s', track, v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (cmd, name))
    seg = f[2] // len(words)
    out = [node("RADIO", name, f, color=RED, outlineStyle=0, orientation=1, steps=len(words),
                x=at, script=script)]
    for i, w in enumerate(words):
        out.append(label("%s%dl" % (name, i + 1), (f[0] + i * seg, f[1], seg, f[3]), w, 14,
                         BLACK if i == at else WHITE))
    return out


def kitradio(name, f, words, cmd, at):
    """A radio for one of the kit's settings, not a track's: the reverb's type. Its words sit over
    its segments, black on the chosen one, as fxradio's do. It sends drums <cmd> <n>, n from 0,
    the segment, and the state hands it back as notify('state', n); at is the segment the file
    starts on."""
    script = (KNOWS % "value") + (
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.floor(self.values.x + 0.5)\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', 'drums', '%s', v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (cmd, name))
    seg = f[2] // len(words)
    out = [node("RADIO", name, f, color=RED, outlineStyle=0, orientation=1, steps=len(words),
                x=at, script=script)]
    for i, w in enumerate(words):
        out.append(label("%s%dl" % (name, i + 1), (f[0] + i * seg, f[1], seg, f[3]), w, 14,
                         BLACK if i == at else WHITE))
    return out


def synth_script(choice):
    """A synth's button: a tap chooses it, and Cut It's /cutit/synth lights the one chosen with
    notify('lit'), which a lit button never answers, as a drum pad does: so the state can't send
    the choice again, and a tap on the chosen one sends nothing."""
    return lit_script("if lit ~= 1 then sendOSC('/cutit', 'synth', %s) end" % lua(choice))


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
    tempo, a BPM at a time, and the global last step's, lastbox, the same with its hi moving. It
    sends /cutit <args> <value> once the value it shows moves off the one it knows, its own or
    the state's; the state hands it a whole number, so a value from Cut It is never sent back."""
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


def lastbox(name, f, args, factor):
    """The global last step's box: a setbox from 1 to as far as the time signature lets the last
    step reach, which c_steps clips it to (c_steps.lua's R.reach), so a drag to the box's top is
    the furthest step and no drag goes past it. The root tells it the top number with every
    state, as notify('num', n), before handing it the last step."""
    script = (
        "local known\n"
        "local hi = %d\n"
        "local function reach(n)\n"
        "  if n > %d then return %d end\n"
        "  return %d * math.floor(%d / n) * n\n"
        "end\n"
        "function onReceiveNotify(key, value)\n"
        "  if key == 'num' then\n"
        "    hi = reach(math.max(1, value))\n"
        "  elseif key == 'state' then\n"
        "    known = value\n"
        "    self.values.x = (value - 0.5) / hi\n"
        "  end\n"
        "end\n"
        "function onValueChanged(key)\n"
        "  if key ~= 'x' then return end\n"
        "  local v = math.max(1, math.min(hi, 1 + math.floor(self.values.x * hi)))\n"
        "  if known == nil then known = v return end\n"
        "  if v == known then return end\n"
        "  known = v\n"
        "  sendOSC('/cutit', %s, v)\n"
        "  root:notify('touched', '%s')\n"
        "end\n" % (ROWS_OF_STEPS * ROW, ROW, ROWS_OF_STEPS * ROW, ROWS_OF_STEPS, ROW,
                    ", ".join(lua(a) for a in args), name))
    return node("FADER", name, f, color=RED, outlineStyle=0, bar=False, cursor=False,
                response=1, responseFactor=factor, script=script)


def velocity_script():
    """The velocity switch: lit by Cut It's /cutit/velocity through notify('lit'), never by its
    own value, and a finger on it asks for the other setting: on when it is out, off when lit. So
    the setting coming back, and its repeat on every heartbeat, cannot send it again."""
    return lit_script("sendOSC('/cutit', 'velocity', lit == 1 and 'off' or 'on')")


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
    k.append(setbox("tempobox", (X0, Y0 + G, PANEL, 6 * G), lo, hi, ["tempo"], 3))
    k.append(label("tempo", (X0, Y0 + G, PANEL, 6 * G), "-", 72, RED))
    # the tap's bottom edge is the knobs', across the gutter
    k.append(button("tap", (X0, Y0 + 8 * G, PANEL, 3 * G), RED, tap_script()))
    k.append(label("tapl", (X0, Y0 + 8 * G, PANEL, 3 * G), "tap", 22))
    k += status("playled", "play", X0, "stopped", PANEL - G)
    # the right panel: the time signature as [n] / [d], each box dragged a step at a time
    # (Brendan, 2026-11-04), about 21 points a step for the top number's 32 and the last step's
    # 32, more where the time signature lets it reach fewer, 24 for the bottom number's 5; the
    # swing and the drunkenness under them; the link
    a, b = COL
    k.append(caption("timec", a, Y0, CW, "time"))
    k.append(box("numbox", (a, Y0 + G, 4 * G, 3 * G), MAX_NUM, "num", 9))
    k.append(label("num", (a, Y0 + G, 4 * G, 3 * G), "4", 32))
    k.append(label("slash", (a + 4 * G, Y0 + G, 2 * G, 3 * G), "/", 32, GREY))
    k.append(box("denbox", (a + 6 * G, Y0 + G, 4 * G, 3 * G), len(DENS), "den", 50))
    k.append(label("den", (a + 6 * G, Y0 + G, 4 * G, 3 * G), "4", 32))
    k.append(caption("lastc", b, Y0, CW, "last step"))
    k.append(lastbox("lastbox", (b, Y0 + G, 4 * G, 3 * G), ["drums", "set-last"], 9))
    k.append(label("last", (b, Y0 + G, 4 * G, 3 * G), "16", 32))
    k += knob("swing", a, Y0 + 5 * G, "swing", SWING[0], SWING[1], "set-swing")
    k += knob("drunk", b, Y0 + 5 * G, "drunk")
    k += status("linkled", "link", b, "no link")
    return k


# ------------------------------------------------------------------ the drum screen (page 2)
def drums():
    """What is per track: the sixteen pads, each showing its track's volume, pitch, last step or
    randomness as the radio chooses, tapped to select and dragged to change it (Brendan,
    2026-11-05), each with its mute and its solo under it (Brendan, 2026-11-05); the selected
    track's effects, chosen by a second radio, distortion, delay or reverb, its controls to the
    right of it (Brendan, 2026-11-05); sync first steps and snap to global; and the link. The
    tempo, the time signature and the drunkenness are the arrangement's (Brendan, 2026-11-04)."""
    k = []
    # the left panel: the sixteen pads where the drum page puts them on the Launchpad, pad 1 at
    # the bottom left (Brendan, 2026-11-04). Each is its fill, a lamp the state lights for the
    # selected track and colors teal for one with a last step of its own while the pads show last
    # steps; the pad itself over it, a fader a finger taps or drags; and its number. Under each,
    # its track's mute and solo, M and S, lit by the state, M red and S teal (Brendan, 2026-11-05).
    # ⛔ This panel alone is off the 20-point grid, on a 10-point step of it: pads 60 wide and 50
    # tall, M and S 30 by 20 each directly under their pad, and 10 points between, Brendan's pick
    # of three mockups (2026-11-05). Four rows of 50 + 20 and three gaps of 10 are 310, from 10
    # points above Y0 to Y1: the page's frame is 334 points tall, so ending at Y1 keeps the bottom
    # row of M and S whole. touchosc-assert names every one of these controls as the grid's one
    # exception.
    pw, ph, fw, fh, gap = 60, 50, 30, 20, 10
    cells = pad_cells()
    top, left = max(r for r, _ in cells.values()), min(c for _, c in cells.values())
    for n in range(1, 17):
        r, c = top - cells[n][0], cells[n][1] - left
        x, y = X0 + c * (pw + gap), Y0 - gap + r * (ph + fh + gap)
        f = (x, y, pw, ph)
        k.append(node("BUTTON", "pad%df" % n, f, color=RED, interactive=False, outline=False))
        k.append(node("FADER", "pad%d" % n, f, color=RED, outlineStyle=0, background=False,
                      bar=False, cursor=False, response=1, responseFactor=PAD_FACTOR, x=0.5,
                      script=pad_script(n)))
        k.append(label("pad%dl" % n, f, "0", 20))
        for i, (which, letter, col) in enumerate(zip(FLAGS, ("M", "S"), (RED, TEAL))):
            g = (x + i * fw, y + ph, fw, fh)
            k.append(button("%s%d" % (which, n), g, col, flag_script(which, n)))
            k.append(label("%s%dl" % (which, n), g, letter, 14))
    # the right panel: sync and snap across the top; under them two vertical radios, what the
    # pads show (Brendan, 2026-11-05: it became vertical) and which effect's controls show, two
    # steps a segment; and the chosen effect's controls to their right. The line saying a sync
    # or a snap waits sits right under those two, on a row of its own, and the link on the bottom
    # row. Under the show radio, as wide as it and a segment tall, the selected track's random
    # pitch: that radio's last segment is the randomness it adds to (Brendan, 2026-11-05).
    a, b = COL
    for x, (name, text) in zip(COL, (("sync", "sync first steps"), ("snap", "snap to global"))):
        f = (x, Y0, CW, 3 * G)
        k.append(button(name, f, RED, sends(["drums", name])))
        k.append(label(name + "l", f, text, 16))
    k.append(label("pending", (a, Y0 + 3 * G, CW, G), "", 14, TEAL, align=1))
    k.append(caption("showc", a, Y0 + 4 * G, 4 * G, "show"))
    k.append(node("RADIO", "show", (a, Y0 + 5 * G, 4 * G, 2 * G * len(SHOW)), color=RED,
                  outlineStyle=0, orientation=SOUTH, steps=len(SHOW), x=0, script=show_script()))
    for i, (word, _c, _lo, _hi, _st) in enumerate(SHOW):
        k.append(label("show%dl" % (i + 1), (a, Y0 + (5 + 2 * i) * G, 4 * G, 2 * G), word, 14,
                       BLACK if i == 0 else WHITE))
    f = (a, Y0 + (5 + 2 * len(SHOW)) * G, 4 * G, 2 * G)
    k.append(button("rndpitch", f, RED, rolled_script()))
    k.append(label("rndpitchl", f, "rnd pitch", 14))
    fx = a + 5 * G
    k.append(caption("fxc", fx, Y0 + 4 * G, 5 * G, "effect"))
    k.append(node("RADIO", "fx", (fx, Y0 + 5 * G, 5 * G, 2 * G * len(EFFECTS)), color=RED,
                  outlineStyle=0, orientation=SOUTH, steps=len(EFFECTS), x=0, script=fx_script()))
    for i, word in enumerate(EFFECTS):
        k.append(label("fx%dl" % (i + 1), (fx, Y0 + (5 + 2 * i) * G, 5 * G, 2 * G), word, 14,
                       BLACK if i == 0 else WHITE))
    k += fx_controls()
    k += status("dlinkled", "dlink", b, "no link")
    return k


FX_X = COL[0] + 11 * G      # the effects' controls: from 568 to the right edge, 14 steps
FX_Y = Y0 + 4 * G           # their first captions, level with the radios'


def fx_controls():
    """Each effect's controls, all in the same place, to the right of the radios: the root shows
    the chosen effect's and hides the rest. In the file every one shows, so TouchOSC's editor,
    where no script runs, reaches each (ref/device/phone.md, In the editor). The delay's come
    after the distortion's and the reverb's knobs, so in the editor its radios draw over them, and
    the reverb's type radio last, over the delay's knobs.
      distortion: its character, soft, hard, fold or crush (Brendan, 2026-11-05), then drive,
        tone and mix, the track's, a radio over knobs as the delay's are
      reverb: the track's send, and the reverb's size and damping, the kit's, and under them its
        type, plate, gigaverb or freeverb, the kit's too (Brendan, 2026-11-05)
      delay: its time, a note value over a feel, then its feedback and its level"""
    x, y, step = FX_X, FX_Y, 5 * G
    k = []
    k.append(caption("charc", x, y, 14 * G, "character"))
    k += fxradio("char", (x, y + G, 3 * G * len(CHAR_NAMES), 2 * G), CHAR_NAMES, FX_CMD["char"],
                 FX_START["char"] - 1)
    k += fxknob("drive", x, y + 3 * G, "drive")
    k += fxknob("tone", x + step, y + 3 * G, "tone")
    k += fxknob("dist", x + 2 * step, y + 3 * G, "mix")
    k += fxknob("send", x, y, "send")
    k += knob("size", x + step, y, "size", d=4 * G)
    k += knob("damping", x + 2 * step, y, "damping", d=4 * G)
    k.append(caption("dtimec", x, y, 14 * G, "time"))
    k += fxradio("dnote", (x, y + G, 2 * G * len(NOTE_NAMES), 2 * G), NOTE_NAMES, FX_CMD["note"],
                 FX_START["note"] - 1)
    k += fxradio("dfeel", (x, y + 3 * G, 4 * G * len(FEEL_NAMES), 2 * G), FEEL_NAMES,
                 FX_CMD["feel"], FX_START["feel"] - 1)
    k += fxknob("feedback", x, y + 5 * G, "feedback")
    k += fxknob("delay", x + step, y + 5 * G, "level")
    k.append(caption("vtypec", x, y + 5 * G, 12 * G, "type"))
    k += kitradio("vtype", (x, y + 6 * G, 4 * G * len(VERB_TYPES), 2 * G), VERB_TYPES,
                  "verb-type", 0)
    return k


def fx_groups():
    """The controls each effect shows, by name, in the effect radio's order: distortion, delay,
    reverb. Every name a node of fx_controls."""
    groups = {"distortion": [], "delay": [], "reverb": []}
    for n in fx_controls():
        name = re.search(r'<key><!\[CDATA\[name\]\]></key><value><!\[CDATA\[([\w-]+)\]\]>',
                         n).group(1)
        base = re.sub(r"(c|v|\dl)$", "", name)
        if base in ("char", "drive", "tone", "dist"):
            groups["distortion"].append(name)
        elif base in ("send", "size", "damping", "vtype"):
            groups["reverb"].append(name)
        else:
            groups["delay"].append(name)
    return [groups[e] for e in EFFECTS]


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
    f = (X0, Y0 + 12 * G, CW, 3 * G)
    k.append(button("svel", f, RED, velocity_script()))
    k.append(label("svell", f, "velocity", 22))
    k += status("slinkled", "slink", COL[1], "no link")
    return k


# ------------------------------------------------------------------ the sections page (7)
R_COL = X0 + 26 * G                 # the right column, 548: past the list and a gutter
R_HALF = (R_COL, R_COL + 8 * G)     # its two halves, 548 and 708, seven steps wide each


def row_script(k):
    """A row of the sections list: a tap selects the section it shows, which only the root knows,
    so it tells the root; Cut It's /cutit/sections lights the one selected with notify('lit'),
    which a lit row never answers, as a synth button does."""
    return lit_script("if lit ~= 1 then root:notify('row', %d) end" % k)


def sections():
    """The current song's sections (Brendan, 2026-11-05, approved from a mockup): down the left,
    numbered, each with its name and length, five rows and a pager; a tap selects one for editing,
    and playing one stays the Launchpad's top row. On the right, the selected section: new, a copy
    of it, move up and down, its length, dragged, loop or bars, and delete; and the link."""
    k = []
    w = 25 * G
    k.append(caption("secsong", X0, Y0, w, "sections"))
    for r in range(1, ROWS + 1):
        y_ = Y0 + G + (r - 1) * 2 * G
        f = (X0, y_, w, 2 * G)
        k.append(button("row%d" % r, f, RED, row_script(r)))
        k.append(label("row%dnl" % r, (X0, y_, 3 * G, 2 * G), "", 18))
        k.append(label("row%dl" % r, (X0 + 3 * G, y_, 15 * G, 2 * G), "", 18, align=LEFT))
        k.append(label("row%dlenl" % r, (X0 + 15 * G, y_, 9 * G, 2 * G), "", 16, GREY, align=3))
    y_ = Y0 + 12 * G
    k.append(button("secprev", (X0, y_, 2 * G, 2 * G), RED, sends(["sections", "page", -1])))
    k.append(label("secprevl", (X0, y_, 2 * G, 2 * G), "◀", 18))
    k.append(label("secpos", (X0 + 3 * G, y_, 17 * G, 2 * G), "-", 16, GREY, align=LEFT))
    k.append(button("secnext", (X0 + 23 * G, y_, 2 * G, 2 * G), RED, sends(["sections", "page", 1])))
    k.append(label("secnextl", (X0 + 23 * G, y_, 2 * G, 2 * G), "▶", 18))
    a, b = R_HALF
    k.append(caption("secsel", a, Y0, X1 - a, "section"))
    f = (a, Y0 + G, X1 - a, 3 * G)
    k.append(button("secnew", f, RED, sends(["sections", "new"])))
    k.append(label("secnewl", f, "new", 20))
    for x, name, text, cmd in ((a, "secup", "move up", "up"), (b, "secdown", "move down", "down")):
        f = (x, Y0 + 5 * G, 7 * G, 3 * G)
        k.append(button(name, f, RED, sends(["sections", cmd])))
        k.append(label(name + "l", f, text, 18))
    k.append(caption("seclenc", a, Y0 + 9 * G, 7 * G, "length"))
    f = (a, Y0 + 10 * G, 7 * G, 3 * G)
    # dragged a step every 18 points or so, as the last step's box is: 65 steps, loop and 1 to 64
    k.append(setbox("seclenbox", f, 0, MAX_LENGTH, ["sections", "length"], 5))
    k.append(label("seclen", f, "loop", 28))
    f = (b, Y0 + 10 * G, 7 * G, 3 * G)
    k.append(button("secdel", f, GREY, sends(["sections", "delete"])))
    k.append(label("secdell", f, "delete", 18))
    k += status("seclinkled", "seclink", a, "no link", X1 - a - G)
    return k


def name_tab(prefix, what):
    """A name being typed (Brendan, 2026-11-05, approved from a mockup): the name, as typed, over
    a keyboard of buttons, A to Z, space, - and ', 0 to 9, with backspace and done. Each key tells
    the root, which holds the name; done sends it, as NAMERS has it for prefix and the tab it was
    opened from, and turns back to that tab. The sections page's names the selected section; the
    songs page's the selected song, or the setlist chosen when opened from the setlists tab, and
    its caption says which."""
    k = []
    w = 25 * G
    k.append(caption(prefix + "what", X0, Y0, w, "name the " + what))
    f = (X0, Y0 + G, w, 2 * G)
    k.append(node("BUTTON", prefix + "field", f, color=GREY, interactive=False, outlineStyle=0))
    k.append(label(prefix + "fieldl", f, "_", 24, align=LEFT))
    a, b = R_HALF
    for x, name, text, col, size in ((a, "back", "⌫", RED, 22), (b, "done", "done", TEAL, 20)):
        f = (x, Y0 + G, 7 * G, 2 * G)
        k.append(button(prefix + name, f, col, tells("type", "%s:%s" % (prefix, name))))
        k.append(label(prefix + name + "l", f, text, size))
    for r, keys in enumerate(KEYS):
        for c, key in enumerate(keys):
            if key is None:
                continue
            name, _ch = key
            wide = 7 if name == "space" else 3
            f = (X0 + c * 4 * G, Y0 + 4 * G + r * 3 * G, wide * G, 2 * G)
            k.append(button(prefix + "k" + name, f, RED, tells("type", "%s:k%s" % (prefix, name))))
            k.append(label(prefix + "k" + name + "l", f,
                           name if name == "space" else _ch.upper(), 18))
    return k


# ------------------------------------------------------------------ the songs page (8)
def list_row_script(what, k):
    """A row of a list on the songs page: a tap selects what it shows, which only the root knows,
    so it tells the root; Cut It's /cutit/songs lights the one selected with notify('lit'), which
    a lit row never answers, as a sections row does."""
    return lit_script("if lit ~= 1 then root:notify(%s, %d) end" % (lua(what), k))


def list_rows(prefix, n, right, size=16):
    """n rows down the left, a page of a list: each a button and its number, name and, flush right
    and grey, what the right says (a song's words, an entry's start)."""
    k = []
    for r in range(1, n + 1):
        y_ = Y0 + G + (r - 1) * 2 * G
        f = (X0, y_, 25 * G, 2 * G)
        k.append(button("%s%d" % (prefix, r), f, RED, list_row_script(prefix, r)))
        k.append(label("%s%dnl" % (prefix, r), (X0, y_, 3 * G, 2 * G), "", 18))
        k.append(label("%s%dl" % (prefix, r), (X0 + 3 * G, y_, 15 * G, 2 * G), "", 18, align=LEFT))
        k.append(label("%s%d%sl" % (prefix, r, right), (X0 + 15 * G, y_, 9 * G, 2 * G), "", size,
                       GREY, align=3))
    return k


def pager_row(prefix, y_, cmd):
    """A list's arrows and where it is, between them."""
    k = [button(prefix + "prev", (X0, y_, 2 * G, 2 * G), RED, sends(cmd + [-1])),
         label(prefix + "prevl", (X0, y_, 2 * G, 2 * G), "◀", 18),
         label(prefix + "pos", (X0 + 3 * G, y_, 17 * G, 2 * G), "-", 16, GREY, align=LEFT),
         button(prefix + "next", (X0 + 23 * G, y_, 2 * G, 2 * G), RED, sends(cmd + [1])),
         label(prefix + "nextl", (X0 + 23 * G, y_, 2 * G, 2 * G), "▶", 18)]
    return k


def songs_tab():
    """Every song (Brendan, 2026-11-05, approved from a mockup): down the left, six rows and a
    pager, each its number, name and what it is doing, loaded, waiting for the next bar or for go,
    unsaved; a tap selects one. On the right, the selected song's name over load, by its
    transition, new song, name, which opens the name tab, add to set, the setlist chosen, and
    delete, which reads sure? until a second tap; and the link."""
    k = [caption("gcap", X0, Y0, 25 * G, "songs")]
    k += list_rows("grow", SONG_ROWS, "w")
    k += pager_row("g", Y0 + 13 * G, ["songs", "page"])
    a, b = R_HALF
    k.append(caption("gsel", a, Y0, X1 - a, "song"))
    f = (a, Y0 + G, X1 - a, 3 * G)
    k.append(button("gload", f, RED, sends(["songs", "load"])))
    k.append(label("gloadl", f, "load", 24))
    for x, y_, name, text, col, script in (
            (a, Y0 + 5 * G, "gnew", "new song", RED, sends(["songs", "new"])),
            (b, Y0 + 5 * G, "gname", "name", RED, tells("open", "gn")),
            (a, Y0 + 9 * G, "gadd", "add to set", RED, sends(["songs", "add"])),
            (b, Y0 + 9 * G, "gdel", "delete", GREY, tells("confirm", "gdel"))):
        f = (x, y_, 7 * G, 3 * G)
        k.append(button(name, f, col, script))
        k.append(label(name + "l", f, text, 18))
    k += status("glinkled", "glink", a, "no link", X1 - a - G)
    return k


def starts_script():
    """The starts switch: TouchOSC's own radio, a segment for each way an entry starts. The state
    hands it the selected entry's with notify('state'), which it never sends back; a finger's
    choice sends songs starts <word>."""
    return ((KNOWS % "value") +
            "local STARTS = %s\n"
            "function onValueChanged(key)\n"
            "  if key ~= 'x' then return end\n"
            "  local v = math.floor(self.values.x + 0.5)\n"
            "  if known == nil or v == known then return end\n"
            "  known = v\n"
            "  sendOSC('/cutit', 'songs', 'starts', STARTS[v + 1])\n"
            "  root:notify('touched', 'lstarts')\n"
            "end\n" % lua(STARTS))


def setlists_tab():
    """The setlist chosen (Brendan, 2026-11-05, approved from a mockup): its songs in order down
    the left, five rows, each its Organelle key, its song and how it starts after the one before;
    the arrows page between setlists, through a long one's own pages first. On the right, the
    selected entry over move up and move down, the starts switch, silence, next bar or go, new
    set and remove; and the link."""
    k = [caption("lcap", X0, Y0, 25 * G, "setlist")]
    k += list_rows("lrow", SET_ROWS, "s")
    k += pager_row("l", Y0 + 13 * G, ["songs", "set"])
    a, b = R_HALF
    k.append(caption("lsel", a, Y0, X1 - a, "entry"))
    for x, name, text, cmd in ((a, "lup", "move up", "up"), (b, "ldown", "move down", "down")):
        f = (x, Y0 + G, 7 * G, 3 * G)
        k.append(button(name, f, RED, sends(["songs", cmd])))
        k.append(label(name + "l", f, text, 18))
    k.append(caption("lstartsc", a, Y0 + 5 * G, X1 - a, "starts"))
    seg = (X1 - a) // len(STARTS)
    k.append(node("RADIO", "lstarts", (a, Y0 + 6 * G, X1 - a, 3 * G), color=RED, outlineStyle=0,
                  orientation=1, steps=len(STARTS), x=0, script=starts_script()))
    for i, word in enumerate(STARTS):
        k.append(label("lstarts%dl" % (i + 1), (a + i * seg, Y0 + 6 * G, seg, 3 * G),
                       STARTS_WORDS[word], 16, BLACK if i == 0 else WHITE))
    for x, name, text, col, cmd in ((a, "lnewset", "new set", RED, "new-set"),
                                    (b, "lrem", "remove", GREY, "remove")):
        f = (x, Y0 + 10 * G, 7 * G, 3 * G)
        k.append(button(name, f, col, sends(["songs", cmd])))
        k.append(label(name + "l", f, text, 18))
    k += status("llinkled", "llink", a, "no link", X1 - a - G)
    return k


# ------------------------------------------------------------------ the checklist page
def checks():
    """The line check a step at a time: on the left where it is, the step's title and its text;
    on the right test mode's lamp, the synth choice, Pass and Fail, Back and Next."""
    k = []
    rx, half = X0 + 30 * G, 5 * G     # the right column, and a button's width in it
    # the top row: where the page is, and test mode's lamp and words
    k.append(label("cpos", (X0, Y0, rx - G - X0, G), "-", 16, GREY, align=1))
    k.append(led("tled", (rx, Y0, G, G), TEAL))
    k.append(label("tmode", (rx + G, Y0, X1 - rx - G, G), "no link", 16, GREY, align=1))
    # the step: its title, then its text, a page of it at a time
    k.append(label("ctitle", (X0, Y0 + 2 * G, rx - G - X0, 2 * G), "-", 22, WHITE, align=1))
    k.append(node("TEXT", "cbody", (X0, Y0 + 4 * G, rx - G - X0, 11 * G), text="",
                  background=False,
                  textColor=rgb(210, 210, 210), textSize=16, textAlignH=1, textAlignV=1))
    # the synth choice, as on the synths screen, so the line check plays either synth without
    # leaving test mode (Brendan, 2026-11-04)
    for i, (choice, text) in enumerate(SYNTHS):
        f = (rx + i * (half + G), Y0 + 2 * G, half, 2 * G)
        k.append(button("c" + choice, f, RED, synth_script(choice)))
        k.append(label("c" + choice + "l", f, text, 16))
    for i, (name, text, col) in enumerate((("cpass", "Pass", TEAL), ("cfail", "Fail", RED))):
        f = (rx + i * (half + G), Y0 + 5 * G, half, 5 * G)
        k.append(button(name, f, col, tells("press", name)))
        k.append(label(name + "l", f, text, 22))
    for i, (name, text) in enumerate((("cback", "Back"), ("cfwd", "Next"))):
        f = (rx + i * (half + G), Y0 + 11 * G, half, 4 * G)
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
local SHOWN = %(shown)s
local LASTSHOW, STEPROW, STEPROWS = %(lastshow)s, %(steprow)s, %(steprows)s
-- The drum screen's effects: each effect's controls, by the effect radio's order; the selected
-- track's controls in the order the state sends their values, after its first PHONE_BASE; the
-- knobs whose value shows in their middle; the radios' segment counts.
local FXGROUPS = %(fxgroups)s
local FXCONTROLS = %(fxcontrols)s
local VERBCONTROLS = %(verbcontrols)s
local FXKNOBS = %(fxknobs)s
local FXRADIOS = %(fxradios)s
local PHONE_BASE, FX_END, FLAGS_END, PHONE = %(phonebase)s, %(fxend)s, %(flagsend)s, %(phone)s
local PHONE_ALL = %(phoneall)s
local FLAGS = %(flags)s
local ROWS, MAX_NAME = %(rows)s, %(maxname)s
local NAMERS = %(namers)s
local CHARS = %(chars)s
-- What each name tab's done sends, by the tab it was opened from: the command NAMERS names, and
-- the name.
%(send)s
local SONG_ROWS, SET_ROWS = %(songrows)s, %(setrows)s
local STARTS, STARTWORDS = %(starts)s, %(startwords)s
local SURE = %(sure)s
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
-- Light a button from the state, by notify('lit'), which it never answers: when what it was last
-- told differs, or a finger let go of it since. A finger's release leaves a lit one out, and its
-- own lit flag set, so comparing the value alone left a button that was lit once deaf to taps
-- after the state had put it out.
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
local BASE = { sync = RED, snap = RED, svel = RED, cpass = TEAL, cfail = RED, secnew = RED,
               secup = RED, secdown = RED, secdel = GREY, sndone = TEAL, gload = RED, gnew = RED,
               gadd = RED, gdel = GREY, lup = RED, ldown = RED, lnewset = RED, lrem = GREY,
               gndone = TEAL }
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

-- ---------------------------------------------------------------- the drum screen's pads
-- What the pads show, the radio's choice, 1 to 4: volume, pitch, last step, randomness. Each pad
-- shows its track's, and is handed it to drag from; its fill is lit for the selected track, and
-- teal for a track with its own last step while the pads show last steps. state is c_steps'
-- last, so a turn of the radio redraws the pads at once.
local show, state = 1, nil
local function signed(v) return v > 0 and ('+' .. v) or tostring(v) end
-- How far a last step reaches at a top number: four rows of as many groups of it as fit in a
-- row's eight cells, or all eight when it is over 8 (c_steps.lua's R.reach).
local function reach(n)
  if n > STEPROW then return STEPROWS * STEPROW end
  return STEPROWS * math.floor(STEPROW / n) * n
end
local function pads()
  local a = state
  if not a then return end
  local track = math.floor(arg(a, 3))
  local far = reach(math.max(1, math.floor(arg(a, 37))))
  for n = 1, 16 do
    local own, sel, pad = arg(a, 20 + n) == 1, n == track, 'pad' .. n
    if told[pad .. ':r'] ~= far then told[pad .. ':r'] = far; get(pad):notify('reach', far) end
    local v, words, teal
    if show == 1 then
      v = math.floor(arg(a, 40 + n)); words = signed(v)
    elseif show == 2 then
      v = math.floor(arg(a, 56 + n)); words = signed(v)
    elseif show == 3 then
      v = math.floor(arg(a, 4 + n)); words = (own and '• ' or '') .. v; teal = own
    else
      v = math.floor(arg(a, 72 + n)); words = v .. '%%'
    end
    color(pad .. 'f', teal and TEAL or RED)
    color(pad, teal and TEAL or RED)
    lit(pad .. 'f', sel)
    local want = sel and 1 or 0
    if told[pad] ~= want then told[pad] = want; get(pad):notify('lit', want) end
    text(pad .. 'l', words)
    ink(pad .. 'l', sel and BLACK or WHITE)
    hand(pad, v)
  end
end

local function setShow(x)
  show = math.max(1, math.min(#SHOWN, math.floor(x + 0.5) + 1))
  for i = 1, #SHOWN do ink('show' .. i .. 'l', i == show and BLACK or WHITE) end
  for n = 1, 16 do get('pad' .. n):notify('show', show) end
  pads()
end

-- ---------------------------------------------------------------- the sequencer's state
-- ---------------------------------------------------------------- the drum screen's effects
-- The effect radio's choice, 1 to 3: distortion, delay, reverb. The chosen effect's controls
-- show and the others' hide; in the file all of them show, for the editor.
local fx = 1
local function showing(name, on)
  if shown[name .. ':v'] ~= on then shown[name .. ':v'] = on; get(name).visible = on end
end
local function setFx(x)
  fx = math.max(1, math.min(#FXGROUPS, math.floor(x + 0.5) + 1))
  for i = 1, #FXGROUPS do
    ink('fx' .. i .. 'l', i == fx and BLACK or WHITE)
    for _, name in ipairs(FXGROUPS[i]) do showing(name, i == fx) end
  end
end

-- The selected track's effects, after the state's first PHONE_BASE numbers, and the reverb's: each
-- control told the track when it changes, then handed its value, as a knob is; and the reverb's
-- type, the state's last, handed to its radio.
local fxtrack = nil
local function effects(a)
  if #a < FX_END then return end
  local track = math.floor(arg(a, 3))
  if track ~= fxtrack then
    fxtrack = track
    for _, name in ipairs(FXCONTROLS) do get(name):notify('track', track) end
  end
  for i, name in ipairs(FXCONTROLS) do hand(name, math.floor(arg(a, PHONE_BASE + i))) end
  for i, name in ipairs(VERBCONTROLS) do
    hand(name, math.floor(arg(a, PHONE_BASE + #FXCONTROLS + i)))
  end
  if #a >= PHONE then hand('vtype', math.floor(arg(a, PHONE))) end
end

-- Each track's mute and solo, after the effects: M and S under its pad, lit by notify('lit'),
-- which a lit one never answers, its letter black on the lit fill.
local function flags(a)
  if #a < FLAGS_END then return end
  for k, which in ipairs(FLAGS) do
    for n = 1, 16 do
      local name, want = which .. n, arg(a, FX_END + (k - 1) * 16 + n) == 1 and 1 or 0
      light(name, want)
      ink(name .. 'l', want == 1 and BLACK or WHITE)
    end
  end
end

-- The selected track's random pitch, the state's last sixteen: its button under the show radio, lit
-- by notify('lit'), which a lit one never answers, its word black on the lit fill. A tap asks the
-- root for the other setting, since it is here that the track is known. A state from before them
-- leaves it as it was.
local function rolled(a)
  if #a < PHONE_ALL then return end
  local want = arg(a, PHONE + math.floor(arg(a, 3))) == 1 and 1 or 0
  light('rndpitch', want)
  ink('rndpitchl', want == 1 and BLACK or WHITE)
end

local function askRolled(v)
  if state then sendOSC('/cutit', 'drums', 'rnd-pitch', math.floor(arg(state, 3)), v) end
end

-- ---------------------------------------------------------------- the sequencer's state
-- c_steps' 148 numbers: playing, the global last step, the selected track, a pending sync or
-- snap (1, 2), the sixteen last steps, then 1 for each track with its own, then the time
-- signature, the drunkenness and the swing, then the sixteen volumes, pitches and
-- randomnesses, then the selected track's effects and the reverb's, then each track's mute and
-- each track's solo, then the reverb's type, then each track's random pitch. The drum screen
-- shows what is per track, the arrangement screen the rest; 88, without the effects, draws all but
-- those, 99, without mute and solo, all but those, 131, without the type, all but that, and 132,
-- without the random pitches, all but those.
local function drums(a)
  if #a < 88 then return end
  local playing, pending = arg(a, 1) == 1, arg(a, 4)
  local last = math.floor(arg(a, 2))
  text('play', playing and 'playing' or 'stopped')
  lit('playled', playing)
  text('last', tostring(last))
  get('lastbox'):notify('num', math.floor(arg(a, 37)))
  hand('lastbox', last)
  text('pending', pending == 2 and 'snap waits for step 1'
       or (pending == 1 and 'sync waits for step 1' or ''))
  state = a
  pads()
  local num, den = math.floor(arg(a, 37)), math.floor(arg(a, 38))
  text('num', tostring(num))
  text('den', tostring(den))
  hand('numbox', num)
  for i, d in ipairs(DENS) do if d == den then hand('denbox', i) end end
  hand('drunk', math.floor(arg(a, 39)))
  hand('swing', math.floor(arg(a, 40)))
  effects(a)
  flags(a)
  rolled(a)
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

-- ---------------------------------------------------------------- the sections page
-- u_song's 22 atoms: the song's name, how many sections, the one selected, the page and how
-- many, the selected one's name and length; then five rows, each a section's number, name and
-- length, 0 for a row with none, which is not shown. The selected row is lit by notify('lit'),
-- which it never answers; a row tapped tells the root, which sends the section it shows.
local secs = nil
local function bars(n)
  if n == 0 then return 'loop' end
  return n .. (n == 1 and ' bar' or ' bars')
end
local function seen(name, on)
  if shown[name .. ':v'] ~= on then shown[name .. ':v'] = on; get(name).visible = on end
end

local function sections(a)
  if #a < 7 + 3 * ROWS then return end
  secs = a
  local sel = math.floor(arg(a, 3))
  text('secsong', 'sections of ' .. tostring(arg(a, 1)))
  text('secsel', 'section ' .. sel)
  text('secnewl', 'new, a copy of ' .. sel)
  text('secpos', math.floor(arg(a, 4)) .. ' / ' .. math.floor(arg(a, 5)))
  local len = math.floor(arg(a, 7))
  text('seclen', bars(len))
  hand('seclenbox', len)
  for r = 1, ROWS do
    local n, row = math.floor(arg(a, 5 + 3 * r)), 'row' .. r
    local on = n == sel
    for _, part in ipairs({ '', 'nl', 'l', 'lenl' }) do seen(row .. part, n > 0) end
    text(row .. 'nl', n > 0 and tostring(n) or '')
    text(row .. 'l', n > 0 and tostring(arg(a, 6 + 3 * r)) or '')
    text(row .. 'lenl', n > 0 and bars(math.floor(arg(a, 7 + 3 * r))) or '')
    ink(row .. 'nl', on and BLACK or WHITE)
    ink(row .. 'l', on and BLACK or WHITE)
    ink(row .. 'lenl', on and BLACK or GREY)
    light(row, on and 1 or 0)
  end
end

local function rowTapped(r)
  if not secs then return end
  local n = math.floor(arg(secs, 5 + 3 * r))
  if n > 0 and n ~= math.floor(arg(secs, 3)) then sendOSC('/cutit', 'sections', 'select', n) end
end

-- ---------------------------------------------------------------- the songs page
-- u_song's 47 atoms: the songs tab, how many songs, the one selected, the page and how many, the
-- selected one's name, then six rows of number, name and words; then the setlists tab, the
-- setlist chosen and how many, its name, its page and how many, how many entries, the one
-- selected, its song and how it starts, then five rows of key, song and starts. 0 is a row with
-- none, which is not shown. Selected rows are lit by notify('lit'), which they never answer.
local songsst = nil
local function songs(a)
  if #a < 5 + 3 * SONG_ROWS + 9 + 3 * SET_ROWS then return end
  songsst = a
  local sel = math.floor(arg(a, 2))
  text('gsel', tostring(arg(a, 5)))
  text('gpos', math.floor(arg(a, 3)) .. ' / ' .. math.floor(arg(a, 4)))
  for r = 1, SONG_ROWS do
    local n, row = math.floor(arg(a, 3 + 3 * r)), 'grow' .. r
    local on = n == sel and n > 0
    for _, part in ipairs({ '', 'nl', 'l', 'wl' }) do seen(row .. part, n > 0) end
    local words = tostring(arg(a, 5 + 3 * r))
    text(row .. 'nl', n > 0 and tostring(n) or '')
    text(row .. 'l', n > 0 and tostring(arg(a, 4 + 3 * r)) or '')
    text(row .. 'wl', (n > 0 and words ~= '-') and words or '')
    ink(row .. 'nl', on and BLACK or WHITE)
    ink(row .. 'l', on and BLACK or WHITE)
    ink(row .. 'wl', on and BLACK or GREY)
    light(row, on and 1 or 0)
  end
  local b = 5 + 3 * SONG_ROWS
  local pages = math.floor(arg(a, b + 5))
  local pos = 'set ' .. math.floor(arg(a, b + 1)) .. ' / ' .. math.floor(arg(a, b + 2))
  if pages > 1 then pos = pos .. '   page ' .. math.floor(arg(a, b + 4)) .. ' / ' .. pages end
  text('lcap', tostring(arg(a, b + 3)))
  text('lpos', pos)
  local entry = math.floor(arg(a, b + 7))
  text('lsel', entry > 0 and (entry .. '  ' .. tostring(arg(a, b + 8))) or 'no entry')
  local starts = tostring(arg(a, b + 9))
  for i, w in ipairs(STARTS) do
    if w == starts then hand('lstarts', i - 1) end
    ink('lstarts' .. i .. 'l', (w == starts) and BLACK or WHITE)
  end
  local c = b + 9
  for r = 1, SET_ROWS do
    local n, row = math.floor(arg(a, c + 3 * r - 2)), 'lrow' .. r
    local on = n == entry and n > 0
    for _, part in ipairs({ '', 'nl', 'l', 'sl' }) do seen(row .. part, n > 0) end
    local st = tostring(arg(a, c + 3 * r))
    text(row .. 'nl', n > 0 and tostring(n) or '')
    text(row .. 'l', n > 0 and tostring(arg(a, c + 3 * r - 1)) or '')
    text(row .. 'sl', n > 0 and (STARTWORDS[st] or st) or '')
    ink(row .. 'nl', on and BLACK or WHITE)
    ink(row .. 'l', on and BLACK or WHITE)
    ink(row .. 'sl', on and BLACK or GREY)
    light(row, on and 1 or 0)
  end
end

-- A row tapped: the song or the entry it shows, unless it is the one selected already.
local function listTapped(which, r)
  if not songsst then return end
  if which == 'grow' then
    local n = math.floor(arg(songsst, 3 + 3 * r))
    if n > 0 and n ~= math.floor(arg(songsst, 2)) then sendOSC('/cutit', 'songs', 'select', n) end
  else
    local c = 5 + 3 * SONG_ROWS + 9
    local n = math.floor(arg(songsst, c + 3 * r - 2))
    if n > 0 and n ~= math.floor(arg(songsst, c - 2)) then sendOSC('/cutit', 'songs', 'entry', n) end
  end
end

-- delete asks twice (judgment call, 2026-11-05): the first tap arms it and it reads sure?, a
-- second within SURE milliseconds deletes, and after them it is delete again.
local armed = {}
local function confirm(name)
  local now = getMillis()
  if armed[name] and now - armed[name] < SURE then
    armed[name] = nil
    sendOSC('/cutit', 'songs', 'delete')
  else
    armed[name] = now
  end
end

-- ---------------------------------------------------------------- a name being typed
-- A name tab opens on the name it is giving, which done sends if it changed, then turns back to
-- the tab it was opened from: what it names is that tab's (NAMERS' what), the songs page's the
-- selected song from its songs tab and the setlist chosen from its setlists tab. The name is
-- lowercase, as Cut It keeps it, and shows in capitals, as the keys do.
local typing, opened, from = {}, {}, {}
local function current(prefix)
  if prefix == 'sn' and secs then return tostring(arg(secs, 6)) end
  if prefix == 'gn' and songsst then
    return tostring(arg(songsst, from.gn == 1 and 5 + 3 * SONG_ROWS + 3 or 5))
  end
  return ''
end
local function showName(prefix)
  text(prefix .. 'fieldl', string.upper(typing[prefix].buf) .. '_')
end
local function openName(prefix)
  local nm = NAMERS[prefix]
  if not nm.what[from[prefix] or 0] then from[prefix] = 0 end
  text(prefix .. 'what', 'name the ' .. nm.what[from[prefix]])
  local name = current(prefix)
  typing[prefix] = { buf = name, was = name }
  showName(prefix)
end
-- A button that opens a name tab: from the tab it is on.
local function openTab(prefix)
  local nm = NAMERS[prefix]
  if not nm then return end
  from[prefix] = get(nm.pager).values.page
  get(nm.pager).values.page = nm.tab
  openName(prefix)
  opened[prefix] = true
end

local function typed(value)
  local prefix, what = string.match(tostring(value), '^(%%w+):(%%w+)$')
  local nm = prefix and NAMERS[prefix]
  if not nm then return end
  if not typing[prefix] then openName(prefix) end
  local t = typing[prefix]
  if what == 'back' then
    t.buf = string.sub(t.buf, 1, -2)
  elseif what == 'done' then
    local name = string.match(t.buf, '^ *(.-) *$')
    if name ~= '' and name ~= t.was then SEND[prefix][from[prefix] or 0](name) end
    t.was = name ~= '' and name or t.was
    get(nm.pager).values.page = from[prefix] or 0
    return
  else
    local ch = CHARS[string.sub(what, 2)]
    if ch and #t.buf < MAX_NAME and not (ch == ' ' and (t.buf == '' or string.sub(t.buf, -1) == ' ')) then
      t.buf = t.buf .. ch
    end
  end
  showName(prefix)
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
  setShow(get('show').values.x)
  setFx(get('fx').values.x)
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
  elseif path == '/cutit/sections' then
    sections(a)
  elseif path == '/cutit/songs' then
    songs(a)
  elseif path == '/cutit/ack' then
    ack(a)
  end
end

function onReceiveNotify(key, value)
  if key == 'touched' then
    touchedAt[value] = getMillis()
  elseif key == 'show' then
    setShow(value)
  elseif key == 'fx' then
    setFx(value)
  elseif key == 'rolled' then
    askRolled(value)
  elseif key == 'row' then
    rowTapped(value)
  elseif key == 'grow' or key == 'lrow' then
    listTapped(key, value)
  elseif key == 'open' then
    openTab(value)
  elseif key == 'confirm' then
    confirm(value)
  elseif key == 'type' then
    typed(value)
  elseif key == 'press' and PRESS[value] then
    PRESS[value]()
    paintCheck()
  end
end

function update()
  local now = getMillis()
  local up = now - lastHb < 1500
  for _, k in ipairs({ 'link', 'dlink', 'slink', 'seclink', 'glink', 'llink' }) do
    text(k, up and 'link' or 'no link')
    lit(k .. 'led', up)
  end
  lit('tled', up and testOn)
  text('tmode', not up and 'no link' or (testOn and 'test mode on' or 'test mode off'))
  ink('tmode', (up and testOn) and TEAL or GREY)
  text('drunkv', math.floor(get('drunk').values.x * 100 + 0.5) .. '%%')
  text('swingv', SWING[1] + math.floor(get('swing').values.x * (SWING[2] - SWING[1]) + 0.5) .. '%%')
  for _, name in ipairs(FXKNOBS) do
    text(name .. 'v', math.floor(get(name).values.x * 100 + 0.5) .. '%%')
  end
  for name, n in pairs(FXRADIOS) do
    local x = math.floor(get(name).values.x + 0.5)
    for i = 1, n do ink(name .. i .. 'l', i == x + 1 and BLACK or WHITE) end
  end
  for name, base in pairs(BASE) do
    local f = flash[name]
    color(name, (f and now < f[1]) and f[2] or base)
  end
  for prefix, nm in pairs(NAMERS) do
    local page = get(nm.pager).values.page
    local open = page == nm.tab
    if not open then from[prefix] = page end
    if open and not opened[prefix] then openName(prefix) end
    opened[prefix] = open
  end
  text('gdell', (armed.gdel and now - armed.gdel < SURE) and 'sure?' or 'delete')
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
        "shown": lua([w for w, _c, _lo, _hi, _st in SHOW]),
        "lastshow": LAST_SHOW, "steprow": ROW, "steprows": ROWS_OF_STEPS,
        "fxgroups": lua(fx_groups()),
        "fxcontrols": lua([FX_CONTROL.get(f, f) for f in FX]),
        "verbcontrols": lua(VERB),
        "fxknobs": lua([f for f in FX if f not in FX_CONTROL] + VERB),
        "fxradios": lua({"dnote": len(NOTE_NAMES), "dfeel": len(FEEL_NAMES),
                         "char": len(CHAR_NAMES), "vtype": len(VERB_TYPES)}),
        "phonebase": PHONE_BASE, "fxend": FX_END, "flagsend": FLAGS_END, "phone": PHONE,
        "phoneall": PHONE_ALL,
        "flags": lua(list(FLAGS)),
        "rows": ROWS, "maxname": MAX_NAME,
        "namers": lua({p: {"pager": n["pager"], "tab": n["tab"],
                           "what": {t: w for t, (w, _c) in n["from"].items()}}
                       for p, n in NAMERS.items()}),
        "chars": lua({name: ch for row in KEYS for key in row if key for name, ch in [key]}),
        "send": "local SEND = {\n" + "".join(
            "  %s = {\n%s  },\n" % (p, "".join(
                "    [%d] = function(name) sendOSC('/cutit', %s, name) end,\n"
                % (t, ", ".join(lua(a) for a in c)) for t, (_w, c) in sorted(n["from"].items())))
            for p, n in NAMERS.items()) + "}",
        "songrows": SONG_ROWS, "setrows": SET_ROWS,
        "starts": lua(STARTS), "startwords": lua(STARTS_WORDS), "sure": SURE_MS,
        "red": lua_color(RED), "teal": lua_color(TEAL), "white": lua_color(WHITE),
        "grey": lua_color(GREY), "black": lua_color(BLACK)}


SCREENS = {"arrangement": arrangement, "drums": drums, "synths": synths}
# A Launchpad page with more than one tab: each tab's page name, its label and its controls.
TABBED = {"sections": [("sections", "sections", sections),
                       ("secname", "name", lambda: name_tab("sn", "section"))],
          "songs": [("songs", "songs", songs_tab), ("setlists", "setlists", setlists_tab),
                    ("songname", "name", lambda: name_tab("gn", "song"))]}


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
        if screen in TABBED:
            held = [page(name, label_, make(), H - TAB) for name, label_, make in TABBED[screen]]
        else:
            held = [page(screen, tab, SCREENS[screen]() if screen in SCREENS else [], H - TAB)]
        inner = tabs("tabs%d" % (i + 1), held)
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
