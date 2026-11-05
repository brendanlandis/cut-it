-- c_steps.lua -- the drum sequencer's rules: the pattern, the step rule, the velocity levels, the
-- selected track and level, the last steps, each track's place in its loop, the time signature,
-- swing, drunkenness, the repeats, each track's randomness, volume and pitch, and which notes fire
-- on a step. Plain Lua with no Pd in it, so test/gate/lua/c_steps_test.lua runs it on the Mac with
-- lua.org's interpreter. c_steps-lua.pd_lua is its Pd face, and c_steps.pd keeps the clock, the
-- transport and the cords to c_kit, g_grid and u_state. ref/module/sequencer.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the pattern. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"note", "pad", {pad, velocity}}                          to c_kit
--   {"note", "vol" | "pitch", {pad, dB or semitones}}         to c_kit, a track's
--   {"page", "steps" | "play" | "vel" | "track" | "last" | "bar" | "rep", {...}}
--                                                             to g_grid's third inlet
--   {"save", "list", {581 numbers, R.save}}                   to the state bus, put section <part>
--   {"clock", "swing" | "rate", {x}}                          to c_steps.pd's step clock
--   {"bar", "bar", {}}                                        to u_song: the pattern's loop ends
--   {"err", "fail", {"c_steps", text}}                        to err (C-12)
--   {"disp", <row name>, {value[, unit]}}                     a knob's row, to disp
-- and R.phone(st), the phone's state, which the Pd face sends to u_net when it changes.

local R = {}

R.TRACKS, R.STEPS, R.LEVELS = 16, 32, 8
-- At load: level 6 (95), track 1, and a last step of 16 that both knobs are held at until they
-- are turned through it (Brendan, 2026-11-03), so nothing jumps to where a knob happens to sit.
R.BOOT_LEVEL, R.BOOT_TRACK, R.BOOT_LAST = 6, 1, 16
-- Swing, knob 4: 50% to 75%, straight at its bottom and swinging one way only (Brendan,
-- 2026-11-05), starting at 50% held like knobs 2 and 3 (2026-11-03). The share of a pair of
-- sixteenths the first one takes.
R.SWING_MIN, R.SWING_MAX = 50, 75
R.BOOT_SWING = 50
-- The time signature's bottom numbers. The bottom number is a matter of record only: it changes
-- neither the page nor how fast the steps go (Brendan, 2026-11-05).
R.DENS = { 1, 2, 4, 8, 16 }
R.MAX_NUM = 32
-- The drum page's steps are four rows of eight cells, as the layout table numbers its step cells,
-- 1 to 8 along the top row, 9 to 16 along the next. The top number N sets how many of a row's
-- cells hold steps: as many groups of N as fit in 8, so 3/4 and 6/8 give rows of 6 and 5/4 rows
-- of 5, and all 8 when N is over 8. The pattern reaches four rows' worth: 24 steps at 3/4, 32 at
-- 4/4 (Brendan, 2026-11-05).
R.ROW, R.ROWS = 8, 4
-- Drunk, at the slider's top every step strays, by up to two steps longer or shorter, and low
-- settings stay subtle (Brendan, 2026-11-05). At x, the slider's 0 to 1, a step strays with the
-- chance x/3 + 2x^4/3, by up to x + x^4 steps: a line, a third of the steps by up to the slider's
-- share of a step, which is most of it low, plus a steep x^4 that adds the rest near the top. At
-- 20% one step in fifteen strays, by up to a fifth of a step; at 50% one in five, by up to 0.56;
-- at 90% three in four, by up to 1.56.
R.DRUNK_STEEP = 4
function R.drunk_chance(drunk)
  local x = drunk / 100
  return x / 3 + 2 * x ^ R.DRUNK_STEEP / 3
end
function R.drunk_reach(drunk)
  local x = drunk / 100
  return x + x ^ R.DRUNK_STEEP
