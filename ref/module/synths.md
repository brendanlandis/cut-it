<!-- schema: module -->
# The synths

**Files:** `Cut It/c_synth.pd`, `Cut It/c_synth.lua`, `Cut It/c_synth-lua.pd_lua`, `Cut It/cut-it-synth-page.txt`, `Cut It/c_melody.pd`, `Cut It/c_melody.lua`, `Cut It/c_melody-lua.pd_lua`, `Cut It/c_mono.pd` · **Gate:** `test/gate/synths-assert.sh`, `test/gate/display-assert.sh`, `test/gate/phone-assert.sh`, `test/gate/touchosc-assert.sh` · **Checklist:** `test/checklists/synths.md`, `test/checklists/linecheck.md`

## What it is

**`c_synth` holds which synth the nanoKEY plays, and holds it on every page.** There are two:
`fm`, the Volca FM, and `strings`, the Waldorf Streichfett, and `fm` at a first load (Brendan,
2026-11-04). The Launchpad's page 3 chooses with two pads, the phone with two buttons, and the
choice stays put whichever page the Launchpad is on, so the nanoKEY plays the chosen synth
everywhere ([nanokey.md](../device/nanokey.md)).

**The one decision that makes it legible: a key's release goes to the synth its press went to.** A
switch while a chord is held leaves those notes on the synth that started them, and their releases
follow them there, so nothing hangs; the next key plays the new choice.

**It also holds the velocity switch** (Brendan, 2026-11-04): on, a key's velocity reaches the synth;
off, every note-on goes out at 127, on either synth, and a release stays 0. The phone's keyboard tab
flips it; the Launchpad has no control for it.

**It holds each synth's sound for the section playing** (Brendan, 2026-11-04): a program number for
the Volca and one for the Streichfett, sent to each as the section starts, or none, which sends
nothing. The choice, the switch and the two programs are parts of every section of the song
([songs.md](songs.md)).

**Its rules are Lua, and its cords are Pd**, as the sequencer's are: `c_synth.lua` holds the choice
and which synth each held key went to, as plain Lua that runs on the Mac without Pd, and
`c_synth.pd` keeps the cords and the state bus, asking the Lua through one pdlua object,
`[c_synth-lua]` ([sequencer.md](sequencer.md), *The rules in Lua, the timing in Pd*).

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Inlet | `<note> <velocity>` from `m_nanokey`, 0 a release; `synth <choice>` from `u_map`'s `synth` destination (a page-3 pad's press) and from `u_net` (the phone's `/cutit synth <choice>`); `velocity <on or off>` from `u_net` (the phone's `/cutit velocity <on or off>`) | unknown |
| Outlet 1 | `note <n> <v>` and `program <n>` to `m_volca` | unknown |
| Outlet 2 | `note <n> <v>` and `program <n>` to `m_streich` | unknown |
| Outlet 3 | `synth <choice>` to `u_net`'s third inlet, which sends `/cutit/synth <choice>` to the phone at once and on every heartbeat ([phone.md](../device/phone.md)) | unknown |
| Outlet 4 | `synth <choice>` to `g_grid`'s fourth inlet, which paints page 3's pads ([display.md](display.md)) | unknown |
| Outlet 5 | `velocity <on or off>` to `u_net`'s third inlet, which sends `/cutit/velocity` to the phone at once and on every heartbeat | unknown |
| `state` | `put section synth <choice>`, `put section velocity <on or off>` and `put section programs <volca> <streichfett>` at load and on every change; `restore synth`, `restore velocity` and `restore programs` as a section starts, the first at ~3.5 s | unknown |
| `err` | `fail c_synth bad-synth` for a choice it does not know, `bad-velocity` for a setting, `bad-selector` for a message, `lua-<selector>` for a throw, `no-lua` when the Lua never loaded (C-12) | unknown |

Outlets 3 and 4 carry the choice, and outlet 5 the velocity switch, at load, at the restore and on
every change, never on a change that changes nothing.

### What it does

