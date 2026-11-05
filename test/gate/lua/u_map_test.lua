-- The map's rules, without Pd: "Cut It/u_map.lua", and the Pd face that carries them,
-- "Cut It/u_map-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The map gate runs
-- this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/u_map_test.lua [-v]
--
-- What the destinations do with a looked-up control, and the timing of the boot window and the
-- knobs.txt read, are map-assert.py's, on a running copy of the instrument. ref/module/map.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "u_map.lua")
local check, equal = T.check, T.equal

-- A small table: two modes, a knob, a fader, a key, pressure, and a row the route won't know.
local MAP = table.concat({
  "mode-1 og-knob-1 tempo 0",
  "mode-2 og-knob-1 tempo 0",
  "mode-1 og-knob-2 volca-cc 42",
  "mode-1 slider-1 volca-cc 41",
  "mode-2 slider-1 volca-note 48",
  "mode-1 og-key-60 volca-key 60",
  "mode-1 pad-13-at volca-cc 45",
  "mode-1 gk-bad no-such-destination 0",
}, "\n") .. "\n"

local function route(dest, arg, value, target, live)
  return { { "route", "list", { dest, arg, value, target, live } } }
end


print("\n--- the table ---")
local map, rows = R.parse(MAP)
equal("a row is <mode> <control> <dest> <arg>, the arg a number",
      map["mode-1"]["slider-1"], { dest = "volca-cc", arg = 41 })
equal("... and every row is counted, as [text size] counts lines", rows, 8)
map, rows = R.parse("mode-1 a tempo 0\nmode-1 a stop 0\n")
equal("a duplicate mode and control: the FIRST row wins, as [text search] found it",
      map["mode-1"]["a"].dest, "tempo")
map, rows = R.parse("mode-1 a tempo\nmode-1 b stop 0 9\n\n  \nmode-1 c start 0\n")
equal("a row of three or five atoms is skipped, and still counted; blank lines are not",
      { map["mode-1"]["a"], map["mode-1"]["b"], map["mode-1"]["c"].dest, rows },
      { nil, nil, "start", 3 })
map, rows = R.parse("mode-1 a tempo 0; mode-2 a stop 0")
equal("a ; ends a row too, as read -c has it", { map["mode-2"]["a"].dest, rows }, { "stop", 2 })
equal("an empty table is 0 rows", { R.parse("") }, { {}, 0 })
local fh = assert(io.open(DIR .. "cut-it-map.txt"))
local shipped = R.new(fh:read("a"))
fh:close()
local tempo_everywhere = true
for n = 1, R.PAGES do
  local r = shipped.map["mode-" .. n]["og-knob-1"]
  tempo_everywhere = tempo_everywhere and r and r.dest == "tempo"
end
check("the shipped table parses: og-knob-1 is tempo on all " .. R.PAGES .. " pages",
      tempo_everywhere, T.show(shipped.map["mode-1"]["og-knob-1"]))
