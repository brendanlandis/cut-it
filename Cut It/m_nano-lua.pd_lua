-- m_nano-lua -- m_nano.lua's Pd face, made inside m_nano.pd as [m_nano-lua]. It turns messages
-- into calls on the rules and the rules' answers into outlets, and nothing else: how a CC
-- decodes is in m_nano.lua. ref/device/nanokontrol.md.
--
-- inlet 1: <controller> <value>, every CC on the nano's two channels. inlet 2: m_nano.pd's own
-- -- init at load.
-- outlet 1: a named control, to param. outlet 2: err. outlet 3: a bang on init, the proof the
-- Lua loaded.
--
-- A Lua error leaves outlet 2 as fail m_nano lua-<rule> -- lua-ctlin, lua-init -- and its text
-- goes to Pd's console where there is one: the device has none (C-12).

local NanoLua = pd.Class:new():register("m_nano-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload m_nano-lua`) reloads them too.
local R = dofile(NanoLua._loadpath .. "m_nano.lua")

local OUTLET = { param = 1, err = 2 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(NanoLua._loadpath .. "lua-face.lua")
F.carry(NanoLua, R, OUTLET, 2, 3)

function NanoLua:initialize()
  self.inlets, self.outlets = 2, 3
  return true
end

function NanoLua:in_1(sel, atoms)
  if sel ~= "list" then return self:answer(sel, nil) end
  self:answer("ctlin", R.cc, atoms[1], atoms[2])
end

function NanoLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
