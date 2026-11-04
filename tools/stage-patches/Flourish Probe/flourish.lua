-- flourish.lua -- the Flourish Probe's rules: two ways to make pad A11 stutter slower and slower
-- while its pitch falls, both played on the 404 itself, with nothing to set up on the 404 by
-- hand (Brendan, 2026-11-04). Plain Lua with no Pd in it; flourish-lua.pd_lua carries it into
-- Pd. main.pd says which key and knob does what.
--
-- Method A, retrigger: Pd fires A11 again and again, the gap between hits widening from a first
-- gap to a last one over the run. In the chromatic variant every hit goes to chromatic mode's
-- channel 16, a semitone lower as the run goes on (48 down to 36). That plays chromatic mode's
-- own sample, which only the 404's front panel sets: a pad fired over MIDI does not change it
-- (Brendan heard A1 after A11, 2026-11-04). In the plain one every hit is A11, so the stutter can
-- be heard without the pitch.
--
-- Method B, looper: Pd loads DJFX Looper on BUS 1 and switches it on, fires A11 once, switches
-- LOOP SW on and lowers SPEED over the run, so the loop repeats slower and lower together; then
-- it puts SPEED back and switches the loop and the effect off. On channel 1: CC 83 = 5 picks
-- BUS 1's Direct FX5, the DJFX Looper button; CC 19 switches the effect; CC 18 is LOOP SW and
-- CC 17 SPEED (recorded looping, its pitch falling, 2026-11-04). The same messages on channel 3,
-- BUS 3, did nothing. That CC 16 is LENGTH, and how its value maps to milliseconds, are guesses.
--
-- Every rule returns a plan: events in time order, each {t, kind, ...}, t in ms from now.
--   {t, "note", note, velocity, channel}   to noteout, channel as Pd numbers it (33 = 404 ch 1)
--   {t, "cc", value, number, channel}      to ctlout
--   {t, "line", n, text}                   to screenLine<n>, at most 21 characters
--   {t, "rec", selector, atoms}            to writesf~, which records the Organelle's input
-- A new plan replaces whatever is still running.

local R = {}

-- The keys, by mother's pitch: the lowest key is 60, and only white keys are used.
R.KEYS = { [60] = "chrom", [62] = "plain", [64] = "loop", [65] = "late", [67] = "once",
           [69] = "stop" }

local function num(x) return type(x) == "number" and x or 0 end

function R.new()
  return {
    base = 33,          -- Pd's channel for the 404's channel 1 (port 3 on the device)
    note = 42,          -- pad 11's note (the SP-404's Reference page, The pad note map)
    vel = 100,
    dur = 3500,         -- ms, knob 1
    gap0 = 30,          -- ms, knob 2: A's first gap, and B's loop LENGTH
    gap1 = 400,         -- ms, knob 3
    speed_end = 20,     -- percent of normal, knob 4
    chrom_chan = 16, chrom_top = 48, chrom_drop = 12,
    bus = 1, fx = 5,    -- BUS 1's channel, and its Direct FX5, the DJFX Looper button
    cc_fx = 83, cc_fx_sw = 19,
    cc_len = 16, cc_speed = 17, cc_loop = 18,
    settle = 50,        -- ms between loading the effect and the hit
    late = 230,         -- ms: DJFX Looper's longest LENGTH
    step = 20,          -- ms between SPEED changes
    looped = false,     -- once the looper has run, every plan starts by resetting it
    rec_dir = "/tmp",   -- each run is recorded to <rec_dir>/flourish-<job>.wav
    rec_tail = 700,     -- ms recorded past a run's last event
  }
end

local function fmt_dur(ms) return string.format("%.1fs", ms / 1000) end

function R.line3(st)
  return fmt_dur(st.dur) .. " gap " .. st.gap0 .. ">" .. st.gap1 .. "ms"
end

function R.line4(st)
  return "loop end speed " .. st.speed_end .. "%"
