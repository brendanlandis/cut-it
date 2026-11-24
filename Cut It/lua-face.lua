-- lua-face.lua -- what the pdlua classes share, every *-lua.pd_lua beside it. Each loads it beside
-- its rules and calls F.carry; the rules stay plain Lua with no Pd in them. It sits beside no
-- abstraction, so it is named for what it is (ref/conventions.md, File naming).
--
-- F.carry fits a class to its rules. The rest is what several faces did each in its own words:
-- F.changed and F.differs send a list only when it differs from the last one sent, F.clocks gives a
-- class its clocks, which F.soon starts and F.stop stops, and F.read reads a file beside the patch.

local F = {}
-- pdlua's clock, taken while pd is in reach: the Lua tests stand pd in only while a class loads.
local Clock = pd and pd.Clock

-- What a face keeps for these: the lists last sent, as strings, and which clocks are waiting.
local function kept(self)
  local k = self.face
  if not k then
    k = { went = {}, waiting = {} }
    self.face = k
  end
  return k
end

-- Whether a list differs from the one last given under this name, which it then replaces.
function F.differs(self, name, atoms)
  local went, k = kept(self).went, table.concat(atoms, "\1")
  if went[name] == k then return false end
  went[name] = k
  return true
end

-- A rule's list out an outlet, when it differs from the last one sent under this name. The rule
-- runs under pcall, and one that throws sends nothing. -> whether it ran, and its list.
function F.changed(self, name, outlet, sel, rule, ...)
  local ok, now = pcall(rule, ...)
  if not ok then return false end
  if F.differs(self, name, now) then self:outlet(outlet, sel, now) end
  return true, now
end

-- Forget what was last sent under a name, so the next goes whatever it is.
function F.forget(self, name)
  kept(self).went[name] = nil
end

-- Give a class a clock for each name: self.<name>_clock, made once the object is and destructed
-- with it, which calls self:<name>_due() when its time comes. F.soon starts one unless it is
-- already waiting, so a burst of changes is one piece of work, at most once every so many ms.
function F.clocks(class, names)
  for _, name in ipairs(names) do
    class[name .. "_clock_fired"] = function(self)
      kept(self).waiting[name] = false
      return self[name .. "_due"](self)
    end
  end
  function class:postinitialize()
    for _, name in ipairs(names) do
      self[name .. "_clock"] = Clock:new():register(self, name .. "_clock_fired")
    end
  end
  function class:finalize()
    for _, name in ipairs(names) do
      local c = self[name .. "_clock"]
      if c then c:destruct() end
    end
  end
end

-- Start a clock in ms, unless it is waiting already. -> whether this started it.
function F.soon(self, name, ms)
  local waiting = kept(self).waiting
  if waiting[name] then return false end
  waiting[name] = true
  self[name .. "_clock"]:delay(ms)
  return true
end

-- Whether a clock is waiting.
function F.waiting(self, name)
  return kept(self).waiting[name] == true
end

-- Stop a clock. -> whether it was waiting.
function F.stop(self, name)
  local waiting = kept(self).waiting
  local was = waiting[name] == true
  waiting[name] = false
  self[name .. "_clock"]:unset()
  return was
end

-- A file beside the patch that holds the object, whole. One that isn't there is "" and an error on
-- the console, which fails a deploy; or nil and no error, if it may be missing.
function F.read(self, name, may_be_missing)
  local fh, why = io.open(self._canvaspath .. name, "rb")
  if not fh then
    if may_be_missing then return nil end
    self:error(self._name .. ": " .. tostring(why))
    return ""
  end
  local text = fh:read("a")
  fh:close()
  return text
end

-- Fit a class to its rules. R: the rules, with R.fail and R.internal. outlets: each answer's
-- first field to its outlet number. inlets: how many in_N methods the class has. proof: the
-- outlet that bangs once init is answered, which shuts the no-lua guard in the patch.
function F.carry(class, R, outlets, inlets, proof)
  -- One rule's answer, or fail <source> lua-<name> if it threw, with its text on the console
  -- where there is one (C-12), or bad-selector if there is no rule. Then the class's
  -- answered(), if it has one.
  function class:answer(name, rule, ...)
    local ok, out = true, { R.fail("bad-selector") }
    if rule then ok, out = pcall(rule, ...) end
    if not ok then
      self:error(self._name .. ": " .. tostring(out))
      out = { R.fail("lua-" .. name) }
    end
    for _, e in ipairs(out) do
      -- A class with a hold() may keep an answer back to send later, as c_steps-lua does its
      -- pattern (ref/module/sequencer.md); it answers true for one it kept.
      if not (self.hold and self:hold(e)) then self:outlet(outlets[e[1]], e[2], e[3]) end
    end
    if self.answered then self:answered() end
  end

  -- The patch's own messages, R.internal's, each given the state and its atoms; init is
  -- answered with the proof bang.
  function class:internal(sel, atoms)
    self:answer(sel, R.internal[sel], self.state, atoms)
    if sel == "init" then self:outlet(proof, "bang", {}) end
  end

  -- Every message straight to its inlet's method. pdlua's own dispatch first builds and tries
  -- two method names from the selector, a large share of a message's cost on the Organelle
  -- (ref/module/map.md). A pdlua that stopped calling dispatch would lose only the shortcut.
  local names = {}
  for i = 1, inlets do names[i] = "in_" .. i end
  function class:dispatch(inlet, sel, atoms)
    return self[names[inlet]](self, sel, atoms)
  end
end

return F
