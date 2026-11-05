-- c_steps-lua -- c_steps.lua's Pd face, made inside c_steps.pd as [c_steps-lua $1]. It turns
-- messages into calls on the rules and the rules' answers into outlets, and nothing else: what
-- the sequencer does is in c_steps.lua. ref/module/sequencer.md.
--
-- creation arg: its bank, 1 for A: vestigial since the SP-404 left the rig, as c_kit plays pads
-- 1 to 16 (c_steps.pd).
-- inlet 1: the presses and releases, from u_map -- step <n> <vel>, vel <level> <vel>, pad <n>
-- <vel>, rep <n> <vel>, fast and recall <n> <vel>, the 500 BPM repeat and the saved tempo, and
-- knobs 2 to 4, last, track-last and swing <0-1> -- and the phone's
-- sync, snap, select, vol, pitch, randomness, set-track-last, num, den, drunk, set-swing and
-- set-last, its effects, drive, tone, dist, char, delay-note, delay-feel, feedback, delay, send,
-- size, damping and verb-type, and each track's mute, solo and rnd-pitch, from u_net.
-- inlet 2: c_steps.pd's own -- tick <bpm>, start, stop, restore <the saved line>, init, and sync
-- off the state bus: put the pattern now if it is being held.
-- outlet 1: pad <pad> <velocity>, and a track's vol <pad> <dB> and pitch <pad> <semitones> and
-- its effects, drive, tone, dist, char, delay-time, feedback, delay and send <pad> <value>, and the
-- reverb's size and damping <value> and verb-type <0-2>, and a held repeat's tape <span> <units>
-- and tape-off, to c_kit. outlet 2: the page, to g_grid. outlet 3: the pattern to save, at most once every
-- SAVE_EVERY ms (below). outlet 4: err. outlet 5: a
-- bang on init, the proof the Lua loaded. outlet 6: a knob's row, to disp. outlet 7: the phone's
-- state, R.phone's 148 numbers, whenever it changes.
-- outlet 8: the step clock's swing <0.5-0.75> and rate <x>, to c_steps.pd's clock.
-- outlet 9: bar, on the global loop's last step, to u_song: a bar is the pattern's loop, and a
-- queued section starts as the loop comes round to its step 1; and recall <key>, a part's saved
-- value asked for. outlet 10: fast <1 or 0>, the 500 BPM repeat's tempo, to u_tempo.
--
-- A Lua error leaves outlet 4 as fail c_steps lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12).

local StepsLua = pd.Class:new():register("c_steps-lua")
-- pdlua's clock, taken while pd is in reach: the Lua tests stand pd in only while loading.
local Clock = pd.Clock

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload c_steps-lua`) reloads them too, and every object keeps its pattern.
local R = dofile(StepsLua._loadpath .. "c_steps.lua")

local OUTLET = { note = 1, page = 2, save = 3, err = 4, disp = 6, clock = 8, bar = 9, one = 9, song = 9,
                 tempo = 10 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(StepsLua._loadpath .. "lua-face.lua")
F.carry(StepsLua, R, OUTLET, 2, 5)

function StepsLua:initialize(_, atoms)
  self.inlets, self.outlets = 2, 10
  self.state = R.new(atoms[1])
  return true
end

-- The pattern to save is 581 numbers, 711 once an effect is set, 743 once a track is muted or
-- soloed, 759 once a track's distortion is not soft and 776 once a track's random pitch is on, and carrying the 581 to u_song and storing them cost about 2.5 ms on the Organelle, so
-- a drag on the phone, a change 30 or 60 times a second, made the audio crackle (2026-11-05: Pd
-- runs with a 6 ms audio buffer, and WiFi hands over two messages at once). So the pattern goes
-- at most once every SAVE_EVERY ms: the first change starts the clock, later ones only mark it
-- held, and the clock puts the pattern as it then stands. Before anything that needs the latest pattern -- a bar, which can start the next section,
-- and u_song's presses, which can save, revert, copy or start one -- it is put at once: on bar
-- here, and on sync, which u_song sends on the state bus before it acts (ref/module/songs.md).
local SAVE_EVERY = 100

function StepsLua:postinitialize()
  self.save_clock = Clock:new():register(self, "save_due")
end

function StepsLua:finalize()
  if self.save_clock then self.save_clock:destruct() end
end

-- lua-face.lua's hold: a press's or the phone's save is kept back; the patch's own messages'
-- (a restore's, which is put straight back as u_song expects, ref/module/state.md, and init's)
-- go at once. A bar first puts whatever is held.
function StepsLua:hold(e)
  if e[1] == "save" and self.holding then
    if not self.save_held then
      self.save_held = true
      self.save_clock:delay(SAVE_EVERY)
    end
    return true
  end
  if e[1] == "bar" then self:save_now() end
  return false
end

function StepsLua:save_now()
  if not self.save_held then return end
  self.save_held = false
  self.save_clock:unset()
  local ok, e = pcall(R.save, self.state)
  if ok then self:outlet(3, e[2], e[3]) end
end

function StepsLua:save_due()
  self:save_now()
end

-- After every answer, the phone's state, out the seventh outlet only when it differs from
-- the last one sent: a tick changes nothing the phone shows, eight times a second.
function StepsLua:answered()
  local ok, now = pcall(R.phone, self.state)
  if not ok then return end
  local key = table.concat(now, " ")
  if key ~= self.phone_sent then
    self.phone_sent = key
    self:outlet(7, "list", now)
  end
end

function StepsLua:in_1(sel, atoms)
  self.holding = true
  self:answer(sel, R.presses[sel], self.state, atoms)
  self.holding = false
end

function StepsLua:in_2(sel, atoms)
  if sel == "sync" then return self:save_now() end
  if sel == "restore" then
    -- the pattern is replaced: what was held is the old one's, and u_song's sync put it already
    self.save_held = false
    self.save_clock:unset()
  end
  self:internal(sel, atoms)
end
