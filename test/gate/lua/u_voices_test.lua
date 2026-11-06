-- A song's voices and the page on show, without Pd: "Cut It/u_voices.lua", and the Pd face that
-- carries it, "Cut It/u_voices-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The voices
-- gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/u_voices_test.lua [-v]
--
-- What the map, the grid and the engines do with these answers is voices-assert.py's and
-- display-assert.py's, on a running copy of the instrument. ref/module/voices.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "u_voices.lua")
local check, equal = T.check, T.equal

-- What an answer says, by its first field.
local function of(out, what)
  local r = {}
  for _, e in ipairs(out) do if e[1] == what then r[#r + 1] = e end end
  return r
end
-- The page an answer puts on the mode bus, or nil.
local function page(out)
  local m = of(out, "mode")
  return m[#m] and m[#m][2]
end
local function seeded()
  local st = R.new()
  R.restore(st, {})
  return st
end

print("\n--- a song's voices ---")
local st = R.new()
equal("before anything: the performance page, no voice", { st.kind, st.row, R.page_name(st), R.grid(st)[3] },
      { "perform", 0, "perform", "-" })
local out = R.restore(st, {})
equal("⛔ a song with none is seeded: its old drum page and the generator's two lines",
      { st.voices[1], st.voices[2], st.voices[3], st.voices[4] },
      { { name = "drums", method = "drums", machine = "kit" },
        { name = "chords", method = "harmony", machine = "strings" },
        { name = "melody", method = "melody", machine = "fm" } })
equal("⛔ ... and saved so, first, as a seed: no change to the song", out[1],
      { "seed", "seed", { "drums", "drums", "kit", "chords", "harmony", "strings", "melody", "melody", "fm",
        "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-" } })
equal("... and says the page, which is the performance page's", page(out), "perform")
local line = R.line(st)
local other = R.new()
out = R.restore(other, line)
equal("⛔ restoring what it holds: the same voices, and no seed and no save", { other.voices, #of(out, "seed"),
      #of(out, "save") }, { st.voices, 0, 0 })
equal("a row with a method or machine it doesn't know is no voice", (function()
  local s = R.new()
  R.restore(s, { "a", "organ", "fm", "b", "keys", "fm" })
  return { s.voices[1], s.voices[2].name }
end)(), { nil, "b" })

print("\n--- the left button ---")
st = seeded()
out = R.left(st, 1)
equal("⛔ a voice's left button: its page, its method's name on the mode bus", { page(out), st.kind, st.row },
      { "drums", "voice", 1 })
equal("... and the last power-off's page is saved as this one", of(out, "page")[1], { "page", "page", { "voice", 1 } })
equal("another's, harmony", page(R.left(st, 2)), "harmony")
equal("⛔ the lit one again: back to the performance page", { page(R.left(st, 2)), st.kind, st.row },
      { "perform", "perform", 0 })
equal("⛔ a row with no voice does nothing", { R.left(st, 5), st.kind }, { {}, "perform" })

print("\n--- the right button ---")
st = seeded()
equal("⛔ a voice's right button: its setup page, sound", { page(R.right(st, 2)), st.kind, st.row },
      { "sound", "setup", 2 })
equal("⛔ the lit one again: back to the performance page", { page(R.right(st, 2)), st.kind },
      { "perform", "perform" })
R.left(st, 2)
equal("from its left page, its right button goes across", { page(R.right(st, 2)), st.kind }, { "sound", "setup" })
out = R.right(st, 5)
equal("⛔ an unused row's: a new voice on it, keys, on a machine no other has, and its setup page",
      { st.voices[5], page(out), st.row }, { { name = "voice_5", method = "keys", machine = "fm" }, "sound", 5 })
equal("... and the song holds it", of(out, "save")[1][2], "voices")
equal("a row off the eight does nothing", R.right(st, 9), {})

print("\n--- aux, and Setup ---")
st = seeded()
R.left(st, 2)
equal("⛔ aux: the songs page, from anywhere", { page(R.aux(st)), st.row }, { "songs", 0 })
equal("⛔ aux again: back where it was", { page(R.aux(st)), st.kind, st.row }, { "harmony", "voice", 2 })
equal("⛔ Setup: the diagnostics page, the same way", page(R.setup(st)), "diag")
equal("⛔ Setup again: back where it was", { page(R.setup(st)), st.row }, { "harmony", 2 })
R.aux(st)
R.setup(st)
equal("⛔ opened over each other, each closes back to what it opened over: diag to songs, songs to the voice",
      { page(R.setup(st)), page(R.aux(st)), st.row }, { "songs", "harmony", 2 })
R.aux(st)
R.remove(st, { 2 })
equal("⛔ a voice that went while they were open comes back as the performance page", page(R.aux(st)), "perform")

print("\n--- PLAY ---")
st = seeded()
R.left(st, 1)
equal("⛔ PLAY: the performance page, from a voice's page", { page(R.start(st)), st.kind }, { "perform", "perform" })
R.right(st, 1)
equal("⛔ ... and its setup page", page(R.start(st)), "perform")
R.aux(st)
equal("⛔ not from the songs page", { R.start(st), st.kind }, { {}, "songs" })
R.aux(st)
R.setup(st)
equal("⛔ nor the diagnostics", { R.start(st), st.kind }, { {}, "diag" })
R.setup(st)

print("\n--- the engines ---")
st = seeded()
R.right(st, 5)
out = R.set_method(st, { 5, "melody" })
equal("⛔ each line of each engine is told its voice's machine, by row order: row 3 and row 5 the melody's",
      { table.unpack(of(out, "engine"), 1, 4) },
      { { "engine", "assign", { 1, "h", "strings" } }, { "engine", "assign", { 1, "m", "fm" } },
        { "engine", "assign", { 2, "h", "off" } }, { "engine", "assign", { 2, "m", "fm" } } })
equal("⛔ a voice's page says which engine it is in", of(R.left(st, 5), "engine")[1],
      { "engine", "active", { 2 } })
equal("... a keys voice in none", (function()
  local s = seeded()
  R.right(s, 4)
  return of(R.left(s, 4), "engine")[1]
end)(), { "engine", "active", { 0 } })
equal("u_perform is told the row on show and each row's engine", of(R.left(st, 3), "perform")[1],
      { "perform", "rows", { 3, 0, 1, 1, 0, 2, 0, 0, 0 } })
equal("⛔ the nanoKEY plays a hardware voice's machine, unsaved: machine, to c_synth", of(R.left(st, 2), "synth")[1],
      { "synth", "machine", { "strings" } })
R.set_machine(st, { 5, "saw" })
equal("... and is left on the last for one that's no hardware", of(R.left(st, 5), "synth"), {})

print("\n--- too many, and the phone's voice page ---")
st = seeded()
R.right(st, 4)
R.right(st, 5)
R.right(st, 6)
equal("a second harmony voice is fine: there are two engines", #of(R.set_method(st, { 4, "harmony" }), "save"), 1)
equal("⛔ a third warns, and changes nothing", { R.set_method(st, { 5, "harmony" }), st.voices[5].method },
      { { { "err", "warn", { "u_voices", "too-many-harmony" } } }, "keys" })
equal("⛔ so does a second drum voice", R.set_method(st, { 6, "drums" }),
      { { "err", "warn", { "u_voices", "too-many-drums" } } })
st = seeded()
R.right(st, 4)
equal("as many keys voices as there are rows", #of(R.set_method(st, { 4, "keys" }), "save"), 0)
out = R.set_method(st, { 3, "keys" })
equal("⛔ a method that can play on its machine keeps it", { st.voices[3].machine, #of(out, "save") }, { "fm", 1 })
equal("⛔ a method that can't takes the first one free", (function()
  local s = seeded()
  R.set_method(s, { 1, "keys" })
  return s.voices[1].machine
end)(), "fm")
equal("a method it doesn't know fails", R.set_method(st, { 3, "dance" }), { { "err", "fail", { "u_voices", "bad-method" } } })
equal("⛔ the page follows, if it's on this voice", (function()
  local s = seeded()
  R.left(s, 3)
  return page(R.set_method(s, { 3, "keys" }))
end)(), "keys")
equal("⛔ a machine: the song holds it", { #of(R.set_machine(st, { 2, "saw" }), "save"), st.voices[2].machine }, { 1, "saw" })
equal("one the method can't play on fails", R.set_machine(st, { 1, "fm" }), { { "err", "fail", { "u_voices", "bad-machine" } } })
equal("⛔ a name: lowercase, one symbol, as long as a song's", (function()
  R.rename(st, { 3, "My", "Lead", "Line", "With", "Far", "Too", "Many" })
  return st.voices[3].name
end)(), "my_lead_line_wit")
equal("the same name again changes nothing", R.rename(st, { 3, "my_lead_line_wit" }), {})
out = R.remove(st, { 4 })
equal("a voice removed: the song holds that", { st.voices[4], #of(out, "save") }, { nil, 1 })
R.left(st, 3)
equal("⛔ ... on show, back to the performance page", page(R.remove(st, { 3 })), "perform")

print("\n--- the page across a power cycle ---")
st = R.new()
equal("⛔ a voice's page before the song is read waits: the auto file comes first", R.restore_page(st, { "voice", 2 }), {})
equal("⛔ ... and comes up when its voices do", { page(R.restore(st, {})), st.kind, st.row }, { "harmony", "voice", 2 })
st = R.new()
R.restore_page(st, { "setup", 7 })
equal("... unless the song holds no such voice", { page(R.restore(st, {})), st.kind }, { "perform", "perform" })
st = seeded()
equal("a page of its own comes straight back", page(R.restore_page(st, { "songs", 0 })), "songs")
equal("one it doesn't know is nothing", R.restore_page(st, { "compose", 0 }), {})
st = seeded()
R.left(st, 3)
equal("⛔ a song with no such row: off that page, to the performance page", page(R.restore(st, { "a", "keys", "fm" })),
      "perform")

print("\n--- what the surfaces show ---")
st = seeded()
R.right(st, 2)
equal("g_grid: the row on show, the kind, each row's method", { table.unpack(R.grid(st), 1, 6) },
      { 2, "setup", "drums", "harmony", "melody", "-" })
local ph = R.phone(st)
equal("the phone: the page's name, kind and row, then the voices, three atoms each: 27", { #ph, ph[1], ph[2], ph[3],
      ph[4], ph[8] }, { 27, "sound", "setup", 2, "drums", "harmony" })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "u_voices-lua.pd_lua", DIR)
local o = T.new(class, {})
check("an object has three inlets and eleven outlets", o.inlets == 3 and o.outlets == 11)
local at_init = T.send(o, 3, "init", {})
equal("init: the bang on outlet 8 that says it loaded", at_init[#at_init], { 8, "bang", {} })
local sent = T.send(o, 3, "restore", { "voices" })
local function sel(s, n)
  local r = {}
  for _, m in ipairs(s) do if m[1] == n then r[#r + 1] = m[2] end end
  return r
end
equal("⛔ a song's voices: outlet 1 the page, 2 the grid, 3 the seed, 4 the engines, 6 the phone, 9 u_perform",
      { sel(sent, 1), sel(sent, 2)[1], sel(sent, 3), sel(sent, 4)[1], sel(sent, 6)[1], sel(sent, 9) },
      { { "perform" }, "voices", { "seed", "page" }, "assign", "voices", { "rows" } })
sent = T.send(o, 1, "left-1", { 1 })
equal("u_map's left-1: its page on outlet 1, and the grid and the phone hear it", { sel(sent, 1), sel(sent, 2), sel(sent, 6) },
      { { "drums" }, { "voices" }, { "voices" } })
equal("⛔ a release does nothing", T.send(o, 1, "left-1", { 0 }), {})
equal("... and one it doesn't know is bad-selector, on outlet 7", T.send(o, 1, "left-9", { 1 }),
      { { 7, "fail", { "u_voices", "bad-selector" } } })
sent = T.send(o, 2, "left", { 1 })
equal("the phone's left 1, the lit one: back to the performance page", sel(sent, 1), { "perform" })
sent = T.send(o, 3, "restore", { "page", "voice", 2 })
equal("restore page on inlet 3", sel(sent, 1), { "harmony" })
equal("a key not its own is nothing", T.send(o, 3, "restore", { "tempo", 120 }), {})

os.exit(T.report() == 0)