| | | Evidence |
|---|---|---|
| A key's press | Goes to the synth chosen now, as `note <n> <v>`, remembered as that key's | unknown |
| Its release | Goes to the synth its press went to, whatever is chosen by then | unknown |
| A press of a key held on the other synth | Releases it there first, then plays it on the choice: a nanoKEY never does this, a stray note-on can | unknown |
| A release with no press on record | Goes to the synth chosen now: a note-off nothing holds is harmless, and one sent nowhere could leave a note hanging | unknown |
| `synth <choice>` | Changes the choice and says so; the same choice again changes nothing and says nothing; a choice it does not know is `bad-synth` and changes nothing | unknown |
| A value of 0 after the choice | A release, ignored; `u_map` sends presses alone and the phone no value | unknown |
| `velocity off` | Every note-on from then goes out at 127, on either synth; a release stays 0, so a key held through the switch still lets go (Brendan, 2026-11-04) | unknown |
| `velocity on` | A key's own velocity reaches the synth again. The same setting twice says nothing; anything else is `bad-velocity` | unknown |
| At load | `fm` and velocity `on`, sent to the pads, the phone and the store | unknown |
| The restore | The saved choice and switch come back at ~3.5 s and are put straight back; one that names no synth, or neither on nor off, keeps the one in force and is repaired by the same put ([state.md](state.md), *A contributor must put back what it restores*) | unknown |
| Panic | Not heard here: each synth's layer sends its own All Notes Off, CC 123, on its own channel | unknown |
| A section's programs | `restore programs <volca> <streichfett>`, each 0 to 127, the program change on the wire, or `none`: each synth with a program is sent `program <n>`, the Volca first, and both are put straight back. A number off 0 to 127, or a word, is `none`; `none` sends nothing and leaves the synth on whatever sound it has | unknown |
| At load, the programs | `none none`, put, so the section playing holds them; no control chooses one yet (`cut-it/songs-and-sections`) | unknown |

### Page 3 on the Launchpad

**`Cut It/cut-it-synth-page.txt` says which cell is which synth**, a row per cell, `<index>
<synth>`, read with `-c` at load by `u_map`, to know what a press means, and by `g_grid`, to paint
it: a press and its lamp cannot disagree, as on the drum page ([display.md](display.md), *The
layout is a file both sides read*).

| Cells | Synth | Map rows | Evidence |
|---|---|---|---|
| 21–24, the second row from the bottom, left half | `fm` | `mode-3 pad-21 synth 21` … `pad-24` | unknown |
| 25–28, the same row, right half | `strings` | `mode-3 pad-25 synth 25` … `pad-28` | unknown |

The beat row stays on row 1, as on every page but the drums. What each cell paints is on
[display.md](display.md), *`g_grid`'s synth pads, page 3*.

### The generator

**A melody has shapes (Brendan, 2026-11-06).** Before its notes, a loop is planned: phrases, each with a
shape and a height for each step, and an arrival that ends each one, long, then a breath. The dice choose
notes around that plan, so a loop drifting under a low lock keeps its shape. **arrive** chooses what an arrival
lands on, up a tension on the chord it will meet, down that chord's own notes. **octave** is how often a note
jumps an octave off the line, which carries on where it was. The loop rolls ahead, a few steps at a time,
each hearing the chord it will meet first time round. Hand edits on the phone's notes tab are pinned, through
drift and roll, until cleared.

**Chords by hand.** With a chord's box held on the harmony tab, keys played on the nanoKEY are that chord, sounding
at once, pinned, and named if the mode knows it. A finger left on a box for 700 ms pins or unpins it, a pinned
chord's words amber. Roll leaves pinned chords, but with a box held rolls just that one, unpinned. The top row
of Launchpad page 3: new melody, new chords, chords on, melody on, new rhythm, the two on buttons bright when
on.

**`c_melody` rolls a loop of up to 8 chords and a loop of up to 32 notes in a key and mode, by
weighted dice, and a lock on each keeps or drifts what it rolled** (Brendan, 2026-11-05). `c_steps`'
clock drives it, each part plays on its own voice, and page 3's tabs on the phone and rows in the
map control it. `c_melody.lua` holds the rules, and `c_melody.pd` the cords, the note timing and the
state bus, as `c_synth`'s are.

