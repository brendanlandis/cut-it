-- The song store's rules, without Pd: "Cut It/u_song.lua", and the Pd face that carries them,
-- "Cut It/u_song-lua.pd_lua", loaded through lib_test's stand-in for pdlua, which reads and
-- writes the song's files in a folder of its own here. The song gate runs this before its Pd
-- half (test/gate/scratch-gates.py); by hand, from the repo root:
--
--   lua test/gate/lua/u_song_test.lua [-v]
--
-- What the patch does with these answers -- the parts restored, the lamps on the Launchpad, the
-- phone's page, the files across a reload -- is song-assert.py's, on a running copy of the
-- instrument. ref/module/songs.md.

local T = dofile("test/gate/lua/lib_test.lua")
local DIR = "Cut It/"
local R = dofile(DIR .. "u_song.lua")
local check, equal = T.check, T.equal

local D, S, P, Q, A = R.DARK, R.SECTION, R.PLAYING, R.QUEUED, R.ARROW

-- A song of named sections, loaded as if from no files, each with a part of its own: drums <n>,
-- the section's place, so a restore says which section started.
local function song(names, lengths)
  local st = R.new()
  R.put(st, { "drums", 1 })
  R.load(st, nil, nil)
  st.song.sections[1].name = names[1]
  st.song.sections[1].length = (lengths or {})[1] or 0
  for i = 2, #names do
    st.selected = st.song.sections[i - 1]
    R.add(st)
    local s = st.song.sections[i]
    s.name, s.length, s.parts = names[i], (lengths or {})[i] or 0, { drums = { i } }
  end
  st.selected, st.page = st.song.sections[1], 1
  st.saved = nil
  st.saved = (function()
    local out = { name = st.song.name, sections = {} }
    for i, s in ipairs(st.song.sections) do
      local parts = {}
      for k, v in pairs(s.parts) do parts[k] = v end
      out.sections[i] = { id = s.id, name = s.name, length = s.length, parts = parts }
    end
    return out
  end)()
  return st
end

local function restores(out)
  local r = {}
  for _, e in ipairs(out) do
    if e[1] == "state" then r[#r + 1] = table.concat((function()
      local w = {}
      for i, a in ipairs(e[3]) do w[i] = R.fmt(a) end
      return w
    end)(), " ") end
  end
  return r
end

local function names(st)
  local n = {}
  for i, s in ipairs(st.song.sections) do n[i] = s.name end
  return n
end

print("\n--- a fresh load: one section, saved as it is ---")
local st = R.new()
equal("before the load: one section, section 1, playing and selected",
      { #st.song.sections, st.song.sections[1].name, st.playing == st.song.sections[1],
        st.selected == st.playing }, { 1, "section 1", true, true })
equal("... nothing is unsaved before the files are read", R.unsaved(st), false)
R.put(st, { "drums", 0, 0, 16 })
R.put(st, { "tempo", 120 })
R.put(st, { "synth", "fm" })
equal("a part's put lands in the section playing, under its key, as its atoms",
      st.playing.parts, { drums = { 0, 0, 16 }, tempo = { 120 }, synth = { "fm" } })
local out = R.load(st, nil, nil)
equal("with no files, the load starts section 1: every part it holds goes back out, in the "
      .. "keys' order", restores(out), { "drums 0 0 16", "synth fm", "tempo 120" })
equal("... and its restores are restore <key> <atoms...> on the state bus", out[1],
      { "state", "restore", { "drums", 0, 0, 16 } })
equal("... the song is saved as it is: nothing unsaved, both files to write",
      { R.unsaved(st), st.write_saved }, { false, true })
equal("... one section on the top row: button 3 lit, playing, and neither arrow",
      R.top(st), { D, D, P, D, D, D, D, D })
local tempo = st.playing.parts.tempo
R.put(st, { "tempo", 120.0 })
equal("a part putting back the same atoms changes nothing: still saved, the same table",
      { R.unsaved(st), st.playing.parts.tempo == tempo }, { false, true })
R.put(st, { "tempo", 132 })
equal("a put that changes a part: unsaved, and the draft to write", { R.unsaved(st), st.dirty },
      { true, true })
R.put(st, { "tempo", 120 })
equal("⛔ changed back to what was saved: nothing unsaved, the lamps go dark again",
      R.unsaved(st), false)
