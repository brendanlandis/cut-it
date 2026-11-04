<!-- schema: module -->
# The map

**Files:** `Cut It/u_map.pd`, `Cut It/u_map.lua`, `Cut It/u_map-lua.pd_lua`, `Cut It/c_mapped.pd`, `Cut It/cut-it-map.txt` · **Gate:** `test/gate/map-assert.sh`, `test/gate/recover-assert.sh` · **Checklist:** `test/checklists/midi.md`, `test/checklists/recover.md`

## What it is

**`u_map` is the only file in Cut It that says what a control MEANS.** Every device layer publishes
named controls onto `param` and stops there; everything above the map is driven by the buses this
file writes. Nothing in `e_` or `c_` may ever learn that a nanoKONTROL exists, and this is the layer
that keeps that true.

Since v0.3 the map is **table-driven and mode-dependent**. `Cut It/cut-it-map.txt` sits beside the
patch, one row per mapping, and a control means whatever the row for the *current* mode says it
means. Telling the instrument "in mode 2, this fader plays the Volca" is one row of a text file.

**Its lookup is Lua, and its destinations are Pd.** `u_map.lua` reads the table and holds the
lookup key's mode, the lookup, the divisor, parameter pickup and the raw row an unmapped control
draws, as plain Lua that runs on the Mac without Pd; `u_map.pd` keeps the six mode keys, the
destination route and every handler behind it, the boot timers and the files pickup reads, and asks
the Lua through one pdlua object, `[u_map-lua]` (`cut-it/logic-as-text`).

⛔ **The table never names a `[send]`.** It names a destination that must exist as a literal argument
on a `route` box inside `u_map`, feeding a handler you can see on the canvas — the **allowlist
guard**, and the whole of what makes a table acceptable here. See *Design*.

`u_map` has no inlets. It has **one outlet per output device**, wired in `u_root`, because no bus
carries a sounding note — and a third, to `c_steps`, for what a press on mode 1's drum page means
([sequencer.md](sequencer.md)).

## Facts

### A row is four atoms, always

```
<mode> <control> <dest> <arg>

mode-1 og-knob-1 tempo    0
mode-1 slider-1  volca-cc 41
```

| Field | Is | Evidence | Item |
|-------|----|----------|------|
| `<mode>` | The **second** atom of the `mode` bus message — `mode-1`, not `compose mode-1`. The class is `u_err`'s business | verified | — |
| `<control>` | A `param` name, physical and never functional — `og-knob-1`, `slider-1`, `sp-a1` | verified | — |
| `<dest>` | One of the **thirteen** below, and **only** those | verified | 229 |
| `<arg>` | A float the handler interprets. `0` where the handler has no use for one | verified | — |

**A row with any other width is a lint failure**, not a runtime one — `map-assert.py` reads the
file and rejects it before Pd ever does, and the Lua skips it.

### The destinations — the allowlist, in order

<!-- check: pd-route "Cut It/u_map.pd" tempo -->

| Destination | `<arg>` means | Value means | Evidence | Item |
|-------------|---------------|-------------|----------|------|
| `tempo` | unused | **10–500 BPM on a curve**, rounded: 50 to 200 BPM take the knob from 9 o'clock to 3 o'clock, 0.2 to 0.8 of its turn (Brendan, 2026-11-03), three straight pieces in `u_map.lua`'s `R.tempo_curve` | verified | — |
| `transport` | unused | Non-zero **toggles** start/stop. ⚠️ **No shipped row names it** — start and stop are separate buttons | verified | — |
| `start` | unused | Non-zero fires; a release does nothing | verified | — |
| `stop` | unused | Non-zero fires | verified | — |
| `panic` | unused | Non-zero fires | verified | — |
| `volca-note` | The note number | Velocity. Duration is a fixed **200 ms** | verified | — |
| `volca-cc` | The CC number | The CC value | verified | — |
| `volca-prog` | The program number | A **gate only** — it decides whether the press counts | verified | — |
| `404-pad` | The pad number | Velocity | verified | — |
| `volca-key` | The note number | **Velocity, and 0 is a real note-off.** No fixed duration — the release comes from the key | verified | 293 |
| `recover` | unused | **Two tiers on one control.** Non-zero raises `panic` at once; held for **2000 ms** it also raises `recover` | verified | 298 |
| `diag` | unused | Non-zero summons `g_oled`'s diagnostic layer. **`og-shift-60`, in all six modes** | verified | 301 |
| `drum-page` | The **grid index**, looked up in `cut-it-drum-page.txt` | `<role> <n> <velocity>` to `c_steps`, the pad's own velocity, and a release as velocity 0, which `c_steps` acts on only for a repeat pad; an index the layout lacks is `fail u_map layout-miss` | verified | — |
| `test-mode` | unused | Non-zero flips `u_net`'s test mode, which puts the phone's line check up ([phone.md](../device/phone.md)). **`og-shift-61` and `lp-setup`, the Launchpad's Setup, in all six modes**; `lp-setup` has no release, and needs none; out `u_map`'s fourth outlet, a cord to `u_net`. Choosing a mode turns test mode off, in `u_net` | unknown | — |
| `drums` | What the control is to `c_steps`: `last`, `track-last` or `swing` | The knob's 0–1, as it is, held or not: `<arg> <0-1>` to `c_steps` on the drum page's outlet, which scales it, latches it and draws its row. `last` is the global last step, **1–32**, **`og-knob-2`**; `track-last` the selected track's own, **`og-knob-3`**; `swing` the sequencer's, 25% to 75%, **`og-knob-4`**, all in mode 1. A new drum control is a map row: `c_steps` refuses an arg it does not know as `bad-selector` (Brendan, 2026-11-04) | verified | — |

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
and scaled into its units.** The row says what the control *means*, not which fader moved. Each is a
`c_mapped` instance inside `u_map` — `[c_mapped <name-format> <mul> <add>]` — and the scaling exists
there and nowhere else.

