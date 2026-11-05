-- c_steps-lua -- c_steps.lua's Pd face, made inside c_steps.pd as [c_steps-lua $1]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else: what
-- the sequencer does is in c_steps.lua. ref/module/sequencer.md.
--
-- creation arg: its bank, 1 for A: vestigial since the SP-404 left the rig, as c_kit plays pads
-- 1 to 16 (c_steps.pd).
-- inlet 1: the presses and releases, from u_map -- step <n> <vel>, vel <level> <vel>, pad <n>
-- <vel>, rep <n> <vel>, and knobs 2 to 4, last, track-last and swing <0-1> -- and the phone's
-- sync, snap, select, num, den, drunk, skip, move, set-swing and set-last, from u_net.
-- inlet 2: c_steps.pd's own -- tick, start, stop, restore <the saved line>, init.
-- outlet 1: pad <pad> <velocity>, to c_kit. outlet 2: the page, to g_grid. outlet 3: the pattern
-- to save. outlet 4: err. outlet 5: a bang on init, the proof the Lua loaded. outlet 6: a knob's
-- row, to disp. outlet 7: the phone's state, R.phone's 42 numbers, whenever it changes.
-- outlet 8: the step clock's swing <0.5-0.75> and rate <x>, to c_steps.pd's clock.
--
-- A Lua error leaves outlet 4 as fail c_steps lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local StepsLua = pd.Class:new():register("c_steps-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload c_steps-lua`) reloads them too, and every object keeps its pattern.
local R = dofile(StepsLua._loadpath .. "c_steps.lua")

local OUTLET = { note = 1, page = 2, save = 3, err = 4, disp = 6, clock = 8 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(StepsLua._loadpath .. "lua-face.lua")
F.carry(StepsLua, R, OUTLET, 2, 5)

function StepsLua:initialize(_, atoms)
  self.inlets, self.outlets = 2, 8
  self.state = R.new(atoms[1])
  return true
end

-- After every answer, the phone's state, out the seventh outlet only when it differs from
-- the last one sent: a tick changes nothing the phone shows, eight times a second.
function StepsLua:answered()
  local ok, now = pcall(R.phone, self.state)
  if not ok then return end
  local key = table.concat(now, " ")
  if key ~= self.phone_sent then
    self.phone_sent = key
    self:outlet(7, "list", now)
  end
end

function StepsLua:in_1(sel, atoms)
  self:answer(sel, R.presses[sel], self.state, atoms)
end

function StepsLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
