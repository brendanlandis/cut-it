-- g_grid.lua -- the Launchpad's home: every page's cells and the edges, from what the instrument
-- says of itself, meaning and never a cell (C-5). Plain Lua with no Pd in it, so
-- test/gate/lua/g_grid_test.lua runs it on the Mac with lua.org's interpreter. g_grid-lua.pd_lua is
-- its Pd face, which writes a frame's cells into g_grid's frame buffer, and g_grid.pd keeps
-- everything else: the layers, the frame clock and the SysEx. ref/module/display.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the page. Every rule but R.paint returns what leaves, in order, as {outlet, selector, atoms}:
--   {"err", "fail", {"g_grid", text}}    to err (C-12)
-- R.paint returns the cells to write, their colors and how many.

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
R.PAD_ON = 148       -- the selected pad, red
-- A pad whose track won't play, muted or left out of a solo, dim: the pink, and the selected
-- pad's red, at a quarter (Brendan, 2026-11-05).
R.PAD_QUIET, R.PAD_ON_QUIET = 152, 153
-- The saved tempo, pad-38: dim blue, and bright while held (Brendan, 2026-11-05).
R.RECALL, R.RECALL_HELD = 154, 155
-- The edges: a section dim and full, revert's gray, save's red.
R.SECTION_DIM, R.SECTION_ON, R.REVERT, R.SAVE = 149, 150, 151, 148
-- A voice's color, by its row (Brendan, 2026-11-06): full at R.VOICE + 2(row - 1), dim one on.
R.VOICE = 156
-- A control on the performance page: a fader's level l, green at the bottom to red at the top, full
-- at R.FADER + l - 1 and dim at R.FADER_DIM + l - 1, while it is held at a value its control hasn't
-- been turned to; a knob blue, dim the same (Brendan, 2026-11-06).
R.FADER, R.FADER_DIM = 172, 180
R.KNOB, R.KNOB_DIM = 188, 189
-- Harmony and melody's pads that aren't a voice's: white held, a dim note of the mode.
R.WHITE = 128
-- The melody page's rows of pitch: this many notes of the mode, low to high from the bottom left.
R.PITCHES = 32
-- The harmony page's rhythm: seven rows of eight.
R.RHYTHM = 56

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
               fast = 0, recall = 0, quiet = {},
               -- The page and the edges.
               page = "perform", kind = "perform", at_row = 0, beat = 0, top = {}, unsaved = 0,
               methods = {},
               -- The generator's, the voice on show's.
               chords = 0, sounding = 0, on_h = 0, on_m = 0, total = 16, bass = 0, style = 1,
               starts = {}, loop = 32, tonic = 0, scale = { 0, 2, 4, 5, 7, 9, 11 }, notes = {},
               codes = {}, t = -1, m = -1, held_chord = 0, held_step = 0, held_note = 0,
               -- The performance page's.
               cols = {}, btns = {}, cells = {}, ci = {}, cc = {},
               -- The sound page's.
               levels = { 0, 0, 0, 0, 0, 0, 0, 0 }, n_patches = 0, patch_at = 0, note_at = 0 }
  for k = 1, 8 do st.top[k], st.methods[k], st.starts[k] = 0, "-", -1 end
  for k = 1, R.STEPS do st.notes[k], st.codes[k] = 0, 0 end
  for k = 1, 8 do st.cols[k] = { 0, 0, 0 } end
  for k = 1, 16 do st.btns[k] = { 0, 0 } end
  for i = 1, R.STEPS do st.steps[i] = 0 end
  for t = 1, R.PADS do st.quiet[t] = 0 end
  -- The cells paint writes: a row whose role is none of these paints nothing, as Pd's
  -- [select step vel pad rep] passed it by, so it is left out here.
  local index, role, n = R.parse(text)
  st.index, st.kind_of, st.n, st.r, st.c, st.colors = {}, {}, {}, {}, {}, {}
  for k = 1, #index do
    if ROLE[role[k]] then
      local j = #st.index + 1
      st.index[j], st.kind_of[j], st.n[j] = index[k], ROLE[role[k]], n[k]
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
  for k = 1, #st.kind_of do
    if st.kind_of[k] == 1 then
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
  -- page <name>, the mode bus.
  page = function(st, a)
    if type(a[1]) == "string" then st.page = a[1] end
    return {}
  end,
  -- beat <n>, for what blinks.
  beat = function(st, a)
    st.beat = num(a[1])
    return {}
  end,
  -- top <8 lamps> and unsaved <0 or 1>, from u_song.
  top = function(st, a)
    for k = 1, 8 do st.top[k] = num(a[k]) end
    return {}
  end,
  unsaved = function(st, a)
    st.unsaved = num(a[1])
    return {}
  end,
  -- voices <row> <kind> <8 methods>, from u_voices: the row on show and each row's method.
  voices = function(st, a)
    st.at_row, st.kind = num(a[1]), a[2]
    for k = 1, 8 do st.methods[k] = a[k + 2] end
    return {}
  end,
  -- melody <67 atoms>, the generator's state for the phone: the harmony page reads its own.
  melody = function(st, a)
    st.chords, st.sounding, st.on_h, st.on_m = num(a[1]), num(a[7]), num(a[8]), num(a[9])
    st.total = math.max(1, num(a[12]))
    for k = 1, 8 do st.starts[k] = num(a[17 + (k - 1) * 4]) end
    st.style, st.bass = num(a[56]), num(a[57])
    return {}
  end,
  -- notes <73 atoms>: the loop, the tonic, the mode's seven, then 32 notes and 32 codes.
  notes = function(st, a)
    st.loop, st.tonic = num(a[1]), num(a[2])
    for d = 1, 7 do st.scale[d] = num(a[2 + d]) end
    for k = 1, R.STEPS do
      st.notes[k], st.codes[k] = num(a[9 + k]), num(a[41 + k])
    end
    return {}
  end,
  -- here <t> <step>: the loops' places, -1 stopped.
  here = function(st, a)
    st.t, st.m = num(a[1]), num(a[2])
    return {}
  end,
  -- held <chord> <step> <note>: what a finger holds on the harmony and melody pages.
  held = function(st, a)
    st.held_chord, st.held_step, st.held_note = num(a[1]), num(a[2]), num(a[3])
    return {}
  end,
  -- sound <8 levels> <patches> <the one in use> <the note held>, from u_sound.
  sound = function(st, a)
    for k = 1, 8 do st.levels[k] = num(a[k]) end
    st.n_patches, st.patch_at, st.note_at = num(a[9]), num(a[10]), num(a[11])
    return {}
  end,
  -- cols <8 of kind, level, held> and btns <16 of row, on>, from u_perform.
  cols = function(st, a)
    for k = 1, 8 do
      local c = st.cols[k]
      local b = (k - 1) * 3
      c[1], c[2], c[3] = num(a[b + 1]), num(a[b + 2]), num(a[b + 3])
    end
    return {}
  end,
  btns = function(st, a)
    for k = 1, 16 do
      local c = st.btns[k]
      local b = (k - 1) * 2
      c[1], c[2] = num(a[b + 1]), num(a[b + 2])
    end
    return {}
  end,
}

