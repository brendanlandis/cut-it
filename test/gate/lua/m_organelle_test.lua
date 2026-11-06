-- The Organelle keyboard's rules, without Pd: "Cut It/m_organelle.lua", and the Pd face that
-- carries them, "Cut It/m_organelle-lua.pd_lua", loaded through lib_test's stand-in for pdlua.
-- The Organelle gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from
-- the repo root:
--
--   lua test/gate/lua/m_organelle_test.lua [-v]
--
-- What mother's names reach, the knobs, aux and presence are organelle-assert.py's, on a running
-- copy of the instrument. ref/device/organelle.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "m_organelle.lua")
local check, equal = T.check, T.equal

local function key(name, velocity)
  return { { "param", name, { velocity } } }
end

print("\n--- one control per key ---")
local st = R.new()
equal("a press is og-key-<pitch> carrying its velocity", R.key(st, 60, 100), key("og-key-60", 100))
equal("a release is published too, at velocity 0", R.key(st, 60, 0), key("og-key-60", 0))
equal("the pitch comes from the message: the top key is og-key-84", R.key(st, 84, 40),
      key("og-key-84", 40))
equal("a pitch Pd hands over as a float names as an integer, as makefilename %d",
      R.key(st, 72.0, 64), key("og-key-72", 64))
equal("a fractional pitch is cut toward zero, as makefilename %d", R.key(st, 61.7, 1),
      key("og-key-61", 1))
equal("a symbol where a number belongs is read as 0", R.key(st, "x", 9),
      key("og-key-0", 9))
equal("no velocity is a release", R.key(st, 62, nil), key("og-key-62", 0))

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "m_organelle-lua.pd_lua", DIR)
check("m_organelle-lua.pd_lua registers the class m_organelle-lua",
      class and class._name == "m_organelle-lua", class and class._name)
local o = T.new(class, {})
check("an object is made, with 2 inlets and 3 outlets",
      o ~= nil and o.inlets == 2 and o.outlets == 3, o and (o.inlets .. " " .. o.outlets))
equal("init answers with a bang on outlet 3, the proof the Lua loaded",
      T.send(o, 2, "init", {}), { { 3, "bang", {} } })
equal("mother's notes on inlet 1 leave outlet 1 for param", T.send(o, 1, "list", { 60, 100 }),
      { { 1, "og-key-60", { 100 } } })
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "list", { 61, 5 }); return o.sent end)(),
      { { 1, "og-key-61", { 5 } } })
equal("... and inlet 2",
      (function() o.sent = {}; o:dispatch(2, "init", {}); return o.sent end)(),
      { { 3, "bang", {} } })
for _, m in ipairs({ { 1, "float", { 60 } }, { 1, "notes", { 60, 1 } }, { 2, "aux", { 1 } },
                     { 2, "shift", { 1 } }, { 2, "list", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail m_organelle bad-selector on outlet 2", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 2, "fail", { "m_organelle", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose key rule throws: the class reads its rules as
-- prefix .. "m_organelle.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-m_organelle.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'm_organelle.lua")\n',
         'R.key = function() error("a bug in key") end\nreturn R\n')
fh:close()
-- The face too, which the class reads from the same prefix.
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "m_organelle-lua.pd_lua", tmp .. "-"), {})
os.remove(tmp .. "-m_organelle.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 2 as fail m_organelle lua-notes, for the error log",
      T.send(broken, 1, "list", { 60, 100 }), { { 2, "fail", { "m_organelle", "lua-notes" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in key", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: init still answers", T.send(broken, 2, "init", {}),
      { { 3, "bang", {} } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