| | Is | Evidence |
|---|---|---|
| Inlet | `step <count> <ms> <place>` and `last <step>` from `c_steps`; a control or a pad from `u_map`'s `melody` destination ([map.md](map.md)); `set`, `audition`, `move` and the pads from the phone ([phone.md](../device/phone.md)); the nanoKEY's keys, which mean nothing to it yet | unknown |
| Outlets | 1 `note <n> <v>` to `m_volca`; 2 the same to `m_streich`; 3 `melody <R.phone's atoms>` and `here <step>` to `u_net`'s third inlet; 4 the Pd voices' signal to `u_root`, summed with the input's ring into the right output, the Fx channel, mixer channel 2 | unknown |
| `state` | `put section melody <R.save's numbers>` at most every 100 ms under a drag; what a roll drifts only on `sync`, so a loop drifting writes nothing to the card; `restore melody` on the step 1 a section starts ([songs.md](songs.md)) | unknown |
| Voices | Each part's own: `fm`, `strings`, or the Pd voices `sine`, `saw` and `square` | unknown |
| A chord | A stack from the mode's notes, weighed by two families of chord tension picks, how little its notes move (`smooth`), how it sits with the tonic (`home`) and how its root moves, modal or functional. On the Volca its lowest three, on a Pd voice each note a voice of its own, four at most; bass only, its root alone, low, on any voice | unknown |
| Where a chord sounds | Its start on a grid `span` times the pattern's last step long, placed by dice or dragged on the phone; dropped on another's start, the two swap. It sounds until the next start, and before the first start the loop's last chord rings on. A new span or last step keeps each in the same place along the grid | unknown |
| A melody note | A rest or a note, weighed by how it sits with the chord and mode (`fit`), how far it is from the one before (`leap`), and what the loop did a phrase back (`echo`) | unknown |
| A lock | Each time round, a chord or step is rolled again with a chance of (1 − lock / 100)²: 100 keeps it and 0 rewrites it | unknown |
| On | A part's on button, a press; on, it starts a stopped transport, the one thing here that does | unknown |
| A step seen before | A repeat pad replaying it: what played plays again, nothing moves on and nothing rolls | unknown |
| A saved line | One without the later fields, `R.LATER`, still loads, those as they stand; any other length keeps what plays and puts that back | unknown |

