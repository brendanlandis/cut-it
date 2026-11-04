-- c_steps-lua -- c_steps.lua's Pd face, made inside c_steps.pd as [c_steps-lua $1]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else: what
-- the sequencer does is in c_steps.lua. ref/module/sequencer.md.
--
-- creation arg: the 404 bank its tracks play, 1 for A.
-- inlet 1: the presses and releases, from u_map -- step <n> <vel>, vel <level> <vel>, pad <n>
-- <vel>, rep <n> <vel>, and knobs 2 to 4, last, track-last and swing <0-1> -- and the drum
-- screen's sync, snap, select, num, den, drunk, skip and move, from u_net.
-- inlet 2: c_steps.pd's own -- tick, start, stop, restore <the saved line>, init.
-- outlet 1: pad <pad> <velocity>, to m_404. outlet 2: the page, to g_grid. outlet 3: the pattern
-- to save. outlet 4: err. outlet 5: a bang on init, the proof the Lua loaded. outlet 6: a knob's
-- row, to disp. outlet 7: the drum screen's state, R.phone's 41 numbers, whenever it changes.
-- outlet 8: the step clock's swing <0.25-0.75> and rate <x>, to c_steps.pd's clock.
--
-- A Lua error leaves outlet 4 as fail c_steps lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local StepsLua = pd.Class:new():register("c_steps-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload c_steps-lua`) reloads them too, and every object keeps its pattern.
local R = dofile(StepsLua._loadpath .. "c_steps.lua")

local OUTLET = { note = 1, page = 2, save = 3, err = 4, disp = 6, clock = 8 }

function StepsLua:initialize(_, atoms)
  self.inlets, self.outlets = 2, 8
  self.state = R.new(atoms[1])
  return true
end

-- One message, answered by the rule of its name in `rules`, or reported.
function StepsLua:answer(rules, sel, atoms)
  local rule, ok, out = rules[sel], true, { R.fail("bad-selector") }
  if rule then ok, out = pcall(rule, self.state, atoms) end
  if not ok then
    self:error("c_steps-lua: " .. tostring(out))
    out = { R.fail("lua-" .. sel) }
  end
  for _, e in ipairs(out) do self:outlet(OUTLET[e[1]], e[2], e[3]) end
  self:phone()
end

-- The drum screen's state, out the last outlet only when it differs from the last one sent: a
-- tick changes nothing the phone shows, eight times a second.
function StepsLua:phone()
  local ok, now = pcall(R.phone, self.state)
  if not ok then return end
  local key = table.concat(now, " ")
  if key ~= self.phone_sent then
    self.phone_sent = key
    self:outlet(7, "list", now)
  end
end

function StepsLua:in_1(sel, atoms)
  self:answer(R.presses, sel, atoms)
end

function StepsLua:in_2(sel, atoms)
  self:answer(R.internal, sel, atoms)
  if sel == "init" then self:outlet(5, "bang", {}) end
end
