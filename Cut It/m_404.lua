-- m_404.lua -- the SP-404MKII's decode, both ways: a note and its bank in, a pad's name out; a
-- pad number out, a note on its bank's channel, behind the trigger budget. Plain Lua with no Pd
-- in it, so test/gate/lua/m_404_test.lua runs it on the Mac with lua.org's interpreter.
-- m_404-lua.pd_lua is its Pd face, and m_404.pd keeps the MIDI objects, the channel gates, the
-- CTRL knobs, the timer, the note-off's pipe, panic and presence. ref/device/sp404.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves,
-- in order, as {outlet, selector, atoms}:
--   {"off", "list", {note, 0, channel}}     a note-off, to the pipe that holds it 200 ms
--   {"note", "list", {note, velocity, channel}}   a note-on, to noteout
--   {"param", <name>, {velocity}}           a pad on the 404, as sp-b5 90
--   {"err", "fail", {"m_404", text}}        to err (C-12)

local R = {}

-- The pad map, pad n's note in every bank: four rows of four, counting upward from the bottom
-- row, so not 47 + n (item 190). ref/device/sp404.md holds the same table, and docs-check
-- compares the two.
R.NOTE = { 48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39 }

-- One table, both directions: the pad for a note is the same map read backwards, so there is
-- no second copy to drift.
R.PAD = {}
for pad, note in ipairs(R.NOTE) do R.PAD[note] = pad end

-- The bank letter, by the channel's offset from bank A: A to J are the 404's channels 1 to 10.
R.BANKS = "abcdefghij"

-- The trigger budget (item 208): sixteen at once, so a sequencer step with every drum track on
-- passes whole, refilled at one per 5 ms, 200 a second.
R.BUCKET, R.REFILL = 16, 0.2

-- A number from a message, as Pd's [f] reads one: a symbol or nothing is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- base: the Pd channel bank A lands on, m_404's creation argument. level: the budget left.
function R.new(base)
  return { base = num(base), level = 0 }
end

-- A note on one of the 404's ten channels: <note> <velocity> <bank>, the bank the channel's
-- offset from bank A, 0 to 9; m_404.pd's gate passes no other. The name carries the bank and
-- the pad, so sp-a1 and sp-b1 are told apart with nothing beside them. A release goes too, at
-- velocity 0. A note outside the pad map names no pad and sends nothing: the 404 sends none
-- (Reference, item 197).
function R.rx(st, note, velocity, bank)
  local pad = R.PAD[num(note)]
  bank = num(bank)
  if not pad or bank < 0 or bank > 9 or bank % 1 ~= 0 then return {} end
  local letter = R.BANKS:sub(bank + 1, bank + 1)
  return { { "param", "sp-" .. letter .. pad, { num(velocity) } } }
end

-- A pad to play: <pad> <velocity> <gap>, pads 1 to 160 across the ten banks, the gap the
-- milliseconds since the last trigger, by Pd's [timer]. The budget refills by the gap first; a
-- trigger it cannot pay for is dropped, never queued, since nothing between Pd and the 404
-- queues (item 209). A trigger that plays schedules its own note-off on its own channel, and a
-- dropped one schedules none. The bank picks the channel, the pad within it the note, as
-- [div 16] and [mod 16] did.
function R.tx(st, pad, velocity, gap)
  st.level = math.min(R.BUCKET, st.level + num(gap) * R.REFILL)
  if st.level < 1 then return {} end
  st.level = st.level - 1
  local i = num(pad) - 1
  local channel = st.base + i // 16
  local note = R.NOTE[i % 16 // 1 + 1]
  return { { "off", "list", { note, 0, channel } },
           { "note", "list", { note, num(velocity), channel } } }
end

-- What m_404.pd itself sends: the load.
R.internal = {
  init = function()
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "m_404", string.sub(text, 1, 21) } }
end

return R