-- The melody page's pitch pads, low to high: the mode's notes from the lowest tonic at or above
-- R.PITCH_LOW. c_melody.lua works out the same to read a press.
R.PITCH_LOW = 44
function R.pitches(tonic, scale)
  local at = tonic
  while at < R.PITCH_LOW do at = at + 12 end
  local out, k = {}, 0
  local order = {}
  for d = 1, 7 do order[d] = (scale[d] - tonic) % 12 end
  table.sort(order)
  local n = at
  while k < R.PITCHES do
    for d = 1, 7 do
      k = k + 1
      out[k] = n + order[d]
      if k == R.PITCHES then break end
    end
    n = n + 12
  end
  return out
end

-- A grid index from a row, 1 at the bottom, and a column, 1 at the left.
local function pad(row, col)
  return row * 10 + col
end

-- What this frame lights, over the fill pd prepare wrote.
local function light(st, i, c)
  local n = st.n_cells + 1
  st.n_cells = n
  st.ci[n], st.cc[n] = i, c
end

local function voice_full(row) return R.VOICE + 2 * (row - 1) end
local function voice_dim(row) return R.VOICE + 2 * (row - 1) + 1 end

-- The edges, on every page. The top row from u_song; each row's two buttons in its voice's color,
-- full where the page is, dim elsewhere and dark with no voice; save and revert, but on the performance
-- page, whose bottom rows are the nanoKONTROL's buttons.
local function edges(st)
  local even = pdmod(st.beat, 2) == 0
  for k = 1, 8 do
    local v = st.top[k]
    local c = R.DARK
    if v == 1 then c = R.SECTION_DIM
    elseif v == 2 then c = R.SECTION_ON
    elseif v == 3 then c = even and R.SECTION_ON or R.DARK
    elseif v == 4 then c = R.DIM
    elseif v == 5 then c = R.BLUE
    elseif v == 6 then c = even and R.BLUE or R.DARK
    end
    if c ~= R.DARK then light(st, 90 + k, c) end
  end
  for r = 1, 8 do
    if st.methods[r] and st.methods[r] ~= "-" then
      local on = st.at_row == r
      light(st, 90 - 10 * r, (on and st.kind == "voice") and voice_full(r) or voice_dim(r))
      light(st, 99 - 10 * r, (on and st.kind == "setup") and voice_full(r) or voice_dim(r))
    end
  end
  if st.page ~= "perform" and st.unsaved ~= 0 then
    light(st, 108, R.SAVE)
    light(st, 8, R.REVERT)
  end
