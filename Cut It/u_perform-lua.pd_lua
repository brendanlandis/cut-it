-- u_perform-lua -- u_perform.lua's Pd face, made inside u_perform.pd as [u_perform-lua]. It reads the
-- controls' table, turns messages into calls on the rules and the rules' answers into outlets, and
-- nothing else. ref/module/voices.md.
--
-- inlet 1: u_map's <arg> <value>: the nanoKONTROL, and REC, and the performance page's pads. inlet 2:
-- the phone's perform <cmd> ..., through u_net. inlet 3: u_perform.pd's own -- restore <atoms...>,
-- rows, heard, init. outlet 1: to the map's route. outlet 2: cols and btns, to g_grid. outlet 3:
-- perform <atoms>, to u_net. outlet 4: perform <atoms>, to the state bus. outlet 5: err. outlet 6: a
-- bang on init, the proof the Lua loaded.

local PerformLua = pd.Class:new():register("u_perform-lua")
local Clock = pd.Clock

local R = dofile(PerformLua._loadpath .. "u_perform.lua")

local OUTLET = { route = 1, save = 4, err = 5 }

local F = dofile(PerformLua._loadpath .. "lua-face.lua")
F.carry(PerformLua, R, OUTLET, 3, 6)

-- A sweep of a fader is a message every few ms: the surfaces hear of it at most this often, and the
-- song store at most this often.
local SHOW_EVERY, SAVE_EVERY = 40, 300

function PerformLua:initialize()
  self.inlets, self.outlets = 3, 6
  local fh = io.open(self._canvaspath .. "cut-it-controls.txt", "r")
  local text = ""
  if fh then
    text = fh:read("a")
    fh:close()
  else
    self:error("u_perform-lua: no cut-it-controls.txt")
  end
  self.state = R.new(text)
  return true
end

function PerformLua:postinitialize()
  self.show_clock = Clock:new():register(self, "show_due")
  self.save_clock = Clock:new():register(self, "save_due")
end

function PerformLua:finalize()
  if self.show_clock then self.show_clock:destruct() end
  if self.save_clock then self.save_clock:destruct() end
end

local function key(a)
  return table.concat(a, " ")
end

function PerformLua:show_due()
  self.show_waiting = false
  local st = self.state
  local ok, c = pcall(R.cols, st)
  if ok then
    local k = key(c)
    if k ~= self.cols_sent then
      self.cols_sent = k
      self:outlet(2, "cols", c)
    end
  end
  local ok2, b = pcall(R.btns, st)
  if ok2 then
    local k = key(b)
    if k ~= self.btns_sent then
      self.btns_sent = k
      self:outlet(2, "btns", b)
    end
  end
  local ok3, p = pcall(R.phone, st)
  if ok3 then
    local k = key(p)
    if k ~= self.phone_sent then
      self.phone_sent = k
      self:outlet(3, "perform", p)
    end
  end
end

function PerformLua:save_due()
  self.save_waiting = false
  local st = self.state
  local names = {}
  for name in pairs(st.list) do names[#names + 1] = name end
  table.sort(names)
  local a = {}
  for _, name in ipairs(names) do
    local c = st.list[name]
    a[#a + 1] = name
    a[#a + 1] = c.dest
    a[#a + 1] = c.arg
    a[#a + 1] = c.row
    a[#a + 1] = tonumber(string.format("%.3f", c.value))
  end
  self:outlet(4, "perform", a)
end

function PerformLua:answered()
  if not self.show_waiting then
    self.show_waiting = true
    self.show_clock:delay(SHOW_EVERY)
  end
  if self.state.dirty and not self.save_waiting then
    self.state.dirty = false
    self.save_waiting = true
    self.save_clock:delay(SAVE_EVERY)
  end
end

function PerformLua:in_1(sel, atoms)
  if sel == "list" then sel = atoms[1]; atoms = { atoms[2] } end
  self:answer("mapped", R.mapped, self.state, sel, atoms)
end

function PerformLua:in_2(sel, atoms)
  -- A command with no argument reaches here as a symbol.
  if sel == "symbol" then sel, atoms = atoms[1], {} end
  self:answer(tostring(sel), R.phone_cmds[sel], self.state, atoms)
end

function PerformLua:in_3(sel, atoms)
  self:internal(sel, atoms)
end
