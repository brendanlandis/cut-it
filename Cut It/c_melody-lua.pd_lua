-- c_melody-lua -- c_melody.lua's Pd face, made inside c_melody.pd as [c_melody-lua <engine>]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else.
--
-- inlet 1: <note> <velocity> from m_nanokey, <control> <0-1>, the roll pads and the home pad from u_map, and
-- step <count> <ms> from c_steps, and set <control> <value>, the roll pads and the home pad from u_net. inlet 2: c_melody.pd's own -- restore <the saved line>, sync,
-- start, stop, init.
-- outlet 1: <synth> <note> <velocity> <ms>, to the note timing. outlet 2: melody <the line>, to
-- put. outlet 3: err. outlet 4: a bang on init, the proof the Lua loaded. outlet 5: a control's row.
-- outlet 6: melody <what the phone shows>, to u_net. outlet 7: <3 or 4> <wave, or -1 for off>, to the
-- Pd voices, c_mono: 3 the melody's, 4 the chords' four. outlet 8: a bang to start the transport.
-- outlet 9: here <step> <melody step>, the loops' places, to u_net. outlet 10: notes <what the melody grid
-- shows>, to u_net, at most every NOTES_EVERY ms. outlet 11: held <chord> <step> <note>, to g_grid.
-- outlet 12: <3 or 4> <param> <value>, a Pd voice's parameter, to c_mono.
--
-- There are as many of these as u_voices.lua's R.ENGINES. Only the one whose voice is on show hears the
-- Launchpad, the phone and the nanoKEY, and speaks to them; a message e<n>-<name>, from u_perform, is for
-- engine n, on show or not.

local MelodyLua = pd.Class:new():register("c_melody-lua")
local Clock = pd.Clock

local R = dofile(MelodyLua._loadpath .. "c_melody.lua")

local OUTLET = { play = 1, save = 2, err = 3, disp = 5, mono = 7, start = 8, here = 9, held = 11, tone = 12 }

local F = dofile(MelodyLua._loadpath .. "lua-face.lua")
F.carry(MelodyLua, R, OUTLET, 2, 4)

-- The line is a few hundred numbers, so a fader's drag puts it at most this often. What a roll changes is
-- not put at all until something needs it: sync, which u_song sends before it acts, so a loop
-- drifting writes nothing to the card.
local SAVE_EVERY = 100
local ROLL_EVERY = 12
-- The melody grid is 73 numbers, and at a low lock changes on every step, so it goes at most this often.
local NOTES_EVERY = 250

function MelodyLua:initialize(_, atoms)
  self.inlets, self.outlets = 2, 12
  self.engine = type(atoms[1]) == "number" and math.floor(atoms[1]) or 1
  self.part = self.engine == 1 and "melody" or ("melody-" .. self.engine)
  self.active = self.engine == 1
  self.state = R.new(nil, self.engine)
  return true
end

function MelodyLua:postinitialize()
  self.save_clock = Clock:new():register(self, "save_due")
  self.roll_clock = Clock:new():register(self, "roll_due")
  self.notes_clock = Clock:new():register(self, "notes_due")
end

function MelodyLua:finalize()
  if self.save_clock then self.save_clock:destruct() end
  if self.roll_clock then self.roll_clock:destruct() end
  if self.notes_clock then self.notes_clock:destruct() end
end

function MelodyLua:hold(e)
  if e[1] == "save" then
    if self.holding then
      if not self.save_held then
        self.save_held = true
        self.save_clock:delay(SAVE_EVERY)
      end
    else
      self:outlet(2, self.part, e[3])
    end
    return true
  end
  if (e[1] == "here" or e[1] == "disp" or e[1] == "held") and not self.active then return true end
  return false
end

function MelodyLua:save_now()
  self.save_held = false
  self.save_clock:unset()
  local ok, e = pcall(R.save, self.state)
  if ok then self:outlet(2, self.part, e[3]) end
end

function MelodyLua:roll_due()
  self.rolling = false
  self.state.show = true
  self:answer("roll-next", R.roll_next, self.state)
end

function MelodyLua:notes_due()
  self.notes_waiting = false
  self.state.show_notes = false
  local ok, now = pcall(R.phone_notes, self.state)
  if ok then self:outlet(10, "notes", now) end
end

function MelodyLua:save_due()
  self:save_now()
end

-- After every answer, what the phone shows, out the sixth outlet only when it differs from the last
-- one sent.
function MelodyLua:answered()
  -- Chords queued to roll go one at a time, so a whole new loop is no burst of work in one audio block.
  if (#self.state.to_roll > 0 or #self.state.to_roll_m > 0) and not self.rolling then
    self.rolling = true
    self.roll_clock:delay(ROLL_EVERY)
  end
  if not self.active then
    self.state.show, self.state.show_notes = false, false
    return
  end
  if self.state.show_notes and not self.notes_waiting then
    self.notes_waiting = true
    self.notes_clock:delay(self.notes_sent and NOTES_EVERY or 20)
    self.notes_sent = true
  end
  -- Only when something it shows may have changed, not on every step.
  if not self.state.show then return end
  self.state.show = false
  local ok, now = pcall(R.phone, self.state)
  if not ok then return end
  local key = table.concat(now, " ")
  if key ~= self.phone_sent then
    self.phone_sent = key
    self:outlet(6, "melody", now)
  end
end

function MelodyLua:in_1(sel, atoms)
  if sel == "active" then
    local now = atoms[1] == self.engine
    if now and not self.active then
      self.phone_sent, self.state.show, self.state.show_notes = nil, true, true
    end
    self.active = now
    if now then self:answered() end
    return
  end
  if sel ~= "step" and sel ~= "assign" and sel ~= "tone" and sel ~= "hear" then
    local e, name = tostring(sel):match("^e(%d+)%-(.+)$")
    if e then
      if tonumber(e) ~= self.engine then return end
      sel = name
    elseif not self.active then
      return
    end
    self.state.show = true
  end
  self.holding = true
  self:answer(sel, R.inputs[sel], self.state, atoms)
  self.holding = false
end

function MelodyLua:in_2(sel, atoms)
  self.state.show = true
  if sel == "sync" then
    if self.save_held or self.state.dirty then self:save_now() end
    return
  end
  if sel == "restore" then
    self.save_held = false
    self.save_clock:unset()
  end
  self:internal(sel, atoms)
end
