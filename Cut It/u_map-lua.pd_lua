-- u_map-lua -- u_map.lua's Pd face, made inside u_map.pd as [u_map-lua]. It reads the table,
-- turns messages into calls on the rules and the rules' answers into outlets, and nothing else:
-- what the map does is in u_map.lua. ref/module/map.md.
--
-- inlet 1: param, every control the mode keys pass on. inlet 2: the mode bus.
-- inlet 3: u_map.pd's own -- init at load, window-shut at 1000 ms, live from the knobs.txt
-- probe and the recover breadcrumb.
-- outlet 1: <dest> <arg> <value> <target> <live>, to the destination route. outlet 2: an
-- unmapped control's raw row, to disp. outlet 3: the mode, to the state store. outlet 4: err.
-- outlet 5: a bang on init, the proof the Lua loaded.
--
-- A Lua error leaves outlet 4 as fail u_map lua-<rule> -- lua-param, lua-mode, lua-init -- and
-- its text goes to Pd's console where there is one: the device has none (C-12).

local MapLua = pd.Class:new():register("u_map-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload u_map-lua`) reloads them too, and every object keeps its table and pickup.
local R = dofile(MapLua._loadpath .. "u_map.lua")

local OUTLET = { route = 1, disp = 2, store = 3, err = 4 }

-- The table is read when the object is made, before any loadbang, from the folder of the patch
-- that holds it, as u_map.pd's `read -c cut-it-map.txt` was. A missing file is an error on the
-- console, which fails a deploy, and map-empty on err at init.
function MapLua:initialize()
  self.inlets, self.outlets = 3, 5
  local fh, why = io.open(self._canvaspath .. "cut-it-map.txt", "r")
  local text = ""
  if fh then
    text = fh:read("a")
    fh:close()
  else
    self:error("u_map-lua: " .. tostring(why))
  end
  self.state = R.new(text)
  return true
end

-- One rule's answer, or fail u_map lua-<name> if it threw, or bad-selector if there is none.
function MapLua:answer(name, rule, ...)
  local ok, out = true, { R.fail("bad-selector") }
  if rule then ok, out = pcall(rule, self.state, ...) end
  if not ok then
    self:error("u_map-lua: " .. tostring(out))
    out = { R.fail("lua-" .. name) }
  end
  for _, e in ipairs(out) do self:outlet(OUTLET[e[1]], e[2], e[3]) end
end

function MapLua:in_1(sel, atoms)
  self:answer("param", R.control, sel, atoms)
end

function MapLua:in_2(sel, atoms)
  self:answer("mode", R.mode, sel, atoms)
end

function MapLua:in_3(sel, atoms)
  self:answer(sel, R.internal[sel], atoms)
  if sel == "init" then self:outlet(5, "bang", {}) end
end
