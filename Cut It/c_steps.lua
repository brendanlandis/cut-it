-- c_steps.lua -- the drum sequencer's rules: the pattern, the step rule, the velocity levels, the
-- selected track and level, the last steps, each track's place in its loop, the time signature,
-- swing, drunkenness, the repeats, each track's chances, and which notes fire on a step. Plain Lua with no Pd in it, so test/gate/lua/c_steps_test.lua runs it on the Mac with
-- lua.org's interpreter. c_steps-lua.pd_lua is its Pd face, and c_steps.pd keeps the clock, the
-- transport and the cords to m_404, g_grid and u_state. ref/module/sequencer.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the pattern. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"note", "pad", {pad, velocity}}                          to m_404
--   {"page", "steps" | "play" | "vel" | "track" | "last" | "bar" | "rep", {...}}
--                                                             to g_grid's third inlet
--   {"save", "list", {563 numbers, R.save}}                   to u_state, as section-1-<part>
--   {"clock", "swing" | "rate", {x}}                          to c_steps.pd's step clock
--   {"err", "fail", {"c_steps", text}}                        to err (C-12)
--   {"disp", <row name>, {value[, unit]}}                     a knob's row, to disp
-- and R.phone(st), the drum screen's state, which the Pd face sends to u_net when it changes.

local R = {}

R.TRACKS, R.STEPS, R.LEVELS = 16, 32, 8
-- At load: level 6 (95), track 1, and a last step of 16 that both knobs are held at until they
-- are turned through it (Brendan, 2026-11-03), so nothing jumps to where a knob happens to sit.
R.BOOT_LEVEL, R.BOOT_TRACK, R.BOOT_LAST = 6, 1, 16
-- Swing, knob 4: 25% to 75%, straight at 50%, where it starts, held like knobs 2 and 3 (Brendan,
-- 2026-11-03). The share of a pair of sixteenths the first one takes.
R.SWING_MIN, R.SWING_MAX, R.BOOT_SWING = 25, 75, 50
-- The time signature's denominators: a bar is num x 16 / den steps, so den divides 16.
R.DENS = { 1, 2, 4, 8, 16 }
R.MAX_NUM = 32
-- Drunk, most steps stay on time (Brendan, 2026-11-04): the slider's share of this is the chance
-- a step strays, so at its top a third of them do.
R.DRUNK_CHANCE = 1 / 3
-- The shortest a drunk step gets, as a share of a step: at the slider's top a step strays up to
-- a whole step (Brendan, 2026-11-03), and a step of nothing would be two at once.
R.MIN_DUR = 0.125
-- The repeat pads, 1 to 4: each replays the last 1, 2, 3 or 4 steps (Brendan, 2026-11-03).
R.REPEATS = 4
-- What R.save writes, in order.
R.SAVED = R.TRACKS * R.STEPS + 3 * R.TRACKS + 3

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

-- A track's pad: track n plays pad n of the bank, 1 for A (pads 1..160 across ten banks).
function R.pad(st, track)
  return (st.bank - 1) * R.TRACKS + track
end

-- A knob's 0-1 as a last step, 1 to 32: 16 sits just left of noon.
function R.knob_step(v)
  return math.floor(clip(num(v), 0, 1) * (R.STEPS - 1) + 0.5) + 1
end

-- A track's last step: its own, or the global one while it follows that (own is 0).
function R.last_of(st, track)
  local own = st.own[track]
  return own >= 1 and own or st.last
end

function R.new(bank)
  local st = { bank = math.floor(clip(num(bank), 1, 10)), pattern = {}, own = {}, pos = {},
               track = R.BOOT_TRACK, level = R.BOOT_LEVEL, last = R.BOOT_LAST,
               master = 0, sync = false, snap = false, playing = false,
               num = 4, den = 4, swing = R.BOOT_SWING, drunk = 0, rate = 1,
               skip = {}, move = {}, late = {}, fate = {}, hist = {},
               rep = 0, rk = 0, win = {}, rand = math.random,
               knob = { last = { held = true }, track = { held = true },
                        swing = { held = true } } }
  for i = 1, R.TRACKS * R.STEPS do st.pattern[i] = 0 end
  for t = 1, R.TRACKS do
    st.own[t], st.pos[t], st.skip[t], st.move[t], st.late[t], st.hist[t] = 0, 0, 0, 0, 0, {}
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

