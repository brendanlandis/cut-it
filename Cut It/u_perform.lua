-- u_perform.lua -- the controls in play: which of a voice's controls each of the nanoKONTROL's faders,
-- knobs and buttons moves, for this section, and where each stands (Brendan, 2026-11-06). Plain Lua
-- with no Pd in it, so test/gate/lua/u_perform_test.lua runs it on the Mac with lua.org's interpreter.
-- u_perform-lua.pd_lua is its Pd face, and u_perform.pd keeps the cords. ref/module/voices.md.
--
-- Taking a control into play: arm (REC, or the phone), move the control on the voice's page, then
-- move the physical one. It lasts for the section, whose list this is, and a new section copies it.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves, in
-- order, as {outlet, selector, atoms}:
--   {"route", "list", {dest, arg, value, target, live}}   u_map's route, as a mapped control's
--   {"err", "warn" | "fail", {"u_perform", text}}         err (C-12)
-- The Launchpad's columns and lights (R.cols, R.btns) and the phone's state (R.phone) are worked out
-- from the state by the face, and sent when they change.

local R = {}

R.GROUPS = 8

local function num(x)
  return type(x) == "number" and x or 0
end

local function report(level, text)
  return { "err", level, { "u_perform", string.sub(text, 1, 21) } }
end
function R.fail(text) return report("fail", text) end

-- cut-it-controls.txt: <dest> <arg> <kind> <label> a line, # a comment.
function R.parse(text)
  local t = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    if not line:match("^%s*#") then
      local dest, arg, kind, label = line:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")
      if dest then t[dest .. " " .. arg] = { kind = kind, label = label } end
    end
  end
  return t
end

function R.new(text)
  return { controls = R.parse(text), list = {}, armed = 0, heard = nil, rows = {}, at_row = 0,
           moved = {} }
end

local function name_of(what, n)
  return what .. "-" .. n
end

-- An address as the table writes it: Pd hands a number over as a float, and 0.0 isn't the table's 0.
-- What's known of a control: the table's row, or for a machine's parameter a value named for itself.
local function info_of(st, dest, arg)
  if type(arg) == "number" then arg = string.format("%g", arg) end
  if dest == "machine" then return { kind = "value", label = tostring(arg) } end
  local exact = st.controls[dest .. " " .. tostring(arg)]
  if exact then return exact end
  -- A row for every track's, its label with the track's number on.
  local name, n = tostring(arg):match("^(.-)%-(%d+)$")
  local row = name and st.controls[dest .. " " .. name .. "-*"]
  if row then return { kind = row.kind, label = row.label .. "-" .. n } end
  return nil
end

local function key_of(dest, arg)
  if type(arg) == "number" then arg = string.format("%g", arg) end
  return dest .. " " .. tostring(arg)
end

-- What goes to the map's route for an address: a generator's control names its engine, since the
-- other may be the one on show.
local function route(st, c, value)
  local arg = c.arg
  if c.dest == "melody" then
    arg = "e" .. math.max(1, st.rows[c.row] or 1) .. "-" .. arg
  elseif c.dest == "machine" then
    arg = c.row .. ":" .. arg
  end
  return { "route", "list", { c.dest, arg, value, value, 1 } }
end

-- A control moved, whoever moved it: the phone (always), the Launchpad or the Organelle's knobs, by
-- way of the map. Armed, it is the control to take into play. In play, its value follows.
function R.heard(st, row, dest, arg, value)
  local info = info_of(st, dest, arg)
  if st.armed == 1 and info then
    st.heard = { dest = dest, arg = arg, row = row, value = value }
    st.armed = 2
  end
  for _, c in pairs(st.list) do
    if c.dest == dest and c.arg == arg and (dest == "tempo" or dest == "rush" or dest == "drums" or c.row == row) then
      if info and info.kind == "toggle" then
        if value ~= 0 then c.value = 1 - c.value end
      else
        c.value = value
      end
      c.live, c.side = false, nil
    end
  end
  return {}
end

