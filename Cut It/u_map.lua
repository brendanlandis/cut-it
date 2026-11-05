-- u_map.lua -- the map's rules: the table, the lookup key's mode, the lookup, the divisor and
-- parameter pickup. Plain Lua with no Pd in it, so
-- test/gate/lua/u_map_test.lua runs it on the Mac with lua.org's interpreter.
-- u_map-lua.pd_lua is its Pd face, and u_map.pd keeps the mode keys, the destination route and
-- its handlers, the boot timers and the files pickup reads. ref/module/map.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves,
-- in order, as {outlet, selector, atoms}:
--   {"route", "list", {dest, arg, value, target, live}}  to u_map.pd's destination route
--   {"store", "list", {mode}}                            the page, to u_state as an auto key
--   {"err", "fail", {"u_map", text}}                     to err (C-12)

local R = {}

-- The lookup key's mode until the mode bus says otherwise: set when the state is made, not by
-- the 500 ms seed, since mother pushes knobs.txt before that (item 234).
R.BOOT_MODE = "mode-1"

-- The pages, mode-1 to mode-8, one per key down the Launchpad's left column, CC 80 to 10
-- (Brendan, 2026-11-04; ref/module/map.md).
R.PAGES = 8

-- The Organelle's knobs: the only controls that arrive 0-1 already (mother's own scale), and
-- the only ones pickup holds.
R.KNOBS = { ["og-knob-1"] = 1, ["og-knob-2"] = 2, ["og-knob-3"] = 3, ["og-knob-4"] = 4 }

-- Knob 1's tempo (Brendan, 2026-11-05): a straight line, 40 BPM at its bottom to 250 at its top, where
-- music sits, now knob 4 has the flourishes. -> the 0-1 that c_mapped bpm 210 40 scales into those
-- BPM, so its held row reads the same line.
R.TEMPO_LOW, R.TEMPO_HIGH = 40, 250
function R.tempo_curve(x)
  return x
end

-- The line's inverse: where knob 1 sits for a BPM, at the nearer end of its turn for a BPM past its 40
-- to 250, so a knob held there is released by reaching that end, a hair off the rail, since a pot may
-- stop short of it.
function R.tempo_position(bpm)
  local x = (bpm - R.TEMPO_LOW) / (R.TEMPO_HIGH - R.TEMPO_LOW)
  if x < 0.01 then return 0.01 end
  if x > 0.99 then return 0.99 end
  return x
end

-- Knob 1 held at a BPM: what its held row reads is that BPM, past its reach or not, by c_mapped's own
-- scaling, where the knob waits for the place it can get to.
local function hold_knob_1(st, k, bpm)
  st.knob[k] = { state = "armed", target = R.tempo_position(bpm),
                 shown = (bpm - R.TEMPO_LOW) / (R.TEMPO_HIGH - R.TEMPO_LOW) }
end

-- A destination's curve, applied to its value and target as they leave: pickup compares the
-- knob's own positions, and the curve only changes what they mean.
R.CURVES = { tempo = R.tempo_curve }

-- A number from a message, as Pd's [f] reads one: a symbol or nothing is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- A message as Pd's list objects see it: its selector first, unless that is list, float or
-- symbol. `mode-1` is {mode-1}, `og-knob-1 0.5` is {og-knob-1, 0.5}; a bang is {}.
local function as_list(sel, atoms)
  if sel == "list" then return atoms end
  if sel == "float" or sel == "symbol" then return { atoms[1] } end
  if sel == "bang" then return {} end
  local l = { sel }
  for i = 1, #atoms do l[i + 1] = atoms[i] end
  return l
end