-- A bar of the time signature, in steps: num x 16 / den.
function R.bar(st)
  return st.num * 16 // st.den
end

-- The bar on the page: every bar's first step is lit blue there, unless a note is.
function R.page_bar(st)
  return { "page", "bar", { R.bar(st) } }
end

-- The whole pattern, zeros included: 512 velocities, then the 16 tracks' own last steps, 0 for
-- one that follows the global last step, then their skip chances and their move chances, 0 to
-- 100, then the time signature and the drunkenness, 0 to 100. What section-1-<part> holds:
-- the phone's settings with the pattern (Brendan, 2026-11-03), and the knobs' not.
function R.save(st)
  local all, cells = {}, R.TRACKS * R.STEPS
  for i = 1, cells do all[i] = st.pattern[i] end
  for t = 1, R.TRACKS do
    all[cells + t] = st.own[t]
    all[cells + R.TRACKS + t] = st.skip[t]
    all[cells + 2 * R.TRACKS + t] = st.move[t]
  end
  local n = cells + 3 * R.TRACKS
  all[n + 1], all[n + 2], all[n + 3] = st.num, st.den, st.drunk
  return { "save", "list", all }
end

-- At load: the page's selection, before anything is pressed, and the step clock straight.
function R.boot(st)
  return { { "page", "vel", { st.level } }, { "page", "track", { st.track } }, R.page_last(st),
           R.steps(st), R.page_bar(st), { "page", "rep", { st.rep } },
           { "clock", "swing", { st.swing / 100 } }, { "clock", "rate", { st.rate } } }
end

-- A step press, on the selected track. The step rule: off takes the selected velocity; on, at
-- any velocity, turns off. A step past the track's last step is dark, and a press there does
-- nothing.
function R.press_step(st, step)
  local s = math.floor(clip(num(step), 1, R.STEPS))
  if s > R.last_of(st, st.track) then return {} end
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

