-- u_tempo-lua -- u_tempo.lua's Pd face, made inside u_tempo.pd as [u_tempo-lua]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else: what
-- tap tempo does is in u_tempo.lua. ref/module/tempo.md.
--
-- inlet 1: tap <ms since the last tap>, from u_tempo.pd's timer, tempo <bpm>, the phone's, from
-- u_net, restored <bpm> off the state bus, and fast <1 or 0> <bpm>, the 500 BPM repeat, from
-- c_steps with the BPM in force. inlet 2: u_tempo.pd's own -- init.
-- outlet 1: a BPM, to the tempo bus. outlet 2: err. outlet 3: a bang on init, the proof the Lua
-- loaded. outlet 4: 1 or 0, whether a BPM on the bus is put in the section.
--
-- A Lua error leaves outlet 2 as fail u_tempo lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local TempoLua = pd.Class:new():register("u_tempo-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload u_tempo-lua`) reloads them too, and every object keeps its count of taps.
local R = dofile(TempoLua._loadpath .. "u_tempo.lua")

local OUTLET = { tempo = 1, err = 2, put = 4 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(TempoLua._loadpath .. "lua-face.lua")
F.carry(TempoLua, R, OUTLET, 2, 3)

function TempoLua:initialize()
  self.inlets, self.outlets = 2, 4
  self.state = R.new()
  return true
end

function TempoLua:in_1(sel, atoms)
  self:answer(sel, R.inputs[sel], self.state, atoms)
end

function TempoLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
