-- What every Lua test needs: the tally, in lib_assert.py's format so a gate's Python and Lua
-- halves read alike, and a stand-in for pdlua's `pd`, so a .pd_lua class loads and answers
-- messages with no Pd at all. Run from the repo root with lua.org's Lua 5.4:
--
--   local T = dofile("test/gate/lua/lib_test.lua")
--   T.check("the thing holds", ok, detail)
--   os.exit(T.report() == 0)

local T = {}
local total, fails = 0, 0
local verbose = false
for _, a in ipairs(arg or {}) do if a == "-v" then verbose = true end end

-- A value as one line, tables included, so a failing check says what it got.
function T.show(v)
  if type(v) ~= "table" then
    return type(v) == "string" and string.format("%q", v) or tostring(v)
  end
  local parts = {}
  for i = 1, #v do parts[#parts + 1] = T.show(v[i]) end
  for k, x in pairs(v) do
    if type(k) ~= "number" or k < 1 or k > #v or k % 1 ~= 0 then
      parts[#parts + 1] = tostring(k) .. "=" .. T.show(x)
    end
  end
  return "{" .. table.concat(parts, " ") .. "}"
end

-- Deep equality, as a check means it: 32 and 32.0 are the same velocity.
function T.same(a, b)
  if type(a) ~= "table" or type(b) ~= "table" then return a == b end
  for k, v in pairs(a) do if not T.same(v, b[k]) then return false end end
  for k in pairs(b) do if a[k] == nil then return false end end
  return true
end

-- One assertion: PASS or FAIL, with the detail on a failure, or always under -v.
function T.check(name, ok, detail)
  total = total + 1
  if not ok then fails = fails + 1 end
  local d = detail ~= nil and tostring(detail) or ""
  print(string.format("  %s  %s%s", ok and "PASS" or "FAIL", name,
                      (ok and not verbose or d == "") and "" or ("   -- " .. d)))
  return ok
end

-- check that got equals want, showing both when it does not.
function T.equal(name, got, want)
  return T.check(name, T.same(got, want), "want " .. T.show(want) .. " got " .. T.show(got))
end

-- The tally, and the failure count. The total proves no check went missing.
function T.report()
  print(string.format("\n%d checks, %d failed", total, fails))
  return fails
end

-- A .pd_lua class loaded without Pd: pd.Class:new():register() as pdlua has it, enough of it
-- for a class that keeps to initialize, inlets and outlets. `prefix` stands in for the
-- directory pdlua found the file in; the class reads its neighbors as prefix .. name.
-- -> the class.
function T.load_class(path, prefix)
  local registered
  local Base = {}
  function Base:new() return setmetatable({}, { __index = self }) end
  function Base:register(name)
    self._name, self._loadpath, registered = name, prefix, self
    return self
  end
  function Base:outlet(n, sel, atoms) table.insert(self.sent, { n, sel, atoms }) end
  function Base:error(msg) table.insert(self.console, msg) end
  _G.pd = { Class = Base }
  dofile(path)
  _G.pd = nil
  return registered
end

-- An object of a class from load_class, as pdlua makes one. `canvas` stands in for the folder
-- of the patch it is made in, pdlua's _canvaspath; the class's own folder if not given.
-- -> the object, or nil if its initialize refused.
function T.new(class, args, canvas)
  local o = class:new()
  o.sent, o.console, o._canvaspath = {}, {}, canvas or class._loadpath
  if not o:initialize(class._name, args or {}) then return nil end
  return o
end

-- A message into an object's inlet, dispatched as pd.lua's pd.Class:dispatch does for these
-- shapes; -> what left its outlets, in order, as {outlet, selector, atoms}.
function T.send(o, inlet, sel, atoms)
  o.sent = {}
  local m = o[string.format("in_%d_%s", inlet, sel)]
  if type(m) == "function" then
    m(o, atoms)
  else
    m = o[string.format("in_%d", inlet)]
    assert(type(m) == "function", "no method for " .. sel .. " at inlet " .. inlet)
    m(o, sel, atoms)
  end
  return o.sent
end

return T
