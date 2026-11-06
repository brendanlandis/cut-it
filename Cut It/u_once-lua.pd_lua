-- u_once-lua -- u_once.lua's Pd face, made inside u_once.pd as [u_once-lua]. ref/device/phone.md.
--
-- inlet 1: <seq> <words...>. inlet 2: init. outlet 1: <words...>, the press. outlet 2: <seq>, its answer.
-- outlet 3: err. outlet 4: a bang on init, the proof the Lua loaded.

local OnceLua = pd.Class:new():register("u_once-lua")

local R = dofile(OnceLua._loadpath .. "u_once.lua")

local OUTLET = { forward = 1, answer = 2, err = 3 }

local F = dofile(OnceLua._loadpath .. "lua-face.lua")
F.carry(OnceLua, R, OUTLET, 2, 4)

function OnceLua:initialize()
  self.inlets, self.outlets = 2, 4
  self.state = R.new()
  return true
end

function OnceLua:in_1(sel, atoms)
  if sel ~= "list" then
    atoms = { sel, table.unpack(atoms) }
  end
  self:answer("once", R.once, self.state, atoms)
end

function OnceLua:in_2(sel, atoms)
  self:internal(sel, atoms)
end
