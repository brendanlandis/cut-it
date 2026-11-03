-- The nanoKONTROL's decode, without Pd: "Cut It/m_nano.lua", and the Pd face that carries it,
-- "Cut It/m_nano-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The nano gate runs
-- this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/m_nano_test.lua [-v]
--
-- The channel gate, what param and disp see and the other two devices' CCs are nano-assert.py's,
-- on a running copy of the instrument. ref/device/nanokontrol.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "m_nano.lua")
local check, equal = T.check, T.equal

local function control(name, value)
  return { { "param", name, { value } } }
end

local function unmapped(cc)
  return { { "err", "warn", { "m_nano", "cc-" .. cc .. "-unmapped" } } }
end

print("\n--- the five families, by tens ---")
equal("CC 1 is slider-1, carrying its value", R.cc(1, 64), control("slider-1", 64))
equal("CC 9 is slider-9", R.cc(9, 3), control("slider-9", 3))
equal("CC 15 is knob-5", R.cc(15, 22), control("knob-5", 22))
equal("CC 22 is btn-t-2", R.cc(22, 127), control("btn-t-2", 1))
equal("CC 34 is btn-b-4", R.cc(34, 127), control("btn-b-4", 1))
equal("CC 43 is xport-3", R.cc(43, 127), control("xport-3", 1))
equal("the units digit 0 names a 0, as [makefilename %d] does: CC 10 is knob-0",
      { R.cc(0, 1), R.cc(10, 2) }, { control("slider-0", 1), control("knob-0", 2) })
local names = {}
for cc = 0, 49 do names[#names + 1] = R.cc(cc, 127)[1][2] end
equal("all fifty: ten of each family, in order", names, (function()
  local want = {}
  for _, f in ipairs({ "slider-", "knob-", "btn-t-", "btn-b-", "xport-" }) do
    for n = 0, 9 do want[#want + 1] = f .. n end
  end
  return want
end)())
equal("a CC Pd hands over as a float decodes as its integer", R.cc(22.0, 127.0),
      control("btn-t-2", 1))

print("\n--- values: continuous controls pass them, buttons send a press as 1 ---")
equal("a slider passes 0, which is a position, not a release", R.cc(3, 0), control("slider-3", 0))
equal("a knob passes 127 as it is", R.cc(11, 127), control("knob-1", 127))
equal("a button's press is 1, not the 127 sent", R.cc(24, 127), control("btn-t-4", 1))
equal("... and its release sends nothing", R.cc(24, 0), {})
equal("a button's value other than 127 sends nothing either", R.cc(24, 64), {})
equal("the transport row is a button too: its release sends nothing", R.cc(42, 0), {})
equal("a value that is not a number is 0", R.cc(5, "x"), control("slider-5", 0))

print("\n--- a CC with no kind ---")
equal("CC 55 warns cc-55-unmapped and sends no control", R.cc(55, 99), unmapped(55))
equal("... on a release as well as a press", R.cc(55, 0), unmapped(55))
equal("CC 50, the first past the transport row, is unmapped", R.cc(50, 1), unmapped(50))
equal("CC 127 is unmapped, and its text fits C-12", R.cc(127, 1), unmapped(127))
equal("a stale name cannot leak: a button, then an unmapped CC, then nothing more",
      { R.cc(26, 127), R.cc(56, 127) }, { control("btn-t-6", 1), unmapped(56) })
equal("... and a continuous control, then an unmapped CC",
      { R.cc(7, 30), R.cc(55, 99) }, { control("slider-7", 30), unmapped(55) })
equal("a negative controller is unmapped, and does not throw", R.cc(-5, 1), unmapped(-5))
equal("a fractional controller is cut toward zero, as [div] and [mod] take it",
      R.cc(22.5, 127), control("btn-t-2", 1))

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "m_nano-lua.pd_lua", DIR)
check("m_nano-lua.pd_lua registers the class m_nano-lua",
      class and class._name == "m_nano-lua", class and class._name)
local o = T.new(class, {})
check("an object is made, with 2 inlets and 3 outlets",
      o ~= nil and o.inlets == 2 and o.outlets == 3, o and (o.inlets .. " " .. o.outlets))
equal("init answers with a bang on outlet 3, the proof the Lua loaded",
      T.send(o, 2, "init", {}), { { 3, "bang", {} } })
equal("<controller> <value> on inlet 1 leaves outlet 1 for param",
      T.send(o, 1, "list", { 1, 64 }), { { 1, "slider-1", { 64 } } })
equal("an unmapped CC leaves outlet 2 for err", T.send(o, 1, "list", { 55, 99 }),
      { { 2, "warn", { "m_nano", "cc-55-unmapped" } } })
equal("a release answers nothing at all", T.send(o, 1, "list", { 24, 0 }), {})
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "list", { 15, 9 }); return o.sent end)(),
      { { 1, "knob-5", { 9 } } })
equal("... and inlet 2",
      (function() o.sent = {}; o:dispatch(2, "init", {}); return o.sent end)(),
      { { 3, "bang", {} } })
for _, m in ipairs({ { 1, "float", { 64 } }, { 1, "cc", { 1, 64 } }, { 2, "list", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail m_nano bad-selector on outlet 2", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 2, "fail", { "m_nano", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose decode throws: the class reads its rules as
-- prefix .. "m_nano.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-m_nano.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'm_nano.lua")\n',
         'R.cc = function() error("a bug in cc") end\nreturn R\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "m_nano-lua.pd_lua", tmp .. "-"), {})
os.remove(tmp .. "-m_nano.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 2 as fail m_nano lua-ctlin, for the error log",
      T.send(broken, 1, "list", { 1, 64 }), { { 2, "fail", { "m_nano", "lua-ctlin" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in cc", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: init still answers", T.send(broken, 2, "init", {}),
      { { 3, "bang", {} } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
