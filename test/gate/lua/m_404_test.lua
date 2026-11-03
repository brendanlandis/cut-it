-- The SP-404's decode, both ways, without Pd: "Cut It/m_404.lua", and the Pd face that carries
-- it, "Cut It/m_404-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The SP-404 gate
-- runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/m_404_test.lua [-v]
--
-- The channel gates, the timer's real milliseconds, the note-off's 200 ms, panic and what
-- param and disp see are sp404-assert.py's, on a running copy of the instrument.
-- ref/device/sp404.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "m_404.lua")
local check, equal = T.check, T.equal

-- Pad n's note in every bank, as measured (item 190): not 47 + n.
local MAP = { 48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39 }

local function pad(name, velocity)
  return { { "param", name, { velocity } } }
end

local function played(note, velocity, channel)
  return { { "off", "list", { note, 0, channel } }, { "note", "list", { note, velocity, channel } } }
end

-- A state whose budget is full: a gap long enough to refill it.
local function full()
  local st = R.new(33)
  st.level = R.BUCKET
  return st
end

print("\n--- the pad map ---")
equal("pads 1 to 16 are the measured notes, four rows of four from the bottom", R.NOTE, MAP)
local back = {}
for p = 1, 16 do back[p] = R.PAD[MAP[p]] end
equal("... and read backwards, every note names its own pad", back,
      { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 })

