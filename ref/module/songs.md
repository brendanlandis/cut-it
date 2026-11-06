<!-- schema: module -->
# Songs and sections

**Files:** `Cut It/u_song.pd`, `Cut It/u_song.lua`, `Cut It/u_song-lua.pd_lua` · **Gate:** `test/gate/song-assert.sh`, `test/gate/phone-assert.sh`, `test/gate/touchosc-assert.sh` · **Checklist:** `test/checklists/sections.md`, `test/checklists/songs.md`

## What it is

**`u_song` is the songs: each one's sections, its draft and its saved song; the one loaded, which
of its sections plays and which is queued; and the setlists.** A song is a name and a list of
sections; a section is a name, a length in bars (0 loops) and **its parts**: what each part of the
instrument put while that section played, under the part's own key. The Launchpad's top row plays
the loaded song's sections, its bottom rows' rightmost buttons save and revert, and the phone's
sections page makes, orders, names and sets them; **the Organelle's keys load songs** from the setlist
chosen, and the next arrow goes on to the next, and the phone's songs page makes, loads, names and arranges songs
into setlists (`cut-it/songs-and-sections`). **A song also holds what all its sections share, under each part's key**:
its voices ([voices.md](voices.md)).

**The one decision this page turns on: the store knows nothing about what a part's key means**,
as `u_state` knows nothing ([state.md](state.md)). A part stores itself per section by putting
`put section <key> <atoms…>` on the `state` bus, which lands in the section playing, and a section
starting sends every part it holds back as `restore <key> <atoms…>`, which the part takes as it
takes any restore, and puts back only what differs from what it holds. A part added later is per section from its first version
with no change here.

**The whole song is one draft** (Brendan, 2026-11-04). Edits play at once and stay with their
section as the song moves; **save** writes every section and the song, **revert** takes them all
back to the last save, and their two lamps are lit only while the draft differs from the save
(Brendan, 2026-11-05). The draft is written to the SD card as it changes, so a crash or a power cut
loses at most its last two seconds. **Each song keeps its own draft** (Brendan, 2026-11-05):
loading another with changes unsaved leaves them as that song's draft, and coming back finds them
there, save and revert lit.

## Facts

### The section policy on the `state` bus

`u_state` routes `put auto` and `put manual` and drops anything else, so `put section` reaches
`u_song` alone; the two never share a key.

| Direction | Message | Meaning | Evidence |
|-----------|---------|---------|----------|
| a part → `u_song` | `put section <key> <atoms…>` | The part as it is now, into the section playing. The same atoms again change nothing | unknown |
| `u_song` → all | `restore <key> <atoms…>` | A section starting: every part it holds, in the keys' order, each once | unknown |
| a part → `u_song` | `put section <key> <atoms…>` | The part put back during the restore if it differs, a line in an older shape, say: it lands in the section now starting | unknown |
| a part → `u_song` | `put song <key> <atoms…>` | The part as it is now, into the song itself: every section shares it. It shows as unsaved, and save and revert keep it, as they do a section's. Restored as `restore <key> <atoms…>` when the song loads or reverts | unknown |
| a part → `u_song` | `put seed <key> <atoms…>` | What a song that holds none starts as: into the song and what's saved of it together, so it shows as nothing unsaved | unknown |

### The parts a section holds

Each part puts at load and on every change, and takes its restore.

| Key | Part | Atoms | Evidence |
|-----|------|-------|----------|
| `perform` | `u_perform` | The controls in play: each one's physical control, destination, arg, row and value, five atoms ([voices.md](voices.md)). A section with none is told so, `restore perform` with nothing after it, first of all, or the last section's would stay | unknown |
| `drums` | `c_steps` | The pattern, 581 numbers: 512 velocities, each track's own last step, randomness, volume and pitch, the time signature, the drunkenness, the swing and the global last step ([sequencer.md](sequencer.md)) | unknown |
| `melody`, `melody-2` | `c_melody`, each engine's | The generator, `R.save`'s numbers: its controls, the 32 steps, the 8 chords and the fields added later ([synths.md](synths.md), *The generator*). Its restore waits for step 1, as the tempo's and the programs' do | unknown |
| `programs` | `c_synth` | The Volca's program, then the Streichfett's: 0 to 127, or `none` ([synths.md](synths.md)) | unknown |
| `synth` | `c_synth` | `fm` or `strings` | unknown |
| `tempo` | `u_tempo` | The BPM, as the tempo bus carries it ([tempo.md](tempo.md)) | unknown |
| A part asked back | `recall <key>` on the third inlet, from `c_steps`, `pad-38`'s `recall tempo` (Brendan, 2026-11-05): the part as the saved song holds it in the section playing, or for a section never saved, or a part its save didn't hold, the draft's, back out as `restore <key> <atoms...>`, the way a section starting sends it. It still knows nothing of what a key means. The part puts back what it restores, so the draft takes it like any change. A part nobody holds sends nothing | verified |
| `velocity` | `c_synth` | `on` or `off` | unknown |

