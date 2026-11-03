<!-- schema: module -->
# The sequencer

**Files:** `Cut It/c_steps.pd`, `Cut It/c_steps.lua`, `Cut It/c_steps-lua.pd_lua` · **Gate:** `test/gate/sequencer-assert.sh` · **Checklist:** `test/checklists/sequencer.md`

## What it is

**`c_steps` knows steps, velocities and pads, and never where they are.** It is a 16-step
sequencer — sixteen tracks of sixteen steps, a velocity per step, 0 for off — that plays the
SP-404's pads on its own `c_clock`. What a press means arrives already translated from `u_map`
(`step 5`, `vel 3`, `pad 13`), and what the page shows leaves as meaning for `g_grid` (`steps …`,
`play 5`); the layout table that turns one into a cell is theirs, not its. That is the `m_`
boundary, and it is why another surface could drive it unchanged.

**Its rules are Lua, and its timing is Pd.** `c_steps.lua` holds the pattern, the step rule, the
velocity levels, the selection and which pads fire on a step, as plain Lua that runs on the Mac
without Pd; `c_steps.pd` keeps the clock, the transport and the cords to `m_404`, `g_grid` and
`u_state`, and asks the Lua through one pdlua object, `[c_steps-lua $1]` (`cut-it/logic-as-text`).

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
| On a step | Every track whose velocity there is 1 or more plays its pad at that velocity, track 1 first, all in one logical instant, then the playhead moves | unknown |
| PLAY (`start`) | Starts at step 1 | unknown |
| STOP (`stop`) and `panic` | Stop it, and put the playhead out | unknown |
| A pad press | Plays that pad now, at the Launchpad pad's own velocity, and selects it as the track being edited | unknown |
| A velocity press | Selects level *n*, velocity round(127·*n*/8): 16 32 48 64 79 95 111 127 | unknown |
| A step press | Off takes the selected velocity; on, at any velocity, turns off (Brendan, 2026-11-03) | unknown |
| At load | Track 1, level 6 (95), stopped | unknown |

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The pattern, the step rule, the velocity levels, the selected track and level, which pads fire on a step, the restore | `c_steps.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_steps-lua.pd_lua`, the class `c_steps-lua`: two inlets (`u_map`'s presses; `c_steps.pd`'s own `fire`, `restore` and `init`), five outlets (notes, page, the pattern to save, `err`, a bang on `init`) | verified |
| The clock, PLAY, STOP and panic, the playhead's `play`, the cords to `m_404`, `g_grid` and `u_state`, `put auto section-1-<part>` | `c_steps.pd` | verified |
| The Lua's answers on the device | Identical to the Mac's: twenty messages through `c_steps-lua` in a test Pd on the Organelle and on the Mac printed the same 37 lines (2026-11-03) | verified |
| What it costs | About 0.4 MB more peak memory than the Pd version, in a test Pd loading `main.pd` on the Organelle (3.0 to 3.4 MB); pdlua itself is on the Organelle's Reference page | verified |

### The pattern in the state store

