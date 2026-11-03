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

local function zeros(n)
  local z = {}
  for i = 1, n do z[i] = 0 end
  return z
end

-- The selected track's row as the page gets it, from a pattern.
local function row(pat, track)
  local r = {}
  for s = 1, 16 do r[s] = pat[(track - 1) * 16 + s] end
  return r
end

-- What a step press answers: the whole pattern to save, then the selected track's row.
local function edited(pat, track)
  return { { "save", "list", pat }, { "page", "steps", row(pat, track) } }
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
equal("a new sequencer holds 256 zeros", st.pattern, zeros(256))
equal("... and starts on track 1 at level 6, all sixteen steps played",
      { st.track, st.level, st.last }, { 1, 6, 16 })
equal("init draws the selection: vel 6, track 1, last 16, then track 1's steps",
      R.internal.init(st, {}), { { "page", "vel", { 6 } }, { "page", "track", { 1 } },
                                 { "page", "last", { 16 } }, { "page", "steps", zeros(16) } })
equal("the bank is clipped to 1..10, as [clip 1 10]",
      { R.new(0).bank, R.new(11).bank, R.new(nil).bank, R.new(3).bank }, { 1, 10, 1, 3 })

print("\n--- the step rule ---")
st = R.new(1)
equal("a velocity press selects its level and answers only vel 2",
      R.presses.vel(st, { 2, 100 }), { { "page", "vel", { 2 } } })
