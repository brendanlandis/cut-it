-- The rules of a voice's sound, run with no Pd.
package.path = "test/gate/lua/?.lua;" .. package.path
local T = require("lib_test")
local equal = T.equal
local DIR = "Cut It/"
local R = dofile(DIR .. "u_sound.lua")

local function read(n)
  local f = assert(io.open(DIR .. n))
  local t = f:read("a")
  f:close()
  return t
end

local st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
local function rows(at, list)
  local a = { at }
  for r = 1, 8 do
    local x = list[r] or { "-", 0, "-" }
    a[#a + 1], a[#a + 2], a[#a + 3] = x[1], x[2], x[3]
  end
  return a
end

print("\n--- a hardware synth taken up keeps its own sound ---")
local out = R.rows(st, rows(2, { [2] = { "strings", 1, "h" } }))
equal("⛔ nothing is said to it, no program and no default", out, {})
equal("... the phone shows the defaults all the same", R.phone(st)[1], "-")

print("\n--- a parameter moved ---")
equal("<row>:<param> <value> says its CC", R.param(st, "2:reverb", 1), { { "strings", "cc", { 94, 127 } } })
equal("... a parameter it doesn't have warns", R.param(st, "2:nope", 1)[1][2], "warn")
equal("... a row with no voice does nothing", R.param(st, "5:reverb", 1), {})

print("\n--- save, patches and the factory ---")
out = R.save(st, false)
equal("save with no patch yet makes one, for the machine", st.rows[2].patch, "strings-patch")
R.param(st, "2:reverb", 0)
out = R.recall(st, "strings-patch")
equal("recalled, it has what was saved", st.rows[2].values.reverb, 1)
equal("⛔ ... and says only what was set", #out, 2)
out = R.copy_factory(st, "wide")
equal("a factory patch copied in, and in use", st.rows[2].patch, "wide")
equal("... its own copy in the song", st.patches.wide.values.ensemble, 0.8)
R.copy_factory(st, "wide")
equal("copied again it's a second song patch", st.rows[2].patch, "wide-2")
R.save(st, true)
equal("save as new takes a new name", st.rows[2].patch, "wide-2-2")

print("\n--- a section: snap back or carry on ---")
R.recall(st, "wide")
R.param(st, "2:reverb", 0.9)
equal("carry on leaves a tweak", { R.tweaks(st, 1), st.rows[2].values.reverb }, { {}, 0.9 })
out = R.tweaks(st, 0)
equal("snap back takes it back to the patch, said out", { st.rows[2].values.reverb, out[1] },
      { 0.5, { "strings", "cc", { 94, 64 } } })

print("\n--- a Pd voice ---")
st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
R.rows(st, rows(3, { [3] = { "saw", 2, "m" } }))
equal("its parameter goes to its engine and line", R.param(st, "3:bright", 0.5),
      { { "engine", "tone", { 2, "m", "bright", 0.5 } } })

print("\n--- a song's files ---")
R.copy_factory(st, "pad")
local s2 = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
R.rows(s2, rows(3, { [3] = { "saw", 2, "m" } }))
R.restore_patches(s2, R.save_patches and {} or {})
local line = R.save_line(st)
out = R.restore_sounds(s2, line)
equal("a song's sounds restored: the same values, the same patch", { s2.rows[3].patch, s2.rows[3].values.bright },
      { "pad", 0.15 })
equal("... said out to the machine", out[1][1], "engine")

print("\n--- the phone ---")
local ph = R.phone(st)
equal("the patch, the song's patches for this machine, the factory's, the parameters",
      { ph[1], ph[2], ph[3], ph[4] }, { "pad", 1, "pad", 3 })

print("\n--- a Pd voice's default is said ---")
st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
out = R.rows(st, rows(3, { [3] = { "saw", 2, "m" } }))
equal("⛔ taken up, its parameters go to its engine, so another patch's don't linger", #out, 11)

print("\n--- a keys voice on a Pd machine ---")
st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
R.rows(st, rows(4, { [4] = { "saw", 0, "-" } }))
equal("⛔ its parameter goes to c_keys", R.param(st, "4:reverb", 0.5), { { "keys", "tone", { "reverb", 0.5 } } })

print("\n--- the FM-1's effects: a top, and a switch ---")
st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
R.rows(st, rows(3, { [3] = { "fm", 1, "h" } }))
equal("⛔ an effect's amount is scaled to its own top, 100, with its switch on before it",
      R.param(st, "3:reverb", 1), { { "fm", "cc", { 4, 1 } }, { "fm", "cc", { 7, 100 } } })
equal("⛔ ... and at nothing its switch goes off", R.param(st, "3:reverb", 0),
      { { "fm", "cc", { 4, 0 } }, { "fm", "cc", { 7, 0 } } })
equal("a top with no switch is the one CC, 0 to that top", R.param(st, "3:cutoff", 1),
      { { "fm", "cc", { 2, 107 } } })
equal("⛔ a program moved says what's been set again behind it: the voice it brings has its own",
      R.param(st, "3:program", 0.5),
      { { "fm", "program", { 64 } }, { "fm", "cc", { 2, 107 } },
        { "fm", "cc", { 4, 0 } }, { "fm", "cc", { 7, 0 } } })

print("\n--- the fm synth's test voices ---")
for n, v in ipairs(R.TEST_VOICES) do
  local sum = 0
  for i = 7, 161 do sum = sum + v[i] end
  equal("voice " .. n .. ": a format 0 dump, 155 bytes of data, its checksum right, ends F7",
        { #v, v[1], v[2], v[4], v[5], v[6], (sum + v[162]) % 128, v[163] },
        { 163, 0xF0, 0x43, 0, 1, 0x1B, 0, 0xF7 })
  local ok = true
  for i = 2, 162 do ok = ok and v[i] >= 0 and v[i] <= 127 end
  equal("... every data byte below 128", ok, true)
end
out = R.mapped(st, "vox1", 1)
equal("⛔ a test voice goes a byte at a time, into the program kept for DX7 voices: C0 7F ahead of it",
      { #out, out[1], out[2], out[3], out[165] },
      { 165, { "fm", "byte", { 0xC0 } }, { "fm", "byte", { 127 } }, { "fm", "byte", { 0xF0 } },
        { "fm", "byte", { 0xF7 } } })
equal("... on a press, not its release", R.mapped(st, "vox1", 0), {})

print("\n--- the DX7 voice library ---")
equal("the bank list is its files in order, comments left out",
      R.parse_library("# the banks\nrom1a.syx\n\n  vrc101a.syx  \n"), { "rom1a.syx", "vrc101a.syx" })

-- A voice with something in every field a bank packs, and a bank of it, packed here from the format
-- and apart from the rules' own unpacking.
local fancy = {}
for i = 7, 161 do fancy[#fancy + 1] = R.TEST_VOICES[1][i] end
for op = 0, 5 do
  local o = op * 21
  fancy[o + 12], fancy[o + 13], fancy[o + 14], fancy[o + 15] = (op + 1) % 4, (op + 2) % 4, op + 1, op % 4
  fancy[o + 16], fancy[o + 18], fancy[o + 19], fancy[o + 21] = op + 2, op % 2, 17 + op, 9 + op
end
fancy[135], fancy[136], fancy[137], fancy[142], fancy[143], fancy[144] = 21, 5, 0, 1, 4, 6
local function packed(d)
  local q = {}
  for op = 0, 5 do
    local o = op * 21
    for i = 1, 11 do q[#q + 1] = d[o + i] end
    q[#q + 1] = d[o + 12] | (d[o + 13] << 2)
    q[#q + 1] = d[o + 14] | (d[o + 21] << 3)
    q[#q + 1] = d[o + 15] | (d[o + 16] << 2)
    q[#q + 1] = d[o + 17]
    q[#q + 1] = d[o + 18] | (d[o + 19] << 1)
    q[#q + 1] = d[o + 20]
  end
  for i = 127, 135 do q[#q + 1] = d[i] end
  q[#q + 1] = d[136] | (d[137] << 3)
  for i = 138, 141 do q[#q + 1] = d[i] end
  q[#q + 1] = d[142] | (d[143] << 1) | (d[144] << 4)
  for i = 145, 155 do q[#q + 1] = d[i] end
  return string.char(table.unpack(q))
end
local bass = {}
for i = 7, 161 do bass[#bass + 1] = R.TEST_VOICES[2][i] end
local voices = packed(fancy) .. string.rep(packed(bass), 31)
local file = "\xF0\x43\x00\x09\x20\x00" .. voices .. "\x00\xF7"

st = R.new(read("cut-it-machines.txt"), read("cut-it-factory.txt"))
equal("a packed voice is 128 bytes, and a bank file 4104", { #packed(fancy), #file }, { 128, 4104 })
equal("⛔ a file that isn't a 32-voice bank is turned away", { R.bank(st, 2, file:sub(1, 4000)),
      R.bank(st, 2, "\xF0\x43\x00\x00" .. file:sub(5)), st.library[2] }, { false, false })
equal("a bank is taken at its place in the list", R.bank(st, 2, file), true)
equal("⛔ a voice comes out of its bank as the 155 bytes it went in as, each field in its own byte",
      R.unpacked(st.library[2], 0), fancy)
equal("... and the last of the 32 as well", R.unpacked(st.library[2], 31), bass)

R.rows(st, rows(3, { [3] = { "fm", 1, "h" } }))
R.param(st, "3:reverb", 1)
local function kinds(o)
  local t = {}
  for _, e in ipairs(o) do
    local k = e[2] == "byte" and "byte" or (e[2] .. " " .. table.concat(e[3], " "))
    if t[#t] ~= k or k ~= "byte" then t[#t + 1] = k end
  end
  return t
end
local function bytes(o)
  local t = {}
  for _, e in ipairs(o) do
    if e[2] == "byte" then t[#t + 1] = e[3][1] end
  end
  return t
end
equal("a bank that isn't there warns and sends nothing", kinds(R.param(st, "3:dx7-voice", 0)),
      { "warn u_sound no-dx7-bank-1" })
out = R.param(st, "3:dx7-bank", 1.5 / 32)
local b = bytes(out)
local sum = 0
for i = 9, 163 do sum = sum + b[i] end
equal("⛔ a DX7 voice goes whole: its program change as bytes, C0 and the program kept for it, then a "
      .. "format 0 dump with its checksum right",
      { #b, b[1], b[2], b[3], b[4], b[6], b[7], b[8], (sum + b[164]) % 128, b[165] },
      { 165, 0xC0, 127, 0xF0, 0x43, 0, 1, 0x1B, 0, 0xF7 })
equal("... carrying that voice", { table.unpack(b, 9, 163) }, fancy)
equal("⛔ ... with no program change of Pd's own, which would arrive behind the voice, and what's been "
      .. "set said again behind it", kinds(out), { "byte", "cc 4 1", "cc 7 100" })
equal("⛔ the same voice again sends nothing: each one is written into the FM-1",
      R.param(st, "3:dx7-voice", 0.01), {})
equal("another voice of the bank goes", #bytes(R.param(st, "3:dx7-voice", 1)), 165)
equal("... kept as the middle of its step", st.rows[3].values["dx7-voice"], 31.5 / 32)

print("\n--- a program or a DX7 voice, whichever was chosen last ---")
out = R.param(st, "3:program", 0.10151)
equal("⛔ a program chosen lets go of the DX7 voice", { st.rows[3].values["dx7-bank"],
      st.rows[3].values["dx7-voice"], kinds(out)[1] }, { nil, nil, "program 12" })
local line = R.save_line(st)
local kept
for i, w in ipairs(line) do
  if w == "program" then kept = line[i + 1] end
end
equal("⛔ ... and is kept as the middle of its step, so a song's three decimals bring the same one back",
      { kept, math.floor(kept * 128) }, { 0.098, 12 })
R.save(st, false)
out = R.param(st, "3:dx7-bank", 1.5 / 32)
equal("⛔ a DX7 voice chosen lets go of the program, and goes again though it was the last one sent",
      { st.rows[3].values.program, #bytes(out) }, { nil, 165 })
equal("a recall says the voice first, then what's set", kinds(R.recall(st, "fm-patch")),
      { "program 12", "cc 4 1", "cc 7 100", "sounds 3 fm-patch fm 2 program 0.098 reverb 1.0" })
R.param(st, "3:dx7-bank", 1.5 / 32)
out = R.tweaks(st, 0)
equal("⛔ a section snapping back takes the voice back to what was saved, and lets go of the other",
      { kinds(out), st.rows[3].values["dx7-bank"] }, { { "program 12", "cc 4 1", "cc 7 100" } })
R.param(st, "3:dx7-bank", 1.5 / 32)
R.save(st, false)
R.param(st, "3:program", 0.5)
equal("... a DX7 voice the same, sent whole", kinds(R.tweaks(st, 0)), { "byte", "cc 4 1", "cc 7 100" })

os.exit(T.report() == 0)
