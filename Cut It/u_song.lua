-- u_song.lua -- the song: its sections, which one plays and which is queued, the draft and the
-- saved song, and the text of their two files. Plain Lua with no Pd in it, so
-- test/gate/lua/u_song_test.lua runs it on the Mac with lua.org's interpreter. u_song-lua.pd_lua
-- is its Pd face, which reads and writes the files, and u_song.pd keeps the cords, the state bus,
-- the transport and the draft's timer. ref/module/songs.md.
--
-- A section is its name, its length in bars (0 loops until another is queued) and its parts: what
-- each part of the instrument put while it played, under the part's own key (drums, tempo, synth,
-- velocity, programs), as the atoms it put. The store knows nothing about what a key means, as
-- u_state knows nothing (ref/module/state.md): a part puts `put section <key> <atoms...>` on the
-- state bus, which lands in the playing section, and a section starting sends every part it holds
-- back as `restore <key> <atoms...>`.
--
-- The state is a plain table and every rule a function of it, so a live reload of the rules keeps
-- the song. Every rule returns what leaves, in order, as {outlet, selector, atoms}:
--   {"state", "restore", {key, atoms...}}         to the state bus: a section starting
--   {"err", "fail" | "warn" | "info", {"u_song", text}}   to err (C-12)
-- The top row's lamps (R.top), the save and revert lamps (R.unsaved) and the phone's state
-- (R.phone) are worked out from the state after every answer, by the face, and sent when they
-- change; and the face writes the files the state asks for (st.dirty, st.write_saved).

local R = {}

-- The top row (Brendan, 2026-11-02): buttons 1 and 2 the arrows, back and forward a section,
-- 3 to 8 the six section buttons, which scroll a section at a time with the one playing.
R.BUTTONS = 6
-- A top-row button's lamp, as g_grid paints it: dark, a section, the section playing, the
-- section queued (blinking), and an arrow that has somewhere to go.
R.DARK, R.SECTION, R.PLAYING, R.QUEUED, R.ARROW = 0, 1, 2, 3, 4
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

-- An atom as the store keeps it: a number read back from how it would be written, so a value
-- that came from Pd, a 32-bit float, compares equal to the same value read from a file.
local function norm(x)
  if type(x) == "number" then return tonumber(R.fmt(x)) end
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
-- the first number from 2 that no section of the song has. A copy of "verse 2" is "verse 3".
function R.copy_name(song, name)
  local base = name:match("^(.-) %d+$") or name
  local used = {}
  for _, s in ipairs(song.sections) do used[s.name] = true end
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
  local out = { name = song.name, sections = {} }
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