**`c_mono` is the Pd voice**, one note at a time: `note <n> <v>`, 0 a release only the note sounding
answers, and `wave <0 sine, 1 saw, 2 square>`, -1 off, through a `vcf~` that opens with the envelope.
Only the chosen wave runs, and the whole voice only while a note sounds and for 220 ms after.
`c_melody` holds five: one for the melody, four for the chords, which share a wave. Their `outlet~`s go
up through `c_melody` to `u_root`: everything Cut It sends out leaves there.

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The choice, which synth each held key went to, the velocity switch, the restores | `c_synth.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_synth-lua.pd_lua`, the class `c_synth-lua`: two inlets (keys, choices and the switch; `c_synth.pd`'s own `restore`, `restore-velocity` and `init`), seven outlets (the Volca, the Streichfett, the choice, the key and value to save, `err`, a bang on `init`, the switch for the phone) | verified |
| The cords out, `put auto` under the key the Lua names, the restores off the `state` bus, the `no-lua` guard | `c_synth.pd` | verified |
| What a page-3 press means | `u_map`'s `synth` destination, which looks the cell up in the layout ([map.md](map.md)) | verified |

### The choice, the switch and the programs in a section

| | | Evidence |
|---|---|---|
| Parts | `synth`, `velocity` and `programs`, three parts of the section playing, kept by `u_song` ([songs.md](songs.md)) | unknown |
| Lines | `synth fm` or `synth strings`, `velocity on` or `velocity off`, `programs none none` or two numbers, written and read back by `synths-assert`, which boots with a song whose one section holds `strings` and `off`; `song-assert` sends a section's programs as it starts | verified |
| Written | `put section` at load and on every change; `u_song` writes the song's draft within 2 s | unknown |
| Before sections | `synth` and `velocity` were `auto` keys; `u_state`'s restore of either, at the first load after the update, is taken the same way and put as the section's | verified |

## Traps

### A release sent to the synth chosen now hangs a note

⛔ A key held while the choice switches would be released on the new synth, which never heard its
press, and the old synth's note sounds until a panic. The two synths are on different ports, so a
note-off on one is nothing on the other.

**Fix:** the Lua remembers, per held key, the synth its press went to, and sends the release there.
`synths-assert` holds a key on fm, switches from the phone and requires the release on the Volca's
channel.

### A pad's release must not choose

⛔ With both page-3 pads held, the first one let go would undo the choice the second one made, if
a release chose.

**Fix:** `u_map`'s `synth` destination passes a press alone, as `diag` and `test-mode` do.
`synths-assert` holds FM, presses STRINGS, lets FM go and requires strings.

### A Lua that never loads leaves the nanoKEY playing nothing

⛔ Without pdlua, or with an error in the Lua, `[c_synth-lua]` fails to create and every key goes
nowhere, in silence.

**Fix:** `c_synth.pd` sends `init` at load and says `fail c_synth no-lua` when no bang comes back,
as `c_steps` does; a throwing rule says `fail c_synth lua-<selector>`. The gates' side of it is the
sequencer's trap, *A Lua that never loads is invisible to the gate's Pd half*
([sequencer.md](sequencer.md)).

### A saved line comes back in floats

⛔ Pd's numbers are all floats, and a float prints as `7.0`, so a name or a key built from one matches
nothing, with no error: chord names were keyed on `7.0`.

**Fix:** `num` in `c_melody.lua` makes a whole float an integer as a message arrives.
`test/gate/lua/c_melody_test.lua` restores a line of floats and requires the phone's line back to
the character.

## Design

### The nanoKEY bypasses the map

A device publishes on `param` and `u_map` decides what each control means per page
([architecture.md](../architecture.md)). The nanoKEY's keys mean one thing on every page, the
chosen synth's note (Brendan, 2026-11-04), so `m_nanokey` hands them to `c_synth` by a cord. What
the choice is stays a mapped thing: the pads reach it through `u_map`, page 3 only.

### Lua, as the sequencer's rules are

The router is a choice and a table of held keys, a few lines of Lua where Pd would need an array
of 128 destinations and the boxes to read and write it; `test/gate/lua/c_synth_test.lua` drives it
without Pd. A key costs about 0.1 ms in Lua on the Organelle (the Organelle's Reference page), and
a keyboard sends a few notes a second, where the cost that kept the Launchpad's layer in Pd is a
pressure stream.

### The choice leaves by cords, and no bus carries it

The phone and the pads are the two places that show the choice, and each gets it on a cord into a
file that already shows `c_synth`'s neighbors' state: `u_net`'s third inlet beside `c_steps`' drum
state, and `g_grid`'s fourth inlet beside the drum page's. A bus would be a new name on C-2's
allowlist for something one file publishes and two files read. The velocity switch has an outlet
of its own, into the same inlet of `u_net`, since only the phone shows it: on the choice's outlet
it would reach `g_grid`, which would refuse it as `bad-selector`.

### The velocity switch is the router's

Every note-on already passes through `c_synth` on its way to one synth or the other, so one line of
the router covers both synths and every page; a switch in each synth's layer would be two to keep
in step. Releases are left alone: a 0 forced to 127 would be a new note. The Launchpad has no
control for it for now (Brendan, 2026-11-04).

### Three parts of a section

The choice, the switch and the programs are put whenever they change, with the section policy, so
each section of a song holds its own (`cut-it/songs-and-sections`). The programs are here because
`c_synth` already reaches both synths' layers by cords, and a section starting is a restore the
router takes like any other; each layer already takes `program <n>` from the map's `volca-prog`.

### `c_`, because there can be more than one

A second keyboard, or a sequencer's track, would want its own choice and its own held keys: a
second `c_synth` with its own cords. Not `u_`: nothing about it is one per instrument.

## Open

- ⬜ **Not played on the rig**: each synth from the nanoKEY, a switch mid-chord, page 3's pads and
  their colors, the phone's keyboard tab, its velocity switch, and the line check's toggle.
  `test/checklists/synths.md`, `cut-it/pages-and-displays`.
- ⬜ **No control chooses a synth's program**: a section holds `none none` until its file is edited.
  `cut-it/songs-and-sections`.