print("\n--- receive: a note names its bank and pad ---")
local st = R.new(33)
equal("note 48 in bank A is sp-a1, carrying its velocity", R.rx(st, 48, 77, 0), pad("sp-a1", 77))
equal("note 44 in bank B is sp-b5", R.rx(st, 44, 90, 1), pad("sp-b5", 90))
equal("a release goes too, at velocity 0", R.rx(st, 44, 0, 1), pad("sp-b5", 0))
equal("bank J is sp-j, and note 39 is pad 16", R.rx(st, 39, 1, 9), pad("sp-j16", 1))
local names = {}
for b = 0, 9 do local r = R.rx(st, 36, 1, b)[1]; names[#names + 1] = r and r[2] or "none" end
equal("the ten banks are a to j", names,
      { "sp-a13", "sp-b13", "sp-c13", "sp-d13", "sp-e13", "sp-f13", "sp-g13", "sp-h13", "sp-i13",
        "sp-j13" })
equal("a note and bank Pd hands over as floats name as integers", R.rx(st, 48.0, 64.0, 2.0),
      pad("sp-c1", 64))
equal("a note outside the map names nothing: no stale name from the last pad",
      { R.rx(st, 48, 77, 0), R.rx(st, 60, 50, 0), R.rx(st, 35, 40, 1), R.rx(st, 52, 1, 0) },
      { pad("sp-a1", 77), {}, {}, {} })
equal("a bank outside 0 to 9 names nothing", { R.rx(st, 48, 1, 10), R.rx(st, 48, 1, -1) }, { {}, {} })

print("\n--- transmit: a pad becomes a note on its bank's channel ---")
st = full()
local got = {}
for p = 1, 16 do local r = R.tx(st, p, 100, 0)[2]; got[p] = r and r[3][1] or 0 end
equal("ALL SIXTEEN pads of bank A play the measured notes", got, MAP)
equal("bank A is the creation argument's channel, 33", R.tx(full(), 1, 100, 0),
      played(48, 100, 33))
equal("pad 33 is bank C's pad 1: note 48 on channel 35", R.tx(full(), 33, 90, 0),
      played(48, 90, 35))
equal("pad 160 is bank J's pad 16: note 39 on channel 42", R.tx(full(), 160, 80, 0),
      played(39, 80, 42))
equal("pad 17 is bank B's pad 1, not bank A's pad 17", R.tx(full(), 17, 70, 0),
      played(48, 70, 34))
equal("the note-off goes first, on the note-on's own channel, at velocity 0",
      R.tx(full(), 5, 64, 0)[1], { "off", "list", { 44, 0, 33 } })
equal("another base: bank A on channel 1", R.tx((function()
  local s = R.new(1); s.level = 16; return s end)(), 2, 10, 0), played(49, 10, 1))
equal("out of range, as [div 16] and [mod 16] had it: pad 0 is bank A's pad 16 a bank below",
      R.tx(full(), 0, 1, 0), played(39, 1, 32))

print("\n--- the trigger budget ---")
st = R.new(33)
equal("a new budget is empty: the first trigger needs a gap to pay for it", R.tx(st, 1, 100, 0), {})
equal("... and a 5 ms gap pays for one", #R.tx(st, 1, 100, 5), 2)
st = R.new(33)
local n = 0
R.tx(st, 1, 100, 10000)
for _ = 1, 20 do if #R.tx(st, 1, 100, 0) > 0 then n = n + 1 end end
equal("after a long rest, 20 at once play 15 more: 16 in all, the bucket's size", n + 1, 16)
equal("drained, a trigger 2 ms on is dropped: 0.4 of a trigger", R.tx(st, 2, 100, 2), {})
equal("... and one 3 ms after that plays: 0.4 and 0.6 make one", #R.tx(st, 3, 100, 3), 2)
equal("... leaving nothing over", st.level, 0)
st = R.new(33)
R.tx(st, 1, 100, 1e9)
equal("the budget is capped at 16 however long the rest", st.level, 15)
equal("a dropped trigger answers nothing at all, so it schedules no note-off",
      R.tx(R.new(33), 1, 100, 0), {})
equal("a gap that is not a number refills nothing", R.tx(R.new(33), 1, 100, "x"), {})

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "m_404-lua.pd_lua", DIR)
check("m_404-lua.pd_lua registers the class m_404-lua",
      class and class._name == "m_404-lua", class and class._name)
local o = T.new(class, { 33 })
check("an object is made, with 3 inlets and 5 outlets",
      o ~= nil and o.inlets == 3 and o.outlets == 5, o and (o.inlets .. " " .. o.outlets))
equal("init answers with a bang on outlet 5, the proof the Lua loaded",
      T.send(o, 3, "init", {}), { { 5, "bang", {} } })
equal("<note> <velocity> <bank> on inlet 1 leaves outlet 3 for param",
      T.send(o, 1, "list", { 44, 90, 1 }), { { 3, "sp-b5", { 90 } } })
equal("<pad> <velocity> <gap> on inlet 2: the note-off on outlet 2, then the note on outlet 1",
      T.send(o, 2, "list", { 33, 100, 1000 }),
      { { 2, "list", { 48, 0, 35 } }, { 1, "list", { 48, 100, 35 } } })
equal("the creation argument is bank A's channel", T.send(T.new(class, { 1 }), 2, "list",
      { 1, 100, 1000 }), { { 2, "list", { 48, 0, 1 } }, { 1, "list", { 48, 100, 1 } } })
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "list", { 48, 7, 0 }); return o.sent end)(),
      { { 3, "sp-a1", { 7 } } })
equal("... inlet 2",
      (function() o.sent = {}; o:dispatch(2, "list", { 1, 7, 1000 }); return o.sent end)(),
      { { 2, "list", { 48, 0, 33 } }, { 1, "list", { 48, 7, 33 } } })
equal("... and inlet 3",
      (function() o.sent = {}; o:dispatch(3, "init", {}); return o.sent end)(),
      { { 5, "bang", {} } })
for _, m in ipairs({ { 1, "float", { 48 } }, { 2, "pad", { 1, 100 } }, { 3, "list", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail m_404 bad-selector on outlet 4", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 4, "fail", { "m_404", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose transmit rule throws: the class reads its
-- rules as prefix .. "m_404.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-m_404.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'm_404.lua")\n',
         'R.tx = function() error("a bug in tx") end\nreturn R\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "m_404-lua.pd_lua", tmp .. "-"), { 33 })
os.remove(tmp .. "-m_404.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 4 as fail m_404 lua-pad, for the error log",
      T.send(broken, 2, "list", { 1, 100, 1000 }), { { 4, "fail", { "m_404", "lua-pad" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in tx", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a note still names its pad",
      T.send(broken, 1, "list", { 48, 1, 0 }), { { 3, "sp-a1", { 1 } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
