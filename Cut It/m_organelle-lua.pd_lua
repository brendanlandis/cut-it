-- m_organelle-lua -- m_organelle.lua's Pd face, made inside m_organelle.pd as [m_organelle-lua].
-- It turns messages into calls on the rules and the rules' answers into outlets, and nothing
-- else: what the keyboard publishes is in m_organelle.lua. ref/device/organelle.md.
--
-- inlet 1: mother's notes, <pitch> <velocity>. inlet 2: m_organelle.pd's own -- shift <0|1>
-- on each edge of aux, init at load.
-- outlet 1: a key's control, to param. outlet 2: err. outlet 3: a bang on init, the proof the
-- Lua loaded.
--
-- A Lua error leaves outlet 2 as fail m_organelle lua-<rule> -- lua-notes, lua-shift, lua-init
-- -- and its text goes to Pd's console where there is one: the device has none (C-12).

local OrgLua = pd.Class:new():register("m_organelle-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload m_organelle-lua`) reloads them too, and every object keeps its layers.
local R = dofile(OrgLua._loadpath .. "m_organelle.lua")

local OUTLET = { param = 1, err = 2 }

function OrgLua:initialize()
  self.inlets, self.outlets = 2, 3
  self.state = R.new()
  return true
end

-- One rule's answer, or fail m_organelle lua-<name> if it threw, or bad-selector if there is
-- none.
function OrgLua:answer(name, rule, ...)
  local ok, out = true, { R.fail("bad-selector") }
  if rule then ok, out = pcall(rule, self.state, ...) end
  if not ok then
    self:error("m_organelle-lua: " .. tostring(out))
    out = { R.fail("lua-" .. name) }
  end
  for _, e in ipairs(out) do self:outlet(OUTLET[e[1]], e[2], e[3]) end
end

function OrgLua:in_1(sel, atoms)
  if sel ~= "list" then return self:answer(sel, nil) end
  self:answer("notes", R.key, atoms[1], atoms[2])
end

function OrgLua:in_2(sel, atoms)
  self:answer(sel, R.internal[sel], atoms)
  if sel == "init" then self:outlet(3, "bang", {}) end
end

-- A key goes straight to its inlet's method: pdlua's own dispatch first builds and tries two
-- method names from the selector (ref/module/map.md). A pdlua that stopped calling dispatch
-- would lose only the shortcut.
local INLET = { "in_1", "in_2" }
function OrgLua:dispatch(inlet, sel, atoms)
  return self[INLET[inlet]](self, sel, atoms)
end