-- Knobs 2 and 4 are the drums' last step and swing on every page, knob 3 the selected track's
-- last step on page 2 alone (Brendan, 2026-11-04).
local knobs, want_knobs = {}, {}
for n = 1, R.PAGES do
  local page = shipped.map["mode-" .. n]
  for k = 2, 4 do
    local r = page["og-knob-" .. k]
    knobs[#knobs + 1] = r and (r.dest .. " " .. r.arg) or "none"
  end
  want_knobs[#want_knobs + 1] = "drums last"
  want_knobs[#want_knobs + 1] = n == 2 and "drums track-last" or "none"
  want_knobs[#want_knobs + 1] = "drums swing"
end
equal("... knobs 2 and 4 are the drums' last step and swing on every page, knob 3 on page 2 alone",
      knobs, want_knobs)

print("\n--- the lookup ---")
local st = R.new(MAP)
equal("the key's mode is mode-1 from the start, before any mode arrives", st.mode, "mode-1")
equal("a mapped control leaves for its destination: <dest> <arg> <value> <target> <live>",
      R.control(st, "slider-1", { 64 }), route("volca-cc", 41, 64 / 127, 64 / 127, 1))
R.mode(st, "mode-2", {})
equal("the same control in another mode means that mode's row -- volca-note 48",
      R.control(st, "slider-1", { 64 }), route("volca-note", 48, 64 / 127, 64 / 127, 1))
R.mode(st, "mode-4", {})
equal("a mode with no row for it: the control is unmapped, and leaves nothing -- no bus, no row",
      R.control(st, "slider-1", { 64 }), {})
st = R.new(MAP)
equal("a row naming a destination the route lacks still leaves: the guard is the route's",
      R.control(st, "gk-bad", { 100 }), route("no-such-destination", 0, 100 / 127, 100 / 127, 1))

print("\n--- the divisor ---")
st = R.new("mode-1 og-knob-3 volca-cc 43\nmode-1 og-aux volca-cc 44\nmode-1 slider-2 volca-cc 45\n")
R.internal.live(st)
equal("an Organelle knob is 0-1 already and passes as it is",
      R.control(st, "og-knob-3", { 0.5 })[1][3][3], 0.5)
equal("anything else is 0-127 and is divided -- og-aux included, it is no knob",
      { R.control(st, "og-aux", { 127 })[1][3][3], R.control(st, "slider-2", { 127 })[1][3][3] },
      { 1, 1 })

print("\n--- the mode bus ---")
st = R.new(MAP)
equal("mode-2: the key takes mode-2, and the store gets it alone",
      R.mode(st, "mode-2", {}), { { "store", "list", { "mode-2" } } })
equal("... and the key is mode-2", st.mode, "mode-2")
for _, m in ipairs({ { "compose", {}, "compose alone, the name lost (item 294)" },
                     { "compose", { "mode-1" }, "the old two-atom form" },
                     { "mode-1", { "x" }, "a page with more after it" },
                     { "mode-0", {}, "mode-0" }, { "mode-" .. (R.PAGES + 1), {}, "a page past the last" },
                     { "mode-1x", {}, "mode-1x" }, { "float", { 3 }, "a float" },
                     { "bang", {}, "a bang" } }) do
  equal(m[3] .. " is refused: bad-mode, and nothing stored",
        R.mode(st, m[1], m[2]), { { "err", "fail", { "u_map", "bad-mode" } } })
end
equal("... and the key survives every one of them", st.mode, "mode-2")
equal("a one-atom list naming a page is a mode too", R.mode(st, "list", { "mode-5" }),
      { { "store", "list", { "mode-5" } } })
equal("... and so is a symbol", R.mode(st, "symbol", { "mode-3" }),
      { { "store", "list", { "mode-3" } } })
local every, want = {}, {}
for n = 1, R.PAGES do
  every[n] = R.mode(st, "mode-" .. n, {})
  want[n] = { { "store", "list", { "mode-" .. n } } }
end
equal("every page from mode-1 to mode-" .. R.PAGES .. " is taken", every, want)

print("\n--- the tempo curve ---")
local C = R.tempo_curve
local bpm = function(x) return math.floor(490 * C(x) + 10 + 0.5) end
equal("knob 1: 10 BPM at the bottom, 50 at 9 o'clock, 125 at noon, 200 at 3 o'clock, 500 at the top",
      { bpm(0), bpm(0.2), bpm(0.5), bpm(0.8), bpm(1) }, { 10, 50, 125, 200, 500 })
check("... rising all the way, with no step back at the joins", (function()
  for i = 1, 1000 do if C(i / 1000) <= C((i - 1) / 1000) then return false end end
  return true
end)(), "")
equal("... and only the tempo has a curve: a mapped CC passes its knob's value as it is",
      R.CURVES["volca-cc"], nil)

print("\n--- pickup ---")
-- R.new(MAP) is a boot after a Save: there is a knobs.txt, and mother's push is a restore.
st = R.new(MAP)
equal("a knob's first value inside the boot window passes",
      R.control(st, "og-knob-1", { 0.0958 }), route("tempo", 0, C(0.0958), C(0.0958), 1))
equal("... and arms it: the next value is HELD, carrying the stored target",
      R.control(st, "og-knob-1", { 0.5 }), route("tempo", 0, C(0.5), C(0.0958), 0))
equal("moving further away is still held", R.control(st, "og-knob-1", { 0.9 })[1][3][5], 0)
equal("CROSSING the target releases it, at the crossing value",
      R.control(st, "og-knob-1", { 0.02 }), route("tempo", 0, C(0.02), C(0.0958), 1))
equal("... and it is live from then on", R.control(st, "og-knob-1", { 0.3 })[1][3][5], 1)

st = R.new(MAP)
R.control(st, "og-knob-1", { 0.5 })
R.control(st, "og-knob-1", { 0.3 })
equal("armed BELOW the target: falling further is held",
      R.control(st, "og-knob-1", { 0.1 })[1][3][5], 0)
equal("... and rising through it releases", R.control(st, "og-knob-1", { 0.7 })[1][3][5], 1)

st = R.new(MAP)
R.control(st, "og-knob-1", { 0 })
equal("a target on the bottom rail: armed at 0, moving up is held",
      R.control(st, "og-knob-1", { 0.5 })[1][3][5], 0)
equal("... and coming back TO it releases -- a rail has no beyond",
      R.control(st, "og-knob-1", { 0 })[1][3][5], 1)

st = R.new(MAP)
R.control(st, "og-knob-1", { 0.2 })
R.control(st, "og-knob-2", { 0.5 })
R.control(st, "og-knob-1", { 0.6 })
R.control(st, "og-knob-1", { 0.1 })
equal("pickup is per knob: knob 1 crossed and is live, knob 2 is still held",
      { R.control(st, "og-knob-1", { 0.4 })[1][3][5], R.control(st, "og-knob-2", { 0.9 })[1][3][5] },
      { 1, 0 })
R.mode(st, "mode-4", {})
equal("a HELD knob unmapped in this mode leaves nothing either",
      R.control(st, "og-knob-2", { 0.75 }), {})
check("... and is still held", st.knob[2].state == "above", T.show(st.knob[2]))

st = R.new(MAP)
R.internal["window-shut"](st)
R.control(st, "og-knob-2", { 0.5 })
equal("a first value AFTER the window is a hand: never armed, the next passes too",
      R.control(st, "og-knob-2", { 0.9 }), route("volca-cc", 42, 0.9, 0.5, 1))

st = R.new(MAP)
R.control(st, "og-knob-1", { 0.2 })
R.control(st, "og-knob-1", { 0.6 })
R.internal.live(st)
equal("live: a held knob is live at once", R.control(st, "og-knob-1", { 0.7 })[1][3][5], 1)
equal("... and so is one that had never moved", R.control(st, "og-knob-2", { 0.4 })[1][3][5], 1)
check("... every slot", st.knob[3].state == "live" and st.knob[4].state == "live",
      T.show(st.knob))

print("\n--- nothing Saved: knob 1 held at 120 ---")
equal("0.48 is where the curve puts 120 BPM", { R.UNSAVED[1], bpm(R.UNSAVED[1]) }, { 0.48, 120 })
fh = assert(io.open(DIR .. "u_tempo.pd"))
local fallback = tonumber(fh:read("a"):match("#X msg %d+ %d+ (%d+);\n#X obj %d+ %d+ s tempo;"))
fh:close()
equal("... the same 120 u_tempo publishes when nothing else has", fallback, 120)
equal("... and no other knob has a place to be held at", { R.UNSAVED[2], R.UNSAVED[3], R.UNSAVED[4] },
      {})
st = R.new(MAP, true)
equal("mother's push of where knob 1 sits is HELD, at 120: the tempo stays u_tempo's",
      R.control(st, "og-knob-1", { 0.0958 }), route("tempo", 0, C(0.0958), C(0.48), 0))
equal("... moving it without reaching 120 is still held", R.control(st, "og-knob-1", { 0.3 }),
      route("tempo", 0, C(0.3), C(0.48), 0))
equal("... and turning it THROUGH 120 releases it, at the crossing value",
      R.control(st, "og-knob-1", { 0.5 }), route("tempo", 0, C(0.5), C(0.48), 1))
equal("... and it is live from then on", R.control(st, "og-knob-1", { 0.3 })[1][3][5], 1)
st = R.new(MAP, true)
equal("from above, it is held until it comes down through 120",
      { R.control(st, "og-knob-1", { 0.9 })[1][3][5], R.control(st, "og-knob-1", { 0.6 })[1][3][5],
        R.control(st, "og-knob-1", { 0.4 })[1][3][5] }, { 0, 0, 1 })
st = R.new(MAP, true)
local function passed(out) return { out[1][3][3], out[1][3][5] } end
equal("every other knob is live from its first value, inside the boot window or not",
      { passed(R.control(st, "og-knob-2", { 0.5 })), passed(R.control(st, "og-knob-2", { 0.9 })) },
      { { 0.5, 1 }, { 0.9, 1 } })
R.internal.live(st)
equal("a recover's live frees knob 1 too: after an emergency nothing is held",
      R.control(st, "og-knob-1", { 0.1 })[1][3][5], 1)

print("\n--- a tempo a tap or the phone set holds knob 1 again ---")
local P = R.tempo_position
equal("the curve's inverse puts each BPM back where the knob sits for it",
      { bpm(P(10)), bpm(P(30)), bpm(P(50)), bpm(P(100)), bpm(P(150)), bpm(P(200)), bpm(P(350)),
        bpm(P(500)) }, { 10, 30, 50, 100, 150, 200, 350, 500 })
equal("... a tempo past the knob's 10 to 500 holds it at the end of its turn",
      { P(5), P(600) }, { 0, 1 })
check("... and 120 is R.UNSAVED's 0.48, the one hold the knob has with nothing Saved",
      math.abs(P(120) - R.UNSAVED[1]) < 1e-9, T.show({ P(120), R.UNSAVED[1] }))
st = R.new(MAP)
R.internal.live(st)
R.control(st, "og-knob-1", { 0.3 })
equal("a tap's 150 leaves nothing: the bus already has it", R.hold_tempo(st, "float", { 150 }), {})
equal("... and knob 1's next turn is HELD at 150, the knob's own tempo in the value",
      R.control(st, "og-knob-1", { 0.42 }), route("tempo", 0, C(0.42), C(P(150)), 0))
equal("... held still, turned the same way", R.control(st, "og-knob-1", { 0.5 })[1][3][5], 0)
equal("... and turned THROUGH 150 it is live, at the crossing value",
      R.control(st, "og-knob-1", { 0.68 }), route("tempo", 0, C(0.68), C(P(150)), 1))
R.hold_tempo(st, "float", { 100 })
equal("the phone's tempo holds it again, from above this time",
      { R.control(st, "og-knob-1", { 0.9 })[1][3][5], R.control(st, "og-knob-1", { 0.3 })[1][3][5] },
      { 0, 1 })
st = R.new(MAP)
R.internal.live(st)
R.mode(st, "mode-3", {})
R.hold_tempo(st, "float", { 150 })
equal("on a page whose knob 1 is no tempo, the hold leaves it alone", st.knob[1].state, "live")
st = R.new(MAP)
R.internal.live(st)
R.hold_tempo(st, "symbol", { "fast" })
equal("... and a tempo that is no number holds nothing", st.knob[1].state, "live")
equal("... and no other knob is held by a tempo", { st.knob[2].state, st.knob[3].state, st.knob[4].state },
      { "live", "live", "live" })

st = R.new("mode-1 xport-2 start 0\n")
equal("a button is never held: PLAY twice is live twice",
      { R.control(st, "xport-2", { 1 })[1][3][5], R.control(st, "xport-2", { 1 })[1][3][5] },
      { 1, 1 })

print("\n--- an unmapped control names nothing ---")
-- Only a control the map binds names itself (Brendan, 2026-11-04).
st = R.new(MAP)
equal("an unmapped control leaves nothing: no <name> <raw> row, no bus",
      R.control(st, "gk-x", { 64 }), {})
equal("... a press of an unmapped pad neither", R.control(st, "pad-15", { 100 }), {})
equal("... nor an unmapped key or its release", { R.control(st, "og-key-61", { 100 }),
      R.control(st, "og-key-61", { 0 }) }, { {}, {} })
equal("... nor unmapped pressure -- pad-11-at", R.control(st, "pad-11-at", { 64 }), {})
equal("while a mapped key still leaves", R.control(st, "og-key-60", { 100 }),
      route("volca-key", 60, 100 / 127, 100 / 127, 1))
equal("... and MAPPED pressure leaves for its destination", R.control(st, "pad-13-at", { 64 }),
      route("volca-cc", 45, 64 / 127, 64 / 127, 1))
equal("a control with no value is 0, as [f] reads it",
      R.control(st, "slider-1", {}), route("volca-cc", 41, 0, 0, 1))
equal("... a symbol value too", R.control(st, "slider-1", { "x" }), route("volca-cc", 41, 0, 0, 1))
equal("a list of name and value is the same control", R.control(st, "list", { "slider-1", 127 }),
      route("volca-cc", 41, 1, 1, 1))
equal("a message with nothing in it does nothing", R.control(st, "bang", {}), {})

print("\n--- at load ---")
equal("init with a table says nothing", R.internal.init(R.new(MAP)), {})
equal("init with an empty one says map-empty", R.internal.init(R.new("")),
      { { "err", "fail", { "u_map", "map-empty" } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

print("\n--- the Pd face ---")
-- A patch folder of its own: the face reads cut-it-map.txt from there, as Pd's read did, and
-- asks whether a Save left a knobs.txt there.
local tmp = os.tmpname()
fh = assert(io.open(tmp .. "-cut-it-map.txt", "w"))
fh:write(MAP)
fh:close()
local unsaved_class = T.load_class(DIR .. "u_map-lua.pd_lua", DIR)
local fresh = T.new(unsaved_class, {}, tmp .. "-")
equal("no knobs.txt where its patch is: knob 1 is held at 120 from mother's first push",
      T.send(fresh, 1, "og-knob-1", { 0.0958 }),
      { { 1, "list", { "tempo", 0, C(0.0958), C(0.48), 0 } } })
check("... and that absence is silent on the console", #fresh.console == 0, T.show(fresh.console))
fh = assert(io.open(tmp .. "-knobs.txt", "w"))
fh:write("0.0957967 0.5 0.5 0.5;\n")
fh:close()
local class = T.load_class(DIR .. "u_map-lua.pd_lua", DIR)
check("u_map-lua.pd_lua registers the class u_map-lua", class and class._name == "u_map-lua",
      class and class._name)
local o = T.new(class, {}, tmp .. "-")
check("an object has four inlets and four outlets", o and o.inlets == 4 and o.outlets == 4,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the bang on outlet 4 that says it loaded, and nothing else",
      T.send(o, 3, "init", {}), { { 4, "bang", {} } })
equal("it read the table from its patch's folder: slider-1 is volca-cc 41, on outlet 1",
      T.send(o, 1, "slider-1", { 64 }), { { 1, "list", { "volca-cc", 41, 64 / 127, 64 / 127, 1 } } })
equal("an unmapped control leaves by no outlet at all", T.send(o, 1, "gk-x", { 64 }), {})
equal("a mode on inlet 2: the store on outlet 2", T.send(o, 2, "mode-4", {}),
      { { 2, "list", { "mode-4" } } })
equal("a bad one: err on outlet 3", T.send(o, 2, "compose", { "mode-1" }),
      { { 3, "fail", { "u_map", "bad-mode" } } })
T.send(o, 2, "mode-1", {})
T.send(o, 3, "window-shut", {})
equal("window-shut on inlet 3: a knob's first value now goes straight to live",
      { T.send(o, 1, "og-knob-1", { 0.5 })[1][3][5], T.send(o, 1, "og-knob-1", { 0.9 })[1][3][5] },
      { 1, 1 })
equal("anything else on inlet 3 is fail u_map bad-selector", T.send(o, 3, "beat", { 1 }),
      { { 3, "fail", { "u_map", "bad-selector" } } })
T.send(o, 3, "live", {})
T.send(o, 1, "og-knob-1", { 0.3 })
equal("a BPM on inlet 4 leaves nothing", T.send(o, 4, "float", { 150 }), {})
equal("... and holds knob 1 there: its next turn is held", T.send(o, 1, "og-knob-1", { 0.42 })[1][3][5], 0)
-- pdlua hands every message to dispatch, which this class answers itself.
local function dispatched(inlet, sel, atoms)
  o.sent = {}
  o:dispatch(inlet, sel, atoms)
  return o.sent
end
equal("dispatch takes each inlet's messages to its method: a control, a mode, init, a tempo",
      { dispatched(1, "slider-1", { 127 }), dispatched(2, "mode-1", {}),
        dispatched(3, "init", {}), dispatched(4, "float", { 120 }) },
      { { { 1, "list", { "volca-cc", 41, 1, 1, 1 } } }, { { 2, "list", { "mode-1" } } },
        { { 4, "bang", {} } }, {} })
equal("a knobs.txt where its patch is: mother's first push is a restore, and passes",
      T.send(T.new(class, {}, tmp .. "-"), 1, "og-knob-1", { 0.0958 }),
      { { 1, "list", { "tempo", 0, C(0.0958), C(0.0958), 1 } } })
os.remove(tmp .. "-cut-it-map.txt")
os.remove(tmp .. "-knobs.txt")

local missing = T.new(class, {}, tmp .. "-nowhere-")
check("no table where its patch is: an error on the console at load",
      #missing.console == 1 and missing.console[1]:find("cut-it-map.txt", 1, true) ~= nil,
      T.show(missing.console))
equal("... and map-empty on err at init, before the bang",
      T.send(missing, 3, "init", {}), { { 3, "fail", { "u_map", "map-empty" } }, { 4, "bang", {} } })

-- A Lua error, made by a copy of the rules whose control rule throws: the class reads its rules
-- as prefix .. "u_map.lua", so the copy sits at a temporary prefix.
fh = assert(io.open(tmp .. "-u_map.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'u_map.lua")\n',
         'R.control = function() error("a bug in control") end\nreturn R\n')
fh:close()
-- The face too, which the class reads from the same prefix.
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "u_map-lua.pd_lua", tmp .. "-"), {}, DIR)
os.remove(tmp .. "-u_map.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 3 as fail u_map lua-param, for the error log",
      T.send(broken, 1, "slider-1", { 64 }), { { 3, "fail", { "u_map", "lua-param" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in control", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a mode still answers",
      T.send(broken, 2, "mode-2", {}), { { 2, "list", { "mode-2" } } })

os.exit(T.report() == 0)
