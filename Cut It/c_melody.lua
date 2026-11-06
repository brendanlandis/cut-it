-- c_melody.lua -- the melody and chord generator: a loop of up to 32 steps and a loop of up to 8 chords,
-- in a key and mode, each rolled by weighted dice and kept or drifted by its own lock. Plain Lua with
-- no Pd in it, as c_synth.lua is. c_melody-lua.pd_lua is its Pd face, and c_melody.pd keeps the cords,
-- the note timing and the state bus.
--
-- Chords are built in thirds and other stacks from the mode's own notes. One is weighed by how little
-- its notes move from the chord before, how tense its own notes are, how its root moves, and how well
-- it sits with the tonic. A melody note is weighed by how well it sits with the chord sounding and the
-- mode, how far it is from the note before, which way the line has been going, and what the loop did
-- a phrase earlier. A locked loop keeps its notes when the chord changes (Brendan, 2026-11-05).
--
-- Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"play", "list", {voice, note, velocity, ms}}  to the note timing
--   {"mono", "list", {3 or 4, wave or -1}}         to the Pd voices
--   {"start", "bang", {}}                          to the transport
--   {"here", "here", {step, melody step}}          the loops' places, to the phone, -1 stopped
--   {"save", "melody", {numbers...}}               to the state bus, put section melody
--   {"disp", <row name>, {value}}                  a control's row, to disp
--   {"err", "fail", {"c_melody", text}}            to err (C-12)

local R = {}

R.STEPS, R.SLOTS, R.MAX_NOTES = 32, 8, 8
R.VOLCA, R.STRINGS = 1, 2
-- Where a part can sound: the two synths, or a basic Pd voice, c_mono, one note each. The melody has one
-- c_mono, 3, and the chords four, 4 to 7, a note each (Brendan, 2026-11-05: a chord on a Pd voice plays
-- all of it). On the Volca, which plays three at once, a chord is its lowest three.
R.VOICES = { "fm", "strings", "sine", "saw", "square" }
R.FIRST_PD = 3
R.MONO_M = 3
R.MONO_H = { 4, 5, 6, 7 }
R.UNROLLED, R.REST = -1, 0
R.CHORD_VELOCITY = 85
-- Softer on the Pd voices, whose notes add up on one output.
R.CHORD_VELOCITY_PD = 60
R.HERE_MIN_MS = 40
-- Where the parts live: the chords around this note, the melody an octave above it.
R.MIDDLE = 56

-- The keys, as the phone says them, and the modes.
R.KEYS = { "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B" }
R.MODES = {
  { "ionian", { 0, 2, 4, 5, 7, 9, 11 } }, { "dorian", { 0, 2, 3, 5, 7, 9, 10 } },
  { "phrygian", { 0, 1, 3, 5, 7, 8, 10 } }, { "lydian", { 0, 2, 4, 6, 7, 9, 11 } },
  { "mixolydian", { 0, 2, 4, 5, 7, 9, 10 } }, { "aeolian", { 0, 2, 3, 5, 7, 8, 10 } },
  { "locrian", { 0, 1, 3, 5, 6, 8, 10 } }, { "harm minor", { 0, 2, 3, 5, 7, 8, 11 } },
  { "mel minor", { 0, 2, 3, 5, 7, 9, 11 } },
}

-- The controls, each 0 to 100 but those with a scale of their own: what the map sends, 0 to 1, is
-- scaled here.
R.ORDER = { "lock", "fit", "leap", "notes", "length", "echo", "loop", "range",
            "chord-lock", "smooth", "tension", "home", "span", "chords", "voice-h", "voice-m",
            "key", "mode", "on-h", "on-m", "total" }
R.BOOT = { lock = 75, fit = 50, leap = 35, notes = 50, length = 50, echo = 40, loop = 16, range = 24,
           ["chord-lock"] = 75, smooth = 60, tension = 30, home = 65, span = 2, chords = 4,
           ["voice-h"] = 2, ["voice-m"] = 1, key = 1, mode = 6, ["on-h"] = 0, ["on-m"] = 0, total = 32 }
local SCALE = {
  loop = function(v) return math.floor(v * 31 + 1.5) end,
  range = function(v) return math.floor(v * 43 + 5.5) end,
  chords = function(v) return math.floor(v * (R.SLOTS - 1) + 1.5) end,
  span = function(v) return math.floor(v * 7 + 1.5) end,
}

-- The nearest whole ratios to the twelve semitones. The harmonicity of p/q is
-- 1 / (indigestibility(p) + indigestibility(q)), Barlow's measure. A unison would be infinite: it
-- counts as 0.5, a little under twice a fifth, so a chord's own notes don't drown out the rest.
local RATIOS = { { 1, 1 }, { 16, 15 }, { 9, 8 }, { 6, 5 }, { 5, 4 }, { 4, 3 }, { 7, 5 }, { 3, 2 },
                 { 8, 5 }, { 5, 3 }, { 16, 9 }, { 15, 8 } }

local function indigestibility(n)
  local sum, p = 0, 2
  while n > 1 do
    while n % p == 0 do
      sum = sum + 2 * (p - 1) * (p - 1) / p
      n = n // p
    end
    p = p + 1
  end
  return sum
end

R.HARMONICITY = {}
for i, r in ipairs(RATIOS) do
  local d = indigestibility(r[1]) + indigestibility(r[2])
  R.HARMONICITY[i - 1] = d == 0 and 0.5 or 1 / d
end

-- ---------------------------------------------------------------------- the mode's chords

-- The stacks a chord can be, as steps up the mode from its root.
local STACKS = { { 0, 2, 4 }, { 0, 2, 4, 6 }, { 0, 2, 4, 8 }, { 0, 2, 6, 8 }, { 0, 1, 4 }, { 0, 3, 4 },
                 { 0, 3, 4, 6 }, { 0, 2, 4, 5 }, { 0, 3, 6 },
                 { 0, 1 }, { 0, 2 }, { 0, 3 }, { 0, 4 }, { 0, 5 }, { 0, 6 } }
-- Dyads are rolled less often than chords, as there are as many kinds of each.
R.DYAD_WEIGHT = 0.4

-- What a set of semitones above a root is called: its name, what a Roman numeral adds, whether the
-- numeral is lower case, and the family it belongs to. A stack that makes none of these isn't rolled.
local QUALITY = {
  ["0 4 7"] = { "", "", false, "triad" }, ["0 3 7"] = { "m", "", true, "triad" },
  ["0 2 7"] = { "sus2", "sus2", false, "sus" }, ["0 5 7"] = { "sus4", "sus4", false, "sus" },
  ["0 5 10"] = { "7sus", "7sus", false, "sus" }, ["0 5 7 10"] = { "7sus4", "7sus4", false, "sus" },
  ["0 2 4 7"] = { "add9", "add9", false, "add" }, ["0 2 3 7"] = { "madd9", "add9", true, "add" },
  ["0 4 7 9"] = { "6", "6", false, "add" }, ["0 3 7 9"] = { "m6", "6", true, "add" },
  ["0 3 7 10"] = { "m7", "7", true, "seventh" }, ["0 4 7 11"] = { "maj7", "maj7", false, "seventh" },
  ["0 4 7 10"] = { "7", "7", false, "seventh" }, ["0 2 4 11"] = { "maj9", "maj9", false, "ninth" },
  ["0 2 3 10"] = { "m9", "9", true, "ninth" }, ["0 2 4 10"] = { "9", "9", false, "ninth" },
  ["0 3 7 11"] = { "mMaj7", "maj7", true, "sour" }, ["0 3 6 10"] = { "m7b5", "ø7", true, "sour" },
  ["0 5 7 11"] = { "maj7sus4", "maj7sus4", false, "sour" }, ["0 3 6"] = { "dim", "°", true, "sour" },
  ["0 4 8"] = { "aug", "+", false, "sour" }, ["0 1 4 7"] = { "addb9", "addb9", false, "sour" },
  ["0 1 3 7"] = { "maddb9", "addb9", true, "sour" }, ["0 1 3 10"] = { "m7b9", "7b9", true, "sour" },
  ["0 4 8 11"] = { "maj7#5", "+maj7", false, "sour" }, ["0 1 4 10"] = { "7b9", "7b9", false, "sour" },
  ["0 3 6 9"] = { "dim7", "°7", true, "sour" },
  ["0 7"] = { " P5", " P5", false, "dyad" }, ["0 5"] = { " P4", " P4", false, "dyad" },
  ["0 4"] = { " M3", " M3", false, "dyad" }, ["0 3"] = { " m3", " m3", true, "dyad" },
  ["0 9"] = { " M6", " M6", false, "dyad" }, ["0 8"] = { " m6", " m6", true, "dyad" },
  ["0 2"] = { " M2", " M2", false, "sour" }, ["0 10"] = { " m7", " m7", true, "sour" },
  ["0 6"] = { " TT", " TT", false, "sour" }, ["0 11"] = { " M7", " M7", false, "sour" },
  ["0 1"] = { " m2", " m2", true, "sour" },
}

