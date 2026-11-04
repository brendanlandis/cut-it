-- mic-lua -- the Mic Probe's controls and screen. Can an SM58 go straight into the Organelle's
-- input, with the chip's input gain at its top and Pd making up the rest, and be good enough for
-- live vocals (Brendan, 2026-11-04)? main.pd holds the audio; this turns knobs into gains and
-- draws the screen.
--
-- inlet 1: init | knob <n> <0..1> | key <pitch> <velocity> | level <Pd dB> | capture <words...>
-- outlet 1: Pd's gain, linear, to line~. outlet 2: the gate's threshold in Pd dB (100 = full
-- scale), -1 for off, to [>]. outlet 3: the chip's Capture step, 0-15, to mic-capture.sh.
-- outlet 4: open, start or stop, to writesf~. outlets 5-9: a symbol, to screenLine1-5.
--
-- Knob 1: Pd's gain, 0 to +40 dB. Knob 2: the gate, off at the bottom, then -75 to -20 dBFS.
-- Knob 3: the chip's input gain, Capture 0-15 (1.5 dB a step, the -6 dB attenuator off).
-- The lowest C records 10 s of the raw input to /tmp/mic.wav.
--
-- The knobs' positions pushed at load are ignored: the probe starts at 0 dB of Pd gain, the
-- gate off and Capture 15, so a knob left high cannot start a mic at +40 dB into the PA.

local M = pd.Class:new():register("mic-lua")

local function num(x) return type(x) == "number" and x or 0 end

function M:initialize(_, _)
  self.inlets, self.outlets = 1, 9
  self.gain_db, self.gate, self.cap = 0, nil, 15
  self.cap_text = "15"
  self.levels = {}
  self.ready = false
  self.ready_clock = pd.Clock:new():register(self, "arm")
  self.rec_clock = pd.Clock:new():register(self, "rec_stop")
  return true
end

function M:finalize()
  self.ready_clock:destruct()
  self.rec_clock:destruct()
end

function M:line(n, text)
  self:outlet(4 + n, "symbol", { text:sub(1, 21) })
end

function M:send_gain()
  self:outlet(1, "float", { 10 ^ (self.gain_db / 20) })
  self:line(3, string.format("pd gain +%d dB", self.gain_db))
end

function M:send_gate()
  if self.gate then
    self:outlet(2, "float", { self.gate + 100 })
    self:line(4, string.format("gate %d dBFS", self.gate))
  else
    self:outlet(2, "float", { -1 })
    self:line(4, "gate off")
  end
end

function M:send_cap()
  self:outlet(3, "float", { self.cap })
  self:line(5, "capture " .. self.cap .. " ...")
end

function M:arm()
  self.ready = true
end

function M:rec_stop()
  self:outlet(4, "stop", {})
  self:line(1, "MIC PROBE saved")
end

function M:in_1(sel, atoms)
  local ok, err = pcall(function()
    if sel == "init" then
      self:line(1, "MIC PROBE")
      self:line(2, "in --")
      self:send_gain()
      self:send_gate()
      self:send_cap()
      self.ready_clock:delay(1500)
    elseif sel == "knob" then
      if not self.ready then return end
      local n, v = num(atoms[1]), num(atoms[2])
      if n == 1 then
        local db = math.floor(40 * v + 0.5)
        if db ~= self.gain_db then self.gain_db = db; self:send_gain() end
      elseif n == 2 then
        local g = nil
        if v >= 0.03 then g = math.floor(-75 + 55 * v + 0.5) end
        if g ~= self.gate then self.gate = g; self:send_gate() end
      elseif n == 3 then
        local c = math.floor(15 * v + 0.5)
        if c ~= self.cap then self.cap = c; self:send_cap() end
      end
    elseif sel == "level" then
      -- env~ every 8192 samples, about 5 a second: show the loudest of the last second
      local l = self.levels
      l[#l + 1] = num(atoms[1]) - 100
      if #l > 5 then table.remove(l, 1) end
      local top = -100
      for _, x in ipairs(l) do if x > top then top = x end end
      self:line(2, string.format("in %d dBFS", math.floor(top + 0.5)))
    elseif sel == "capture" then
      local words = {}
      for _, a in ipairs(atoms) do words[#words + 1] = tostring(a) end
      self:line(5, "capture " .. table.concat(words, " "))
    elseif sel == "key" then
      if num(atoms[1]) == 60 and num(atoms[2]) > 0 then
        self:outlet(4, "open", { "-bytes", 2, "/tmp/mic.wav" })
        self:outlet(4, "start", {})
        self:line(1, "MIC PROBE rec 10s")
        self.rec_clock:delay(10000)
      end
    end
  end)
  if not ok then
    pd.post("mic-lua: " .. tostring(err))
    self:line(1, "lua error")
  end
end