-- Knob 4: swing, 25% to 75%, the share of each pair of sixteenths the first one takes, straight
-- at 50%: above it every second sixteenth comes later, below it earlier (Brendan, 2026-11-03).
-- Not saved; it starts at 50% with the knob held there, as knob 2 at 16. The step clock takes it
-- at the next pair, so a turn never moves a step already cut.
function R.knob_swing(st, v)
  local n = R.SWING_MIN + math.floor(clip(num(v), 0, 1) * (R.SWING_MAX - R.SWING_MIN) + 0.5)
  local live = latch(st.knob.swing, n, st.swing)
  if not live then return { { "disp", "swing", { st.swing, "(" .. n .. ")" } } } end
  local out = { { "disp", "swing", { n, "%" } } }
  if n ~= st.swing then
    st.swing = n
    out[#out + 1] = { "clock", "swing", { n / 100 } }
  end
  return out
end

-- Knob 2: the global last step, 1 to 32, for every track that follows it. It is not saved, and
-- starts at 16 with the knob held there.
function R.knob_last(st, v)
  local n = R.knob_step(v)
  local live = latch(st.knob.last, n, st.last)
  if not live then return { row("last-step", false, st.last, n) } end
  st.last = n
  local out = { row("last-step", true, n) }
  if st.own[st.track] == 0 then
    rearm(st.knob.track)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- Knob 3: the selected track's own last step. It is held whenever another track is selected,
-- until turned through that track's last step, and it is saved with the pattern. Released at the
-- step it already has, a track that follows the global one goes on following it.
function R.knob_track(st, v)
  local n, cur = R.knob_step(v), R.last_of(st, st.track)
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

-- The drum screen's time signature, two numbers, each stepped by its - and + (Brendan,
-- 2026-11-03): the top 1 to 32, the bottom through 1 2 4 8 16. Saved; the page lights each bar's
-- first step.
function R.time(st, which, dir)
  local d = num(dir) < 0 and -1 or 1
  if which == "num" then
    st.num = clip(st.num + d, 1, R.MAX_NUM)
  else
    local k = 3
    for i, v in ipairs(R.DENS) do if v == st.den then k = i end end
    st.den = R.DENS[clip(k + d, 1, #R.DENS)]
  end
  return { R.save(st), R.page_bar(st) }
end

-- A setting of the drum screen's sliders, 0 to 100, rounded: drunkenness for the whole pattern,
-- skip and move for the selected track. Saved.
local function percent(v)
  return math.floor(clip(num(v), 0, 100) + 0.5)
end

function R.drunk(st, v)
  st.drunk = percent(v)
  return { R.save(st) }
end

function R.chance(st, which, v)
  st[which][st.track] = percent(v)
  return { R.save(st) }
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

-- The drum screen's state, for the phone: playing (1 or 0), the global last step, the selected
-- track, a pending sync or snap (0 none, 1 sync, 2 snap), then each track's last step, then 1 for
-- each track with a last step of its own, then the time signature, the drunkenness, and the
-- selected track's skip and move chances. 41 numbers.
function R.phone(st)
  local out = { st.playing and 1 or 0, st.last, st.track, st.snap and 2 or (st.sync and 1 or 0) }
  for t = 1, R.TRACKS do out[#out + 1] = R.last_of(st, t) end
  for t = 1, R.TRACKS do out[#out + 1] = st.own[t] >= 1 and 1 or 0 end
  for _, v in ipairs({ st.num, st.den, st.drunk, st.skip[st.track], st.move[st.track] }) do
    out[#out + 1] = v
  end
  return out
end

-- A pad press plays the pad now, at the press's own velocity, and selects its track; knob 3 is
-- then held at that track's last step.
function R.press_pad(st, track, velocity)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  return { { "note", "pad", { R.pad(st, st.track), num(velocity) } },
           { "page", "track", { st.track } }, R.page_last(st), R.steps(st) }
end

-- What the next step does to the loops, without doing it: the global loop's step, every
-- track's, and whether a pending sync lands there. The global loop moves on; when it comes round
-- to its own step 1 a pending sync puts every track back before its step 1, and a pending snap
-- puts every track on the global last step; then every track moves on in its own loop.
local function advance(st)
  local m = st.master % st.last + 1
  local synced = st.sync and m == 1
  local pos = {}
  for t = 1, R.TRACKS do
    local p = synced and 0 or st.pos[t]
    local last = (synced and st.snap) and st.last or R.last_of(st, t)
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

-- A note's fate under its track's chances (Brendan, 2026-11-03): skipped, moved a step later,
-- moved a step earlier when it is rolled a step ahead, or played as written. A track with no
-- chances never rolls.
local function roll(st, t, early)
  local skip, move = st.skip[t], st.move[t]
  if skip <= 0 and move <= 0 then return "now" end
  if skip > 0 and st.rand() * 100 < skip then return "skip" end
  if move > 0 and st.rand() * 100 < move then
    if early and st.rand() < 0.5 then return "early" end
    return "late"
  end
  return "now"
end

local function note(st, out, t, v)
  out[#out + 1] = { "note", "pad", { R.pad(st, t), v } }
end

-- A step of the clock. The loops move on (advance), and every track plays the step it is heard
-- at (heard), track 1 first, all in one logical instant: a note moved late from the last step,
-- then its own note, as its fate says. Then each track's next note is rolled a step ahead, and
-- one moved early plays now. Then the playhead, the selected track's step, and the step clock's
-- rate for the step coming: drunk, now and then a step lasts up to the drunkenness longer or
-- shorter, the more often the drunker, and the error stays -- its own drift becomes the clock
-- (Brendan, 2026-11-03).
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
    if st.late[t] > 0 then
      note(st, out, t, st.late[t])
      st.late[t] = 0
    end
    local v = st.pattern[R.index(t, play[t])]
    if v >= 1 then
      local f = st.fate[t]
      local fate = (f and f.step == play[t]) and f.fate or roll(st, t, false)
      if fate == "now" then note(st, out, t, v) elseif fate == "late" then st.late[t] = v end
    end
    st.fate[t] = nil
  end
  local _, ahead = advance(st)
  for t = 1, R.TRACKS do
    if st.skip[t] > 0 or st.move[t] > 0 then
      local q = heard(st, t, ahead[t])
      local v = st.pattern[R.index(t, q)]
      if v >= 1 then
        local fate = roll(st, t, true)
        if fate == "early" then note(st, out, t, v) end
        st.fate[t] = { step = q, fate = fate }
      end
    end
  end
  out[#out + 1] = { "page", "play", { play[st.track] } }
  local rate = 1
  if st.drunk > 0 and st.rand() < R.DRUNK_CHANCE * st.drunk / 100 then
    local stray = (st.rand() * 2 - 1) * st.drunk / 100
    rate = 1 / math.max(R.MIN_DUR, 1 + stray)
  end
  if rate ~= st.rate then
    st.rate = rate
    out[#out + 1] = { "clock", "rate", { rate } }
  end
  return out
end

-- PLAY: every loop, the global one included, starts again at step 1 on the next step, which is
-- a sync already; a pending snap lands now. The step clock starts on the beat, at its own rate:
-- PLAY is the one thing that puts a drunk machine back on the clock. A held repeat lets go.
function R.start(st)
  st.master, st.sync, st.playing, st.rep = 0, false, true, 0
  for t = 1, R.TRACKS do st.pos[t], st.late[t], st.fate[t], st.hist[t] = 0, 0, nil, {} end
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

-- u_state's restore of section-1-<part>, then put straight back (ref/module/state.md), which also
-- repairs a short or malformed line. A line of exactly 256 is the 16-step pattern this replaced,
-- track by track: its steps go to each track's first sixteen. Anything else is read as this
-- file saves it, as far as it goes, a symbol as 0, the rest left as they were: a line of 528,
-- from before the phone's settings, keeps 4/4, sober, and no chances. A bottom number that is
-- not one of 1 2 4 8 16 is 4.
function R.restore(st, values)
  local cells = R.TRACKS * R.STEPS
  if #values == 256 then
    for t = 1, R.TRACKS do
      for s = 1, 16 do st.pattern[R.index(t, s)] = num(values[(t - 1) * 16 + s]) end
    end
  else
    for i = 1, math.min(#values, cells) do st.pattern[i] = num(values[i]) end
    for t = 1, R.TRACKS do
      local v, k, m = values[cells + t], values[cells + R.TRACKS + t],
                      values[cells + 2 * R.TRACKS + t]
      if v ~= nil then st.own[t] = math.floor(clip(num(v), 0, R.STEPS)) end
      if k ~= nil then st.skip[t] = percent(k) end
      if m ~= nil then st.move[t] = percent(m) end
    end
    local n = cells + 3 * R.TRACKS
    if values[n + 1] ~= nil then st.num = math.floor(clip(num(values[n + 1]), 1, R.MAX_NUM)) end
    if values[n + 2] ~= nil then
      local d = num(values[n + 2])
      st.den = 4
      for _, v in ipairs(R.DENS) do if v == d then st.den = v end end
    end
    if values[n + 3] ~= nil then st.drunk = percent(values[n + 3]) end
  end
  return { R.save(st), R.page_last(st), R.steps(st), R.page_bar(st) }
end

-- A press's velocity: 0 is a release, which only a repeat pad acts on.
local function pressed(a)
  return a[1] ~= nil and a[2] ~= 0
end

-- What arrives on the first inlet: u_map's drum-page presses and releases, <selector> <n>
-- <velocity>; its knobs, last, track-last and swing with the knob's 0-1; and the drum screen's
-- sync, snap, select, num and den (-1 or 1), and drunk, skip and move (0 to 100), through u_net.
-- A press, a knob or a setting with no number in it does nothing.
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
  skip = function(st, a) return a[1] and R.chance(st, "skip", a[1]) or {} end,
  move = function(st, a) return a[1] and R.chance(st, "move", a[1]) or {} end,
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
