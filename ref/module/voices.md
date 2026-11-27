<!-- schema: module -->
# The voices and the controls in play

**Files:** `Cut It/e_line.pd`, `Cut It/e_echo.pd`, `Cut It/c_keys.pd`, `Cut It/u_sound.pd`, `Cut It/u_sound.lua`, `Cut It/u_sound-lua.pd_lua`, `Cut It/cut-it-instruments.txt`, `Cut It/cut-it-factory.txt`, `Cut It/u_voices.pd`, `Cut It/u_voices.lua`, `Cut It/u_voices-lua.pd_lua`, `Cut It/u_perform.pd`, `Cut It/u_perform.lua`, `Cut It/u_perform-lua.pd_lua`, `Cut It/cut-it-controls.txt` · **Gate:** `test/gate/voices-assert.sh`, `test/gate/display-assert.sh` · **Checklist:** `test/checklists/launchpad.md`, `test/checklists/nanokontrol.md`

## What it is

**A row of the Launchpad is a voice, not a fixed part** (Brendan, 2026-11-06). A section has up to eight voices, one a
row, each section its own (Brendan, 2026-11-25; the song's, before). Each has a name, a behavior, what it does, and an instrument, what it does it on. **Harmony, melody and the drum page
are ways of doing something, not voices.** The button on the left is what the voice does, and the button across from it
on the right sets it up.

**`u_voices` holds the playing section's voices and the page on show, and it alone writes the `mode` bus**, a page's name as the
selector: `perform`, `drums`, `harmony`, `melody`, `keys`, `sound`, `songs` or `diag`. `u_map`, `g_grid` and `u_net`
each hear it and decide what that means to them.

**`u_perform` is what the nanoKONTROL means, section by section.** Its faders, knobs and buttons are the same on
every page: whatever this section has taken into play. It can't show anything, so the Launchpad's columns and the
phone do, and a control waits to be turned through its value after a section changes, because a fader doesn't move by
itself.

## Facts

### The page

| Press | On | Does | Evidence |
|---|---|---|---|
| A left button, CC 90 − 10 × row | A row with a voice | Its behavior's page; the lit one again, the performance page | unknown |
| | A row with none | Nothing | unknown |
| A right button, CC 99 − 10 × row | A row with a voice | `sound`, its setup; the lit one again, the performance page | unknown |
| | A row with none | `sound` for that row, with no voice yet: the phone asks what it does and on what, and nothing is made or put until its `add` (Brendan, 2026-11-25). Again, the performance page (`test/gate/lua/u_voices_test.lua`) | verified |
| aux, on the Organelle, or songs under the phone's left column | Any page | Opens `songs`; again, back where it was | unknown |
| Setup, on the Launchpad | Any page | Opens `diag`; again, back where it was. Its `pad-81` is the diagnostic layer, and `pad-82` test mode | unknown |
| PLAY | A voice's left or right page, stopped | The performance page, by itself. Not from `songs` or `diag`, and not while the transport already runs | unknown |

| | | Evidence |
|---|---|---|
| Across a power cycle | `put auto page <kind> <row>`, on every change of page; restored at boot | unknown |
| A voice's page, restored | Waits for the first section's voices, which come after the auto file; the performance page if it has no such row | unknown |
| The boot, with nothing saved | The performance page | unknown |

### What a section's voices are

| | | Evidence |
|---|---|---|
| A behavior | `drums`, `harmony`, `melody` or `keys` | unknown |
| An instrument | `kit`, on the drums; `fm`, `strings`, `sine`, `saw` or `square`, on the others | unknown |
| How many | One drums, two each of harmony and melody, what there are engines for: a third warns `too-many-harmony` and changes nothing. Keys as many as there are rows | unknown |
| A name | Lowercase, one symbol, spaces as `_`, at most 16 characters | unknown |
| Where it's saved | `put section voices <24 atoms>`, name, behavior and instrument a row, `-` for one with none, in the section playing ([songs.md](songs.md)). It shows as unsaved, as any change to a song does | unknown |
| A section with no line | Is given the seed's when it starts: row 1 `drums`, on `kit`; row 2 `chords`, harmony, on `strings`; row 3 `melody`, on `fm`. `put seed-section voices`, which is no change to the song. That is the first song of a card with none, and a song saved before sections held voices | unknown |
| A section with no voices | A line of 24 `-`: a new song's section, or one whose last voice was removed. It has none, and is given nothing (Brendan, 2026-11-25) (`test/gate/lua/u_voices_test.lua`) | verified |
| A voice added | The phone's `add <r> <behavior> <instrument>`, on a row with none: named for its behavior, `melody`, then `melody_2` where that's taken, and its setup shown. A behavior with no room left warns `too-many-<behavior>`; a word that is no behavior fails `bad-behavior`, an instrument it doesn't play `bad-instrument`; none of them makes anything (`test/gate/lua/u_voices_test.lua`) | verified |
| A new section | Copies them, as it copies every part | unknown |
| A section starting | `restore voices`, first of its parts, on step 1 while the transport runs. The same voices as the last section's say nothing. Others assign the engines and tell the rows, and the page is said again only when what it hangs on changed, its voice's behavior, instrument or engine; a page whose row is gone gives way to the performance page (`test/gate/lua/u_voices_test.lua`) | verified |
| A voice removed | The performance page, if it was on show | unknown |
| The drums voice removed, or given another behavior | Takes the section's drum pattern with it (Brendan, 2026-11-26), so a drums voice added back starts from an empty one: `clear` on `voices-drums`, and `c_steps` sets every hit and each track's own last step, randomness, mute and solo back to a blank section's and puts that, a change to the section like any other, which revert brings back. The time signature, swing, drunkenness and global last step stay, the section's clock and not the kit's, and so does the kit's sound, the song's (`test/gate/lua/u_voices_test.lua`, `test/gate/lua/c_steps_test.lua`) | verified |
| A section with no drums voice | Plays no drums, as harmony and melody play nothing with no voice of theirs (Brendan, 2026-11-26): `voiced <1 or 0>` on `voices-drums` whenever a row's being one changes, and `c_steps` plays no hit while it is 0, its playhead and loops going on. It goes by the rows, not the pattern, so a section saved with a pattern and no drums voice is quiet too. A section starting while the transport runs says it on its step 1, with its voices, and `c_steps` hears it before it decides that step, so the downbeat plays by the new section's rows (`test/gate/lua/c_steps_test.lua`) | verified |
| A voice's engine | Each harmony and melody voice by row order: the first of each engine 1's, the second engine 2's. `assign <engine> <h or m> <instrument or off>` tells each `c_melody` what it plays on; `active <engine>` which one the page's voice is in, 0 for neither, so the Launchpad, the phone and the nanoKEY reach only that one ([synths.md](synths.md)) | unknown |
| The nanoKEY | `instrument <fm or strings>` to `c_synth`, on a page whose voice is on hardware. The performance page, and a voice on a Pd instrument, leave it on the last ([synths.md](synths.md)) | unknown |

### The interface of `u_voices`

| | Is | Evidence |
|---|---|---|
| Inlet 1 | From `u_map`'s seventh outlet: `left-<r>`, `right-<r>`, `aux`, `setup`, each `<value>`; a release does nothing ([map.md](map.md)) | unknown |
| Inlet 2 | The phone's `voices`, through `u_net`: `left <r>`, `right <r>`, `aux`, `setup`, `add <r> <behavior> <instrument>`, `name <r> <words>`, `behavior <r> <m>`, `instrument <r> <m>`, `remove <r>` | unknown |
| Outlet 1 | To `g_grid`, `voices <row> <kind> <8 behaviors>`, when it changes | unknown |
| Outlet 2 | To the `c_melody`s, `assign` and `active` | unknown |
| Outlet 3 | To `c_synth`, `instrument <instrument>` | unknown |
| Outlet 4 | To `u_net`, `voices <page> <kind> <row> <24 atoms>`, sent as `/cutit/voices`, when it changes and on every heartbeat | unknown |
| Buses | Writes `mode`, `put section voices`, `put seed-section voices`, `put auto page` on `state`, `err`, `voices-rows` to `u_perform`, the row on show and each row's engine, and `voices-drums` to `c_steps`, `voiced` and `clear`. Hears `start`, `stop`, `panic` and `restore voices` and `restore page` on `state` | unknown |

### Taking a control into play

**REC arms, then the control is heard, then a physical control binds it**, and it lasts for this section
(Brendan, 2026-11-06).

| Step | | Evidence |
|---|---|---|
| Arm | `xport-6`, REC, or the phone's `perform arm`. Again, not armed | unknown |
| Heard | A control moved that `cut-it-controls.txt` names, through the map or the phone's `perform ctl <row> <dest> <arg> <value>`. Others aren't taken | unknown |
| Bound | The next physical control, one of the eight groups' `slider-<n>`, `knob-<n>`, `btn-a-<n>` and `btn-b-<n>`, takes it, where it is, live, and sends nothing. It replaces what was there | unknown |
| Removed | A name tapped on the phone, `perform remove <name>` | unknown |

**`Cut It/cut-it-controls.txt` is every control a voice's page or the master has an address for**: `<dest> <arg>
<kind> <label>` a line, the label what the phone shows. `u_map_test.lua` holds every address to one its destination
takes.

| A control's kind | A fader or knob | A button | A tap on its column | Evidence |
|---|---|---|---|---|
| `value` | Its value, 0 to 1 | Its top and back | That height, row / 8 | unknown |
| `toggle` | Flips as it passes a half | Flips | Flips | unknown |
| `hit` | Fires as it passes a half going up | Fires | Fires | unknown |

| | | Evidence |
|---|---|---|
| Where a move goes | `<dest> <arg> <value> <value> 1` on `map-route`, into `u_map`'s destination route, as a mapped control's: the same handlers, the same row on the screen | unknown |
| A generator's control | Its arg gets `e<n>-` in front, the engine of the row it was taken from, so it reaches that engine whichever voice is on show | unknown |
| Pickup | A control waits at its value after a section starts, a tap on its column, or a move of its address another way: until turned to within 0.012 of it, or through it. Waiting, it moves nothing | unknown |
| A lane on the Launchpad | Its fader, or its knob; with both, whichever moved last, and the fader until one has | unknown |

### The section's list

| | | Evidence |
|---|---|---|
| Where it's saved | `put section perform <name> <dest> <arg> <row> <value>…`, five atoms a control, in the section playing, at most every 300 ms ([songs.md](songs.md)) | unknown |
| A new section | Copies it, as it copies every part | unknown |
| A section starting | `restore perform <atoms>`: the list, each waiting. A section with none says so, an empty restore, or the last one's would stay | unknown |
| What the surfaces hear | `cols` and `btns` to `g_grid`, `perform <113 atoms>` to `u_net`, sent as `/cutit/perform`, each when it changes, at most every 40 ms | unknown |

### Instruments and patches

**`u_sound` is what each voice sounds like** (Brendan, 2026-11-06). `cut-it-instruments.txt` lists each instrument's
parameters and how each is said: a control change, a program change, a Pd voice's own or a DX7 voice of the library
(below). A **patch** is an instrument's saved sound. `cut-it-factory.txt` holds factory patches, good starting points outside any song; a song copies one and
depends on nothing after that. A song holds its patches (`put song patches`), and each section each voice's sound as it stands
(`put section sounds`).

| | | Evidence |
|---|---|---|
| A parameter moved | `<row>:<param> <value>`, 0 to 1, by way of the map's route: from the phone (`perform ctl <row> instrument <param> <value>`), the Launchpad's sound page or a control in play | unknown |
| An instrument taken up | A hardware synth is told nothing, so it keeps its own sound, and is told only what's then set; a Pd voice takes its defaults at once | unknown |
| A control change's range | 0 to 127, or to the row's sixth word, its top, where a device's stops short (the FM-1's effects: 100, 107, 10 or 2). A seventh is a switch: that controller said first, 1 while the value is above 0 and 0 at 0, so one control brings an effect in and takes it out (`test/gate/lua/u_sound_test.lua`) | verified |
| A program moved | Said, then every control change that's been set, again behind it: the voice a program brings has settings of its own (`test/gate/lua/u_sound_test.lua`) | verified |
| `sound patch <name>` | The song's patch, recalled | unknown |
| `sound copy <name>` | A factory patch copied into the song, under a name of its own, and recalled | unknown |
| `sound save` | What the voice sounds like now is what its patch holds; with no patch yet, a new one | unknown |
| `sound saveas` | The same, always a new one | unknown |
| A voice's sound, in a section | `put section sounds`, each row's patch, instrument and values as they stand, 300 ms after a change, a recall or a save, in the section playing: a tweak stays with the section it was made in. `restore sounds`, second of a section's parts and on step 1 while the transport runs, is what its voices snap back to; a row new on its instrument takes it at once, said whole (`test/gate/lua/u_sound_test.lua`) | verified |
| A section starting, `tweaks` 0 | Snap back: every voice's sound to what the section holds for it, only what differs said out. A value the section doesn't hold goes back to a Pd instrument's default, and stays as it sounds on a hardware synth, which is told nothing | verified |
| A section starting, `tweaks` 1 | Carry on: as it stands (`sections tweaks <0 or 1>`, the section's own) | unknown |
| The kit | `c_steps` holds its sound, each track's volume, pitch, effects and random pitch and the reverb, and puts it as `put song kit`; a section's `drums` line holds its pattern and a mute or solo. A song with no kit takes its first section's sound, which is no change to it | unknown |
| A voice's save on the kit | What the kit snaps back to is what it sounds like now | unknown |

| A Pd voice's effects | `e_line`, one a generator line and one for keys: `drive`, `drive-type`, `echo`, `echo-time`, `echo-fb`, `reverb` and `room`, each off until asked for, at its CPU cost then | unknown |
| A keys voice on a Pd instrument | `c_keys`, four notes at once, from `c_synth` | unknown |
| The fm synth's test | Pads 83 and 84 on the diagnostics page, or the phone's: a DX7 voice built here, sent as the library's are, into the voice kept for them (below) | verified |

### The DX7 library

**The `fm` instrument plays any of 1,024 DX7 voices** (Brendan, 2026-11-24): Yamaha's factory ROMs 1A to 4B and its
VRC-101 to 112 cartridges, 32 banks of 32. `cut-it-dx7.txt` lists the bank files in order and `u_sound`'s face reads each
from the patch's `dx7` folder at load; the files are Yamaha's and outside git, as the drum samples are. Two of the
instrument's parameters choose one, `dx7-bank` and `dx7-voice`.

| | | Evidence |
|---|---|---|
| A bank file | 32 voices as a DX7 saves them, 4104 bytes. One that isn't is turned away and named in Pd's log (`test/gate/lua/u_sound_test.lua`) | verified |
| A bank's number | Its place in `cut-it-dx7.txt`, and a song keeps a voice by it, so a new bank goes at the end | verified |
| A voice chosen | Unpacked to a one-voice dump and sent whole, a byte at a time, into the FM-1's voice 128, which Cut It keeps for it, its program change ahead of it as bytes ([fm1.md](../device/fm1.md), *`byte` is a whole voice, into the one voice kept for it*). Every control change that's been set is said again behind it, as for a program | verified |
| The same voice again | Sends nothing: each one sent is written into the FM-1's memory | verified |
| A bank that isn't there | `warn u_sound no-dx7-bank-<n>`, and nothing is sent | verified |
| A program or a DX7 voice | Whichever was chosen last: choosing one lets go of the other, in the voice's sound and so in its patch | verified |
| A recall, a song loading, a section snapping back | The voice first, a program or a DX7 voice, then what's set | verified |
| A section starting on the voice the FM-1 holds | Sends no dump: the voice last sent is kept by instrument, not by row, and forgotten when a program is chosen | verified |
| What a song keeps | The middle of the bank's, the voice's or the program's step, so the three decimals it writes bring the same one back | verified |

**The Launchpad's sound page:** the instrument's first eight parameters as columns on rows 3 to 8, tapped to set; row 2 its
song patches, tapped to recall; row 1 eight notes to hear it with. A row with no voice yet has none of it.

## Traps

### Pd hands a number over as a float

⛔ An address's arg comes through Pd as a float, and in Lua 5.4 `tostring(0.0)` is `0.0`, not the table's `0`. Tempo and
rush, which the table writes with an arg of `0`, could never be taken into play, and nothing said why.

**Fix:** `u_perform.lua`'s `key_of` writes a number with `%g`. `u_perform_test.lua` and the gate's own run take tempo
into play.

### A start isn't always PLAY

⛔ `pad-38` restarts the transport on the `start` bus while it runs. If that were PLAY, the page would turn to the
performance page under the finger, and the pad's release would land on another page's row, leaving its lamp lit.

**Fix:** `u_voices` hears `stop` and `panic` too, and takes a start only from stopped.

### Seeding a section must not be a change to the song

⛔ A section that holds no voices line is given the seed's when it starts, at load and after every revert. As an ordinary
`put section` it would light save and revert at load, and no revert could ever put them out.

**Fix:** `put seed-section`, which goes into what's saved of the section as well.

### Looking at a voice's page must not be a change to the song

⛔ A voice's page chooses what the nanoKEY plays. Through `c_synth`'s `synth`, which the phone's buttons use, it would
be put in the section, and lighting save and revert would be all it took to look around.

**Fix:** `instrument`, which sets the choice and tells the phone, and isn't put.

## Design

### Lua, as the map's rules are

`u_voices.lua` and `u_perform.lua` are plain Lua, with the state a table and every rule a function of it, answering
what leaves as `{outlet, selector, atoms}`; their faces are `u_voices-lua.pd_lua` and `u_perform-lua.pd_lua`, and
`test/gate/lua/u_voices_test.lua` and `u_perform_test.lua` run them without Pd. The voices gate runs both before its
Pd half, which holds the cords.

### Pages have names

A page is what a voice does there, so a row's page follows its behavior, and a row's behavior can change. The table's
rows, `g_grid`'s painters and the phone's tabs all key on the name: a voice on the fifth row and one on the second are
the same page, each in its own color.

### A fader sweep reaches the song store at most every 300 ms

A sweep is a message every few milliseconds. The list changes with each, and writing the song store each time would
be work a beat can't spare, so it's put on a clock of its own, as `c_melody`'s saves are.

## Open

- ⬜ **Not played on the rig**: voices, the pages, taking a control into play, a section's list.
  `test/checklists/launchpad.md`, `test/checklists/nanokontrol.md`, `cut-it/cut-it-app`.


