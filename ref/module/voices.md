<!-- schema: module -->
# The voices and the controls in play

**Files:** `Cut It/u_sound.pd`, `Cut It/u_sound.lua`, `Cut It/u_sound-lua.pd_lua`, `Cut It/cut-it-machines.txt`, `Cut It/cut-it-factory.txt`, `Cut It/u_voices.pd`, `Cut It/u_voices.lua`, `Cut It/u_voices-lua.pd_lua`, `Cut It/u_perform.pd`, `Cut It/u_perform.lua`, `Cut It/u_perform-lua.pd_lua`, `Cut It/cut-it-controls.txt` · **Gate:** `test/gate/voices-assert.sh`, `test/gate/display-assert.sh` · **Checklist:** `test/checklists/launchpad.md`, `test/checklists/nanokontrol.md`

## What it is

**A row of the Launchpad is a voice, not a fixed part** (Brendan, 2026-11-06). A song has up to eight voices, one a
row. Each has a name, a method, what it does, and a machine, what it does it on. **Harmony, melody and the drum page
are ways of doing something, not voices.** The button on the left is what the voice does, and the button across from it
on the right sets it up.

**`u_voices` holds a song's voices and the page on show, and it alone writes the `mode` bus**, a page's name as the
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
| A left button, CC 90 − 10 × row | A row with a voice | Its method's page; the lit one again, the performance page | unknown |
| | A row with none | Nothing | unknown |
| A right button, CC 99 − 10 × row | A row with a voice | `sound`, its setup; the lit one again, the performance page | unknown |
| | A row with none | Starts a new voice, `voice_<row>`, keys, on the first machine no other has, and shows its setup | unknown |
| aux, on the Organelle | Any page | Opens `songs`; again, back where it was | unknown |
| Setup, on the Launchpad | Any page | Opens `diag`; again, back where it was. Its `pad-81` is the diagnostic layer, and `pad-82` test mode | unknown |
| PLAY | A voice's left or right page, stopped | The performance page, by itself. Not from `songs` or `diag`, and not while the transport already runs | unknown |

| | | Evidence |
|---|---|---|
| Across a power cycle | `put auto page <kind> <row>`, on every change of page; restored at boot | unknown |
| A voice's page, restored | Waits for the song's voices, which come after the auto file; the performance page if the song has no such row | unknown |
| The boot, with nothing saved | The performance page | unknown |

### What a song's voices are

| | | Evidence |
|---|---|---|
| A method | `drums`, `harmony`, `melody` or `keys` | unknown |
| A machine | `kit`, on the drums; `fm`, `strings`, `sine`, `saw` or `square`, on the others | unknown |
| How many | One drums, two each of harmony and melody, what there are engines for: a third warns `too-many-harmony` and changes nothing. Keys as many as there are rows | unknown |
| A name | Lowercase, one symbol, spaces as `_`, at most 16 characters | unknown |
| Where it's saved | `put song voices <24 atoms>`, name, method and machine a row, `-` for one with none, in the song itself, for every section ([songs.md](songs.md)). It shows as unsaved, as any change to a song does | unknown |
| A song with none | Is given the seed's: row 1 `drums`, on `kit`; row 2 `chords`, harmony, on `strings`; row 3 `melody`, on `fm`. `put seed voices`, which is no change to the song | unknown |
| A voice removed | The performance page, if it was on show | unknown |
| A voice's engine | Each harmony and melody voice by row order: the first of each engine 1's, the second engine 2's. `assign <engine> <h or m> <machine or off>` tells each `c_melody` what it plays on; `active <engine>` which one the page's voice is in, 0 for neither, so the Launchpad, the phone and the nanoKEY reach only that one ([synths.md](synths.md)) | unknown |
| The nanoKEY | `machine <fm or strings>` to `c_synth`, on a page whose voice is on hardware. The performance page, and a voice on a Pd machine, leave it on the last ([synths.md](synths.md)) | unknown |

### The interface of `u_voices`

