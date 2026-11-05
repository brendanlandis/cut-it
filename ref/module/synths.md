<!-- schema: module -->
# The synths

**Files:** `Cut It/c_synth.pd`, `Cut It/c_synth.lua`, `Cut It/c_synth-lua.pd_lua`, `Cut It/cut-it-synth-page.txt` · **Gate:** `test/gate/synths-assert.sh`, `test/gate/display-assert.sh`, `test/gate/phone-assert.sh`, `test/gate/touchosc-assert.sh` · **Checklist:** `test/checklists/synths.md`, `test/checklists/linecheck.md`

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
off, every note-on goes out at 127, on either synth, and a release stays 0. The phone's synths screen
flips it; the Launchpad has no control for it.

**Its rules are Lua, and its cords are Pd**, as the sequencer's are: `c_synth.lua` holds the choice
and which synth each held key went to, as plain Lua that runs on the Mac without Pd, and
`c_synth.pd` keeps the cords and the state bus, asking the Lua through one pdlua object,
`[c_synth-lua]` ([sequencer.md](sequencer.md), *The rules in Lua, the timing in Pd*).

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Inlet | `<note> <velocity>` from `m_nanokey`, 0 a release; `synth <choice>` from `u_map`'s `synth` destination (a page-3 pad's press) and from `u_net` (the phone's `/cutit synth <choice>`); `velocity <on or off>` from `u_net` (the phone's `/cutit velocity <on or off>`) | unknown |
| Outlet 1 | `note <n> <v>` to `m_volca` | unknown |
| Outlet 2 | `note <n> <v>` to `m_streich` | unknown |
| Outlet 3 | `synth <choice>` to `u_net`'s third inlet, which sends `/cutit/synth <choice>` to the phone at once and on every heartbeat ([phone.md](../device/phone.md)) | unknown |
| Outlet 4 | `synth <choice>` to `g_grid`'s fourth inlet, which paints page 3's pads ([display.md](display.md)) | unknown |
| Outlet 5 | `velocity <on or off>` to `u_net`'s third inlet, which sends `/cutit/velocity` to the phone at once and on every heartbeat | unknown |
| `state` | `put auto synth <choice>` and `put auto velocity <on or off>` on every change; `restore synth <choice>` and `restore velocity <setting>` at ~3.5 s | unknown |
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

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The choice, which synth each held key went to, the velocity switch, the restores | `c_synth.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_synth-lua.pd_lua`, the class `c_synth-lua`: two inlets (keys, choices and the switch; `c_synth.pd`'s own `restore`, `restore-velocity` and `init`), seven outlets (the Volca, the Streichfett, the choice, the key and value to save, `err`, a bang on `init`, the switch for the phone) | verified |
| The cords out, `put auto` under the key the Lua names, the restores off the `state` bus, the `no-lua` guard | `c_synth.pd` | verified |
| What a page-3 press means | `u_map`'s `synth` destination, which looks the cell up in the layout ([map.md](map.md)) | verified |

### The choice and the switch in the state store

| | | Evidence |
|---|---|---|
| Keys | `synth` and `velocity`, two `auto` keys in `cut-it-auto.txt` | unknown |
| Lines | `synth fm` or `synth strings`, and `velocity on` or `velocity off`, written and read back by `synths-assert`, which boots with `strings` and `off` saved | verified |
| Written | `put auto synth` and `put auto velocity` at load and on every change; `u_state` flushes within 2 s | unknown |

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

### Two auto keys, for now

The choice and the switch are running values, put whenever they change, as the page is
([map.md](map.md), *`mode` is persisted; the table is not*). Sections will own both, each with its
synth, when songs arrive (`cut-it/songs-and-sections`).

### `c_`, because there can be more than one

A second keyboard, or a sequencer's track, would want its own choice and its own held keys: a
second `c_synth` with its own cords. Not `u_`: nothing about it is one per instrument.

## Open

- ⬜ **Not played on the rig**: each synth from the nanoKEY, a switch mid-chord, page 3's pads and
  their colors, the phone's synths screen, its velocity switch, and the line check's toggle.
  `test/checklists/synths.md`, `cut-it/pages-and-displays`.
- ⬜ **The choice and the velocity switch are global until sections own them.**
  `cut-it/songs-and-sections`.
