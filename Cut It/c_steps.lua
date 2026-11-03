-- c_steps.lua -- the drum sequencer's rules: the pattern, the step rule, the velocity levels, the
-- selected track and level, the last steps, each track's place in its loop, and which notes fire
-- on a step. Plain Lua with no Pd in it, so test/gate/lua/c_steps_test.lua runs it on the Mac with
-- lua.org's interpreter. c_steps-lua.pd_lua is its Pd face, and c_steps.pd keeps the clock, the
-- transport and the cords to m_404, g_grid and u_state. ref/module/sequencer.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the pattern. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"note", "pad", {pad, velocity}}                          to m_404
--   {"page", "steps" | "play" | "vel" | "track" | "last", {...}}  to g_grid's third inlet
--   {"save", "list", {512 velocities, 16 last steps}}         to u_state, as section-1-<part>
--   {"err", "fail", {"c_steps", text}}                        to err (C-12)
--   {"disp", <row name>, {value[, unit]}}                     a knob's row, to disp

local R = {}

R.TRACKS, R.STEPS, R.LEVELS = 16, 32, 8
-- At load: level 6 (95), track 1, and a last step of 16 that both knobs are held at until they
-- are turned through it (Brendan, 2026-11-03), so nothing jumps to where a knob happens to sit.
R.BOOT_LEVEL, R.BOOT_TRACK, R.BOOT_LAST = 6, 1, 16

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
               master = 0, sync = false, snap = false,
               knob = { last = { held = true }, track = { held = true } } }
  for i = 1, R.TRACKS * R.STEPS do st.pattern[i] = 0 end
  for t = 1, R.TRACKS do st.own[t], st.pos[t] = 0, 0 end
  return st
end

-- The selected track's 32 velocities, as the page shows them.
function R.steps(st)
  local row = {}
  for s = 1, R.STEPS do row[s] = st.pattern[R.index(st.track, s)] end
  return { "page", "steps", row }
end

-- The selected track's last step, as the page shows it.
function R.page_last(st)
  return { "page", "last", { R.last_of(st, st.track) } }
end

-- The whole pattern, zeros included: 512 velocities, then the 16 tracks' own last steps, 0 for
-- one that follows the global last step. What section-1-<part> holds.
function R.save(st)
  local all = {}
  for i = 1, R.TRACKS * R.STEPS do all[i] = st.pattern[i] end
  for t = 1, R.TRACKS do all[R.TRACKS * R.STEPS + t] = st.own[t] end
  return { "save", "list", all }
end

-- At load: the page's selection, before anything is pressed.
function R.boot(st)
  return { { "page", "vel", { st.level } }, { "page", "track", { st.track } }, R.page_last(st),
           R.steps(st) }
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

-- A pad press plays the pad now, at the press's own velocity, and selects its track; knob 3 is
-- then held at that track's last step.
function R.press_pad(st, track, velocity)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  return { { "note", "pad", { R.pad(st, st.track), num(velocity) } },
           { "page", "track", { st.track } }, R.page_last(st), R.steps(st) }
end

-- A step of the clock. The global loop moves on, and when it comes round to its own step 1 a
-- pending sync puts every track back before its step 1, and a pending snap puts every track on the
-- global last step. Then every track moves on in its own loop, and each whose velocity there is 1
-- or more plays its pad at it, track 1 first, all in one logical instant. Then the playhead: the
-- selected track's step.
function R.tick(st)
  st.master = st.master % st.last + 1
  local out = {}
  if st.sync and st.master == 1 then
    for t = 1, R.TRACKS do st.pos[t] = 0 end
    st.sync = false
    if st.snap then out = land_snap(st) end
  end
  for t = 1, R.TRACKS do
    st.pos[t] = st.pos[t] % R.last_of(st, t) + 1
    local v = st.pattern[R.index(t, st.pos[t])]
    if v >= 1 then out[#out + 1] = { "note", "pad", { R.pad(st, t), v } } end
  end
  out[#out + 1] = { "page", "play", { st.pos[st.track] } }
  return out
end

-- PLAY: every loop, the global one included, starts again at step 1 on the next step, which is
-- a sync already; a pending snap lands now.
function R.start(st)
  st.master, st.sync = 0, false
  for t = 1, R.TRACKS do st.pos[t] = 0 end
  if st.snap then return land_snap(st) end
  return {}
end

-- STOP and panic: the playhead goes out.
function R.stop(st)
  return { { "page", "play", { 0 } } }
end

-- u_state's restore of section-1-<part>, then put straight back (ref/module/state.md), which also
-- repairs a short or malformed line. A line of exactly 256 is the 16-step pattern this replaced,
-- track by track: its steps go to each track's first sixteen. Anything else is read as this
-- file saves it, as far as it goes, a symbol as 0, the rest left as they were.
function R.restore(st, values)
  local cells = R.TRACKS * R.STEPS
  if #values == 256 then
    for t = 1, R.TRACKS do
      for s = 1, 16 do st.pattern[R.index(t, s)] = num(values[(t - 1) * 16 + s]) end
    end
  else
    for i = 1, math.min(#values, cells) do st.pattern[i] = num(values[i]) end
    for t = 1, R.TRACKS do
      local v = values[cells + t]
      if v ~= nil then st.own[t] = math.floor(clip(num(v), 0, R.STEPS)) end
    end
  end
  return { R.save(st), R.page_last(st), R.steps(st) }
end

-- What arrives on the first inlet: u_map's drum-page presses, <selector> <n> <velocity>; its
-- knobs, last and track-last with the knob's 0-1; and the drum screen's sync and snap, through
-- u_net. A press or a knob with no number in it does nothing.
R.presses = {
  step = function(st, a) return a[1] and R.press_step(st, a[1]) or {} end,
  vel = function(st, a) return a[1] and R.press_vel(st, a[1]) or {} end,
  pad = function(st, a) return a[1] and R.press_pad(st, a[1], a[2]) or {} end,
  last = function(st, a) return a[1] and R.knob_last(st, a[1]) or {} end,
  ["track-last"] = function(st, a) return a[1] and R.knob_track(st, a[1]) or {} end,
  sync = function(st) return R.sync(st) end,
  snap = function(st) return R.snap(st) end,
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
