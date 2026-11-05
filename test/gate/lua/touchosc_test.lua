-- The phone's TouchOSC layout, its scripts run under lib_touchosc.lua's stand-in: the pages and
-- the mode, test mode, the arrangement screen, the drum screen, the synths screen, the sections
-- page and its name tab, the songs page, its setlists and its name tab, and the checklist page. Run by touchosc-assert.py, which unpacks the layout into a folder and writes
-- expect.lua beside it:
--
--   lua test/gate/lua/touchosc_test.lua <folder> [-v]

local T = dofile("test/gate/lua/lib_test.lua")
local L = dofile("test/gate/lua/lib_touchosc.lua")
local check, equal = T.check, T.equal
local dir = arg[1]
local E = dofile(dir .. "/expect.lua")
local manifest = dofile(dir .. "/controls.lua")
local w = L.load(dir)
local C = w.controls
local function hb(test) L.osc(w, "/cutit/hb", 1, test and 1 or 0) end
local function mode(m) L.osc(w, "/cutit/mode", m) end
-- Where the phone is: the outer page showing, and the tab its own pager shows.
local function where()
  local outer = L.page(w, "pages")
  local inner = outer.children[1]
  return { outer.name, L.page(w, inner.name).tabLabel }
end
local function teal(c) return c[2] > 0.7 and c[1] < 0.3 end
local function red(c) return c[1] > 0.9 and c[2] < 0.2 end
local function black(c) return c and c[1] < 0.1 and c[2] < 0.1 end
-- The state c_steps sends: 131 numbers, from what differs; after the first 88 the selected
-- track's effects, its character last, and the reverb's, at their starting points unless t.fx
-- gives them, then each track's mute and each track's solo, 0 unless t.mute or t.solo gives them.
local FX = { { "drive", 50 }, { "tone", 100 }, { "dist", 0 }, { "note", 3 }, { "feel", 1 },
             { "feedback", 40 }, { "delay", 0 }, { "send", 0 }, { "char", 1 }, { "size", 50 },
             { "damping", 50 } }
