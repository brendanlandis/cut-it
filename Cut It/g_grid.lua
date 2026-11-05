-- g_grid.lua -- the drum page's painter, page 2 of the Launchpad: what each cell of the layout
-- table shows, from what c_steps says of the selected track. Plain Lua with no Pd in it, so
-- test/gate/lua/g_grid_test.lua runs it on the Mac with lua.org's interpreter. g_grid-lua.pd_lua
-- is its Pd face, which writes a frame's cells into g_grid's frame buffer, and g_grid.pd keeps
-- everything else: the layers, the mode lamps, the beat row, the other pages, the edges and the
-- SysEx. ref/module/display.md, g_grid's drum page.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the page. Every rule but R.paint returns what leaves, in order, as {outlet, selector, atoms}:
--   {"err", "fail", {"g_grid", text}}    to err (C-12)
-- R.paint returns the cells to write and their colors.

local R = {}

-- A color is what g_grid's frame buffer holds: a palette index below 128, and 128 + k for entry
-- k of g_grid.pd's RGB table, from 0 (paint's array define $0-rgb). g_grid_test.lua reads the
-- table and checks each entry named here is the color ref/module/display.md gives it.
R.DARK, R.DIM, R.PLAYHEAD = 0, 1, 21
R.LEVEL = 128        -- velocity level v at full brightness is R.LEVEL + v - 1, white to red
R.QUARTER = 136      -- ... and at a quarter, R.QUARTER + v - 1: a velocity button not selected
R.PAD = 144          -- a drum pad not selected, bright pink
R.BLUE = 145         -- every Nth step, off: blue
-- A repeat pad and the 500 BPM repeat, pad-35: the brightest purple there is at rest, and whiter,
-- not dimmer, while held (Brendan, 2026-11-05).
R.REP, R.REP_HELD = 146, 147
R.PAD_ON = 154       -- the selected pad, red
-- A pad whose track won't play, muted or left out of a solo, dim: the pink, and the selected
-- pad's red, at a quarter (Brendan, 2026-11-05).
R.PAD_QUIET, R.PAD_ON_QUIET = 158, 159
-- The saved tempo, pad-38: dim blue, and bright while held (Brendan, 2026-11-05).
R.RECALL, R.RECALL_HELD = 160, 161

-- The step cells are four rows of eight, numbered 1 to 32 along them by the layout table; the
-- selected track's levels are 32 long.
R.COLS, R.STEPS = 8, 32
-- The pads, one a track.
R.PADS = 16
-- The step a cell past its row shows: past every last step, so dark.
R.PAST = 33

local ROLE = { step = 1, vel = 2, pad = 3, rep = 4, fast = 5, recall = 6 }

