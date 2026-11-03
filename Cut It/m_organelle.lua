-- m_organelle.lua -- the Organelle keyboard's rules: each key's control name, on the layer aux
-- held when that key went down. Plain Lua with no Pd in it, so test/gate/lua/m_organelle_test.lua
-- runs it on the Mac with lua.org's interpreter. m_organelle-lua.pd_lua is its Pd face, and
-- m_organelle.pd keeps mother's names, the knobs, aux's modal and presence.
-- ref/device/organelle.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves,
-- in order, as {outlet, selector, atoms}:
--   {"param", <name>, {velocity}}            a key, as og-key-60 100 or og-shift-60 0
--   {"err", "fail", {"m_organelle", text}}   to err (C-12)

local R = {}

-- A number from a message, as Pd's [f] reads one: a symbol or nothing is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- A number as [makefilename %d] writes it: the integer part, toward zero.
local function int(x)
  return string.format("%d", x < 0 and math.ceil(x) or math.floor(x))
end

-- shift: aux, held or not. layer: per key, whether it went down under aux.
function R.new()
  return { shift = false, layer = {} }
end

-- A key: <pitch> <velocity>, mother's notes list, a release at velocity 0. The layer is latched
-- per key at press time, and the release reads it: let go of aux before the key and the release
-- still says og-shift-NN, or the shifted control never sees its note-off (a stuck Volca note in
-- mode 1). Per key, so a chord's keys keep their own layers.
function R.key(st, pitch, velocity)
  pitch, velocity = num(pitch), num(velocity)
  if velocity ~= 0 then st.layer[pitch] = st.shift end
  local prefix = st.layer[pitch] and "og-shift-" or "og-key-"
  return { { "param", prefix .. int(pitch), { velocity } } }
end

-- What m_organelle.pd itself sends: aux's two edges, and the load.
R.internal = {
  shift = function(st, atoms)
    st.shift = num(atoms[1]) ~= 0
    return {}
  end,
  init = function()
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "m_organelle", string.sub(text, 1, 21) } }
end

return R
