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
equal("its two ends are u_map's, where it holds the knob", { R.RUSH_LOW, R.RUSH_TOP }, { map_rules.RUSH_LOW, map_rules.RUSH_TOP })
local near = function(a, b) return math.abs(a - b) < 1e-6 * b end
check("⛔ an absolute rate over the whole turn: 10 BPM at the bottom, 22 kHz as a one-step loop's BPM at the top",
      near(R.rush_bpm(0), 10) and near(R.rush_bpm(1), 330000) and near(R.rush_bpm(0.5), (10 * 330000) ^ 0.5))
local x_at = function(rate) return math.log(rate / 10) / math.log(R.RUSH_TOP / 10) end
check("⛔ the rest of the turn past the handoff runs 0 to 1", near(R.rush_past(x_at(1000)) + 1, 1)
      and near(R.rush_past(1), 1) and R.rush_past(0.1) == 0)
st = R.new()
equal("⛔ held by u_map: its row is the tempo in force with the knob's own rate in brackets, and nothing else",
      R.inputs.rush(st, { 0.5, 0, 120 }), { { "disp", "rush", { 120, "(1817)" } } })
equal("... in thousands up there, so it fits the screen", R.inputs.rush(st, { 1, 0, 120 })[1][3][2], "(330k)")
equal("⛔ live: the put shut first, then the rate on its own bus, and the row",
      R.inputs.rush(st, { x_at(500), 1, 120 }),
      { { "put", "float", { 0 } }, { "bus", "float", { 500 } }, { "disp", "rush", { 500, "bpm" } } })
equal("⛔ ... down to 10 BPM", R.inputs.rush(st, { 0, 1, 500 }),
      { { "bus", "float", { 10 } }, { "disp", "rush", { 10, "bpm" } } })
local function sent(out, kind)
  for _, e in ipairs(out) do
    if e[1] == kind then return e[3][1] end
  end
end
local out = R.inputs.rush(st, { x_at(1500), 1, 10 })
check("⛔ at the handoff: the bus at 1000 and no further, then how far past to c_steps, which draws the row",
      #out == 2 and sent(out, "bus") == 1000 and near(sent(out, "steps") + 1, R.rush_past(x_at(1500)) + 1), T.show(out))
out = R.inputs.rush(st, { 1, 1, 1000 })
check("past it: how far alone, 1 at the top", #out == 1 and sent(out, "steps") == 1, T.show(out))
out = R.inputs.rush(st, { x_at(990), 1, 1000 })
check("⛔ coming down it holds on a little under the handoff, so a knob at rest does not capture again",
      #out == 1 and sent(out, "steps") == 0, T.show(out))
equal("⛔ below that: the tempo, then the loop told to hand back at it", R.inputs.rush(st, { x_at(700), 1, 1000 }),
      { { "bus", "float", { 700 } }, { "steps", "rush-back", { 700 } }, { "disp", "rush", { 700, "bpm" } } })
for _, c in ipairs({ { "a tap", function(q) R.tap(q, 5000); return R.tap(q, 500) end, 120 },
                     { "the phone", function(q) return R.inputs.tempo(q, { 133 }) end, 133 },
                     { "a section's restore", function(q) return R.inputs.restored(q, { 90 }) end, 90 } }) do
  st = R.new()
  R.inputs.rush(st, { 1, 1, 120 })
  equal("⛔ " .. c[1] .. " ends rush: the loop stops, the put opens, then its tempo, as a tap's, so both knobs are held",
        c[2](st), { { "steps", "rush-off", {} }, { "put", "float", { 1 } }, { "tempo", "float", { c[3] } } })
  check("... and it is over", st.rush == nil)
end
st = R.new()
R.inputs.rush(st, { 1, 1, 120 })
equal("⛔ knob 1 going live ends it too, u_map saying so before the BPM, which it sends itself",
      R.inputs.rush(st, { -1, 1, 1000 }), { { "steps", "rush-off", {} }, { "put", "float", { 1 } } })
R.inputs.rush(st, { 1, 1, 120 })
equal("⛔ pad-38: over at once, whatever comes back, the knobs held where the bus is",
      R.inputs["rush-home"](st, {}), { { "steps", "rush-off", {} }, { "put", "float", { 1 } }, { "hold", "float", { 1000 } } })
equal("... and with no rush it does nothing", R.inputs["rush-home"](st, {}), {})
R.inputs.rush(st, { 1, 1, 120 })
equal("⛔ pad-35 pressed ends it, the put stays shut, and the tempo it was at is what it goes back to",
      R.inputs.fast(st, { 1, 1000 }), { { "steps", "rush-off", {} }, { "put", "float", { 0 } }, { "tempo", "float", { 500 } } })
R.inputs.rush(st, { x_at(800), 1, 500 })
equal("⛔ turned through 500 under it, rush again; its release ends that, with the put open only after",
      R.inputs.fast(st, { 0 }), { { "tempo", "float", { 1000 } }, { "put", "float", { 1 } } })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "u_tempo-lua.pd_lua", DIR)
check("u_tempo-lua.pd_lua registers the class u_tempo-lua", class and class._name == "u_tempo-lua",
      class and class._name)
local o = T.new(class, {})
check("an object has two inlets and eight outlets", o and o.inlets == 2 and o.outlets == 8,
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
equal("⛔ past the handoff, rush <0-1> on outlet 6, for c_steps", { face[2][1], face[2][2] }, { 6, "rush" })
face = T.send(o, 1, "rush-home", {})
equal("⛔ rush-home: rush-off on outlet 6, and the hold on outlet 8", { face[1][1], face[1][2], face[3][1] }, { 6, "rush-off", 8 })
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
