<!-- schema: module -->
# The map

**Files:** `Cut It/u_map.pd`, `Cut It/u_map.lua`, `Cut It/u_map-lua.pd_lua`, `Cut It/c_mapped.pd`, `Cut It/cut-it-map.txt`, `Cut It/cut-it-arrangement-page.txt` · **Gate:** `test/gate/map-assert.sh`, `test/gate/recover-assert.sh` · **Checklist:** `test/checklists/midi.md`, `test/checklists/recover.md`

## What it is

**`u_map` is the only file in Cut It that says what a control MEANS.** Every device layer publishes
named controls onto `param` and stops there; everything above the map is driven by the buses this
file writes. Nothing in `e_` or `c_` may ever learn that a nanoKONTROL exists, and this is the layer
that keeps that true.

The map is **table-driven, by page**. `Cut It/cut-it-map.txt` sits beside the patch, one row per
mapping, and a control means whatever the row for the page on show says it means, or an `all` row
says on every page. Telling the instrument "on the drum page, this fader plays the Volca" is one row
of a text file. `u_voices` chooses the page and writes it on the `mode` bus ([voices.md](voices.md)).

**Its lookup is Lua, and its destinations are Pd.** `u_map.lua` reads the table and holds the
lookup key's page, the lookup, the divisor and parameter pickup, as plain Lua that runs on the Mac
without Pd; `u_map.pd` keeps the destination route and every handler behind it, the boot timers and
the files pickup reads, and asks the Lua through one pdlua object, `[u_map-lua]`
(`cut-it/logic-as-text`).

⛔ **The table never names a `[send]`.** It names a destination that must exist as a literal argument
on a `route` box inside `u_map`, feeding a handler you can see on the canvas — the **allowlist
guard**, and the whole of what makes a table acceptable here. See *Design*.

`u_map` has **one inlet**, the BPM a tap or the phone set, from `u_tempo`, at which it holds knob 1
([tempo.md](tempo.md)). It has **one outlet per output device**, wired in `u_root`, because no bus
carries a sounding note — the Volca's, the one since the SP-404 left the rig (Brendan, 2026-11-04) —
then one to `c_steps`, for what a press on the drum page means ([sequencer.md](sequencer.md)),
one to `u_net`, which flips test mode, one to `u_tempo`, for the tap button and knob 4
([tempo.md](tempo.md)), one to `u_song`, for the top row, save and revert, the Organelle's
keys ([songs.md](songs.md)), one to `c_melody`, for the generator's controls
([synths.md](synths.md)), and one each to `u_voices` and `u_perform` ([voices.md](voices.md)).

## Facts

### A row is four atoms, always

```
<page> <control> <dest> <arg>

all     og-knob-1 tempo    0
drums   pad-81    drum-page 81
harmony pad-*     melody   h
```

