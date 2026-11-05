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

local R = {}

-- The legal range, u_tempo.pd's own [clip 5 600], wider than knob 1's so a tap is not limited by
-- what one knob chose (tempo.md): u_tempo_test.lua reads the box and checks the two agree.
R.MIN, R.MAX = 5, 600
-- A tap this long after the one before starts the count over (Brendan, 2026-11-04: two seconds).
R.GAP = 2000
-- How many of the last intervals are averaged: enough to steady a hand, few enough that a tempo
-- tapped faster or slower follows within a bar.
R.KEEP = 4
-- The 500 BPM repeat's tempo (Brendan, 2026-11-05).
R.FAST = 500

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A BPM as the bus gets it: whole, and within the legal range.
local function bpm(x)
  return math.floor(clip(x, R.MIN, R.MAX) + 0.5)
end

-- taps: the last R.KEEP intervals, oldest first. armed: a tap has started the count. bpm: the master
-- BPM in force, as the bus carried it, u_tempo.pd's fallback until it says. before: while the 500
-- BPM repeat is held, the tempo it goes back to.
function R.new()
  return { taps = {}, armed = false, bpm = 120 }
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

-- The 500 BPM repeat, pad-35, from c_steps (Brendan, 2026-11-05). fast 1: the tempo in force is kept
-- and 500 goes out, as a tap's would, so knob 1 is held there until it reaches it. fast 0: the tempo
-- kept goes out the same way, so knob 1 is held there. It is a flourish and no change to the song:
-- while it is held nothing on the bus is put in the section, so the section's tempo stands as it
-- was, and what the knob or the phone set meanwhile is gone at the release.
function R.fast(st, on)
  if on ~= 0 then
    if st.before then return {} end
    st.before = st.bpm
    return { { "put", "float", { 0 } }, { "tempo", "float", { R.FAST } } }
  end
  if not st.before then return {} end
  local back = st.before
  st.before = nil
  return { { "tempo", "float", { back } }, { "put", "float", { 1 } } }
end

-- A section's restore of its tempo, or the saved tempo asked for, restored <bpm>: as the phone's
-- tempo does, but under the 500 BPM repeat, the tempo it goes back to.
function R.restored(st, v)
  if st.before and type(v) == "number" then
    st.before = bpm(v)
    return {}
  end
  return R.set(st, v)
end

-- What reaches the inlet: tap <ms>, the interval u_tempo.pd's timer measured, tempo <bpm> from
-- u_net, restored <bpm> off the state bus, and fast <1 or 0> from c_steps.
R.inputs = {
  tap = function(st, a) return R.tap(st, a[1]) end,
  tempo = function(st, a) return R.set(st, a[1]) end,
  restored = function(st, a) return R.restored(st, a[1]) end,
  fast = function(st, a) return R.fast(st, a[1]) end,
}

-- What u_tempo.pd itself sends: the load, answered with the proof bang alone, and bpm <bpm>, every
-- BPM the bus carries, clamped.
R.internal = {
  init = function() return {} end,
  bpm = function(st, a)
    if type(a[1]) == "number" then st.bpm = a[1] end
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "u_tempo", string.sub(text, 1, 21) } }
end

return R
