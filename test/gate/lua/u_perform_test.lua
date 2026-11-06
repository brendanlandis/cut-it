-- The controls in play, without Pd: "Cut It/u_perform.lua", and the Pd face that carries it,
-- "Cut It/u_perform-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The voices gate runs
-- this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/u_perform_test.lua [-v]
--
-- What a control does once it reaches the map's route is voices-assert.py's, on a running copy of
-- the instrument. ref/module/voices.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "u_perform.lua")
local check, equal = T.check, T.equal

local fh = assert(io.open(DIR .. "cut-it-controls.txt"))
local TABLE = fh:read("a")
fh:close()

local function route(dest, arg, value)
  return { { "route", "list", { dest, arg, value, value, 1 } } }
end
-- The state with this control taken into play on this physical control, its value where it is.
local function bound(name, dest, arg, row, value)
  local st = R.new(TABLE)
  R.arm(st, 1)
  R.heard(st, row or 0, dest, arg, value or 0.5)
  R.control(st, name, name:match("^btn") and 1 or value or 0.5)
  return st
end

print("\n--- the table ---")
local t = R.parse("# a comment\ntempo 0 value tempo\nmelody roll hit again\nshort line\n")
equal("a line is <dest> <arg> <kind> <label>, a # a comment, a short one nothing",
      t, { ["tempo 0"] = { kind = "value", label = "tempo" }, ["melody roll"] = { kind = "hit", label = "again" } })
check("⛔ the shipped table parses: tempo and a roll among its rows",
      R.new(TABLE).controls["tempo 0"] and R.new(TABLE).controls["melody roll-melody"].kind == "hit")

print("\n--- arm, heard, bind ---")
local st = R.new(TABLE)
equal("REC: armed, waiting for a control", { R.arm(st, 1), st.armed }, { {}, 1 })
equal("... its release does nothing", { R.arm(st, 0), st.armed }, { {}, 1 })
R.heard(st, 2, "melody", "unknown-one", 0.4)
equal("a control not in the table isn't taken", st.armed, 1)
R.heard(st, 2, "melody", "smooth", 0.4)
equal("⛔ one in the table is: armed, waiting for a physical control", { st.armed, st.heard },
      { 2, { dest = "melody", arg = "smooth", row = 2, value = 0.4 } })
R.heard(st, 3, "melody", "tension", 0.1)
equal("... a second heard doesn't take over", st.heard.arg, "smooth")
local out = R.control(st, "slider-3", 0.7)
equal("⛔ the physical control binds to it, sending nothing, live where it is", { out, st.armed, st.list["slider-3"] },
      { {}, 0, { dest = "melody", arg = "smooth", row = 2, value = 0.7, live = true } })
check("... and it's to be saved", st.dirty == true)
st = R.new(TABLE)
R.arm(st, 1)
R.arm(st, 1)
equal("⛔ REC again: not armed", st.armed, 0)
equal("⛔ an address Pd hands over as a float is the table's: tempo 0.0 is tempo 0", (function()
  local s = R.new(TABLE)
  R.arm(s, 1)
  R.heard(s, 0, "tempo", 0.0, 0.5)
  return s.armed
end)(), 2)

print("\n--- in play ---")
st = bound("slider-1", "tempo", 0, 0, 0.5)
equal("⛔ a fader in play goes to the map's route, as a mapped control's", R.control(st, "slider-1", 0.6),
      route("tempo", 0, 0.6))
equal("a physical control in play for nothing says nothing", R.control(st, "slider-2", 0.6), {})
equal("past the eight groups, nothing", R.control(st, "slider-9", 0.6), {})
st = bound("slider-1", "melody", "smooth", 2, 0.5)
R.internal.rows(st, { 2, 0, 2, 0, 0, 0, 0, 0, 0 })
equal("⛔ a generator's control names its engine, whichever is on show", R.control(st, "slider-1", 0.6),
      route("melody", "e2-smooth", 0.6))
equal("a button's release does nothing", (function()
  local s = bound("btn-a-1", "tempo", 0)
  return R.control(s, "btn-a-1", 0)
end)(), {})

print("\n--- pickup ---")
st = bound("slider-1", "tempo", 0, 0, 0.5)
R.restore(st, { "slider-1", "tempo", 0, 0, 0.5 })
equal("⛔ restored, a control waits: held at its value", { R.control(st, "slider-1", 0.2), st.list["slider-1"].live },
      { {}, false })