| Destination | Live row | Held row | Evidence | Item |
|-------------|----------|----------|----------|------|
| `tempo` | `bpm 75` | `bpm 29 (120)` | verified | 316 |
| `volca-cc` | `volca-cc41 64` | `volca-cc41 64 (114)` | verified | 316 |
| `volca-note` | `volca-note60 100` | same shape | verified | 316 |
| `404-pad` | `404-pad5 90` | same shape | verified | 316 |
| `volca-prog` | `volca-prog 20` — the **arg**, because the value is only a gate | none | verified | 316 |
| `drums` | `last-step 12`, `pad2-last 6`, `swing 62 %`: drawn by `c_steps`, which holds the latch | `last-step 16 (7)`, `swing 50 (25)` | verified | — |
| `volca-key` | **nothing** — 25 keys reporting both edges would evict the five-row screen twice per note | none | verified | 293 |
| `drum-page` | **nothing** — the grid is the feedback, and 56 pads in use would bury the screen | none | unknown | — |
| the buttons — `start` `stop` `transport` `panic` `recover` `diag` | **nothing** — the footer, the aux LED, the grid and the diag layer already say what happened | none | verified | 316 |

⚠️ **The held row's second number rides in the UNIT field.** `g_oled` runs a row's value through
`makefilename %g`, which refuses a symbol, so `(120)` cannot be the value — it is a free symbol in
the third slot.

| | Evidence | Item |
|---|----------|------|
| **A control draws exactly one row, and it is `u_map`'s.** No `m_` file sends a control's row to `disp` — `m_nano`, `m_404` and `m_launchpad` publish on `param` alone, as `m_organelle` always has. A fader mapped to `volca-cc 41` draws `volca-cc41 64` and nothing beside it; an unmapped control draws `<name> <raw>` (*Traps*); a mapped button draws nothing. **The SP-404 included:** its `sp-pad` and `sp-bank` rows are gone too, and a hit draws `sp-b5 90`, one name carrying bank and pad — decided 2026-10-20, at the cost of a fast run of pads meeting the five-row limit with no stable row to fall back on | verified | 317 |
| `map-assert.py` reads every `m_` file's `[s disp]` count, exactly — `m_organelle`'s one carries aux's `modal shift`, never a control | verified | 317 |

### Values are normalized to 0–1, and the divisor is not uniform

⚠️ **`param` values are not one unit.** Every handler sees **0 to 1**, and everything is divided by
127 *except* five controls that already arrive that way.

| Source | Range on `param` | Divided by 127 | Evidence | Item |
|--------|------------------|----------------|----------|------|
| nano faders and knobs | 0–127 | yes | verified | — |
| nano buttons | 1 | yes | verified | — |
| Launchpad pads | 0 or 127 | yes | verified | — |
| 404 pads | a real velocity | yes | verified | — |
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
| Miss | The control's raw row on `disp`, or nothing for a key or pressure (*Parameter pickup*, below) | verified | 242 |
| A duplicate row | The first for a mode and control wins; the rest are dead | verified | — |
| Empty table | `fail u_map map-empty` on `err` at load; a missing file is an error on the console too, which fails a deploy | verified | 234 |