local function drumstate(t)
  local st = { t.playing or 0, t.last or 16, t.track or 1, t.pending or 0 }
  for n = 1, 16 do st[#st + 1] = (t.lasts or {})[n] or t.last or 16 end
  for n = 1, 16 do st[#st + 1] = (t.owns or {})[n] or 0 end
  for _, v in ipairs({ t.num or 4, t.den or 4, t.drunk or 0, t.swing or 50 }) do
    st[#st + 1] = v
  end
  for _, which in ipairs({ "vol", "pitch", "randomness" }) do
    for n = 1, 16 do st[#st + 1] = (t[which] or {})[n] or 0 end
  end
  for _, f in ipairs(FX) do st[#st + 1] = (t.fx or {})[f[1]] or f[2] end
  for _, which in ipairs({ "mute", "solo" }) do
    for n = 1, 16 do st[#st + 1] = (t[which] or {})[n] or 0 end
  end
  return st
end
-- A drum pad's step, as a share of its whole travel: the layout's, which the reading half holds
-- to about 20 points.
local STEP = 1 / E.pad_steps

print("\n--- the pages, the mode and test mode ---")
local bar
for _, m in ipairs(manifest) do if m.name == "pages" then bar = m.tabbar end end
equal("the outer pager's tab bar is on in the file, the editor's way to each page", bar, true)
equal("⛔ ... and the root's script hides it, so the phone shows the page's own tabs",
      C.pages.tabbar, false)
equal("before any mode: page 1, the arrangement, under its own tab", where(),
      { "p1", "arrangement" })
L.update(w)
equal("no heartbeat yet: no link on every screen and the checklist page",
      { L.text(w, "link"), L.text(w, "dlink"), L.text(w, "slink"), L.text(w, "seclink"),
        L.text(w, "tmode") }, { "no link", "no link", "no link", "no link", "no link" })
hb(false)
L.update(w)
equal("a heartbeat: link, its lamps lit, and test mode off",
      { L.text(w, "link"), C.linkled.values.x, C.dlinkled.values.x, C.slinkled.values.x,
        C.seclinkled.values.x, L.text(w, "tmode") }, { "link", 1, 1, 1, 1, "test mode off" })
local TABS = { "arrangement", "drums", "synths", "page 4", "page 5", "page 6", "sections", "songs" }
for n, tab in ipairs(TABS) do
  mode("mode-" .. n)
  equal("page " .. n .. ": the Launchpad's page " .. n .. ", its first tab named " .. tab, where(),
        { "p" .. n, tab })
end
mode("mode-2")
w.sent = {}
mode("mode-2")
equal("the mode's repeat turns nothing and sends nothing", { where(), #w.sent },
      { { "p2", "drums" }, 0 })
equal("⛔ pages 4 to 6 are blank", { #C.page4.children, #C.page5.children, #C.page6.children },
      { 0, 0, 0 })
hb(true)
L.update(w)
equal("test mode on: the checklist page in place of the Launchpad's, its lamp lit",
      { where(), L.text(w, "tmode"), C.tled.values.x },
      { { "pcheck", "line check" }, "test mode on", 1 })
mode("mode-3")
equal("... staying through a change of mode", where(), { "pcheck", "line check" })
hb(true)
equal("a heartbeat still saying test mode changes nothing", where()[1], "pcheck")
hb(false)
equal("test mode off: the page of the mode chosen meanwhile", where(), { "p3", "synths" })
mode("mode-9")
equal("a mode off the Launchpad's eight is page 1", where()[1], "p1")
mode("mode-1")

print("\n--- the arrangement screen: the tempo ---")
w.sent = {}
L.osc(w, "/cutit/tempo", 120)
equal("u_tempo's 120: the tempo, large, and nothing sent back", { L.text(w, "tempo"), #w.sent },
      { "120", 0 })
-- the state put 120 in the middle of its step, 115.5 / 596
equal("a tempo dragged up two BPM sends tempo 122, once",
      L.drag(w, "tempobox", 117.5 / 596), { { "/cutit", "tempo", 122 } })
equal("... and nothing while the BPM shown does not change",
      L.drag(w, "tempobox", 117.9 / 596), {})
L.update(w, 500)
L.osc(w, "/cutit/tempo", 120)
equal("the old tempo half a second later leaves the box where the finger put it, and the "
      .. "number says Cut It's", { #w.sent, L.text(w, "tempo") }, { 1, "120" })
L.update(w, 1100)
w.sent = {}
L.osc(w, "/cutit/tempo", 117.5)
equal("⛔ a tempo that is not whole shows as it is, and is not sent back rounded",
      { L.text(w, "tempo"), #w.sent }, { "117.5", 0 })
L.osc(w, "/cutit/tempo", 150)
L.osc(w, "/cutit/tempo", 150)
equal("⛔ the tempo set elsewhere, a tap or knob 1, and its repeat, send nothing back", #w.sent, 0)
equal("the box drags a BPM at a time down to 5 and up to 600",
      { L.drag(w, "tempobox", 0)[1][3], L.drag(w, "tempobox", 1)[1][3] }, { 5, 600 })
L.update(w, 1100)
L.osc(w, "/cutit/tempo")
L.osc(w, "/cutit/tempo", "x")
equal("an empty tempo, before the first, or a word, changes nothing", L.text(w, "tempo"), "150")

print("\n--- the arrangement screen: tap tempo ---")
-- The phone times its own taps, as the finger lands (WiFi delivers unevenly), and sends the tempo.
L.update(w, 3000)
w.sent = {}
equal("the first tap only starts the count", L.press(w, "tap"), {})
L.update(w, 500)
equal("a second, half a second later: 120", L.press(w, "tap"), { { "/cutit", "tempo", 120 } })
L.update(w, 400)
equal("a third, 400 ms on: the average of the two intervals, 133",
      L.press(w, "tap"), { { "/cutit", "tempo", 133 } })
for _ = 1, 4 do L.update(w, 600); L.press(w, "tap") end
equal("after four more at 600 ms, only the last four intervals count: 100",
      w.sent[#w.sent], { "/cutit", "tempo", 100 })
equal("two taps in one instant count nothing", L.press(w, "tap"), {})
L.update(w, 2100)
equal("over two seconds later, tapping starts over: nothing sent", L.press(w, "tap"), {})
L.update(w, 2)
equal("taps 2 ms apart give the most u_tempo takes, 600", L.press(w, "tap"),
      { { "/cutit", "tempo", 600 } })
L.update(w, 2100); L.press(w, "tap"); L.update(w, 1999)
equal("and taps 1999 ms apart, 30", L.press(w, "tap"), { { "/cutit", "tempo", 30 } })

print("\n--- the arrangement screen: the sequencer's settings ---")
w.sent = {}
L.osc(w, "/cutit/drums", table.unpack(drumstate({ playing = 1, last = 12, num = 7, den = 8,
                                                 drunk = 30, swing = 62 })))
L.update(w)
equal("c_steps' state: playing, its lamp lit, 7 / 8, the last step 12",
      { L.text(w, "play"), C.playled.values.x, L.text(w, "num"), L.text(w, "den"),
        L.text(w, "last") }, { "playing", 1, "7", "8", "12" })
equal("the swing and drunk knobs take theirs, and say them",
      { C.swing.values.x, L.text(w, "swingv"), C.drunk.values.x, L.text(w, "drunkv") },
      { (62 - 50) / 25, "62%", 0.3, "30%" })
equal("⛔ taking the state sends nothing back", #w.sent, 0)
equal("⛔ a turn of swing sends set-swing in whole percents, 50 to 75, c_steps' range",
      { L.drag(w, "swing", (70 - 50) / 25), L.drag(w, "swing", 0), L.drag(w, "swing", 1) },
      { { { "/cutit", "drums", "set-swing", 70 } }, { { "/cutit", "drums", "set-swing", 50 } },
        { { "/cutit", "drums", "set-swing", 75 } } })
L.update(w)
equal("... and says it", L.text(w, "swingv"), "75%")
L.drag(w, "swing", (70 - 50) / 25)
equal("a turn of drunk sends whole percents, once each", L.drag(w, "drunk", 0.501),
      { { "/cutit", "drums", "drunk", 50 } })
equal("... and nothing when the percent does not change", L.drag(w, "drunk", 0.504), {})
-- the box reaches 28 at the state's 7/8, and the state put 12 in the middle of its step
equal("dragging the last step from 12 to 14 sends set-last 14",
      L.drag(w, "lastbox", (13 + 0.5) / 28), { { "/cutit", "drums", "set-last", 14 } })
L.update(w, 500)
L.osc(w, "/cutit/drums", table.unpack(drumstate({ playing = 1, last = 12, num = 7, den = 8,
                                                 drunk = 30, swing = 62 })))
equal("the old state half a second later leaves the knob where the finger put it",
      C.drunk.values.x, 0.504)
L.update(w, 1100)
w.sent = {}
L.osc(w, "/cutit/drums", table.unpack(drumstate({ playing = 1, last = 14, num = 7, den = 8,
                                                 drunk = 50, swing = 70 })))
equal("... and once the state agrees, nothing more is sent", #w.sent, 0)
-- the boxes: the state put 7 in the middle of its step, 6.5 / 32
equal("dragging 7 up two steps sends num 1 twice", L.drag(w, "numbox", 8.5 / 32),
      { { "/cutit", "drums", "num", 1 }, { "/cutit", "drums", "num", 1 } })
equal("dragging 8 down one step, of 1 2 4 8 16, sends den -1", L.drag(w, "denbox", 2.5 / 5),
      { { "/cutit", "drums", "den", -1 } })
local short = drumstate({})
for _ = 88, #short do table.remove(short) end
L.osc(w, "/cutit/drums", table.unpack(short))
equal("fewer than 88 numbers draws nothing", L.text(w, "play"), "playing")

print("\n--- the arrangement screen: how far the last step reaches ---")
-- The time signature's top number sets how far a last step reaches, four rows of the drum page
-- (Brendan, 2026-11-05): c_steps.lua's R.reach, which clips the phone's set-last to it. The box
-- reaches exactly that far: dragged to its top it sends the furthest step, and a step is a
-- step of that range.
local S = dofile("Cut It/c_steps.lua")
local function at_num(num, last)
  L.update(w, 1100)
  L.osc(w, "/cutit/drums", table.unpack(drumstate({ last = last or 12, num = num })))
end
local function top(num)
  at_num(num)
  local out = L.drag(w, "lastbox", 1)
  at_num(num)
  return out[1] and out[1][4]
end
equal("⛔ dragged to its top the box sends the furthest step c_steps takes: 24 at 3/4, 20 at "
      .. "5/4, 28 at 7/8, 32 at 4/4, 9/8 and 1/4",
      { top(3), top(5), top(7), top(4), top(9), top(1) }, { 24, 20, 28, 32, 32, 32 })
local off = {}
for n = 1, 32 do
  local st = S.new(1)
  st.num = n
  if top(n) ~= S.reach(st) then off[#off + 1] = n .. ": " .. tostring(top(n)) end
end
equal("⛔ ... for every top number, 1 to 32, as far as c_steps' own R.reach", off, {})
at_num(3)
equal("at 3/4 the state's 12 sits in the middle of its step of 24, and nothing is sent",
      { C.lastbox.values.x, #L.drag(w, "lastbox", (12 - 0.5) / 24) }, { (12 - 0.5) / 24, 0 })
at_num(3)
equal("... and a drag one step of 24 up sends 13", L.drag(w, "lastbox", (13 - 0.5) / 24),
      { { "/cutit", "drums", "set-last", 13 } })
at_num(5, 20)
w.sent = {}
at_num(5, 20)
equal("⛔ a time signature that moves the reach sends nothing back: 5/4 at its 20", #w.sent, 0)
at_num(4, 20)
equal("... and 4/4 then puts 20 lower in a box of 32, still sending nothing",
      { C.lastbox.values.x, #w.sent }, { (20 - 0.5) / 32, 0 })

print("\n--- the drum screen ---")
mode("mode-2")
w.sent = {}
local st = drumstate({ playing = 1, last = 12, track = 2, pending = 1, lasts = { [3] = 5 },
                       owns = { [3] = 1 }, vol = { [1] = -6, [4] = 3 },
                       pitch = { [1] = 7, [5] = -12 }, randomness = { [6] = 40 } })
L.osc(w, "/cutit/drums", table.unpack(st))
L.update(w)
equal("a sync pending says so", L.text(w, "pending"), "sync waits for step 1")
equal("⛔ the radio starts on volume: each pad shows its track's in dB, signed",
      { C.show.values.x, L.text(w, "pad1l"), L.text(w, "pad2l"), L.text(w, "pad4l") },
      { 0, "-6", "0", "+3" })
equal("pad 2, selected, has its fill lit and the rest not",
      { C.pad2f.values.x, C.pad1f.values.x, C.pad3f.values.x }, { 1, 0, 0 })
check("... its number black on the lit fill, the rest white",
      black(C.pad2l.textColor) and not black(C.pad1l.textColor), T.show(C.pad2l.textColor))
check("on volume every pad is red, pad 3 with its own last step too",
      red(C.pad3f.color) and red(C.pad3.color), T.show({ C.pad3f.color, C.pad3.color }))
equal("⛔ lighting the selected pad and handing every pad its number sends nothing", #w.sent, 0)
equal("⛔ the radio sends nothing to Cut It", L.drag(w, "show", 1), {})
equal("on pitch every pad shows its track's in semitones, signed",
      { L.text(w, "pad1l"), L.text(w, "pad5l"), L.text(w, "pad2l") }, { "+7", "-12", "0" })
check("... the radio's pitch black on its lit segment, volume white again",
      black(C.show2l.textColor) and not black(C.show1l.textColor), "")
L.drag(w, "show", 2)
equal("on last each pad shows its last step; pad 3, with its own, a dot before it",
      { L.text(w, "pad1l"), L.text(w, "pad3l") }, { "12", "\u{2022} 5" })
check("... and is teal, pad 1 red", teal(C.pad3f.color) and teal(C.pad3.color) and red(C.pad1f.color),
      T.show({ C.pad3f.color, C.pad1f.color }))
L.drag(w, "show", 3)
equal("on random each pad shows its randomness in percent", { L.text(w, "pad6l"), L.text(w, "pad1l") },
      { "40%", "0%" })
check("... and pad 3 is red again", red(C.pad3f.color), T.show(C.pad3f.color))
equal("still nothing sent", #w.sent, 0)
-- four pads pressed at once on the Launchpad: four states, a track each, as fast as they come
for _, t in ipairs({ 11, 12, 15, 16 }) do
  st[3] = t
  L.osc(w, "/cutit/drums", table.unpack(st))
end
equal("states selecting one track after another light each in turn and send nothing back",
      { C.pad16f.values.x, C.pad11f.values.x, #w.sent }, { 1, 0, 0 })
equal("⛔ a pad tapped, a finger down and up, selects its track", L.tap(w, "pad5"),
      { { "/cutit", "drums", "select", 5 } })
equal("⛔ ... and the selected pad tapped sends nothing", L.tap(w, "pad16"), {})
-- A pad's drag: from its middle, where the state puts it, a step every 20 points, STEP of it.
L.drag(w, "show", 0)
equal("⛔ on volume, pad 4 dragged up 40 points sends its volume as it stands, +5 dB, and selects "
      .. "nothing", L.drag(w, "pad4", 0.5 + 2 * STEP), { { "/cutit", "drums", "vol", 4, 5 } })
equal("... half a step further is still +5: nothing", L.drag(w, "pad4", 0.5 + 2.4 * STEP), {})
equal("... and down past where it started, -1", L.drag(w, "pad4", 0.5 - 4 * STEP),
      { { "/cutit", "drums", "vol", 4, -1 } })
L.update(w, 500)
L.osc(w, "/cutit/drums", table.unpack(st))
equal("the old state half a second later leaves the pad where the finger put it",
      C.pad4.values.x, 0.5 - 4 * STEP)
L.update(w, 1100)
w.sent = {}
st[40 + 4] = 6
L.osc(w, "/cutit/drums", table.unpack(st))
equal("⛔ once a second has passed, the state, +6, puts the pad back in its middle and sends nothing",
      { C.pad4.values.x, L.text(w, "pad4l"), #w.sent }, { 0.5, "+6", 0 })
equal("at +6, the top, a drag further up sends nothing, and selects nothing",
      L.drag(w, "pad4", 0.6), {})
L.drag(w, "show", 1)
equal("on pitch, pad 1 dragged down a step sends its pitch, +6", L.drag(w, "pad1", 0.5 - STEP),
      { { "/cutit", "drums", "pitch", 1, 6 } })
equal("... and no further than -12 at the bottom", L.drag(w, "pad1", 0),
      { { "/cutit", "drums", "pitch", 1, -12 } })
L.drag(w, "show", 2)
equal("on last, pad 7 dragged up three steps sends set-track-last 7 15",
      L.drag(w, "pad7", 0.5 + 3 * STEP), { { "/cutit", "drums", "set-track-last", 7, 15 } })
L.drag(w, "show", 3)
equal("⛔ on random, a step is five: pad 6 dragged up a step, 40 to 45",
      L.drag(w, "pad6", 0.5 + STEP), { { "/cutit", "drums", "randomness", 6, 45 } })
L.update(w, 1100)
st[72 + 6] = 33
L.osc(w, "/cutit/drums", table.unpack(st))
equal("from 33, set before the fives, a step up is 35 and a step down 30",
      { L.drag(w, "pad6", 0.5 + STEP), L.drag(w, "pad6", 0.5 - STEP) },
      { { { "/cutit", "drums", "randomness", 6, 35 } }, { { "/cutit", "drums", "randomness", 6, 30 } } })
equal("... and no further than 100", L.drag(w, "pad6", 1), { { "/cutit", "drums", "randomness", 6, 100 } })
print("\n--- the drum screen's effects ---")
-- A second vertical radio picks the selected track's effect, and its controls show to the right
-- of it (Brendan, 2026-11-05). The selected track is 16, from the presses above.
local function shows(names)
  local out = {}
  for _, n in ipairs(names) do out[#out + 1] = L.visible(w, n) end
  return out
end
equal("⛔ the effect radio starts on distortion: its character, drive, tone and mix show, the "
      .. "delay's and the reverb's controls hide",
      { C.fx.values.x, shows({ "char", "charc", "char4l", "drive", "tone", "dist", "distc", "dnote",
                               "dfeel1l", "feedback", "send", "size", "damping" }) },
      { 0, { true, true, true, true, true, true, true, false, false, false, false, false,
             false } })
equal("⛔ the radio sends nothing to Cut It", L.drag(w, "fx", 1), {})
equal("on delay its time, a note over a feel, its feedback and its level show, and nothing else",
      shows({ "dnote", "dnote4l", "dfeel", "dtimec", "feedback", "delay", "delayc", "drive",
              "send", "char", "char1l" }),
      { true, true, true, true, true, true, true, false, false, false, false })
check("... the radio's delay black on its lit segment, distortion white again",
      black(C.fx2l.textColor) and not black(C.fx1l.textColor), "")
L.drag(w, "fx", 2)
equal("on reverb the track's send and the reverb's size and damping",
      shows({ "send", "size", "damping", "sizec", "dnote", "drive" }),
      { true, true, true, true, false, false })
w.sent = {}
L.update(w, 1100)
st[3] = 16
for i, v in ipairs({ 70, 20, 40, 2, 3, 55, 30, 60, 3, 80, 10 }) do st[88 + i] = v end
L.osc(w, "/cutit/drums", table.unpack(st))
L.update(w)
equal("⛔ the state hands the selected track's effects to their controls, and nothing goes back",
      { C.drive.values.x, C.dist.values.x, C.dnote.values.x, C.dfeel.values.x, C.delay.values.x,
        C.send.values.x, C.char.values.x, C.size.values.x, C.damping.values.x, #w.sent },
      { 0.7, 0.4, 1, 2, 0.3, 0.6, 2, 0.8, 0.1, 0 })
equal("... each knob's value in its middle, the note value, the feel and the character black on "
      .. "theirs", { L.text(w, "distv"), L.text(w, "sizev"), black(C.dnote2l.textColor),
                     black(C.dnote3l.textColor), black(C.dfeel3l.textColor),
                     black(C.char3l.textColor), black(C.char1l.textColor) },
      { "40%", "80%", true, false, true, true, false })
equal("⛔ a knob turned sends its effect for the selected track, as it stands",
      { L.drag(w, "send", 0.65), L.drag(w, "dist", 0.5) },
      { { { "/cutit", "drums", "send", 16, 65 } }, { { "/cutit", "drums", "dist", 16, 50 } } })
equal("⛔ the delay's radios send its note value and its feel, 1 the first",
      { L.drag(w, "dnote", 3), L.drag(w, "dfeel", 1) },
      { { { "/cutit", "drums", "delay-note", 16, 4 } }, { { "/cutit", "drums", "delay-feel", 16, 2 } } })
equal("⛔ the character radio sends the distortion's character for the selected track, 1 soft to "
      .. "4 crush, and the one it was handed again sends nothing",
      { L.drag(w, "char", 3), L.drag(w, "char", 0), L.drag(w, "char", 0) },
      { { { "/cutit", "drums", "char", 16, 4 } }, { { "/cutit", "drums", "char", 16, 1 } }, {} })
equal("the reverb's size and damping are the kit's: no track", L.drag(w, "size", 0.9),
      { { "/cutit", "drums", "size", 90 } })
L.update(w, 1100)
st[3] = 5
L.osc(w, "/cutit/drums", table.unpack(st))
equal("⛔ another track selected, a knob sends for it", L.drag(w, "feedback", 0.25),
      { { "/cutit", "drums", "feedback", 5, 25 } })
w.sent = {}
L.update(w, 1100)
L.osc(w, "/cutit/drums", table.unpack(drumstate({ track = 5 })))
equal("an 88-number state, from before the effects, still draws the pads and leaves the "
      .. "effects as they were", (function()
        local old = drumstate({ track = 5, vol = { [5] = -3 } })
        while #old > 88 do table.remove(old) end
        L.drag(w, "show", 0)
        L.osc(w, "/cutit/drums", table.unpack(old))
        return { L.text(w, "pad5l"), C.drive.values.x, #w.sent }
      end)(), { "-3", 0.5, 0 })
-- The pads' last step reaches only as far as the time signature lets it (c_steps.lua's R.reach):
-- 24 at 3/4, four rows of six.
L.drag(w, "show", 2)
L.update(w, 1100)
L.osc(w, "/cutit/drums", table.unpack(drumstate({ num = 3, den = 4, last = 12, track = 5 })))
equal("⛔ at 3/4 a pad dragged all the way up on last sends 24, the furthest a last step reaches",
      L.drag(w, "pad7", 1), { { "/cutit", "drums", "set-track-last", 7, 24 } })
L.update(w, 1100)
L.osc(w, "/cutit/drums", table.unpack(drumstate({ num = 4, den = 4, last = 12, track = 5 })))
equal("... and 32 at 4/4", L.drag(w, "pad8", 1), { { "/cutit", "drums", "set-track-last", 8, 32 } })
print("\n--- the drum screen's mutes and solos ---")
-- An M and an S under each pad (Brendan, 2026-11-05), lit by the state, never by a finger's own
-- value, and a tap asks for the other setting, as the velocity switch does.
local function flags(which)
  local out = {}
  for n = 1, 16 do out[n] = C[which .. n].values.x end
  return out
end
local function lit_at(...)
  local out = {}
  for n = 1, 16 do out[n] = 0 end
  for _, n in ipairs({ ... }) do out[n] = 1 end
  return out
end
w.sent = {}
L.osc(w, "/cutit/drums", table.unpack(drumstate({ track = 5, mute = { [3] = 1, [9] = 1 },
                                                 solo = { [5] = 1 } })))
equal("⛔ the state lights each track's M and S: tracks 3 and 9 muted, track 5 soloed, the rest out",
      { flags("mute"), flags("solo") }, { lit_at(3, 9), lit_at(5) })
check("... a lit one's letter black on its fill, an out one's white",
      black(C.mute3l.textColor) and black(C.solo5l.textColor) and not black(C.mute4l.textColor)
      and not black(C.solo3l.textColor), T.show({ C.mute3l.textColor, C.mute4l.textColor }))
check("... M red and S teal", red(C.mute4.color) and teal(C.solo4.color),
      T.show({ C.mute4.color, C.solo4.color }))
equal("⛔ lighting them sends nothing", #w.sent, 0)
equal("⛔ a tap on M 4, out, asks to mute track 4; on M 3, lit, to unmute track 3",
      { L.press(w, "mute4"), L.press(w, "mute3") },
      { { { "/cutit", "drums", "mute", 4, 1 } }, { { "/cutit", "drums", "mute", 3, 0 } } })
equal("⛔ ... and S the same: S 5, lit, asks for 0, S 16, out, for 1",
      { L.press(w, "solo5"), L.press(w, "solo16") },
      { { { "/cutit", "drums", "solo", 5, 0 } }, { { "/cutit", "drums", "solo", 16, 1 } } })
equal("⛔ a tap before the answer asks again for the same, not the other: M and S are the state's",
      L.press(w, "mute4"), { { "/cutit", "drums", "mute", 4, 1 } })
w.sent = {}
L.osc(w, "/cutit/drums", table.unpack(drumstate({ track = 5, mute = { [3] = 1, [9] = 1 },
                                                 solo = { [5] = 1 } })))
equal("⛔ the state's repeat lights again the ones a finger let go of, and sends nothing back",
      { flags("mute"), flags("solo"), #w.sent }, { lit_at(3, 9), lit_at(5), 0 })
L.osc(w, "/cutit/drums", table.unpack(drumstate({ track = 5, mute = { [4] = 1 } })))
equal("the answer: track 4 muted, 3 and 9 not, nothing soloed", { flags("mute"), flags("solo") },
      { lit_at(4), lit_at() })
local old98 = drumstate({ track = 5 })
while #old98 > 98 do table.remove(old98) end
L.osc(w, "/cutit/drums", table.unpack(old98))
equal("a 98-number state, from before mute and solo, leaves M and S as they were",
      { flags("mute"), flags("solo"), #w.sent }, { lit_at(4), lit_at(), 0 })
equal("⛔ a pad with its M and S under it still selects its track at a tap",
      L.tap(w, "pad3"), { { "/cutit", "drums", "select", 3 } })
L.drag(w, "show", 0)
L.drag(w, "fx", 0)
equal("sync and snap", { L.press(w, "sync")[1], L.press(w, "snap")[1] },
      { { "/cutit", "drums", "sync" }, { "/cutit", "drums", "snap" } })
w.sent = {}
L.osc(w, "/cutit/ack", "drums", "sync")
L.update(w)
check("sync's answer flashes it teal", teal(C.sync.color), T.show(C.sync.color))
equal("... by its color, so it sends nothing", #w.sent, 0)
L.update(w, 400)
check("... for a moment, then red again", red(C.sync.color), T.show(C.sync.color))
check("no tempo, drunkenness, time signature, alert, skip or move on the drum screen (Brendan, "
      .. "2026-11-04 and 2026-11-05)", (function()
        for _, c in ipairs(C.drums.children) do
          if ({ tempo = 1, drunk = 1, numbox = 1, alert = 1, skip = 1, move = 1 })[c.name] then
            return false
          end
        end
        return true
      end)(), "")

print("\n--- the synths screen ---")
mode("mode-3")
local function lamps()
  return { C.sfm.values.x, C.sstrings.values.x, C.cfm.values.x, C.cstrings.values.x }
end
w.sent = {}
L.osc(w, "/cutit/synth", "fm")
equal("c_synth's choice, fm: lit on the synths screen and the checklist page, strings not",
      lamps(), { 1, 0, 1, 0 })
check("... fm's labels black on the lit fill, strings' not",
      black(C.sfml.textColor) and black(C.cfml.textColor) and not black(C.sstringsl.textColor),
      T.show({ C.sfml.textColor, C.sstringsl.textColor }))
equal("lighting them sends nothing", #w.sent, 0)
equal("a tap on strings chooses it", L.press(w, "sstrings"), { { "/cutit", "synth", "strings" } })
equal("⛔ a tap on fm, chosen, sends nothing", L.press(w, "sfm"), {})
w.sent = {}
L.osc(w, "/cutit/synth", "strings")
equal("the answer, strings: strings lit, fm not, on both", lamps(), { 0, 1, 0, 1 })
L.osc(w, "/cutit/synth", "strings")
L.osc(w, "/cutit/synth", "strings")
equal("⛔ the choice lit, and again on each heartbeat's repeat, sends nothing back", #w.sent, 0)
equal("⛔ a tap on strings, lit, sends nothing", L.press(w, "sstrings"), {})
L.osc(w, "/cutit/synth", "strings")
equal("... and the repeat lights it again", lamps(), { 0, 1, 0, 1 })

print("\n--- the velocity switch ---")
w.sent = {}
L.osc(w, "/cutit/velocity", "on")
equal("velocity on: the switch lit, its label black, and nothing sent",
      { C.svel.values.x, black(C.svell.textColor), #w.sent }, { 1, true, 0 })
L.osc(w, "/cutit/velocity", "on")
L.osc(w, "/cutit/velocity", "on")
equal("⛔ its repeat on every heartbeat sends nothing back", #w.sent, 0)
equal("⛔ a tap on it lit asks for off, once", L.press(w, "svel"),
      { { "/cutit", "velocity", "off" } })
L.osc(w, "/cutit/velocity", "off")
equal("velocity off: the switch out, its label white", { C.svel.values.x, black(C.svell.textColor) },
      { 0, false })
equal("a tap on it out asks for on, once", L.press(w, "svel"), { { "/cutit", "velocity", "on" } })
equal("⛔ a tap before the answer asks again for on, not off: the switch is the state's",
      L.press(w, "svel"), { { "/cutit", "velocity", "on" } })
w.sent = {}
L.osc(w, "/cutit/velocity", "loud")
equal("a setting that is neither changes nothing", C.svel.values.x, 0)
L.osc(w, "/cutit/ack", "velocity", "on")
L.update(w)
check("its answer flashes it teal", teal(C.svel.color), T.show(C.svel.color))
equal("... by its color, so it sends nothing", #w.sent, 0)
L.update(w, 400)
check("... for a moment, then red again", red(C.svel.color), T.show(C.svel.color))
equal("not on the checklist page (Brendan, 2026-11-04)", C.cvel, nil)

print("\n--- the checklist page ---")
-- E is the checklist the gate built the page on, one with a step on several pages.
equal("step 1 of the checklist, its title",
      { L.text(w, "cpos"), L.text(w, "ctitle") }, { "1 of " .. E.steps, E.title })
equal("no Send button, and no checklist to pick: the page holds one, which sends nothing",
      { C.csend, C.cprev, C.cnext }, {})
equal("the page's FM chooses fm, so the line check can play the Volca",
      L.press(w, "cfm"), { { "/cutit", "synth", "fm" } })
L.osc(w, "/cutit/synth", "fm")
equal("... the answer lights it, here and on the synths screen", lamps(), { 1, 0, 1, 0 })
equal("⛔ ... and a tap on it then sends nothing", L.press(w, "cfm"), {})
equal("its STRINGS chooses strings, for the Streichfett", L.press(w, "cstrings"),
      { { "/cutit", "synth", "strings" } })
equal("none of them moved the step", L.text(w, "cpos"):find("^1 of ") ~= nil, true)
equal("Pass: the verdict, and on to the next step", L.press(w, "cpass"),
      { { "/cutit", "result", E.pass } })
check("... step 2", L.text(w, "cpos"):find("^2 of ") ~= nil, L.text(w, "cpos"))
L.press(w, "cback")
check("Back: the step just passed, marked passed", L.text(w, "cpos"):find("passed$") ~= nil,
      L.text(w, "cpos"))
L.osc(w, "/cutit/ack", "result")
L.update(w)
check("... and the answer to it flashes Pass", C.cpass.color[1] > 0.9 and C.cpass.color[2] > 0.9,
      T.show(C.cpass.color))
L.update(w, 400)
-- To a step, by the page's own button.
for _ = 1, 100 do
  if L.text(w, "cpos"):find("^" .. E.multi.si .. " of ") then break end
  L.press(w, "cfwd")
end
equal("a step on " .. E.multi.pages .. " pages shows its first",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.steps .. "   1/" .. E.multi.pages)
check("... its text, a line at a time", L.text(w, "cbody"):find("\n") ~= nil, L.text(w, "cbody"))
L.press(w, "cfwd")
equal("Next shows its second page before the next step",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.steps .. "   2/" .. E.multi.pages)
L.press(w, "cback")
equal("... and Back the first again",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.steps .. "   1/" .. E.multi.pages)
equal("Fail: its verdict", L.press(w, "cfail"), { { "/cutit", "result", E.multi.verdict } })
L.osc(w, "/cutit/ack", "result")
L.update(w)
check("... and its answer flashes Fail", C.cfail.color[1] > 0.9 and C.cfail.color[2] > 0.9,
      T.show(C.cfail.color))

print("\n--- the sections page ---")
mode("mode-7")
equal("page 7: the sections page, under its sections tab, and a name tab beside it",
      { where(), C.tabs7.children[2].tabLabel }, { { "p7", "sections" }, "name" })
w.sent = {}
-- u_song's 22 atoms: the song, how many, the selected, the page and pages, its name and length,
-- then five rows of number, name and length.
L.osc(w, "/cutit/sections", "song 1", 7, 3, 1, 2, "chorus", 0, 1, "intro", 8, 2, "verse", 1,
      3, "chorus", 0, 4, "verse 2", 16, 5, "bridge", 8)
equal("u_song's state: the caption names the song, the right column the selected section, the "
      .. "pager the page", { L.text(w, "secsong"), L.text(w, "secsel"), L.text(w, "secnewl"),
      L.text(w, "secpos"), L.text(w, "seclen") },
      { "sections of song 1", "section 3", "new, a copy of 3", "1 / 2", "loop" })
equal("... five rows, each its number, name and length: bars, a bar, or loop",
      { L.text(w, "row1nl"), L.text(w, "row1l"), L.text(w, "row1lenl"), L.text(w, "row2lenl"),
        L.text(w, "row3lenl"), L.text(w, "row4l") }, { "1", "intro", "8 bars", "1 bar", "loop",
      "verse 2" })
equal("⛔ the selected row is lit, by the state, and nothing goes back",
      { C.row3.values.x, C.row1.values.x, #w.sent }, { 1, 0, 0 })
check("... its words black on the lit fill, the others white and gray",
      black(C.row3l.textColor) and black(C.row3lenl.textColor) and not black(C.row1l.textColor),
      T.show({ C.row3l.textColor, C.row1l.textColor }))
equal("a row tapped selects the section it shows", L.press(w, "row2"),
      { { "/cutit", "sections", "select", 2 } })
equal("⛔ the selected row tapped sends nothing", L.press(w, "row3"), {})
L.osc(w, "/cutit/sections", "song 1", 7, 3, 2, 2, "chorus", 0, 6, "outro", 0, 7, "end", 4,
      0, "-", 0, 0, "-", 0, 0, "-", 0)
equal("the second page: two rows shown, the empty three hidden",
      { C.row1.visible, C.row2.visible, C.row3.visible, C.row5l.visible, L.text(w, "row1nl"),
        L.text(w, "row2l") }, { true, true, false, false, "6", "end" })
equal("... and a row with no section sends nothing", L.press(w, "row4"), {})
equal("the pager's arrows: a page back and a page on",
      { L.press(w, "secprev"), L.press(w, "secnext") },
      { { { "/cutit", "sections", "page", -1 } }, { { "/cutit", "sections", "page", 1 } } })
equal("new, move up, move down and delete, each its command",
      { L.press(w, "secnew"), L.press(w, "secup"), L.press(w, "secdown"), L.press(w, "secdel") },
      { { { "/cutit", "sections", "new" } }, { { "/cutit", "sections", "up" } },
        { { "/cutit", "sections", "down" } }, { { "/cutit", "sections", "delete" } } })
L.osc(w, "/cutit/ack", "sections", "new")
L.update(w)
check("an answer to new flashes it teal", teal(C.secnew.color), T.show(C.secnew.color))
L.update(w, 400)
check("... and it goes back to red", red(C.secnew.color), T.show(C.secnew.color))
L.update(w, 1100)
-- The state handed the length box loop, 0, in the middle of its step: 0.5 / 65.
equal("the length dragged up to 8 sends length 8, once", L.drag(w, "seclenbox", 8.5 / 65),
      { { "/cutit", "sections", "length", 8 } })
equal("... and down to loop sends length 0", L.drag(w, "seclenbox", 0.2 / 65),
      { { "/cutit", "sections", "length", 0 } })
L.update(w, 1100)
w.sent = {}
L.osc(w, "/cutit/sections", "song 1", 7, 3, 1, 2, "chorus", 12, 1, "intro", 8, 2, "verse", 1,
      3, "chorus", 12, 4, "verse 2", 16, 5, "bridge", 8)
equal("⛔ a length from the state shows, and is not sent back", { L.text(w, "seclen"), #w.sent },
      { "12 bars", 0 })

print("\n--- the name tab ---")
C.tabs7.values.page = 1
L.update(w)
equal("the name tab opens on the selected section's name, in capitals as the keys are",
      L.text(w, "snfieldl"), "CHORUS_")
for _ = 1, 7 do L.press(w, "snback") end
equal("backspace takes it back a character at a time, and no further than nothing",
      L.text(w, "snfieldl"), "_")
for _, k in ipairs({ "v", "e", "r", "s", "e", "space", "space", "2", "apos", "dash" }) do
  L.press(w, "snk" .. k)
end
equal("a key types its letter, a space one space at most, a digit, ' and -",
      L.text(w, "snfieldl"), "VERSE 2'-_")
L.press(w, "snback")
L.press(w, "snback")
equal("⛔ done sends the name, lowercase, as one string, and turns back to the sections tab",
      { L.press(w, "sndone"), where() },
      { { { "/cutit", "sections", "name", "verse 2" } }, { "p7", "sections" } })
L.osc(w, "/cutit/ack", "sections", "name")
L.update(w)
check("... its answer flashes done", C.sndone.color[1] > 0.9 and C.sndone.color[2] > 0.9,
      T.show(C.sndone.color))
C.tabs7.values.page = 1
L.update(w)
equal("opened again, it starts from the name in the state", L.text(w, "snfieldl"), "CHORUS_")
equal("⛔ done with the name unchanged sends nothing back, and turns back",
      { L.press(w, "sndone"), where() }, { {}, { "p7", "sections" } })
C.tabs7.values.page = 1
L.update(w)
for _ = 1, 30 do L.press(w, "snka") end
equal("a name is twenty characters at most", #L.text(w, "snfieldl"), 21)
for _ = 1, 25 do L.press(w, "snback") end
L.press(w, "snkspace")
equal("a leading space is not typed", L.text(w, "snfieldl"), "_")
equal("... and done with nothing typed sends nothing", L.press(w, "sndone"), {})

print("\n--- the songs page ---")
mode("mode-8")
equal("page 8: the songs page, under its songs tab, a setlists tab and a name tab beside it",
      { where(), C.tabs8.children[2].tabLabel, C.tabs8.children[3].tabLabel },
      { { "p8", "songs" }, "setlists", "name" })
-- u_song's 47 atoms: the songs tab's five and six rows, then the setlists tab's nine and five.
local function songsstate(t)
  local a = { t.count or 3, t.sel or 2, t.page or 1, t.pages or 1, t.name or "hollow bell" }
  local rows = t.rows or { { 1, "night drive", "loaded · unsaved" }, { 2, "hollow bell", "-" },
                           { 3, "lantern", "for go" } }
  for r = 1, 6 do
    for _, v in ipairs(rows[r] or { 0, "-", "-" }) do a[#a + 1] = v end
  end
  for _, v in ipairs(t.set or { 1, 3, "friday at the bell", 1, 2, 7, 3, "hollow bell", "go" }) do
    a[#a + 1] = v
  end
  local es = t.entries or { { 1, "lantern", "silence" }, { 2, "night drive", "next-bar" },
                            { 3, "hollow bell", "go" }, { 4, "undertow", "next-bar" },
                            { 5, "slow names", "silence" } }
  for r = 1, 5 do
    for _, v in ipairs(es[r] or { 0, "-", "-" }) do a[#a + 1] = v end
  end
  return a
end
w.sent = {}
L.osc(w, "/cutit/songs", table.unpack(songsstate({})))
equal("u_song's state: the selected song over the right column, the pager the page",
      { L.text(w, "gsel"), L.text(w, "gpos") }, { "hollow bell", "1 / 1" })
equal("... a row each, its number, name and what it is doing, nothing shown for none",
      { L.text(w, "grow1nl"), L.text(w, "grow1l"), L.text(w, "grow1wl"), L.text(w, "grow2wl"),
        L.text(w, "grow3wl"), C.grow4.visible, C.grow4l.visible },
      { "1", "night drive", "loaded · unsaved", "", "for go", false, false })
equal("⛔ the selected row is lit, by the state, and nothing goes back",
      { C.grow2.values.x, C.grow1.values.x, #w.sent }, { 1, 0, 0 })
equal("a row tapped selects the song it shows; the selected one, nothing",
      { L.press(w, "grow3"), L.press(w, "grow2") }, { { { "/cutit", "songs", "select", 3 } }, {} })
equal("load, new song and add to set, each its command; the pager's arrows a page each way",
      { L.press(w, "gload"), L.press(w, "gnew"), L.press(w, "gadd"), L.press(w, "gprev"),
        L.press(w, "gnext") },
      { { { "/cutit", "songs", "load" } }, { { "/cutit", "songs", "new" } },
        { { "/cutit", "songs", "add" } }, { { "/cutit", "songs", "page", -1 } },
        { { "/cutit", "songs", "page", 1 } } })
L.osc(w, "/cutit/ack", "songs", "load")
L.update(w)
check("an answer to load flashes it teal", teal(C.gload.color), T.show(C.gload.color))
L.update(w, 400)
check("... and it goes back to red", red(C.gload.color), T.show(C.gload.color))
equal("⛔ delete asks first: the first tap sends nothing, and it reads sure?",
      { L.press(w, "gdel"), (function() L.update(w) return L.text(w, "gdell") end)() },
      { {}, "sure?" })
equal("⛔ ... a second tap deletes", L.press(w, "gdel"), { { "/cutit", "songs", "delete" } })
L.update(w)
equal("... and it reads delete again", L.text(w, "gdell"), "delete")
L.press(w, "gdel")
L.update(w, 3100)
equal("⛔ a first tap left alone three seconds lapses: delete again, and the next tap only asks",
      { L.text(w, "gdell"), L.press(w, "gdel") }, { "delete", {} })
L.update(w, 3100)

print("\n--- the setlists tab ---")
C.tabs8.values.page = 1
L.update(w)
w.sent = {}
L.osc(w, "/cutit/songs", table.unpack(songsstate({})))
equal("the setlist chosen: its name over the rows, the pager the setlist and its page",
      { L.text(w, "lcap"), L.text(w, "lpos"), L.text(w, "lsel") },
      { "friday at the bell", "set 1 / 3   page 1 / 2", "3  hollow bell" })
equal("... each row its key, song and how it starts, in words",
      { L.text(w, "lrow1nl"), L.text(w, "lrow1l"), L.text(w, "lrow1sl"), L.text(w, "lrow2sl"),
        L.text(w, "lrow3sl") }, { "1", "lantern", "silence", "next bar", "go" })
equal("⛔ the selected entry lit; the starts switch handed its go, the third, and nothing sent",
      { C.lrow3.values.x, C.lrow1.values.x, C.lstarts.values.x, #w.sent }, { 1, 0, 2, 0 })
check("... go's word black on its lit segment, the others white",
      black(C.lstarts3l.textColor) and not black(C.lstarts1l.textColor),
      T.show({ C.lstarts3l.textColor, C.lstarts1l.textColor }))
equal("a row tapped selects the entry it shows", L.press(w, "lrow4"),
      { { "/cutit", "songs", "entry", 4 } })
equal("⛔ the switch dragged to next bar sends it, once", L.drag(w, "lstarts", 1),
      { { "/cutit", "songs", "starts", "next-bar" } })
L.update(w, 1100)
equal("move up, move down, new set, remove and the arrows, each its command",
      { L.press(w, "lup"), L.press(w, "ldown"), L.press(w, "lnewset"), L.press(w, "lrem"),
        L.press(w, "lprev"), L.press(w, "lnext") },
      { { { "/cutit", "songs", "up" } }, { { "/cutit", "songs", "down" } },
        { { "/cutit", "songs", "new-set" } }, { { "/cutit", "songs", "remove" } },
        { { "/cutit", "songs", "set", -1 } }, { { "/cutit", "songs", "set", 1 } } })
w.sent = {}
L.osc(w, "/cutit/songs", table.unpack(songsstate({ set = { 2, 3, "set 2", 1, 1, 0, 0, "-", "-" },
                                                    entries = {} })))
equal("⛔ an empty setlist: no rows, no entry, a one-page pager, and nothing sent",
      { C.lrow1.visible, L.text(w, "lsel"), L.text(w, "lpos"), #w.sent },
      { false, "no entry", "set 2 / 3", 0 })

print("\n--- the songs page's name tab ---")
C.tabs8.values.page = 2
L.update(w)
equal("opened from the setlists tab, it names the setlist chosen, from its name",
      { L.text(w, "gnwhat"), L.text(w, "gnfieldl") }, { "name the setlist", "SET 2_" })
for _ = 1, 5 do L.press(w, "gnback") end
for _, k in ipairs({ "g", "i", "g" }) do L.press(w, "gnk" .. k) end
equal("⛔ done sends songs set-name, and turns back to the setlists tab",
      { L.press(w, "gndone"), where() }, { { { "/cutit", "songs", "set-name", "gig" } },
      { "p8", "setlists" } })
C.tabs8.values.page = 0
L.update(w)
L.osc(w, "/cutit/songs", table.unpack(songsstate({})))
equal("the songs tab's name button opens it on the selected song",
      { L.press(w, "gname"), where(), L.text(w, "gnwhat"), L.text(w, "gnfieldl") },
      { {}, { "p8", "name" }, "name the song", "HOLLOW BELL_" })
L.press(w, "gnback")
L.press(w, "gnback")
L.press(w, "gnkn")
equal("⛔ done sends songs name, and turns back to the songs tab",
      { L.press(w, "gndone"), where() }, { { { "/cutit", "songs", "name", "hollow ben" } },
      { "p8", "songs" } })
L.osc(w, "/cutit/ack", "songs", "name")
L.update(w)
check("... its answer flashes done", C.gndone.color[1] > 0.9 and C.gndone.color[2] > 0.9,
      T.show(C.gndone.color))
L.update(w, 400)
C.tabs8.values.page = 2
L.update(w)
equal("opened from the songs tab's own tab bar, it names the song again",
      L.text(w, "gnwhat"), "name the song")
equal("... and done with the name unchanged sends nothing, and turns back",
      { L.press(w, "gndone"), where() }, { {}, { "p8", "songs" } })
mode("mode-7")
C.tabs7.values.page = 1
L.update(w)
equal("⛔ the sections page's name tab still names the section", { L.text(w, "snwhat"),
      L.text(w, "snfieldl") }, { "name the section", "CHORUS_" })
L.press(w, "snkx")
equal("... and its done still sends sections name", L.press(w, "sndone"),
      { { "/cutit", "sections", "name", "chorusx" } })

print("\n--- what the phone no longer shows ---")
w.sent = {}
L.osc(w, "/cutit/param", "bpm", 120, "(29)")
L.osc(w, "/cutit/status", "128-bpm")
L.osc(w, "/cutit/alert", 1, "fail", "c_synth", "bad-synth")
equal("⛔ a parameter, a status or an alert changes nothing and sends nothing: the OLED's",
      { L.text(w, "tempo"), #w.sent }, { "150", 0 })
equal("⛔ ... and nothing in the layout would show one", { C.pname, C.ralert, C.alert, C.salert },
      {})

print("\n--- the link ---")
L.update(w, 2000)
equal("two seconds with no heartbeat: no link everywhere, the lamps out",
      { L.text(w, "link"), L.text(w, "dlink"), L.text(w, "slink"), L.text(w, "seclink"),
        L.text(w, "glink"), L.text(w, "llink"), L.text(w, "tmode"), C.linkled.values.x,
        C.dlinkled.values.x, C.slinkled.values.x, C.seclinkled.values.x, C.glinkled.values.x,
        C.llinkled.values.x, C.tled.values.x },
      { "no link", "no link", "no link", "no link", "no link", "no link", "no link", 0, 0, 0, 0,
        0, 0, 0 })

print("\n--- a lit button's look is the state's ---")
-- Every button the state lights with notify('lit'), its script the shared one that keeps its look
-- the state's: pressed, it showed the finger, let go it went dark, and the state lit it again a
-- moment later, on, off, on (Brendan, 2026-11-05). Pressed now, out or lit, it shows what the
-- state said at every step. Last in the file: a press here sends, and moves the root's selection.
local lit = {}
for _, m in ipairs(manifest) do
  if m.script then
    local fh = io.open(dir .. "/" .. m.name .. ".lua")
    local src = fh and fh:read("a") or ""
    if fh then fh:close() end
    if src:find("local function show()", 1, true) then lit[#lit + 1] = m.name end
  end
end
table.sort(lit)
local flicker = {}
for _, name in ipairs(lit) do
  for _, v in ipairs({ 0, 1 }) do
    C[name]:notify("lit", v)
    local xs = L.looks(w, name)
    for _, x in ipairs(xs) do
      if x ~= v then flicker[#flicker + 1] = name .. " lit " .. v .. ": " .. table.concat(xs, " ") break end
    end
  end
end
check("the state's buttons: the M and S under every pad, both synths', the velocity switch's and "
      .. "the rows of the sections and songs lists, " .. #lit .. " in all", #lit >= 32 + 4 + 1 + 5,
      table.concat(lit, " "))
check("⛔ ... and pressed, out or lit, each shows the state's look at every step, never the "
      .. "finger's", #flicker == 0, table.concat(flicker, "; "))

os.exit(T.report() == 0)