end

-- The whole screen, at load.
function R.init(st)
  return {
    { 0, "line", 1, "FLOURISH PROBE" },
    { 0, "line", 2, "pad A11" },
    { 0, "line", 3, R.line3(st) },
    { 0, "line", 4, R.line4(st) },
    { 0, "line", 5, "ready" },
  }
end

-- SPEED, as a CC value: -100..100 spread over 0..127, so 100% is 127 and 0% about 64.
function R.speed_cc(pct)
  local v = math.floor(63.5 + pct / 100 * 63.5 + 0.5)
  if v > 127 then v = 127 elseif v < 0 then v = 0 end
  return v
end

-- LENGTH, as a CC value: the manual lists it from 230 ms down to 12 ms, guessed here to run
-- straight across 0..127 in that order.
function R.length_cc(ms)
  local v = math.floor((230 - ms) / (230 - 12) * 127 + 0.5)
  if v > 127 then v = 127 elseif v < 0 then v = 0 end
  return v
end

local function chan(st) return st.base + st.bus - 1 end

-- The loop and the effect off, SPEED back to normal.
local function reset(st, plan, t)
  plan[#plan + 1] = { t, "cc", 0, st.cc_loop, chan(st) }
  plan[#plan + 1] = { t, "cc", 127, st.cc_speed, chan(st) }
  plan[#plan + 1] = { t, "cc", 0, st.cc_fx_sw, chan(st) }
end

local function start(st)
  local plan = {}
  if st.looped then reset(st, plan, 0) end
  return plan
end

-- The hit times of a retrigger run: the gap grows exponentially from gap0 to gap1 over dur.
function R.hits(st)
  local t, out = 0, {}
  local g0, g1 = math.max(1, st.gap0), math.max(1, st.gap1)
  while t <= st.dur do
    out[#out + 1] = t
    t = t + g0 * (g1 / g0) ^ (t / st.dur)
  end
  return out
end

local function retrigger(st, chrom)
  local plan = start(st)
  local hits = R.hits(st)
  local pad_ch, chrom_ch = st.base, st.base + st.chrom_chan - 1
  local prev, prev_ch
  for _, t in ipairs(hits) do
    local note, ch = st.note, pad_ch
    if chrom then
      note = st.chrom_top - math.floor(st.chrom_drop * t / st.dur + 0.5)
      ch = chrom_ch
    end
    -- A note-off first, so a chromatic mode set to LEGATO retriggers instead of gliding. The
    -- 404's chart says it ignores note-off, which costs nothing then.
    if prev then plan[#plan + 1] = { t, "note", prev, 0, prev_ch } end
    plan[#plan + 1] = { t, "note", note, st.vel, ch }
    prev, prev_ch = note, ch
  end
  local last = hits[#hits]
  plan[#plan + 1] = { last + st.gap1, "note", prev, 0, prev_ch }
  local label
  if chrom then
    label = "A chrom " .. #hits .. " hits"
  else
    label = "A plain " .. #hits .. " hits"
  end
  plan[#plan + 1] = { 0, "line", 5, label }
  plan[#plan + 1] = { last + st.gap1, "line", 5, "done" }
  return plan
end

local function looper(st, on)
  st.looped = true
  local plan, ch, hit = {}, chan(st), st.settle
  plan[#plan + 1] = { 0, "cc", 0, st.cc_loop, ch }
  plan[#plan + 1] = { 0, "cc", st.fx, st.cc_fx, ch }
  plan[#plan + 1] = { 0, "cc", 127, st.cc_fx_sw, ch }
  plan[#plan + 1] = { 0, "cc", R.length_cc(st.gap0), st.cc_len, ch }
  plan[#plan + 1] = { 0, "cc", 127, st.cc_speed, ch }
  plan[#plan + 1] = { 0, "line", 5, "B loop on @" .. on .. "ms" }
  plan[#plan + 1] = { hit, "note", st.note, st.vel, st.base }
  plan[#plan + 1] = { hit + on, "cc", 127, st.cc_loop, ch }
  local last, t = 127, 0
  while t < st.dur do
    local v = R.speed_cc(100 * (st.speed_end / 100) ^ (t / st.dur))
    if v ~= last then
      plan[#plan + 1] = { hit + on + t, "cc", v, st.cc_speed, ch }
      last = v
    end
    t = t + st.step
  end
  local v = R.speed_cc(st.speed_end)
  if v ~= last then plan[#plan + 1] = { hit + on + st.dur, "cc", v, st.cc_speed, ch } end
  reset(st, plan, hit + on + st.dur)
  plan[#plan + 1] = { hit + on + st.dur, "line", 5, "done" }
  return plan
end

local function plan_for(st, job)
  if job == "chrom" then return retrigger(st, true)
  elseif job == "plain" then return retrigger(st, false)
  elseif job == "loop" then return looper(st, 10)
  elseif job == "late" then return looper(st, st.late)
  elseif job == "once" then
    local plan = start(st)
    plan[#plan + 1] = { 0, "note", st.note, st.vel, st.base }
    plan[#plan + 1] = { 0, "line", 5, "once A11" }
    return plan
  elseif job == "stop" then
    local plan = {}
    reset(st, plan, 0)
    plan[#plan + 1] = { 0, "line", 5, "stopped" }
    return plan
  end
  return nil
end

-- A key: <pitch> <velocity>. A release, or a key with no job, plans nothing (nil). Every run
-- but stop is recorded from the Organelle's input, the 404 as it reaches the Organelle, so a
-- run can be heard back off the device: the Mac's own recording of the rig is not available to
-- Claude's tools (2026-11-04).
function R.key(st, pitch, vel)
  if num(vel) <= 0 then return nil end
  local job = R.KEYS[num(pitch)]
  local plan = plan_for(st, job)
  if not plan or job == "stop" then return plan end
  local last = 0
  for _, e in ipairs(plan) do if e[1] > last then last = e[1] end end
  local rec = {
    { 0, "rec", "open", { "-bytes", 2, st.rec_dir .. "/flourish-" .. job .. ".wav" } },
    { 0, "rec", "start", {} },
  }
  for _, e in ipairs(plan) do rec[#rec + 1] = e end
  rec[#rec + 1] = { last + st.rec_tail, "rec", "stop", {} }
  return rec
end

-- A knob: <n> <position 0..1>. Changes the next run, never the one in flight; plans only the
-- line it redraws, so it is an "add" rather than a replacement (see the face).
function R.knob(st, n, v)
  n, v = num(n), num(v)
  if v < 0 then v = 0 elseif v > 1 then v = 1 end
  if n == 1 then
    st.dur = math.floor(1000 + 5000 * v + 0.5)
    return { { 0, "line", 3, R.line3(st) } }
  elseif n == 2 then
    st.gap0 = math.floor(10 * 15 ^ v + 0.5)
    return { { 0, "line", 3, R.line3(st) } }
  elseif n == 3 then
    st.gap1 = math.floor(80 * 10 ^ v + 0.5)
    return { { 0, "line", 3, R.line3(st) } }
  elseif n == 4 then
    st.speed_end = math.floor(5 + 95 * v + 0.5)
    return { { 0, "line", 4, R.line4(st) } }
  end
  return {}
end

-- Patch closing: put the looper back if it ran, so the 404 is not left looping.
function R.quit(st)
  if not st.looped then return {} end
  local plan = {}
  reset(st, plan, 0)
  return plan
end

-- In time order, keeping each time's events in the order they were planned.
function R.sort(plan)
  for i, e in ipairs(plan) do e.i = i end
  table.sort(plan, function(a, b)
    if a[1] ~= b[1] then return a[1] < b[1] end
    return a.i < b.i
  end)
  return plan
end

return R