**An unmapped control is the normal state of most controls and must stay silent.** Six modes × 92
controls is 552 possible rows and the shipped file has **143** — knob 1 in all six modes; knobs 2
to 4, slider 1, the keyboard's 25 and the drum page's 60 pads in mode 1; and CC 90, PLAY, STOP, the
four shifted keys and Setup in all six.

### Where each part lives

| | Lives in | Evidence |
|---|---|---|
| The table, the key's mode and its guard, the lookup, the divisor, pickup's five states and the raw row with its two exemptions | `u_map.lua`: a state table and a function per rule, each returning what leaves as `{outlet, selector, atoms}` | verified |
| Reading the table and asking whether a `knobs.txt` is there, turning messages into those calls and their answers into outlets | `u_map-lua.pd_lua`, the class `u_map-lua`: three inlets (every control the mode keys pass on; the `mode` bus; `u_map.pd`'s own `init`, `window-shut` and `live`), five outlets (the destination route, an unmapped control's row, the mode to store, `err`, a bang on `init`) | verified |
| The six mode keys and their release gates, the 500 ms seed, the destination route and its handlers, `c_mapped`, the 1000 ms boot window, the recover breadcrumb at 2000 ms, `put auto mode` and the restore | `u_map.pd` | verified |
| The Lua's answers | The Pd version's, exactly: 38 controls and modes through `u_map` printed the same 42 lines from the Pd version and the Lua, on the Mac and on the Organelle (2026-11-03) | verified |
| What it costs in memory | About 0.1 MB more peak resident in a test Pd loading `main.pd` on the Organelle (3.31–3.42 MB before, 3.44–3.48 after), since `c_steps` loads pdlua already | verified |
| What it costs per control | About twice the Pd version's on the Organelle, in a test Pd niced beside the live one: 9000 mixed controls in 2.9–3.4 s against 1.35 s, and 9000 unmapped pressure messages in 1.6–1.8 s against 0.7–0.9 s (2026-11-03) | verified |

### What happens at load

| ~Time | Event | Evidence | Item |
|-------|-------|----------|------|
| 0 ms, as the patch is made | `[u_map-lua]` reads the table and asks whether a `knobs.txt` is there, and its lookup key's mode is `mode-1` | verified | 234, 239 |
| 0 ms, `loadbang` | `init`: `map-empty` if the table holds nothing, then the bang that proves the Lua loaded | verified | — |
| before 500 ms | mother pushes `knobs.txt`, if a Save has ever happened | verified | 139, 200 |
| 500 ms | The `mode` seed fires — `compose mode-1` — behind a spigot any real mode has already closed | verified | — |
| 1000 ms | `window-shut`: from now on a knob's first value is a hand, not a restore | verified | 236 |
| 2000 ms | The recover breadcrumb, which may say `live` | verified | 299 |
| ~3500 ms | `u_state` restores, and a saved `mode` arrives as a real selection | verified | — |

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
| With **no** `knobs.txt` | **Knob 1 is held at 120 BPM**, `u_tempo`'s own, until it is turned through 0.48, where the curve puts 120 (Brendan, 2026-11-04): its first push draws `bpm 120 (29)` and moves nothing. Every other knob is live from its first value | verified | — |
| **After a `recover`** | the breadcrumb, read at 2000 ms, sends `live`, `knobs.txt` or not: every knob, knob 1 included | verified | 299 |
| The held row is drawn by the **destination**, for any knob mapped to one that carries a value | `c_mapped` gets the latched target and the live flag with every message and draws `name <latched> (<knob>)` in its own units | verified | 316 |
| **Reaching** the target releases, not only passing it | a target on a rail has no beyond: armed above a target of `0`, the flip test waits for `value < 0` | verified | 241 |
| An **unmapped** control reports `<name> <raw>` on `disp` | The Lua's miss, out of `u_map-lua`'s second outlet. Silent on every bus, never on the screen | verified | 242 |
| …**except `og-key-*`**, which is silent on the screen too | 25 controls that also report their releases would evict a five-row screen twice per note. See *Traps* | verified | 293 |
| …**and pressure**, any name ending `-at` — `m_launchpad`'s `pad-NN-at`, and nothing else | A stream per held pad would fill the screen under four fingers. Only the raw row is gated: pressure the mode maps still draws its destination's row. See *Design* | verified | 318 |
| Pickup never stops the lookup | so a held control still knows whether it is mapped, and a held, unmapped knob still draws its raw row | verified | 242 |
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
raised during the boot stages is buried by `modal launchpad` at 3000 and the footer hand-over at
4000, so it waits until 4500. One read, two deadlines.

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
key no mode, and every Organelle knob falls to the raw-row branch — `og-knob-1 0` on screen where a
BPM belongs (item 294).

