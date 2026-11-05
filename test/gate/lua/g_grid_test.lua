-- The drum page's painter without Pd: "Cut It/g_grid.lua", and the Pd face that carries it,
-- "Cut It/g_grid-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The display gate runs
-- this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/g_grid_test.lua [-v]
--
-- What reaches the Launchpad -- the frame clock, the layers, the SysEx, the rest of the page --
-- is display-assert.py's and sequencer-assert.py's, on a running copy of the instrument.
-- ref/module/display.md, g_grid's drum page.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "g_grid.lua")
local check, equal = T.check, T.equal

local fh = assert(io.open(DIR .. "cut-it-drum-page.txt"))
local LAYOUT = fh:read("a")
fh:close()
fh = assert(io.open(DIR .. "g_grid.pd"))
local PATCH = fh:read("a")
fh:close()

-- The RGB table in g_grid.pd's paint, the one message that sets it, 32 entries of three: a color
-- of 128 + k is entry k.
local RGB = {}
for body in PATCH:gmatch("\n#X msg %d+ %d+ ([%d ]+);\n#X obj %d+ %d+ array set \\%$0%-rgb;") do
  for v in body:gmatch("%d+") do RGB[#RGB + 1] = tonumber(v) end
end
local DEFINED = tonumber(PATCH:match("\n#X obj %d+ %d+ array define \\%$0%-rgb (%d+);"))
local function rgb(color)
  if color < 128 then return color end
  local k = (color - 128) * 3
  return { RGB[k + 1], RGB[k + 2], RGB[k + 3] }
end

-- The colors ref/module/display.md gives the drum page, read through the table.
local LEVEL = { { 127, 127, 127 }, { 127, 109, 109 }, { 127, 91, 91 }, { 127, 73, 73 },
                { 127, 54, 54 }, { 127, 36, 36 }, { 127, 18, 18 }, { 127, 0, 0 } }
local QUARTER = { { 32, 32, 32 }, { 32, 27, 27 }, { 32, 23, 23 }, { 32, 18, 18 },
                  { 32, 14, 14 }, { 32, 9, 9 }, { 32, 4, 4 }, { 32, 0, 0 } }
local PINK, RED, BLUE = { 127, 20, 72 }, { 127, 0, 0 }, { 16, 40, 127 }
-- A pad whose track won't play, muted or left out of a solo: the pink, or the selected pad's red,
-- at a quarter (Brendan, 2026-11-05).
local PINK_QUIET, RED_QUIET = { 32, 5, 18 }, { 32, 0, 0 }
local REP, HELD = { 20, 8, 32 }, { 80, 24, 127 }
local DARK, DIM, GREEN = 0, 1, 21

-- A paint as {grid index: color}, the color as the Launchpad shows it.
local function frame(st)
  local index, colors = R.paint(st)
  local f = {}
  for k = 1, #index do f[index[k]] = rgb(colors[k]) end
  return f
end

-- The layout's cells by role: {role: {n: grid index}}.
local CELL = { step = {}, vel = {}, pad = {}, rep = {} }
for line in LAYOUT:gmatch("[^\n]+") do
  local i, r, n = line:match("^(%d+) (%a+) (%d+)$")
  if i then CELL[r][tonumber(n)] = tonumber(i) end
end

-- The step cells' colors, cells 1 to 32 along the four rows of eight.
local function cells(f)
  local out = {}
  for n = 1, 32 do out[n] = f[CELL.step[n]] end
  return out
end

-- A fresh page with these messages sent, in order.
local function page(...)
  local st = R.new(LAYOUT)
  for _, m in ipairs({ ... }) do R.inputs[m[1]](st, { table.unpack(m, 2) }) end
  return st
end

local function rep(v, n)
  local t = {}
  for i = 1, n do t[i] = v end
  return t
end

print("\n--- the colors are g_grid's RGB table's ---")
check("the table is g_grid.pd's 32 entries of three, the array defined to hold them",
      #RGB == 96 and DEFINED == 96, T.show({ #RGB, DEFINED }))
local lv, qt = {}, {}
for v = 1, 8 do lv[v], qt[v] = rgb(R.LEVEL + v - 1), rgb(R.QUARTER + v - 1) end
equal("a level's color, full: white for level 1 falling evenly to red for 8", lv, LEVEL)
equal("... and at a quarter, for a velocity button not selected", qt, QUARTER)
equal("a pad, the selected pad, a blue step, a repeat pad and the one held",
      { rgb(R.PAD), rgb(R.PAD_ON), rgb(R.BLUE), rgb(R.REP), rgb(R.REP_HELD) },
      { PINK, RED, BLUE, REP, HELD })
equal("⛔ a pad whose track won't play: the pink at a quarter, and the selected pad's red",
      { rgb(R.PAD_QUIET), rgb(R.PAD_ON_QUIET) }, { PINK_QUIET, RED_QUIET })
equal("dark, dim and the playhead are palette 0, 1 and 21", { R.DARK, R.DIM, R.PLAYHEAD },
      { 0, 1, 21 })

print("\n--- the layout ---")
local st = R.new(LAYOUT)
local count = { step = 0, vel = 0, pad = 0, rep = 0 }
for k in pairs(CELL) do for _ in pairs(CELL[k]) do count[k] = count[k] + 1 end end
equal("cut-it-drum-page.txt: 32 step cells, 8 velocity buttons, 16 pads, 4 repeat pads", count,
      { step = 32, vel = 8, pad = 16, rep = 4 })
local ORDER = {}
for line in LAYOUT:gmatch("[^\n]+") do ORDER[#ORDER + 1] = tonumber(line:match("^(%d+)")) end
equal("paint writes those 60 cells and no other, in the table's order", R.paint(st), ORDER)
equal("a row of another role, a blank line or a malformed one paints nothing",
      R.paint(R.new("11 pad 1\n\n12 mute 2\nx pad 3\n13 4 5\n14 rep\n15 rep 2\n")),
      { 11, 15 })

print("\n--- at load ---")
local f = frame(st)
equal("⛔ every step cell dark until c_steps sends its first bar: no step to a row", cells(f),
      rep(DARK, 32))
equal("every velocity button a quarter: none selected", (function()
  local t = {}
  for v = 1, 8 do t[v] = f[CELL.vel[v]] end
  return t
end)(), QUARTER)
equal("every pad bright pink, every repeat pad dim purple", (function()
  local t = {}
  for n = 1, 16 do t[#t + 1] = f[CELL.pad[n]] end
  for n = 1, 4 do t[#t + 1] = f[CELL.rep[n]] end
  return t
end)(), (function()
  local t = rep(PINK, 16)
  for _ = 1, 4 do t[#t + 1] = REP end
  return t
end)())

print("\n--- the rows of steps ---")
local want = rep(DIM, 16)
for _, n in ipairs({ 1, 5, 9, 13 }) do want[n] = BLUE end
for n = 17, 32 do want[n] = DARK end
equal("4/4, bar 4 8, last 16: steps 1 to 16 dim, every 4th blue, 17 to 32 past the last, dark",
      cells(frame(page({ "bar", 4, 8 }))), want)
want = rep(DIM, 32)
for _, n in ipairs({ 1, 4, 9, 12, 17, 20, 25, 28 }) do want[n] = BLUE end
for _, n in ipairs({ 7, 8, 15, 16, 23, 24, 31, 32 }) do want[n] = DARK end
equal("⛔ 3/4, bar 3 6, last 24: rows of six, cells 7 and 8 of each dark, blue every 3rd",
      cells(frame(page({ "bar", 3, 6 }, { "last", 24 }))), want)
equal("... and the second row's first cell is step 7: lit at level 2, it shows level 2",
      frame(page({ "bar", 3, 6 }, { "last", 24 }, { "steps", 0, 0, 0, 0, 0, 0, 2 }))[CELL.step[9]],
      LEVEL[2])
want = rep(DIM, 32)
for _, n in ipairs({ 1, 10, 19, 28 }) do want[n] = BLUE end
equal("9/8, bar 9 8, last 32: blue every 9th, wrapping across the rows", cells(frame(page(
      { "bar", 9, 8 }, { "last", 32 }))), want)
-- The step cells in rows of `row`, blue every `every`th, past `last` dark.
local function rows(every, row, last)
  local w = {}
  for n = 1, 32 do
    local c = (n - 1) % 8
    local s = (n - 1) // 8 * row + c + 1
    if c >= row or s > last then w[n] = DARK
    else w[n] = (s - 1) % every == 0 and BLUE or DIM end
  end
  return w
end
equal("7/8, bar 7 7, last 28: rows of seven, the eighth cell dark, blue every 7th",
      cells(frame(page({ "bar", 7, 7 }, { "last", 28 }))), rows(7, 7, 28))
equal("5/4, bar 5 5, last 20: rows of five, blue every 5th", cells(frame(page({ "bar", 5, 5 },
      { "last", 20 }))), rows(5, 5, 20))
equal("bar 0 is Pd's mod by 1: every step blue", cells(frame(page({ "bar", 0, 8 }))),
      (function() local t = rep(BLUE, 16) for n = 17, 32 do t[n] = DARK end return t end)())

print("\n--- the steps ---")
local lit = { 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 1 }
st = page({ "bar", 4, 8 }, { "steps", table.unpack(lit) })
f = frame(st)
equal("a step on is its level's color, full, white to red", { f[CELL.step[1]], f[CELL.step[3]],
      f[CELL.step[9]], f[CELL.step[15]] }, { LEVEL[1], LEVEL[2], LEVEL[5], LEVEL[8] })
equal("an off step is dim, or blue every 4th: a lit 4th is its level", { f[CELL.step[2]],
      f[CELL.step[5]], f[CELL.step[13]] }, { DIM, LEVEL[3], LEVEL[7] })
equal("⛔ a step past the last step is dark, lit or not: 17 at level 8, 32 at level 1",
      { f[CELL.step[17]], f[CELL.step[32]], f[CELL.step[18]] }, { DARK, DARK, DARK })
R.inputs.last(st, { 32 })
f = frame(st)
equal("... and shows again when the last step reaches it", { f[CELL.step[17]], f[CELL.step[32]] },
      { LEVEL[8], LEVEL[1] })
R.inputs.steps(st, { 0, 0, 0 })
f = frame(st)
equal("a shorter steps sets the steps it holds and keeps the rest",
      { f[CELL.step[1]], f[CELL.step[3]], f[CELL.step[5]] }, { BLUE, DIM, LEVEL[3] })

print("\n--- the playhead ---")
st = page({ "bar", 4, 8 }, { "steps", 3, 0, 0, 0, 0, 0, 0, 0 })
local function at(play)
  R.inputs.play(st, { play })
  local f = frame(st)
  local n = 0
  for _, c in pairs(cells(f)) do if c == GREEN then n = n + 1 end end
  return n, f
end
local n1, f1 = at(1)
local n2, f2 = at(5)
local n3, f3 = at(2)
equal("green over a lit step, a blue one and a dim one, one cell each time",
      { n1, f1[CELL.step[1]], n2, f2[CELL.step[5]], n3, f3[CELL.step[2]] },
      { 1, GREEN, 1, GREEN, 1, GREEN })
equal("... and the step it left shows what it holds again", { f2[CELL.step[1]], f3[CELL.step[5]] },
      { LEVEL[3], BLUE })
local n0 = at(0)
equal("play 0, stopped: no playhead", n0, 0)
local n20, f20 = at(20)
equal("over a step past the last step, green as g_grid.pd drew it", { n20, f20[CELL.step[20]] },
      { 1, GREEN })
equal("play 33, past every step: no cell at 4/4 shows it, so none is green",
      (function()
        local s = page({ "bar", 4, 8 }, { "last", 32 }, { "play", 33 })
        local g = 0
        for _, c in pairs(cells(frame(s))) do if c == GREEN then g = g + 1 end end
        return g
      end)(), 0)

print("\n--- the buttons and the pads ---")
st = page({ "vel", 6 }, { "track", 13 }, { "rep", 3 })
f = frame(st)
equal("the selected velocity button full, the rest a quarter", (function()
  local t = {}
  for v = 1, 8 do t[v] = f[CELL.vel[v]] end
  return t
end)(), { QUARTER[1], QUARTER[2], QUARTER[3], QUARTER[4], QUARTER[5], LEVEL[6], QUARTER[7],
          QUARTER[8] })
equal("⛔ the selected pad red, the other fifteen bright pink", (function()
  local red, pink = {}, 0
  for p = 1, 16 do
    if T.same(f[CELL.pad[p]], RED) then red[#red + 1] = p
    elseif T.same(f[CELL.pad[p]], PINK) then pink = pink + 1 end
  end
  return { red, pink }
end)(), { { 13 }, 15 })
equal("the repeat pad held bright purple, the other three dim", { f[CELL.rep[1]], f[CELL.rep[2]],
      f[CELL.rep[3]], f[CELL.rep[4]] }, { REP, REP, HELD, REP })
R.inputs.rep(st, { 0 })
R.inputs.track(st, { 1 })
R.inputs.vel(st, { 1 })
f = frame(st)
equal("rep 0 holds none; pad 1 and level 1 follow", { f[CELL.rep[3]], f[CELL.pad[1]],
      f[CELL.pad[13]], f[CELL.vel[1]], f[CELL.vel[6]] }, { REP, RED, PINK, LEVEL[1], QUARTER[6] })
-- The pads in order, 1 to 16, as the Launchpad shows them.
local function pads(fr)
  local t = {}
  for p = 1, 16 do t[p] = fr[CELL.pad[p]] end
  return t
end
R.inputs.quiet(st, { 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1 })
local want_pads = rep(PINK, 16)
want_pads[1], want_pads[3], want_pads[16] = RED_QUIET, PINK_QUIET, PINK_QUIET
equal("⛔ quiet 1 0 1 ... 1: pad 1, selected, dim red, pads 3 and 16 dim pink, the rest as they were",
      pads(frame(st)), want_pads)
R.inputs.quiet(st, { 0, 1 })
want_pads[1], want_pads[2] = RED, PINK_QUIET
equal("... a shorter list sets the pads it holds: pad 1 red again, pad 2 dim, 3 and 16 still dim",
      pads(frame(st)), want_pads)
R.inputs.track(st, { 3 })
want_pads[1], want_pads[3] = PINK, RED_QUIET
equal("⛔ ... and a quiet pad selected is dim red, the one it left bright pink",
      pads(frame(st)), want_pads)

print("\n--- what changes nothing ---")
st = page({ "bar", 4, 8 }, { "play", 2 }, { "vel", 3 })
local before = frame(st)
R.inputs.play(st, {})
R.inputs.play(st, { "x" })
R.inputs.vel(st, { "x" })
R.inputs.steps(st, { "x", 5, 5 })
R.inputs.bar(st, { "x", 6 })
R.inputs.quiet(st, { "x", 1, 1 })
R.inputs.quiet(st, {})
equal("a field left off, or one that is not a number, as in Pd", frame(st), before)
R.inputs.bar(st, { 3 })
equal("bar <N> without a row keeps the row: blue every 3rd in rows of eight", cells(frame(st))[4],
      BLUE)
check("every input answers nothing: the page is painted, not sent", (function()
  local s = R.new(LAYOUT)
  for name, rule in pairs(R.inputs) do
    if #rule(s, { 1, 1 }) ~= 0 then return false end
  end
  return true
end)())

print("\n--- init ---")
equal("init with the layout answers nothing", R.internal.init(R.new(LAYOUT)), {})
equal("⛔ init with no cell is fail g_grid layout-empty: the page would paint nothing",
      R.internal.init(R.new("")), { { "err", "fail", { "g_grid", "layout-empty" } } })

print("\n--- the Pd face ---")
local class = T.load_class(DIR .. "g_grid-lua.pd_lua", DIR)
check("g_grid-lua.pd_lua registers the class g_grid-lua", class and class._name == "g_grid-lua",
      class and class._name)
T.arrays["1003-surface"] = T.array(109)
local surface = T.arrays["1003-surface"]
local o = T.new(class, { "1003-surface" })
check("an object has two inlets and two outlets", o and o.inlets == 2 and o.outlets == 2,
      o and (o.inlets .. " " .. o.outlets))
check("... and read the layout from its patch's folder, in silence", o and #o.state.index == 60
      and #o.console == 0, o and T.show(o.console))
equal("init: the bang on outlet 2 that says it loaded, and nothing else",
      T.send(o, 2, "init", {}), { { 2, "bang", {} } })
equal("c_steps' page on inlet 1 answers nothing", {
  T.send(o, 1, "bar", { 4, 8 }), T.send(o, 1, "steps", { 8, 0, 0, 0, 2 }),
  T.send(o, 1, "track", { 5 }), T.send(o, 1, "vel", { 2 }), T.send(o, 1, "play", { 3 }),
  T.send(o, 1, "last", { 16 }), T.send(o, 1, "rep", { 4 }),
  T.send(o, 1, "quiet", { 0, 0, 0, 0, 1, 1 }) }, { {}, {}, {}, {}, {}, {}, {}, {} })
for i = 0, 108 do surface[i] = 7 end
equal("paint on inlet 2 answers nothing", T.send(o, 2, "paint", {}), {})
equal("... and writes the page into the frame buffer: step 1 level 8, step 3 the playhead, "
      .. "step 5 blue and lit at 2, pad 5 red and pad 6 pink, both quiet, so at a quarter, pad 7 "
      .. "pink, level 2 full, repeat pad 4 held", {
  surface[CELL.step[1]], surface[CELL.step[2]], surface[CELL.step[3]], surface[CELL.step[5]],
  surface[CELL.step[17]], surface[CELL.pad[5]], surface[CELL.pad[6]], surface[CELL.pad[7]],
  surface[CELL.vel[2]], surface[CELL.vel[1]], surface[CELL.rep[4]], surface[CELL.rep[1]] },
  { 135, 1, 21, 129, 0, 159, 158, 144, 129, 136, 147, 146 })
check("⛔ ... and nothing outside its 60 cells: the fill and the other regions are g_grid.pd's",
      (function()
        local mine = {}
        for line in LAYOUT:gmatch("[^\n]+") do mine[tonumber(line:match("^(%d+)"))] = true end
        for i = 0, 108 do if not mine[i] and surface[i] ~= 7 then return false end end
        return true
      end)())
for _, m in ipairs({ { 1, "bang", {} }, { 1, "float", { 3 } }, { 1, "paint", {} },
                     { 2, "steps", { 1 } } }) do
  equal(string.format("%s on inlet %d is fail g_grid bad-selector on outlet 1", m[2], m[1]),
        T.send(o, m[1], m[2], m[3]), { { 1, "fail", { "g_grid", "bad-selector" } } })
end
equal("pdlua's dispatch reaches inlet 1 through the class's own",
      (function() o.sent = {}; o:dispatch(1, "bogus", {}); return o.sent end)(),
      { { 1, "fail", { "g_grid", "bad-selector" } } })
equal("no frame buffer by that name is fail g_grid no-surface",
      T.send(T.new(class, { "1004-surface" }), 2, "paint", {}),
      { { 1, "fail", { "g_grid", "no-surface" } } })
equal("... nor with no name at all", T.send(T.new(class, {}), 2, "paint", {}),
      { { 1, "fail", { "g_grid", "no-surface" } } })
check("⛔ a frame buffer made after the object is found at its first paint after: it is looked "
      .. "up every frame", (function()
  local late = T.new(class, { "1005-surface" })
  local none = T.send(late, 2, "paint", {})
  T.arrays["1005-surface"] = T.array(109)
  local now = T.send(late, 2, "paint", {})
  return #none == 1 and #now == 0 and T.arrays["1005-surface"][CELL.pad[1]] == R.PAD
end)())

local tmp = os.tmpname()
local nolayout = T.new(class, { "1003-surface" }, tmp .. "-")
check("⛔ no layout file: its error on the console, which fails a deploy", #nolayout.console == 1
      and nolayout.console[1]:find("cut-it-drum-page.txt", 1, true) ~= nil,
      T.show(nolayout.console))
equal("... and init is fail g_grid layout-empty, then the proof bang",
      T.send(nolayout, 2, "init", {}),
      { { 1, "fail", { "g_grid", "layout-empty" } }, { 2, "bang", {} } })

-- A Lua error, made by a copy of the rules whose paint throws: the class reads its rules as
-- prefix .. "g_grid.lua", so the copy sits at a temporary prefix, with the face beside it.
fh = assert(io.open(tmp .. "-g_grid.lua", "w"))
fh:write('local R = dofile("' .. DIR .. 'g_grid.lua")\n',
         'R.paint = function() error("a bug in paint") end\n',
         'R.inputs.vel = function() error("a bug in vel") end\nreturn R\n')
fh:close()
fh = assert(io.open(tmp .. "-lua-face.lua", "w"))
fh:write('return dofile("' .. DIR .. 'lua-face.lua")\n')
fh:close()
local broken = T.new(T.load_class(DIR .. "g_grid-lua.pd_lua", tmp .. "-"), { "1003-surface" }, DIR)
os.remove(tmp .. "-g_grid.lua")
os.remove(tmp .. "-lua-face.lua")
os.remove(tmp)
for i = 0, 108 do surface[i] = 7 end
equal("a Lua error in paint leaves outlet 1 as fail g_grid lua-paint, for the error log",
      T.send(broken, 2, "paint", {}), { { 1, "fail", { "g_grid", "lua-paint" } } })
check("... with its text on the console, and the frame buffer untouched", #broken.console == 1
      and broken.console[1]:find("a bug in paint", 1, true) ~= nil and surface[81] == 7,
      T.show(broken.console))
equal("one in a message is fail g_grid lua-<selector>", T.send(broken, 1, "vel", { 2 }),
      { { 1, "fail", { "g_grid", "lua-vel" } } })
equal("... and the object carries on: the next message still sets the page",
      { T.send(broken, 1, "track", { 2 }), broken.state.track }, { {}, 2 })
equal("a report is one symbol of 21 characters or fewer",
      R.fail("lua-" .. string.rep("x", 30))[3][2], "lua-" .. string.rep("x", 17))

print("\n--- g_grid.pd ---")
check("g_grid.pd makes [g_grid-lua $0-surface], its frame buffer by name, and declares pdlua",
      PATCH:find("\n#X obj %d+ %d+ g_grid%-lua \\%$0%-surface;") ~= nil
      and PATCH:find("\n#X declare %-lib pdlua;") ~= nil
      and PATCH:find("\n#X obj %d+ %d+ array define \\%$0%-surface 109;") ~= nil)
check("... and no longer reads the layout itself: the Lua does",
      PATCH:find("cut-it-drum-page.txt;", 1, true) == nil)

os.exit(T.report() == 0)
