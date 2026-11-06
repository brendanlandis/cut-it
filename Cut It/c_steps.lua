-- c_steps.lua -- the drum sequencer's rules: the pattern, the step rule, the velocity levels, the
-- selected track and level, the last steps, each track's place in its loop, the time signature,
-- swing, drunkenness, the repeats, each track's randomness, volume and pitch, each track's
-- effects and the reverb's, each track's mute and solo, and which notes fire on a step. Plain
-- Lua with no Pd in it, so test/gate/lua/c_steps_test.lua runs it on the Mac with
-- lua.org's interpreter. c_steps-lua.pd_lua is its Pd face, and c_steps.pd keeps the clock, the
-- transport and the cords to c_kit, g_grid and u_state. ref/module/sequencer.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the pattern. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"note", "pad", {pad, velocity}}                          to c_kit
--   {"note", "vol" | "pitch", {pad, dB or semitones}}         to c_kit, a track's
--   {"note", <effect>, {pad, value} or {value}}               to c_kit, an effect's (R.FX)
--   {"note", "tape", {span, units}} and {"note", "tape-off", {}}
--                                                             to c_kit: a held repeat's tails (R.tape)
--   {"note", "rush", {span, hz}}, "rush-rate" {hz}, "rush-mix" {loop, sine}, "rush-back" {},
--   "rush-off" {} and "tape-run" {1 or 0}                     to c_kit: rush's loop (R.rush)
--   {"page", "steps" | "play" | "vel" | "track" | "last" | "bar" | "rep" | "quiet" | "fast"
--    | "recall", {...}}                                       to g_grid's third inlet
--   {"save", "list", {581, 711, 743, 759, 760 or 776 numbers, R.save}}
--                                                             to the state bus, put section <part>
--   {"clock", "restart", {}}                                 to the start bus, the saved tempo's press
--   {"clock", "swing" | "rate", {x}}                          to c_steps.pd's step clock
--   {"clock", "ticks", {1 or 0}}                              whether its steps reach R.tick
--   {"clock", "place", {phase}}                               its phase set, and its steps let through
--   {"bar", "bar", {}}                                        to u_song: the pattern's loop ends
--   {"song", "recall", {key}}                                 to u_song: a part's saved value
--   {"tempo", "fast", {1 or 0}}                               to u_tempo: the 500 BPM repeat
--   {"err", "fail", {"c_steps", text}}                        to err (C-12)
--   {"disp", <row name>, {value[, unit]}}                     a knob's row, to disp
-- and R.phone(st), the phone's state, which the Pd face sends to u_net when it changes.

local R = {}

R.TRACKS, R.STEPS, R.LEVELS = 16, 32, 8
-- At load: level 6 (95), track 1, and a last step of 16 that both knobs are held at until they
-- are turned through it (Brendan, 2026-11-03), so nothing jumps to where a knob happens to sit.
R.BOOT_LEVEL, R.BOOT_TRACK, R.BOOT_LAST = 6, 1, 16
-- Swing: 50% to 75%, straight at its bottom and swinging one way only (Brendan,
-- 2026-11-05), starting at 50% held like knobs 2 and 3 (2026-11-03). The share of a pair of
-- sixteenths the first one takes.
R.SWING_MIN, R.SWING_MAX = 50, 75
R.BOOT_SWING = 50
-- u_tempo's fallback, until the tempo bus says otherwise.
R.BOOT_BPM = 120
-- The time signature's bottom numbers. The bottom number is a matter of record only: it changes
-- neither the page nor how fast the steps go (Brendan, 2026-11-05).
R.DENS = { 1, 2, 4, 8, 16 }
R.MAX_NUM = 32
-- The drum page's steps are four rows of eight cells, as the layout table numbers its step cells,
-- 1 to 8 along the top row, 9 to 16 along the next. The top number N sets how many of a row's
-- cells hold steps: as many groups of N as fit in 8, so 3/4 and 6/8 give rows of 6 and 5/4 rows
-- of 5, and all 8 when N is over 8. The pattern reaches four rows' worth: 24 steps at 3/4, 32 at
-- 4/4 (Brendan, 2026-11-05).
R.ROW, R.ROWS = 8, 4
-- Drunk, at the slider's top every step strays, by up to two steps longer or shorter, and low
-- settings stay subtle (Brendan, 2026-11-05). At x, the slider's 0 to 1, a step strays with the
-- chance x/3 + 2x^4/3, by up to x + x^4 steps: a line, a third of the steps by up to the slider's
-- share of a step, which is most of it low, plus a steep x^4 that adds the rest near the top. At
-- 20% one step in fifteen strays, by up to a fifth of a step; at 50% one in five, by up to 0.56;
-- at 90% three in four, by up to 1.56.
R.DRUNK_STEEP = 4
function R.drunk_chance(drunk)
  local x = drunk / 100
  return x / 3 + 2 * x ^ R.DRUNK_STEEP / 3
end
function R.drunk_reach(drunk)
  local x = drunk / 100
  return x + x ^ R.DRUNK_STEEP