⛔ **Fed from its own `[r mode]`, the store repairs it in the wrong direction.** Whatever reaches the
bus goes straight back into the store, so the truncated value is re-saved; the auto flush is armed
**by the restore**, so the correct `mode-1` the seed stored at 500 ms is replaced before it ever
reaches the disk. Every boot reads the bad value, re-stores it and writes it back.

⚠️ **On screen it reads as every mapped control drawing its raw row** — `og-knob-1 0` where a BPM
belongs, `slider-1 64` where `volca-cc41 64` does — because a control's only row is `u_map`'s and a
dead lookup sends every control down the unmapped branch (item 317). Nothing else reports it.

**Fix:** **the Lua refuses a `mode` that is not two atoms and says `fail u_map bad-mode`**, the
way an unknown *destination* does — item 297.

⛔ **And the store gets the mode from the Lua, only when the key took it**, never from its own
`[r mode]`, which is what stops a bad value surviving a power cycle. The store never sees it, keeps
the seed's `compose mode-1`, and **the auto flush repairs the file on its own** — measured: a
`cut-it-auto.txt` holding `mode compose` came back reading `mode compose mode-1` after one boot, with
the knobs mapping correctly throughout.

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

### Renaming or re-balancing the six modes is not cosmetic

⚠️ `u_err` routes on `compose` / `perform` — compose shows every error, perform only `fail`. **A
split weighted toward `perform` makes most mode selections silently quieten the error display.**

**Fix:** the current 3/3 split is a decision, not a placeholder. The mode *names* are placeholders;
the ratio is not.

### A knob's raw position is not a readable parameter row

A knob reported to `disp` as well as `param` puts `og-knob-1 0.245` on screen — and ⛔ **`g_oled`'s
param layer REPLACES the footer**, so the BPM it is mapped to disappears exactly while you are
turning it. A 0–1 number where a BPM belongs is not feedback; it is arithmetic homework.

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

### An unmapped control is silent on every bus, but not on the screen

⛔ *"An unmapped control must stay silent"* is a rule about the **buses**. Applied to the screen it
produces a control that does nothing and says nothing — indistinguishable from a broken one
(item 242).

**Fix:** the Lua's miss reports `<control-name> <raw value>` on `disp` — the **pre-divisor** value,
what the device actually sent.

⛔ **This is why pickup never stops the lookup.** A held knob that skipped it would be equally
safe and blind: nothing could tell an unmapped control from a suppressed one. The lookup always
runs; only the destination's action is held.

⚠️ **It is the only row the control gets.** No `m_` layer posts one of its own (item 317), so this
report is what makes `slider-3`, `sp-b5` and `pad-43` name themselves on the screen — a release
included, at velocity 0, wherever the device layer publishes one.

### A target sitting on a rail can never be crossed

⛔ The release test is a **side flip** — a knob armed *above* the target, `target <= value`, waits
for that to go false, which is `value < target`. **With a target of `0` that is
unreachable however far the knob is turned down.** Save with knob 1 at the bottom and master tempo is
dead for the whole session, and nothing reports it (item 241).

**Fix:** release on the flip **or** on `value == target`. Equality can never fire spuriously — a knob
sitting exactly on its stored value *is* in sync, which is the entire definition of pickup.

### An armed knob that is mapped to nothing draws its raw row, not a held one

⛔ A held row built for every armed knob announces the knobs mapped to nothing in whatever units it
was hardcoded to — `bpm 10 (60)` from a knob that drives no tempo (item 240).

**Fix:** the held row is the destination's, so a knob that reaches no destination draws none. It is
still held, and it still reports `og-knob-2 0.75` through the unmapped path above, so it cannot be
told from a broken one.

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
`[u_map-lua]` fails to create, and every control but the six mode keys is dead: no tempo knob, no
PLAY or STOP, no keyboard.

**Fix:** `u_map.pd` sends `init` at load and says `fail u_map no-lua` on the screen when no bang
comes back; a throwing rule says `fail u_map lua-<rule>` — `lua-param`, `lua-mode` — and the object
carries on. The gates' side of it is the sequencer's trap, *A Lua that never loads is invisible to
the gate's Pd half* ([sequencer.md](sequencer.md)).

## Design

### Why a table at all

