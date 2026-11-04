-- flourish.lua -- the Flourish Probe's rules: two ways to make one 404 pad stutter slower and
-- slower while its pitch falls, both played on the 404 itself. Plain Lua with no Pd in it;
-- flourish-lua.pd_lua carries it into Pd. main.pd says which key and knob does what.
--
-- Method A, retrigger: Pd fires the pad again and again, the gap between hits widening from a
-- first gap to a last one over the run. In the chromatic variant every hit goes to chromatic
-- mode's channel 16, a semitone lower as the run goes on (48 down to 36); in the plain one,
-- to the pad's own note, so the stutter can be heard without the pitch.
--
-- Method B, looper: Pd fires the pad once, switches DJFX Looper's LOOP SW on, and lowers its
-- SPEED over the run, so the loop repeats slower and lower together; then it switches the loop
-- off and puts SPEED back. Assumes the 404's v3.00 MIDI chart: CC 16-18 are CTRL 1-3 on the
-- channel of the bus (1 = BUS 1), and the looper's CTRL 2 is SPEED and CTRL 3 is LOOP SW.
--
-- Every rule returns a plan: events in time order, each {t, kind, ...}, t in ms from now.
--   {t, "note", note, velocity, channel}   to noteout, channel as Pd numbers it (33 = 404 ch 1)
--   {t, "cc", value, number, channel}      to ctlout
--   {t, "line", n, text}                   to screenLine<n>, at most 21 characters
-- A new plan replaces whatever is still running.

local R = {}

-- Pad n's note in every bank (the SP-404's Reference page, The pad note map).
R.NOTE = { 48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39 }
R.PAD = {}
for pad, note in ipairs(R.NOTE) do R.PAD[note] = pad end
R.BANKS = "ABCDEFGHIJ"

-- The keys, by mother's pitch: the lowest key is 60, and only white keys are used.
R.KEYS = { [60] = "chrom", [62] = "plain", [64] = "loop", [65] = "late", [67] = "once",
           [69] = "stop" }

local function num(x) return type(x) == "number" and x or 0 end

function R.new()
  return {
    base = 33,          -- Pd's channel for the 404's channel 1 (port 3 on the device)
    bank = 0, pad = 11, -- A11, the pad Brendan compares the methods on
    vel = 100,
    dur = 3500,         -- ms, knob 1
    gap0 = 30,          -- ms, knob 2
    gap1 = 400,         -- ms, knob 3
    speed_end = 20,     -- percent of normal, knob 4
    chrom_chan = 16, chrom_top = 48, chrom_drop = 12,
    bus = 1, cc_speed = 17, cc_loop = 18,
    late = 230,         -- ms: DJFX Looper's longest LENGTH
    step = 20,          -- ms between SPEED changes
    looped = false,     -- once the looper has run, every plan starts by resetting it
  }
end

function R.pad_name(st)
  return "pad " .. R.BANKS:sub(st.bank + 1, st.bank + 1) .. st.pad
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
    { 0, "line", 2, R.pad_name(st) },
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

local function reset(st, plan)
  local ch = st.base + st.bus - 1
  plan[#plan + 1] = { 0, "cc", 0, st.cc_loop, ch }
  plan[#plan + 1] = { 0, "cc", 127, st.cc_speed, ch }
end

local function start(st)
  local plan = {}
  if st.looped then reset(st, plan) end
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
  local ch, prev
  if chrom then ch = st.base + st.chrom_chan - 1 else ch = st.base + st.bank end
  for _, t in ipairs(hits) do
    local note
    if chrom then
      note = st.chrom_top - math.floor(st.chrom_drop * t / st.dur + 0.5)
    else
      note = R.NOTE[st.pad]
    end
    -- A note-off first, so a chromatic mode set to LEGATO retriggers instead of gliding. The
    -- 404's chart says it ignores note-off, which costs nothing then.
    if prev then plan[#plan + 1] = { t, "note", prev, 0, ch } end
    plan[#plan + 1] = { t, "note", note, st.vel, ch }
    prev = note
  end
  local last = hits[#hits]
  plan[#plan + 1] = { last + st.gap1, "note", prev, 0, ch }
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
  local plan, ch = {}, st.base + st.bus - 1
  reset(st, plan)
  plan[#plan + 1] = { 0, "note", R.NOTE[st.pad], st.vel, st.base + st.bank }
  plan[#plan + 1] = { 0, "line", 5, "B loop on @" .. on .. "ms" }
  plan[#plan + 1] = { on, "cc", 127, st.cc_loop, ch }
  local last = -1
  local t = 0
  while t < st.dur do
    local pct = 100 * (st.speed_end / 100) ^ (t / st.dur)
    local v = R.speed_cc(pct)
    if v ~= last then
      plan[#plan + 1] = { on + t, "cc", v, st.cc_speed, ch }
      last = v
    end
    t = t + st.step
  end
  local v = R.speed_cc(st.speed_end)
  if v ~= last then plan[#plan + 1] = { on + st.dur, "cc", v, st.cc_speed, ch } end
  plan[#plan + 1] = { on + st.dur, "cc", 0, st.cc_loop, ch }
  plan[#plan + 1] = { on + st.dur, "cc", 127, st.cc_speed, ch }
  plan[#plan + 1] = { on + st.dur, "line", 5, "done" }
  return plan
end

-- A key: <pitch> <velocity>. A release, or a key with no job, plans nothing (nil).
function R.key(st, pitch, vel)
  if num(vel) <= 0 then return nil end
  local job = R.KEYS[num(pitch)]
  if job == "chrom" then return retrigger(st, true)
  elseif job == "plain" then return retrigger(st, false)
  elseif job == "loop" then return looper(st, 10)
  elseif job == "late" then return looper(st, st.late)
  elseif job == "once" then
    local plan = start(st)
    plan[#plan + 1] = { 0, "note", R.NOTE[st.pad], st.vel, st.base + st.bank }
    plan[#plan + 1] = { 0, "line", 5, "once " .. R.pad_name(st) }
    return plan
  elseif job == "stop" then
    local plan = {}
    reset(st, plan)
    plan[#plan + 1] = { 0, "line", 5, "stopped" }
    return plan
  end
  return nil
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

-- A pad struck on the 404: <note> <velocity> <Pd channel>. Selects it; a release, a note off
-- the pad map or a channel past bank J selects nothing.
function R.pad(st, note, vel, chan)
  local pad, bank = R.PAD[num(note)], num(chan) - st.base
  if num(vel) <= 0 or not pad or bank < 0 or bank > 9 then return {} end
  st.bank, st.pad = bank, pad
  return { { 0, "line", 2, R.pad_name(st) } }
end

-- Patch closing: put the looper back if it ran, so the 404 is not left looping.
function R.quit(st)
  if not st.looped then return {} end
  local plan = {}
  reset(st, plan)
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
