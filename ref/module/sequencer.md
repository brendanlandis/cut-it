<!-- schema: module -->
# The sequencer

**Files:** `Cut It/c_steps.pd`, `Cut It/c_steps.lua`, `Cut It/c_steps-lua.pd_lua`, `Cut It/c_kit.pd`, `Cut It/c_voice.pd`, `Cut It/e_drive.pd`, `Cut It/e_delay.pd`, `Cut It/e_delays.pd`, `Cut It/e_verb.pd`, `Cut It/e_plate.pd`, `Cut It/e_gigaverb.pd`, `Cut It/e_freeverb.pd`, `Cut It/e_tail.pd`, `Cut It/e_tape.pd`, `Cut It/e_rec.pd`, `Cut It/e_rush.pd`, `tools/samples.sh` · **Gate:** `test/gate/sequencer-assert.sh`, `test/gate/kit-assert.sh` · **Checklist:** `test/checklists/sequencer.md`

## What it is

**`c_steps` knows steps, velocities and pads, and never where they are.** It is a 32-step
sequencer — sixteen tracks of 32 steps, a velocity per step, 0 for off, and a last step for the
whole pattern or for one track — that plays sixteen drum samples on its own `c_clock`, with swing,
drunkenness, a time signature, four repeat pads and one at 500 BPM, a pad for the saved tempo, and a
randomness, a volume, a pitch, a distortion, a delay, a send to one reverb of three types, a mute and a
solo per track (`cut-it/drum-timing`). What a press means arrives already translated from `u_map`
(`step 5`, `vel 3`, `pad 13`), and what the page shows leaves as meaning for `g_grid` (`steps …`,
`play 5`); the layout table that turns one into a cell is theirs, not its. That is the `m_`
boundary, and it is why another surface could drive it unchanged.

**Its rules are Lua, and its timing is Pd.** `c_steps.lua` holds the pattern, the step rule, the
velocity levels, the selection, the last steps and the knobs' latch, each track's place in its
loop, the repeats, each track's randomness, volume, pitch and effects, each step's drunk length, and which pads fire on a step, as plain Lua that runs on the Mac without Pd; `c_steps.pd`
keeps the clock, the transport and the cords to `c_kit`, `g_grid`, `u_song` and `disp`, and asks
the Lua through one pdlua object, `[c_steps-lua $1]` (`cut-it/logic-as-text`).

It is page 2's drum machine (`cut-it/drum-machine`), and a part of every section of the song
(`cut-it/songs-and-sections`): its pattern, with the arrangement page's settings, is the section
playing's `drums`, kept by `u_song` ([songs.md](songs.md)), and it says where the pattern loops, the
bar a queued section waits for. `u_root` holds one instance, `c_steps 1 drums` — bank A, stored as
the part `drums`.

**The drums are played in Pd, by `c_kit`**, since 2026-11-04 (Brendan): sixteen samples, one a pad,
loaded beside the patch and played from memory, where they were the SP-404's pads before, with
each track's distortion and delay and the reverb they share (2026-11-05). *The kit*, below.

## Facts

### The interface

| | Is | Evidence |
|---|---|---|
| Creation arg 1 | Its bank, 1–10, 1 for A, **vestigial**: from when the SP-404 played the drums, which left the rig on 2026-11-04. Track *n* is pad (bank − 1) × 16 + *n*, and `c_kit` plays pads 1–16 only. It stays because dropping it would move arg 2 and the state key named for it | unknown |
| Creation arg 2 | The part its pattern is stored as in a section: `drums` | unknown |
| Inlet | `step <n> <vel>`, `vel <level> <vel>`, `pad <n> <vel>`, `rep <n> <vel>`, and `fast 1 <vel>` and `recall 1 <vel>`, the 500 BPM repeat and the saved tempo, from `u_map`'s `drum-page` destination, presses and releases (velocity 0), a `step`'s *n* the layout table's step cell, 1 to 32 (*The rows of steps*, below); `last` and `track-last <0-1>`, knobs 2 and 3, and `swing <0-1>` if a map row names it, from its `drums` destination, whose map rows name each: knobs 2 and 4 on every page, knob 3 on page 2 alone (Brendan, 2026-11-04); `sync`, `snap` and `select <n>`, the phone's drum screen, and `vol`, `pitch`, `randomness` and `set-track-last <track> <value>`, its pads dragged, and its effects, `drive`, `tone`, `dist`, `char <1-4>`, `delay-note <1-5>`, `delay-feel <1-3>`, `feedback`, `delay` and `send <track> <value>` and `size` and `damping <value>` and `verb-type <0-2>` (*The effects*, below), and `mute` and `solo <track> <0 or 1>`, the M and S under its pads, and `rnd-pitch <track> <0 or 1>`, the button under its show radio, and `num` and `den <-1 or 1>`, `drunk <0-100>`, `set-swing <50-75>` and `set-last <1-32>`, its arrangement screen, from `u_net`'s first outlet. Anything else is `fail c_steps bad-selector` | unknown |
| Outlet 1 | `pad <1..160> <velocity>`, and a track's `vol <pad> <dB>` and `pitch <pad> <semitones>`, every track's at a restore and one when the phone changes it, and its effects, `drive`, `tone`, `dist`, `char <pad> <1-4>`, `delay-time <pad> <steps>`, `feedback`, `delay` and `send <pad> <0-100>`, and the reverb's `size` and `damping <0-100>` and `verb-type <0-2>`: every one at load, then each as the phone changes it and whichever a restore changes, a held repeat's `tape <span> <units>` and `tape-off`, and rush's `rush <span> <hz>`, `rush-rate <hz>`, `rush-off` and `tape-run <1 or 0>`, to `c_kit` | unknown |
| Outlet 2 | The drum page's state, to `g_grid`'s third inlet: `steps <32 levels>` for the selected track, each step's velocity level, 0 for off, `play <step>` (0 while stopped), `vel <level>`, `track <pad>`, `last <step>` for the selected track, `bar <N> <row>`, the time signature as the page shows it, a blue step every *N* and *row* steps to a row, and `rep <pad>`, the repeat pad held, 0 for none, `fast` and `recall <1 or 0>`, the 500 BPM repeat and the saved tempo's pad held, and `quiet <16 flags>`, track 1 first, 1 for each track that won't play, muted or left out of a solo, sent when that changes | unknown |
| Outlet 3 | The phone's state, to `u_net`'s second inlet: 148 numbers, `R.phone`, after the first 88 the selected track's effects, its character last, and the reverb's, then each track's mute and each track's solo, then the reverb's type, then each track's random pitch, sent by the Pd face only when they change, for the drum and arrangement screens ([phone.md](../device/phone.md)) | unknown |
| Outlet 4 | `bar`, to `u_song`'s third inlet, on the step the global loop wraps after: a bar is the pattern's loop (Brendan, 2026-11-05), the time signature no part of it ([songs.md](songs.md)); and `recall tempo`, the saved tempo asked for | unknown |
| Outlet 5 | `fast <1 or 0>`, the 500 BPM repeat pressed and let go, to `u_tempo`'s inlet ([tempo.md](tempo.md)) | unknown |
| Outlet 6 | To `c_melody` ([synths.md](synths.md)): `step <count> <ms> <place>`, each step after its hits, numbered so a repeat pad's step is told from a new one, its place in the global loop; and `last <step>`, the global last step, at load and when it changes | unknown |
| `disp` | Knobs 2 and 3's rows: `last-step 12`, `pad2-last 6`, and held, `last-step 16 (7)`; `swing 62 %` under a map row that names it; and rush's past the handoff, `rush 8300 Hz` | unknown |

### What it does

