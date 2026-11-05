<!-- schema: module -->
# The sequencer

**Files:** `Cut It/c_steps.pd`, `Cut It/c_steps.lua`, `Cut It/c_steps-lua.pd_lua`, `Cut It/c_kit.pd`, `Cut It/c_voice.pd`, `tools/samples.sh` · **Gate:** `test/gate/sequencer-assert.sh`, `test/gate/kit-assert.sh` · **Checklist:** `test/checklists/sequencer.md`

## What it is

**`c_steps` knows steps, velocities and pads, and never where they are.** It is a 32-step
sequencer — sixteen tracks of 32 steps, a velocity per step, 0 for off, and a last step for the
whole pattern or for one track — that plays sixteen drum samples on its own `c_clock`, with swing,
drunkenness, a time signature, four repeat pads, and a skip and a move chance per track
(`cut-it/drum-timing`). What a press means arrives already translated from `u_map`
(`step 5`, `vel 3`, `pad 13`), and what the page shows leaves as meaning for `g_grid` (`steps …`,
`play 5`); the layout table that turns one into a cell is theirs, not its. That is the `m_`
boundary, and it is why another surface could drive it unchanged.

**Its rules are Lua, and its timing is Pd.** `c_steps.lua` holds the pattern, the step rule, the
velocity levels, the selection, the last steps and the knobs' latch, each track's place in its
loop, the repeats, the chances, each step's drunk length, and which pads fire on a step, as plain Lua that runs on the Mac without Pd; `c_steps.pd`
keeps the clock, the transport and the cords to `c_kit`, `g_grid`, `u_state` and `disp`, and asks
the Lua through one pdlua object, `[c_steps-lua $1]` (`cut-it/logic-as-text`).

It is page 2's drum machine (`cut-it/drum-machine`), and the first part of a song's sections
(`cut-it/songs-and-sections`): its pattern is stored as section 1's drum part from the start.
`u_root` holds one instance, `c_steps 1 drums` — bank A, stored as `section-1-drums`.

**The drums are played in Pd, by `c_kit`**, since 2026-11-04 (Brendan): sixteen samples, one a pad,
loaded beside the patch and played from memory, where they were the SP-404's pads before. *The
kit*, below.

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Creation arg 1 | Its bank, 1–10, 1 for A, **vestigial**: from when the SP-404 played the drums, which left the rig on 2026-11-04. Track *n* is pad (bank − 1) × 16 + *n*, and `c_kit` plays pads 1–16 only. It stays because dropping it would move arg 2 and the state key named for it | unknown |
| Creation arg 2 | The part its pattern is stored as: `drums` keys it `section-1-drums` | unknown |
| Inlet | `step <n> <vel>`, `vel <level> <vel>`, `pad <n> <vel>`, `rep <n> <vel>`, from `u_map`'s `drum-page` destination, presses and releases (velocity 0); `last`, `track-last` and `swing <0-1>`, knobs 2 to 4, from its `drums` destination, whose map rows name each: knobs 2 and 4 on every page, knob 3 on page 2 alone (Brendan, 2026-11-04); `sync`, `snap`, `select <n>`, `skip` and `move <0-100>`, the phone's drum screen, and `num` and `den <-1 or 1>`, `drunk <0-100>`, `set-swing <25-75>` and `set-last <1-32>`, its arrangement screen, from `u_net`'s first outlet. Anything else is `fail c_steps bad-selector` | unknown |
| Outlet 1 | `pad <1..160> <velocity>`, to `c_kit` | unknown |
| Outlet 2 | The drum page's state, to `g_grid`'s third inlet: `steps <32 levels>` for the selected track, each step's velocity level, 0 for off, `play <step>` (0 while stopped), `vel <level>`, `track <pad>`, `last <step>` for the selected track, `bar <steps>`, a bar of the time signature, and `rep <pad>`, the repeat pad held, 0 for none | unknown |
| Outlet 3 | The phone's state, to `u_net`'s second inlet: 42 numbers, `R.phone`, sent by the Pd face only when they change, for the drum and arrangement screens ([phone.md](../device/phone.md)) | unknown |
| `disp` | Knobs 2 to 4's rows: `last-step 12`, `pad2-last 6`, `swing 62 %`, and held, `last-step 16 (7)` | unknown |

