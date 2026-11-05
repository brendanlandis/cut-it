-- g_grid-lua -- g_grid.lua's Pd face, made inside g_grid.pd as [g_grid-lua $0-surface]. It reads
-- the layout table, turns c_steps' messages into calls on the rules, and writes the drum page's
-- cells into g_grid's frame buffer when asked, and nothing else: what the page shows is in
-- g_grid.lua. ref/module/display.md, g_grid's drum page.
--
-- creation arg: the frame buffer's name, g_grid's $0-surface.
-- inlet 1: the drum page's state, from c_steps -- steps <32 levels>, play <step>, vel <level>,
-- track <pad>, last <step>, bar <N> <row> and rep <pad>. inlet 2: g_grid.pd's own -- init at
-- load, and paint, from pd regions on page 2, before each frame's SysEx.
-- outlet 1: err. outlet 2: a bang on init, the proof the Lua loaded.
--
-- A Lua error leaves outlet 1 as fail g_grid lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local GridLua = pd.Class:new():register("g_grid-lua")
-- pdlua's arrays, taken while pd is in reach: the Lua tests stand pd in only while loading.
local Table = pd.Table

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload g_grid-lua`) reloads them too, and every object keeps its page.
local R = dofile(GridLua._loadpath .. "g_grid.lua")

local OUTLET = { err = 1 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(GridLua._loadpath .. "lua-face.lua")
F.carry(GridLua, R, OUTLET, 2, 2)

-- The layout is read when the object is made, before any loadbang, from the folder of the patch
-- that holds it, as g_grid.pd's `read -c cut-it-drum-page.txt` was. A missing file is an error
-- on the console, which fails a deploy, and layout-empty on err at init.
function GridLua:initialize(_, atoms)
  self.inlets, self.outlets = 2, 2
  self.surface = atoms[1]
  self.table = Table:new()
  local fh, why = io.open(self._canvaspath .. "cut-it-drum-page.txt", "r")
  local text = ""
  if fh then
    text = fh:read("a")
    fh:close()
  else
    self:error("g_grid-lua: " .. tostring(why))
  end
  self.state = R.new(text)
  return true
end

function GridLua:in_1(sel, atoms)
  self:answer(sel, R.inputs[sel], self.state, atoms)
end

function GridLua:in_2(sel, atoms)
  if sel == "paint" then return self:paint() end
  self:internal(sel, atoms)
end

-- One frame's drum page into the frame buffer, cell by cell, over the fill pd prepare wrote. The
-- array is found again every frame, as pdlua asks, so a buffer made after this object, or one
-- redefined, is still the one written. No buffer is fail g_grid no-surface.
function GridLua:paint()
  local ok, index, colors = pcall(R.paint, self.state)
  if not ok then
    self:error(self._name .. ": " .. tostring(index))
    return self:outlet(OUTLET.err, "fail", R.fail("lua-paint")[3])
  end
  local t = type(self.surface) == "string" and self.table:sync(self.surface)
  if not t then
    return self:outlet(OUTLET.err, "fail", R.fail("no-surface")[3])
  end
  for k = 1, #index do t:set(index[k], colors[k]) end
end
