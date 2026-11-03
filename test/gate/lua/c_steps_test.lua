-- The sequencer's rules, without Pd: "Cut It/c_steps.lua", and the Pd face that carries them,
-- "Cut It/c_steps-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The sequencer
-- gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/c_steps_test.lua [-v]
--
-- What the patch does with these answers -- the notes on the clock, the page, the disk -- is
-- sequencer-assert.py's, on a running copy of the instrument. ref/module/sequencer.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "c_steps.lua")
local check, equal = T.check, T.equal

local LEVELS = { 16, 32, 48, 64, 79, 95, 111, 127 }
local CELLS = 16 * 32

local function zeros(n)
  local z = {}
  for i = 1, n do z[i] = 0 end
  return z
end

-- The selected track's row as the page gets it, from a pattern.
local function row(pat, track)
  local r = {}
  for s = 1, 32 do r[s] = pat[(track - 1) * 32 + s] end
  return r
end

-- The saved line: 512 velocities, then the 16 tracks' own last steps.
local function line(pat, own)
  local l = {}
  for i = 1, CELLS do l[i] = pat[i] end
  for t = 1, 16 do l[CELLS + t] = own and own[t] or 0 end
  return l
end

-- What a step press answers: the whole pattern to save, then the selected track's row.
local function edited(pat, track, own)
  return { { "save", "list", line(pat, own) }, { "page", "steps", row(pat, track) } }
end

-- A knob position for a step: what R.knob_step reads back as n.
local function at(n) return (n - 1) / 31 end

