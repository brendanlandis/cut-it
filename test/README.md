# The tests

**Everything that decides whether Cut It works.** Two kinds, and the difference is the *oracle* —
who or what says pass:

| | Verdict from | Runs |
|---|---|---|
| `gate/` | **a program**, unattended | every commit, in about a minute, on the Mac |
| [`checklists/`](checklists/README.md) | **a person**, with the rig plugged in | when hardware behavior needs judging |

⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert. This
project has shipped a gate that passed a broken patch 15/15, and one that had run its own driver
generator exactly never. Both looked green. See the **`gate`** skill.

⚠️ **The Mac is not the device.** The Phase 6 gate passed 25/25 on the Mac twice and shipped three
bugs. These prove a change did not break what was working; hands on the hardware are still the last
word.

## One gate per module

Twenty-five gates, and each answers for exactly one page: under `ref/`, or for `u_inject` and the
phone's line check page, the checklists' guide. That is the whole organizing principle: **a page that names a gate should be able
to name one whose entire subject is that page**, or say `none` honestly. Five pages once named a single `phase6-assert.sh`, and two of those claims
were false.

| Gate | Checks | Answers for |
|---|---|---|
| `midi-emitters-assert.sh` | 7 | **no page** — see below |
| `init-assert.sh` | 17 | `module/boot` |
| `audio-assert.sh` | 17 | `module/audio` |
| `err-assert.sh` | 24 | `module/error` |
| `display-assert.sh` | 112: 66 in Lua, 46 in Pd | `module/display` — the grid, its drum page's painter, page 3's synth pads and page 1's tap pad included |
| `oled-assert.sh` | 69 | `module/display` — the OLED |
| `led-assert.sh` | 12 | `module/display` and `device/organelle` — the aux LED |
| `tempo-assert.sh` | 68: 33 in Lua, 35 in Pd | `module/tempo` — `u_tempo`, tap tempo and the phone's tempo |
| `clock-assert.sh` | 22 | `module/tempo` — `c_clock` |
| `map-assert.sh` | 191: 103 in Lua, 88 in Pd | `module/map` |
| `recover-assert.sh` | 30 | `module/map` and `module/boot` — panic's second tier |
| `state-assert.sh` | 15 | `module/state` |
| `song-assert.sh` | 284: 217 in Lua, 67 in Pd | `module/songs` — the songs, the setlists, the keys and go, the sections, the top row, save and revert, the files |
| `presence-assert.sh` | 49 | `module/presence` |
| `launchpad-assert.sh` | 19 | `device/launchpad` |
| `nano-assert.sh` | 64: 39 in Lua, 25 in Pd | `device/nanokontrol` |
| `organelle-assert.sh` | 56: 35 in Lua, 21 in Pd | `device/organelle` |
| `phone-assert.sh` | 140 | `device/phone` |
| `inject-assert.sh` | 9 | `test/checklists/README.md`, *Send lines* — `u_inject` |
| `touchosc-assert.sh` | 253: 42 read, 211 in Lua | `device/phone` — the phone's TouchOSC layout, the line check's page included |
| `volca-assert.sh` | 10 | `device/volca` |
| `debug-assert.sh` | 34 | `module/debug` — the SECOND deployable |
| `sequencer-assert.sh` | 362: 275 in Lua, 87 in Pd | `module/sequencer` |
| `kit-assert.sh` | 38 | `module/sequencer` — the kit and its effects, as a signal |
| `synths-assert.sh` | 97: 72 in Lua, 25 in Pd | `module/synths`, and `device/streichfett` and `device/nanokey`, its two layers |

**1999 checks.** ⚠️ **Twenty-four of the twenty-five gates print their own `N checks` line and one
does not** — `midi-emitters-assert.sh` prints an inventory instead, so its 7 is hand-maintained and
the total cannot be derived from a run by summing. Totaling the run gives **1992**; the difference is
that gate. `sequencer-assert.sh`, `map-assert.sh`, `nano-assert.sh`, `organelle-assert.sh`,
`synths-assert.sh`, `song-assert.sh`, `tempo-assert.sh` and `display-assert.sh` print two each, one per half: the Lua tests', then the
analyzer's; `touchosc-assert.sh` two as well, its scripts' Lua tally printed before the reading's.
Worth knowing before trusting an arithmetic check of this number against a log.

⚠️ **`presence-assert.sh`'s 49 come from TWO Pd runs and one tally**, which is the only entry here
that does. The first run is the schedule at the shipped tick; the second scales `u_present`'s settle
and tick by ten and leaves its **counts** exactly as shipped, so the eighth re-wire and the give-up
actually happen — inside nine seconds rather than seventy-two. ⛔ **One analyzer reads both
captures**, because two would print two `N checks` lines and this number is what proves no assertion
went missing.

✅ **The checks that keep the SP-404 out were each made to fail** when it left the rig (Brendan,
2026-11-04), with `m_404` put back in the patch: `presence-assert`'s roster in both runs, and, with
the roster let be five, the Roland reply's taker; `oled-assert`'s roster and its pitch, which had
filtered the drawn rows to the known sources and passed a fifth line until they read every row shaped
like one; `map-assert`'s `m_` file set; and `nano-assert`'s channel 33. `kit-assert`'s *to nothing
else* failed on a second cord out of `c_steps`' pad outlet, and `presence-assert`'s first-reply check,
with three others, on `c_presence` publishing `seen` on a poll. `debug-assert` failed five against the
old debug patch, and its probe count with the velocity gate broken. The tempo, phone and layout
checks are under their own gates below.

✅ **The synths' checks were each made to fail** when the Streichfett, the nanoKEY and `c_synth`
came in (2026-11-04). `presence-assert`: `m_streich` matching Korg's byte (8 failed), its inquiry on
port 2 (1), and `m_nano` matching Waldorf's (3). `display-assert`: the synth not chosen lit (4),
the pads painted on page 4 (7), the choice read backwards (4). `map-assert`'s lint: a row the
layout lacks (2), a cell naming a synth `c_synth` lacks (1), a row off page 3 (1). `oled-assert`:
the Streichfett registering under another name (4). The phone, the layout and the synths' own gate
are under their sections below.

✅ **The page checks were each made to fail** when the mode bus lost its class, the pages became
eight and the drum page moved to page 2 (Brendan, 2026-11-04), each against the code before its
step: `u_map_test.lua`'s mode bus on the old two-atom rule (15) and on a rule that counted the atom
without naming a page (6); `err-assert` on the old `u_err` (3: no mode receive, the old `perform
mode-6`, the info witness); `map-assert` with the class-dropping route bypassed (the old save came
back as `compose mode-1`), `R.PAGES` one short, the six-key route (2), a page-8 row missing, and
the map before the drum page moved (the Organelle's key played a second note); `display-assert` on
the grid before the bus change (9), before eight lamps (9) and before the drum page moved (5, and
a traceback in `lib_grid`'s message for an RGB cell, fixed); `touchosc-assert` on the phone's old
handler (3) and old `MAIN` (4); `nano-assert`'s fader and `sequencer-assert` (34, its page 1
among them) on the map before the drum page moved.

✅ **The song store's checks were each made to fail** when sections came in (2026-11-05), each
against the code without the change, the file then restored. `u_song_test.lua`: a press while
playing starting its section at once (12), a section's length ignored (3), the draft never unsaved
(15), a Pd float kept as it came (1), the six buttons never scrolling (4), a file that can't be
written failing in silence (1), a copy named after the whole name, "verse 2 2" (5), deleting the
section playing without starting another (1), STOP leaving a section queued (2). `c_steps_test.lua`:
no `bar` (7), the bar counted on the time signature (4), a restore that leaves the loops where they
were (2), the swing and the last step left out of the line (26); `c_synth_test.lua`: no program
sent (4). `song-assert`'s Pd half: `g_grid` painting the section playing dim, save gray and a queued
section solid (12); `c_synth` deaf to `restore programs`, `c_steps` restarting no loop and deaf to
`section-1-drums`, together (16); the draft never flushed (Lua 3, Pd 4); a press while playing at
once (Lua 12, Pd 4); a length ignored (Lua 3, Pd 8). `init-assert`, `u_root`'s trigger reversed so
the song loads before `u_state` restores (1). `map-assert`, a section row naming the wrong button
and a page without save (2). `display-assert`, the playing lamp in a color no edge takes (9).
`phone-assert`, `sections` cut from `u_net`'s route and its state's inlet unwired (15), and `up`
dropped from its acknowledgments (8). `touchosc-assert`, a row that answers the state (2), a done
that sends a name unchanged or empty (2), and a command misspelt with its flash gone (3).
`sequencer-assert`, the pattern put as the old auto key and knob 4 unsaved (Lua 1, Pd 14);
`synths-assert`, `c_synth` putting as `auto` (7). `u_tempo`'s spigot open to a tempo already in
force held knob 1 at the load's restore: `map-assert` (2) and `recover-assert` (1).

✅ **A lit button's look was made to fail** (2026-11-05, Brendan: state buttons flickered on and off
when pressed): with the shared script no longer putting a finger's value back, `touchosc_test.lua`
failed on every one of the 53, pressed out and pressed lit (1).

✅ **The held put was made to fail, check by check** (2026-11-05, the crackle while dragging on the
phone), each against the code without the change, the file then restored. `c_steps_test.lua`: the
clock set again on every change (1), no hold (stopped the run), `sync` ignored (1);
`u_song_test.lua`: no `sync` before a press or a phone command (7), none before STOP (1), a Pd
fraction kept as it came (1). `sequencer-assert`'s Pd half: no hold, a drag put three times (1).

