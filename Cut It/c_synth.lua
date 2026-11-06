-- c_synth.lua -- the synth choice and the router: which synth the nanoKEY plays, which synth
-- each key it holds is sounding on, whether a key's velocity reaches it, and each synth's sound,
-- a program number, sent as a section starts. Plain Lua with no Pd in it, so
-- test/gate/lua/c_synth_test.lua runs it on the Mac with lua.org's interpreter.
-- c_synth-lua.pd_lua is its Pd face, and c_synth.pd keeps the cords and the state bus.
-- ref/module/synths.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the choice and the keys held. Every rule returns what leaves, in order, as
-- {outlet, selector, atoms}:
--   {"fm" | "strings", "note", {note, velocity}}   to that synth's device layer, 0 a release
--   {"fm" | "strings", "program", {n}}             to that synth's device layer: its sound
--   {"choice", "synth", {choice}}                  to u_net (the phone)
--   {"phone", "velocity", {"on" | "off"}}          to u_net (the phone) alone
--   {"save", "synth" | "velocity" | "programs", {value...}}
--                                                  to the state bus, put section <key>
--   {"err", "fail", {"c_synth", text}}             to err (C-12)

local R = {}

-- The synths, in the order their outlets sit: fm is the Volca FM, strings the Waldorf
-- Streichfett. fm until something says otherwise (Brendan, 2026-11-04).
R.SYNTHS = { "fm", "strings" }
R.BOOT = "fm"

-- The velocity switch, for both synths (Brendan, 2026-11-04): on, a key's velocity passes; off,
-- every note-on goes out at R.FULL and a release stays 0. On until something says otherwise.
R.VELOCITY = { on = true, off = true }
R.BOOT_VELOCITY = "on"
R.FULL = 127

-- Each synth's sound, a section's (Brendan, 2026-11-04): a program number, 0 to 127, the program
-- change on the wire, which each synth's layer takes as `program <n>`; or none, which sends
-- nothing. Nothing chooses one yet, so a section holds none until its file says otherwise.
R.NONE = "none"

local KNOWN = {}
for _, s in ipairs(R.SYNTHS) do KNOWN[s] = true end

-- A number from a message, as Pd's [f] reads one: a symbol or nothing is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- A MIDI data byte: whole, 0 to 127.
local function byte(x)
  x = math.floor(num(x) + 0.5)
  if x < 0 then return 0 end
  if x > 127 then return 127 end
  return x
end

-- held[note] is the synth that note's note-on went to, while the key is down.
function R.new()
  return { choice = R.BOOT, held = {}, velocity = R.BOOT_VELOCITY,
           programs = { fm = R.NONE, strings = R.NONE } }
end

-- The choice, out to the phone, and to the song store.
local function tell(st)
  return { { "choice", "synth", { st.choice } }, { "save", "synth", { st.choice } } }
end

-- The velocity switch, out to the phone, and to u_state.
local function tell_velocity(st)
  return { { "phone", "velocity", { st.velocity } }, { "save", "velocity", { st.velocity } } }
end