-- A Pd float is 32 bits: 0.1 arrives as 0.100000001490116, and the file says 0.1.
R.put(st, { "swingish", 0.100000001490116 })
equal("a number is kept as the file would write it, so Pd's 0.1 and the file's are one",
      st.playing.parts.swingish, { 0.1 })
equal("a put with no key is fail u_song bad-put", R.put(st, { 3 }),
      { { "err", "fail", { "u_song", "bad-put" } } })

print("\n--- the files ---")
st = song({ "intro", "verse", "chorus" }, { 4, 8, 0 })
st.song.sections[2].parts.synth = { "strings" }
st.song.sections[2].parts.programs = { "none", 20 }
local text = R.text(st.song)
equal("a song is a line for its name, then each section's line and its parts, keys in order",
      text, "song song 1\nsection 1 4 intro\ndrums 1\nsection 2 8 verse\ndrums 2\n"
      .. "programs none 20\nsynth strings\nsection 3 0 chorus\ndrums 3\n")
local back = R.parse(text)
equal("... and reads back as it was", R.text(back), text)
equal("a number reads back a number and a word a word",
      { back.sections[2].parts.programs[1], back.sections[2].parts.programs[2] }, { "none", 20 })
equal("a name runs to the end of its line", R.parse("song night drive\nsection 4 0 verse 2\n")
      .sections[1].name, "verse 2")
equal("a file with no section, or no song line, or nothing, is no song",
      { R.parse("song x\n"), R.parse("section 1 0 a\ndrums 1\n"), R.parse(""), R.parse(nil) },
      {})
local odd = R.parse("song X\nsection 2 99 A\ndrums 1\nsection 2 -1\ntempo 90\n")
equal("a length past 64 is 64, below 0 is 0, a name with none is section 1, the song's lowered",
      { odd.sections[1].length, odd.sections[2].length, odd.sections[2].name, odd.name },
      { 64, 0, "section 1", "x" })

print("\n--- the load: the draft, the saved song, or both ---")
local saved = "song song 1\nsection 1 0 intro\ndrums 1\ntempo 100\nsection 2 8 verse\ndrums 2\n"
local draft = "song song 1\nsection 1 0 intro\ndrums 1\ntempo 110\nsection 2 8 verse\ndrums 2\n"
st = R.new()
out = R.load(st, draft, saved)
equal("both: the draft plays, its first section started", restores(out), { "drums 1", "tempo 110" })
equal("... and it differs from the saved song, so save and revert are lit", R.unsaved(st), true)
equal("... no file to write", { st.dirty, st.write_saved }, { false, false })
st = R.new()
R.load(st, saved, saved)
equal("both alike: nothing unsaved", R.unsaved(st), false)
equal("... and their equal parts are one table, so comparing them costs a glance",
      st.song.sections[2].parts.drums == st.saved.sections[2].parts.drums, true)
st = R.new()
R.load(st, nil, saved)
equal("the saved song alone: it plays, and the draft is to be written",
      { names(st), R.unsaved(st), st.dirty, st.write_saved }, { { "intro", "verse" }, false,
      true, false })
st = R.new()
R.load(st, draft, nil)
equal("the draft alone: it is saved as it is, both files written",
      { R.unsaved(st), st.write_saved }, { false, true })
st = R.new()
R.load(st, "song a\nsection 3 0 x\nsection 3 0 y\nsection 0 0 z\n", nil)
local ids = {}
for i, s in ipairs(st.song.sections) do ids[i] = s.id end
equal("a section with no id, or one another has, gets a new one", ids, { 3, 4, 5 })
equal("... and the next new section another", st.next_id, 6)

print("\n--- the top row: stopped, a section starts at once ---")
st = song({ "a", "b", "c" })
equal("three sections: a playing, the forward arrow lit, b and c lit as sections",
      R.top(st), { D, A, P, S, S, D, D, D })
out = R.press(st, 4)
equal("stopped, button 4 starts b at once: its parts go out", restores(out), { "drums 2" })
equal("... b plays, and both arrows are lit", R.top(st), { A, A, S, P, S, D, D, D })
equal("the section playing, pressed again while stopped, does nothing", R.press(st, 4), {})
equal("button 7, which shows no section, does nothing", R.press(st, 7), {})
equal("back, button 1: a, at once", restores(R.press(st, 1)), { "drums 1" })
equal("back from the first does nothing", R.press(st, 1), {})
equal("a button past 8 is fail u_song bad-button", R.press(st, 9),
      { { "err", "fail", { "u_song", "bad-button" } } })