✅ **Several songs, the keys, go and the songs page were made to fail, check by check**
(2026-11-05), each against a mutation of the code, the file then restored. `u_song_test.lua`: a
song left losing its draft (6), a key while stopped waiting for its transition (9), silence
sending no STOP (3), go doing nothing (6), the bar ignoring a song queued (8), STOP ignoring one
(2), a key a place off (stopped the run), a rename reaching the draft alone (2), a song deleted
left in its setlists (5), song 1's files named for its id (stopped the run), the index without the
song loaded (5), the setlist's arrows skipping a long setlist's pages (1), no unsaved word (3), a
new song empty (4), and the face writing no draft but the loaded song's (3), keeping a deleted
song's files (1), sending no go lamp (4) and loading the first song over the one loaded last (2).
`song-assert`'s Pd half: the go lamp's two colors swapped (3), its painter's cord cut (3),
`u_song`'s cord to the stop bus cut (2), `u_map`'s song handler unwired (11), its go handler
unwired (2), and a song left losing its draft (Lua 6, Pd 3). `map-assert`'s lint: a key naming
another place (2), a page without go (1), go on CC 79 (2). `phone-assert`: `songs` cut from
`u_net`'s route (9, its branch becoming the reject), the songs state's route cut (1), `delete`
misspelt among the acknowledgments (1), and no heartbeat repeat of the songs state (3).
`touchosc-assert`: delete sending at its first tap (Lua 2), the starts switch answering the state
(Lua 1), the name tab naming a setlist as a song (read 2, Lua 1), load's acknowledgment lighting
nothing (read 1, Lua 1), add misspelt (read 1, Lua 1), the setlist's page left off its pager (Lua
1), and a lit row answering the state (Lua 2), but only with the root's check on the row gone too:
either alone holds, by design, so taking one away passes.

✅ **The OLED's revision was made to fail, check by check** (Brendan's split, 2026-11-04: alerts and
warnings, the output's levels and the name of a control as it moves), each against the code
before its step. The output meters: `audio-assert` on the old `u_root`, `c_kit` and `g_oled` (8
failed: `c_kit`'s own `throw~ outL`, the meters named and fed from the input, and `out-l` still
while a drum played and the input was silent), and with `out-l` renamed but left on the input (2:
its cords, and the drum it never saw); `kit-assert` on the old `c_kit` (6: no `outlet~` to record
or to cord into the sum); `oled-assert` on the old `g_oled` (3: the `L` and `R` readouts, the two
gate marks' `gBox`es). No tempo at rest: `oled-assert` on the `g_oled`, `u_tempo` and `u_init` with
the footer (3: a third line, `140-bpm`, at y=54, and the bars at the old 12 px), and `init-assert`
on the `u_init` and `u_tempo` with it (1: `status v0.3-ready` and the BPM on `disp`). Knobs 2 and
4 on every page: `map-assert` on the old map (Lua 1; Pd 2: the every-page rows, and knob 2 on page 4
drawing a raw row where `c_steps`' held one belongs), on the map with page 4's knob 2 and page 6's
knob 4 cut (Lua 1, Pd 2), and with knob 3 on page 5 too (Lua 1, Pd 1). Only a mapped control
names itself: against the `u_map.lua`, its face and `u_map.pd` with the raw row, `map-assert`
(Lua 14: the rows themselves, and the face's outlet numbers moving down one; Pd 4: `gk-cc`, `og-knob-3`,
`lp-cc-91` and `pad-36` drawn), `nano-assert` (2: `slider-3` and `lp-cc-19`) and `sequencer-assert` (2:
`pad-36` and `pad-81`). The roster's sixth row: `oled-assert` on the old `g_oled` and `m_nanokey`
(6: five rows, the strip at 48 and 56, the nanoKEY neither `never` nor `here`), on the old `g_oled`
with the new `m_nanokey` (6: the bound at five dropped `m_streich`), and on the new `g_oled` with the
old `m_nanokey` (5); `presence-assert` on the old `m_nanokey` (the roster of five in both runs),
and on an `m_nanokey` registered `active` through a `c_presence` (2 of the new, among 5). Knob 1
held at a tapped or phoned tempo: `tempo-assert` against `u_map`, its Lua and face, `u_tempo` and
`u_root` without the hold (3: 0.42 set 105 after the taps, its row read `bpm 105`, and 0.7 set 175
after the phone's 133), and with only `u_root`'s cord from `u_tempo` to `u_map` cut (the same 3);
`u_map_test.lua` against the old rules (no `R.tempo_position`: it stopped there) and with the hold
arming the knob at the wrong place (3). The log line a re-wire asked for writes, renamed `rewire-asked` from the
phone's button it no longer comes from: `presence-assert` on the old `u_present` (1).

✅ **The levels moved to mother's info bar and were made to fail** (Brendan, 2026-11-04: "the way
the organelle usually shows it by default, on a single line, and with levels at 0 when nothing is
playing"). `oled-assert` on the `g_oled` with Cut It's meters (12: the bar off in 300 frames, text
and a box drawn in rows 0-7, 442 `gFillArea`s, home's readouts and bars, and every layer's rows
eight higher), and with only the modal's word moved into row 4 (1: the rows-0-7 check alone);
`audio-assert` on the `u_root` and `u_level` that metered (1: eight `out-l` and `out-r` reports on
`disp`).

✅ **The phone's pages, the arrangement screen, tap tempo and the velocity switch were each made to
fail** (2026-11-04), against the code without the change or a mutation of it. `phone-assert`: the
old `u_net` (46 failed: the mirror's three addresses, the diagnostics reaching things, no tempo or
velocity), and the tempo's coalescer bypassed (5). `touchosc-assert`: the old layout (its hidden
screens, then a crash on what it lacks), and six rebuilt with a fault each — the tempo handed back
unrounded (Lua 2), the outer bar left showing (1), the switch answering its own value (3), the root
lighting by value alone (2), a re-wire button left (read 2), the switch misspelling `off` (read 1,
Lua 1), a blank page with a control (read 1, Lua 1), the switch in a hidden group (read 2), a ninth
page (read 1, Lua 1) and no acknowledgment for the switch (read 1, Lua 1). `tempo-assert`'s Lua on
four mutations (no window on the intervals 1, no gap 4, the knob's range 4, a zero interval
counted 1), and its Pd half with `u_root`'s cords from the tap pad and the phone cut (6).
`display-assert`: the tap pad's cord cut (1) and its region never painted (4). `map-assert`'s lint:
the role misspelt and a page-2 row (5), and `u_tempo`'s route renamed (1). `c_steps_test.lua`: no
swing in the phone's state and no re-arm (10), and the swing's re-arm alone (1).
`c_synth_test.lua`: the switch ignored (4). `synths-assert`: `c_synth` deaf to the switch's restore
(3) and `u_net` routing no `velocity` (6).

✅ **The kit's volume and pitch were made to fail** (2026-11-05): `kit-assert` on the old `c_kit`
and `c_voice` together (6 failed: the levels at -6 and +6 dB, the octave up and its length, the
octave down's level and length), on the old `c_kit` alone, which passes neither on (the same 6),
and on the old `c_voice` alone (7: the octave down's frequency too, once it was measured over
what both an unpitched and a pitched sample cover).

✅ **The drums' effects were made to fail, check by check** (2026-11-05, Brendan's Drums 3), each
against a mutation of the code, the file then restored from git. `c_steps_test.lua`: the phone's
effects never told to `c_kit` (7 failed), every effect told again at a restore (8), the line always
711 (30), a short line leaving the effects as they were (4), a dotted note at 5/4 (2), the phone's
state without the selected track's effects (9), and the load telling `c_kit` none (4).
`sequencer-assert`: a restore telling `c_kit` no effect (Lua 4, Pd 1: the seeded effects never
reach `t_kit`), and the line never holding them (Lua 4, Pd 8). `kit-assert`: the distortion adding
the driven sound without taking the dry (3), the delay without its block's 64 samples (1: the echo
64 samples late), deaf to the tempo bus (4), switched off at once at level 0 (1: the tail cut), the
reverb catching nothing (1), and `e_verb` without its `switch~` (1). `audio-assert`: a voice
throwing to a name nothing catches (1). `touchosc-assert`, each layout rebuilt with the fault: the
show radio horizontal (read 2, the contrast audit among them), the effect radio's delay and reverb
swapped (read 2, Lua 2), the mix knob sending `mix` (read 2, Lua 1), the root never hiding an
effect (Lua 1), every effect knob sending for track 1 (Lua 2), the pads' last step unclipped (Lua
1), and the contrast audit reading a vertical radio as one segment (read 1).