| | Is | Evidence |
|---|---|---|
| Inlet 1 | From `u_map`'s seventh outlet: `left-<r>`, `right-<r>`, `aux`, `setup`, each `<value>`; a release does nothing ([map.md](map.md)) | unknown |
| Inlet 2 | The phone's `voices`, through `u_net`: `left <r>`, `right <r>`, `aux`, `setup`, `name <r> <words>`, `method <r> <m>`, `machine <r> <m>`, `remove <r>` | unknown |
| Outlet 1 | To `g_grid`, `voices <row> <kind> <8 methods>`, when it changes | unknown |
| Outlet 2 | To the `c_melody`s, `assign` and `active` | unknown |
| Outlet 3 | To `c_synth`, `machine <machine>` | unknown |
| Outlet 4 | To `u_net`, `voices <page> <kind> <row> <24 atoms>`, sent as `/cutit/voices`, when it changes and on every heartbeat | unknown |
| Buses | Writes `mode`, `put song voices`, `put seed voices`, `put auto page` on `state`, `err`, and `voices-rows` to `u_perform`, the row on show and each row's engine. Hears `start`, `stop`, `panic` and `restore voices` and `restore page` on `state` | unknown |

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

### Machines and patches

**`u_sound` is what each voice sounds like** (Brendan, 2026-11-06). `cut-it-machines.txt` lists each machine's
parameters and how each is said: a control change, a program change or a Pd voice's own. A **patch** is a machine's
saved sound. `cut-it-factory.txt` holds factory patches, good starting points outside any song; a song copies one and
depends on nothing after that. A song holds its patches (`put song patches`) and each voice's sound as it stands
(`put song sounds`).

| | | Evidence |
|---|---|---|
| A parameter moved | `<row>:<param> <value>`, 0 to 1, by way of the map's route: from the phone (`perform ctl <row> machine <param> <value>`), the Launchpad's sound page or a control in play | unknown |
| A machine taken up | A hardware synth is told nothing, so it keeps its own sound, and is told only what's then set; a Pd voice takes its defaults at once | unknown |
| `sound patch <name>` | The song's patch, recalled | unknown |
| `sound copy <name>` | A factory patch copied into the song, under a name of its own, and recalled | unknown |
| `sound save` | What the voice sounds like now is what its patch holds; with no patch yet, a new one | unknown |
| `sound saveas` | The same, always a new one | unknown |
| A section starting, `tweaks` 0 | Snap back: every voice's sound back to what it was saved as, what differs said out | unknown |
| A section starting, `tweaks` 1 | Carry on: as it stands (`sections tweaks <0 or 1>`, the section's own) | unknown |
| The kit | `c_steps` holds its sound, each track's volume, pitch, effects and random pitch and the reverb, and puts it as `put song kit`; a section's `drums` line holds its pattern and a mute or solo. A song with no kit takes its first section's sound, which is no change to it | unknown |
| A voice's save on the kit | What the kit snaps back to is what it sounds like now | unknown |

**The Launchpad's sound page:** the machine's first eight parameters as columns on rows 3 to 8, tapped to set; row 2 its
song patches, tapped to recall; row 1 eight notes to hear it with.

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

### Seeding a song must not be a change to it

⛔ A song from before there were voices is given the seed's at load and at every revert. As an ordinary `put song` it
would light save and revert at load, and no revert could ever put them out.

**Fix:** `put seed`, which goes into what's saved as well.

### Looking at a voice's page must not be a change to the song

⛔ A voice's page chooses what the nanoKEY plays. Through `c_synth`'s `synth`, which the phone's buttons use, it would
be put in the section, and lighting save and revert would be all it took to look around.

**Fix:** `machine`, which sets the choice and tells the phone, and isn't put.

## Design

### Lua, as the map's rules are

`u_voices.lua` and `u_perform.lua` are plain Lua, with the state a table and every rule a function of it, answering
what leaves as `{outlet, selector, atoms}`; their faces are `u_voices-lua.pd_lua` and `u_perform-lua.pd_lua`, and
`test/gate/lua/u_voices_test.lua` and `u_perform_test.lua` run them without Pd. The voices gate runs both before its
Pd half, which holds the cords.

### Pages have names

A page is what a voice does there, so a row's page follows its method, and a row's method can change. The table's
rows, `g_grid`'s painters and the phone's tabs all key on the name: a voice on the fifth row and one on the second are
the same page, each in its own color.

### A fader sweep reaches the song store at most every 300 ms

A sweep is a message every few milliseconds. The list changes with each, and writing the song store each time would
be work a beat can't spare, so it's put on a clock of its own, as `c_melody`'s saves are.

## Open

- ⬜ **Not played on the rig**: voices, the pages, taking a control into play, a section's list.
  `test/checklists/launchpad.md`, `test/checklists/nanokontrol.md`, `cut-it/cut-it-app`.


