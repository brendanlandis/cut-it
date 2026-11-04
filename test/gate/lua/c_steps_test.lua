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

-- The selected track's row as the page gets it, from a pattern.
local function row(pat, track)
  local r = {}
  for s = 1, 32 do r[s] = pat[(track - 1) * 32 + s] end
  return r
end

-- The saved line: 512 velocities, then the 16 tracks' own last steps, their skip and move
-- chances, then the time signature and the drunkenness: 563 numbers. x holds what differs from
-- a new sequencer's: skip, move, num, den, drunk.
local function line(pat, own, x)
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

-- What a step press answers: the whole pattern to save, then the selected track's row.
local function edited(pat, track, own)
  return { { "save", "list", line(pat, own) }, { "page", "steps", row(pat, track) } }
end

-- A knob position for a step: what R.knob_step reads back as n.
local function at(n) return (n - 1) / 31 end

-- The drum screen's 41 numbers, from the few that differ: lasts and owns by track, then the
-- time signature, the drunkenness and the selected track's chances (4 4 0 0 0 unless given).
local function phone(playing, last, track, pending, lasts, owns, tail)
  local p = { playing, last, track, pending }
  for t = 1, 16 do p[#p + 1] = lasts[t] or last end
  for t = 1, 16 do p[#p + 1] = owns[t] or 0 end
  for _, v in ipairs(tail or { 4, 4, 0, 0, 0 }) do p[#p + 1] = v end
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

print("\n--- at load ---")
local st = R.new(1)
equal("a new sequencer holds 512 zeros, every track following the global last step",
      { st.pattern, st.own }, { zeros(CELLS), zeros(16) })
equal("... and starts on track 1 at level 6, the last step 16", { st.track, st.level, st.last },
      { 1, 6, 16 })
local BOOT = { { "page", "vel", { 6 } }, { "page", "track", { 1 } }, { "page", "last", { 16 } },
               { "page", "steps", zeros(32) }, { "page", "bar", { 16 } }, { "page", "rep", { 0 } },
               { "clock", "swing", { 0.5 } }, { "clock", "rate", { 1 } } }
equal("init draws the selection -- vel 6, track 1, last 16, track 1's 32 steps, a bar of 16, no "
      .. "repeat -- and sets the step clock straight", R.internal.init(st, {}), BOOT)
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
equal("a pad press plays its pad now, selects its track, and draws its last step and row",
      R.presses.pad(st, { 2, 90 }), { { "note", "pad", { 2, 90 } }, { "page", "track", { 2 } },
                                      { "page", "last", { 16 } }, { "page", "steps", zeros(32) } })
R.presses.step(st, { 1, 100 })
want = zeros(CELLS)
want[33] = R.velocity(6)
equal("a step press edits the SELECTED track -- track 2's step 1, track 1 untouched",
      st.pattern, want)
local st3 = R.new(3)
equal("bank C's track 2 is pad 34", R.presses.pad(st3, { 2, 90 })[1],
      { "note", "pad", { 34, 90 } })
equal("pads are clipped to 1..16 and levels to 1..8",
      { R.presses.pad(R.new(1), { 0, 90 })[1], R.presses.pad(R.new(1), { 20, 90 })[1],
        R.presses.vel(R.new(1), { 40, 100 })[1] },
      { { "note", "pad", { 1, 90 } }, { "note", "pad", { 16, 90 } }, { "page", "vel", { 8 } } })
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
equal("passing 16 releases it, at the step it reached -- 18",
      R.presses.last(st, { at(18) }), { { "disp", "last-step", { 18 } },
                                       { "page", "last", { 18 } } })
equal("... and it is live from then on", R.presses.last(st, { at(4) }),
      { { "disp", "last-step", { 4 } }, { "page", "last", { 4 } } })
st = R.new(1)
equal("reaching 16 exactly releases it too", R.presses.last(st, { at(16) }),
      { { "disp", "last-step", { 16 } }, { "page", "last", { 16 } } })
check("the global last step is not saved: no put", (function()
  for _, e in ipairs(R.presses.last(st, { at(9) })) do if e[1] == "save" then return false end end
  return true
end)(), "")

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
equal("knob 2 moves the global last step for every track but the ones with their own",
      { R.presses.last(st, { at(24) })[2], R.last_of(st, 1), R.last_of(st, 2) },
      { nil, 10, 24 })
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
equal("a restore takes the 512 and the 16 last steps, puts them straight back and redraws",
      R.internal.restore(st, line(pat, own)),
      { { "save", "list", line(pat, own) }, { "page", "last", { 16 } },
        { "page", "steps", row(pat, 1) }, { "page", "bar", { 16 } } })
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
local function sw(n) return (n - 25) / 50 end
st = R.new(1)
equal("⛔ at load it is HELD at 50%: a knob at 62% draws the held row and changes nothing",
      R.presses.swing(st, { sw(62) }), { { "disp", "swing", { 50, "(62)" } } })
equal("passing 50% releases it: the row, and the step clock takes the swing as a share",
      R.presses.swing(st, { sw(38) }), { { "disp", "swing", { 38, "%" } },
                                        { "clock", "swing", { 0.38 } } })
equal("its ends are 25% and 75%, and the knob between is rounded to whole percents",
      { R.presses.swing(st, { 0 })[2][3][1], R.presses.swing(st, { 1 })[2][3][1],
        R.presses.swing(st, { 0.513 })[2][3][1] }, { 0.25, 0.75, 0.51 })
check("swing is not saved: no put", (function()
  for _, e in ipairs(R.presses.swing(st, { 0.2 })) do if e[1] == "save" then return false end end
  return true
end)(), "")

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

print("\n--- the drum screen's sliders ---")
st = R.new(1)
equal("drunkenness, 0 to 100, rounded and saved",
      { R.presses.drunk(st, { 33.4 }), R.presses.drunk(st, { 140 })[1][3][CELLS + 51] },
      { { { "save", "list", line(zeros(CELLS), nil, x("drunk", 33)) } }, 100 })
R.presses.select(st, { 3 })
R.presses.skip(st, { 20 })
R.presses.move(st, { 70 })
equal("skip and move are the SELECTED track's, saved", { st.skip[3], st.move[3], st.skip[1] },
      { 20, 70, 0 })
equal("the drum screen shows the time signature, the drunkenness and the selected track's chances",
      R.phone(st), phone(0, 16, 3, 0, {}, {}, { 4, 4, 100, 20, 70 }))
R.presses.select(st, { 1 })
equal("... another track's when another is selected", R.phone(st),
      phone(0, 16, 1, 0, {}, {}, { 4, 4, 100, 0, 0 }))

print("\n--- the chances ---")
st = R.new(1)
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 3, 100 })
R.presses.last(st, { at(16) })
R.presses.last(st, { at(4) })
R.presses.skip(st, { 100 })
R.presses.move(st, { 100 })
R.internal.start(st, {})
equal("skip 100: no note plays", run(st, 8), "1: 2: 3: 4: 1: 2: 3: 4:")
st = R.new(1)
R.presses.step(st, { 1, 100 })
R.presses.step(st, { 5, 100 })
R.presses.last(st, { at(16) })
R.presses.last(st, { at(8) })
R.presses.move(st, { 100 })
R.internal.start(st, {})
st.rand = dice(0.9, 0.2, 0.3, 0.2, 0.9)
equal("⛔ move 100: the first step after PLAY can only go late; step 5, rolled a step ahead, plays "
      .. "early, at 4; step 1 next time round, late, at 2", run(st, 10),
      "1: 2:1@95 3: 4:1@95 5: 6: 7: 8: 1: 2:1@95")
st.skip[1], st.move[1] = 0, 0
R.internal.start(st, {})
equal("... and with no chances a track rolls nothing and plays as written", run(st, 5),
      "1:1@95 2: 3: 4: 5:1@95")
st = R.new(1)
R.presses.step(st, { 2, 100 })
R.presses.move(st, { 100 })
R.internal.start(st, {})
st.rand = dice(0.1, 0.9)
equal("a note moved late plays at the next step, at its own velocity", run(st, 3), "1: 2: 3:1@95")

print("\n--- drunkenness ---")
st = R.new(1)
R.internal.start(st, {})
equal("sober, a step changes nothing of the clock's", #R.internal.tick(st, {}), 1)
R.presses.drunk(st, { 50 })
st.rand = dice(0, 1)
equal("drunk 50: a step that strays can last half a step longer -- the clock's rate 1/1.5",
      R.internal.tick(st, {})[2], { "clock", "rate", { 1 / 1.5 } })
st.rand = dice(0, 0)
equal("... or half a step shorter -- rate 2", R.internal.tick(st, {})[2], { "clock", "rate", { 2 } })
st.rand = dice(0.17, 0)
equal("drunk 50, a step strays one time in six: a roll of 0.17 plays on time -- rate 1, "
      .. "and no size is rolled", { R.internal.tick(st, {})[2], st.rand() },
      { { "clock", "rate", { 1 } }, 0 })
R.presses.drunk(st, { 100 })
st.rand = dice(0, 0)
equal("drunk 100: a whole step shorter is held at an eighth of a step -- rate 8",
      R.internal.tick(st, {})[2], { "clock", "rate", { 8 } })
st.rand = dice(0.34, 0)
equal("drunk 100, most steps stay on time: a roll of 0.34 is past the third that strays -- rate 1",
      R.internal.tick(st, {})[2], { "clock", "rate", { 1 } })
st.rand = dice(0, 0.5)
equal("a stray of the middle is a step as written: no rate sent",
      #R.internal.tick(st, {}), 1)
-- On a sequencer of its own: the last roll leaves the rate wherever it fell.
local strays, d = 0, R.new(1)
R.internal.start(d, {})
R.presses.drunk(d, { 100 })
d.rand = math.random
for _ = 1, 3000 do
  R.internal.tick(d, {})
  if d.rate ~= 1 then strays = strays + 1 end
end
equal("drunk 100, over 3000 steps about a third stray: between 850 and 1150",
      strays >= 850 and strays <= 1150 or strays, true)
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
local full = line(zeros(CELLS), nil, { skip = { [2] = 30 }, move = { [5] = 60 }, num = 7, den = 8,
                                       drunk = 25 })
equal("a line of 563 brings back the chances, the time signature and the drunkenness",
      { R.internal.restore(st, full)[4], st.skip[2], st.move[5], st.drunk },
      { { "page", "bar", { 14 } }, 30, 60, 25 })
st = R.new(1)
local old528 = {}
for i = 1, 528 do old528[i] = full[i] end
R.internal.restore(st, old528)
equal("a line of 528, from before them, keeps 4/4, sober, and no chances",
      { st.num, st.den, st.drunk, st.skip[2] }, { 4, 4, 0, 0 })
full[CELLS + 50] = 6
R.internal.restore(st, full)
equal("a bottom number that is not 1 2 4 8 or 16 is 4", st.den, 4)

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "c_steps-lua.pd_lua", DIR)
check("c_steps-lua.pd_lua registers the class c_steps-lua", class and class._name == "c_steps-lua",
      class and class._name)
local o = T.new(class, { 1 })
check("an object has two inlets and eight outlets", o and o.inlets == 2 and o.outlets == 8,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the page's selection on outlet 2, the drum screen's state on outlet 7, then the "
      .. "bang on outlet 5 that says it loaded",
      T.send(o, 2, "init", {}), { { 2, "vel", { 6 } }, { 2, "track", { 1 } }, { 2, "last", { 16 } },
                                  { 2, "steps", zeros(32) }, { 2, "bar", { 16 } }, { 2, "rep", { 0 } },
                                  { 8, "swing", { 0.5 } }, { 8, "rate", { 1 } },
                                  { 7, "list", phone(0, 16, 1, 0, {}, {}) }, { 5, "bang", {} } })
equal("knob 2 held: its row on outlet 6", T.send(o, 1, "last", { at(9) }),
      { { 6, "last-step", { 16, "(9)" } } })
local sent = T.send(o, 1, "step", { 1, 100 })
want = zeros(CELLS)
want[1] = 95
equal("a step press: the pattern on outlet 3, then the page on outlet 2",
      sent, { { 3, "list", line(want) }, { 2, "steps", row(want, 1) } })
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

-- A Lua error, made by a copy of the rules whose tick throws: the class reads its rules as
-- prefix .. "c_steps.lua", so the copy sits at a temporary prefix.
local tmp = os.tmpname()
local fh = assert(io.open(tmp .. "-c_steps.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'c_steps.lua")\n',
         'R.internal.tick = function() error("a bug in tick") end\nreturn R\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "c_steps-lua.pd_lua", tmp .. "-"), { 1 })
os.remove(tmp .. "-c_steps.lua")
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
