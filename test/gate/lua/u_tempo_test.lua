-- Tap tempo's rules and the phone's tempo, without Pd: "Cut It/u_tempo.lua", and the Pd face that
-- carries them, "Cut It/u_tempo-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The
-- tempo gate runs this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo
-- root:
--
--   lua test/gate/lua/u_tempo_test.lua [-v]
--
-- What the patch does with these answers -- the timer between taps, the tempo bus, the pad's
-- flash -- is tempo-assert.py's and display-assert.py's, on a running copy of the instrument.
-- ref/module/tempo.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "u_tempo.lua")
local check, equal = T.check, T.equal

local function tempo(bpm) return { { "tempo", "float", { bpm } } } end

-- Taps <ms> apart, after the one that starts the count. -> what the last one answered.
local function taps(st, ...)
  R.tap(st, 5000)
  local out
  for _, ms in ipairs({ ... }) do out = R.tap(st, ms) end
  return out
end

print("\n--- the range ---")
local fh = assert(io.open(DIR .. "u_tempo.pd"))
local pd = fh:read("a")
fh:close()
local lo, hi = pd:match("\n#X obj %d+ %d+ clip (%d+) (%d+);")
equal("its range is u_tempo's own [clip 5 1000], the legal range, read from the patch",
      { R.MIN, R.MAX }, { tonumber(lo), tonumber(hi) })
equal("a gap of two seconds starts over, and the last four intervals are averaged",
      { R.GAP, R.KEEP }, { 2000, 4 })

print("\n--- tapping ---")
local st = R.new()
equal("the first tap after load sets nothing, however long since load", R.tap(st, 700), {})
equal("the second, 500 ms later, sets 120", R.tap(st, 500), tempo(120))
equal("a third 400 ms on averages the two: 450 ms, 133", R.tap(st, 400), tempo(133))
equal("⛔ only the last four intervals count: 500 400 then four of 300 is 200 BPM",
      (function() R.tap(st, 300); R.tap(st, 300); R.tap(st, 300); return R.tap(st, 300) end)(),
      tempo(200))
equal("⛔ a tap two seconds after the one before starts over, and sets nothing",
      R.tap(st, 2000), {})
equal("... the next one counts from it alone: 1000 ms, 60", R.tap(st, 1000), tempo(60))
equal("1999 ms is still a tap: the average of 1000 and 1999 is 40 BPM", R.tap(st, 1999),
      tempo(40))
equal("a tap in the same instant as the one before counts nothing and keeps the count",
      { R.tap(st, 0), R.tap(st, 1000) }, { {}, tempo(45) })

print("\n--- the clamp ---")
equal("⛔ taps 50 ms apart are 1200 BPM, clamped to 1000", taps(R.new(), 50, 50), tempo(1000))
equal("... 59 ms is 1017, still 1000; 61 ms 984, whole", { taps(R.new(), 59), taps(R.new(), 61) },
      { tempo(1000), tempo(984) })
equal("the slowest a tap can set is 2 s apart less a little: 31 BPM, never below 5",
      taps(R.new(), 1950), tempo(31))
equal("a tap that is not a number starts over", (function()
  local s = R.new()
  R.tap(s, 5000)
  R.tap(s, 500)
  return { R.tap(s, "x"), R.tap(s, 500) }
end)(), { {}, tempo(120) })

print("\n--- the phone's tempo ---")
st = R.new()
equal("tempo 133 from the phone is 133", R.set(st, 133), tempo(133))
equal("whole BPM, and within 5 to 1000", { R.set(st, 90.4), R.set(st, 2000), R.set(st, 1) },
      { tempo(90), tempo(1000), tempo(5) })
equal("a tempo that is not a number is fail u_tempo bad-tempo", { R.set(st, "fast"), R.set(st, nil) },
      { { { "err", "fail", { "u_tempo", "bad-tempo" } } },
        { { "err", "fail", { "u_tempo", "bad-tempo" } } } })
R.tap(st, 5000)
R.tap(st, 500)
R.set(st, 90)
equal("the phone leaves a count of taps alone: the next tap still averages with it",
      R.tap(st, 500), tempo(120))


print("\n--- the 500 BPM repeat and a section's tempo ---")
st = R.new()
equal("⛔ fast 1: the section's put shut first, then 500 on the bus, as a tap's, so knob 1 is held there",
      R.inputs.fast(st, { 1, 133 }), { { "put", "float", { 0 } }, { "tempo", "float", { 500 } } })
equal("a second fast 1 changes nothing", R.inputs.fast(st, { 1, 77 }), {})
equal("⛔ fast 0: back to the tempo before the press, whatever the knob or the phone set since, then "
      .. "the put open again", R.inputs.fast(st, { 0 }),
      { { "tempo", "float", { 133 } }, { "put", "float", { 1 } } })
equal("a second fast 0 changes nothing", R.inputs.fast(st, { 0 }), {})
equal("restored <bpm> is the phone's tempo, while it is not held",
      R.inputs.restored(st, { 90.4 }), tempo(90))