| | | Evidence |
|---|---|---|
| Key | `section-1-<part>`, an `auto` key in `cut-it-auto.txt` ([state.md](state.md)) | unknown |
| Line | The key and 256 velocities, track 1's sixteen steps first, zeros included | unknown |
| Written | `put auto` on every change; `u_state` flushes it within 2 s | unknown |
| Restored | At ~3.5 s by `u_state`, and put straight back | unknown |
| A short or long line | The Lua takes as many velocities as the line holds, up to 256, a symbol as 0, and leaves the rest as they were; the put after it writes all 256 | verified |
| A 257-atom line | Written and read whole, since both sides use `-c` (`~/Sites/!reference/pure-data.md`, *`[text write]` writes Pd's own format unless told `-c`*) | unknown |

## Traps

### A step is a chord

⛔ Every track on a step fires in one logical instant, and a minimum-interval rate limit keeps the
first note and drops the rest: a kick and a hat on the same sixteenth would play one.

**Fix:** `m_404`'s budget is a token bucket that passes sixteen at once ([sp404.md](../device/sp404.md)).

### Never cut steps from `c_clock`'s beat bang

⛔ It tops out at 14.3 a second ([tempo.md](tempo.md)); sixteenths at 240 BPM are sixteen.

**Fix:** the beat phase, ×4, the way `c_clock` cuts its own pulses.

### A `.pd_lua` named for an abstraction replaces it

⛔ pdlua's loader runs before Pd looks for an abstraction, so a `c_steps.pd_lua` in the patch folder
would make every `[c_steps]` the Lua object, and `c_steps.pd` would never load.

**Fix:** the Pd face is `c_steps-lua.pd_lua`, a name no abstraction has.

### A Lua error printed by pdlua reaches no one on the device

⛔ pdlua prints a script's errors on Pd's console, and the menu-launched patch has none.

**Fix:** `c_steps-lua` runs every rule under `pcall` and sends an error out as
`fail c_steps lua-<selector>` (C-12). A Lua that never loads, from a syntax error or a missing pdlua,
can't report itself, so `c_steps.pd` sends `init` at load and says `fail c_steps no-lua` when no
bang comes back.

### A Lua that never loads is invisible to the gate's Pd half

⛔ `fail c_steps no-lua` is sent at load, before `sequencer-assert`'s driver and its `err` tap
exist, so its "nothing on err" check can't see it; the run fails on silence instead.

**Fix:** the syntax gate is the check for it: a `c_steps-lua` that fails to create prints
`couldn't create`, and `u_err`'s `[print err]` prints the `fail` that its log takes.

## Design

### `c_`, because it makes control data and there will be more than one

The prefix table's `c_` is *control data generation*, and a sequencer is that; and a `c_` is
instantiable, which this is: the bank and the part are creation arguments, so a second sequencer —
the fx bank's, a synth's — is one more box with its own clock. Not `u_`: nothing about it is one per
instrument. Not `m_`: it must not know a device. Not `g_`: it draws nothing itself.

### The rules in Lua, the timing in Pd

The rules are a few dozen lines of Lua where they were a hundred boxes and cords, and they are
tested without Pd: `test/gate/lua/c_steps_test.lua` drives them, and the Pd face through a stand-in
for pdlua, with lua.org's interpreter, in the sequencer gate before its Pd half. What stays in Pd is
what Pd is for: the phase-cut clock, the transport, MIDI out through `m_404` (dropping, never
queuing), the page through `g_grid` and the pattern through `u_state`. The randomizers and per-track
subdivisions go into `c_steps.lua` from the start (`cut-it/drum-machine`).

**`c_steps.lua` never calls Pd.** Every rule takes the state and returns what leaves, in order, so a
test reads the answers as data; only `c_steps-lua.pd_lua` knows outlets, and it is the one file that
needs pdlua. **The state is a plain table and the rules are functions of it**, so a reload of the
rules keeps the pattern.

### Editing the rules

1. Edit `Cut It/c_steps.lua`; `lua test/gate/lua/c_steps_test.lua` checks it in a second, without Pd.
2. In a running Pd, `; pdluax reload c_steps-lua` re-reads `c_steps-lua.pd_lua` and, through it,
   `c_steps.lua`: every object keeps its pattern and answers by the new rules. A change to the
   inlets or outlets needs the patch reopened.
3. `./test/run.sh`, then `./tools/deploy.sh`, which reloads the patch on the device.

pdlua and lua.org's Lua come from `device/README.md`, *Lua and ELSE*; without pdlua on the path the
object fails to create and the sequencer says `no-lua`.

### The layout table is not this file's

`c_steps` never reads `cut-it-drum-page.txt`. `u_map` turns a pad into a step and `g_grid` turns a
step into a cell, from the same table ([display.md](display.md)), so the sequencer's vocabulary is
the table's roles and nothing about the surface.

### One counter, and room for a multiplier per track

Every track reads one step counter cut from one phase. Per-track subdivision would give a track its
own multiplier on the same phase in place of the ×4, and its own counter; the rules would then be
asked about each track's own step.

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
file. Dense, zeros and all, so a restore fills the pattern in one pass and the line is the same shape
every time. The Lua answers what to save and takes the restore; `c_steps.pd` names the key and
talks to `u_state`. **The restore is put straight back**, as every contributor's must be
([state.md](state.md), *A contributor must put back what it restores*), and the same put repairs a
short or malformed line.

## Open

- ⬜ **Nothing here has run on the rig.** Whether a one-shot pad restarts on a second note-on —
  fast hats depend on it — and whether the page reads as intended; [the sequencer
  checklist](../../test/checklists/sequencer.md) asks both.
  See `cut-it/drum-machine`, its rig step.
- ⬜ **The selected track and velocity are not saved**; every boot starts at track 1, level 6.
  See `cut-it/drum-machine`.
- ⬜ **The Lua version has not played on the rig**: its CPU beside the Pd version's 11.2% with the
  drum machine playing (`~/Sites/!reference/pure-data.md`, *Newer versions on the Organelle*) is unmeasured. See `cut-it/logic-as-text`.