equal("... and changes no step", st.pattern, zeros(256))
local want = zeros(256)
want[5] = 32
equal("an off step takes the selected velocity -- 32 -- saved whole, then redrawn",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
want[5] = 0
equal("the same step at the same velocity turns off -- 0",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
R.presses.step(st, { 5, 100 })
R.presses.vel(st, { 6, 100 })
want[5] = 0
equal("an on step at another velocity turns off too -- 0, not 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
st.pattern[5] = 0.5
want[5] = 95
equal("a rest below 1 is off: a press gives it the selected velocity -- 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))

print("\n--- the selected track ---")
st = R.new(1)
equal("a pad press plays its pad now at the press's velocity, then selects its track",
      R.presses.pad(st, { 2, 90 }), { { "note", "pad", { 2, 90 } }, { "page", "track", { 2 } },
                                      { "page", "steps", zeros(16) } })
R.presses.step(st, { 1, 100 })
want = zeros(256)
want[17] = R.velocity(6)
equal("a step press edits the SELECTED track -- track 2's step 1, track 1 untouched",
      st.pattern, want)
local st3 = R.new(3)
equal("bank C's track 2 is pad 34", R.presses.pad(st3, { 2, 90 })[1],
      { "note", "pad", { 34, 90 } })
equal("pads are clipped to 1..16 and levels to 1..8",
      { R.presses.pad(R.new(1), { 0, 90 })[1], R.presses.pad(R.new(1), { 20, 90 })[1],
        R.presses.vel(R.new(1), { 40, 0 })[1] },
      { { "note", "pad", { 1, 90 } }, { "note", "pad", { 16, 90 } }, { "page", "vel", { 8 } } })
equal("a press with no number in it does nothing",
      { R.presses.step(R.new(1), {}), R.presses.vel(R.new(1), {}), R.presses.pad(R.new(1), {}) },
      { {}, {}, {} })

print("\n--- the last step ---")
st = R.new(1)
R.presses.step(st, { 12, 100 })
local before = {}
for i = 1, 256 do before[i] = st.pattern[i] end
equal("knob 2's last 12 answers only last 12, for the page and the counter",
      R.presses.last(st, { 12 }), { { "page", "last", { 12 } } })
equal("... and keeps every note, the steps past it included", st.pattern, before)
equal("it is clipped to 1..16 and floored, and a last with no number does nothing",
      { R.presses.last(R.new(1), { 0 })[1], R.presses.last(R.new(1), { 40 })[1],
        R.presses.last(R.new(1), { 7.9 })[1], R.presses.last(R.new(1), {}) },
      { { "page", "last", { 1 } }, { "page", "last", { 16 } }, { "page", "last", { 7 } }, {} })

print("\n--- which notes fire ---")
st = R.new(1)
st.pattern[R.index(1, 3)] = 20
st.pattern[R.index(5, 3)] = 0.5
st.pattern[R.index(2, 3)] = 77
st.pattern[R.index(16, 3)] = 127
st.pattern[R.index(2, 4)] = 50
equal("a step plays every track at 1 or more, track 1 first, at its velocity",
      R.internal.fire(st, { 3 }), { { "note", "pad", { 1, 20 } }, { "note", "pad", { 2, 77 } },
                                    { "note", "pad", { 16, 127 } } })
equal("... a rest below 1 plays nothing, and an empty step nothing at all",
      { #R.internal.fire(st, { 3 }), R.internal.fire(st, { 1 }) }, { 3, {} })
equal("... and only that step: step 4 plays track 2 at 50",
      R.internal.fire(st, { 4 }), { { "note", "pad", { 2, 50 } } })
st3 = R.new(3)
st3.pattern[R.index(1, 1)] = 64
equal("bank C's track 1 fires pad 33", R.internal.fire(st3, { 1 }),
      { { "note", "pad", { 33, 64 } } })

print("\n--- the restore ---")
st = R.new(1)
local line = zeros(256)
line[3], line[9], line[23], line[256] = 20, 77, 50, 127
equal("a restore takes all 256, then puts them straight back and redraws",
      R.internal.restore(st, line), edited(line, 1))
equal("... and the pattern is the line", st.pattern, line)
st.pattern[200] = 5
R.internal.restore(st, { 1, 2, "x" })
want = {}
for i = 1, 256 do want[i] = line[i] end
want[1], want[2], want[3], want[200] = 1, 2, 0, 5
equal("a short line sets what it holds, a symbol as 0, and leaves the rest", st.pattern, want)
local long = zeros(300)
long[257] = 99
R.internal.restore(st, long)
equal("a long line stops at 256", { #st.pattern, st.pattern[256] }, { 256, 0 })
equal("an empty restore changes nothing and still puts the pattern back",
      R.internal.restore(st, {})[1], { "save", "list", zeros(256) })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_steps-lua.pd_lua", DIR)
check("c_steps-lua.pd_lua registers the class c_steps-lua", class and class._name == "c_steps-lua",
      class and class._name)
local o = T.new(class, { 1 })
check("an object has two inlets and five outlets", o and o.inlets == 2 and o.outlets == 5,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the page's selection on outlet 2, then the bang on outlet 5 that says it loaded",
      T.send(o, 2, "init", {}), { { 2, "vel", { 6 } }, { 2, "track", { 1 } }, { 2, "last", { 16 } },
                                  { 2, "steps", zeros(16) }, { 5, "bang", {} } })
equal("knob 2's last on inlet 1: the page's last on outlet 2", T.send(o, 1, "last", { 9 }),
      { { 2, "last", { 9 } } })
local sent = T.send(o, 1, "step", { 1, 100 })
want = zeros(256)
want[1] = 95
equal("a step press: the pattern on outlet 3, then the page on outlet 2",
      sent, { { 3, "list", want }, { 2, "steps", row(want, 1) } })
equal("a step of the clock: its notes on outlet 1", T.send(o, 2, "fire", { 1 }),
      { { 1, "pad", { 1, 95 } } })
for _, m in ipairs({ { 1, "float", { 3 } }, { 1, "beat", { 1 } }, { 1, "fire", { 1 } },
                     { 2, "step", { 1, 100 } } }) do
  equal(string.format("%s on inlet %d is fail c_steps bad-selector on outlet 4", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 4, "fail", { "c_steps", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose fire throws: the class reads its rules as
-- prefix .. "c_steps.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-c_steps.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'c_steps.lua")\n',
         'R.internal.fire = function() error("a bug in fire") end\nreturn R\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "c_steps-lua.pd_lua", tmp .. "-"), { 1 })
os.remove(tmp .. "-c_steps.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 4 as fail c_steps lua-fire, for the error log",
      T.send(broken, 2, "fire", { 1 }), { { 4, "fail", { "c_steps", "lua-fire" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in fire", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a press still answers",
      T.send(broken, 1, "vel", { 2, 0 }), { { 2, "vel", { 2 } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