| Field | Is | Evidence | Item |
|-------|----|----------|------|
| `<page>` | One of `u_map.lua`'s `R.PAGES`, a name on the `mode` bus: `perform`, `drums`, `harmony`, `melody`, `keys`, `sound`, `songs`, `diag`. Or `all`, every page's. **A page's own row beats an `all` row** | unknown | — |
| `<control>` | A `param` name, physical and never functional — `og-knob-1`, `slider-1`, `pad-43`. Or `pad-*`: a page of pads as one row, each pad's number after the arg, so `harmony pad-* melody h` makes `pad-71` `melody h71` | unknown | — |
| `<dest>` | One of the **twenty-three** below, and **only** those | verified | 229 |
| `<arg>` | A float or a word the handler interprets. `0` where the handler has no use for one | verified | — |

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
| `diag` | unused | Non-zero summons `g_oled`'s diagnostic layer. **`pad-81` on the diagnostics page**, which Setup opens ([voices.md](voices.md)) | unknown | 301 |
| `drum-page` | The **grid index**, looked up in `cut-it-drum-page.txt` | `<role> <n> <velocity>` to `c_steps`, the pad's own velocity, and a release as velocity 0, which `c_steps` acts on only for a repeat pad, the 500 BPM repeat and the saved tempo's lamp; `pad-35` and `pad-38` are two of them (Brendan, 2026-11-05), and `pad-36` and `pad-37` between them no row at all; an index the layout lacks is `fail u_map layout-miss` | verified | — |
| `test-mode` | unused | Non-zero flips `u_net`'s test mode, which puts the phone's line check up ([phone.md](../device/phone.md)). **`pad-82` on the diagnostics page**; out `u_map`'s third outlet, a cord to `u_net`. Choosing a page turns test mode off, in `u_net` | unknown | — |
| `drums` | What the control is to `c_steps`: `last`, `track-last` or `swing` | The knob's 0–1, as it is, held or not: `<arg> <0-1>` to `c_steps` on the drum page's outlet, which scales it, latches it and draws its row. `last` is the global last step, **1 to the time signature's reach**, 32 at 4/4 ([sequencer.md](sequencer.md)), **`og-knob-2`**, and `swing` the sequencer's, 50% to 75%, which no shipped row names since knob 4 became `rush` (the phone's stays), and `track-last` the selected track's own, **`og-knob-3`**, all on every page (Brendan, 2026-11-06). A new drum control is a map row: `c_steps` refuses an arg it does not know as `bad-selector` (Brendan, 2026-11-04) | verified | — |
| `arrangement` | A cell, looked up in `cut-it-arrangement-page.txt` | Non-zero sends the cell's role to `u_tempo` out `u_map`'s fourth outlet — `tap`, the one there is — and a release nothing. One row, `all xport-4 arrangement 21`, the nanoKONTROL's LOOP; a cell the layout lacks is `fail u_map layout-miss` | unknown | — |
| `section` | The top-row button, 1 and 2 the arrows, 3 to 8 the six section buttons | Non-zero sends `top <arg>` to `u_song` out `u_map`'s fifth outlet; a release nothing. `lp-cc-91` to `lp-cc-98`, buttons 1 to 8, on every page ([songs.md](songs.md)) | unknown | — |
| `save` | unused | Non-zero sends `save` to `u_song`, the fifth outlet. `lp-cc-108`, the upper bottom row's rightmost, on every page but the performance page, where it's a button of its own | unknown | — |
| `revert` | unused | Non-zero sends `revert` to `u_song`, the fifth outlet. `lp-cc-8`, the lowest row's rightmost, on every page but the performance page | unknown | — |
| `song` | The Organelle's key, 1 the lowest | Non-zero sends `key <arg>` to `u_song`, the fifth outlet, which loads the setlist's song at that place; a release nothing. `og-key-60` to `og-key-84`, keys 1 to 25, on every page (Brendan, 2026-11-05; [songs.md](songs.md)) | unknown | — |
| `rush` | unused | The knob's 0–1 and its live flag, held or not, `rush <0-1> <live>` to `u_tempo` out `u_map`'s fourth outlet, which draws its row: an absolute rate, 10 BPM at the bottom, the tempo up to 1000 and then a loop of what is being repeated, climbing and thinning to silence at 22 kHz ([sequencer.md](sequencer.md), *Rush*); `rush -1 1` says knob 1 has gone live, which ends it. **`og-knob-4`, on every page** (Brendan, 2026-11-05) | unknown | — |
| `melody` | What the control is to `c_melody`, one of `c_melody.lua`'s `R.ORDER`, or a page's `h<NN>` and `m<NN>` pads, `roll-melody`, `roll-chords`, `roll-rhythm`, `on-h`, `on-m`, `bass`, `style` or `pins-clear`, or any of those as `e<n>-<name>` for engine n | The control's 0–1, as it is, or the pad's velocity, `<arg> <value>` to the `c_melody`s out `u_map`'s sixth outlet: the one whose voice is on show takes it, or the one its `e<n>` names. It scales a control, draws its row and puts it, and takes a pad's press and leaves its release. The harmony and melody pages' pads and upper bottom rows ([synths.md](synths.md), *The generator*) | unknown | — |
| `voices` | `left-<r>`, `right-<r>`, `aux` or `setup` | `<arg> <value>` to `u_voices` out `u_map`'s seventh outlet, which takes a press and leaves a release: the page ([voices.md](voices.md)). `lp-cc-80` to `lp-cc-10`, `lp-cc-89` to `lp-cc-19`, `og-aux` and `lp-setup`, on every page | unknown | — |
| `perform` | A physical control's own name, `slider-<n>`, `knob-<n>`, `btn-a-<n>`, `btn-b-<n>`; `arm`; or a pad, `pad-<NN>` | `<arg> <value>` to `u_perform` out `u_map`'s eighth outlet: whatever this section has that control move ([voices.md](voices.md)). The nanoKONTROL's eight groups and REC on every page, the grid and the bottom rows on the performance page | unknown | — |

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
| `arrangement` | **nothing** — the phone shows the tempo | none | unknown | — |
| `voices` | **nothing** — the columns' lamps say it | none | unknown | — |
| `perform` | **nothing of its own**: a control in play draws its destination's row ([voices.md](voices.md)) | as its destination | unknown | — |
| `section` `save` `revert` `song` | **nothing** — the top row's lamps and save and revert's say it, and the phone's songs page | none | unknown | — |
| the buttons — `start` `stop` `transport` `panic` `recover` `diag` | **nothing** — the aux LED, the grid and the diag layer already say what happened | none | verified | 316 |

⚠️ **The held row's second number rides in the UNIT field.** `g_oled` runs a row's value through
`makefilename %g`, which refuses a symbol, so `(120)` cannot be the value — it is a free symbol in
the third slot.

| | Evidence | Item |
|---|----------|------|
| **A control draws exactly one row, and it is `u_map`'s.** No `m_` file sends a control's row to `disp` — `m_nano` and `m_launchpad` publish on `param` alone, as `m_organelle` always has, and as `m_404` did until the SP-404 left the rig (2026-11-04). A fader mapped to `volca-cc 41` draws `volca-cc41 64` and nothing beside it; an unmapped control draws nothing (*Design*); a mapped button draws nothing | verified | 317 |
| `map-assert.py` reads every `m_` file's `[s disp]` count, exactly, and the set of `m_` files with it: none has one | verified | 317 |

### Values are normalized to 0–1, and the divisor is not uniform

⚠️ **`param` values are not one unit.** Every handler sees **0 to 1**, and everything is divided by
127 *except* four controls that already arrive that way.

| Source | Range on `param` | Divided by 127 | Evidence | Item |
|--------|------------------|----------------|----------|------|
| nano faders and knobs | 0–127 | yes | verified | — |
| nano buttons | 1 | yes | verified | — |
| Launchpad pads | 0 or 127 | yes | verified | — |
| **Organelle knobs 1–4** | **0–1** — mother's own scale | **no** | verified | — |
| Organelle aux | `og-aux 1`, a press | yes | unknown | — |

One destination fed from two surfaces would otherwise need two scalings. The four knobs are one
table in `u_map.lua`, `R.KNOBS`, which also names the controls pickup holds.

### The lookup

| Step | Detail | Evidence | Item |
|------|--------|----------|------|
| Key | The key's page and the control's name: `perform` and `og-knob-1` | verified | — |
| Table | `u_map.lua`'s, by page and then control, read from `cut-it-map.txt` when `[u_map-lua]` is made, before any `loadbang`. Relative to the folder of the patch that holds it, so the same on the Mac, on the device and inside the gate's scratch copy | verified | 234 |
| Hit | The page's own row, an `all` row, then the page's `pad-*` for a pad: `<dest> <arg>`, which leaves for the destination route as `<dest> <arg> <value> <target> <live>`. A live control that could be taken into play goes to `u_perform` too, on `perform-heard` ([voices.md](voices.md)) | unknown | — |
| Miss | Nothing: no bus and no row (Brendan, 2026-11-04; *Design*) | verified | — |
| A duplicate row | The first for a page and control wins; the rest are dead | verified | — |
| Empty table | `fail u_map map-empty` on `err` at load; a missing file is an error on the console too, which fails a deploy | verified | 234 |

**An unmapped control is the normal state of many controls and must stay silent.** The shipped file
has **185** rows. **94 are `all` rows, every page's**: the Organelle's four knobs, the same on every
page (Brendan, 2026-11-06), PLAY, STOP, LOOP and REC, CC 90, Setup and aux, the top row's eight, save
and revert, the Organelle's 25 keys, key N the Nth song of the setlist chosen, the lowest the opener,
and playing no note (Brendan, 2026-11-05), the columns' sixteen, and the nanoKONTROL's thirty-two. A
page's own rows are its grid: the drum page's 62 pads, the harmony page's `pad-*` and five commands,
the melody page's `pad-*` and three, the performance page's `pad-*` and sixteen buttons, and the
diagnostics page's two pads. ⛔ **`map-assert.py` holds that no page takes a shared control back** but
the performance page, save and revert's buttons (Brendan, 2026-11-06), so no page strands you without
a stop or a recover but the Launchpad's own.

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The table, the key's page and its guard, the lookup, the divisor and pickup's five states | `u_map.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Reading the table and asking whether a `knobs.txt` is there, turning messages into those calls and their answers into outlets | `u_map-lua.pd_lua`, the class `u_map-lua`: four inlets (every control; the `mode` bus; `u_map.pd`'s own `init`, `window-shut` and `live`; a BPM a tap or the phone set, from `u_tempo`), four outlets (the destination route, `err`, a bang on `init`, and `heard`, to `u_perform`) | unknown |
| The destination route and its handlers, `map-route`, what `u_perform`'s controls come in on, `c_mapped`, the 1000 ms boot window and the recover breadcrumb at 2000 ms | `u_map.pd` | unknown |
| The Lua's answers | The Pd version's, exactly: 38 controls and modes through `u_map` printed the same 42 lines from the Pd version and the Lua, on the Mac and on the Organelle (2026-11-03) | verified |
| What it costs in memory | About 0.1 MB more peak resident in a test Pd loading `main.pd` on the Organelle (3.31–3.42 MB before, 3.44–3.48 after), since `c_steps` loads pdlua already | verified |
| What it costs per control | About twice the Pd version's on the Organelle, in a test Pd niced beside the live one: 9000 mixed controls in 2.9–3.4 s against 1.35 s, and 9000 unmapped pressure messages in 1.6–1.8 s against 0.7–0.9 s (2026-11-03) | verified |

### What happens at load

| ~Time | Event | Evidence | Item |
|-------|-------|----------|------|
| 0 ms, as the patch is made | `[u_map-lua]` reads the table and asks whether a `knobs.txt` is there, and its lookup key's page is `perform` | verified | 234, 239 |
| 0 ms, `loadbang` | `init`: `map-empty` if the table holds nothing, then the bang that proves the Lua loaded | verified | — |
| before 500 ms | mother pushes `knobs.txt`, if a Save has ever happened | verified | 139, 200 |
| 1000 ms | `window-shut`: from now on a knob's first value is a hand, not a restore | verified | 236 |
| 2000 ms | The recover breadcrumb, which may say `live` | verified | 299 |
| ~3500 ms | The song loads, and `u_voices` says the page on the `mode` bus ([voices.md](voices.md)) | unknown | — |

⛔ **Both the read and the key's page have to be there before mother's push.** See *Traps*.

### Parameter pickup — a restored control is held until it crosses

**mother replays `knobs.txt` at boot, so the patch believes a knob sits where the knob physically
does not.** Nothing on the instrument can detect it: mother reports a *position*, not whether that
position is still true. Pickup holds a control until its value passes **through** the stored one,
then hands it authority.

| | | Evidence | Item |
|---|---|---|---|
| The jump it replaces | 443 BPM on knob 1, which is master tempo | verified | 236 |
| Applies to | `og-knob-1`…`og-knob-4` only | verified | 236 |
| Never applies to | any control that is not an Organelle knob — the keys included. The nanoKONTROL's in play are `u_perform`'s ([voices.md](voices.md)) | verified | 236 |
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

### The lookup key has its page at load

⛔ The same symptom, a second cause. mother's push arrives before anything else speaks, so a key that
waits for the `mode` bus has **no page at all** and misses every row.

**Fix:** the key's page is `perform` from the moment the Lua's state is made, so a lookup is never
waiting on a clock. Any real page overwrites it.

### A page carrying no name would empty the key

⛔ The same symptom, a **third** cause. A `mode` naming no page, a lone `compose`, would give the key
no page, and every control would fall to the unmapped branch — no tempo from knob 1, and nothing on
the screen where a BPM belongs (item 294).

⚠️ **On screen it reads as every control falling silent** — nothing where `bpm 120` or
`volca-cc41 64` belongs — because a control's only row is its destination's and a dead lookup sends
every control down the unmapped branch, which draws nothing. Nothing else reports it.

**Fix:** **the Lua refuses a `mode` that is not one atom naming a page, and says `fail u_map
bad-mode`**, the way an unknown *destination* does — item 297. ⚠️ The name is checked as well as
the count: a lone `compose` is one atom too. The key survives it.

### The `[list trim]` before the destination `route` is load-bearing

⛔ The Lua sends the looked-up row as a list, so its selector is `list`, and `route` matches a
**selector** (C-6; Pure Data, in Reference). Without the trim the route never matches, and every
mapped control takes the reject as `unknown-dest`.

**Fix:** `[list trim]` between them.

### A duplicate `<page> <control>` pair silently loses

⚠️ The Lua keeps the **first** row for a page and control, as `[text search]` did before it, so a
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
is the only file that knows what a control means. See [organelle.md](../device/organelle.md).

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

### A Lua that never loads leaves no control at all

⛔ Without pdlua on the path, or with an error in the Lua, `[u_map-lua]` fails to create, and every
control is dead: no page, no tempo knob, no PLAY or STOP, no keyboard.

**Fix:** `u_map.pd` sends `init` at load and says `fail u_map no-lua` on the screen when no bang
comes back; a throwing rule says `fail u_map lua-<rule>` — `lua-param`, `lua-mode` — and the object
carries on. The gates' side of it is the sequencer's trap, *A Lua that never loads is invisible to
the gate's Pd half* ([sequencer.md](sequencer.md)).

## Design

### The pages

**A page is a set of rows in the map and, on the grid, a painter of `g_grid`'s** ([display.md](display.md)).
`u_voices` says which is on show ([voices.md](voices.md)); every page draws every warning
([error.md](error.md)).

| Page | Is | Rows, beside the 94 `all` rows |
|------|----|------------|
| `perform` | The controls in play: the boot's, and PLAY's | The grid's columns and the bottom rows' sixteen buttons, for `u_perform` |
| `drums` | A drum voice's behavior | The drum page's 62 pads, for `c_steps` |
| `harmony` | A harmony voice's | Its pads and five commands, for `c_melody` |
| `melody` | A melody voice's | Its pads and three commands, for `c_melody` |
| `keys` | A voice that's only played from the nanoKEY | None |
| `sound` | A voice's setup, on the phone | None |
| `songs` | The songs and sections, on the phone, opened by aux | None |
| `diag` | The diagnostics, opened by Setup | Its two pads, diag and test mode |

### Why a table at all

The old rule was one `route` branch per mapping, with a written condition to revisit past about ten
mappings. **185 rows is far past it.**

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

### A release is the handler's to ignore

⛔ A Launchpad CC button sends **127 on the press and 0 on the release**, where a nanoKONTROL button
sends only the press. Each button destination's handler opens on non-zero, or every press would fire
**twice** — idempotent often enough that nothing on screen would look wrong. `voices` and `perform`
carry the release to their Lua, which ignores it the same way.

⛔ **The gate cannot go above the route.** `og-key-*` releases are **real note-offs** `volca-key` must
act on (item 293), and `recover` reads its release; a value test up there would swallow every one.

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

The drum page's 62 pads are 62 rows, `drums pad-81 drum-page 81`, and the arg is the grid
index because the handler never sees the control's name — the `volca-key` precedent. The handler
looks the index up in `cut-it-drum-page.txt`, the table `g_grid` paints the page from
([display.md](display.md)), so `c_steps` receives `step 1 100` and never a cell. **The map says
which pads are the drum page; the layout says what each one is.** A row the layout
lacks is a real error, `layout-miss`, as an unknown destination is.

### Tap is one destination and a layout table

The tap button is a row, `all xport-4 arrangement 21`, the nanoKONTROL's LOOP, and the handler looks
its arg up in `cut-it-arrangement-page.txt`, so `u_tempo` gets `tap`. The destination is named for
the arrangement, not the tap, so its next control is a row of the layout and a role `u_tempo`'s
`[route tap]` takes, or a cord of its own for a role another file takes; `map-assert.py` reads the
rows, the layout and that route: every row's cell is in the layout, every cell has its row, on every
page, and every role is one `u_tempo` routes.

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

### The page is `u_voices'`; the table is not state

`u_map` writes nothing about the page: it hears the `mode` bus as `g_grid` and `u_net` do, and
`u_voices` keeps the page across a power cycle ([voices.md](voices.md)).

⚠️ **The table is code, not state.** Nothing rewrites it at runtime, so persisting it would store a
constant, and a restore could silently override the shipped file.

### The lookup in Lua, the destinations in Pd

What moved is what was hardest to read as boxes: pickup's five states were two arrays and forty
boxes, and the divisor and the pickup slots were two routes that had to name the same four knobs.
In `u_map.lua` they are a few dozen lines, tested without Pd: `test/gate/lua/u_map_test.lua` drives the rules, and the
Pd face through a stand-in for pdlua, in the map gate before its Pd half. What stayed is I/O and
timing, and the route that is the allowlist (*The allowlist guard*, above).

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
  and it brings its own persistence with it. NO PLAN OWNS THIS.
- ⬜ **A page change does not re-arm pickup**, so a knob mapped to different destinations per page
  would jump once per change. Not reachable: the Organelle's knobs mean the same on every page
  (Brendan, 2026-11-06). NO PLAN OWNS THIS.
- ⬜ **The Lua map has not been played on the rig.** The gates and a test Pd prove it answers as the
  Pd version did and loads in silence; what it costs under four fingers of pressure, at the live
  Pd's priority, is unmeasured. `cut-it/logic-as-text`.
