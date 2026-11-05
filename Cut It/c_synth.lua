-- c_synth.lua -- the synth choice and the router: which synth the nanoKEY plays, and which synth
-- each key it holds is sounding on. Plain Lua with no Pd in it, so test/gate/lua/c_synth_test.lua
-- runs it on the Mac with lua.org's interpreter. c_synth-lua.pd_lua is its Pd face, and
-- c_synth.pd keeps the cords and the state bus. ref/module/synths.md.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the choice and the keys held. Every rule returns what leaves, in order, as
-- {outlet, selector, atoms}:
--   {"fm" | "strings", "note", {note, velocity}}   to that synth's device layer, 0 a release
--   {"choice", "synth", {choice}}                  to u_net (the phone) and g_grid (the pads)
--   {"save", "list", {choice}}                     to u_state, as the auto key synth
--   {"err", "fail", {"c_synth", text}}             to err (C-12)

local R = {}

-- The synths, in the order their outlets sit: fm is the Volca FM, strings the Waldorf
-- Streichfett. fm until something says otherwise (Brendan, 2026-11-04).
R.SYNTHS = { "fm", "strings" }
R.BOOT = "fm"

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
  return { choice = R.BOOT, held = {} }
end

-- The choice, out to the phone and the pads, and to u_state.
local function tell(st)
  return { { "choice", "synth", { st.choice } }, { "save", "list", { st.choice } } }
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
  out[#out + 1] = { st.choice, "note", { n, v } }
  return out
end

-- synth <choice> [<value>], from the map (a page-3 pad) and from the phone. A value of 0 is a
-- release and does nothing; the map passes only presses, and the phone sends none. The same
-- choice again changes nothing and says nothing.
function R.choose(st, atoms)
  local choice = atoms[1]
  if atoms[2] ~= nil and num(atoms[2]) == 0 then return {} end
  if not KNOWN[choice] then return { R.fail("bad-synth") } end
  if choice == st.choice then return {} end
  st.choice = choice
  return tell(st)
end

-- u_state's restore of synth: the choice saved, put straight back (ref/module/state.md). One
-- that names no synth keeps the one in force and puts that back, so the file is repaired.
function R.restore(st, atoms)
  if KNOWN[atoms[1]] then st.choice = atoms[1] end
  return tell(st)
end

-- At load: the choice, so the pads and the phone show it before anything is pressed.
function R.boot(st)
  return tell(st)
end

-- What reaches the inlet: a key from m_nanokey, or synth <choice> from u_map or u_net.
R.inputs = {
  list = function(st, a) return R.key(st, a[1], a[2]) end,
  float = function(st, a) return R.key(st, a[1], 0) end,
  synth = function(st, a) return R.choose(st, a) end,
}

-- What c_synth.pd itself sends: u_state's restore, and the load.
R.internal = {
  restore = function(st, a) return R.restore(st, a) end,
  init = function(st) return R.boot(st) end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "c_synth", string.sub(text, 1, 21) } }
end

return R