### The parts a song holds

Lines between `song` and the first `section` in its file. Sent on load and on revert, after the section's.

| Key | Part | Atoms | Evidence |
|-----|------|-------|----------|
| `voices` | `u_voices` | The eight rows, name, method and machine each, `-` for one with none, 24 atoms ([voices.md](voices.md)). A song with none is told so, `restore voices` with nothing after it, and is given the seed's | unknown |

### The interface

| | Is | Evidence |
|---|---|---|
| Creation arg 1 | The state directory, `u_state`'s: the songs' list and the setlists are `cut-it-songs.txt` there, and each song is two files (*The files*, below) | unknown |
| Inlet 1 | From `u_map`'s fifth outlet: `top <1-8>`, a top-row button's press, `save` and `revert`, `key <1-25>`, an Organelle key's press ([map.md](map.md)) | unknown |
| Inlet 2 | From `u_net`'s fourth outlet: the phone's sections page, `select <n>`, `page <-1 or 1>`, `new`, `saveas`, `up`, `down`, `length <bars>`, `delete`, `name <name>`; and its songs page, `songs <command> …` ([phone.md](../device/phone.md)) | unknown |
| Inlet 3 | `bar`, from `c_steps`' fourth outlet, on the global loop's last step | unknown |
| Inlet 4 | A bang meaning load now, from `u_init` after `u_state`'s restore, through a trigger in `u_root`: startup order is `u_init`'s | unknown |
| Outlet 1 | To `g_grid`'s state inlet: `top <8 lamps>` and `unsaved <0 or 1>`, each when it changes ([display.md](display.md)) | unknown |
| Outlet 2 | To `u_net`'s fifth inlet, each when it changes: the sections page's state, 22 atoms as a list, and the songs page's, `songs <47 atoms>` | unknown |
| Buses | Hears `state` (`put section`, `put song`, `put seed`), `start`, `stop` and `panic`; says `restore` on `state`, and on `err` `info u_song saved`, `reverted` and `loaded-<name>`, `warn u_song last-section`, `last-song` and `set-full`, `fail u_song bad-button`, `bad-put`, `bad-selector`, `bad-starts`, `lua-<selector>`, `write-failed` and `no-lua` (C-12) | unknown |

### The top row

| Button | CC | Does | Lamp | Evidence |
|--------|----|------|------|----------|
| 1 | 91 | Back a section from the one queued, or else the one playing | Dim, palette 1, while there is one that way | unknown |
| 2 | 92 | Forward a section, the same way | The same | unknown |
| 3–8 | 93–98 | The six section buttons: the section each shows | A section dim green, RGB 0, 32, 8; the one playing full green, 0, 127, 32; the one queued full and dark by turns, a beat each; none dark | unknown |

| | | Evidence |
|---|---|---|
| A press while the transport is stopped | Starts the section at once; the section playing, pressed again, does nothing | unknown |
| A press while it runs | Queues the section for the next bar; a second press queues another instead, and the section playing, pressed, is queued to start again | unknown |
| The six buttons' window | Moves as little as it can, a section at a time: the playing section always in it, a queued one too where both fit. Playing the seventh of ten, button 3 shows section 2 and button 8 section 7 (Brendan, 2026-11-02) | unknown |
| A button with no section | Does nothing | unknown |
| STOP or panic with a section queued | No bar is coming, so the queued section starts at once | unknown |

### Bars and lengths

