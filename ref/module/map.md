<!-- schema: module -->
# The map

**Files:** `Cut It/u_map.pd`, `Cut It/u_map.lua`, `Cut It/u_map-lua.pd_lua`, `Cut It/c_mapped.pd`, `Cut It/cut-it-map.txt`, `Cut It/cut-it-arrangement-page.txt` · **Gate:** `test/gate/map-assert.sh`, `test/gate/recover-assert.sh` · **Checklist:** `test/checklists/midi.md`, `test/checklists/recover.md`

## What it is

**`u_map` is the only file in Cut It that says what a control MEANS.** Every device layer publishes
named controls onto `param` and stops there; everything above the map is driven by the buses this
file writes. Nothing in `e_` or `c_` may ever learn that a nanoKONTROL exists, and this is the layer
that keeps that true.

Since v0.3 the map is **table-driven and mode-dependent**. `Cut It/cut-it-map.txt` sits beside the
patch, one row per mapping, and a control means whatever the row for the *current* mode says it
means. Telling the instrument "in mode 2, this fader plays the Volca" is one row of a text file.

**Its lookup is Lua, and its destinations are Pd.** `u_map.lua` reads the table and holds the
lookup key's mode, the lookup, the divisor and parameter pickup, as plain Lua that runs on the Mac without Pd; `u_map.pd` keeps the eight mode keys, the
destination route and every handler behind it, the boot timers and the files pickup reads, and asks
the Lua through one pdlua object, `[u_map-lua]` (`cut-it/logic-as-text`).

⛔ **The table never names a `[send]`.** It names a destination that must exist as a literal argument
on a `route` box inside `u_map`, feeding a handler you can see on the canvas — the **allowlist
guard**, and the whole of what makes a table acceptable here. See *Design*.

`u_map` has **one inlet**, the BPM a tap or the phone set, from `u_tempo`, at which it holds knob 1
([tempo.md](tempo.md)). It has **one outlet per output device**, wired in `u_root`, because no bus
carries a sounding note — the Volca's, the one since the SP-404 left the rig (Brendan, 2026-11-04) —
then one to `c_steps`, for what a press on page 2's drum page means ([sequencer.md](sequencer.md)),
one to `u_net`, which flips test mode, one to `c_synth`, for a press of page 3's synth pads
([synths.md](synths.md)), one to `u_tempo`, for a press of page 1's tap pad
([tempo.md](tempo.md)), one to `u_song`, for the top row, save and revert, the Organelle's
keys and go ([songs.md](songs.md)), and one to `c_melody`, for page 3's generator controls
([synths.md](synths.md)).

## Facts

### A row is four atoms, always

```
<mode> <control> <dest> <arg>

mode-1 og-knob-1 tempo    0
mode-3 slider-1  volca-cc 41
```

| Field | Is | Evidence | Item |
|-------|----|----------|------|
| `<mode>` | The `mode` bus message, one atom: the page, `mode-1` to `mode-8` | verified | — |
| `<control>` | A `param` name, physical and never functional — `og-knob-1`, `slider-1`, `pad-43` | verified | — |
| `<dest>` | One of the **twenty-three** below, and **only** those | verified | 229 |
| `<arg>` | A float the handler interprets. `0` where the handler has no use for one | verified | — |

**A row with any other width is a lint failure**, not a runtime one — `map-assert.py` reads the
file and rejects it before Pd ever does, and the Lua skips it.

### The destinations — the allowlist, in order

<!-- check: pd-route "Cut It/u_map.pd" tempo -->

