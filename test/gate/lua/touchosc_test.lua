-- The phone's TouchOSC layout, its scripts run under lib_touchosc.lua's stand-in: the tabs and
-- the mode, test mode, the drum screen, the remote screen and the checklist page. Run by
-- touchosc-assert.py, which unpacks the layout into a folder and writes expect.lua beside it:
--
--   lua test/gate/lua/touchosc_test.lua <folder> [-v]

local T = dofile("test/gate/lua/lib_test.lua")
local L = dofile("test/gate/lua/lib_touchosc.lua")
local check, equal = T.check, T.equal
local dir = arg[1]
local E = dofile(dir .. "/expect.lua")
local w = L.load(dir)
local C = w.controls
local function hb(test) L.osc(w, "/cutit/hb", 1, test and 1 or 0) end
local function mode(m) L.osc(w, "/cutit/mode", "compose", m) end
-- Where the phone is: the tab's name, its screen, and whether the checklists stand in for it.
local function where()
  return { C.main.tabLabel, C.drums.visible and "drums" or "remote",
           (C.checkpager.visible and not C.pager.visible) and "checklists" or "tabs" }
end
local function teal(c) return c[2] > 0.7 and c[1] < 0.3 end
local function red(c) return c[1] > 0.9 and c[2] < 0.2 end

print("\n--- the tabs, the mode and test mode ---")
equal("before any mode: the tab, the remote screen", where(), { "remote", "remote", "tabs" })
L.update(w)
equal("no heartbeat yet: no link, on both screens and the checklists",
      { L.text(w, "rlink"), L.text(w, "link"), L.text(w, "tmode") }, { "no link", "no link", "no link" })
hb(false)
L.update(w)
equal("a heartbeat: link, its lamps lit, and test mode off",
      { L.text(w, "rlink"), C.rlinkled.values.x, C.linkled.values.x, L.text(w, "tmode") },
      { "link", 1, 1, "test mode off" })
mode("mode-1")
equal("mode 1: the tab holds the drum screen, and says drums", where(), { "drums", "drums", "tabs" })
mode("mode-2")
equal("mode 2: the remote screen", where(), { "remote", "remote", "tabs" })
hb(true)
L.update(w)
equal("test mode on: the checklist page in place of the tabs, its lamp lit",
      { where()[3], L.text(w, "tmode"), C.tled.values.x }, { "checklists", "test mode on", 1 })
mode("mode-1")
equal("... staying through a change of mode, which fills the tab behind it",
      where(), { "drums", "drums", "checklists" })
hb(true)
equal("a heartbeat still saying test mode changes nothing", where()[3], "checklists")
hb(false)
equal("test mode off: the tabs again", where(), { "drums", "drums", "tabs" })