print("\n--- the top row: playing, a section is queued for the next bar ---")
st = song({ "a", "b", "c" })
R.start(st)
equal("playing, button 5 queues c: nothing goes out yet", R.press(st, 5), {})
equal("... c blinks, a still plays, and the arrows go from c, the last", R.top(st),
      { A, D, P, S, Q, D, D, D })
equal("... the end of the bar starts c", restores(R.bar(st)), { "drums 3" })
equal("... c plays, solid", R.top(st), { A, D, S, S, P, D, D, D })
R.press(st, 3)
R.press(st, 4)
equal("a second press before the bar queues the second section instead",
      R.top(st), { A, A, S, Q, P, D, D, D })
R.bar(st)
equal("forward, button 2, queues the one after the one playing", { R.press(st, 2), R.top(st) },
      { {}, { A, D, S, P, Q, D, D, D } })
R.press(st, 2)
equal("... and from the one queued: forward past the last does nothing",
      R.top(st), { A, D, S, P, Q, D, D, D })
R.press(st, 1)
R.press(st, 1)
equal("back twice from the one queued: a", R.top(st), { D, A, Q, P, S, D, D, D })
R.bar(st)
R.press(st, 3)
equal("the section playing, pressed while playing, is queued to start again",
      R.top(st), { D, A, Q, S, S, D, D, D })
equal("... at the bar its parts go out again", restores(R.bar(st)), { "drums 1" })
R.press(st, 4)
equal("STOP with a section queued: no bar is coming, so it starts now", restores(R.stop(st)),
      { "drums 2" })
equal("... and nothing is left queued", st.queued, nil)