✅ **Mute and solo were made to fail, check by check** (2026-11-05, Brendan's mute and solo per
track), each against a mutation of the code, the file then restored from git. `c_steps_test.lua`:
a muted track still playing (6 failed), a solo heeding the mutes (1), a muted track rolling no dice
(1), the mutes and solos never saved (4), the restore never reading them (4), a short line keeping
them (2), the page told every time (8), the phone's state without them (10), a press on a muted pad
silent (1), `mute` taken as `solo` (10), the page told `mute` for `quiet` (8), a value kept as it
came (1), track 1 starting muted (66), the same value saved again (2), the mute inverted (31), and
the line's length a number short (1). `g_grid_test.lua`: the painter ignoring `quiet` (4), the two
dim colors swapped (5), the RGB table without them (5), the pink at a third (4), the array defined
too short (1), a short `quiet` clearing the rest (2), `quiet` a pad off (4), taking a symbol first
(1), and answering (2). `sequencer-assert`'s Pd half: a muted track still playing (2), a solo
heeding the mutes (2), the painter ignoring `quiet` (2, both frames), the mutes and solos never
saved (3: both puts and the draft), the RGB table without the two entries (5), and the drunkenness
never stopped (1: *STOP stops it again*, which reads the drag's window now that the mute and solo
windows come before the drunkenness, for the draft's 2 s). `touchosc-assert`, each layout rebuilt
with the fault: gaps of 15 (read 3: the 10-point step, the margin and the home bar), sync and snap
10 points low (read 1: the 20-point grid still holds every other control), the block 10 low (read
2), M teal and S red (read 1, Lua 1), every M and S for track 1 (read 1, Lua 3), a tap asking for
what it shows (Lua 3), the root never lighting them (Lua 7) or reading them a block off (Lua 7), a
98-number state putting them out (Lua 1), a pad's drag 25 points a step (read 1), M and S lit by
what they were told alone, deaf after a finger let go (Lua 1), no M or S at all (read 3, then the
Lua stopped), an M a step wide (read 1), the letters swapped (read 1), a lit letter left white (Lua
1), M and S sending as the state lights them (Lua 6), a pad selecting the next track (read 1, Lua
2), a pad's script on its old 100 steps (Lua 2), and an 88-number state drawing the effects (Lua 1).

 ⚠️ Three pages name more than one gate, and that is the rule working rather than
bending: `module/display` covers three surfaces with three different owners, `module/tempo` covers the
master reference and the clock cut from it, and `device/organelle` covers a front panel and an LED.
**A gate whose subject is two abstractions is what the split was for**; a page whose subject is two
surfaces gets two gates for the same reason.

**No page declares `Gate: none` any more.** `module/audio`, `device/nanokontrol` and
`device/organelle` were the last three, and each has its own gate now. ⛔ **`audio-assert.sh` and
`kit-assert.sh` are the two that read a SIGNAL back** — the first records `u_root`'s output to a
soundfile and asserts the passthrough is not silent, not swapped and not attenuated, that a drum
reaches the left alone, and that nothing reports a level, since the info bar is the meter; the second
records `c_kit`'s drums and asserts their levels, silences and retrigger, and a track's volume and
pitch, read back as a level, a frequency and a length. Every other gate here
asserts on messages, which is what made the audio path invisible for as long as it was.

**`midi-emitters-assert.sh` belongs to no device on purpose.** Its only claim is structural — *these
are all the MIDI objects in the patch* — and a new `[noteout]` in some future `e_` stage is not the
Volca's business, but very much the instrument's. It needs no Pd and takes ~200 ms.

### The shared machinery

| | |
|---|---|
| `lib_scratch.py` | imported by every gate that copies the patch. Holds the **one** `MIDI_EXPECT`, the stub rewrite, the private state directory and port, `u_net`'s sink, the generator status check and the watchdog. ⛔ It counts and rewrites boxes **by record**, through `lib_pd.py`, and forks nothing to do it |
| `scratch-gates.py` | one short recipe per scratch-copy gate: its required files, map rows, rewrites, driver and watchdog. Each `<gate>-assert.sh` is its header and one `exec` into it, so the path every page names still runs it |
| `lib_assert.py` | the check tally, the capture parser, and `require_capture` — a gate handed an empty capture must FAIL, not report nothing and exit 0 |
| `lib_drive.py` | window table → driver patch. Absolute delays off one `loadbang`, one delay per action, the `MARK` on the highest outlet; `extra` adds boxes a window reaches by name, as `synths-assert`'s socket into `u_net` |
| `lib_grid.py` | reassembles Launchpad SysEx. ⛔ Skips realtime bytes ≥ 248, which are legal *inside* a SysEx stream — `u_tempo` emits 96 a second |

⚠️ **The underscore in the four `lib_` files is not a slip.** A hyphen is not a legal Python
identifier, so a module that is *imported* cannot have one; a script that is only *run* can.

⚠️ **`u_net`'s sink is a socket in the gate's own process**, bound before Pd starts and held until
the gate exits, so its OSC lands somewhere known. Under Pd 0.49 a port with nothing bound answered
with ICMP and `u_net` raised `net-link-down` mid-run; 0.57 keeps the socket and that warning is gone
(2026-11-03). On macOS a second bind on a held port fails even with `SO_REUSEADDR`, so the bind is
checked.

⛔ **`MIDI_EXPECT` is an EXACT count per class, never "not zero".** A lower count means assertions
have gone vacuous; a higher one means an emitter no gate knows about. The gate it replaced checked
only for non-zero and its comment claimed five `[midiout]` where the patch has six — the count
drifted and nothing noticed.

## Running everything

```sh
./test/run.sh                every gate in one command, ~1 min, exit non-zero on any failure
```

**The gates run side by side**, all of them at once, each printed whole in table order, so the log
reads as a serial run's did. `CUTIT_JOBS=1 ./test/run.sh`
runs them one at a time. Each module gate's `main-dev.pd` copy gets its own inbound UDP port
(`CUTIT_INPORT`), and each gate's Pd runs with an empty `HOME` so it skips the Mac's Pd preferences —
see `test/runner/gates.py`.

Layout and graph structure, the documentation, all three entry points loading in silence, the MIDI
inventory, and one gate per module — the boot sequence, the audio path, the error bus, the display
arbiter, the OLED, the aux LED, the tempo reference, the clock, the map, panic's second tier, the
data store, the Launchpad, the nanoKONTROL, the Organelle's own panel, the phone and its layout, the
Volca and the debug patch. **Mac
only — it touches no device**, so it is safe to run at any time, including with the Organelle
switched off.

⚠️ **Run it before calling anything done.** Phase 8 edited `u_map`, `u_init` and `u_root` — files
Phases 5, 6 and 7 all rest on — and came within one step of shipping without re-running *their*
gates. The gates were all there, all passing, and all unused. **A gate you have to remember to run
is a gate that eventually does not run.**

⚠️ **`lp-monitor.pd` and `lp-step0.pd` are NOT here.** They were listed under
`test/` and they live in [tools/](../tools/README.md), where the directory-is-the-kind rule puts
them: they are probes a person runs, not tests with an oracle.

⛔ **`test/run.sh` runs nothing a person judges, and takes no options.** The hands-on half is
[checklists/](checklists/README.md), one Markdown file per area, read at the rig. It replaced the
bench runner on 2026-11-03: `--bench` and `--all`, the generated bench patches, `runner-assert.sh`
and the verdict file in `results/` all went, and every step's text is in the checklists.

## `display-assert.sh` and `launchpad-assert.sh` — no eyes and no hardware

```sh
./test/gate/display-assert.sh          66 + 46 checks, ~46 s — the drum page's painter in Lua, then the ARBITER
./test/gate/launchpad-assert.sh        19 checks, ~15 s — the DEVICE
```

Both take `--keep` to leave the byte capture behind to read. **They were one gate**, which is why
five pages once named it and two of those claims were false: it tested nothing about the
nanoKONTROL and nothing about the OLED.

**This is the part that asserts what the grid is actually showing.** The bench used to claim in its
own header that *"there is no way to read back what the LEDs are actually showing"* — too strong,
and it conflated three different things. Pd cannot ask the Launchpad what is lit, but **the bytes
the patch sends are completely knowable**, and that is the right level to test our own code at.

⚠️ **The split is not cosmetic — it is 46 seconds.** `display-assert` needs DSP, because the beat
row hangs off `threshold~`; the two SysEx checks about the *device* need no clock at all and were
paying that bill for no reason. `launchpad-assert` now runs in four seconds and gained three checks
it could not previously afford: the **order** of the mode switch against the first painted frame,
which neither message existing implies. LED writes sent in Live Mode do not appear, so a patch that
painted first and switched second would send both messages and still come up dark.

| Piece | |
|---|---|
| `test/stubs/t_midiout.pd` | a stand-in for `[midiout]` that prints every byte with its port, and sends it on `t-midiout` for a driver playing the device |
| the drivers | generated into the scratch directory on every run by `display-assert-drive-gen.py` and `launchpad-assert-drive-gen.py`. Not committed |
| `test/gate/lib_grid.py` | reassembles the SysEx frames — shared, because both gates read the same byte stream and want different frames out of it |
| `display-assert.py` | the arbiter: which layer owns the surface, and what happens when one gives it up |
| `launchpad-assert.py` | the device: what the hardware is told, and in what order |

⚠️ **The stand-in cannot be supplied by search path.** `mac-stubs/` works because `shell` is an
*external absent on the Mac*, so Pd falls through to an abstraction. `midiout` is a **built-in
class**, and Pd resolves the class table before it looks for a file — ✅ measured both ways, and a
`midiout.pd` on the path is simply ignored. So the object name has to change, which means
rewriting the box. **`Cut It/` is never touched**; the scratch copy is thrown away.

The script counts the boxes it rewrote and **refuses to run if it found none** — otherwise every
assertion would pass vacuously, which is worse than failing.

**46 checks**: frame shape and the 1–108 span, the mode lamp index, page 2's drum page with the
beat row giving way to it and page 1's beat row, page 1's tap pad dim beside it and full for a
moment at a tap, read with its layout file, page 3's synth pads above the beat row, the chosen
synth's bright and the other's dim, before and after STRINGS' pad, read with the layout file, the modal claiming all 108 specs, `fail` painting red and `warn` painting nothing, the alert expiring back to the modal
underneath, the beat row never leaving 11–18, the grid SURVIVING a panic, and
`m_launchpad`'s Programmer and Live SysEx.

**It runs the drum page's painter's Lua tests first** (2026-11-05): `test/gate/lua/g_grid_test.lua`,
with no Pd, drives `g_grid.lua` and its face through `lib_test`'s stand-in for pdlua, which carries
a `pd.Table` over arrays the test makes. **66 checks**: the colors read through `g_grid.pd`'s own
RGB table and held to the page's, the layout's 60 cells in its order, every cell at load, the rows
of steps at 4/4, 3/4, 9/8, 7/8, 5/4 and `bar 0`, the levels, a step past the last step dark, the
playhead, the buttons, the pads and the repeat pads, the pads whose tracks won't play, dim, what
changes nothing, `init`, and the face: the writes into the frame buffer and nowhere else, a buffer
made after it, `bad-selector`, `no-surface`, a missing layout, a throw, and `g_grid.pd` making it
and no longer reading the layout itself. What reaches the Launchpad is the Pd half's, and
`sequencer-assert`'s.

✅ **The drum page's painter was made to fail, check by check** (2026-11-05, when it moved from
`pd regions` to Lua), each against a mutation, the file then restored, until every one of the 62
had failed at least once. `g_grid_test.lua`: the blue step a step off (8 failed) or on the wrong
remainder (11), a step past the last step lit (8), the pads swapped (5), the rows ignored (5), the
velocity buttons' full and quarter swapped (4), a held repeat pad never shown (2), no playhead (3),
the playhead counted from 0 (12), a time signature that does not re-shape the rows (17), a level a
color off (7), a short `steps` clearing the rest (1), a row of another role painted (1), a symbol
taken as the playhead (1), the cells in reverse (2), no `layout-empty` (2) or always (2), an input
answering (2), a report not cut to 21 characters (1), the level, quarter and playhead entries a step
off (10, 5, 4), and from the face: its paint outside `pcall` (stopped the run), `no-surface` silent
(3), the layout read beside the class rather than the patch (3) or misspelt (6), the proof bang on
the wrong outlet (2), the writes an index off (3), the buffer never synced (stopped the run) or
synced only at creation (1), the class misnamed (1), three outlets (1), the page sent as internal
messages (4), `paint` not answered (7), an unknown selector ignored (4), the page taken on the
second inlet (1), the dispatch shortcut lost (1), the reports misnamed `lua-draw` (1) and `lua-page`
(1), and `lua-face.lua` stopping an object after its first error (1). From the patch and the layout:
`g_grid.pd` without `declare -lib pdlua` (1), reading the layout itself (1), its RGB table three
short (23) or its pink a step off (4), and the layout's fourth repeat pad made a pad (4). The Pd
halves, through the running instrument: the pads swapped (`display-assert` 1, `sequencer-assert`
16), the blue step a step off (`sequencer-assert` 14), the rows ignored (16), `pd regions`' cord to
the painter cut (`display-assert` 2, `sequencer-assert` 31), and the third inlet's cord to it cut
(`sequencer-assert` 30). ⚠️ **The proof bang's cord cut, so `fail g_grid no-lua` at every load,
passes every analyzer**, since the grid is not the patch's until after the alert's two seconds and
no driver is loaded yet; *both entry points load in silence* fails on it, `u_err` printing the
fail. With `g_grid-lua.pd_lua` gone the patch says `couldn't create` and `fail g_grid no-lua`. The
move itself was checked once, by a harness kept out of the suite: `g_grid` alone, the old and the
new, fed three seeded runs of everything it takes, 12,630 frames, byte-for-byte the same.

