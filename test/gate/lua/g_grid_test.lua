-- The Launchpad's home without Pd, every page's cells and the edges: "Cut It/g_grid.lua", and the Pd face that carries it,
-- "Cut It/g_grid-lua.pd_lua", loaded through lib_test's stand-in for pdlua. The display gate runs
-- this before its Pd half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/g_grid_test.lua [-v]
--
-- What reaches the Launchpad -- the frame clock, the layers, the SysEx, the rest of the page --
-- is display-assert.py's and sequencer-assert.py's, on a running copy of the instrument.
-- ref/module/display.md.

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

-- The RGB table in g_grid.pd's paint, the one message that sets it, 62 entries of three: a color
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
-- A repeat pad and the 500 BPM repeat: the brightest purple there is, and whiter, never dimmer,
-- while held (Brendan, 2026-11-05). The saved tempo: blue, dim, and bright while held.
local REP, HELD = { 127, 0, 127 }, { 127, 80, 127 }
local RECALL, RECALL_HELD = { 8, 20, 64 }, { 40, 100, 127 }
local DARK, DIM, GREEN = 0, 1, 21

-- A paint as {grid index: color}, the color as the Launchpad shows it. A cell paint didn't name is
-- dark: g_grid.pd's fill.
local function frame(st)
  local index, colors, n = R.paint(st)
  local f = setmetatable({}, { __index = function() return DARK end })
  for k = 1, n do f[index[k]] = rgb(colors[k]) end
  return f
end

-- The cells paint named, in order: a list of n, since its tables are the same every frame.
local function painted(st)
  local index, _, n = R.paint(st)
  return { table.unpack(index, 1, n) }
end

-- The layout's cells by role: {role: {n: grid index}}.
local CELL = { step = {}, vel = {}, pad = {}, rep = {}, fast = {}, recall = {} }
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

-- A fresh drum page with these messages sent, in order.
local function page(...)
  local st = R.new(LAYOUT)
  R.inputs.page(st, { "drums" })
  for _, m in ipairs({ ... }) do R.inputs[m[1]](st, { table.unpack(m, 2) }) end
  return st
end

local function rep(v, n)
  local t = {}
  for i = 1, n do t[i] = v end
  return t
end

