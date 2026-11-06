-- u_map-lua -- u_map.lua's Pd face, made inside u_map.pd as [u_map-lua]. It reads the table,
-- turns messages into calls on the rules and the rules' answers into outlets, and nothing else:
-- what the map does is in u_map.lua. ref/module/map.md.
--
-- inlet 1: param, every control. inlet 2: the mode bus.
-- inlet 3: u_map.pd's own -- init at load, window-shut at 1000 ms, live from the recover
-- breadcrumb. inlet 4: a BPM a tap or the phone set, from u_tempo, which holds knob 1 there.
-- outlet 1: <dest> <arg> <value> <target> <live>, to the destination route. outlet 2: err.
-- outlet 3: a bang on init, the proof the Lua loaded. outlet 4: heard, to u_perform.
-- An unmapped control leaves by no outlet at all (Brendan, 2026-11-04).
--
-- A Lua error leaves outlet 2 as fail u_map lua-<rule> -- lua-param, lua-mode, lua-init -- and
-- its text goes to Pd's console where there is one: the device has none (C-12).

local MapLua = pd.Class:new():register("u_map-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload u_map-lua`) reloads them too, and every object keeps its table and pickup.
local R = dofile(MapLua._loadpath .. "u_map.lua")

local OUTLET = { route = 1, err = 2, heard = 4 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(MapLua._loadpath .. "lua-face.lua")
F.carry(MapLua, R, OUTLET, 4, 3)

-- The table is read when the object is made, before any loadbang, from the folder of the patch
-- that holds it, as u_map.pd's `read -c cut-it-map.txt` was. A missing file is an error on the
-- console, which fails a deploy, and map-empty on err at init. Whether a Save has left a
-- knobs.txt there is asked then too, before mother's push: without one, knob 1 is held at 120
-- (u_map.lua's R.UNSAVED). Its absence is silent, as it is on a machine never Saved.
function MapLua:initialize()
  self.inlets, self.outlets = 4, 4
  local fh, why = io.open(self._canvaspath .. "cut-it-map.txt", "r")
  local text = ""
  if fh then
    text = fh:read("a")
    fh:close()
  else
    self:error("u_map-lua: " .. tostring(why))
  end
  local saved = io.open(self._canvaspath .. "knobs.txt", "r")
  if saved then saved:close() end
  self.state = R.new(text, not saved)
  return true
end

function MapLua:in_1(sel, atoms)
  self:answer("param", R.control, self.state, sel, atoms)
end

function MapLua:in_2(sel, atoms)
  self:answer("mode", R.mode, self.state, sel, atoms)
end

function MapLua:in_3(sel, atoms)
  self:internal(sel, atoms)
end

function MapLua:in_4(sel, atoms)
  self:answer("tempo", R.hold_tempo, self.state, sel, atoms)
end
