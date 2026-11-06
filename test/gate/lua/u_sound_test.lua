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
equal("⛔ taken up, its four parameters go to its engine, so another patch's don't linger", #out, 4)

os.exit(T.report() == 0)
