-- u_sound.lua -- a voice's sound: each instrument's parameters, the song's patches and the factory's
-- (Brendan, 2026-11-06). A patch is an instrument's saved sound. Factory patches are starting points, in a
-- library outside songs; song patches live with the song, copied and depending on nothing after that.
-- Plain Lua with no Pd in it, so test/gate/lua/u_sound_test.lua runs it on the Mac with lua.org's
-- interpreter. u_sound-lua.pd_lua is its Pd face, and u_sound.pd keeps the cords. ref/module/voices.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves, in
-- order, as {outlet, selector, atoms}:
--   {"fm" | "strings", "cc" | "program", {...}}   that synth's device layer
--   {"engine", "tone", {engine, line, param, value}}   c_melody: a Pd voice's parameter
--   {"save", "sounds" | "patches", {atoms}}       the state bus: put song
--   {"heard", "list", {"instrument", param, value}}   u_perform: a parameter moved on the Launchpad
--   {"kit", "bang", {}}                           c_steps: the kit's sound as it stands is what it snaps back to
--   {"keys", "tone" | "list", {...}}              c_keys: a keys voice on a Pd instrument
--   {"fm", "byte", {b}}                           m_fm1: a whole DX7 voice a byte at a time, from the library
--   {"err", "warn" | "fail", {"u_sound", text}}   err (C-12)
-- The phone's state (R.phone) is worked out by the face, and sent when it changes.

local R = {}

R.ROWS = 8
R.MAX_NAME = 16
R.HARDWARE = { fm = true, strings = true }

local function num(x)
  return type(x) == "number" and x or 0
end

local function report(level, text)
  return { "err", level, { "u_sound", string.sub(text, 1, 21) } }
end
function R.fail(text) return report("fail", text) end

