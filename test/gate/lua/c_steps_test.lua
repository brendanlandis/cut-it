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

-- The saved line: 512 velocities, then the 16 tracks' own last steps, their randomness, their
-- volumes and their pitches, then the time signature, the drunkenness, the swing and the global
-- last step: 581 numbers. x holds what differs from a new sequencer's: randomness, vol and pitch
-- by track, num, den, drunk, swing, last.
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
  return l
end

-- The line saved before sections: the same without the swing and the global last step, 579.
local function sectionless(pat, own, x)
  local l = line(pat, own, x)
  l[#l], l[#l - 1] = nil, nil
  return l
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

-- The phone's 88 numbers, from the few that differ: lasts and owns by track, then the time
-- signature, the drunkenness and the swing (4 4 0 50 unless given), then every track's volume,
-- pitch and randomness (per.vol, per.pitch and per.randomness by track, 0 unless given).
local function phone(playing, last, track, pending, lasts, owns, tail, per)
  per = per or {}
  local p = { playing, last, track, pending }
  for t = 1, 16 do p[#p + 1] = lasts[t] or last end
  for t = 1, 16 do p[#p + 1] = owns[t] or 0 end
  for _, v in ipairs(tail or { 4, 4, 0, 50 }) do p[#p + 1] = v end
  for _, which in ipairs({ "vol", "pitch", "randomness" }) do
    for t = 1, 16 do p[#p + 1] = (per[which] or {})[t] or 0 end
  end
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
      if e[1] == "note" then pads[#pads + 1] = e[3][1] .. "@" .. e[3][2] end
      if e[1] == "page" then head = e[3][1] end
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
               { "page", "steps", zeros(32) }, { "page", "bar", { 16 } }, { "page", "rep", { 0 } },
               { "clock", "swing", { 0.5 } }, { "clock", "rate", { 1 } },
               { "save", "list", line(zeros(CELLS)) } }
equal("init draws the selection -- vel 6, track 1, last 16, track 1's 32 steps, a bar of 16, no "
      .. "repeat -- sets the step clock straight, and puts the pattern, so the section playing "
      .. "holds the drums from the start", R.internal.init(st, {}), BOOT)
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
            { "page", "steps", row(pat, 1) }, { "page", "bar", { 16 } },
            { "clock", "swing", { 0.5 } } }, kit()))
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
st = R.new(1)
local function x(k, v) local t = {} t[k] = v return t end
equal("the top number steps up by one: 5/4 is a bar of 20 steps, saved, and the page lights it",
      R.presses.num(st, { 1 }), { { "save", "list", line(zeros(CELLS), nil, x("num", 5)) },
                                  { "page", "bar", { 20 } } })
R.presses.num(st, { -1 })
R.presses.num(st, { 1 })
R.presses.num(st, { 1 })
R.presses.num(st, { 1 })
equal("the bottom number steps through 1 2 4 8 16: 7/8 is 14 steps",
      R.presses.den(st, { 1 })[2], { "page", "bar", { 14 } })
equal("... 7/16 is 7, and it stops at 16", { R.presses.den(st, { 1 })[2][3][1],
                                             R.presses.den(st, { 1 })[2][3][1], st.den }, { 7, 7, 16 })
for _ = 1, 6 do R.presses.den(st, { -1 }) end
equal("... and at 1 at the other end: 7/1 is 112", { st.den, R.bar(st) }, { 1, 112 })
for _ = 1, 40 do R.presses.num(st, { 1 }) end
equal("the top number stops at 32 and at 1", { st.num, (function()
  for _ = 1, 40 do R.presses.num(st, { -1 }) end
  return st.num
end)() }, { 32, 1 })

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
      { { { "page", "rep", { 0 } } }, "4:1@95 5:1@95" })
R.presses.rep(st, { 1, 127 })
equal("pad 1 replays the last step heard", run(st, 3), "5:1@95 5:1@95 5:1@95")
R.presses.rep(st, { 4, 127 })
equal("... and a second pad pressed takes over, from the steps heard: 5 5 5 5", run(st, 2),
      "5:1@95 5:1@95")
equal("PLAY lets go of a held repeat", { R.internal.start(st, {})[2], run(st, 2) },
      { { "page", "rep", { 0 } }, "1:1@95 2:1@95" })

print("\n--- the settings in the restore ---")
st = R.new(1)
local full = line(zeros(CELLS), nil, { randomness = { [2] = 30 }, vol = { [5] = -12 },
                                       pitch = { [7] = 5 }, num = 7, den = 8, drunk = 25,
                                       swing = 60, last = 12 })
local back = R.internal.restore(st, full)
equal("a line of 581 brings back the randomness, the volumes, the pitches, the time signature, "
      .. "the drunkenness, the swing and the global last step",
      { back[4], st.randomness[2], st.vol[5], st.pitch[7], st.drunk, st.swing, st.last },
      { { "page", "bar", { 14 } }, 30, -12, 5, 25, 60, 12 })
equal("⛔ ... the step clock takes the swing, and the page the last step", { back[5], back[2] },
      { { "clock", "swing", { 0.6 } }, { "page", "last", { 12 } } })
equal("⛔ ... and knobs 2 and 4 are held at them, as at the phone's: a knob elsewhere waits",
      { R.presses.last(st, { at(20) }), R.presses.swing(st, { 0.9 }) },
      { { { "disp", "last-step", { 12, "(20)" } } }, { { "disp", "swing", { 60, "(73)" } } } })
equal("⛔ ... and tells c_kit every track's volume and pitch, track 5's -12 and track 7's 5 among "
      .. "them", { #back, back[5 + 5], back[5 + 16 + 7] },
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

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_steps-lua.pd_lua", DIR)
check("c_steps-lua.pd_lua registers the class c_steps-lua", class and class._name == "c_steps-lua",
      class and class._name)
local o = T.new(class, { 1 })
check("an object has two inlets and nine outlets", o and o.inlets == 2 and o.outlets == 9,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the page's selection on outlet 2, the drum screen's state on outlet 7, then the "
      .. "bang on outlet 5 that says it loaded",
      T.send(o, 2, "init", {}), { { 2, "vel", { 6 } }, { 2, "track", { 1 } }, { 2, "last", { 16 } },
                                  { 2, "steps", zeros(32) }, { 2, "bar", { 16 } }, { 2, "rep", { 0 } },
                                  { 8, "swing", { 0.5 } }, { 8, "rate", { 1 } },
                                  { 3, "list", line(zeros(CELLS)) },
                                  { 7, "list", phone(0, 16, 1, 0, {}, {}) }, { 5, "bang", {} } })
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