-- A loop's vocabulary (2026-11-05): most of its chords come from one family and a few from another, so it
-- has a sound of its own. Tension picks the families, each centered here, 0 to 1.
R.FAMILIES = { "triad", "dyad", "sus", "add", "seventh", "ninth", "sour" }
local CENTER = { triad = 0, dyad = 0.15, sus = 0.3, add = 0.35, seventh = 0.45, ninth = 0.6, sour = 0.85 }
local FROM_MAIN, FROM_COLOR, FROM_OTHER = 1, 0.2, 0.02

-- Modal or functional (Brendan, 2026-11-05), by the two ways a root moves. Modal drifts: steps and thirds,
-- few fourths and fifths, the same shape sliding along the mode, and the note that makes the mode itself
-- heard, each mode's here, above the tonic.
R.STYLES = { "modal", "functional" }
local MODAL_MOVE = { [0] = 0.3, 1.2, 1.5, 1.2, 1.2, 0.7, 0.6, 0.5, 1.2, 1.2, 1.5, 1.2 }
local CHARACTER = { 5, 9, 1, 6, 10, 8, 6, 11, 9 }
-- Functional has roles: each degree tonic, predominant or dominant, and a loop runs through them to a
-- dominant that leads back round.
local ROLE = { "T", "P", "T", "P", "D", "T", "D" }
local function role_at(k, n)
  if k == n and n > 1 then return "D" end
  if k == n - 1 and n > 2 then return "P" end
  return k % 2 == 1 and "T" or "P"
end

local LETTERS = { "C", "D", "E", "F", "G", "A", "B" }
local NATURAL = { 0, 2, 4, 5, 7, 9, 11 }
local NUMERALS = { "I", "II", "III", "IV", "V", "VI", "VII" }
local MAJOR = { 0, 2, 4, 5, 7, 9, 11 }

local function accidental(diff)
  if diff < 0 then return string.rep("b", -diff) end
  return string.rep("#", diff)
end

local function fit_of(notes)
  local fit = {}
  for pc = 0, 11 do
    local h = 0
    for _, t in ipairs(notes) do h = h + R.HARMONICITY[(pc - t) % 12] end
    fit[pc] = h / #notes
  end
  return fit
end