equal("... still held, moving on the same side", R.control(st, "slider-1", 0.3), {})
equal("⛔ turned through its value, it's caught", R.control(st, "slider-1", 0.6), route("tempo", 0, 0.6))
check("... and live from then on", st.list["slider-1"].live)
R.restore(st, { "slider-1", "tempo", 0, 0, 0.5 })
equal("⛔ turned to it, it's caught too", R.control(st, "slider-1", 0.505), route("tempo", 0, 0.505))
R.restore(st, { "slider-1", "tempo", 0, 0, 0.5 })
R.control(st, "slider-1", 0.8)
equal("from above, it waits for below", { R.control(st, "slider-1", 0.7), #R.control(st, "slider-1", 0.3) }, { {}, 1 })
st = bound("slider-1", "tempo", 0, 0, 0.5)
R.heard(st, 0, "tempo", 0, 0.9)
equal("⛔ moved another way, a control follows it and waits again", { st.list["slider-1"].value, st.list["slider-1"].live },
      { 0.9, false })
equal("... so its physical control jumps nothing", R.control(st, "slider-1", 0.2), {})

print("\n--- a section's list ---")
st = bound("slider-1", "tempo", 0, 0, 0.5)
equal("⛔ the section starting holds this list, each control waiting", (function()
  R.restore(st, { "knob-2", "rush", 0, 0, 0.25, "btn-a-3", "melody", "on-h", 2, 1 })
  return { st.list["slider-1"], st.list["knob-2"], st.list["btn-a-3"], st.armed }
end)(), { nil, { dest = "rush", arg = 0, row = 0, value = 0.25, live = false },
          { dest = "melody", arg = "on-h", row = 2, value = 1, live = false }, 0 })
R.arm(st, 1)
equal("⛔ one with none: none in play, and not armed", { R.restore(st, {}), next(st.list), st.armed }, { {}, nil, 0 })

print("\n--- toggle and hit ---")
st = bound("btn-a-1", "melody", "on-h", 2, 0)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a toggle on a button: each press says so, the state flips", { R.control(st, "btn-a-1", 1), st.list["btn-a-1"].value },
      { route("melody", "e1-on-h", 1), 1 })
equal("... and back", { R.control(st, "btn-a-1", 1), st.list["btn-a-1"].value }, { route("melody", "e1-on-h", 1), 0 })
R.heard(st, 2, "melody", "on-h", 1)
equal("⛔ moved on its own page, a toggle flips the state it shows", st.list["btn-a-1"].value, 1)
st = bound("slider-1", "melody", "on-h", 2, 0.2)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a toggle on a fader flips as it passes a half, and only then", { R.control(st, "slider-1", 0.3),
      R.control(st, "slider-1", 0.6), R.control(st, "slider-1", 0.7), R.control(st, "slider-1", 0.1) },
      { {}, route("melody", "e1-on-h", 1), {}, route("melody", "e1-on-h", 1) })
st = bound("btn-b-1", "melody", "roll-chords", 2, 1)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a hit on a button: every press", { R.control(st, "btn-b-1", 1), R.control(st, "btn-b-1", 1) },
      { route("melody", "e1-roll-chords", 1), route("melody", "e1-roll-chords", 1) })
st = bound("knob-1", "melody", "roll-chords", 2, 0.2)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a hit on a knob: once, as it passes a half, or a sweep would be a roll a message",
      { R.control(st, "knob-1", 0.6), R.control(st, "knob-1", 0.7), R.control(st, "knob-1", 0.2),
        R.control(st, "knob-1", 0.8) },
      { route("melody", "e1-roll-chords", 1), {}, {}, route("melody", "e1-roll-chords", 1) })
st = bound("btn-a-1", "tempo", 0, 0, 0)
equal("a button on a value goes to its top and back", { R.control(st, "btn-a-1", 1), R.control(st, "btn-a-1", 1) },
      { route("tempo", 0, 1), route("tempo", 0, 0) })

print("\n--- the Launchpad's columns ---")
st = bound("slider-2", "tempo", 0, 0, 0.5)
local function col(s, lane)
  local c = R.cols(s)
  return { c[(lane - 1) * 3 + 1], c[(lane - 1) * 3 + 2], c[(lane - 1) * 3 + 3] }
end
equal("nothing in play: kind 0, level 0, not held", col(st, 1), { 0, 0, 0 })
equal("⛔ a fader's column: kind 1, its level of eight, not held", col(st, 2), { 1, 4, 0 })
out = R.pad(st, 62, 1)
equal("⛔ a tap in its column sets it to that height, row 6 of 8, and it waits for its control",
      { out, col(st, 2) }, { route("tempo", 0, 0.75), { 1, 6, 1 } })
equal("a release does nothing", R.pad(st, 62, 0), {})
equal("a column with nothing in play does nothing", R.pad(st, 63, 1), {})
st = bound("knob-2", "tempo", 0, 0, 0.5)
equal("⛔ a knob alone: kind 2", col(st, 2), { 2, 4, 0 })
equal("... and a tap sets it, with no fader", R.pad(st, 82, 1), route("tempo", 0, 1))
st = bound("slider-1", "tempo", 0, 0, 0.5)
R.arm(st, 1)
R.heard(st, 0, "rush", 0, 0.25)
R.control(st, "knob-1", 0.25)
equal("⛔ with both, whichever moved last: the knob, just bound", col(st, 1), { 2, 2, 0 })
R.control(st, "slider-1", 0.5)
equal("⛔ ... then the fader", col(st, 1), { 1, 4, 0 })
R.control(st, "knob-1", 0.5)
equal("⛔ ... then the knob, even while it's held", col(st, 1)[1], 2)
st = bound("slider-1", "melody", "on-h", 2, 0)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a tap on a toggle's column flips it, as a press", { R.pad(st, 31, 1), st.list["slider-1"].value },
      { route("melody", "e1-on-h", 1), 1 })
