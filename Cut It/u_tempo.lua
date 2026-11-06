-- u_tempo.lua -- what reaches u_tempo's inlet and becomes the master BPM: tap tempo, from the
-- nanoKONTROL's LOOP, by way of the map, and the phone's tempo, from the arrangement screen. Plain Lua
-- with no Pd in it, so test/gate/lua/u_tempo_test.lua runs it on the Mac with lua.org's
-- interpreter. u_tempo-lua.pd_lua is its Pd face, and u_tempo.pd keeps the timer between taps,
-- the clock and the transport. ref/module/tempo.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- a count of taps. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"tempo", "float", {bpm}}            to the tempo bus
--   {"put", "float", {1 or 0}}           whether a BPM on the bus is put in the section
--   {"err", "fail", {"u_tempo", text}}   to err (C-12)
--   {"bus", "float", {bpm}}              to the tempo bus alone: rush's, whose knob holds knob 1 itself
--   {"steps", "rush", {t}}, "rush-back" {bpm} and "rush-off" {}   to c_steps: how far past the handoff,
--                                        0 to 1; the knob back below it; and something else set the tempo
--   {"disp", "rush", {value, unit}}      rush's row, to disp
--   {"hold", "float", {bpm}}             to u_map alone: hold the knobs there, the bus staying as it is

local R = {}

-- The legal range, u_tempo.pd's own [clip 5 1000], wider than knob 1's so a tap is not limited by
-- what one knob chose (tempo.md): u_tempo_test.lua reads the box and checks the two agree.
R.MIN, R.MAX = 5, 1000
-- A tap this long after the one before starts the count over (Brendan, 2026-11-04: two seconds).
R.GAP = 2000
-- How many of the last intervals are averaged: enough to steady a hand, few enough that a tempo
-- tapped faster or slower follows within a bar.
R.KEEP = 4
-- The 500 BPM repeat's tempo (Brendan, 2026-11-05).
R.FAST = 500
-- Rush, knob 4 (Brendan, 2026-11-05): an absolute rate over its whole turn, R.RUSH_LOW * (R.RUSH_TOP /
-- R.RUSH_LOW) ^ x BPM, 10 BPM at the bottom. Below R.HANDOFF it is the tempo, the steps racing. From there c_steps freezes a loop
-- of what is being repeated, and the rest of the turn is that loop's frequency, from playback speed 1
-- up to 22 kHz, whatever its length. R.RUSH_TOP is 22 kHz as a one-step loop's BPM. Coming back it
-- hands over at R.RUSH_BACK, a little lower, so a knob resting on the handoff, whose reading jitters
-- a place or two, a place being 1%, does not capture over and over. u_map.lua has the curve's two
-- ends too.
R.HANDOFF, R.RUSH_BACK, R.RUSH_LOW, R.RUSH_TOP = 1000, 980, 10, 22000 * 15

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A BPM as the bus gets it: whole, and within the legal range.
local function bpm(x)
  return math.floor(clip(x, R.MIN, R.MAX) + 0.5)
end

-- taps: the last R.KEEP intervals, oldest first. armed: a tap has started the count. before: while
-- the 500 BPM repeat is held, the tempo it goes back to. rush: while knob 4 has the tempo, the BPM it
-- has the bus at, bpm, and whether a loop has the sound, looping.
function R.new()
  return { taps = {}, armed = false }
end