| | | Evidence |
|---|---|---|
| A step | Sixteen to a bar, cut from the sequencer's own phase, a pair of steps a cycle, which runs at `c_clock 1 4`'s rate times the Lua's: swung, then ×2, `wrap~`, and a `threshold~` on its fall, and sent to the Lua as `tick` (*One phase of its own*, below) | verified |
| When it fires | Straight and sober, on the step's boundary, to the block (1.45 ms): PLAY's step 1 within two blocks of PLAY, whether or not `threshold~` was still to re-arm, and step 3 on the 250 ms it is due at 120 BPM, in the sequencer gate (2026-11-05). That is half a pulse before `u_tempo`'s MIDI pulse for the sixteenth, which every `c_clock` shares (*Start alignment*, [tempo.md](tempo.md)) and nothing in the rig follows (*A step fires on its boundary*, below) | verified |
| Swing | The phone's (knob 4 left it for rush, Brendan, 2026-11-05), 50% to 75%, straight at its bottom and swinging one way only (Brendan, 2026-11-05): the share of each pair of sixteenths the first one takes, so above 50% every second sixteenth comes later. Taken at the next pair. Saved, a section's. 66% at 120 BPM measured 165 and 85 ms | verified |
| The phone's swing and last step | The arrangement screen sets each as it stands, `set-swing <50-75>` and `set-last <1-32>`, the last step clipped to the time signature's reach, where knob 2 sends knob positions through its latch (Brendan, 2026-11-04). The knob is held again at the phone's value, so its next turn waits to pass it rather than jumping back; a selected track that follows the global last step holds knob 3 again too. Saved, a section's, as the knobs' are; a message with no number does nothing | unknown |
| Drunkenness | 0 to 100 from the phone's arrangement screen: at 100 every step strays, by up to two steps longer or shorter, and low settings stay subtle (Brendan, 2026-11-05). At *x*, the slider's 0 to 1, a step strays with the chance *x*/3 + 2*x*⁴/3, by up to *x* + *x*⁴ steps, at random either way: a line, which is most of it low, plus a steep fourth power that adds the rest near the top. At 20% one step in fifteen strays, by up to a fifth of a step; at 50% one in five, by up to 0.56; at 90% three in four, by up to 1.56. A step is never less than an eighth of a step. The error stays: its own drift becomes the clock, and only PLAY puts it back on `u_tempo`'s (Brendan, 2026-11-03). Saved | verified |
| The time signature | Two numbers from the phone's arrangement screen, the top 1 to 32 and the bottom one of 1 2 4 8 16, 4/4 at first, both saved (Brendan, 2026-11-05). **The top number *N*** says how often the page shows a blue step, every *N* steps from step 1, whatever the subdivision, and how long a row of steps is and how far a last step reaches (*The rows of steps*, below). A change of it that moves the reach holds knobs 2 and 3 again, since a turn of either then stands for another step. **The bottom number is a matter of record only**: it changes neither the page nor how fast the steps go, which only the tempo and drunkenness set | verified |
| The rows of steps | The page's step cells are four rows of eight, and a row holds as many groups of *N* as fit in 8, or all 8 when *N* is over 8: rows of 6 at 3/4 and 6/8, blue at a row's cells 1 and 4, or 1; 8 at 4/4, blue at 1 and 5; 5 at 5/4; 7 at 7/8; 8 at 2/4 and at 1/*x*, where every step is blue. Over 8, the blue counts straight through the pattern and wraps across the rows: at 9/8, steps 1, 10, 19 and 28. A row's cells past its steps are dark, and a press there does nothing. The step cell *n*, row *r* and column *c* from 0, is step *r* × row + *c* + 1 | verified |
| How far a last step reaches | Four rows' worth: 24 at 3/4, 32 at 4/4, 20 at 5/4, 28 at 7/8, 32 with *N* over 8. The global last step and every track's own are clipped to it where they are used, on the page, in the loops, the bar and the phone's state, and kept as set and saved, so a time signature passed through on the way to another does not cut them short for good: 32 at 4/4 is 24 at 3/4 and 32 again at 4/4. Knobs 2 and 3 turned all the way up and the phone's `set-last` and `set-track-last` reach exactly that far | verified |
| The repeat pads | The top row of the right 4×4, 1 to 4 from the left: held, every track replays the last 1 to 4 steps it played, while the loops go on underneath unheard; let go, every track plays on from where it would have been (Brendan, 2026-11-03). PLAY lets go | verified |
| A repeat's steps | Played exactly as they were played the first time (Brendan, 2026-11-05): each track's hit, its velocity and its random pitch as its randomness chose them then, and each step's drunk length, so the loop sounds the same every time round, and no die is rolled until it is let go. Mute and solo are heard as they stand: a track muted under a held repeat is silent in it from the next step, one soloed plays it alone. A step edited, or a section restored, under a held repeat is heard once it is let go. Pressed with fewer steps played since PLAY than its number, the steps to come are played, rolled as usual, and kept until there are that many (*A repeat replays what was decided*, below) | verified |
| A repeat's tails | Held, no new delay or reverb, and the tails that were playing replay exactly (Brendan, 2026-11-05): the hits send nothing to the effects, the live sound of the effects is muted while they ring on silently, and the last N steps of what they played, as they ran, swing and drunk lengths included, loop in time with the hits. Move the tempo under it and the loop's speed follows, its pitch with it, like tape. Let go, the live sound comes back and the sends with it (*A held repeat's tails*, below) | verified |
| The 500 BPM repeat | `pad-35`, under repeat pad 1 (Brendan, 2026-11-05): held, the last step plays over and over and the tempo snaps to 500, knob 1 held at the top of its turn until it gets there. Its tails speed up with it, as any repeat's follow the tempo. Let go, the tempo snaps back to what it was before the press, knob 1 held there, and the pattern carries on from the step it was pressed on: the loops and the bars counted from them wait for it, so nothing keeps the canonical beat (a judgment call: *The 500 BPM repeat*, below). The repeat pads do nothing while it is held, and PLAY lets go of it, its tempo back. Nothing of it is put in the section | verified |
| The saved tempo | `pad-38`, under repeat pad 4 (Brendan, 2026-11-05): a press snaps the tempo to the section's saved BPM and, while playing, starts every loop at step 1 that instant, on the start bus, as PLAY does (stopped, it starts nothing). The saved BPM is the saved song's and not the draft's, or for a section never saved, the draft's, knob 1 held there. A press alone: the release only puts its lamp out. The tempo is put in the draft as any change of it is, so save and revert show what that leaves (`u_tempo` and `u_song`: [tempo.md](tempo.md), [songs.md](songs.md)) | verified |
| A track's random pitch | On or off, each track its own, from `rnd pitch` under the phone's show radio (Brendan, 2026-11-05): when the track's randomness flips a coin and the coin plays the hit, that hit has a pitch of its own, a whole number of semitones from 12 under to 12 over the track's set pitch, evenly, kept to the track's −12 to +12, so a set pitch off 0 piles the ones past the edge up on it. Any other hit plays at the set pitch. One more die, rolled only with it on, so a track with it off rolls as it always did. A repeat replays the pitch with the hit. Saved | verified |
| A track's randomness | 0 to 100, each track its own, from its pad on the drum screen (Brendan, 2026-11-05, after the Arturia DrumBrute's Randomness): at *R*% each step it plays has an *R*% chance of ignoring what is written and flipping a coin instead, played or not, and played at one of the eight levels at random. So it drops hits from a busy track and adds them to a sparse one; at 100 every step is a coin, at 0 the pattern plays as written and nothing is rolled. Fresh on every pass, but a held repeat's, which plays the coins as they fell (*A repeat's steps*). Saved | verified |
| A track's volume and pitch | −30 to +6 dB and −12 to +12 semitones, each track its own, 0 at first, from its pad on the drum screen: each is saved and goes to `c_kit` for that track's pad, which plays it from the next hit (*The kit*, below). A restore sends every track's | verified |
| A track's effects | Its distortion's drive, tone and mix and its character, soft, hard, fold or crush, its delay's time, a note value, 1/2 to 1/32, and a feel, straight, triplet or dotted, its feedback and its level, and its send to the reverb, and the reverb's size, damping and type, plate, gigaverb or freeverb, the kit's (Brendan, 2026-11-05): 0 to 100 but the character, the note, the feel and the type, 0 to 2, from the drum screen for the selected track. Each is saved and told to `c_kit`, the note and the feel as the delay's time in steps, a step a sixteenth. Every track starts at drive 50, tone 100, open (Brendan, 2026-11-05: 60, a 3.5 kHz low-pass, dulled every drum), mix 0, soft, 1/8 straight, feedback 40, level 0 and send 0, and the reverb at size 50 and damping 50, the plate: a mix, a level or a send of 0 is off (*The effects*, below) | verified |
| Mute and solo | Each track's own, from the M and S under its pad on the drum screen, `mute` and `solo <track> <0 or 1>` (Brendan, 2026-11-05): with any track soloed only the soloed tracks play and the mutes are ignored; otherwise a muted track doesn't. A track that won't play stops at its next step, while what `c_kit` is already sounding of it, its echoes and its reverb, rings out (*Mute and solo stop the hits, not the sound*, below). Its randomness still rolls and its loop and a held repeat go on, so it comes back in where it would have been. The Launchpad shows its pad dim ([display.md](display.md)). Saved, a section's | verified |
| A track's last step from the phone | `set-track-last <track> <1-32>`, from its pad, clipped to the reach, as knob 3 sets the selected track's: the step a track already has changes nothing, so one that follows the global step goes on following; set for the selected track, it holds knob 3 again. Saved | verified |
| On a step | The global loop moves on, then every track moves on in its own loop, wrapping after its own last step; every track plays the step it is at, its note at its velocity if 1 or more, or as its randomness flips it, or while a repeat is held, what it played at the step repeated; track 1 first, all in one logical instant, but a track muted or left out of a solo plays nothing. Then the playhead moves, to the selected track's step, and the step's drunk length goes to the clock, or the repeated step's | verified |
| PLAY (`start`) | Starts every loop at step 1, the phase on the beat at its own rate, and lets go of a held repeat | verified |
| STOP (`stop`) and `panic` | Stop it, and put the playhead out | unknown |
| A pad press | Plays that pad now, at full velocity however hard it is pressed (Brendan, 2026-11-04), muted or left out of a solo or not, so a muted track can be heard before it comes back in, and selects it as the track being edited | unknown |
| A velocity press | Selects level *n*, velocity round(127·*n*/8): 16 32 48 64 79 95 111 127 | unknown |
| A step's level, whose color it takes | (*v* − 1) div 16 + 1, 0 for off, so each level's own velocity is that level. Worked out here and sent to `g_grid`, the one place the rule is | verified |
| A step press | On the step its cell is in the rows (*The rows of steps*): off takes the selected velocity; on, at any velocity, turns off (Brendan, 2026-11-03). Past its row, or past the selected track's last step, nothing. A release of a step, a velocity or a pad does nothing | unknown |
| The global last step | Knob 2, on every page (Brendan, 2026-11-04), 1 to the time signature's reach, 32 at 4/4, for every track that has no last step of its own (Brendan, 2026-11-03). Steps past it keep their notes, unplayed and dark. Saved, a section's | unknown |
| A track's own last step | Knob 3, on page 2 alone, where the track is selected, 1 to the reach, for the selected track, saved with the pattern. Released at the step a following track already has, it goes on following | unknown |
| The knobs' latch | At load knobs 2 and 3 are held at 16, and knob 3 again whenever another track is selected, or the global last step moves while the selected track follows it: held until turned to or through the step it stands for. A held knob changes nothing and draws its row with its own value in brackets | verified |
| `sync` (the drum screen's "sync first steps") | When the global loop next comes round to its step 1, every track goes back to its own step 1 there, keeping its own last step | verified |
| `snap` (its "snap to global") | The same, and at that step every track gives up its own last step, saved. Stopped, it lands at PLAY | verified |
| At load | Track 1, level 6 (95), last step 16 with knobs 2 and 3 held there, swing 50%, stopped; every track at 0 dB, its own pitch and no randomness until the restore. The pattern is put at once, so the section playing holds the drums from the start | unknown |
| A bar | Ends on the step after which the global loop comes round to its step 1, counted on the machine's own steps from PLAY: the 16th with the global last step at 16, the 12th at 12, however the time signature reads and however drunk, but no further than its reach: a global last step of 32 at 3/4 ends a bar on the 24th. A global last step moved under the loop's place wraps into it with no bar there. `bar` is the step's last answer, after its notes | verified |
| A section's restore | Starts every loop, the global one and each track's, again at step 1 on the next step, as PLAY does: so a section whose global last step differs from the one before starts on its own step 1, not the old loop's place plus one | verified |

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The pattern, the step rule, the velocity levels, the selected track and level, the last steps and the knobs' latch, each track's place in its loop, sync and snap, which pads fire on a step, the playhead, the restore | `c_steps.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Turning messages into those calls and their answers into outlets | `c_steps-lua.pd_lua`, the class `c_steps-lua`: two inlets (the presses, knobs and drum buttons; `c_steps.pd`'s own `tick <bpm>`, `start`, `stop`, `restore` and `init`, and `sync` off the state bus), eleven outlets (notes, page, the pattern to save, `err`, a bang on `init`, the knobs' rows, the drum screen's state, the clock's `swing` and `rate`, the bar and a part's `recall`, the 500 BPM repeat's `fast`, the step and last step for `c_melody`) | verified |
| The clock and its swing and rate, PLAY, STOP and panic, the cords to `c_kit`, `g_grid`, `u_song` and `disp`, `put section <part>` | `c_steps.pd` | verified |
| The Lua's answers on the device | Identical to the Mac's: twenty messages through `c_steps-lua` in a test Pd on the Organelle and on the Mac printed the same 37 lines (2026-11-03) | verified |
| What it costs | About 0.4 MB more peak memory than the Pd version, in a test Pd loading `main.pd` on the Organelle (3.0 to 3.4 MB); pdlua itself is on the Organelle's Reference page | verified |

### The kit

| | Is | Evidence |
|---|---|---|
| `c_kit` | Takes `pad <1..16> <velocity>` from `c_steps`' outlet 1, a pad past 16 ignored, and `vol <pad> <dB>` and `pitch <pad> <semitones>`, a track's volume and pitch, and its effects, and holds sixteen `c_voice`, one a pad, each with its `e_drive` inside it, sixteen `e_delay` inside one `e_delays`, whose own `switch~` is off while all sixteen are, so at rest they are skipped once a block rather than sixteen times (0.2–0.3% of the core; idle went from 15.3–16.0% to 15.3–15.6%, 2026-11-05), and one `e_verb`, summed out its `outlet~`, which `u_root` adds to the left output where the OLED meters it ([audio.md](audio.md)) | unknown |
| A sample | `samples/drums/NN.wav` in the patch's own folder, NN its pad, `01` to `16`: mono 16-bit WAV at 44.1 kHz, as `tools/samples.sh` writes it. Read by `c_voice` at load into a table of its own | unknown |
| A hit | Plays its pad's sample from the start. The level dips to 0 in 2 ms and the read restarts, so a hit cuts the one before, as a one-shot pad on the 404 did, without a click | unknown |
| Velocity | 30 dB of range, even in dB: 127 is 0 dB, 95 (level 6) about −7.6, 16 (level 1) about −26. 0 plays nothing | unknown |
| A track's volume | −30 to +6 dB, added in that pad's `c_voice` to the velocity's own: at 0 dB the velocity's level is as it was, and +6 at 127 is twice the sample's amplitude. Taken at the next hit | unknown |
| A track's pitch | −12 to +12 semitones, as the sample's playback rate, 2^(*st*/12): an octave up plays it twice as fast and half as long, an octave down half as fast and twice as long. Worked out when it arrives, and taken at the next hit | unknown |
| A pad with no sample | Silent, and no error: `c_voice` checks the file is there before reading it | unknown |
| The count | 2 s after load, on `err`: `info c_kit samples-16` with all sixteen, `warn c_kit samples-<n>` with some, `info c_kit no-samples` with none | unknown |
| What it costs | About 0.65% of the Organelle's core for each voice while it sounds; `switch~` keeps a silent voice's DSP off (the Organelle's Reference page). With the effects in it, 0.74–0.78% while a voice sounds with none of its own on, and 0.6% more for the kit at rest (*The effects*, below) | verified |
| A track's distortion | `e_drive`, inside its `c_voice`: the sound scaled to its sample's peak, which `c_voice` tells it once the sample is read, so a drive means the same on every pad, times a gain of g = 10^(drive/50) into `[clip~ lo hi] [-~ 0.25] [cos~] [*~ k] [clip~ lo2 hi2]`, a sine of it, the peak going in at an eighth of a cycle at drive 0 and g times that; then a makeup of 1/√g, but never below −8 dB, 0.4, times the peak again and the character's trim; `hip~ 15` against the DC a lopsided clip leaves; a one-pole low-pass at 300 Hz (tone 0) to 18 kHz (100), even in octaves; and mixed with the dry sound by `dist`, its mix: the voice sums the dry with mix × (driven − dry). At mix 100 a sine at drive 100 is a square at 0.36 of its peak, as loud as at drive 50; at mix 0 the dry passes untouched | verified |
| Its characters | Brendan's (2026-11-05), the same chain's numbers, lo hi k lo2 hi2 and a trim: **soft**, −0.25 0.25 1 −1 1 and 0.9, a sine-shaped soft clip; **hard**, −0.25 0.25 3 −0.6 1 and 1, a hard knee, lopsided; **fold**, unclipped, 1 −1 1 and 1.1, the sine folding back past a quarter cycle; **crush**, −0.25 0.25 1.5 −1 1 and 0.8, its gain 0.175 × 10^(drive/100), a range of ten, its makeup down to −6 dB, then rounded to 6 bits, 32 steps either side of 0, and held at 22 kHz × 2^(−0.03 × drive), 22 kHz at drive 0 to 2.8 kHz at 100. Choosing one is numbers, and costs nothing: the crush's rounding and hold are a subpatch, `pd crush`, with a `switch~` of its own, on only for crush | verified |
| A track's delay | `e_delay`, beside its `c_voice`: what the voice throws it at the delay's level, squared, `(level/100)²`, plus its own echoes at feedback × 0.95, into a 4 s buffer, read a note value later: the time in steps times a step's length, 15000 / BPM ms from the tempo bus, so it follows the tempo, gliding there over 50 ms. A half note at 240 BPM echoes 500 ms after its hit, to the sample. The level is what goes in, so echoes already made ring out when it goes down | verified |
| Rush | `e_rush`, between all of the above and `c_kit`'s `outlet~`: `rush <span> <hz>`, `rush-rate <hz>` and `rush-off` from `c_steps` freeze the kit's whole output and loop what is being repeated of it (*Rush*, below) | unknown |
| A held repeat's tails | `e_tape`, between `c_kit`'s `catch~` and its `outlet~`: everything on `$0-out`, the delays and the reverb, the voices' dry sound going round it. A 12.5 s delay line records it all the time, in an `e_rec` with a `switch~`, and a `pd play` with a `switch~` of its own reads it while a repeat is held. `tape <span> <units>` zeroes the sends, freezes the recording three blocks later, then plays *span* ms of it in *units* steps' time at the tempo in force. Off: the sends back, the live sound and the loop crossing back in 10 ms, the recording running on once the player is silent (*A held repeat's tails*, below) | verified |
| The reverb | `e_verb`, one for the kit, since sixteen are more than the Organelle can afford, of three types the phone chooses between (Brendan, 2026-11-05): the **plate**, Dattorro's in vanilla boxes, `e_plate`, the one it starts on; **gigaverb**, ELSE's `giga.rev~`, `e_gigaverb`; and **freeverb**, Jezar's Freeverb in vanilla boxes, its eight combs and four allpasses, `e_freeverb`. Each takes what every voice and delay throws `e_verb` at its track's send, squared, behind the same controls: size is its decay, measured the same in each, 0.5 s at 0 to 10 s at 100, even in ratio, 2.2 s at 50; damping darkens each tail alike, none at 0; and their levels are matched, so a change of type does not jump. Mono: the plate's and gigaverb's two sides are summed. Its output is the reverb alone (*Three reverbs behind the same controls*, below) | verified |
| Off when unused | Each effect has a `switch~`: a distortion is on while its mix is above 0; a delay while its level is, and at 0, once what goes into it has been below −80 dBFS for its time and 100 ms, its buffer then cleared; each of the reverb's engines while it is the type and any send is above 0, and once it is not, until its tail has been below −80 dBFS for 300 ms, so a type changed away from rings out first, and `e_verb` while any engine is. The voice's throws to its delay and the reverb are switched the same way, on while its level or its send is | verified |

### The pattern in a section

| | | Evidence |
|---|---|---|
| Key | `<part>`, `drums`: a part of the section playing, put with the section policy, which `u_song` keeps ([songs.md](songs.md)) | unknown |
| Line | The key, 512 velocities, track 1's 32 steps first, then the sixteen tracks' own last steps, 0 for one that follows the global one, their randomness, their volumes, their pitches, the time signature's two numbers, the drunkenness, the swing and the global last step: 582 atoms, zeros included. Once any effect is off its starting point, each track's eight effects follow, `R.FX`'s order, drive, tone, mix, note, feel, feedback, level and send, sixteen of each, then the reverb's size and damping: 712 (Brendan, 2026-11-05: saved per section, with the pattern). While none is, the line stays 582, so a song saved before the effects is put back as it was and nothing about it reads as a change to save. Once any track is muted or soloed, the sixteen mutes and the sixteen solos, 1 or 0, follow the effects, written whether any effect moved or not: 744 (Brendan, 2026-11-05: saved per section, with the pattern). Once any track's distortion is not soft, the sixteen characters, 1 to 4, follow the mutes and solos, written whether anything before them moved or not: 760 (Brendan, 2026-11-05: saved per section). Once the reverb's type is not the plate, it follows the characters, 0 to 2, everything before it written as it stands: 761 (Brendan, 2026-11-05: saved per section, as its size and damping are). Once any track's random pitch is on, the sixteen flags, 1 or 0, follow the type, everything before them written as they stand: 777 (Brendan, 2026-11-05: saved per section). Knob 3's last step is the selected track's own, in the line; knobs 2 and 4 are the global last step and the swing | verified |
| Written | `put section` at load and at once after the patch's own messages (a restore, init); after a press or the phone, **held up to 100 ms**: the first change sets a clock, later ones only mark it held, and the clock puts the pattern as it then stands. `bar`, and `sync` from `u_song` before it saves, reverts, copies or starts a section, put it at once. A put carries 581 numbers, and every change sending one, a drag on the phone 30 to 60 a second, cost 4 to 6 ms each on the Organelle and crackled the audio, which runs with a 6 ms buffer (2026-11-05): held, a drag costs 2 ms a change, the put ten times a second. `u_song` writes the song's draft within 2 s | verified |
| Restored | When its section starts, the first at ~3.5 s; put back only if it differs from what the sequencer would save | unknown |
| A line without the effects | Of 581 numbers, or any length below 711 the Lua takes: every effect comes back off, at its starting point, and `c_kit` is told whichever changed. So an old section's drums play dry | verified |
| A line without mute and solo | Of 711 numbers or fewer, any length the Lua takes: every track comes back unmuted and unsoloed, and the page is told when that changes its pads. So an old section plays every track | verified |
| A line without the characters | Of 743 numbers or fewer, any length the Lua takes: every track comes back soft, and `c_kit` is told whichever changed. So an old section's distortion is soft. Its tone stays as it was saved: a section saved with an effect moved before the tone opened holds tone 60 | verified |
| A line without the type | Of 759 numbers or fewer, any length the Lua takes: the reverb comes back as the plate, and `c_kit` is told when that changes it. So an old section plays the plate | verified |
| A line without the random pitches | Of 775 numbers or fewer, any length the Lua takes: every track's comes back off. So an old section rolls no pitches | verified |
| A line of exactly 579 | Saved before sections, without the swing and the global last step: those in force stay, and the put after it writes the new line | verified |
| `section-1-<part>` | The `auto` key the pattern had before sections: a restore of it from `u_state`, at the first load after the update, is taken the same way and put as the section's, and the auto file drops it at its next flush | verified |
| A line of exactly 256 | The 16-step pattern this replaced: each track's sixteen go to its first sixteen steps, and the put after it writes the new line | verified |
| A line of exactly 563 | Saved before 2026-11-05, with a skip and a move chance per track where the randomness and the volumes are now: its skip chances come back as each track's randomness, which took their place, its move chances are dropped, and its time signature and drunkenness are read from where it kept them. The put after it writes the new line | verified |
| A short or long line | The Lua takes what the line holds, as far as the drunkenness, a symbol as 0, and leaves the rest as they were; the put after it writes all of it. A line of 528, from before the drum screen's settings, comes back at 4/4, sober, with no randomness and every track at 0 dB and its own pitch | verified |
| A 760-atom line | The sequencer gate makes track 4's distortion fold over OSC, as the phone sends it: it is put at once, its character after the mutes and solos, `c_kit` is told `char 4 3`, and the final pattern reaches the song's draft whole | verified |
| A 777-atom line | The sequencer gate turns track 1's random pitch on over OSC, as the phone sends it, after the type: it is put at once, the flags last, and the final pattern reaches the song's draft whole | verified |
| A 761-atom line | The sequencer gate makes the reverb gigaverb over OSC, as the phone sends it, after the character: it is put at once, the type last, `c_kit` is told `verb-type 1`, and the final pattern reaches the song's draft whole | verified |
| A 744-atom line | The sequencer gate mutes and then solos track 1 over OSC, as the phone sends them: each is put at once, the final pattern reaches the song's draft whole, track 1 muted and soloed, and its notes stop and start as the rules say | verified |
| A 712-atom line | Written and read whole by `u_song`'s Lua; the sequencer gate's seed, a song of one section, holds a last step of its own, a volume, a pitch, 7/8 and four tracks' effects and the reverb's size, which come back, and `c_kit` is told the effects that moved since load and no others, and the final pattern reaches the song's draft | verified |

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

**Swing bends each pair.** The phase is shifted back a ten-thousandth of a pair first, for PLAY
(*A step fires on its boundary*, below); `samphold~` takes the swing as the pair begins, so a turn
never moves a step already cut; and an `expr~` gives the first step the swing's share of the pair
and the second the rest. Then ×2, `wrap~`, and the threshold on `1 −` that: a step is the phase's
fall from near 1 to 0. A threshold on a rising phase was not re-armed by a `start` landing
mid-step, and PLAY's first step came a step late.

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

### A repeat replays what was decided

Brendan's (2026-11-05): a held repeat plays *exactly* what was played on the steps it covers,
including what the randomness chose that time. So `R.tick` decides each step once, before mute
and solo: every track's hit and its velocity after its randomness, and the step clock's rate for
the step's length, drunk or not. It keeps the last four, and a repeat pad takes the last *n* and
plays them again in a loop, rolling nothing. Mute and solo are asked as each step plays,
repeated or not, so a track muted or soloed under a held repeat is heard so, and a muted track's
coins, decided all the same, are heard if it is unmuted mid-repeat. A track's volume, pitch and
effects are `c_kit`'s, live anyway. **Swing is the clock's, not a step's**: a repeat of 2 or 4
keeps its pairs, but one of 1 or 3 at a swing above 50% plays its steps alternately long and
short.

Three judgment calls (2026-11-05):

- **Pressed with fewer steps played since PLAY than its number**, the steps to come are played,
  rolled as usual, and kept until there are that many, so a repeat is as long as its pad says:
  pad 4 held on PLAY's second step loops steps 1 to 4. Pressed before anything has played since
  load, it does nothing, as before; PLAY lets go of it anyway.
- **A step edited under a held repeat** is heard once it is let go: the repeat is what was heard.
- **A section restored under a held repeat** is the same: the repeat goes on with the old
  section's steps while the new section's loops start underneath, and let go, the new section
  plays from where they have got to.

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

### A step fires on its boundary

The drums play in Pd, and nothing in the rig follows `u_tempo`'s MIDI clock: it goes to the
Launchpad alone, which ignores it in Programmer Mode ([tempo.md](tempo.md)). So a step fires on
its boundary and not in that clock's pulse, half a pulse later, where it fired while the SP-404
played the drums from it; waiting for the pulse only kept PLAY's step 1 a twelfth of a step late,
10 ms at 120 BPM and 42 at 30 (`cut-it/drum-machine`, 2026-11-05). The beat row and a queued
section's blink, which `c_clock`'s beat drives, light half a pulse after the step they mark.

**The phase still goes back a ten-thousandth of a pair, for PLAY.** `threshold~` makes one change a
block, and its input must fall below 0.4 to re-arm, which it does only late in a step. PLAY resets
the phase to 0; shifted, that reads as the last sliver of a step, low, so a `threshold~` still
waiting to re-arm does so in that block and fires on the boundary in the next, and an armed one
fires in the first. Unshifted, the reset reads as a step's start, high, and a PLAY in the first
60% of a step would leave it waiting: step 1 a whole step late. A ten-thousandth is under a block
at any tempo down to 5 BPM.

**Gear that follows the MIDI clock again would hear the drums half a pulse early**, plus its own
lag: shift the phase back a twelfth of a step (1/24 of the pair, the `-~` in `c_steps.pd`) to land
them in the pulse, as before.

### STOP and panic both stop it

The transport is `u_tempo`'s, and `stop` is the request for it. A panic stops the sequencer too, or
it would play straight through the silence the panic made; the pattern is kept.

### One part of a section

`drums` is the section playing's drum part (`cut-it/songs-and-sections`): it was `section-1-drums`,
an auto key named for a section from the first version, so that songs would make it each section's
without rewriting this file, and they did. Dense, zeros and all, so a restore fills the pattern in
one pass and the line is the same shape every time. The Lua answers what to save and takes the
restore; `c_steps.pd` names the part and puts it with the section policy. **A restore is put back only
if it differs from what the sequencer would save**: a line in an older shape, or short or malformed,
is repaired that way, while one the store already holds isn't sent again. Unlike `u_state`'s keys
([state.md](state.md), *A contributor must put back what it restores*), the song store keeps a part
whether or not it is put back. A section change happens just before the beat, and work there stalls
the audio: Pd runs with a 6 ms buffer, and the beat dropped around a section's 1 (Brendan, 2026-11-05).
So `c_kit` also hears only the volumes and pitches that differ.

**The arrangement page's settings ride in the pattern's line**: the time signature and the
drunkenness from the first, the swing and the global last step since sections (Brendan,
2026-11-04: a section holds the rhythm page), so knob 2 and the phone's swing are saved as the phone's values are,
and a section restored holds knob 2 again where it set it.

### The bar is the pattern's loop

A queued section starts when the global last step comes round (Brendan, 2026-11-05), so the whole
pattern finishes first; the time signature is not consulted. The Lua knows where the global loop is
and says `bar` as the last answer of its last step, in the same logical instant, so `u_song`'s
restore of the next section reaches the Lua before the next step is cut: the new section's step 1
is the downbeat. That restore starts every loop again from step 1, as PLAY does, since the old
loop's place means nothing in a loop of another length.

### The effects

Brendan's (2026-11-05): a distortion and a delay on each track, so different drums can have
different delays, and a send from each to one reverb, since sixteen reverbs are more than the
Organelle can afford. The phone's drum screen sets them for the selected track
([phone.md](../device/phone.md)), `c_steps` keeps and saves them with the pattern, as it does a
track's volume and pitch, and `c_kit` plays them. Measured on the Organelle, each in a second Pd
beside the live one (its Reference page, *Cut It's drum effects*):

| | Its share of the core |
|---|---|
| The kit at rest, every effect off | 1.7%, 0.6 more than before the effects |
| A voice sounding, no effect on | 0.74–0.78%, 0.1 more than before |
| A distortion, while its voice sounds | 0.33%, before its characters (below) |
| A delay | 1.05% |
| The reverb before its types, four combs and two allpasses | 1.7% |
| Its plate, gigaverb and freeverb | about 4.5%, 3.8% and 3.0%, estimates scaled from the Mac until measured here (*Three reverbs behind the same controls*, below) |
| All sixteen with every effect on, every voice sounding | 39–42%, sixteen voices alone 13.5–14.2%, before the characters and the reverb's types |

⚠️ **The distortion's characters are estimates until measured on the Organelle** (2026-11-05):
each character's `e_drive` and the one before them, 64 copies each fed a drum sample, 60 s of
audio under `-batch` on the Mac, the least cycles of five runs less the sample players alone,
scaled to the 0.33% the old one measured on the Organelle. The low figure is the cycles' ratio,
the high one the instructions', which the Mac's Reference page counts the nearer guess where a
box calls a function:

| Character, while its voice sounds | Against the old distortion | Estimate on the Organelle |
|---|---|---|
| Soft, hard or fold | 2.0× the cycles, 2.55× the instructions | 0.65–0.85% |
| Crush | 2.8× the cycles, 4.1× the instructions | 0.9–1.35% |

So all sixteen with every effect on, every voice sounding, would be about 44–51% rather than
39–42%. The crush stage computed for every character, rather than behind its own `switch~`, cost
soft, hard and fold 2.6× the cycles. At rest nothing changes: the distortion is off at mix 0, its
crush stage with it.

**An effect unused costs nothing**, or as near as Pd allows: each has a `switch~`, off while its
mix, its level or every send is 0, and a delay or the reverb stays on after that only until its
tail has died, so turning one down never cuts what it is still sounding. Nothing gets louder or
thinner for being switched: a switched-off abstraction's output is silence, and the distortion adds
to the dry sound only what it changes. The 0.6 the kit costs at rest more than it did is sixteen
`delwrite~`s, which cost a little even switched off, and the voices' switched-off distortion and
sends. On the full rig's 15.2% that makes about 15.8%, inside `tools/display-cpu.sh`'s budget of
16.2%: an estimate from the second Pd, until the instrument is measured with them deployed.

**The distortion is in the voice, the delay beside it.** A distortion only ever sounds while its
voice does, so in `c_voice` it costs nothing between hits; a delay's echoes outlive the hit, so it
is an `e_delay` of its own in `c_kit`, beside the voice.

**They reach each other by `throw~` and `catch~` under `c_kit`'s `$0`, not by cords** (C-1). A
switched-off abstraction with a signal inlet or outlet still copies a block through it every
block: sixteen delays corded in and out cost 2.2% of the core at rest, against 0.3% thrown to. The
voices' dry sound stays on its cords into `c_kit`'s `outlet~`, as it was. Two things keep the
throws safe. A `catch~` that is switched off does not empty itself, so whatever is thrown at it
piles up until it runs again: each one is on whenever anything but zeros can reach it, a delay
while its level is above 0, the reverb while any send is. And Pd runs boxes with no signal inlet
in the reverse of their order in the file, so `c_kit`'s delays, its reverb and its `catch~` come
after the voices and run before them: the delays first, then the reverb, then the `catch~`, so
each catches its throws in the block they were made, and only a voice's throw to its delay arrives
a block late, 64 samples, which `e_delay` takes off the time. `kit-assert` holds an echo to the
sample, and `audio-assert` holds exactly these throws, all private to `c_kit`.

**The distortion is one chain of plain boxes, four characters by its numbers** (Brendan,
2026-11-05: it "should make the samples sound bigger, harsher, more distorted"). The cubic soft
clip it replaced was weak more for its level and its tone than its curve: its makeup fell as
1/√g all the way, so at drive 100 a hit's peaks sat 18 dB under the dry sample, and its tone
started at 60, a 3.5 kHz low-pass. Now more drive is louder and dirtier, never quieter: the
makeup stops at −8 dB, and at drive 75 the research measured a kick +2 dB, a snare +4 and a hat
+1 against the dry, by their level, their peaks never above the dry's. `[-~ 0.25] [cos~]` is a
sine of its input, a soft clip below a quarter cycle and a fold past it, so soft, hard and fold
are five numbers of one chain (`~/Sites/!reference/pure-data.md`, *Distortion*), and crush is
soft's into a rounding and a hold. `expr~ tanh` cost 1.4% of the core a voice. There is no
oversampling: a clipped drum's aliasing is part of its edge, and oversampling took it off and
cost 5.6 times the old clip.

**The delay's time is a note value**, 1/2 to 1/32, straight, triplet or dotted (Brendan,
2026-11-05), since that is how he counts it: `c_steps` tells `c_kit` it in steps, and `c_kit`
works out a step's length from the tempo bus, so the echoes follow the tempo, as the steps do, and
not the drunkenness or the swing, which bend the steps alone.

**`c_kit` sets no effect of its own at load**: `c_steps` tells it every one at load, and after that
each that changes. Pd fires an abstraction's loadbangs before its parent's, `c_steps`' before
`c_kit`'s, so a value `c_kit` set at load would land after `c_steps`' and undo it; each box holds
its starting point instead. A restore tells `c_kit` only the effects that changed, since every
message out of the Lua costs about 0.025 ms on the Organelle and there are 130 of them: a
section's restore lands on a step.

**The line grows only when an effect is used.** It stays the 581 numbers it was while every effect
is at its starting point, so a song saved before the effects restores, isn't put back, and reads
as nothing to save; once one moves, the line is 711. The characters came after
mute and solo, so they are saved after them, 759 once any track is not soft, and a line saved
before them loads every track soft.

### Three reverbs behind the same controls

The reverb that was, four of Freeverb's combs and two of its allpasses, "sounds very cheap and
unnatural" (Brendan, 2026-11-05), and renders of his drums through the candidates left him unable
to choose between three, so **the phone chooses**: a third control beside size and damping, its
type, saved per section as they are. Each type is an engine of its own inside `e_verb`:

- **The plate**, `e_plate`: Dattorro's plate (*Effect Design Part 1*, JAES 1997, figure 1) in
  vanilla boxes, the research's sketch as he heard it, modulated tank and all, its two sides' seven
  taps each summed. The one a section starts on, and the one every section saved before the types
  plays.
- **Gigaverb**, `e_gigaverb`: ELSE's `[else/giga.rev~]` in a room of 25, early reflections a
  quarter of its tail and its dry sound off, as the research heard it, its two sides summed. It
  creates silently under `-nogui` on the Mac; on the device it has not been loaded yet (*Open*).
- **Freeverb**, `e_freeverb`: Jezar's public-domain Freeverb in vanilla boxes, not the binary
  `freeverb~`, which would need a build for every machine: eight lowpass-feedback combs and four
  allpasses at the standard tunings, its left side. On a drum phrase it matches `freeverb~`'s left
  output to −124 dB, float rounding; against the research's render, which averaged both sides, its
  octave bands from 250 Hz up are within 0.4 dB, its decay the same, 0.98 s against 0.99, its
  125 Hz 2 dB lower and its tail a little less dense, one side's combs against two's.

**The same controls mean the same in each**, measured, not assumed (2026-11-05, Pd 0.57 on the Mac):

| | Is | Evidence |
|---|---|---|
| Size | Each engine's decay, worked out so its tail's T30 from an impulse is 0.5 s at 0 to 10 s at 100, even in ratio, as the research's plate read size: within 5% of it from size 22 to 100 in all three. At 0 the plate and gigaverb ring 0.55–0.57 s, their floor. The plate's tank decay, gigaverb's own decay in seconds and freeverb's one comb feedback each carry the factor that makes them measure true | verified |
| Damping | Each tail darkened alike: the 4 kHz band's decay over the 500 Hz band's is 1.0 at 0, about 0.73 at 50 and 0.61 at 100 in all three, which is Freeverb's own damping range. The plate's low-pass pole is 0.959 d / (d + 23), gigaverb's damp 0.006 d: its 1 leaves no tail | verified |
| Level | Matched as the research's renders were: Brendan's drum phrase sent through each, its RMS high-passed at 300 Hz, within 0.5 dB of the plate from size 22 to 80, and 1.2 dB at 100. A longer tail is louder in each, gigaverb's and freeverb's more than the plate's, so their gains fall a little as size grows. Gigaverb is 2.2 dB quieter at size 0. The plate at size 22, which decays about as the reverb before it did at its 50, is as loud as that was | verified |
| Type | `verb-type <0-2>`, 0 the plate, 1 gigaverb, 2 freeverb, from the phone's radio under size and damping ([phone.md](../device/phone.md)), saved and told to `c_kit`, which tells `e_verb` `type`: a line without it is the plate | verified |

⚠️ **Size reads longer than it did.** The reverb before its types read size 50 as about 0.9 s, its
comb feedback 0.84; every type now reads it as 2.2 s, and size 22 is the old 50. A section saved at
the starting point plays a longer tail, about 1 dB louder.

**Only the chosen engine runs.** Each sits in its own `switch~`, run by `e_tail`: on as soon as it
is wanted, the type with a send above 0, and once it is not, off when its tail has been below
−80 dBFS for 300 ms, its delay lines cleared. So a change of type stops the old engine taking the
sends, it rings out, and the two run together only for that tail; and with every send at 0 and every
tail died, nothing of the reverb runs. `e_verb`'s own `switch~` is on while any engine is, so at
rest it is skipped once a block, as before. The reverb before its types went off 300 ms after the
last send went to 0 even while its tail still sounded; `e_tail` waits for the tail.

**The sends reach the engines by `send~` and `receive~`**, `e_verb`'s `$0-in`, which each engine
takes at its own gain while it is wanted and at 0 once it is not. The `catch~` and the `send~` come
after the engines in `e_verb`'s file, so they run first and the engines hear the block they are
in. `audio-assert` holds this one `send~` as it holds the throws.

**What each costs**, measured on the Mac with `-batch` against the reverb before its types the same
way, 600 s of noise at a send of 50, seven rounds, its median share net of an empty patch, and
scaled to that reverb's 1.7% on the device (*Cut It's drum effects* on the Organelle's Reference
page):

| | On the Mac, against the reverb before | On the device, estimated |
|---|---|---|
| Plate | 2.6× | about 4.5% |
| Gigaverb | 2.2× | about 3.8% |
| Freeverb | 1.75–1.8× | about 3.0% |
| At rest, every send 0 | the same as before | 0 |

Gigaverb is C and the plate and freeverb are boxes, so the device may weigh them differently:
these hold until the instrument is measured there. A change of type costs both engines for the old
one's tail.

**`kit-assert` tells the engines apart by ear**: a click's reverb starts at once in gigaverb, after
394 samples in the plate, the right half's first tap, and after 1116 in freeverb, its shortest
comb, each a block later for the voice's throw. So a type routed to the wrong engine, or to two,
fails, where a tail and a level would pass.

### A held repeat's tails

Brendan's (2026-11-05), of a held repeat: "Not create any more delay or reverb, and replay the reverb
and delay tails exactly that they were playing before... the tails should shrink or grow if I adjust
the bpm while holding repeat." So tape: the wet sound is recorded all the time, the recording stops
where the replay begins, and the last N steps of it loop, at a speed that fits N steps of the tempo in
force.

**`c_steps.lua` says when and how much, `e_tape` plays it.** On the step the replay begins, before
that step's hits, `R.tick` sends `tape <span> <units>`: *span*, how long in ms the window's steps ran,
each at the tempo it was decided under, and *units*, the same steps in steps. `e_tape` reads the tempo
bus itself, as a step's length from `c_kit`, so the loop's rate is 1000 / (*units* × step) Hz, on both
sides of a tempo change at once, and its speed the span over that. At the tempo it was recorded under
the speed is exactly 1, and the loop comes round on the hits without a correction, since both run from
one rate. Knob 1, a tap and the phone are all on the one bus.

**A step's length is worked out, not timed.** Each step decided keeps its length in steps, its share
of its pair of sixteenths and the BPM, which comes with each `tick`, since a sweep of knob 1 is some 200
BPMs a second and a Lua call each would be a cost for nothing, so a span is exact to the step clock's own sums, where a
`[timer]` is good to a block and a loop of an eighth of a second would play 1% off pitch. An even
window keeps its pairs, so its swing is in both numbers and cancels. An odd one plays alternately long
and short (*A repeat replays what was decided*), so the swing is left out of both: it plays at speed 1
and comes round on the hits every second time, half a pair either side of them in between (a judgment
call). A swing turned under a held repeat of drunk steps moves the hits off the loop until it is let
go, as nothing resends the units.

⛔ **A delay line frozen by a `switch~` does not read as a running one.** `delread4~` counts back from
the write head and steps on a block every block with it, so a frozen line played by a steady delay
repeats one block forever. `pd play` takes off 63 − *i* from what it asks for the block's sample *i*,
from a 64-point table `tabreceive~` reads every block, and the head goes where the phase says. Measured
smooth to float rounding; without it the read jumps 64 samples a block (Reference, `pure-data`,
*A delay line frozen by a `switch~`*). The kit gate's level, pitch and place checks all fail without it.

**The seam is a crossfade over the tape's own past.** Two heads a loop apart: over the loop's last
10 ms of tape, or its last quarter if shorter, the head a loop back fades in, reading what came before
the loop's start, as the other fades out, and it arrives at the loop's start exactly as the phase
wraps. So nothing jumps, and the recording only ever has to hold the loop and those 10 ms.

**The recording stops three blocks after the step and fades out over them**, and fades in when it runs
on. It can't simply stop: a quick release and press reads back across the place, and a frozen tail
meeting a live one there would click on every pass. So where two stretches of recording meet is a
dip to silence, 8 ms of tape, in a repeat that spans it. The loop's end stays on the step: its reads are
192 samples short of the write head, and the player starts those three blocks in, where it would have
been. The player has to be silent before the recorder runs again, 11.7 ms after a release, or the
head reads a moving line.

**The sends are zeroed at the voices, one block's ramp, and no `catch~` is ever switched off** (*They
reach each other by `throw~`*, above). A hit's sound only rises 2 ms in, so a hit on the replay's
first step sends nothing at all. The engines ring on, muted, with their own tails dying, so what is
heard after a short hold is what would have been there. An echo going on into the reverb counts as
its tail, and goes on. A voice sounding at a release sends what is left of it.

**The loop's length is capped at 12 s**, four steps at the legal tempo's slowest, 5 BPM; the line holds
12.5 s for the seam and the recording's end, 2.2 MB. A repeat longer than that, only a very drunk one
down there, plays its last 12 s in the time its steps take, slower and lower.

**What it costs**, measured on the Mac with `-batch` against a delay's cost (`-r 44100`, 120 s of audio,
least of five runs of `c_kit` alone), and scaled to a delay's 1.05% on the device: at rest, recording,
0.18–0.30% of the core more than before (0.17× a delay's cycles, 0.29× its instructions), which takes
the kit from 1.7% to about 2%; held, 1.45–1.7% more (1.63× the cycles, 1.39× the instructions). Estimates
until measured on the Organelle. `tools/display-cpu.sh`'s budget of 16.2% has about 0.1 left on the
effects' estimate; an Organelle S2 is coming (Brendan, 2026-11-05), so this one is not worth more boxes.

### The 500 BPM repeat

Brendan's (2026-11-05): `pad-35` repeats one cell at 500 BPM, a machine gun to reach for and let go of,
and he said there is no need to keep the canonical beat through it, "though if that's free or easy to
implement, fine". It isn't: what would have been playing depends on every drunk step and swing the
pattern would have rolled, and landing on it means moving the clock's phase. **So the loops wait** (a
judgment call): nothing advances, no bar ends and no section starts while it is held, and on release the
next step is the one after the step it was pressed on, with the clock's phase wherever it is. It reads
as stopping the pattern, playing a fill, and going on.

**Its tempo is a flourish, not a change to the song.** `u_tempo` keeps the BPM in force, sends 500 the
way a tap's goes, so `u_map` holds knob 1 at the end of its turn, and on release sends the kept BPM the
same way, knob 1 held there. A spigot keeps every BPM in between out of the section, so the draft never
reads 500 and save and revert don't flicker. The knob can be turned to its end and go live, and the
phone can move the tempo, both heard at once in the repeat and its tails, and both gone at the release.
A section's tempo restored under it, which only a press of a section button can do, becomes what the
release goes back to.

### Rush

Brendan's (2026-11-05), of knob 4: "keep feeling faster and faster. At a certain point, we hit the audio
range of repeats... After that point, it starts playing a recording of whatever's being repeated, and
that recording keeps getting higher and higher pitched as the knob continues turning." Then, having heard
it: one grabbed 15 ms step made a pattern hitting a few times a second suddenly a 66 Hz tone, so the loop is
now what is being repeated. `u_tempo` has the knob's curve and the tempo up to the handoff, 1000 BPM
([tempo.md](tempo.md)); past it `c_steps.lua`'s `R.rush` says when and how much, and `e_rush`, at the very
end of `c_kit`, plays it.

**The capture is the next step's boundary**, at most 15 ms off with the bus at 1000, or at once if nothing
is playing. It tells `c_kit` `rush <span> <hz>`, and no hit plays. *span* is the last *N* steps as they
ran, each worked out from the BPM, length and swing share at its tick as *A step's length is worked out*
says, *N* being the repeat pad held, one under `pad-35`, and with neither the whole pattern, the global
loop's steps. 32 steps at 1000 BPM are 480 ms; the recorder keeps 3 s, and a knob thrown from a slow tempo
loops the last 3 s of what ran.

**The rest of the knob's turn is the loop's frequency**, from 1000 / *span* Hz, playback speed exactly 1, so
nothing jumps, evenly up to 22 kHz at the top, whatever *N* is. With the steps at 1000 BPM that start is
(1000/15) / *N* Hz, and a pattern of sixteen starts at 4.2 Hz; if they ran slower, since the knob was
thrown, it starts lower, at speed 1 all the same (a judgment call, over a fixed (1000/15) / *N*). The row
reads that frequency, and draws nothing until there is a loop to read.

**While it plays** the step clock runs on and reaches nothing, by a second spigot in `c_steps.pd`: no Lua
call and no phone state 66 times a second. The loops wait, as under `pad-35`, and no bar ends, so a queued
section waits too. Anything but the knob that ends it, a tap, the phone, a section, knob 1, lets the steps
carry on from where they stopped, over a 5 ms cross. **`pad-38` is the
way home:** the loop stops, over the same 5 ms cross, the tempo goes to the section's saved BPM and step 1
restarts, as ever while playing, and both knobs are held there.

**A held repeat's tail loop stops under it**, 16 ms in, once the kit is muted, since the recording has the
wet in it: `tape-run 0` stops `e_tape`'s player with its recorder still frozen, and `tape-run 1` carries on
from there. A repeat let go meanwhile is a `tape-off` as ever. `pad-35` pressed or let go ends rush as any
tempo does. **STOP and panic stop the loop too**, parked until the knob comes below the handoff or PLAY,
since silence is what they ask for (judgment calls).

**The way down lands where the loop is** (Brendan, 2026-11-05: "It doesn't really skip on the way up, but
it does on the way down."). Below the hand-back, `rush-back <bpm>`: the loop is brought to speed 1, in case
the knob was thrown, and asked where it is. `e_rush` answers in that same instant, `rush-at <0-1>`, a
`snapshot~` of the player's phase, out `c_kit`'s second outlet to `c_steps`. By how long each ran, that is one
of the loop's steps, part way through, so many back from the last. A held repeat's next step goes back that
far, or with none held the global loop's place and each track's in its own, and the pair's parity with them,
and the step clock's phase is set so the next step comes when this one ends in the loop: `place <phase>`,
two steps a cycle, swing ignored, an error under a step at these speeds. Setting a phase can fire
`threshold~` at once, so the ticks come back 4 ms later, and the next step is kept 5 ms off. The kit and the
loop cross over 40 ms, the loop playing on over the first hits. The way up stays 5 ms.

**The loop is raw, and the top vanishes** (Brendan, 2026-11-05: "Shouldn't it be inaudible by the time it
gets to 22khz? It still sounds really buzzy."). The buzz is aliasing: at 22 kHz there are two samples a cycle,
and they drift through the recording. So: raw up to `R.RUSH_RAW`, 8 kHz, no fade, no anti-aliasing, fold-back
welcome; from there to `R.RUSH_PURE`, 16 kHz, an equal-power cross to a plain `osc~` at the same frequency; and
from there the sine alone, fading evenly up the turn to nothing at `R.RUSH_HZ`, 22 kHz. The three are named in
`c_steps.lua`, to move by ear. The sine is as loud as the loop was, by an `env~` on the player, so a silent loop
stays silent. Its canvas runs only while its gain is above 0, and the player's stops once it is fully crossed.
A wrap's jump below that is part of the waveform, as a retrigger's is: one read head and no seam. `e_rush` takes
the kit's whole output, dry and wet, in an `e_rec`, the recorder `e_tape` uses, its line 3.2 s. It reads the
frozen line as `e_tape` does (*A held repeat's tails*), but asks for 64 samples more than the 192 the recorder
ran on: a `delread4~` with no signal in sorts before its `delwrite~` and reads a block nearer than asked, which
`e_tape`'s long loops don't feel, and a block of a 15 ms loop would be in the recorder's fade. The rate moves
over 20 ms, so the knob's places do not zipper.

**What it costs**, on the Mac, least of five runs of `c_kit` alone under `-batch`, as above: 0.113% of real
time before it, 0.129% at rest, 0.174% looping and 0.184% on the sine alone, the player off. Scaled as the
kit's 1.7% on the device, about 0.2%, 0.8% and 1% of the Organelle's core, with the ticks' Lua saved while
looping. Estimates until measured on the Organelle.

### The saved tempo

Brendan's (2026-11-05): a way back to the BPM a section was saved with after knob 1 has wandered.
`u_song` keeps to knowing nothing of what a part means: `recall <key>` hands back the saved copy of the
section playing's part as a section starting would, `restore <key> <atoms...>`, and `u_tempo`, as a
contributor, takes it as it takes any restore, holding knob 1 and putting it straight back. So what comes
back is in the draft as any change of the tempo is, and the save lamp reads whatever that leaves. A
restore of the tempo already in force is dropped, as ever, which leaves a knob live at that tempo as it
was.

### A track's random pitch

Brendan's (2026-11-05): "the randomizer for the selected sample should also apply to its pitch as
well". A rule in `chance`, on the hit the coin plays and no other, so the toggle changes nothing about
which hits play or how loud. The pitch is kept with the step's decision, so a repeat replays it, and told
to `c_kit` before the hit only when `c_kit` holds another, which `c_steps` tracks: a hit its randomness
didn't roll is told the set pitch again, and a track that rolls nothing sends no more than it did. It
makes `pitch <pad> <semitones>` a message of a playing pattern, so `c_voice` no longer scans its sample for
its peak on every one, which was harmless when a person dragged a pitch.

### Mute and solo stop the hits, not the sound

Brendan's (2026-11-05), to test the drum effects one track at a time: an M and an S under each
pad on the phone, saved per section, and **tails ring out**. So a mute is a rule in `c_steps.lua`,
in `R.tick`, not a gain in `c_kit`: the track's hits stop, and what its voice, its delay and the
reverb are already sounding goes on until it dies away, as when a delay's level goes down. The
gate is the last thing a step asks, after the track's randomness has rolled, so a muted track
plays neither what is written nor a coin its randomness adds nor a repeat's step, and its dice are
rolled all the same: muting one track changes none of the others' coins. Its loop and a held
repeat go on underneath, so unmuted it comes back in on its own beat.

**A press on a muted pad still plays it** (a judgment call, 2026-11-05): a Launchpad pad plays
its sample now, whatever the step rule says, so a muted track can be heard before it is brought
back in. The phone's tap on a pad selects without playing, as it always did.

**Solo wins.** With any track soloed only the soloed play, and the mutes are kept, unheard, until
the last solo goes: the usual mixing-desk rule, so a solo is a look at a few tracks that leaves the
mutes as they were. The page is told which pads won't play, `quiet`, only when that changes, so a
mute under a solo and a restore that changes nothing send it nothing.

**The line grows only when they are used**, as it did for the effects: 581 numbers with neither,
711 with an effect moved, 743 once a track is muted or soloed, 759 once a track's distortion is not
soft, 760 once the reverb is not the plate and 776 once a track's random pitch is on, so an old section
loads and is put back as it was, with nothing muted.

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
- ⬜ **The effects have not played on the rig**: how the distortion, the delays and the reverb
  sound on Brendan's samples, their levels against the dry drums, and the instrument's CPU with
  them on, beside the second Pd's numbers above. See `cut-it/drum-timing`.
- ⬜ **The distortion's four characters have not played on the rig** (`cut-it/drum-timing`): how
  soft, hard, fold and crush sound on Brendan's samples, drive's level against the dry, and their
  CPU on the Organelle beside the Mac's estimates above. The sequencer checklist's steps 40 to 43
  judge the sound.
- ⬜ **The reverb's three types have not played on the rig** (`cut-it/drum-timing`), nor been
  measured on the device: how each sounds on Brendan's drums and whether their levels hold there
  (the sequencer checklist's steps 44 to 46), what each costs beside the estimates above, and
  whether `[else/giga.rev~]` loads silently from `/sdcard/PdExtraLibs`
  (`device/pd-libs/loadcheck.sh`).
- ⬜ **Mute and solo have not been used on the rig** (`cut-it/drum-timing`): the phone's M and S,
  the Launchpad's dim pads, and the tails ringing out after a mute. The sequencer checklist's
  steps 36 to 39 judge them.
- ⬜ **A held repeat replaying its coins and its drunk lengths has not played on the rig**: the
  sequencer checklist's step 17 judges it. See `cut-it/drum-timing`.
- ⬜ **A held repeat's tails, the 500 BPM repeat, the saved tempo and the random pitch have not played on
  the rig** (`cut-it/drum-timing`), nor been measured there: the sequencer checklist's steps 47 to 54
  judge them, and `e_tape`'s cost above is the Mac's estimate.
- ⬜ **The Lua version has not played on the rig**: its CPU beside the Pd version's 11.2% with the
  drum machine playing (`~/Sites/!reference/pure-data.md`, *Newer versions on the Organelle*) is unmeasured. See `cut-it/logic-as-text`.
