-- u_sound-lua -- u_sound.lua's Pd face, made inside u_sound.pd as [u_sound-lua]. It reads the machines'
-- and the factory's tables, turns messages into calls on the rules and the rules' answers into outlets,
-- and nothing else. ref/module/voices.md.
--
-- inlet 1: u_map's <row>:<param> <value>. inlet 2: the phone's sound <cmd> ..., through u_net. inlet 3:
-- u_sound.pd's own -- restore <key> <atoms...>, rows, init. outlet 1: to m_volca. outlet 2: to m_streich.
-- outlet 3: tone, to the c_melody engines. outlet 4: sound <atoms>, to u_net. outlet 5: <key> <atoms>, to
-- put song on the state bus. outlet 6: err. outlet 7: a bang on init, the proof the Lua loaded. outlet 8: heard, to u_perform.
-- outlet 9: a bang when the kit's sound is saved, to c_steps. outlet 10: sound <11 atoms>, to g_grid. outlet 11: to c_keys.

local SoundLua = pd.Class:new():register("u_sound-lua")
local Clock = pd.Clock

local R = dofile(SoundLua._loadpath .. "u_sound.lua")

local OUTLET = { fm = 1, strings = 2, engine = 3, save = 5, err = 6, heard = 8, kit = 9, keys = 11 }

local F = dofile(SoundLua._loadpath .. "lua-face.lua")
F.carry(SoundLua, R, OUTLET, 3, 7)

local SAVE_EVERY, SHOW_EVERY = 300, 60

local function read(self, name)
  local fh = io.open(self._canvaspath .. name, "r")
  if not fh then
    self:error("u_sound-lua: no " .. name)
    return ""
  end
  local t = fh:read("a")
  fh:close()
  return t
end

function SoundLua:initialize()
  self.inlets, self.outlets = 3, 11
  self.state = R.new(read(self, "cut-it-machines.txt"), read(self, "cut-it-factory.txt"))
  return true
end

function SoundLua:postinitialize()
  self.save_clock = Clock:new():register(self, "save_due")
  self.show_clock = Clock:new():register(self, "show_due")
end

function SoundLua:finalize()
  if self.save_clock then self.save_clock:destruct() end
  if self.show_clock then self.show_clock:destruct() end
end

function SoundLua:save_due()
  self.save_waiting = false
  local ok, out = pcall(R.save_line, self.state)
  if ok then self:outlet(5, "sounds", out) end
end

function SoundLua:show_due()
  self.show_waiting = false
  local ok, p = pcall(R.phone, self.state)
  if not ok then return end
  local k = table.concat(p, " ")
  if k ~= self.phone_sent then
    self.phone_sent = k
    self:outlet(4, "sound", p)
  end
  local ok2, g = pcall(R.grid, self.state)
  if not ok2 then return end
  k = table.concat(g, " ")
  if k ~= self.grid_sent then
    self.grid_sent = k
    self:outlet(10, "sound", g)
  end
end

function SoundLua:answered()
  if not self.show_waiting then
    self.show_waiting = true
    self.show_clock:delay(SHOW_EVERY)
  end
  if self.state.dirty_sounds and not self.save_waiting then
    self.state.dirty_sounds = false
    self.save_waiting = true
    self.save_clock:delay(SAVE_EVERY)
  end
end

function SoundLua:in_1(sel, atoms)
  if sel == "list" then sel = atoms[1]; atoms = { atoms[2] } end
  self:answer("mapped", R.mapped, self.state, sel, atoms[1])
end

function SoundLua:in_2(sel, atoms)
  -- A command with no argument reaches here as a symbol.
  if sel == "symbol" then sel, atoms = atoms[1], {} end
  self:answer(tostring(sel), R.phone_cmds[sel], self.state, atoms)
end

function SoundLua:in_3(sel, atoms)
  self:internal(sel, atoms)
end
