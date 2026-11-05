-- u_tempo.lua -- what reaches u_tempo's inlet and becomes the master BPM: tap tempo, from the
-- Launchpad's tap pad on page 1, and the phone's tempo, from the arrangement screen. Plain Lua
-- with no Pd in it, so test/gate/lua/u_tempo_test.lua runs it on the Mac with lua.org's
-- interpreter. u_tempo-lua.pd_lua is its Pd face, and u_tempo.pd keeps the timer between taps,
-- the clock and the transport. ref/module/tempo.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- a count of taps. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"tempo", "float", {bpm}}            to the tempo bus
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

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A BPM as the bus gets it: whole, and within the legal range.
local function bpm(x)
  return math.floor(clip(x, R.MIN, R.MAX) + 0.5)
end

-- taps: the last R.KEEP intervals, oldest first. armed: a tap has started the count.
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

-- What reaches the inlet: tap <ms>, the interval u_tempo.pd's timer measured, and tempo <bpm>
-- from u_net.
R.inputs = {
  tap = function(st, a) return R.tap(st, a[1]) end,
  tempo = function(st, a) return R.set(st, a[1]) end,
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
