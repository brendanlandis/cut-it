-- m_organelle-lua -- m_organelle.lua's Pd face, made inside m_organelle.pd as [m_organelle-lua].
-- It turns messages into calls on the rules and the rules' answers into outlets, and nothing
-- else: what the keyboard publishes is in m_organelle.lua. ref/device/organelle.md.
--
-- inlet 1: mother's notes, <pitch> <velocity>. inlet 2: m_organelle.pd's own, init at load.
-- outlet 1: a key's control, to param. outlet 2: err. outlet 3: a bang on init, the proof the
-- Lua loaded.
--
-- A Lua error leaves outlet 2 as fail m_organelle lua-<rule> -- lua-notes, lua-init
-- -- and its text goes to Pd's console where there is one: the device has none (C-12).

local OrgLua = pd.Class:new():register("m_organelle-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload m_organelle-lua`) reloads them too.
local R = dofile(OrgLua._loadpath .. "m_organelle.lua")

local OUTLET = { param = 1, err = 2 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(OrgLua._loadpath .. "lua-face.lua")
F.carry(OrgLua, R, OUTLET, 2, 3)

function OrgLua:initialize()
  self.inlets, self.outlets = 2, 3
  self.state = R.new()
  return true
end

function OrgLua:in_1(sel, atoms)
  if sel ~= "list" then return self:answer(sel, nil) end
  self:answer("notes", R.key, self.state, atoms[1], atoms[2])
end

function OrgLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
