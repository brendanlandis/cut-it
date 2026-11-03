-- m_nano.lua -- the nanoKONTROL's decode: a CC number and its value in, a named control out.
-- Plain Lua with no Pd in it, so test/gate/lua/m_nano_test.lua runs it on the Mac with lua.org's
-- interpreter. m_nano-lua.pd_lua is its Pd face, and m_nano.pd keeps [ctlin], the channel gate,
-- presence and the device inquiry. ref/device/nanokontrol.md.
--
-- Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"param", <name>, {value}}             a control, as slider-3 21 or btn-t-2 1
--   {"err", "warn" | "fail", {"m_nano", text}}  to err (C-12)

local R = {}

-- The surface by tens (ref/device/nanokontrol.md): the CC's tens digit is the kind, its units
-- digit which one. Sliders and knobs carry their value; the three button rows send 1 on a
-- press and nothing on a release, since they are momentary and Pd owns their state. The
-- transport row is CC 41-46, so it is the fifth kind and a button.
R.KINDS = {
  [0] = { "slider-", false },
  [1] = { "knob-", false },
  [2] = { "btn-t-", true },
  [3] = { "btn-b-", true },
  [4] = { "xport-", true },
}

-- A number from a message, as Pd's [f] reads one: a symbol or nothing is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- A number's integer part, toward zero, as [div] and [mod] take a controller number.
local function int(x)
  return x < 0 and math.ceil(x) or math.floor(x)
end

-- Every name the surface can have, worked out once: a control's message is then a lookup.
-- NAME[cc] is its name, BUTTON[cc] whether it is a button; a CC with no kind has neither.
R.NAME, R.BUTTON = {}, {}
for cc = 0, 49 do
  local kind = R.KINDS[cc // 10]
  R.NAME[cc], R.BUTTON[cc] = kind[1] .. (cc % 10), kind[2]
end

-- A CC on the nano's own two channels: <controller> <value>. A CC that decodes to no kind is
-- a warning and nothing else, so it can never go out under another control's name.
function R.cc(controller, value)
  local cc = int(num(controller))
  local name = R.NAME[cc]
  if not name then return { R.report("warn", "cc-" .. cc .. "-unmapped") } end
  value = num(value)
  if R.BUTTON[cc] then
    if value ~= 127 then return {} end
    value = 1
  end
  return { { "param", name, { value } } }
end

-- What m_nano.pd itself sends: the load.
R.internal = {
  init = function()
    return {}
  end,
}

-- A report on err, C-12: one symbol of 21 characters or fewer.
function R.report(level, text)
  return { "err", level, { "m_nano", string.sub(text, 1, 21) } }
end

function R.fail(text)
  return R.report("fail", text)
end

return R