end

-- The drum page.
local function drums(st)
  local kind, n, colors = st.kind_of, st.n, st.colors
  local shows, at, blue = st.shows, st.at, st.blue
  local steps, play, last = st.steps, st.play, st.last
  local vel, track, rep, quiet, fast, recall = st.vel, st.track, st.rep, st.quiet, st.fast, st.recall
  local DARK, DIM, PLAYHEAD, BLUE = R.DARK, R.DIM, R.PLAYHEAD, R.BLUE
  local LEVEL, QUARTER = R.LEVEL - 1, R.QUARTER - 1
  local PAD, PAD_ON, REP, REP_HELD = R.PAD, R.PAD_ON, R.REP, R.REP_HELD
  local PAD_QUIET, PAD_ON_QUIET = R.PAD_QUIET, R.PAD_ON_QUIET
  for k = 1, #kind do
    local role = kind[k]
    local c
    if role == 1 then
      local s = shows[k]
      if s == play then
        c = PLAYHEAD
      elseif s > last then
        c = DARK
      else
        local lv = steps[at[k]]
        if lv < 1 then
          c = blue[k] and BLUE or DIM
        else
          c = lv + LEVEL
        end
      end
    elseif role == 2 then
      c = n[k] + (n[k] == vel and LEVEL or QUARTER)
    elseif role == 3 then
      local hushed = (quiet[n[k]] or 0) ~= 0
      if n[k] == track then
        c = hushed and PAD_ON_QUIET or PAD_ON
      else
        c = hushed and PAD_QUIET or PAD
      end
    elseif role == 4 then
      c = n[k] == rep and REP_HELD or REP
    elseif role == 5 then
      c = fast ~= 0 and REP_HELD or REP
    else
      c = recall ~= 0 and R.RECALL_HELD or R.RECALL
    end
    colors[k] = c
    if c ~= DARK then light(st, st.index[k], c) end
  end
end

-- The harmony page (Brendan, 2026-11-06): the chords on the top row, in their playing order, full on
-- the one sounding; seven rows of rhythm below, each chord lit where it starts, a blue step every N,
-- green where the loop is, and a longer rhythm shows the part that's playing; the commands on the
-- upper bottom row: on, roll chords, roll rhythm, bass only and modal or functional.
local function harmony(st)
  local row = st.at_row > 0 and st.at_row or 1
  local full, dim = voice_full(row), voice_dim(row)
  for k = 1, 8 do
    if k <= st.chords then
      local c = st.held_chord == k and R.WHITE or (st.sounding == k and full or dim)
      light(st, pad(8, k), c)
    end
  end
  local window = st.t >= 0 and st.t // R.RHYTHM * R.RHYTHM or 0
  local at = {}
  for k = 1, st.chords do
    if st.starts[k] >= 0 then at[st.starts[k]] = k end
  end
  for s = 0, R.RHYTHM - 1 do
    local t = window + s
    if t < st.total then
      local r, c = s // 8, s % 8
      local i = pad(7 - r, c + 1)
      if t == st.t then
        light(st, i, R.PLAYHEAD)
      elseif at[t] then
        light(st, i, st.held_chord == at[t] and R.WHITE or full)
      elseif t % st.every == 0 then
        light(st, i, R.BLUE)
      else
        light(st, i, R.DIM)
      end
    end
  end
  light(st, 101, st.on_h ~= 0 and full or dim)
  light(st, 102, dim)
  light(st, 103, R.BLUE)
  light(st, 104, st.bass ~= 0 and full or dim)
  light(st, 105, st.style == 2 and full or dim)
end

