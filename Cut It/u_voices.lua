-- u_voices.lua -- a section's voices and the page on show. A row of the Launchpad is a voice: its
-- right button chooses the voice's instrument, names it and sets it, and the button across from it, on
-- the left, is what it does (Brendan, 2026-11-06). Plain Lua with no Pd in it, so
-- test/gate/lua/u_voices_test.lua runs it on the Mac with lua.org's interpreter. u_voices-lua.pd_lua
-- is its Pd face, and u_voices.pd keeps the cords. ref/module/voices.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves, in
-- order, as {outlet, selector, atoms}:
--   {"mode", <page>, {}}                     the mode bus: the page, the map's key and g_grid's
--   {"grid", "voices", {row, kind, 8 kinds}} g_grid: the row on show and each row's behavior
--   {"save", "voices", {atoms}}              the state bus: put section voices, with the section
--   {"seed", "seed", {atoms}}                the state bus: put seed-section voices, what it starts as
--   {"page", "page", {kind, row}}            the state bus: put auto page, across a power cycle
--   {"engine", "assign", {e, line, instrument}}   c_melody <e>: this line plays on this instrument, or off
--   {"engine", "active", {e}}                the c_melody the page's voice is in, 0 for neither
--   {"synth", "instrument", {instrument}}    c_synth: the instrument the nanoKEY plays
--   {"perform", "rows", {row, 8 engines}}    u_perform: the row on show and each row's engine
--   {"sound", "rows", {row, 8 of instrument, engine, line}}   u_sound: the same, and each row's instrument
--   {"phone", "voices", {atoms}}             u_net: /cutit/voices
--   {"disp", "led", {state}}                 g_led: white while the songs page is open
--   {"err", "fail" | "warn", {"u_voices", text}}   err (C-12)

local R = {}

R.ROWS = 8
-- How many of each generator line there are: c_melody is built this many times, a harmony line and
-- a melody line in each (u_root.pd).
R.ENGINES = 2
-- What a voice does, and what it can do that on. Harmony, melody and the drum page are ways of doing
-- that, not voices. There is one drum sequencer for now, and so one voice of it.
R.BEHAVIORS = { "drums", "harmony", "melody", "keys" }
R.INSTRUMENTS = { "kit", "fm", "strings", "sine", "saw", "square" }
local FOR = { drums = { kit = true }, harmony = {}, melody = {}, keys = {} }
for _, m in ipairs({ "fm", "strings", "sine", "saw", "square" }) do
  FOR.harmony[m], FOR.melody[m] = true, true
end
FOR.keys.fm, FOR.keys.strings = true, true
FOR.keys.sine, FOR.keys.saw, FOR.keys.square = true, true, true
-- An instrument a voice starts on: the first one no other voice has.
local START = { drums = { "kit" }, harmony = { "strings", "fm", "sine", "saw", "square" },
                melody = { "fm", "strings", "saw", "square", "sine" },
                keys = { "fm", "strings", "sine", "saw", "square" } }
-- Hardware is one voice's; the phone warns before a second voice takes it (Brendan, 2026-11-06).
R.HARDWARE = { fm = true, strings = true }

-- A name, as a song's: lowercase, one symbol, spaces as _, this long at most.
R.MAX_NAME = 16

local function num(x)
  return type(x) == "number" and x or 0
end

local function report(level, text)
  return { "err", level, { "u_voices", string.sub(text, 1, 21) } }
end
function R.fail(text) return report("fail", text) end