end
-- The shortest a drunk step gets, as a share of a step: a step two steps shorter would be less
-- than nothing, and a step of nothing would be two at once.
R.MIN_DUR = 0.125
-- The repeat pads, 1 to 4: each replays the last 1, 2, 3 or 4 steps (Brendan, 2026-11-03).
R.REPEATS = 4
-- Each track's own volume, in dB, and pitch, in semitones, played by its c_voice; and its
-- randomness, 0 to 100 (Brendan, 2026-11-05).
R.VOL_MIN, R.VOL_MAX = -30, 6
R.PITCH_MIN, R.PITCH_MAX = -12, 12
-- What R.save writes, in order; what it wrote until the song store, without the swing and the
-- global last step, which a section holds since (cut-it/songs-and-sections); and what it wrote
-- until 2026-11-05, when each track had a skip and a move chance where its randomness and its
-- volume are now, and no pitch.
R.SAVED = R.TRACKS * R.STEPS + 4 * R.TRACKS + 5
R.SAVED_SECTIONLESS = R.TRACKS * R.STEPS + 4 * R.TRACKS + 3
R.SAVED_CHANCES = R.TRACKS * R.STEPS + 3 * R.TRACKS + 3

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A number from a message, as Pd's [f] reads one: a symbol is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- Level n's velocity: 127n/8, rounded. 16 at 1, 127 at 8.
function R.velocity(level)
  return math.floor(127 * level / R.LEVELS + 0.5)
end