-- A number made whole toward zero, as C's (int) makes it.
local function whole(x)
  return x < 0 and -((-x) // 1) or x // 1
end

-- Pd's [mod]: both sides whole, a divisor of 0 taken as 1 and a negative one as its size, and a
-- result never negative.
local function pdmod(a, b)
  b = whole(b < 0 and -b or b)
  if b == 0 then b = 1 end
  local r = math.fmod(whole(a), b)
  if r < 0 then r = r + b end
  return r
end

-- cut-it-drum-page.txt, `<index> <role> <n>` a line, the table u_map reads too, so a press and
-- its lamp cannot disagree. -> the cells in file order: index, role and n, a list each. A line
-- that is not that shape paints nothing, as Pd's [unpack f s f] made nothing of one.
function R.parse(text)
  local index, role, n = {}, {}, {}
  for line in string.gmatch(text or "", "[^\r\n]+") do
    local i, r, k = string.match(line, "^%s*(%S+)%s+(%S+)%s+(%S+)")
    i, k = tonumber(i), tonumber(k)
    if i and r and k and not tonumber(r) then
      index[#index + 1], role[#role + 1], n[#n + 1] = i, r, k
    end
  end
  return index, role, n
end

-- The page as c_steps last said it, starting where g_grid.pd's boxes started: every step off,
-- no playhead, no velocity button or pad selected, last step 16, a blue step every 4 and no step
-- to a row until the first bar, so every step cell dark, and no repeat pad, 500 BPM repeat or saved
-- tempo held; and every pad's track playing, as c_steps' start with nothing muted or soloed.
-- text: the layout table.
function R.new(text)
  local st = { steps = {}, play = 0, vel = 0, track = 0, last = 16, every = 4, row = 0, rep = 0,
               fast = 0, recall = 0, quiet = {} }
  for i = 1, R.STEPS do st.steps[i] = 0 end
  for t = 1, R.PADS do st.quiet[t] = 0 end
  -- The cells paint writes: a row whose role is none of these paints nothing, as Pd's
  -- [select step vel pad rep] passed it by, so it is left out here.
  local index, role, n = R.parse(text)
  st.index, st.kind, st.n, st.r, st.c, st.colors = {}, {}, {}, {}, {}, {}
  for k = 1, #index do
    if ROLE[role[k]] then
      local j = #st.index + 1
      st.index[j], st.kind[j], st.n[j] = index[k], ROLE[role[k]], n[k]
      -- a step cell's row and column, from 0, as g_grid.pd's expr worked them out: int((n - 1)
      -- / 8) and (n - 1) % 8, C's %, its sign the left side's
      st.r[j] = whole((n[k] - 1) / R.COLS)
      st.c[j] = math.fmod(whole(n[k] - 1), R.COLS)
      st.colors[j] = R.DARK
    end
  end
  R.shape(st)
  return st
end

-- What each step cell shows under the time signature, worked out when it changes rather than in
-- every frame: the step, its row r and column c from 0 being step r x row + c + 1, or R.PAST past
-- the row; where its level is in the 32, whole and held inside them, as [tabread] read it; and
-- whether it is blue when off, every Nth from step 1, by Pd's [mod].
function R.shape(st)
  st.shows, st.at, st.blue = {}, {}, {}
  local row, every = st.row, st.every
  for k = 1, #st.kind do
    if st.kind[k] == 1 then
      local s = st.c[k] < row and st.r[k] * row + st.c[k] + 1 or R.PAST
      local i = s < 1 and 0 or whole(s - 1)
      if i > R.STEPS - 1 then i = R.STEPS - 1 end
      st.shows[k], st.at[k], st.blue[k] = s, i + 1, pdmod(s - 1, every) == 0
    end
  end
end

local function num(v)
  return type(v) == "number" and v or 0
end

-- What reaches the face's first inlet: c_steps' page, meaning and never a cell (C-5). A field
-- left off, or one that is not a number, changes nothing, as it changed nothing in Pd; nor does
-- anything after a first field that is not one.
R.inputs = {
  -- steps <32 levels>, the selected track's, 0 for off. A shorter list sets the steps it holds.
  steps = function(st, a)
    if type(a[1]) ~= "number" then return {} end
    local s = st.steps
    for i = 1, math.min(#a, R.STEPS) do s[i] = num(a[i]) end
    return {}
  end,
  -- play <step>, the playhead, 0 while stopped.
  play = function(st, a)
    if type(a[1]) == "number" then st.play = a[1] end
    return {}
  end,
  -- vel <level>, the velocity button selected.
  vel = function(st, a)
    if type(a[1]) == "number" then st.vel = a[1] end
    return {}
  end,
  -- track <pad>, the pad selected.
  track = function(st, a)
    if type(a[1]) == "number" then st.track = a[1] end
    return {}
  end,
  -- last <step>, the selected track's last step.
  last = function(st, a)
    if type(a[1]) == "number" then st.last = a[1] end
    return {}
  end,
  -- bar <N> <row>, the time signature as the page shows it: a blue step every N, and row steps
  -- to a row of the page.
  bar = function(st, a)
    if type(a[1]) ~= "number" then return {} end
    st.every = a[1]
    if type(a[2]) == "number" then st.row = a[2] end
    R.shape(st)
    return {}
  end,
  -- rep <pad>, the repeat pad held, 0 for none.
  rep = function(st, a)
    if type(a[1]) == "number" then st.rep = a[1] end
    return {}
  end,
  -- fast <1 or 0>, the 500 BPM repeat held.
  fast = function(st, a)
    if type(a[1]) == "number" then st.fast = a[1] end
    return {}
  end,
  -- recall <1 or 0>, the saved tempo's pad held.
  recall = function(st, a)
    if type(a[1]) == "number" then st.recall = a[1] end
    return {}
  end,
  -- quiet <16 flags>, track 1 first: 1 for a track that won't play, muted or left out of a solo,
  -- whose pad shows dim. A shorter list sets the pads it holds.
  quiet = function(st, a)
    if type(a[1]) ~= "number" then return {} end
    local q = st.quiet
    for i = 1, math.min(#a, R.PADS) do q[i] = num(a[i]) end
    return {}
  end,
}

-- The frame's drum page, at most 50 times a second: -> the cells, grid indices, and the color
-- each takes, two lists in the layout table's order, the same tables every time.
--   a step cell: green under the playhead; else dark past the last step, lit or not; else its
--     level's color if on, and if off dim, or blue every Nth from step 1 (R.shape).
--   a velocity button: its level's color, full when selected and a quarter otherwise.
--   a pad: red when selected, bright pink otherwise; each at a quarter when its track won't
--     play.
--   a repeat pad: the brightest purple, and whiter while held.
--   the 500 BPM repeat: the same, while it is held.
--   the saved tempo: blue, dim, and bright while held.
function R.paint(st)
  local kind, n, colors = st.kind, st.n, st.colors
  local shows, at, blue = st.shows, st.at, st.blue
  local steps, play, last = st.steps, st.play, st.last
  local vel, track, rep, quiet, fast, recall = st.vel, st.track, st.rep, st.quiet, st.fast, st.recall
  local DARK, DIM, PLAYHEAD, BLUE = R.DARK, R.DIM, R.PLAYHEAD, R.BLUE
  local LEVEL, QUARTER = R.LEVEL - 1, R.QUARTER - 1
  local PAD, PAD_ON, REP, REP_HELD = R.PAD, R.PAD_ON, R.REP, R.REP_HELD
  local PAD_QUIET, PAD_ON_QUIET = R.PAD_QUIET, R.PAD_ON_QUIET
  for k = 1, #kind do
    local role = kind[k]
    if role == 1 then
      local s = shows[k]
      if s == play then
        colors[k] = PLAYHEAD
      elseif s > last then
        colors[k] = DARK
      else
        local lv = steps[at[k]]
        if lv < 1 then
          colors[k] = blue[k] and BLUE or DIM
        else
          colors[k] = lv + LEVEL
        end
      end
    elseif role == 2 then
      colors[k] = n[k] + (n[k] == vel and LEVEL or QUARTER)
    elseif role == 3 then
      local hushed = (quiet[n[k]] or 0) ~= 0
      if n[k] == track then
        colors[k] = hushed and PAD_ON_QUIET or PAD_ON
      else
        colors[k] = hushed and PAD_QUIET or PAD
      end
    elseif role == 4 then
      colors[k] = n[k] == rep and REP_HELD or REP
    elseif role == 5 then
      colors[k] = fast ~= 0 and REP_HELD or REP
    else
      colors[k] = recall ~= 0 and R.RECALL_HELD or R.RECALL
    end
  end
  return st.index, colors
end

-- What g_grid.pd itself sends: the load, answered with the proof bang, or layout-empty when the
-- table held no cell, so the page would paint nothing.
R.internal = {
  init = function(st)
    if #st.index == 0 then return { R.fail("layout-empty") } end
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "g_grid", string.sub(text, 1, 21) } }
end

return R
