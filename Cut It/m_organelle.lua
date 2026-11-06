-- m_organelle.lua -- the Organelle keyboard's rules: each key's control name. Plain Lua with no
-- Pd in it, so test/gate/lua/m_organelle_test.lua runs it on the Mac with lua.org's interpreter. m_organelle-lua.pd_lua is its Pd face, and
-- m_organelle.pd keeps mother's names, the knobs, aux and presence.
-- ref/device/organelle.md.
--
-- The state is a plain table and every rule a function of it. Every rule returns what leaves,
-- in order, as {outlet, selector, atoms}:
--   {"param", <name>, {velocity}}            a key, as og-key-60 100
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

function R.new()
  return {}
end

-- A key: <pitch> <velocity>, mother's notes list, a release at velocity 0.
function R.key(st, pitch, velocity)
  pitch, velocity = num(pitch), num(velocity)
  return { { "param", "og-key-" .. int(pitch), { velocity } } }
end

-- What m_organelle.pd itself sends: the load.
R.internal = {
  init = function()
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.fail(text)
  return { "err", "fail", { "m_organelle", string.sub(text, 1, 21) } }
end

return R
