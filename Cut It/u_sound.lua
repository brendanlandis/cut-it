-- u_sound.lua -- a voice's sound: each machine's parameters, the song's patches and the factory's
-- (Brendan, 2026-11-06). A patch is a machine's saved sound. Factory patches are starting points, in a
-- library outside songs; song patches live with the song, copied and depending on nothing after that.
-- Plain Lua with no Pd in it, so test/gate/lua/u_sound_test.lua runs it on the Mac with lua.org's
-- interpreter. u_sound-lua.pd_lua is its Pd face, and u_sound.pd keeps the cords. ref/module/voices.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves, in
-- order, as {outlet, selector, atoms}:
--   {"fm" | "strings", "cc" | "program", {...}}   that synth's device layer
--   {"engine", "tone", {engine, line, param, value}}   c_melody: a Pd voice's parameter
--   {"save", "sounds" | "patches", {atoms}}       the state bus: put song
--   {"heard", "list", {"machine", param, value}}  u_perform: a parameter moved on the Launchpad
--   {"kit", "bang", {}}                           c_steps: the kit's sound as it stands is what it snaps back to
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

-- cut-it-machines.txt: { machine = { list = {params in order}, by = {param = {how, n, default}} } }.
function R.parse_machines(text)
  local t = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    if not line:match("^%s*#") then
      local m, p, how, n, d = line:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")
      if m then
        t[m] = t[m] or { list = {}, by = {} }
        t[m].list[#t[m].list + 1] = p
        t[m].by[p] = { how = how, n = tonumber(n) or 0, default = tonumber(d) or 0 }
      end
    end
  end
  return t
end

-- cut-it-factory.txt: { machine = { list = {names}, by = {name = {param = value}} } }.
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

function R.new(machines_text, factory_text)
  local st = { machines = R.parse_machines(machines_text), factory = R.parse_factory(factory_text),
               rows = {}, patches = {}, order = {}, at_row = 0, last_sent = {} }
  return st
end

local function defaults(st, machine)
  local v = {}
  local m = st.machines[machine]
  if m then
    for _, p in ipairs(m.list) do v[p] = m.by[p].default end
  end
  return v
end

local function copy(t)
  local o = {}
  for k, x in pairs(t) do o[k] = x end
  return o
end

-- What a parameter's value says to its machine.
local function say(st, r, row, param, value, out)
  local m = st.machines[row.machine]
  local p = m and m.by[param]
  if not p then return out end
  if p.how == "cc" then
    out[#out + 1] = { row.machine, "cc", { p.n, math.floor(value * 127 + 0.5) } }
  elseif p.how == "pc" then
    out[#out + 1] = { row.machine, "program", { math.min(p.n - 1, math.floor(value * p.n)) } }
  elseif p.how == "pd" and row.engine and row.engine > 0 then
    out[#out + 1] = { "engine", "tone", { row.engine, row.line, param, value } }
  end
  return out
end

-- A row's whole sound said again: a machine taken up, a patch recalled, a song loaded.
local function say_all(st, r, out)
  local row = st.rows[r]
  local m = row and st.machines[row.machine]
  if not m then return out end
  for _, p in ipairs(m.list) do
    if row.values[p] ~= nil then say(st, r, row, p, row.values[p], out) end
  end
  return out
end

local function sounds_line(st)
  local a = {}
  for r = 1, R.ROWS do
    local row = st.rows[r]
    if row and st.machines[row.machine] then
      a[#a + 1] = r
      a[#a + 1] = row.patch or "-"
      a[#a + 1] = row.machine
      local list = st.machines[row.machine].list
      a[#a + 1] = #list
      for _, p in ipairs(list) do
        a[#a + 1] = p
        a[#a + 1] = tonumber(string.format("%.3f", row.values[p] or 0))
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
    a[#a + 1] = p.machine
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

-- u_voices: the row on show, and each row's machine, engine and line (- 0 - for none). A machine a row
-- has just taken up starts from its defaults; the rest is as it was.
function R.rows(st, a)
  st.at_row = math.floor(num(a[1]))
  local out = {}
  for r = 1, R.ROWS do
    local b = 2 + (r - 1) * 3
    local machine, engine, line = a[b], math.floor(num(a[b + 1])), a[b + 2]
    if machine == "-" or machine == nil then
      st.rows[r] = nil
    else
      local row = st.rows[r]
      if not row or row.machine ~= machine then
        st.rows[r] = { machine = machine, engine = engine, line = line, patch = nil,
                       values = defaults(st, machine) }
        st.rows[r].base = copy(st.rows[r].values)
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
  local m = st.machines[row.machine]
  if not (m and m.by[p]) then return { report("warn", "no-param-" .. tostring(p)) } end
  value = math.max(0, math.min(1, num(value)))
  row.values[p] = value
  st.dirty_sounds = true
  return say(st, r, row, p, value, {})
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
  if not row or not p or p.machine ~= row.machine then return {} end
  row.patch = name
  local v = defaults(st, row.machine)
  for k, x in pairs(p.values) do v[k] = x end
  row.values, row.base = v, copy(v)
  local out = {}
  say_all(st, st.at_row, out)
  return saved(st, out)
end

-- A factory patch copied into the song, and recalled: it depends on nothing after that.
function R.copy_factory(st, name)
  local row = row_on_show(st)
  if not row then return {} end
  local f = st.factory[row.machine]
  local p = f and f.by[name]
  if not p then return { report("warn", "no-factory-patch") } end
  local n = unique(st, name)
  st.patches[n] = { machine = row.machine, values = copy(p) }
  st.order[#st.order + 1] = n
  local out = R.recall(st, n)
  return saved_patches(st, out)
end

-- save to patch: the row's sound becomes what its patch holds; with no patch yet, a new one.
function R.save(st, as_new)
  local row = row_on_show(st)
  if not row then return {} end
  if row.machine == "kit" then return { { "kit", "bang", {} } } end
  local name = row.patch
  if as_new or not name then
    name = unique(st, row.patch or (row.machine .. "-patch"))
    st.order[#st.order + 1] = name
  end
  st.patches[name] = { machine = row.machine, values = copy(row.values) }
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
    if row and row.base then
      local changed = false
      for k, v in pairs(row.base) do
        if row.values[k] ~= v then
          row.values[k] = v
          say(st, r, row, k, v, out)
          changed = true
        end
      end
      if changed then st.dirty_sounds = true end
    end
  end
  return out
end

-- restore sounds / restore patches, as a song loads. Sounds are said out as they arrive.
function R.restore_patches(st, a)
  st.patches, st.order = {}, {}
  local i = 1
  while i <= #a do
    local name, machine, n = a[i], a[i + 1], math.floor(num(a[i + 2]))
    if type(name) == "number" then name = string.format("%g", name) end
    i = i + 3
    local v = {}
    for _ = 1, n do
      v[a[i]] = num(a[i + 1])
      i = i + 2
    end
    if type(name) == "string" and type(machine) == "string" then
      st.patches[name] = { machine = machine, values = v }
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
    local r, patch, machine, n = math.floor(num(a[i])), a[i + 1], a[i + 2], math.floor(num(a[i + 3]))
    i = i + 4
    local v = {}
    for _ = 1, n do
      v[a[i]] = num(a[i + 1])
      i = i + 2
    end
    local row = st.rows[r]
    if row and row.machine == machine then
      row.values, row.base = v, copy(v)
      row.patch = type(patch) == "string" and patch ~= "-" and patch or nil
      say_all(st, r, out)
    end
  end
  return out
end

-- /cutit/sound: the voice on show's patch, the song's patches for its machine, the factory's, then its
-- parameters, name and value.
function R.phone(st)
  local row = row_on_show(st)
  if not row then return { "-", 0, 0, 0 } end
  local a = { row.patch or "-" }
  local names = {}
  for _, n in ipairs(st.order) do
    if st.patches[n].machine == row.machine then names[#names + 1] = n end
  end
  a[#a + 1] = #names
  for _, n in ipairs(names) do a[#a + 1] = n end
  local f = st.factory[row.machine]
  a[#a + 1] = f and #f.list or 0
  for _, n in ipairs(f and f.list or {}) do a[#a + 1] = n end
  local m = st.machines[row.machine]
  a[#a + 1] = m and #m.list or 0
  for _, p in ipairs(m and m.list or {}) do
    a[#a + 1] = p
    a[#a + 1] = row.values[p] or 0
  end
  return a
end

-- The Launchpad's sound page (Brendan, 2026-11-06): the machine's first eight parameters as columns on rows
-- 3 to 8, tapped to set; row 2 this machine's song patches, tapped to recall; row 1 eight notes to hear it
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
    if R.HARDWARE[row.machine] then
      return { { row.machine, "note", { n, down and 90 or 0 } } }
    elseif row.engine and row.engine > 0 then
      return { { "engine", "hear", { row.engine, row.line, n, down and 1 or 0 } } }
    end
    return {}
  end
  if not down then return {} end
  if r == 2 then
    local names = {}
    for _, n in ipairs(st.order) do
      if st.patches[n].machine == row.machine then names[#names + 1] = n end
    end
    return names[c] and R.recall(st, names[c]) or {}
  end
  local m = st.machines[row.machine]
  local p = m and m.list[c]
  if not p then return {} end
  local v = (r - 2) / R.LEVELS
  local out = R.param(st, st.at_row .. ":" .. p, v)
  out[#out + 1] = { "heard", "list", { "machine", p, v } }
  return out
end

-- g_grid: 8 levels, 0 for a column with no parameter or at the bottom; how many song patches this machine
-- has; which is in use; the note held.
function R.grid(st)
  local a = {}
  local row = row_on_show(st)
  local m = row and st.machines[row.machine]
  for c = 1, 8 do
    local p = m and m.list[c]
    local v = p and (row.values[p] or 0) or 0
    a[c] = p and math.max(v > 0 and 1 or 0, math.min(R.LEVELS, math.floor(v * R.LEVELS + 0.5))) or 0
  end
  local count, at = 0, 0
  if row then
    for _, n in ipairs(st.order) do
      if st.patches[n].machine == row.machine then
        count = count + 1
        if n == row.patch then at = count end
      end
    end
  end
  a[9], a[10], a[11] = count, at, st.held_note or 0
  return a
end

-- What arrives from the map: a machine's parameter, <row>:<param>, or a pad on the sound page, p<nn>.
function R.mapped(st, sel, value)
  local nn = tostring(sel):match("^p(%d%d)$")
  if nn then return R.pad(st, tonumber(nn), value) end
  return R.param(st, sel, value)
end

R.phone_cmds = {
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