✅ **It has been proven to fail.** Reintroducing the one-based beat bug in a scratch copy — the
beat-row offset back to `+ 11` — makes it report `lit outside every region: [(19, 3)]` and exit 1.
⚠️ **The three `home-*` checks still passed under that mutation**, which is exactly why *seven
beats out of eight looked perfect*: only the six-second beat-row window catches it. A gate that
cannot fail is worth nothing, so re-run that mutation if you ever change the analyzer.

**`launchpad-assert` plays the device for the Setup tap** (2026-11-04). Its driver watches
`t-midiout` and answers every Programmer Mode entry 1 ms later with the announcement the Launchpad
makes, until a window mutes it; between, it sends the announcement unasked, and three frames that
are not it. ✅ **Red on each of eight mutations:** the heartbeat raising no expected echo (1
failed: the echoes published), the init raising none (3), the 250 ms forget cut (2), the match
waiting for another layout (4), a mismatch never clearing the match (2), mode 1's `lp-setup` row
gone from the map (2), `t_midiout` not sending on `t-midiout` (1: nothing was answered) and the
driver never muting (1: the forget's witness).

## `tempo-assert.sh` — two kinds of check, because neither is enough

```sh
./test/gate/tempo-assert.sh          33 + 35 checks, ~24 s — tap tempo's rules in Lua, then the clock, the taps and the phone's tempo
```

**It runs tap tempo's Lua tests first**: `test/gate/lua/u_tempo_test.lua`, with no Pd, drives
`Cut It/u_tempo.lua` (the first tap, the average of the last four intervals, the two-second gap,
two taps in one instant, the clamp, the phone's tempo and `bad-tempo`) and `u_tempo-lua.pd_lua`
through `lib_test.lua`'s stand-in for pdlua, and reads `[clip 5 600]` out of `u_tempo.pd` so the
Lua's range cannot drift from the patch's. The gate fails if either half does.

`u_tempo` is the instrument's interval timer: it publishes a beat on a bus that `g_grid`, every
`c_clock` and every future effect stage subscribe to, and writes MIDI clock to the wire at 24 pulses
per quarter note. **Nothing read those bytes back** until this existed.

| Half | Owns |
|---|---|
| a **static lint** — reads `[clip 5 600]` and `[* 24]` out of `u_tempo.pd`, ~1 ms, no Pd | the **bounds** |
| a **rate count** — System Real-Time bytes over a known window | whether the clamp is in the **signal path** |

⛔ **Neither can do the other's job, and that was found by trying to break it.** The pulse ceiling is
~344 Hz — `threshold~` decrements its dead time once per DSP block — so 600 BPM is 240 Hz and
**5000 BPM saturates at ~338 rather than reaching 2000**. A clamp widened to 5000 is caught easily; a
clamp widened to **650** reads 260 Hz, inside a 12 % band on 240, and is caught *only* by the lint.
Widening the tolerance would not have helped. The wire cannot resolve it.

⚠️ **It needs DSP**, like `display-assert`, because the pulse is a `[phasor~]` read by a
`[threshold~]`. With DSP off every count is zero, which reads exactly like a dead clock; `-noaudio`
does not turn it off (item 280).

**What it protects:** 24 PPQN at two tempos and the **ratio** between them (which cancels the
real-time scheduler entirely); ⛔ that the clock leaves on **port 1 alone**, and the transport's STOP
too, with panic's on 1 and 4 — exact sets, so nothing reaches port 3, the SP-404's until it left the
rig; the clamp warning at both ends and *not* warning in range; start 250, stop 252, panic 252, and
⛔ that **Continue (251) is never sent**; and ⛔ that **stop does not halt the clock** — the transport
pauses the subscribers, it does not clear the timer. Then **tap tempo through the running
instrument**: page 1's tap pad pressed as `param pad-21`, 400 ms apart, puts 150 on the tempo bus
from the second tap, and ⛔ **knob 1 held at it**: turned short of 150 it moves nothing and reads
`bpm 150 (105)`, turned through it it sets 170; 2.5 s later a tap sets nothing, and the next, 600 ms
on, 100; the same pad on page 2, a drum pad there, sets nothing; and **the phone's tempo** as a
datagram into `u_net`'s port, 133 to the bus, knob 1 held at it too, 900 clamped to 600, and a word
refused as `bad-tempo`.

## `map-assert.sh` and `volca-assert.sh` — the map and the output device

```sh
./test/gate/map-assert.sh            103 + 86 checks, ~19 s — u_map's rules in Lua, then the lookup and the static lint
./test/gate/volca-assert.sh          10 checks, ~5 s — four destinations, one channel
```

Each takes `-v` for the detail behind every check and `--keep` to leave the scratch directory and
capture behind. **They were one gate, and it claimed three pages at once** — the map's page, the
404's and the Volca's — which is exactly the false-coverage this refactor exists to remove. The
split reconciles upward: 28 checks became 34, because each gate could then say things the shared one
had no window for. The third, `sp404-assert`, went with the SP-404 when it left the rig
(Brendan, 2026-11-04), and so did `map-assert`'s `404-pad` row.

⚠️ **`map-assert` uses `volca-cc` and asserts nothing about the Volca.** A lookup has to land
somewhere; what the destination then does with the value is the device gate's business.

**`map-assert` runs the map's Lua tests first**: `test/gate/lua/u_map_test.lua`, with lua.org's Lua
5.4 and no Pd, drives the rules in `Cut It/u_map.lua` (the table, the lookup per mode, the divisor,
the mode guard, every pickup transition, an unmapped control leaving nothing) and `u_map-lua.pd_lua`
through `test/gate/lua/lib_test.lua`'s stand-in for pdlua (reading the table from its patch's
folder, `map-empty`, `bad-selector`, a throwing rule caught as `fail u_map lua-param`). The Pd half
below is unchanged since the lookup was Pd: **it is the proof the Lua port changed nothing.** The
gate fails if either half does.

**Half of the Pd half is a STATIC LINT.** It parses the literal `route` box out of `u_map.pd` and the rows
out of `cut-it-map.txt` and asserts that **every destination a row can name exists as an argument on
that route** — the allowlist guard, enforced by reading, exactly the way this project audits its
global sends. It also catches a **duplicate `(mode, control)` pair**, which the lookup resolves
to the *first* row only, so a repeat is dead and silent. And it reads every `m_` file's `[s disp]`
count, **exactly** — zero everywhere but `m_organelle`'s one, which carries aux's modal — because a
device layer posting a control's row beside `u_map`'s draws that control twice, or names an unmapped
one, which draws nothing since 2026-11-04 (item 317). That half runs without Pd at all.

The other half of each gate rewrites the MIDI object boxes in a scratch copy — **all seven classes, from the one
`MIDI_EXPECT` in `test/gate/lib_scratch.py`**, shared with every other gate that makes a copy. ⛔
**`[midiout]` alone was never enough**: `m_volca` emits through `noteout` / `ctlout` / `pgmout`, as
`m_404` did, so a rewrite of `midiout` only finds nothing in it and every assertion about it passes
**vacuously**. ⛔ **And the two input stubs are not optional**: every *output* path can be driven from
a bus, but the Launchpad's pads sit behind `[notein]` and `m_nano`'s *entire surface* sits behind
`[ctlin]`, and **no bus reaches a MIDI input**. ⛔ **`[polytouchin]` is the one class left with no
stub, and it was in NEITHER list until `scan_unknown` asked the question as a closed one** —
walking every MIDI class Pd has and checking it against the inventory, rather than checking the
inventory against itself. `[sysexin]` had no stub either until `t_sysexin` landed with the
hot-swap work, because a device-inquiry reply is the only evidence of presence there is and it
arrives on a MIDI input.

⚠️ **The count is EXACT per class, never "not zero".** A **lower** count means assertions have gone
vacuous; a **higher** one means an emitter no gate knows about. `test/gate/midi-emitters-assert.sh`
asserts the same inventory on its own, without Pd, so the claim has an owner that belongs to no
device.

⚠️ **Each owns its state directory**, and every gate that loads `main-dev.pd` now does. `main-dev.pd`
passes `/tmp`, shared by every run on the machine, and `u_init` restores saved state at ~3.5 s — so
one test that changes mode silently rewrites the starting conditions of every test after it. That
cost a wrong diagnosis once: item 232.

**Proven to fail** — the shared gate was, on a `47 + n` pad map (12 of 16 pads, both directions), a row naming a
non-existent destination, and a duplicate row. ⛔ **It PASSED a disarmed rate limiter on the first
try** — the SP-404's, whose burst window fired in one logical instant, and `[del 0]` still defers to
the next scheduler tick, so it proved *drops-rather-than-queues* and nothing about the interval. Any
rate limit tested again needs two events a real millisecond or two apart.

**One row per control** (item 317) was made to fail against the `m_nano`, `m_404` and `m_launchpad`
that still posted their own rows: four red in `nano-assert` — an unmapped slider drawn twice, a
mapped one drawn as `slider-1` beside `volca-cc41`, the 404's CTRL knob and a Launchpad ring button —
two in `sp404-assert`, and the static count; the file-set check went red on a stray `m_` file, and
again with `m_404.pd` put back after the SP-404 left the rig (2026-11-04).
**The pressure exemption** (item 318) went red against the `u_map` without it, with the key and
pressure tests swapped so the key test reopened the spigot, and — on the witness pad, then `pad-15` and now `pad-45` — with a
test wide enough to silence every raw row.

✅ **And again against the Lua**, both halves red on each of six mutations of `u_map.lua` (Lua
failures, then Pd): the lookup reading mode 1's rows in every mode (3, 3), pickup arming on the wrong
side (2, 2), the mode guard taking one atom (6, 5), pressure drawing a raw row (1, 1), no release on
reaching a rail target (1, 1) and the boot window never shutting (2, 1); a `live` that sets nothing
turned the Lua (3) and `recover-assert` (1) red. Knob 1 held at 120 with no `knobs.txt`
(2026-11-04): the face never asking for the file turned the Lua (1) and the Pd half's no-`knobs.txt`
run (5) red, and an empty `R.UNSAVED` the Lua (an error) and that run (2). The
allowlist stayed a Pd `route`, so its mutations are there: the reject cut from `unknown-dest` turned
the Pd half red (1), and a destination added to the route that nothing handles turned `docs-check`
red, as the guard's three sides intend.

⛔ **It also HUNG once instead of failing** — the driver generator errored, its exit status was
unchecked, Pd was handed a file that did not exist, and the `; pd quit` that lives *inside that file*
never fired. **A gate that hangs is worse than one that fails.** The generator's status and the
driver's existence are checked now, behind a 40 s watchdog.

Each driver is an OUTPUT, generated into the scratch directory on every run — edit `map-assert-drive-gen.py` or `volca-assert-drive-gen.py`. None is committed.

## `state-assert.sh` — the data store, and the cheapest oracle in the suite

```sh
./test/gate/state-assert.sh          15 checks, ~12 s, exit non-zero on any failure
./test/gate/state-assert.sh -v       and the detail behind every check
```

`u_state` writes a **file**, so this gate reads what landed on disk. No scratch copy (Phase 6
needed one, because `[midiout]` is a built-in class with no side channel), no socket (Phase 7's
trick), no hardware. It works entirely inside its own scratch directory and never touches
`Cut It/`, `/sdcard/cut-it-state` or the device.

**What it protects, stated as properties rather than proxies:** the two policies never leak into
each other; re-putting a key REPLACES its line; **a contributor answering behind a `[del]` is
absent from the file** — the synchronous contract itself; manual is replayed before auto so auto
wins a duplicate key; **a boot does not overwrite saved state before reading it**; and both entry
points load in **silence**, which is `tools/deploy.sh`'s own gate.

⚠️ **It passed the broken patch on its first can-it-fail run** — the driver banged the restore at
600 ms when the bug needs it after 3000 ms, and the final check asserted against a value nothing
drove. **The 3600 ms in the driver is load-bearing**; shortening it re-blinds the gate. Proven
both ways now: 15/15 clean, 2 failures with the bug reintroduced. The driver is an OUTPUT,
generated into the scratch directory on every run — edit `state-assert-drive-gen.py`. None is
committed.

## `phone-assert.sh` — the same idea, and much cheaper

```sh
./test/gate/phone-assert.sh            # ~65 s, exits non-zero on any failure
```

**Phase 7's gate needs no scratch copy and rewrites nothing.** `[midiout]` is a built-in class
with no side channel, which is the whole reason `display-assert.sh` has to swap it for a stand-in
in a throwaway copy of the patch. **`u_net` already emits to a socket** — so the gate binds
`127.0.0.1:9995`, instantiates `u_net 127.0.0.1 9995 9994` and reads the real datagrams, then sends
commands *into* 9994 to drive the inbound half. `Cut It/` is never touched.

**The other end of the inbound vocabulary, what the phone's buttons send, is `touchosc-assert`'s**
(below): the layout and `u_net` deploy by different routes, and their spellings must not drift.

| Piece | |
|---|---|
| `phone-assert-drive-gen.py` | generates the driver into the scratch directory on every run — it instantiates `u_net`, feeds its four inlets as `u_root`'s cords would, taps its three outlets, and puts the OLED's traffic on `disp` to prove `u_net` ignores it. **Edit this**; no driver is committed |
| `phone-assert.py` | binds the port, launches Pd, decodes OSC, does the reasoning |

⚠️ **The analyzer owns the lifecycle, and that is not tidiness.** It binds the socket *before*
Pd starts, because a UDP connect to a port with nothing listening survives exactly one datagram
(item 114). Start the driver by hand and you get one packet and then silence — which looks
exactly like a broken rate limiter.

**The window marks travel as datagrams**, to the same port, through the driver's own `netsend`.
A mark on stdout would have to be correlated with socket timestamps afterwards; a mark *in* the
stream arrives in true order with the data around it.

**140 checks**: the known addresses and nothing else; **no `[r disp]` in `u_net`, and no
`/cutit/param`, `/cutit/status` or `/cutit/alert` ever on the wire**, with a sweep, a status, an
alert, a meter and `diag` put on `disp` (Brendan, 2026-11-04: the phone stopped copying the OLED); a
monotonic heartbeat at 2 Hz; the tempo from `u_tempo`'s cord at once, on every heartbeat, coalesced
at 20 Hz with its trailing edge; `re-wire`, `clear-alert` and `test-note` reaching nothing, as six
malformed commands do; test mode, `result` and the gone `send`; every drum and arrangement command
out the first outlet as it came, acknowledged or not as the screens need; `synth` and `velocity`
out the second, `tempo` out the third, each passing on what it does not know for its owner to
refuse; `sections` out the fourth, each of the sections page's commands as it came, a name with a
space as one string, the buttons' five acknowledged and the rest not; `songs` out the same fourth,
`songs` kept in front, its sixteen commands in order, the buttons' ten acknowledged and the rest
not; and the mode, `c_steps`' numbers, the choice, the velocity switch, `u_song`'s 22 atoms and its
songs page's 47 at once and on every heartbeat, the two pages each on its own address. Its rate-limit history, below, is the old mirror's, whose coalescer the tempo now uses.

✅ **It was proven to fail before it was trusted, and for free.** `u_net` was built plumbing-first
with no coalescer, and that build failed exactly three checks — the three rate ceilings — at
401, 802 and 401 packets, while every shape check passed. Adding the store took those to 42, 84
and 42. No mutation had to be invented afterwards, which is the one weakness of Phase 6's
equivalent.
✅ **And for the drums lane** (2026-11-04): `u_net`'s cord from it to `c_steps` cut, 9 failed. In
`map-assert` a drums row naming `lastt` failed its lint, and `u_map` dropping the knob's value
(`list split 1`) failed `sequencer-assert`'s Pd half (14).
✅ **And for the SP-404 leaving** (2026-11-04): the old `u_net`, its `test-note m_404` branch back,
failed 10 — `cmd404`'s, which requires that command to reach nothing now, on an ack and a pad out
the outlet `c_steps` has taken over, and nine for the drum outlet moving back up one.
✅ **And for the synth choice** (2026-11-04): `synth` off the inbound route failed 7, since its
branch became the reject and bogus commands reached `c_synth`; no heartbeat repeat of the choice,
3; and the choice dropped on its way in, 1.
✅ **And for the drum screen's pads** (2026-11-05): `vol`, `pitch`, `set-track-last` and
`randomness` pass through `u_net` as every drum command does, by its design, so the old `u_net`
passes them; with its cord from `drums` to `c_steps` cut, all four failed with the rest (13).

## `touchosc-assert.sh` — the phone's layout, read and run

```sh
./test/gate/touchosc-assert.sh       42 + 209 checks, ~1 s — the layout read, then its scripts run
```

**Two halves, two tallies.** First, by reading `tools/touchosc/CutIt.tosc`: it is `build.py`'s
output; every control has a name of its own, since a script finds a control by name and TouchOSC
returns the first of two; **every screen is a page of a pager and nothing is hidden**, so the
editor, which runs no script, reaches each by its tab: the root holds one pager, its tab bar on in
the file, whose pages are the Launchpad's eight, as many as `u_map.lua`'s `R.PAGES`, then the
checklist page, each holding a pager of its own with one tab named for the page, but the sections
page's two and the songs page's three, and pages 4 to 6 blank (Brendan, 2026-11-04 and 2026-11-05);
no diagnostic command is left; and what its buttons send equals what `u_net` routes and `c_steps`
and `c_synth` take, **the inbound vocabulary read from both ends**: the velocity switch asks for
exactly the settings `u_net` acknowledges, and every synth button sends a synth `c_synth.lua`'s
`R.SYNTHS` names, `u_net` acknowledges exactly those, and there is one on the synths screen and one
on the checklist page for each. The drum screen's sixteen pads each drag their own track's volume,
pitch, last step and randomness, the four its radio chooses between; the radio is TouchOSC's own,
vertical, its first segment on top, a word over each, and sends nothing, and so is the effect radio
beside it, distortion, delay and reverb (Brendan, 2026-11-05), whose controls sit to its right and
send exactly the effect commands `c_steps` takes; under each pad its M and S, 30 by 20, M red and S
teal, each sending its own track's `mute` or `solo`; and a pad is a relative fader, about 20 points
of drag a step. **Every control sits on the editor's 20-point grid**, inside the margins, **but the
drum screen's pads and their M and S**, 112 controls named one by one, which step by 10 and start 10
points into the top margin, ending on the bottom one inside the page's 334-point frame (Brendan,
2026-11-05). The songs page sends
exactly the commands `u_song.lua`'s `R.songs_cmds` takes, its name tab both `name` and `set-name`,
and its starts switch is a radio asking for exactly `R.STARTS`. The phone is the only sender there
is, and the layout and `u_net` deploy by different routes, `push.sh` and `tools/deploy.sh`, so their
spellings could drift apart with nothing failing until somebody is at the rig. Every acknowledgment
`u_net` sends must light a button. **And every pairing meets WCAG AA contrast as TouchOSC draws
it**: each label against what lies under it, 4.5:1 or 3:1 for large text, each control's outline
against the page, 3:1, and each tab's text and states, from the resting fill TouchOSC draws at 26%
of a color (measured, TouchOSC's Reference page).

Then the layout's own scripts, unpacked into the scratch directory and run by
`test/gate/lua/touchosc_test.lua` under `test/gate/lua/lib_touchosc.lua`, a stand-in for TouchOSC as
`lib_test.lua` is for pdlua: the outer bar hidden by the root's script, the pages following the
mode and each tab's name, test mode turning to the checklist page and back, the arrangement
screen's tempo, time signature, last step, swing and drunkenness (a value from Cut It never sent
back, a tempo that is not whole never sent back rounded, the last step's box reaching exactly as
far as `c_steps.lua`'s `R.reach` lets the last step for every top number, 1 to 32), the drum screen's pads (the number its
radio chooses, a tap that selects, a drag that sends its track's value as it stands, and the state
never sent back, a last step dragged no further than `R.reach`), its M and S (lit by the state
and never sending it back, a tap asking for the other setting, a 98-number state leaving them as
they were), its effects (the chosen
effect's controls shown and the others hidden, each handed the selected track's value and sending
for that track, the reverb's size and damping for none) and buttons, the synths screen and the checklist page's FM and STRINGS, and the velocity switch, lit by
the state and never sending when lit, the songs page (its rows lit by the state and a lit one
sending nothing, load, new song, add to set, delete asking twice and lapsing after three seconds,
the setlists tab's rows, pager and starts switch, the state's starts never sent back, and its name
tab naming the song or the setlist by the tab it was opened from, the sections page's still
naming a section), the checklist page's Pass, Fail, Back and Next, nothing drawn
from a parameter, a status or an alert, and NO-LINK. The
page is driven on a development checklist with a step on two pages, built for the run, since every
line-check step may fit on one; the reading half holds the line check to having no Send line. **What it cannot judge is how TouchOSC draws**; the
phone checklist is the oracle for that.

✅ **Proven red** (2026-11-04): test mode never changing the tab (Lua 1 failed), a pad sending
`drums selec` (read 2, Lua 1), and the checklist page sending a Send line's numbers as text (Lua 1).
✅ **And again for the redesign**: grey text too dim for AA (read 1, Lua 1), a time signature box
sending one step for a drag across two (Lua 1), and answers lighting a button by its value rather
than its color, which sends its command again (Lua 9).
✅ **And for test 404 going with the SP-404** (2026-11-04): the old layout, the button still on it,
failed read 2 — the devices it names against `u_net`'s, and the acknowledgments it lights — and
Lua 1, the remote screen's three commands.
✅ **And for the line check** (2026-11-04): a Send line in it failed read 1, and the old `u_net`,
still taking `send`, failed `phone-assert` 12 (three for the command, nine for the drum outlet
moving down one). The phone's pads laid out with pad 1 top left, after the drum page put it
bottom left, failed read 1.
✅ **And for the pads** (2026-11-04): a pad sending when the state lights it, which bounced four
selections between Cut It and the phone, failed 2; the old `u_net`, with no heartbeat on a flip of
test mode, failed `phone-assert`'s two "at once" checks, 299 and 99 ms late; and with no cord
from a mode to the flip, a mode chosen in test mode left it on, failing 3.
✅ **And for the synths** (2026-11-04), each layout rebuilt with the fault: a synth button with no
`lit` guard (Lua 2), the root lighting one by its value (Lua 2), page 3 with no synths screen (Lua
1), a button for a synth `c_synth` lacks (read 2), the checklist page's buttons sending nothing
(read 1, Lua 6), and `u_net` acknowledging `fm` alone (read 1).
✅ **And for the drum screen's radio and its pads' drags** (2026-11-05): the new checks on the
layout before them (read 5, then Lua 2 and a stop at the radio it lacks), and eight layouts rebuilt
with a fault each: a drag that selects as well (Lua 10), the radio sending (read 2, Lua 3),
randomness in ones (Lua 3), a state handed back unguarded (Lua 1), the pads ignoring the radio
(Lua 8), every pad dragging track 1 (read 1, Lua 6), the radio standing up (read 2) and two steps a
pad's height (read 1). And the swing's range: the layout built at the old 25% (Lua 2).
✅ **And for the last step's reach** (2026-11-05), three layouts rebuilt with a fault each: the
old box of 1 to 32 (Lua 5), the root never telling the box the top number (Lua 5), and the box's
reach worked out wrong (Lua 9).

## `sequencer-assert.sh` — the drum machine, from the outside

```sh
./test/gate/sequencer-assert.sh      275 + 87 checks, ~40 s — c_steps' rules in Lua, then the drum page and the pattern in the song's draft
```

**Two halves, two tallies.** First `test/gate/lua/c_steps_test.lua`, with lua.org's Lua 5.4 and no
Pd: the rules in `Cut It/c_steps.lua` press by press (the levels, the step rule's three cases, the
selected track, which pads fire, swing, drunkenness's curve, randomness's coin with seeded dice, the
drum screen's pads, mute and solo (a muted track's hits, its coins and its repeats silent, its dice
still rolled, a solo winning over the mutes, the page told which pads won't play only when that
changes, and the lines saved before them loading unmuted), the repeat pads (a held repeat playing
exactly what was played, its coins and its drunk lengths, with no die rolled, mute and solo heard
live in it, a pattern edit and a section's restore under it unheard until it is let go, one pressed
short of its length since PLAY filled first, and let go, rolling again), the bar, the time signature's rows, a
press landing on the step its row and column mean, the reach that clips every last step, the bottom
number changing nothing but the save, a section's restore starting every loop again, the restore,
lines saved before the randomness and before sections included), and `c_steps-lua.pd_lua` through
`test/gate/lua/lib_test.lua`'s stand-in for pdlua (its inlets and outlets, `bad-selector`, a
throwing rule caught as `fail c_steps lua-fire`). Then the Pd half below, on a running copy of the
instrument, which is unchanged since the rules were Pd: **it is the proof the Lua port changed
nothing.** The gate fails if either half does.

