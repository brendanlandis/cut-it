-- u_song-lua -- u_song.lua's Pd face, made inside u_song.pd as [u_song-lua $1]. It turns messages
-- into calls on the rules and the rules' answers into outlets, reads the song's two files at the
-- load and writes them when the rules ask: what the store does is in u_song.lua.
-- ref/module/songs.md.
--
-- creation arg: the state directory, u_state's, absolute with no trailing slash: the saved song
-- is cut-it-song.txt there, the draft cut-it-song-draft.txt.
-- inlet 1: u_map's top row and save and revert -- top <1-8>, save, revert.
-- inlet 2: the phone's sections page, through u_net -- select, page, new, up, down, length,
-- delete, name.
-- inlet 3: u_song.pd's own -- put <key> <atoms...> off the state bus, bar from c_steps, start
-- and stop, load at the restore, flush on the draft's timer, init.
-- outlet 1: to g_grid -- top <8 lamps> and unsaved <0 or 1>, each when it changes.
-- outlet 2: the phone's state, R.phone's 22 atoms, when it changes, to u_net.
-- outlet 3: to the state bus: restore <key> <atoms...>, a section starting, and sync before a
-- press, a phone command, start or stop, so a part holding back a put puts it first.
-- outlet 4: err. outlet 5: a bang on init, the proof the Lua loaded.
--
-- A Lua error leaves outlet 4 as fail u_song lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12). A file that can't be written is fail u_song
-- write-failed.

local SongLua = pd.Class:new():register("u_song-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload u_song-lua`) reloads them too, and every object keeps its song.
local R = dofile(SongLua._loadpath .. "u_song.lua")

local OUTLET = { state = 3, err = 4 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(SongLua._loadpath .. "lua-face.lua")
F.carry(SongLua, R, OUTLET, 3, 5)

SongLua.SAVED, SongLua.DRAFT = "cut-it-song.txt", "cut-it-song-draft.txt"

function SongLua:initialize(_, atoms)
  self.inlets, self.outlets = 3, 5
  self.dir = type(atoms[1]) == "string" and atoms[1] or "."
  self.state = R.new()
  return true
end

local function read(path)
  local fh = io.open(path, "r")
  if not fh then return nil end
  local text = fh:read("a")
  fh:close()
  return text
end

-- A file written whole or not at all: into a neighbor, then renamed over it, so a power cut
-- mid-write leaves the last good file.
function SongLua:write(name, text)
  local path = self.dir .. "/" .. name
  local tmp = path .. ".tmp"
  local fh = io.open(tmp, "w")
  local ok = fh and fh:write(text) and fh:close()
  if ok then ok = os.rename(tmp, path) end
  if not ok then
    if fh then os.remove(tmp) end
    self:outlet(4, "fail", { "u_song", "write-failed" })
  end
end

-- After every answer: the top row's lamps, the save and revert lamps and the phone's state, each
-- when it differs from the last sent; and the saved song, when a save asked for it, with the
-- draft beside it, so the two files agree.
function SongLua:answered()
  local st = self.state
  local ok, top = pcall(R.top, st)
  if ok then
    local key = table.concat(top, " ")
    if key ~= self.top_sent then
      self.top_sent = key
      self:outlet(1, "top", top)
    end
  end
  local ok2, unsaved = pcall(R.unsaved, st)
  if ok2 then
    local v = unsaved and 1 or 0
    if v ~= self.unsaved_sent then
      self.unsaved_sent = v
      self:outlet(1, "unsaved", { v })
    end
  end
  local ok3, phone = pcall(R.phone, st)
  if ok3 then
    local parts = {}
    for i, a in ipairs(phone) do parts[i] = R.fmt(a) end
    local key = table.concat(parts, "\1")
    if key ~= self.phone_sent then
      self.phone_sent = key
      self:outlet(2, "list", phone)
    end
  end
  if st.write_saved then
    st.write_saved, st.dirty = false, false
    self:write(SongLua.SAVED, R.text(st.saved))
    self:write(SongLua.DRAFT, R.text(st.song))
  end
end

-- A part may hold its put back while it changes fast: c_steps sends its pattern at most every
-- 100 ms (ref/module/sequencer.md). Anything here that saves, reverts, copies or starts a
-- section needs the latest, so it asks for it first: sync on the state bus, which a holding part
-- answers with its put at once, landing here, in the section still playing, before the press.
function SongLua:sync()
  self:outlet(3, "sync", {})
end

function SongLua:in_1(sel, atoms)
  self:sync()
  self:answer(sel, R.presses[sel], self.state, atoms)
end

function SongLua:in_2(sel, atoms)
  self:sync()
  self:answer(sel, R.phone_cmds[sel], self.state, atoms)
end

-- The load reads both files and hands their text to the rules; the flush writes the draft when
-- it has changed, never before the load has read it (ref/module/state.md, u_state must never
-- write a file it has not yet read).
function SongLua:in_3(sel, atoms)
  local st = self.state
  if sel == "load" then
    local draft = read(self.dir .. "/" .. SongLua.DRAFT)
    local saved = read(self.dir .. "/" .. SongLua.SAVED)
    self:answer("load", R.load, st, draft, saved)
  elseif sel == "flush" then
    if st.loaded and st.dirty then
      st.dirty = false
      local ok, text = pcall(R.text, st.song)
      if ok then self:write(SongLua.DRAFT, text) end
    end
  else
    if sel == "start" or sel == "stop" then self:sync() end
    self:internal(sel, atoms)
  end
end
