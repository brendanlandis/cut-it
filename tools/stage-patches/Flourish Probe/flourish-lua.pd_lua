-- flourish-lua -- flourish.lua's Pd face, made in main.pd as [flourish-lua]. It turns messages
-- into calls on the rules and plays the plans they return on a clock; what a plan holds is in
-- flourish.lua.
--
-- inlet 1: init | key <pitch> <velocity> | knob <n> <0..1> | wire <words...> | quit
-- outlet 1: <note> <velocity> <channel>, to noteout. outlet 2: <value> <number> <channel>, to
-- ctlout. outlets 3-7: a symbol, to screenLine1-5. outlet 8: open, start or stop, to writesf~.
--
-- A key's plan replaces the one running; a knob's only adds its screen line now. A
-- Lua error shows as "lua error" on line 5 and its text goes to the console where there is one.

local P = pd.Class:new():register("flourish-lua")
local R = dofile(P._loadpath .. "flourish.lua")

function P:initialize(_, _)
  self.inlets, self.outlets = 1, 8
  self.st = R.new()
  self.plan, self.i, self.now = {}, 1, 0
  self.clock = pd.Clock:new():register(self, "tick")
  return true
end

function P:finalize()
  self.clock:destruct()
end

function P:emit(e)
  if e[2] == "note" then
    self:outlet(1, "list", { e[3], e[4], e[5] })
  elseif e[2] == "cc" then
    self:outlet(2, "list", { e[3], e[4], e[5] })
  elseif e[2] == "line" then
    self:outlet(2 + e[3], "symbol", { e[4] })
  elseif e[2] == "rec" then
    self:outlet(8, e[3], e[4])
  end
end

-- Fire every event due now, then wait for the next.
function P:tick()
  local plan = self.plan
  while self.i <= #plan and plan[self.i][1] <= self.now do
    self:emit(plan[self.i])
    self.i = self.i + 1
  end
  if self.i <= #plan then
    local wait = plan[self.i][1] - self.now
    self.now = plan[self.i][1]
    self.clock:delay(wait)
  end
end

function P:run(plan)
  self.clock:unset()
  self.plan, self.i, self.now = R.sort(plan), 1, 0
  self:tick()
end

-- Events now, without touching the plan in flight.
function P:now_only(plan)
  for _, e in ipairs(R.sort(plan)) do self:emit(e) end
end

function P:in_1(sel, atoms)
  local ok, err = pcall(function()
    if sel == "key" then
      local plan = R.key(self.st, atoms[1], atoms[2])
      if plan then self:run(plan) end
    elseif sel == "knob" then
      self:now_only(R.knob(self.st, atoms[1], atoms[2]))
    elseif sel == "init" then
      self:now_only(R.init(self.st))
    elseif sel == "wire" then
      local words = {}
      for _, a in ipairs(atoms) do words[#words + 1] = tostring(a) end
      self:outlet(7, "symbol", { table.concat(words, " "):sub(1, 21) })
    elseif sel == "quit" then
      self.clock:unset()
      self:now_only(R.quit(self.st))
    end
  end)
  if not ok then
    pd.post("flourish-lua: " .. tostring(err))
    self:outlet(7, "symbol", { "lua error" })
  end
end
