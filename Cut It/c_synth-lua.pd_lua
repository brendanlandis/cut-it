-- c_synth-lua -- c_synth.lua's Pd face, made inside c_synth.pd as [c_synth-lua]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else: what
-- the router does is in c_synth.lua. ref/module/synths.md.
--
-- inlet 1: <note> <velocity> from m_nanokey, 0 a release, machine <choice> from u_voices, synth
-- <choice> and velocity <on or off> from u_net. inlet 2: c_synth.pd's own -- restore <the saved choice>,
-- restore-velocity <the saved setting>, restore-programs <volca> <streichfett>, init.
-- outlet 1: note <n> <v> and program <n>, to m_volca. outlet 2: the same, to m_streich. outlet
-- 3: synth <choice>, on a change, to u_net. outlet 4: synth <choice>, velocity
-- <setting> or programs <volca> <streichfett>, to put under that key. outlet 5: err. outlet 6: a bang on init, the proof the Lua loaded.
-- outlet 7: velocity <on or off>, on a change, to u_net.
--
-- A Lua error leaves outlet 5 as fail c_synth lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local SynthLua = pd.Class:new():register("c_synth-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload c_synth-lua`) reloads them too, and every object keeps its choice.
local R = dofile(SynthLua._loadpath .. "c_synth.lua")

local OUTLET = { fm = 1, strings = 2, choice = 3, save = 4, err = 5, phone = 7 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(SynthLua._loadpath .. "lua-face.lua")
F.carry(SynthLua, R, OUTLET, 2, 6)

function SynthLua:initialize()
  self.inlets, self.outlets = 2, 7
  self.state = R.new()
  return true
end

function SynthLua:in_1(sel, atoms)
  self:answer(sel, R.inputs[sel], self.state, atoms)
end

function SynthLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