| Destination | `<arg>` means | Value means | Evidence | Item |
|-------------|---------------|-------------|----------|------|
| `tempo` | unused | **40–250 BPM on a straight line**, rounded (Brendan, 2026-11-05: knob 4 has the flourishes): `c_mapped bpm 210 40` and `u_map.lua`'s `R.tempo_curve` and `R.tempo_position` | verified | — |
| `transport` | unused | Non-zero **toggles** start/stop. ⚠️ **No shipped row names it** — start and stop are separate buttons | verified | — |
| `start` | unused | Non-zero fires; a release does nothing | verified | — |
| `stop` | unused | Non-zero fires | verified | — |
| `panic` | unused | Non-zero fires | verified | — |
| `volca-note` | The note number | Velocity. Duration is a fixed **200 ms** | verified | — |
| `volca-cc` | The CC number | The CC value | verified | — |
| `volca-prog` | The program number | A **gate only** — it decides whether the press counts | verified | — |
| `volca-key` | The note number | **Velocity, and 0 is a real note-off.** No fixed duration — the release comes from the key. ⚠️ **No shipped row names it** since the Organelle's keys left the map (2026-11-04) | verified | 293 |
| `recover` | unused | **Two tiers on one control.** Non-zero raises `panic` at once; held for **2000 ms** it also raises `recover` | verified | 298 |
| `diag` | unused | Non-zero summons `g_oled`'s diagnostic layer. **`og-shift-60`, on every page** | verified | 301 |
| `drum-page` | The **grid index**, looked up in `cut-it-drum-page.txt` | `<role> <n> <velocity>` to `c_steps`, the pad's own velocity, and a release as velocity 0, which `c_steps` acts on only for a repeat pad, the 500 BPM repeat and the saved tempo's lamp; `pad-35` and `pad-38` are two of them (Brendan, 2026-11-05), and `pad-36` and `pad-37` between them no row at all; an index the layout lacks is `fail u_map layout-miss` | verified | — |
| `test-mode` | unused | Non-zero flips `u_net`'s test mode, which puts the phone's line check up ([phone.md](../device/phone.md)). **`og-shift-61` and `lp-setup`, the Launchpad's Setup, on every page**; `lp-setup` has no release, and needs none; out `u_map`'s third outlet, a cord to `u_net`. Choosing a mode turns test mode off, in `u_net` | unknown | — |
| `drums` | What the control is to `c_steps`: `last`, `track-last` or `swing` | The knob's 0–1, as it is, held or not: `<arg> <0-1>` to `c_steps` on the drum page's outlet, which scales it, latches it and draws its row. `last` is the global last step, **1 to the time signature's reach**, 32 at 4/4 ([sequencer.md](sequencer.md)), **`og-knob-2`**, and `swing` the sequencer's, 50% to 75%, which no shipped row names since knob 4 became `rush` (the phone's stays), both on every page; `track-last` the selected track's own, **`og-knob-3`**, on page 2 alone, where the track is selected (Brendan, 2026-11-04). A new drum control is a map row: `c_steps` refuses an arg it does not know as `bad-selector` (Brendan, 2026-11-04) | verified | — |
| `synth` | The **grid index**, looked up in `cut-it-synth-page.txt` | Non-zero sends `synth <choice>`, the cell's synth, to `c_synth` out `u_map`'s fourth outlet; a release does nothing, so with both pads held the first let go cannot undo the second. Eight rows, `pad-21` to `pad-28`, page 3 alone; an index the layout lacks is `fail u_map layout-miss`, as for `drum-page` (Brendan, 2026-11-04) | unknown | — |
| `arrangement` | The **grid index**, looked up in `cut-it-arrangement-page.txt` | Non-zero sends the cell's role to `u_tempo` out `u_map`'s fifth outlet — `tap`, the one there is — and a release nothing. One row, `mode-1 pad-21 arrangement 21`, page 1 alone; an index the layout lacks is `fail u_map layout-miss` (Brendan, 2026-11-04) | unknown | — |
| `section` | The top-row button, 1 and 2 the arrows, 3 to 8 the six section buttons | Non-zero sends `top <arg>` to `u_song` out `u_map`'s sixth outlet; a release nothing. `lp-cc-91` to `lp-cc-98`, buttons 1 to 8, on every page ([songs.md](songs.md)) | unknown | — |
| `save` | unused | Non-zero sends `save` to `u_song`, the sixth outlet. `lp-cc-108`, the upper bottom row's rightmost, on every page | unknown | — |
| `revert` | unused | Non-zero sends `revert` to `u_song`, the sixth outlet. `lp-cc-8`, the lowest row's rightmost, on every page | unknown | — |
| `song` | The Organelle's key, 1 the lowest | Non-zero sends `key <arg>` to `u_song`, the sixth outlet, which loads the setlist's song at that place; a release nothing. `og-key-60` to `og-key-84`, keys 1 to 25, on every page (Brendan, 2026-11-05; [songs.md](songs.md)) | unknown | — |
| `go` | unused | Non-zero sends `go` to `u_song`, the sixth outlet: a song waiting for go starts at the next bar. `lp-cc-89`, the right column's top, on every page (Brendan, 2026-11-05) | unknown | — |
| `rush` | unused | The knob's 0–1 and its live flag, held or not, `rush <0-1> <live>` to `u_tempo` out `u_map`'s fifth outlet, which draws its row: an absolute rate, 10 BPM at the bottom, the tempo up to 1000 and then a loop of what is being repeated, climbing and thinning to silence at 22 kHz ([sequencer.md](sequencer.md), *Rush*); `rush -1 1` says knob 1 has gone live, which ends it. **`og-knob-4`, on every page** (Brendan, 2026-11-05) | unknown | — |
| `melody` | What the control is to `c_melody`: `lock`, `fit`, `leap`, `notes`, `length`, `echo`, `loop`, `range`, `chord-lock`, `smooth`, `tension`, `home`, `span`, `chords`; or a pad's `roll-melody`, `roll-chords`, `roll-rhythm`, `on-h`, `on-m` | The control's 0–1, as it is, or the pad's velocity, `<arg> <value>` to `c_melody` out `u_map`'s seventh outlet, which scales a control, draws its row and puts it, and takes a pad's press and leaves its release. Page 3 alone: faders 2 to 8, knobs 1 to 6 and 9, `pad-81` to `pad-85` ([synths.md](synths.md), *The generator*) (Brendan, 2026-11-05) | unknown | — |

This table is checked against the literal `route` box, so a destination added to the patch and not
to this page fails the doc gate. `map-assert.py` checks the same box against the map's rows.

⛔ **`recover` is the one destination that reads the RELEASE**, so it cannot use the uniform spigot
trigger test — that gate opens on non-zero and throws the release away. `volca-key` is the existing
precedent for a branch that lets a `0` through. The press raises `panic` and starts a `[del 2000]`;
the release sends it `stop`. **Only the timer's completion reaches `recover`.**

⚠️ **A hold raises `panic` twice** — once on the press here, once inside `u_init` before the reload —
and that is deliberate, so `recover` is self-contained whatever reaches it. Every effect is
idempotent, and the counts stay exactly assertable: **one on a tap, two on a hold.**

⛔ **No map row may name `panic`, and the tiers are why that still holds.** The table names `recover`;
raising `panic` is the *handler's* business. `map-assert.py` asserts the rule directly, because a
control anyone could reach for must not be able to silence the instrument mid-set.

### What the screen shows for each destination

**Every destination that carries a value draws its own row on `disp`, named for the destination
and scaled into its units, and nothing else names a control** (Brendan, 2026-11-04): an unmapped
control draws nothing. The row says what the control *means*, not which fader moved. Each is a
`c_mapped` instance inside `u_map` — `[c_mapped <name-format> <mul> <add>]` — and the scaling exists
there and nowhere else.

| Destination | Live row | Held row | Evidence | Item |
|-------------|----------|----------|----------|------|
| `tempo` | `bpm 75` | `bpm 60 (120)` | verified | 316 |
| `volca-cc` | `volca-cc41 64` | `volca-cc41 64 (114)` | verified | 316 |
| `volca-note` | `volca-note60 100` | same shape | verified | 316 |
| `volca-prog` | `volca-prog 20` — the **arg**, because the value is only a gate | none | verified | 316 |
| `drums` | `last-step 12`, `pad2-last 6`, `swing 62 %`: drawn by `c_steps`, which holds the latch | `last-step 16 (7)`, `swing 50 (62)` | verified | — |
| `rush` | `rush 420 bpm` below the handoff, `rush 4.2 Hz`, the loop's real frequency, above it, drawn by `u_tempo` and `c_steps` | `rush 120 (1817)`, `rush 120 (46k)`: the tempo in force with the knob's own rate in brackets | unknown | — |
| `volca-key` | **nothing** — 25 keys reporting both edges would evict the five-row screen twice per note | none | verified | 293 |
| `drum-page` | **nothing** — the grid is the feedback, and 62 pads in use would bury the screen | none | unknown | — |
| `synth` | **nothing** — the pads and the phone show the choice | none | unknown | — |
| `arrangement` | **nothing** — the pad flashes and the phone shows the tempo | none | unknown | — |
| `section` `save` `revert` `song` `go` | **nothing** — the top row's lamps, save and revert's and the go lamp say it, and the phone's songs page | none | unknown | — |
| the buttons — `start` `stop` `transport` `panic` `recover` `diag` | **nothing** — the aux LED, the grid and the diag layer already say what happened | none | verified | 316 |

⚠️ **The held row's second number rides in the UNIT field.** `g_oled` runs a row's value through
`makefilename %g`, which refuses a symbol, so `(120)` cannot be the value — it is a free symbol in
the third slot.

| | Evidence | Item |
|---|----------|------|
| **A control draws exactly one row, and it is `u_map`'s.** No `m_` file sends a control's row to `disp` — `m_nano` and `m_launchpad` publish on `param` alone, as `m_organelle` always has, and as `m_404` did until the SP-404 left the rig (2026-11-04). A fader mapped to `volca-cc 41` draws `volca-cc41 64` and nothing beside it; an unmapped control draws nothing (*Design*); a mapped button draws nothing | verified | 317 |
| `map-assert.py` reads every `m_` file's `[s disp]` count, exactly, and the set of `m_` files with it — `m_organelle`'s one carries aux's `modal shift`, never a control | verified | 317 |

### Values are normalized to 0–1, and the divisor is not uniform

⚠️ **`param` values are not one unit.** Every handler sees **0 to 1**, and everything is divided by
127 *except* five controls that already arrive that way.

| Source | Range on `param` | Divided by 127 | Evidence | Item |
|--------|------------------|----------------|----------|------|
| nano faders and knobs | 0–127 | yes | verified | — |
| nano buttons | 1 | yes | verified | — |
| Launchpad pads | 0 or 127 | yes | verified | — |
| **Organelle knobs 1–4** | **0–1** — mother's own scale | **no** | verified | — |
| **Organelle aux** | **0–1** | **no** | verified | — |

One destination fed from two surfaces would otherwise need two scalings. The four knobs are one
table in `u_map.lua`, `R.KNOBS`, which also names the controls pickup holds.

### The lookup

| Step | Detail | Evidence | Item |
|------|--------|----------|------|
| Key | The key's mode and the control's name: `mode-1` and `og-knob-1` | verified | — |
| Table | `u_map.lua`'s, by mode and then control, read from `cut-it-map.txt` when `[u_map-lua]` is made, before any `loadbang`. Relative to the folder of the patch that holds it, so the same on the Mac, on the device and inside the gate's scratch copy | verified | 234 |
| Hit | `<dest> <arg>`, which leaves for the destination route as `<dest> <arg> <value> <target> <live>` | verified | — |
| Miss | Nothing: no bus and no row (Brendan, 2026-11-04; *Design*) | verified | — |
| A duplicate row | The first for a mode and control wins; the rest are dead | verified | — |
| Empty table | `fail u_map map-empty` on `err` at load; a missing file is an error on the console too, which fails a deploy | verified | 234 |

**An unmapped control is the normal state of most controls and must stay silent.** Eight pages × 92
controls is 736 possible rows and the shipped file has **449** — knobs 1, 2 and 4 on all eight; the
tap pad on page 1; knob 3 and the drum page's 62 pads on page 2; slider 1 and the eight synth pads
on page 3; and CC 90, PLAY, STOP, the four shifted keys, Setup, the top row's eight, save and
revert, the Organelle's 25 keys and go on all eight. **The Organelle's own keys load songs**, key
N the Nth song of the setlist chosen, the lowest the opener, and play no note (Brendan,
2026-11-05). ⛔ **Those forty-seven rows are on every page**: the three knobs so the tempo, the
drums' last step and rush are at hand whichever page is up (Brendan, 2026-11-04 and 2026-11-05), the top
row, save and revert, the keys and go so the song is played, kept and changed from any page
(Brendan, 2026-11-02, 2026-11-04 and 2026-11-05), the rest so no page strands you without a stop
or a recover but the Launchpad's own. `map-assert.py` reads that off the file, that each top-row
button and each key names its own place, that go is CC 89 alone, and that knob 3, the selected
track's, is page 2's alone.

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The table, the key's mode and its guard, the lookup, the divisor and pickup's five states | `u_map.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Reading the table and asking whether a `knobs.txt` is there, turning messages into those calls and their answers into outlets | `u_map-lua.pd_lua`, the class `u_map-lua`: four inlets (every control the mode keys pass on; the `mode` bus; `u_map.pd`'s own `init`, `window-shut` and `live`; a BPM a tap or the phone set, from `u_tempo`), four outlets (the destination route, the mode to store, `err`, a bang on `init`) | verified |
| The eight mode keys and their release gates, the 500 ms seed, the destination route and its handlers, `c_mapped`, the 1000 ms boot window, the recover breadcrumb at 2000 ms, `put auto mode` and the restore | `u_map.pd` | verified |
| The Lua's answers | The Pd version's, exactly: 38 controls and modes through `u_map` printed the same 42 lines from the Pd version and the Lua, on the Mac and on the Organelle (2026-11-03) | verified |
| What it costs in memory | About 0.1 MB more peak resident in a test Pd loading `main.pd` on the Organelle (3.31–3.42 MB before, 3.44–3.48 after), since `c_steps` loads pdlua already | verified |
| What it costs per control | About twice the Pd version's on the Organelle, in a test Pd niced beside the live one: 9000 mixed controls in 2.9–3.4 s against 1.35 s, and 9000 unmapped pressure messages in 1.6–1.8 s against 0.7–0.9 s (2026-11-03) | verified |

### What happens at load

| ~Time | Event | Evidence | Item |
|-------|-------|----------|------|
| 0 ms, as the patch is made | `[u_map-lua]` reads the table and asks whether a `knobs.txt` is there, and its lookup key's mode is `mode-1` | verified | 234, 239 |
| 0 ms, `loadbang` | `init`: `map-empty` if the table holds nothing, then the bang that proves the Lua loaded | verified | — |
| before 500 ms | mother pushes `knobs.txt`, if a Save has ever happened | verified | 139, 200 |
| 500 ms | The `mode` seed fires — `mode-1` — behind a spigot any real mode has already closed | verified | — |
| 1000 ms | `window-shut`: from now on a knob's first value is a hand, not a restore | verified | 236 |
| 2000 ms | The recover breadcrumb, which may say `live` | verified | 299 |
| ~3500 ms | `u_state` restores, and a saved `mode` arrives as a real selection, its page alone | verified | — |

⛔ **Both the read and the key's mode have to be there before mother's push.** See *Traps*.

### Parameter pickup — a restored control is held until it crosses

**mother replays `knobs.txt` at boot, so the patch believes a knob sits where the knob physically
does not.** Nothing on the instrument can detect it: mother reports a *position*, not whether that
position is still true. Pickup holds a control until its value passes **through** the stored one,
then hands it authority.

| | | Evidence | Item |
|---|---|---|---|
| The jump it replaces | 443 BPM on knob 1, which is master tempo | verified | 236 |
| Applies to | `og-knob-1`…`og-knob-4` only | verified | 236 |
| Never applies to | any control that is not an Organelle knob — the keys and the shifted keys included | verified | 236 |
| Boot window | 1000 ms. A first value inside it is a restore and **arms**; after it, a hand, and goes straight to live | verified | 236 |
| Whether the push is a restore at all | `[u_map-lua]` **asks whether `knobs.txt` is there** as it is made, before mother's push, beside the table it reads | verified | 239 |
| With **no** `knobs.txt` | **Knob 1 is held at 120 BPM**, `u_tempo`'s own, until it is turned through 0.38, where its line puts 120 (Brendan, 2026-11-04): its first push draws `bpm 120 (60)` and moves nothing. Every other knob is live from its first value | verified | — |
| **After a `recover`** | the breadcrumb, read at 2000 ms, sends `live`, `knobs.txt` or not: every knob, knob 1 included, but one mapped to `rush` | verified | 299 |
| **A knob mapped to `rush`** | Held as knob 1 is, until turned to or through where the tempo in force stands on its curve. Armed at 120 at load, Saved or not, and its side not decided until the boot window shuts, since a value in it may be `knobs.txt`'s; and not freed by a `recover`. Held again at any tempo a tap, the phone, a section or a pad sets, and at knob 1's as knob 1 moves live, and a live move of it holds knob 1 in turn, so whichever moved last wins ([tempo.md](tempo.md), *Knob 4 races the tempo*) (Brendan, 2026-11-05) | unknown | — |
| **After a tap or the phone sets the tempo** | every knob the page maps to `tempo` is armed again at where the line puts that BPM (`R.hold_tempo`, `R.tempo_position`), so it is held until turned through it and draws `bpm <tempo> (<knob>)` meanwhile (Brendan, 2026-11-04; [tempo.md](tempo.md)). A tempo outside its 40 to 250, from rush, the phone, a tap or the 500 BPM repeat, holds it at the nearer end of its turn, a hair off the rail so a pot that stops short still gets there, released by reaching that end; its row still reads the tempo (Brendan, 2026-11-05) | unknown | — |
| The held row is drawn by the **destination**, for any knob mapped to one that carries a value | `c_mapped` gets the latched target and the live flag with every message and draws `name <latched> (<knob>)` in its own units | verified | 316 |
| **Reaching** the target releases, not only passing it | a target on a rail has no beyond: armed above a target of `0`, the flip test waits for `value < 0` | verified | 241 |
| An **unmapped** control draws nothing | The Lua's miss leaves by no outlet: silent on every bus and on the screen (Brendan, 2026-11-04) | verified | — |
| Pickup never stops the lookup | so a held control still reaches its destination, and draws that destination's held row | verified | 242 |
| State | Five, per knob, in the Lua's state table, with the knob's target | verified | 236 |
| mother pushes **once** at load and then says nothing: the saved position at ~100 ms with a `knobs.txt`, the live one at ~223 ms without | `~/Sites/!reference/critter-guitari-organelle-1.md`, *Panel messages* | verified | 237, 239 |

**The five states.** `virgin`, never seen a value · `armed`, side not yet known · `above`, armed
**above** (or on) the target, waiting for a fall · `below`, armed **below** it, waiting for a rise ·
`live`. The first value after arming is held and decides the side.

**Arming takes two answers, and the boot window is only the first.** A first value inside the window
is a restore rather than a hand, so it arms; a first value after it is a hand and goes straight to
live. ⛔ **But mother pushes a value either way** — the *saved* position when `knobs.txt` exists, the
*live physical* position when it does not, both inside the window — so the window alone armed knobs
that were already in sync. `[u_map-lua]` therefore **asks whether `knobs.txt` is there** when it is
made, and without one the push is no restore: knob 1 is held at 120 and the rest are live
(`u_map.lua`'s `R.UNSAVED`).

⚠️ **A restore passes the value through, which is the only reason a timer is tolerable here.** Item
234 was two boot races that shipped silently. A window too short costs the old jump; one too long
costs a knob that needs one sweep to free it. **Neither can produce silence.** Knob 1 held at 120
with nothing Saved is silent on `tempo` by design: `u_tempo`'s fallback 120 is the tempo then
([tempo.md](tempo.md)).

### The recover breadcrumb, and why `u_map` reads it

**`u_init` writes `<state-dir>/cut-it-recover.txt` immediately before it fires the reload**, and
`u_map` reads it at 2000 ms. Item 299.

| | | Evidence | Item |
|---|---|---|---|
| Armed contents | `recover <ms>` — the stamp is elapsed milliseconds since load, from `[realtime]` | verified | 299 |
| Cleared contents | `none`, written back over line 0 | verified | 299 |
| A missing file | `[text size]` answers **0** and nothing happens | verified | 299 |
| The arming override | Every knob straight to **live**, knob 1 held at 120 included | verified | 299 |
| The report | `warn u_map recovered`, deferred to **4500 ms** | verified | 299 |

⛔ **The override lands at 2000 ms and the report must not.** After an emergency the knobs you are
*holding* are the truth, so nothing may be held; the read waits for `[del 2000]` only because a
missing file prints three lines (C-9). The **report** goes the other way: a `warn`
raised during the boot stages is buried by `modal launchpad` at 3000 and the rest of the boot,
which ends at 3500, so it waits until 4500. One read, two deadlines.

⛔ **The file is cleared by OVERWRITING it, never by deleting it.** Vanilla Pd cannot delete a file;
`[shell]` forks, is a do-nothing stub on the Mac, and would let a gate reach only one branch — the
same argument that forbade it for `knobs.txt` (*Traps*). A one-line sentinel makes the read decide
on **content**, so nothing depends on how `[text]` writes an empty table, which has never been
measured here.

⚠️ **`[text set]` takes a LIST and has no outlet** — so the sentinel is `list none`, and the write
hangs off a trigger beside it rather than downstream of it. Both were found by loading the patch, not
by reading it.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### The map must be read at load, with no delay

⛔ A read behind `[del 2000]` — to keep a missing file's error clear of `tools/deploy.sh`'s 735 ms
output gate — lands after **mother pushes `knobs.txt` at boot**, so the restored tempo knob hits an
**empty table** and is silently dropped. The instrument boots at `u_tempo`'s fallback 120 instead of
the saved value, and nothing reports it (item 234).

**Fix:** `[u_map-lua]` reads the table when it is made, before any `loadbang`. A missing map
*should* fail a deploy, so its console error is welcome rather than something to hide from — and an
empty table is reported on `err` for the same reason.

### The lookup key gets its mode at load, not from the seed

⛔ The same symptom, a second cause. The `mode` bus is seeded at 500 ms and mother's push arrives
before that, so a key that waits for the seed has **no mode at all** and misses every row.

**Fix:** the key's mode is `mode-1` from the moment the Lua's state is made, so a lookup is never
waiting on a clock. Any real mode still overwrites it, from the seed or from a restore.

### A restored `mode` carrying no name empties the key again, and a reboot does not clear it

⛔ The same symptom, a **third** cause, and the only one that survives a power cycle. `u_state`
replays the saved `mode` at ~3500 ms; a stored value of `compose` with **no mode name** gives the
key no mode, and every control falls to the unmapped branch — no tempo from knob 1, and nothing
on the screen where a BPM belongs (item 294).

⛔ **Fed from its own `[r mode]`, the store repairs it in the wrong direction.** Whatever reaches the
bus goes straight back into the store, so the truncated value is re-saved; the auto flush is armed
**by the restore**, so the correct `mode-1` the seed stored at 500 ms is replaced before it ever
reaches the disk. Every boot reads the bad value, re-stores it and writes it back.

⚠️ **On screen it reads as every control falling silent** — nothing where `bpm 120` or
`volca-cc41 64` belongs — because a control's only row is its destination's and a dead lookup sends
every control down the unmapped branch, which draws nothing. Nothing else reports it.

**Fix:** **the Lua refuses a `mode` that is not one atom naming a page, and says `fail u_map
bad-mode`**, the way an unknown *destination* does — item 297. ⚠️ The name is checked as well as
the count: a lone `compose` is one atom too.

⛔ **And the store gets the mode from the Lua, only when the key took it**, never from its own
`[r mode]`, which is what stops a bad value surviving a power cycle. The store never sees it, keeps
the seed's `mode-1`, and **the auto flush repairs the file on its own** — measured on the device
while the bus still carried a class: a `cut-it-auto.txt` holding `mode compose` came back whole
after one boot, with the knobs mapping correctly throughout.

### A mode saved before 2026-11-04 carries a class

⛔ Until then the bus carried `<class> <page>`, and `cut-it-auto.txt` keeps what was saved: `mode
compose mode-4`. A restore puts it on the bus as it stands, a selector no reader knows, so the grid
keeps its old lamp, the phone its old screen and the Lua says `bad-mode`.

**Fix:** `[route compose perform]` between the restore and `[s mode]` drops the class, so a mode
saved either way comes back as its page alone, and the next flush writes it back that way.
`map-assert.sh` restores one.

### The `[list trim]` before the destination `route` is load-bearing

⛔ The Lua sends the looked-up row as a list, so its selector is `list`, and `route` matches a
**selector** (C-6; Pure Data, in Reference). Without the trim the route never matches, and every
mapped control takes the reject as `unknown-dest`.

**Fix:** `[list trim]` between them.

### A duplicate `<mode> <control>` pair silently loses

⚠️ The Lua keeps the **first** row for a mode and control, as `[text search]` did before it, so a
second row for the same pair is dead and nothing says so.

**Fix:** none available in the patch — **the gate's static lint is what catches it**, because a
running instrument cannot.

### A row naming an unknown destination is a real error

⚠️ It goes to `err` as `fail u_map unknown-dest` and emits nothing. **This is the one failure this
design can have that nothing else would catch.**

⛔ **Contrast the lookup's miss, which is normal and silent.** The two mean opposite things: an
unmapped *control* is expected, an unmapped *destination* is a bug.

### A knob's raw position is not a readable parameter row

A knob reported to `disp` as well as `param` puts `og-knob-1 0.245` on screen, beside or instead of
the BPM it is mapped to. A 0–1 number where a BPM belongs is not feedback; it is arithmetic
homework.

**Fix:** the knobs do not report to `disp`. `u_map` reports the **mapped** value instead, because it
is the only file that knows what a control means. ⚠️ **`og-aux` is not a control at all** — it is
the keyboard's modifier, so there is nothing for the map to bind and nothing to draw. See
[organelle.md](../device/organelle.md).

### While pickup holds, one row carries both numbers

`bpm 57 (120)` — the latched tempo still in force, and where the knob is currently pointing. The gap
between them tells you which way to turn.

⛔ **The value must be a float** — `g_oled` runs it through `makefilename %g`, which refuses a
symbol. So the second number rides in the **unit** field, which is a free symbol.

⛔ **The held row has to be built where the scaling is.** Built beside pickup it cannot know what
the knob maps to, so it is hardcoded to one destination's units and every armed knob
announces itself in them (item 240) — and the scaling then exists twice, once for the action and once
for the row.

**Fix:** the message that reaches the destination `route` carries the latched target and the live
flag, and each `c_mapped` draws its own held row from them. One scaling per destination, as that
instance's creation arguments.

### Pickup holds the action, never the message

A held knob that sent nothing would draw nothing either, so the gap between the latched value and
the knob could never be shown.

**Fix:** the message reaches the destination whole, with a live flag as its last atom, and
`c_mapped`'s spigot sits on the assembled `arg value` pair. A button destination's `unpack f f`
reads the first two atoms and drops the rest — measured in 0.49 — so a button is never held, which
is what the gate asserts of PLAY and STOP.

### Pickup holds the action, never the lookup

⛔ A held knob that skipped the lookup would know nothing of its destination, so it could draw no
held row and the gap between the latched value and the knob could not be shown.

**Fix:** the lookup always runs; only the destination's action is held (*Pickup holds the action,
never the message*, above).

### A target sitting on a rail can never be crossed

⛔ The release test is a **side flip** — a knob armed *above* the target, `target <= value`, waits
for that to go false, which is `value < target`. **With a target of `0` that is
unreachable however far the knob is turned down.** Save with knob 1 at the bottom and master tempo is
dead for the whole session, and nothing reports it (item 241).

**Fix:** release on the flip **or** on `value == target`. Equality can never fire spuriously — a knob
sitting exactly on its stored value *is* in sync, which is the entire definition of pickup.

### An armed knob that is mapped to nothing draws no held row

⛔ A held row built for every armed knob announces the knobs mapped to nothing in whatever units it
was hardcoded to — `bpm 10 (60)` from a knob that drives no tempo (item 240).

**Fix:** the held row is the destination's, so a knob that reaches no destination draws none. It is
still held, and draws nothing at all, as every unmapped control does.

### A boot push is not proof that anything was restored

⛔ mother pushes a knob value at load **whether or not `knobs.txt` exists** — the saved position when
it does, the knob's own live position when it does not. Arming on the push alone latched knobs that
already agreed with the hardware, and they then stayed dead until turned back past where they
started. Reachable on a fresh install and after any `tools/deploy.sh --clean` (item 239).

**Fix:** ask the direct question. `[u_map-lua]` opens `knobs.txt` beside the table as it is made,
before mother's push, and with none the push is where each knob physically sits: knob 1 is held at
120 and the rest are live.

⛔ **Do not answer it from the timing.** The push lands at 100 ms with the file and at ~223 ms
without, and that gap is an artifact of the error path taking longer, not a promised signal.
⛔ **Do not answer it with `[shell]` either.** It forks and replies hundreds of milliseconds later,
it is a do-nothing stub on the Mac, and a gate could then only ever reach one of the two branches. A
file read behaves identically on both machines, so the gate creates the file or does not and
exercises the real path either way.

⚠️ **Ask it in the Lua, not with `[text define]`.** A `[text]` read of a missing file prints three
lines, so it had to sit behind `[del 2000]` (C-9), long after mother's push: the push then set the
tempo from wherever knob 1 sat until the answer came. Lua's `io.open` fails in silence.

### A Lua that never loads leaves only the mode keys

⛔ Without pdlua on the path, or with an error in the Lua,
`[u_map-lua]` fails to create, and every control but the eight mode keys is dead: no tempo knob, no
PLAY or STOP, no keyboard.

**Fix:** `u_map.pd` sends `init` at load and says `fail u_map no-lua` on the screen when no bang
comes back; a throwing rule says `fail u_map lua-<rule>` — `lua-param`, `lua-mode` — and the object
carries on. The gates' side of it is the sequencer's trap, *A Lua that never loads is invisible to
the gate's Pd half* ([sequencer.md](sequencer.md)).

## Design

### The pages

**Eight pages, one per key down the Launchpad's left column, and what each is for** (Brendan,
2026-11-04). A page is a set of rows in the map and, on the grid, either the beat row or a page of
its own; there is no compose and perform split, and every page draws every warning
([error.md](error.md)).

| Page | Is | Rows today, beside the forty-seven every page has |
|------|----|------------|
| 1 | The arrangement | The tap pad, cell 21, for `u_tempo` ([tempo.md](tempo.md)). The boot page, `R.BOOT_MODE` |
| 2 | The drums | The drum page's 62 pads and knob 3, for `c_steps` |
| 3 | The synths | Fader 1, the Volca's CC 41, and the synth pads, cells 21 to 28, for `c_synth`; faders 2 to 8, knobs 1 to 6 and 9 and `pad-81` to `pad-85` for `c_melody` ([synths.md](synths.md)) |
| 4–6 | Nothing yet | None |
| 7 | The sections: making and arranging the current song's sections, on the phone (Brendan, 2026-11-05) | None: its grid is the beat row ([songs.md](songs.md)) |
| 8 | The songs: making, loading and arranging them into setlists, on the phone (Brendan, 2026-11-05) | None: its grid is the beat row ([songs.md](songs.md)) |

### Why a table at all

The old rule was one `route` branch per mapping, with a written condition to revisit past about ten
mappings. **42 controls × eight pages is far past it**, and the page dependency alone would have
multiplied the branch count by eight.

### The allowlist guard

⛔ **A data-driven `[send]` could write any global name with no evidence of it on the canvas**, which
defeats an allowlist that is audited by reading (C-2). So the table names a **destination**, which
must exist as a literal argument on `u_map`'s `route` box, feeding a handler you can see. **There is
no send with a variable name anywhere in this file.**

The set of things a control can reach is still the set of boxes you can read — the property the
one-branch-per-mapping rule existed to protect, kept while the mappings became data.

⚠️ **Skip the guard and it is gone silently**: nothing fails, and no test notices. That is why it is
checked from three sides — `map-assert.py` against the map's rows, `docs-check.py` against the
table on this page, and a runtime `unknown-dest` on `err`.

**The guard stayed a Pd `route` when the lookup moved to Lua.** The route is what cords each
destination to a handler you can see, so it is the allowlist and the dispatch at once; in Lua the
list of destinations and the handlers they reach would be two things to keep in step, and the lint
and the docs gate would have to read the Lua instead of the box.

### The eight mode keys stay hardcoded, and they come first

They **are** the mode selector, so a mode change can never itself be mode-dependent — and if the
table were empty or broken, or the Lua never loaded, you could still change mode on a device with no
console. Everything the mode `route` does not match falls out of its reject and goes to the Lua.

**They are the Launchpad's left column, `lp-cc-80` down to `lp-cc-10`**, page 1 at the top — eight
pages (Brendan, 2026-11-04), the eight buttons `g_grid` lights as the mode lamps, so the thing you
look at is the thing you press. `u_map.lua`'s `R.PAGES` takes the same eight, and `map-assert.py`
checks the two agree. The top row, CC 91–98, is the song's sections ([songs.md](songs.md)). See
[launchpad.md](../device/launchpad.md).

⛔ **Each of the eight branches carries a `[select 0]`, and that is not decoration.** A Launchpad CC
button sends **127 on the press and 0 on the release**, where a nanoKONTROL button sends only the
press. Ungated, every mode selection fires **twice** — idempotent, so nothing on screen looks wrong,
while every `mode` message, every state-store write and every `g_grid` repaint silently doubles.

⛔ **The gate cannot go above the route.** That reject is the whole table path, and `og-key-*`
releases are **real note-offs** `volca-key` must act on (item 293) — a value test up there would
swallow every one and hang notes on the Volca. `[select 0]`'s reject carries anything that is not a
release, which is the value the message box wanted anyway (C-8).

### Each scaling lives with its destination

The message that reaches the destination `route` is five atoms — `<dest> <arg> <value> <target>
<live>` — and a destination that carries a value is a `c_mapped` instance that reads all five. It
scales the value once, passes `arg scaled` to the handler beside it only while live, and draws its
own row, live or held, in its own units. The alternative — one scaling in the handler and another in
a shared readout — is the duplication item 240 was, and it grows with every destination.

**The row is named for the destination, and it is the only one.** A nanoKONTROL fader mapped to
`volca-cc 41` draws `volca-cc41 64` and never `slider-1 64` beside it: the `m_` layers publish on
`param` alone and leave the screen to this file, as `m_organelle` always did for the knobs. One row
per control, so two faders moving are two rows rather than four (item 317).

### The drum page is one destination and a layout table

Page 2's 62 drum-page pads are 62 rows, `mode-2 pad-81 drum-page 81`, and the arg is the grid
index because the handler never sees the control's name — the `volca-key` precedent. The handler
looks the index up in `cut-it-drum-page.txt`, the table `g_grid` paints the page from
([display.md](display.md)), so `c_steps` receives `step 1 100` and never a cell. **The map says
which pads are the drum page in which mode; the layout says what each one is.** A row the layout
lacks is a real error, `layout-miss`, as an unknown destination is.

### The synth pads are one destination and a layout table, as the drum page is

Page 3's eight synth pads are eight rows, `mode-3 pad-21 synth 21`, the arg the grid index, and the
handler looks it up in `cut-it-synth-page.txt`, the table `g_grid` paints them from, so `c_synth`
gets `synth fm` and never a cell. **The map says which pads choose on which page; the layout says
which synth each one is**, so the two halves of page 3's row cannot disagree, and `map-assert.py`
reads both: every `synth` row's index is a cell of the layout, every cell has its row on page 3, and
every cell names a synth `c_synth` takes.

### The tap pad is one destination and a layout table, as the synth pads are

Page 1's tap pad is a row, `mode-1 pad-21 arrangement 21`, the arg the grid index, and the handler
looks it up in `cut-it-arrangement-page.txt`, the table `g_grid` paints page 1's pads from, so
`u_tempo` gets `tap` and never a cell. The destination is named for the page, not the tap, so the
arrangement's next pad is a row of the layout and a role `u_tempo`'s `[route tap]` takes, or a
cord of its own for a role another file takes; `map-assert.py` reads the rows, the layout and that
route: every row's index is a cell of the layout, every cell has its row on page 1 and no other,
and every role is one `u_tempo` routes.

### Only a mapped control names itself

**An unmapped control draws nothing** (Brendan, 2026-11-04: "Mapped ones only"). The OLED is for
alerts and warnings, the output's levels and the name of a control as it moves, and a control the
current page does not bind means nothing there, so its name on the screen said only that it was
touched. A page's rows are now what its controls mean: `bpm 120`, `volca-cc41 64`,
`last-step 16 (7)`.

**What it costs is item 242's case**: a control that does nothing and says nothing cannot be told
from a broken one on the screen. That was the reason for the raw row, `<name> <raw>`, from
2026-10 until this decision, and it is now answered off the screen: which name each nanoKONTROL CC
and Organelle key decodes to is `nano-assert`'s and `organelle-assert`'s, the Launchpad's pads light
where they are pressed on the drum page, whether a device's events arrive at all is the debug
patch's `1-MIDI-IN` screen ([debug.md](debug.md)), and a mapped control on a page is the hands-on
proof that a surface reaches the map.

**The two exemptions went with it.** The raw row skipped the Organelle's keys, 25 controls reporting
both edges (item 293), and pressure, a stream per held pad (item 318), so neither could flood the
five-row screen. With no raw row there is nothing to skip: `R.quiet` and its prefix and suffix
tests are gone, and a key or a pressure name the page maps still draws its destination's row, or
nothing for `volca-key`.

### Arg then value, always — and `[unpack]` gives them in the right order for free

Every branch receives `<arg> <value>` as two floats, and `[unpack]` fires **right to left**: the
value lands in a cold inlet or sets a gate before the arg arrives to trigger. That is the same
guarantee `m_volca`'s `[t b f]` had to be built by hand to get.

### The spigot is one uniform trigger test

A nano button sends 1, a pad sends 127 and an Organelle aux sends 1 —
**all non-zero after normalizing, and a release is zero.** So the gate opens on non-zero and the arg
passes through it: one test, not a different threshold per surface.

`volca-prog` uses the value as a gate rather than as data, because a program number is the *arg* —
so a fader release cannot select a patch.

### A file, not a table in the code

The rows live in `cut-it-map.txt` so the map **diffs one row at a time** and can be edited without
opening Pd or the Lua. The read is relative — from the folder of the patch that holds
`[u_map-lua]`, no path, no creation argument, nothing absolute — so one file works on the Mac, on
the device and inside the gate's scratch copy (item 229).

### The Volca handlers build the message `m_volca` expects

`[list trim]` is what turns `list notes 48 100 200` into a message whose **selector** is `notes`.
Without it `m_volca`'s `route` would reject every one straight to `err` — loudly, at least, which is
why that reject exists. See [volca.md](../device/volca.md).

### `mode` is persisted; the table is not

`u_map` is the first contributor to the state store, and `mode` is an **auto** key: a running value
rather than a committed take, pushed whenever it changes and flushed on `u_state`'s own clock. A
restore arrives as `mode-1`, the page as its selector, which is exactly the shape `s mode` wants —
so no `[list trim]` on that side. One saved as `<class> <page>` loses its class first (*Traps*).

⚠️ **The table is code, not state.** Nothing rewrites it at runtime, so persisting it would store a
constant, and a restore could silently override the shipped file.

### The seed fills a silence, it does not set a default

Nothing else writes `mode` at load, so without the seed the grid boots with no mode to show. Any
incoming mode closes the spigot, so a real selection always wins — including the seed's own send,
harmlessly, because Pd is synchronous and the bang has already passed through.

### The lookup in Lua, the destinations in Pd

What moved is what was hardest to read as boxes: pickup's five states were two arrays and forty
boxes, and the divisor and the pickup slots were two routes that had to name the same four knobs.
In `u_map.lua` they are a few dozen lines, tested without Pd: `test/gate/lua/u_map_test.lua` drives the rules, and the
Pd face through a stand-in for pdlua, in the map gate before its Pd half. What stayed is I/O and
timing, and the two things that must not depend on the Lua: the mode keys, and the route that is
the allowlist (*The allowlist guard*, above).

**`u_map.lua` never calls Pd**, and every rule takes the state and returns what leaves, as
`c_steps.lua` does ([sequencer.md](sequencer.md), *The rules in Lua, the timing in Pd*). The face is
`u_map-lua.pd_lua`, never `u_map.pd_lua`, which would replace the abstraction
([conventions.md](../conventions.md), *File naming*).

**Every control passes through the Lua, so its cost is per message**, about twice the Pd version's
on the Organelle (*Where each part lives*). `u_map-lua` answers pdlua's `dispatch` itself, by inlet:
pdlua's own builds and tries two method names from each selector first, and skipping that took
between a fifth and two fifths off a control's time there.

### Editing the rules

1. Edit `Cut It/u_map.lua`; `lua test/gate/lua/u_map_test.lua` checks it in a second, without Pd.
2. In a running Pd, `; pdluax reload u_map-lua` re-reads the rules, as for `c_steps`
   ([sequencer.md](sequencer.md), *Editing the rules*). The table is read when the object is made,
   so a change to `cut-it-map.txt` needs the patch reopened.
3. `./test/run.sh`, then `./tools/deploy.sh`, which reloads the patch on the device.

## Open

- ⬜ **Live re-assignment — editing a mapping from the instrument rather than the file — is v0.4**,
  and it brings its own persistence with it. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **The page names are placeholders, and pages 4 to 6 have no role yet.** `mode-1`…`mode-8` say
  nothing about what each page is for, though five now have one (*The pages*, above),
  and the sound work is what will name them. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **A mode change does not re-arm pickup**, so a knob mapped to different destinations per mode
  would jump once per change. Not reachable today — knobs 1, 2 and 4 mean the same on every page,
  and knob 3 nothing off page 2. **It
  closes with live re-assignment above, or not at all**: see [plan-v04.md](../../plan-v04.md) §3.
  ⚠️ Doing it *cheaply* is worse than nothing — re-arming to the knob's last position puts the next
  move on the far side and suppresses until you turn back. Doing it right needs a per-`(mode, knob)`
  value memory: pickup's state in `u_map.lua` keyed by mode as well as knob.
- ⬜ **The Lua map has not been played on the rig.** The gates and a test Pd prove it answers as the
  Pd version did and loads in silence; what it costs under four fingers of pressure, at the live
  Pd's priority, is unmeasured. `cut-it/logic-as-text`.