-- Something else has set the tempo, so rush is over: the loop stops, and the put opens, under the 500
-- BPM repeat when that is let go.
local function end_rush(st, out)
  local r = st.rush
  if not r then return end
  st.rush = nil
  if r.looping then out[#out + 1] = { "steps", "rush-off", {} } end
  if not st.before then out[#out + 1] = { "put", "float", { 1 } } end
end

-- A tap, <ms> since the one before, from u_tempo.pd's [timer]. The first tap after load, and any
-- tap R.GAP or more after the one before, starts the count and sets nothing; every tap after it
-- sets the tempo from the average of the last R.KEEP intervals. Two in one instant count nothing.
function R.tap(st, ms)
  if type(ms) ~= "number" or ms >= R.GAP or not st.armed then
    st.taps, st.armed = {}, true
    return {}
  end
  if ms <= 0 then return {} end
  local t = st.taps
  t[#t + 1] = ms
  if #t > R.KEEP then table.remove(t, 1) end
  local sum = 0
  for _, v in ipairs(t) do sum = sum + v end
  local out = {}
  end_rush(st, out)
  out[#out + 1] = { "tempo", "float", { bpm(60000 * #t / sum) } }
  return out
end

-- tempo <bpm>, the phone's: a BPM as it stands, whole and within the legal range. It leaves a
-- count of taps alone. Anything but a number is fail u_tempo bad-tempo.
function R.set(st, v)
  if type(v) ~= "number" then return { R.fail("bad-tempo") } end
  local out = {}
  end_rush(st, out)
  out[#out + 1] = { "tempo", "float", { bpm(v) } }
  return out
end

-- The 500 BPM repeat, pad-35, from c_steps (Brendan, 2026-11-05). fast 1 <bpm>: the tempo in force,
-- which u_tempo.pd adds, is kept and 500 goes out, as a tap's would, so knob 1 is held there until it reaches it. fast 0: the tempo
-- kept goes out the same way, so knob 1 is held there. It is a flourish and no change to the song:
-- while it is held nothing on the bus is put in the section, so the section's tempo stands as it
-- was, and what the knob or the phone set meanwhile is gone at the release. Each ends rush.
function R.fast(st, on, now)
  local out = {}
  if on ~= 0 then
    if st.before or type(now) ~= "number" then return {} end
    st.before = now
    end_rush(st, out)
    out[#out + 1] = { "put", "float", { 0 } }
    out[#out + 1] = { "tempo", "float", { R.FAST } }
    return out
  end
  if not st.before then return {} end
  local back = st.before
  end_rush(st, out)
  st.before = nil
  out[#out + 1] = { "tempo", "float", { back } }
  out[#out + 1] = { "put", "float", { 1 } }
  return out
end

-- The rate at knob position x, in BPM.
function R.rush_bpm(x)
  return R.RUSH_LOW * (R.RUSH_TOP / R.RUSH_LOW) ^ clip(x, 0, 1)
end

-- How far through the turn past the handoff position x is, 0 to 1.
function R.rush_past(x)
  local at = math.log(R.HANDOFF / R.RUSH_LOW) / math.log(R.RUSH_TOP / R.RUSH_LOW)
  return clip((x - at) / (1 - at), 0, 1)
end

local function rush_row(value, unit)
  return { "disp", "rush", { value, unit } }
end

-- The knob's own rate, for a held row's brackets: a BPM, in thousands past four figures' reach.
local function bracket(rate)
  if rate >= 10000 then return "(" .. math.floor(rate / 1000 + 0.5) .. "k)" end
  return "(" .. math.floor(rate + 0.5) .. ")"
end

-- Knob 4, rush <x> <live> <bpm>: its 0-1, whether u_map still holds it, and the BPM in force, which
-- u_tempo.pd adds. Held, as knob 1 is held, until turned to or through where the tempo in force
-- stands: its row is that tempo with the knob's own rate in brackets. Live, it has the tempo, a
-- flourish and no change to the song, so nothing is put in the section until something else sets the
-- tempo. There is no bottom to go back to: pad-38 is the way home (R.rush_home). Past the handoff the bus stays
-- at 1000, so the step clock's next step, the capture, is at most 15 ms off, and c_steps gets how far
-- past and draws the row, since only it knows the loop's frequency. x below 0: knob 1 has gone live,
-- u_map says, and its BPM comes next.
function R.rush(st, x, live, now)
  if type(x) ~= "number" then return {} end
  if x < 0 then
    local out = {}
    end_rush(st, out)
    return out
  end
  local rate = R.rush_bpm(x)
  if live == 0 then
    if type(now) ~= "number" then return {} end
    return { rush_row(now, bracket(rate)) }
  end
  local out = {}
  local r = st.rush
  if not r then
    r = { looping = false }
    st.rush = r
    out[1] = { "put", "float", { 0 } }
  end
  if rate >= (r.looping and R.RUSH_BACK or R.HANDOFF) then
    if not r.looping then
      r.looping, r.bpm = true, R.HANDOFF
      out[#out + 1] = { "bus", "float", { R.HANDOFF } }
    end
    out[#out + 1] = { "steps", "rush", { R.rush_past(x) } }
    return out
  end
  r.bpm = bpm(rate)
  out[#out + 1] = { "bus", "float", { r.bpm } }
  if r.looping then
    r.looping = false
    out[#out + 1] = { "steps", "rush-back", { r.bpm } }
  end
  out[#out + 1] = rush_row(r.bpm, "bpm")
  return out
end

-- The saved tempo's pad, from c_steps, before it asks for the tempo: rush is over that instant, even
-- if the restore that follows is of the tempo already on the bus, which u_tempo.pd drops. The knobs
-- are held where the bus is, and held again at the saved BPM when that comes.
function R.rush_home(st)
  local r = st.rush
  if not r then return {} end
  local out = {}
  end_rush(st, out)
  out[#out + 1] = { "hold", "float", { r.bpm } }
  return out
end

-- A section's restore of its tempo, or the saved tempo asked for, restored <bpm>: as the phone's
-- tempo does, so it ends rush, but under the 500 BPM repeat, the tempo it goes back to.
function R.restored(st, v)
  if type(v) == "number" and st.before then
    local out = {}
    local rushed = st.rush
    end_rush(st, out)
    st.before = bpm(v)
    if rushed then out[#out + 1] = { "tempo", "float", { R.FAST } } end
    return out
  end
  return R.set(st, v)
end

-- What reaches the inlet: tap <ms>, the interval u_tempo.pd's timer measured, tempo <bpm> from
-- u_net, restored <bpm> off the state bus, fast <1 or 0> <bpm> and rush-home from c_steps, the first
-- by u_tempo.pd, and rush <x> <live> <bpm> from u_map, by u_tempo.pd.
R.inputs = {
  tap = function(st, a) return R.tap(st, a[1]) end,
  tempo = function(st, a) return R.set(st, a[1]) end,
  restored = function(st, a) return R.restored(st, a[1]) end,
  fast = function(st, a) return R.fast(st, a[1], a[2]) end,
  rush = function(st, a) return R.rush(st, a[1], a[2], a[3]) end,
  ["rush-home"] = function(st) return R.rush_home(st) end,
}

-- What u_tempo.pd itself sends: the load, answered with the proof bang alone.
R.internal = {
  init = function() return {} end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "u_tempo", string.sub(text, 1, 21) } }
end

return R
