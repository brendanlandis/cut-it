#!/usr/bin/env python3
"""Builds a TouchOSC layout of the phone's drum screen, CutItDrums.tosc, a proof of concept
beside the PdParty one (Brendan, 2026-11-04).

    python3 tools/touchosc/build-drums.py           write it
    python3 tools/touchosc/build-drums.py --check   exit 1 if it is stale

It talks to u_net exactly as PdParty's drum screen does, so Cut It needs no change: it sends
/cutit drums <action> [<n>] to the Organelle's 9001 and shows /cutit/drums, c_steps' 41 numbers,
with /cutit/hb, /cutit/status, /cutit/alert and /cutit/ack, coming back to its 8000
(ref/device/phone.md). The layout is PdParty's (tools/pdparty-scene/build-remote.py) at twice the
size: 896 by 414 points, an iPhone 11 in landscape, with the right edge and the bottom kept clear.

A .tosc file is zlib-compressed XML. Each control sends from a script of its own, sendOSC, never
from TouchOSC's message settings, and the root script holds everything that comes in.
"""
import os
import re
import sys
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "CutItDrums.tosc")

S = 2               # PdParty's units to TouchOSC's points
W, H = 896, 414


def rgb(r, g, b, a=1.0):
    return (r / 255, g / 255, b / 255, a)


INK, PAPER, BTN, LIT, EDGE = rgb(24, 24, 24), rgb(232, 232, 232), rgb(252, 252, 252), \
    rgb(140, 210, 140), rgb(96, 96, 96)
DOWN = rgb(232, 140, 140)
GROUND = rgb(40, 40, 40)
CLEAR = rgb(0, 0, 0, 0)
PRESS = rgb(255, 255, 255, 0.35)
# A pad: following the global last step, with its own, selected, selected with its own.
PADS = [(rgb(200, 200, 200), rgb(40, 40, 40)), (rgb(248, 208, 112), rgb(60, 40, 0)),
        (rgb(60, 60, 60), rgb(255, 255, 255)), (rgb(150, 100, 20), rgb(255, 255, 255))]


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


# What every control has, as TouchOSC's editor saved them (~/Desktop/Untitled.tosc).
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
    """PdParty's units, from the drum screen's left edge, as TouchOSC's points."""
    return (x * S, y * S, w * S, h * S)


# TouchOSC draws a label's or a button's background faint and a box at full strength (measured
# on the Mac's TouchOSC, 2026-11-04), so a colored cell is a box, <name>bg, under a label with no
# background, <name>, which holds the text.
def cell(name, x, y, w, h, text, size, fill=PAPER, ink=INK):
    return [node("BOX", name + "bg", at(x, y, w, h), color=fill),
            node("LABEL", name, at(x, y, w, h), text=text, background=False, textColor=ink,
                 textSize=size * S)]


def words(name, x, y, w, h, text, size, ink=PAPER):
    """Text straight on the screen."""
    return node("LABEL", name, at(x, y, w, h), text=text, background=False, textColor=ink,
                textSize=size * S)


def touch(name, x, y, w, h, send):
    """The touch over a cell: no background, so the cell shows through, a flash while pressed,
    and the message on the press."""
    script = ("function onValueChanged(key)\n"
              "  if key == 'x' and self.values.x == 1 then sendOSC('/cutit', %s) end\n"
              "end\n" % send)
    return node("BUTTON", name, at(x, y, w, h), background=False, outline=False, color=PRESS,
                script=script)


def fader(name, x, y, w, h):
    """A slider, 0 to 100, its percent beside it. It sends whole percents when its value moves
    off the last one it knows, its own or one the root script hands it from Cut It's state with
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
    return [words(name + "v", x, y, lw, h, name + " 0%", 10),
            node("FADER", name, at(x + lw, y, w - lw, h), color=LIT, orientation=1,
                 script=script)]


# ------------------------------------------------------------------ the root's script
ROOT = r"""-- Cut It's drum screen: what u_net sends, onto the controls (ref/device/phone.md).
local PADS = { %(pads)s }
local PAPER, BTN, LIT, DOWN = %(paper)s, %(btn)s, %(lit)s, %(down)s
local pad, bg, lab, fad = {}, {}, {}, {}
local touchedAt, flash, shown = {}, {}, {}
local lastHb = -100000

