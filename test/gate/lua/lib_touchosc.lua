-- A stand-in for TouchOSC, enough to run a layout's scripts with no phone: its controls, with
-- values that call onValueChanged when they change, properties and a frame a script sets, notify,
-- root:findByName, sendOSC and getMillis (~/Sites/!reference/touchosc.md, Scripting).
--
--   local L = dofile("test/gate/lua/lib_touchosc.lua")
--   local w = L.load(dir)       -- dir: controls.lua and a <name>.lua per script, from the gate
--   L.osc(w, "/cutit/hb", 1, 0)
--   L.press(w, "tap5")
--
-- What the stand-in can't say is how TouchOSC draws; the phone is the oracle for that.

local L = {}

function L.load(dir)
  local w = { now = 0, sent = {}, controls = {}, envs = {} }
  _G.getMillis = function() return w.now end
  _G.Color = function(r, g, b, a) return { r, g, b, a or 1 } end
  _G.Orientation = { NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3 }
  _G.sendOSC = function(...) w.sent[#w.sent + 1] = { ... } end
  local manifest = dofile(dir .. "/controls.lua")
  for _, m in ipairs(manifest) do
    local vals = { x = m.x or 0, page = 0, touch = false, text = m.text or "" }
    local c = { name = m.name, type = m.type, visible = m.visible, color = m.color,
                tabLabel = m.tabLabel, tabbar = m.tabbar, frame = {}, children = {} }
    c.values = setmetatable({}, {
      __index = vals,
      __newindex = function(_, k, v)
        local old = vals[k]
        vals[k] = v
        local e = w.envs[m.name]
        if old ~= v and e and e.onValueChanged then e.onValueChanged(k) end
      end })
    function c:notify(k, v)
      local e = w.envs[self.name]
      if e and e.onReceiveNotify then e.onReceiveNotify(k, v) end
    end
    function c:findByName(n) return w.controls[n] end
    w.controls[m.name] = c
  end
  -- Each control's children, by name, in the file's order: a pager's pages.
  for _, m in ipairs(manifest) do
    if m.parent then table.insert(w.controls[m.parent].children, w.controls[m.name]) end
  end
  _G.root = w.controls.root
  for _, m in ipairs(manifest) do
    if m.script then
      local env = setmetatable({ self = w.controls[m.name] }, { __index = _G })
      assert(loadfile(dir .. "/" .. m.name .. ".lua", "t", env))()
      w.envs[m.name] = env
    end
  end
  for _, e in pairs(w.envs) do if e.init then e.init() end end
  return w
end

-- A message arriving on the receive port; numbers tagged f, the rest s.
function L.osc(w, path, ...)
  local a = {}
  for i, v in ipairs({ ... }) do a[i] = { tag = type(v) == "number" and "f" or "s", value = v } end
  w.envs.root.onReceiveOSC({ path, a }, {})
end

-- A finger down on a button and up again. -> what it sent.
function L.press(w, name)
  local before = #w.sent
  local c = w.controls[name]
  c.values.touch = true
  c.values.x = 1
  c.values.x = 0
  c.values.touch = false
  local out = {}
  for i = before + 1, #w.sent do out[#out + 1] = w.sent[i] end
  return out
end

-- A finger down on a button and up again, as press does. -> its x after each step: touch down,
-- x 1, x 0, touch up, so a button whose look is the state's shows the state's all through.
function L.looks(w, name)
  local c, xs = w.controls[name], {}
  c.values.touch = true
  xs[#xs + 1] = c.values.x
  c.values.x = 1
  xs[#xs + 1] = c.values.x
  c.values.x = 0
  xs[#xs + 1] = c.values.x
  c.values.touch = false
  xs[#xs + 1] = c.values.x
  return xs
end

-- A finger down on a control and up again, without moving it: a tap on a fader. -> what it
-- sent.
function L.tap(w, name)
  local before = #w.sent
  local c = w.controls[name]
  c.values.touch = true
  c.values.touch = false
  local out = {}
  for i = before + 1, #w.sent do out[#out + 1] = w.sent[i] end
  return out
end

-- A finger dragging a fader to a value, 0 to 1, or a radio to a segment, 0 the first. -> what
-- it sent.
function L.drag(w, name, x)
  local before = #w.sent
  local c = w.controls[name]
  c.values.touch = true
  c.values.x = x
  c.values.touch = false
  local out = {}
  for i = before + 1, #w.sent do out[#out + 1] = w.sent[i] end
  return out
end

function L.update(w, ms)
  w.now = w.now + (ms or 0)
  for _, e in pairs(w.envs) do if e.update then e.update() end end
end

function L.text(w, name) return w.controls[name].values.text end
function L.visible(w, name) return w.controls[name].visible end

-- The page a pager shows: its child at its page value, 0 the first.
function L.page(w, pager)
  local c = w.controls[pager]
  return c.children[c.values.page + 1]
end

return L