| | | Evidence |
|---|---|---|
| A bar | **The pattern's loop** (Brendan, 2026-11-05): `c_steps` says `bar` on the step its global loop wraps after, so a queued section starts when the global last step comes round, the whole pattern played. The time signature has no part in it | unknown |
| When a section starts on a bar | On the last step of the old loop, in the same logical instant, so its restore reaches `c_steps` before the next step is cut: the new section's step 1 | unknown |
| A bar that moves the song | The face sends `sync` first, `R.moves_at_bar`, so what `c_melody` has drifted lands in the section ending | unknown |
| A section's drums restored | Every loop, the global one and each track's, starts again at step 1 on the next step, as PLAY starts the pattern, whatever last step the section before had | unknown |
| A length | Bars, each the section's own loop; 0 is loop, the phone drags 0 to 64. A section with a length counts its bars from its start, or from PLAY, and at the end of its last starts the next by itself | unknown |
| The last section with a length | Has no next, and plays on as a loop until another is queued | unknown |
| A press during a section with a length | Still jumps, at the next bar | unknown |

### Save and revert

| | | Evidence |
|---|---|---|
| Save, CC 108 (the upper bottom row's rightmost) | The draft becomes the saved song, both files written at once, and `info u_song saved`. With nothing unsaved, nothing | unknown |
| Revert, CC 8 (the lowest row's rightmost) | Every section back to the save, at once: the section playing starts again from it, or the one now in its place if it was new, and `info u_song reverted`. With nothing unsaved, nothing | unknown |
| Their lamps | Lit only while the draft differs from the save: save red, RGB 127, 0, 0, revert gray, 40, 40, 40; dark otherwise (Brendan, 2026-11-05) | unknown |
| Unsaved | The song's sections' order, or a section's name, length or any part differing from the save; a change put back to what was saved is saved again. A song's own name is not a change to it: naming one renames its draft and its save at once (*A song's name is what it is called*, below) | unknown |
| Another song loaded | The song left keeps its draft as it stands, unsaved changes and all, written to its own draft file within 2 s; the lamps show the song loaded now (Brendan, 2026-11-05) | unknown |

### The files

| | | Evidence |
|---|---|---|
| Where | `/sdcard/cut-it-state/` on the device, beside `u_state`'s files, so a deploy, `--clean` and a power cycle leave them; `main-dev.pd`'s directory on the Mac | unknown |
| `cut-it-songs.txt` | The index: the songs in the songs tab's order, the song loaded, the setlist chosen and the setlists, written within 2 s of a change | unknown |
| `cut-it-song.txt`, `cut-it-song-<id>.txt` | A song saved, written at a save; song 1's keeps the name the one song had before there were several, and every other's is named for its id (`R.files`) | unknown |
| `cut-it-song-draft.txt`, `cut-it-song-<id>-draft.txt` | Its draft, written within 2 s of a change, and at a save | unknown |
| A new song, a song renamed | Both its files, at once | unknown |
| A song deleted | Both its files removed, at once, and the index without it within 2 s | unknown |
| A write | Into a `.tmp` beside the file, then renamed over it, so a cut mid-write leaves the last good file; a failure is `fail u_song write-failed` | unknown |
| The load | At ~3.5 s, after `u_state`'s restore. Every song the index names, each its draft playing, or with no draft its saved song; a song with neither file is gone. With no index, the one song from before there were several: song 1, from `cut-it-song.txt` and its draft as they stand, the opener of a setlist named set 1; with no file at all, the one section the parts put into since load, saved as it is, so a fresh load has one section and nothing to save. The song loaded last loads again, at section 1 | unknown |

The index, a line a record:

```
next 4                     the id the next new song takes
current 2                  the song loaded
chosen 1                   the setlist chosen, 1 the first
song 1                     the songs, in the songs tab's order
song 3
song 2
set friday at the bell     a setlist, its name to the end of the line, then its entries in order:
entry 2                    entry <song id>
entry 3 next-bar
```

One song file is one song, a line a record, read and written by the Lua face, plain text anyone can read:

```
song song 1
section 1 8 intro          section <id> <length> <name>, the name to the end of the line
drums 95 0 0 …             <key> <atoms…>, every part of the section above, keys in order
programs none none
synth fm
tempo 120
velocity on
section 2 0 verse 2
…
```

The id ties a section of the draft to the same section of the saved song, so a reordering or a
rename is seen as one. A number is written whole, or with `%g` as Pd's own `[text]` writes a float.

### The sections page, on the phone

| | | Evidence |
|---|---|---|
| The state | `/cutit/sections`: the song's name, how many sections, the one selected, the page and how many, the selected one's name and length, then five rows of number, name and length, `0 - 0` for a row with none; 22 atoms, sent when they change and on every heartbeat | unknown |
| The selection | The phone's, held here: what `new`, `up`, `down`, `length`, `delete` and `name` act on. Playing a section stays the top row's | unknown |
| `new` | A copy of the selected section, after it, named after it, "verse" to "verse 2", the first number from 2 the song does not have, and selected | unknown |
| `saveas` | What's playing, as it stands, becomes a new section after it, named after it, playing and selected, and nothing heard changes. The section it was goes back to what it holds as saved, so playing around leaves it as it was; one never saved keeps what it has (Brendan, 2026-11-06) | verified |
| `up` and `down` | The selected section a place earlier or later; the one playing and the one queued keep playing and queued | unknown |
| `delete` | The selected section goes and the one now in its place is selected; a song keeps one section, so the last is `warn u_song last-section`; deleting the one playing starts the one now in its place, at once | unknown |
| `name` | The name tab's done: the selected section renamed. A name is lowercase, A to Z, 0 to 9, space, - and ', single spaces, at most 20 characters | unknown |

### Songs and setlists

| | | Evidence |
|---|---|---|
| A setlist | A name and up to 25 entries, each a song; the same song may be in it twice. One is chosen at a time, the one the setlists tab shows (Brendan, 2026-11-05) | unknown |
| The keys | Key N, from the lowest, `og-key-60`, is the Nth entry of the setlist chosen: moving an entry moves its song to another key. A key past the setlist's end does nothing; a press counts, a release nothing (Brendan, 2026-11-05) | unknown |
| Stopped | A key loads its song at once: nothing is playing to start after. The song loaded, at its section 1 already, is nothing to do | unknown |
| Playing | The song waits for the pattern to come round, as a queued section does, and loads on its step 1 | unknown |
| The next arrow | CC 92 on a song's last section is blue and asks for the setlist's next song, as its key would, whichever entry the song was loaded from; dark on the setlist's last, or for a song not in it. A song queued makes it blink on the beat, whatever asked, and CC 91 takes that song back (Brendan, 2026-11-06). A song to start from silence: STOP, the arrow, which loads at once, then PLAY ([display.md](display.md)) | unknown |
| One queued at a time | A key asked while a song waits takes its place. At the bar a song queued goes before a section queued, which is dropped | unknown |
| STOP or panic with a song waiting | No bar is coming, so it loads at once | unknown |
| The song loaded, asked for again | Starts again from its section 1 | unknown |
| A load | `info u_song loaded-<name>`, logged; nothing on the OLED, which is for alerts and warnings (Brendan, 2026-11-04) | unknown |

### The songs page, on the phone

| | | Evidence |
|---|---|---|
| The state | `/cutit/songs`: the songs tab's how many songs, the one selected, the page and how many and the selected one's name, then six rows of number, name and words; then the setlists tab's setlist chosen and how many, its name, its page and how many, how many entries, the one selected, its song and how it starts, then five rows of key, song and starts, `0 - -` for a row with none; 47 atoms, sent when they change and on every heartbeat | unknown |
| A song's words | `loaded`, `next bar` while it waits, and `unsaved` while its draft differs from its save, joined by a middle dot; `-` for none | unknown |
| The selections | The phone's, held here: the song selected for `load`, `name`, `add` and `delete`, the entry selected for `up`, `down` and `remove` | unknown |
| `load` | The selected song, as a key asks for it | unknown |
| `new` | A song after the selected, "song 2", the first number from 2 no song has, of one section: a copy of the section playing, its name, length and parts. Saved as it is, selected, and not loaded | unknown |
| `add` | The selected song, the setlist chosen's last entry, from silence, and selected; past 25, `warn u_song set-full` | unknown |
| `delete` | The selected song goes, from every setlist too, its files with it, and the one now in its place is selected; the last song is `warn u_song last-song`; deleting the song loaded loads the one now in its place, at once. The phone asks twice (*Delete asks twice*, below) | unknown |
| `entry`, `up`, `down`, `remove` | A row tapped selects an entry; move up and down move it and its key; remove takes it out, the one now in its place selected | unknown |
| `set` | The arrows: through the setlist chosen's own pages, then on to the next setlist, or back to the last page of the one before, which is then chosen, its first entry on the page selected | unknown |
| `new-set` | An empty setlist after the one chosen, "set 2" the same way as songs, and chosen | unknown |
| `name`, `set-name` | The name tab's done: the selected song, or the setlist chosen, renamed. A name is cleaned as a section's is | unknown |

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The songs, the setlists, the song loaded and the one waiting, the sections, playing and queued, the window, the bars, the drafts against the saves, the files' text | `u_song.lua`: a state table and a function per rule, each returning what leaves | verified |
| Reading and writing the files, the lamps and the phone's states sent when they change | `u_song-lua.pd_lua`, the class `u_song-lua`: three inlets (the top row, save, revert, the keys; the phone; `u_song.pd`'s own `put`, `put-song`, `seed-song`, `bar`, `start`, `stop`, `load`, `flush` and `init`), six outlets (to `g_grid`, the phone, the state bus, `err`, a bang on `init`, the stop bus). Before a press, a key, go, a phone command, `start` or `stop` it sends `sync` on the state bus, so a part holding its put back (`c_steps`, up to 100 ms, [sequencer.md](sequencer.md)) puts it first, into the section still playing of the song still loaded | verified |
| The cords, the state bus's section policy, the transport and the STOP a silence sends, the draft's 2 s timer armed by the load, the `no-lua` guard | `u_song.pd` | verified |

## Traps

### A part restored must land in the section starting

⛔ A part may put back what it restores (*A contributor must put back what it restores*,
[state.md](state.md)), and that put arrives during the restore, re-entrantly. Sent before the
section changed, it would land in the section before.

**Fix:** a section starting is playing before its first restore leaves; the put then lands in it,
unchanged, and leaves nothing unsaved.

### The draft must never be written before it is read

⛔ The draft's timer armed by a `loadbang` would write the load's defaults over the last session's
draft before the restore read it, as `u_state`'s flush would (*`u_state` must never write a file it
has not yet read*, [state.md](state.md)).

**Fix:** the load bang loads, then arms the timer, off one trigger, right to left.

### A section's tempo held knob 1 even when it changed nothing

⛔ `u_tempo` takes a section's tempo as it takes the phone's, holding knob 1 there; the load's
section 1 restored the tempo already in force and held a knob that was live.

**Fix:** `u_tempo` drops a restore of the tempo in force with a spigot; one that changes the tempo
holds the knob, as the phone's does.

### A section with another last step went on counting the old loop

⛔ The next step after a section started was the old global loop's position plus one in the new
loop: from a loop of 8 into one of 32, step 9.

**Fix:** a drums restore starts every loop again at step 1 on the next step.

### A Pd float is not the file's number

⛔ A part's atoms arrive as 32-bit floats: 0.1 is 0.100000001490116, and the file says 0.1, so a
part read back from the file and put back from Pd would never compare equal, and save and revert
would light after every load.

**Fix:** the store keeps each number as the file would write it.

### A name with a space is one atom only in memory

⛔ `[oscparse]` gives the phone's "verse 2" as one symbol, and pdlua keeps it one; written through a
`[text]` and read back, it would be two atoms.

**Fix:** the Lua face reads and writes the files, a name to the end of its line; nothing in Pd
re-parses a name.

## Design

### A store keyed by part, not a part holding its sections

Each part could hold every section's copy of itself and switch on a message; then every part would
know about songs, and copying, reordering or deleting a section would be a message to each. Keyed
by part on the `state` bus, the parts keep the shape they had under `u_state` (a put on change, a
restore taken and put back), and the song's structure is one file's.

### The section policy is `u_song`'s, not a third store in `u_state`

`u_state` owns when the auto and manual stores are written; the song is not one keyed line per part
but a list of sections, written whole, with a playing section, a queue and a saved copy to compare
with. It hears the same bus for the same reason `u_state` does: so a contributor needs no cord.

### The Lua face does the file I/O

As `u_map-lua` reads the map ([map.md](map.md)). A song is a list of sections of five parts,
hundreds of atoms each, and names with spaces; Lua builds and parses the text in one place, each
part's line kept against its atoms so only what changed is formatted again, and writes it whole
with a rename. The rules stay plain Lua with no I/O, tested without Pd.

### The draft is written as it changes, like the auto store

Every change marks the draft; a 2 s timer, armed by the load, writes it when marked. At load the
draft is what plays, so a crash or a power cut comes back to where it was, with save and revert lit
if it differed from the save; save and revert act against the saved file. A fresh load, with no
song files, saves the song it starts with, so the lamps start dark.

### Section 1 starts at load

Not the section that was playing when the power went: a loaded song starts at its top, as one the
Organelle's keys load does.

### Stopped, a press is at once

A queue waits for a bar, and a stopped transport has none coming; so a press while stopped starts
its section at once, and STOP starts one already queued, which PLAY then plays.

### The blink is the clock's

The Launchpad flashes a pad itself, but at its own ≈118 BPM whatever the clock
(`~/Sites/!reference/novation-launchpad-pro-mk3.md`, *Lighting, two ways*). `g_grid` paints a
queued section full on the even beats of the grid's own `c_clock` and dark on the odd, a repaint a
beat already makes, so the blink keeps time with the music at no cost.

### Programs are numbers on the wire, and none until chosen

A section holds each synth's program as the program change on the wire, 0 to 127, which each
synth's layer takes as `program <n>`; `none` sends nothing. No control chooses one yet, so every
section holds `none none` until its file says otherwise.

### The auto keys before sections are read once

`c_steps` and `c_synth` still route `restore section-1-drums`, `synth` and `velocity` from
`u_state`'s auto file and put them as the section's; `u_state` then drops the old lines at its next
flush, since nothing puts them. So the pattern and the synth a rig had before sections become
section 1's at the first load after the update.

### Each song keeps its own draft

Loading a song while the one loaded has unsaved changes keeps them as that song's draft (Brendan,
2026-11-05): every song is held whole in memory, its draft and its saved copy, and the one left is
marked to be written, so its draft file has the changes within 2 s and a reload finds them. Holding
every song costs memory, not time: a load at the bar is a change of tables, with no file read on the
downbeat.

