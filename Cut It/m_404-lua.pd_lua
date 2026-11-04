-- m_404-lua -- m_404.lua's Pd face, made inside m_404.pd as [m_404-lua $1]. It turns messages
-- into calls on the rules and the rules' answers into outlets, and nothing else: how a note
-- names a pad and a pad becomes a note is in m_404.lua. ref/device/sp404.md.
--
-- creation arg: the Pd channel bank A lands on, m_404's own.
-- inlet 1: <note> <velocity> <bank>, every note on the 404's ten channels. inlet 2: <pad>
-- <velocity> <gap>, every pad to play, with the ms since the last. inlet 3: m_404.pd's own --
-- init at load.
-- outlet 1: a note-on, <note> <velocity> <channel>, to noteout. outlet 2: its note-off, to the
-- pipe. outlet 3: a pad's name and velocity, to param. outlet 4: err. outlet 5: a bang on init,
-- the proof the Lua loaded.
--
-- A Lua error leaves outlet 4 as fail m_404 lua-<rule> -- lua-notein, lua-pad, lua-init -- and
-- its text goes to Pd's console where there is one: the device has none (C-12).

local PadsLua = pd.Class:new():register("m_404-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload m_404-lua`) reloads them too, and every object keeps its budget.
local R = dofile(PadsLua._loadpath .. "m_404.lua")

local OUTLET = { note = 1, off = 2, param = 3, err = 4 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(PadsLua._loadpath .. "lua-face.lua")
F.carry(PadsLua, R, OUTLET, 3, 5)

function PadsLua:initialize(_, atoms)
  self.inlets, self.outlets = 3, 5
  self.state = R.new(atoms[1])
  return true
end

function PadsLua:in_1(sel, atoms)
  if sel ~= "list" then return self:answer(sel, nil) end
  self:answer("notein", R.rx, self.state, atoms[1], atoms[2], atoms[3])
end

function PadsLua:in_2(sel, atoms)
  if sel ~= "list" then return self:answer(sel, nil) end
  self:answer("pad", R.tx, self.state, atoms[1], atoms[2], atoms[3])
end

function PadsLua:in_3(sel, atoms)
  self:internal(sel, atoms)
end
