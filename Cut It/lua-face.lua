-- lua-face.lua -- what the six pdlua classes share: c_steps-lua, c_synth-lua, u_map-lua,
-- u_tempo-lua, m_nano-lua and m_organelle-lua. Each loads it beside its rules and calls F.carry; the rules
-- stay plain Lua with no Pd in them. It sits beside no abstraction, so it is named for what it
-- is (ref/conventions.md, File naming).

local F = {}

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