st = bound("slider-1", "melody", "roll-chords", 2, 0)
R.internal.rows(st, { 2, 0, 1, 0, 0, 0, 0, 0, 0 })
equal("⛔ a tap on a hit's column hits it", R.pad(st, 31, 1), route("melody", "e1-roll-chords", 1))

print("\n--- the lights, and the phone ---")
st = bound("btn-a-2", "melody", "on-h", 3, 1)
local b = R.btns(st)
equal("⛔ a button's light: the top row's second, its voice's row, on above a half", { b[3], b[4], b[1], b[2] },
      { 3, 1, 0, 0 })
R.arm(st, 1)
R.heard(st, 0, "tempo", 0, 0.25)
R.control(st, "btn-b-1", 1)
b = R.btns(st)
equal("⛔ the bottom row's first, a global control lit in row 1's color, its state off", { b[17], b[18] }, { 1, 0 })
st = bound("slider-1", "tempo", 0, 0, 0.5)
local ph = R.phone(st)
equal("the phone: armed, then a group's knob and fader, label, row, value and held, and its two buttons: 113 atoms",
      { #ph, ph[1], ph[2], ph[6], ph[7], ph[8], ph[9] }, { 113, 0, "-", "tempo", 0, 0.5, 0 })
equal("⛔ a name tapped takes it out of play", { R.remove(st, "slider-1"), st.list["slider-1"] }, { {}, nil })
equal("... one not there is nothing", R.remove(st, "slider-1"), {})

print("\n--- from the phone ---")
st = R.new(TABLE)
R.phone_cmds.arm(st)
equal("arm", st.armed, 1)
equal("⛔ ctl: any of a voice's controls goes to the route, heard as it passes",
      { R.phone_cmds.ctl(st, { 2, "melody", "smooth", 0.25 }), st.armed },
      { route("melody", "e1-smooth", 0.25), 2 })
equal("a ctl with no dest fails", R.phone_cmds.ctl(st, { 2 }), { { "err", "fail", { "u_perform", "bad-ctl" } } })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "u_perform-lua.pd_lua", DIR)
local o = T.new(class, {}, DIR)
check("an object has three inlets and six outlets, and read the table", o.inlets == 3 and o.outlets == 6
      and o.state.controls["tempo 0"] ~= nil)
equal("init: the bang on outlet 6", T.send(o, 3, "init", {}), { { 6, "bang", {} } })
T.send(o, 1, "arm", { 1 })
T.send(o, 3, "heard", { "tempo", 0.0, 0.5 })
equal("u_map's slider-1 binds it: nothing sent", T.send(o, 1, "slider-1", { 0.5 }), {})
equal("⛔ a fader's next move: outlet 1, the map's route", T.send(o, 1, "slider-1", { 0.6 }),
      { { 1, "list", { "tempo", 0.0, 0.6, 0.6, 1 } } })
local shown = T.fire(o, o.show_clock)
equal("⛔ the surfaces hear on a clock: cols and btns on outlet 2, perform on 3",
      { shown[1][1], shown[1][2], shown[2][2], shown[3][1], shown[3][2] }, { 2, "cols", "btns", 3, "perform" })
local saved = T.fire(o, o.save_clock)
equal("⛔ the song store on a slower one: perform on outlet 4, name, dest, arg, row and value", saved,
      { { 4, "perform", { "slider-1", "tempo", 0.0, 0, 0.6 } } })
T.send(o, 1, "slider-1", { 0.6 })
equal("nothing changed, the surfaces hear nothing", T.fire(o, o.show_clock), {})
equal("⛔ pad-<nn> on inlet 1 is a column's", T.send(o, 1, "pad-41", { 1 }),
      { { 1, "list", { "tempo", 0.0, 0.5, 0.5, 1 } } })
T.send(o, 3, "restore", {})
equal("restore on inlet 3 takes it all away", next(o.state.list), nil)
equal("a phone command it doesn't know is bad-selector, on outlet 5", T.send(o, 2, "shuffle", {}),
      { { 5, "fail", { "u_perform", "bad-selector" } } })

print("\n--- a drum control into play ---")
do
  local text = assert(io.open("Cut It/cut-it-controls.txt")):read("a")
  local st = R.new(text)
  R.arm(st, 1)
  R.heard(st, 1, "drums", "drive-3", 0.5)
  equal("⛔ a track's control is known by its table row, track and all", st.armed, 2)
  R.control(st, "slider-2", 0.2)
  equal("⛔ bound", st.list["slider-2"].arg, "drive-3")
  equal("⛔ it moves that track's", R.control(st, "slider-2", 0.4),
        { { "route", "list", { "drums", "drive-3", 0.4, 0.4, 1 } } })
  equal("⛔ the phone names it with its track", R.phone(st)[1 + 14 + 4 + 1], "drive-3")
end

os.exit(T.report() == 0)
