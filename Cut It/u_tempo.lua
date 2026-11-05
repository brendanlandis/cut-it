-- u_tempo.lua -- what reaches u_tempo's inlet and becomes the master BPM: tap tempo, from the
-- Launchpad's tap pad on page 1, and the phone's tempo, from the arrangement screen. Plain Lua
-- with no Pd in it, so test/gate/lua/u_tempo_test.lua runs it on the Mac with lua.org's
-- interpreter. u_tempo-lua.pd_lua is its Pd face, and u_tempo.pd keeps the timer between taps,
-- the clock and the transport. ref/module/tempo.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- a count of taps. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"tempo", "float", {bpm}}            to the tempo bus
--   {"put", "float", {1 or 0}}           whether a BPM on the bus is put in the section
--   {"err", "fail", {"u_tempo", text}}   to err (C-12)
--   {"bus", "float", {bpm}}              to the tempo bus alone, so knob 1 is not held there: rush's
--   {"steps", "rush", {bpm}}             to c_steps: the rate past the handoff, 0 below it
--   {"disp", "rush", {value, unit}}      rush's row, to disp

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
-- Rush, knob 4 (Brendan, 2026-11-05): "keep feeling faster and faster". One curve over the whole
-- turn, base * (R.RUSH_TOP / base) ^ x, base the tempo in force when the knob left its bottom. Below
-- R.HANDOFF it is the tempo, the steps racing. From there c_steps freezes a loop of what was just
-- playing and the curve is its rate, up to R.RUSH_TOP, 22 kHz as a one-step loop's BPM. Coming back
-- it hands over at R.RUSH_BACK, a little lower, so a knob resting on the handoff, whose reading
-- jitters a place or two, a place being 0.8%, does not capture over and over.
R.HANDOFF, R.RUSH_BACK, R.RUSH_TOP = 1000, 980, 22000 * 15
-- The knob's bottom, a hair wide, u_map.lua's R.RUSH_BOTTOM: the curve starts from it.
R.RUSH_BOTTOM = 0.01

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
-- the 500 BPM repeat is held, the tempo it goes back to. rush: while knob 4 is off its bottom, the
-- tempo its curve starts from and goes back to, base, and whether a loop has the sound, looping.
function R.new()
  return { taps = {}, armed = false }
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
  return { { "tempo", "float", { bpm(60000 * #t / sum) } } }
end

-- tempo <bpm>, the phone's: a BPM as it stands, whole and within the legal range. It leaves a
-- count of taps alone. Anything but a number is fail u_tempo bad-tempo.
function R.set(st, v)
  if type(v) ~= "number" then return { R.fail("bad-tempo") } end
  return { { "tempo", "float", { bpm(v) } } }
end

-- The 500 BPM repeat, pad-35, from c_steps (Brendan, 2026-11-05). fast 1 <bpm>: the tempo in force,
-- which u_tempo.pd adds, is kept and 500 goes out, as a tap's would, so knob 1 is held there until it reaches it. fast 0: the tempo
-- kept goes out the same way, so knob 1 is held there. It is a flourish and no change to the song:
-- while it is held nothing on the bus is put in the section, so the section's tempo stands as it
-- was, and what the knob or the phone set meanwhile is gone at the release.
function R.fast(st, on, now)
  if on ~= 0 then
    if st.before or type(now) ~= "number" then return {} end
    local rush = st.rush
    st.before = rush and rush.base or now
    if rush then rush.base = R.FAST end
    return { { "put", "float", { 0 } }, { "tempo", "float", { R.FAST } } }
  end
  if not st.before then return {} end
  local back = st.before
  st.before = nil
  if st.rush then
    st.rush.base = back
    return { { "tempo", "float", { back } } }
  end
  return { { "tempo", "float", { back } }, { "put", "float", { 1 } } }
end

-- The rate the curve gives at knob position x, in BPM, from base.
function R.rush_bpm(base, x)
  local t = clip((x - R.RUSH_BOTTOM) / (1 - R.RUSH_BOTTOM), 0, 1)
  return base * (R.RUSH_TOP / base) ^ t
end

local function rush_row(value, unit)
  return { "disp", "rush", { value, unit } }
end

-- Knob 4, rush <x> <live> <bpm>: its 0-1, whether u_map still holds it, and the BPM in force, which
-- u_tempo.pd adds. It sets the tempo as the 500 BPM repeat does, a flourish and no change to the
-- song, so nothing is put in the section, but on a tempo bus of its own, so knob 1 is not held and
-- the lamps stay as they are. Back at the bottom the tempo is what it was; a section's restore or
-- pad-35 meanwhile moves what that is (R.restored, R.fast). What knob 1, a tap or the phone set
-- meanwhile is gone at its next move, as under pad-35. Past the handoff the bus stays at 1000, so the
-- step clock's next step, the capture, is at most 15 ms off, and c_steps gets the rate and draws the
-- row, since it knows the loop's length.
function R.rush(st, x, live, now)
  if type(x) ~= "number" or type(now) ~= "number" then return {} end
  if live == 0 then
    return { rush_row(0, "(" .. math.floor(x * 100 + 0.5) .. ")") }
  end
  local r = st.rush
  if x <= R.RUSH_BOTTOM then
    if not r then return { rush_row(now, "bpm") } end
    st.rush = nil
    local out = { { "bus", "float", { r.base } } }
    if r.looping then out[#out + 1] = { "steps", "rush", { 0 } } end
    out[#out + 1] = rush_row(r.base, "bpm")
    if not st.before then out[#out + 1] = { "put", "float", { 1 } } end
    return out
  end
  local out = {}
  if not r then
    r = { base = now, looping = false }
    st.rush = r
    out[1] = { "put", "float", { 0 } }
  end
  local rate = R.rush_bpm(r.base, x)
  if r.looping and rate >= R.RUSH_BACK or not r.looping and rate >= R.HANDOFF then
    if not r.looping then
      r.looping = true
      out[#out + 1] = { "bus", "float", { R.HANDOFF } }
    end
    out[#out + 1] = { "steps", "rush", { rate } }
    return out
  end
  out[#out + 1] = { "bus", "float", { bpm(rate) } }
  if r.looping then
    r.looping = false
    out[#out + 1] = { "steps", "rush", { 0 } }
  end
  out[#out + 1] = rush_row(bpm(rate), "bpm")
  return out
end

-- A section's restore of its tempo, or the saved tempo asked for, restored <bpm>: as the phone's
-- tempo does, but under the 500 BPM repeat, the tempo it goes back to, and under rush alone, the one
-- its curve starts from.
function R.restored(st, v)
  if type(v) == "number" and (st.before or st.rush) then
    if st.before then st.before = bpm(v) else st.rush.base = bpm(v) end
    return {}
  end
  return R.set(st, v)
end

-- What reaches the inlet: tap <ms>, the interval u_tempo.pd's timer measured, tempo <bpm> from
-- u_net, restored <bpm> off the state bus, fast <1 or 0> <bpm> from c_steps, by u_tempo.pd, and rush
-- <x> <live> <bpm> from u_map, by u_tempo.pd.
R.inputs = {
  tap = function(st, a) return R.tap(st, a[1]) end,
  tempo = function(st, a) return R.set(st, a[1]) end,
  restored = function(st, a) return R.restored(st, a[1]) end,
  fast = function(st, a) return R.fast(st, a[1], a[2]) end,
  rush = function(st, a) return R.rush(st, a[1], a[2], a[3]) end,
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