function R.new()
  local st = { next_id = 1, page = 1, first = 1, bars = 0, running = false, loaded = false,
               dirty = false, write_saved = false }
  local s = section(st, R.FIRST, 0, {})
  st.song = { name = R.SONG, sections = { s } }
  st.playing, st.selected = s, s
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
local function begin(st, s)
  st.playing, st.queued, st.bars = s, nil, 0
  follow(st)
  local keys = {}
  for k in pairs(s.parts) do keys[#keys + 1] = k end
  table.sort(keys)
  local out = {}
  for _, k in ipairs(keys) do
    local a = { k }
    for _, x in ipairs(s.parts[k]) do a[#a + 1] = x end
    out[#out + 1] = { "state", "restore", a }
  end
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
  local a, b = st.song, st.saved
  if a.name ~= b.name or #a.sections ~= #b.sections then return true end
  for i, s in ipairs(a.sections) do
    local t = b.sections[i]
    if s.id ~= t.id or s.name ~= t.name or s.length ~= t.length then return true end
    for k, v in pairs(s.parts) do
      local w = t.parts[k]
      if not w or not same_atoms(v, w) then return true end
    end
    for k in pairs(t.parts) do
      if not s.parts[k] then return true end
    end
  end
  return false
end

-- A part's put, `put <key> <atoms...>`: into the playing section. The same atoms again change
-- nothing, so a part putting back what it restored leaves the song as it was.
function R.put(st, atoms)
  local key = atoms[1]
  if type(key) ~= "string" then return { R.fail("bad-put") } end
  local a = {}
  for i = 2, #atoms do a[#a + 1] = norm(atoms[i]) end
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
  local function find(id, i)
    for _, x in ipairs(st.song.sections) do
      if x.id == id then return x end
    end
    return st.song.sections[math.min(i, #st.song.sections)]
  end
  st.selected = find(s, si)
  st.page = page_of(R.index(st, st.selected))
  st.dirty = true
  local out = begin(st, find(p, pi))
  table.insert(out, 1, report("info", "reverted"))
  return out
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
      song = { name = R.clean({ table.unpack(words, 2) }) or R.SONG, sections = {} }
      cur = nil
    elseif k == "section" and song then
      cur = { id = tonumber(words[2]), length = math.floor(clip(tonumber(words[3]) or 0, 0,
              R.MAX_LENGTH)), name = R.clean({ table.unpack(words, 4) }) or R.FIRST, parts = {} }
      song.sections[#song.sections + 1] = cur
    elseif k and cur then
      local a = {}
      for i = 2, #words do a[#a + 1] = tonumber(words[i]) or words[i] end
      cur.parts[k] = a
    end
  end
  if not song or #song.sections == 0 then return nil end
  return song
end

-- Every section an id of its own, whole, and next_id past them all, in the draft and the saved
-- song together: a section in both is the same section.
local function number(st, songs)
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
  st.next_id = top + 1
  for _, song in ipairs(songs) do
    for _, s in ipairs(song.sections) do
      if not s.id then s.id = st.next_id; st.next_id = st.next_id + 1 end
    end
  end
end

-- Where the draft and the saved song hold equal parts, one table: comparing them is then a
-- glance (R.unsaved), until a put replaces one.
local function share(st)
  local by = {}
  for _, s in ipairs(st.saved.sections) do by[s.id] = s end
  for _, s in ipairs(st.song.sections) do
    local t = by[s.id]
    if t then
      for k, v in pairs(s.parts) do
        local w = t.parts[k]
        if w and same_atoms(v, w) then s.parts[k] = w end
      end
    end
  end
end

-- The files, read at load (~3.5 s, after u_state's restore): the draft, and the saved song.
-- Either missing is made from the other, and with neither the song is the one section the
-- parts have put into since load, saved as it is: a fresh load has one section, and nothing to
-- save. Then section 1 starts, and the files missing are written.
function R.load(st, draft_text, saved_text)
  local draft, saved = R.parse(draft_text), R.parse(saved_text)
  local read = {}
  if draft then read[#read + 1] = draft end
  if saved then read[#read + 1] = saved end
  if #read == 0 then read[1] = st.song end
  number(st, read)
  st.song = draft or (saved and copy_song(saved)) or st.song
  st.saved = saved or copy_song(st.song)
  share(st)
  st.loaded = true
  st.dirty = draft == nil
  st.write_saved = saved == nil
  st.selected, st.page, st.first = st.song.sections[1], 1, 1
  return begin(st, st.song.sections[1])
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

-- A top-row button, 1 to 8: back and forward one section from the one queued, or the one
-- playing; or the section a button shows. A button with no section does nothing.
function R.press(st, n)
  local b = math.floor(num(n))
  local count = #st.song.sections
  local at = R.index(st, st.queued or st.playing)
  local target
  if b == 1 then
    target = at - 1
  elseif b == 2 then
    target = at + 1
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
-- pattern has played. A queued section starts; else a section with a length that has played its
-- bars hands over to the next. The last section with a length has no next, and plays on as a
-- loop, until another is queued.
function R.bar(st)
  st.bars = st.bars + 1
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
  return {}
end

-- STOP and panic: no next bar is coming, so a section queued starts now.
function R.stop(st)
  st.running = false
  if st.queued then return begin(st, st.queued) end
  return {}
end

-- The top row's eight lamps: the arrows, lit when there is a section that way from the one
-- queued, or the one playing; then the six buttons' sections.
function R.top(st)
  local n = #st.song.sections
  local p = R.index(st, st.playing)
  local q = st.queued and R.index(st, st.queued)
  local at = q or p
  local out = { at > 1 and R.ARROW or R.DARK, at < n and R.ARROW or R.DARK }
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

-- What arrives on the first inlet: u_map's top row, top <1-8>, and save and revert.
R.presses = {
  top = function(st, a) return R.press(st, a[1]) end,
  save = function(st) return R.save(st) end,
  revert = function(st) return R.revert(st) end,
}

-- What arrives on the second: the phone's sections page, through u_net.
R.phone_cmds = {
  select = function(st, a) return R.select(st, a[1]) end,
  page = function(st, a) return R.turn(st, a[1]) end,
  new = function(st) return R.add(st) end,
  up = function(st) return R.up(st) end,
  down = function(st) return R.down(st) end,
  length = function(st, a) return R.length(st, a[1]) end,
  delete = function(st) return R.delete(st) end,
  name = function(st, a) return R.rename(st, a) end,
}

-- What u_song.pd itself sends: a part's put, the end of a bar, PLAY and STOP, and the load (the
-- face reads the files and hands their text to R.load).
R.internal = {
  put = function(st, a) return R.put(st, a) end,
  bar = function(st) return R.bar(st) end,
  start = function(st) return R.start(st) end,
  stop = function(st) return R.stop(st) end,
  init = function() return {} end,
}

return R
