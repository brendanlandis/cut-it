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

-- A bar's answer and what it held for the next step 1, the tempo and the programs, together.
local function at_one(out)
  for _, e in ipairs(R.one(st)) do out[#out + 1] = e end
  return out
end
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

print("\n--- a part's saved value, asked for ---")
st = song({ "a", "b" })
R.put(st, { "tempo", 120 })
R.save(st)
R.put(st, { "tempo", 133 })
equal("⛔ recall tempo: the saved song's, 120, not the draft's 133, as a section starting sends it",
      R.internal.recall(st, { "tempo" }), { { "state", "restore", { "tempo", 120 } } })
check("... and the draft is still the draft: what comes back is the part's to put",
      R.unsaved(st) and st.playing.parts.tempo[1] == 133, T.show(st.playing.parts.tempo))
R.put(st, { "tempo", 120 })
check("⛔ the part's put back: nothing unsaved on its account", not R.unsaved(st), "")
equal("it knows nothing of keys: any part's saved atoms, whole", (function()
  R.put(st, { "synth", "fm", 3 })
  R.save(st)
  R.put(st, { "synth", "strings", 9 })
  return R.internal.recall(st, { "synth" })
end)(), { { "state", "restore", { "synth", "fm", 3 } } })
equal("⛔ the section PLAYING's: section b's saved tempo, once it plays", (function()
  R.press(st, 4)
  R.put(st, { "tempo", 90 })
  R.save(st)
  R.put(st, { "tempo", 95 })
  return R.internal.recall(st, { "tempo" })
end)(), { { "state", "restore", { "tempo", 90 } } })
equal("⛔ a section never saved: the draft's", (function()
  st.selected = st.playing
  R.add(st)
  R.press(st, R.index(st, st.selected) + 2)
  R.put(st, { "tempo", 77 })
  return R.internal.recall(st, { "tempo" })
end)(), { { "state", "restore", { "tempo", 77 } } })
equal("a part its save did not hold: the draft's", (function()
  R.put(st, { "new-part", 5 })
  return R.internal.recall(st, { "new-part" })
end)(), { { "state", "restore", { "new-part", 5 } } })
equal("a part nobody holds: nothing", R.internal.recall(st, { "nothing" }), {})

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

print("\n--- several songs: a fresh load, and the index ---")
-- A song's text, one section of each name given, each with drums <n> of its place.
local function songtext(name, sections, tempo)
  local out = { "song " .. name }
  for i, n in ipairs(sections) do
    out[#out + 1] = string.format("section %d 0 %s", i, n)
    out[#out + 1] = "drums " .. i
    if tempo then out[#out + 1] = "tempo " .. tempo end
  end
  return table.concat(out, "\n") .. "\n"
end
local function snames(st)
  local n = {}
  for i, rec in ipairs(st.songs) do n[i] = rec.song.name end
  return n
end
local function entries(st)
  local n = {}
  for i, e in ipairs(st.sets[st.set].entries) do n[i] = e.song.song.name .. " " .. e.starts end
  return n
end
st = R.new()
R.put(st, { "drums", 4 })
R.load(st, nil, nil)
equal("with no files: one song, song 1, and one setlist, set 1, song 1 its opener from silence",
      { snames(st), st.sets[1].name, entries(st), st.set, st.entry },
      { { "song 1" }, "set 1", { "song 1 silence" }, 1, 1 })
equal("... and the index to write", { st.index_dirty, R.index_text(st) },
      { true, "next 2\ncurrent 1\nchosen 1\nsong 1\nset set 1\nentry 1 silence\n" })
equal("song 1's files keep the one song's names; another's are named for its id",
      { R.files(1), select(2, R.files(1)), R.files(12), select(2, R.files(12)), R.INDEX },
      { "cut-it-song.txt", "cut-it-song-draft.txt", "cut-it-song-12.txt",
        "cut-it-song-12-draft.txt", "cut-it-songs.txt" })
local ixt = "next 9\ncurrent 3\nchosen 2\nsong 3\nsong 1\nsong 5\nsong 7\nsong 3\nset friday at the bell\n"
  .. "entry 7 go\nentry 1 next-bar\nentry 4 go\nentry 3 shuffle\nset\nentry 1 silence\n"
local ix = R.parse_index(ixt)
equal("the index read: next, current, chosen, the songs in order, each once",
      { ix.next, ix.current, ix.chosen, ix.songs }, { 9, 3, 2, { 3, 1, 5, 7 } })
equal("... each set its name and entries; a starts it does not know is silence, a set with no "
      .. "name set 1", { ix.sets[1].name, #ix.sets[1].entries, ix.sets[1].entries[4].starts,
      ix.sets[2].name }, { "friday at the bell", 4, "silence", "set 1" })
equal("an index with no song in it, or none, is no index",
      { R.parse_index("next 2\nset a\n"), R.parse_index(nil) }, {})

print("\n--- several songs: the load ---")
local function load3(ixtext)
  local s3 = R.new()
  local out = R.load(s3, songtext("song 1", { "a", "b" }, 100), songtext("song 1", { "a", "b" },
    100), ixtext or ixt, {
      [3] = { songtext("night drive", { "intro" }, 90), songtext("night drive", { "intro" }, 90) },
      [7] = { songtext("lantern", { "x", "y", "z" }, 140), songtext("lantern", { "x" }, 140) } })
  return s3, out
end
st, out = load3()
equal("the songs in the index's order, a song it names with no files gone",
      snames(st), { "night drive", "song 1", "lantern" })
equal("the song loaded last loads, its section 1 starting", { st.cur.id, restores(out) },
      { 3, { "drums 1", "tempo 90" } })
equal("the setlist chosen, its entries whose songs are there, in order",
      { st.set, st.sets[1].name, entries(st) }, { 2, "friday at the bell", { "song 1 silence" } })
st.set = 1
equal("... the other's: an entry naming a song that's gone is gone too",
      entries(st), { "lantern go", "song 1 next-bar", "night drive silence" })
equal("each song its own draft against its save: lantern's differs", { st.songs[3].unsaved,
      st.songs[2].unsaved, R.unsaved(st) }, { true, false, false })
equal("... nothing to write but the index, which lost a song", { st.index_dirty, st.dirty,
      st.write_saved }, { true, false, false })
equal("the next new song is 9, past every id", st.next_song, 9)
st = load3("next 2\ncurrent 5\nsong 7\nsong 3\n")
equal("a current the index lacks: the first song loads; no set: set 1, empty but for its first song",
      { st.cur.id, #st.sets, entries(st) }, { 7, 1, { "lantern silence" } })
st = R.new()
R.put(st, { "drums", 4 })
R.load(st, nil, nil, "next 3\ncurrent 2\nsong 2\n", {})
equal("an index whose songs all have no files: the one song before there were several",
      { snames(st), st.cur.id, st.index_dirty }, { { "song 1" }, 1, true })

print("\n--- the songs tab: new, name, add to set, delete ---")
st = load3()
R.song_select(st, 3)
equal("a row tapped selects that song, and loads nothing", { st.sel_song.song.name, st.cur.id },
      { "lantern", 3 })
R.song_select(st, 1)
R.put(st, { "tempo", 95 })
local wrote = st.index_dirty
st.index_dirty = false
R.song_new(st)
equal("new song: after the selected, named song 2, selected, and not loaded",
      { snames(st), st.sel_song.song.name, st.cur.id }, { { "night drive", "song 2", "song 1",
      "lantern" }, "song 2", 3 })
local new = st.sel_song
equal("... one section, a copy of the section playing, its parts as they are now",
      { #new.song.sections, new.song.sections[1].name, new.song.sections[1].parts.tempo },
      { 1, "intro", { 95 } })
equal("... saved as it is, both its files to write, its id the next, and the index",
      { R.differs(new.song, new.saved), new.write_saved, new.id, st.next_song, st.index_dirty },
      { false, true, 9, 10, true })
R.song_new(st)
equal("another is song 3", st.sel_song.song.name, "song 3")
R.song_select(st, 2)
R.song_rename(st, { "Hollow", "Bell" })
equal("the name tab's done renames the selected song, its draft and its save at once",
      { snames(st)[2], new.song.name, new.saved.name, R.differs(new.song, new.saved),
        new.write_saved }, { "hollow bell", "hollow bell", "hollow bell", false, true })
R.song_select(st, 1)
st.write_saved = false
R.song_rename(st, { "night ride" })
equal("... the song loaded too, its files written at once, nothing unsaved",
      { st.song.name, st.saved.name, st.write_saved, R.unsaved(st) },
      { "night ride", "night ride", true, true })
equal("... a name with nothing in it changes nothing", { R.song_rename(st, { "!" }),
      st.song.name }, { {}, "night ride" })
R.song_select(st, 2)
st.set = 1
R.song_add(st)
equal("add to set: the selected song the setlist's last, from silence, and selected",
      { entries(st), st.entry }, { { "lantern go", "song 1 next-bar", "night ride silence",
      "hollow bell silence" }, 4 })
for _ = 1, 21 do R.song_add(st) end
equal("a setlist holds 25, a song a key", { #st.sets[1].entries, R.song_add(st) },
      { 25, { { "err", "warn", { "u_song", "set-full" } } } })
for _ = 1, 21 do st.entry = 5; R.entry_remove(st) end
st.removed = {}
R.song_select(st, 4)
out = R.song_delete(st)
equal("delete: the selected song goes, from the list and every setlist, and the one in its "
      .. "place is selected", { out, snames(st), entries(st), st.sel_song.song.name },
      { {}, { "night ride", "hollow bell", "song 3", "lantern" }, { "lantern go",
      "night ride silence", "hollow bell silence" }, "lantern" })
equal("... its files to go", st.removed, { 1 })
R.song_select(st, 1)
out = R.song_delete(st)
equal("⛔ deleting the song loaded loads the one now in its place, at once, and says so",
      { restores(out), out[1], st.cur.song.name }, { { "drums 1", "tempo 95" }, { "err", "info",
      { "u_song", "loaded-hollow-bell" } }, "hollow bell" })
for _ = 1, 2 do R.song_delete(st) end
equal("⛔ there is always a song: deleting the last is warn u_song last-song",
      R.song_delete(st), { { "err", "warn", { "u_song", "last-song" } } })

print("\n--- the keys: stopped, a song loads at once ---")
st = load3()
st.set = 1
R.put(st, { "tempo", 77 })
equal("night drive changed: unsaved", R.unsaved(st), true)
out = R.key(st, 1)
equal("key 1, the opener, stopped: lantern loads at once, its section 1 started, the log told",
      { out[1], restores(out), st.cur.song.name, R.index(st, st.playing) },
      { { "err", "info", { "u_song", "loaded-lantern" } }, { "drums 1", "tempo 140" }, "lantern",
        1 })
equal("... its own draft, differing from its save: unsaved", R.unsaved(st), true)
equal("⛔ night drive keeps its change as its own draft: unsaved, its draft to write",
      { st.songs[1].unsaved, st.songs[1].dirty, st.songs[1].song.sections[1].parts.tempo },
      { true, true, { 77 } })
out = R.key(st, 3)
equal("⛔ key 3 loads night drive again: its change still there, unsaved, save and revert lit",
      { restores(out), R.unsaved(st) }, { { "drums 1", "tempo 77" }, true })
equal("the song loaded, its section 1 playing, asked for while stopped: nothing to do",
      R.key(st, 3), {})
equal("a key past the setlist's end does nothing", { R.key(st, 4), R.key(st, 25), st.cur.id },
      { {}, {}, 3 })
equal("revert on night drive takes its change back", { restores(R.revert(st)), R.unsaved(st) },
      { { "drums 1", "tempo 90" }, false })

print("\n--- the keys: playing, by each entry's transition ---")
st = load3()
st.set = 1
R.start(st)
out = R.key(st, 3)
equal("silence: the transport stopped, nothing loaded yet", { out, st.cur.id },
      { { { "stop", "bang", {} } }, 3 })
equal("... the song shows as queued, the go lamp too", R.go_lamp(st), R.GO_QUEUED)
out = R.stop(st)
equal("⛔ ... and the STOP that comes back loads it, ready for PLAY", { restores(out), st.cur.id,
      st.running, R.go_lamp(st) }, { { "drums 1", "tempo 90" }, 3, false, R.GO_DARK })
R.start(st)
equal("next bar: nothing at once", { R.key(st, 2), st.cur.id }, { {}, 3 })
equal("... queued: the go lamp blinks as a queued section's", R.go_lamp(st), R.GO_QUEUED)
out = at_one(R.bar(st))
equal("⛔ ... and it loads as the pattern comes round", { out[1], restores(out), st.cur.id },
      { { "err", "info", { "u_song", "loaded-song-1" } }, { "drums 1", "tempo 100" }, 1 })
R.press(st, 4)
R.key(st, 1)
equal("go: nothing at once, a section queued as well", { st.cur.id, R.index(st, st.queued) },
      { 1, 2 })
equal("... the go lamp says it waits for go", R.go_lamp(st), R.GO_WAIT)
equal("⛔ the bar starts the section queued, and the song waits on, the last song playing on",
      { restores(at_one(R.bar(st))), st.cur.id, R.go_lamp(st) }, { { "drums 2", "tempo 100" }, 1,
      R.GO_WAIT })
equal("go pressed: the song now waits for the bar", { R.go_button(st), R.go_lamp(st) },
      { {}, R.GO_QUEUED })
R.press(st, 3)
equal("⛔ the next bar loads it, ahead of a section queued since", { restores(at_one(R.bar(st))),
      st.cur.id, st.queued }, { { "drums 1", "tempo 140" }, 7, nil })
equal("go with no song waiting does nothing", { R.go_button(st), R.go_lamp(st) },
      { {}, R.GO_DARK })
R.key(st, 1)
R.key(st, 2)
equal("one song queued at a time: the next key takes the queue's place", st.pending.rec.id, 1)
R.key(st, 1)
equal("⛔ STOP with a song waiting for go: no bar is coming, so it loads now",
      { restores(R.stop(st)), st.cur.id }, { { "drums 1", "tempo 140" }, 7 })
R.start(st)
R.key(st, 2)
R.press(st, 4)
equal("the song loaded asked for again starts again from its section 1, at the bar",
      { restores(at_one(R.bar(st))), st.cur.id }, { { "drums 1", "tempo 100" }, 1 })

print("\n--- a section starts on the 1 ---")
-- The old section's last step plays out at its own tempo (Brendan, 2026-11-05): "the next section
-- begins just a fraction of a second too early".
st = R.new()
st.song.sections[1].parts = { drums = { 1 }, tempo = { 100 }, programs = { "none" } }
st.running, st.queued = true, st.song.sections[1]
equal("⛔ the bar, running: the pattern now, and the tempo and programs held for step 1",
      restores(R.bar(st)), { "drums 1" })
equal("⛔ ... and step 1 lets them go", restores(R.one(st)), { "programs none", "tempo 100" })
equal("... once", R.one(st), {})
st.running, st.queued = false, st.song.sections[1]
equal("⛔ stopped, everything at once", restores(R.stop(st)),
      { "drums 1", "programs none", "tempo 100" })

print("\n--- the songs tab's load ---")
st = load3()
st.set = 1
R.start(st)
R.song_select(st, 3)
equal("load: the selected song by its entry's transition in the setlist chosen: lantern, go",
      { R.song_load(st), R.go_lamp(st) }, { {}, R.GO_WAIT })
st.set = 2
equal("... a song in no entry of the setlist chosen starts from silence", R.song_load(st),
      { { "stop", "bang", {} } })

print("\n--- the setlists tab ---")
st = load3()
st.set = 1
R.entry_select(st, 2)
R.entry_starts(st, "go")
equal("a row tapped selects the entry; starts sets how it starts", entries(st),
      { "lantern go", "song 1 go", "night drive silence" })
equal("... a starts it does not know is fail u_song bad-starts", R.entry_starts(st, "soon"),
      { { "err", "fail", { "u_song", "bad-starts" } } })
R.songs_cmds.up(st)
equal("move up: the entry a place earlier, its key with it, still selected",
      { entries(st), st.entry }, { { "song 1 go", "lantern go", "night drive silence" }, 1 })
equal("... from the top, nothing", { R.songs_cmds.up(st), st.entry }, { {}, 1 })
R.songs_cmds.down(st)
R.songs_cmds.down(st)
equal("move down, twice", { entries(st), st.entry }, { { "lantern go", "night drive silence",
      "song 1 go" }, 3 })
equal("⛔ the keys follow the order: key 3 is song 1 now", (function()
  R.start(st); R.key(st, 3); return st.pending.rec.id end)(), 1)
R.stop(st)
R.entry_remove(st)
equal("remove: the entry goes, and the one now in its place, here the last, is selected",
      { entries(st), st.entry }, { { "lantern go", "night drive silence" }, 2 })
R.set_new(st)
equal("new set: an empty setlist after the one chosen, set 2, chosen",
      { #st.sets, st.set, st.sets[2].name, entries(st), st.entry }, { 3, 2, "set 2", {}, 0 })
equal("... the keys play nothing from it", R.key(st, 1), {})
R.set_rename(st, { "Saturday" })
equal("its name from the name tab", st.sets[2].name, "saturday")
for _, id in ipairs({ 3, 1, 7, 3, 1, 7, 3 }) do
  st.sel_song = (function() for _, r in ipairs(st.songs) do if r.id == id then return r end end end)()
  R.song_add(st)
end
equal("seven entries: two pages", { #st.sets[2].entries, st.set_page, R.songs_phone(st)[28] },
      { 7, 2, 2 })
st.set_page = 1
R.set_turn(st, 1)
equal("the arrows go through a setlist's own pages first", { st.set, st.set_page }, { 2, 2 })
R.set_turn(st, 1)
equal("... then on to the next, which is then the one chosen, its first entry selected",
      { st.set, st.set_page, st.entry, st.sets[st.set].name }, { 3, 1, 1, "set 1" })
R.set_turn(st, 1)
equal("... and no further than the last", { st.set, st.set_page }, { 3, 1 })
R.set_turn(st, -1)
equal("back: the setlist before, on its last page", { st.set, st.set_page, st.entry },
      { 2, 2, 6 })
for _ = 1, 4 do R.set_turn(st, -1) end
equal("... and no further than the first's first", { st.set, st.set_page }, { 1, 1 })

print("\n--- the songs page's state ---")
st = load3()
st.set = 1
R.start(st)
R.put(st, { "tempo", 91 })
R.key(st, 2)
R.entry_select(st, 3)
local ph = R.songs_phone(st)
equal("47 atoms", #ph, R.SONGS_PHONE)
equal("the songs tab: how many, the selected, the page and pages, the selected one's name",
      { ph[1], ph[2], ph[3], ph[4], ph[5] }, { 3, 1, 1, 1, "night drive" })
equal("... each row its number, name and words: loaded and unsaved, queued, unsaved; then none",
      { table.unpack(ph, 6, 17) }, { 1, "night drive", "loaded · unsaved", 2, "song 1", "next bar",
      3, "lantern", "unsaved", 0, "-", "-" })
equal("the setlists tab: the setlist chosen and how many, its name, the page and pages, how many "
      .. "entries, the one selected, its song and how it starts",
      { table.unpack(ph, 24, 32) }, { 1, 2, "friday at the bell", 1, 1, 3, 3, "night drive",
      "silence" })
equal("... five rows of key, song and starts", { table.unpack(ph, 33, 47) },
      { 1, "lantern", "go", 2, "song 1", "next-bar", 3, "night drive", "silence", 0, "-", "-", 0,
        "-", "-" })
R.key(st, 1)
equal("a song waiting for go says so", R.songs_phone(st)[14], "for go · unsaved")
for _ = 1, 5 do R.song_new(st) end
R.song_turn(st, 1)
ph = R.songs_phone(st)
equal("eight songs: the second page, the seventh and eighth", { ph[3], ph[4], ph[6], ph[9],
      ph[12] }, { 2, 2, 7, 8, 0 })

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
equal("init: the lamps, the go lamp and the phone's two states, once each, then the proof bang",
      { sent[1], sent[2], sent[3], sent[4][1], sent[4][2], sent[5][2], sent[6], #sent },
      { { 1, "top", { D, D, P, D, D, D, D, D } }, { 1, "unsaved", { 0 } }, { 1, "go", { 0 } }, 2,
        "list", "songs", { 5, "bang", {} }, 6 })
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

-- Several songs on disk: song 1 as it was before there were several, then a song made, loaded
-- from a key and a flush of each, a reload, and a song deleted.
tmp = os.tmpname()
os.remove(tmp)
assert(os.execute("mkdir -p " .. tmp))
local function put_file(name, text)
  local w = assert(io.open(tmp .. "/" .. name, "w"))
  w:write(text)
  w:close()
end
local function songs_state(sent)
  for _, e in ipairs(sent) do if e[1] == 2 and e[2] == "songs" then return e[3] end end
end
local one = "song song 1\nsection 1 0 intro\ndrums 1\ntempo 100\n"
put_file("cut-it-song.txt", one)
put_file("cut-it-song-draft.txt", one)
o = T.new(class, { tmp })
T.send(o, 3, "init", {})
sent = T.send(o, 3, "load", {})
equal("⛔ a state directory from before several songs: its one song is song 1, as it stands",
      { o.state.cur.id, o.state.song.name, #o.state.songs, file("cut-it-songs.txt") },
      { 1, "song 1", 1 })
T.send(o, 3, "flush", {})
equal("... and the first flush writes the index, song 1 the first setlist's opener",
      file("cut-it-songs.txt"), "next 2\ncurrent 1\nchosen 1\nsong 1\nset set 1\nentry 1 silence\n")
equal("... song 1's files as they were", { file("cut-it-song.txt"), file("cut-it-song-draft.txt") },
      { one, one })
sent = T.send(o, 2, "songs", { "new" })
equal("⛔ songs new, from the phone: the songs page's state, two songs, the new one selected, "
      .. "after a sync", { sent[1], songs_state(sent)[1], songs_state(sent)[5] },
      { { 3, "sync", {} }, 2, "song 2" })
equal("... its two files written at once, named for its id",
      { file("cut-it-song-2.txt"), file("cut-it-song-2-draft.txt") },
      { "song song 2\nsection 1 0 intro\ndrums 1\ntempo 100\n",
        "song song 2\nsection 1 0 intro\ndrums 1\ntempo 100\n" })
T.send(o, 2, "songs", { "add" })
T.send(o, 3, "put", { "tempo", 120 })
sent = T.send(o, 1, "key", { 2 })
equal("key 2, stopped: song 2 loads, its section 1 restored", sent[3], { 3, "restore",
      { "drums", 1 } })
equal("... and the lamps: dark, since song 2 is as saved", lamps(sent), { { 1, "unsaved", { 0 } } })
T.send(o, 3, "flush", {})
equal("⛔ the flush writes song 1's draft, its change kept, and the index, song 2 loaded",
      { file("cut-it-song-draft.txt"), file("cut-it-song.txt"), file("cut-it-songs.txt") },
      { "song song 1\nsection 1 0 intro\ndrums 1\ntempo 120\n", one,
        "next 3\ncurrent 2\nchosen 1\nsong 1\nsong 2\nset set 1\nentry 1 silence\n"
        .. "entry 2 silence\n" })
o2 = T.new(class, { tmp })
T.send(o2, 3, "init", {})
sent = T.send(o2, 3, "load", {})
local ss = songs_state(sent)
equal("⛔ a reload: both songs, song 2 loaded, song 1 unsaved", { o2.state.cur.id, ss[7], ss[8],
      ss[10], ss[11] }, { 2, "song 1", "unsaved", "song 2", "loaded" })
sent = T.send(o2, 1, "key", { 1 })
equal("⛔ key 1 loads song 1 again, its change still unsaved: save and revert lit",
      { lamps(sent), o2.state.song.sections[1].parts.tempo }, { { { 1, "unsaved", { 1 } } }, { 120 } })
sent = T.send(o2, 2, "songs", { "select", 2 })
sent = T.send(o2, 2, "songs", { "delete" })
equal("songs delete: song 2's files go", { file("cut-it-song-2.txt"), file("cut-it-song-2-draft.txt"),
      songs_state(sent)[1] }, { nil, nil, 1 })
T.send(o2, 2, "songs", { "set", 1 })
equal("an unknown songs command is fail u_song bad-selector",
      T.send(o2, 2, "songs", { "shuffle" }), { { 3, "sync", {} }, { 4, "fail",
      { "u_song", "bad-selector" } } })
T.send(o2, 3, "start", {})
T.send(o2, 2, "songs", { "new" })
T.send(o2, 2, "songs", { "add" })
T.send(o2, 2, "songs", { "starts", "go" })
sent = T.send(o2, 1, "key", { 2 })
equal("⛔ playing, a key whose entry starts on go: the go lamp waits, nothing loads",
      { sent[2], o2.state.cur.id }, { { 1, "go", { 1 } }, 1 })
sent = T.send(o2, 1, "go", {})
equal("go: the lamp says queued for the bar", sent[2], { 1, "go", { 2 } })
sent = T.send(o2, 3, "bar", {})
equal("⛔ the bar: the parts asked to sync, since it moves the song, then the song loads, the log says "
      .. "which, and the lamp goes dark",
      { sent[1], sent[2], o2.state.cur.id,
      (function() for _, e in ipairs(sent) do if e[2] == "go" then return e[3][1] end end end)() },
      { { 3, "sync", {} }, { 4, "info", { "u_song", "loaded-song-2" } }, 3, 0 })
T.send(o2, 2, "songs", { "entry", 1 })
sent = T.send(o2, 1, "key", { 1 })
equal("⛔ a key whose entry starts from silence, playing: a bang to the stop bus, out the sixth",
      { sent[2], o2.state.cur.id }, { { 6, "bang", {} }, 3 })
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