-- cut-it-instruments.txt: { instrument = { list = {params in order}, by = {param = {how, n, default, top, switch}},
-- bank = its bank parameter, voice = its voice parameter } }.
function R.parse_instruments(text)
  local t = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    if not line:match("^%s*#") then
      local m, p, how, n, d, top, switch =
        line:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s*(%S*)%s*(%S*)")
      if m then
        t[m] = t[m] or { list = {}, by = {} }
        t[m].list[#t[m].list + 1] = p
        t[m].by[p] = { how = how, n = tonumber(n) or 0, default = tonumber(d) or 0,
                       top = tonumber(top), switch = tonumber(switch) }
        if how == "bank" or how == "voice" then t[m][how] = p end
      end
    end
  end
  return t
end

-- cut-it-factory.txt: { instrument = { list = {names}, by = {name = {param = value}} } }.
function R.parse_factory(text)
  local t = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    if not line:match("^%s*#") then
      local w = {}
      for x in line:gmatch("%S+") do w[#w + 1] = x end
      if #w >= 2 then
        local m, name = w[1], w[2]
        t[m] = t[m] or { list = {}, by = {} }
        t[m].list[#t[m].list + 1] = name
        local v = {}
        for i = 3, #w - 1, 2 do v[w[i]] = tonumber(w[i + 1]) or 0 end
        t[m].by[name] = v
      end
    end
  end
  return t
end

function R.new(instruments_text, factory_text)
  local st = { instruments = R.parse_instruments(instruments_text), factory = R.parse_factory(factory_text),
               rows = {}, patches = {}, order = {}, at_row = 0, last_sent = {}, library = {} }
  return st
end

-- The DX7 voice library (Brendan, 2026-11-24): bank files as a DX7 saves them, 32 voices each, in the
-- patch's dx7 folder and outside git. cut-it-dx7.txt lists them, and a bank's place there is its number.
function R.parse_library(text)
  local t = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    local f = line:match("^%s*([^#%s]+)")
    if f then t[#t + 1] = f end
  end
  return t
end

-- A bank file as read: a format 9 dump, F0 43 0n 09 20 00, 32 voices of 128 packed bytes, a checksum,
-- F7. Kept as its 4096 bytes of voices; anything else is turned away.
function R.bank(st, i, data)
  if type(data) ~= "string" or #data ~= 4104 or data:byte(1) ~= 0xF0 or data:byte(2) ~= 0x43
     or data:byte(4) ~= 0x09 or data:byte(4104) ~= 0xF7 then
    return false
  end
  st.library[i] = data:sub(7, 4102)
  return true
end

-- One of a bank's voices, v from 0, as the 155 bytes of a one-voice dump: a bank packs several
-- parameters to a byte, and a one-voice dump has each in its own. Six operators, OP6 first, 17 bytes
-- packed and 21 not; then the pitch EG, the algorithm and the rest, and the name.
function R.unpacked(bank, v)
  local at = v * 128
  local function b(i) return bank:byte(at + i + 1) end
  local d = {}
  for op = 0, 5 do
    local o = op * 17
    for i = 0, 10 do d[#d + 1] = b(o + i) & 127 end   -- EG rates and levels, keyboard scaling's breakpoint and depths
    d[#d + 1] = b(o + 11) & 3                         -- left curve
    d[#d + 1] = (b(o + 11) >> 2) & 3                  -- right curve
    d[#d + 1] = b(o + 12) & 7                         -- rate scaling
    d[#d + 1] = b(o + 13) & 3                         -- amp mod sensitivity
    d[#d + 1] = (b(o + 13) >> 2) & 7                  -- velocity sensitivity
    d[#d + 1] = b(o + 14) & 127                       -- output level
    d[#d + 1] = b(o + 15) & 1                         -- ratio or fixed
    d[#d + 1] = (b(o + 15) >> 1) & 31                 -- coarse
    d[#d + 1] = b(o + 16) & 127                       -- fine
    d[#d + 1] = (b(o + 12) >> 3) & 15                 -- detune
  end
  for i = 102, 109 do d[#d + 1] = b(i) & 127 end      -- pitch EG
  d[#d + 1] = b(110) & 31                             -- algorithm
  d[#d + 1] = b(111) & 7                              -- feedback
  d[#d + 1] = (b(111) >> 3) & 1                       -- oscillator sync
  for i = 112, 115 do d[#d + 1] = b(i) & 127 end      -- LFO speed and delay, pitch and amp mod depth
  d[#d + 1] = b(116) & 1                              -- LFO sync
  d[#d + 1] = (b(116) >> 1) & 7                       -- LFO wave
  d[#d + 1] = (b(116) >> 4) & 7                       -- pitch mod sensitivity
  d[#d + 1] = b(117) & 127                            -- transpose
  for i = 118, 127 do d[#d + 1] = b(i) & 127 end      -- name
  return d
end

-- A voice's 155 bytes as a one-voice dump, format 0 on MIDI channel 1: F0 43 00 00 01 1B <155>
-- <checksum> F7.
local function dump(d)
  local sum = 0
  for _, b in ipairs(d) do sum = sum + b end
  local out = { 0xF0, 0x43, 0x00, 0x00, 0x01, 0x1B }
  for _, b in ipairs(d) do out[#out + 1] = b end
  out[#out + 1] = (128 - (sum % 128)) % 128
  out[#out + 1] = 0xF7
  return out
end

-- A parameter as it stands: what's been set, or else its default, which is only what the page shows.
-- A hardware synth is told only what's been set, so taking one up leaves its own sound alone.
local function value_of(st, row, p)
  local v = row.values[p]
  if v ~= nil then return v end
  local m = st.instruments[row.instrument]
  return m and m.by[p] and m.by[p].default or 0
end

local function copy(t)
  local o = {}
  for k, x in pairs(t) do o[k] = x end
  return o
end

-- A parameter that counts in steps: which of its n a value is, from 0.
local function index(value, n)
  return math.max(0, math.min(n - 1, math.floor(value * n)))
end

-- The hows that choose the voice itself: a row's voice is a program or a DX7 voice, whichever was chosen
-- last. Each counts in steps.
local CHOOSES = { pc = true, bank = true, voice = true }

-- A whole voice into the program the instrument keeps for DX7 voices, the voice parameter's top. The FM-1
-- takes a voice in place of the one it is on and keeps it for good (Reference, m-vave-fm-1), so its
-- program change goes first, and as bytes like the voice: Pd sends a byte at once and queues a program
-- change, so a [pgmout]'s would arrive behind the voice, which would land wherever the FM-1 was
-- (ref/device/fm1.md). On MIDI channel 1, as the dump is.
local function into_slot(instrument, m, bytes, out)
  out[#out + 1] = { instrument, "byte", { 0xC0 } }
  out[#out + 1] = { instrument, "byte", { m.by[m.voice].top or 127 } }
  for _, b in ipairs(bytes) do out[#out + 1] = { instrument, "byte", { b } } end
  return out
end

-- A DX7 voice from the library. The same voice isn't sent twice running, since each is written into the
-- FM-1. again: send it whatever was last sent, as a recall does. True if it went.
local function say_voice(st, row, out, again)
  local m = st.instruments[row.instrument]
  if not (m and m.bank and m.voice) then return false end
  local bank = index(value_of(st, row, m.bank), m.by[m.bank].n)
  local voice = index(value_of(st, row, m.voice), m.by[m.voice].n)
  local key = bank * m.by[m.voice].n + voice
  if row.voiced == key and not again then return false end
  local data = st.library[bank + 1]
  if not data then
    out[#out + 1] = report("warn", "no-dx7-bank-" .. (bank + 1))
    return false
  end
  row.voiced = key
  into_slot(row.instrument, m, dump(R.unpacked(data, voice)), out)
  return true
end

-- What a parameter's value says to its instrument.
local function say(st, r, row, param, value, out)
  local m = st.instruments[row.instrument]
  local p = m and m.by[param]
  if not p then return out end
  if p.how == "cc" then
    -- A controller's own top (the FM-1's effects stop at 100, 107, 10 or 2), and its effect's on-off
    -- first: on above nothing, so one control both brings an effect in and takes it away.
    local v = math.floor(value * (p.top or 127) + 0.5)
    if p.switch then out[#out + 1] = { row.instrument, "cc", { p.switch, v > 0 and 1 or 0 } } end
    out[#out + 1] = { row.instrument, "cc", { p.n, v } }
  elseif p.how == "pc" then
    out[#out + 1] = { row.instrument, "program", { index(value, p.n) } }
  elseif p.how == "bank" or p.how == "voice" then
    say_voice(st, row, out)
  elseif p.how == "pd" and row.engine and row.engine > 0 then
    out[#out + 1] = { "engine", "tone", { row.engine, row.line, param, value } }
  elseif p.how == "pd" then
    out[#out + 1] = { "keys", "tone", { param, value } }
  end
  return out
end

-- A row's whole sound said again: an instrument taken up, a patch recalled, a song loaded.
local function say_all(st, r, out)
  local row = st.rows[r]
  local m = row and st.instruments[row.instrument]
  if not m then return out end
  -- The voice itself first, a program or a DX7 voice, since it brings settings of its own; then the rest.
  for _, p in ipairs(m.list) do
    if m.by[p].how == "pc" and row.values[p] ~= nil then say(st, r, row, p, row.values[p], out) end
  end
  if m.bank and m.voice and (row.values[m.bank] ~= nil or row.values[m.voice] ~= nil) then
    say_voice(st, row, out, true)
  end
  for _, p in ipairs(m.list) do
    local how = m.by[p].how
    if how == "pd" then
      say(st, r, row, p, value_of(st, row, p), out)
    elseif not CHOOSES[how] and row.values[p] ~= nil then
      say(st, r, row, p, row.values[p], out)
    end
  end
  return out
end

local function sounds_line(st)
  local a = {}
  for r = 1, R.ROWS do
    local row = st.rows[r]
    if row and st.instruments[row.instrument] then
      a[#a + 1] = r
      a[#a + 1] = row.patch or "-"
      a[#a + 1] = row.instrument
      local list = {}
      for _, p in ipairs(st.instruments[row.instrument].list) do
        if row.values[p] ~= nil then list[#list + 1] = p end
      end
      a[#a + 1] = #list
      for _, p in ipairs(list) do
        a[#a + 1] = p
        a[#a + 1] = tonumber(string.format("%.3f", row.values[p]))
      end
    end
  end
  return a
end

local function patches_line(st)
  local a = {}
  for _, name in ipairs(st.order) do
    local p = st.patches[name]
    a[#a + 1] = name
    a[#a + 1] = p.instrument
    local keys = {}
    for k in pairs(p.values) do keys[#keys + 1] = k end
    table.sort(keys)
    a[#a + 1] = #keys
    for _, k in ipairs(keys) do
      a[#a + 1] = k
      a[#a + 1] = tonumber(string.format("%.3f", p.values[k]))
    end
  end
  return a
end

R.save_line = sounds_line

local function saved(st, out)
  out[#out + 1] = { "save", "sounds", sounds_line(st) }
  return out
end

local function saved_patches(st, out)
  out[#out + 1] = { "save", "patches", patches_line(st) }
  return saved(st, out)
end

-- u_voices: the row on show, and each row's instrument, engine and line (- 0 - for none). An instrument a row
-- has just taken up starts from its defaults; the rest is as it was.
function R.rows(st, a)
  st.at_row = math.floor(num(a[1]))
  local out = {}
  for r = 1, R.ROWS do
    local b = 2 + (r - 1) * 3
    local instrument, engine, line = a[b], math.floor(num(a[b + 1])), a[b + 2]
    if instrument == "-" or instrument == nil then
      st.rows[r] = nil
    else
      local row = st.rows[r]
      if not row or row.instrument ~= instrument then
        st.rows[r] = { instrument = instrument, engine = engine, line = line, patch = nil, values = {}, base = {} }
        say_all(st, r, out)
      else
        local moved = row.engine ~= engine or row.line ~= line
        row.engine, row.line = engine, line
        if moved then say_all(st, r, out) end
      end
    end
  end
  return out
end

-- A parameter moved: <row>:<param> <value>, from the map's route, the phone's or a physical control's.
function R.param(st, row_param, value)
  local r, p = tostring(row_param):match("^(%d+):(.+)$")
  r = tonumber(r)
  local row = r and st.rows[r]
  if not row then return {} end
  local m = st.instruments[row.instrument]
  if not (m and m.by[p]) then return { report("warn", "no-param-" .. tostring(p)) } end
  value = math.max(0, math.min(1, num(value)))
  local how = m.by[p].how
  local out = {}
  if not CHOOSES[how] then
    row.values[p] = value
    st.dirty_sounds = true
    return say(st, r, row, p, value, out)
  end
  -- Kept as the middle of its step: a song writes three decimals, and a value near a step's edge would
  -- come back as the step beside it.
  value = (index(value, m.by[p].n) + 0.5) / m.by[p].n
  row.values[p] = value
  st.dirty_sounds = true
  -- A program or a DX7 voice, whichever was chosen last: choosing one lets go of the other.
  for _, q in ipairs(m.list) do
    local hq = m.by[q].how
    if CHOOSES[hq] and (hq == "pc") ~= (how == "pc") then row.values[q] = nil end
  end
  local went = true
  if how == "pc" then
    row.voiced = nil
    say(st, r, row, p, value, out)
  else
    went = say_voice(st, row, out)
  end
  -- A voice brings its own settings with it (the FM-1's effects: Reference, m-vave-fm-1), so what's
  -- been set here is said again behind it, as a recall says it.
  if went then
    for _, q in ipairs(m.list) do
      if m.by[q].how == "cc" and row.values[q] ~= nil then say(st, r, row, q, row.values[q], out) end
    end
  end
  return out
end

local function unique(st, name)
  if not st.patches[name] then return name end
  local n = 2
  while st.patches[name .. "-" .. n] do n = n + 1 end
  return name .. "-" .. n
end

local function row_on_show(st)
  return st.at_row > 0 and st.rows[st.at_row] or nil
end

-- The row's sound becomes that song patch, recalled.
function R.recall(st, name)
  local row = row_on_show(st)
  local p = st.patches[name]
  if not row or not p or p.instrument ~= row.instrument then return {} end
  row.patch = name
  row.values, row.base = copy(p.values), copy(p.values)
  local out = {}
  say_all(st, st.at_row, out)
  return saved(st, out)
end

-- A factory patch copied into the song, and recalled: it depends on nothing after that.
function R.copy_factory(st, name)
  local row = row_on_show(st)
  if not row then return {} end
  local f = st.factory[row.instrument]
  local p = f and f.by[name]
  if not p then return { report("warn", "no-factory-patch") } end
  local n = unique(st, name)
  st.patches[n] = { instrument = row.instrument, values = copy(p) }
  st.order[#st.order + 1] = n
  local out = R.recall(st, n)
  return saved_patches(st, out)
end

-- save to patch: the row's sound becomes what its patch holds; with no patch yet, a new one.
function R.save(st, as_new)
  local row = row_on_show(st)
  if not row then return {} end
  if row.instrument == "kit" then return { { "kit", "bang", {} } } end
  local name = row.patch
  if as_new or not name then
    name = unique(st, row.patch or (row.instrument .. "-patch"))
    st.order[#st.order + 1] = name
  end
  st.patches[name] = { instrument = row.instrument, values = copy(row.values) }
  row.patch, row.base = name, copy(row.values)
  return saved_patches(st, {})
end

-- A section starts. Snap back (0): every voice's sound back to what it was saved as. Carry on (1): as it
-- stands (Brendan, 2026-11-06: it depends on the song and section).
function R.tweaks(st, keep)
  if num(keep) == 1 then return {} end
  local out = {}
  for r = 1, R.ROWS do
    local row = st.rows[r]
    local m = row and st.instruments[row.instrument]
    if row and row.base and m then
      local moved, chosen = {}, false
      for k, v in pairs(row.base) do
        if row.values[k] ~= v then
          row.values[k] = v
          moved[#moved + 1] = k
          chosen = chosen or CHOOSES[m.by[k] and m.by[k].how] or false
        end
      end
      if chosen then
        -- Its voice went back: what it was saved with chooses it alone, and the rest is said behind it.
        for _, q in ipairs(m.list) do
          if CHOOSES[m.by[q].how] and row.base[q] == nil then row.values[q] = nil end
        end
        say_all(st, r, out)
      else
        for _, k in ipairs(moved) do say(st, r, row, k, row.values[k], out) end
      end
      if #moved > 0 then st.dirty_sounds = true end
    end
  end
  return out
end

-- restore sounds / restore patches, as a song loads. Sounds are said out as they arrive.
function R.restore_patches(st, a)
  st.patches, st.order = {}, {}
  local i = 1
  while i <= #a do
    local name, instrument, n = a[i], a[i + 1], math.floor(num(a[i + 2]))
    if type(name) == "number" then name = string.format("%g", name) end
    i = i + 3
    local v = {}
    for _ = 1, n do
      v[a[i]] = num(a[i + 1])
      i = i + 2
    end
    if type(name) == "string" and type(instrument) == "string" then
      st.patches[name] = { instrument = instrument, values = v }
      st.order[#st.order + 1] = name
    end
  end
  return {}
end

function R.restore_sounds(st, a)
  local i = 1
  local out = {}
  st.loaded = true
  while i <= #a do
    local r, patch, instrument, n = math.floor(num(a[i])), a[i + 1], a[i + 2], math.floor(num(a[i + 3]))
    i = i + 4
    local v = {}
    for _ = 1, n do
      v[a[i]] = num(a[i + 1])
      i = i + 2
    end
    local row = st.rows[r]
    if row and row.instrument == instrument then
      row.values, row.base = v, copy(v)
      row.patch = type(patch) == "string" and patch ~= "-" and patch or nil
      say_all(st, r, out)
    end
  end
  return out
end

-- /cutit/sound: the voice on show's patch, the song's patches for its instrument, the factory's, then its
-- parameters, name and value.
function R.phone(st)
  local row = row_on_show(st)
  if not row then return { "-", 0, 0, 0 } end
  local a = { row.patch or "-" }
  local names = {}
  for _, n in ipairs(st.order) do
    if st.patches[n].instrument == row.instrument then names[#names + 1] = n end
  end
  a[#a + 1] = #names
  for _, n in ipairs(names) do a[#a + 1] = n end
  local f = st.factory[row.instrument]
  a[#a + 1] = f and #f.list or 0
  for _, n in ipairs(f and f.list or {}) do a[#a + 1] = n end
  local m = st.instruments[row.instrument]
  a[#a + 1] = m and #m.list or 0
  for _, p in ipairs(m and m.list or {}) do
    a[#a + 1] = p
    a[#a + 1] = value_of(st, row, p)
  end
  return a
end

-- The Launchpad's sound page (Brendan, 2026-11-06): the instrument's first eight parameters as columns on rows
-- 3 to 8, tapped to set; row 2 this instrument's song patches, tapped to recall; row 1 eight notes to hear it
-- with. A pad's p<row><column> <1 or 0>.
R.NOTES = { 60, 62, 64, 65, 67, 69, 71, 72 }
R.LEVELS = 6
function R.pad(st, nn, value)
  local row = row_on_show(st)
  if not row then return {} end
  local r, c = nn // 10, nn % 10
  if c < 1 or c > 8 or r < 1 or r > 8 then return {} end
  local down = num(value) > 0
  if r == 1 then
    local n = R.NOTES[c]
    st.held_note = down and c or 0
    if R.HARDWARE[row.instrument] then
      return { { row.instrument, "note", { n, down and 90 or 0 } } }
    elseif row.engine and row.engine > 0 then
      return { { "engine", "hear", { row.engine, row.line, n, down and 1 or 0 } } }
    end
    return { { "keys", "list", { 4, n, down and 90 or 0 } } }
  end
  if not down then return {} end
  if r == 2 then
    local names = {}
    for _, n in ipairs(st.order) do
      if st.patches[n].instrument == row.instrument then names[#names + 1] = n end
    end
    return names[c] and R.recall(st, names[c]) or {}
  end
  local m = st.instruments[row.instrument]
  local p = m and m.list[c]
  if not p then return {} end
  local v = (r - 2) / R.LEVELS
  local out = R.param(st, st.at_row .. ":" .. p, v)
  out[#out + 1] = { "heard", "list", { "instrument", p, v } }
  return out
end

-- g_grid: 8 levels, 0 for a column with no parameter or at the bottom; how many song patches this instrument
-- has; which is in use; the note held.
function R.grid(st)
  local a = {}
  local row = row_on_show(st)
  local m = row and st.instruments[row.instrument]
  for c = 1, 8 do
    local p = m and m.list[c]
    local v = p and value_of(st, row, p) or 0
    a[c] = p and math.max(v > 0 and 1 or 0, math.min(R.LEVELS, math.floor(v * R.LEVELS + 0.5))) or 0
  end
  local count, at = 0, 0
  if row then
    for _, n in ipairs(st.order) do
      if st.patches[n].instrument == row.instrument then
        count = count + 1
        if n == row.patch then at = count end
      end
    end
  end
  a[9], a[10], a[11] = count, at, st.held_note or 0
  return a
end

-- What arrives from the map: an instrument's parameter, <row>:<param>, or a pad on the sound page, p<nn>.
function R.mapped(st, sel, value)
  local nn = tostring(sel):match("^p(%d%d)$")
  if nn then return R.pad(st, tonumber(nn), value) end
  local vox = tostring(sel):match("^vox(%d)$")
  if vox then return num(value) > 0 and R.test_voice(st, tonumber(vox)) or {} end
  return R.param(st, sel, value)
end

-- A DX7 voice made here for the fm synth (Brendan, 2026-11-06), the diagnostics page's test that a whole
-- voice reaches it: sent as the library's are, into the program kept for them. Six operators, OP6 first,
-- 21 bytes each; then the pitch EG, the algorithm and the rest, and the name: 155 bytes.
local function operator(level, coarse, fine, decay, sustain)
  return { 99, decay, 40, 50,           -- EG rates
           99, sustain, sustain // 2, 0,  -- EG levels
           39, 0, 0, 0, 0,              -- keyboard scaling, its breakpoint, depths and curves
           2, 0, 2,                     -- rate scaling, amp mod sensitivity, velocity sensitivity
           level, 0, coarse, fine, 7 }  -- output level, ratio mode, coarse, fine, detune centered
end

local function voice_bytes(name, algorithm, feedback, ops)
  local d = {}
  for _, op in ipairs(ops) do
    for _, b in ipairs(op) do d[#d + 1] = b end
  end
  for _, b in ipairs({ 99, 99, 99, 99, 50, 50, 50, 50 }) do d[#d + 1] = b end   -- pitch EG, flat
  for _, b in ipairs({ algorithm - 1, feedback, 1, 35, 0, 0, 0, 0, 0, 3, 24 }) do d[#d + 1] = b end
  for i = 1, 10 do d[#d + 1] = string.byte(name, i) or 32 end
  return dump(d)
end

-- Two voices nothing like each other or like its presets: a glassy bell, and a growling bass.
R.TEST_VOICES = {
  voice_bytes("CUTIT BELL", 5, 3, {
    operator(0, 1, 0, 30, 0), operator(99, 1, 0, 40, 0), operator(70, 3, 50, 45, 0),
    operator(92, 1, 0, 35, 0), operator(82, 7, 0, 50, 0), operator(99, 1, 0, 28, 0) }),
  voice_bytes("CUTIT BASS", 1, 7, {
    operator(50, 1, 0, 50, 40), operator(70, 1, 0, 60, 60), operator(80, 2, 0, 60, 50),
    operator(85, 1, 0, 40, 50), operator(90, 1, 0, 45, 70), operator(99, 1, 0, 40, 90) }),
}

function R.test_voice(st, n)
  local v = R.TEST_VOICES[math.floor(num(n))]
  local m = st.instruments.fm
  if not (v and m and m.voice) then return {} end
  local out = into_slot("fm", m, v, {})
  -- Whatever row held a DX7 voice no longer has it there.
  for r = 1, R.ROWS do
    if st.rows[r] then st.rows[r].voiced = nil end
  end
  return out
end

R.phone_cmds = {
  vox = function(st, a) return R.test_voice(st, a[1]) end,
  patch = function(st, a) return R.recall(st, a[1]) end,
  copy = function(st, a) return R.copy_factory(st, a[1]) end,
  save = function(st) return R.save(st, false) end,
  saveas = function(st) return R.save(st, true) end,
}

R.internal = {
  init = function() return {} end,
  rows = function(st, a) return R.rows(st, a) end,
  restore = function(st, a)
    local key = a[1]
    local rest = { table.unpack(a, 2) }
    if key == "patches" then return R.restore_patches(st, rest) end
    if key == "sounds" then return R.restore_sounds(st, rest) end
    if key == "tweaks" then return R.tweaks(st, rest[1]) end
    return {}
  end,
}

return R
