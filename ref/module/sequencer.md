<!-- schema: module -->
# The sequencer

**Files:** `Cut It/c_steps.pd`, `Cut It/c_steps.lua`, `Cut It/c_steps-lua.pd_lua`, `Cut It/c_kit.pd`, `Cut It/c_voice.pd`, `tools/samples.sh` · **Gate:** `test/gate/sequencer-assert.sh`, `test/gate/kit-assert.sh` · **Checklist:** `test/checklists/sequencer.md`

## What it is

**`c_steps` knows steps, velocities and pads, and never where they are.** It is a 32-step
sequencer — sixteen tracks of 32 steps, a velocity per step, 0 for off, and a last step for the
whole pattern or for one track — that plays sixteen drum samples on its own `c_clock`, with swing,
drunkenness, a time signature, four repeat pads, and a randomness, a volume and a pitch per
track (`cut-it/drum-timing`). What a press means arrives already translated from `u_map`
(`step 5`, `vel 3`, `pad 13`), and what the page shows leaves as meaning for `g_grid` (`steps …`,
`play 5`); the layout table that turns one into a cell is theirs, not its. That is the `m_`
boundary, and it is why another surface could drive it unchanged.

**Its rules are Lua, and its timing is Pd.** `c_steps.lua` holds the pattern, the step rule, the
velocity levels, the selection, the last steps and the knobs' latch, each track's place in its
loop, the repeats, each track's randomness, volume and pitch, each step's drunk length, and which pads fire on a step, as plain Lua that runs on the Mac without Pd; `c_steps.pd`
keeps the clock, the transport and the cords to `c_kit`, `g_grid`, `u_song` and `disp`, and asks
the Lua through one pdlua object, `[c_steps-lua $1]` (`cut-it/logic-as-text`).

It is page 2's drum machine (`cut-it/drum-machine`), and a part of every section of the song
(`cut-it/songs-and-sections`): its pattern, with the arrangement page's settings, is the section
playing's `drums`, kept by `u_song` ([songs.md](songs.md)), and it says where the pattern loops, the
bar a queued section waits for. `u_root` holds one instance, `c_steps 1 drums` — bank A, stored as
the part `drums`.

**The drums are played in Pd, by `c_kit`**, since 2026-11-04 (Brendan): sixteen samples, one a pad,
loaded beside the patch and played from memory, where they were the SP-404's pads before. *The
kit*, below.

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Creation arg 1 | Its bank, 1–10, 1 for A, **vestigial**: from when the SP-404 played the drums, which left the rig on 2026-11-04. Track *n* is pad (bank − 1) × 16 + *n*, and `c_kit` plays pads 1–16 only. It stays because dropping it would move arg 2 and the state key named for it | unknown |
| Creation arg 2 | The part its pattern is stored as in a section: `drums` | unknown |
| Inlet | `step <n> <vel>`, `vel <level> <vel>`, `pad <n> <vel>`, `rep <n> <vel>`, from `u_map`'s `drum-page` destination, presses and releases (velocity 0), a `step`'s *n* the layout table's step cell, 1 to 32 (*The rows of steps*, below); `last`, `track-last` and `swing <0-1>`, knobs 2 to 4, from its `drums` destination, whose map rows name each: knobs 2 and 4 on every page, knob 3 on page 2 alone (Brendan, 2026-11-04); `sync`, `snap` and `select <n>`, the phone's drum screen, and `vol`, `pitch`, `randomness` and `set-track-last <track> <value>`, its pads dragged, and `num` and `den <-1 or 1>`, `drunk <0-100>`, `set-swing <50-75>` and `set-last <1-32>`, its arrangement screen, from `u_net`'s first outlet. Anything else is `fail c_steps bad-selector` | unknown |
| Outlet 1 | `pad <1..160> <velocity>`, and a track's `vol <pad> <dB>` and `pitch <pad> <semitones>`, every track's at a restore and one when the phone changes it, to `c_kit` | unknown |
| Outlet 2 | The drum page's state, to `g_grid`'s third inlet: `steps <32 levels>` for the selected track, each step's velocity level, 0 for off, `play <step>` (0 while stopped), `vel <level>`, `track <pad>`, `last <step>` for the selected track, `bar <N> <row>`, the time signature as the page shows it, a blue step every *N* and *row* steps to a row, and `rep <pad>`, the repeat pad held, 0 for none | unknown |
| Outlet 3 | The phone's state, to `u_net`'s second inlet: 88 numbers, `R.phone`, sent by the Pd face only when they change, for the drum and arrangement screens ([phone.md](../device/phone.md)) | unknown |
| Outlet 4 | `bar`, to `u_song`'s third inlet, on the step the global loop wraps after: a bar is the pattern's loop (Brendan, 2026-11-05), the time signature no part of it ([songs.md](songs.md)) | unknown |
| `disp` | Knobs 2 to 4's rows: `last-step 12`, `pad2-last 6`, `swing 62 %`, and held, `last-step 16 (7)` | unknown |