The old rule was one `route` branch per mapping, with a written condition to revisit past about ten
mappings. **42 controls × six modes is far past it**, and the mode dependency alone would have
multiplied the branch count by six.

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

### The six mode keys stay hardcoded, and they come first

They **are** the mode selector, so a mode change can never itself be mode-dependent — and if the
table were empty or broken, or the Lua never loaded, you could still change mode on a device with no
console. Everything the mode `route` does not match falls out of its reject and goes to the Lua.

**They are the top six of the Launchpad's left column, `lp-cc-80` down to `lp-cc-30`**, mode 1 at the
top — the six buttons `g_grid` lights as the mode lamps, so the thing you look at is the thing you
press. The top row, CC 91–98, is free. See
[launchpad.md](../device/launchpad.md).

⛔ **Each of the six branches carries a `[select 0]`, and that is not decoration.** A Launchpad CC
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

Mode 1's 60 drum-page pads are 60 rows, `mode-1 pad-81 drum-page 81`, and the arg is the grid
index because the handler never sees the control's name — the `volca-key` precedent. The handler
looks the index up in `cut-it-drum-page.txt`, the table `g_grid` paints the page from
([display.md](display.md)), so `c_steps` receives `step 1 100` and never a cell. **The map says
which pads are the drum page in which mode; the layout says what each one is.** A row the layout
lacks is a real error, `layout-miss`, as an unknown destination is.

### Pressure draws no raw row, like the keys

**An unmapped `pad-NN-at` draws nothing** — decided 2026-10-20 (item 318). Pad pressure is a
continuous stream per held pad, which is why `m_launchpad` keeps it off `disp`; the unmapped report
put it back on the screen the moment polyphonic aftertouch was on, four fingers filling all five
rows. The keys were exempted for the same reason (item 293).

The test is a **suffix**, `-at`, because only `m_launchpad`'s pressure names carry it, beside the
keys' prefix, `og-key`, in one rule of `u_map.lua`.

⚠️ **Only the raw row is exempt.** A pressure name the mode maps still reaches its destination and
draws that destination's row; `map-assert` drives one mapped and one unmapped, with a pad's own press
beside them as proof the test is not too wide.

### Arg then value, always — and `[unpack]` gives them in the right order for free

Every branch receives `<arg> <value>` as two floats, and `[unpack]` fires **right to left**: the
value lands in a cold inlet or sets a gate before the arg arrives to trigger. That is the same
guarantee `m_volca`'s `[t b f]` had to be built by hand to get.

### The spigot is one uniform trigger test

A nano button sends 1, a pad sends 127, an Organelle aux sends 1, a 404 pad sends a real velocity —
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
restore arrives as `compose mode-1` with `compose` as its selector, which is exactly the shape
`s mode` wants — so no `[list trim]` on that side.

⚠️ **The table is code, not state.** Nothing rewrites it at runtime, so persisting it would store a
constant, and a restore could silently override the shipped file.

### The seed fills a silence, it does not set a default

Nothing else writes `mode` at load, so without the seed the grid boots with no mode to show. Any
incoming mode closes the spigot, so a real selection always wins — including the seed's own send,
harmlessly, because Pd is synchronous and the bang has already passed through.

### The lookup in Lua, the destinations in Pd

What moved is what was hardest to read as boxes: pickup's five states were two arrays and forty
boxes, the divisor and the pickup slots were two routes that had to name the same four knobs, and the
key and pressure tests were each a chain of `list` objects taking a name apart. In `u_map.lua` they
are a few dozen lines, tested without Pd: `test/gate/lua/u_map_test.lua` drives the rules, and the
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
- ⬜ **The mode names are placeholders.** `mode-1`…`mode-6` say nothing about what each mode is for,
  and the sound work is what will name them. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **A mode change does not re-arm pickup**, so a knob mapped to different destinations per mode
  would jump once per change. Not reachable today — `og-knob-1` is `tempo` in all six modes. **It
  closes with live re-assignment above, or not at all**: see [plan-v04.md](../../plan-v04.md) §3.
  ⚠️ Doing it *cheaply* is worse than nothing — re-arming to the knob's last position puts the next
  move on the far side and suppresses until you turn back. Doing it right needs a per-`(mode, knob)`
  value memory: pickup's state in `u_map.lua` keyed by mode as well as knob.
- ⬜ **The Lua map has not been played on the rig.** The gates and a test Pd prove it answers as the
  Pd version did and loads in silence; what it costs under four fingers of pressure, at the live
  Pd's priority, is unmeasured. `cut-it/logic-as-text`.