end
-- The shortest a drunk step gets, as a share of a step: a step two steps shorter would be less
-- than nothing, and a step of nothing would be two at once.
R.MIN_DUR = 0.125
-- The repeat pads, 1 to 4: each replays the last 1, 2, 3 or 4 steps (Brendan, 2026-11-03),
-- exactly as they were played, randomness and drunkenness included (2026-11-05).
R.REPEATS = 4
-- A held repeat's tails (Brendan, 2026-11-05): c_kit's e_tape keeps the last while of the wet sound
-- and loops the last N steps of it while a repeat is held. It holds this much, in ms, a little
-- less than e_tape's line: four steps at the legal tempo's slowest, 5 BPM. A longer repeat, only
-- ever a very drunk one down there, plays the last R.TAPE_MAX in the time its steps take.
R.TAPE_MAX = 12000
-- Rush's loop (Brendan, 2026-11-05): e_rush records the kit's whole output, and past u_tempo's
-- handoff freezes and loops the last steps of it. It holds a little more than this much, in ms: 32
-- steps at 640 BPM, far more than the 480 ms of them at 1000 BPM it is for; a knob thrown from a slow
-- tempo gets the last of what ran. The rest of the turn takes the loop from speed 1 to R.RUSH_HZ.
R.RUSH_MAX, R.RUSH_HZ = 3000, 22000
-- How the top vanishes (Brendan, 2026-11-05: "Shouldn't it be inaudible by the time it gets to 22khz?
-- It still sounds really buzzy."): the raw loop up to R.RUSH_RAW; from there to R.RUSH_PURE it crosses
-- to a sine at its frequency, as loud as it was; from there to R.RUSH_HZ the sine fades to nothing.
R.RUSH_RAW, R.RUSH_PURE = 8000, 16000
-- A hand-back's next step is at least this far off, in ms, so the step clock's ticks are back on by
-- then (c_steps.pd).
R.RUSH_LAND = 5
-- Each track's own volume, in dB, and pitch, in semitones, played by its c_voice; and its
-- randomness, 0 to 100 (Brendan, 2026-11-05).
R.VOL_MIN, R.VOL_MAX = -30, 6
R.PITCH_MIN, R.PITCH_MAX = -12, 12
-- Each track's effects (Brendan, 2026-11-05), c_kit's to play: a distortion, its drive, its tone
-- and its mix; a delay, its time a note value and a feel, its feedback and its level; its send
-- to the one reverb, whose size and damping are the kit's; and the distortion's character. Each
-- is 0 to 100 but the note, the feel and the character, places in R.NOTES, R.FEELS and R.CHARS.
-- In the order the phone gets them, each with its range and what a track starts at: a mix, a
-- level or a send of 0 is off, and c_kit switches that effect's DSP off, so a pattern saved
-- before the effects loads with them off and costs nothing. The tone starts open (Brendan,
-- 2026-11-05: 60, a 3.5 kHz low-pass, dulled every drum), and the character soft.
R.FX = { { "drive", 0, 100, 50 }, { "tone", 0, 100, 100 }, { "dist", 0, 100, 0 },
         { "note", 1, 5, 3 }, { "feel", 1, 3, 1 }, { "feedback", 0, 100, 40 },
         { "delay", 0, 100, 0 }, { "send", 0, 100, 0 }, { "char", 1, 4, 1 } }
R.VERB = { { "size", 0, 100, 50 }, { "damping", 0, 100, 50 } }
-- R.save writes the first R.FX_BLOCK of them after the pattern's 581 numbers, as it did before
-- the distortion had a character; the rest, the character, after the mutes and solos, so a line
-- saved before it loads as it was, every track soft.
R.FX_BLOCK = 8
-- The distortion's characters (Brendan, 2026-11-05): e_drive's curve at char 1 to 4. The phone
-- shows their names.
R.CHARS = { "soft", "hard", "fold", "crush" }
-- The reverb's type (Brendan, 2026-11-05): which of its three engines plays, 0 to 2, the kit's, as
-- its size and damping are. Plate, 0, at first, so a pattern saved before the type loads as one.
R.VERB_TYPES = { "plate", "gigaverb", "freeverb" }
-- The delay's times, counted in note values with triplets and dotted ones (Brendan, 2026-11-05):
-- each note value in steps, a step a sixteenth, so the delay follows the tempo; and each feel's
-- share of it. The phone shows their names.
R.NOTES = { 8, 4, 2, 1, 0.5 }
R.NOTE_NAMES = { "1/2", "1/4", "1/8", "1/16", "1/32" }
R.FEELS = { 1, 2 / 3, 3 / 2 }
R.FEEL_NAMES = { "straight", "triplet", "dotted" }
-- What R.save writes, in order, with each track's character; what it writes with the mutes and
-- solos, with the effects, and with none of them; what it wrote until the song
-- store, without the swing and the global last step, which a section holds since
-- (cut-it/songs-and-sections); and what it wrote until 2026-11-05, when each track had a skip and
-- a move chance where its randomness and its volume are now, and no pitch.
R.SAVED_FXLESS = R.TRACKS * R.STEPS + 4 * R.TRACKS + 5
R.SAVED_FX = R.SAVED_FXLESS + R.FX_BLOCK * R.TRACKS + #R.VERB
R.SAVED_FLAGS = R.SAVED_FX + 2 * R.TRACKS
R.SAVED = R.SAVED_FLAGS + (#R.FX - R.FX_BLOCK) * R.TRACKS
R.SAVED_TYPED = R.SAVED + 1
R.SAVED_ROLLED = R.SAVED_TYPED + R.TRACKS
R.SAVED_SECTIONLESS = R.TRACKS * R.STEPS + 4 * R.TRACKS + 3
R.SAVED_CHANCES = R.TRACKS * R.STEPS + 3 * R.TRACKS + 3

local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A number from a message, as Pd's [f] reads one: a symbol is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- Level n's velocity: 127n/8, rounded. 16 at 1, 127 at 8.
function R.velocity(level)
  return math.floor(127 * level / R.LEVELS + 0.5)
end

-- A velocity's level, whose color its step takes: 0 for off, else (v - 1) div 16 + 1, so each
-- level's own velocity is that level, and a pattern saved at any other velocity looks as it did
-- when g_grid worked this out.
function R.level(velocity)
  if velocity < 1 then return 0 end
  return clip((velocity - 1) // 16 + 1, 1, R.LEVELS)
end

-- The pattern's index of a track's step, both 1-based: track 1's 32 steps come first.
function R.index(track, step)
  return (track - 1) * R.STEPS + step
end

-- A track's pad: track n plays pad n of the bank, 1 for A (pads 1..160 across ten banks, the
-- SP-404's addressing; c_kit plays 1..16, so only bank 1 sounds).
function R.pad(st, track)
  return (st.bank - 1) * R.TRACKS + track
end

-- A row of the drum page, in steps: as many groups of the top number as fit in a row's 8
-- cells, or all 8 when it is over 8.
function R.row(st)
  if st.num > R.ROW then return R.ROW end
  return (R.ROW // st.num) * st.num
end

-- The furthest a last step reaches: four rows' worth, 24 at 3/4, 32 at 4/4.
function R.reach(st)
  return R.ROWS * R.row(st)
end

-- A knob's 0-1 as a last step, 1 to top, 32 unless given: a full turn reaches the last step
-- the time signature allows. At 32, 16 sits just left of noon.
function R.knob_step(v, top)
  return math.floor(clip(num(v), 0, 1) * ((top or R.STEPS) - 1) + 0.5) + 1
end

-- The global last step in force: as set, clipped to the reach. What is set is kept, and saved,
-- so a time signature passed through on the way to another does not cut it short for good.
function R.global_last(st)
  return math.min(st.last, R.reach(st))
end

-- A track's last step: its own, or the global one while it follows that (own is 0), clipped
-- to the reach as the global one is.
function R.last_of(st, track)
  local own = st.own[track]
  return math.min(own >= 1 and own or st.last, R.reach(st))
end

function R.new(bank)
  local st = { bank = math.floor(clip(num(bank), 1, 10)), pattern = {}, own = {}, pos = {},
               track = R.BOOT_TRACK, level = R.BOOT_LEVEL, last = R.BOOT_LAST,
               master = 0, sync = false, snap = false, playing = false,
               num = 4, den = 4, swing = R.BOOT_SWING, drunk = 0, rate = 1,
               randomness = {}, vol = {}, pitch = {}, heard = {}, rolled = {}, hist = {},
               rep = 0, rk = 0, win = {}, rand = math.random,
               bpm = R.BOOT_BPM, pair = 0, pair_swing = R.BOOT_SWING, taping = false, fast = false, ran = {},
               knob = { last = { held = true }, track = { held = true },
                        swing = { held = true } } }
  for i = 1, R.TRACKS * R.STEPS do st.pattern[i] = 0 end
  for t = 1, R.TRACKS do
    st.own[t], st.pos[t] = 0, 0
    st.randomness[t], st.vol[t], st.pitch[t] = 0, 0, 0
    st.heard[t], st.rolled[t] = 0, 0
  end
  -- the effects at their starting points, and what c_kit has been told of them: nothing yet
  st.fx, st.verb, st.told = {}, {}, {}
  for _, f in ipairs(R.FX) do
    st.fx[f[1]] = {}
    for t = 1, R.TRACKS do st.fx[f[1]][t] = f[4] end
  end
  for _, f in ipairs(R.VERB) do st.verb[f[1]] = f[4] end
  st.verb_type = 0
  -- nothing muted or soloed, and the page told so: g_grid starts with every pad sounding
  st.mute, st.solo = {}, {}
  for t = 1, R.TRACKS do st.mute[t], st.solo[t] = 0, 0 end
  st.quiet_told = table.concat(R.page_quiet(st)[3], " ")
  return st
end

-- The selected track's 32 steps as the page shows them: each one's level, 0 for off.
function R.steps(st)
  local row = {}
  for s = 1, R.STEPS do row[s] = R.level(st.pattern[R.index(st.track, s)]) end
  return { "page", "steps", row }
end

-- The selected track's last step, as the page shows it.
function R.page_last(st)
  return { "page", "last", { R.last_of(st, st.track) } }
end

-- The time signature as the page shows it, bar <N> <row>: a blue cell every N steps, N the top
-- number, whatever the subdivision, lit unless a note is; and rows of R.row steps. Over 8, the
-- blue counts straight through the pattern and wraps across the rows (Brendan, 2026-11-05).
function R.page_bar(st)
  return { "page", "bar", { st.num, R.row(st) } }
end

-- A press on the step cell n, 1 to 32, as the layout table numbers them, eight a row: the step
-- its row and column mean, row r and column c (from 0) being step r x R.row + c + 1, or nil
-- for a cell past the row's last step, which is dark.
function R.cell_step(st, n)
  local r, c = (n - 1) // R.ROW, (n - 1) % R.ROW
  if c >= R.row(st) then return nil end
  return r * R.row(st) + c + 1
end

-- The whole pattern, zeros included: 512 velocities, then the 16 tracks' own last steps, 0 for
-- one that follows the global last step, then their randomness, 0 to 100, their volumes in dB and
-- their pitches in semitones, then the time signature, the drunkenness, 0 to 100, the swing, 50 to
-- 75, and the global last step, 581 numbers; then, once any effect is off its starting point,
-- each of R.FX's first R.FX_BLOCK for every track, track 1 first, and the reverb's size and
-- damping: 711; then, once any track is muted or soloed, the sixteen mutes and the sixteen solos,
-- 1 or 0, the effects written as they stand whether moved or not: 743; then, once any track's
-- distortion is not soft, the sixteen characters, 1 to 4, the effects, the mutes and the solos
-- written as they stand: 759; then, once the reverb's type is not the plate, the type, 0 to 2,
-- everything before it written as it stands: 760; then, once any track's random pitch is on, the
-- sixteen flags, 1 or 0, everything before them written as it stands: 776.
-- While every effect is at its starting point and nothing is muted or soloed, the line stays 581,
-- as it was saved before the effects, so a song saved before them restores and is put back as it
-- was, not as a change to save, and an unused effect costs the put nothing; while nothing is
-- muted or soloed, 711 or 581, so a song saved before mute and solo does the same; and while every
-- track is soft, 743, 711 or 581, as a song saved before the characters. What a section holds of
-- the drums and the arrangement page (Brendan, 2026-11-04), its effects with them, and its mutes
-- and solos and its characters (2026-11-05), put as the section's <part> (ref/module/songs.md).
function R.save(st)
  local all, cells = {}, R.TRACKS * R.STEPS
  for i = 1, cells do all[i] = st.pattern[i] end
  for t = 1, R.TRACKS do
    all[cells + t] = st.own[t]
    all[cells + R.TRACKS + t] = st.randomness[t]
    all[cells + 2 * R.TRACKS + t] = st.vol[t]
    all[cells + 3 * R.TRACKS + t] = st.pitch[t]
  end
  local n = cells + 4 * R.TRACKS
  all[n + 1], all[n + 2], all[n + 3] = st.num, st.den, st.drunk
  all[n + 4], all[n + 5] = st.swing, st.last
  -- The kit's sound is the song's (R.kit_line), so a section's line holds its pattern, and a mute or solo.
  if st.kit_on then
    for t = 1, R.TRACKS do
      all[cells + 2 * R.TRACKS + t], all[cells + 3 * R.TRACKS + t] = 0, 0
    end
    if not R.flagged(st) then return { "save", "list", all } end
    local k = R.SAVED_FXLESS
    for i = 1, R.FX_BLOCK do
      for _ = 1, R.TRACKS do k = k + 1; all[k] = R.FX[i][4] end
    end
    for _, f in ipairs(R.VERB) do k = k + 1; all[k] = f[4] end
    for t = 1, R.TRACKS do all[k + t], all[k + R.TRACKS + t] = st.mute[t], st.solo[t] end
    return { "save", "list", all }
  end
  local rolled = R.any_rolled(st)
  local flagged, late, typed = R.flagged(st), R.late_moved(st), st.verb_type ~= 0 or rolled
  if not flagged and not typed and not R.fx_moved(st) then return { "save", "list", all } end
  local k = R.SAVED_FXLESS
  for i = 1, R.FX_BLOCK do
    for t = 1, R.TRACKS do k = k + 1; all[k] = st.fx[R.FX[i][1]][t] end
  end
  for _, f in ipairs(R.VERB) do k = k + 1; all[k] = st.verb[f[1]] end
  if not flagged and not late and not typed then return { "save", "list", all } end
  for t = 1, R.TRACKS do all[k + t], all[k + R.TRACKS + t] = st.mute[t], st.solo[t] end
  if not late and not typed then return { "save", "list", all } end
  k = R.SAVED_FLAGS
  for i = R.FX_BLOCK + 1, #R.FX do
    for t = 1, R.TRACKS do k = k + 1; all[k] = st.fx[R.FX[i][1]][t] end
  end
  if not typed then return { "save", "list", all } end
  all[R.SAVED_TYPED] = st.verb_type
  if not rolled then return { "save", "list", all } end
  for t = 1, R.TRACKS do all[R.SAVED_TYPED + t] = st.rolled[t] end
  return { "save", "list", all }
end

-- Whether any track's random pitch is on.
function R.any_rolled(st)
  for t = 1, R.TRACKS do if st.rolled[t] ~= 0 then return true end end
  return false
end

-- Whether any of the effects saved after the mutes and solos, the characters, is off its
-- starting point.
function R.late_moved(st)
  for i = R.FX_BLOCK + 1, #R.FX do
    local f = R.FX[i]
    for t = 1, R.TRACKS do if st.fx[f[1]][t] ~= f[4] then return true end end
  end
  return false
end

-- Whether any track is muted or soloed.
function R.flagged(st)
  for t = 1, R.TRACKS do
    if st.mute[t] ~= 0 or st.solo[t] ~= 0 then return true end
  end
  return false
end

-- Mute and solo (Brendan, 2026-11-05): with any track soloed, only the soloed tracks play and
-- the mutes are ignored; otherwise a muted track doesn't play. A track that won't play is quiet.
-- solo: whether any track is soloed, worked out once a step by the caller, or here if not given.
function R.any_solo(st)
  for t = 1, R.TRACKS do if st.solo[t] ~= 0 then return true end end
  return false
end

function R.sounds(st, t, solo)
  if solo == nil then solo = R.any_solo(st) end
  if solo then return st.solo[t] ~= 0 end
  return st.mute[t] == 0
end

-- The page's quiet pads, quiet <16 flags>, track 1 first: 1 for a track that won't play, which
-- the Launchpad shows dim.
function R.page_quiet(st)
  local solo, q = R.any_solo(st), {}
  for t = 1, R.TRACKS do q[t] = R.sounds(st, t, solo) and 0 or 1 end
  return { "page", "quiet", q }
end

-- The page told its quiet pads, unless they are what it was told last: a mute while another
-- track is soloed changes no pad, and a restore that changes no pad sends none.
local function tell_quiet(st, out)
  local e = R.page_quiet(st)
  local key = table.concat(e[3], " ")
  if key == st.quiet_told then return end
  st.quiet_told = key
  out[#out + 1] = e
end

-- Whether any effect, a track's or the reverb's, is off its starting point.
function R.fx_moved(st)
  for _, f in ipairs(R.FX) do
    for t = 1, R.TRACKS do if st.fx[f[1]][t] ~= f[4] then return true end end
  end
  for _, f in ipairs(R.VERB) do if st.verb[f[1]] ~= f[4] then return true end end
  return false
end

-- At load: the page's selection, before anything is pressed, and the step clock straight; the
-- pattern, put, so the section playing holds the drums from the start (ref/module/songs.md); and
-- every effect's value to c_kit, which sets none of its own at load (R.tell_fx).
function R.boot(st)
  local out = { { "page", "vel", { st.level } }, { "page", "track", { st.track } },
                R.page_last(st), R.steps(st), R.page_bar(st), { "page", "rep", { st.rep } },
                { "clock", "swing", { st.swing / 100 } }, { "clock", "rate", { st.rate } },
                R.save(st) }
  for _, e in ipairs(R.tell_fx(st)) do out[#out + 1] = e end
  return out
end

-- A step press, on the selected track, on a step cell (R.cell_step). The step rule: off takes
-- the selected velocity; on, at any velocity, turns off. A cell past its row's last step, or a
-- step past the track's last step, is dark, and a press there does nothing.
function R.press_step(st, cell)
  local s = R.cell_step(st, math.floor(clip(num(cell), 1, R.STEPS)))
  if not s or s > R.last_of(st, st.track) then return {} end
  local i = R.index(st.track, s)
  if st.pattern[i] >= 1 then st.pattern[i] = 0 else st.pattern[i] = R.velocity(st.level) end
  return { R.save(st), R.steps(st) }
end

-- A velocity press selects its level. It plays nothing and changes no step.
function R.press_vel(st, level)
  st.level = clip(num(level), 1, R.LEVELS)
  return { { "page", "vel", { st.level } } }
end

-- A knob's latch: held until its step reaches or passes the one it stands for, so a knob that
-- sits elsewhere never jumps the value. The first held step decides the side it waits on.
-- -> true if the knob is live.
local function latch(k, n, cur)
  if not k.held then return true end
  local side = n < cur and "below" or "above"
  if n == cur or (k.side and k.side ~= side) then
    k.held, k.side = false, nil
    return true
  end
  k.side = side
  return false
end

-- Hold a knob again, against whatever it now stands for.
local function rearm(k)
  k.held, k.side = true, nil
end

-- A knob's row: the value while live, and the value it is held at with the knob's own step in
-- brackets while held, as u_map's c_mapped draws a held row.
local function row(name, live, value, n)
  if live then return { "disp", name, { value } } end
  return { "disp", name, { value, "(" .. n .. ")" } }
end

local function track_row(st)
  return "pad" .. st.track .. "-last"
end

-- Knob 4: swing, 50% to 75%, the share of each pair of sixteenths the first one takes, straight
-- at 50%, its bottom: above it every second sixteenth comes later (Brendan, 2026-11-05). Saved,
-- as a section's (Brendan, 2026-11-04); it starts at 50% with the knob held there, as knob 2 at
-- 16, and since 50% is the knob's bottom, it is held until turned all the way down. The step
-- clock takes it at the next pair, so a turn never moves a step already cut.
function R.knob_swing(st, v)
  local n = R.SWING_MIN + math.floor(clip(num(v), 0, 1) * (R.SWING_MAX - R.SWING_MIN) + 0.5)
  local live = latch(st.knob.swing, n, st.swing)
  if not live then return { { "disp", "swing", { st.swing, "(" .. n .. ")" } } } end
  local out = { { "disp", "swing", { n, "%" } } }
  if n ~= st.swing then
    st.swing = n
    out[#out + 1] = { "clock", "swing", { n / 100 } }
    out[#out + 1] = R.save(st)
  end
  return out
end

-- Knob 2: the global last step, 1 to the time signature's reach (R.reach), for every track that
-- follows it. Saved, as a section's, and it starts at 16 with the knob held there.
function R.knob_last(st, v)
  local n, cur = R.knob_step(v, R.reach(st)), R.global_last(st)
  local live = latch(st.knob.last, n, cur)
  if not live then return { row("last-step", false, cur, n) } end
  local out = { row("last-step", true, n) }
  if n ~= cur then
    st.last = n
    out[#out + 1] = R.save(st)
  end
  if st.own[st.track] == 0 then
    rearm(st.knob.track)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- The phone's swing and global last step, on the arrangement page (Brendan, 2026-11-04): each a
-- value as it stands, since swing and last are the knobs' positions and pass their latch. The
-- knob that sets the same value is held again at the phone's, so its next turn waits to pass it
-- rather than jumping back to wherever it sits. Both are saved, as the knobs' are; a message
-- with no number in it does nothing.
function R.set_swing(st, v)
  if type(v) ~= "number" then return {} end
  local n = math.floor(clip(v, R.SWING_MIN, R.SWING_MAX) + 0.5)
  if n == st.swing then return {} end
  st.swing = n
  rearm(st.knob.swing)
  return { { "clock", "swing", { n / 100 } }, R.save(st) }
end

function R.set_last(st, v)
  if type(v) ~= "number" then return {} end
  local n = math.floor(clip(v, 1, R.reach(st)) + 0.5)
  if n == R.global_last(st) then return {} end
  st.last = n
  rearm(st.knob.last)
  if st.own[st.track] ~= 0 then return { R.save(st) } end
  rearm(st.knob.track)
  return { R.save(st), R.page_last(st) }
end

-- Knob 3: the selected track's own last step. It is held whenever another track is selected,
-- until turned through that track's last step, and it is saved with the pattern. Released at the
-- step it already has, a track that follows the global one goes on following it.
function R.knob_track(st, v)
  local n, cur = R.knob_step(v, R.reach(st)), R.last_of(st, st.track)
  local live = latch(st.knob.track, n, cur)
  if not live then return { row(track_row(st), false, cur, n) } end
  local out = { row(track_row(st), true, n) }
  if n ~= cur then
    st.own[st.track] = n
    out[#out + 1] = R.save(st)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- The drum screen's "sync first steps": every track back to its step 1 together, the next time
-- the global loop comes round to its own step 1, each keeping its own last step (Brendan,
-- 2026-11-03).
function R.sync(st)
  st.sync = true
  return {}
end

-- The drum screen's "snap to global": the same, and at that same step every track follows the
-- global last step again.
function R.snap(st)
  st.sync, st.snap = true, true
  return {}
end

-- A pending snap, landed: every track on the global last step, saved, and knob 3 held again.
local function land_snap(st)
  st.snap = false
  for t = 1, R.TRACKS do st.own[t] = 0 end
  rearm(st.knob.track)
  return { R.save(st), R.page_last(st) }
end

-- The arrangement screen's time signature, two numbers, each stepped by its box (Brendan,
-- 2026-11-03): the top 1 to 32, the bottom through 1 2 4 8 16, both saved. The top number sets
-- the page's rows and its blue cells, and how far a last step reaches (R.row, R.reach): the
-- selected track's last step goes to the page again, clipped to it, and when the reach moves,
-- knobs 2 and 3 are held again, since a turn of either now stands for another step. The bottom
-- number is a matter of record only: it changes neither the page nor the step clock's rate
-- (Brendan, 2026-11-05).
function R.time(st, which, dir)
  local d = num(dir) < 0 and -1 or 1
  if which ~= "num" then
    local k = 3
    for i, v in ipairs(R.DENS) do if v == st.den then k = i end end
    st.den = R.DENS[clip(k + d, 1, #R.DENS)]
    return { R.save(st) }
  end
  local reach = R.reach(st)
  st.num = clip(st.num + d, 1, R.MAX_NUM)
  if R.reach(st) ~= reach then
    rearm(st.knob.last)
    rearm(st.knob.track)
  end
  return { R.save(st), R.page_bar(st), R.page_last(st) }
end

-- A value within its range, rounded: a percent, 0 to 100, a volume, a pitch, a last step.
local function whole(v, lo, hi)
  return math.floor(clip(num(v), lo, hi) + 0.5)
end

local function percent(v)
  return whole(v, 0, 100)
end

-- The arrangement screen's drunkenness, 0 to 100. Saved.
function R.drunk(st, v)
  st.drunk = percent(v)
  return { R.save(st) }
end

-- The drum screen's pads, each dragged for its own track, selected or not (Brendan, 2026-11-05):
-- a track's volume in dB, its pitch in semitones, its randomness, or its own last step, each as it
-- stands. Saved; a volume or a pitch goes to c_kit too, for the track's next hits. The same value
-- again, or a message without a track and a number, does nothing.
local function track_value(track, v)
  if type(track) ~= "number" or type(v) ~= "number" then return nil end
  return math.floor(clip(track, 1, R.TRACKS))
end

local function set_sound(st, which, lo, hi, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, lo, hi)
  if n == st[which][t] then return {} end
  st[which][t] = n
  if which == "pitch" then st.heard[t] = n end
  st.told[which .. " " .. R.pad(st, t)] = n
  return { R.save(st), { "note", which, { R.pad(st, t), n } } }
end

function R.set_vol(st, track, v)
  return set_sound(st, "vol", R.VOL_MIN, R.VOL_MAX, track, v)
end

function R.set_pitch(st, track, v)
  return set_sound(st, "pitch", R.PITCH_MIN, R.PITCH_MAX, track, v)
end

function R.set_randomness(st, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = percent(v)
  if n == st.randomness[t] then return {} end
  st.randomness[t] = n
  return { R.save(st) }
end

-- A track's own last step, set from its pad as knob 3 sets the selected track's, as far as the
-- time signature reaches: the step it already has changes nothing, so a track that follows the
-- global one goes on following it. Knob 3 is held again when the track is the selected one, as
-- at a phone's value of knob 2's.
function R.set_track_last(st, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, 1, R.reach(st))
  if n == R.last_of(st, t) then return {} end
  st.own[t] = n
  local out = { R.save(st) }
  if t == st.track then
    rearm(st.knob.track)
    out[#out + 1] = R.page_last(st)
  end
  return out
end

-- A track's mute or solo from the drum screen, mute or solo <track> <0 or 1>, each as it stands
-- (Brendan, 2026-11-05): saved, and the page told which pads are quiet when that changes. A mute
-- silences the track's hits from the next step, in R.tick, and nothing else: echoes and reverb
-- already sounding ring out in c_kit, and a press on its pad still plays it, so it can be heard
-- while muted. The same value again, or a message without a track and a number, does nothing.
local function set_flag(st, which, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, 0, 1)
  if n == st[which][t] then return {} end
  st[which][t] = n
  local out = { R.save(st) }
  tell_quiet(st, out)
  return out
end

function R.set_mute(st, track, v)
  return set_flag(st, "mute", track, v)
end

function R.set_solo(st, track, v)
  return set_flag(st, "solo", track, v)
end

-- A track's random pitch from the drum screen, rnd-pitch <track> <0 or 1>, as it stands (Brendan,
-- 2026-11-05): saved. A hit its randomness rolls then takes a pitch of its own (chance), and every
-- other hit the track's set pitch. The same value again, or a message without a track and a
-- number, does nothing.
function R.set_rolled(st, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local n = whole(v, 0, 1)
  if n == st.rolled[t] then return {} end
  st.rolled[t] = n
  return { R.save(st) }
end

local take_window, tape_off, let_go, rush_end

-- A step's share of its pair of sixteenths, as the swing bends it: the first takes the swing's
-- share of the pair and the second the rest, so at 50% each is one step's worth.
local function pair_share(swing, pair)
  local x = swing / 100
  return 2 * (pair == 0 and x or 1 - x)
end

-- A held repeat's tails: what c_kit's e_tape is told as the replay begins, tape <span> <units>.
-- span: how long, in ms, the window's steps ran, each at the tempo it was decided under, the last
-- R.TAPE_MAX of it if longer. units: the same steps, in steps, as they run now. e_tape reads the span
-- in the units' time at the tempo in force, so the tails follow the tempo, as the steps do. An even
-- window keeps its pairs of sixteenths, so its swing is in both; an odd one plays alternately long
-- and short (Swing is the clock's, ref/module/sequencer.md), so both leave the swing out, and it
-- comes round in time with the hits every second time, at the speed they had.
function R.tape(st)
  local even, pair = #st.win % 2 == 0, st.pair
  local span, units = 0, 0
  for _, d in ipairs(st.win) do
    span = span + d.len * (even and d.share or 1) * 15000 / d.bpm
    units = units + d.len * (even and pair_share(st.swing, pair) or 1)
    pair = 1 - pair
  end
  return math.min(span, R.TAPE_MAX), units
end

-- The tails loop no longer, if they were: what c_kit plays live comes back.
function tape_off(st, out)
  if st.taping then
    st.taping = false
    out[#out + 1] = { "note", "tape-off", {} }
  end
end

-- A repeat let go. Every track plays from where it would have been.
function let_go(st)
  local out = { { "page", "rep", { 0 } } }
  st.rep, st.win = 0, {}
  tape_off(st, out)
  return out
end

-- A repeat pad, 1 to 4, held: the last n steps, as they were decided (R.tick's st.hist), are
-- played again over and over, while the loops go on underneath unheard; let go, and every track
-- plays from where it would have been (Brendan, 2026-11-03). Exactly as they were played: each
-- track's hit and its velocity as its randomness chose them that time, and each step's drunk
-- length, with nothing rolled (Brendan, 2026-11-05). Pressed with fewer than n steps decided
-- since PLAY, the steps to come are played and kept until there are n, so a repeat is always as
-- long as its pad says; pressed before anything has played, it waits for nothing: there is
-- nothing to replay. Letting go of a pad that is not the one repeating changes nothing.
function R.press_rep(st, n, velocity)
  if st.fast then return {} end
  local k = math.floor(clip(num(n), 1, R.REPEATS))
  if velocity == 0 then
    if st.rep ~= k then return {} end
    return let_go(st)
  end
  return take_window(st, k)
end

-- The window a repeat pad takes, the last k steps decided; nothing to take, nothing happens. One
-- pressed short of its length under a held repeat plays fresh steps until it is full, so the tails
-- of the one before stop looping for them.
function take_window(st, k)
  if #st.hist == 0 then return {} end
  local w = {}
  for i = math.max(1, #st.hist - k + 1), #st.hist do w[#w + 1] = st.hist[i] end
  st.rep, st.rk, st.win = k, 0, w
  local out = { { "page", "rep", { st.fast and 0 or k } } }
  if #w < k then tape_off(st, out) end
  return out
end

-- The 500 BPM repeat, pad-35 (Brendan, 2026-11-05): held, the last step decided plays over and over
-- at 500 BPM, u_tempo holding the tempo and knob 1 there; let go, the tempo goes back to what it
-- was, and the pattern carries on from the step it was pressed on, since the loops, and the bars
-- counted from them, wait for it (R.tick). The repeat pads do nothing while it is held.
function R.press_fast(st, velocity)
  if velocity ~= 0 then
    if st.fast then return {} end
    st.fast = true
    local out = { { "tempo", "fast", { 1 } }, { "page", "fast", { 1 } } }
    for _, e in ipairs(take_window(st, 1)) do out[#out + 1] = e end
    return out
  end
  if not st.fast then return {} end
  st.fast = false
  local out = let_go(st)
  table.insert(out, 1, { "tempo", "fast", { 0 } })
  table.insert(out, 2, { "page", "fast", { 0 } })
  return out
end

-- The saved tempo, pad-38 (Brendan, 2026-11-05): a press ends rush, whose loop stops at once, and asks u_song for the section's saved tempo,
-- which comes back as a section starting's does, on the state bus to u_tempo. Its lamp lights while
-- it is held, and the release does nothing else. While playing, the press also starts every loop
-- at step 1 that instant (Brendan, 2026-11-05: "it shouldn't wait for a new step"): the start bus,
-- as a press of PLAY, sent after the tempo so step 1 lands at the saved BPM. Stopped, it starts
-- nothing.
function R.press_recall(st, velocity)
  if velocity == 0 then return { { "page", "recall", { 0 } } } end
  local out = { { "page", "recall", { 1 } }, { "tempo", "rush-home", {} },
                { "song", "recall", { "tempo" } } }
  if st.playing then out[4] = { "clock", "restart", {} } end
  return out
end

-- The drum screen selects a track without playing it, as a pad press does otherwise.
function R.select(st, track)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  return { { "page", "track", { st.track } }, R.page_last(st), R.steps(st) }
end

-- The sequencer's state, for the phone's drum and arrangement screens: playing (1 or 0), the
-- global last step, the selected track, a pending sync or snap (0 none, 1 sync, 2 snap), then
-- each track's last step, then 1 for each track with a last step of its own, then the time
-- signature, the drunkenness and the swing, then each track's volume, its pitch and its
-- randomness, then the selected track's effects, in R.FX's order, its character last, and the
-- reverb's size and damping, then each track's mute and each track's solo, 1 or 0, then the
-- reverb's type, 0 to 2, then each track's random pitch, 1 or 0. 148 numbers.
R.PHONE = 4 + 2 * R.TRACKS + 4 + 3 * R.TRACKS + #R.FX + #R.VERB + 2 * R.TRACKS + 1 + R.TRACKS
function R.phone(st)
  local out = { st.playing and 1 or 0, R.global_last(st), st.track,
                st.snap and 2 or (st.sync and 1 or 0) }
  for t = 1, R.TRACKS do out[#out + 1] = R.last_of(st, t) end
  for t = 1, R.TRACKS do out[#out + 1] = st.own[t] >= 1 and 1 or 0 end
  for _, v in ipairs({ st.num, st.den, st.drunk, st.swing }) do out[#out + 1] = v end
  for _, which in ipairs({ "vol", "pitch", "randomness" }) do
    for t = 1, R.TRACKS do out[#out + 1] = st[which][t] end
  end
  for _, f in ipairs(R.FX) do out[#out + 1] = st.fx[f[1]][st.track] end
  for _, f in ipairs(R.VERB) do out[#out + 1] = st.verb[f[1]] end
  for _, which in ipairs({ "mute", "solo" }) do
    for t = 1, R.TRACKS do out[#out + 1] = st[which][t] end
  end
  out[#out + 1] = st.verb_type
  for t = 1, R.TRACKS do out[#out + 1] = st.rolled[t] end
  return out
end

-- A pad press plays the pad now, at full velocity however hard it is pressed (Brendan,
-- 2026-11-04), muted or left out of a solo or not, so a muted track can be heard before it comes
-- back in; and selects its track; knob 3 is then held at that track's last step.
R.TAP = 127
-- The pitch a hit plays at, told to c_kit before the hit when it isn't what c_kit holds: a hit its
-- randomness rolled plays at a pitch of its own, and the next at the set pitch again.
local function heard_pitch(st, t, p, out)
  if st.heard[t] == p then return end
  st.heard[t] = p
  st.told["pitch " .. R.pad(st, t)] = p
  out[#out + 1] = { "note", "pitch", { R.pad(st, t), p } }
end
function R.press_pad(st, track, velocity)
  st.track = math.floor(clip(num(track), 1, R.TRACKS))
  rearm(st.knob.track)
  local out = {}
  heard_pitch(st, st.track, st.pitch[st.track], out)
  out[#out + 1] = { "note", "pad", { R.pad(st, st.track), R.TAP } }
  out[#out + 1] = { "page", "track", { st.track } }
  out[#out + 1] = R.page_last(st)
  out[#out + 1] = R.steps(st)
  return out
end

-- What the next step does to the loops, without doing it: the global loop's step, every
-- track's, and whether a pending sync lands there. The global loop moves on; when it comes round
-- to its own step 1 a pending sync puts every track back before its step 1, and a pending snap
-- puts every track on the global last step; then every track moves on in its own loop.
local function advance(st)
  local m = st.master % R.global_last(st) + 1
  local synced = st.sync and m == 1
  local pos = {}
  for t = 1, R.TRACKS do
    local p = synced and 0 or st.pos[t]
    local last = (synced and st.snap) and R.global_last(st) or R.last_of(st, t)
    pos[t] = p % last + 1
  end
  return m, pos, synced
end

-- A step's velocity under its track's randomness (Brendan, 2026-11-05, after the DrumBrute's): at
-- R%, each step has an R% chance of ignoring what is written and flipping a coin instead: played or
-- not, and played at one of the eight levels, at random. So it drops hits from a busy track and
-- adds them to a sparse one; at 100 it is chaos, at 0 the pattern as written. A track at 0 never
-- rolls. And with its random pitch on (Brendan, 2026-11-05), a hit the coin plays has a pitch of its
-- own: up to R.ROLL_REACH semitones either way of the track's set pitch, at random, kept to a
-- track's range, one more die the track rolls only with it on. -> the velocity, and that pitch.
R.ROLL_REACH = 12
local function chance(st, t, v)
  local r = st.randomness[t]
  if r <= 0 or st.rand() * 100 >= r then return v end
  if st.rand() >= 0.5 then return 0 end
  local vel = R.velocity(math.min(R.LEVELS, math.floor(st.rand() * R.LEVELS) + 1))
  if st.rolled[t] == 0 then return vel end
  local off = math.floor(st.rand() * (2 * R.ROLL_REACH + 1)) - R.ROLL_REACH
  return vel, clip(st.pitch[t] + off, R.PITCH_MIN, R.PITCH_MAX)
end

-- What a step decides, before mute and solo: each track's step, at its place in its loop; the
-- velocity it plays at, as its randomness says (chance), 0 for none, track 1 first, and the pitch
-- its randomness gave it, if any; and the step clock's rate for the step's length: drunk, a step
-- may last longer or shorter, the more often and the further the drunker (R.drunk_chance,
-- R.drunk_reach). Every die of the step is rolled here, and a muted track's too, so muting one
-- track changes no other's. How long it runs is kept with it, for a held repeat's tails (R.tape):
-- its length in steps, its share of its pair and the tempo.
local function decide(st, pos)
  local d = { step = {}, vel = {}, pitch = {}, rate = 1 }
  for t = 1, R.TRACKS do
    d.step[t] = pos[t]
    d.vel[t], d.pitch[t] = chance(st, t, st.pattern[R.index(t, pos[t])])
  end
  if st.drunk > 0 and st.rand() < R.drunk_chance(st.drunk) then
    local stray = (st.rand() * 2 - 1) * R.drunk_reach(st.drunk)
    d.rate = 1 / math.max(R.MIN_DUR, 1 + stray)
  end
  d.len, d.share, d.bpm = 1 / d.rate, pair_share(st.pair_swing, st.pair), st.bpm
  -- Numbered, so c_melody can tell a step a repeat pad plays again from a new one.
  st.count = (st.count or 0) + 1
  d.count = st.count
  return d
end

-- The step a held repeat plays next: the next of its window's decided steps, or nil while none is
-- held, or while one pressed short of its length since PLAY is still being filled (R.press_rep). As
-- it begins, the first of a window, c_kit hears of it first, on out.
local function replay(st, out)
  if st.rep == 0 or #st.win < st.rep then return nil end
  if st.rk == 0 then
    st.taping = true
    out[#out + 1] = { "note", "tape", { R.tape(st) } }
  end
  local d = st.win[st.rk % #st.win + 1]
  st.rk = st.rk + 1
  return d
end

-- A step of the clock. The loops move on (advance), but under the 500 BPM repeat (R.press_fast),
-- and the step is decided (decide), or while a repeat pad is held, one already decided is played
-- again (replay): the same hits at the same velocities and pitches and the same length, nothing
-- rolled (Brendan, 2026-11-05). Either way it is kept, the last four, for a repeat pad to take. As
-- the replay begins, c_kit is told, before the step's hits, so they send nothing to the delays or
-- the reverb and the wet sound's last steps loop in time with them (R.tape). Every track plays its
-- hit, track 1 first, all in one logical instant, its rolled pitch or its set pitch told first
-- when c_kit holds another, but a track muted, or left out of a solo, plays nothing (R.sounds):
-- not what is written, not a coin its randomness adds, not a repeat's. Mute and solo are asked
-- now, not when the step was decided, so a track muted or soloed under a held repeat is silenced or
-- soloed in it; and its loop and its repeat go on, so it comes back in where it would have been.
-- Then the playhead, the selected track's step, and the step clock's rate for the step's length,
-- drunk or not, whose error stays -- its own drift becomes the clock (Brendan, 2026-11-03).
-- Last, on the global loop's last step, bar: a bar is the pattern's loop (Brendan, 2026-11-05),
-- so the song store starts a queued section when the global loop next comes round to its step 1,
-- the whole pattern played, and its restore reaches here before that step is cut
-- (ref/module/songs.md).
function R.tick(st)
  local out = {}
  local first = R.take_one(st)
  local waiting = st.fast and st.rep > 0
  if st.pair == 0 then st.pair_swing = st.swing end
  local pos = st.pos
  if not waiting then
    local m, moved, synced = advance(st)
    pos = moved
    st.master = m
    if synced then
      st.sync = false
      if st.snap then out = land_snap(st) end
    end
    for t = 1, R.TRACKS do st.pos[t] = pos[t] end
  end
  local d = replay(st, out)
  if not d then
    d = decide(st, pos)
    if st.rep > 0 then st.win[#st.win + 1] = d end
  end
  local ran = st.ran
  ran[#ran + 1] = d.len * pair_share(st.pair_swing, st.pair) * 15000 / st.bpm
  st.last_count, st.last_ms = d.count, ran[#ran]
  if #ran > R.STEPS then table.remove(ran, 1) end
  st.pair = 1 - st.pair
  local h = st.hist
  h[#h + 1] = d
  if #h > R.REPEATS then table.remove(h, 1) end
  local solo = R.any_solo(st)
  for t = 1, R.TRACKS do
    if d.vel[t] >= 1 and R.sounds(st, t, solo) then
      heard_pitch(st, t, d.pitch[t] or st.pitch[t], out)
      out[#out + 1] = { "note", "pad", { R.pad(st, t), d.vel[t] } }
    end
  end
  out[#out + 1] = { "page", "play", { d.step[st.track] } }
  if d.rate ~= st.rate then
    st.rate = d.rate
    out[#out + 1] = { "clock", "rate", { d.rate } }
  end
  -- The pattern's loop ends when the next step is the global loop's step 1, as advance() counts
  -- it: a global last step moved under the loop's place wraps into it, and no bar ends there.
  if not waiting and st.master % R.global_last(st) == 0 then
    out[#out + 1] = { "bar", "bar", {} }
    st.bar_passed = true
  end
  for i = #first, 1, -1 do table.insert(out, 1, first[i]) end
  return out
end

-- What waits for step 1: u_song asked, once a bar has passed, for the parts it holds for the 1, then
-- what a restore held back (R.restore). PLAY and STOP take it too, since no step 1 may come.
function R.take_one(st)
  local out = {}
  if st.bar_passed then
    st.bar_passed = false
    out[1] = { "one", "one", {} }
  end
  for _, e in ipairs(st.on_one or {}) do out[#out + 1] = e end
  st.on_one = nil
  return out
end

-- PLAY: every loop, the global one included, starts again at step 1 on the next step, which is
-- a sync already; a pending snap lands now. The step clock starts on the beat, at its own rate:
-- PLAY is the one thing that puts a drunk machine back on the clock. A held repeat lets go, and
-- the steps decided before it are forgotten; its tails stop looping, and the 500 BPM repeat's tempo
-- goes back.
function R.start(st)
  st.master, st.sync, st.playing, st.rep = 0, false, true, 0
  st.hist, st.win, st.ran = {}, {}, {}
  st.pair = 0
  for t = 1, R.TRACKS do st.pos[t] = 0 end
  st.rate = 1
  local out = R.take_one(st)
  out[#out + 1] = { "clock", "rate", { 1 } }
  out[#out + 1] = { "page", "rep", { 0 } }
  tape_off(st, out)
  if st.fast then
    st.fast = false
    out[#out + 1] = { "tempo", "fast", { 0 } }
    out[#out + 1] = { "page", "fast", { 0 } }
  end
  if st.snap then
    for _, e in ipairs(land_snap(st)) do out[#out + 1] = e end
  end
  if st.rush == "parked" then st.rush = nil end
  return out
end

-- STOP and panic: the playhead goes out, and a held repeat's tails stop looping, since its hits have
-- stopped. The pad held still holds its repeat, and the 500 BPM repeat its tempo, until let go.
-- Rush's loop stops too, and stays parked until the knob comes back or PLAY: silence is what they ask.
function R.stop(st)
  st.playing = false
  local out = R.take_one(st)
  out[#out + 1] = { "page", "play", { 0 } }
  tape_off(st, out)
  if st.rush == "on" then rush_end(st, out) end
  if st.rush then st.rush = "parked" end
  return out
end

-- ---------------------------------------------------------------- rush
-- Knob 4 past u_tempo's handoff (Brendan, 2026-11-05). st.rush is nil, "waiting" for the step that
-- ends the loop, "on", "landing" while the loop says where it is, or "parked" by STOP. The loop is what
-- is being repeated, as it ran: the steps of the repeat pad held, pad-35's being one, or the whole
-- pattern, the global loop. Its frequency starts at 1000 / span, playback speed 1, so nothing jumps,
-- which is (1000 / 15) / N if its steps ran at 1000 BPM, and goes up evenly with the rest of the knob's
-- turn to R.RUSH_HZ, whatever its length. At the capture the sequencer stops: no hits, and the step
-- clock's ticks shut off in c_steps.pd, since a Lua call and the phone's state 66 times a second would
-- be for nothing. A tail loop stops too, under e_rush's mute, since the recording has it; it goes on
-- where it was after.

local function rush_hz(st)
  return st.rush_f0 * (R.RUSH_HZ / st.rush_f0) ^ st.rush_t
end

-- Its real frequency, to a tenth under 100 Hz, and only ever from a loop that has been taken.
local function rush_row(hz)
  local shown = hz < 100 and math.floor(hz * 10 + 0.5) / 10 or math.floor(hz + 0.5)
  return { "disp", "rush", { shown, "Hz" } }
end

-- At hz, the loop's gain and the sine's: the loop alone, then an equal-power cross, as the two have
-- nothing in common, then the sine alone, fading evenly up the turn to nothing at the top.
function R.rush_mix(hz)
  if hz <= R.RUSH_RAW then return 1, 0 end
  if hz < R.RUSH_PURE then
    local u = math.log(hz / R.RUSH_RAW) / math.log(R.RUSH_PURE / R.RUSH_RAW)
    return math.cos(u * math.pi / 2), math.sin(u * math.pi / 2)
  end
  local fade = 1 - math.log(hz / R.RUSH_PURE) / math.log(R.RUSH_HZ / R.RUSH_PURE)
  return 0, math.max(0, fade)
end

-- The two told when they change, which below R.RUSH_RAW is never.
local function tell_mix(st, out, hz)
  local loop, sine = R.rush_mix(hz)
  if st.rush_loop == loop and st.rush_sine == sine then return end
  st.rush_loop, st.rush_sine = loop, sine
  out[#out + 1] = { "note", "rush-mix", { loop, sine } }
end

-- The step's boundary, or now if nothing is playing: the steps that just ran are the loop.
local function rush_take(st)
  local n = math.min(st.rep > 0 and st.rep or R.global_last(st), #st.ran)
  local span, loop = 0, {}
  for i = #st.ran - n + 1, #st.ran do
    span = span + st.ran[i]
    loop[#loop + 1] = st.ran[i]
  end
  if span <= 0 then span = 15 end
  span = math.min(span, R.RUSH_MAX)
  st.rush, st.rush_f0, st.rush_ran = "on", 1000 / span, loop
  st.rush_loop, st.rush_sine = nil, nil
  local hz = rush_hz(st)
  local out = { { "note", "rush", { span, hz } } }
  tell_mix(st, out, hz)
  out[#out + 1] = { "clock", "ticks", { 0 } }
  out[#out + 1] = rush_row(hz)
  if st.taping then out[#out + 1] = { "note", "tape-run", { 0 } } end
  return out
end

-- The kit and the steps come back, from where they were.
function rush_end(st, out)
  out[#out + 1] = { "note", "rush-off", {} }
  out[#out + 1] = { "clock", "ticks", { 1 } }
  if st.taping then out[#out + 1] = { "note", "tape-run", { 1 } } end
end

-- rush <t>, from u_tempo: how far past the handoff, 0 to 1.
function R.rush(st, t)
  st.rush_t = clip(num(t), 0, 1)
  if st.rush == "on" then
    local hz = rush_hz(st)
    local out = { { "note", "rush-rate", { hz } } }
    tell_mix(st, out, hz)
    out[#out + 1] = rush_row(hz)
    return out
  end
  if st.rush then return {} end
  if not st.playing then return rush_take(st) end
  st.rush = "waiting"
  return {}
end

-- rush-off, from u_tempo: something else has set the tempo.
function R.rush_off(st)
  local out = {}
  if st.rush == "on" or st.rush == "landing" then rush_end(st, out) end
  st.rush = nil
  return out
end

-- rush-back <bpm>, from u_tempo: the knob is back below the handoff (Brendan, 2026-11-05: "It doesn't
-- really skip on the way up, but it does on the way down."). The steps must land where the loop is, not
-- where they stopped, so the loop is asked: at speed 1, in case the knob was thrown, e_rush answers with
-- its phase, rush-at, in this same instant, and crosses back over 40 ms, the loop playing on over
-- the first hits.
function R.rush_back(st, bpm)
  if st.rush ~= "on" then
    st.rush = nil
    return {}
  end
  st.rush, st.rush_t, st.rush_land = "landing", 0, num(bpm)
  local hz = rush_hz(st)
  local out = { { "note", "rush-rate", { hz } } }
  tell_mix(st, out, hz)
  out[#out + 1] = { "note", "rush-back", {} }
  return out
end

-- rush-at <phase>, from e_rush: 0 to 1 through the loop. It is on one of its steps, and part way
-- through it, by how long each ran, and those are back steps from the last of them, where the sequencer
-- stands. So: a held repeat's next step, or the global loop's place and each track's in its own, go back
-- that far, and the parity of the pair with them; and the step clock's phase, two steps a cycle, is set
-- so the next step comes when this one ends in the loop. Swing is ignored, an error under a step at
-- these speeds. R.RUSH_LAND keeps that next step from coming before the ticks are back on.
function R.rush_at(st, phase)
  if st.rush ~= "landing" then return {} end
  st.rush = nil
  local loop = st.rush_ran
  local total = 0
  for _, ms in ipairs(loop) do total = total + ms end
  local at, step, through = clip(num(phase), 0, 1) * total, #loop, 0
  for k, ms in ipairs(loop) do
    if at < ms then
      step, through = k, at / ms
      break
    end
    at = at - ms
  end
  local back = math.max(0, #loop - step)
  if st.rep > 0 then
    if #st.win >= st.rep then
      local rk = (st.rk - back) % #st.win
      -- 0 is the replay beginning, which would tell the tails again.
      if rk == 0 and st.taping then rk = #st.win end
      st.rk = rk
    end
  elseif st.playing and #loop > 0 then
    st.master = (st.master - 1 - back) % R.global_last(st) + 1
    for t = 1, R.TRACKS do st.pos[t] = (st.pos[t] - 1 - back) % R.last_of(st, t) + 1 end
  end
  st.pair = (st.pair + back) % 2
  local step_ms = 15000 / math.max(1, st.rush_land)
  through = math.min(through, 1 - R.RUSH_LAND / step_ms)
  local out = { { "clock", "place", { (st.pair == 1 and 0 or 0.5) + through / 2 } } }
  if st.taping then out[#out + 1] = { "note", "tape-run", { 1 } } end
  return out
end

-- ---------------------------------------------------------------- the effects
-- Each track's distortion, delay and send, and the reverb's size and damping (Brendan,
-- 2026-11-05), played by c_kit: R.FX and R.VERB name them. c_kit sets none of its own at load,
-- so it is told every value at load (R.boot), and after that each one as it changes.

local FX_BY, VERB_BY = {}, {}
for _, f in ipairs(R.FX) do FX_BY[f[1]] = f end
for _, f in ipairs(R.VERB) do VERB_BY[f[1]] = f end

-- What c_kit is told of a track's effect: its value, or for the note and the feel, the delay's
-- time in steps, the one c_kit plays, delay-time <pad> <steps>.
local function fx_said(st, t, field)
  if field == "note" or field == "feel" then
    return "delay-time", R.NOTES[st.fx.note[t]] * R.FEELS[st.fx.feel[t]]
  end
  return field, st.fx[field][t]
end

-- c_kit told a value, unless it is the one it was told last: so a section's restore, which lands
-- on a step, sends only what changed, since every message out of the Lua costs about 0.025 ms on
-- the Organelle and there are 130 values to tell (the Organelle's Reference page, pdlua).
local function tell(st, out, sel, pad, v)
  local key = pad and (sel .. " " .. pad) or sel
  if st.told[key] == v then return end
  st.told[key] = v
  out[#out + 1] = { "note", sel, pad and { pad, v } or { v } }
end

-- Every effect's value c_kit has not been told: each track's in R.FX's order, track 1 first, the
-- note and the feel as one delay-time, then the reverb's, its type last, as verb-type.
function R.tell_fx(st)
  local out = {}
  for t = 1, R.TRACKS do
    for _, f in ipairs(R.FX) do
      local sel, v = fx_said(st, t, f[1])
      tell(st, out, sel, R.pad(st, t), v)
    end
  end
  for _, f in ipairs(R.VERB) do tell(st, out, f[1], nil, st.verb[f[1]]) end
  tell(st, out, "verb-type", nil, st.verb_type)
  return out
end

-- The drum screen's effect controls for the selected track, sent with the track (Brendan,
-- 2026-11-05): drive, tone, dist (the distortion's mix), char (its character, 1 to 4, soft, hard,
-- fold, crush), delay-note (1 to 5, 1/2 to 1/32), delay-feel (1 to 3, straight, triplet,
-- dotted), feedback, delay (its level) and send, each <track> <value>. Saved, and told to c_kit.
-- The same value again, or a message without a track and a number, does nothing.
function R.set_fx(st, field, track, v)
  local t = track_value(track, v)
  if not t then return {} end
  local f = FX_BY[field]
  local n = whole(v, f[2], f[3])
  if n == st.fx[field][t] then return {} end
  st.fx[field][t] = n
  local out = { R.save(st) }
  local sel, x = fx_said(st, t, field)
  tell(st, out, sel, R.pad(st, t), x)
  return out
end

-- The reverb's size and damping, the kit's, as they stand. Saved, and told to c_kit.
function R.set_verb(st, field, v)
  if type(v) ~= "number" then return {} end
  local f = VERB_BY[field]
  local n = whole(v, f[2], f[3])
  if n == st.verb[field] then return {} end
  st.verb[field] = n
  local out = { R.save(st) }
  tell(st, out, field, nil, n)
  return out
end

-- The reverb's type, 0 plate, 1 gigaverb, 2 freeverb, the kit's (Brendan, 2026-11-05): saved,
-- and told to c_kit as verb-type. The same type again, or no number, does nothing.
function R.set_verb_type(st, v)
  if type(v) ~= "number" then return {} end
  local n = whole(v, 0, #R.VERB_TYPES - 1)
  if n == st.verb_type then return {} end
  st.verb_type = n
  local out = { R.save(st) }
  tell(st, out, "verb-type", nil, n)
  return out
end

-- The effects from a saved line, past its first 581, and the characters past its first 743: each
-- as far as the line holds it, a symbol as its range's bottom, and what it does not hold at its
-- starting point, off. So a line saved before the effects, of any length R.restore takes, comes
-- back with every effect off, and one saved before the characters with every track soft.
local function restore_fx(st, values)
  local k = R.SAVED_FXLESS
  local function take(f, t)
    k = k + 1
    st.fx[f[1]][t] = values[k] ~= nil and whole(values[k], f[2], f[3]) or f[4]
  end
  for i = 1, R.FX_BLOCK do
    for t = 1, R.TRACKS do take(R.FX[i], t) end
  end
  for _, f in ipairs(R.VERB) do
    k = k + 1
    st.verb[f[1]] = values[k] ~= nil and whole(values[k], f[2], f[3]) or f[4]
  end
  k = R.SAVED_FLAGS
  for i = R.FX_BLOCK + 1, #R.FX do
    for t = 1, R.TRACKS do take(R.FX[i], t) end
  end
end

-- The reverb's type from a saved line, its 760th number, a symbol as 0, and plate, 0, when the line
-- is shorter: so every line saved before the type comes back as the plate.
local function restore_type(st, values)
  local v = values[R.SAVED_TYPED]
  st.verb_type = v ~= nil and whole(v, 0, #R.VERB_TYPES - 1) or 0
end

-- The random pitch flags from a saved line, past its first 760: each as far as the line holds it,
-- 1 or 0, a symbol as 0, and what it does not hold 0. So a line saved before them comes back with
-- every track's off.
local function restore_rolled(st, values)
  for t = 1, R.TRACKS do
    local v = values[R.SAVED_TYPED + t]
    st.rolled[t] = v ~= nil and whole(v, 0, 1) or 0
  end
end

-- The mutes and solos from a saved line, past its first 711: each as far as the line holds it,
-- 1 or 0, a symbol as 0, and what it does not hold 0. So a line saved before mute and solo, of
-- any length R.restore takes, comes back with nothing muted or soloed.
local function restore_flags(st, values)
  for t = 1, R.TRACKS do
    local m, s = values[R.SAVED_FX + t], values[R.SAVED_FX + R.TRACKS + t]
    st.mute[t] = m ~= nil and whole(m, 0, 1) or 0
    st.solo[t] = s ~= nil and whole(s, 0, 1) or 0
  end
end

-- A section's restore of <part>, from the song store, or u_state's of section-1-<part>, the auto
-- key the pattern had before sections, once, then put straight back (ref/module/state.md), which
-- also repairs a short or malformed line; and every track's volume and pitch to c_kit, and
-- whichever effects changed (R.tell_fx), a line of fewer than 711 bringing them back off and one
-- of fewer than 759 every track back soft and one of fewer than 760 the reverb back to the plate;
-- a line of fewer than 776 every track's random pitch off;
-- and last, the page's quiet pads when they changed, a line of fewer than 743 bringing every
-- track back unmuted and unsoloed. A line of
-- exactly 256 is the 16-step pattern this replaced, track by track: its steps go to each track's
-- first sixteen. A line of exactly 563 is from before the randomness (2026-11-05): its skip
-- chances come back as each track's randomness, which took their place, its move chances are
-- dropped, and the volumes and pitches stay 0. Anything else is read as this file saves it, as far
-- as it goes, a symbol as 0, the rest left as they were: a line of 579, from before sections, keeps
-- the swing and the global last step in force, and one of 528, from before the phone's settings,
-- 4/4, sober, and no randomness. A bottom number that is not one of 1 2 4 8 16 is 4. A swing or a
-- global last step restored holds its knob again, as the phone's does, and the step clock takes
-- the swing. Every loop, the global one included, starts again at step 1 on the next step: a
-- section starts on its own step 1, whatever its last step and the one before it had, as PLAY
-- starts the pattern (ref/module/songs.md). A repeat held through it goes on playing the steps it
-- holds, as they were heard, while the new section's loops go on underneath, as a pattern edit
-- under a held repeat changes nothing heard until it is let go.
-- The kit's sound, what a song's sections share (Brendan, 2026-11-06): each track's volume and pitch, its
-- effects in R.FX's order, the reverb's size and damping and its type, and each track's random pitch.
R.KIT = 2 * R.TRACKS + #R.FX * R.TRACKS + #R.VERB + 1 + R.TRACKS
function R.kit_line(st)
  local a, k = {}, 0
  for _, which in ipairs({ "vol", "pitch" }) do
    for t = 1, R.TRACKS do k = k + 1; a[k] = st[which][t] end
  end
  for _, f in ipairs(R.FX) do
    for t = 1, R.TRACKS do k = k + 1; a[k] = st.fx[f[1]][t] end
  end
  for _, f in ipairs(R.VERB) do k = k + 1; a[k] = st.verb[f[1]] end
  k = k + 1; a[k] = st.verb_type
  for t = 1, R.TRACKS do k = k + 1; a[k] = st.rolled[t] end
  return a
end

-- The kit's sound as a list says, and everything that hears of it told what changed.
local function take_kit(st, v)
  local k = 0
  local function next_atom() k = k + 1; return v[k] end
  for t = 1, R.TRACKS do st.vol[t] = whole(next_atom(), R.VOL_MIN, R.VOL_MAX) end
  for t = 1, R.TRACKS do st.pitch[t] = whole(next_atom(), R.PITCH_MIN, R.PITCH_MAX) end
  for _, f in ipairs(R.FX) do
    for t = 1, R.TRACKS do st.fx[f[1]][t] = whole(next_atom(), f[2], f[3]) end
  end
  for _, f in ipairs(R.VERB) do st.verb[f[1]] = whole(next_atom(), f[2], f[3]) end
  st.verb_type = whole(next_atom(), 0, #R.VERB_TYPES - 1)
  for t = 1, R.TRACKS do st.rolled[t] = whole(next_atom(), 0, 1) end
  local out = {}
  for _, which in ipairs({ "vol", "pitch" }) do
    for t = 1, R.TRACKS do tell(st, out, which, R.pad(st, t), st[which][t]) end
  end
  for t = 1, R.TRACKS do st.heard[t] = st.pitch[t] end
  for _, e in ipairs(R.tell_fx(st)) do out[#out + 1] = e end
  return out
end

-- restore kit <the line>, as a song loads: this song's kit. None: it has none yet, and the first section
-- it starts gives it one.
function R.restore_kit(st, values)
  if #values ~= R.KIT then
    st.kit_on, st.kit_base, st.kit_wanted = false, nil, true
    return {}
  end
  st.kit_on, st.kit_wanted = true, false
  st.kit_base = values
  return take_kit(st, values)
end

-- A section starting, snap back (0) or carry on (1): snap back takes the kit to what it was last saved as.
function R.restore_tweaks(st, keep)
  if num(keep) == 1 or not st.kit_on or not st.kit_base then return {} end
  local now = R.kit_line(st)
  local same = true
  for i = 1, #now do
    if now[i] ~= st.kit_base[i] then
      same = false
      break
    end
  end
  if same then return {} end
  return take_kit(st, st.kit_base)
end

function R.restore(st, values)
  local cells = R.TRACKS * R.STEPS
  st.master = 0
  for t = 1, R.TRACKS do st.pos[t] = 0 end
  if #values == 256 then
    for t = 1, R.TRACKS do
      for s = 1, 16 do st.pattern[R.index(t, s)] = num(values[(t - 1) * 16 + s]) end
    end
  else
    local chances = #values == R.SAVED_CHANCES
    for i = 1, math.min(#values, cells) do st.pattern[i] = num(values[i]) end
    for t = 1, R.TRACKS do
      local v, k = values[cells + t], values[cells + R.TRACKS + t]
      if v ~= nil then st.own[t] = math.floor(clip(num(v), 0, R.STEPS)) end
      if k ~= nil then st.randomness[t] = percent(k) end
      if not chances and not st.kit_on then
        local db, p = values[cells + 2 * R.TRACKS + t], values[cells + 3 * R.TRACKS + t]
        if db ~= nil then st.vol[t] = whole(db, R.VOL_MIN, R.VOL_MAX) end
        if p ~= nil then st.pitch[t] = whole(p, R.PITCH_MIN, R.PITCH_MAX) end
      end
    end
    local n = cells + (chances and 3 or 4) * R.TRACKS
    if values[n + 1] ~= nil then st.num = math.floor(clip(num(values[n + 1]), 1, R.MAX_NUM)) end
    if values[n + 2] ~= nil then
      local d = num(values[n + 2])
      st.den = 4
      for _, v in ipairs(R.DENS) do if v == d then st.den = v end end
    end
    if values[n + 3] ~= nil then st.drunk = percent(values[n + 3]) end
    if not chances and values[n + 4] ~= nil then
      st.swing = whole(values[n + 4], R.SWING_MIN, R.SWING_MAX)
      rearm(st.knob.swing)
    end
    if not chances and values[n + 5] ~= nil then
      st.last = whole(values[n + 5], 1, R.STEPS)
      rearm(st.knob.last)
      if st.own[st.track] == 0 then rearm(st.knob.track) end
    end
  end
  restore_flags(st, values)
  -- A song that has no kit of its own yet takes this section's sound as it.
  if not st.kit_on then
    restore_fx(st, values)
    restore_type(st, values)
    restore_rolled(st, values)
    if st.kit_wanted then
      st.kit_on, st.kit_wanted, st.kit_first = true, false, true
      st.kit_base = R.kit_line(st)
    end
  end
  -- A section change happens on the beat, and a burst of messages there stalls the audio: Pd runs
  -- with a 6 ms buffer, and the beat dropped around a section's 1 (Brendan, 2026-11-05). So a line
  -- that says what the sequencer would save isn't put back, since the store already holds it; one
  -- saved before today's shape, or clipped here, is. And c_kit hears only the volumes and pitches
  -- that differ from what it was last told.
  local out, saved = {}, R.save(st)
  local same = #saved[3] == #values
  for i = 1, same and #values or 0 do
    if saved[3][i] ~= values[i] then
      same = false
      break
    end
  end
  -- A section's line holds no sound once the song has a kit, and one from before that is left as it is.
  local put = not same and not st.kit_on and saved or nil
  for _, e in ipairs({ R.page_last(st), R.steps(st), R.page_bar(st),
                       { "clock", "swing", { st.swing / 100 } } }) do
    out[#out + 1] = e
  end
  for _, which in ipairs({ "vol", "pitch" }) do
    for t = 1, R.TRACKS do tell(st, out, which, R.pad(st, t), st[which][t]) end
  end
  for t = 1, R.TRACKS do st.heard[t] = st.pitch[t] end
  for _, e in ipairs(R.tell_fx(st)) do out[#out + 1] = e end
  tell_quiet(st, out)
  -- While playing, the section starts on the beat: bar comes on the old section's last step, and
  -- all that can be heard or seen of the new one waits for the next tick, step 1, as the old
  -- section's last step plays out as it was (Brendan, 2026-11-05: "the next section begins just a
  -- fraction of a second too early"). Only the pattern's own numbers change now, unheard.
  if st.playing then
    st.on_one = st.on_one or {}
    for _, e in ipairs(out) do st.on_one[#st.on_one + 1] = e end
    return put and { put } or {}
  end
  if put then table.insert(out, 1, put) end
  return out
end

-- A press's velocity: 0 is a release, which only a repeat pad acts on.
local function pressed(a)
  return a[1] ~= nil and a[2] ~= 0
end

-- What arrives on the first inlet: u_map's drum-page presses and releases, <selector> <n>
-- <velocity>, step, vel, pad and rep and the 500 BPM repeat's fast and the saved tempo's recall;
-- its knobs, last and track-last with the knob's 0-1, and swing, which no row of the table names
-- since knob 4 became rush (Brendan, 2026-11-05) but a row could; rush <0-1>, rush-back <bpm> and rush-off, u_tempo's, and rush-at <0-1>, c_kit's; the drum
-- screen's sync,
-- snap and select, and its pads' vol, pitch, randomness and set-track-last <track> <value>,
-- through u_net; and the arrangement screen's num and den (-1 or 1), drunk (0 to 100), set-swing
-- (50 to 75) and set-last (1 to 32), through u_net too; and the drum screen's effects, drive,
-- tone, dist, char, delay-note, delay-feel, feedback, delay and send <track> <value>, and size and
-- damping <value> and verb-type <0-2>; and its mute, solo and rnd-pitch <track> <0 or 1>. A press,
-- a knob or a setting with no number in it does nothing.
R.presses = {
  step = function(st, a) return pressed(a) and R.press_step(st, a[1]) or {} end,
  vel = function(st, a) return pressed(a) and R.press_vel(st, a[1]) or {} end,
  pad = function(st, a) return pressed(a) and R.press_pad(st, a[1], a[2]) or {} end,
  rep = function(st, a) return a[1] and R.press_rep(st, a[1], a[2]) or {} end,
  fast = function(st, a) return a[1] and R.press_fast(st, a[2]) or {} end,
  recall = function(st, a) return a[1] and R.press_recall(st, a[2]) or {} end,
  last = function(st, a) return a[1] and R.knob_last(st, a[1]) or {} end,
  ["track-last"] = function(st, a) return a[1] and R.knob_track(st, a[1]) or {} end,
  swing = function(st, a) return a[1] and R.knob_swing(st, a[1]) or {} end,
  rush = function(st, a) return R.rush(st, a[1]) end,
  ["rush-off"] = function(st) return R.rush_off(st) end,
  ["rush-back"] = function(st, a) return R.rush_back(st, a[1]) end,
  ["rush-at"] = function(st, a) return R.rush_at(st, a[1]) end,
  sync = function(st) return R.sync(st) end,
  snap = function(st) return R.snap(st) end,
  select = function(st, a) return a[1] and R.select(st, a[1]) or {} end,
  num = function(st, a) return a[1] and R.time(st, "num", a[1]) or {} end,
  den = function(st, a) return a[1] and R.time(st, "den", a[1]) or {} end,
  drunk = function(st, a) return a[1] and R.drunk(st, a[1]) or {} end,
  vol = function(st, a) return R.set_vol(st, a[1], a[2]) end,
  pitch = function(st, a) return R.set_pitch(st, a[1], a[2]) end,
  randomness = function(st, a) return R.set_randomness(st, a[1], a[2]) end,
  ["set-track-last"] = function(st, a) return R.set_track_last(st, a[1], a[2]) end,
  drive = function(st, a) return R.set_fx(st, "drive", a[1], a[2]) end,
  tone = function(st, a) return R.set_fx(st, "tone", a[1], a[2]) end,
  dist = function(st, a) return R.set_fx(st, "dist", a[1], a[2]) end,
  char = function(st, a) return R.set_fx(st, "char", a[1], a[2]) end,
  ["delay-note"] = function(st, a) return R.set_fx(st, "note", a[1], a[2]) end,
  ["delay-feel"] = function(st, a) return R.set_fx(st, "feel", a[1], a[2]) end,
  feedback = function(st, a) return R.set_fx(st, "feedback", a[1], a[2]) end,
  delay = function(st, a) return R.set_fx(st, "delay", a[1], a[2]) end,
  send = function(st, a) return R.set_fx(st, "send", a[1], a[2]) end,
  size = function(st, a) return R.set_verb(st, "size", a[1]) end,
  damping = function(st, a) return R.set_verb(st, "damping", a[1]) end,
  ["verb-type"] = function(st, a) return R.set_verb_type(st, a[1]) end,
  ["set-swing"] = function(st, a) return R.set_swing(st, a[1]) end,
  ["set-last"] = function(st, a) return R.set_last(st, a[1]) end,
  mute = function(st, a) return R.set_mute(st, a[1], a[2]) end,
  solo = function(st, a) return R.set_solo(st, a[1], a[2]) end,
  ["rnd-pitch"] = function(st, a) return R.set_rolled(st, a[1], a[2]) end,
}

-- What c_steps.pd itself sends: the clock's step, with the tempo bus's BPM, which a step decided
-- keeps for a held repeat's tails (R.tape); PLAY, STOP, u_state's restore, and the load.
-- The drum page's controls as a control in play moves them, 0 to 1 (Brendan, 2026-11-06), each to what the
-- phone's own command takes: <name>-<track>, or the kit's and the song's with no track.
local function scale(v, lo, hi)
  return lo + (hi - lo) * math.max(0, math.min(1, num(v)))
end
local function round_to(x)
  return math.floor(x + 0.5)
end
for t = 1, R.TRACKS do
  R.presses["vol-" .. t] = function(st, a) return R.set_vol(st, t, round_to(scale(a[1], R.VOL_MIN, R.VOL_MAX))) end
  R.presses["pitch-" .. t] = function(st, a) return R.set_pitch(st, t, round_to(scale(a[1], R.PITCH_MIN, R.PITCH_MAX))) end
  R.presses["randomness-" .. t] = function(st, a) return R.set_randomness(st, t, round_to(scale(a[1], 0, 100))) end
  for _, f in ipairs({ "drive", "tone", "dist", "feedback", "delay", "send" }) do
    R.presses[f .. "-" .. t] = function(st, a) return R.set_fx(st, f, t, round_to(scale(a[1], 0, 100))) end
  end
end
R.presses["kit-size"] = function(st, a) return R.set_verb(st, "size", round_to(scale(a[1], 0, 100))) end
R.presses["kit-damping"] = function(st, a) return R.set_verb(st, "damping", round_to(scale(a[1], 0, 100))) end
R.presses["kit-drunk"] = function(st, a) return R.drunk(st, round_to(scale(a[1], 0, 100))) end
R.presses["kit-swing"] = function(st, a) return R.set_swing(st, round_to(scale(a[1], R.SWING_MIN, R.SWING_MAX))) end

R.internal = {
  ["restore-kit"] = function(st, a) return R.restore_kit(st, a) end,
  ["restore-tweaks"] = function(st, a) return R.restore_tweaks(st, a[1]) end,
  ["kit-save"] = function(st)
    st.kit_base = R.kit_line(st)
    return {}
  end,
  tick = function(st, a)
    if type(a[1]) == "number" then st.bpm = clip(a[1], 5, 1000) end
    if st.rush == "waiting" then return rush_take(st) end
    return R.tick(st)
  end,
  start = function(st) return R.start(st) end,
  stop = function(st) return R.stop(st) end,
  restore = function(st, a) return R.restore(st, a) end,
  init = function(st) return R.boot(st) end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_steps", string.sub(text, 1, 21) } }
end

return R
