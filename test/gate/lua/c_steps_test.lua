-- The sequencer's rules, without Pd: "Cut It/c_steps.lua", and the Pd face that carries them,
-- "Cut It/c_steps-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The sequencer
-- gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/c_steps_test.lua [-v]
--
-- What the patch does with these answers -- the notes on the clock, the page, the disk -- is
-- sequencer-assert.py's, on a running copy of the instrument. ref/module/sequencer.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
-- The checks that count what math.random does over thousands of steps hold to about four
-- standard deviations, and Lua seeds it afresh on every run, so now and then one failed by
-- chance (once in about forty runs, 2026-11-05). A fixed seed makes every run the same run.
math.randomseed(20261105)
local R = dofile(DIR .. "c_steps.lua")
local check, equal = T.check, T.equal

local LEVELS = { 16, 32, 48, 64, 79, 95, 111, 127 }
local CELLS = 16 * 32

local function zeros(n)
  local z = {}
  for i = 1, n do z[i] = 0 end
  return z
end

-- The selected track's row as the page gets it, from a pattern: each step's level.
local function row(pat, track)
  local r = {}
  for s = 1, 32 do r[s] = R.level(pat[(track - 1) * 32 + s]) end
  return r
end

-- The effects, as a new sequencer has them, written out here rather than read from R.FX, so a
-- change to a starting point is a change this test sees (Brendan, 2026-11-05): every track's
-- drive 50, tone 100 (60 until the characters), mix 0, note 3 (1/8), feel 1 (straight), feedback
-- 40, level 0, send 0 and character 1 (soft), in the order the phone gets them, and the reverb's
-- size and damping, 50 each. The line holds the first BLOCK after its 581, and the character
-- after the mutes and solos.
local FX = { { "drive", 50 }, { "tone", 100 }, { "dist", 0 }, { "note", 3 }, { "feel", 1 },
             { "feedback", 40 }, { "delay", 0 }, { "send", 0 }, { "char", 1 } }
local BLOCK = 8
local VERB = { { "size", 50 }, { "damping", 50 } }
-- A delay's time in steps: 1/2 to 1/32, straight, triplet or dotted.
local NOTE_STEPS, FEEL_SHARE = { 8, 4, 2, 1, 0.5 }, { 1, 2 / 3, 3 / 2 }

-- An effect's value for a track, from fx = { drive = { [3] = 70 }, ... }, its starting point unless
-- given; and the reverb's, from verb = { size = 80 }.
local function fx_of(fx, field, t, start)
  return fx and fx[field] and fx[field][t] or start
end

