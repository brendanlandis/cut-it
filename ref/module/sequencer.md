<!-- schema: module -->
# The sequencer

**Files:** `Cut It/c_steps.pd` · **Gate:** `test/gate/sequencer-assert.sh` · **Checklist:** `test/checklists/sequencer.md`

## What it is

**`c_steps` knows steps, velocities and pads, and never where they are.** It is a 16-step
sequencer — sixteen tracks of sixteen steps, a velocity per step, 0 for off — that plays the
SP-404's pads on its own `c_clock`. What a press means arrives already translated from `u_map`
(`step 5`, `vel 3`, `pad 13`), and what the page shows leaves as meaning for `g_grid` (`steps …`,
`play 5`); the layout table that turns one into a cell is theirs, not its. That is the `m_`
boundary, and it is why another surface could drive it unchanged.

It is mode 1's drum machine (`cut-it/drum-machine`), and the first part of a song's sections
(`cut-it/songs-and-sections`): its pattern is stored as section 1's drum part from the start.
`u_root` holds one instance, `c_steps 1 drums` — bank A, stored as `section-1-drums`.

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Creation arg 1 | The 404 bank its tracks play, 1–10, 1 for A. Track *n* plays pad *n* of that bank | unknown |
| Creation arg 2 | The part its pattern is stored as: `drums` keys it `section-1-drums` | unknown |
| Inlet | `step <n> <vel>`, `vel <level> <vel>`, `pad <n> <vel>`, from `u_map`'s `drum-page` destination. Anything else is `fail c_steps bad-selector` | unknown |
| Outlet 1 | `pad <1..160> <velocity>`, to `m_404`'s pad path | unknown |
| Outlet 2 | The drum page's state, to `g_grid`'s third inlet: `steps <16 velocities>` for the selected track, `play <step>` (0 while stopped), `vel <level>`, `track <pad>` | unknown |

### What it does

| | | Evidence |
|---|---|---|
| A step | Sixteen to a bar, cut from `c_clock 1 4`'s beat phase: ×4, `wrap~`, `threshold~ 0.0833333 0 0.04 0` | unknown |
| When it fires | A twelfth of a step after the boundary, in the block of `u_tempo`'s MIDI pulse for that sixteenth: the offset every clock in the patch shares (*Start alignment*, [tempo.md](tempo.md)) | unknown |
| On a step | Every track whose velocity there is not 0 plays its pad at that velocity, all in one logical instant, then the playhead moves | unknown |
| PLAY (`start`) | Starts at step 1 | unknown |
| STOP (`stop`) and `panic` | Stop it, and put the playhead out | unknown |
| A pad press | Plays that pad now, at the Launchpad pad's own velocity, and selects it as the track being edited | unknown |
| A velocity press | Selects level *n*, velocity round(127·*n*/16): 8 16 24 32 40 48 56 64 71 79 87 95 103 111 119 127 | unknown |
| A step press | Off takes the selected velocity; on at the selected velocity turns off; on at another takes the selected one | unknown |
| At load | Track 1, level 13 (103), stopped | unknown |

### The pattern in the state store

| | | Evidence |
|---|---|---|
| Key | `section-1-<part>`, an `auto` key in `cut-it-auto.txt` ([state.md](state.md)) | unknown |
| Line | The key and 256 velocities, track 1's sixteen steps first, zeros included | unknown |
| Written | `put auto` on every change; `u_state` flushes it within 2 s | unknown |
| Restored | At ~3.5 s by `u_state`, and put straight back | unknown |
| A 257-atom line | Written and read whole, since both sides use `-c` (`~/Sites/!reference/pure-data.md`, *`[text write]` writes Pd's own format unless told `-c`*) | unknown |

## Traps

### A step is a chord

⛔ Every track on a step fires in one logical instant, and a minimum-interval rate limit keeps the
first note and drops the rest: a kick and a hat on the same sixteenth would play one.

**Fix:** `m_404`'s budget is a token bucket that passes sixteen at once ([sp404.md](../device/sp404.md)).

### Never cut steps from `c_clock`'s beat bang

⛔ It tops out at 14.3 a second ([tempo.md](tempo.md)); sixteenths at 240 BPM are sixteen.

**Fix:** the beat phase, ×4, the way `c_clock` cuts its own pulses.

## Design

### `c_`, because it makes control data and there will be more than one

The prefix table's `c_` is *control data generation*, and a sequencer is that; and a `c_` is
instantiable, which this is: the bank and the part are creation arguments, so a second sequencer —
the fx bank's, a synth's — is one more box with its own clock. Not `u_`: nothing about it is one per
instrument. Not `m_`: it must not know a device. Not `g_`: it draws nothing itself.

### The layout table is not this file's

`c_steps` never reads `cut-it-drum-page.txt`. `u_map` turns a pad into a step and `g_grid` turns a
step into a cell, from the same table ([display.md](display.md)), so the sequencer's vocabulary is
the table's roles and nothing about the surface.

### One counter, and room for a multiplier per track

Every track reads one step counter cut from one phase. Per-track subdivision would give a track its
own multiplier on the same phase in place of the ×4, and its own counter; nothing else changes.

### PLAY parks the counter, and the run gate shuts for an instant

The counter parks at 15, so the next step is step 1, and `c_clock`'s own `start` resets the phase in
the same instant. The run gate shuts for one logical instant (`[del 0]`): a step cut from the old
phase in the block before PLAY can still be waiting in Pd's scheduler, and it would play as step 1
and push the downbeat to step 2.

### STOP and panic both stop it

The transport is `u_tempo`'s, and `stop` is the request for it. A panic stops the sequencer too, or
it would play straight through the silence the panic made; the pattern is kept.

### One auto key, named for a section

`section-1-drums` is section 1's drum part, so songs make it section *n*'s without rewriting this
file. Dense, zeros and all, so a restore is one `array set` and the line is the same shape every
time. **The restore is put straight back**, as every contributor's must be ([state.md](state.md),
*A contributor must put back what it restores*), and the same put repairs a short or malformed line:
`array set` takes what is there and the put writes all 256.

## Open

- ⬜ **Nothing here has run on the rig.** Whether a one-shot pad restarts on a second note-on —
  fast hats depend on it — and whether the page reads as intended; [the sequencer
  checklist](../../test/checklists/sequencer.md) asks both.
  See `cut-it/drum-machine`, its rig step.
- ⬜ **The selected track and velocity are not saved**; every boot starts at track 1, level 13.
  See `cut-it/drum-machine`.