-- What leaves when the physical control is live.
local function hit(st, c, name, value)
  local info = info_of(st, c.dest, c.arg) or {}
  local button = name:match("^btn")
  if info.kind == "hit" then
    if button then return { route(st, c, 1) } end
    -- A fader or knob hits as it passes a half, or a sweep would be a roll a message.
    local was = c.value
    c.value = value
    if value >= 0.5 and was < 0.5 then return { route(st, c, 1) } end
    return {}
  elseif info.kind == "toggle" then
    if button or (value >= 0.5) ~= (c.value >= 0.5) then
      c.value = 1 - c.value
      return { route(st, c, 1) }
    end
    return {}
  end
  if button then
    c.value = c.value >= 0.5 and 0 or 1
    return { route(st, c, c.value) }
  end
  c.value = value
  return { route(st, c, value) }
end

-- A physical control: <name> <value>, 0 to 1. Armed with a control heard, it takes it, and is where
-- it is. A fader or knob held at a value waits to be turned to or through it.
function R.control(st, name, value)
  value = num(value)
  local button = name:match("^btn")
  if button and value == 0 then return {} end
  local lane = tonumber(name:match("%-(%d+)$"))
  if not lane or lane < 1 or lane > R.GROUPS then return {} end
  if st.armed == 2 and st.heard then
    local h = st.heard
    st.list[name] = { dest = h.dest, arg = h.arg, row = h.row, value = button and h.value or value,
                      live = true }
    st.armed, st.heard = 0, nil
    if not button then st.moved[lane] = name end
    st.dirty = true
    return { }
  end
  local c = st.list[name]
  if not c then return {} end
  if not button then
    st.moved[lane] = name
    if not c.live then
      local near = math.abs(value - c.value) < 0.012
      local above = value > c.value
      if near or (c.side ~= nil and c.side ~= above) then
        c.live, c.side = true, nil
      else
        c.side = above
        return {}
      end
    end
  end
  st.dirty = true
  return hit(st, c, name, value)
end

-- A column's pad on the Launchpad, pad-<row><column>: its fader goes to that height, or its knob with
-- no fader, and waits for the physical one to come to it. A toggle or a hit takes the tap as a press.
function R.pad(st, nn, value)
  if num(value) == 0 then return {} end
  local row, col = nn // 10, nn % 10
  if row < 1 or row > 8 or col < 1 or col > R.GROUPS then return {} end
  local name = name_of("slider", col)
  local c = st.list[name]
  if not c then
    name = name_of("knob", col)
    c = st.list[name]
  end
  if not c then return {} end
  c.live, c.side = false, nil
  st.moved[col] = name
  st.dirty = true
  local info = info_of(st, c.dest, c.arg) or {}
  if info.kind and info.kind ~= "value" then return hit(st, c, "btn", 1) end
  c.value = row / 8
  return { route(st, c, c.value) }
end

-- REC, or the phone's: armed, and again, not.
function R.arm(st, value)
  if num(value) == 0 then return {} end
  st.armed = st.armed == 0 and 1 or 0
  st.heard = nil
  return {}
end

-- The phone's page: a name tapped takes it out of play.
function R.remove(st, name)
  if not st.list[name] then return {} end
  st.list[name] = nil
  st.dirty = true
  return { }
end

-- ------------------------------------------------------------------ what the surfaces show

-- A lane's control on the Launchpad: whichever of its fader and knob moved last, the fader until then.
local function shown(st, lane)
  local slider, knob = st.list[name_of("slider", lane)], st.list[name_of("knob", lane)]
  if slider and knob then
    if st.moved[lane] == name_of("knob", lane) then return knob, 2 end
    return slider, 1
  end
  if slider then return slider, 1 end
  if knob then return knob, 2 end
  return nil, 0
end

local function level(v)
  if v <= 0 then return 0 end
  return math.max(1, math.min(8, math.ceil(v * 8 - 0.0001)))
end