It plays page 2's drum page on `param`, as `m_launchpad` publishes it, from a state directory
seeded with a song whose one section holds a pattern, and reads only what leaves the patch: the pads
for `c_kit`, the grid's frames, the state bus and the song's draft. First the time signature, over
OSC as the phone sends it: 9/8 and 3/4 set the page's rows and blue steps, at 3/4 the second
row's first cell is step 7 and the top row's seventh does nothing, and back to the seed's 7/8,
whose rows of seven every later frame is read in. **A note's step is the playhead of the frame painted after it** —
`c_steps` sends a step's notes and its playhead in one logical instant, and the frame clock paints
within 20 ms, six times inside a sixteenth at 120 BPM — so every step's exact notes are asserted
without a timestamp. The tempo is set by the driver, and PLAY to STOP is counted: 21 steps. Knob 2
is held at 16 and then sets the last step to 3 before PLAY again, which must walk 1 2 3 1 2. Then
knob 3 gives track 2 a last step of 6, and nine steps are checked against two loops, 3 and 6, note
by note. Then the drum screen's `snap` is sent as the phone sends it, OSC to `u_net`'s own port
(`CUTIT_INPORT`), so the cord from `u_net` to `c_steps` in `u_root` is under test too. Knob 4's swing
is held at 50% until turned all the way down, and at 75% puts step 2 three quarters through its pair;
the global last step and the swing are put as they change, a section's.
The drum screen's pads come over OSC too: a track's volume and pitch reach `c_kit`'s stand-in,
`test/stubs/t_kit.pd`, which prints them, as every track's do at the restore, and the seed's
effects, four tracks' and the reverb's size, reach it at the restore too, those alone, since
`c_kit` was told the rest at load, and come back whole in the song's draft; a track at full
randomness plays a coin on every step, at a level's velocity, while the rest play as written; with
four tracks at full randomness, repeat pad 2 held after step 3 replays steps 2, 3 and 2 with
exactly the hits and velocities their coins fell to, and let go, the loop of 3 goes on at 1; and
at full drunkenness at most 60 of 96 sixteenths hold exactly one step. Then track 1 is muted and
then soloed as well, over OSC: muted, it is silent while track 2 plays, soloed, it plays though
muted while track 2 is silent, each is put as a 743-number line, and the Launchpad shows the pads
that won't play dim, pink or the selected red at a quarter; the song's draft ends with both.