print("\n--- the drum screen ---")
local st = { 1, 12, 2, 1 }
for t = 1, 16 do st[#st + 1] = (t == 3) and 5 or 12 end
for t = 1, 16 do st[#st + 1] = (t == 3) and 1 or 0 end
for _, v in ipairs({ 7, 8, 30, 20, 0 }) do st[#st + 1] = v end
L.osc(w, "/cutit/drums", table.unpack(st))
L.osc(w, "/cutit/status", "120-bpm")
L.update(w)
equal("c_steps' state: playing, last 12, sync waits, 7 / 8, the tempo from the status",
      { L.text(w, "play"), C.playled.values.x, L.text(w, "glob"), L.text(w, "pending"),
        L.text(w, "num"), L.text(w, "den"), L.text(w, "tempo") },
      { "playing", 1, "12", "sync waits for step 1", "7", "8", "120" })
equal("each pad shows its last step; pad 3, with its own, a dot before it",
      { L.text(w, "pad1l"), L.text(w, "pad3l") }, { "12", "\u{2022} 5" })
check("pad 3 is teal, pad 1 red", teal(C.pad3.color) and red(C.pad1.color),
      T.show({ C.pad3.color, C.pad1.color }))
equal("pad 2, selected, is lit and the rest not",
      { C.pad2.values.x, C.pad1.values.x, C.pad3.values.x }, { 1, 0, 0 })
equal("lighting the selected pad sends nothing", #w.sent, 0)
-- four pads pressed at once: four states, a track each, as fast as they come
for _, t in ipairs({ 11, 12, 15, 16 }) do
  st[3] = t
  L.osc(w, "/cutit/drums", table.unpack(st))
end
equal("states selecting one track after another light each in turn and send nothing back",
      { C.pad16.values.x, C.pad11.values.x, #w.sent }, { 1, 0, 0 })
st[3] = 2
L.osc(w, "/cutit/drums", table.unpack(st))
w.sent = {}
equal("the knobs and boxes take the state, and send nothing back",
      { C.drunk.values.x, C.skip.values.x, L.text(w, "drunkv"), #w.sent },
      { 0.3, 0.2, "30%", 0 })
equal("a turn of a knob sends whole percents, once each", L.drag(w, "drunk", 0.501),
      { { "/cutit", "drums", "drunk", 50 } })
equal("... and nothing when the percent does not change", L.drag(w, "drunk", 0.504), {})
L.update(w, 500)
L.osc(w, "/cutit/drums", table.unpack(st))
equal("the old state half a second later leaves the knob where the finger put it",
      C.drunk.values.x, 0.504)
L.update(w, 1100)
st[39] = 50
L.osc(w, "/cutit/drums", table.unpack(st))
equal("... and once the state agrees, nothing more is sent", #w.sent, 1)
w.sent = {}
-- the boxes: the state put 7 in the middle of its step, 6.5 / 32
equal("dragging 7 up two steps sends num 1 twice", L.drag(w, "numbox", 8.5 / 32),
      { { "/cutit", "drums", "num", 1 }, { "/cutit", "drums", "num", 1 } })
equal("dragging 8 down one step, of 1 2 4 8 16, sends den -1", L.drag(w, "denbox", 2.5 / 5),
      { { "/cutit", "drums", "den", -1 } })
equal("a pad tap selects its track", L.press(w, "pad5"), { { "/cutit", "drums", "select", 5 } })
equal("sync and snap", { L.press(w, "sync")[1], L.press(w, "snap")[1] },
      { { "/cutit", "drums", "sync" }, { "/cutit", "drums", "snap" } })
w.sent = {}
L.osc(w, "/cutit/ack", "drums", "sync")
L.update(w)
check("sync's answer flashes it teal", teal(C.sync.color), T.show(C.sync.color))
equal("... by its color, so it sends nothing", #w.sent, 0)
L.update(w, 400)
check("... for a moment, then red again", red(C.sync.color), T.show(C.sync.color))

print("\n--- the remote screen ---")
mode("mode-2")
L.osc(w, "/cutit/param", "bpm", 120, "(29)")
equal("a parameter: its name, and its value with the unit",
      { L.text(w, "pname"), L.text(w, "pvalue") }, { "bpm", "120 (29)" })
L.osc(w, "/cutit/param", "volca-cc41", 64, "-")
equal("... and no unit when it is a dash", L.text(w, "pvalue"), "64")
equal("the tempo from the status", L.text(w, "rstatus"), "120 bpm")
L.osc(w, "/cutit/alert", 1, "warn", "u_tempo", "bpm-out-of-range")
equal("an alert: its level and text, its lamp lit, and the text on the drum screen too",
      { L.text(w, "ralert"), C.ralertled.values.x, L.text(w, "alert") },
      { "warn  bpm-out-of-range", 1, "bpm-out-of-range" })
L.osc(w, "/cutit/alert", 0, "none", "-", "-")
equal("... and none", { L.text(w, "ralert"), C.ralertled.values.x }, { "no alerts", 0 })
equal("the three commands, and no test 404 since the SP-404 left the rig",
      { L.press(w, "rewire")[1], L.press(w, "clear")[1], L.press(w, "tvolca")[1], C.t404 },
      { { "/cutit", "re-wire" }, { "/cutit", "clear-alert" },
        { "/cutit", "test-note", "m_volca" } })
L.osc(w, "/cutit/ack", "test-note", "m_volca")
L.update(w)
check("test Volca's answer flashes it, and not re-wire or clear alert",
      teal(C.tvolca.color) and red(C.rewire.color) and red(C.clear.color),
      T.show({ C.tvolca.color, C.rewire.color, C.clear.color }))

print("\n--- the checklist page ---")
-- E is the checklist the gate built the page on, one with a step on several pages.
equal("step 1 of the checklist, its title",
      { L.text(w, "cpos"), L.text(w, "ctitle") }, { "1 of " .. E.steps, E.title })
equal("no Send button, and no checklist to pick: the page holds one, which sends nothing",
      { C.csend, C.cprev, C.cnext }, {})
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

print("\n--- the link ---")
L.update(w, 2000)
equal("two seconds with no heartbeat: no link everywhere, the lamps out",
      { L.text(w, "rlink"), L.text(w, "link"), L.text(w, "tmode"), C.linkled.values.x,
        C.tled.values.x },
      { "no link", "no link", "no link", 0, 0 })

os.exit(T.report() == 0)
