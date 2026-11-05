-- The synth choice and the router, without Pd: "Cut It/c_synth.lua", and the Pd face that
-- carries it, "Cut It/c_synth-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The
-- synths gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo
-- root:
--
--   lua test/gate/lua/c_synth_test.lua [-v]
--
-- What reaches the two synths' channels, the pads, the phone and the state file are
-- synths-assert.py's, on a running copy of the instrument. ref/module/synths.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "c_synth.lua")
local check, equal = T.check, T.equal

local function note(synth, n, v) return { synth, "note", { n, v } } end
local function told(choice)
  return { { "choice", "synth", { choice } }, { "save", "synth", { choice } } }
end
-- The velocity switch, to the phone and the store (Brendan, 2026-11-04).
local function vel(v)
  return { { "phone", "velocity", { v } }, { "save", "velocity", { v } } }
end
local function both(choice, v)
  local out = told(choice)
  for _, e in ipairs(vel(v)) do out[#out + 1] = e end
  out[#out + 1] = { "save", "programs", { "none", "none" } }
  return out
end

print("\n--- the choice ---")
local st = R.new()
equal("fm until something says otherwise", st.choice, "fm")
equal("the synths, in their outlets' order", R.SYNTHS, { "fm", "strings" })
equal("load tells the pads, the phone and the store the choice and the velocity switch on, and "
      .. "puts no program for either synth, so the section playing holds them from the start",
      R.boot(st), both("fm", "on"))
equal("synth strings changes it, and says so", R.choose(st, { "strings" }), told("strings"))
equal("... the same choice again changes nothing and says nothing",
      R.choose(st, { "strings" }), {})
equal("a press from the map carries its value, and chooses", R.choose(st, { "fm", 1 }), told("fm"))
equal("... a release, value 0, does nothing", R.choose(st, { "strings", 0 }), {})
equal("... and leaves the choice where it was", st.choice, "fm")
equal("a synth it does not know is fail c_synth bad-synth", R.choose(st, { "piano" }),
      { { "err", "fail", { "c_synth", "bad-synth" } } })
equal("... a number too", R.choose(st, { 3 }), { { "err", "fail", { "c_synth", "bad-synth" } } })
equal("... and so is no synth at all", R.choose(st, {}),
      { { "err", "fail", { "c_synth", "bad-synth" } } })
equal("... none of which moves the choice", st.choice, "fm")

print("\n--- keys go to the chosen synth ---")
st = R.new()
equal("a press goes to fm, chosen", R.key(st, 60, 100), { note("fm", 60, 100) })
equal("its release goes to fm", R.key(st, 60, 0), { note("fm", 60, 0) })
R.choose(st, { "strings" })
equal("with strings chosen, a press goes to strings alone", R.key(st, 62, 90),
      { note("strings", 62, 90) })
equal("... and its release", R.key(st, 62, 0), { note("strings", 62, 0) })

print("\n--- a switch while keys are held ---")
st = R.new()
R.key(st, 60, 100)
R.key(st, 64, 100)
R.choose(st, { "strings" })
equal("a key pressed on fm releases on fm after the switch", R.key(st, 60, 0), { note("fm", 60, 0) })
equal("a key pressed after the switch plays strings", R.key(st, 67, 80), { note("strings", 67, 80) })
R.choose(st, { "fm" })
equal("switch back: the strings key releases on strings", R.key(st, 67, 0),
      { note("strings", 67, 0) })
equal("... and the fm key still held releases on fm", R.key(st, 64, 0), { note("fm", 64, 0) })
equal("nothing is held after", next(st.held), nil)
R.key(st, 72, 100)
R.choose(st, { "strings" })
equal("a key pressed again while its press on another synth is held releases that first",
      R.key(st, 72, 50), { note("fm", 72, 0), note("strings", 72, 50) })
equal("... and its release then goes to the synth that has it", R.key(st, 72, 0),
      { note("strings", 72, 0) })
equal("a release with no press on record goes to the synth chosen now", R.key(st, 40, 0),
      { note("strings", 40, 0) })

print("\n--- a key's numbers ---")
st = R.new()
equal("floats from Pd are whole notes and velocities", R.key(st, 60.0, 100.0),
      { note("fm", 60, 100) })
equal("a velocity past 127 is 127, a note below 0 is 0", R.key(st, -3, 300),
      { note("fm", 0, 127) })
equal("a symbol is 0, so a release", R.key(st, 60, "x"), { note("fm", 60, 0) })

print("\n--- the velocity switch ---")
-- On, the key's velocity passes; off, every note-on goes out at 127 and a release stays 0, on
-- both synths (Brendan, 2026-11-04).
st = R.new()
equal("on at first", st.velocity, "on")
equal("on: a key's velocity passes", R.key(st, 60, 40), { note("fm", 60, 40) })
equal("velocity off turns it off, and says so to the phone and the store",
      R.inputs.velocity(st, { "off" }), vel("off"))
equal("⛔ off: a soft press goes out at 127", R.key(st, 62, 20), { note("fm", 62, 127) })
equal("... and its release at 0", R.key(st, 62, 0), { note("fm", 62, 0) })
R.choose(st, { "strings" })
equal("⛔ ... on the strings too", R.key(st, 64, 1), { note("strings", 64, 127) })
equal("a press of a key held on fm still releases it there first, at 0",
      (function() R.key(st, 60, 0); R.choose(st, { "fm" }); R.key(st, 67, 5)
                  R.choose(st, { "strings" }); return R.key(st, 67, 9) end)(),
      { note("fm", 67, 0), note("strings", 67, 127) })
equal("the same setting again changes nothing and says nothing", R.inputs.velocity(st, { "off" }), {})
equal("velocity on turns it back on", R.inputs.velocity(st, { "on" }), vel("on"))
equal("... and the key's velocity passes again", R.key(st, 69, 33), { note("strings", 69, 33) })
equal("a setting it does not know is fail c_synth bad-velocity, and changes nothing",
      { R.inputs.velocity(st, { "loud" }), R.inputs.velocity(st, {}), st.velocity },
      { { { "err", "fail", { "c_synth", "bad-velocity" } } },
        { { "err", "fail", { "c_synth", "bad-velocity" } } }, "on" })
equal("the choice says nothing of it, and it nothing of the choice",
      { R.choose(st, { "fm" }), R.inputs.velocity(st, { "off" }) }, { told("fm"), vel("off") })

print("\n--- the restore ---")
st = R.new()
equal("a saved strings comes back, and is put straight back", R.restore(st, { "strings" }),
      told("strings"))
equal("... and is the choice", st.choice, "strings")
equal("a saved choice naming no synth keeps the one in force and puts that back",
      R.restore(st, { "compose" }), told("strings"))
equal("an empty one too", R.restore(st, {}), told("strings"))
st = R.new()
equal("a saved velocity off comes back, and is put straight back",
      R.internal["restore-velocity"](st, { "off" }), vel("off"))
equal("... and is the setting", st.velocity, "off")
equal("a saved velocity naming neither keeps the one in force and puts that back",
      R.internal["restore-velocity"](st, { 3 }), vel("off"))

print("\n--- each synth's program, a section's ---")
st = R.new()
equal("a section's programs, the Volca's 20 and the Streichfett's 5: each sent to its synth, the "
      .. "Volca first, and put straight back", R.internal["restore-programs"](st, { 20, 5 }),
      { { "fm", "program", { 20 } }, { "strings", "program", { 5 } },
        { "save", "programs", { 20, 5 } } })
equal("⛔ none sends nothing, and is put back as none",
      R.internal["restore-programs"](st, { "none", 7 }),
      { { "strings", "program", { 7 } }, { "save", "programs", { "none", 7 } } })
equal("... both none: nothing to either synth", R.internal["restore-programs"](st, { "none", "none" }),
      { { "save", "programs", { "none", "none" } } })
equal("a program past 0 to 127, or missing, is none; one in it is whole",
      R.internal["restore-programs"](st, { 128, 3.6 }),
      { { "strings", "program", { 4 } }, { "save", "programs", { "none", 4 } } })
equal("... and none of it changes the choice or the switch", { st.choice, st.velocity },
      { "fm", "on" })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_synth-lua.pd_lua", DIR)
check("c_synth-lua.pd_lua registers the class c_synth-lua",
      class and class._name == "c_synth-lua", class and class._name)
local o = T.new(class, {})
check("an object is made, with 2 inlets and 7 outlets",
      o ~= nil and o.inlets == 2 and o.outlets == 7, o and (o.inlets .. " " .. o.outlets))
equal("init answers with the choice on outlets 3 and 4, the velocity switch on 7 and 4, the "
      .. "programs on 4, then a bang on 6", T.send(o, 2, "init", {}),
      { { 3, "synth", { "fm" } }, { 4, "synth", { "fm" } }, { 7, "velocity", { "on" } },
        { 4, "velocity", { "on" } }, { 4, "programs", { "none", "none" } }, { 6, "bang", {} } })
equal("a section's programs: the Volca's on outlet 1, the Streichfett's on 2, then the put on 4",
      T.send(o, 2, "restore-programs", { 9, 12 }),
      { { 1, "program", { 9 } }, { 2, "program", { 12 } }, { 4, "programs", { 9, 12 } } })
equal("a key on inlet 1 leaves outlet 1, the Volca's, as note <n> <v>",
      T.send(o, 1, "list", { 60, 100 }), { { 1, "note", { 60, 100 } } })
equal("synth strings leaves outlets 3 and 4", T.send(o, 1, "synth", { "strings" }),
      { { 3, "synth", { "strings" } }, { 4, "synth", { "strings" } } })
equal("the held key releases on outlet 1", T.send(o, 1, "list", { 60, 0 }),
      { { 1, "note", { 60, 0 } } })
equal("a new key leaves outlet 2, the Streichfett's", T.send(o, 1, "list", { 62, 90 }),
      { { 2, "note", { 62, 90 } } })
equal("restore on inlet 2 takes the saved choice and puts it back",
      T.send(o, 2, "restore", { "fm" }), { { 3, "synth", { "fm" } }, { 4, "synth", { "fm" } } })
equal("velocity off on inlet 1 leaves outlet 7, for the phone, and 4, to save",
      T.send(o, 1, "velocity", { "off" }),
      { { 7, "velocity", { "off" } }, { 4, "velocity", { "off" } } })
equal("... and a key then leaves at 127", T.send(o, 1, "list", { 64, 12 }),
      { { 1, "note", { 64, 127 } } })
equal("restore-velocity on inlet 2 takes the saved setting and puts it back",
      T.send(o, 2, "restore-velocity", { "on" }),
      { { 7, "velocity", { "on" } }, { 4, "velocity", { "on" } } })
equal("a bad synth leaves outlet 5 for err", T.send(o, 1, "synth", { "organ" }),
      { { 5, "fail", { "c_synth", "bad-synth" } } })
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "list", { 62, 0 }); return o.sent end)(),
      { { 2, "note", { 62, 0 } } })
for _, m in ipairs({ { 1, "notes", { 1, 2, 3 } }, { 1, "bang", {} }, { 2, "synth", { "fm" } } }) do
  equal(string.format("%s on inlet %d is fail c_synth bad-selector on outlet 5", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 5, "fail", { "c_synth", "bad-selector" } } })
end

-- A Lua error, made by a copy of the rules whose key rule throws: the class reads its rules as
-- prefix .. "c_synth.lua", so the copy sits at a temporary prefix, with the face beside it.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-c_synth.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'c_synth.lua")\n',
         'R.inputs.list = function() error("a bug in key") end\nreturn R\n')
fh:close()
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "c_synth-lua.pd_lua", tmp .. "-"), {})
os.remove(tmp .. "-c_synth.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 5 as fail c_synth lua-list, for the error log",
      T.send(broken, 1, "list", { 60, 100 }), { { 5, "fail", { "c_synth", "lua-list" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in key", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: init still answers", T.send(broken, 2, "init", {}),
      { { 3, "synth", { "fm" } }, { 4, "synth", { "fm" } }, { 7, "velocity", { "on" } },
        { 4, "velocity", { "on" } }, { 4, "programs", { "none", "none" } }, { 6, "bang", {} } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