equal("... and a bad one is the phone's error", R.inputs.restored(st, { "x" }),
      { R.fail("bad-tempo") })
R.inputs.fast(st, { 1, 90 })
equal("⛔ held, a section's tempo changes nothing now ...", R.inputs.restored(st, { 140 }), {})
equal("⛔ ... and is what it goes back to", R.inputs.fast(st, { 0 })[1], { "tempo", "float", { 140 } })
equal("the phone's tempo under it reaches the bus, and is gone at the release",
      (function()
        R.inputs.fast(st, { 1, 140 })
        local out = R.inputs.tempo(st, { 200 })
        return { out, R.inputs.fast(st, { 0 })[1] }
      end)(), { tempo(200), { "tempo", "float", { 140 } } })

print("\n--- rush, knob 4 ---")
local map_rules = dofile(DIR .. "u_map.lua")
equal("its bottom is u_map's, where the hold lets go", R.RUSH_BOTTOM, map_rules.RUSH_BOTTOM)
local near = function(a, b) return math.abs(a - b) < 1e-6 * b end
check("⛔ one curve: the tempo at the knob's bottom, 22 kHz as a one-step loop's BPM at its top",
      near(R.rush_bpm(120, R.RUSH_BOTTOM), 120) and near(R.rush_bpm(120, 1), 330000))
local mid = (R.RUSH_BOTTOM + 1) / 2
check("⛔ ... and even in ratio: half the turn is the geometric mean, wherever it starts",
      near(R.rush_bpm(120, mid), (120 * 330000) ^ 0.5) and near(R.rush_bpm(60, mid), (60 * 330000) ^ 0.5))
-- Where the curve from 120 stands at a BPM.
local function x_at(bpm)
  return R.RUSH_BOTTOM + (1 - R.RUSH_BOTTOM) * math.log(bpm / 120) / math.log(R.RUSH_TOP / 120)
end
local function sent(out, kind)
  for _, e in ipairs(out) do
    if e[1] == kind then return e[3][1] end
  end
end
st = R.new()
equal("held by u_map, it draws its row with the knob's place in brackets, and does nothing else",
      R.inputs.rush(st, { 0.57, 0, 120 }), { { "disp", "rush", { 0, "(57)" } } })
equal("at its bottom, nothing to do: the row, the tempo in force", R.inputs.rush(st, { 0, 1, 120 }),
      { { "disp", "rush", { 120, "bpm" } } })
local out = R.inputs.rush(st, { x_at(500), 1, 120 })
equal("⛔ leaving its bottom: the put shut first, then the curve's BPM on its own bus, never tempo, so "
      .. "knob 1 is not held, and the row",
      out, { { "put", "float", { 0 } }, { "bus", "float", { 500 } }, { "disp", "rush", { 500, "bpm" } } })
out = R.inputs.rush(st, { x_at(900), 1, 500 })
equal("⛔ the curve keeps the tempo it left its bottom at, not the one on the bus now",
      out, { { "bus", "float", { 900 } }, { "disp", "rush", { 900, "bpm" } } })