local function arg(a, i)
  return a[i] and a[i].value or 0
end

-- Set a text only when it differs, since update() runs every frame.
local function text(c, t)
  if shown[c] ~= t then shown[c] = t; c.values.text = t end
end

function init()
  for n = 1, 16 do
    pad[n], bg['pad' .. n] = root:findByName('pad' .. n, true), root:findByName('pad' .. n .. 'bg', true)
  end
  for _, k in ipairs({ 'play', 'status', 'glob', 'alert', 'link', 'pending', 'num', 'den',
                       'sync', 'snap', 'skipv', 'movev', 'drunkv' }) do
    lab[k] = root:findByName(k, true)
    bg[k] = root:findByName(k .. 'bg', true)
  end
  for _, k in ipairs({ 'skip', 'move', 'drunk' }) do
    fad[k] = root:findByName(k, true)
    if Orientation then fad[k].orientation = Orientation.EAST end
  end
end

local function setFader(k, v)
  if fad[k].values.touch or getMillis() - (touchedAt[k] or -100000) < 1000 then return end
  fad[k]:notify('state', v)
end

-- c_steps' 41 numbers: playing, the global last step, the selected track, a pending sync or
-- snap (1, 2), the sixteen last steps, then 1 for each track with its own, then the time
-- signature, the drunkenness and the selected track's skip and move.
local function drums(a)
  if #a < 41 then return end
  local playing, track, pending = arg(a, 1) == 1, math.floor(arg(a, 3)), arg(a, 4)
  text(lab.play, playing and 'playing' or 'stopped')
  bg.play.color = playing and LIT or PAPER
  text(lab.glob, 'last ' .. math.floor(arg(a, 2)))
  text(lab.pending, pending == 2 and 'snap waits for step 1'
       or (pending == 1 and 'sync waits for step 1' or ''))
  for n = 1, 16 do
    local c = PADS[(n == track and 2 or 0) + (arg(a, 20 + n) == 1 and 1 or 0) + 1]
    bg['pad' .. n].color, pad[n].textColor = c[1], c[2]
    text(pad[n], tostring(math.floor(arg(a, 4 + n))))
  end
  text(lab.num, tostring(math.floor(arg(a, 37))))
  text(lab.den, tostring(math.floor(arg(a, 38))))
  setFader('drunk', math.floor(arg(a, 39)))
  setFader('skip', math.floor(arg(a, 40)))
  setFader('move', math.floor(arg(a, 41)))
end

function onReceiveOSC(message, connections)
  local path, a = message[1], message[2]
  if path == '/cutit/drums' then
    drums(a)
  elseif path == '/cutit/hb' then
    lastHb = getMillis()
  elseif path == '/cutit/status' then
    text(lab.status, tostring(arg(a, 1)))
  elseif path == '/cutit/alert' then
    local level = tostring(arg(a, 2))
    text(lab.alert, level == 'none' and 'no-alerts'
         or (tostring(arg(a, 3)) .. ' ' .. tostring(arg(a, 4))))
  elseif path == '/cutit/ack' and arg(a, 1) == 'drums' and bg[arg(a, 2)] then
    flash[arg(a, 2)] = getMillis() + 300
  end
end

function onReceiveNotify(key, value)
  if key == 'touched' then touchedAt[value] = getMillis() end
end