-- cols <8 of kind (0 none, 1 fader, 2 knob), level (0 to 8), held (1 while waiting for its control)>.
function R.cols(st)
  local a = {}
  for lane = 1, R.GROUPS do
    local c, kind = shown(st, lane)
    a[#a + 1] = kind
    a[#a + 1] = c and level(c.value) or 0
    a[#a + 1] = (c and not c.live) and 1 or 0
  end
  return a
end

-- btns <16 of row (0 none), on>: the top row's eight, then the bottom's. A button in play lights by
-- the control's state, on above a half.
function R.btns(st)
  local a = {}
  for _, what in ipairs({ "btn-a", "btn-b" }) do
    for lane = 1, R.GROUPS do
      local c = st.list[name_of(what, lane)]
      a[#a + 1] = c and math.max(1, c.row) or 0
      a[#a + 1] = (c and c.value >= 0.5) and 1 or 0
    end
  end
  return a
end

local function label(st, c)
  if not c then return "-" end
  local info = info_of(st, c.dest, c.arg)
  return info and info.label or tostring(c.arg)
end

-- /cutit/perform: armed (0, 1 waiting for a control, 2 for a physical one), then for each of the eight
-- groups its knob and fader, label, row, value and held, and its two buttons, label, row and on, - 0 0
-- for one not in play. 113 atoms.
function R.phone(st)
  local a = { st.armed }
  for lane = 1, R.GROUPS do
    for _, what in ipairs({ "knob", "slider" }) do
      local c = st.list[name_of(what, lane)]
      a[#a + 1] = label(st, c)
      a[#a + 1] = c and c.row or 0
      a[#a + 1] = c and c.value or 0
      a[#a + 1] = (c and not c.live) and 1 or 0
    end
    for _, what in ipairs({ "btn-a", "btn-b" }) do
      local c = st.list[name_of(what, lane)]
      a[#a + 1] = label(st, c)
      a[#a + 1] = c and c.row or 0
      a[#a + 1] = (c and c.value >= 0.5) and 1 or 0
    end
  end
  return a
end

-- ------------------------------------------------------------------ what arrives

-- restore perform <atoms>: the section starting holds this list, each waiting for its control.
function R.restore(st, a)
  st.list, st.moved = {}, {}
  for i = 1, #a, 5 do
    local name, dest, arg, row, value = a[i], a[i + 1], a[i + 2], a[i + 3], a[i + 4]
    if type(name) == "string" and type(dest) == "string" then
      st.list[name] = { dest = dest, arg = arg, row = num(row), value = num(value), live = false }
    end
  end
  st.armed, st.heard = 0, nil
  return {}
end

-- From u_map, <arg> <value>.
function R.mapped(st, sel, a)
  if sel == "arm" then return R.arm(st, a[1]) end
  local nn = tostring(sel):match("^pad%-(%d+)$")
  if nn then return R.pad(st, math.floor(tonumber(nn)), a[1]) end
  return R.control(st, sel, a[1])
end

-- From the phone: ctl <row> <dest> <arg> <value>, any of the voice pages' controls; arm; remove.
R.phone_cmds = {
  ctl = function(st, a)
    local row, dest, arg, value = math.floor(num(a[1])), a[2], a[3], num(a[4])
    if type(dest) ~= "string" then return { R.fail("bad-ctl") } end
    R.heard(st, row, dest, arg, value)
    return { route(st, { dest = dest, arg = arg, row = row }, value) }
  end,
  arm = function(st) return R.arm(st, 1) end,
  remove = function(st, a) return R.remove(st, a[1]) end,
  press = function(st, a) return R.control(st, a[1], 1) end,
}

R.internal = {
  init = function() return {} end,
  restore = function(st, a) return R.restore(st, a) end,
  -- rows <the row on show> <8 engines>, from u_voices.
  rows = function(st, a)
    st.at_row = math.floor(num(a[1]))
    for r = 1, 8 do st.rows[r] = math.floor(num(a[r + 1])) end
    return {}
  end,
  -- heard <dest> <arg> <value>, from the map: a control moved on the page on show.
  heard = function(st, a)
    return R.heard(st, st.at_row, a[1], a[2], num(a[3]))
  end,
}

return R
