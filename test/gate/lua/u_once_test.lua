-- A press from the phone, once, with no Pd.
package.path = "test/gate/lua/?.lua;" .. package.path
local T = require("lib_test")
local equal = T.equal
local R = dofile("Cut It/u_once.lua")

local st = R.new()
equal("⛔ the first time: answered, and through", R.once(st, { 7, "voices", "left", 2 }),
      { { "answer", "list", { 7 } }, { "forward", "list", { "voices", "left", 2 } } })
equal("⛔ sent again: answered, and not through", R.once(st, { 7, "voices", "left", 2 }),
      { { "answer", "list", { 7 } } })
equal("no words is a failure", R.once(st, { 8 }), { { "err", "fail", { "u_once", "bad-once" } } })
for i = 100, 100 + R.REMEMBER do R.once(st, { i, "x" }) end
equal("it forgets the oldest, so a long set can't grow it", st.seen[100], nil)
equal("... and remembers the newest", st.seen[100 + R.REMEMBER], true)

os.exit(T.report() == 0)
