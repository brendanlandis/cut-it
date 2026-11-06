-- u_song-lua -- u_song.lua's Pd face, made inside u_song.pd as [u_song-lua $1]. It turns messages
-- into calls on the rules and the rules' answers into outlets, reads the songs' files at the load
-- and writes them when the rules ask: what the store does is in u_song.lua.
-- ref/module/songs.md.
--
-- creation arg: the state directory, u_state's, absolute with no trailing slash: the songs' list
-- and the setlists are cut-it-songs.txt there, and each song is two files, its saved song and its
-- draft, cut-it-song.txt and cut-it-song-draft.txt for song 1 and cut-it-song-<id>.txt and
-- cut-it-song-<id>-draft.txt for the rest (R.files).
-- inlet 1: u_map's top row, save and revert, the Organelle's keys and go -- top <1-8>, save,
-- revert, key <1-25>, go.
-- inlet 2: the phone's sections page, through u_net -- select, page, new, up, down, length,
-- delete, name; and its songs page, songs <command> ... (R.songs_cmds).
-- inlet 3: u_song.pd's own -- put <key> <atoms...> off the state bus, bar and recall <key> from
-- c_steps, start and stop, load at the restore, flush on the draft's timer, init.
-- outlet 1: to g_grid -- top <8 lamps>, unsaved <0 or 1> and go <0, 1 or 2>, each when it
-- changes.
-- outlet 2: to u_net, each when it changes: the sections page's state, R.phone's 22 atoms, as a
-- list, and the songs page's, songs <R.songs_phone's 47 atoms>.
-- outlet 3: to the state bus: restore <key> <atoms...>, a section starting, and sync before a
-- press, a phone command, start or stop, so a part holding back a put puts it first.
-- outlet 4: err. outlet 5: a bang on init, the proof the Lua loaded. outlet 6: a bang to the stop
-- bus, a song starting from silence.
--
-- A Lua error leaves outlet 4 as fail u_song lua-<selector>, and its text goes to Pd's console
-- where there is one: the device has none (C-12). A file that can't be written is fail u_song
-- write-failed.

local SongLua = pd.Class:new():register("u_song-lua")

-- The rules, from the file beside this one, loaded when this file is: a reload of the class
-- (`; pdluax reload u_song-lua`) reloads them too, and every object keeps its songs.
local R = dofile(SongLua._loadpath .. "u_song.lua")

local OUTLET = { state = 3, err = 4, stop = 6 }

-- Answering under pcall, the proof bang on init and the dispatch shortcut are lua-face.lua's,
-- shared by every class that carries rules into Pd.
local F = dofile(SongLua._loadpath .. "lua-face.lua")
F.carry(SongLua, R, OUTLET, 3, 5)

function SongLua:initialize(_, atoms)
  self.inlets, self.outlets = 3, 6
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

-- Both of one song's files, the saved song and the draft, so the two agree.
function SongLua:write_song(id, saved, draft)
  local s, d = R.files(id)
  self:write(s, R.text(saved))
  self:write(d, R.text(draft))
end

local function key(atoms)
  local parts = {}
  for i, a in ipairs(atoms) do parts[i] = R.fmt(a) end
  return table.concat(parts, "\1")
end