### What it does

| | | Evidence |
|---|---|---|
| A step | Sixteen to a bar, cut from the sequencer's own phase, a pair of steps a cycle, which runs at `c_clock 1 4`'s rate times the Lua's: swung, then ×2, `wrap~`, and a `threshold~` on its fall, and sent to the Lua as `tick` (*One phase of its own*, below) | verified |
| When it fires | Straight and sober, a twelfth of a step after the boundary, in the block of `u_tempo`'s MIDI pulse for that sixteenth: the offset every clock in the patch shares (*Start alignment*, [tempo.md](tempo.md)). Within a block, ±1.45 ms, at 120 BPM in a test Pd (2026-11-03) | verified |
| Swing | Knob 4, on every page (Brendan, 2026-11-04), 50% to 75%, straight at its bottom and swinging one way only (Brendan, 2026-11-05): the share of each pair of sixteenths the first one takes, so above 50% every second sixteenth comes later. Taken at the next pair. Held at 50% at load, as knob 2 at 16, and since 50% is the knob's bottom, held until turned all the way down; saved, a section's. 66% at 120 BPM measured 165 and 85 ms | verified |
| The phone's swing and last step | The arrangement screen sets each as it stands, `set-swing <50-75>` and `set-last <1-32>`, the last step clipped to the time signature's reach, where knobs 4 and 2 send knob positions through their latch (Brendan, 2026-11-04). The knob is held again at the phone's value, so its next turn waits to pass it rather than jumping back; a selected track that follows the global last step holds knob 3 again too. Saved, a section's, as the knobs' are; a message with no number does nothing | unknown |
| Drunkenness | 0 to 100 from the phone's arrangement screen: at 100 every step strays, by up to two steps longer or shorter, and low settings stay subtle (Brendan, 2026-11-05). At *x*, the slider's 0 to 1, a step strays with the chance *x*/3 + 2*x*⁴/3, by up to *x* + *x*⁴ steps, at random either way: a line, which is most of it low, plus a steep fourth power that adds the rest near the top. At 20% one step in fifteen strays, by up to a fifth of a step; at 50% one in five, by up to 0.56; at 90% three in four, by up to 1.56. A step is never less than an eighth of a step. The error stays: its own drift becomes the clock, and only PLAY puts it back on `u_tempo`'s (Brendan, 2026-11-03). Saved | verified |
| The time signature | Two numbers from the phone's arrangement screen, the top 1 to 32 and the bottom one of 1 2 4 8 16, 4/4 at first, both saved (Brendan, 2026-11-05). **The top number *N*** says how often the page shows a blue step, every *N* steps from step 1, whatever the subdivision, and how long a row of steps is and how far a last step reaches (*The rows of steps*, below). A change of it that moves the reach holds knobs 2 and 3 again, since a turn of either then stands for another step. **The bottom number is a matter of record only**: it changes neither the page nor how fast the steps go, which only the tempo and drunkenness set | verified |
| The rows of steps | The page's step cells are four rows of eight, and a row holds as many groups of *N* as fit in 8, or all 8 when *N* is over 8: rows of 6 at 3/4 and 6/8, blue at a row's cells 1 and 4, or 1; 8 at 4/4, blue at 1 and 5; 5 at 5/4; 7 at 7/8; 8 at 2/4 and at 1/*x*, where every step is blue. Over 8, the blue counts straight through the pattern and wraps across the rows: at 9/8, steps 1, 10, 19 and 28. A row's cells past its steps are dark, and a press there does nothing. The step cell *n*, row *r* and column *c* from 0, is step *r* × row + *c* + 1 | verified |
| How far a last step reaches | Four rows' worth: 24 at 3/4, 32 at 4/4, 20 at 5/4, 28 at 7/8, 32 with *N* over 8. The global last step and every track's own are clipped to it where they are used, on the page, in the loops, the bar and the phone's state, and kept as set and saved, so a time signature passed through on the way to another does not cut them short for good: 32 at 4/4 is 24 at 3/4 and 32 again at 4/4. Knobs 2 and 3 turned all the way up and the phone's `set-last` and `set-track-last` reach exactly that far | verified |
| The repeat pads | The top row of the right 4×4, 1 to 4 from the left: held, every track replays the last 1 to 4 steps it played, while the loops go on underneath unheard; let go, every track plays on from where it would have been (Brendan, 2026-11-03). PLAY lets go | verified |
| A track's randomness | 0 to 100, each track its own, from its pad on the drum screen (Brendan, 2026-11-05, after the Arturia DrumBrute's Randomness): at *R*% each step it plays has an *R*% chance of ignoring what is written and flipping a coin instead, played or not, and played at one of the eight levels at random. So it drops hits from a busy track and adds them to a sparse one; at 100 every step is a coin, at 0 the pattern plays as written and nothing is rolled. Fresh on every pass, a repeat's steps too. Saved | verified |
| A track's volume and pitch | −30 to +6 dB and −12 to +12 semitones, each track its own, 0 at first, from its pad on the drum screen: each is saved and goes to `c_kit` for that track's pad, which plays it from the next hit (*The kit*, below). A restore sends every track's | verified |
| A track's last step from the phone | `set-track-last <track> <1-32>`, from its pad, clipped to the reach, as knob 3 sets the selected track's: the step a track already has changes nothing, so one that follows the global step goes on following; set for the selected track, it holds knob 3 again. Saved | verified |
| On a step | The global loop moves on, then every track moves on in its own loop, wrapping after its own last step; every track plays the step it is heard at (a repeat's, while one is held), its note at its velocity if 1 or more, or as its randomness flips it, track 1 first, all in one logical instant. Then the playhead moves, to the selected track's step, and the step's drunk length goes to the clock | verified |
| PLAY (`start`) | Starts every loop at step 1, the phase on the beat at its own rate, and lets go of a held repeat | verified |
| STOP (`stop`) and `panic` | Stop it, and put the playhead out | unknown |
| A pad press | Plays that pad now, at full velocity however hard it is pressed (Brendan, 2026-11-04), and selects it as the track being edited | unknown |
| A velocity press | Selects level *n*, velocity round(127·*n*/8): 16 32 48 64 79 95 111 127 | unknown |
| A step's level, whose color it takes | (*v* − 1) div 16 + 1, 0 for off, so each level's own velocity is that level. Worked out here and sent to `g_grid`, the one place the rule is | verified |
| A step press | On the step its cell is in the rows (*The rows of steps*): off takes the selected velocity; on, at any velocity, turns off (Brendan, 2026-11-03). Past its row, or past the selected track's last step, nothing. A release of a step, a velocity or a pad does nothing | unknown |
| The global last step | Knob 2, on every page (Brendan, 2026-11-04), 1 to the time signature's reach, 32 at 4/4, for every track that has no last step of its own (Brendan, 2026-11-03). Steps past it keep their notes, unplayed and dark. Saved, a section's | unknown |
| A track's own last step | Knob 3, on page 2 alone, where the track is selected, 1 to the reach, for the selected track, saved with the pattern. Released at the step a following track already has, it goes on following | unknown |
| The knobs' latch | At load knobs 2 and 3 are held at 16 and knob 4 at 50%, and knob 3 again whenever another track is selected, or the global last step moves while the selected track follows it: held until turned to or through the step it stands for, which for knob 4 at 50%, its bottom, is all the way down. A held knob changes nothing and draws its row with its own value in brackets | verified |
| `sync` (the drum screen's "sync first steps") | When the global loop next comes round to its step 1, every track goes back to its own step 1 there, keeping its own last step | verified |
| `snap` (its "snap to global") | The same, and at that step every track gives up its own last step, saved. Stopped, it lands at PLAY | verified |
| At load | Track 1, level 6 (95), last step 16 with knobs 2 and 3 held there, swing 50% with knob 4 held there, stopped; every track at 0 dB, its own pitch and no randomness until the restore. The pattern is put at once, so the section playing holds the drums from the start | unknown |
| A bar | Ends on the step after which the global loop comes round to its step 1, counted on the machine's own steps from PLAY: the 16th with the global last step at 16, the 12th at 12, however the time signature reads and however drunk, but no further than its reach: a global last step of 32 at 3/4 ends a bar on the 24th. A global last step moved under the loop's place wraps into it with no bar there. `bar` is the step's last answer, after its notes | verified |
| A section's restore | Starts every loop, the global one and each track's, again at step 1 on the next step, as PLAY does: so a section whose global last step differs from the one before starts on its own step 1, not the old loop's place plus one | verified |

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The pattern, the step rule, the velocity levels, the selected track and level, the last steps and the knobs' latch, each track's place in its loop, sync and snap, which pads fire on a step, the playhead, the restore | `c_steps.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_steps-lua.pd_lua`, the class `c_steps-lua`: two inlets (the presses, knobs and drum buttons; `c_steps.pd`'s own `tick`, `start`, `stop`, `restore` and `init`, and `sync` off the state bus), nine outlets (notes, page, the pattern to save, `err`, a bang on `init`, the knobs' rows, the drum screen's state, the clock's `swing` and `rate`, the bar) | verified |
| The clock and its swing and rate, PLAY, STOP and panic, the cords to `c_kit`, `g_grid`, `u_song` and `disp`, `put section <part>` | `c_steps.pd` | verified |
| The Lua's answers on the device | Identical to the Mac's: twenty messages through `c_steps-lua` in a test Pd on the Organelle and on the Mac printed the same 37 lines (2026-11-03) | verified |
| What it costs | About 0.4 MB more peak memory than the Pd version, in a test Pd loading `main.pd` on the Organelle (3.0 to 3.4 MB); pdlua itself is on the Organelle's Reference page | verified |

### The kit

| | Is | Evidence |
|---|---|---|
| `c_kit` | Takes `pad <1..16> <velocity>` from `c_steps`' outlet 1, a pad past 16 ignored, and `vol <pad> <dB>` and `pitch <pad> <semitones>`, a track's volume and pitch, and holds sixteen `c_voice`, one a pad, summed out its `outlet~`, which `u_root` adds to the left output where the OLED meters it ([audio.md](audio.md)) | unknown |
| A sample | `samples/drums/NN.wav` in the patch's own folder, NN its pad, `01` to `16`: mono 16-bit WAV at 44.1 kHz, as `tools/samples.sh` writes it. Read by `c_voice` at load into a table of its own | unknown |
| A hit | Plays its pad's sample from the start. The level dips to 0 in 2 ms and the read restarts, so a hit cuts the one before, as a one-shot pad on the 404 did, without a click | unknown |
| Velocity | 30 dB of range, even in dB: 127 is 0 dB, 95 (level 6) about −7.6, 16 (level 1) about −26. 0 plays nothing | unknown |
| A track's volume | −30 to +6 dB, added in that pad's `c_voice` to the velocity's own: at 0 dB the velocity's level is as it was, and +6 at 127 is twice the sample's amplitude. Taken at the next hit | unknown |
| A track's pitch | −12 to +12 semitones, as the sample's playback rate, 2^(*st*/12): an octave up plays it twice as fast and half as long, an octave down half as fast and twice as long. Worked out when it arrives, and taken at the next hit | unknown |
| A pad with no sample | Silent, and no error: `c_voice` checks the file is there before reading it | unknown |
| The count | 2 s after load, on `err`: `info c_kit samples-16` with all sixteen, `warn c_kit samples-<n>` with some, `info c_kit no-samples` with none | unknown |
| What it costs | About 0.65% of the Organelle's core for each voice while it sounds; `switch~` keeps a silent voice's DSP off (the Organelle's Reference page) | verified |

### The pattern in a section

| | | Evidence |
|---|---|---|
| Key | `<part>`, `drums`: a part of the section playing, put with the section policy, which `u_song` keeps ([songs.md](songs.md)) | unknown |
| Line | The key, 512 velocities, track 1's 32 steps first, then the sixteen tracks' own last steps, 0 for one that follows the global one, their randomness, their volumes, their pitches, the time signature's two numbers, the drunkenness, the swing and the global last step: 582 atoms, zeros included. Knob 3's last step is the selected track's own, in the line; knobs 2 and 4 are the global last step and the swing | verified |
| Written | `put section` at load and at once after the patch's own messages (a restore, init); after a press or the phone, **held up to 100 ms**: the first change sets a clock, later ones only mark it held, and the clock puts the pattern as it then stands. `bar`, and `sync` from `u_song` before it saves, reverts, copies or starts a section, put it at once. A put carries 581 numbers, and every change sending one, a drag on the phone 30 to 60 a second, cost 4 to 6 ms each on the Organelle and crackled the audio, which runs with a 6 ms buffer (2026-11-05): held, a drag costs 2 ms a change, the put ten times a second. `u_song` writes the song's draft within 2 s | verified |
| Restored | When its section starts, the first at ~3.5 s, and put straight back | unknown |
| A line of exactly 579 | Saved before sections, without the swing and the global last step: those in force stay, and the put after it writes the new line | verified |
| `section-1-<part>` | The `auto` key the pattern had before sections: a restore of it from `u_state`, at the first load after the update, is taken the same way and put as the section's, and the auto file drops it at its next flush | verified |
| A line of exactly 256 | The 16-step pattern this replaced: each track's sixteen go to its first sixteen steps, and the put after it writes the new line | verified |
| A line of exactly 563 | Saved before 2026-11-05, with a skip and a move chance per track where the randomness and the volumes are now: its skip chances come back as each track's randomness, which took their place, its move chances are dropped, and its time signature and drunkenness are read from where it kept them. The put after it writes the new line | verified |
| A short or long line | The Lua takes what the line holds, as far as the drunkenness, a symbol as 0, and leaves the rest as they were; the put after it writes all of it. A line of 528, from before the drum screen's settings, comes back at 4/4, sober, with no randomness and every track at 0 dB and its own pitch | verified |
| A 582-atom line | Written and read whole by `u_song`'s Lua; the sequencer gate's seed, a song of one section, holds a last step of its own, a volume, a pitch and 7/8, which come back, and the final pattern reaches the song's draft | verified |

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

`c_steps` never reads `cut-it-drum-page.txt`. `u_map` turns a pad into a step cell and `g_grid`
lights a cell, from the same table ([display.md](display.md)), so the sequencer's vocabulary is
the table's roles and nothing about the surface. **What it does know is the step cells' shape**,
four rows of eight numbered along the rows, since the time signature's top number sets how many
of a row's cells hold steps (Brendan, 2026-11-05): `R.cell_step` turns a press's cell into its
step, and `g_grid` does the same sum for each cell it paints, from the row length `c_steps` sends
in `bar <N> <row>`. Where the cells sit is still only the table's.

### The time signature shapes the page, not the clock

A bar of *N* × 16 / *D* steps with only its first step blue had no bearing on the page Brendan
could read: at 3/4, steps 1, 13 and 25, wherever they fell in rows of eight (he reported it as a
bug, 2026-11-05). So *N* marks every *N*th step, and a row holds whole groups of *N*, so 3/4's
beats line up down the columns; four rows is the pattern's reach, so a 32-step pattern fits only
where a row is eight. The bottom number is
kept for the record and the phone, and touches nothing else: the steps were never timed by it, and
the bar a queued section waits for is the pattern's loop ([songs.md](songs.md)). **A last step past
the reach is clipped where it is used and kept as set**, because the top number is stepped one at
a time on the phone: 4/4 to 8/8 passes 5/4, whose 20 would otherwise cut a last step of 32 short
for good.

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

### One part of a section

`drums` is the section playing's drum part (`cut-it/songs-and-sections`): it was `section-1-drums`,
an auto key named for a section from the first version, so that songs would make it each section's
without rewriting this file, and they did. Dense, zeros and all, so a restore fills the pattern in
one pass and the line is the same shape every time. The Lua answers what to save and takes the
restore; `c_steps.pd` names the part and puts it with the section policy. **The restore is put
straight back**, as every contributor's must be ([state.md](state.md), *A contributor must put back
what it restores*), and the same put repairs a short or malformed line.

**The arrangement page's settings ride in the pattern's line**: the time signature and the
drunkenness from the first, the swing and the global last step since sections (Brendan,
2026-11-04: a section holds the rhythm page), so knobs 2 and 4 are saved as the phone's values are,
and a section restored holds them again where it set them.

### The bar is the pattern's loop

A queued section starts when the global last step comes round (Brendan, 2026-11-05), so the whole
pattern finishes first; the time signature is not consulted. The Lua knows where the global loop is
and says `bar` as the last answer of its last step, in the same logical instant, so `u_song`'s
restore of the next section reaches the Lua before the next step is cut: the new section's step 1
is the downbeat. That restore starts every loop again from step 1, as PLAY does, since the old
loop's place means nothing in a loop of another length.

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
- ⬜ **Swing, drunkenness, randomness and the tracks' volume and pitch have not played on the
  rig**, nor have the phone's controls for them (the drum screen's radio and its pads' drags) or
  the page's rows and blue steps under the time signature. See `cut-it/drum-timing`.
- ⬜ **The drum screen's pads, showing last steps, still drag 1 to 32**: `c_steps` clips a pad's
  step to the time signature's reach, so past it a drag changes nothing until it comes back under.
  The arrangement screen's box reaches exactly that far. See `cut-it/drum-timing`.
- ⬜ **The Lua version has not played on the rig**: its CPU beside the Pd version's 11.2% with the
  drum machine playing (`~/Sites/!reference/pure-data.md`, *Newer versions on the Organelle*) is unmeasured. See `cut-it/logic-as-text`.