-- A key: <note> <velocity>, 0 a release. A press goes to the synth chosen now and is remembered
-- there; its release goes to the synth that got the press, whatever the choice is by then, so a
-- switch mid-chord leaves nothing hanging. A press of a key already down on another synth
-- releases it there first. A release with no press on record, a key held through a reload of
-- the patch, goes to the synth chosen now: a note-off nothing holds is harmless.
function R.key(st, note, velocity)
  local n, v = byte(note), byte(velocity)
  local was = st.held[n]
  if v == 0 then
    st.held[n] = nil
    return { { was or st.choice, "note", { n, 0 } } }
  end
  local out = {}
  if was and was ~= st.choice then out[#out + 1] = { was, "note", { n, 0 } } end
  st.held[n] = st.choice
  if st.velocity == "off" then v = R.FULL end
  out[#out + 1] = { st.choice, "note", { n, v } }
  return out
end

-- velocity <on or off>, from the phone's synths screen. The same setting again changes nothing
-- and says nothing; anything else is fail c_synth bad-velocity.
function R.set_velocity(st, atoms)
  local v = atoms[1]
  if not R.VELOCITY[v] then return { R.fail("bad-velocity") } end
  if v == st.velocity then return {} end
  st.velocity = v
  return tell_velocity(st)
end

-- synth <choice> [<value>], from the phone. A value of 0 is a release and does nothing, and the
-- phone sends none. The same choice again changes nothing and says nothing.
function R.choose(st, atoms)
  local choice = atoms[1]
  if atoms[2] ~= nil and num(atoms[2]) == 0 then return {} end
  if not KNOWN[choice] then return { R.fail("bad-synth") } end
  if choice == st.choice then return {} end
  st.choice = choice
  return tell(st)
end

-- machine <choice>, from u_voices: the voice on show's machine, which the nanoKEY plays. The phone
-- hears, and it isn't put: looking at a voice's page changes nothing in the song.
function R.machine(st, atoms)
  local choice = atoms[1]
  if not KNOWN[choice] then return { R.fail("bad-synth") } end
  st.by_voice = true
  if choice == st.choice then return {} end
  st.choice = choice
  return { { "choice", "synth", { choice } } }
end

-- A section's restore of synth: the choice saved, put straight back (ref/module/state.md). One
-- that names no synth keeps the one in force and puts that back, so the file is repaired.
function R.restore(st, atoms)
  if KNOWN[atoms[1]] and not st.by_voice then st.choice = atoms[1] end
  return tell(st)
end

-- A section's restore of velocity, put straight back as the choice is; one that is neither on nor
-- off keeps the one in force and puts that back.
function R.restore_velocity(st, atoms)
  if R.VELOCITY[atoms[1]] then st.velocity = atoms[1] end
  return tell_velocity(st)
end

-- The programs as a section holds them: the Volca's, then the Streichfett's, in R.SYNTHS' order.
local function tell_programs(st)
  local p = {}
  for i, s in ipairs(R.SYNTHS) do p[i] = st.programs[s] end
  return { "save", "programs", p }
end

-- A program as the store keeps it: a whole number 0 to 127, or none for anything else.
local function program(x)
  if type(x) ~= "number" or x < 0 or x > 127 then return R.NONE end
  return math.floor(x + 0.5)
end

-- A section's restore of programs, <volca> <streichfett>, as it starts (Brendan, 2026-11-04):
-- each synth with a program is sent it, the Volca first, and the two are put straight back. None
-- sends nothing, and leaves the synth on whatever sound it has.
function R.restore_programs(st, atoms)
  local out = {}
  for i, s in ipairs(R.SYNTHS) do
    local n = program(atoms[i])
    st.programs[s] = n
    if n ~= R.NONE then out[#out + 1] = { s, "program", { n } } end
  end
  out[#out + 1] = tell_programs(st)
  return out
end

-- At load: the choice, the velocity switch and the programs, so the phone shows them before anything is pressed and the section playing holds them from the start.
function R.boot(st)
  local out = tell(st)
  for _, e in ipairs(tell_velocity(st)) do out[#out + 1] = e end
  out[#out + 1] = tell_programs(st)
  return out
end

-- What reaches the inlet: a key from m_nanokey, machine <choice> from u_voices, synth <choice> or
-- velocity <on or off> from u_net.
R.inputs = {
  list = function(st, a) return R.key(st, a[1], a[2]) end,
  float = function(st, a) return R.key(st, a[1], 0) end,
  synth = function(st, a) return R.choose(st, a) end,
  machine = function(st, a) return R.machine(st, a) end,
  velocity = function(st, a) return R.set_velocity(st, a) end,
}

-- What c_synth.pd itself sends: a section's restores of synth, velocity and programs, from the
-- song store (u_state's of synth and velocity too, the auto keys they were before sections,
-- once), and the load.
R.internal = {
  restore = function(st, a) return R.restore(st, a) end,
  ["restore-velocity"] = function(st, a) return R.restore_velocity(st, a) end,
  ["restore-programs"] = function(st, a) return R.restore_programs(st, a) end,
  init = function(st) return R.boot(st) end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_synth", string.sub(text, 1, 21) } }
end

return R