-- After every answer: the top row's lamps, the save and revert lamps, the go lamp and the
-- phone's two states, each when it differs from the last sent; the saved song loaded, when a
-- save or a rename asked for it, with the draft beside it, and a new or renamed song's two
-- files; and the files of a song deleted, gone.
function SongLua:answered()
  local st = self.state
  local ok, top = pcall(R.top, st)
  if ok then
    local k = table.concat(top, " ")
    if k ~= self.top_sent then
      self.top_sent = k
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
  local ok4, go = pcall(R.go_lamp, st)
  if ok4 and go ~= self.go_sent then
    self.go_sent = go
    self:outlet(1, "go", { go })
  end
  local ok3, phone = pcall(R.phone, st)
  if ok3 then
    local k = key(phone)
    if k ~= self.phone_sent then
      self.phone_sent = k
      self:outlet(2, "list", phone)
    end
  end
  -- The songs page's state changes with what a put changes only through the song loaded's
  -- unsaved, so a put that leaves that as it was skips it: a knob's sweep puts many.
  if not (self.putting and ok2 and unsaved == self.songs_unsaved) then
    self.songs_unsaved = ok2 and unsaved
    local ok5, songs = pcall(R.songs_phone, st, ok2 and unsaved)
    if ok5 then
      local k = key(songs)
      if k ~= self.songs_sent then
        self.songs_sent = k
        self:outlet(2, "songs", songs)
      end
    end
  end
  if st.write_saved then
    st.write_saved, st.dirty = false, false
    self:write_song(st.cur.id, st.saved, st.song)
  end
  for _, rec in ipairs(st.songs or {}) do
    if rec.write_saved and rec ~= st.cur then
      rec.write_saved, rec.dirty = false, false
      self:write_song(rec.id, rec.saved, rec.song)
    end
  end
  if st.removed and #st.removed > 0 then
    for _, id in ipairs(st.removed) do
      local s, d = R.files(id)
      os.remove(self.dir .. "/" .. s)
      os.remove(self.dir .. "/" .. d)
    end
    st.removed = {}
  end
end

-- A part may hold its put back while it changes fast: c_steps sends its pattern at most every
-- 100 ms (ref/module/sequencer.md). Anything here that saves, reverts, copies, starts a section
-- or loads a song needs the latest, so it asks for it first: sync on the state bus, which a
-- holding part answers with its put at once, landing here, in the section still playing, before
-- the press.
function SongLua:sync()
  self:outlet(3, "sync", {})
end

function SongLua:in_1(sel, atoms)
  self:sync()
  self:answer(sel, R.presses[sel], self.state, atoms)
end

-- The phone's sections page as it comes, and its songs page after songs: the command, then what
-- follows it.
function SongLua:in_2(sel, atoms)
  self:sync()
  if sel == "songs" then
    local rest = {}
    for i = 2, #atoms do rest[#rest + 1] = atoms[i] end
    self:answer("songs", R.songs_cmds[atoms[1]], self.state, rest)
    return
  end
  self:answer(sel, R.phone_cmds[sel], self.state, atoms)
end

-- The load reads the index and every song's files and hands their text to the rules; the flush
-- writes each draft that has changed, and the index, never before the load has read them
-- (ref/module/state.md, u_state must never write a file it has not yet read).
function SongLua:in_3(sel, atoms)
  local st = self.state
  if sel == "load" then
    local index = read(self.dir .. "/" .. R.INDEX)
    local ix = R.parse_index(index)
    local files = {}
    for _, id in ipairs(ix and ix.songs or {}) do
      if id ~= 1 then
        local s, d = R.files(id)
        files[id] = { read(self.dir .. "/" .. d), read(self.dir .. "/" .. s) }
      end
    end
    local s1, d1 = R.files(1)
    self:answer("load", R.load, st, read(self.dir .. "/" .. d1), read(self.dir .. "/" .. s1),
                index, files)
  elseif sel == "flush" then
    if not st.loaded then return end
    if st.dirty then
      st.dirty = false
      local ok, text = pcall(R.text, st.song)
      if ok then self:write(select(2, R.files(st.cur.id)), text) end
    end
    for _, rec in ipairs(st.songs) do
      if rec.dirty and rec ~= st.cur then
        rec.dirty = false
        local ok, text = pcall(R.text, rec.song)
        if ok then self:write(select(2, R.files(rec.id)), text) end
      end
    end
    if st.index_dirty then
      st.index_dirty = false
      local ok, text = pcall(R.index_text, st)
      if ok then self:write(R.INDEX, text) end
    end
  else
    if sel == "start" or sel == "stop" then self:sync() end
    if sel == "bar" and R.moves_at_bar(st) then self:sync() end
    self.putting = sel == "put"
    self:internal(sel, atoms)
    self.putting = false
  end
end
