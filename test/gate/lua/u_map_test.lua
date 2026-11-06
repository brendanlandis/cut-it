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

-- A small table: two pages, a knob, a fader, a key, pressure, and a row the route won't know.
local MAP = table.concat({
  "perform og-knob-1 tempo 0",
  "drums og-knob-1 tempo 0",
  "perform og-knob-2 volca-cc 42",
  "perform slider-1 volca-cc 41",
  "drums slider-1 volca-note 48",
  "perform og-key-60 volca-key 60",
  "perform pad-13-at volca-cc 45",
  "perform gk-bad no-such-destination 0",
}, "\n") .. "\n"

local function route(dest, arg, value, target, live)
  return { { "route", "list", { dest, arg, value, target, live } } }
end

-- What a control sends to its destination: what it tells u_perform has a section of its own.
local function control(st, sel, atoms)
  local out = {}
  for _, e in ipairs(R.control(st, sel, atoms)) do
    if e[1] ~= "heard" then out[#out + 1] = e end
  end
  return out
end


print("\n--- the table ---")
local map, rows = R.parse(MAP)
equal("a row is <page> <control> <dest> <arg>, the arg a number",
      map["perform"]["slider-1"], { dest = "volca-cc", arg = 41 })
equal("... and every row is counted, as [text size] counts lines", rows, 8)
map, rows = R.parse("perform a tempo 0\nperform a stop 0\n")
equal("a duplicate page and control: the FIRST row wins, as [text search] found it",
      map["perform"]["a"].dest, "tempo")
map, rows = R.parse("perform a tempo\nperform b stop 0 9\n\n  \nperform c start 0\n")
equal("a row of three or five atoms is skipped, and still counted; blank lines are not",
      { map["perform"]["a"], map["perform"]["b"], map["perform"]["c"].dest, rows },
      { nil, nil, "start", 3 })
map, rows = R.parse("perform a tempo 0; drums a stop 0")
equal("a ; ends a row too, as read -c has it", { map["drums"]["a"].dest, rows }, { "stop", 2 })
equal("an empty table is 0 rows", { R.parse("") }, { {}, 0 })
local fh = assert(io.open(DIR .. "cut-it-map.txt"))
local shipped = R.new(fh:read("a"))
fh:close()
-- The pages u_voices can put on the mode bus (ref/module/voices.md), which the rows are keyed on.
local PAGE_NAMES = { "perform", "drums", "harmony", "melody", "keys", "sound", "songs", "diag" }
local knobs, want_knobs = {}, {}
for _, page in ipairs(PAGE_NAMES) do
  for k, want in ipairs({ "tempo 0", "drums last", "drums track-last", "rush 0" }) do
    local r = R.lookup(shipped.map, page, "og-knob-" .. k)
    knobs[#knobs + 1] = r and (r.dest .. " " .. r.arg) or "none"
    want_knobs[#want_knobs + 1] = want
  end
end
equal("⛔ the shipped table parses: the Organelle's four knobs are the same on every page, tempo, last "
      .. "step, track last step and rush (Brendan, 2026-11-06)", knobs, want_knobs)
for name in pairs(shipped.map) do
  check("a shipped row's page is one u_voices can put on the bus, or all: " .. name,
        name == "all" or R.PAGES[name])
end

-- What a row names, read by the file it reaches: a misspelt one is a press that says bad-selector, or
-- nothing at all, on the rig.
local Melody, Voices, Steps = dofile(DIR .. "c_melody.lua"), dofile(DIR .. "u_voices.lua"), dofile(DIR .. "c_steps.lua")
local wrong = {}
for page, rows_of in pairs(shipped.map) do
  for control, row in pairs(rows_of) do
    local arg = row.arg
    local takes = true
    if row.dest == "melody" then
      takes = Melody.inputs[control == "pad-*" and arg .. "71" or arg] ~= nil
    elseif row.dest == "voices" then
      takes = Voices.controls[arg] ~= nil
    elseif row.dest == "perform" then
      takes = control == "pad-*" and arg == "pad-" or arg == "arm" or arg:match("^slider%-%d$") ~= nil
              or arg:match("^knob%-%d$") ~= nil or arg:match("^btn%-[ab]%-%d$") ~= nil
    end
    if not takes then wrong[#wrong + 1] = page .. " " .. control .. " " .. tostring(arg) end
  end
end
equal("⛔ every melody row's arg is an input of c_melody's, a voices row's a control of u_voices', a perform "
      .. "row's one of u_perform's", wrong, {})
-- Every address a control can be taken into play by, cut-it-controls.txt's, is one its destination takes.
fh = assert(io.open(DIR .. "cut-it-controls.txt"))
local controls = fh:read("a")
fh:close()
wrong = {}
local addresses = 0
for line in controls:gmatch("[^\n]+") do
  local dest, arg = line:match("^(%S+) (%S+) %S+ %S+$")
  if dest and line:sub(1, 1) ~= "#" then
    addresses = addresses + 1
    local takes = dest == "tempo" or dest == "rush"
    if dest == "melody" then takes = Melody.inputs[arg] ~= nil end
    if dest == "drums" then takes = Steps.presses[(arg:gsub("%*$", "1"))] ~= nil end
    if not takes then wrong[#wrong + 1] = dest .. " " .. arg end
  end
end
check("cut-it-controls.txt holds addresses to check", addresses > 20, addresses)
equal("⛔ every address cut-it-controls.txt names is one its destination takes", wrong, {})

print("\n--- the lookup ---")
local st = R.new(MAP)
equal("the key's page is perform from the start, before any page arrives", st.mode, "perform")
equal("a mapped control leaves for its destination: <dest> <arg> <value> <target> <live>",
      control(st, "slider-1", { 64 }), route("volca-cc", 41, 64 / 127, 64 / 127, 1))
R.mode(st, "drums", {})
equal("the same control on another page means that page's row -- volca-note 48",
      control(st, "slider-1", { 64 }), route("volca-note", 48, 64 / 127, 64 / 127, 1))
R.mode(st, "keys", {})
equal("a page with no row for it: the control is unmapped, and leaves nothing -- no bus, no row",
      R.control(st, "slider-1", { 64 }), {})
st = R.new(MAP)
equal("a row naming a destination the route lacks still leaves: the guard is the route's",
      R.control(st, "gk-bad", { 100 })[1], route("no-such-destination", 0, 100 / 127, 100 / 127, 1)[1])
st = R.new("all slider-1 tempo 0\ndrums slider-1 stop 0\nharmony pad-* melody h\nall pad-81 start 0\n"
           .. "harmony pad-82 stop 0\n")
equal("⛔ an all row is every page's", { control(st, "slider-1", { 127 })[1][3][1], st.mode },
      { "tempo", "perform" })
R.mode(st, "drums", {})
equal("⛔ a page's own row beats an all row", control(st, "slider-1", { 127 })[1][3][1], "stop")
R.mode(st, "harmony", {})
equal("⛔ pad-* appends the pad's number to its arg: pad-71 is melody h71", control(st, "pad-71", { 127 }),
      route("melody", "h71", 1, 1, 1))
equal("⛔ ... while an all row for the pad beats it, and a page's own row beats both",
      { control(st, "pad-81", { 127 })[1][3][1], control(st, "pad-82", { 127 })[1][3][1] },
      { "start", "stop" })
equal("... and a control that is no pad never matches it", control(st, "lp-cc-71", { 127 }), {})
R.mode(st, "drums", {})
equal("... and on a page with no pad-* row a pad is unmapped", control(st, "pad-71", { 127 }), {})

print("\n--- the divisor ---")
st = R.new("perform og-knob-3 volca-cc 43\nperform og-aux volca-cc 44\nperform slider-2 volca-cc 45\n")
R.internal.live(st)
equal("an Organelle knob is 0-1 already and passes as it is",
      R.control(st, "og-knob-3", { 0.5 })[1][3][3], 0.5)
equal("anything else is 0-127 and is divided -- og-aux included, it is no knob",
      { R.control(st, "og-aux", { 127 })[1][3][3], R.control(st, "slider-2", { 127 })[1][3][3] },
      { 1, 1 })

print("\n--- the mode bus ---")
st = R.new(MAP)
equal("drums: the key takes it, and nothing leaves: the page is u_voices' to keep",
      { R.mode(st, "drums", {}), st.mode }, { {}, "drums" })
for _, m in ipairs({ { "compose", {}, "compose alone, the name lost (item 294)" },
                     { "compose", { "perform" }, "the old two-atom form" },
                     { "perform", { "x" }, "a page with more after it" },
                     { "mode-1", {}, "a page's old name" }, { "float", { 3 }, "a float" },
                     { "bang", {}, "a bang" } }) do
  equal(m[3] .. " is refused: bad-mode", R.mode(st, m[1], m[2]),
        { { "err", "fail", { "u_map", "bad-mode" } } })
end
equal("... and the key survives every one of them", st.mode, "drums")
equal("a one-atom list naming a page is a page too", { R.mode(st, "list", { "harmony" }), st.mode },
      { {}, "harmony" })
equal("... and so is a symbol", { R.mode(st, "symbol", { "melody" }), st.mode }, { {}, "melody" })
for _, name in ipairs(PAGE_NAMES) do
  R.mode(st, name, {})
  equal("the page " .. name .. " is taken", st.mode, name)
end

print("\n--- what u_perform hears ---")
-- A control moved that could be taken into play, by way of the table, the phone's being its own.
st = R.new("all a melody smooth\nall b tempo 0\nall c perform slider-1\nall d voices left-1\n"
           .. "all e section 1\nall f melody h71\nall g melody m11\n")
equal("a voice's control on the table: its route, then heard <dest> <arg> <value>",
      R.control(st, "a", { 127 }), { { "route", "list", { "melody", "smooth", 1, 1, 1 } },
                                     { "heard", "list", { "melody", "smooth", 1 } } })
equal("the master's too", R.control(st, "b", { 127 })[2], { "heard", "list", { "tempo", 0, 1 } })
equal("⛔ a perform, voices or section row is no voice's control: nothing heard",
      { #R.control(st, "c", { 127 }), #R.control(st, "d", { 127 }), #R.control(st, "e", { 127 }) },
      { 1, 1, 1 })
equal("⛔ nor is a harmony or melody page's pad", { #R.control(st, "f", { 127 }), #R.control(st, "g", { 127 }) },
      { 1, 1 })
st = R.new("all og-knob-1 tempo 0\n", true)
equal("⛔ nor is a knob still held: the value isn't in force", #R.control(st, "og-knob-1", { 0.2 }), 1)

print("\n--- the tempo line ---")
local C = R.tempo_curve
local bpm = function(x) return math.floor(210 * C(x) + 40 + 0.5) end
equal("knob 1: a straight line, 40 BPM at the bottom, 145 at noon, 250 at the top",
      { bpm(0), bpm(0.5), bpm(1) }, { 40, 145, 250 })
fh = assert(io.open(DIR .. "u_map.pd"))
equal("... which is the patch's own c_mapped", fh:read("a"):match("c_mapped bpm (%d+ %d+);"), "210 40")
fh:close()
equal("... and only the tempo has a curve: a mapped CC passes its knob's value as it is",
      R.CURVES["volca-cc"], nil)

print("\n--- pickup ---")
-- R.new(MAP) is a boot after a Save: there is a knobs.txt, and mother's push is a restore.
st = R.new(MAP)
equal("a knob's first value inside the boot window passes",
      control(st, "og-knob-1", { 0.0958 }), route("tempo", 0, C(0.0958), C(0.0958), 1))
equal("... and arms it: the next value is HELD, carrying the stored target",
      control(st, "og-knob-1", { 0.5 }), route("tempo", 0, C(0.5), C(0.0958), 0))
equal("moving further away is still held", control(st, "og-knob-1", { 0.9 })[1][3][5], 0)
equal("CROSSING the target releases it, at the crossing value",
      control(st, "og-knob-1", { 0.02 }), route("tempo", 0, C(0.02), C(0.0958), 1))
equal("... and it is live from then on", control(st, "og-knob-1", { 0.3 })[1][3][5], 1)

st = R.new(MAP)
control(st, "og-knob-1", { 0.5 })
control(st, "og-knob-1", { 0.3 })
equal("armed BELOW the target: falling further is held",
      control(st, "og-knob-1", { 0.1 })[1][3][5], 0)
equal("... and rising through it releases", control(st, "og-knob-1", { 0.7 })[1][3][5], 1)

st = R.new(MAP)
control(st, "og-knob-1", { 0 })
equal("a target on the bottom rail: armed at 0, moving up is held",
      control(st, "og-knob-1", { 0.5 })[1][3][5], 0)
equal("... and coming back TO it releases -- a rail has no beyond",
      control(st, "og-knob-1", { 0 })[1][3][5], 1)

st = R.new(MAP)
control(st, "og-knob-1", { 0.2 })
control(st, "og-knob-2", { 0.5 })
control(st, "og-knob-1", { 0.6 })
control(st, "og-knob-1", { 0.1 })
equal("pickup is per knob: knob 1 crossed and is live, knob 2 is still held",
      { control(st, "og-knob-1", { 0.4 })[1][3][5], control(st, "og-knob-2", { 0.9 })[1][3][5] },
      { 1, 0 })
R.mode(st, "keys", {})
equal("a HELD knob unmapped in this mode leaves nothing either",
      control(st, "og-knob-2", { 0.75 }), {})
check("... and is still held", st.knob[2].state == "above", T.show(st.knob[2]))

st = R.new(MAP)
R.internal["window-shut"](st)
control(st, "og-knob-2", { 0.5 })
equal("a first value AFTER the window is a hand: never armed, the next passes too",
      control(st, "og-knob-2", { 0.9 }), route("volca-cc", 42, 0.9, 0.5, 1))

st = R.new(MAP)
control(st, "og-knob-1", { 0.2 })
control(st, "og-knob-1", { 0.6 })
R.internal.live(st)
equal("live: a held knob is live at once", control(st, "og-knob-1", { 0.7 })[1][3][5], 1)
equal("... and so is one that had never moved", control(st, "og-knob-2", { 0.4 })[1][3][5], 1)
check("... every slot", st.knob[3].state == "live" and st.knob[4].state == "live",
      T.show(st.knob))

print("\n--- nothing Saved: knob 1 held at 120 ---")
local AT120 = R.UNSAVED[1]
equal("it waits where the line puts 120 BPM", bpm(AT120), 120)
fh = assert(io.open(DIR .. "u_tempo.pd"))
local fallback = tonumber(fh:read("a"):match("#X msg %d+ %d+ (%d+);\n#X obj %d+ %d+ s tempo;"))
fh:close()
equal("... the same 120 u_tempo publishes when nothing else has", fallback, 120)
equal("... and no other knob has a place to be held at", { R.UNSAVED[2], R.UNSAVED[3], R.UNSAVED[4] },
      {})
st = R.new(MAP, true)
equal("mother's push of where knob 1 sits is HELD, at 120: the tempo stays u_tempo's",
      control(st, "og-knob-1", { 0.0958 }), route("tempo", 0, C(0.0958), AT120, 0))
equal("... moving it without reaching 120 is still held", control(st, "og-knob-1", { 0.3 }),
      route("tempo", 0, C(0.3), AT120, 0))
equal("... and turning it THROUGH 120 releases it, at the crossing value",
      control(st, "og-knob-1", { 0.5 }), route("tempo", 0, C(0.5), AT120, 1))
equal("... and it is live from then on", control(st, "og-knob-1", { 0.3 })[1][3][5], 1)
st = R.new(MAP, true)
equal("from above, it is held until it comes down through 120",
      { control(st, "og-knob-1", { 0.9 })[1][3][5], control(st, "og-knob-1", { 0.6 })[1][3][5],
        control(st, "og-knob-1", { 0.3 })[1][3][5] }, { 0, 0, 1 })
st = R.new(MAP, true)
local function passed(out) return { out[1][3][3], out[1][3][5] } end
equal("every other knob is live from its first value, inside the boot window or not",
      { passed(control(st, "og-knob-2", { 0.5 })), passed(control(st, "og-knob-2", { 0.9 })) },
      { { 0.5, 1 }, { 0.9, 1 } })
R.internal.live(st)
equal("a recover's live frees knob 1 too: after an emergency nothing is held",
      control(st, "og-knob-1", { 0.1 })[1][3][5], 1)

print("\n--- a tempo a tap or the phone set holds knob 1 again ---")
local P = R.tempo_position
equal("the line's inverse puts each BPM back where the knob sits for it",
      { bpm(P(50)), bpm(P(100)), bpm(P(150)), bpm(P(200)), bpm(P(240)) }, { 50, 100, 150, 200, 240 })
equal("⛔ a tempo past the knob's 40 to 250 holds it at the nearer end, a hair off the rail, so a pot that "
      .. "stops short still reaches it", { P(5), P(39), P(251), P(1000) }, { 0.01, 0.01, 0.99, 0.99 })
check("... and 120 is R.UNSAVED's, the one hold the knob has with nothing Saved",
      math.abs(P(120) - R.UNSAVED[1]) < 1e-9, T.show({ P(120), R.UNSAVED[1] }))
st = R.new(MAP)
R.internal.live(st)
control(st, "og-knob-1", { 0.3 })
equal("a tap's 150 leaves nothing: the bus already has it", R.hold_tempo(st, "float", { 150 }), {})
equal("... and knob 1's next turn is HELD at 150, the knob's own tempo in the value",
      control(st, "og-knob-1", { 0.42 }), route("tempo", 0, C(0.42), C(P(150)), 0))
equal("... held still, turned the same way", control(st, "og-knob-1", { 0.5 })[1][3][5], 0)
equal("... and turned THROUGH 150 it is live, at the crossing value",
      control(st, "og-knob-1", { 0.68 }), route("tempo", 0, C(0.68), C(P(150)), 1))
R.hold_tempo(st, "float", { 100 })
equal("the phone's tempo holds it again, from above this time",
      { control(st, "og-knob-1", { 0.9 })[1][3][5], control(st, "og-knob-1", { 0.2 })[1][3][5] },
      { 0, 1 })
R.hold_tempo(st, "float", { 500 })
equal("⛔ held at a tempo past its reach, its row still reads that tempo: 40 + 210 * target is 500",
      control(st, "og-knob-1", { 0.5 }), route("tempo", 0, 0.5, 460 / 210, 0))
equal("⛔ ... and it is released by reaching the top, a hair short of the rail",
      control(st, "og-knob-1", { 0.995 })[1][3][5], 1)
st = R.new(MAP)
R.internal.live(st)
R.mode(st, "keys", {})
R.hold_tempo(st, "float", { 150 })
equal("on a page whose knob 1 is no tempo, the hold leaves it alone", st.knob[1].state, "live")
st = R.new(MAP)
R.internal.live(st)
R.hold_tempo(st, "symbol", { "fast" })
equal("... and a tempo that is no number holds nothing", st.knob[1].state, "live")
equal("... and no other knob is held by a tempo", { st.knob[2].state, st.knob[3].state, st.knob[4].state },
      { "live", "live", "live" })

st = R.new("perform xport-2 start 0\n")
equal("a button is never held: PLAY twice is live twice",
      { control(st, "xport-2", { 1 })[1][3][5], control(st, "xport-2", { 1 })[1][3][5] },
      { 1, 1 })

print("\n--- an unmapped control names nothing ---")
-- Only a control the map binds names itself (Brendan, 2026-11-04).
st = R.new(MAP)
equal("an unmapped control leaves nothing: no <name> <raw> row, no bus",
      control(st, "gk-x", { 64 }), {})
equal("... a press of an unmapped pad neither", control(st, "pad-15", { 100 }), {})
equal("... nor an unmapped key or its release", { control(st, "og-key-61", { 100 }),
      control(st, "og-key-61", { 0 }) }, { {}, {} })
equal("... nor unmapped pressure -- pad-11-at", control(st, "pad-11-at", { 64 }), {})
equal("while a mapped key still leaves", control(st, "og-key-60", { 100 }),
      route("volca-key", 60, 100 / 127, 100 / 127, 1))
equal("... and MAPPED pressure leaves for its destination", control(st, "pad-13-at", { 64 }),
      route("volca-cc", 45, 64 / 127, 64 / 127, 1))
equal("a control with no value is 0, as [f] reads it",
      control(st, "slider-1", {}), route("volca-cc", 41, 0, 0, 1))
equal("... a symbol value too", control(st, "slider-1", { "x" }), route("volca-cc", 41, 0, 0, 1))
equal("a list of name and value is the same control", control(st, "list", { "slider-1", 127 }),
      route("volca-cc", 41, 1, 1, 1))
equal("a message with nothing in it does nothing", control(st, "bang", {}), {})

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
      { { 1, "list", { "tempo", 0, C(0.0958), AT120, 0 } } })
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
equal("init: the bang on outlet 3 that says it loaded, and nothing else",
      T.send(o, 3, "init", {}), { { 3, "bang", {} } })
equal("it read the table from its patch's folder: slider-1 is volca-cc 41, on outlet 1, and u_perform "
      .. "hears of it on outlet 4",
      T.send(o, 1, "slider-1", { 64 }), { { 1, "list", { "volca-cc", 41, 64 / 127, 64 / 127, 1 } },
                                          { 4, "list", { "volca-cc", 41, 64 / 127 } } })
equal("an unmapped control leaves by no outlet at all", T.send(o, 1, "gk-x", { 64 }), {})
equal("a page on inlet 2 leaves nothing, the key takes it", { T.send(o, 2, "keys", {}), o.state.mode },
      { {}, "keys" })
equal("a bad one: err on outlet 2", T.send(o, 2, "compose", { "perform" }),
      { { 2, "fail", { "u_map", "bad-mode" } } })
T.send(o, 2, "perform", {})
T.send(o, 3, "window-shut", {})
equal("window-shut on inlet 3: a knob's first value now goes straight to live",
      { T.send(o, 1, "og-knob-1", { 0.5 })[1][3][5], T.send(o, 1, "og-knob-1", { 0.9 })[1][3][5] },
      { 1, 1 })
equal("anything else on inlet 3 is fail u_map bad-selector", T.send(o, 3, "beat", { 1 }),
      { { 2, "fail", { "u_map", "bad-selector" } } })
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
      { dispatched(1, "slider-1", { 127 })[1], dispatched(2, "perform", {}),
        dispatched(3, "init", {}), dispatched(4, "float", { 120 }) },
      { { 1, "list", { "volca-cc", 41, 1, 1, 1 } }, {}, { { 3, "bang", {} } }, {} })
equal("a knobs.txt where its patch is: mother's first push is a restore, and passes",
      T.send(T.new(class, {}, tmp .. "-"), 1, "og-knob-1", { 0.0958 })[1],
      { 1, "list", { "tempo", 0, C(0.0958), C(0.0958), 1 } })
os.remove(tmp .. "-cut-it-map.txt")
os.remove(tmp .. "-knobs.txt")

local missing = T.new(class, {}, tmp .. "-nowhere-")
check("no table where its patch is: an error on the console at load",
      #missing.console == 1 and missing.console[1]:find("cut-it-map.txt", 1, true) ~= nil,
      T.show(missing.console))
equal("... and map-empty on err at init, before the bang",
      T.send(missing, 3, "init", {}), { { 2, "fail", { "u_map", "map-empty" } }, { 3, "bang", {} } })

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
equal("a Lua error leaves outlet 2 as fail u_map lua-param, for the error log",
      T.send(broken, 1, "slider-1", { 64 }), { { 2, "fail", { "u_map", "lua-param" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in control", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a page still lands",
      { T.send(broken, 2, "drums", {}), broken.state.mode }, { {}, "drums" })

print("\n--- a knob mapped to rush ---")
local RUSHING = "perform og-knob-4 rush 0\nperform og-knob-1 tempo 0\nperform og-knob-2 volca-cc 42\n"
local AT_120 = R.rush_position(120)
for _, unsaved in ipairs({ false, true }) do
  local q = R.new(RUSHING, unsaved)
  local live = function(x) return control(q, "og-knob-4", { x })[1][3][5] end
  equal("⛔ held at load at 120, Saved or not (" .. tostring(unsaved) .. "), and its value still leaves, for its row",
        control(q, "og-knob-4", { 0.7 }), route("rush", 0, 0.7, AT_120, 0))
  equal("⛔ inside the boot window a value may be knobs.txt's, so even past 120 it stays held", live(0.1), 0)
  R.internal["window-shut"](q)
  equal("still held on the side its first value finds", live(0.7), 0)
  R.internal.live(q)
  equal("⛔ a recover does not free it: left up it would jump the moment it was touched", live(0.7), 0)
  equal("⛔ turned through the tempo in force it lets go", live(0.2), 1)
  equal("... and is live from then on", live(0.9), 1)
end
local q = R.new(RUSHING, true)
R.internal["window-shut"](q)
control(q, "og-knob-4", { 0.7 })
control(q, "og-knob-4", { 0.2 })
local at = R.tempo_position(R.rush_bpm(0.2))
check("⛔ a knob 4 move holds knob 1 at that tempo", q.knob[1].state == "armed"
      and math.abs(q.knob[1].target - at) < 1e-9, T.show(q.knob[1]))
control(q, "og-knob-4", { 0.9 })
check("⛔ ... at 1000, past the handoff, what the bus stays at", q.knob[1].target == R.tempo_position(1000), q.knob[1].target)
control(q, "og-knob-1", { 1 })
local moved = control(q, "og-knob-1", { 0.5 })
equal("⛔ knob 1 turned through it: rush told first, then its tempo", moved[1], route("rush", 0, -1, 0, 1)[1])
check("... once", #control(q, "og-knob-1", { 0.51 }) == 1)
check("⛔ ... and knob 4 is held at knob 1's tempo", q.knob[4].state == "armed"
      and math.abs(q.knob[4].target - R.rush_position(40 + 210 * 0.51)) < 1e-9, T.show(q.knob[4]))
R.hold_tempo(q, "float", { 300 })
check("⛔ a tempo from a tap, the phone, a section or a pad holds both", q.knob[4].target == R.rush_position(300)
      and q.knob[1].target == R.tempo_position(300) and not q.rushing, T.show(q.knob))
equal("⛔ a tempo below its 10 BPM holds it at its bottom, a hair off the rail, so a pot that stops short still reaches it",
      { R.rush_position(5), R.rush_position(10) }, { 0.01, 0.01 })
equal("another destination on that knob is not held for it",
      R.new("perform og-knob-4 volca-cc 44\n", true).knob[4].state, "live")

os.exit(T.report() == 0)
