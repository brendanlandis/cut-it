-- u_sound-lua -- u_sound.lua's Pd face, made inside u_sound.pd as [u_sound-lua]. It reads the instruments'
-- and the factory's tables and the DX7 library, turns messages into calls on the rules and the rules' answers into outlets,
-- and nothing else. ref/module/voices.md.
--
-- inlet 1: u_map's <row>:<param> <value>. inlet 2: the phone's sound <cmd> ..., through u_net. inlet 3:
-- u_sound.pd's own -- restore <key> <atoms...>, rows, init. outlet 1: to m_fm1. outlet 2: to m_streich.
-- outlet 3: tone, to the c_melody engines. outlet 4: sound <atoms>, to u_net. outlet 5: <key> <atoms>, to
-- put song on the state bus. outlet 6: err. outlet 7: a bang on init, the proof the Lua loaded. outlet 8: heard, to u_perform.
-- outlet 9: a bang when the kit's sound is saved, to c_steps. outlet 10: sound <11 atoms>, to g_grid. outlet 11: to c_keys.

local SoundLua = pd.Class:new():register("u_sound-lua")

local R = dofile(SoundLua._loadpath .. "u_sound.lua")

local OUTLET = { fm = 1, strings = 2, engine = 3, save = 5, err = 6, heard = 8, kit = 9, keys = 11 }

local F = dofile(SoundLua._loadpath .. "lua-face.lua")
F.carry(SoundLua, R, OUTLET, 3, 7)
F.clocks(SoundLua, { "save", "show" })

local SAVE_EVERY, SHOW_EVERY = 300, 60

function SoundLua:initialize()
  self.inlets, self.outlets = 3, 11
  self.state = R.new(F.read(self, "cut-it-instruments.txt"), F.read(self, "cut-it-factory.txt"))
  -- The DX7 library's banks, in cut-it-dx7.txt's order. One that isn't there is no error: the files are
  -- outside git, and its voices just aren't sent (ref/module/voices.md).
  for i, name in ipairs(R.parse_library(F.read(self, "cut-it-dx7.txt"))) do
    local bank = F.read(self, "dx7/" .. name, true)
    if bank and not R.bank(self.state, i, bank) then self:error("u_sound-lua: not a DX7 bank: " .. name) end
  end
  return true
end

function SoundLua:save_due()
  local ok, out = pcall(R.save_line, self.state)
  if ok then self:outlet(5, "sounds", out) end
end

-- What the phone and the grid show, each when it differs from the last sent.
function SoundLua:show_due()
  if not F.changed(self, "phone", 4, "sound", R.phone, self.state) then return end
  F.changed(self, "grid", 10, "sound", R.grid, self.state)
end

function SoundLua:answered()
  F.soon(self, "show", SHOW_EVERY)
  if self.state.dirty_sounds and F.soon(self, "save", SAVE_EVERY) then self.state.dirty_sounds = false end
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
