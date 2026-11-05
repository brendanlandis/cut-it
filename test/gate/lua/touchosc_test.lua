-- The phone's TouchOSC layout, its scripts run under lib_touchosc.lua's stand-in: the pages and
-- the mode, test mode, the arrangement screen, the drum screen, the synths screen and the
-- checklist page. Run by touchosc-assert.py, which unpacks the layout into a folder and writes
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
-- The state c_steps sends: 42 numbers, from what differs.
local function drumstate(t)
  local st = { t.playing or 0, t.last or 16, t.track or 1, t.pending or 0 }
  for n = 1, 16 do st[#st + 1] = (t.lasts or {})[n] or t.last or 16 end
  for n = 1, 16 do st[#st + 1] = (t.owns or {})[n] or 0 end
  for _, v in ipairs({ t.num or 4, t.den or 4, t.drunk or 0, t.skip or 0, t.move or 0,
                       t.swing or 50 }) do st[#st + 1] = v end
  return st
end

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
      { L.text(w, "link"), L.text(w, "dlink"), L.text(w, "slink"), L.text(w, "tmode") },
      { "no link", "no link", "no link", "no link" })
hb(false)
L.update(w)
equal("a heartbeat: link, its lamps lit, and test mode off",
      { L.text(w, "link"), C.linkled.values.x, C.dlinkled.values.x, C.slinkled.values.x,
        L.text(w, "tmode") }, { "link", 1, 1, 1, "test mode off" })
local TABS = { "arrangement", "drums", "synths", "page 4", "page 5", "page 6", "page 7", "songs" }
for n, tab in ipairs(TABS) do
  mode("mode-" .. n)
  equal("page " .. n .. ": the Launchpad's page " .. n .. ", its one tab named " .. tab, where(),
        { "p" .. n, tab })
end
mode("mode-2")
w.sent = {}
mode("mode-2")
equal("the mode's repeat turns nothing and sends nothing", { where(), #w.sent },
      { { "p2", "drums" }, 0 })
equal("⛔ pages 4 to 7 and songs are blank", { #C.page4.children, #C.page7.children,
      #C.songs.children }, { 0, 0, 0 })
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
      { (62 - 25) / 50, "62%", 0.3, "30%" })
equal("⛔ taking the state sends nothing back", #w.sent, 0)
equal("a turn of swing sends set-swing in whole percents, 25 to 75",
      L.drag(w, "swing", (70 - 25) / 50), { { "/cutit", "drums", "set-swing", 70 } })
equal("a turn of drunk sends whole percents, once each", L.drag(w, "drunk", 0.501),
      { { "/cutit", "drums", "drunk", 50 } })
equal("... and nothing when the percent does not change", L.drag(w, "drunk", 0.504), {})
equal("dragging the last step from 12 to 14 sends set-last 14",
      L.drag(w, "lastbox", (13 + 0.5) / 32), { { "/cutit", "drums", "set-last", 14 } })
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
table.remove(short)
L.osc(w, "/cutit/drums", table.unpack(short))
equal("fewer than 42 numbers draws nothing", L.text(w, "play"), "playing")

print("\n--- the drum screen ---")
mode("mode-2")
w.sent = {}
local st = drumstate({ playing = 1, last = 12, track = 2, pending = 1, lasts = { [3] = 5 },
                       owns = { [3] = 1 }, skip = 20 })
L.osc(w, "/cutit/drums", table.unpack(st))
L.update(w)
equal("a sync pending says so", L.text(w, "pending"), "sync waits for step 1")
equal("each pad shows its last step; pad 3, with its own, a dot before it",
      { L.text(w, "pad1l"), L.text(w, "pad3l") }, { "12", "\u{2022} 5" })
check("pad 3 is teal, pad 1 red", teal(C.pad3.color) and red(C.pad1.color),
      T.show({ C.pad3.color, C.pad1.color }))
equal("pad 2, selected, is lit and the rest not",
      { C.pad2.values.x, C.pad1.values.x, C.pad3.values.x }, { 1, 0, 0 })
equal("the selected track's skip and move take theirs", { C.skip.values.x, C.move.values.x },
      { 0.2, 0 })
equal("lighting the selected pad sends nothing", #w.sent, 0)
-- four pads pressed at once: four states, a track each, as fast as they come
for _, t in ipairs({ 11, 12, 15, 16 }) do
  st[3] = t
  L.osc(w, "/cutit/drums", table.unpack(st))
end
equal("states selecting one track after another light each in turn and send nothing back",
      { C.pad16.values.x, C.pad11.values.x, #w.sent }, { 1, 0, 0 })
equal("a pad tap selects its track", L.press(w, "pad5"), { { "/cutit", "drums", "select", 5 } })
equal("sync and snap", { L.press(w, "sync")[1], L.press(w, "snap")[1] },
      { { "/cutit", "drums", "sync" }, { "/cutit", "drums", "snap" } })
equal("skip's knob sends skip", L.drag(w, "skip", 0.4), { { "/cutit", "drums", "skip", 40 } })
w.sent = {}
L.osc(w, "/cutit/ack", "drums", "sync")
L.update(w)
check("sync's answer flashes it teal", teal(C.sync.color), T.show(C.sync.color))
equal("... by its color, so it sends nothing", #w.sent, 0)
L.update(w, 400)
check("... for a moment, then red again", red(C.sync.color), T.show(C.sync.color))
check("no tempo, drunkenness, time signature or alert on the drum screen (Brendan, 2026-11-04)",
      (function()
        for _, c in ipairs(C.drums.children) do
          if ({ tempo = 1, drunk = 1, numbox = 1, alert = 1 })[c.name] then return false end
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
      { L.text(w, "link"), L.text(w, "dlink"), L.text(w, "slink"), L.text(w, "tmode"),
        C.linkled.values.x, C.dlinkled.values.x, C.slinkled.values.x, C.tled.values.x },
      { "no link", "no link", "no link", "no link", 0, 0, 0, 0 })

os.exit(T.report() == 0)
