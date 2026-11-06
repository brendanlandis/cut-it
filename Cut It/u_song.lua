-- u_song.lua -- the songs: each one's sections, its draft and its saved copy; the one loaded, its
-- section playing and the one queued; the setlists, and the song a key, the next arrow or the phone
-- loads; and the text of their files. Plain Lua with no Pd in it, so
-- test/gate/lua/u_song_test.lua runs it on the Mac with lua.org's interpreter. u_song-lua.pd_lua
-- is its Pd face, which reads and writes the files, and u_song.pd keeps the cords, the state bus,
-- the transport and the draft's timer. ref/module/songs.md.
--
-- A song holds what all its sections share, under each part's key, its voices (put song <key>). A
-- section is its name, its length in bars (0 loops until another is queued) and its parts: what
-- each part of the instrument put while it played, under the part's own key (drums, tempo, synth,
-- velocity, programs), as the atoms it put. The store knows nothing about what a key means, as
-- u_state knows nothing (ref/module/state.md): a part puts `put section <key> <atoms...>` on the
-- state bus, which lands in the playing section, and a section starting sends every part it holds
-- back as `restore <key> <atoms...>`.
--
-- Several songs (Brendan, 2026-11-05), each its own draft: the one loaded is st.song, its saved
-- copy st.saved, and the rules for one song work on those; the rest wait in st.songs, each a
-- record of its draft and its saved copy, until a key or the phone loads one. Setlists are songs
-- in order.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the songs. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"state", "restore", {key, atoms...}}         to the state bus: a section starting
--   {"err", "fail" | "warn" | "info", {"u_song", text}}   to err (C-12)
-- The top row's lamps (R.top), the save and revert lamps (R.unsaved)
-- and the phone's two states (R.phone, R.songs_phone) are worked out from the state after every
-- answer, by the face, and sent when they change; and the face writes the files the state asks
-- for (st.dirty, st.write_saved, and a song's own dirty and write_saved, st.index_dirty,
-- st.removed).

local R = {}