### What it does

| | | Evidence |
|---|---|---|
| A step | Sixteen to a bar, cut from the sequencer's own phase, a pair of steps a cycle, which runs at `c_clock 1 4`'s rate times the Lua's: swung, then ×2, `wrap~`, and a `threshold~` on its fall, and sent to the Lua as `tick` (*One phase of its own*, below) | verified |
| When it fires | Straight and sober, a twelfth of a step after the boundary, in the block of `u_tempo`'s MIDI pulse for that sixteenth: the offset every clock in the patch shares (*Start alignment*, [tempo.md](tempo.md)). Within a block, ±1.45 ms, at 120 BPM in a test Pd (2026-11-03) | verified |
| Swing | Knob 4, on every page (Brendan, 2026-11-04), 25% to 75%, straight at 50%: the share of each pair of sixteenths the first one takes, so above 50% every second sixteenth comes later and below it earlier (Brendan, 2026-11-03). Taken at the next pair. Held at 50% at load, as knob 2 at 16; not saved. 66% at 120 BPM measured 165 and 85 ms, 25% 62 and 188 | verified |
| The phone's swing and last step | The arrangement screen sets each as it stands, `set-swing <25-75>` and `set-last <1-32>`, where knobs 4 and 2 send knob positions through their latch (Brendan, 2026-11-04). The knob is held again at the phone's value, so its next turn waits to pass it rather than jumping back; a selected track that follows the global last step holds knob 3 again too. Not saved, as the knobs' are not; a message with no number does nothing | unknown |
| Drunkenness | 0 to 100 from the phone's arrangement screen: most steps stay on time (Brendan, 2026-11-04): at 100 one step in three strays, at 50 one in six, and a step that strays lasts up to that share of a step longer or shorter, at random, never less than an eighth of a step. The error stays: its own drift becomes the clock, and only PLAY puts it back on `u_tempo`'s (Brendan, 2026-11-03). Saved | verified |
| The time signature | Two numbers from the phone's arrangement screen, the top 1 to 32 and the bottom one of 1 2 4 8 16, 4/4 at first: a bar is top × 16 / bottom steps, which the page marks. Saved | verified |
| The repeat pads | The top row of the right 4×4, 1 to 4 from the left: held, every track replays the last 1 to 4 steps it played, while the loops go on underneath unheard; let go, every track plays on from where it would have been (Brendan, 2026-11-03). PLAY lets go | verified |
| A track's chances | Skip and move, 0 to 100 each, for the selected track from the drum screen: a note is skipped, or moved a step early or late at random, rolled a step ahead so it can go early, fresh on every pass. The first step after PLAY can only go late. Saved | verified |
| On a step | The global loop moves on, then every track moves on in its own loop, wrapping after its own last step; every track plays the step it is heard at (a repeat's, while one is held): a note moved late from the step before, then its own note at its velocity if 1 or more, as its chances say, track 1 first, all in one logical instant. Then each track's next note is rolled, and one moved early plays now. Then the playhead moves, to the selected track's step, and the step's drunk length goes to the clock | verified |
| PLAY (`start`) | Starts every loop at step 1, the phase on the beat at its own rate, and lets go of a held repeat | verified |
| STOP (`stop`) and `panic` | Stop it, and put the playhead out | unknown |
| A pad press | Plays that pad now, at full velocity however hard it is pressed (Brendan, 2026-11-04), and selects it as the track being edited | unknown |
| A velocity press | Selects level *n*, velocity round(127·*n*/8): 16 32 48 64 79 95 111 127 | unknown |
| A step's level, whose color it takes | (*v* − 1) div 16 + 1, 0 for off, so each level's own velocity is that level. Worked out here and sent to `g_grid`, the one place the rule is | verified |
| A step press | Off takes the selected velocity; on, at any velocity, turns off (Brendan, 2026-11-03). Past the selected track's last step, nothing. A release of a step, a velocity or a pad does nothing | unknown |
| The global last step | Knob 2, on every page (Brendan, 2026-11-04), 1–32, for every track that has no last step of its own (Brendan, 2026-11-03). Steps past it keep their notes, unplayed and dark. Not saved | unknown |
| A track's own last step | Knob 3, on page 2 alone, where the track is selected, 1–32, for the selected track, saved with the pattern. Released at the step a following track already has, it goes on following | unknown |
| The knobs' latch | At load both are held at 16, and knob 3 again whenever another track is selected, or the global last step moves while the selected track follows it: held until turned to or through the step it stands for. A held knob changes nothing and draws its row with its own step in brackets | verified |
| `sync` (the drum screen's "sync first steps") | When the global loop next comes round to its step 1, every track goes back to its own step 1 there, keeping its own last step | verified |
| `snap` (its "snap to global") | The same, and at that step every track gives up its own last step, saved. Stopped, it lands at PLAY | verified |
| At load | Track 1, level 6 (95), last step 16 with knobs 2 and 3 held there, swing 50% with knob 4 held there, stopped | unknown |

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The pattern, the step rule, the velocity levels, the selected track and level, the last steps and the knobs' latch, each track's place in its loop, sync and snap, which pads fire on a step, the playhead, the restore | `c_steps.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_steps-lua.pd_lua`, the class `c_steps-lua`: two inlets (the presses, knobs and drum buttons; `c_steps.pd`'s own `tick`, `start`, `stop`, `restore` and `init`), eight outlets (notes, page, the pattern to save, `err`, a bang on `init`, the knobs' rows, the drum screen's state, the clock's `swing` and `rate`) | verified |
| The clock and its swing and rate, PLAY, STOP and panic, the cords to `c_kit`, `g_grid`, `u_state` and `disp`, `put auto section-1-<part>` | `c_steps.pd` | verified |
| The Lua's answers on the device | Identical to the Mac's: twenty messages through `c_steps-lua` in a test Pd on the Organelle and on the Mac printed the same 37 lines (2026-11-03) | verified |
| What it costs | About 0.4 MB more peak memory than the Pd version, in a test Pd loading `main.pd` on the Organelle (3.0 to 3.4 MB); pdlua itself is on the Organelle's Reference page | verified |

### The kit

| | Is | Evidence |
|---|---|---|
| `c_kit` | Takes `pad <1..16> <velocity>` from `c_steps`' outlet 1, a pad past 16 ignored, and holds sixteen `c_voice`, one a pad, summed out its `outlet~`, which `u_root` adds to the left output where the OLED meters it ([audio.md](audio.md)) | unknown |
| A sample | `samples/drums/NN.wav` in the patch's own folder, NN its pad, `01` to `16`: mono 16-bit WAV at 44.1 kHz, as `tools/samples.sh` writes it. Read by `c_voice` at load into a table of its own | unknown |
| A hit | Plays its pad's sample from the start. The level dips to 0 in 2 ms and the read restarts, so a hit cuts the one before, as a one-shot pad on the 404 did, without a click | unknown |
| Velocity | 30 dB of range, even in dB: 127 is 0 dB, 95 (level 6) about −7.6, 16 (level 1) about −26. 0 plays nothing | unknown |
| A pad with no sample | Silent, and no error: `c_voice` checks the file is there before reading it | unknown |
| The count | 2 s after load, on `err`: `info c_kit samples-16` with all sixteen, `warn c_kit samples-<n>` with some, `info c_kit no-samples` with none | unknown |
| What it costs | About 0.65% of the Organelle's core for each voice while it sounds; `switch~` keeps a silent voice's DSP off (the Organelle's Reference page) | verified |

### The pattern in the state store

| | | Evidence |
|---|---|---|
| Key | `section-1-<part>`, an `auto` key in `cut-it-auto.txt` ([state.md](state.md)) | unknown |
| Line | The key, 512 velocities, track 1's 32 steps first, then the sixteen tracks' own last steps, 0 for one that follows the global one, their skip chances, their move chances, the time signature's two numbers and the drunkenness: 564 atoms, zeros included. The knobs' values are not in it | verified |
| Written | `put auto` on every change; `u_state` flushes it within 2 s | unknown |
| Restored | At ~3.5 s by `u_state`, and put straight back | unknown |
| A line of exactly 256 | The 16-step pattern this replaced: each track's sixteen go to its first sixteen steps, and the put after it writes the new line | verified |
| A short or long line | The Lua takes what the line holds, as far as the drunkenness, a symbol as 0, and leaves the rest as they were; the put after it writes all of it. A line of 528, from before the drum screen's settings, comes back at 4/4, sober, with no chances | verified |
| A 564-atom line | Written and read whole, since both sides use `-c` (`~/Sites/!reference/pure-data.md`, *`[text write]` writes Pd's own format unless told `-c`*); the sequencer gate's seed holds a last step of its own and 7/8, which come back | verified |

## Traps

### A step is a chord

⛔ Every track on a step fires in one logical instant, and a minimum-interval rate limit keeps the
first note and drops the rest: a kick and a hat on the same sixteenth would play one.

**Fix:** nothing between the sequencer and the drums limits the rate: `c_kit` plays every pad of a
step, a voice each. While the SP-404 played them, `m_404`'s budget was a token bucket that passed
sixteen at once; anything that takes the pads out as MIDI again needs the same.

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

### The drums in Pd, not on the SP-404

Brendan moved the drums off the 404 (2026-11-04) for control of every hit: a pitch, a start point
or a retrigger per step is a message here, where the 404 offered a note and its velocity, and the
flourish he wants (a pad retriggered slower and lower over a few seconds) has no way to be played
on the 404 over MIDI (the SP-404's Reference page). A voice costs little on the Organelle, about
0.65% of its core while it sounds, and the mic needs no preamp in front of the Organelle's input,
so the 404 is no longer the rig's audio front end. The same day it left the rig altogether
([rig.md](../rig.md)).

**One `c_voice` a pad, as an abstraction**, since a copied subpatch is not allowed (C-13). It
reads its sample once, at load, from `samples/drums/` in the patch's own folder, found with
`pdcontrol`, so `main-dev.pd` on the Mac and `main.pd` on the device find them the same way and
no creation argument changes. **The samples are not in git**, since this repo is public:
`samples/drums/` is Brendan's, in any format and named by pad, and `tools/samples.sh` converts it
into the patch's folder, which `tools/deploy.sh` runs and copies with the patch. The gates copy
the patch without them.

### `c_`, because it makes control data and there will be more than one

The prefix table's `c_` is *control data generation*, and a sequencer is that; and a `c_` is
instantiable, which this is: the bank and the part are creation arguments, so a second sequencer —
the fx bank's, a synth's — is one more box with its own clock. Not `u_`: nothing about it is one per
instrument. Not `m_`: it must not know a device. Not `g_`: it draws nothing itself.

### The rules in Lua, the timing in Pd

The rules are a few dozen lines of Lua where they were a hundred boxes and cords, and they are
tested without Pd: `test/gate/lua/c_steps_test.lua` drives them, and the Pd face through a stand-in
for pdlua, with lua.org's interpreter, in the sequencer gate before its Pd half. What stays in Pd is
what Pd is for: the phase-cut clock, the transport, the pads out to `c_kit`, the page through
`g_grid` and the pattern through `u_state`. The randomizers and per-track
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

### One phase of its own

The steps are cut from a phase of the sequencer's own, not `c_clock`'s, because drunkenness moves
it off the beat for good. `rzero~ 1` and `wrap~` read `c_clock`'s phase as its increment per
sample, so the phase follows `c_clock`'s rate and ratio without a second copy of the tempo; an
`expr~` drops the one large increment a `start` makes, and `samplerate~` turns the increment back
into a frequency for a `phasor~` at two steps a cycle, times the rate the Lua sends. At rate 1 it
is `c_clock`'s beat phase times two to within a sample, so the steps land where they did; PLAY
resets both in the same block.

**Swing bends each pair.** The phase is shifted back a twelfth of a step first, so the offset
that lands a step in its MIDI pulse's block stays a fixed time and not a share of a swung step;
`samphold~` takes the swing as the pair begins, so a turn never moves a step already cut; and an
`expr~` gives the first step the swing's share of the pair and the second the rest. Then ×2,
`wrap~`, and the threshold on `1 −` that: a step is the phase's fall from near 1 to 0. A
threshold on a rising phase was not re-armed by a `start` landing mid-step, and PLAY's first step
came a step late.

**Drunk, the rate changes once a step.** The Lua rolls on each `tick` whether the step coming
strays and, if it does, its length, and sends `rate <1/length>` when that differs from the last; the phase runs at that rate until the next. The error is never paid back, so
the drum machine wanders off `u_tempo`'s clock, and nothing that follows that clock follows it
(Brendan, 2026-11-03).

### One clock, a loop per track

One phase is cut into steps, and each `tick` moves every track on in its own loop, so a track with
a last step of its own drifts against the rest until a sync brings them back together. The global
loop moves on too, as the reference a sync and a snap wait for: they land on its step 1, so the
tracks line up on its downbeat rather than wherever the button was pressed. Per-track subdivision
would give a track its own multiplier on the same phase in place of the ×4, and its own ticks.

### The knobs latch, because each knob means more than one value

Knob 3 stands for whichever track is selected, so selecting another would make the next touch jump
from that track's last step to wherever the knob sits; knob 2 at load has the same jump against the
16 it starts at. Each is held until turned to or through the step it stands for, as `u_map`'s pickup
holds a knob against a Save (*Parameter pickup*, [map.md](map.md)). The latch lives here, not in
`u_map`, because only `c_steps` knows the selected track's last step, and so these two knobs draw
their own rows. `u_map` passes them through untouched, held or not.

### PLAY starts every loop, and the run gate shuts for an instant

`start` puts every loop before its step 1, and `c_clock`'s own `start` resets the phase in the same
instant. The run gate shuts for one logical instant (`[del 0]`): a step cut from the old phase in
the block before PLAY can still be waiting in Pd's scheduler, and it would play as step 1 and push
the downbeat to step 2.

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

- ⬜ **The kit has not played on the rig**, nor have Brendan's samples: their levels against each
  other, the velocity curve's 30 dB, or the CPU with the pattern running. See `cut-it/drum-machine`.
- ⬜ **The mic and the drums share `outL`**, so one mixer channel's EQ and compressor. See
  `cut-it/drum-machine`.
- ✅ **On the rig** (Brendan, 2026-11-03): the knobs' latch, a track's own last step, the drum
  screen's pads and its two buttons, and a one-shot pad restarting on every step, which fast hats
  depend on (the SP-404's Reference page).
- ⬜ **The selected track and velocity are not saved**; every boot starts at track 1, level 6.
  See `cut-it/drum-machine`.
- ✅ **On the rig, a repeat pad holds for as long as it is held** (Brendan, 2026-11-04), once the
  Launchpad's heartbeat waited for it ([launchpad](../device/launchpad.md)).
- ⬜ **Swing, drunkenness and the chances have not played on the rig**, nor have the phone's
  controls for them or the page's blue bars. See `cut-it/drum-timing`.
- ⬜ **The Lua version has not played on the rig**: its CPU beside the Pd version's 11.2% with the
  drum machine playing (`~/Sites/!reference/pure-data.md`, *Newer versions on the Organelle*) is unmeasured. See `cut-it/logic-as-text`.
