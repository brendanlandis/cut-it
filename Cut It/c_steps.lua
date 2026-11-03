-- c_steps.lua -- the drum sequencer's rules: the pattern, the step rule, the velocity levels, the
-- selected track and level, and which notes fire on a step. Plain Lua with no Pd in it, so
-- test/gate/lua/c_steps_test.lua runs it on the Mac with lua.org's interpreter.
-- c_steps-lua.pd_lua is its Pd face, and c_steps.pd keeps the clock, the transport and the cords
-- to m_404, g_grid and u_state. ref/module/sequencer.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the pattern. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"note", "pad", {pad, velocity}}                    to m_404
--   {"page", "steps" | "vel" | "track", {...}}          to g_grid's third inlet
--   {"save", "list", {256 velocities}}                  to u_state, as section-1-<part>
--   {"err", "fail", {"c_steps", text}}                  to err (C-12)

local R = {}

R.TRACKS, R.STEPS, R.LEVELS = 16, 16, 16
-- At load: level 13 (103) and track 1, so the page has a selection before anything is pressed.
R.BOOT_LEVEL, R.BOOT_TRACK = 13, 1

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A number from a message, as Pd's [f] reads one: a symbol is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- Level n's velocity: 127n/16, rounded. 8 at 1, 127 at 16.
function R.velocity(level)
  return math.floor(127 * level / 16 + 0.5)
end

-- The pattern's index of a track's step, both 1-based: track 1's sixteen steps come first.
function R.index(track, step)
  return (track - 1) * R.STEPS + step
end

-- A track's pad: track n plays pad n of the bank, 1 for A (pads 1..160 across ten banks).
function R.pad(st, track)
  return (st.bank - 1) * R.TRACKS + track
end

function R.new(bank)
  local st = { bank = math.floor(clip(num(bank), 1, 10)), pattern = {},
               track = R.BOOT_TRACK, level = R.BOOT_LEVEL }
  for i = 1, R.TRACKS * R.STEPS do st.pattern[i] = 0 end
  return st
end

-- The selected track's sixteen velocities, as the page shows them.
function R.steps(st)
  local row = {}
  for s = 1, R.STEPS do row[s] = st.pattern[R.index(st.track, s)] end
  return { "page", "steps", row }
end

-- The whole pattern, 256 velocities, zeros included: what section-1-<part> holds.
function R.save(st)
  local all = {}
  for i = 1, R.TRACKS * R.STEPS do all[i] = st.pattern[i] end
  return { "save", "list", all }
end

-- At load: the page's selection, before anything is pressed.
function R.boot(st)
  return { { "page", "vel", { st.level } }, { "page", "track", { st.track } }, R.steps(st) }
end

-- A step press, on the selected track. The step rule: off takes the selected velocity; on at
-- the selected velocity turns off; on at another takes the selected one.
function R.press_step(st, step)
  local i = R.index(st.track, math.floor(clip(num(step), 1, R.STEPS)))
  local v = R.velocity(st.level)
  if st.pattern[i] == v then st.pattern[i] = 0 else st.pattern[i] = v end
  return { R.save(st), R.steps(st) }
end

-- A velocity press selects its level. It plays nothing and changes no step.
function R.press_vel(st, level)
  st.level = clip(num(level), 1, R.LEVELS)
  return { { "page", "vel", { st.level } } }
end

-- A pad press plays the pad now, at the press's own velocity, and selects its track.
function R.press_pad(st, track, velocity)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  return { { "note", "pad", { R.pad(st, st.track), num(velocity) } },
           { "page", "track", { st.track } }, R.steps(st) }
end

-- A step of the clock: every track whose velocity there is 1 or more plays its pad at that
-- velocity, track 1 first, all in one logical instant. Below 1 is a rest.
function R.fire(st, step)
  local out, s = {}, math.floor(clip(num(step), 1, R.STEPS))
  for t = 1, R.TRACKS do
    local v = st.pattern[R.index(t, s)]
    if v >= 1 then out[#out + 1] = { "note", "pad", { R.pad(st, t), v } } end
  end
  return out
end

-- u_state's restore of section-1-<part>: as many velocities as the line holds, from track 1's
-- step 1, the rest left as they were; then put straight back (ref/module/state.md), which also
-- repairs a short or malformed line.
function R.restore(st, values)
  for i = 1, math.min(#values, R.TRACKS * R.STEPS) do st.pattern[i] = num(values[i]) end
  return { R.save(st), R.steps(st) }
end

-- What arrives from u_map's drum-page destination: <selector> <n> <velocity>.
-- A press with no number in it does nothing, as before.
R.presses = {
  step = function(st, a) return a[1] and R.press_step(st, a[1]) or {} end,
  vel = function(st, a) return a[1] and R.press_vel(st, a[1]) or {} end,
  pad = function(st, a) return a[1] and R.press_pad(st, a[1], a[2]) or {} end,
}

-- What c_steps.pd itself sends: the clock's step, u_state's restore, and the load.
R.internal = {
  fire = function(st, a) return R.fire(st, a[1]) end,
  restore = function(st, a) return R.restore(st, a) end,
  init = function(st) return R.boot(st) end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_steps", string.sub(text, 1, 21) } }
end

return R