-- The top row (Brendan, 2026-11-02): buttons 1 and 2 the arrows, back and forward a section,
-- 3 to 8 the six section buttons, which scroll a section at a time with the one playing.
R.BUTTONS = 6
-- A top-row button's lamp, as g_grid paints it: dark, a section, the section playing, the
-- section queued (blinking), an arrow that has somewhere to go, the next arrow when that is the next
-- song, blue, and that song queued (blinking) (Brendan, 2026-11-06).
R.DARK, R.SECTION, R.PLAYING, R.QUEUED, R.ARROW, R.NEXT_SONG, R.NEXT_QUEUED = 0, 1, 2, 3, 4, 5, 6
-- The phone's sections tab: five rows to a page (Brendan, 2026-11-05).
R.ROWS = 5
-- A section's length, in bars, each the pattern's loop, the global last step's steps (Brendan,
-- 2026-11-05): 0 loops until another is queued; the phone drags 0 to 64.
R.MAX_LENGTH = 64
-- A name, typed on the phone's keyboard: A to Z, space, - and ', and 0 to 9, lowercase here, at
-- most this long.
R.MAX_NAME = 20
-- With no song saved yet: one section, named so a copy of it is "section 2".
R.SONG, R.FIRST = "song 1", "section 1"
-- The phone's songs tab: six rows to a page; its setlists tab, five (Brendan, 2026-11-05, as
-- drawn). A new setlist is "set 2", and the first "set 1".
R.SONG_ROWS, R.SET_ROWS = 6, 5
R.SET = "set 1"
-- The Organelle's keys, og-key-60 to og-key-84: key N loads the Nth song of the setlist chosen,
-- the lowest the opener, so a setlist holds at most this many.
R.KEYS = 25
local function clip(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

-- A number from a message, as Pd's [f] reads one: a symbol is 0.
local function num(x)
  return type(x) == "number" and x or 0
end

-- An atom as the files write it: a whole number as one, any other with %g, as Pd's own [text]
-- writes a float; a symbol as it is.
function R.fmt(x)
  if type(x) == "number" then
    if x == math.floor(x) and math.abs(x) < 1e15 then return string.format("%d", x) end
    return string.format("%g", x)
  end
  return tostring(x)
end

local function same_atoms(a, b)
  if a == b then return true end
  if #a ~= #b then return false end
  for i = 1, #a do
    if a[i] ~= b[i] then return false end
  end
  return true
end

-- A name from the atoms the phone sent: lowercase, the keyboard's characters only, single spaces,
-- at most R.MAX_NAME long. -> the name, or nil for one with nothing left in it.
function R.clean(atoms)
  local words = {}
  for _, a in ipairs(atoms or {}) do words[#words + 1] = R.fmt(a) end
  local s = table.concat(words, " "):lower()
  s = (s:gsub("[^a-z0-9 '%-]", ""))
  s = (s:gsub("%s+", " "))
  s = (s:gsub("^ ", ""))
  s = (s:sub(1, R.MAX_NAME):gsub(" $", ""))
  if s == "" then return nil end
  return s
end

-- A copy's name (Brendan, 2026-11-05): named after the one it copies, "verse" -> "verse 2", with
-- the first number from 2 that no section of the song has. A copy of "verse 2" is "verse 3". A
-- new song is "song 2" the same way, among the songs' names, and a new setlist "set 2".
function R.copy_name(song, name)
  local names = {}
  for i, s in ipairs(song.sections) do names[i] = s.name end
  return R.next_name(names, name)
end

function R.next_name(names, name)
  local base = name:match("^(.-) %d+$") or name
  local used = {}
  for _, n in ipairs(names) do used[n] = true end
  local n = 2
  while true do
    local suffix = " " .. n
    local cand = (base:sub(1, R.MAX_NAME - #suffix):gsub(" $", "")) .. suffix
    if not used[cand] then return cand end
    n = n + 1
  end
end

-- Parts are copied by reference: a part's atoms are never changed in place, only replaced by a
-- put, so a copy shares what has not changed, and comparing the draft with the saved song is a
-- glance at what has.
local function copy_parts(parts)
  local out = {}
  for k, v in pairs(parts) do out[k] = v end
  return out
end

-- A copy of a song, keeping its sections' ids: the saved song's sections are the draft's, by id.
local function copy_song(song)
  local out = { name = song.name, parts = copy_parts(song.parts or {}), sections = {} }
  for i, s in ipairs(song.sections) do
    out.sections[i] = { id = s.id, name = s.name, length = s.length, parts = copy_parts(s.parts) }
  end
  return out
end

local function section(st, name, length, parts)
  local s = { id = st.next_id, name = name, length = length or 0, parts = parts or {} }
  st.next_id = st.next_id + 1
  return s
end

-- A song's record: its id, which names its files, its draft and its saved copy, and what the
-- face has to write for it. The record of the song loaded holds the same draft and saved copy as
-- st.song and st.saved, but its next section id, and whether its draft or both files are to be
-- written, are st's while it is loaded.
local function record(id, song, saved)
  return { id = id, song = song, saved = saved, next_id = 1, dirty = false, write_saved = false,
           unsaved = false }
end

function R.new()
  local st = { next_id = 1, page = 1, first = 1, bars = 0, running = false, loaded = false,
               dirty = false, write_saved = false, next_song = 2, song_page = 1, set = 1,
               set_page = 1, entry = 1, index_dirty = false, removed = {} }
  local s = section(st, R.FIRST, 0, {})
  st.song = { name = R.SONG, parts = {}, sections = { s } }
  st.playing, st.selected = s, s
  local rec = record(1, st.song, nil)
  st.songs, st.cur, st.sel_song = { rec }, rec, rec
  st.sets = { { name = R.SET, entries = { { song = rec } } } }
  return st
end

-- Where a section is in the song, 1 the first.
function R.index(st, s)
  for i, x in ipairs(st.song.sections) do
    if x == s then return i end
  end
  return nil
end

local function pages(st)
  return math.max(1, math.ceil(#st.song.sections / R.ROWS))
end

-- The page that shows section i.
local function page_of(i)
  return (i - 1) // R.ROWS + 1
end

-- The six buttons' window, moved as little as it can be: the playing section always in it,
-- and a queued one too where both fit.
local function follow(st)
  local n, w = #st.song.sections, R.BUTTONS
  local function show(first, i)
    if i < first then return i end
    if i > first + w - 1 then return i - w + 1 end
    return first
  end
  local p = R.index(st, st.playing)
  local first = show(st.first, p)
  local q = st.queued and R.index(st, st.queued)
  if q then
    local f = show(first, q)
    if p >= f and p <= f + w - 1 then first = f end
  end
  st.first = clip(first, 1, math.max(1, n - w + 1))
end

-- A section starting: it plays, nothing is queued, its bars count from 0, and every part it
-- holds goes back out, in the keys' order, so each part plays what the section saved. A part
-- puts straight back what it restores (ref/module/state.md), and that put lands here, in the
-- section now playing.
-- A part in R.ON_THE_ONE, while the transport runs, waits for the next step 1 (R.one), so it lands
-- on the beat and the old section's last step plays out at its own tempo (Brendan, 2026-11-05).
R.ON_THE_ONE = { tempo = true, programs = true, melody = true, ["melody-2"] = true, tweaks = true }

local function begin(st, s)
  st.playing, st.queued, st.bars = s, nil, 0
  follow(st)
  local keys = {}
  for k in pairs(s.parts) do keys[#keys + 1] = k end
  table.sort(keys)
  local out, held = {}, {}
  -- A section with no controls in play says so, or the last section's would stay.
  if not s.parts.perform then out[1] = { "state", "restore", { "perform" } } end
  -- And whether the voices' sounds snap back or carry on into it (Brendan, 2026-11-06), snap back unless
  -- it says.
  if not s.parts.tweaks then
    local e = { "state", "restore", { "tweaks", 0 } }
    if st.running then held[1] = e else out[#out + 1] = e end
  end
  for _, k in ipairs(keys) do
    local a = { k }
    for _, x in ipairs(s.parts[k]) do a[#a + 1] = x end
    local e = { "state", "restore", a }
    if st.running and R.ON_THE_ONE[k] then held[#held + 1] = e else out[#out + 1] = e end
  end
  st.on_one = held
  return out
end

-- What the song holds for all its sections, as begin sends a section's, and before it, so a section
-- starts on its song's voices: the voices first, for what follows them; each of these always, so a song
-- that has none says so, and is given some.
R.SONG_PARTS = { "voices", "patches", "sounds", "kit" }
local function song_parts(st, after)
  local parts = st.song.parts or {}
  local out, known = {}, {}
  for _, k in ipairs(R.SONG_PARTS) do
    known[k] = true
    local a = { k }
    for _, x in ipairs(parts[k] or {}) do a[#a + 1] = x end
    out[#out + 1] = { "state", "restore", a }
  end
  local keys = {}
  for k in pairs(parts) do
    if not known[k] then keys[#keys + 1] = k end
  end
  table.sort(keys)
  for _, k in ipairs(keys) do
    local a = { k }
    for _, x in ipairs(parts[k]) do a[#a + 1] = x end
    out[#out + 1] = { "state", "restore", a }
  end
  for _, e in ipairs(after) do out[#out + 1] = e end
  return out
end

-- The next step 1 after a bar, from c_steps: what begin held for it.
function R.one(st)
  local out = st.on_one or {}
  st.on_one = nil
  return out
end

-- A report on err, C-12: one symbol of 21 characters or fewer.
local function report(level, text)
  return { "err", level, { "u_song", string.sub(text, 1, 21) } }
end
function R.fail(text) return report("fail", text) end

-- ------------------------------------------------------------------ the draft and the saved song

-- True when the draft differs from the saved song: its name, its sections' order, a section's
-- name, length or parts. Nothing is unsaved before the files are read.
function R.unsaved(st)
  if not st.loaded or not st.saved then return false end
  return R.differs(st.song, st.saved)
end

-- True when a draft differs from its saved copy, as R.unsaved has it.
function R.differs(a, b)
  if not b then return false end
  if a.name ~= b.name or #a.sections ~= #b.sections then return true end
  local ap, bp = a.parts or {}, b.parts or {}
  for k, v in pairs(ap) do
    if not bp[k] or not same_atoms(v, bp[k]) then return true end
  end
  for k in pairs(bp) do
    if not ap[k] then return true end
  end
  for i, s in ipairs(a.sections) do
    local t = b.sections[i]
    if s.id ~= t.id or s.name ~= t.name or s.length ~= t.length then return true end
    for k, v in pairs(s.parts) do
      local w = t.parts[k]
      if not w or not same_atoms(v, w) then return true end
      -- Equal, so they share one table from here on, and the next look is a glance. The draft and
      -- the save come from two files, so nothing shared at load, and this ran on every message,
      -- every number of every section (2026-11-05). Atoms are never changed in place.
      s.parts[k] = w
    end
    for k in pairs(t.parts) do
      if not s.parts[k] then return true end
    end
  end
  return false
end

-- A part's put to the song itself, `put song <key> <atoms...>`: what every section shares.
function R.put_song(st, atoms)
  local key = atoms[1]
  if type(key) ~= "string" then return { R.fail("bad-put") } end
  local a = {}
  for i = 2, #atoms do a[#a + 1] = atoms[i] end
  st.song.parts = st.song.parts or {}
  local cur = st.song.parts[key]
  if cur and same_atoms(cur, a) then return {} end
  st.song.parts[key] = a
  st.dirty = true
  return {}
end

-- `put seed <key> <atoms...>`: what a song that holds none starts as, a song's from before there were
-- any. It is no change to the song, so it goes into what's saved too, and shows as nothing unsaved.
function R.seed_song(st, atoms)
  local key = atoms[1]
  if type(key) ~= "string" then return { R.fail("bad-put") } end
  local a = {}
  for i = 2, #atoms do a[#a + 1] = atoms[i] end
  st.song.parts = st.song.parts or {}
  st.song.parts[key] = a
  if st.saved then
    st.saved.parts = st.saved.parts or {}
    st.saved.parts[key] = { table.unpack(a) }
    st.write_saved = true
  end
  st.dirty = true
  return {}
end

-- A part's put, `put <key> <atoms...>`: into the playing section. The same atoms again change
-- nothing, so a part putting back what it restored leaves the song as it was.
function R.put(st, atoms)
  local key = atoms[1]
  if type(key) ~= "string" then return { R.fail("bad-put") } end
  -- Each atom as the store keeps it: a number read back from how it would be written, so a value
  -- that came from Pd, a 32-bit float, compares equal to the same value read from a file. A
  -- whole number is written as itself, so it is kept as it came, without the round trip through
  -- text: nearly every number in a drum pattern is whole, and formatting all 581 on every put
  -- took about 5 ms on the Organelle, longer than its 6 ms audio buffer allows beside the rest,
  -- so a drag on the phone crackled (2026-11-05). Written out, not a function per atom: the
  -- calls cost 40% more there.
  local a, k = {}, 0
  for i = 2, #atoms do
    local x = atoms[i]
    if type(x) ~= "number" then
      x = tostring(x)
    elseif x % 1 ~= 0 or x >= 1e15 or x <= -1e15 then
      x = tonumber(string.format("%g", x))
    end
    if x ~= nil then
      k = k + 1
      a[k] = x
    end
  end
  local cur = st.playing.parts[key]
  if cur and same_atoms(cur, a) then return {} end
  st.playing.parts[key] = a
  st.dirty = true
  return {}
end

-- Save, the upper bottom row's rightmost button (CC 108): the draft becomes the saved song,
-- written at once, both files. Nothing to save, nothing happens.
function R.save(st)
  if not R.unsaved(st) then return {} end
  st.saved = copy_song(st.song)
  st.cur.saved = st.saved
  st.write_saved, st.dirty = true, true
  return { report("info", "saved") }
end

-- Revert, the lowest row's rightmost (CC 8): every section back to the last save, at once. The
-- section playing plays on as it was saved, or the one now in its place if it was new; the one
-- selected on the phone stays selected the same way.
function R.revert(st)
  if not R.unsaved(st) then return {} end
  local pi, si = R.index(st, st.playing), R.index(st, st.selected)
  local p, s = st.playing.id, st.selected.id
  st.song = copy_song(st.saved)
  st.cur.song = st.song
  local function find(id, i)
    for _, x in ipairs(st.song.sections) do
      if x.id == id then return x end
    end
    return st.song.sections[math.min(i, #st.song.sections)]
  end
  st.selected = find(s, si)
  st.page = page_of(R.index(st, st.selected))
  st.dirty = true
  local out = song_parts(st, begin(st, find(p, pi)))
  table.insert(out, 1, report("info", "reverted"))
  return out
end

-- A part asked to go back to what the section playing holds as saved (Brendan, 2026-11-05: pad-38,
-- for the tempo): the saved song's copy of it, or for a section never saved, or a part its save did
-- not hold, the draft's. It goes back out as a section starting sends it, restore <key> <atoms...>,
-- to whichever part it is: the store still knows nothing of what a key means, and the part puts
-- back what it restores, as ever, so what comes back is in the draft like any change.
function R.recall(st, key)
  local a
  for _, s in ipairs(st.saved and st.saved.sections or {}) do
    if s.id == st.playing.id then a = s.parts[key] end
  end
  a = a or st.playing.parts[key]
  if not a then return {} end
  local m = { key }
  for _, x in ipairs(a) do m[#m + 1] = x end
  return { { "state", "restore", m } }
end

-- ------------------------------------------------------------------ the files
-- One file per song, a line a record, as Pd's [text] writes with -c and as plain text anyone can
-- read or edit:
--   song <name>
--   section <id> <length> <name>
--   <key> <atoms...>                  every part of the section above it, one line each
-- A name runs to the end of its line. The draft, written as it changes, and the saved song are
-- two files of the same shape.

-- A part's line, kept against its atoms: a part is never changed in place, so a line already
-- built for these atoms is still the line.
local lines = setmetatable({}, { __mode = "k" })
local function part_line(key, a)
  local cached = lines[a]
  if cached and cached[1] == key then return cached[2] end
  local words = { key }
  for _, x in ipairs(a) do words[#words + 1] = R.fmt(x) end
  local line = table.concat(words, " ")
  lines[a] = { key, line }
  return line
end

function R.text(song)
  local out = { "song " .. song.name }
  local shared = {}
  for k in pairs(song.parts or {}) do shared[#shared + 1] = k end
  table.sort(shared)
  for _, k in ipairs(shared) do out[#out + 1] = part_line(k, song.parts[k]) end
  for _, s in ipairs(song.sections) do
    out[#out + 1] = string.format("section %d %d %s", s.id, s.length, s.name)
    local keys = {}
    for k in pairs(s.parts) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do out[#out + 1] = part_line(k, s.parts[k]) end
  end
  return table.concat(out, "\n") .. "\n"
end

-- A file's text as a song, or nil when there is none in it: no song line, or no section. A
-- section with no id, or one another section has, takes a new one; a length off 0 to 64 is
-- clipped; a name with nothing in it is the first section's.
function R.parse(text)
  if type(text) ~= "string" then return nil end
  local song, cur = nil, nil
  for line in text:gmatch("[^\r\n]+") do
    local words = {}
    for w in line:gmatch("%S+") do words[#words + 1] = w end
    local k = words[1]
    if k == "song" then
      song = { name = R.clean({ table.unpack(words, 2) }) or R.SONG, parts = {}, sections = {} }
      cur = nil
    elseif k == "section" and song then
      cur = { id = tonumber(words[2]), length = math.floor(clip(tonumber(words[3]) or 0, 0,
              R.MAX_LENGTH)), name = R.clean({ table.unpack(words, 4) }) or R.FIRST, parts = {} }
      song.sections[#song.sections + 1] = cur
    elseif k and cur then
      local a = {}
      for i = 2, #words do a[#a + 1] = tonumber(words[i]) or words[i] end
      cur.parts[k] = a
    elseif k and song then
      local a = {}
      for i = 2, #words do a[#a + 1] = tonumber(words[i]) or words[i] end
      song.parts[k] = a
    end
  end
  if not song or #song.sections == 0 then return nil end
  return song
end

-- Every section an id of its own, whole, and next_id past them all, in the draft and the saved
-- song together: a section in both is the same section.
local function number(songs)
  local seen, top = {}, 0
  for _, song in ipairs(songs) do
    local mine = {}
    for _, s in ipairs(song.sections) do
      local id = s.id
      if type(id) ~= "number" or id < 1 or id ~= math.floor(id) or mine[id] then
        s.id = nil
      else
        mine[id], seen[id] = true, true
        if id > top then top = id end
      end
    end
  end
  local next_id = top + 1
  for _, song in ipairs(songs) do
    for _, s in ipairs(song.sections) do
      if not s.id then s.id = next_id; next_id = next_id + 1 end
    end
  end
  return next_id
end

-- Where the draft and the saved song hold equal parts, one table: comparing them is then a
-- glance (R.unsaved), until a put replaces one.
local function share(song, saved)
  local by = {}
  for _, s in ipairs(saved.sections) do by[s.id] = s end
  for _, s in ipairs(song.sections) do
    local t = by[s.id]
    if t then
      for k, v in pairs(s.parts) do
        local w = t.parts[k]
        if w and same_atoms(v, w) then s.parts[k] = w end
      end
    end
  end
end

-- One song's two files as a record: the draft and the saved song, either missing made from the
-- other, its sections numbered across both, and their equal parts one table. nil when neither
-- holds a song. A draft missing is to be written, and with the saved song missing both are.
local function read_song(id, draft_text, saved_text)
  local draft, saved = R.parse(draft_text), R.parse(saved_text)
  if not draft and not saved then return nil end
  local read = {}
  if draft then read[#read + 1] = draft end
  if saved then read[#read + 1] = saved end
  local rec = record(id, nil, nil)
  rec.next_id = number(read)
  rec.song = draft or copy_song(saved)
  rec.saved = saved or copy_song(rec.song)
  share(rec.song, rec.saved)
  rec.dirty = draft == nil
  rec.write_saved = saved == nil
  rec.unsaved = R.differs(rec.song, rec.saved)
  return rec
end

-- The songs' list and the setlists, cut-it-songs.txt: a line a record, as plain text anyone can
-- read or edit.
--   next <id>                 the id the next new song takes
--   current <id>              the song loaded, which loads again at the next load
--   chosen <n>                the setlist chosen, the one the keys play, 1 the first
--   song <id>                 a song, in the songs tab's order: its files are named for its id
--   set <name>                a setlist, its name to the end of the line, then its entries:
--   entry <song id>           a song of it, in order
function R.index_text(st)
  local out = { "next " .. st.next_song, "current " .. st.cur.id, "chosen " .. st.set }
  for _, rec in ipairs(st.songs) do out[#out + 1] = "song " .. rec.id end
  for _, set in ipairs(st.sets) do
    out[#out + 1] = "set " .. set.name
    for _, e in ipairs(set.entries) do
      out[#out + 1] = "entry " .. e.song.id
    end
  end
  return table.concat(out, "\n") .. "\n"
end

-- The index's text as { next, current, chosen, songs = {ids}, sets = {{name, entries}} }, or nil
-- when there is none: no song line. A song named twice is once; an entry's words after its id,
-- how it once started, are left; a set with no name is set 1.
function R.parse_index(text)
  if type(text) ~= "string" then return nil end
  local ix = { songs = {}, sets = {} }
  local seen = {}
  for line in text:gmatch("[^\r\n]+") do
    local words = {}
    for w in line:gmatch("%S+") do words[#words + 1] = w end
    local k, n = words[1], tonumber(words[2])
    if k == "next" or k == "current" or k == "chosen" then
      ix[k] = n
    elseif k == "song" and n and n >= 1 and n == math.floor(n) and not seen[n] then
      seen[n] = true
      ix.songs[#ix.songs + 1] = n
    elseif k == "set" then
      local name = R.clean({ table.unpack(words, 2) }) or R.SET
      ix.sets[#ix.sets + 1] = { name = name, entries = {} }
    elseif k == "entry" and n and #ix.sets > 0 then
      local es = ix.sets[#ix.sets].entries
      es[#es + 1] = { id = n }
    end
  end
  if #ix.songs == 0 then return nil end
  return ix
end

-- Where a song's files are: song 1's keep the names the one song had before there were several,
-- so a state directory from then is song 1's as it stands; each other's are named for its id.
-- -> the saved song's file, the draft's.
function R.files(id)
  if id == 1 then return "cut-it-song.txt", "cut-it-song-draft.txt" end
  return "cut-it-song-" .. id .. ".txt", "cut-it-song-" .. id .. "-draft.txt"
end
R.INDEX = "cut-it-songs.txt"

-- The song loaded: its draft and saved copy are st's, its next section id and what is to be
-- written for it too, and the record keeps them while another is loaded.
local function take(st, rec)
  st.cur = rec
  st.song, st.saved, st.next_id = rec.song, rec.saved, rec.next_id
  st.dirty, st.write_saved = rec.dirty, rec.write_saved
  rec.dirty, rec.write_saved = false, false
end

local function leave(st)
  local old = st.cur
  old.song, old.saved, old.next_id = st.song, st.saved, st.next_id
  old.dirty = old.dirty or st.dirty
  old.write_saved = old.write_saved or st.write_saved
  old.unsaved = R.differs(st.song, st.saved)
  st.dirty, st.write_saved = false, false
end

-- The files, read at load (~3.5 s, after u_state's restore): the index, and each song's draft and
-- saved song, song 1's as draft_text and saved_text and the rest in files, { [id] = {draft,
-- saved} }. With no index, the one song before there were several: song 1, from its two files,
-- either missing made from the other, and with neither the one section the parts have put into
-- since load, saved as it is, so a fresh load has one section and nothing to save; and one
-- setlist, song 1 its opener. A song the index names with neither file is gone. Then the song
-- loaded last starts at section 1, and the files missing are written.
function R.load(st, draft_text, saved_text, index_text, files)
  local ix = R.parse_index(index_text)
  files = files or {}
  local recs, by = {}, {}
  if ix then
    for _, id in ipairs(ix.songs) do
      local f = id == 1 and { draft_text, saved_text } or files[id] or {}
      local rec = read_song(id, f[1], f[2])
      if rec then
        recs[#recs + 1], by[id] = rec, rec
      end
    end
  end
  if #recs == 0 then
    local rec = read_song(1, draft_text, saved_text)
    if not rec then
      rec = record(1, st.song, copy_song(st.song))
      rec.next_id = number({ st.song })
      rec.dirty, rec.write_saved = false, true
    end
    recs, by = { rec }, { [1] = rec }
    ix = nil
  end
  st.songs = recs
  local top = 0
  for _, rec in ipairs(recs) do top = math.max(top, rec.id) end
  st.next_song = math.max(ix and ix.next or 0, top + 1)
  st.sets = {}
  for _, set in ipairs(ix and ix.sets or {}) do
    local es = {}
    for _, e in ipairs(set.entries) do
      if by[e.id] and #es < R.KEYS then es[#es + 1] = { song = by[e.id] } end
    end
    st.sets[#st.sets + 1] = { name = set.name, entries = es }
  end
  if #st.sets == 0 then
    st.sets[1] = { name = R.SET, entries = { { song = recs[1] } } }
  end
  st.set = math.floor(clip(ix and ix.chosen or 1, 1, #st.sets))
  st.set_page, st.entry = 1, #st.sets[st.set].entries > 0 and 1 or 0
  st.index_dirty = ix == nil or #recs < #ix.songs
  st.removed = {}
  local cur = ix and by[ix.current] or recs[1]
  take(st, cur)
  st.sel_song, st.song_page = cur, 1
  st.pending = nil
  st.loaded = true
  st.selected, st.page, st.first = st.song.sections[1], 1, 1
  return song_parts(st, begin(st, st.song.sections[1]))
end

-- ------------------------------------------------------------------ playing the song

-- Go to a section: at once while the transport is stopped, else queued for the next bar. While
-- stopped, the section playing again is nothing to do.
function R.go(st, s)
  if not st.running then
    if s == st.playing then return {} end
    return begin(st, s)
  end
  st.queued = s
  follow(st)
  return {}
end

-- The entry of the setlist chosen after the song loaded, or nil on its last, or for a song not in
-- it: the entry a key or the arrow loaded it from, else the first that names it, so a song in a
-- setlist twice goes on from where it was.
local function next_entry(st)
  local es = st.sets[st.set].entries
  local at = st.at_entry
  if not (at and es[at] and es[at].song == st.cur) then
    at = nil
    for i, e in ipairs(es) do
      if e.song == st.cur then
        at = i
        break
      end
    end
  end
  if not at or not es[at + 1] then return nil end
  return at + 1
end

-- A top-row button, 1 to 8: back and forward one section from the one queued, or the one playing;
-- or the section a button shows. A button with no section does nothing. Forward from the last
-- section is the next song of the setlist (Brendan, 2026-11-06), and back takes back a song queued.
function R.press(st, n)
  local b = math.floor(num(n))
  local count = #st.song.sections
  local at = R.index(st, st.queued or st.playing)
  local target
  if b == 1 then
    if st.pending then
      st.pending = nil
      return {}
    end
    target = at - 1
  elseif b == 2 then
    target = at + 1
    if target > count then
      local k = next_entry(st)
      if not k or st.pending then return {} end
      st.at_entry = k
      return R.ask(st, st.sets[st.set].entries[k].song)
    end
  elseif b >= 3 and b <= 2 + R.BUTTONS then
    target = st.first + b - 3
  else
    return { R.fail("bad-button") }
  end
  if target < 1 or target > count then return {} end
  return R.go(st, st.song.sections[target])
end

-- The end of a bar, from c_steps. A bar is the pattern's loop (Brendan, 2026-11-05): the global
-- last step has just played, and the global loop comes round to its step 1 next, so the whole
-- pattern has played. A song queued for the next bar loads, its section 1 starting; else a queued
-- section starts; else a section with a length that has played its bars hands over to the next. The last section with a length has no next, and plays on as a
-- loop, until another is queued.
-- Whether this bar starts another section or song. c_melody puts its drifting loops only when asked,
-- so the face asks before one does.
function R.moves_at_bar(st)
  if st.pending or st.queued then return true end
  local len = st.playing.length
  return len > 0 and st.bars + 1 >= len and st.song.sections[R.index(st, st.playing) + 1] ~= nil
end

function R.bar(st)
  st.bars = st.bars + 1
  if st.pending then return R.load_now(st, st.pending.rec) end
  if st.queued then return begin(st, st.queued) end
  local len = st.playing.length
  if len > 0 and st.bars >= len then
    local nxt = st.song.sections[R.index(st, st.playing) + 1]
    if nxt then return begin(st, nxt) end
  end
  return {}
end

-- PLAY: the section playing counts its bars from the pattern's step 1.
function R.start(st)
  st.running, st.bars = true, 0
  return R.one(st)
end

-- STOP and panic: no next bar is coming, so a song queued loads now, and else a section queued
-- starts now.
function R.stop(st)
  st.running = false
  if st.pending then return R.load_now(st, st.pending.rec) end
  if st.queued then return begin(st, st.queued) end
  return R.one(st)
end

-- The top row's eight lamps: the arrows, lit when there is a section that way from the one
-- queued, or the one playing; forward, past the last section, blue for the setlist's next song, and
-- blinking whenever a song is queued, which back takes back; then the six buttons' sections.
function R.top(st)
  local n = #st.song.sections
  local p = R.index(st, st.playing)
  local q = st.queued and R.index(st, st.queued)
  local at = q or p
  local forward = R.DARK
  if st.pending then
    forward = R.NEXT_QUEUED
  elseif at < n then
    forward = R.ARROW
  elseif next_entry(st) then
    forward = R.NEXT_SONG
  end
  local out = { (at > 1 or st.pending) and R.ARROW or R.DARK, forward }
  for k = 1, R.BUTTONS do
    local i = st.first + k - 1
    local v = R.DARK
    if i == q then
      v = R.QUEUED
    elseif i == p then
      v = R.PLAYING
    elseif i <= n then
      v = R.SECTION
    end
    out[#out + 1] = v
  end
  return out
end

-- ------------------------------------------------------------------ the sections page (7)

-- The phone's sections tab: the song's name, how many sections, the one selected, the page and
-- how many, the selected one's name and length; then five rows, each a section's number, name
-- and length, 0 - 0 for a row with none. 22 atoms.
R.PHONE = 7 + 3 * R.ROWS
function R.phone(st)
  local secs = st.song.sections
  local np = pages(st)
  local page = clip(st.page, 1, np)
  local out = { st.song.name, #secs, R.index(st, st.selected), page, np, st.selected.name,
                st.selected.length }
  for r = 1, R.ROWS do
    local i = (page - 1) * R.ROWS + r
    local s = secs[i]
    local row = s and { i, s.name, s.length } or { 0, "-", 0 }
    for _, a in ipairs(row) do out[#out + 1] = a end
  end
  return out
end

-- A row tapped: that section selected for editing. Playing it stays the top row's.
function R.select(st, n)
  local s = st.song.sections[math.floor(num(n))]
  if not s then return {} end
  st.selected = s
  return {}
end

-- The pager's arrows: a page back or on.
function R.turn(st, d)
  st.page = clip(clip(st.page, 1, pages(st)) + (num(d) < 0 and -1 or 1), 1, pages(st))
  return {}
end

-- new: a copy of the selected section, after it, named after it, and selected.
function R.add(st)
  local src = st.selected
  local i = R.index(st, src)
  local s = section(st, R.copy_name(st.song, src.name), src.length, copy_parts(src.parts))
  table.insert(st.song.sections, i + 1, s)
  st.selected, st.page = s, page_of(i + 1)
  follow(st)
  st.dirty = true
  return {}
end

-- save as new (Brendan, 2026-11-06): what is playing, as it stands now, becomes a new section after the
-- one it was, which goes back to what it holds as saved, so playing around leaves it as it was. Nothing
-- heard changes: the new section just takes over, and is selected. A section never saved has nothing to go
-- back to, and keeps what it has.
function R.save_new(st)
  local src = st.playing
  local i = R.index(st, src)
  local s = section(st, R.copy_name(st.song, src.name), src.length, copy_parts(src.parts))
  table.insert(st.song.sections, i + 1, s)
  for _, t in ipairs(st.saved and st.saved.sections or {}) do
    if t.id == src.id then src.parts = copy_parts(t.parts) end
  end
  st.playing, st.selected, st.page = s, s, page_of(i + 1)
  follow(st)
  st.dirty = true
  return {}
end

-- move up and move down: the selected section a place earlier or later, still selected.
local function move(st, d)
  local secs = st.song.sections
  local i = R.index(st, st.selected)
  local j = i + d
  if j < 1 or j > #secs then return {} end
  secs[i], secs[j] = secs[j], secs[i]
  st.page = page_of(j)
  follow(st)
  st.dirty = true
  return {}
end
function R.up(st) return move(st, -1) end
function R.down(st) return move(st, 1) end

-- The selected section's length, as it stands: 0 loops, else bars, up to R.MAX_LENGTH.
function R.length(st, v)
  if type(v) ~= "number" then return {} end
  local n = math.floor(clip(v, 0, R.MAX_LENGTH) + 0.5)
  if n == st.selected.length then return {} end
  st.selected.length = n
  st.dirty = true
  return {}
end

-- delete: the selected section goes, and the one now in its place is selected. A song keeps one
-- section at least. Deleting the section playing starts the one now in its place, at once.
function R.delete(st)
  local secs = st.song.sections
  if #secs == 1 then return { report("warn", "last-section") } end
  local i = R.index(st, st.selected)
  local gone = table.remove(secs, i)
  local k = math.min(i, #secs)
  st.selected, st.page = secs[k], page_of(k)
  if st.queued == gone then st.queued = nil end
  st.dirty = true
  if st.playing == gone then return begin(st, secs[k]) end
  follow(st)
  return {}
end

-- The name tab's done: the selected section renamed. A name with nothing in it, once cleaned,
-- changes nothing.
function R.rename(st, atoms)
  local name = R.clean(atoms)
  if not name or name == st.selected.name then return {} end
  st.selected.name = name
  st.dirty = true
  return {}
end

-- ------------------------------------------------------------------ songs and setlists

local function find(list, x)
  for i, y in ipairs(list) do
    if y == x then return i end
  end
  return nil
end

local function song_pages(st)
  return math.max(1, math.ceil(#st.songs / R.SONG_ROWS))
end

local function set_pages(set)
  return math.max(1, math.ceil(#set.entries / R.SET_ROWS))
end

-- The log's line for a song loaded: its name, a word, in the 21 characters C-12 allows. info
-- draws nothing on the OLED, which is for alerts and warnings (ref/module/error.md).
local function loaded(rec)
  return report("info", "loaded-" .. rec.song.name:gsub(" ", "-"))
end

-- A song loaded now: the one loaded keeps its draft as it stands, unsaved changes and all, and
-- the song taken up starts at its section 1, as a load at power-up does, with its own draft. The
-- song loaded, loaded again, starts again at its section 1.
function R.load_now(st, rec)
  st.pending, st.queued = nil, nil
  if rec ~= st.cur then
    leave(st)
    take(st, rec)
    st.index_dirty = true
    st.selected, st.page, st.first = st.song.sections[1], 1, 1
    local out = song_parts(st, begin(st, st.song.sections[1]))
    table.insert(out, 1, loaded(rec))
    return out
  end
  return begin(st, st.song.sections[1])
end

-- A song asked for (Brendan, 2026-11-06). Stopped, it loads at once; the song loaded, at its section
-- 1 already, is nothing to do. Playing, it waits for the pattern coming round, as a queued section,
-- the last song playing until then. One song is queued at a time: another asked for takes its place.
function R.ask(st, rec)
  if not st.running then
    st.pending = nil
    if rec == st.cur and st.playing == st.song.sections[1] and not st.queued then return {} end
    return R.load_now(st, rec)
  end
  st.pending = { rec = rec }
  return {}
end

-- An Organelle key, key <n>, 1 the lowest (Brendan, 2026-11-05): the nth song of the setlist
-- chosen. A key past the setlist's end does nothing.
function R.key(st, n)
  local k = math.floor(num(n))
  local e = st.sets[st.set].entries[k]
  if not e then return {} end
  st.at_entry = k
  return R.ask(st, e.song)
end

-- ---- the songs tab

-- A row tapped: the nth song selected, for load, name, add to set and delete.
function R.song_select(st, n)
  local rec = st.songs[math.floor(num(n))]
  if rec then st.sel_song = rec end
  return {}
end

function R.song_turn(st, d)
  st.song_page = clip(clip(st.song_page, 1, song_pages(st)) + (num(d) < 0 and -1 or 1), 1,
                      song_pages(st))
  return {}
end

-- load: the selected song.
function R.song_load(st)
  return R.ask(st, st.sel_song)
end

-- new song: one section, a copy of the section playing, after the selected song, named "song
-- 2", the first number from 2 no song has, and selected; saved as it is, so there is nothing to
-- save. Not loaded: load does that.
function R.song_new(st)
  local p = st.playing
  local s = { id = 1, name = p.name, length = p.length, parts = copy_parts(p.parts) }
  local names = {}
  for i, rec in ipairs(st.songs) do names[i] = rec.song.name end
  local song = { name = R.next_name(names, "song"), parts = copy_parts(st.song.parts or {}),
                 sections = { s } }
  local rec = record(st.next_song, song, copy_song(song))
  rec.next_id, rec.write_saved = 2, true
  st.next_song = st.next_song + 1
  local i = find(st.songs, st.sel_song) + 1
  table.insert(st.songs, i, rec)
  st.sel_song, st.song_page = rec, (i - 1) // R.SONG_ROWS + 1
  st.index_dirty = true
  return {}
end

-- The name tab's done, from the songs tab: the selected song renamed. A song's name is what it
-- is called, not a change to it: the draft and the saved song both take it, at once, so it
-- leaves nothing to save.
function R.song_rename(st, atoms)
  local name = R.clean(atoms)
  local rec = st.sel_song
  if not name or name == rec.song.name then return {} end
  rec.song.name = name
  if rec.saved then rec.saved.name = name end
  if rec == st.cur then st.write_saved = true else rec.write_saved = true end
  return {}
end

-- add to set: the selected song, the setlist's last entry, and selected.
-- A setlist holds as many songs as there are keys.
function R.song_add(st)
  local set = st.sets[st.set]
  if #set.entries >= R.KEYS then return { report("warn", "set-full") } end
  set.entries[#set.entries + 1] = { song = st.sel_song }
  st.entry = #set.entries
  st.set_page = (st.entry - 1) // R.SET_ROWS + 1
  st.index_dirty = true
  return {}
end

-- delete: the selected song goes, out of every setlist, its files with it, and the one now in
-- its place is selected. There is always a song: the last is warn u_song last-song. Deleting the
-- song loaded loads the one now in its place, at once, as deleting the section playing starts
-- the one in its place.
function R.song_delete(st)
  if #st.songs == 1 then return { report("warn", "last-song") } end
  local i = find(st.songs, st.sel_song)
  local gone = table.remove(st.songs, i)
  for _, set in ipairs(st.sets) do
    for j = #set.entries, 1, -1 do
      if set.entries[j].song == gone then table.remove(set.entries, j) end
    end
  end
  local es = st.sets[st.set].entries
  st.entry = math.min(st.entry, #es)
  if st.entry == 0 and #es > 0 then st.entry = 1 end
  st.set_page = clip(st.set_page, 1, set_pages(st.sets[st.set]))
  if st.pending and st.pending.rec == gone then st.pending = nil end
  st.removed[#st.removed + 1] = gone.id
  st.index_dirty = true
  local k = math.min(i, #st.songs)
  st.sel_song, st.song_page = st.songs[k], (k - 1) // R.SONG_ROWS + 1
  if gone == st.cur then
    st.pending, st.queued = nil, nil
    take(st, st.songs[k])
    st.selected, st.page, st.first = st.song.sections[1], 1, 1
    local out = begin(st, st.song.sections[1])
    table.insert(out, 1, loaded(st.cur))
    return out
  end
  return {}
end

-- ---- the setlists tab

-- A row tapped: the nth entry of the setlist selected, for move up, move down and remove.
function R.entry_select(st, n)
  local k = math.floor(num(n))
  if st.sets[st.set].entries[k] then st.entry = k end
  return {}
end

-- The arrows page between setlists (Brendan, 2026-11-05): through a setlist's own pages first,
-- where it has more entries than rows, and on into the next. The setlist showing is the one
-- chosen, which the keys play.
function R.set_turn(st, d)
  local set = st.sets[st.set]
  local p = clip(st.set_page, 1, set_pages(set))
  local was = st.set
  if num(d) < 0 then
    if p > 1 then
      st.set_page = p - 1
    elseif st.set > 1 then
      st.set = st.set - 1
      st.set_page = set_pages(st.sets[st.set])
    end
  else
    if p < set_pages(set) then
      st.set_page = p + 1
    elseif st.set < #st.sets then
      st.set, st.set_page = st.set + 1, 1
    end
  end
  if st.set ~= was then
    local es = st.sets[st.set].entries
    st.entry = #es > 0 and math.min(#es, (st.set_page - 1) * R.SET_ROWS + 1) or 0
    st.index_dirty = true
  end
  return {}
end

-- move up and move down: the selected entry a place earlier or later, its key with it.
local function move_entry(st, d)
  local es = st.sets[st.set].entries
  local i = st.entry
  local j = i + d
  if not es[i] or j < 1 or j > #es then return {} end
  es[i], es[j] = es[j], es[i]
  st.entry, st.set_page = j, (j - 1) // R.SET_ROWS + 1
  st.index_dirty = true
  return {}
end

-- remove: the selected entry out of the setlist, and the one now in its place selected.
function R.entry_remove(st)
  local es = st.sets[st.set].entries
  if not es[st.entry] then return {} end
  table.remove(es, st.entry)
  st.entry = math.min(st.entry, #es)
  st.set_page = clip(st.set_page, 1, set_pages(st.sets[st.set]))
  st.index_dirty = true
  return {}
end

-- new set: an empty setlist after the one chosen, "set 2" as songs are "song 2", and chosen.
function R.set_new(st)
  local names = {}
  for i, set in ipairs(st.sets) do names[i] = set.name end
  table.insert(st.sets, st.set + 1, { name = R.next_name(names, "set"), entries = {} })
  st.set, st.set_page, st.entry = st.set + 1, 1, 0
  st.index_dirty = true
  return {}
end

-- The name tab's done, from the setlists tab: the setlist chosen renamed.
function R.set_rename(st, atoms)
  local name = R.clean(atoms)
  local set = st.sets[st.set]
  if not name or name == set.name then return {} end
  set.name = name
  st.index_dirty = true
  return {}
end

-- ---- the songs page's state, /cutit/songs

-- A song's row's words: queued for the next bar, or loaded; and unsaved when
-- its draft differs from its save. - for none.
local function status(st, rec, unsaved_now)
  local w = {}
  local p = st.pending
  if p and p.rec == rec then
    w[1] = "next bar"
  elseif rec == st.cur then
    w[1] = "loaded"
  end
  if (rec == st.cur and unsaved_now) or (rec ~= st.cur and rec.unsaved) then
    w[#w + 1] = "unsaved"
  end
  return #w > 0 and table.concat(w, " · ") or "-"
end

-- The songs page: first the songs tab, how many songs, the one selected, the page and how many,
-- the selected one's name, then six rows of number, name and words, 0 - - for a row with none;
-- then the setlists tab, the setlist chosen and how many, its name, its page and how many, how
-- many entries, the one selected and its song's name, then five rows of key and song, 0 - for a
-- row with none. 41 atoms.
R.SONGS_PHONE = 5 + 3 * R.SONG_ROWS + 8 + 2 * R.SET_ROWS
function R.songs_phone(st, unsaved_now)
  if unsaved_now == nil then unsaved_now = R.unsaved(st) end
  local np = song_pages(st)
  local page = clip(st.song_page, 1, np)
  local out = { #st.songs, find(st.songs, st.sel_song) or 0, page, np, st.sel_song.song.name }
  for r = 1, R.SONG_ROWS do
    local i = (page - 1) * R.SONG_ROWS + r
    local rec = st.songs[i]
    local row = rec and { i, rec.song.name, status(st, rec, unsaved_now) } or { 0, "-", "-" }
    for _, a in ipairs(row) do out[#out + 1] = a end
  end
  local set = st.sets[st.set]
  local es = set.entries
  local sp = set_pages(set)
  local spage = clip(st.set_page, 1, sp)
  local e = es[st.entry]
  for _, a in ipairs({ st.set, #st.sets, set.name, spage, sp, #es, e and st.entry or 0,
                       e and e.song.song.name or "-" }) do
    out[#out + 1] = a
  end
  for r = 1, R.SET_ROWS do
    local j = (spage - 1) * R.SET_ROWS + r
    local en = es[j]
    local row = en and { j, en.song.song.name } or { 0, "-" }
    for _, a in ipairs(row) do out[#out + 1] = a end
  end
  return out
end

-- The whole lists, for the app, which scrolls: the setlist chosen and how many, their names; the entry
-- selected and how many, each its song's name and words; the song selected and how many, each its name
-- and words; then the song loaded: its name, whether it's unsaved, the section playing, queued (0 for
-- none) and selected, whether the selected one's tweaks carry on, and how many, each its name and length.
function R.lists(st, unsaved_now)
  if unsaved_now == nil then unsaved_now = R.unsaved(st) end
  local a = { st.set, #st.sets }
  for _, set in ipairs(st.sets) do a[#a + 1] = set.name end
  local es = st.sets[st.set].entries
  a[#a + 1] = st.entry
  a[#a + 1] = #es
  for _, e in ipairs(es) do
    a[#a + 1] = e.song.song.name
    a[#a + 1] = status(st, e.song, unsaved_now)
  end
  a[#a + 1] = find(st.songs, st.sel_song) or 0
  a[#a + 1] = #st.songs
  for _, rec in ipairs(st.songs) do
    a[#a + 1] = rec.song.name
    a[#a + 1] = status(st, rec, unsaved_now)
  end
  local secs = st.song.sections
  a[#a + 1] = st.song.name
  a[#a + 1] = unsaved_now and 1 or 0
  a[#a + 1] = R.index(st, st.playing)
  a[#a + 1] = st.queued and R.index(st, st.queued) or 0
  a[#a + 1] = R.index(st, st.selected)
  local t = st.selected.parts.tweaks
  a[#a + 1] = t and t[1] or 0
  a[#a + 1] = #secs
  for _, s in ipairs(secs) do
    a[#a + 1] = s.name
    a[#a + 1] = s.length
  end
  return a
end

-- What arrives on the first inlet: u_map's top row, top <1-8>, save and revert, the Organelle's
-- keys, key <1-25>.
R.presses = {
  top = function(st, a) return R.press(st, a[1]) end,
  save = function(st) return R.save(st) end,
  revert = function(st) return R.revert(st) end,
  key = function(st, a) return R.key(st, a[1]) end,
}

-- What arrives on the second: the phone's sections page, through u_net.
R.phone_cmds = {
  select = function(st, a) return R.select(st, a[1]) end,
  page = function(st, a) return R.turn(st, a[1]) end,
  new = function(st) return R.add(st) end,
  saveas = function(st) return R.save_new(st) end,
  up = function(st) return R.up(st) end,
  down = function(st) return R.down(st) end,
  length = function(st, a) return R.length(st, a[1]) end,
  delete = function(st) return R.delete(st) end,
  name = function(st, a) return R.rename(st, a) end,
  tweaks = function(st, a)
    local v = num(a[1]) == 1 and 1 or 0
    st.selected.parts.tweaks = { v }
    st.dirty = true
    return {}
  end,
}

-- What arrives on the second after songs: the phone's songs page, through u_net, its songs tab
-- and its setlists tab, and the name tab's done from each.
R.songs_cmds = {
  select = function(st, a) return R.song_select(st, a[1]) end,
  page = function(st, a) return R.song_turn(st, a[1]) end,
  load = function(st) return R.song_load(st) end,
  new = function(st) return R.song_new(st) end,
  name = function(st, a) return R.song_rename(st, a) end,
  add = function(st) return R.song_add(st) end,
  delete = function(st) return R.song_delete(st) end,
  entry = function(st, a) return R.entry_select(st, a[1]) end,
  set = function(st, a) return R.set_turn(st, a[1]) end,
  up = function(st) return move_entry(st, -1) end,
  down = function(st) return move_entry(st, 1) end,
  ["new-set"] = function(st) return R.set_new(st) end,
  remove = function(st) return R.entry_remove(st) end,
  ["set-name"] = function(st, a) return R.set_rename(st, a) end,
  choose = function(st, a)
    local n = math.floor(num(a[1]))
    if not st.sets[n] then return {} end
    st.set, st.set_page, st.entry = n, 1, #st.sets[n].entries > 0 and 1 or 0
    st.at_entry = nil
    st.index_dirty = true
    return {}
  end,
}

-- What u_song.pd itself sends: a part's put, the end of a bar, PLAY and STOP, and the load (the
-- face reads the files and hands their text to R.load).
R.internal = {
  put = function(st, a) return R.put(st, a) end,
  ["put-song"] = function(st, a) return R.put_song(st, a) end,
  ["seed-song"] = function(st, a) return R.seed_song(st, a) end,
  recall = function(st, a) return R.recall(st, a[1]) end,
  bar = function(st) return R.bar(st) end,
  one = function(st) return R.one(st) end,
  start = function(st) return R.start(st) end,
  stop = function(st) return R.stop(st) end,
  init = function() return {} end,
}

return R
