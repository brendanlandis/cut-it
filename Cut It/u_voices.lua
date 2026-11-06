-- u_voices.lua -- a song's voices and the page on show. A row of the Launchpad is a voice: its
-- right button chooses the voice's machine, names it and sets it, and the button across from it, on
-- the left, is what it does (Brendan, 2026-11-06). Plain Lua with no Pd in it, so
-- test/gate/lua/u_voices_test.lua runs it on the Mac with lua.org's interpreter. u_voices-lua.pd_lua
-- is its Pd face, and u_voices.pd keeps the cords. ref/module/voices.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves, in
-- order, as {outlet, selector, atoms}:
--   {"mode", <page>, {}}                     the mode bus: the page, the map's key and g_grid's
--   {"grid", "voices", {row, kind, 8 kinds}} g_grid: the row on show and each row's method
--   {"save", "voices", {atoms}}              the state bus: put song voices, with the song
--   {"seed", "seed", {atoms}}                the state bus: put seed voices, what it starts as
--   {"page", "page", {kind, row}}            the state bus: put auto page, across a power cycle
--   {"engine", "assign", {e, line, machine}} c_melody <e>: this line plays on this machine, or off
--   {"engine", "active", {e}}                the c_melody the page's voice is in, 0 for neither
--   {"synth", "machine", {machine}}          c_synth: the machine the nanoKEY plays
--   {"perform", "rows", {row, 8 engines}}    u_perform: the row on show and each row's engine
--   {"phone", "voices", {atoms}}             u_net: /cutit/voices
--   {"err", "fail" | "warn", {"u_voices", text}}   err (C-12)

local R = {}

R.ROWS = 8
-- How many of each generator line there are: c_melody is built this many times, a harmony line and
-- a melody line in each (u_root.pd).
R.ENGINES = 2
-- What a voice does, and what it can do that on. Harmony, melody and the drum page are ways of doing
-- that, not voices. There is one drum sequencer for now, and so one voice of it.
R.METHODS = { "drums", "harmony", "melody", "keys" }
R.MACHINES = { "kit", "fm", "strings", "sine", "saw", "square" }
local FOR = { drums = { kit = true }, harmony = {}, melody = {}, keys = {} }
for _, m in ipairs({ "fm", "strings", "sine", "saw", "square" }) do
  FOR.harmony[m], FOR.melody[m], FOR.keys[m] = true, true, true
end
-- A machine a voice starts on: the first one no other voice has.
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
    return v and v.method or "perform"
  elseif st.kind == "setup" then
    return "sound"
  end
  return st.kind
end