✅ **Proven red before it was trusted**: with `c_steps` absent (the known exit 2), against the patch
before the sequencer was wired (20 of 28), and on eight mutations — the step rule inverted, PLAY not
parking the counter, no put after a restore, panic ignored, eighths for sixteenths, `m_404`'s old
5 ms gap, the brightness ramp one hue off, and two velocity rows swapped in the layout table.
✅ **And again against the Lua**, both halves red on each of three mutations of `c_steps.lua`: the
step rule inverted (Lua 6 failed, Pd 12), the velocity levels off by one (5, 9), and a step reading
the next step's notes (5, 3). A rule that throws turns the Pd half red with `fail c_steps lua-fire`
on `err`, and a syntax error with silence (18 failed); the Lua half dies on both with a traceback.
✅ **And for the level `c_steps` sends** (2026-11-04): velocities sent to the page as they were
before (Lua 5 failed, Pd 12), and every level one too high (3, 12).
✅ **And for one velocity row** (2026-11-03), against the old step rule and the old color ramp
together: Lua 1 failed, Pd 12; with the old map, a press on the freed row was a `layout-miss`.
✅ **And for the last step**: PLAY parking the counter at 15, as it did, started PLAY again on step 2
with the last step at 3 (4 failed). 3, not 4, because a last step that divides 16 hides it. Without
`u_root`'s cord from `u_net` to `c_steps`, the snap never landed (3 failed).
✅ **And for swing, drunkenness, randomness, volume and pitch** (2026-11-05). `c_steps_test.lua`
on the old rules: the swing's 9 failed, and with the old curve given the new names, drunkenness's
11; then on eight mutations of the new rules: randomness ignored (6), a line of 563 read as the new
one (3), a restore telling `c_kit` nothing (3), a pad's sound kept from `c_kit` (5, then a stop), the
phone's state without the per-track numbers (8), a pad's last step leaving knob 3 live (2), a pad
setting the selected track's sound (8), and the coin playing the written velocity (3). The Pd half
on the old rules failed 20, among them the 579-atom put, `c_kit`'s volumes and pitches at the
restore and from the pads, the randomness and the swing, and then stopped on a line too short for
the new layout; on the old swing and drunk curve, 2; and with randomness ignored, 2.
✅ **And for the time signature's rows** (2026-11-05), each against the code without the change or
a mutation of it, the file then restored. The old `c_steps.lua` with the new `g_grid`: the Lua half
stopped at `R.row`, the Pd half failed 37. The old `g_grid` with the new rules: 17, among them each
row's eighth cell lit at 7/8, 9/8's blue step 10 missing and the playhead lost past the first row.
`c_steps_test.lua` on ten mutations: a cell pressed as its own step (3), rows of 8 whatever the top
number (17), a track's last step unclipped (1), the global one unclipped (2), the bottom number
setting the step clock's rate (1), a tick timed by it (1), no hold on knobs 2 and 3 when the reach
moves (1), knob 2's full turn left at 32 (3), the phone's `set-last` unclipped (2), and the old bar
of N × 16 / D (7). The Pd half with `g_grid` painting a cell as its own step (15), with a row's
cells past it not dark (16), and with `c_steps` taking a press as its cell's number (Lua 3, Pd 12).
✅ **And for a step on its boundary** (2026-11-05): with the phase shifted back a twelfth of a step
again, where it landed in `u_tempo`'s MIDI pulse, PLAY's step 1 came 10 ms late, past `RE-SOON` and
`SW-SOON`, and step 3 past `RE-STEP3` (3 failed). The windows bracket each against PLAY, which the
driver sends 20 ms after its mark: step 1 within 5 ms, once with `threshold~` armed at PLAY and once
still to re-arm, and step 3 between 246 and 256 ms. With no shift at all, the PLAYs landing early in
a step lost step 1 to the next step (4 failed, the swing's and the snap's walks among them) and the
armed one passed: the ten-thousandth is what re-arms it.
✅ **And for a repeat playing exactly what was played** (2026-11-05, Brendan: a held repeat rolled
randomness again on every step), each against a mutation of `c_steps.lua`, the file then restored.
`c_steps_test.lua`: a repeat rolling its coins and its drunk lengths again, the bug as reported (9
failed); its drunk lengths alone rolled again (2); mute and solo frozen into the step when it was
decided (3: a mute or a solo under the repeat unheard, and a muted track's coins lost to the
replay); let go, the window still playing (8); a window short of its length repeating at once (1);
the replay reading the pattern as it now stands (7); a restore letting go of the repeat (1); and,
for the dice the new checks set up, the coin inverted (11), a drunk step straying the other way
(8), and a press short of its length refused (2). The Pd half: the bug as reported (1: the four
random tracks' replay, the steps under it 2 3 2 and its hits re-rolled), and let go, the window
still playing (2: pad 1's and pad 2's walks after the release).

⚠️ **The layout table is read, not restated**, so a frame is decoded with the same table the patch
paints from. The analyzer's expectations are what keeps that honest: the driver presses `pad-26`
and expects level 2, so a table that moves the button is caught.

## `synths-assert.sh` — the nanoKEY and the two synths

```sh
./test/gate/synths-assert.sh         72 + 25 checks, ~11 s — c_synth's rules in Lua, then the nanoKEY through the instrument
```

**Two halves, two tallies.** First `test/gate/lua/c_synth_test.lua`, with lua.org's Lua 5.4 and no
Pd: the choice, where a key goes, a switch while keys are held, a key's numbers, the velocity
switch, the restores, and
`c_synth-lua.pd_lua` through `lib_test.lua`'s stand-in for pdlua (its outlets, `bad-synth`,
`bad-selector`, a throwing rule caught as `fail c_synth lua-list`). Then a running copy of the
instrument, booted on page 3 with a song whose one section holds `synth strings` and `velocity off`: the nanoKEY's keys go in through
`t-notein`, page 3's pads as `param pad-NN`, and the phone's `/cutit synth <choice>` as a datagram
into `u_net`'s own port, from a socket the driver builds with `lib_drive`'s `extra`.