-- The playhead and the pads that sound on each of n ticks.
local function run(st, n)
  local out = {}
  for _ = 1, n do
    local pads, head = {}, nil
    for _, e in ipairs(R.internal.tick(st, {})) do
      if e[1] == "note" then pads[#pads + 1] = e[3][1] .. "@" .. e[3][2] end
      if e[1] == "page" then head = e[3][1] end
    end
    out[#out + 1] = head .. ":" .. table.concat(pads, ",")
  end
  return table.concat(out, " ")
end

print("\n--- the velocity levels ---")
local got = {}
for n = 1, 8 do got[n] = R.velocity(n) end
equal("level n is round(127n/8): 16 32 48 ... 111 127", got, LEVELS)
check("... and every one is a whole number", (function()
  for n = 1, 8 do if math.type(R.velocity(n)) ~= "integer" then return false end end
  return true
end)(), T.show(got))

print("\n--- at load ---")
local st = R.new(1)
equal("a new sequencer holds 512 zeros, every track following the global last step",
      { st.pattern, st.own }, { zeros(CELLS), zeros(16) })
equal("... and starts on track 1 at level 6, the last step 16", { st.track, st.level, st.last },
      { 1, 6, 16 })
equal("init draws the selection: vel 6, track 1, last 16, then track 1's 32 steps",
      R.internal.init(st, {}), { { "page", "vel", { 6 } }, { "page", "track", { 1 } },
                                 { "page", "last", { 16 } }, { "page", "steps", zeros(32) } })
equal("the bank is clipped to 1..10, as [clip 1 10]",
      { R.new(0).bank, R.new(11).bank, R.new(nil).bank, R.new(3).bank }, { 1, 10, 1, 3 })

print("\n--- the step rule ---")
st = R.new(1)
equal("a velocity press selects its level and answers only vel 2",
      R.presses.vel(st, { 2, 100 }), { { "page", "vel", { 2 } } })
equal("... and changes no step", st.pattern, zeros(CELLS))
local want = zeros(CELLS)
want[5] = 32
equal("an off step takes the selected velocity -- 32 -- saved whole, then redrawn",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
want[5] = 0
equal("the same step at the same velocity turns off -- 0",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
R.presses.step(st, { 5, 100 })
R.presses.vel(st, { 6, 100 })
equal("an on step at another velocity turns off too -- 0, not 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
st.pattern[5] = 0.5
want[5] = 95
equal("a rest below 1 is off: a press gives it the selected velocity -- 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
equal("a step past the last step is dark, and a press there does nothing -- step 17",
      R.presses.step(st, { 17, 100 }), {})

print("\n--- the selected track ---")
st = R.new(1)
equal("a pad press plays its pad now, selects its track, and draws its last step and row",
      R.presses.pad(st, { 2, 90 }), { { "note", "pad", { 2, 90 } }, { "page", "track", { 2 } },
                                      { "page", "last", { 16 } }, { "page", "steps", zeros(32) } })
R.presses.step(st, { 1, 100 })
want = zeros(CELLS)
want[33] = R.velocity(6)
equal("a step press edits the SELECTED track -- track 2's step 1, track 1 untouched",
      st.pattern, want)
local st3 = R.new(3)
equal("bank C's track 2 is pad 34", R.presses.pad(st3, { 2, 90 })[1],
      { "note", "pad", { 34, 90 } })
equal("pads are clipped to 1..16 and levels to 1..8",
      { R.presses.pad(R.new(1), { 0, 90 })[1], R.presses.pad(R.new(1), { 20, 90 })[1],
        R.presses.vel(R.new(1), { 40, 0 })[1] },
      { { "note", "pad", { 1, 90 } }, { "note", "pad", { 16, 90 } }, { "page", "vel", { 8 } } })
equal("a press or a knob with no number in it does nothing",
      { R.presses.step(R.new(1), {}), R.presses.vel(R.new(1), {}), R.presses.pad(R.new(1), {}),
        R.presses.last(R.new(1), {}), R.presses["track-last"](R.new(1), {}) },
      { {}, {}, {}, {}, {} })

print("\n--- knob 2, the global last step ---")
equal("a knob's 0-1 is a step from 1 to 32, 16 just left of noon",
      { R.knob_step(0), R.knob_step(at(16)), R.knob_step(0.5), R.knob_step(1), R.knob_step(7) },
      { 1, 16, 17, 32, 32 })
st = R.new(1)
equal("⛔ at load it is HELD at 16: a knob at step 7 draws the held row and changes nothing",
      R.presses.last(st, { at(7) }), { { "disp", "last-step", { 16, "(7)" } } })
equal("... still held further below", R.presses.last(st, { at(3) }),
      { { "disp", "last-step", { 16, "(3)" } } })
equal("passing 16 releases it, at the step it reached -- 18",
      R.presses.last(st, { at(18) }), { { "disp", "last-step", { 18 } },
                                       { "page", "last", { 18 } } })
equal("... and it is live from then on", R.presses.last(st, { at(4) }),
      { { "disp", "last-step", { 4 } }, { "page", "last", { 4 } } })
st = R.new(1)
equal("reaching 16 exactly releases it too", R.presses.last(st, { at(16) }),
      { { "disp", "last-step", { 16 } }, { "page", "last", { 16 } } })
check("the global last step is not saved: no put", (function()
  for _, e in ipairs(R.presses.last(st, { at(9) })) do if e[1] == "save" then return false end end
  return true
end)(), "")

print("\n--- knob 3, the selected track's own last step ---")
st = R.new(1)
R.presses.pad(st, { 2, 90 })
equal("held at the selected track's last step, 16: a knob at 7 changes nothing",
      R.presses["track-last"](st, { at(7) }), { { "disp", "pad2-last", { 16, "(7)" } } })
equal("passing 16 releases it: track 2 gets its own last step, saved, and the page shows it",
      R.presses["track-last"](st, { at(20) }),
      { { "disp", "pad2-last", { 20 } }, { "save", "list", line(zeros(CELLS), { 0, 20 }) },
        { "page", "last", { 20 } } })
equal("... the other tracks still follow the global one", { R.last_of(st, 1), R.last_of(st, 2) },
      { 16, 20 })
equal("⛔ selecting another track holds the knob again, at THAT track's last step",
      { R.presses.pad(st, { 3, 90 })[3], R.presses["track-last"](st, { at(20) }) },
      { { "page", "last", { 16 } }, { { "disp", "pad3-last", { 16, "(20)" } } } })
st = R.new(1)
R.presses["track-last"](st, { at(16) })
equal("released AT the track's last step, a track following the global one keeps following",
      { st.own[1], R.presses["track-last"](st, { at(16) }) },
      { 0, { { "disp", "pad1-last", { 16 } } } })
st = R.new(1)
R.presses["track-last"](st, { at(16) })
R.presses["track-last"](st, { at(10) })
R.presses.last(st, { at(16) })
equal("knob 2 moves the global last step for every track but the ones with their own",
      { R.presses.last(st, { at(24) })[2], R.last_of(st, 1), R.last_of(st, 2) },
      { nil, 10, 24 })
st = R.new(1)
R.presses.last(st, { at(16) })
R.presses["track-last"](st, { at(16) })
R.presses.last(st, { at(12) })
equal("⛔ ... and when the selected track follows it, knob 3 is held again, at the new one",
      R.presses["track-last"](st, { at(20) }), { { "disp", "pad1-last", { 12, "(20)" } } })

print("\n--- sync and snap, from the drum screen ---")
equal("sync and snap answer nothing at once: they wait for the global loop's step 1",
      { R.presses.sync(R.new(1), {}), R.presses.snap(R.new(1), {}) }, { {}, {} })

print("\n--- the loops ---")
st = R.new(1)
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 3, 100 })
R.presses.pad(st, { 2, 90 })
R.presses["track-last"](st, { at(4) })
R.presses["track-last"](st, { at(6) })
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 6, 100 })
R.internal.start(st, {})
equal("⛔ each track loops on its own: track 1 every 4, track 2 every 6, the playhead track 2's",
      run(st, 13), "1:1@95,2@95 2: 3:1@95 4: 5:1@95 6:2@95 1:1@95,2@95 2: 3:1@95 4: 5:1@95 6:2@95 "
        .. "1:1@95,2@95")
R.internal.start(st, {})
equal("PLAY starts every loop at step 1 again", run(st, 2), "1:1@95,2@95 2:")
R.presses.sync(st, {})
equal("⛔ sync waits for the global loop's step 1, then every track is back at its own",
      run(st, 6), "3:1@95 4: 1:1@95,2@95 2: 3:1@95 4:")
equal("... each keeping its own last step", { R.last_of(st, 1), R.last_of(st, 2) }, { 4, 6 })
R.internal.start(st, {})
run(st, 2)
R.presses.snap(st, {})
equal("snap waits for the global loop's step 1 too", run(st, 2), "3:1@95 4:")
local landed = R.internal.tick(st, {})
equal("⛔ ... and there every track takes the global last step, saved, and plays from step 1",
      { landed[1][1], landed[1][3][CELLS + 2], landed[2], landed[3], landed[4], landed[5] },
      { "save", 0, { "page", "last", { 4 } }, { "note", "pad", { 1, 95 } },
        { "note", "pad", { 2, 95 } }, { "page", "play", { 1 } } })
equal("... and goes round the global loop from then on", run(st, 4), "2: 3:1@95 4: 1:1@95,2@95")
st = R.new(1)
R.presses["track-last"](st, { at(16) })
R.presses["track-last"](st, { at(9) })
R.presses.snap(st, {})
equal("a snap while stopped lands at PLAY", R.internal.start(st, {}),
      { { "save", "list", line(zeros(CELLS)) }, { "page", "last", { 16 } } })
equal("STOP puts the playhead out", R.internal.stop(st, {}), { { "page", "play", { 0 } } })
st = R.new(1)
R.internal.start(st, {})
run(st, 10)
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
equal("a loop shortened under its place wraps into it at once -- 10 in 4 is 3", run(st, 2), "3: 4:")
R.presses.step(st, { 2, 100 })
equal("... and goes round it from there", run(st, 2), "1: 2:1@95")

print("\n--- the restore ---")
st = R.new(1)
local pat = zeros(CELLS)
pat[3], pat[9], pat[39], pat[CELLS] = 20, 77, 50, 127
local own = zeros(16)
own[2], own[16] = 6, 24
equal("a restore takes the 512 and the 16 last steps, puts them straight back and redraws",
      R.internal.restore(st, line(pat, own)),
      { { "save", "list", line(pat, own) }, { "page", "last", { 16 } },
        { "page", "steps", row(pat, 1) } })
equal("... and the pattern and the last steps are the line's", { st.pattern, st.own }, { pat, own })
local old = zeros(256)
old[3], old[16], old[17], old[256] = 20, 99, 77, 127
st = R.new(1)
R.internal.restore(st, old)
want = zeros(CELLS)
want[3], want[16], want[33], want[16 * 32 - 16] = 20, 99, 77, 127
equal("⛔ a line of 256 is the old 16-step pattern: each track's sixteen go to its first sixteen",
      st.pattern, want)
st = R.new(1)
st.pattern[200] = 5
R.internal.restore(st, { 1, 2, "x" })
want = zeros(CELLS)
want[1], want[2], want[200] = 1, 2, 5
equal("a short line sets what it holds, a symbol as 0, and leaves the rest", st.pattern, want)
local long = zeros(600)
long[CELLS + 3] = 40
R.internal.restore(st, long)
equal("a long line stops at the 16 last steps, each clipped to 0..32",
      { #st.pattern, st.own[3], #st.own }, { CELLS, 32, 16 })
equal("an empty restore changes nothing and still puts the pattern back",
      R.internal.restore(R.new(1), {})[1], { "save", "list", line(zeros(CELLS)) })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_steps-lua.pd_lua", DIR)
check("c_steps-lua.pd_lua registers the class c_steps-lua", class and class._name == "c_steps-lua",
      class and class._name)
local o = T.new(class, { 1 })
check("an object has two inlets and six outlets", o and o.inlets == 2 and o.outlets == 6,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the page's selection on outlet 2, then the bang on outlet 5 that says it loaded",
      T.send(o, 2, "init", {}), { { 2, "vel", { 6 } }, { 2, "track", { 1 } }, { 2, "last", { 16 } },
                                  { 2, "steps", zeros(32) }, { 5, "bang", {} } })
equal("knob 2 held: its row on outlet 6", T.send(o, 1, "last", { at(9) }),
      { { 6, "last-step", { 16, "(9)" } } })
local sent = T.send(o, 1, "step", { 1, 100 })
want = zeros(CELLS)
want[1] = 95
equal("a step press: the pattern on outlet 3, then the page on outlet 2",
      sent, { { 3, "list", line(want) }, { 2, "steps", row(want, 1) } })
T.send(o, 2, "start", {})
equal("a tick: its notes on outlet 1, then the playhead on outlet 2", T.send(o, 2, "tick", {}),
      { { 1, "pad", { 1, 95 } }, { 2, "play", { 1 } } })
equal("sync from the drum screen, on inlet 1: nothing at once", T.send(o, 1, "sync", {}), {})
for _, m in ipairs({ { 1, "float", { 3 } }, { 1, "beat", { 1 } }, { 1, "tick", {} },
                     { 2, "step", { 1, 100 } }, { 2, "fire", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail c_steps bad-selector on outlet 4", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 4, "fail", { "c_steps", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose tick throws: the class reads its rules as
-- prefix .. "c_steps.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-c_steps.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'c_steps.lua")\n',
         'R.internal.tick = function() error("a bug in tick") end\nreturn R\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "c_steps-lua.pd_lua", tmp .. "-"), { 1 })
os.remove(tmp .. "-c_steps.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 4 as fail c_steps lua-tick, for the error log",
      T.send(broken, 2, "tick", {}), { { 4, "fail", { "c_steps", "lua-tick" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in tick", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a press still answers",
      T.send(broken, 1, "vel", { 2, 0 }), { { 2, "vel", { 2 } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