-- The song's voices as atoms: name, method and machine a row, - for one with none.
function R.line(st)
  local a = {}
  for r = 1, R.ROWS do
    local v = st.voices[r]
    a[#a + 1] = v and v.name or "-"
    a[#a + 1] = v and v.method or "-"
    a[#a + 1] = v and v.machine or "-"
  end
  return a
end

-- Each generator line's voice, by row order: { harmony = {[e] = row}, melody = {[e] = row} }.
local function lines(st)
  local out = { harmony = {}, melody = {} }
  for r = 1, R.ROWS do
    local v = st.voices[r]
    if v and out[v.method] then
      local t = out[v.method]
      t[#t + 1] = r
    end
  end
  return out
end

-- The engine a row's voice is in, or nil.
function R.engine_of(st, row)
  local v = st.voices[row]
  if not v then return nil end
  local t = lines(st)[v.method]
  if not t then return nil end
  for e, r in ipairs(t) do
    if r == row then return e end
  end
  return nil
end

-- A machine another voice has, as the phone needs to warn: the row, or nil.
function R.taken(st, machine, row)
  for r = 1, R.ROWS do
    local v = st.voices[r]
    if r ~= row and v and v.machine == machine then return r end
  end
  return nil
end

local function first_free(st, method, row)
  for _, m in ipairs(START[method]) do
    if not R.taken(st, m, row) then return m end
  end
  return START[method][1]
end

-- What the engines play on: each line of each engine, its voice's machine or off.
local function assign(st)
  local out = {}
  local l = lines(st)
  for e = 1, R.ENGINES do
    local h, m = st.voices[l.harmony[e] or 0], st.voices[l.melody[e] or 0]
    out[#out + 1] = { "engine", "assign", { e, "h", h and h.machine or "off" } }
    out[#out + 1] = { "engine", "assign", { e, "m", m and m.machine or "off" } }
  end
  return out
end

-- Everything that follows the page: the mode bus, the grid, the engine the phone and the Launchpad
-- talk to, the machine the nanoKEY plays. The perform page keeps the last of those.
local function show(st, out)
  out = out or {}
  local name = R.page_name(st)
  out[#out + 1] = { "mode", name, {} }
  local v = st.voices[st.row]
  if v and (st.kind == "voice" or st.kind == "setup") then
    out[#out + 1] = { "engine", "active", { R.engine_of(st, st.row) or 0 } }
    if R.HARDWARE[v.machine] then out[#out + 1] = { "synth", "machine", { v.machine } } end
  end
  out[#out + 1] = { "page", "page", { st.kind, st.row } }
  local rows = { (st.kind == "voice" or st.kind == "setup") and st.row or 0 }
  for r = 1, R.ROWS do rows[r + 1] = R.engine_of(st, r) or 0 end
  out[#out + 1] = { "perform", "rows", rows }
  return out
end

local function go(st, kind, row, out)
  st.kind, st.row = kind, row
  return show(st, out)
end

local function changed(st, out)
  out[#out + 1] = { "save", "voices", R.line(st) }
  for _, e in ipairs(assign(st)) do out[#out + 1] = e end
  return out
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

-- A new voice on an unused row: keys, on a machine no other voice has, named for its row.
local function add(st, r, out)
  st.voices[r] = { name = "voice_" .. r, method = "keys", machine = first_free(st, "keys", r) }
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
  local running = st.running
  st.running = true
  if running or st.kind == "perform" or st.kind == "songs" or st.kind == "diag" then return {} end
  return go(st, "perform", 0)
end

function R.stop(st)
  st.running = false
  return {}
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

-- What a voice does: its machine stays if the method can play on it, else the first one free. The
-- page follows, if it is this voice's left page.
function R.set_method(st, a)
  local r = row_of(a)
  local v = r and st.voices[r]
  local m = a[2]
  if not v then return {} end
  if not FOR[m] then return { R.fail("bad-method") } end
  if v.method == m then return {} end
  local count = 0
  local limit = m == "drums" and 1 or R.ENGINES
  if m ~= "keys" then
    for x = 1, R.ROWS do
      local o = st.voices[x]
      if x ~= r and o and o.method == m then count = count + 1 end
    end
    if count >= limit then return { report("warn", "too-many-" .. m) } end
  end
  v.method = m
  if not FOR[m][v.machine] then v.machine = first_free(st, m, r) end
  local out = changed(st, {})
  if st.row == r then show(st, out) end
  return out
end

-- A voice's machine. The phone has already asked, if another voice has it.
function R.set_machine(st, a)
  local r = row_of(a)
  local v = r and st.voices[r]
  local m = a[2]
  if not v then return {} end
  if not FOR[v.method][m] then return { R.fail("bad-machine") } end
  if v.machine == m then return {} end
  v.machine = m
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

-- ------------------------------------------------------------------ a song's voices

-- A song with no voices yet, one from before there were any: what it held, a drum page, and the
-- generator's two lines on the machines they played on. Only what a new song needs to start with.
local function seed(st)
  st.voices = {
    [1] = { name = "drums", method = "drums", machine = "kit" },
    [2] = { name = "chords", method = "harmony", machine = "strings" },
    [3] = { name = "melody", method = "melody", machine = "fm" },
  }
end

-- restore voices <atoms>: the song loaded holds these. None: it is seeded, and saved so, which is no
-- change to it. A voice's page from the last power-off waited for this: the auto file is read before
-- the song is.
function R.restore(st, a)
  st.voices = {}
  local any = false
  for r = 1, R.ROWS do
    local i = (r - 1) * 3
    local name, method, machine = a[i + 1], a[i + 2], a[i + 3]
    if type(name) == "number" then name = string.format("%g", name) end
    if type(name) == "string" and name ~= "-" and FOR[method] and FOR[method][machine] then
      st.voices[r] = { name = name, method = method, machine = machine }
      any = true
    end
  end
  local out = {}
  if not any then
    seed(st)
    out[1] = { "seed", "seed", R.line(st) }
  end
  for _, e in ipairs(assign(st)) do out[#out + 1] = e end
  local due = st.page_due
  st.page_due = nil
  if due and st.voices[due.row] then st.kind, st.row = due.kind, due.row end
  if (st.kind == "voice" or st.kind == "setup") and not st.voices[st.row] then
    return go(st, "perform", 0, out)
  end
  return show(st, out)
end

-- restore page <kind> <row>: where it was at the last power-off. A voice's page waits for the song's
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

-- g_grid: the row on show, 0 for none; whether it is the left or right page; each row's method.
function R.grid(st)
  local a = { st.row, st.kind }
  for r = 1, R.ROWS do
    local v = st.voices[r]
    a[#a + 1] = v and v.method or "-"
  end
  return a
end

-- /cutit/voices: the page's name, its kind and row, then the song's voices, name, method and machine
-- a row. The phone knows from these which rows to light and what a machine's other voice is. 27
-- atoms.
function R.phone(st)
  local a = { R.page_name(st), st.kind, st.row }
  for _, x in ipairs(R.line(st)) do a[#a + 1] = x end
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
  method = function(st, a) return R.set_method(st, a) end,
  machine = function(st, a) return R.set_machine(st, a) end,
  remove = function(st, a) return R.remove(st, a) end,
}

R.internal = {
  init = function() return {} end,
  start = function(st) return R.start(st) end,
  stop = function(st) return R.stop(st) end,
  restore = function(st, a)
    local key = a[1]
    if key == "voices" then return R.restore(st, { table.unpack(a, 2) }) end
    if key == "page" then return R.restore_page(st, { table.unpack(a, 2) }) end
    return {}
  end,
}

return R
