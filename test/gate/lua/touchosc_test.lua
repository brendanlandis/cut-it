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
local SCREENS = { "remote", "drums", "checks" }
local function tabs()
  local t = {}
  for i = 1, 4 do if L.visible(w, "tab" .. i) then t[#t + 1] = L.text(w, "tab" .. i) end end
  return t
end
local function hb(test) L.osc(w, "/cutit/hb", 1, test and 1 or 0) end
local function mode(m) L.osc(w, "/cutit/mode", "compose", m) end

print("\n--- the tabs, the mode and test mode ---")
equal("before any mode: the remote screen, its tabs remote and checklists",
      { L.showing(w, SCREENS), tabs() }, { "remote", { "remote", "checklists" } })
L.update(w)
equal("no heartbeat yet: NO-LINK, and the checklist pill says no link",
      { L.text(w, "rlink"), L.text(w, "pill") }, { "NO-LINK", "no link" })
hb(false)
L.update(w)
equal("a heartbeat: link, and the pill says test mode is off",
      { L.text(w, "rlink"), L.text(w, "pill") }, { "link", "test mode off" })
mode("mode-1")
equal("mode 1: the drum screen, its tabs drums and checklists, and the mode named",
      { L.showing(w, SCREENS), tabs(), L.text(w, "mode") },
      { "drums", { "drums", "checklists" }, "mode-1" })
L.press(w, "tab2t")
equal("a tap on the last tab: the checklists", L.showing(w, SCREENS), "checks")
L.press(w, "tab1t")
equal("... and on the first, the drums again", L.showing(w, SCREENS), "drums")
mode("mode-2")
equal("mode 2: the remote screen, its tabs remote and checklists",
      { L.showing(w, SCREENS), tabs() }, { "remote", { "remote", "checklists" } })
mode("mode-2")
L.press(w, "tab2t")
mode("mode-2")
equal("the same mode again, as u_net repeats it twice a second, leaves the tab alone",
      L.showing(w, SCREENS), "checks")
L.press(w, "tab1t")
hb(true)
L.update(w)
equal("test mode on: the checklists come up, and the pill says so",
      { L.showing(w, SCREENS), L.text(w, "pill") }, { "checks", "test mode on" })
mode("mode-1")
equal("... and stay up through a change of mode: the new mode's last tab",
      { L.showing(w, SCREENS), tabs() }, { "checks", { "drums", "checklists" } })
L.press(w, "tab1t")
hb(true)
equal("a heartbeat still saying test mode leaves a tab chosen by hand alone",
      L.showing(w, SCREENS), "drums")
hb(false)
equal("test mode off: the mode's first tab", L.showing(w, SCREENS), "drums")
L.press(w, "tab2t")
hb(false)
equal("... and once off, the heartbeat leaves the checklists alone", L.showing(w, SCREENS), "checks")
L.press(w, "tab1t")

print("\n--- the drum screen ---")
local st = { 1, 12, 2, 1 }
for t = 1, 16 do st[#st + 1] = (t == 3) and 5 or 12 end
for t = 1, 16 do st[#st + 1] = (t == 3) and 1 or 0 end
for _, v in ipairs({ 7, 8, 30, 20, 0 }) do st[#st + 1] = v end
L.osc(w, "/cutit/drums", table.unpack(st))
L.update(w)
equal("c_steps' state: playing, last 12, sync waits, 7/8, each pad's last step",
      { L.text(w, "play"), L.text(w, "glob"), L.text(w, "pending"), L.text(w, "num"),
        L.text(w, "den"), L.text(w, "pad1"), L.text(w, "pad3") },
      { "playing", "last 12", "sync waits for step 1", "7", "8", "12", "5" })
check("pad 2, selected, is dark; pad 3, with its own last step, amber",
      w.controls.pad2bg.color[1] < 0.3 and w.controls.pad3bg.color[2] > 0.7,
      T.show({ w.controls.pad2bg.color, w.controls.pad3bg.color }))
equal("the sliders take the state, and send nothing back",
      { w.controls.drunk.values.x, w.controls.skip.values.x, L.text(w, "drunkv"), #w.sent },
      { 0.3, 0.2, "drunk 30%", 0 })
equal("a drag sends whole percents, once each", L.drag(w, "drunk", 0.501),
      { { "/cutit", "drums", "drunk", 50 } })
equal("... and nothing when the percent does not change", L.drag(w, "drunk", 0.504), {})
L.update(w, 500)
L.osc(w, "/cutit/drums", table.unpack(st))
equal("the old state half a second later leaves the slider where the finger put it",
      w.controls.drunk.values.x, 0.504)
L.update(w, 1100)
st[39] = 50
L.osc(w, "/cutit/drums", table.unpack(st))
equal("... and once the state agrees, nothing is sent", #w.sent, 1)
equal("a pad tap selects its track", L.press(w, "tap5"), { { "/cutit", "drums", "select", 5 } })
equal("sync, snap and the time signature's buttons",
      { L.press(w, "synct")[1], L.press(w, "snapt")[1], L.press(w, "denpt")[1],
        L.press(w, "nummt")[1] },
      { { "/cutit", "drums", "sync" }, { "/cutit", "drums", "snap" },
        { "/cutit", "drums", "den", 1 }, { "/cutit", "drums", "num", -1 } })
L.osc(w, "/cutit/ack", "drums", "sync")
L.update(w)
check("sync's acknowledgment lights it", w.controls.syncbg.color[2] > 0.8 and
      w.controls.syncbg.color[1] < 0.6, T.show(w.controls.syncbg.color))
L.update(w, 400)
check("... for a moment", w.controls.syncbg.color[1] > 0.9, T.show(w.controls.syncbg.color))

print("\n--- the remote screen ---")
mode("mode-2")
L.osc(w, "/cutit/param", "bpm", 120, "(29)")
equal("a parameter: its name, and its value with the unit", { L.text(w, "rname"), L.text(w, "rvalue") },
      { "bpm", "120 (29)" })
L.osc(w, "/cutit/param", "volca-cc41", 64, "-")
equal("... and no unit when it is a dash", L.text(w, "rvalue"), "64")
L.osc(w, "/cutit/status", "120-bpm")
equal("the status, on both screens", { L.text(w, "rstatus"), L.text(w, "status") },
      { "120-bpm", "120-bpm" })
L.osc(w, "/cutit/alert", 1, "warn", "u_tempo", "bpm-out-of-range")
equal("an alert: its level, and its text, on both screens",
      { L.text(w, "ralvl"), L.text(w, "ralert"), L.text(w, "alert") },
      { "warn", "bpm-out-of-range", "bpm-out-of-range" })
L.osc(w, "/cutit/alert", 0, "none", "-", "-")
equal("... and none", { L.text(w, "ralvl"), L.text(w, "ralert") }, { "-", "no-alerts" })
equal("the four commands",
      { L.press(w, "rewiret")[1], L.press(w, "cleart")[1], L.press(w, "tvolcat")[1],
        L.press(w, "t404t")[1] },
      { { "/cutit", "re-wire" }, { "/cutit", "clear-alert" },
        { "/cutit", "test-note", "m_volca" }, { "/cutit", "test-note", "m_404" } })
L.osc(w, "/cutit/ack", "test-note", "m_404")
L.update(w)
check("test-404's acknowledgment lights it, and not test-volca",
      w.controls.t404bg.color[1] < 0.6 and w.controls.tvolcabg.color[1] > 0.9,
      T.show({ w.controls.t404bg.color, w.controls.tvolcabg.color }))

print("\n--- the checklist page ---")
L.press(w, "tab2t")
equal("the first checklist, step 1", { L.text(w, "cname"), L.text(w, "cpos") },
      { E.lists[1].name, "1 of " .. E.lists[1].steps })
L.press(w, "cnextt")
equal("the next checklist", L.text(w, "cname"), E.lists[2].name)
L.press(w, "cprevt")
L.press(w, "cprevt")
equal("back past the first: the last", L.text(w, "cname"), E.lists[#E.lists].name)
L.press(w, "cnextt")
-- To a checklist and step: from step 1 of the first, by the page's own buttons.
local function go(ci, si)
  L.press(w, "cnextt")
  for _ = 1, #E.lists do
    if L.text(w, "cname") == E.lists[ci].name then break end
    L.press(w, "cnextt")
  end
  for _ = 1, 100 do
    if L.text(w, "cpos"):find("^" .. si .. " of ") then break end
    L.press(w, "cnext2t")
  end
end
go(E.send.ci, E.send.si)
equal("the step with a Send line: its title", L.text(w, "ctitle"), E.send.title)
local got = L.press(w, "csendt")
equal("Send: one /cutit send a message, numbers as numbers", got, E.send.sent)
L.osc(w, "/cutit/ack", "test-off")
L.update(w)
check("refused, test mode off: Send flashes red", w.controls.csendbg.color[1] > 0.85 and
      w.controls.csendbg.color[2] < 0.6, T.show(w.controls.csendbg.color))
L.update(w, 400)
equal("Pass: the verdict, and on to the next step", L.press(w, "cpasst"),
      { { "/cutit", "result", E.send.verdict } })
check("... step " .. (E.send.si + 1), L.text(w, "cpos"):find("^" .. (E.send.si + 1) .. " of ") ~= nil,
      L.text(w, "cpos"))
L.press(w, "cbackt")
equal("Back: the step just passed, marked passed", L.text(w, "cmark"), "passed")
go(E.multi.ci, E.multi.si)
equal("a step on " .. E.multi.pages .. " pages shows its first",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "  1/" .. E.multi.pages)
L.press(w, "cnext2t")
equal("Next shows its second page before the next step",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "  2/" .. E.multi.pages)
L.press(w, "cbackt")
equal("... and Back the first again",
      L.text(w, "cpos"), E.multi.si .. " of " .. E.multi.steps .. "  1/" .. E.multi.pages)
equal("Fail: its verdict", L.press(w, "cfailt"), { { "/cutit", "result", E.multi.verdict } })

print("\n--- the link ---")
L.update(w, 2000)
equal("two seconds with no heartbeat: NO-LINK on every screen",
      { L.text(w, "rlink"), L.text(w, "link"), L.text(w, "pill") }, { "NO-LINK", "NO-LINK", "no link" })

os.exit(T.report() == 0)