print("\n--- lengths: a section plays its bars and hands over ---")
st = song({ "a", "b", "c" }, { 2, 0, 0 })
R.start(st)
equal("a section of two bars: after one, nothing", R.bar(st), {})
equal("... after two, the next starts by itself", restores(R.bar(st)), { "drums 2" })
equal("b loops, with no length: bars go by and nothing starts",
      { #R.bar(st), #R.bar(st), #R.bar(st), R.index(st, st.playing) }, { 0, 0, 0, 2 })
st.song.sections[3].length = 1
R.press(st, 5)
R.bar(st)
equal("⛔ the last section with a length has no next: it plays on as a loop",
      { #R.bar(st), #R.bar(st), R.index(st, st.playing) }, { 0, 0, 3 })
st = song({ "a", "b", "c" }, { 4, 0, 0 })
R.start(st)
R.bar(st)
R.press(st, 5)
equal("a press still jumps at the next bar, whatever the length", restores(R.bar(st)),
      { "drums 3" })
st = song({ "a", "b" }, { 2, 0 })
R.start(st)
R.bar(st)
R.start(st)
equal("⛔ PLAY counts the bars again from its downbeat", { #R.bar(st), #restores(R.bar(st)) },
      { 0, 1 })

print("\n--- the six buttons scroll with the section playing ---")
st = song({ "1", "2", "3", "4", "5", "6", "7", "8", "9", "10" })
equal("ten sections: the first six on the buttons", R.top(st), { D, A, P, S, S, S, S, S })
R.press(st, 8)
equal("the sixth started: the window stays", { st.first, R.top(st) },
      { 1, { A, A, S, S, S, S, S, P } })
R.press(st, 2)
equal("forward to the seventh: the window scrolls one section, so button 3 shows section 2 "
      .. "and button 8 section 7 (Brendan, 2026-11-02)", { st.first, R.top(st) },
      { 2, { A, A, S, S, S, S, S, P } })
R.press(st, 2)
R.press(st, 2)
R.press(st, 2)
equal("... to the tenth, a section at a time", { st.first, R.top(st) },
      { 5, { A, D, S, S, S, S, S, P } })
R.press(st, 3)
equal("button 3 is the window's first: section 5", R.index(st, st.playing), 5)
R.start(st)
R.press(st, 1)
equal("playing, back queues the fourth: the window scrolls to show it beside the fifth",
      { st.first, R.top(st) }, { 4, { A, A, Q, P, S, S, S, S } })

print("\n--- the sections page: select, page, new, move, length, delete ---")
st = song({ "intro", "verse", "chorus" })
R.select(st, 2)
equal("a row tapped selects that section, and plays nothing", { st.selected.name,
      R.index(st, st.playing) }, { "verse", 1 })
equal("a row with no section selects nothing", { R.select(st, 9), st.selected.name },
      { {}, "verse" })
R.add(st)
equal("new: a copy of the selected, after it, named after it, and selected",
      { names(st), st.selected.name }, { { "intro", "verse", "verse 2", "chorus" }, "verse 2" })
equal("... its parts are the copied section's", st.selected.parts.drums, { 2 })
equal("... and the song differs from the saved one", R.unsaved(st), true)
R.add(st)
equal("a copy of verse 2 is verse 3", st.selected.name, "verse 3")
R.select(st, 1)
R.add(st)
equal("... and of intro, intro 2", names(st), { "intro", "intro 2", "verse", "verse 2",
      "verse 3", "chorus" })
equal("six sections: two pages, the copy's page shown", { R.phone(st)[4], R.phone(st)[5] },
      { 1, 2 })
R.up(st)
equal("move up: the selected one a place earlier, still selected",
      { names(st)[1], names(st)[2], st.selected.name }, { "intro 2", "intro", "intro 2" })
equal("move up from the top does nothing", { R.up(st), names(st)[1] }, { {}, "intro 2" })
R.select(st, 6)
equal("move down from the bottom does nothing", { R.down(st), names(st)[6] }, { {}, "chorus" })
R.length(st, 16)
equal("length 16: the selected one plays sixteen bars", st.selected.length, 16)
R.length(st, 99)
equal("... a length past 64 is 64, and below 0 loop", { st.selected.length,
      (function() R.length(st, -3) return st.selected.length end)() }, { 64, 0 })
equal("... and a length with no number changes nothing", { R.length(st, "x"),
      st.selected.length }, { {}, 0 })
R.delete(st)
equal("delete: the selected one goes, and the one now in its place, here the last, is selected",
      { names(st), st.selected.name }, { { "intro 2", "intro", "verse", "verse 2", "verse 3" },
      "verse 3" })
st = song({ "a", "b", "c" })
R.press(st, 4)
R.select(st, 2)
equal("deleting the section playing starts the one now in its place, at once",
      restores(R.delete(st)), { "drums 3" })
equal("... which is playing", st.playing.name, "c")
st = song({ "a" })
equal("⛔ a song keeps one section: deleting the last is warn u_song last-section",
      R.delete(st), { { "err", "warn", { "u_song", "last-section" } } })
st = song({ "a", "b", "c" })
R.start(st)
R.press(st, 5)
R.select(st, 3)
R.delete(st)
equal("deleting the section queued leaves nothing queued", { st.queued, restores(R.bar(st)) },
      { nil, {} })

print("\n--- names ---")
equal("a name is lowered, single-spaced and trimmed", R.clean({ "  Verse ", "2 " }), "verse 2")
equal("... the keyboard's characters only: A to Z, space, - and ', 0 to 9",
      R.clean({ "don't-stop!@#" }), "don't-stop")
equal("... a number in it reads as typed", R.clean({ "take", 12 }), "take 12")
equal("... at most 20 characters", R.clean({ "abcdefghij klmnopqrstuvwxyz" }),
      "abcdefghij klmnopqrs")
equal("... and one with nothing left is no name", { R.clean({}), R.clean({ "!!!" }) }, {})
st = song({ "a", "b" })
R.select(st, 2)
R.rename(st, { "Bridge" })
equal("the name tab's done renames the selected section", names(st), { "a", "bridge" })
equal("... a name with nothing in it changes nothing", { R.rename(st, { "?" }), names(st)[2] },
      { {}, "bridge" })
equal("a copy's name fits in 20, the number kept", R.copy_name({ sections = {} },
      "abcdefghijklmnopqrst"), "abcdefghijklmnopqr 2")
equal("a copy of 2 is 2 2", R.copy_name({ sections = {} }, "2"), "2 2")

print("\n--- save and revert ---")
st = song({ "a", "b" })
R.press(st, 4)
R.put(st, { "drums", 22 })
R.select(st, 1)
R.add(st)
equal("a part changed and a section added: unsaved", R.unsaved(st), true)
equal("save: the info line, and the saved file to write", R.save(st),
      { { "err", "info", { "u_song", "saved" } } })
equal("... nothing unsaved now, both files written", { R.unsaved(st), st.write_saved },
      { false, true })
equal("save with nothing to save does nothing", R.save(st), {})
equal("revert with nothing to revert does nothing", R.revert(st), {})
R.put(st, { "drums", 33 })
R.select(st, 1)
R.delete(st)
R.length(st, 4)
equal("three changes since: unsaved", R.unsaved(st), true)
out = R.revert(st)
equal("revert: every section as saved, the one playing started again from the save",
      { names(st), restores(out), R.unsaved(st) }, { { "a", "a 2", "b" }, { "drums 22" }, false })
equal("... with an info line first", out[1], { "err", "info", { "u_song", "reverted" } })
equal("... the section playing is the same section, and the selection kept by id",
      { st.playing.name, st.selected.name }, { "b", "a 2" })
R.select(st, 2)
R.add(st)
R.press(st, 4)
R.revert(st)
equal("revert while a new section plays: the one now in its place plays",
      { names(st), st.playing.name }, { { "a", "a 2", "b" }, "a 2" })

print("\n--- the phone's state ---")
st = song({ "intro", "verse", "chorus", "verse 2", "bridge", "outro", "end" }, { 8, 16, 0 })
R.select(st, 3)
equal("the song, how many, the selected, the page and pages, the selected one's name and "
      .. "length, then five rows", R.phone(st),
      { "song 1", 7, 3, 1, 2, "chorus", 0, 1, "intro", 8, 2, "verse", 16, 3, "chorus", 0,
        4, "verse 2", 0, 5, "bridge", 0 })
equal("... 22 atoms", #R.phone(st), R.PHONE)
R.turn(st, 1)
equal("page on: the sixth and seventh, then empty rows", R.phone(st),
      { "song 1", 7, 3, 2, 2, "chorus", 0, 6, "outro", 0, 7, "end", 0, 0, "-", 0, 0, "-", 0,
        0, "-", 0 })
R.turn(st, 1)
equal("... and no further than the last page", R.phone(st)[4], 2)
R.turn(st, -1)
R.turn(st, -1)
equal("... nor before the first", R.phone(st)[4], 1)

print("\n--- the Pd face ---")
local tmp = os.tmpname()
os.remove(tmp)
assert(os.execute("mkdir -p " .. tmp))
local class = T.load_class(DIR .. "u_song-lua.pd_lua", DIR)
local o = T.new(class, { tmp })
local function lamps(sent)
  local l = {}
  for _, e in ipairs(sent) do if e[1] == 1 and e[2] == "unsaved" then l[#l + 1] = e end end
  return l
end
local function phone(sent)
  for _, e in ipairs(sent) do if e[1] == 2 then return e[3] end end
end
local function file(name)
  local fh = io.open(tmp .. "/" .. name)
  if not fh then return nil end
  local t = fh:read("a")
  fh:close()
  return t
end
local sent = T.send(o, 3, "init", {})
equal("init: the lamps and the phone's state, once each, then the proof bang",
      { sent[1], sent[2], sent[3][1], sent[4], #sent }, { { 1, "top", { D, D, P, D, D, D, D, D } },
      { 1, "unsaved", { 0 } }, 2, { 5, "bang", {} }, 4 })
equal("a put the lamps don't show sends nothing", T.send(o, 3, "put", { "drums", 7 }), {})
sent = T.send(o, 3, "flush", {})
equal("⛔ the draft's timer before the load writes nothing", { sent, file("cut-it-song-draft.txt") },
      { {} })
sent = T.send(o, 3, "load", {})
equal("the load, with no files: section 1 starts, out the third outlet to the state bus",
      sent[1], { 3, "restore", { "drums", 7 } })
equal("... and both files are written, the song as it is",
      { file("cut-it-song.txt"), file("cut-it-song-draft.txt") },
      { "song song 1\nsection 1 0 section 1\ndrums 7\n",
        "song song 1\nsection 1 0 section 1\ndrums 7\n" })
T.send(o, 3, "put", { "drums", 8 })
equal("a change lights save and revert", lamps(o.sent), { { 1, "unsaved", { 1 } } })
T.send(o, 3, "flush", {})
equal("the draft's timer writes the draft, and the saved song stays",
      { file("cut-it-song-draft.txt"), file("cut-it-song.txt") },
      { "song song 1\nsection 1 0 section 1\ndrums 8\n",
        "song song 1\nsection 1 0 section 1\ndrums 7\n" })
sent = T.send(o, 2, "new", {})
equal("⛔ a phone command first asks the parts for what they hold back: sync on the state bus",
      sent[1], { 3, "sync", {} })
table.remove(sent, 1)
local ph = phone(sent)
equal("the phone's new: the phone's state, two sections, the copy selected, its row",
      { ph[2], ph[3], ph[11], ph[12] }, { 2, 2, 2, "section 2" })
equal("... and the top row's second section, and the forward arrow", sent[1],
      { 1, "top", { D, A, P, S, D, D, D, D } })
sent = T.send(o, 1, "top", { 4 })
equal("⛔ a press first asks the parts for what they hold back, before section 2 starts",
      sent[1], { 3, "sync", {} })
table.remove(sent, 1)
equal("the top row's button 4, stopped: section 2 starts", sent[1], { 3, "restore",
      { "drums", 8 } })
sent = T.send(o, 1, "save", {})
equal("save: the lamps go dark", lamps(sent), { { 1, "unsaved", { 0 } } })
equal("... and both files are the song", { file("cut-it-song.txt") == file("cut-it-song-draft.txt"),
      select(2, file("cut-it-song.txt"):gsub("\nsection ", "")) }, { true, 2 })
T.send(o, 3, "put", { "drums", 9 })
local o2 = T.new(class, { tmp })
T.send(o2, 3, "init", {})
T.send(o2, 3, "load", {})
equal("⛔ a reload before the draft is flushed: the saved song, which is all the files hold",
      R.text(o2.state.song), "song song 1\nsection 1 0 section 1\ndrums 8\nsection 2 0 section 2\n"
      .. "drums 8\n")
T.send(o, 3, "flush", {})
local o3 = T.new(class, { tmp })
T.send(o3, 3, "init", {})
sent = T.send(o3, 3, "load", {})
equal("⛔ after the flush, a reload has the draft, its change unsaved: save and revert lit",
      { o3.state.song.sections[2].parts.drums, lamps(sent)[1] },
      { { 9 }, { 1, "unsaved", { 1 } } })
equal("... and section 1 starts", sent[1], { 3, "restore", { "drums", 8 } })
sent = T.send(o3, 1, "revert", {})
equal("revert: back to the save, the lamps dark", { lamps(sent), o3.state.song.sections[2].parts.drums },
      { { { 1, "unsaved", { 0 } } }, { 8 } })
equal("⛔ STOP first asks the parts for what they hold back, since it can start a queued section",
      T.send(o3, 3, "stop", {})[1], { 3, "sync", {} })
equal("a message the store does not know is fail u_song bad-selector",
      T.send(o3, 2, "shuffle", {}), { { 3, "sync", {} }, { 4, "fail", { "u_song", "bad-selector" } } })
local lost = T.new(class, { tmp .. "/nowhere" })
T.send(lost, 3, "init", {})
sent = T.send(lost, 3, "load", {})
local fails = {}
for _, e in ipairs(sent) do if e[1] == 4 then fails[#fails + 1] = e end end
equal("⛔ a file that can't be written is fail u_song write-failed, not silence",
      fails, { { 4, "fail", { "u_song", "write-failed" } }, { 4, "fail", { "u_song",
      "write-failed" } } })
os.execute("rm -rf " .. tmp)

-- A broken copy of the rules, from a prefix of its own: a throw reaches err as lua-<selector>.
local bad = os.tmpname()
local fh = assert(io.open(DIR .. "u_song.lua"))
local src = fh:read("a")
fh:close()
src = src:gsub("function R%.add%(st%)\n", "function R.add(st)\n  error('broken')\n", 1)
for _, f in ipairs({ { "u_song.lua", src } }) do
  local w = assert(io.open(bad .. "-" .. f[1], "w"))
  w:write(f[2])
  w:close()
end
local face = assert(io.open(DIR .. "lua-face.lua"))
local fw = assert(io.open(bad .. "-lua-face.lua", "w"))
fw:write(face:read("a"))
face:close()
fw:close()
local broken = T.new(T.load_class(DIR .. "u_song-lua.pd_lua", bad .. "-"), { "/nonexistent" })
equal("a rule that throws is fail u_song lua-<selector>", T.send(broken, 2, "new", {})[2],
      { 4, "fail", { "u_song", "lua-new" } })
os.remove(bad .. "-u_song.lua")
os.remove(bad .. "-lua-face.lua")
os.remove(bad)

os.exit(T.report() == 0)