-- Work out the key and mode: the mode's notes, spelled with a letter each, every chord it can make,
-- with its name, spelling and Roman numeral, and the tonic's triad, which home pulls toward.
local function tune(st)
  local steps = R.MODES[st.mode][2]
  local tonic = math.floor(st.key - 1)
  local name = R.KEYS[st.key]
  local letter
  for i, l in ipairs(LETTERS) do if l == name:sub(1, 1) then letter = i end end
  st.scale, st.in_scale, st.spelled = {}, {}, {}
  for d = 1, 7 do
    local pc = (tonic + steps[d]) % 12
    st.scale[d] = pc
    st.in_scale[pc] = true
    local l = (letter + d - 2) % 7 + 1
    st.spelled[d] = LETTERS[l] .. accidental((pc - NATURAL[l] + 6) % 12 - 6)
  end
  local all, by = {}, {}
  for d = 1, 7 do
    by[d] = {}
    for sh, stack in ipairs(STACKS) do
      local pcs, spell, semis = {}, {}, {}
      for j, up in ipairs(stack) do
        local at = (d - 1 + up) % 7 + 1
        pcs[j] = st.scale[at]
        spell[j] = st.spelled[at]
        semis[j] = (pcs[j] - st.scale[d]) % 12
      end
      table.sort(semis)
      local q = QUALITY[table.concat(semis, " ")]
      if q then
        local numeral = q[3] and NUMERALS[d]:lower() or NUMERALS[d]
        local c = { deg = d, shape = sh, pcs = pcs, root = st.scale[d],
                    family = q[4], name = st.spelled[d] .. q[1], spell = table.concat(spell, " "),
                    roman = accidental(steps[d] - MAJOR[d]) .. numeral .. q[2] }
        all[#all + 1] = c
        by[d][sh] = c
      end
    end
  end
  st.candidates, st.cand_by = all, by
  st.tonic = tonic
  st.character = (tonic + CHARACTER[st.mode]) % 12
  st.tonic_pcs = by[1][1] and by[1][1].pcs or { tonic }
  st.home_fit = fit_of(st.tonic_pcs)
end

-- What the melody hears: how each pitch class sits with these notes, the mode's own far ahead of the rest.
local function hear(st, notes)
  local fit = fit_of(#notes > 0 and notes or st.tonic_pcs)
  for pc = 0, 11 do
    if not st.in_scale[pc] then fit[pc] = fit[pc] * 0.25 end
  end
  st.heard = fit
end

-- How strong a step is: its place in the loop, step 1 the strongest, the off-beats nothing.
function R.pulse(i)
  local n = i - 1
  if n % 16 == 0 then return 1 end
  if n % 8 == 0 then return 0.8 end
  if n % 4 == 0 then return 0.6 end
  if n % 2 == 0 then return 0.3 end
  return 0
end

-- A number from a message. Pd's are all floats, and a whole one is made an integer here: a float
-- prints as 7.0, which no table of names would know.
local function num(x)
  if type(x) ~= "number" then return 0 end
  return math.tointeger(x) or x
end

function R.new(rand)
  local st = { rand = rand or math.random, pos = 0, hist = {}, running = false,
               note = {}, vel = {}, gate = {}, pin = {}, target = {}, flag = {}, disp = {},
               slot = {}, slot_start = {}, slot_pin = {}, slot_deg = {}, slot_shape = {},
               last = 16, bar = 0, ch_pos = 0, sounding = {}, pressed = {}, where = {}, to_roll = {}, to_roll_m = {}, dirty = false }
  for k, v in pairs(R.BOOT) do st[k] = v end
  st.style, st["v-main"], st["v-color"], st.pedal, st.bass = 1, 1, 4, 0, 0
  st.arrive, st.octave = 75, 25
  for i = 1, R.STEPS do
    st.note[i], st.vel[i], st.gate[i], st.pin[i] = R.UNROLLED, 0, 0, 0
    st.target[i], st.flag[i], st.disp[i] = R.MIDDLE + 12, 0, 0
  end
  for i = 1, R.SLOTS do
    st.slot[i], st.slot_start[i], st.slot_pin[i], st.slot_deg[i], st.slot_shape[i] = {}, -1, 0, 0, 0
  end
  st.center = R.MIDDLE + 12
  tune(st)
  hear(st, {})
  return st
end

-- ---------------------------------------------------------------------- the chords

-- How much a root's move is worth: fourths and fifths most, then steps, thirds, half steps, the tritone;
-- staying on a root least.
local ROOT_MOVE = { [0] = 0.2, 0.7, 1.2, 1, 1, 1.6, 0.5, 1.6, 1, 1, 1.2, 0.7 }

-- The active slots in the order they play, by where each starts.
local function in_order(st)
  local list = {}
  for i = 1, st.chords do
    if st.slot_start[i] >= 0 then list[#list + 1] = i end
  end
  table.sort(list, function(a, b) return st.slot_start[a] < st.slot_start[b] end)
  return list
end

-- A new vocabulary for the loop: two families, as near to tension as dice say. In a modal loop, a held
-- tonic in the bass as often as home is turned up.
local function roll_vocab(st)
  local function draw(skip)
    local weights, total = {}, 0
    for i, f in ipairs(R.FAMILIES) do
      local off = (CENTER[f] - st.tension / 100) / 0.2
      local w = f == skip and 0 or math.exp(-off * off) + 0.001
      if f == "dyad" then w = w * 0.4 end
      weights[i] = w
      total = total + w
    end
    local roll = st.rand() * total
    for i, f in ipairs(R.FAMILIES) do
      roll = roll - weights[i]
      if roll <= 0 and weights[i] > 0 then return i end
    end
    return 1
  end
  st["v-main"] = draw(nil)
  st["v-color"] = draw(R.FAMILIES[st["v-main"]])
  st.pedal = (st.style == 1 and st.rand() < st.home / 100) and 1 or 0
end

-- A chord by weighted dice over the mode's chords. A chord is weighed by the loop's vocabulary, by how
-- far its notes are from the chord before (smooth), how well it sits with the tonic (home), how the root
-- moves, by the style's own rules, and by whether it carries on the shape of the phrase before it: seq, a
-- degree, when it does. A chord already in the loop is rarely picked again, so a longer loop has more
-- chords in it, not the same ones over.
local function pick_chord(st, how)
  local prev = how.prev
  local rand = st.rand
  local all = st.candidates
  local near = {}
  for pc = 0, 11 do
    local best = 6
    for _, p in ipairs(prev) do
      local d = (pc - p) % 12
      if d > 6 then d = 12 - d end
      if d < best then best = d end
    end
    near[pc] = best
  end
  local smooth = st.smooth / 100 * 2.5
  local pull = st.home / 100 * 6
  local home_fit = st.home_fit
  local tonic_by = 1 + st.home / 50
  local modal = st.style == 1
  local main, color = R.FAMILIES[st["v-main"]], R.FAMILIES[st["v-color"]]
  local weights, total = {}, 0
  for n, c in ipairs(all) do
    local pcs = c.pcs
    local size, far, fit, has_character = #pcs, 0, 0, false
    for j = 1, size do
      local pc = pcs[j]
      far = far + near[pc]
      fit = fit + home_fit[pc]
      if pc == st.character then has_character = true end
    end
    local w = math.exp(-far / size * smooth) * (fit / size) ^ pull
    w = w * (c.family == main and FROM_MAIN or c.family == color and FROM_COLOR or FROM_OTHER)
    if far == 0 and #prev > 0 then w = w * 0.02 end
    if c.deg == 1 then w = w * tonic_by end
    if how.used[c.deg .. " " .. c.shape] then w = w * 0.03 end
    if how.seq == c.deg then w = w * 4 end
    if modal then
      if how.prev_root then w = w * MODAL_MOVE[(c.root - how.prev_root) % 12] end
      if how.prev_shape == c.shape then w = w * 3 end
      if has_character then w = w * 1.8 end
    else
      if how.prev_root then w = w * ROOT_MOVE[(c.root - how.prev_root) % 12] end
      w = w * (ROLE[c.deg] == how.role and 8 or 0.25)
      if how.into_root then w = w * (ROOT_MOVE[(how.into_root - c.root) % 12] + 0.2) end
    end
    weights[n] = w
    total = total + w
  end
  local roll = rand() * total
  for n, c in ipairs(all) do
    roll = roll - weights[n]
    if roll <= 0 then return c end
  end
  return all[#all]
end

local function into(n, lo, hi)
  while n < lo do n = n + 12 end
  while n > hi do n = n - 12 end
  return n
end

-- Real notes for pitch classes: the root low, the rest above it around the middle, each as near as it
-- can be to a note of the chord before, so the voices move little.
local function voice(pcs, prev, pedal)
  local bass_was, uppers = nil, {}
  for _, p in ipairs(prev) do
    if not bass_was or p < bass_was then bass_was = p end
  end
  for _, p in ipairs(prev) do
    if p ~= bass_was then uppers[#uppers + 1] = p end
  end
  local mid = R.MIDDLE
  local bass = bass_was and bass_was + (pcs[1] - bass_was + 6) % 12 - 6
               or mid - 15 + (pcs[1] - (mid - 15)) % 12
  local first = 2
  if pedal then
    bass, first = mid - 15 + (pedal - (mid - 15)) % 12, 1
  end
  local notes = { into(bass, mid - 15, mid - 4) }
  for i = first, #pcs do
    local pc, n, gap = pcs[i], nil, 99
    for _, p in ipairs(uppers) do
      local d = (pc - p + 6) % 12 - 6
      if math.abs(d) < gap then n, gap = p + d, math.abs(d) end
    end
    n = n or (mid - 2 + (pc - (mid - 2)) % 12)
    notes[#notes + 1] = into(n, mid - 2, mid + 12)
  end
  return notes
end

-- The rhythm: where each chord starts, on the grid of the whole loop, span times the pattern's last step
-- long. Each is drawn by weighted dice, so the changes needn't fall at even distances, though they may
-- (Brendan, 2026-11-05): a bar's first step is likeliest, then its half and quarters, and off-beats least.
local function strength(st, t)
  local p = t % st.last
  if p == 0 then return 6 end
  if p % 8 == 0 then return 2.5 end
  if p % 4 == 0 then return 1.5 end
  if p % 2 == 0 then return 0.6 end
  return 0.35
end

-- A free place for a chord: far enough from those placed, by weighted dice.
local function place(st, taken, gap)
  local total, weights = 0, {}
  for t = 0, st.total - 1 do
    local w = strength(st, t)
    for _, other in ipairs(taken) do
      local d = math.abs(t - other)
      if math.min(d, st.total - d) < gap then w = 0 break end
    end
    weights[t] = w
    total = total + w
  end
  if total == 0 then
    if gap > 1 then return place(st, taken, 1) end
    return -1
  end
  local roll = st.rand() * total
  for t = 0, st.total - 1 do
    roll = roll - weights[t]
    if roll <= 0 and weights[t] > 0 then return t end
  end
  return -1
end

local function min_gap(st)
  return math.max(1, st.total // (st.chords * 2))
end

-- A whole new rhythm. The first chord needn't be on the loop's first step (Brendan, 2026-11-05): before it,
-- the last chord is still ringing. They are given to the slots in order, so the chords keep theirs.
local function roll_rhythm(st)
  local gap = min_gap(st)
  local taken = {}
  for _ = 1, math.min(st.chords, st.total) do
    local t = place(st, taken, gap)
    if t >= 0 then taken[#taken + 1] = t end
  end
  table.sort(taken)
  for i = 1, R.SLOTS do st.slot_start[i] = -1 end
  local list = {}
  for i = 1, st.chords do list[i] = i end
  for n, t in ipairs(taken) do st.slot_start[list[n]] = t end
  st.dirty = true
end

-- A slot rolled, following the chord before it in the order they play. In a loop of four or more, the second
-- half leans toward the first's shape: the same moves of its root, from where it now is, so it answers the
-- first half without repeating it.
local function roll_chord(st, i)
  local order = in_order(st)
  local n, at = #order, 1
  for k, s in ipairs(order) do if s == i then at = k end end
  local back = order[(at - 2) % math.max(1, n) + 1]
  local prev = back and back ~= i and st.slot[back] or {}
  local rolled_back = #prev > 0
  if not rolled_back then prev = st.sounding end
  local first = order[1]
  local how = { prev = prev, role = role_at(at, n), used = {},
                prev_root = rolled_back and st.scale[st.slot_deg[back]] or nil,
                prev_shape = rolled_back and st.slot_shape[back] or nil }
  if at == n and first ~= i and st.slot_deg[first] > 0 then how.into_root = st.scale[st.slot_deg[first]] end
  local half = n // 2
  if n >= 4 and at >= half + 2 and at < n and rolled_back then
    local a, b = st.slot_deg[order[at - half]], st.slot_deg[order[at - half - 1]]
    if a > 0 and b > 0 then how.seq = (st.slot_deg[back] - 1 + a - b) % 7 + 1 end
  end
  for _, s in ipairs(order) do
    if s ~= i and #st.slot[s] > 0 then how.used[st.slot_deg[s] .. " " .. st.slot_shape[s]] = true end
  end
  local c = pick_chord(st, how)
  st.slot[i] = voice(c.pcs, prev, st.pedal == 1 and st.tonic or nil)
  st.slot_deg[i], st.slot_shape[i] = c.deg, c.shape
  st.dirty = true
end

-- A slot's chord, as the mode knows it; for one played in that the mode has no name for, its notes as they
-- stand; nil for an empty one.
local FLATS = { [0] = "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B" }
local function chord_of(st, i)
  local by = st.cand_by[st.slot_deg[i]]
  local c = by and by[st.slot_shape[i]]
  if c or #st.slot[i] == 0 then return c end
  local spell = {}
  for j, n in ipairs(st.slot[i]) do spell[j] = FLATS[n % 12] end
  return { name = spell[1] .. "*", spell = table.concat(spell, " "), roman = "?" }
end

-- Where the melody sounds now.
local function melody_to(st)
  local v = st["voice-m"]
  return v >= R.FIRST_PD and R.MONO_M or v
end

-- Which of a chord's notes sound. Bass only (Brendan, 2026-11-06): its root alone, down in the bass, on any
-- voice. A held tonic isn't the chord's root, which is then the next note. Else what its voice can play.
local function playable(st, notes)
  if st.bass == 1 and #notes > 0 then
    local root = st.pedal == 1 and notes[2] or notes[1]
    return { into(root, R.MIDDLE - 15, R.MIDDLE - 4) }
  end
  local v = st["voice-h"]
  local limit = v >= R.FIRST_PD and #R.MONO_H or v == R.VOLCA and 3 or #notes
  local sorted = {}
  for i, n in ipairs(notes) do sorted[i] = n end
  table.sort(sorted)
  local out = {}
  for i = 1, math.min(limit, #sorted) do out[i] = sorted[i] end
  return out
end

-- From the chord sounding to this one: all its notes let go and all the new ones are struck, shared ones
-- too, so every chord is heard to land when it should (Brendan, 2026-11-05). where[note] is the voice a note
-- is sounding on, and on the Pd voices each new note takes the next of the four.
local function change_to(st, notes, out)
  local v = st["voice-h"]
  local pd = v >= R.FIRST_PD
  for _, n in ipairs(st.pressed) do
    out[#out + 1] = { "play", "list", { st.where[n], n, 0, 0 } }
  end
  st.where = {}
  local want = playable(st, notes)
  for k, n in ipairs(want) do
    local t = pd and R.MONO_H[k] or v
    st.where[n] = t
    out[#out + 1] = { "play", "list", { t, n, pd and R.CHORD_VELOCITY_PD or R.CHORD_VELOCITY, 0 } }
  end
  st.pressed, st.sounding = want, notes
  hear(st, notes)
end

-- What each Pd voice should be: its wave, or off when its part is elsewhere.
local function waves(st, out)
  local m, h = st["voice-m"], st["voice-h"]
  out[#out + 1] = { "mono", "list", { R.MONO_M, m >= R.FIRST_PD and m - R.FIRST_PD or -1 } }
  out[#out + 1] = { "mono", "list", { R.MONO_H[1], h >= R.FIRST_PD and h - R.FIRST_PD or -1 } }
  return out
end

-- The chord that should be sounding at t on the grid: the one that started last, and before the first
-- start, the last chord of the loop, still ringing.
local function active_at(st, t)
  local best, best_at, latest, latest_at = nil, -1, nil, -1
  for i = 1, st.chords do
    local s = st.slot_start[i]
    if s >= 0 then
      if s <= t and s > best_at then best, best_at = i, s end
      if s > latest_at then latest, latest_at = i, s end
    end
  end
  return best or latest
end

-- A step of the chord loop, at this place in the pattern. The loop keeps its place whether the chords are
-- on or not, so turned on mid-loop they land where they belong. When a chord's turn comes it is rolled if
-- empty, or if its lock lets it, and sounds. A chord being tapped keeps sounding, and the loop counts on
-- under it. -> the place on the grid.
local function chord_step(st, pos, out)
  if pos == 1 or st.bar == 0 then st.bar = st.bar % st.span + 1 end
  local t = ((st.bar - 1) * st.last + pos - 1) % math.max(1, st.total)
  if st["on-h"] == 0 then
    if #st.sounding > 0 and not st.audition then change_to(st, {}, out) end
    if st.ch_pos ~= 0 then st.ch_pos, st.show = 0, true end
    return t
  end
  local i = active_at(st, t)
  if not i then return t end
  if i == st.ch_pos and st.slot_start[i] ~= t then return t end
  st.ch_pos, st.show = i, true
  local free = 1 - st["chord-lock"] / 100
  if #st.slot[i] == 0 or (st.slot_pin[i] == 0 and st.rand() < free * free) then roll_chord(st, i) end
  if not st.audition then change_to(st, st.slot[i], out) end
  return t
end

-- Make sure every active slot has a place and a chord: a slot with no place gets one now, and those with
-- no chord are queued, for the face to roll one at a time, so the phone has names to show without a burst
-- of work in one audio block.
local function queue_empty(st)
  st.to_roll = {}
  local any = false
  for i = 1, st.chords do if st.slot_start[i] >= 0 then any = true end end
  if not any then
    roll_rhythm(st)
  else
    local taken = {}
    for i = 1, st.chords do
      if st.slot_start[i] >= 0 then taken[#taken + 1] = st.slot_start[i] end
    end
    for i = 1, st.chords do
      if st.slot_start[i] < 0 then
        local t = place(st, taken, min_gap(st))
        st.slot_start[i] = t
        if t >= 0 then taken[#taken + 1] = t end
      end
    end
  end
  for i = 1, st.chords do
    if #st.slot[i] == 0 and st.slot_start[i] >= 0 then st.to_roll[#st.to_roll + 1] = i end
  end
end

-- When the loop's length changes, with the span or the pattern's last step, the chords stay in the same
-- places along it.
local function rescale(st)
  local total = st.span * st.last
  if total == st.total then return end
  local was = st.total
  st.total = total
  local seen = {}
  for i = 1, R.SLOTS do
    local s = st.slot_start[i]
    if s >= 0 then
      local t = math.floor(s * total / math.max(1, was) + 0.5) % total
      while seen[t] and t < total - 1 do t = t + 1 end
      seen[t] = true
      st.slot_start[i] = t
    end
  end
  st.bar = math.min(st.bar, st.span)
end

-- Queue the melody's unrolled steps. The face rolls a few at a time, each hearing the chord it will meet the
-- first time round, so the phone's grid shows the whole loop at once.
local function queue_melody(st)
  st.to_roll_m = {}
  for i = 1, st.loop do
    if st.note[i] == R.UNROLLED then st.to_roll_m[#st.to_roll_m + 1] = i end
  end
end
R.queue_melody = queue_melody

R.ROLL_AT_ONCE = 4

-- One queued slot rolled, or a few of the melody's steps, from the face's clock.
function R.roll_next(st)
  if #st.to_roll == 0 and #st.to_roll_m > 0 then
    local was = st.dirty
    for _ = 1, R.ROLL_AT_ONCE do
      local i = table.remove(st.to_roll_m, 1)
      if not i then break end
      if st.note[i] == R.UNROLLED then
        local c = active_at(st, (i - 1) % math.max(1, st.total))
        st.meeting = c and #st.slot[c] > 0 and st.slot[c] or nil
        hear(st, st.meeting or {})
        R.roll_step(st, i)
      end
    end
    st.meeting = nil
    hear(st, st.sounding)
    if st.quiet then st.dirty = was end
    if #st.to_roll_m == 0 then st.quiet = false end
    return {}
  end
  local i = table.remove(st.to_roll, 1)
  if i and #st.slot[i] == 0 then
    local was = st.dirty
    roll_chord(st, i)
    if st.quiet then st.dirty = was end
  end
  if #st.to_roll == 0 and #st.to_roll_m == 0 then st.quiet = false end
  return {}
end

-- ---------------------------------------------------------------------- the melody

-- A melody has shapes: it goes up and down and arrives somewhere (Brendan, 2026-11-06). So a loop is planned
-- before its notes are rolled: it is cut into phrases, each with a shape, whose height at each step says
-- about where the line should be, and each phrase ends on an arrival, a long note, on a tension if arrive
-- is up, then a breath. The dice choose the actual notes around that plan, so a loop drifting under a low
-- lock keeps its shape while its notes change.
local CONTOURS = {
  arch = function(x) return math.sin(x * math.pi) end,
  rise = function(x) return x end,
  fall = function(x) return 1 - x end,
  valley = function(x) return 1 - math.sin(x * math.pi) end,
  late = function(x) return x < 0.7 and x / 0.7 or (1 - x) / 0.3 end,
}
local FIRST_SHAPES = { "arch", "rise", "fall", "late", "valley", "rise", "late" }
-- What answers a shape: a phrase that climbed tends to come back down, and so on.
local ANSWERS = { rise = { "fall", "arch" }, fall = { "rise", "valley" }, arch = { "fall", "rise" },
                  valley = { "rise", "arch" }, late = { "fall", "valley" } }
R.NORMAL, R.ARRIVAL, R.BREATH = 0, 1, 2

local function plan_melody(st)
  local rand = st.rand
  local n = st.loop
  local count = n >= 24 and 3 or n >= 10 and 2 or 1
  -- Where each phrase ends: about evenly along, on an even step, a little off so they aren't always so.
  local ends = {}
  for p = 1, count - 1 do
    local at = math.floor(n * p / count + (rand() * 4 - 2) + 0.5)
    at = at - at % 2
    ends[p] = math.max(2, math.min(n - 2, at))
  end
  ends[count] = n
  local amp = st.range * (0.3 + 0.7 * st.leap / 100)
  local shape = FIRST_SHAPES[math.floor(rand() * #FIRST_SHAPES) + 1]
  local from = 1
  for p = 1, count do
    local last = ends[p]
    local len = math.max(1, last - from + 1)
    -- The arrival, on a strong step if one is near, and after it a breath of up to three steps.
    local breath = math.min(len - 1, math.floor(rand() * 4))
    local arrive = last - breath
    if arrive > from and (arrive - 1) % 2 == 1 then arrive = arrive - 1 end
    local curve = CONTOURS[shape]
    local top = arrive - from
    for i = from, last do
      local x = top > 0 and math.min(1, (i - from) / top) or 1
      st.target[i] = math.floor(st.center + (curve(x) - 0.5) * amp + 0.5)
      st.flag[i] = i == arrive and R.ARRIVAL or i > arrive and R.BREATH or R.NORMAL
    end
    local answers = ANSWERS[shape]
    shape = answers[math.floor(rand() * #answers) + 1]
    from = last + 1
  end
  for i = n + 1, R.STEPS do st.target[i], st.flag[i] = st.center, R.NORMAL end
end

-- The line a note is on: what it would be without its octave displacement.
local function line_of(st, j)
  return st.note[j] - st.disp[j]
end

-- The note before step i on the line, and the step it is on; nil if there is none.
local function before(st, i)
  for back = 1, st.loop - 1 do
    local j = (i - back - 1) % st.loop + 1
    if st.note[j] > 0 then return line_of(st, j), j end
  end
  return nil
end

-- The step whose rhythm and interval a roll of step i may repeat: a phrase back.
local function phrase_back(st, i)
  local back = st.loop >= 12 and 8 or math.max(2, st.loop // 2)
  return (i - back - 1) % st.loop + 1
end

-- Whether step i sounds. An arrival does, and a breath doesn't. Else notes says how many of the loop's steps
-- do, and a roll leans toward whichever brings the loop back to it. A step after a note is likelier to
-- sound than one after a rest, and strong steps are likelier. echo may copy a phrase back instead, unless
-- the loop is well off what notes asks.
local function sounds(st, i)
  if st.flag[i] == R.ARRIVAL then return true end
  if st.flag[i] == R.BREATH then return false end
  local d = st.notes / 100
  local rolled, sounding = 0, 0
  for j = 1, st.loop do
    if j ~= i and st.note[j] ~= R.UNROLLED then
      rolled = rolled + 1
      if st.note[j] > 0 then sounding = sounding + 1 end
    end
  end
  local short = rolled >= 4 and d - sounding / rolled or 0
  local j = phrase_back(st, i)
  if math.abs(short) < 0.15 and st.rand() < st.echo / 100 and st.note[j] ~= R.UNROLLED
     and st.flag[j] == R.NORMAL then
    return st.note[j] > 0
  end
  local last = st.note[(i - 2) % st.loop + 1]
  local p = last > 0 and d + (1 - d) * 0.35 or d * 0.65
  return st.rand() < p * (0.8 + 0.76 * R.pulse(i)) + short
end

-- How each pitch class serves as an arrival: arrive up, a tension, the mode's notes off the chord, and best
-- a whole step or more above a chord tone; arrive down, the chord's own notes.
local function arrival_weights(st)
  local chord = {}
  local notes = st.meeting or (#st.sounding > 0 and st.sounding) or st.tonic_pcs
  for _, t in ipairs(notes) do chord[t % 12] = true end
  local want = st.arrive / 100
  local out = {}
  for pc = 0, 11 do
    if chord[pc] then
      out[pc] = 1 - want + 0.02
    elseif st.in_scale[pc] then
      out[pc] = (0.05 + want) * (chord[(pc - 1) % 12] and 0.5 or 1)
    else
      out[pc] = 0
    end
  end
  return out
end

-- The note of step i on the line, by weighted dice over the range: near the plan's height for this step,
-- near the note before, sitting with the chord and mode; at an arrival, the arrival's own weights in place
-- of the fit.
local function pick(st, i)
  local rand = st.rand
  local prev = before(st, i) or st.target[i]
  local arriving = st.flag[i] == R.ARRIVAL
  -- What the same place did a phrase back, from here.
  local echoed
  if not arriving and rand() < st.echo / 100 then
    local j = phrase_back(st, i)
    local was = before(st, j)
    if st.note[j] > 0 and was then echoed = prev + line_of(st, j) - was end
  end
  local k = st.fit / 100 * 8 - 2 + (R.pulse(i) - 0.4) * 2
  local width = 1 + (st.leap / 100) ^ 1.5 * 12
  local target = st.target[i]
  local toward = arriving and 5 or 3
  local lo = math.max(12, st.center - st.range // 2)
  local hi = math.min(108, st.center + st.range // 2)
  local heard = arriving and arrival_weights(st) or st.heard
  local weights, total = {}, 0
  for c = lo, hi do
    local d = c - prev
    local w = arriving and heard[c % 12] or heard[c % 12] ^ k
    w = w * math.exp(-math.abs(d) / width) * math.exp(-math.abs(c - target) / toward)
    if d == 0 then w = w * 0.2 end
    if echoed then
      if c == echoed then w = w * 8 elseif math.abs(c - echoed) == 1 then w = w * 2 end
    end
    weights[c - lo + 1] = w
    total = total + w
  end
  if total <= 0 then return target end
  local roll = rand() * total
  for c = lo, hi do
    roll = roll - weights[c - lo + 1]
    if roll <= 0 then return c end
  end
  return hi
end

-- A step rolled: a rest, or a note with its velocity and length, whole numbers all. Octave displacement: now
-- and then a note jumps an octave off the line, and the line carries on where it was, so the shape stays.
-- An arrival is likelier to, and plays harder and long, into the breath.
local function roll(st, i)
  st.dirty, st.show_notes = true, true
  st.disp[i] = 0
  if not sounds(st, i) then
    st.note[i], st.vel[i], st.gate[i] = R.REST, 0, 0
    return
  end
  local n = pick(st, i)
  local arriving = st.flag[i] == R.ARRIVAL
  if st.rand() < st.octave / 100 * (arriving and 0.6 or 0.3) then
    local by = st.rand() < 0.5 and 12 or -12
    if n + by > 96 or n + by < 24 then by = -by end
    st.disp[i] = by
    n = n + by
  end
  local half = st.range / 2
  local v = 70 + 40 * R.pulse(i) + 16 * (n - st.center) / half + (st.rand() * 24 - 12)
  if arriving then v = v + 14 end
  local r = st.rand()
  st.note[i] = n
  st.vel[i] = math.floor(math.max(20, math.min(127, v)) + 0.5)
  st.gate[i] = arriving and 800 or math.floor((0.25 + (st.length / 100) ^ 1.5 * r * r * 8) * 100 + 0.5)
end

R.roll_step = roll

-- How many steps until the next sounding note, so a note lets go before the next one lands.
local function room(st, i)
  for ahead = 1, st.loop do
    if st.note[(i + ahead - 1) % st.loop + 1] > 0 then return ahead end
  end
  return st.loop
end

-- A note out: on now, off after its length, on the grid.
local function sound(e, ms, out)
  if e.n <= 0 then return out end
  out[#out + 1] = { "play", "list", { e.to, e.n, e.v, 0 } }
  out[#out + 1] = { "play", "list", { e.to, e.n, 0, math.max(20, e.len * ms - 5) } }
  return out
end

-- A step of the clock, numbered by c_steps, and how long it lasts in ms. A number seen before is
-- a repeat pad replaying that step, so what it played plays again: nothing moves on and nothing
-- rolls. Else the chords move on first, so the melody hears the new one, then the loop moves on,
-- and its step is rolled if it never has been or if the lock lets it.
function R.step(st, atoms)
  local count, ms, pos = num(atoms[1]), num(atoms[2]), num(atoms[3])
  local seen = st.hist[count]
  if seen then return sound(seen, ms, {}) end
  local out = {}
  local here = chord_step(st, pos, out)
  st.pos = st.pos % st.loop + 1
  local i = st.pos
  local e = { n = 0, v = 0, len = 0, to = melody_to(st) }
  if st.notes > 0 and st["on-m"] == 1 then
    local free = 1 - st.lock / 100
    if st.note[i] == R.UNROLLED or (st.pin[i] == 0 and st.rand() < free * free) then roll(st, i) end
    if st.note[i] > 0 then
      e.n, e.v = st.note[i], st.vel[i]
      e.len = math.min(st.gate[i] / 100, room(st, i))
    end
  end
  st.hist[count] = e
  st.hist[count - 64] = nil
  -- Where the loop is, for the phone's grid, unless the steps come too fast for it to matter.
  if ms >= R.HERE_MIN_MS then out[#out + 1] = { "here", "here", { here, i } } end
  return sound(e, ms, out)
end

-- ---------------------------------------------------------------------- saving

-- What the song store holds: the controls, the 32 steps, then the 8 chords.
function R.save(st)
  local a = {}
  for _, k in ipairs(R.ORDER) do a[#a + 1] = st[k] end
  for i = 1, R.STEPS do
    a[#a + 1] = st.note[i]
    a[#a + 1] = st.vel[i]
    a[#a + 1] = st.gate[i]
    a[#a + 1] = st.pin[i]
  end
  for i = 1, R.SLOTS do
    local list = st.slot[i]
    a[#a + 1] = #list
    for j = 1, R.MAX_NOTES do a[#a + 1] = list[j] or 0 end
    a[#a + 1] = st.slot_start[i]
    a[#a + 1] = st.slot_pin[i]
    a[#a + 1] = st.slot_deg[i]
    a[#a + 1] = st.slot_shape[i]
  end
  for _, k in ipairs(R.LATER) do a[#a + 1] = st[k] end
  for i = 1, R.STEPS do
    a[#a + 1] = st.target[i]
    a[#a + 1] = st.flag[i]
    a[#a + 1] = st.disp[i]
  end
  st.dirty = false
  return { "save", "melody", a }
end

-- Added after the first lines were saved: a line without them still loads, with these as they stand.
R.LATER = { "style", "v-main", "v-color", "pedal", "bass", "arrive", "octave" }
local LINE = #R.ORDER + 4 * R.STEPS + (1 + R.MAX_NOTES + 4) * R.SLOTS

-- A section's melody and chords, on its step 1: both loops start again from there. A line that isn't
-- this shape keeps what is playing, and puts that back.
function R.restore(st, atoms)
  if #atoms < LINE or #atoms > LINE + #R.LATER + 3 * R.STEPS then return { R.save(st) } end
  local p = 0
  local function take()
    p = p + 1
    return num(atoms[p])
  end
  for _, k in ipairs(R.ORDER) do st[k] = take() end
  for i = 1, R.STEPS do
    st.note[i], st.vel[i], st.gate[i], st.pin[i] = take(), take(), take(), take()
  end
  for i = 1, R.SLOTS do
    local n, list = take(), {}
    for j = 1, R.MAX_NOTES do
      local t = take()
      if j <= n then list[j] = t end
    end
    st.slot[i] = list
    st.slot_start[i], st.slot_pin[i], st.slot_deg[i], st.slot_shape[i] = take(), take(), take(), take()
  end
  for _, k in ipairs(R.LATER) do
    if p < #atoms then st[k] = take() end
  end
  if p < #atoms then
    for i = 1, R.STEPS do st.target[i], st.flag[i], st.disp[i] = take(), take(), take() end
  else
    st.plan_due = true
  end
  st.pos, st.ch_pos, st.bar, st.dirty = 0, 0, 0, false
  tune(st)
  rescale(st)
  -- A section with empty slots has them rolled, so the phone has chords to show, without marking it changed.
  queue_empty(st)
  st.show_notes = true
  if #st.sounding == 0 then hear(st, {}) end
  if st.plan_due then
    st.plan_due = false
    plan_melody(st)
  end
  queue_melody(st)
  st.quiet, st.dirty = #st.to_roll + #st.to_roll_m > 0, false
  return waves(st, {})
end

-- ---------------------------------------------------------------------- what reaches it

-- A control's new value: its row on the screen, and the song store, held by the face.
local function assign(st, name, v)
  local out = { { "disp", name, { v } } }
  if st[name] ~= v then
    st[name] = v
    if name == "chords" then queue_empty(st) end
    if name == "span" then rescale(st) end
    if name == "tension" then roll_vocab(st) end
    if name == "leap" or name == "range" or name == "loop" then
      plan_melody(st)
      queue_melody(st)
      st.show_notes = true
    end
    out[2] = R.save(st)
  end
  return out
end

-- A control from the map, 0 to 1.
local function control(name)
  local scale = SCALE[name] or function(v) return math.floor(v * 100 + 0.5) end
  return function(st, atoms)
    return assign(st, name, scale(num(atoms[1])))
  end
end

local function set_voice(st, name, v)
  v = math.max(1, math.min(#R.VOICES, math.floor(v)))
  if st[name] == v then return {} end
  st[name] = v
  local out = { { "disp", "voice", { R.VOICES[v] } } }
  waves(st, out)
  if name == "voice-h" and #st.sounding > 0 then change_to(st, st.sounding, out) end
  out[#out + 1] = R.save(st)
  return out
end

-- A new key: the chords and the melody move with it, the shortest way, and what the chords are stays
-- the same.
local function set_key(st, v)
  v = math.max(1, math.min(#R.KEYS, math.floor(v)))
  if v == st.key then return {} end
  local delta = (v - st.key + 6) % 12 - 6
  st.key = v
  tune(st)
  for i = 1, R.SLOTS do
    for j, n in ipairs(st.slot[i]) do
      st.slot[i][j] = j == 1 and into(n + delta, R.MIDDLE - 15, R.MIDDLE - 4)
                      or into(n + delta, R.MIDDLE - 2, R.MIDDLE + 12)
    end
  end
  for i = 1, R.STEPS do
    if st.note[i] > 0 then st.note[i] = st.note[i] + delta end
  end
  st.show_notes = true
  local out = { { "disp", "key", { R.KEYS[v] } } }
  local at = st.ch_pos > 0 and st.slot[st.ch_pos] or {}
  if #st.sounding > 0 then change_to(st, at, out) else hear(st, {}) end
  out[#out + 1] = R.save(st)
  return out
end

-- A new mode: the chords are rolled again, pinned ones too, since they may not be in it, and melody
-- notes outside it move to the nearest that is.
local function set_mode(st, v)
  v = math.max(1, math.min(#R.MODES, math.floor(v)))
  if v == st.mode then return {} end
  st.mode = v
  tune(st)
  for i = 1, R.SLOTS do
    st.slot[i], st.slot_pin[i], st.slot_deg[i], st.slot_shape[i] = {}, 0, 0, 0
  end
  for i = 1, R.STEPS do
    local n = st.note[i]
    if n > 0 and not st.in_scale[n % 12] then
      st.note[i] = st.in_scale[(n - 1) % 12] and n - 1 or n + 1
    end
  end
  queue_empty(st)
  hear(st, {})
  st.show_notes = true
  return { { "disp", "mode", { R.MODES[v][1] } }, R.save(st) }
end

-- A control from the phone: set <name> <value>, as it stands.
local KNOWN = { arrive = true, octave = true }
for _, name in ipairs(R.ORDER) do KNOWN[name] = true end

local function set(st, atoms)
  local name, v = atoms[1], num(atoms[2])
  if name == "voice-h" or name == "voice-m" then return set_voice(st, name, v) end
  if name == "key" then return set_key(st, v) end
  if name == "mode" then return set_mode(st, v) end
  if not KNOWN[name] then return { R.fail("bad-control") } end
  return assign(st, name, v)
end

-- What the phone shows: the chords' controls, the slot sounding, whether each part is on, the key and
-- mode, the grid's length and the pattern's last step, each slot's name, spelling, Roman numeral and
-- start, the two voices, then the melody's controls.
function R.phone(st)
  local a = { st.chords, st["chord-lock"], st.smooth, st.tension, st.home, st.span,
              st.audition or st.ch_pos, st["on-h"], st["on-m"], st.key, st.mode, st.total, st.last }
  for i = 1, R.SLOTS do
    local c = chord_of(st, i)
    a[#a + 1] = c and c.name or "-"
    a[#a + 1] = c and c.spell or "-"
    a[#a + 1] = c and c.roman or "-"
    a[#a + 1] = i <= st.chords and st.slot_start[i] or -1
  end
  for _, k in ipairs({ "voice-h", "voice-m", "lock", "fit", "leap", "notes", "length", "echo", "loop",
                       "range", "style", "bass", "arrive", "octave" }) do
    a[#a + 1] = st[k]
  end
  for i = 1, R.SLOTS do a[#a + 1] = st.slot_pin[i] end
  return a
end

-- What the phone's melody grid shows: the loop's length, the tonic, the mode's notes, each step's note (0 a
-- rest, -1 not rolled), and each step's flag plus 4 if it is pinned.
function R.phone_notes(st)
  local a = { st.loop, st.tonic }
  for d = 1, 7 do a[#a + 1] = st.scale[d] end
  for i = 1, R.STEPS do a[#a + 1] = st.note[i] end
  for i = 1, R.STEPS do a[#a + 1] = st.flag[i] + 4 * st.pin[i] end
  return a
end

-- Hand edits on the melody grid. A step edited is pinned: drift and roll leave it until pins are cleared
-- (Brendan, 2026-11-05).
local function step_at(atoms, k)
  local i = math.floor(num(atoms[k]))
  if i < 1 or i > R.STEPS then return nil end
  return i
end

-- note-set <step> <note>: that step is this note.
local function note_set(st, atoms)
  local i, n = step_at(atoms, 1), math.floor(num(atoms[2]))
  if not i then return { R.fail("bad-step") } end
  st.note[i], st.disp[i], st.pin[i] = n, 0, 1
  if st.vel[i] == 0 then st.vel[i], st.gate[i] = 90, 100 end
  if st.flag[i] == R.BREATH then st.flag[i] = R.NORMAL end
  st.show_notes = true
  return { R.save(st) }
end

-- note-move <from> <to> <note>: a note dragged to another step, its velocity, length and whether it is an
-- arrival going with it. The step it left is free to be rolled again as a rest.
local function note_move(st, atoms)
  local a, b, n = step_at(atoms, 1), step_at(atoms, 2), math.floor(num(atoms[3]))
  if not a or not b then return { R.fail("bad-step") } end
  st.note[b], st.vel[b], st.gate[b], st.flag[b] = n, st.vel[a], st.gate[a], st.flag[a]
  st.disp[b], st.pin[b] = 0, 1
  if st.vel[b] == 0 then st.vel[b], st.gate[b] = 90, 100 end
  if a ~= b then
    st.note[a], st.vel[a], st.gate[a], st.flag[a], st.disp[a], st.pin[a] = R.REST, 0, 0, R.NORMAL, 0, 0
  end
  st.show_notes = true
  return { R.save(st) }
end

-- note-rest <step>: a note tapped away. The rest is pinned too, so nothing fills it.
local function note_rest(st, atoms)
  local i = step_at(atoms, 1)
  if not i then return { R.fail("bad-step") } end
  st.note[i], st.vel[i], st.gate[i], st.disp[i], st.pin[i] = R.REST, 0, 0, 0, 1
  st.show_notes = true
  return { R.save(st) }
end

-- note-hear <note> <1 or 0>: a note under a finger, on the melody's voice.
local function note_hear(st, atoms)
  local n, down = math.floor(num(atoms[1])), num(atoms[2])
  local to = st["voice-m"] >= R.FIRST_PD and R.MONO_M or st["voice-m"]
  return { { "play", "list", { to, n, down > 0 and 90 or 0, 0 } } }
end

-- pins-clear, a press: every step is free again.
local function pins_clear(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  for i = 1, R.STEPS do st.pin[i] = 0 end
  st.show_notes = true
  return { R.save(st) }
end

-- A key from the nanoKEY. While a chord's box is held, the keys held together are that chord, sounding at
-- once and pinned (2026-11-06): the first press with none down starts it. It is named if the mode knows it.
-- With no box held, keys are c_synth's alone.
function R.key(st, note, velocity)
  if num(velocity) == 0 then
    st.down = math.max(0, (st.down or 0) - 1)
    return {}
  end
  local i = st.audition
  if not i then return {} end
  local list = (st.down or 0) == 0 and {} or st.slot[i]
  st.down = (st.down or 0) + 1
  if #list < R.MAX_NOTES then list[#list + 1] = math.floor(num(note)) end
  table.sort(list)
  st.slot[i], st.slot_pin[i], st.wrote = list, 1, true
  st.slot_deg[i], st.slot_shape[i] = 0, 0
  local have = {}
  local count = 0
  for _, n in ipairs(list) do
    if not have[n % 12] then have[n % 12], count = true, count + 1 end
  end
  for _, c in ipairs(st.candidates) do
    if #c.pcs == count then
      local all = true
      for _, pc in ipairs(c.pcs) do all = all and have[pc] end
      if all and c.root == list[1] % 12 then
        st.slot_deg[i], st.slot_shape[i] = c.deg, c.shape
        break
      end
    end
  end
  local out = {}
  change_to(st, list, out)
  out[#out + 1] = R.save(st)
  return out
end

-- chord-pin <slot>, a finger left on a box: pinned or unpinned, and left alone by drift and roll while
-- pinned. Not after keys were played into it, which pinned it already.
local function chord_pin(st, atoms)
  local i = math.floor(num(atoms[1]))
  if i < 1 or i > R.SLOTS then return { R.fail("bad-slot") } end
  if st.wrote then return {} end
  st.slot_pin[i] = 1 - st.slot_pin[i]
  return { R.save(st) }
end

-- A part's on button, from the phone or a pad's press. On, it plays whenever the transport runs, and
-- starts the transport if it isn't running: the one thing that starts it. Off, the chords let go.
local function toggle(name)
  return function(st, atoms)
    if num(atoms[1]) == 0 then return {} end
    st[name] = 1 - st[name]
    local out = {}
    if st[name] == 1 then
      if name == "on-h" then queue_empty(st) end
      if not st.running then out[1] = { "start", "bang", {} } end
    elseif name == "on-h" and not st.audition then
      change_to(st, {}, out)
    end
    out[#out + 1] = R.save(st)
    return out
  end
end

-- A chord pad's finger on the phone: audition <slot> <1 or 0>. Down, the slot's chord sounds at once,
-- rolled if empty. Up, the loop's chord comes back if the loop is playing, else silence.
local function audition(st, atoms)
  local i, down = math.floor(num(atoms[1])), num(atoms[2])
  if i < 1 or i > R.SLOTS then return { R.fail("bad-slot") } end
  local out = {}
  if down > 0 then
    if #st.slot[i] == 0 then roll_chord(st, i) end
    st.audition, st.down, st.wrote = i, 0, false
    change_to(st, st.slot[i], out)
    return out
  end
  if st.audition ~= i then return out end
  st.audition = nil
  if st.running and st["on-h"] == 1 and st.ch_pos > 0 then
    change_to(st, st.slot[st.ch_pos], out)
  else
    change_to(st, {}, out)
  end
  return out
end

-- A chord moved on the phone's grid: move <slot> <start>. It stays where it's put, and the order follows;
-- dropped exactly on another chord's start, the two swap places, each keeping the other's start.
local function move(st, atoms)
  local i, t = math.floor(num(atoms[1])), math.floor(num(atoms[2]))
  if i < 1 or i > st.chords then return { R.fail("bad-slot") } end
  t = math.max(0, math.min(st.total - 1, t))
  local was = st.slot_start[i]
  if was == t then return {} end
  for other = 1, st.chords do
    if other ~= i and st.slot_start[other] == t then st.slot_start[other] = was end
  end
  st.slot_start[i] = t
  return { R.save(st) }
end

-- The pattern's last step, from c_steps, when it changes.
local function set_last(st, atoms)
  local n = math.max(1, math.floor(num(atoms[1])))
  if n == st.last then return {} end
  st.last = n
  rescale(st)
  return {}
end

-- The roll pads' presses: everything not pinned is rolled again, the chords' at once, one at a time, so
-- their names show, and the melody's as each step comes round. A new rhythm keeps the chords.
local function roll_rhythm_pad(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  roll_rhythm(st)
  queue_empty(st)
  return { { "disp", "roll", { "rhythm" } }, R.save(st) }
end

local function roll_melody(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  for i = 1, R.STEPS do
    if st.pin[i] == 0 then st.note[i], st.disp[i] = R.UNROLLED, 0 end
  end
  plan_melody(st)
  queue_melody(st)
  st.dirty, st.show_notes = true, true
  return { { "disp", "roll", { "melody" } } }
end

local function roll_chords(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  -- With a chord's box held, just that one: unpinned and rolled anew, and heard at once.
  if st.audition then
    local i = st.audition
    st.slot_pin[i] = 0
    roll_chord(st, i)
    local out = {}
    change_to(st, st.slot[i], out)
    out[#out + 1] = R.save(st)
    return out
  end
  for i = 1, R.SLOTS do
    if st.slot_pin[i] == 0 then
      st.slot[i], st.slot_deg[i], st.slot_shape[i] = {}, 0, 0
    end
  end
  roll_vocab(st)
  queue_empty(st)
  st.dirty = true
  return { { "disp", "roll", { "chords" } } }
end

-- Bass only, a press: the chord sounding changes at once.
local function flip_bass(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  st.bass = 1 - st.bass
  local out = {}
  if #st.sounding > 0 then change_to(st, st.sounding, out) end
  out[#out + 1] = R.save(st)
  return out
end

-- Modal or functional, a press: the chords are rolled again in it, so it's heard at once.
local function flip_style(st, atoms)
  if num(atoms[1]) == 0 then return {} end
  st.style = st.style == 1 and 2 or 1
  local out = roll_chords(st, { 1 })
  out[1] = { "disp", "style", { R.STYLES[st.style] } }
  out[2] = R.save(st)
  return out
end

R.inputs = {
  list = function(st, a) return R.key(st, a[1], a[2]) end,
  step = R.step,
  set = set,
  audition = audition,
  move = move,
  last = set_last,
  ["roll-rhythm"] = roll_rhythm_pad,
  ["note-set"] = note_set,
  ["note-move"] = note_move,
  ["note-rest"] = note_rest,
  ["note-hear"] = note_hear,
  ["pins-clear"] = pins_clear,
  ["chord-pin"] = chord_pin,
  style = flip_style,
  bass = flip_bass,
  ["roll-melody"] = roll_melody,
  ["roll-chords"] = roll_chords,
  ["on-h"] = toggle("on-h"),
  ["on-m"] = toggle("on-m"),
}
R.inputs.arrive, R.inputs.octave = control("arrive"), control("octave")
for _, name in ipairs(R.ORDER) do
  if not R.inputs[name] and name ~= "voice-h" and name ~= "voice-m" and name ~= "key"
     and name ~= "mode" and name ~= "total" then
    R.inputs[name] = control(name)
  end
end

-- PLAY: both loops start again from their beginnings on the next step, and what played is forgotten.
local function start(st)
  st.running = true
  st.pos, st.ch_pos, st.bar, st.hist = 0, 0, 0, {}
  return {}
end

-- STOP and panic: the same, and the chord lets go.
local function stop(st)
  local out = {}
  st.audition = nil
  change_to(st, {}, out)
  start(st)
  st.running = false
  out[#out + 1] = { "here", "here", { -1, -1 } }
  return out
end

-- At load the first chords are rolled, so the phone has them to show, without marking the song changed.
local function boot(st)
  queue_empty(st)
  plan_melody(st)
  queue_melody(st)
  st.quiet, st.dirty, st.show_notes = true, false, true
  return waves(st, {})
end

R.internal = {
  restore = function(st, a) return R.restore(st, a) end,
  start = start,
  stop = stop,
  init = boot,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_melody", string.sub(text, 1, 21) } }
end

return R
