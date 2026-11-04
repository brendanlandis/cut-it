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
-- Where the phone is: the tab showing, and which screen the first tab holds.
local function where()
  return { C.pager.values.page, C.main.tabLabel, C.drums.visible and "drums" or "remote" }
end
local function teal(c) return c[2] > 0.7 and c[1] < 0.3 end
local function red(c) return c[1] > 0.9 and c[2] < 0.2 end

print("\n--- the tabs, the mode and test mode ---")
equal("before any mode: the first tab, the remote screen", where(), { 0, "remote", "remote" })
L.update(w)
equal("no heartbeat yet: no link, on both screens and the checklists",
      { L.text(w, "rlink"), L.text(w, "link"), L.text(w, "tmode") }, { "no link", "no link", "no link" })
hb(false)
L.update(w)
equal("a heartbeat: link, its lamps lit, and test mode off",
      { L.text(w, "rlink"), C.rlinkled.values.x, C.linkled.values.x, L.text(w, "tmode") },
      { "link", 1, 1, "test mode off" })
mode("mode-1")
equal("mode 1: the first tab holds the drum screen, and says drums", where(), { 0, "drums", "drums" })
C.pager.values.page = 1
mode("mode-1")
equal("the same mode again, as u_net repeats it twice a second, leaves the tab chosen alone",
      C.pager.values.page, 1)
mode("mode-2")
equal("mode 2: the first tab, holding the remote screen", where(), { 0, "remote", "remote" })
hb(true)
L.update(w)
equal("test mode on: the checklists come up, its lamp lit",
      { C.pager.values.page, L.text(w, "tmode"), C.tled.values.x }, { 1, "test mode on", 1 })
mode("mode-1")
equal("... and stay up through a change of mode", where(), { 1, "drums", "drums" })
C.pager.values.page = 0
hb(true)
equal("a heartbeat still saying test mode leaves a tab chosen by hand alone", C.pager.values.page, 0)
hb(false)
C.pager.values.page = 1
hb(false)
equal("test mode off, then the checklists chosen: the heartbeat leaves them alone",
      C.pager.values.page, 1)
hb(true)
hb(false)
equal("test mode going off: the first tab", C.pager.values.page, 0)

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
local sent = {}
for i, m in ipairs(w.sent) do sent[i] = table.concat(m, " ") end
equal("lighting the selected pad says select 2 again, which selects it again and nothing more",
      sent, { "/cutit drums select 2" })
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
equal("the four commands",
      { L.press(w, "rewire")[1], L.press(w, "clear")[1], L.press(w, "tvolca")[1],
        L.press(w, "t404")[1] },
      { { "/cutit", "re-wire" }, { "/cutit", "clear-alert" },
        { "/cutit", "test-note", "m_volca" }, { "/cutit", "test-note", "m_404" } })
L.osc(w, "/cutit/ack", "test-note", "m_404")
L.update(w)
check("test 404's answer flashes it, and not test Volca", teal(C.t404.color) and red(C.tvolca.color),
      T.show({ C.t404.color, C.tvolca.color }))

print("\n--- the checklist page ---")
C.pager.values.page = 1
equal("the first checklist, step 1", { L.text(w, "cname"), L.text(w, "cpos"):match("^%d+ of %d+") },
      { E.lists[1].name, "1 of " .. E.lists[1].steps })
L.press(w, "cnext")
equal("the next checklist", L.text(w, "cname"), E.lists[2].name)
L.press(w, "cprev")
L.press(w, "cprev")
equal("back past the first: the last", L.text(w, "cname"), E.lists[#E.lists].name)
-- To a checklist and step, by the page's own buttons.
local function go(ci, si)
  L.press(w, "cnext")
  for _ = 1, #E.lists do
    if L.text(w, "cname") == E.lists[ci].name then break end
    L.press(w, "cnext")
  end
  for _ = 1, 100 do
    if L.text(w, "cpos"):find("^" .. si .. " of ") then break end
    L.press(w, "cfwd")
  end
end
go(E.send.ci, E.send.si)
equal("the step with a Send line: its title, and Send showing",
      { L.text(w, "ctitle"), C.csend.visible }, { E.send.title, true })
equal("Send: one /cutit send a message, numbers as numbers", L.press(w, "csend"), E.send.sent)
L.osc(w, "/cutit/ack", "test-off")
L.update(w)
check("refused, test mode off: Send flashes grey", C.csend.color[1] > 0.4 and C.csend.color[1] < 0.7,
      T.show(C.csend.color))
L.update(w, 400)
equal("Pass: the verdict, and on to the next step", L.press(w, "cpass"),
      { { "/cutit", "result", E.send.verdict } })
check("... step " .. (E.send.si + 1), L.text(w, "cpos"):find("^" .. (E.send.si + 1) .. " of ") ~= nil,
      L.text(w, "cpos"))
L.press(w, "cback")
check("Back: the step just passed, marked passed", L.text(w, "cpos"):find("passed$") ~= nil,
      L.text(w, "cpos"))
go(E.nosend.ci, E.nosend.si)
equal("a step with no Send line hides Send", C.csend.visible, false)
go(E.multi.ci, E.multi.si)
equal("a step on " .. E.multi.pages .. " pages shows its first",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "   1/" .. E.multi.pages)
check("... its text, a line at a time", L.text(w, "cbody"):find("\n") ~= nil, L.text(w, "cbody"))
L.press(w, "cfwd")
equal("Next shows its second page before the next step",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "   2/" .. E.multi.pages)
L.press(w, "cback")
equal("... and Back the first again",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "   1/" .. E.multi.pages)
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
