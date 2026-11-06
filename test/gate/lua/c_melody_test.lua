-- The melody and chord generator's rules, without Pd: "Cut It/c_melody.lua". One proof per
-- behavior. The synths gate runs this before its Pd half (test/gate/scratch-gates.py); by hand,
-- from the repo root:
--
--   lua test/gate/lua/c_melody_test.lua [-v]
--
-- How a loop sounds is the ear's, at the rig. ref/module/synths.md, The generator.

local T = dofile("test/gate/lua/lib_test.lua")
local R = dofile("Cut It/c_melody.lua")
local check, equal = T.check, T.equal

-- Dice that come up the same on any machine.
local function dice(seed)
  return function()
    seed = (seed * 1103515245 + 12345) % 2147483648
    return seed / 2147483648
  end
end

-- A loop one pattern long with its chords at these starts, 0 the first step, rolled and playing.
local function loop(starts, lock)
  local st = R.new(dice(7))
  st.chords, st.span, st.total, st["on-h"], st["chord-lock"] = #starts, 1, st.last, 1, lock or 100
  for i, t in ipairs(starts) do st.slot_start[i] = t end
  R.internal.init(st)
  while #st.to_roll > 0 do R.roll_next(st) end
  return st
end

-- A step of the clock at this place in the pattern. -> what it struck, each {voice, note}.
local function step(st, pos)
  st.count = (st.count or 0) + 1
  local struck = {}
  for _, e in ipairs(R.step(st, { st.count, 125, pos })) do
    if e[1] == "play" and e[3][3] > 0 then struck[#struck + 1] = { e[3][1], e[3][2] } end
  end
  return struck
end

-- Once round the pattern. -> {place, what it struck} for each step that struck something.
local function round(st)
  local out = {}
  for pos = 1, st.last do
    local struck = step(st, pos)
    if #struck > 0 then out[#out + 1] = { pos, struck } end
  end
  return out
end

-- A chord's notes struck on a voice, lowest first, as they leave.
local function on(voice, notes)
  local low, out = { table.unpack(notes) }, {}
  table.sort(low)
  for i, n in ipairs(low) do out[i] = { voice, n } end
  return out
end

-- Every chord's notes, as a copy to hold beside what comes later.
local function chords(st)
  local out = {}
  for i = 1, st.chords do out[i] = table.concat(st.slot[i], " ") end
  return out
end

print("\n--- a saved line ---")
local a = loop({ 4, 12 })
R.inputs.set(a, { "key", 8 })
local line = R.save(a)[3]
local floats = {}
for i, v in ipairs(line) do floats[i] = v + 0.0 end
local b = R.new(dice(2))
R.restore(b, floats)
-- By the text: 7 and 7.0 are equal as numbers, and a name or a key built from one is not.
equal("⛔ a restore from Pd's floats: the phone's line as it was saved, chord names and all",
      table.concat(R.phone(b), " "), table.concat(R.phone(a), " "))

-- The line as first saved: the controls, the steps and the chords, none of what came after.
local old = {}
for i = 1, #R.ORDER + 4 * R.STEPS + (1 + R.MAX_NOTES + 4) * R.SLOTS do old[i] = line[i] end
b = R.new(dice(2))
b.style = 2
R.restore(b, old)
equal("a line saved before the later fields loads: its key and chords, and the rest as they stand",
      { b.key, chords(b), b.style }, { 8, chords(a), 2 })

print("\n--- the lock ---")
local st = loop({ 0, 8 }, 100)
local was = chords(st)
for _ = 1, 4 do round(st) end
equal("chord lock 100 keeps every chord", chords(st), was)
st = loop({ 0, 8 }, 0)
was = chords(st)
for _ = 1, 4 do round(st) end
check("chord lock 0 rewrites them", table.concat(chords(st), "/") ~= table.concat(was, "/"),
      T.show(chords(st)))

print("\n--- when a chord sounds ---")
st = loop({ 4, 12 })
equal("before the first chord's start, the loop's last chord sounds", step(st, 1),
      on(R.STRINGS, st.slot[2]))
for pos = 2, st.last do step(st, pos) end
equal("each chord changes on the step its start says, and nowhere else, the last ringing on through "
      .. "the loop's top", round(st),
      { { 5, on(R.STRINGS, st.slot[1]) }, { 13, on(R.STRINGS, st.slot[2]) } })

print("\n--- the grid ---")
st = loop({ 4, 12 })
R.inputs.move(st, { 1, 7 })
equal("a chord moved goes where it is put", { st.slot_start[1], st.slot_start[2] }, { 7, 12 })
R.inputs.move(st, { 1, 12 })
equal("dropped on another chord's start, the two swap", { st.slot_start[1], st.slot_start[2] },
      { 12, 7 })
st = loop({ 4, 12 })
R.inputs.set(st, { "span", 2 })
equal("twice the span: the grid twice as long, and the chords in the same places along it",
      { st.total, st.slot_start[1], st.slot_start[2] }, { 32, 8, 24 })

print("\n--- what a chord plays on ---")
st = loop({ 0 })
st.slot[1] = { 45, 57, 60, 64 }
st.pedal = 0
R.inputs.bass(st, { 1 })
equal("bass only: one note, low", step(st, 1), { { R.STRINGS, 45 } })
st = loop({ 0, 8 })
st.slot[1], st.slot[2] = { 45, 57, 60, 64 }, { 47, 59 }
R.inputs.set(st, { "voice-h", R.FIRST_PD })
for pos = 1, 8 do step(st, pos) end
local notes = {}
for _, e in ipairs(R.step(st, { 100, 125, 9 })) do
  if e[1] == "play" then notes[#notes + 1] = { e[3][1], e[3][2], e[3][3] } end
end
equal("on a Pd voice each note of a chord has a voice of its own, and lets go on that voice", notes,
      { { 4, 45, 0 }, { 5, 57, 0 }, { 6, 60, 0 }, { 7, 64, 0 },
        { 4, 47, R.CHORD_VELOCITY_PD }, { 5, 59, R.CHORD_VELOCITY_PD } })

do
  -- The melody grid's hand edits: pinned, so a lock at 0 and a roll leave them, until pins are cleared.
  local st = R.new(dice(9))
  R.internal.init(st)
  while #st.to_roll + #st.to_roll_m > 0 do R.roll_next(st) end
  check("the whole melody is rolled ahead of playing, a note or a rest on every step",
        (function()
          for i = 1, st.loop do if st.note[i] == R.UNROLLED then return false end end
          return true
        end)())
  R.inputs["note-set"](st, { 3, 70 })
  R.inputs["note-move"](st, { 3, 5, 72 })
  R.inputs["note-rest"](st, { 7 })
  equal("a note moved leaves its step free, and lands pinned; one tapped away is a pinned rest",
        { st.note[3], st.pin[3], st.note[5], st.pin[5], st.note[7], st.pin[7] }, { 0, 0, 72, 1, 0, 1 })
  st["on-m"], st.notes, st.lock = 1, 100, 0
  R.internal.start(st)
  for c = 1, 32 do R.step(st, { c, 125, (c - 1) % st.last + 1 }) end
  R.inputs["roll-melody"](st, { 1 })
  equal("pinned steps stay through drift and a roll", { st.note[5], st.note[7] }, { 72, 0 })
  R.inputs["pins-clear"](st, { 1 })
  R.inputs["roll-melody"](st, { 1 })
  equal("cleared, a roll takes them", st.note[5], R.UNROLLED)
  equal("what the grid is sent: the loop, the tonic, seven notes of the mode, then each step's note and code",
        #R.phone_notes(st), 2 + 7 + 2 * R.STEPS)
end

do
  -- A melody has shapes and arrives somewhere: each phrase's arrival sounds, and its breath doesn't.
  local st = R.new(dice(11))
  R.internal.init(st)
  while #st.to_roll + #st.to_roll_m > 0 do R.roll_next(st) end
  local ok, arrivals = true, 0
  for i = 1, st.loop do
    if st.flag[i] == R.ARRIVAL then
      arrivals = arrivals + 1
      if st.note[i] <= 0 then ok = false end
    elseif st.flag[i] == R.BREATH and st.note[i] > 0 then
      ok = false
    end
  end
  check("every arrival sounds and every breath is silent", ok and arrivals >= 1, arrivals)
  -- Arrive all the way up: an arrival is a tension on the chord it will meet, not one of that chord's notes.
  st.arrive = 100
  local on_chord, seen = 0, 0
  for _ = 1, 30 do
    R.inputs["roll-melody"](st, { 1 })
    while #st.to_roll_m > 0 do R.roll_next(st) end
    for i = 1, st.loop do
      if st.flag[i] == R.ARRIVAL and st.note[i] > 0 then
        local best, at = nil, -1
        for k = 1, st.chords do
          local s = st.slot_start[k]
          if s >= 0 and s <= i - 1 and s > at then best, at = k, s end
        end
        if not best then
          for k = 1, st.chords do
            if st.slot_start[k] > at then best, at = k, st.slot_start[k] end
          end
        end
        seen = seen + 1
        for _, n in ipairs(st.slot[best]) do
          if n % 12 == st.note[i] % 12 then on_chord = on_chord + 1 end
        end
      end
    end
  end
  check("arrive up: arrivals land off the chord they meet", seen > 20 and on_chord * 10 < seen,
        on_chord .. " of " .. seen)
end

os.exit(T.report() == 0)