function update()
  local now = getMillis()
  local up = now - lastHb < 1500
  text(lab.link, up and 'link' or 'NO-LINK')
  if shown.linkUp ~= up then
    shown.linkUp = up
    bg.link.color = up and LIT or DOWN
  end
  for k, f in pairs(fad) do
    text(lab[k .. 'v'], k .. ' ' .. math.floor(f.values.x * 100 + 0.5) .. '%%')
  end
  for _, k in ipairs({ 'sync', 'snap' }) do
    local on = flash[k] ~= nil and now < flash[k]
    if shown[k .. 'On'] ~= on then
      shown[k .. 'On'] = on
      bg[k].color = on and LIT or BTN
    end
  end
end
"""


def lua_color(c):
    return "Color(%g, %g, %g)" % c[:3]


def root_script():
    return ROOT % {
        "pads": ", ".join("{ %s, %s }" % (lua_color(f), lua_color(t)) for f, t in PADS),
        "paper": lua_color(PAPER), "btn": lua_color(BTN), "lit": lua_color(LIT),
        "down": lua_color(DOWN)}


# ------------------------------------------------------------------ the screen
PAD, PITCH = 33, 35
BX, BW, BH = 304, 118, 34


def build():
    c = []
    # down the left: the transport, the tempo, the global last step, the alert and the link
    for name, y, h, text, size in (("play", 4, 30, "stopped", 14), ("status", 38, 44, "-", 20),
                                   ("glob", 86, 34, "last 16", 16),
                                   ("alert", 124, 28, "no-alerts", 12),
                                   ("link", 156, 32, "NO-LINK", 16)):
        c += cell(name, 4, y, 146, h, text, size, DOWN if name == "link" else PAPER)
    # the pads, as the Launchpad lays them out, pad 1 at the top left: the cell shows the
    # track's last step and its state, the touch over it selects the track
    for n in range(1, 17):
        r, k = (n - 1) // 4, (n - 1) % 4
        x, y = 156 + k * PITCH, 4 + r * PITCH
        c += cell("pad%d" % n, x, y, PAD, PAD, "16", 14, PADS[0][0], PADS[0][1])
        c.append(touch("tap%d" % n, x, y, PAD, PAD, "'drums', 'select', %d" % n))
    # the selected track's chances under the pads
    for name, y in (("skip", 146), ("move", 170)):
        c += fader(name, 156, y, 3 * PITCH + PAD, 20)
    # down the right: sync and snap, the line saying one waits, the time signature, drunk
    for name, y, text in (("sync", 4, "sync first steps"), ("snap", 42, "snap to global")):
        c += cell(name, BX, y, BW, BH, text, 12, BTN)
        c.append(touch(name + "t", BX, y, BW, BH, "'drums', '%s'" % name))
    c.append(words("pending", BX, 78, BW, 14, "", 9))
    for name, y in (("num", 95), ("den", 127)):
        c += cell(name + "m", BX, y, 28, 28, "−", 16, BTN)
        c.append(touch(name + "mt", BX, y, 28, 28, "'drums', '%s', -1" % name))
        c += cell(name, BX + 32, y, 54, 28, "4", 16)
        c += cell(name + "p", BX + 90, y, 28, 28, "+", 16, BTN)
        c.append(touch(name + "pt", BX + 90, y, 28, 28, "'drums', '%s', 1" % name))
    c += fader("drunk", BX, 160, BW, 30)
    root = node("GROUP", "root", (0, 0, W, H), c, color=GROUND, script=root_script())
    return '<?xml version="1.0" encoding="UTF-8"?><lexml version="6">' + root + "</lexml>"


def main():
    xml = build().encode("utf-8")
    if "--check" in sys.argv:
        # IDs are fresh on every build, so compare with them taken out
        old = zlib.decompress(open(OUT, "rb").read()).decode("utf-8")
        strip = lambda s: re.sub(r'ID="[^"]+"', 'ID=""', s)
        sys.exit(0 if strip(old) == strip(xml.decode("utf-8")) else 1)
    with open(OUT, "wb") as fh:
        fh.write(zlib.compress(xml, 9))
    print("wrote %s (%d bytes of XML)" % (os.path.relpath(OUT), len(xml)))


if __name__ == "__main__":
    main()
