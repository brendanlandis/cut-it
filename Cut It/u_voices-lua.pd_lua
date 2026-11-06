-- u_voices-lua -- u_voices.lua's Pd face, made inside u_voices.pd as [u_voices-lua]. It turns messages
-- into calls on the rules and the rules' answers into outlets, and nothing else. ref/module/voices.md.
--
-- inlet 1: u_map's <arg> <value>: a left or right button, aux, setup. inlet 2: the phone's voices
-- <cmd> ..., through u_net. inlet 3: u_voices.pd's own -- restore <key> <atoms...>, start, stop, init.
-- outlet 1: the page's name, to the mode bus. outlet 2: to g_grid, voices <atoms>. outlet 3: voices,
-- seed and page <atoms>, to the state bus as put song voices, put seed voices and put auto page. outlet 4: to the c_melody engines,
-- assign and active. outlet 5: machine <machine>, to c_synth. outlet 6: voices <atoms>, to u_net.
-- outlet 7: err. outlet 8: a bang on init, the proof the Lua loaded. outlet 9: rows, to u_perform.

local VoicesLua = pd.Class:new():register("u_voices-lua")

local R = dofile(VoicesLua._loadpath .. "u_voices.lua")

local OUTLET = { mode = 1, save = 3, seed = 3, page = 3, engine = 4, synth = 5, err = 7, perform = 9 }

local F = dofile(VoicesLua._loadpath .. "lua-face.lua")
F.carry(VoicesLua, R, OUTLET, 3, 8)

function VoicesLua:initialize()
  self.inlets, self.outlets = 3, 9
  self.state = R.new()
  return true
end

local function key(a)
  return table.concat(a, " ")
end

-- After every answer: what the grid and the phone show, each when it differs from the last sent.
function VoicesLua:answered()
  local ok, g = pcall(R.grid, self.state)
  if ok then
    local k = key(g)
    if k ~= self.grid_sent then
      self.grid_sent = k
      self:outlet(2, "voices", g)
    end
  end
  local ok2, p = pcall(R.phone, self.state)
  if ok2 then
    local k = key(p)
    if k ~= self.phone_sent then
      self.phone_sent = k
      self:outlet(6, "voices", p)
    end
  end
end

function VoicesLua:in_1(sel, atoms)
  if sel == "list" then sel = atoms[1]; atoms = { atoms[2] } end
  if type(atoms[1]) == "number" and atoms[1] == 0 then return end
  self:answer(tostring(sel), R.controls[sel], self.state)
end

function VoicesLua:in_2(sel, atoms)
  self:answer(tostring(sel), R.phone_cmds[sel], self.state, atoms)
end

function VoicesLua:in_3(sel, atoms)
  self:internal(sel, atoms)
end