print("\n--- the colors are g_grid's RGB table's ---")
check("the table is g_grid.pd's 62 entries of three, the array defined to hold them",
      #RGB == 186 and DEFINED == 186, T.show({ #RGB, DEFINED }))
equal("⛔ a repeat at rest is as bright as purple gets, and held its red and blue stay full: whiter",
      { rgb(R.REP)[1], rgb(R.REP)[3], rgb(R.REP_HELD)[1], rgb(R.REP_HELD)[3] }, { 127, 127, 127, 127 })
equal("⛔ the saved tempo's pad, dim blue and bright while held", { rgb(R.RECALL), rgb(R.RECALL_HELD) },
      { RECALL, RECALL_HELD })
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
local st = page()
local count = { step = 0, vel = 0, pad = 0, rep = 0, fast = 0, recall = 0 }
for k in pairs(CELL) do for _ in pairs(CELL[k]) do count[k] = count[k] + 1 end end
equal("cut-it-drum-page.txt: 32 step cells, 8 velocity buttons, 16 pads, 4 repeat pads, the 500 BPM "
      .. "repeat and the saved tempo", count,
      { step = 32, vel = 8, pad = 16, rep = 4, fast = 1, recall = 1 })
local ORDER = {}
for line in LAYOUT:gmatch("[^\n]+") do ORDER[#ORDER + 1] = tonumber(line:match("^(%d+)")) end
equal("paint writes those 62 cells and no other, in the table's order, once they all show: a dark "
      .. "one it leaves to the fill", painted(page({ "bar", 4, 8 }, { "last", 32 })), ORDER)
local partial = R.new("11 pad 1\n\n12 mute 2\nx pad 3\n13 4 5\n14 rep\n15 rep 2\n")
R.inputs.page(partial, { "drums" })
equal("a row of another role, a blank line or a malformed one paints nothing", painted(partial),
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
equal("every pad bright pink, every repeat pad full purple", (function()
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
equal("the repeat pad held whiter purple, the other three full purple", { f[CELL.rep[1]], f[CELL.rep[2]],
      f[CELL.rep[3]], f[CELL.rep[4]] }, { REP, REP, HELD, REP })
equal("⛔ the 500 BPM repeat, pad-35 under repeat pad 1, purple, and the saved tempo, pad-38 under repeat "
      .. "pad 4, dim blue, at rest", { CELL.fast[1], CELL.recall[1], f[CELL.fast[1]], f[CELL.recall[1]] },
      { 35, 38, REP, RECALL })
check("⛔ the cells between them are in no row: pad-36 and pad-37 stay dark", not (function()
  for _, role in pairs(CELL) do
    for _, i in pairs(role) do if i == 36 or i == 37 then return true end end
  end
  return false
end)())
R.inputs.fast(st, { 1 })
R.inputs.recall(st, { 1 })
f = frame(st)
equal("⛔ held, each brightens, and only it", { f[CELL.fast[1]], f[CELL.recall[1]], f[CELL.rep[1]] },
      { HELD, RECALL_HELD, REP })
R.inputs.fast(st, { 0 })
R.inputs.recall(st, { 0 })
R.inputs.rep(st, { 0 })
R.inputs.track(st, { 1 })
R.inputs.vel(st, { 1 })
f = frame(st)
equal("let go, each back", { f[CELL.fast[1]], f[CELL.recall[1]] }, { REP, RECALL })
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

print("\n--- the voices' colors ---")
local VOICES = { { 127, 20, 72 }, { 0, 96, 127 }, { 127, 56, 0 }, { 0, 127, 32 }, { 64, 20, 127 },
                 { 127, 110, 0 }, { 127, 24, 8 }, { 90, 90, 90 } }
local function quarter(c) return { c[1] // 4, c[2] // 4, c[3] // 4 } end
local full, dim, want_full, want_dim = {}, {}, {}, {}
for r = 1, 8 do
  full[r], dim[r] = rgb(R.VOICE + 2 * (r - 1)), rgb(R.VOICE + 2 * (r - 1) + 1)
  want_full[r], want_dim[r] = VOICES[r], quarter(VOICES[r])
end
equal("⛔ a color per row, the same on both columns, full", full, want_full)
equal("... and at a quarter", dim, want_dim)
local fader, fader_dim = {}, {}
for l = 1, 8 do fader[l], fader_dim[l] = rgb(R.FADER + l - 1), rgb(R.FADER_DIM + l - 1) end
equal("a fader's level, green at the bottom to red at the top",
      { fader[1], fader[8] }, { { 0, 127, 32 }, RED })
equal("... and at a quarter while held", { fader_dim[1], fader_dim[8] }, { { 0, 31, 8 }, { 31, 0, 0 } })
equal("a knob blue, and dim while held", { rgb(R.KNOB), rgb(R.KNOB_DIM) }, { BLUE, { 4, 10, 32 } })

print("\n--- the edges, on every page ---")
local function voices(row, kind, ...)
  local a = { row, kind, ... }
  for k = #a + 1, 10 do a[k] = "-" end
  return a
end
st = R.new(LAYOUT)
equal("before any page or voice: the performance page, nothing lit", { st.page, painted(st) },
      { "perform", {} })
R.inputs.voices(st, voices(0, "perform", "drums", "harmony", "melody"))
f = frame(st)
equal("⛔ a row with a voice lights its two buttons dim, in its color, CC 80 and 89 at the top",
      { f[80], f[89], f[70], f[79], f[60], f[69] },
      { dim[1], dim[1], dim[2], dim[2], dim[3], dim[3] })
equal("⛔ ... and a row with none is dark", { f[50], f[59], f[10], f[19] }, { DARK, DARK, DARK, DARK })
R.inputs.voices(st, voices(2, "voice", "drums", "harmony", "melody"))
f = frame(st)
equal("⛔ a voice's page: its left button full, and only it", { f[70], f[79], f[80] },
      { full[2], dim[2], dim[1] })
R.inputs.voices(st, voices(2, "setup", "drums", "harmony", "melody"))
f = frame(st)
equal("⛔ its setup page: its right button full, and only it", { f[70], f[79] }, { dim[2], full[2] })
st = R.new(LAYOUT)
R.inputs.top(st, { 1, 2, 3, 4, 5, 6, 0, 0 })
R.inputs.beat(st, { 0 })
f = frame(st)
equal("the top row, CC 91 to 98: a section dim and full, one queued and the next song's arrow on an even "
      .. "beat, an arrow dim and the next song blue", { f[91], f[92], f[93], f[94], f[95], f[96], f[97] },
      { { 0, 32, 8 }, { 0, 127, 32 }, { 0, 127, 32 }, DIM, BLUE, BLUE, DARK })
R.inputs.beat(st, { 1 })
f = frame(st)
equal("⛔ ... and what blinks is dark on an odd one", { f[93], f[96], f[92], f[95] },
      { DARK, DARK, { 0, 127, 32 }, BLUE })
R.inputs.page(st, { "songs" })
equal("save and revert dark with nothing unsaved", { frame(st)[108], frame(st)[8] }, { DARK, DARK })
R.inputs.unsaved(st, { 1 })
f = frame(st)
equal("⛔ lit with something unsaved, save red and revert gray", { f[108], f[8] }, { RED, { 40, 40, 40 } })
R.inputs.page(st, { "perform" })
f = frame(st)
equal("⛔ but not on the performance page, whose bottom rows are the nanoKONTROL's", { f[108], f[8] },
      { DARK, DARK })

print("\n--- the harmony page ---")
-- What c_melody sends the phone: t's fields, over what doesn't show.
local function melody_state(t)
  local a = {}
  for k = 1, 67 do a[k] = 0 end
  a[1], a[7], a[8], a[9], a[12] = t.chords or 0, t.sounding or 0, t.on_h or 0, t.on_m or 0, t.total or 16
  for k = 1, 8 do a[17 + (k - 1) * 4] = (t.starts or {})[k] or -1 end
  a[56], a[57] = t.style or 1, t.bass or 0
  return a
end
local function harmony(row, t)
  st = R.new(LAYOUT)
  R.inputs.page(st, { "harmony" })
  R.inputs.voices(st, voices(row, "voice", "drums", "harmony"))
  R.inputs.melody(st, melody_state(t))
  R.inputs.bar(st, { 4, 8 })
  return st
end
st = harmony(2, { chords = 3, sounding = 2, total = 16, starts = { 0, 6, 12 } })
f = frame(st)
equal("⛔ the chords on the top row, in the voice's color, dim, and full on the one sounding",
      { f[81], f[82], f[83], f[84] }, { dim[2], full[2], dim[2], DARK })
equal("⛔ under them the rhythm from the top left, a chord full where it starts, a blue step every N, the "
      .. "rest dim", { f[71], f[72], f[75], f[77], f[61], f[65] }, { full[2], DIM, BLUE, full[2], BLUE, full[2] })
equal("⛔ ... and past the rhythm's total, dark: its 16th the second row's last", { f[68], f[51], f[41] },
      { DIM, DARK, DARK })
R.inputs.here(st, { 1, 0 })
equal("the loop's place is green", frame(st)[72], GREEN)
R.inputs.held(st, { 2, 0, 0 })
f = frame(st)
equal("a chord held is white, its pad and where it starts", { f[82], f[77] }, { LEVEL[1], LEVEL[1] })
st = harmony(2, { chords = 1, total = 64, starts = { 60 } })
R.inputs.here(st, { 60, 0 })
f = frame(st)
equal("⛔ a rhythm longer than 56 shows the part playing: step 60 is the top row's fifth cell",
      { f[75], f[71], f[73] }, { GREEN, BLUE, DIM })
st = harmony(2, { chords = 1, on_h = 1, style = 2, bass = 1 })
f = frame(st)
equal("the commands on the upper bottom row: on, roll, the rhythm's roll, bass, modal",
      { f[101], f[102], f[103], f[104], f[105] }, { full[2], dim[2], BLUE, full[2], full[2] })
st = harmony(2, { chords = 1 })
f = frame(st)
equal("... on, bass and modal dim while off", { f[101], f[104], f[105] }, { dim[2], dim[2], dim[2] })

print("\n--- the melody page ---")
local function notes_state(t)
  local a = { t.loop or 32, t.tonic or 0 }
  for d = 1, 7 do a[#a + 1] = ({ 0, 2, 4, 5, 7, 9, 11 })[d] end
  for k = 1, 32 do a[#a + 1] = (t.notes or {})[k] or 0 end
  for k = 1, 32 do a[#a + 1] = (t.codes or {})[k] or 0 end
  return a
end
local function melody(row, t)
  st = R.new(LAYOUT)
  R.inputs.page(st, { "melody" })
  R.inputs.voices(st, voices(row, "voice", "drums", "harmony", "melody"))
  R.inputs.melody(st, melody_state(t))
  R.inputs.notes(st, notes_state(t))
  return st
end
st = melody(3, { loop = 12, notes = { 62, 0, -1, 60 }, codes = { 0, 0, 0, 4 } })
f = frame(st)
equal("⛔ the steps on the top four rows, a note in the voice's color, a rest or one not rolled dim, a pinned "
      .. "note white", { f[81], f[82], f[83], f[84] }, { full[3], DIM, DIM, LEVEL[1] })
equal("⛔ ... and past the loop, dark, the second row's fifth step the 13th", { f[74], f[75], f[61] },
      { DIM, DARK, DARK })
local list = R.pitches(0, { 0, 2, 4, 5, 7, 9, 11 })
equal("⛔ below, the mode's notes low to high from the bottom left, from the lowest tonic at or above "
      .. R.PITCH_LOW, { list[1], list[2], list[8], list[32] }, { 48, 50, 60, 101 })
equal("... the tonic marked in the voice's dim color, the rest dim", { f[11], f[12], f[18], f[21] },
      { dim[3], DIM, dim[3], DIM })
R.inputs.here(st, { -1, 1 })
f = frame(st)
equal("⛔ the step playing is green, and its note lights, in the voice's color",
      { f[81], f[21] }, { GREEN, full[3] })
R.inputs.held(st, { 0, 4, 0 })
f = frame(st)
equal("... a step held shows its note instead, over what is playing", { f[18], f[21] }, { full[3], DIM })
R.inputs.held(st, { 0, 0, 62 })
f = frame(st)
equal("⛔ ... and a note held shows itself over either", { f[21], f[18] }, { full[3], dim[3] })
R.inputs.here(st, { -1, -1 })
R.inputs.held(st, { 0, 2, 0 })
equal("a step held is white", frame(st)[82], LEVEL[1])
st = melody(3, { on_m = 1 })
equal("the commands: on, roll, clear pins", { frame(st)[101], frame(st)[102], frame(st)[103] },
      { full[3], dim[3], dim[3] })

print("\n--- the performance page ---")
local function perform(cols, btns)
  st = R.new(LAYOUT)
  local a = {}
  for k = 1, 24 do a[k] = (cols or {})[k] or 0 end
  R.inputs.cols(st, a)
  a = {}
  for k = 1, 32 do a[k] = (btns or {})[k] or 0 end
  R.inputs.btns(st, a)
  return st
end
st = perform({ 1, 3, 0 })
f = frame(st)
equal("⛔ a fader's column, its level from the bottom, green up", { f[11], f[21], f[31], f[41] },
      { fader[1], fader[2], fader[3], DARK })
st = perform({ 1, 8, 1 })
f = frame(st)
equal("⛔ ... and dimmer while held at a value its control hasn't reached", { f[11], f[81] },
      { fader_dim[1], fader_dim[8] })
st = perform({ 0, 0, 0, 2, 2, 0, 0, 0, 0, 2, 1, 1 })
f = frame(st)
equal("⛔ a knob's blue, in its own column, dim while held",
      { f[12], f[22], f[32], f[14], f[24] }, { BLUE, BLUE, DARK, rgb(R.KNOB_DIM), DARK })
st = perform(nil, { 3, 0, 0, 0, 2, 1 })
f = frame(st)
equal("⛔ the buttons, top row CC 101 on: in their voices' colors, dim off and bright on, and dark with none",
      { f[101], f[102], f[103] }, { dim[3], DARK, full[2] })
local b = {}
for k = 1, 32 do b[k] = 0 end
b[17], b[18] = 4, 1
b[31], b[32] = 5, 0
st = perform(nil, b)
f = frame(st)
equal("⛔ ... the bottom row from CC 1, and save's and revert's cells are its", { f[1], f[8] },
      { full[4], dim[5] })

print("\n--- the other pages ---")
st = R.new(LAYOUT)
R.inputs.page(st, { "diag" })
f = frame(st)
equal("the diagnostics page: its two pads top left, diag and test mode",
      { f[81], f[82], #painted(st) }, { { 0, 127, 32 }, BLUE, 2 })
for _, name in ipairs({ "songs", "keys" }) do
  st = R.new(LAYOUT)
  R.inputs.page(st, { name })
  equal("⛔ " .. name .. " has no cells of its own", painted(st), {})
end
st = page({ "bar", 4, 8 })
R.inputs.page(st, { "perform" })
equal("⛔ a page left leaves nothing behind", painted(st), {})

print("\n--- the melody page's pitches are c_melody's ---")
-- A press and its lamp cannot disagree: each file works the list out from the same mode.
local C = dofile(DIR .. "c_melody.lua")
local agree, tried = true, 0
for _, sc in ipairs({ { 0, 2, 4, 5, 7, 9, 11 }, { 0, 2, 3, 5, 7, 8, 10 }, { 0, 1, 3, 5, 7, 8, 10 },
                      { 0, 2, 3, 5, 7, 8, 11 } }) do
  for tonic = 0, 11 do
    local scale = {}
    for d = 1, 7 do scale[d] = (sc[d] + tonic) % 12 end
    local m = C.new()
    m.tonic, m.scale = tonic, scale
    local a, z = R.pitches(tonic, scale), C.pitches(m)
    tried = tried + 1
    if not T.same(a, z) then agree = false end
  end
end
check("⛔ g_grid.lua's R.pitches and c_melody.lua's agree on every tonic of " .. tried .. " modes and keys", agree)

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
check("... and read the layout from its patch's folder, in silence", o and #o.state.index == 62
      and #o.console == 0, o and T.show(o.console))
equal("init: the bang on outlet 2 that says it loaded, and nothing else",
      T.send(o, 2, "init", {}), { { 2, "bang", {} } })
T.send(o, 1, "page", { "drums" })
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
  { 135, 1, 21, 129, 7, 153, 152, 144, 129, 136, 147, 146 })
check("⛔ ... and nothing outside its 62 cells, and a dark one not at all: the fill is g_grid.pd's",
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
  T.send(late, 1, "page", { "drums" })
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