local function clean(words)
  local t = {}
  for _, w in ipairs(words) do
    if type(w) == "number" then w = string.format("%g", w) end
    if type(w) == "string" then t[#t + 1] = w end
  end
  local s = table.concat(t, "_"):lower():gsub("[^%w_%-']", "")
  s = s:sub(1, R.MAX_NAME)
  return s ~= "" and s or nil
end

-- The page on show: perform, a voice's left page, its right page, the songs page or the diagnostics.
function R.new()
  return { voices = {}, kind = "perform", row = 0, back = {} }
end

-- The map's name for a page: perform, drums, harmony, melody, keys, sound, songs, diag.
function R.page_name(st)
  if st.kind == "voice" then
    local v = st.voices[st.row]
    return v and v.behavior or "perform"
  elseif st.kind == "setup" then
    return "sound"
  end
  return st.kind
end

-- The voices as atoms: name, behavior and instrument a row, - for one with none.
function R.line(st)
  local a = {}
  for r = 1, R.ROWS do
    local v = st.voices[r]
    a[#a + 1] = v and v.name or "-"
    a[#a + 1] = v and v.behavior or "-"
    a[#a + 1] = v and v.instrument or "-"
  end
  return a
end

-- Each generator line's voice, by row order: { harmony = {[e] = row}, melody = {[e] = row} }.
local function lines(st)
  local out = { harmony = {}, melody = {} }
  for r = 1, R.ROWS do
    local v = st.voices[r]
    if v and out[v.behavior] then
      local t = out[v.behavior]
      t[#t + 1] = r
    end
  end
  return out
end

-- The engine a row's voice is in, or nil.
function R.engine_of(st, row)
  local v = st.voices[row]
  if not v then return nil end
  local t = lines(st)[v.behavior]
  if not t then return nil end
  for e, r in ipairs(t) do
    if r == row then return e end
  end
  return nil
end

-- An instrument another voice has, as the phone needs to warn: the row, or nil.
function R.taken(st, instrument, row)
  for r = 1, R.ROWS do
    local v = st.voices[r]
    if r ~= row and v and v.instrument == instrument then return r end
  end
  return nil
end

local function first_free(st, behavior, row)
  for _, m in ipairs(START[behavior]) do
    if not R.taken(st, m, row) then return m end
  end
  return START[behavior][1]
end

-- What the engines play on: each line of each engine, its voice's instrument or off.
local function assign(st)
  local out = {}
  local l = lines(st)
  for e = 1, R.ENGINES do
    local h, m = st.voices[l.harmony[e] or 0], st.voices[l.melody[e] or 0]
    out[#out + 1] = { "engine", "assign", { e, "h", h and h.instrument or "off" } }
    out[#out + 1] = { "engine", "assign", { e, "m", m and m.instrument or "off" } }
  end
  return out
end

-- u_perform and u_sound: the row on show, and each row's engine and instrument.
local function tell_rows(st, out)
  local rows = { (st.kind == "voice" or st.kind == "setup") and st.row or 0 }
  for r = 1, R.ROWS do rows[r + 1] = R.engine_of(st, r) or 0 end
  out[#out + 1] = { "perform", "rows", rows }
  local sound = { rows[1] }
  for r = 1, R.ROWS do
    local v = st.voices[r]
    sound[#sound + 1] = v and v.instrument or "-"
    sound[#sound + 1] = R.engine_of(st, r) or 0
    sound[#sound + 1] = v and (v.behavior == "harmony" and "h" or (v.behavior == "melody" and "m" or "-")) or "-"
  end
  out[#out + 1] = { "sound", "rows", sound }
  return out
end

-- Everything that follows the page: the mode bus, the grid, the engine the phone and the Launchpad
-- talk to, the instrument the nanoKEY plays. The perform page keeps the last of those.
local function show(st, out)
  out = out or {}
  local name = R.page_name(st)
  out[#out + 1] = { "mode", name, {} }
  local v = st.voices[st.row]
  if v and (st.kind == "voice" or st.kind == "setup") then
    out[#out + 1] = { "engine", "active", { R.engine_of(st, st.row) or 0 } }
    if R.HARDWARE[v.instrument] or v.behavior == "keys" then
      out[#out + 1] = { "synth", "instrument", { v.instrument } }
    end
  end
  out[#out + 1] = { "page", "page", { st.kind, st.row } }
  local open = st.kind == "songs"
  if open ~= (st.led_open or false) then
    st.led_open = open
    out[#out + 1] = { "disp", "led", { open and "songs" or "songs-off" } }
  end
  return tell_rows(st, out)
end

local function go(st, kind, row, out)
  st.kind, st.row = kind, row
  return show(st, out)
end

local function changed(st, out)
  out[#out + 1] = { "save", "voices", R.line(st) }
  for _, e in ipairs(assign(st)) do out[#out + 1] = e end
  return tell_rows(st, out)
end

-- ------------------------------------------------------------------ the buttons

-- A left button: what that voice does. The lit one again goes back to the performance page. A row
-- with no voice does nothing.
function R.left(st, n)
  local r = math.floor(num(n))
  if not st.voices[r] then return {} end
  if st.kind == "voice" and st.row == r then return go(st, "perform", 0) end
  return go(st, "voice", r)
end

-- A new voice on an unused row: keys, on an instrument no other voice has, named for its row.
local function add(st, r, out)
  st.voices[r] = { name = "voice_" .. r, behavior = "keys", instrument = first_free(st, "keys", r) }
  return changed(st, out)
end

-- A right button: that voice's setup. An unused row's starts a new voice; the lit one again goes
-- back to the performance page.
function R.right(st, n)
  local r = math.floor(num(n))
  if r < 1 or r > R.ROWS then return {} end
  if st.kind == "setup" and st.row == r then return go(st, "perform", 0) end
  local out = {}
  if not st.voices[r] then add(st, r, out) end
  return go(st, "setup", r, out)
end

-- A page of its own, opened from anywhere and closed by the same button, back to where it was, each
-- keeping its own way back, so songs and the diagnostics can be opened over each other. A voice that
-- has gone since is the performance page.
local function toggle(st, kind)
  if st.kind == kind then
    local b = st.back[kind] or { kind = "perform", row = 0 }
    if (b.kind == "voice" or b.kind == "setup") and not st.voices[b.row] then
      return go(st, "perform", 0)
    end
    return go(st, b.kind, b.row)
  end
  st.back[kind] = { kind = st.kind, row = st.row }
  return go(st, kind, 0)
end

-- Aux, on the Organelle: the songs and sections page (Brendan, 2026-11-06).
function R.aux(st) return toggle(st, "songs") end

-- Setup, on the Launchpad: the diagnostics and test mode (Brendan, 2026-11-06).
function R.setup(st) return toggle(st, "diag") end

-- PLAY: the performance page comes up by itself (Brendan, 2026-11-06). A start while the transport
-- runs is no PLAY: the saved tempo's pad restarts it by the same bus, under a finger on the drum page.
function R.start(st)
  if st.kind == "perform" or st.kind == "songs" or st.kind == "diag" then return {} end
  return go(st, "perform", 0)
end


-- ------------------------------------------------------------------ the phone's voice page

local function row_of(a)
  local r = math.floor(num(a[1]))
  return (r >= 1 and r <= R.ROWS) and r or nil
end

function R.rename(st, a)
  local r = row_of(a)
  local v = r and st.voices[r]
  if not v then return {} end
  local name = clean({ table.unpack(a, 2) })
  if not name or name == v.name then return {} end
  v.name = name
  return changed(st, {})
end

-- What a voice does: its instrument stays if the behavior can play on it, else the first one free. The
-- page follows, if it is this voice's left page.
function R.set_behavior(st, a)
  local r = row_of(a)
  local v = r and st.voices[r]
  local m = a[2]
  if not v then return {} end
  if not FOR[m] then return { R.fail("bad-behavior") } end
  if v.behavior == m then return {} end
  local count = 0
  local limit = m == "drums" and 1 or R.ENGINES
  if m ~= "keys" then
    for x = 1, R.ROWS do
      local o = st.voices[x]
      if x ~= r and o and o.behavior == m then count = count + 1 end
    end
    if count >= limit then return { report("warn", "too-many-" .. m) } end
  end
  v.behavior = m
  if not FOR[m][v.instrument] then v.instrument = first_free(st, m, r) end
  local out = changed(st, {})
  if st.row == r then show(st, out) end
  return out
end

-- A voice's instrument. The phone has already asked, if another voice has it.
function R.set_instrument(st, a)
  local r = row_of(a)
  local v = r and st.voices[r]
  local m = a[2]
  if not v then return {} end
  if not FOR[v.behavior][m] then return { R.fail("bad-instrument") } end
  if v.instrument == m then return {} end
  v.instrument = m
  local out = changed(st, {})
  if st.row == r then show(st, out) end
  return out
end

-- A voice gone: back to the performance page if it was on show.
function R.remove(st, a)
  local r = row_of(a)
  if not (r and st.voices[r]) then return {} end
  st.voices[r] = nil
  local out = changed(st, {})
  if st.row == r then go(st, "perform", 0, out) end
  return out
end

-- ------------------------------------------------------------------ a section's voices

-- A section with no voices yet, one from before there were any: what a song held then, a drum page,
-- and the generator's two lines on the instruments they played on. Only what a new song needs to
-- start with.
local function seed(st)
  st.voices = {
    [1] = { name = "drums", behavior = "drums", instrument = "kit" },
    [2] = { name = "chords", behavior = "harmony", instrument = "strings" },
    [3] = { name = "melody", behavior = "melody", instrument = "fm" },
  }
end

-- What the page on show hangs on: its name, kind and row, and its voice's engine and instrument.
local function shown(st)
  local v = st.voices[st.row]
  return table.concat({ R.page_name(st), st.kind, st.row, R.engine_of(st, st.row) or 0,
                        v and v.instrument or "-" }, " ")
end

-- restore voices <atoms>: the section starting holds these (Brendan, 2026-11-25: a section's own,
-- where the song held one set for all of them). None: it is seeded, and saved so, which is no change
-- to it. It comes at every section's start, so the same voices again say nothing; voices that differ
-- are assigned, and the page on show follows only if what it hangs on changed. A voice's page from
-- the last power-off waited for the first: the auto file is read before the song is.
function R.restore(st, a)
  local was = st.restored and table.concat(R.line(st), " ") or nil
  local page = shown(st)
  st.restored = true
  st.voices = {}
  local any = false
  for r = 1, R.ROWS do
    local i = (r - 1) * 3
    local name, behavior, instrument = a[i + 1], a[i + 2], a[i + 3]
    if type(name) == "number" then name = string.format("%g", name) end
    if type(name) == "string" and name ~= "-" and FOR[behavior] and FOR[behavior][instrument] then
      st.voices[r] = { name = name, behavior = behavior, instrument = instrument }
      any = true
    end
  end
  local out = {}
  if not any then
    seed(st)
    out[1] = { "seed", "seed", R.line(st) }
  end
  local due = st.page_due
  st.page_due = nil
  if was == table.concat(R.line(st), " ") and not due then return out end
  for _, e in ipairs(assign(st)) do out[#out + 1] = e end
  if due and st.voices[due.row] then st.kind, st.row = due.kind, due.row end
  if (st.kind == "voice" or st.kind == "setup") and not st.voices[st.row] then
    return go(st, "perform", 0, out)
  end
  if was and shown(st) == page then return tell_rows(st, out) end
  return show(st, out)
end

-- restore page <kind> <row>: where it was at the last power-off. A voice's page waits for the section's
-- voices, if they haven't come yet.
function R.restore_page(st, a)
  local kind, row = a[1], math.floor(num(a[2]))
  if kind == "voice" or kind == "setup" then
    if not st.voices[row] then
      st.page_due = { kind = kind, row = row }
      return {}
    end
  elseif kind ~= "perform" and kind ~= "songs" and kind ~= "diag" then
    return {}
  end
  return go(st, kind, row)
end

-- ------------------------------------------------------------------ what the surfaces show

-- g_grid: the row on show, 0 for none; whether it is the left or right page; each row's behavior.
function R.grid(st)
  local a = { st.row, st.kind }
  for r = 1, R.ROWS do
    local v = st.voices[r]
    a[#a + 1] = v and v.behavior or "-"
  end
  return a
end

-- /cutit/voices, field by field, in the order it goes: a name, how many atoms it takes, what writes
-- them and, for a field of groups, what each group holds. The page's name, its kind and row, then the
-- section's voices, name, behavior and instrument a row. The phone knows from these which rows to light and
-- what an instrument's other voice is. 27 atoms. The app reads the list by position, and takes each
-- field's place from this table: phone/state-at.py writes them into phone/CutIt/StateAt.swift, and
-- test/gate/app-assert.py fails when that file is behind.
R.PHONE_FIELDS = {
  { "page", 1, function(st, a) a[#a + 1] = R.page_name(st) end },
  { "kind", 1, function(st, a) a[#a + 1] = st.kind end },
  { "row", 1, function(st, a) a[#a + 1] = st.row end },
  { "voice", 3 * R.ROWS, function(st, a)
    for _, x in ipairs(R.line(st)) do a[#a + 1] = x end
  end, { "name", "behavior", "instrument" } },
}
R.PHONE, R.PHONE_AT = 0, {}
for _, f in ipairs(R.PHONE_FIELDS) do
  R.PHONE_AT[f[1]] = R.PHONE + 1
  R.PHONE = R.PHONE + f[2]
end
function R.phone(st)
  local a = {}
  for _, f in ipairs(R.PHONE_FIELDS) do f[3](st, a) end
  return a
end

-- ------------------------------------------------------------------ what arrives

-- From u_map, <arg> <value>: left-N, right-N, aux and setup, a press, any non-zero value.
R.controls = {}
for r = 1, R.ROWS do
  R.controls["left-" .. r] = function(st) return R.left(st, r) end
  R.controls["right-" .. r] = function(st) return R.right(st, r) end
end
R.controls.aux = function(st) return R.aux(st) end
R.controls.setup = function(st) return R.setup(st) end

-- From u_net: the app's own rails and voice page.
R.phone_cmds = {
  left = function(st, a) return R.left(st, a[1]) end,
  right = function(st, a) return R.right(st, a[1]) end,
  aux = function(st) return R.aux(st) end,
  setup = function(st) return R.setup(st) end,
  name = function(st, a) return R.rename(st, a) end,
  behavior = function(st, a) return R.set_behavior(st, a) end,
  instrument = function(st, a) return R.set_instrument(st, a) end,
  remove = function(st, a) return R.remove(st, a) end,
}

R.internal = {
  init = function() return {} end,
  play = function(st) return R.start(st) end,
  restore = function(st, a)
    local key = a[1]
    if key == "voices" then return R.restore(st, { table.unpack(a, 2) }) end
    if key == "page" then return R.restore_page(st, { table.unpack(a, 2) }) end
    return {}
  end,
}

return R