-- The melody page (Brendan, 2026-11-06): 32 steps on the top four rows, a note in the voice's color,
-- a rest dim, green where the loop is; below, four rows of the mode's notes, low to high, the tonic
-- marked, lit on the note playing or held; on, roll and clear pins on the upper bottom row.
local function melody(st)
  local row = st.at_row > 0 and st.at_row or 1
  local full, dim = voice_full(row), voice_dim(row)
  for s = 1, R.STEPS do
    if s <= st.loop then
      local r, c = (s - 1) // 8, (s - 1) % 8
      local i = pad(8 - r, c + 1)
      if s == st.m then
        light(st, i, R.PLAYHEAD)
      elseif st.held_step == s then
        light(st, i, R.WHITE)
      elseif st.notes[s] > 0 then
        light(st, i, st.codes[s] >= 4 and R.WHITE or full)
      else
        light(st, i, R.DIM)
      end
    end
  end
  local now = st.held_note
  if now == 0 and st.held_step > 0 then now = st.notes[st.held_step] or 0 end
  if now == 0 and st.m > 0 then now = st.notes[st.m] or 0 end
  local list = R.pitches(st.tonic, st.scale)
  for d = 1, R.PITCHES do
    local n = list[d]
    local r, c = (d - 1) // 8, (d - 1) % 8
    local i = pad(r + 1, c + 1)
    if n == now then
      light(st, i, full)
    elseif n % 12 == st.tonic then
      light(st, i, dim)
    else
      light(st, i, R.DIM)
    end
  end
  light(st, 101, st.on_m ~= 0 and full or dim)
  light(st, 102, dim)
  light(st, 103, dim)
end

-- The performance page (Brendan, 2026-11-06): each column one control of the nanoKONTROL's first eight
-- groups, its fader green to red or its knob blue, whichever moved last, dimmer while held at a value
-- its control hasn't been turned to; the bottom rows its sixteen buttons, in their voices' colors, dim
-- off and bright on.
local function perform(st)
  for k = 1, 8 do
    local c = st.cols[k]
    local kind, level, held = c[1], c[2], c[3] ~= 0
    for l = 1, level do
      local color
      if kind == 1 then
        color = (held and R.FADER_DIM or R.FADER) + l - 1
      else
        color = held and R.KNOB_DIM or R.KNOB
      end
      light(st, pad(l, k), color)
    end
  end
  for k = 1, 16 do
    local b = st.btns[k]
    if b[1] > 0 then
      local i = k <= 8 and 100 + k or k - 8
      light(st, i, b[2] ~= 0 and voice_full(b[1]) or voice_dim(b[1]))
    end
  end
end

-- A voice's sound page (Brendan, 2026-11-06): its first eight parameters as columns on rows 3 to 8; row 2
-- its machine's song patches; row 1 eight notes to hear it with.
local function sound(st)
  local row = st.at_row > 0 and st.at_row or 1
  local full, dim = voice_full(row), voice_dim(row)
  for c = 1, 8 do
    for l = 1, st.levels[c] do light(st, pad(l + 2, c), full) end
    if c <= st.n_patches then light(st, pad(2, c), st.patch_at == c and full or dim) end
    light(st, pad(1, c), st.note_at == c and R.WHITE or R.DIM)
  end
end

-- The diagnostics page: its two pads, top left.
local function diag(st)
  light(st, 81, R.SECTION_ON)
  light(st, 82, R.BLUE)
  light(st, 83, voice_full(3))
  light(st, 84, voice_full(3))
end

-- The frame, at most 50 times a second: -> the cells, grid indices, and the color each takes, two
-- lists, the same tables every time, st.n_cells long. What isn't named is dark: pd prepare's fill.
--   a drum step cell: green under the playhead; else dark past the last step, lit or not; else its
--     level's color if on, and if off dim, or blue every Nth from step 1 (R.shape).
--   a velocity button: its level's color, full when selected and a quarter otherwise.
--   a pad: red when selected, bright pink otherwise; each at a quarter when its track won't play.
--   a repeat pad: the brightest purple, and whiter while held.
--   the 500 BPM repeat: the same, while it is held.
--   the saved tempo: blue, dim, and bright while held.
function R.paint(st)
  st.n_cells = 0
  local page = st.page
  if page == "drums" then drums(st)
  elseif page == "harmony" then harmony(st)
  elseif page == "melody" then melody(st)
  elseif page == "perform" then perform(st)
  elseif page == "sound" then sound(st)
  elseif page == "diag" then diag(st)
  end
  edges(st)
  return st.ci, st.cc, st.n_cells
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