-- cut-it-map.txt's text, read as `read -c` did: a line or a ; ends a row, and a row is
-- <mode> <control> <dest> <arg>. The first row for a mode and control wins, as [text search]
-- found only the first, so a duplicate is dead: map-assert's lint catches it, and a row of any
-- other width, which is skipped here. -> the table by mode and control, and the rows counted.
function R.parse(text)
  local map, rows = {}, 0
  for line in (text or ""):gmatch("[^\n;]+") do
    local f = {}
    for w in line:gmatch("%S+") do f[#f + 1] = w end
    if #f > 0 then rows = rows + 1 end
    if #f == 4 then
      map[f[1]] = map[f[1]] or {}
      if not map[f[1]][f[2]] then
        map[f[1]][f[2]] = { dest = f[3], arg = tonumber(f[4]) or f[4] }
      end
    end
  end
  return map, rows
end

-- Where a knob is held when nothing has been Saved (Brendan, 2026-11-04): knob 1 is tempo in
-- every mode, and stays at 120 BPM, u_tempo's own, until it is turned through where its line puts
-- 120. A knob not named here is live from its first value.
R.UNSAVED = { [1] = R.tempo_position(120) }

-- Rush (Brendan, 2026-11-05): a knob the table maps to it is an absolute rate over its whole turn,
-- R.RUSH_LOW * (R.RUSH_TOP / R.RUSH_LOW) ^ x BPM, and held as knob 1 is, until turned to or through where the tempo in force
-- stands, so whichever knob moved last wins and the other does not jump. It starts held at u_tempo's
-- own 120, Saved or not, through the boot window, whose first value may be knobs.txt's and not where
-- the knob sits, and through a recover. u_tempo.lua has the curve's two ends too.
R.RUSH_LOW, R.RUSH_TOP = 10, 22000 * 15
R.BOOT_BPM = 120

-- The rush knob's rate at x.
function R.rush_bpm(x)
  return R.RUSH_LOW * (R.RUSH_TOP / R.RUSH_LOW) ^ x
end

-- Where the rush knob stands for a BPM: at its bottom for a BPM below its reach, as knob 1 for one
-- past its own, and that a hair off the rail, so a pot that stops short of 0 can still reach it.
function R.rush_position(bpm)
  return math.max(0.01, math.log(bpm / R.RUSH_LOW) / math.log(R.RUSH_TOP / R.RUSH_LOW))
end

-- Which knob the table maps to rush, on any page.
local function rush_knob(map)
  for _, page in pairs(map) do
    for name, k in pairs(R.KNOBS) do
      if page[name] and page[name].dest == "rush" then return k end
    end
  end
  return nil
end

-- A knob's pickup: "virgin" has never seen a value; "armed" has been restored, side unknown;
-- "above" sat above (or on) its target and waits for a fall, "below" waits for a rise; "live"
-- passes everything. The window is the boot's first 1000 ms, when a first value is a restore.
-- unsaved: the patch's folder holds no knobs.txt, so mother's boot push is where each knob
-- physically sits, not a restore (item 239).
function R.new(text, unsaved)
  local st = { mode = R.BOOT_MODE, window = true, knob = {} }
  st.map, st.rows = R.parse(text)
  st.rush_knob = rush_knob(st.map)
  for k = 1, 4 do
    local at = R.UNSAVED[k]
    if k == st.rush_knob then
      st.knob[k] = { state = "armed", target = R.rush_position(R.BOOT_BPM) }
    elseif not unsaved then
      st.knob[k] = { state = "virgin", target = 0 }
    elseif at then
      st.knob[k] = { state = "armed", target = at }
    else
      st.knob[k] = { state = "live", target = 0 }
    end
  end
  return st
end

-- Knob k's pickup, given its value: mother replays knobs.txt at boot, so a knob is held until
-- its value passes through the stored one, or the first touch would jump (item 236).
-- -> the target the message carries, and 1 if the knob is live or 0 if held.
function R.pickup(st, k, value)
  local p = st.knob[k]
  local above = p.target <= value
  if k == st.rush_knob and st.window then return p.target, 0 end
  if p.state == "virgin" then
    -- A first value passes either way; inside the window it is a restore, and arms. mother
    -- pushes a value with or without knobs.txt, which is why u_map.pd asks that file (item 239).
    p.target, p.state = value, st.window and "armed" or "live"
    return p.target, 1
  end
  if p.state == "armed" then
    p.state = above and "above" or "below"
  elseif p.state ~= "live" and ((p.state == "above") ~= above or value == p.target) then
    -- The side flipped, or the knob reached the target, which is in sync by definition: a
    -- target on a rail has no beyond to cross to (item 241).
    p.state = "live"
  end
  return p.target, p.state == "live" and 1 or 0
end

-- A control on param: <name> <value>. The value is divided into 0-1, pickup decides whether a
-- knob is held, and then the lookup. A mapped control leaves for its destination with its
-- target and live flag, held or not, so c_mapped can draw a held row. An unmapped one is silent
-- on every bus and on the screen: only a control the map binds names itself (Brendan,
-- 2026-11-04), so a page shows what its controls mean and nothing it does not use.
function R.control(st, sel, atoms)
  local m = as_list(sel, atoms)
  if #m == 0 then return {} end
  local name, raw = m[1], num(m[2])
  local k = R.KNOBS[name]
  local value = k and raw or raw / 127
  local target, live = value, 1
  if k then
    target, live = R.pickup(st, k, value)
    target = st.knob[k].shown or target
  end
  local row = st.map[st.mode] and st.map[st.mode][name]
  if row then
    local curve = R.CURVES[row.dest]
    if curve then value, target = curve(value), curve(target) end
    local out = {}
    if live == 1 then
      if row.dest == "rush" then
        -- Knob 4 has the tempo: knob 1 is held where that puts it, the bus at 1000 past the handoff.
        st.rushing = true
        local bpm = math.min(R.rush_bpm(value), 1000)
        for n, kk in pairs(R.KNOBS) do
          local r = (st.map[st.mode] or {})[n]
          if r and r.dest == "tempo" then hold_knob_1(st, kk, bpm) end
        end
      elseif row.dest == "tempo" and st.rush_knob then
        -- Knob 1 has it: rush is told it is over, before the BPM, and knob 4 is held at it.
        if st.rushing then
          st.rushing = false
          out[1] = { "route", "list", { "rush", 0, -1, 0, 1 } }
        end
        st.knob[st.rush_knob] = { state = "armed", target = R.rush_position(R.TEMPO_LOW + (R.TEMPO_HIGH - R.TEMPO_LOW) * value) }
      end
    end
    out[#out + 1] = { "route", "list", { row.dest, row.arg, value, target, live } }
    return out
  end
  return {}
end

-- A tempo a tap or the phone set, from u_tempo (Brendan, 2026-11-04): every knob the page maps to
-- tempo or rush is held again at where its curve puts that tempo, so its next turn waits to pass it
-- rather than jumping back to wherever the knob sits, as c_steps holds knobs 2 and 4 when the
-- phone sets the last step or the swing. Armed, so its first value decides the side it waits on.
-- Nothing leaves: the tempo bus already carries the tempo, and the held row is drawn when the knob
-- next moves. Anything but a number does nothing.
function R.hold_tempo(st, sel, atoms)
  local bpm = as_list(sel, atoms)[1]
  if type(bpm) ~= "number" then return {} end
  local page = st.map[st.mode] or {}
  for name, k in pairs(R.KNOBS) do
    local row = page[name]
    if row and row.dest == "tempo" then
      hold_knob_1(st, k, bpm)
    elseif row and row.dest == "rush" then
      st.knob[k] = { state = "armed", target = R.rush_position(bpm) }
    end
  end
  st.rushing = false
  return {}
end

-- A page's name, mode-1 to mode-<R.PAGES>, or nil for anything else.
function R.page(x)
  local n = type(x) == "string" and x:match("^mode%-(%d+)$")
  n = n and tonumber(n)
  if n and n >= 1 and n <= R.PAGES then return x end
  return nil
end

-- The mode bus: one atom, the page. Anything else is refused, and the atom must name a page:
-- a saved `compose` with its name missing once became the key, and every control missed (item
-- 294). The store gets only what the key took, so a bad mode is never saved to come back after
-- a power cycle (item 297). A mode the old code saved, <class> <page>, comes back as its page
-- alone: u_map.pd's restore drops the class before the bus.
function R.mode(st, sel, atoms)
  local m = as_list(sel, atoms)
  if #m ~= 1 or not R.page(m[1]) then return { R.fail("bad-mode") } end
  st.mode = m[1]
  return { { "store", "list", { m[1] } } }
end

-- What u_map.pd itself sends: the load, the boot window shutting at 1000 ms, and every knob
-- straight to live when the boot follows a recover (item 299), but one held for rush: left up, it
-- would race the tempo the moment it was touched.
R.internal = {
  init = function(st)
    if st.rows == 0 then return { R.fail("map-empty") } end
    return {}
  end,
  ["window-shut"] = function(st)
    st.window = false
    return {}
  end,
  live = function(st)
    for k = 1, 4 do
      if k ~= st.rush_knob then st.knob[k].state = "live" end
    end
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "u_map", string.sub(text, 1, 21) } }
end

return R