-- The saved line: 512 velocities, then the 16 tracks' own last steps, their randomness, their
-- volumes and their pitches, then the time signature, the drunkenness, the swing and the global
-- last step: 581 numbers; then, when x gives any effect, each of the first BLOCK effects of every
-- track and the reverb's two: 711; then, when x mutes or solos any track, the sixteen mutes and the
-- sixteen solos, the effects before them whether given or not: 743; then, when x gives any track
-- a character, the sixteen characters, everything before them whether given or not: 759; then,
-- when x gives the reverb a type other than the plate, 0, the type, everything before it as it
-- stands: 760; then, when x turns any track's random pitch on, the sixteen flags: 776. x holds what differs from a new sequencer's: randomness, vol and pitch by track,
-- num, den, drunk, swing, last, fx (fx.char among them) and verb, mute and solo by track, type,
-- and rolled by track.
local function line(pat, own, x)
  x = x or {}
  local l = {}
  for i = 1, CELLS do l[i] = pat[i] end
  for t = 1, 16 do
    l[CELLS + t] = own and own[t] or 0
    l[CELLS + 16 + t] = x.randomness and x.randomness[t] or 0
    l[CELLS + 32 + t] = x.vol and x.vol[t] or 0
    l[CELLS + 48 + t] = x.pitch and x.pitch[t] or 0
  end
  l[CELLS + 65], l[CELLS + 66], l[CELLS + 67] = x.num or 4, x.den or 4, x.drunk or 0
  l[CELLS + 68], l[CELLS + 69] = x.swing or 50, x.last or 16
  local late, typed = x.fx and x.fx.char, (x.type and x.type ~= 0) or x.rolled
  local flagged = x.mute or x.solo or late or typed
  if not x.fx and not x.verb and not flagged then return l end
  for i = 1, BLOCK do
    for t = 1, 16 do l[#l + 1] = fx_of(x.fx, FX[i][1], t, FX[i][2]) end
  end
  for _, f in ipairs(VERB) do l[#l + 1] = (x.verb or {})[f[1]] or f[2] end
  if not flagged then return l end
  for _, which in ipairs({ "mute", "solo" }) do
    for t = 1, 16 do l[#l + 1] = (x[which] or {})[t] or 0 end
  end
  if not late and not typed then return l end
  for i = BLOCK + 1, #FX do
    for t = 1, 16 do l[#l + 1] = fx_of(x.fx, FX[i][1], t, FX[i][2]) end
  end
  if not typed then return l end
  l[#l + 1] = x.type or 0
  if not x.rolled then return l end
  for t = 1, 16 do l[#l + 1] = x.rolled[t] or 0 end
  return l
end

-- The first n numbers of a line: 581, saved before the effects; 579, before sections, without
-- the swing and the global last step as well.
local function first(l, n)
  local out = {}
  for i = 1, n do out[i] = l[i] end
  return out
end

local function sectionless(pat, own, x)
  return first(line(pat, own, x), 579)
end

-- The line saved until 2026-11-05: 563 numbers, each track's skip and move chance where its
-- randomness and its volume are now, no pitches, then the time signature and the drunkenness.
local function old_line(pat, own, x)
  x = x or {}
  local l = {}
  for i = 1, CELLS do l[i] = pat[i] end
  for t = 1, 16 do
    l[CELLS + t] = own and own[t] or 0
    l[CELLS + 16 + t] = x.skip and x.skip[t] or 0
    l[CELLS + 32 + t] = x.move and x.move[t] or 0
  end
  l[CELLS + 49], l[CELLS + 50], l[CELLS + 51] = x.num or 4, x.den or 4, x.drunk or 0
  return l
end

-- What a restore tells c_kit, after the line and the page: every track's volume, then every
-- track's pitch, 0 unless given.
local function kit(vol, pitch)
  local out = {}
  for t = 1, 16 do out[#out + 1] = { "note", "vol", { t, (vol or {})[t] or 0 } } end
  for t = 1, 16 do out[#out + 1] = { "note", "pitch", { t, (pitch or {})[t] or 0 } } end
  return out
end

-- Every effect c_kit is told when it has been told none, at load or by a sequencer that never
-- loaded: each track's drive, tone, dist, delay-time, feedback, delay, send and char, track 1 first,
-- then the reverb's size and damping, at their starting points unless given (fx, verb), then
-- its type, verb-type, 0 unless given (verb.type).
local function fx_all(fx, verb)
  local out = {}
  for t = 1, 16 do
    for _, f in ipairs(FX) do
      if f[1] == "note" then
        out[#out + 1] = { "note", "delay-time", { t, NOTE_STEPS[fx_of(fx, "note", t, 3)]
                                                     * FEEL_SHARE[fx_of(fx, "feel", t, 1)] } }
      elseif f[1] ~= "feel" then
        out[#out + 1] = { "note", f[1], { t, fx_of(fx, f[1], t, f[2]) } }
      end
    end
  end
  for _, f in ipairs(VERB) do out[#out + 1] = { "note", f[1], { (verb or {})[f[1]] or f[2] } } end
  out[#out + 1] = { "note", "verb-type", { (verb or {}).type or 0 } }
  return out
end

-- Lists one after the other.
local function cat(...)
  local out = {}
  for _, l in ipairs({ ... }) do for _, e in ipairs(l) do out[#out + 1] = e end end
  return out
end

-- What a step press answers: the whole pattern to save, then the selected track's row.
local function edited(pat, track, own)
  return { { "save", "list", line(pat, own) }, { "page", "steps", row(pat, track) } }
end

-- A knob position for a step: what R.knob_step reads back as n.
local function at(n) return (n - 1) / 31 end

-- The phone's 148 numbers, from the few that differ: lasts and owns by track, then the time
-- signature, the drunkenness and the swing (4 4 0 50 unless given), then every track's volume,
-- pitch and randomness (per.vol, per.pitch and per.randomness by track, 0 unless given), then the
-- selected track's effects and the reverb's (per.fx and per.verb, as line's x.fx and x.verb), then
-- every track's mute and every track's solo (per.mute and per.solo by track, 0 unless given), then
-- the reverb's type, then every track's random pitch (per.rolled by track, 0 unless given).
local function phone(playing, last, track, pending, lasts, owns, tail, per)
  per = per or {}
  local p = { playing, last, track, pending }
  for t = 1, 16 do p[#p + 1] = lasts[t] or last end
  for t = 1, 16 do p[#p + 1] = owns[t] or 0 end
  for _, v in ipairs(tail or { 4, 4, 0, 50 }) do p[#p + 1] = v end
  for _, which in ipairs({ "vol", "pitch", "randomness" }) do
    for t = 1, 16 do p[#p + 1] = (per[which] or {})[t] or 0 end
  end
  for _, f in ipairs(FX) do p[#p + 1] = fx_of(per.fx, f[1], track, f[2]) end
  for _, f in ipairs(VERB) do p[#p + 1] = (per.verb or {})[f[1]] or f[2] end
  for _, which in ipairs({ "mute", "solo" }) do
    for t = 1, 16 do p[#p + 1] = (per[which] or {})[t] or 0 end
  end
  p[#p + 1] = per.type or 0
  for t = 1, 16 do p[#p + 1] = (per.rolled or {})[t] or 0 end
  return p
end

-- Random numbers in a given order, then 0.5 forever: the dice for the chances and the drink.
local function dice(...)
  local q = { ... }
  return function()
    if #q == 0 then return 0.5 end
    return table.remove(q, 1)
  end
end

-- The playhead and the pads that sound on each of n ticks.
local function run(st, n)
  local out = {}
  for _ = 1, n do
    local pads, head = {}, nil
    for _, e in ipairs(R.internal.tick(st, {})) do
      if e[1] == "note" and e[2] == "pad" then pads[#pads + 1] = e[3][1] .. "@" .. e[3][2] end
      if e[1] == "page" and e[2] == "play" then head = e[3][1] end
    end
    out[#out + 1] = head .. ":" .. table.concat(pads, ",")
  end
  return table.concat(out, " ")
end

print("\n--- the velocity levels ---")
local got = {}
for n = 1, 8 do got[n] = R.velocity(n) end
equal("level n is round(127n/8): 16 32 48 ... 111 127", got, LEVELS)
check("... and every one is a whole number", (function()
  for n = 1, 8 do if math.type(R.velocity(n)) ~= "integer" then return false end end
  return true
end)(), T.show(got))
got = {}
for n = 1, 8 do got[n] = R.level(R.velocity(n)) end
equal("each level's own velocity is that level, so a step lit at it takes its color",
      got, { 1, 2, 3, 4, 5, 6, 7, 8 })
equal("off is level 0; 1 to 16 is level 1, 17 is 2, 127 is 8",
      { R.level(0), R.level(1), R.level(16), R.level(17), R.level(127) }, { 0, 1, 1, 2, 8 })
equal("the page gets levels, never velocities: a step at 95 goes as 6",
      (function()
        local s = R.new(1)
        s.pattern[R.index(1, 3)] = 95
        return R.steps(s)[3][3]
      end)(), 6)

print("\n--- at load ---")
local st = R.new(1)
equal("a new sequencer holds 512 zeros, every track following the global last step",
      { st.pattern, st.own }, { zeros(CELLS), zeros(16) })
equal("... and starts on track 1 at level 6, the last step 16", { st.track, st.level, st.last },
      { 1, 6, 16 })
local BOOT = { { "page", "vel", { 6 } }, { "page", "track", { 1 } }, { "page", "last", { 16 } },
               { "page", "steps", zeros(32) }, { "page", "bar", { 4, 8 } }, { "page", "rep", { 0 } },
               { "clock", "swing", { 0.5 } }, { "clock", "rate", { 1 } },
               { "save", "list", line(zeros(CELLS)) } }
equal("init draws the selection -- vel 6, track 1, last 16, track 1's 32 steps, a blue cell "
      .. "every 4 in rows of 8, no "
      .. "repeat -- sets the step clock straight, puts the pattern, so the section playing "
      .. "holds the drums from the start, and tells c_kit every effect, which sets none of its own",
      R.internal.init(st, {}), cat(BOOT, fx_all()))
equal("the bank is clipped to 1..10, as [clip 1 10]",
      { R.new(0).bank, R.new(11).bank, R.new(nil).bank, R.new(3).bank }, { 1, 10, 1, 3 })

print("\n--- the step rule ---")
st = R.new(1)
equal("a velocity press selects its level and answers only vel 2",
      R.presses.vel(st, { 2, 100 }), { { "page", "vel", { 2 } } })
equal("... and changes no step", st.pattern, zeros(CELLS))
local want = zeros(CELLS)
want[5] = 32
equal("an off step takes the selected velocity -- 32 -- saved whole, then redrawn",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
want[5] = 0
equal("the same step at the same velocity turns off -- 0",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
R.presses.step(st, { 5, 100 })
R.presses.vel(st, { 6, 100 })
equal("an on step at another velocity turns off too -- 0, not 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
st.pattern[5] = 0.5
want[5] = 95
equal("a rest below 1 is off: a press gives it the selected velocity -- 95",
      R.presses.step(st, { 5, 100 }), edited(want, 1))
equal("a step past the last step is dark, and a press there does nothing -- step 17",
      R.presses.step(st, { 17, 100 }), {})

print("\n--- the selected track ---")
st = R.new(1)
equal("a pad press plays its pad now at full velocity, selects its track, and draws its last step and row",
      R.presses.pad(st, { 2, 90 }), { { "note", "pad", { 2, 127 } }, { "page", "track", { 2 } },
                                      { "page", "last", { 16 } }, { "page", "steps", zeros(32) } })
R.presses.step(st, { 1, 100 })
want = zeros(CELLS)
want[33] = R.velocity(6)
equal("a step press edits the SELECTED track -- track 2's step 1, track 1 untouched",
      st.pattern, want)
local st3 = R.new(3)
equal("bank C's track 2 is pad 34", R.presses.pad(st3, { 2, 90 })[1],
      { "note", "pad", { 34, 127 } })
equal("pads are clipped to 1..16 and levels to 1..8",
      { R.presses.pad(R.new(1), { 0, 90 })[1], R.presses.pad(R.new(1), { 20, 90 })[1],
        R.presses.vel(R.new(1), { 40, 100 })[1] },
      { { "note", "pad", { 1, 127 } }, { "note", "pad", { 16, 127 } }, { "page", "vel", { 8 } } })
equal("a press or a knob with no number in it does nothing",
      { R.presses.step(R.new(1), {}), R.presses.vel(R.new(1), {}), R.presses.pad(R.new(1), {}),
        R.presses.last(R.new(1), {}), R.presses["track-last"](R.new(1), {}) },
      { {}, {}, {}, {}, {} })

print("\n--- knob 2, the global last step ---")
equal("a knob's 0-1 is a step from 1 to 32, 16 just left of noon",
      { R.knob_step(0), R.knob_step(at(16)), R.knob_step(0.5), R.knob_step(1), R.knob_step(7) },
      { 1, 16, 17, 32, 32 })
st = R.new(1)
equal("⛔ at load it is HELD at 16: a knob at step 7 draws the held row and changes nothing",
      R.presses.last(st, { at(7) }), { { "disp", "last-step", { 16, "(7)" } } })
equal("... still held further below", R.presses.last(st, { at(3) }),
      { { "disp", "last-step", { 16, "(3)" } } })
equal("passing 16 releases it, at the step it reached -- 18, saved, a section's",
      R.presses.last(st, { at(18) }), { { "disp", "last-step", { 18 } },
                                       { "save", "list", line(zeros(CELLS), nil, { last = 18 }) },
                                       { "page", "last", { 18 } } })
equal("... and it is live from then on", R.presses.last(st, { at(4) }),
      { { "disp", "last-step", { 4 } }, { "save", "list", line(zeros(CELLS), nil, { last = 4 }) },
        { "page", "last", { 4 } } })
st = R.new(1)
equal("reaching 16 exactly releases it, and saves nothing, the step being the same",
      R.presses.last(st, { at(16) }), { { "disp", "last-step", { 16 } }, { "page", "last", { 16 } } })

print("\n--- knob 3, the selected track's own last step ---")
st = R.new(1)
R.presses.pad(st, { 2, 90 })
equal("held at the selected track's last step, 16: a knob at 7 changes nothing",
      R.presses["track-last"](st, { at(7) }), { { "disp", "pad2-last", { 16, "(7)" } } })
equal("passing 16 releases it: track 2 gets its own last step, saved, and the page shows it",
      R.presses["track-last"](st, { at(20) }),
      { { "disp", "pad2-last", { 20 } }, { "save", "list", line(zeros(CELLS), { 0, 20 }) },
        { "page", "last", { 20 } } })
equal("... the other tracks still follow the global one", { R.last_of(st, 1), R.last_of(st, 2) },
      { 16, 20 })
equal("⛔ selecting another track holds the knob again, at THAT track's last step",
      { R.presses.pad(st, { 3, 90 })[3], R.presses["track-last"](st, { at(20) }) },
      { { "page", "last", { 16 } }, { { "disp", "pad3-last", { 16, "(20)" } } } })
st = R.new(1)
R.presses["track-last"](st, { at(16) })
equal("released AT the track's last step, a track following the global one keeps following",
      { st.own[1], R.presses["track-last"](st, { at(16) }) },
      { 0, { { "disp", "pad1-last", { 16 } } } })
st = R.new(1)
R.presses["track-last"](st, { at(16) })
R.presses["track-last"](st, { at(10) })
R.presses.last(st, { at(16) })
local moved = R.presses.last(st, { at(24) })
equal("knob 2 moves the global last step for every track but the ones with their own: saved, "
      .. "and the selected track's page left alone", { moved[2][1], moved[3], R.last_of(st, 1),
      R.last_of(st, 2) }, { "save", nil, 10, 24 })
st = R.new(1)
R.presses.last(st, { at(16) })
R.presses["track-last"](st, { at(16) })
R.presses.last(st, { at(12) })
equal("⛔ ... and when the selected track follows it, knob 3 is held again, at the new one",
      R.presses["track-last"](st, { at(20) }), { { "disp", "pad1-last", { 12, "(20)" } } })

print("\n--- sync and snap, from the drum screen ---")
equal("sync and snap answer nothing at once: they wait for the global loop's step 1",
      { R.presses.sync(R.new(1), {}), R.presses.snap(R.new(1), {}) }, { {}, {} })

print("\n--- the drum screen ---")
st = R.new(1)
equal("its state: stopped, global 16, track 1, nothing pending, every track at 16 and following",
      R.phone(st), phone(0, 16, 1, 0, {}, {}))
R.presses.pad(st, { 2, 90 })
R.presses["track-last"](st, { at(16) })
R.presses["track-last"](st, { at(5) })
R.internal.start(st, {})
R.presses.snap(st, {})
equal("... playing, track 2 selected with its own 5, a snap pending",
      R.phone(st), phone(1, 16, 2, 2, { [2] = 5 }, { [2] = 1 }))
st = R.new(1)
equal("select picks a track without playing it, and knob 3 is held at its last step",
      { R.presses.select(st, { 7 }), R.presses["track-last"](st, { at(3) }) },
      { { { "page", "track", { 7 } }, { "page", "last", { 16 } }, { "page", "steps", zeros(32) } },
        { { "disp", "pad7-last", { 16, "(3)" } } } })
equal("... clipped to 1..16, and a select with no number does nothing",
      { R.presses.select(R.new(1), { 40 })[1], R.presses.select(R.new(1), {}) },
      { { "page", "track", { 16 } }, {} })

print("\n--- the loops ---")
st = R.new(1)
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 3, 100 })
R.presses.pad(st, { 2, 90 })
R.presses["track-last"](st, { at(4) })
R.presses["track-last"](st, { at(6) })
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 6, 100 })
R.internal.start(st, {})
equal("⛔ each track loops on its own: track 1 every 4, track 2 every 6, the playhead track 2's",
      run(st, 13), "1:1@95,2@95 2: 3:1@95 4: 5:1@95 6:2@95 1:1@95,2@95 2: 3:1@95 4: 5:1@95 6:2@95 "
        .. "1:1@95,2@95")
R.internal.start(st, {})
equal("PLAY starts every loop at step 1 again", run(st, 2), "1:1@95,2@95 2:")
R.presses.sync(st, {})
equal("⛔ sync waits for the global loop's step 1, then every track is back at its own",
      run(st, 6), "3:1@95 4: 1:1@95,2@95 2: 3:1@95 4:")
equal("... each keeping its own last step", { R.last_of(st, 1), R.last_of(st, 2) }, { 4, 6 })
R.internal.start(st, {})
run(st, 2)
R.presses.snap(st, {})
equal("snap waits for the global loop's step 1 too", run(st, 2), "3:1@95 4:")
local landed = R.internal.tick(st, {})
equal("⛔ ... and there every track takes the global last step, saved, and plays from step 1",
      { landed[1][1], landed[1][3][CELLS + 2], landed[2], landed[3], landed[4], landed[5] },
      { "save", 0, { "page", "last", { 4 } }, { "note", "pad", { 1, 95 } },
        { "note", "pad", { 2, 95 } }, { "page", "play", { 1 } } })
equal("... and goes round the global loop from then on", run(st, 4), "2: 3:1@95 4: 1:1@95,2@95")
st = R.new(1)
R.presses["track-last"](st, { at(16) })
R.presses["track-last"](st, { at(9) })
R.presses.snap(st, {})
equal("a snap while stopped lands at PLAY", R.internal.start(st, {}),
      { { "clock", "rate", { 1 } }, { "page", "rep", { 0 } }, { "save", "list", line(zeros(CELLS)) },
        { "page", "last", { 16 } } })
equal("STOP puts the playhead out", R.internal.stop(st, {}), { { "page", "play", { 0 } } })
st = R.new(1)
R.internal.start(st, {})
run(st, 10)
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
equal("a loop shortened under its place wraps into it at once -- 10 in 4 is 3", run(st, 2), "3: 4:")
R.presses.step(st, { 2, 100 })
equal("... and goes round it from there", run(st, 2), "1: 2:1@95")

print("\n--- the restore ---")
st = R.new(1)
local pat = zeros(CELLS)
pat[3], pat[9], pat[39], pat[CELLS] = 20, 77, 50, 127
local own = zeros(16)
own[2], own[16] = 6, 24
equal("a restore takes the 512 and the 16 last steps, puts them straight back, redraws, and "
      .. "tells c_kit every track's volume and pitch",
      R.internal.restore(st, line(pat, own)),
      cat({ { "save", "list", line(pat, own) }, { "page", "last", { 16 } },
            { "page", "steps", row(pat, 1) }, { "page", "bar", { 4, 8 } },
            { "clock", "swing", { 0.5 } } }, kit(), fx_all()))
equal("... and the pattern and the last steps are the line's", { st.pattern, st.own }, { pat, own })
local old = zeros(256)
old[3], old[16], old[17], old[256] = 20, 99, 77, 127
st = R.new(1)
R.internal.restore(st, old)
want = zeros(CELLS)
want[3], want[16], want[33], want[16 * 32 - 16] = 20, 99, 77, 127
equal("⛔ a line of 256 is the old 16-step pattern: each track's sixteen go to its first sixteen",
      st.pattern, want)
st = R.new(1)
st.pattern[200] = 5
R.internal.restore(st, { 1, 2, "x" })
want = zeros(CELLS)
want[1], want[2], want[200] = 1, 2, 5
equal("a short line sets what it holds, a symbol as 0, and leaves the rest", st.pattern, want)
local long = zeros(600)
long[CELLS + 3] = 40
R.internal.restore(st, long)
equal("a long line stops at the settings, each last step clipped to 0..32",
      { #st.pattern, st.own[3], #st.own }, { CELLS, 32, 16 })
equal("an empty restore changes nothing and still puts the pattern back",
      R.internal.restore(R.new(1), {})[1], { "save", "list", line(zeros(CELLS)) })

print("\n--- releases ---")
st = R.new(1)
equal("a release -- velocity 0 -- of a step, a velocity or a pad does nothing",
      { R.presses.step(st, { 5, 0 }), R.presses.vel(st, { 2, 0 }), R.presses.pad(st, { 3, 0 }) },
      { {}, {}, {} })
equal("... and changes nothing", { st.pattern, st.level, st.track }, { zeros(CELLS), 6, 1 })

print("\n--- knob 4, swing ---")
-- 50% to 75%, straight at the knob's bottom, swinging one way only (Brendan, 2026-11-05).
local function sw(n) return (n - 50) / 25 end
st = R.new(1)
equal("⛔ at load it is HELD at 50%: a knob at 62% draws the held row and changes nothing",
      R.presses.swing(st, { sw(62) }), { { "disp", "swing", { 50, "(62)" } } })
equal("... and still held all the way up: 50% is the knob's bottom, so nothing is past it",
      R.presses.swing(st, { 1 }), { { "disp", "swing", { 50, "(75)" } } })
equal("⛔ turned all the way down, to 50%, it is live: the row, and the step clock unchanged",
      R.presses.swing(st, { 0 }), { { "disp", "swing", { 50, "%" } } })
equal("... and from there the step clock takes the swing as a share, saved, a section's",
      R.presses.swing(st, { sw(62) }), { { "disp", "swing", { 62, "%" } },
                                        { "clock", "swing", { 0.62 } },
                                        { "save", "list", line(zeros(CELLS), nil, { swing = 62 }) } })
equal("⛔ its ends are 50% and 75% -- straight at the bottom -- and the knob between is rounded "
      .. "to whole percents",
      { R.presses.swing(st, { 0 })[2][3][1], R.presses.swing(st, { 1 })[2][3][1],
        R.presses.swing(st, { 0.513 })[2][3][1] }, { 0.5, 0.75, 0.63 })
equal("the same swing again saves nothing", R.presses.swing(st, { sw(63) }),
      { { "disp", "swing", { 63, "%" } } })

print("\n--- the phone's swing and global last step ---")
-- The phone sets each as a value, not a knob position (Brendan, 2026-11-04): set-swing and
-- set-last, since swing and last are the knobs' and pass their latch.
st = R.new(1)
R.presses.swing(st, { sw(50) })
equal("set-swing sets the swing at once, live knob or not, the step clock takes it, and it is saved",
      R.presses["set-swing"](st, { 62 }), { { "clock", "swing", { 0.62 } },
                                          { "save", "list", line(zeros(CELLS), nil, { swing = 62 }) } })
equal("... and the phone hears it, after the drunkenness", R.phone(st)[40], 62)
equal("⛔ its ends are 50% and 75%, below 50 is 50, and it rounds to whole percents",
      { R.presses["set-swing"](st, { 10 })[1][3][1], R.presses["set-swing"](st, { 90 })[1][3][1],
        R.presses["set-swing"](st, { 60.4 })[1][3][1] }, { 0.5, 0.75, 0.6 })
equal("the same swing again says nothing", R.presses["set-swing"](st, { 60 }), {})
equal("⛔ knob 4 is held again at the phone's 60%: a knob at 72% changes nothing",
      R.presses.swing(st, { sw(72) }), { { "disp", "swing", { 60, "(72)" } } })
equal("... until it passes 60", R.presses.swing(st, { sw(55) })[1], { "disp", "swing", { 55, "%" } })
equal("set-swing with no number does nothing", { R.presses["set-swing"](st, {}),
      R.presses["set-swing"](st, { "x" }), st.swing }, { {}, {}, 55 })
st = R.new(1)
R.presses.last(st, { at(16) })
equal("set-last sets the global last step at once, live knob or not, saved, and the page shows it",
      R.presses["set-last"](st, { 12 }), { { "save", "list", line(zeros(CELLS), nil, { last = 12 }) },
                                         { "page", "last", { 12 } } })
equal("... for every track that follows it", { R.last_of(st, 1), R.phone(st)[2] }, { 12, 12 })
equal("⛔ knob 2 is held again at the phone's 12: a knob at 20 changes nothing",
      R.presses.last(st, { at(20) }), { { "disp", "last-step", { 12, "(20)" } } })
equal("its ends are 1 and 32, rounded", { (R.presses["set-last"](st, { 0 }) and st.last),
      (R.presses["set-last"](st, { 40 }) and st.last), (R.presses["set-last"](st, { 7.4 }) and st.last) },
      { 1, 32, 7 })
equal("the same step again says nothing", R.presses["set-last"](st, { 7 }), {})
R.presses["track-last"](st, { at(7) })
R.presses["track-last"](st, { at(9) })
local kept = R.presses["set-last"](st, { 20 })
equal("a selected track with its own last step keeps it: the step saved, no page change",
      { #kept, kept[1][1], kept[1][3][CELLS + 69], R.last_of(st, 1), R.last_of(st, 2) },
      { 1, "save", 20, 9, 20 })

print("\n--- the bar, for the song store ---")
-- Which ticks end a bar, from PLAY. A bar is the pattern's loop (Brendan, 2026-11-05): the song
-- store starts a queued section when the global loop comes round to its step 1
-- (ref/module/songs.md).
local function bars(st, n)
  local ends = {}
  for i = 1, n do
    local out = R.internal.tick(st, {})
    for k, e in ipairs(out) do
      if e[1] == "bar" then
        ends[#ends + 1] = i
        check("... bar is the tick's last answer, after the notes", k == #out, "at " .. k)
      end
    end
  end
  return ends
end
st = R.new(1)
R.internal.start(st, {})
equal("the global last step 16: a bar ends on the 16th step and the 32nd", bars(st, 33), { 16, 32 })
st = R.new(1)
st.last = 12
st.num, st.den = 7, 8
R.internal.start(st, {})
equal("⛔ the global last step 12: every 12th, whatever the time signature", bars(st, 30),
      { 12, 24 })
R.internal.start(st, {})
bars(st, 5)
R.internal.start(st, {})
equal("⛔ PLAY counts the loop again from its step 1", bars(st, 12), { 12 })
st = R.new(1)
R.internal.start(st, {})
bars(st, 10)
st.last = 4
equal("a global last step moved under the loop's place wraps into it: 10 in 4 is 3, so the bar "
      .. "ends at its 4, the 2nd step after", bars(st, 6), { 2, 6 })
st = R.new(1)
st.own[1] = 5
R.internal.start(st, {})
equal("a track with its own last step changes nothing: the bar is the global loop's",
      bars(st, 16), { 16 })
st = R.new(1)
R.internal.start(st, {})
st.drunk = 100
equal("drunk, the bar is still counted in the machine's own steps", bars(st, 32), { 16, 32 })
st = R.new(1)
st.last = 8
R.internal.start(st, {})
st.own[2] = 5
run(st, 8)
local next_section = zeros(CELLS)
next_section[1], next_section[33] = 95, 95
R.internal.restore(st, line(next_section, nil, { last = 32 }))
equal("⛔ a section's restore at the end of a bar starts every loop at step 1 on the next step, "
      .. "though its last step, 32, would have taken the old loop's 8 on to 9", run(st, 2),
      "1:1@95,2@95 2:")
equal("... and its bar is its own 32 steps: it ends 30 steps after those two", bars(st, 32), { 30 })

print("\n--- the time signature ---")
-- The top number N sets the page's rows and its blue cells, and how far a last step reaches; the
-- bottom number is a matter of record only (Brendan, 2026-11-05).
st = R.new(1)
local function x(k, v) local t = {} t[k] = v return t end
equal("⛔ the top number steps up by one: 5/4, saved, and the page gets a blue cell every 5 in "
      .. "rows of 5, and the selected track's last step again",
      R.presses.num(st, { 1 }), { { "save", "list", line(zeros(CELLS), nil, x("num", 5)) },
                                  { "page", "bar", { 5, 5 } }, { "page", "last", { 16 } } })
equal("the top number stops at 32 and at 1", { (function()
  for _ = 1, 40 do R.presses.num(st, { 1 }) end
  return st.num
end)(), (function()
  for _ = 1, 40 do R.presses.num(st, { -1 }) end
  return st.num
end)() }, { 32, 1 })
local rows, reaches = {}, {}
for n = 1, 12 do
  st.num = n
  rows[n], reaches[n] = R.row(st), R.reach(st)
end
equal("⛔ a row holds as many groups of N as fit in 8, and all 8 over 8: 1/x to 12/x",
      rows, { 8, 8, 6, 8, 5, 6, 7, 8, 8, 8, 8, 8 })
equal("⛔ ... and a last step reaches four rows: 24 at 3/4, 32 at 4/4, 20 at 5/4, 28 at 7/8",
      reaches, { 32, 32, 24, 32, 20, 24, 28, 32, 32, 32, 32, 32 })
st.num = 32
equal("... and at 32/x, rows of 8 and 32 steps, a blue cell every 32", { R.row(st), R.reach(st),
      R.page_bar(st) }, { 8, 32, { "page", "bar", { 32, 8 } } })
st.num = 6
equal("6/8 is rows of 6 with a blue cell every 6, and 9/8 rows of 8 with one every 9",
      { R.page_bar(st), (function() st.num = 9 return R.page_bar(st) end)() },
      { { "page", "bar", { 6, 6 } }, { "page", "bar", { 9, 8 } } })
st = R.new(1)
equal("⛔ the bottom number is a matter of record: saved, and nothing for the page or the step "
      .. "clock", R.presses.den(st, { 1 }), { { "save", "list", line(zeros(CELLS), nil, x("den", 8)) } })
equal("it steps through 1 2 4 8 16 and stops at 16, and at 1 at the other end",
      { (R.presses.den(st, { 1 }) and st.den), (R.presses.den(st, { 1 }) and st.den),
        (function() for _ = 1, 6 do R.presses.den(st, { -1 }) end return st.den end)() },
      { 16, 16, 1 })
R.internal.start(st, {})
local clocked = {}
for _ = 1, 32 do
  for _, e in ipairs(R.internal.tick(st, {})) do
    if e[1] == "clock" then clocked[#clocked + 1] = e end
  end
end
for _ = 1, 4 do R.presses.den(st, { 1 }) end
for _ = 1, 32 do
  for _, e in ipairs(R.internal.tick(st, {})) do
    if e[1] == "clock" then clocked[#clocked + 1] = e end
  end
end
equal("⛔ ... so the steps go at the same rate at 4/1 and 4/16: sober, no tick changes the clock",
      clocked, {})

print("\n--- the rows of steps ---")
-- A press on a step cell, 1 to 32 along the four rows of eight as the layout table numbers them,
-- is the step its row and column mean: row r and column c, from 0, are step r x row + c + 1.
-- -> the step of the selected track it turned on, which is then turned off again, or "nothing".
local function lands(st, cell)
  local before = {}
  for s = 1, 32 do before[s] = st.pattern[R.index(st.track, s)] end
  local out = R.presses.step(st, { cell, 100 })
  for s = 1, 32 do
    if st.pattern[R.index(st.track, s)] ~= before[s] then
      st.pattern[R.index(st.track, s)] = before[s]
      return s
    end
  end
  return #out == 0 and "nothing" or "an answer and no step"
end
local function cells(st, list)
  local got = {}
  for i, c in ipairs(list) do got[i] = lands(st, c) end
  return got
end
st = R.new(1)
R.presses["set-last"](st, { 32 })
equal("4/4, rows of 8: each cell is its own step, 1 to 32", cells(st, { 1, 8, 9, 25, 32 }),
      { 1, 8, 9, 25, 32 })
R.presses.num(st, { -1 })
equal("⛔ 3/4, rows of 6: a row's first six cells are its steps, the next row goes on from 7, the "
      .. "fourth ends at 24, and a row's seventh and eighth cells do nothing",
      cells(st, { 1, 4, 6, 7, 8, 9, 14, 25, 30, 31, 32 }),
      { 1, 4, 6, "nothing", "nothing", 7, 12, 19, 24, "nothing", "nothing" })
for _ = 1, 2 do R.presses.num(st, { 1 }) end
equal("5/4, rows of 5: the sixth cell does nothing, and the fourth row ends at 20",
      cells(st, { 5, 6, 9, 29, 30 }), { 5, "nothing", 6, 20, "nothing" })
for _ = 1, 4 do R.presses.num(st, { 1 }) end
equal("9/8, rows of 8 again: each cell its own step", cells(st, { 8, 9, 32 }), { 8, 9, 32 })
st = R.new(1)
R.presses.num(st, { -1 })
equal("⛔ a cell whose step is past the last step does nothing: at 3/4 with the last step 16, "
      .. "cell 20 is step 16 and cell 21 step 17", cells(st, { 20, 21 }), { 16, "nothing" })
equal("a press past the row answers nothing at all", R.presses.step(st, { 8, 100 }), {})

print("\n--- the reach ---")
st = R.new(1)
R.presses["set-last"](st, { 32 })
R.presses["set-track-last"](st, { 2, 30 })
R.presses.num(st, { -1 })
equal("⛔ at 3/4 the global last step, 32, and track 2's own, 30, are clipped to 24, on the phone "
      .. "too", { R.global_last(st), R.last_of(st, 1), R.last_of(st, 2), R.phone(st)[2],
                  R.phone(st)[5], R.phone(st)[6] }, { 24, 24, 24, 24, 24, 24 })
R.internal.start(st, {})
equal("⛔ ... so the pattern loops at 24: the bar ends on the 24th step and the 48th",
      bars(st, 49), { 24, 48 })
local held = R.save(st)[3]
equal("... while what was set is kept and saved: 32 and 30", { held[CELLS + 69], held[CELLS + 2] },
      { 32, 30 })
R.presses.num(st, { 1 })
equal("⛔ so at 4/4 again they come back: 32 and 30", { R.global_last(st), R.last_of(st, 2) },
      { 32, 30 })
st = R.new(1)
R.presses.num(st, { 1 })
equal("⛔ the phone's last steps reach exactly that far: at 5/4 a pad's 30 is 20, and set-last "
      .. "30 too", { (R.presses["set-track-last"](st, { 3, 30 }) and st.own[3]),
                     (R.presses["set-last"](st, { 30 }) and st.last) }, { 20, 20 })
equal("... and 20 again, or a track's 20, changes nothing",
      { R.presses["set-last"](st, { 20 }), R.presses["set-last"](st, { 25 }),
        R.presses["set-track-last"](st, { 3, 26 }) }, { {}, {}, {} })
equal("a knob's full turn is the reach: 24, 20, 28, and 32 unless given",
      { R.knob_step(1, 24), R.knob_step(1, 20), R.knob_step(1, 28), R.knob_step(1),
        R.knob_step(0, 20) }, { 24, 20, 28, 32, 1 })
st = R.new(1)
R.presses.num(st, { -1 })
R.presses.last(st, { 0 })
equal("⛔ at 3/4 knob 2 turned all the way up is last step 24, saved",
      R.presses.last(st, { 1 }), { { "disp", "last-step", { 24 } },
                                   { "save", "list", line(zeros(CELLS), nil,
                                                          { num = 3, last = 24 }) },
                                   { "page", "last", { 24 } } })
R.presses.pad(st, { 2, 90 })
R.presses["track-last"](st, { 0 })
equal("⛔ ... and knob 3 all the way up is the selected track's 24",
      R.presses["track-last"](st, { 1 })[1], { "disp", "pad2-last", { 24 } })
st = R.new(1)
R.presses.last(st, { at(16) })
R.presses.den(st, { 1 })
equal("knob 2 live, the bottom number moves nothing: still live",
      R.presses.last(st, { at(10) })[1], { "disp", "last-step", { 10 } })
for _ = 1, 4 do R.presses.num(st, { 1 }) end
R.presses.last(st, { at(10) })
equal("... nor does a top number with the same reach, 8 for 4", R.presses.last(st, { at(11) })[1],
      { "disp", "last-step", { 11 } })
R.presses.num(st, { -1 })
equal("⛔ but a top number that moves the reach holds knobs 2 and 3 again, a turn of each now "
      .. "standing for another step: 7/8, knob 2 at 0.9 is 25",
      { R.presses.last(st, { 0.9 }), R.presses["track-last"](st, { 0.9 }) },
      { { { "disp", "last-step", { 11, "(25)" } } }, { { "disp", "pad1-last", { 11, "(25)" } } } })

print("\n--- the drum screen's pads ---")
-- Each pad dragged, for its own track, selected or not (Brendan, 2026-11-05): a volume, a pitch,
-- a randomness or a last step, each as it stands.
st = R.new(1)
equal("drunkenness, 0 to 100, rounded and saved",
      { R.presses.drunk(st, { 33.4 }), R.presses.drunk(st, { 140 })[1][3][CELLS + 67] },
      { { { "save", "list", line(zeros(CELLS), nil, x("drunk", 33)) } }, 100 })
st = R.new(1)
equal("⛔ a pad's volume is ITS track's, not the selected one's: saved, and to c_kit for its pad",
      R.presses.vol(st, { 3, -6 }), { { "save", "list", line(zeros(CELLS), nil, { vol = { [3] = -6 } }) },
                                      { "note", "vol", { 3, -6 } } })
equal("... -30 to +6 dB, in whole dB",
      { R.presses.vol(st, { 3, -50 })[2], R.presses.vol(st, { 3, 9 })[2],
        R.presses.vol(st, { 3, 2.4 })[2] },
      { { "note", "vol", { 3, -30 } }, { "note", "vol", { 3, 6 } }, { "note", "vol", { 3, 2 } } })
equal("⛔ a pad's pitch: saved, and to c_kit", R.presses.pitch(st, { 5, 7 }),
      { { "save", "list", line(zeros(CELLS), nil, { vol = { [3] = 2 }, pitch = { [5] = 7 } }) },
        { "note", "pitch", { 5, 7 } } })
equal("... -12 to +12 semitones, whole",
      { R.presses.pitch(st, { 5, -20 })[2], R.presses.pitch(st, { 5, 13 })[2],
        R.presses.pitch(st, { 5, -3.6 })[2] },
      { { "note", "pitch", { 5, -12 } }, { "note", "pitch", { 5, 12 } },
        { "note", "pitch", { 5, -4 } } })
equal("⛔ a pad's randomness, 0 to 100: saved, and nothing for c_kit",
      R.presses.randomness(st, { 2, 40.4 }),
      { { "save", "list", line(zeros(CELLS), nil, { randomness = { [2] = 40 }, vol = { [3] = 2 },
                                                    pitch = { [5] = -4 } }) } })
equal("... clipped to 0 and 100", { (R.presses.randomness(st, { 2, -5 }) and st.randomness[2]),
                                    (R.presses.randomness(st, { 2, 150 }) and st.randomness[2]) },
      { 0, 100 })
equal("the same value again says nothing",
      { R.presses.vol(st, { 3, 2 }), R.presses.pitch(st, { 5, -4 }),
        R.presses.randomness(st, { 2, 100 }) }, { {}, {}, {} })
equal("without a track and a number, nothing",
      { R.presses.vol(st, {}), R.presses.vol(st, { 3 }), R.presses.pitch(st, { "x", 4 }),
        R.presses.randomness(st, { 2, "x" }), R.presses["set-track-last"](st, { 2 }) },
      { {}, {}, {}, {}, {} })
equal("a track past 16 is 16, and bank C's track 2 is pad 34 for c_kit",
      { R.presses.vol(st, { 40, -3 })[2], R.presses.vol(R.new(3), { 2, -3 })[2] },
      { { "note", "vol", { 16, -3 } }, { "note", "vol", { 34, -3 } } })
equal("⛔ the drum screen hears every track's volume, pitch and randomness",
      R.phone(st), phone(0, 16, 1, 0, {}, {}, nil, { vol = { [3] = 2, [16] = -3 },
                                                     pitch = { [5] = -4 },
                                                     randomness = { [2] = 100 } }))
st = R.new(1)
R.presses.select(st, { 3 })
R.presses["track-last"](st, { at(16) })
equal("⛔ a pad's last step, its own track's: saved, and the page's, the track being selected",
      R.presses["set-track-last"](st, { 3, 9 }),
      { { "save", "list", line(zeros(CELLS), { [3] = 9 }) }, { "page", "last", { 9 } } })
equal("⛔ ... and knob 3 is held again at it",
      R.presses["track-last"](st, { at(20) }), { { "disp", "pad3-last", { 9, "(20)" } } })
equal("another track's: saved, and the page and knob 3 left alone",
      { R.presses["set-track-last"](st, { 5, 4 }), R.presses["track-last"](st, { at(20) }) },
      { { { "save", "list", line(zeros(CELLS), { [3] = 9, [5] = 4 }) } },
        { { "disp", "pad3-last", { 9, "(20)" } } } })
equal("the step a track already has says nothing, so one that follows the global step goes on "
      .. "following", { R.presses["set-track-last"](st, { 7, 16 }), st.own[7] }, { {}, 0 })
equal("1 to 32, whole", { (R.presses["set-track-last"](st, { 7, 0 }) and st.own[7]),
                          (R.presses["set-track-last"](st, { 7, 40 }) and st.own[7]),
                          (R.presses["set-track-last"](st, { 7, 6.4 }) and st.own[7]) },
      { 1, 32, 6 })
equal("... and the phone shows each track's last step and its dot",
      { R.phone(st)[4 + 5], R.phone(st)[20 + 5], R.phone(st)[4 + 7], R.phone(st)[20 + 7] },
      { 4, 1, 6, 1 })

print("\n--- randomness ---")
-- At R% each step has an R% chance of ignoring what is written and flipping a coin: played or
-- not, and played at one of the eight levels (Brendan, 2026-11-05, after the DrumBrute's). The
-- dice of a track that rolls, step by step: the chance, then the coin, then the level if played.
st = R.new(1)
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 3, 100 })
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.internal.start(st, {})
st.rand = dice(0.1, 0.2)
equal("⛔ at 0 the pattern plays as written, and nothing is rolled",
      { run(st, 4), st.rand(), st.rand() }, { "1:1@95 2: 3:1@95 4:", 0.1, 0.2 })
R.presses.randomness(st, { 1, 100 })
R.internal.start(st, {})
st.rand = dice(0.99, 0.7, 0.99, 0.2, 0.5, 0.99, 0.3, 0.999, 0.99, 0.6, 0.123)
equal("⛔ at 100 every step flips the coin, a roll of 0.99 too: step 1's hit dropped, empty step 2 "
      .. "played at level 5 (79), step 3 at level 8 (127), step 4 silent",
      { run(st, 4), st.rand() }, { "1: 2:1@79 3:1@127 4:", 0.123 })
R.presses.randomness(st, { 1, 30 })
R.internal.start(st, {})
st.rand = dice(0.29, 0.7, 0.30, 0.31, 0.0, 0.1, 0.0, 0.123)
equal("⛔ at 30 a roll under 0.3 flips the coin -- step 1 silent, step 4 played at level 1 (16) -- "
      .. "and any other plays as written, with no coin", { run(st, 4), st.rand() },
      { "1: 2: 3:1@95 4:1@16", 0.123 })
st = R.new(1)
for k = 1, 4 do R.presses.select(st, { 2 }) R.presses.step(st, { k, 100 }) end
R.presses.randomness(st, { 1, 100 })
R.internal.start(st, {})
st.rand = dice(0, 0.9, 0, 0.9, 0, 0.9, 0, 0.9, 0.123)
equal("it is a track's own: track 1 at 100, all silent coins, and track 2 beside it as written",
      { run(st, 4), st.rand() }, { "1:2@95 2:2@95 3:2@95 4:2@95", 0.123 })
-- On sequencers of their own, at 50: half the steps flip a coin, so a quarter of an empty
-- track's steps play, and three quarters of a full one's.
local function share(fill, r)
  local q = R.new(1)
  for k = 1, 32 do q.pattern[R.index(1, k)] = fill and 95 or 0 end
  q.last, q.randomness[1], q.rand = 32, r, math.random
  R.internal.start(q, {})
  local played, levels = 0, {}
  for _ = 1, 8000 do
    for _, e in ipairs(R.internal.tick(q, {})) do
      if e[1] == "note" then played, levels[e[3][2]] = played + 1, true end
    end
  end
  local seen = {}
  for v in pairs(levels) do seen[#seen + 1] = v end
  table.sort(seen)
  return played, seen
end
local sparse = share(false, 50)
local busy = share(true, 50)
equal("⛔ at 50 it adds hits to an empty track: a quarter of 8000 steps, between 1850 and 2150",
      sparse >= 1850 and sparse <= 2150 or sparse, true)
equal("⛔ ... and drops them from a full one: three quarters, between 5850 and 6150",
      busy >= 5850 and busy <= 6150 or busy, true)
local _, seen = share(true, 100)
equal("at 100 a played step takes one of the eight levels, and every one comes up", seen, LEVELS)
check("randomness is saved, as skip and move were", (function()
  local q = R.new(1)
  return R.presses.randomness(q, { 4, 25 })[1][3][CELLS + 16 + 4] == 25
end)(), "")

print("\n--- drunkenness ---")
-- At x, the slider's 0 to 1, a step strays with the chance x/3 + 2x^4/3, by up to x + x^4 steps
-- (Brendan, 2026-11-05: every step at the top, by up to two; low settings subtle).
local function near(a, b) return math.abs(a - b) < 1e-9 end
check("⛔ at the top every step strays, by up to two steps: chance 1, reach 2",
      near(R.drunk_chance(100), 1) and near(R.drunk_reach(100), 2),
      T.show({ R.drunk_chance(100), R.drunk_reach(100) }))
check("⛔ low it stays subtle: at 20% one step in fifteen, by up to a fifth of a step",
      near(R.drunk_chance(20), 0.2 / 3 + 2 * 0.2 ^ 4 / 3) and R.drunk_chance(20) < 0.07
      and near(R.drunk_reach(20), 0.2016),
      T.show({ R.drunk_chance(20), R.drunk_reach(20) }))
check("⛔ ... and it ramps steeply near the top: at 50% one in five by up to 0.56, at 90% three "
      .. "in four by up to 1.56",
      near(R.drunk_chance(50), 5 / 24) and near(R.drunk_reach(50), 0.5625)
      and near(R.drunk_chance(90), 0.7374) and near(R.drunk_reach(90), 1.5561),
      T.show({ R.drunk_chance(50), R.drunk_reach(50), R.drunk_chance(90), R.drunk_reach(90) }))
check("... and it never falls as the slider rises", (function()
  for k = 1, 100 do
    if R.drunk_chance(k) < R.drunk_chance(k - 1) or R.drunk_reach(k) < R.drunk_reach(k - 1) then
      return false
    end
  end
  return true
end)(), "")
equal("sober, nothing strays: chance and reach 0", { R.drunk_chance(0), R.drunk_reach(0) }, { 0, 0 })
st = R.new(1)
R.internal.start(st, {})
equal("sober, a step changes nothing of the clock's", #R.internal.tick(st, {}), 1)
R.presses.drunk(st, { 50 })
st.rand = dice(0, 1)
equal("drunk 50: a step that strays can last 0.56 of a step longer -- the clock's rate 1/1.5625",
      R.internal.tick(st, {})[2], { "clock", "rate", { 1 / 1.5625 } })
st.rand = dice(0, 0)
equal("... or 0.56 shorter -- rate 1/0.4375", R.internal.tick(st, {})[2],
      { "clock", "rate", { 1 / 0.4375 } })
st.rand = dice(0.21, 0)
equal("drunk 50, a step strays about one time in five: a roll of 0.21 plays on time -- rate 1, "
      .. "and no size is rolled", { R.internal.tick(st, {})[2], st.rand() },
      { { "clock", "rate", { 1 } }, 0 })
R.presses.drunk(st, { 100 })
st.rand = dice(0.999, 1)
equal("⛔ drunk 100: every step strays -- a roll of 0.999 still does -- up to two steps longer, "
      .. "rate 1/3", R.internal.tick(st, {})[2], { "clock", "rate", { 1 / 3 } })
st.rand = dice(0.999, 0)
equal("⛔ ... and two steps shorter is held at an eighth of a step, never nothing -- rate 8",
      R.internal.tick(st, {})[2], { "clock", "rate", { 8 } })
st.rand = dice(0.5, 0.25)
equal("... as is a whole step shorter -- rate 8 again, so nothing sent", #R.internal.tick(st, {}), 1)
st.rand = dice(0.5, 0.75)
equal("a whole step longer: rate 1/2", R.internal.tick(st, {})[2], { "clock", "rate", { 0.5 } })
st.rand = dice(0, 0.5)
equal("a stray of the middle is a step as written: rate 1",
      R.internal.tick(st, {})[2], { "clock", "rate", { 1 } })
-- On a sequencer of its own: the last roll leaves the rate wherever it fell.
local strays, d = 0, R.new(1)
R.internal.start(d, {})
R.presses.drunk(d, { 100 })
d.rand = math.random
for _ = 1, 3000 do
  R.internal.tick(d, {})
  if d.rate ~= 1 then strays = strays + 1 end
end
equal("⛔ drunk 100, over 3000 steps every one strays", strays, 3000)
strays = 0
R.presses.drunk(d, { 50 })
for _ = 1, 12000 do
  R.internal.tick(d, {})
  if d.rate ~= 1 then strays = strays + 1 end
end
equal("drunk 50, over 12000 steps about one in five, 2500: between 2320 and 2680",
      strays >= 2320 and strays <= 2680 or strays, true)
R.presses.drunk(st, { 0 })
st.rand = dice(0)
equal("sober again, the rate is 1 and the drift is kept: nothing pulls it back",
      #R.internal.tick(st, {}), 1)

print("\n--- the repeat pads ---")
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(8) })
equal("held before anything has played, a repeat pad does nothing", R.presses.rep(st, { 3, 127 }),
      {})
R.internal.start(st, {})
run(st, 5)
equal("⛔ pad 3 held after step 5: the page shows it, and every track replays steps 3 4 5",
      { R.presses.rep(st, { 3, 127 }), run(st, 6) },
      { { { "page", "rep", { 3 } } }, "3:1@95 4:1@95 5:1@95 3:1@95 4:1@95 5:1@95" })
equal("letting go of another pad changes nothing", R.presses.rep(st, { 2, 0 }), {})
equal("⛔ let go: the page clears, and every track plays from where it would have been -- six "
      .. "steps after 5 in a loop of 8, step 4", { R.presses.rep(st, { 3, 0 }), run(st, 2) },
      { { { "page", "rep", { 0 } }, { "note", "tape-off", {} } }, "4:1@95 5:1@95" })
R.presses.rep(st, { 1, 127 })
equal("pad 1 replays the last step heard", run(st, 3), "5:1@95 5:1@95 5:1@95")
R.presses.rep(st, { 4, 127 })
equal("... and a second pad pressed takes over, from the steps heard: 5 5 5 5", run(st, 2),
      "5:1@95 5:1@95")
equal("PLAY lets go of a held repeat", { R.internal.start(st, {})[2], run(st, 2) },
      { { "page", "rep", { 0 } }, "1:1@95 2:1@95" })
-- A repeat plays exactly what was played: each track's hit and its velocity as its randomness
-- chose them that time, and each step's drunk length, with nothing rolled (Brendan, 2026-11-05).
-- The dice of a track at 100, step by step: 0 flips the coin, then the coin, then the level.
st = R.new(1)
for k = 1, 4 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(8) })
R.presses.randomness(st, { 1, 100 })
R.internal.start(st, {})
st.rand = dice(0, 0.1, 0.99, 0, 0.9, 0, 0.2, 0, 0, 0.3, 0.5)
equal("track 1 at 100: four coins, played at 127, silent, 16 and 79", run(st, 4),
      "1:1@127 2: 3:1@16 4:1@79")
R.presses.rep(st, { 3, 127 })
st.rand = dice(0.123)
equal("⛔ pad 3 held replays steps 2 3 4 exactly as their coins fell, on every pass, three "
      .. "passes, and rolls no die", { run(st, 9), st.rand() },
      { "2: 3:1@16 4:1@79 2: 3:1@16 4:1@79 2: 3:1@16 4:1@79", 0.123 })
R.presses.rep(st, { 3, 0 })
st.rand = dice(0, 0.1, 0.99, 0, 0.9)
equal("⛔ let go, it plays on from where it would have been, thirteen steps in a loop of 8, step "
      .. "6, and rolls again: a coin at 127, then silent", { run(st, 2), st.rand() },
      { "6:1@127 7:", 0.5 })
st = R.new(1)
R.internal.start(st, {})
R.presses.drunk(st, { 100 })
st.rand = dice(0.5, 1, 0.5, 0, 0.5, 0.75)
-- The step clock's rate sent on each of n ticks, "-" for none.
local function lengths(q, n)
  local out = {}
  for _ = 1, n do
    local sent = "-"
    for _, e in ipairs(R.internal.tick(q, {})) do
      if e[1] == "clock" then sent = e[3][1] end
    end
    out[#out + 1] = sent
  end
  return out
end
equal("drunk 100: three steps two longer, two shorter and one longer -- rates 1/3, 8, 1/2",
      lengths(st, 3), { 1 / 3, 8, 0.5 })
R.presses.rep(st, { 3, 127 })
st.rand = dice(0.123)
equal("⛔ pad 3 held replays each step's length as it was, on every pass, and rolls no die",
      { lengths(st, 6), st.rand() }, { { 1 / 3, 8, 0.5, 1 / 3, 8, 0.5 }, 0.123 })
st.rand = dice(0.5, 0.5)
equal("... and let go, the next step's length is rolled again: on time, rate 1",
      { R.presses.rep(st, { 3, 0 })[1], lengths(st, 1), st.rand() },
      { { "page", "rep", { 0 } }, { 1 }, 0.5 })
st = R.new(1)
for _, t in ipairs({ 1, 2 }) do
  R.presses.select(st, { t })
  for k = 1, 4 do R.presses.step(st, { k, 100 }) end
end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.randomness(st, { 2, 100 })
R.internal.start(st, {})
st.rand = dice(0, 0.1, 0.99, 0, 0.1, 0)
run(st, 2)
R.presses.rep(st, { 2, 127 })
st.rand = dice(0.123)
equal("track 2's coins, 127 and 16, held by pad 2 beside track 1 as written", run(st, 2),
      "1:1@95,2@127 2:1@95,2@16")
R.presses.mute(st, { 2, 1 })
equal("⛔ track 2 muted while the repeat is held is silent in it from the next step", run(st, 2),
      "1:1@95 2:1@95")
R.presses.solo(st, { 2, 1 })
equal("⛔ ... and soloed, it alone plays the repeat, its coins as they fell, though muted",
      { run(st, 2), st.rand() }, { "1:2@127 2:2@16", 0.123 })
st = R.new(1)
for k = 1, 4 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(8) })
R.presses.randomness(st, { 1, 100 })
R.internal.start(st, {})
st.rand = dice(0, 0.1, 0.99)
run(st, 1)
equal("pad 4 pressed with one step played since PLAY: the page shows it at once",
      R.presses.rep(st, { 4, 127 }), { { "page", "rep", { 4 } } })
st.rand = dice(0, 0.9, 0, 0.2, 0, 0, 0.3, 0.5, 0.123)
equal("⛔ ... and the next three are played and kept, coins rolled, until there are four; then "
      .. "the four repeat as they fell", { run(st, 7), st.rand() },
      { "2: 3:1@16 4:1@79 1:1@127 2: 3:1@16 4:1@79", 0.123 })
st = R.new(1)
for k = 1, 4 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.internal.start(st, {})
run(st, 2)
R.presses.rep(st, { 2, 127 })
R.presses.step(st, { 1, 100 })
equal("⛔ a step turned off under a held repeat is still heard in it: it replays what was heard",
      run(st, 2), "1:1@95 2:1@95")
R.presses.rep(st, { 2, 0 })
equal("... and let go, the loop plays on as the pattern now stands, step 1 off", run(st, 2),
      "1: 2:1@95")
R.presses.rep(st, { 2, 127 })
R.internal.restore(st, line(zeros(CELLS)))
equal("⛔ a section's restore under a held repeat: the repeat goes on, as it was heard",
      run(st, 2), "1: 2:1@95")
R.presses.rep(st, { 2, 0 })
equal("... and let go, the new section plays from where its loops would have been, steps 3 and "
      .. "4, empty", run(st, 2), "3: 4:")

print("\n--- a held repeat's tails ---")
-- What a tick tells c_kit of the tails: its tape and tape-off, and nothing else of its answers.
local function tails(out)
  local got = {}
  for _, e in ipairs(out) do
    if e[1] == "note" and (e[2] == "tape" or e[2] == "tape-off") then
      got[#got + 1] = { e[2], table.unpack(e[3]) }
    end
  end
  return got
end
-- The first of a tick's answers that is a hit, and where the tails' message comes against it.
local function before_hit(out)
  for _, e in ipairs(out) do
    if e[1] == "note" and e[2] == "pad" then return false end
    if e[1] == "note" and e[2] == "tape" then return true end
  end
  return false
end
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
st.bpm = 120
R.internal.start(st, {})
run(st, 5)
equal("pressed, nothing yet: the recording runs until the replay begins, at the next step",
      R.presses.rep(st, { 4, 127 }), { { "page", "rep", { 4 } } })
local began = R.internal.tick(st, {})
equal("⛔ the step the replay begins on tells c_kit: 4 steps at 120 BPM ran 500 ms, and take 4 steps",
      tails(began), { { "tape", 500, 4 } })
check("⛔ ... before the step's hits, so they send nothing", before_hit(began), T.show(began))
equal("the replay's other steps tell it nothing, nor the next pass's first",
      (function()
        local n = {}
        for _ = 1, 7 do for _, e in ipairs(tails(R.internal.tick(st, {}))) do n[#n + 1] = e end end
        return n
      end)(), {})
equal("⛔ let go: the page clears, and c_kit hears the tails stop", R.presses.rep(st, { 4, 0 }),
      { { "page", "rep", { 0 } }, { "note", "tape-off", {} } })
equal("... once", R.presses.rep(st, { 4, 0 }), {})
equal("⛔ a repeat let go before its first step never began: nothing to stop",
      (function()
        R.presses.rep(st, { 2, 127 })
        return R.presses.rep(st, { 2, 0 })
      end)(), { { "page", "rep", { 0 } } })
equal("the steps' lengths are as the tempo was then: pad 1 at 60 BPM is 250 ms, whatever is in force",
      (function()
        st.bpm = 60
        R.internal.tick(st, {})
        st.bpm = 240
        R.presses.rep(st, { 1, 127 })
        return tails(R.internal.tick(st, {}))
      end)(), { { "tape", 250, 1 } })
equal("⛔ a tick brings the tempo bus's BPM, which the step it decides keeps: 100 BPM is 150 ms",
      (function()
        local q = R.new(1)
        R.internal.start(q, {})
        R.internal.tick(q, { 100 })
        R.presses.rep(q, { 1, 127 })
        return tails(R.internal.tick(q, { 100 }))
      end)(), { { "tape", 150, 1 } })
equal("⛔ pressed short of its length, no tails until its steps are there: then all four's",
      (function()
        local q = R.new(1)
        q.bpm = 120
        R.internal.start(q, {})
        R.internal.tick(q, {})
        R.presses.rep(q, { 4, 127 })
        local got = {}
        for k = 1, 4 do got[k] = tails(R.internal.tick(q, {})) end
        return got
      end)(), { {}, {}, {}, { { "tape", 500, 4 } } })
equal("⛔ a second pad under a held repeat begins again, at its own length",
      (function()
        R.presses.rep(st, { 3, 127 })
        return tails(R.internal.tick(st, {}))
      end)()[1][1], "tape")
equal("⛔ PLAY lets go, and the tails stop", tails(R.internal.start(st, {})), { { "tape-off" } })
st.bpm = 120
run(st, 2)
R.presses.rep(st, { 1, 127 })
R.internal.tick(st, {})
equal("⛔ STOP stops the tails too, since the hits have stopped", tails(R.internal.stop(st, {})),
      { { "tape-off" } })
equal("... so letting go then says it once only", R.presses.rep(st, { 1, 0 }),
      { { "page", "rep", { 0 } } })
R.internal.start(st, {})
run(st, 2)
R.presses.rep(st, { 1, 127 })
R.internal.tick(st, {})
equal("⛔ a pad pressed short of its length under a held repeat plays fresh steps: the tails stop",
      R.presses.rep(st, { 4, 127 }), { { "page", "rep", { 4 } }, { "note", "tape-off", {} } })
-- Swing bends a pair: at 75% the first of each pair runs 1.5 steps and the second 0.5.
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
st.bpm = 120
R.presses["set-swing"](st, { 75 })
R.internal.start(st, {})
run(st, 4)
R.presses.rep(st, { 2, 127 })
equal("⛔ two steps at 75% keep their pair: 250 ms in 2 steps, the swing in both, so the speed is 1",
      tails(R.internal.tick(st, {})), { { "tape", 250, 2 } })
R.presses.rep(st, { 2, 0 })
run(st, 1)
R.presses.rep(st, { 1, 127 })
equal("⛔ one step plays alternately long and short: 125 ms in 1 step, no swing, so the speed is 1 and "
      .. "it comes round on the hits every second time", tails(R.internal.tick(st, {})),
      { { "tape", 125, 1 } })
equal("⛔ swing and drunk together, a pair of three steps and one: 1.5 x 3 and 0.5 x 1, five steps, "
      .. "as the pair ran, and comes round on it", (function()
  local q = R.new(1)
  q.bpm = 120
  R.presses["set-swing"](q, { 75 })
  R.internal.start(q, {})
  R.presses.drunk(q, { 100 })
  q.rand = dice(0.5, 1, 0.5, 0.5)
  run(q, 2)
  R.presses.rep(q, { 2, 127 })
  return tails(R.internal.tick(q, {}))
end)(), { { "tape", 625, 5 } })
-- Drunk: a step's own length, in steps, is its own.
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
st.bpm = 120
R.internal.start(st, {})
R.presses.drunk(st, { 100 })
st.rand = dice(0.5, 1, 0.5, 0.25, 0.5, 0.5)
run(st, 3)
equal("three drunk steps, three, an eighth and one steps long, as they ran", (function()
  R.presses.rep(st, { 3, 127 })
  st.rand = dice(0.123)
  return { tails(R.internal.tick(st, {})), st.rand() }
end)(), { { { "tape", 515.625, 4.125 } }, 0.123 })
equal("⛔ a repeat longer than the tape keeps to the tape: 4 steps at 5 BPM fit, 12000 ms ...",
      (function()
        local q = R.new(1)
        q.bpm = 5
        R.internal.start(q, {})
        run(q, 4)
        R.presses.rep(q, { 4, 127 })
        return tails(R.internal.tick(q, {}))
      end)(), { { "tape", 12000, 4 } })
equal("... and the same four drunk, three steps each, play its last 12000 in 12 steps' time",
      (function()
        local q = R.new(1)
        q.bpm = 5
        R.internal.start(q, {})
        R.presses.drunk(q, { 100 })
        q.rand = dice(0, 1, 0, 1, 0, 1, 0, 1)
        run(q, 4)
        R.presses.rep(q, { 4, 127 })
        return tails(R.internal.tick(q, {}))
      end)(), { { "tape", 12000, 12 } })

print("\n--- the 500 BPM repeat and the saved tempo ---")
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
st.bpm = 120
R.internal.start(st, {})
run(st, 2)
equal("⛔ pad-35 pressed: u_tempo holds 500, its lamp lights, and the last step repeats, no repeat "
      .. "pad's lamp lit", R.presses.fast(st, { 1, 127 }),
      { { "tempo", "fast", { 1 } }, { "page", "fast", { 1 } }, { "page", "rep", { 0 } } })
st.bpm = 500
local tick1 = R.internal.tick(st, {})
equal("⛔ the replay begins at the next step, its tails told as any repeat's: one step at 120 BPM",
      tails(tick1), { { "tape", 125, 1 } })
equal("⛔ held, step 2 plays over and over", run(st, 5), "2:1@95 2:1@95 2:1@95 2:1@95 2:1@95")
equal("⛔ ... and the loops wait: no bar, in many times the loop of 4",
      (function()
        local n = 0
        for _ = 1, 20 do
          for _, e in ipairs(R.internal.tick(st, {})) do if e[1] == "bar" then n = n + 1 end end
        end
        return n
      end)(), 0)
equal("a repeat pad while it is held does nothing, press or release",
      { R.presses.rep(st, { 3, 127 }), R.presses.rep(st, { 1, 0 }) }, { {}, {} })
equal("⛔ let go: the tempo back first, its lamp out, the repeat let go and the tails stopped",
      R.presses.fast(st, { 1, 0 }),
      { { "tempo", "fast", { 0 } }, { "page", "fast", { 0 } }, { "page", "rep", { 0 } },
        { "note", "tape-off", {} } })
equal("⛔ ... and the pattern carries on from the step it was pressed on: 3, 4, then 1", run(st, 3),
      "3:1@95 4:1@95 1:1@95")
equal("... the release once only", R.presses.fast(st, { 1, 0 }), {})
R.presses.fast(st, { 1, 127 })
R.internal.tick(st, {})
equal("⛔ PLAY lets go of it, the tempo back too", (function()
  local e = R.internal.start(st, {})
  local got = {}
  for _, x in ipairs(e) do
    if x[1] == "tempo" or x[2] == "fast" or x[2] == "tape-off" then got[#got + 1] = x[2] end
  end
  return got
end)(), { "tape-off", "fast", "fast" })
equal("... and its release after that says nothing", R.presses.fast(st, { 1, 0 }), {})
equal("⛔ pressed before anything has played: the tempo and its lamp, and no repeat, as a repeat pad",
      (function()
        local q = R.new(1)
        return R.presses.fast(q, { 1, 127 })
      end)(), { { "tempo", "fast", { 1 } }, { "page", "fast", { 1 } } })
equal("⛔ pad-38 pressed: its lamp lights, and u_song is asked for the saved tempo",
      R.presses.recall(st, { 1, 127 }),
      { { "page", "recall", { 1 } }, { "song", "recall", { "tempo" } } })
equal("... and let go, only its lamp", R.presses.recall(st, { 1, 0 }),
      { { "page", "recall", { 0 } } })

print("\n--- a track's random pitch ---")
-- The pitches told to c_kit on a tick, and whether each comes before its track's hit.
local function pitched(out)
  local got = {}
  for _, e in ipairs(out) do
    if e[1] == "note" and (e[2] == "pitch" or e[2] == "pad") then
      got[#got + 1] = e[2] .. " " .. table.concat(e[3], " ")
    end
  end
  return table.concat(got, ", ")
end
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.randomness(st, { 1, 50 })
R.internal.start(st, {})
-- The dice: 0 fires the roll and 0.9 doesn't, the coin plays below 0.5, the level, then the pitch.
st.rand = dice(0, 0.1, 0.99)
equal("off: a rolled hit plays at its set pitch, and rolls three dice", pitched(R.internal.tick(st, {})),
      "pad 1 127")
equal("⛔ off, the next die is untouched: no fourth was rolled", st.rand(), 0.5)
equal("rnd-pitch on is saved, 776 numbers, and tells c_kit nothing",
      R.presses["rnd-pitch"](st, { 1, 1 }),
      { { "save", "list", line((function()
        local z = zeros(CELLS)
        for k = 1, 8 do z[k] = 95 end
        return z
      end)(), nil, { randomness = { [1] = 50 }, last = 4, rolled = { [1] = 1 } }) } })
equal("the same again does nothing", R.presses["rnd-pitch"](st, { 1, 1 }), {})
equal("a message with no number does nothing", R.presses["rnd-pitch"](st, { 1 }), {})
st.rand = dice(0, 0.1, 0.99, 1 / 25 * 19.5, 0.123)
equal("⛔ on: a rolled hit takes a pitch of its own, die 0.78 of 25 places, +7, told before the hit",
      pitched(R.internal.tick(st, {})), "pitch 1 7, pad 1 127")
equal("⛔ ... rolling one more die, the fourth", st.rand(), 0.123)
st.rand = dice(0.9)
equal("⛔ a roll that does not fire leaves the written step: back at its set pitch, 0, before the hit",
      pitched(R.internal.tick(st, {})), "pitch 1 0, pad 1 95")
st.rand = dice(0.9)
equal("... and the next, at its set pitch already, tells nothing", pitched(R.internal.tick(st, {})),
      "pad 1 95")
st.rand = dice(0, 0.9, 0.123)
equal("⛔ a coin that silences the hit rolls no pitch and tells none", { pitched(R.internal.tick(st, {})),
      st.rand() }, { "", 0.123 })
st.rand = dice(0, 0.1, 0.99, 0)
equal("the die at its bottom is -12", pitched(R.internal.tick(st, {})), "pitch 1 -12, pad 1 127")
st.rand = dice(0, 0.1, 0.99, 0.9999999)
equal("... and at its top +12", pitched(R.internal.tick(st, {})), "pitch 1 12, pad 1 127")
R.presses.pitch(st, { 1, 6 })
st.rand = dice(0, 0.1, 0.99, 0.9999999)
equal("⛔ around the set pitch, kept to the range: 6 + 12 is +12", pitched(R.internal.tick(st, {})),
      "pitch 1 12, pad 1 127")
st.rand = dice(0, 0.1, 0.99, 0)
equal("... and 6 - 12 is -6", pitched(R.internal.tick(st, {})), "pitch 1 -6, pad 1 127")
R.presses.pitch(st, { 1, -6 })
st.rand = dice(0, 0.1, 0.99, 0)
equal("⛔ ... -6 - 12 kept to -12", pitched(R.internal.tick(st, {})), "pitch 1 -12, pad 1 127")
R.presses.pitch(st, { 1, 0 })
st.rand = dice(0, 0.1, 0.99, 0.75)
equal("a set pitch dragged in between is what c_kit holds: told the pitch it rolled, die 0.75, +6",
      pitched(R.internal.tick(st, {})), "pitch 1 6, pad 1 127")
equal("⛔ a press on its pad plays at the set pitch: told first, then the hit",
      pitched(R.presses.pad(st, { 1, 100 })), "pitch 1 0, pad 1 127")
-- A repeat replays it: the rolled hit's pitch, then the unrolled hit's, as they fell.
st = R.new(1)
for k = 1, 8 do R.presses.step(st, { k, 100 }) end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.randomness(st, { 1, 50 })
R.presses["rnd-pitch"](st, { 1, 1 })
R.internal.start(st, {})
st.rand = dice(0, 0.1, 0.99, 0.75, 0.9)
local a1, a2 = pitched(R.internal.tick(st, {})), pitched(R.internal.tick(st, {}))
equal("two steps: a rolled hit at +6, then an unrolled one at its set pitch", { a1, a2 },
      { "pitch 1 6, pad 1 127", "pitch 1 0, pad 1 95" })
R.presses.rep(st, { 2, 127 })
st.rand = dice(0.123)
equal("⛔ a repeat replays them exactly, the pitch with the hit, every pass, rolling nothing",
      { pitched(R.internal.tick(st, {})), pitched(R.internal.tick(st, {})),
        pitched(R.internal.tick(st, {})), st.rand() },
      { "pitch 1 6, pad 1 127", "pitch 1 0, pad 1 95", "pitch 1 6, pad 1 127", 0.123 })
R.presses.rep(st, { 2, 0 })
-- A section's restore: the line round trip, and older lines off.
local saved = line(zeros(CELLS), nil, { rolled = { [3] = 1, [16] = 1 } })
equal("⛔ a line of 776 numbers restores each track's random pitch, in the phone's last 16",
      (function()
        R.internal.restore(st, saved)
        local p = R.phone(st)
        return { #saved, p[132 + 3], p[132 + 16], p[132 + 1], R.save(st)[3][776] }
      end)(), { 776, 1, 1, 0, 1 })
equal("⛔ ... and goes back out as it came", R.save(st)[3], saved)
equal("⛔ a line of 760, older, loads every track's off, and is put back the 760 it was",
      (function()
        local older = line(zeros(CELLS), nil, { type = 1 })
        R.internal.restore(st, older)
        local p = R.phone(st)
        return { p[132 + 3], p[132 + 16], #R.save(st)[3], #older }
      end)(), { 0, 0, 760, 760 })
equal("a line of 581 the same", (function()
  R.internal.restore(st, first(saved, 581))
  return { R.phone(st)[132 + 3], #R.save(st)[3] }
end)(), { 0, 581 })
equal("⛔ a restore tells c_kit the set pitch: c_kit holds it, so the next hit tells none",
      (function()
        local q = R.new(1)
        R.presses.step(q, { 1, 100 })
        R.presses["rnd-pitch"](q, { 1, 1 })
        R.presses.randomness(q, { 1, 100 })
        R.internal.start(q, {})
        q.rand = dice(0, 0.1, 0.99, 0.75)
        R.internal.tick(q, {})
        local l = line(zeros(CELLS))
        l[1] = 95
        R.internal.restore(q, l)
        q.rand = dice(0.9)
        return pitched(R.internal.tick(q, {}))
      end)(), "pad 1 95")

print("\n--- the settings in the restore ---")
st = R.new(1)
R.internal.init(st, {})
local full = first(line(zeros(CELLS), nil, { randomness = { [2] = 30 }, vol = { [5] = -12 },
                                             pitch = { [7] = 5 }, num = 7, den = 8, drunk = 25,
                                             swing = 60, last = 12 }), 581)
local back = R.internal.restore(st, full)
equal("a line of 581 brings back the randomness, the volumes, the pitches, the time signature, "
      .. "the drunkenness, the swing and the global last step",
      { back[4], st.randomness[2], st.vol[5], st.pitch[7], st.drunk, st.swing, st.last },
      { { "page", "bar", { 7, 7 } }, 30, -12, 5, 25, 60, 12 })
equal("⛔ ... the step clock takes the swing, and the page the last step", { back[5], back[2] },
      { { "clock", "swing", { 0.6 } }, { "page", "last", { 12 } } })
equal("⛔ ... and knobs 2 and 4 are held at them, as at the phone's: a knob elsewhere waits, "
      .. "knob 2's step 20 of 7/8's 28", { R.presses.last(st, { 19 / 27 }), R.presses.swing(st, { 0.9 }) },
      { { { "disp", "last-step", { 12, "(20)" } } }, { { "disp", "swing", { 60, "(73)" } } } })
equal("⛔ ... and tells c_kit every track's volume and pitch, track 5's -12 and track 7's 5 among "
      .. "them, and no effect, since a line of 581 brings them back off, as c_kit was told at load",
      { #back, back[5 + 5], back[5 + 16 + 7] },
      { 5 + 32, { "note", "vol", { 5, -12 } }, { "note", "pitch", { 7, 5 } } })
st = R.new(1)
st.swing, st.last = 70, 20
back = R.internal.restore(st, sectionless(zeros(CELLS), nil, { num = 3 }))
equal("⛔ a line of 579, from before sections, keeps the swing and the global last step in force",
      { st.num, st.swing, st.last }, { 3, 70, 20 })
equal("... and is put straight back as the line of 581", back[1],
      { "save", "list", line(zeros(CELLS), nil, { num = 3, swing = 70, last = 20 }) })
st = R.new(1)
back = R.internal.restore(st, old_line(zeros(CELLS), { [16] = 24 },
                                       { skip = { [2] = 30 }, move = { [5] = 60 }, num = 7, den = 8,
                                         drunk = 25 }))
equal("⛔ a line of 563, saved before the randomness, still loads: its last steps, and 7/8 and the "
      .. "drunkenness from where it kept them", { st.own[16], st.num, st.den, st.drunk },
      { 24, 7, 8, 25 })
equal("⛔ ... its skip chances come back as the randomness, which took their place, and its move "
      .. "chances go, not read as volumes", { st.randomness[2], st.randomness[5], st.vol[5] },
      { 30, 0, 0 })
equal("⛔ ... and it is put straight back as the line of 581", back[1],
      { "save", "list", line(zeros(CELLS), { [16] = 24 }, { randomness = { [2] = 30 }, num = 7,
                                                           den = 8, drunk = 25 }) })
st = R.new(1)
local old528 = {}
for i = 1, 528 do old528[i] = full[i] end
R.internal.restore(st, old528)
equal("a line of 528, from before the phone's settings, keeps 4/4, sober, no randomness, and every "
      .. "track at 0 dB and its own pitch", { st.num, st.den, st.drunk, st.randomness[2], st.vol[5],
                                             st.pitch[7] }, { 4, 4, 0, 0, 0, 0 })
full[CELLS + 66] = 6
R.internal.restore(st, full)
equal("a bottom number that is not 1 2 4 8 or 16 is 4", st.den, 4)
full[CELLS + 33], full[CELLS + 34], full[CELLS + 49], full[CELLS + 50] = -99, 50, 30, -30
R.internal.restore(st, full)
equal("a volume or a pitch out of its range is clipped: -30 to +6 dB, -12 to +12 semitones",
      { st.vol[1], st.vol[2], st.pitch[1], st.pitch[2] }, { -30, 6, 12, -12 })

print("\n--- the effects ---")
-- Each track's distortion, delay and send, and the one reverb's size and damping (Brendan,
-- 2026-11-05): saved with the pattern, told to c_kit, and on the phone for the selected track.
st = R.new(1)
equal("a new sequencer has every effect at its starting point, and every mix, level and send at 0, "
      .. "off", { st.fx.drive[1], st.fx.tone[16], st.fx.dist[5], st.fx.note[2], st.fx.feel[2],
                  st.fx.feedback[9], st.fx.delay[3], st.fx.send[16], st.verb.size,
                  st.verb.damping, st.fx.char[4] }, { 50, 100, 0, 3, 1, 40, 0, 0, 50, 50, 1 })
equal("⛔ the line is 711 numbers with the effects, after the 581 it held before them, 743 "
      .. "with the mutes and solos after them, and 759 with the characters after those",
      { R.SAVED_FX, R.SAVED_FLAGS, R.SAVED }, { 711, 743, 759 })
R.internal.init(st, {})
equal("⛔ a track's distortion mix from the drum screen, its own track's: saved, and to c_kit",
      R.presses.dist(st, { 3, 40 }),
      { { "save", "list", line(zeros(CELLS), nil, { fx = { dist = { [3] = 40 } } }) },
        { "note", "dist", { 3, 40 } } })
equal("... the same value again does nothing", R.presses.dist(st, { 3, 40 }), {})
equal("... nor does one with no track or no number",
      { R.presses.dist(st, { 3 }), R.presses.dist(st, {}), R.presses.drive(st, { "x", 20 }) },
      { {}, {}, {} })
equal("drive, tone, feedback, level and send, each its own track's, each to c_kit as it is",
      { R.presses.drive(st, { 1, 80 })[2], R.presses.tone(st, { 2, 10 })[2],
        R.presses.feedback(st, { 4, 70 })[2], R.presses.delay(st, { 5, 30 })[2],
        R.presses.send(st, { 6, 55 })[2] },
      { { "note", "drive", { 1, 80 } }, { "note", "tone", { 2, 10 } },
        { "note", "feedback", { 4, 70 } }, { "note", "delay", { 5, 30 } },
        { "note", "send", { 6, 55 } } })
equal("⛔ each is clipped to 0 to 100 and rounded", { R.presses.drive(st, { 1, 150 })[2],
                                                    R.presses.send(st, { 6, -5 })[2],
                                                    R.presses.tone(st, { 2, 10.4 }) },
      { { "note", "drive", { 1, 100 } }, { "note", "send", { 6, 0 } }, {} })
equal("⛔ a delay's note value goes to c_kit as its time in steps: 1/16 is one step",
      R.presses["delay-note"](st, { 7, 4 })[2], { "note", "delay-time", { 7, 1 } })
equal("⛔ ... dotted, half again: 1.5 steps", R.presses["delay-feel"](st, { 7, 3 })[2],
      { "note", "delay-time", { 7, 1.5 } })
equal("⛔ ... a half note triplet, two thirds of eight steps", (function()
  R.presses["delay-note"](st, { 7, 1 })
  return R.presses["delay-feel"](st, { 7, 2 })[2]
end)(), { "note", "delay-time", { 7, 16 / 3 } })
equal("... and the notes run 1 to 5 and the feels 1 to 3, clipped", (function()
  R.presses["delay-note"](st, { 8, 9 })
  R.presses["delay-feel"](st, { 8, 0 })
  return { st.fx.note[8], st.fx.feel[8], st.told["delay-time 8"] }
end)(), { 5, 1, 0.5 })
equal("⛔ the reverb's size and damping are the kit's, one each: saved, and to c_kit with no pad",
      { R.presses.size(st, { 80 }), R.presses.damping(st, { 20 })[2], R.presses.size(st, {}) },
      { { { "save", "list", line(zeros(CELLS), nil, {
            fx = { dist = { [3] = 40 }, drive = { [1] = 100 }, tone = { [2] = 10 },
                   feedback = { [4] = 70 }, delay = { [5] = 30 }, note = { [7] = 1, [8] = 5 },
                   feel = { [7] = 2 } }, verb = { size = 80 } }) },
          { "note", "size", { 80 } } }, { "note", "damping", { 20 } }, {} })
local P = 4 + 32 + 4 + 48
equal("⛔ the phone hears the selected track's effects and the reverb's, after the rest",
      { R.phone(st)[P + 1], R.phone(st)[P + 3], R.phone(st)[P + 10], R.phone(st)[P + 11],
        #R.phone(st) }, { 100, 0, 80, 20, 148 })
R.select(st, 7)
equal("... and another track's once it is selected: track 7's 1/2 triplet",
      { R.phone(st)[P + 4], R.phone(st)[P + 5], R.phone(st)[P + 6] }, { 1, 2, 40 })
equal("the effects play no note and change no step", { run(st, 1), st.pattern }, { "1:", zeros(CELLS) })

print("\n--- the effects in the restore ---")
st = R.new(1)
R.internal.init(st, {})
local fxl = line(zeros(CELLS), nil, { fx = { dist = { [2] = 60 }, delay = { [2] = 45 },
                                             note = { [2] = 2 }, feel = { [2] = 3 },
                                             send = { [9] = 70 } },
                                      verb = { damping = 90 } })
back = R.internal.restore(st, fxl)
equal("⛔ a line of 711 brings every effect back, and is put straight back as it came",
      { st.fx.dist[2], st.fx.delay[2], st.fx.note[2], st.fx.feel[2], st.fx.send[9],
        st.verb.damping, back[1] }, { 60, 45, 2, 3, 70, 90, { "save", "list", fxl } })
equal("⛔ ... and tells c_kit only the effects that changed, after the volumes and pitches",
      { #back, back[5 + 32 + 1], back[5 + 32 + 2], back[5 + 32 + 3], back[5 + 32 + 4],
        back[5 + 32 + 5] },
      { 5 + 32 + 5, { "note", "dist", { 2, 60 } }, { "note", "delay-time", { 2, 6 } },
        { "note", "delay", { 2, 45 } }, { "note", "send", { 9, 70 } },
        { "note", "damping", { 90 } } })
equal("⛔ the same line again tells c_kit no effect at all", #R.internal.restore(st, fxl), 5 + 32)
back = R.internal.restore(st, first(fxl, 581))
equal("⛔ a line of 581, saved before the effects, brings every one back off, and c_kit is told so",
      { st.fx.dist[2], st.fx.delay[2], st.fx.send[9], st.verb.damping, #back, back[5 + 32 + 1],
        back[5 + 32 + 4] },
      { 0, 0, 0, 50, 5 + 32 + 5, { "note", "dist", { 2, 0 } }, { "note", "send", { 9, 0 } } })
equal("⛔ ... and is put back as the 581 it came as, so a song saved before the effects is no "
      .. "change to save", back[1], { "save", "list", first(fxl, 581) })
st.fx.drive[4] = 51
equal("⛔ the line is 711 once any effect is off its starting point, a drive among them, and 581 "
      .. "again once none is", { #R.save(st)[3], (function() st.fx.drive[4] = 50
                                                    return #R.save(st)[3] end)() }, { 711, 581 })
R.internal.restore(st, fxl)
R.internal.restore(st, sectionless(zeros(CELLS)))
equal("⛔ so does a line of 579, and the old lines of 563 and 256", (function()
  local got = { st.fx.dist[2] }
  R.internal.restore(st, fxl)
  R.internal.restore(st, old_line(zeros(CELLS)))
  got[2] = st.fx.send[9]
  R.internal.restore(st, fxl)
  R.internal.restore(st, zeros(256))
  got[3] = st.fx.delay[2]
  return got
end)(), { 0, 0, 0 })
local odd = line(zeros(CELLS), nil, {})
odd[582], odd[582 + 16 * 3] = 400, "x"
odd[582 + 16 * 4 + 1] = 7
R.internal.restore(st, odd)
equal("a value out of its range is clipped, and a symbol is its range's bottom",
      { st.fx.drive[1], st.fx.note[1], st.fx.feel[2] }, { 100, 1, 3 })
st = R.new(1)
equal("⛔ a sequencer that never loaded tells c_kit every effect at its first restore",
      #R.internal.restore(st, fxl), 5 + 32 + 131)

print("\n--- mute and solo ---")
-- Each track's mute and solo from the drum screen (Brendan, 2026-11-05): with any track soloed
-- only the soloed play and the mutes are ignored; otherwise a muted track doesn't. A mute stops
-- the track's hits in the rules, so what c_kit is already sounding rings out.
-- The page's quiet pads: 1 for each track given, which won't play.
local function quiet(...)
  local q = zeros(16)
  for _, t in ipairs({ ... }) do q[t] = 1 end
  return { "page", "quiet", q }
end
st = R.new(1)
equal("a new sequencer has nothing muted or soloed", { st.mute, st.solo }, { zeros(16), zeros(16) })
equal("⛔ mute 3 1: saved, the line 743 with track 3's mute, and the page told track 3 is quiet",
      R.presses.mute(st, { 3, 1 }),
      { { "save", "list", line(zeros(CELLS), nil, { mute = { [3] = 1 } }) }, quiet(3) })
equal("... the same again does nothing, nor does one without a track and a number",
      { R.presses.mute(st, { 3, 1 }), R.presses.mute(st, { 3 }), R.presses.mute(st, {}),
        R.presses.solo(st, { "x", 1 }), R.presses.solo(st, { 3, "x" }) }, { {}, {}, {}, {}, {} })
equal("a track past 16 is 16, and a value is 0 or 1, rounded",
      { R.presses.mute(st, { 40, 7 })[2], R.presses.mute(st, { 16, 0.4 })[2],
        R.presses.mute(st, { 16, 0.6 })[2] }, { quiet(3, 16), quiet(3), quiet(3, 16) })
R.presses.mute(st, { 16, 0 })
st = R.new(1)
for _, t in ipairs({ 1, 2, 3 }) do
  R.presses.select(st, { t })
  for k = 1, 4 do R.presses.step(st, { k, 100 }) end
end
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.internal.start(st, {})
equal("three tracks playing every step", run(st, 2), "1:1@95,2@95,3@95 2:1@95,2@95,3@95")
R.presses.mute(st, { 2, 1 })
equal("⛔ track 2 muted plays nothing from the next step, and the rest play on",
      run(st, 2), "3:1@95,3@95 4:1@95,3@95")
equal("⛔ ... but a press on its pad still plays it, at full velocity, so it can be heard",
      R.presses.pad(st, { 2, 90 })[1], { "note", "pad", { 2, 127 } })
R.presses.randomness(st, { 2, 100 })
R.presses.select(st, { 2 })
for k = 1, 4 do R.presses.step(st, { k, 100 }) end
st.rand = dice(0, 0.1, 0.99, 0, 0.1, 0.99, 0.123)
equal("⛔ muted, its randomness adds no hit: two empty steps whose coins would play at level 8 "
      .. "stay silent, and it still rolls its dice, so muting it changes no other track's",
      { run(st, 2), st.rand() }, { "1:1@95,3@95 2:1@95,3@95", 0.123 })
R.presses.randomness(st, { 2, 0 })
for k = 1, 4 do R.presses.step(st, { k, 100 }) end
equal("⛔ a repeat held replays the muted track's steps silently", (function()
  R.presses.rep(st, { 2, 127 })
  return run(st, 2)
end)(), "1:1@95,3@95 2:1@95,3@95")
R.presses.mute(st, { 2, 0 })
equal("⛔ ... and unmuted while the repeat is held, it plays the repeat with the rest: the coins "
      .. "its randomness flipped then, level 8, not the steps written since",
      { run(st, 2), R.presses.rep(st, { 2, 0 })[1] },
      { "1:1@95,2@127,3@95 2:1@95,2@127,3@95", { "page", "rep", { 0 } } })
R.internal.start(st, {})
equal("⛔ solo 1: only track 1 plays, and every other pad is quiet",
      { R.presses.solo(st, { 1, 1 })[2], run(st, 1) },
      { quiet(2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16), "1:1@95" })
equal("⛔ a mute while another track is soloed changes no pad: saved, and the page told nothing",
      { #R.presses.mute(st, { 3, 1 }), R.presses.mute(st, { 3, 1 }) }, { 1, {} })
equal("⛔ with any solo the mutes are ignored: track 3 soloed though muted plays beside track 1",
      { R.presses.solo(st, { 3, 1 })[2], run(st, 1) },
      { quiet(2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16), "2:1@95,3@95" })
R.presses.solo(st, { 1, 0 })
equal("⛔ no solo left, the mutes are heard again: track 3 muted, tracks 1 and 2 play",
      { R.presses.solo(st, { 3, 0 })[2], run(st, 1) }, { quiet(3), "3:1@95,2@95" })
equal("⛔ the phone hears each track's mute, then each track's solo, after the effects",
      (function()
        R.presses.solo(st, { 5, 1 })
        return { #R.phone(st), R.phone(st)[99 + 3], R.phone(st)[99 + 2], R.phone(st)[115 + 5],
                 R.phone(st)[115 + 3] }
      end)(), { 148, 1, 0, 1, 0 })
st = R.new(1)
R.presses.dist(st, { 4, 30 })
R.presses.solo(st, { 6, 1 })
equal("⛔ the line is 743 while any track is muted or soloed, 711 again with an effect moved once "
      .. "none is, and 581 with neither",
      { #R.save(st)[3], (function() R.presses.solo(st, { 6, 0 }) return #R.save(st)[3] end)(),
        (function() R.presses.dist(st, { 4, 0 }) return #R.save(st)[3] end)() }, { 743, 711, 581 })

print("\n--- mute and solo in the restore ---")
st = R.new(1)
R.internal.init(st, {})
local msl = line(zeros(CELLS), nil, { mute = { [2] = 1, [7] = 1 }, solo = { [9] = 1 } })
back = R.internal.restore(st, msl)
equal("⛔ a line of 743 brings the mutes and solos back, and is put straight back as it came",
      { st.mute[2], st.mute[7], st.solo[9], st.mute[9], back[1] },
      { 1, 1, 1, 0, { "save", "list", msl } })
equal("⛔ ... and tells the page its quiet pads last, after c_kit", { #back, back[#back] },
      { 5 + 32 + 1, quiet(1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16) })
equal("⛔ the same line again tells the page nothing", #R.internal.restore(st, msl), 5 + 32)
back = R.internal.restore(st, first(msl, 711))
equal("⛔ a line of 711, saved before mute and solo, brings every track back unmuted and "
      .. "unsoloed, tells the page, and is put back as the 581 it is",
      { st.mute, st.solo, back[#back], back[1] },
      { zeros(16), zeros(16), quiet(), { "save", "list", first(msl, 581) } })
equal("⛔ so do lines of 581, 579, 563 and 256", (function()
  local got = {}
  for _, old in ipairs({ first(msl, 581), sectionless(zeros(CELLS)), old_line(zeros(CELLS)),
                         zeros(256) }) do
    R.internal.restore(st, msl)
    R.internal.restore(st, old)
    got[#got + 1] = R.flagged(st)
  end
  return got
end)(), { false, false, false, false })
local oddms = line(zeros(CELLS), nil, { mute = { [1] = 1 } })
oddms[712], oddms[713], oddms[714 + 16] = 7, "x", -3
R.internal.restore(st, oddms)
equal("a mute or a solo is 1 or 0: a value over 1 is 1, a symbol or a value below 0 is 0",
      { st.mute[1], st.mute[2], st.solo[3] }, { 1, 0, 0 })

print("\n--- the distortion's character ---")
-- Each track's distortion is soft, hard, fold or crush, 1 to 4 (Brendan, 2026-11-05): saved per
-- section after the mutes and solos, told to c_kit, and on the phone after the track's send.
st = R.new(1)
R.internal.init(st, {})
equal("a new sequencer has every track soft, and the phone's names are the four, in order",
      { st.fx.char, R.CHARS }, { { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 },
                                 { "soft", "hard", "fold", "crush" } })
equal("⛔ char 3 2 from the drum screen: saved, the line 759 with track 3 hard, and to c_kit",
      R.presses.char(st, { 3, 2 }),
      { { "save", "list", line(zeros(CELLS), nil, { fx = { char = { [3] = 2 } } }) },
        { "note", "char", { 3, 2 } } })
equal("... the same value again does nothing, nor one with no track or no number",
      { R.presses.char(st, { 3, 2 }), R.presses.char(st, { 3 }), R.presses.char(st, {}),
        R.presses.char(st, { "x", 4 }) }, { {}, {}, {}, {} })
equal("⛔ it is clipped to 1 to 4 and rounded: 9 is crush, 0 soft, 2.4 hard",
      { R.presses.char(st, { 5, 9 })[2], R.presses.char(st, { 6, 0 }),
        R.presses.char(st, { 6, 2.4 })[2] },
      { { "note", "char", { 5, 4 } }, {}, { "note", "char", { 6, 2 } } })
equal("⛔ the line is 759 while any track is not soft, the effects, mutes and solos before the "
      .. "characters as they stand; 743 once every track is soft again with one muted, 711 with an "
      .. "effect moved, 581 with neither",
      { #R.save(st)[3], R.save(st)[3][743 + 3], R.save(st)[3][743 + 5], R.save(st)[3][711 + 1],
        (function()
          R.presses.mute(st, { 1, 1 })
          for _, t in ipairs({ 3, 5, 6 }) do R.presses.char(st, { t, 1 }) end
          return #R.save(st)[3]
        end)(),
        (function() R.presses.mute(st, { 1, 0 }) R.presses.dist(st, { 2, 30 })
          return #R.save(st)[3] end)(),
        (function() R.presses.dist(st, { 2, 0 }) return #R.save(st)[3] end)() },
      { 759, 2, 4, 0, 743, 711, 581 })
R.presses.char(st, { 8, 3 })
R.select(st, 8)
local Q = 4 + 32 + 4 + 48
equal("⛔ the phone hears the selected track's character after its send, before the reverb's two",
      { R.phone(st)[Q + 8], R.phone(st)[Q + 9], R.phone(st)[Q + 10], #R.phone(st) },
      { 0, 3, 50, 148 })
R.select(st, 1)
equal("... and track 1's, soft, once it is selected", R.phone(st)[Q + 9], 1)

print("\n--- the characters in the restore ---")
st = R.new(1)
R.internal.init(st, {})
local chl = line(zeros(CELLS), nil, { fx = { char = { [2] = 3, [16] = 4 }, drive = { [2] = 80 } } })
back = R.internal.restore(st, chl)
equal("⛔ a line of 759 brings the characters back, and is put straight back as it came",
      { st.fx.char[2], st.fx.char[16], st.fx.char[1], st.fx.drive[2], #chl, back[1] },
      { 3, 4, 1, 80, 759, { "save", "list", chl } })
equal("⛔ ... and tells c_kit the ones that changed, in the order the rest are told",
      { #back, back[5 + 32 + 1], back[5 + 32 + 2], back[5 + 32 + 3] },
      { 5 + 32 + 3, { "note", "drive", { 2, 80 } }, { "note", "char", { 2, 3 } },
        { "note", "char", { 16, 4 } } })
back = R.internal.restore(st, first(chl, 743))
equal("⛔ a line of 743, saved before the characters, brings every track back soft, tells c_kit "
      .. "so, and is put back as the line it is",
      { st.fx.char, st.fx.drive[2], #back, back[5 + 32 + 1], back[5 + 32 + 2], back[1] },
      { { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 }, 80, 5 + 32 + 2,
        { "note", "char", { 2, 1 } }, { "note", "char", { 16, 1 } },
        { "save", "list", first(chl, 711) } })
equal("⛔ so do lines of 711, 581, 579, 563 and 256", (function()
  local got = {}
  for _, old in ipairs({ first(chl, 711), first(chl, 581), sectionless(zeros(CELLS)),
                         old_line(zeros(CELLS)), zeros(256) }) do
    R.internal.restore(st, chl)
    R.internal.restore(st, old)
    got[#got + 1] = R.late_moved(st)
  end
  return got
end)(), { false, false, false, false, false })
local oddch = line(zeros(CELLS), nil, { fx = { char = { [1] = 2 } } })
oddch[744], oddch[745], oddch[746] = 7, "x", -3
R.internal.restore(st, oddch)
equal("a character is 1 to 4: a value over 4 is crush, a symbol or a value below 1 soft",
      { st.fx.char[1], st.fx.char[2], st.fx.char[3] }, { 4, 1, 1 })

print("\n--- the reverb's type ---")
-- Which of the reverb's three engines plays, the kit's (Brendan, 2026-11-05): 0 plate, 1
-- gigaverb, 2 freeverb, saved per section at the end of the line, after the characters, the
-- plate when not.
st = R.new(1)
equal("a new sequencer is on the plate, the first of three", { st.verb_type, R.VERB_TYPES },
      { 0, { "plate", "gigaverb", "freeverb" } })
equal("⛔ the line is 760 with the type, after the 759", R.SAVED_TYPED, 760)
R.internal.init(st, {})
equal("⛔ verb-type 2 from the drum screen: saved, the line 760 ending in the type, the effects, "
      .. "mutes, solos and characters before it as they stand, and to c_kit with no pad",
      R.presses["verb-type"](st, { 2 }),
      { { "save", "list", line(zeros(CELLS), nil, { type = 2 }) },
        { "note", "verb-type", { 2 } } })
equal("... the same type again does nothing, nor does one with no number",
      { R.presses["verb-type"](st, { 2 }), R.presses["verb-type"](st, {}),
        R.presses["verb-type"](st, { "x" }) }, { {}, {}, {} })
equal("⛔ a type is 0 to 2, clipped and rounded", { R.presses["verb-type"](st, { 7 }),
                                                   R.presses["verb-type"](st, { 0.6 })[2],
                                                   R.presses["verb-type"](st, { -4 })[2] },
      { {}, { "note", "verb-type", { 1 } }, { "note", "verb-type", { 0 } } })
equal("⛔ back on the plate the line is 581 again, with nothing else moved", #R.save(st)[3], 581)
R.presses["verb-type"](st, { 1 })
R.presses.size(st, { 30 })
R.presses.mute(st, { 4, 1 })
equal("⛔ ... and with a type and an effect and a mute, all of them in the 760",
      R.save(st)[3], line(zeros(CELLS), nil, { verb = { size = 30 }, mute = { [4] = 1 },
                                               type = 1 }))
equal("⛔ the phone hears the type before the random pitches, its 132nd number",
      { #R.phone(st), R.phone(st)[132] }, { 148, 1 })

print("\n--- the reverb's type in the restore ---")
st = R.new(1)
R.internal.init(st, {})
local tyl = line(zeros(CELLS), nil, { type = 2 })
back = R.internal.restore(st, tyl)
equal("⛔ a line of 760 brings the type back, and is put straight back as it came",
      { st.verb_type, back[1] }, { 2, { "save", "list", tyl } })
equal("⛔ ... and tells c_kit the type, the one effect that changed", { #back, back[#back] },
      { 5 + 32 + 1, { "note", "verb-type", { 2 } } })
equal("⛔ the same line again tells c_kit nothing", #R.internal.restore(st, tyl), 5 + 32)
back = R.internal.restore(st, first(tyl, 759))
equal("⛔ a line of 759, saved before the type, brings the plate back, tells c_kit so, and is put "
      .. "back as the 581 it is",
      { st.verb_type, back[#back], back[1] },
      { 0, { "note", "verb-type", { 0 } }, { "save", "list", first(tyl, 581) } })
equal("⛔ so do lines of 743, 711, 581, 579, 563 and 256", (function()
  local got = {}
  for _, old in ipairs({ first(tyl, 743), first(tyl, 711), first(tyl, 581),
                         sectionless(zeros(CELLS)), old_line(zeros(CELLS)), zeros(256) }) do
    R.internal.restore(st, tyl)
    R.internal.restore(st, old)
    got[#got + 1] = st.verb_type
  end
  return got
end)(), { 0, 0, 0, 0, 0, 0 })
local oddty = line(zeros(CELLS), nil, { type = 1 })
oddty[760] = 9
R.internal.restore(st, oddty)
local got = { st.verb_type }
oddty[760] = "x"
R.internal.restore(st, oddty)
got[2] = st.verb_type
equal("a type past 2 is 2, and a symbol is the plate", got, { 2, 0 })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_steps-lua.pd_lua", DIR)
check("c_steps-lua.pd_lua registers the class c_steps-lua", class and class._name == "c_steps-lua",
      class and class._name)
local o = T.new(class, { 1 })
check("an object has two inlets and ten outlets", o and o.inlets == 2 and o.outlets == 10,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the page's selection on outlet 2, every effect on outlet 1, for c_kit, the drum "
      .. "screen's state on outlet 7, then the bang on outlet 5 that says it loaded",
      T.send(o, 2, "init", {}), cat({ { 2, "vel", { 6 } }, { 2, "track", { 1 } }, { 2, "last", { 16 } },
                                  { 2, "steps", zeros(32) }, { 2, "bar", { 4, 8 } }, { 2, "rep", { 0 } },
                                  { 8, "swing", { 0.5 } }, { 8, "rate", { 1 } },
                                  { 3, "list", line(zeros(CELLS)) } },
      (function()
        local out = {}
        for _, e in ipairs(fx_all()) do out[#out + 1] = { 1, e[2], e[3] } end
        return out
      end)(), { { 7, "list", phone(0, 16, 1, 0, {}, {}) }, { 5, "bang", {} } }))
equal("knob 2 held: its row on outlet 6", T.send(o, 1, "last", { at(9) }),
      { { 6, "last-step", { 16, "(9)" } } })
local sent = T.send(o, 1, "step", { 1, 100 })
want = zeros(CELLS)
want[1] = 95
equal("a step press: the page on outlet 2, the pattern held back, its clock set for 100 ms",
      { sent, o.save_clock.armed }, { { { 2, "steps", row(want, 1) } }, 100 })
local sets = o.save_clock.sets
T.send(o, 1, "drunk", { 0 })
equal("⛔ a second change while it is held: the clock is not set again, so a drag still saves",
      { o.save_clock.sets - sets, o.save_clock.armed }, { 0, 100 })
equal("⛔ the clock: the pattern as it stands now, on outlet 3", T.fire(o, o.save_clock),
      { { 3, "list", line(want) } })
equal("... and once only", T.fire(o, o.save_clock), nil)
-- the step off and on again, a press and a release each: held, the clock set
for _ = 1, 2 do T.send(o, 1, "step", { 1, 0 }); T.send(o, 1, "step", { 1, 100 }) end
equal("⛔ sync off the state bus puts a held pattern at once, and stops the clock",
      { T.send(o, 2, "sync", {}), o.save_clock.armed }, { { { 3, "list", line(want) } }, nil })
equal("... and with nothing held, sync sends nothing", T.send(o, 2, "sync", {}), {})
equal("a restore: the pattern on outlet 3, the page on outlet 2, and every track's volume and pitch "
      .. "on outlet 1, for c_kit", (function()
  local got = T.send(T.new(class, { 1 }), 2, "restore", line(zeros(CELLS), nil, { vol = { [4] = -9 } }))
  return { got[5], got[6], got[5 + 4], got[5 + 32] }
end)(), { { 8, "swing", { 0.5 } }, { 1, "vol", { 1, 0 } }, { 1, "vol", { 4, -9 } },
          { 1, "pitch", { 16, 0 } } })
equal("a pad's volume from the drum screen: the volume on outlet 1, the phone's state, and the "
      .. "pattern on outlet 3 when its clock comes", (function()
  local q = T.new(class, { 1 })
  local got = T.send(q, 1, "vol", { 2, -6 })
  local saved = T.fire(q, q.save_clock)
  return { saved[1][1], got[1], got[2][1], got[2][3][4 + 32 + 4 + 2] }
end)(), { 3, { 1, "vol", { 2, -6 } }, 7, -6 })
equal("⛔ a mute from the drum screen: the page's quiet pads on outlet 2 and the phone's state "
      .. "on outlet 7, its put held as any press's, and the line its clock puts mutes track 4",
      (function()
        local q = T.new(class, { 1 })
        local got = T.send(q, 1, "mute", { 4, 1 })
        local armed = q.save_clock.armed
        local saved = T.fire(q, q.save_clock)
        return { got[1], got[2][1], got[2][3][99 + 4], armed, #saved[1][3], saved[1][3][711 + 4] }
      end)(), { { 2, "quiet", quiet(4)[3] }, 7, 1, 100, 743, 1 })
equal("⛔ a character from the drum screen: char to c_kit on outlet 1 and the phone's state on "
      .. "outlet 7, its put held as any press's, and the line its clock puts holds track 4 fold",
      (function()
        local q = T.new(class, { 1 })
        local got = T.send(q, 1, "char", { 4, 3 })
        local armed = q.save_clock.armed
        local saved = T.fire(q, q.save_clock)
        return { got[1], got[2][1], armed, #saved[1][3], saved[1][3][743 + 4] }
      end)(), { { 1, "char", { 4, 3 } }, 7, 100, 759, 3 })
equal("PLAY: the step clock back at its own rate, no repeat, and the drum screen hears it is playing",
      T.send(o, 2, "start", {}), { { 8, "rate", { 1 } }, { 2, "rep", { 0 } },
                                   { 7, "list", phone(1, 16, 1, 0, {}, {}) } })
equal("a tick: its notes on outlet 1, then the playhead on outlet 2, and nothing for the phone",
      T.send(o, 2, "tick", {}), { { 1, "pad", { 1, 95 } }, { 2, "play", { 1 } } })
equal("sync from the drum screen, on inlet 1: only the phone's state, a sync pending",
      T.send(o, 1, "sync", {}), { { 7, "list", phone(1, 16, 1, 1, {}, {}) } })
equal("select from the drum screen: the track and its steps, and the phone's state, with no note",
      T.send(o, 1, "select", { 3 }), { { 2, "track", { 3 } }, { 2, "last", { 16 } },
                                        { 2, "steps", zeros(32) },
                                        { 7, "list", phone(1, 16, 3, 1, {}, {}) } })
for _, m in ipairs({ { 1, "float", { 3 } }, { 1, "beat", { 1 } }, { 1, "tick", {} },
                     { 2, "step", { 1, 100 } }, { 2, "fire", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail c_steps bad-selector on outlet 4", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 4, "fail", { "c_steps", "bad-selector" } } })
end

-- pdlua hands every message to dispatch, which the class answers itself (lua-face.lua): a knob
-- turn and every tick pass through it.
local function dispatched(inlet, sel, atoms)
  o.sent = {}
  o:dispatch(inlet, sel, atoms)
  return o.sent
end
equal("dispatch takes each inlet's messages to its method, which refuses a stray one",
      { dispatched(1, "beat", { 1 }), dispatched(2, "beat", {}) },
      { { { 4, "fail", { "c_steps", "bad-selector" } } }, { { 4, "fail", { "c_steps", "bad-selector" } } } })
check("... and it is the class's own, not pdlua's", rawget(class, "dispatch") ~= nil, "")

-- A Lua error, made by a copy of the rules whose tick throws: the class reads its rules as
-- prefix .. "c_steps.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-c_steps.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'c_steps.lua")\n',
         'R.internal.tick = function() error("a bug in tick") end\nreturn R\n')
fh:close()
-- The face too, which the class reads from the same prefix.
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "c_steps-lua.pd_lua", tmp .. "-"), { 1 })
os.remove(tmp .. "-c_steps.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 4 as fail c_steps lua-tick, for the error log",
      T.send(broken, 2, "tick", {})[1], { 4, "fail", { "c_steps", "lua-tick" } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in tick", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: a press still answers",
      T.send(broken, 1, "vel", { 2, 100 }), { { 2, "vel", { 2 } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