**25 checks**: the saved choice and switch restored and put back, the first key on the
Streichfett's channel alone, at 127, the phone's `velocity on` and `off` put, FM's pad choosing once, any channel of the nanoKEY's port playing, a key held through the
phone's switch releasing on the Volca, only a press choosing (two pads held), notes on four other
ports playing nothing, the choice holding on page 1 where the pads mean nothing, `bad-synth` from
the phone, and `bad-velocity`, a soft key at 127 with the switch off and its release at 0, panic's
CC 123 on channel 33, nothing on another channel, nothing else on `err`, and `synth strings` and
`velocity off` in the song's draft at the end.

✅ **Proven red** (2026-11-04), each against the code without the change: `c_synth` releasing on
the synth chosen now (Lua 4, Pd 1); `m_nanokey`'s gate open above its port (1) and below it (1);
`u_net` routing no `synth` (4); `m_streich`'s panic channel on `ctlout`'s controller inlet (1);
`c_synth` deaf to its restore (4) and storing under another key (4); `u_map` choosing on a release
(1); the layout giving pad 22 to strings (6); a synth row on page 1 (3); `m_streich` given the
nano's channel (6); the layout missing pad 26 (5). The Lua half alone: no `bad-synth` (5), a release
that chooses (3), a restore that takes anything (2), `strings` at boot (15), no release before a
repeated press (1), a repeated choice said again (1).

