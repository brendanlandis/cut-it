-- u_once.lua -- a press from the phone, once. OSC here is UDP, which can drop a message: the app sends a
-- one-time press as once <seq> <words...> and sends it again until it hears once <seq> back, so a press isn't
-- lost; and this lets each through once, so a press isn't doubled when only its answer was lost. Plain Lua with
-- no Pd in it, so test/gate/lua/u_once_test.lua runs it on the Mac. u_once-lua.pd_lua is its Pd face, and
-- u_once.pd keeps the cords. ref/device/phone.md.
--
-- Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"forward", "list", {words...}}    the press, on to u_net's route, as if it had come plain
--   {"answer", "list", {seq}}          /cutit/once <seq>
--   {"err", "fail", {"u_once", text}}  err (C-12)

local R = {}

-- How many presses it remembers: well past as many as a retry could still be chasing.
R.REMEMBER = 64

function R.fail(text)
  return { "err", "fail", { "u_once", string.sub(text, 1, 21) } }
end

function R.new()
  return { seen = {}, order = {}, at = 0 }
end

-- once <seq> <words...>: answered always; through only the first time.
function R.once(st, atoms)
  local seq = atoms[1]
  if type(seq) ~= "number" or #atoms < 2 then return { R.fail("bad-once") } end
  local out = { { "answer", "list", { seq } } }
  if st.seen[seq] then return out end
  st.seen[seq] = true
  st.at = st.at % R.REMEMBER + 1
  local old = st.order[st.at]
  if old then st.seen[old] = nil end
  st.order[st.at] = seq
  out[#out + 1] = { "forward", "list", { table.unpack(atoms, 2) } }
  return out
end

R.internal = {
  init = function() return {} end,
}

return R