out = R.inputs.rush(st, { x_at(1500), 1, 900 })
check("⛔ at the handoff: the bus at 1000 and no further, then the rate to c_steps, which draws the row",
      #out == 2 and sent(out, "bus") == 1000 and near(sent(out, "steps"), 1500), T.show(out))
out = R.inputs.rush(st, { x_at(20000), 1, 1000 })
check("past it: the rate alone", #out == 1 and near(sent(out, "steps"), 20000), T.show(out))
out = R.inputs.rush(st, { x_at(990), 1, 1000 })
check("⛔ coming down it holds on a little under the handoff, so a knob at rest does not capture again",
      #out == 1 and near(sent(out, "steps"), 990), T.show(out))
equal("⛔ below that: the tempo, and the loop told to stop", R.inputs.rush(st, { x_at(700), 1, 1000 }),
      { { "bus", "float", { 700 } }, { "steps", "rush", { 0 } }, { "disp", "rush", { 700, "bpm" } } })
equal("⛔ back at its bottom: the tempo it left, the row, and the put open, with nothing put by then",
      R.inputs.rush(st, { 0, 1, 700 }),
      { { "bus", "float", { 120 } }, { "disp", "rush", { 120, "bpm" } }, { "put", "float", { 1 } } })
check("... and it is over", st.rush == nil)
R.inputs.rush(st, { x_at(20000), 1, 120 })
equal("⛔ straight from past the handoff to its bottom, the loop stops too",
      R.inputs.rush(st, { 0, 1, 1000 }),
      { { "bus", "float", { 120 } }, { "steps", "rush", { 0 } }, { "disp", "rush", { 120, "bpm" } },
        { "put", "float", { 1 } } })
R.inputs.rush(st, { x_at(300), 1, 120 })
equal("⛔ a section's tempo under it changes nothing now ...", R.inputs.restored(st, { 90 }), {})
equal("⛔ ... and is what it goes back to", R.inputs.rush(st, { 0, 1, 300 })[1], { "bus", "float", { 90 } })
R.inputs.rush(st, { x_at(300), 1, 120 })
equal("⛔ pad-35 under it: 500, as ever", R.inputs.fast(st, { 1, 300 })[2], { "tempo", "float", { 500 } })
equal("⛔ ... its release snaps back to the tempo rush left from, with the put still shut",
      R.inputs.fast(st, { 0 }), { { "tempo", "float", { 120 } } })
equal("... and that is what rush goes back to, the put open at last", R.inputs.rush(st, { 0, 1, 120 }),
      { { "bus", "float", { 120 } }, { "disp", "rush", { 120, "bpm" } }, { "put", "float", { 1 } } })
R.inputs.fast(st, { 1, 120 })
R.inputs.rush(st, { 0.02, 1, 500 })
equal("⛔ rush under pad-35 starts from 500, and goes back there, the put shut for pad-35",
      R.inputs.rush(st, { 0, 1, 800 }), { { "bus", "float", { 500 } }, { "disp", "rush", { 500, "bpm" } } })
equal("⛔ ... and pad-35's release still snaps back", R.inputs.fast(st, { 0 }),
      { { "tempo", "float", { 120 } }, { "put", "float", { 1 } } })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "u_tempo-lua.pd_lua", DIR)
check("u_tempo-lua.pd_lua registers the class u_tempo-lua", class and class._name == "u_tempo-lua",
      class and class._name)
local o = T.new(class, {})
check("an object has two inlets and seven outlets", o and o.inlets == 2 and o.outlets == 7,
      o and (o.inlets .. " " .. o.outlets))
equal("init: the bang on outlet 3 that says it loaded, and nothing else",
      T.send(o, 2, "init", {}), { { 3, "bang", {} } })
equal("tap <ms> on inlet 1: the first starts the count", T.send(o, 1, "tap", { 9000 }), {})
equal("... the next sets the tempo on outlet 1, as a float", T.send(o, 1, "tap", { 600 }),
      { { 1, "float", { 100 } } })
equal("tempo <bpm> on inlet 1, from the phone, the same", T.send(o, 1, "tempo", { 140 }),
      { { 1, "float", { 140 } } })
equal("a bad one leaves outlet 2 for err", T.send(o, 1, "tempo", { "x" }),
      { { 2, "fail", { "u_tempo", "bad-tempo" } } })
equal("⛔ fast 1 on inlet 1 shuts the put on outlet 4, then 500 on outlet 1",
      T.send(o, 1, "fast", { 1, 140 }), { { 4, "float", { 0 } }, { 1, "float", { 500 } } })
equal("⛔ fast 0 the tempo before it, then the put open",
      T.send(o, 1, "fast", { 0 }), { { 1, "float", { 140 } }, { 4, "float", { 1 } } })
local face = T.send(o, 1, "rush", { 0.2, 1, 120 })
equal("⛔ rush on inlet 1: the put on outlet 4, its BPM on outlet 5, not 1, and its row on outlet 7",
      { face[1][1], face[2][1], face[3][1], face[3][2] }, { 4, 5, 7, "rush" })
face = T.send(o, 1, "rush", { 1, 1, 120 })
equal("⛔ past the handoff, rush <bpm> on outlet 6, for c_steps", { face[2][1], face[2][2] }, { 6, "rush" })
T.send(o, 1, "rush", { 0, 1, 120 })
for _, m in ipairs({ { 1, "bang", {} }, { 1, "float", { 3 } }, { 2, "tap", { 500 } } }) do
  equal(string.format("%s on inlet %d is fail u_tempo bad-selector on outlet 2", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 2, "fail", { "u_tempo", "bad-selector" } } })
end
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "tempo", { 77 }); return o.sent end)(),
      { { 1, "float", { 77 } } })

-- A Lua error, made by a copy of the rules whose tap throws: the class reads its rules as
-- prefix .. "u_tempo.lua", so the copy sits at a temporary prefix, with the face beside it.
local tmp = os.tmpname()
fh = assert(io.open(tmp .. "-u_tempo.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'u_tempo.lua")\n',
         'R.inputs.tap = function() error("a bug in tap") end\nreturn R\n')
fh:close()
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "u_tempo-lua.pd_lua", tmp .. "-"), {})
os.remove(tmp .. "-u_tempo.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
equal("a Lua error leaves outlet 2 as fail u_tempo lua-tap, for the error log",
      T.send(broken, 1, "tap", { 500 }), { { 2, "fail", { "u_tempo", "lua-tap" } } })
check("... with its text on the console", #broken.console == 1
      and broken.console[1]:find("a bug in tap", 1, true) ~= nil, T.show(broken.console))
equal("... and the object carries on: the phone's tempo still answers",
      T.send(broken, 1, "tempo", { 120 }), { { 1, "float", { 120 } } })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

os.exit(T.report() == 0)