-- A velocity's level, whose color its step takes: 0 for off, else (v - 1) div 16 + 1, so each
-- level's own velocity is that level, and a pattern saved at any other velocity looks as it did
-- when g_grid worked this out.
function R.level(velocity)
  if velocity < 1 then return 0 end
  return clip((velocity - 1) // 16 + 1, 1, R.LEVELS)
end

-- The pattern's index of a track's step, both 1-based: track 1's 32 steps come first.
function R.index(track, step)
  return (track - 1) * R.STEPS + step
end

-- A track's pad: track n plays pad n of the bank, 1 for A (pads 1..160 across ten banks, the
-- SP-404's addressing; c_kit plays 1..16, so only bank 1 sounds).
function R.pad(st, track)
  return (st.bank - 1) * R.TRACKS + track
end

-- A row of the drum page, in steps: as many groups of the top number as fit in a row's 8
-- cells, or all 8 when it is over 8.
function R.row(st)
  if st.num > R.ROW then return R.ROW end
  return (R.ROW // st.num) * st.num
end

-- The furthest a last step reaches: four rows' worth, 24 at 3/4, 32 at 4/4.
function R.reach(st)
  return R.ROWS * R.row(st)
end

-- A knob's 0-1 as a last step, 1 to top, 32 unless given: a full turn reaches the last step
-- the time signature allows. At 32, 16 sits just left of noon.
function R.knob_step(v, top)
  return math.floor(clip(num(v), 0, 1) * ((top or R.STEPS) - 1) + 0.5) + 1
end

-- The global last step in force: as set, clipped to the reach. What is set is kept, and saved,
-- so a time signature passed through on the way to another does not cut it short for good.
function R.global_last(st)
  return math.min(st.last, R.reach(st))
end

-- A track's last step: its own, or the global one while it follows that (own is 0), clipped
-- to the reach as the global one is.
function R.last_of(st, track)
  local own = st.own[track]
  return math.min(own >= 1 and own or st.last, R.reach(st))
end

function R.new(bank)
  local st = { bank = math.floor(clip(num(bank), 1, 10)), pattern = {}, own = {}, pos = {},
               track = R.BOOT_TRACK, level = R.BOOT_LEVEL, last = R.BOOT_LAST,
               master = 0, sync = false, snap = false, playing = false,
               num = 4, den = 4, swing = R.BOOT_SWING, drunk = 0, rate = 1,
               randomness = {}, vol = {}, pitch = {}, hist = {},
               rep = 0, rk = 0, win = {}, rand = math.random,
               knob = { last = { held = true }, track = { held = true },
                        swing = { held = true } } }
  for i = 1, R.TRACKS * R.STEPS do st.pattern[i] = 0 end
  for t = 1, R.TRACKS do
    st.own[t], st.pos[t], st.hist[t] = 0, 0, {}
    st.randomness[t], st.vol[t], st.pitch[t] = 0, 0, 0
  end
  return st
end

-- The selected track's 32 steps as the page shows them: each one's level, 0 for off.
function R.steps(st)
  local row = {}
  for s = 1, R.STEPS do row[s] = R.level(st.pattern[R.index(st.track, s)]) end
  return { "page", "steps", row }
end

-- The selected track's last step, as the page shows it.
function R.page_last(st)
  return { "page", "last", { R.last_of(st, st.track) } }
end

-- The time signature as the page shows it, bar <N> <row>: a blue cell every N steps, N the top
-- number, whatever the subdivision, lit unless a note is; and rows of R.row steps. Over 8, the
-- blue counts straight through the pattern and wraps across the rows (Brendan, 2026-11-05).
function R.page_bar(st)
  return { "page", "bar", { st.num, R.row(st) } }
end

-- A press on the step cell n, 1 to 32, as the layout table numbers them, eight a row: the step
-- its row and column mean, row r and column c (from 0) being step r x R.row + c + 1, or nil
-- for a cell past the row's last step, which is dark.
function R.cell_step(st, n)
  local r, c = (n - 1) // R.ROW, (n - 1) % R.ROW
  if c >= R.row(st) then return nil end
  return r * R.row(st) + c + 1
end

-- The whole pattern, zeros included: 512 velocities, then the 16 tracks' own last steps, 0 for
-- one that follows the global last step, then their randomness, 0 to 100, their volumes in dB and
-- their pitches in semitones, then the time signature, the drunkenness, 0 to 100, the swing, 50 to
-- 75, and the global last step: 581 numbers. What a section holds of the drums and the
-- arrangement page (Brendan, 2026-11-04), put as the section's <part> (ref/module/songs.md).
function R.save(st)
  local all, cells = {}, R.TRACKS * R.STEPS
  for i = 1, cells do all[i] = st.pattern[i] end
  for t = 1, R.TRACKS do
    all[cells + t] = st.own[t]
    all[cells + R.TRACKS + t] = st.randomness[t]
    all[cells + 2 * R.TRACKS + t] = st.vol[t]
    all[cells + 3 * R.TRACKS + t] = st.pitch[t]
  end
  local n = cells + 4 * R.TRACKS
  all[n + 1], all[n + 2], all[n + 3] = st.num, st.den, st.drunk
  all[n + 4], all[n + 5] = st.swing, st.last
  return { "save", "list", all }
end

-- At load: the page's selection, before anything is pressed, and the step clock straight; and
-- the pattern, put, so the section playing holds the drums from the start (ref/module/songs.md).
function R.boot(st)
  return { { "page", "vel", { st.level } }, { "page", "track", { st.track } }, R.page_last(st),
           R.steps(st), R.page_bar(st), { "page", "rep", { st.rep } },
           { "clock", "swing", { st.swing / 100 } }, { "clock", "rate", { st.rate } }, R.save(st) }
end

-- A step press, on the selected track, on a step cell (R.cell_step). The step rule: off takes
-- the selected velocity; on, at any velocity, turns off. A cell past its row's last step, or a
-- step past the track's last step, is dark, and a press there does nothing.
function R.press_step(st, cell)
  local s = R.cell_step(st, math.floor(clip(num(cell), 1, R.STEPS)))
  if not s or s > R.last_of(st, st.track) then return {} end
  local i = R.index(st.track, s)
  if st.pattern[i] >= 1 then st.pattern[i] = 0 else st.pattern[i] = R.velocity(st.level) end
  return { R.save(st), R.steps(st) }
end

-- A velocity press selects its level. It plays nothing and changes no step.
function R.press_vel(st, level)
  st.level = clip(num(level), 1, R.LEVELS)
  return { { "page", "vel", { st.level } } }
end

-- A knob's latch: held until its step reaches or passes the one it stands for, so a knob that
-- sits elsewhere never jumps the value. The first held step decides the side it waits on.
-- -> true if the knob is live.
local function latch(k, n, cur)
  if not k.held then return true end
  local side = n < cur and "below" or "above"
  if n == cur or (k.side and k.side ~= side) then
    k.held, k.side = false, nil
    return true
  end
  k.side = side
  return false
end

-- Hold a knob again, against whatever it now stands for.
local function rearm(k)
  k.held, k.side = true, nil
end

-- A knob's row: the value while live, and the value it is held at with the knob's own step in
-- brackets while held, as u_map's c_mapped draws a held row.
local function row(name, live, value, n)
  if live then return { "disp", name, { value } } end
  return { "disp", name, { value, "(" .. n .. ")" } }
end

local function track_row(st)
  return "pad" .. st.track .. "-last"
end

-- Knob 4: swing, 50% to 75%, the share of each pair of sixteenths the first one takes, straight
-- at 50%, its bottom: above it every second sixteenth comes later (Brendan, 2026-11-05). Saved,
-- as a section's (Brendan, 2026-11-04); it starts at 50% with the knob held there, as knob 2 at
-- 16, and since 50% is the knob's bottom, it is held until turned all the way down. The step
-- clock takes it at the next pair, so a turn never moves a step already cut.
function R.knob_swing(st, v)
  local n = R.SWING_MIN + math.floor(clip(num(v), 0, 1) * (R.SWING_MAX - R.SWING_MIN) + 0.5)
  local live = latch(st.knob.swing, n, st.swing)
  if not live then return { { "disp", "swing", { st.swing, "(" .. n .. ")" } } } end
  local out = { { "disp", "swing", { n, "%" } } }
  if n ~= st.swing then
    st.swing = n
    out[#out + 1] = { "clock", "swing", { n / 100 } }
    out[#out + 1] = R.save(st)
  end
  return out
end

-- Knob 2: the global last step, 1 to the time signature's reach (R.reach), for every track that
-- follows it. Saved, as a section's, and it starts at 16 with the knob held there.
function R.knob_last(st, v)
  local n, cur = R.knob_step(v, R.reach(st)), R.global_last(st)
  local live = latch(st.knob.last, n, cur)
  if not live then return { row("last-step", false, cur, n) } end
  local out = { row("last-step", true, n) }
  if n ~= cur then
    st.last = n
    out[#out + 1] = R.save(st)
  end
  if st.own[st.track] == 0 then
    rearm(st.knob.track)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- The phone's swing and global last step, on the arrangement page (Brendan, 2026-11-04): each a
-- value as it stands, since swing and last are the knobs' positions and pass their latch. The
-- knob that sets the same value is held again at the phone's, so its next turn waits to pass it
-- rather than jumping back to wherever it sits. Both are saved, as the knobs' are; a message
-- with no number in it does nothing.
function R.set_swing(st, v)
  if type(v) ~= "number" then return {} end
  local n = math.floor(clip(v, R.SWING_MIN, R.SWING_MAX) + 0.5)
  if n == st.swing then return {} end
  st.swing = n
  rearm(st.knob.swing)
  return { { "clock", "swing", { n / 100 } }, R.save(st) }
end

function R.set_last(st, v)
  if type(v) ~= "number" then return {} end
  local n = math.floor(clip(v, 1, R.reach(st)) + 0.5)
  if n == R.global_last(st) then return {} end
  st.last = n
  rearm(st.knob.last)
  if st.own[st.track] ~= 0 then return { R.save(st) } end
  rearm(st.knob.track)
  return { R.save(st), R.page_last(st) }
end

-- Knob 3: the selected track's own last step. It is held whenever another track is selected,
-- until turned through that track's last step, and it is saved with the pattern. Released at the
-- step it already has, a track that follows the global one goes on following it.
function R.knob_track(st, v)
  local n, cur = R.knob_step(v, R.reach(st)), R.last_of(st, st.track)
  local live = latch(st.knob.track, n, cur)
  if not live then return { row(track_row(st), false, cur, n) } end
  local out = { row(track_row(st), true, n) }
  if n ~= cur then
    st.own[st.track] = n
    out[#out + 1] = R.save(st)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- The drum screen's "sync first steps": every track back to its step 1 together, the next time
-- the global loop comes round to its own step 1, each keeping its own last step (Brendan,
-- 2026-11-03).
function R.sync(st)
  st.sync = true
  return {}
end

-- The drum screen's "snap to global": the same, and at that same step every track follows the
-- global last step again.
function R.snap(st)
  st.sync, st.snap = true, true
  return {}
end

-- A pending snap, landed: every track on the global last step, saved, and knob 3 held again.
local function land_snap(st)
  st.snap = false
  for t = 1, R.TRACKS do st.own[t] = 0 end
  rearm(st.knob.track)
  return { R.save(st), R.page_last(st) }
end

-- The arrangement screen's time signature, two numbers, each stepped by its box (Brendan,
-- 2026-11-03): the top 1 to 32, the bottom through 1 2 4 8 16, both saved. The top number sets
-- the page's rows and its blue cells, and how far a last step reaches (R.row, R.reach): the
-- selected track's last step goes to the page again, clipped to it, and when the reach moves,
-- knobs 2 and 3 are held again, since a turn of either now stands for another step. The bottom
-- number is a matter of record only: it changes neither the page nor the step clock's rate
-- (Brendan, 2026-11-05).
function R.time(st, which, dir)
  local d = num(dir) < 0 and -1 or 1
  if which ~= "num" then
    local k = 3
    for i, v in ipairs(R.DENS) do if v == st.den then k = i end end
    st.den = R.DENS[clip(k + d, 1, #R.DENS)]
    return { R.save(st) }
  end
  local reach = R.reach(st)
  st.num = clip(st.num + d, 1, R.MAX_NUM)
  if R.reach(st) ~= reach then
    rearm(st.knob.last)
    rearm(st.knob.track)
  end
  return { R.save(st), R.page_bar(st), R.page_last(st) }
end

-- A value within its range, rounded: a percent, 0 to 100, a volume, a pitch, a last step.
local function whole(v, lo, hi)
  return math.floor(clip(num(v), lo, hi) + 0.5)
end

local function percent(v)
  return whole(v, 0, 100)
end

-- The arrangement screen's drunkenness, 0 to 100. Saved.
function R.drunk(st, v)
  st.drunk = percent(v)
  return { R.save(st) }
end

-- The drum screen's pads, each dragged for its own track, selected or not (Brendan, 2026-11-05):
-- a track's volume in dB, its pitch in semitones, its randomness, or its own last step, each as it
-- stands. Saved; a volume or a pitch goes to c_kit too, for the track's next hits. The same value
-- again, or a message without a track and a number, does nothing.
local function track_value(track, v)
  if type(track) ~= "number" or type(v) ~= "number" then return nil end
  return math.floor(clip(track, 1, R.TRACKS))
end

local function set_sound(st, which, lo, hi, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, lo, hi)
  if n == st[which][t] then return {} end
  st[which][t] = n
  return { R.save(st), { "note", which, { R.pad(st, t), n } } }
end

function R.set_vol(st, track, v)
  return set_sound(st, "vol", R.VOL_MIN, R.VOL_MAX, track, v)
end

function R.set_pitch(st, track, v)
  return set_sound(st, "pitch", R.PITCH_MIN, R.PITCH_MAX, track, v)
end

function R.set_randomness(st, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = percent(v)
  if n == st.randomness[t] then return {} end
  st.randomness[t] = n
  return { R.save(st) }
end

-- A track's own last step, set from its pad as knob 3 sets the selected track's, as far as the
-- time signature reaches: the step it already has changes nothing, so a track that follows the
-- global one goes on following it. Knob 3 is held again when the track is the selected one, as
-- at a phone's value of knob 2's.
function R.set_track_last(st, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, 1, R.reach(st))
  if n == R.last_of(st, t) then return {} end
  st.own[t] = n
  local out = { R.save(st) }
  if t == st.track then
    rearm(st.knob.track)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- A repeat pad, 1 to 4, held: every track replays the last n steps it played, over and over,
-- while the loops go on underneath unheard; let go, and every track plays from where it would
-- have been (Brendan, 2026-11-03). Pressed before anything has played, it waits for nothing:
-- there is nothing to replay. Letting go of a pad that is not the one repeating changes nothing.
function R.press_rep(st, n, velocity)
  local k = math.floor(clip(num(n), 1, R.REPEATS))
  if velocity == 0 then
    if st.rep ~= k then return {} end
    st.rep = 0
    return { { "page", "rep", { 0 } } }
  end
  if #st.hist[1] == 0 then return {} end
  for t = 1, R.TRACKS do
    local h, w = st.hist[t], {}
    for i = math.max(1, #h - k + 1), #h do w[#w + 1] = h[i] end
    st.win[t] = w
  end
  st.rep, st.rk = k, 0
  return { { "page", "rep", { k } } }
end

-- The drum screen selects a track without playing it, as a pad press does otherwise.
function R.select(st, track)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  return { { "page", "track", { st.track } }, R.page_last(st), R.steps(st) }
end

-- The sequencer's state, for the phone's drum and arrangement screens: playing (1 or 0), the
-- global last step, the selected track, a pending sync or snap (0 none, 1 sync, 2 snap), then
-- each track's last step, then 1 for each track with a last step of its own, then the time
-- signature, the drunkenness and the swing, then each track's volume, its pitch and its
-- randomness. 88 numbers.
R.PHONE = 4 + 2 * R.TRACKS + 4 + 3 * R.TRACKS
function R.phone(st)
  local out = { st.playing and 1 or 0, R.global_last(st), st.track,
                st.snap and 2 or (st.sync and 1 or 0) }
  for t = 1, R.TRACKS do out[#out + 1] = R.last_of(st, t) end
  for t = 1, R.TRACKS do out[#out + 1] = st.own[t] >= 1 and 1 or 0 end
  for _, v in ipairs({ st.num, st.den, st.drunk, st.swing }) do out[#out + 1] = v end
  for _, which in ipairs({ "vol", "pitch", "randomness" }) do
    for t = 1, R.TRACKS do out[#out + 1] = st[which][t] end
  end
  return out
end

-- A pad press plays the pad now, at full velocity however hard it is pressed (Brendan,
-- 2026-11-04), and selects its track; knob 3 is then held at that track's last step.
R.TAP = 127
function R.press_pad(st, track, velocity)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  return { { "note", "pad", { R.pad(st, st.track), R.TAP } },
           { "page", "track", { st.track } }, R.page_last(st), R.steps(st) }
end

-- What the next step does to the loops, without doing it: the global loop's step, every
-- track's, and whether a pending sync lands there. The global loop moves on; when it comes round
-- to its own step 1 a pending sync puts every track back before its step 1, and a pending snap
-- puts every track on the global last step; then every track moves on in its own loop.
local function advance(st)
  local m = st.master % R.global_last(st) + 1
  local synced = st.sync and m == 1
  local pos = {}
  for t = 1, R.TRACKS do
    local p = synced and 0 or st.pos[t]
    local last = (synced and st.snap) and R.global_last(st) or R.last_of(st, t)
    pos[t] = p % last + 1
  end
  return m, pos, synced
end

-- The step a track plays at a place in its loop: that place, or while a repeat pad is held, the
-- next of the steps it is replaying.
local function heard(st, t, p)
  if st.rep == 0 then return p end
  local w = st.win[t]
  return w[st.rk % #w + 1]
end

-- A step's velocity under its track's randomness (Brendan, 2026-11-05, after the DrumBrute's): at
-- R%, each step has an R% chance of ignoring what is written and flipping a coin instead: played or
-- not, and played at one of the eight levels, at random. So it drops hits from a busy track and
-- adds them to a sparse one; at 100 it is chaos, at 0 the pattern as written. A track at 0 never
-- rolls.
local function chance(st, t, v)
  local r = st.randomness[t]
  if r <= 0 or st.rand() * 100 >= r then return v end
  if st.rand() >= 0.5 then return 0 end
  return R.velocity(math.min(R.LEVELS, math.floor(st.rand() * R.LEVELS) + 1))
end

-- A step of the clock. The loops move on (advance), and every track plays the step it is heard
-- at (heard), as its randomness says, track 1 first, all in one logical instant. Then the
-- playhead, the selected track's step, and the step clock's rate for the step coming: drunk, a
-- step may last longer or shorter, the more often and the further the drunker (R.drunk_chance,
-- R.drunk_reach), and the error stays -- its own drift becomes the clock (Brendan, 2026-11-03).
-- Last, on the global loop's last step, bar: a bar is the pattern's loop (Brendan, 2026-11-05),
-- so the song store starts a queued section when the global loop next comes round to its step 1,
-- the whole pattern played, and its restore reaches here before that step is cut
-- (ref/module/songs.md).
function R.tick(st)
  local m, pos, synced = advance(st)
  local out = {}
  st.master = m
  if synced then
    st.sync = false
    if st.snap then out = land_snap(st) end
  end
  local play = {}
  for t = 1, R.TRACKS do
    st.pos[t] = pos[t]
    play[t] = heard(st, t, pos[t])
    local h = st.hist[t]
    h[#h + 1] = play[t]
    if #h > R.REPEATS then table.remove(h, 1) end
  end
  if st.rep > 0 then st.rk = st.rk + 1 end
  for t = 1, R.TRACKS do
    local v = chance(st, t, st.pattern[R.index(t, play[t])])
    if v >= 1 then out[#out + 1] = { "note", "pad", { R.pad(st, t), v } } end
  end
  out[#out + 1] = { "page", "play", { play[st.track] } }
  local rate = 1
  if st.drunk > 0 and st.rand() < R.drunk_chance(st.drunk) then
    local stray = (st.rand() * 2 - 1) * R.drunk_reach(st.drunk)
    rate = 1 / math.max(R.MIN_DUR, 1 + stray)
  end
  if rate ~= st.rate then
    st.rate = rate
    out[#out + 1] = { "clock", "rate", { rate } }
  end
  -- The pattern's loop ends when the next step is the global loop's step 1, as advance() counts
  -- it: a global last step moved under the loop's place wraps into it, and no bar ends there.
  if st.master % R.global_last(st) == 0 then out[#out + 1] = { "bar", "bar", {} } end
  return out
end

-- PLAY: every loop, the global one included, starts again at step 1 on the next step, which is
-- a sync already; a pending snap lands now. The step clock starts on the beat, at its own rate:
-- PLAY is the one thing that puts a drunk machine back on the clock. A held repeat lets go.
function R.start(st)
  st.master, st.sync, st.playing, st.rep = 0, false, true, 0
  for t = 1, R.TRACKS do st.pos[t], st.hist[t] = 0, {} end
  st.rate = 1
  local out = { { "clock", "rate", { 1 } }, { "page", "rep", { 0 } } }
  if st.snap then
    for _, e in ipairs(land_snap(st)) do out[#out + 1] = e end
  end
  return out
end

-- STOP and panic: the playhead goes out.
function R.stop(st)
  st.playing = false
  return { { "page", "play", { 0 } } }
end

-- A section's restore of <part>, from the song store, or u_state's of section-1-<part>, the auto
-- key the pattern had before sections, once, then put straight back (ref/module/state.md), which
-- also repairs a short or malformed line; and every track's volume and pitch to c_kit. A line of
-- exactly 256 is the 16-step pattern this replaced, track by track: its steps go to each track's
-- first sixteen. A line of exactly 563 is from before the randomness (2026-11-05): its skip
-- chances come back as each track's randomness, which took their place, its move chances are
-- dropped, and the volumes and pitches stay 0. Anything else is read as this file saves it, as far
-- as it goes, a symbol as 0, the rest left as they were: a line of 579, from before sections, keeps
-- the swing and the global last step in force, and one of 528, from before the phone's settings,
-- 4/4, sober, and no randomness. A bottom number that is not one of 1 2 4 8 16 is 4. A swing or a
-- global last step restored holds its knob again, as the phone's does, and the step clock takes
-- the swing. Every loop, the global one included, starts again at step 1 on the next step: a
-- section starts on its own step 1, whatever its last step and the one before it had, as PLAY
-- starts the pattern (ref/module/songs.md).
function R.restore(st, values)
  local cells = R.TRACKS * R.STEPS
  st.master = 0
  for t = 1, R.TRACKS do st.pos[t] = 0 end
  if #values == 256 then
    for t = 1, R.TRACKS do
      for s = 1, 16 do st.pattern[R.index(t, s)] = num(values[(t - 1) * 16 + s]) end
    end
  else
    local chances = #values == R.SAVED_CHANCES
    for i = 1, math.min(#values, cells) do st.pattern[i] = num(values[i]) end
    for t = 1, R.TRACKS do
      local v, k = values[cells + t], values[cells + R.TRACKS + t]
      if v ~= nil then st.own[t] = math.floor(clip(num(v), 0, R.STEPS)) end
      if k ~= nil then st.randomness[t] = percent(k) end
      if not chances then
        local db, p = values[cells + 2 * R.TRACKS + t], values[cells + 3 * R.TRACKS + t]
        if db ~= nil then st.vol[t] = whole(db, R.VOL_MIN, R.VOL_MAX) end
        if p ~= nil then st.pitch[t] = whole(p, R.PITCH_MIN, R.PITCH_MAX) end
      end
    end
    local n = cells + (chances and 3 or 4) * R.TRACKS
    if values[n + 1] ~= nil then st.num = math.floor(clip(num(values[n + 1]), 1, R.MAX_NUM)) end
    if values[n + 2] ~= nil then
      local d = num(values[n + 2])
      st.den = 4
      for _, v in ipairs(R.DENS) do if v == d then st.den = v end end
    end
    if values[n + 3] ~= nil then st.drunk = percent(values[n + 3]) end
    if not chances and values[n + 4] ~= nil then
      st.swing = whole(values[n + 4], R.SWING_MIN, R.SWING_MAX)
      rearm(st.knob.swing)
    end
    if not chances and values[n + 5] ~= nil then
      st.last = whole(values[n + 5], 1, R.STEPS)
      rearm(st.knob.last)
      if st.own[st.track] == 0 then rearm(st.knob.track) end
    end
  end
  local out = { R.save(st), R.page_last(st), R.steps(st), R.page_bar(st),
                { "clock", "swing", { st.swing / 100 } } }
  for _, which in ipairs({ "vol", "pitch" }) do
    for t = 1, R.TRACKS do out[#out + 1] = { "note", which, { R.pad(st, t), st[which][t] } } end
  end
  return out
end

-- A press's velocity: 0 is a release, which only a repeat pad acts on.
local function pressed(a)
  return a[1] ~= nil and a[2] ~= 0
end

-- What arrives on the first inlet: u_map's drum-page presses and releases, <selector> <n>
-- <velocity>; its knobs, last, track-last and swing with the knob's 0-1; the drum screen's sync,
-- snap and select, and its pads' vol, pitch, randomness and set-track-last <track> <value>,
-- through u_net; and the arrangement screen's num and den (-1 or 1), drunk (0 to 100), set-swing
-- (50 to 75) and set-last (1 to 32), through u_net too. A press, a knob or a setting with no
-- number in it does nothing.
R.presses = {
  step = function(st, a) return pressed(a) and R.press_step(st, a[1]) or {} end,
  vel = function(st, a) return pressed(a) and R.press_vel(st, a[1]) or {} end,
  pad = function(st, a) return pressed(a) and R.press_pad(st, a[1], a[2]) or {} end,
  rep = function(st, a) return a[1] and R.press_rep(st, a[1], a[2]) or {} end,
  last = function(st, a) return a[1] and R.knob_last(st, a[1]) or {} end,
  ["track-last"] = function(st, a) return a[1] and R.knob_track(st, a[1]) or {} end,
  swing = function(st, a) return a[1] and R.knob_swing(st, a[1]) or {} end,
  sync = function(st) return R.sync(st) end,
  snap = function(st) return R.snap(st) end,
  select = function(st, a) return a[1] and R.select(st, a[1]) or {} end,
  num = function(st, a) return a[1] and R.time(st, "num", a[1]) or {} end,
  den = function(st, a) return a[1] and R.time(st, "den", a[1]) or {} end,
  drunk = function(st, a) return a[1] and R.drunk(st, a[1]) or {} end,
  vol = function(st, a) return R.set_vol(st, a[1], a[2]) end,
  pitch = function(st, a) return R.set_pitch(st, a[1], a[2]) end,
  randomness = function(st, a) return R.set_randomness(st, a[1], a[2]) end,
  ["set-track-last"] = function(st, a) return R.set_track_last(st, a[1], a[2]) end,
  ["set-swing"] = function(st, a) return R.set_swing(st, a[1]) end,
  ["set-last"] = function(st, a) return R.set_last(st, a[1]) end,
}

-- What c_steps.pd itself sends: the clock's step, PLAY, STOP, u_state's restore, and the load.
R.internal = {
  tick = function(st) return R.tick(st) end,
  start = function(st) return R.start(st) end,
  stop = function(st) return R.stop(st) end,
  restore = function(st, a) return R.restore(st, a) end,
  init = function(st) return R.boot(st) end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_steps", string.sub(text, 1, 21) } }
end

return R