### Song 1 keeps the one song's file names

`cut-it-song.txt` and its draft are song 1's, as they stand, so a state directory from before
several songs needs nothing done to it: with no index, the load reads them as song 1 and writes an
index beside them. Every other song's files are named for its id, and an id is never reused.

### A song's name is what it is called

Naming a song renames its draft and its save together, at once (judgment call, 2026-11-05): a name
is chosen on the songs tab, often for a song not loaded, and a rename that waited for a save would
leave every song named before a gig unsaved until each was loaded and saved. A section's name is
still part of the draft, as the song's sections are.

### A new song is a copy of the section playing

One section, as the section playing is now, name and all, named "song 2" as a copied section is
"verse 2" (judgment call, 2026-11-05): what you are playing is the likeliest start of the next
song. It is not loaded: **load** does that.

### Delete asks twice

On the phone, **delete** reads sure? at the first tap and deletes at a second within three
seconds (judgment call, 2026-11-05). Its files go with it, so the phone asks; the store deletes at
the one `delete` it is sent.

### Stopped, a key loads at once

Nothing is playing to start after, so every key loads at once, as a section button starts its
section at once.

## Open

- ⬜ **No control chooses a synth's program yet**: every section holds `none none`, and a program
  is set only by editing the song's file. How a control numbers them, as each synth's own screen
  does, waits for it. `cut-it/songs-and-sections`.
- ⬜ **Not played on the rig**: the top row's lamps and presses, a queue landing at the loop, a
  length handing over, save and revert and their lamps, the phone's sections page and name tab,
  and a power cut mid-session. `test/checklists/sections.md`, `cut-it/songs-and-sections`.
- ⬜ **Several songs, the keys and the next arrow have not been played on the rig**: a song
  loading on the downbeat, the arrow's blink, the phone's songs page. `test/checklists/songs.md`,
  `cut-it/songs-and-sections`.
- ⬜ **A setlist cannot be deleted**: new set adds one, and nothing takes one away but editing the
  index. `cut-it/songs-and-sections`.
- ⬜ **The bottom rows' other fourteen, off the performance page,** have nothing yet.
  `cut-it/songs-and-sections`.
- ⬜ **The cost on the Organelle is unmeasured**: a pdlua call for each tempo a knob-1 sweep puts,
  and the draft's text built every 2 s while it changes. `cut-it/songs-and-sections`.