## The device layers' Lua halves

```sh
./test/gate/nano-assert.sh           39 + 25 checks, ~17 s — the decode in Lua, then the channel gate
./test/gate/organelle-assert.sh      35 + 21 checks, ~20 s — the keyboard's names in Lua, then the panel
```

**A device layer whose decoding is Lua runs its Lua tests first**, as the map and the sequencer do,
with lua.org's Lua 5.4 and no Pd. `test/gate/lua/m_nano_test.lua` drives `Cut It/m_nano.lua`: all
fifty names by tens and units, a button's press as 1 and its release as nothing, the unmapped
warning, and that no name outlives its message. `test/gate/lua/m_organelle_test.lua` drives
`Cut It/m_organelle.lua`: each key's name, the layer `aux` held when it went down, a chord across a
change of modifier. The SP-404's layer had a third, until it left the rig (2026-11-04). Each also
drives its face through `lib_test.lua`'s stand-in for pdlua: its
inlets and outlets, `bad-selector`, and a throwing rule caught as `fail <layer> lua-<bus>`. Each Pd
half is unchanged since its layer was Pd: **it is the proof the port changed nothing.**

✅ **Both halves red on each of four mutations of `m_nano.lua`** (Lua failures, then Pd): a button's
release passed (4, 1), the units digit off by one (18, 14), the transport row continuous (2, 2) and
an unmapped CC silent (8, 1). **On each of three of `m_organelle.lua`**: no latch, the live
modifier naming every edge (3, 1); the latch rewritten on the release (3, 1); and the release dropped
(7, 3).

✅ **And `lua-face.lua`, which all the faces share** (2026-11-04): with no bang on `init`, each of
the five Lua tests there were then, the SP-404's among them, went red (1 to 3 failed); with a rule
run outside `pcall`, each died on its throwing rule.

## `song-assert.sh` — the song store, played from the Launchpad's edges

```sh
./test/gate/song-assert.sh           217 + 67 checks, ~50 s — u_song's rules in Lua, then four runs of the instrument
```

**Two halves, two tallies.** First `test/gate/lua/u_song_test.lua`, with lua.org's Lua 5.4 and no
Pd: a fresh load, the files' text both ways, a load from the draft, the saved song or both, the top
row stopped and playing, lengths and the last one with a length, the six buttons scrolling, the
sections page's commands, names, save and revert, the phone's state; several songs, the index both
ways, a load with and without one, the songs tab's and the setlists tab's commands, the keys stopped
and by each transition, go and its lamp, a song left keeping its draft, the songs page's state; and
`u_song-lua.pd_lua` through `lib_test.lua`'s stand-in for pdlua, reading and writing real files in a
folder of its own, across reloads, a song's own files made, flushed and deleted, a write that fails,
and a throwing rule. Then **four runs of a scratch copy of the instrument**, one analyzer reading
them all:

- **The song**, booted on page 2 with three sections saved, intro, verse of two loops and chorus,
  each with every part: the top row pressed as the Launchpad sends it, the transport on its buses, a
  change as a tempo on the bus. At load section 1 starts; stopped, a button starts its section at
  once, its programs out to both synths; a change lights save and revert, revert and save put them
  out; playing, verse hands over by itself on chorus's step 1, the drum page's playhead showing it;
  a section pressed blinks on the beat and starts when the pattern comes round; the arrows; a button
  with no section. Both files on disk after it.
- **A reload** of what the first left: the draft comes back, unsaved, and revert takes it to the
  save.
- **A first load from a state directory before sections**: the auto file's 579-number pattern, synth
  and switch become section 1's, and the auto file lets the old keys go. This run and the first
  start with no index, as a state directory from before several songs, and both end with one: song
  1, the opener of set 1.
- **Three songs**, booted on page 8 with a setlist, gig, saved: the Organelle's keys pressed as
  `m_organelle` publishes them, stopped, then playing by each entry's transition. Stopped, a key
  loads at once whatever its entry says; a song changed and left keeps its change as its draft,
  and comes back with it, unsaved; next bar waits while the go lamp blinks green and loads on the
  step 1; go waits through the pattern coming round while the lamp blinks amber, go turns it green,
  and the song loads at the next bar; silence puts STOP on the bus before the song loads; a key past
  the setlist's end does nothing. The index and the songs' own files on disk after it.

⚠️ **The driver turns DSP on**: the steps are cut from a `phasor~`, and the queued lamp blinks on
the beat row's clock, which is one too. Without it the transport plays nothing and no bar comes.

## `stubs/` — stand-ins the gates need

`t_midiout.pd` replaces `[midiout]` so a headless run can read back every byte the patch emits,
and sends each on `t-midiout`, so a driver can answer as a device would: `launchpad-assert`'s
answers every Programmer Mode entry with the announcement the Launchpad makes.
⚠️ **It cannot be supplied by search path**, which is why `display-assert.sh` rewrites boxes in a
scratch copy — see that gate below.

**Phase 9 added four more, because `[midiout]` is not the only way this patch emits MIDI:**

| | |
|---|---|
| `t_noteout.pd` | `[noteout]` — prints `pitch velocity channel` |
| `t_ctlout.pd` | `[ctlout]` — prints `value controller channel` |
| `t_pgmout.pd` | `[pgmout]` — prints `program channel`. ⚠️ **It cannot answer the 0-based/1-based question** (item 228): it prints what Pd was *given*, not the byte on the wire |
| `t_notein.pd` | ⛔ **a SOURCE, not a sink** — the only way to test a receive path. Drive it with `; t-notein <pitch> <velocity> <channel>` |

⛔ **`m_volca` emits through `noteout`/`ctlout`/`pgmout`, not `midiout`**, as `m_404` did, so
`display-assert.sh`'s rewrite finds nothing in it and every assertion about it would pass
**vacuously**. ⚠️ **And phase 6's regex is anchored so the class name must END the line** — it
silently skips any box carrying creation arguments, of which the patch has one: `m_volca`'s
`[ctlout 123]`. A phase 9 rewriter has to take a trailing argument list, and the stubs
therefore read creation args too.

⛔ **`t_notein` exists because the receive side is otherwise untestable.** Every *output* path can
be driven from a bus, but the Launchpad's pads sit behind `[notein]`, as `m_404`'s whole receive
side did, and **there is no bus behind a MIDI input** — a channel gate and the decode behind it
would go unexercised. Its outlet order reproduces the real object's
(channel, then velocity, then pitch) rather than approximating it; get that backwards and the
stub tests itself instead of the patch.

## The checklists

**[checklists/README.md](checklists/README.md)** has the list, how to read a step, how to put a
**Send** line on the buses from the Mac, and the rules for writing one. A step there is a promise
about something a person sees, hears or reads on the rig; whatever a program can check without eyes
belongs in a gate here instead.

## Reading a patch's box indices

### `--boxes` — ask, don't count

```sh
python3 test/gate/pd-layout-check.py --boxes "Cut It/u_state.pd"
```

Prints the index of every box exactly as `#X connect` counts them. **Use it before writing a
connect block by hand.** Pd numbers boxes by position in the FILE: comments count, `#X declare`
does not, a subpatch's contents do not but its closing `#X restore` does. Getting any of that
wrong shifts every later index and silently rewires the patch — which has bitten this project
five times, plus two near-misses while Phase 8 was written, both caught only by re-deriving the
indices by hand. That is what this flag is for.

The check itself now separates **PROBLEM** (structural — exits non-zero) from **note**
(cosmetic — does not). A crossed cord has never once meant the patch was wrong; a cord landing on
a comment always has.

### `pd-layout-check.py`

Not a patch — a static check on `.pd` files:

```sh
python3 test/gate/pd-layout-check.py "Cut It"/*.pd
```

Reports overlapping boxes, **connections drawn through unrelated boxes**, content that extends past
the saved canvas size, and ⛔ **connects that name a box defined LATER in the file**. Exits non-zero
on any of them.

⛔ **That last one is C-10's second half, and Pd is silent about it in every way that matters.** The
rule says append boxes at the end and move the connects with them — and it is easy to move the NEW
connects while an EDITED one still sits in the original block, hundreds of lines above the box it
now names. Pd replays a canvas top to bottom, finds no such object, drops the cord, and **loads
anyway**. The patch is simply not wired.

⚠️ **Pd does print `connect: no such object`, and that is not a defense.** A menu-launched patch
runs `-nogui` with stdout on tty1, `tools/deploy.sh` gates on output only before ~735 ms, and a gate
reading a capture is not looking for it. It caused two silent miswirings in one session — a presence
publish that never fired, and mode selection that stopped working outright — and both looked exactly
like a logic error in the new code. The check is exact rather than heuristic: it is what Pd itself
does.

Layout is the only structural documentation Pd has, and the failure it was written for is
specific: a comment placed between the logic and a message column gets cords drawn straight
through it, which is invisible until you open the patch. Box sizes are estimated from the text
rather than measured, so it is a smell detector, not a renderer.

The diagnostic patches above predate it and do not pass — they are working references, not
examples of layout.

### Re-running `m_nano`'s decode test without the hardware

`m_nano`'s decode was verified by swapping `[ctlin]` for a three-outlet stand-in driven by
`nano-ch`, `nano-cc`, `nano-val` **in that order** — which is `ctlin`'s measured firing order made
explicit. To repeat it: copy `Cut It/` aside, replace the `ctlin` line in `m_nano.pd` with a
stand-in abstraction of that shape, and drive it. All 21 cases and the bug it found are recorded in
item 31. The firing order itself is item 23 and needs the real
device.
