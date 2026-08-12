<!-- schema: module -->
# The map

**Files:** `Cut It/u_map.pd`, `Cut It/cut-it-map.txt` · **Gate:** `test/gate/map-assert.sh`, `test/gate/recover-assert.sh` · **Bench:** `test/bench/midi-bench.pd`

## What it is

**`u_map` is the only file in Cut It that says what a control MEANS.** Every device layer publishes
named controls onto `param` and stops there; everything above the map is driven by the buses this
file writes. Nothing in `e_` or `c_` may ever learn that a nanoKONTROL exists, and this is the layer
that keeps that true.

Since v0.3 the map is **table-driven and mode-dependent**. `Cut It/cut-it-map.txt` sits beside the
patch, one row per mapping, and a control means whatever the row for the *current* mode says it
means. Telling the instrument "in mode 2, this fader plays the Volca" is one row of a text file.

⛔ **The table never names a `[send]`.** It names a destination that must exist as a literal argument
on a `route` box inside `u_map`, feeding a handler you can see on the canvas — the **allowlist
guard**, and the whole of what makes a table acceptable here. See *Design*.

`u_map` has no creation arguments and no inlets. It has **one outlet per output device**, wired in
`u_root`, because no bus carries a sounding note.

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
| `<control>` | A `param` name, physical and never functional — `og-knob-1`, `slider-1`, `sp-hit` | verified | — |
| `<dest>` | One of the **twelve** below, and **only** those | verified | 229 |
| `<arg>` | A float the handler interprets. `0` where the handler has no use for one | verified | — |

**A row with any other width is a lint failure**, not a runtime one — `map-assert.py` reads the
file and rejects it before Pd ever does.

### The destinations — the allowlist, in order

<!-- check: pd-route "Cut It/u_map.pd" tempo -->

| Destination | `<arg>` means | Value means | Evidence | Item |
|-------------|---------------|-------------|----------|------|
| `tempo` | unused | Scaled over **10–500 BPM**, rounded | verified | — |
| `transport` | unused | Non-zero **toggles** start/stop. ⚠️ **No shipped row names it** — start and stop are separate buttons now | verified | — |
| `start` | unused | Non-zero fires; a release does nothing | verified | — |
| `stop` | unused | Non-zero fires | verified | — |
| `panic` | unused | Non-zero fires | verified | — |
| `volca-note` | The note number | Velocity. Duration is a fixed **200 ms** | verified | — |
| `volca-cc` | The CC number | The CC value | verified | — |
| `volca-prog` | The program number | A **gate only** — it decides whether the press counts | verified | — |
| `404-pad` | The pad number | Velocity | verified | — |
| `volca-key` | The note number | **Velocity, and 0 is a real note-off.** No fixed duration — the release comes from the key | verified | 293 |
| `recover` | unused | **Two tiers on one control.** Non-zero raises `panic` at once; held for **2000 ms** it also raises `recover` | verified | 298 |
| `diag` | unused | Non-zero summons `g_oled`'s diagnostic layer. **`lp-cc-80`, in all six modes** | verified | 301 |

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

### Values are normalised to 0–1, and the divisor is not uniform

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

One destination fed from two surfaces would otherwise need two scalings.

### The lookup

| Step | Detail | Evidence | Item |
|------|--------|----------|------|
| Key | `<mode> <control>`, two atoms | verified | 229 |
| `[text search $0-map]` | A two-atom key matches leading fields **0 and 1 with no field arguments at all** | verified | 229 |
| Hit | The row number, into `[text get $0-map 2 2]` → `<dest> <arg>` | verified | 229 |
| Miss | Returns **-1**, into `[moses 0]`, and **nothing is connected to the left outlet** | verified | 229 |
| Read | `read -c cut-it-map.txt` at `loadbang`, **no delay**. Relative, so it resolves against the patch folder on the Mac, on the device and inside the gate's scratch copy | verified | 229, 234 |
| Empty table | Reported on `err` as `map-empty` | verified | 234 |

**An unmapped control is the normal state of most controls and must stay silent.** Six modes × 67
controls is 402 possible rows and the shipped file has **56** — seven, plus the keyboard's 25 in
mode 1, plus CC 90, CC 80, PLAY and STOP in all six.

### What happens at load

| ~Time | Event | Evidence | Item |
|-------|-------|----------|------|
| 0 ms | The table is read, and the lookup key's mode is set to `mode-1` **synchronously** | verified | 234 |
| before 500 ms | mother pushes `knobs.txt`, if a Save has ever happened | verified | 139, 200 |
| 500 ms | The `mode` seed fires — `compose mode-1` — behind a spigot any real mode has already closed | verified | — |
| ~3500 ms | `u_state` restores, and a saved `mode` arrives as a real selection | verified | — |

⛔ **Both the read and the key-seed used to be later than mother's push, and both broke the same
thing.** See *Traps*.

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
| Whether that arming survives | `u_map` **reads `knobs.txt` itself** at 2000 ms. `[text size]` answers 1 when the file is there and 0 when it is not | verified | 239 |
| With **no** `knobs.txt` | every slot is written straight to LIVE and no knob is ever held | verified | 239 |
| **After a `recover`** | the breadcrumb is read in the same 2000 ms pass and every slot goes straight to LIVE, `knobs.txt` or not | verified | 299 |
| The held row is drawn for **knob 1 only** | it is built inside the pickup machine, which cannot know what a held knob maps to. Knobs 2–4 are held *silently* | verified | 240 |
| **Reaching** the target releases, not only passing it | a target on a rail has no beyond: armed above a target of `0`, the flip test waits for `value < 0` | verified | 241 |
| An **unmapped** control reports `<name> <raw>` on `disp` | `[moses 0]`'s left outlet — `[text search]` answers `-1`. Silent on every bus, never on the screen | verified | 242 |
| …**except `og-key-*`**, which is silent on the screen too | 25 controls that also report their releases would evict a five-row screen twice per note. See *Traps* | verified | 293 |
| The pickup gate sits **below** the lookup | so a held control still knows whether it is mapped. The lookup is a pure read | verified | 242 |
| State | Five, per knob, in two 4-element arrays | verified | 236 |
| mother pushes **once** at load and then says nothing | One `og-knob-1` in twelve seconds, untouched, on the device | verified | 237 |
| With `knobs.txt`, the push is the **saved** value, at **100 ms** | Three consecutive boots, identical | verified | 239 |
| With **no** `knobs.txt`, mother pushes the **live physical position**, at ~223 ms | `0.373412` against a saved `0.0957967` | verified | 239 |

**The five states.** `0` virgin, never seen a value · `1` armed, side not yet known · `2` armed
**above** the target, waiting for a fall · `3` armed **below** it, waiting for a rise · `4` live.
States 2 and 3 *are* the answer they wait for offset by two, so one comparison releases both.

**Arming takes two answers, and the boot window is only the first.** A first value inside the window
is a restore rather than a hand, so it arms; a first value after it is a hand and goes straight to
live. ⛔ **But mother pushes a value either way** — the *saved* position when `knobs.txt` exists, the
*live physical* position when it does not, both inside the window — so the window alone armed knobs
that were already in sync. `u_map` therefore **reads `knobs.txt` itself**, and if the file is absent
it writes every slot to LIVE. Nothing is held on a machine that has never been Saved.

⚠️ **Both branches pass the value through, which is the only reason a timer is tolerable here.** Item
234 was two boot races that shipped silently. A window too short costs the old jump; one too long
costs a knob that needs one sweep to free it. **Neither can produce silence.**

### The recover breadcrumb, and why `u_map` reads it

**`u_init` writes `<state-dir>/cut-it-recover.txt` immediately before it fires the reload**, and
`u_map`'s 2000 ms probe reads it in the same pass that reads `knobs.txt`. Item 299.

| | | Evidence | Item |
|---|---|---|---|
| Armed contents | `recover <ms>` — the stamp is elapsed milliseconds since load, from `[realtime]` | verified | 299 |
| Cleared contents | `none`, written back over line 0 | verified | 299 |
| A missing file | `[text size]` answers **0** and nothing happens, exactly as a missing `knobs.txt` does | verified | 299 |
| The arming override | Every slot straight to **4, LIVE** — it bangs the same `msg 4` the no-save probe uses | verified | 299 |
| The report | `warn u_map recovered`, deferred to **4500 ms** | verified | 299 |

⛔ **The override must land at 2000 ms and the report must not.** After an emergency the knobs you
are *holding* are the truth, so nothing may be held — but arming is decided at 2000, and an override
any later would simply be undone by the knobs probe. The **report** goes the other way: a `warn`
raised during the boot stages is buried by `modal launchpad` at 3000 and the footer hand-over at
4000, so it waits until 4500. One read, two deadlines.

⛔ **The file is cleared by OVERWRITING it, never by deleting it.** Vanilla Pd cannot delete a file;
`[shell]` forks, is a do-nothing stub on the Mac, and would let a gate reach only one branch — the
same argument that already forbids it in the no-save probe. A one-line sentinel makes the read decide
on **content**, so nothing depends on how `[text]` writes an empty table, which has never been
measured here.

⚠️ **`[text set]` takes a LIST and has no outlet** — so the sentinel is `list none`, and the write
hangs off a trigger beside it rather than downstream of it. Both were found by loading the patch, not
by reading it.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### The map must be read at `loadbang` with no delay

⛔ The read sat behind `[del 2000]`, to keep a missing file's error clear of `tools/deploy.sh`'s 735 ms
output gate. But **mother pushes `knobs.txt` at boot, long before 2000 ms**, so the restored tempo
knob hit an **empty table** and was silently dropped. The instrument booted at `u_tempo`'s fallback
120 instead of the saved 57, and nothing reported it (item 234).

**Fix:** read at `loadbang`. A missing map *should* fail a deploy, so that error is welcome rather
than something to hide from — and an empty table is reported on `err` for the same reason.

### The lookup key gets its mode at load, not from the seed

⛔ The same symptom, a second cause. The `mode` bus is seeded at 500 ms; mother's push arrives before
that, so the key had **no mode at all** and missed every row.

**Fix:** set the key to `mode-1` synchronously at load, so a lookup is never waiting on a clock. Any
real mode still overwrites it, from the seed or from a restore.

### A restored `mode` carrying no name empties the key again, and a reboot does not clear it

⛔ The same symptom, a **third** cause, and the only one that survives a power cycle. `u_state`
replays the saved `mode` at ~3500 ms; a stored value of `compose` with **no mode name** leaves
`[list split 1]`'s remainder empty, so `[list prepend]`'s cold inlet is emptied and the key becomes
the control name alone. `[text search]` then hunts for `og-knob-1` in the **mode** column, where it
can never match, and every Organelle knob falls to the raw-row branch — `og-knob-1 0` on screen
where a BPM belongs (item 294).

⛔ **And it used to repair itself in the wrong direction.** `u_map` put whatever reached the bus
straight back into the store, so the truncated value was re-saved; the auto flush is armed **by the
restore**, so the correct `mode-1` the seed stored at 500 ms was replaced before it ever reached the
disk. Every boot read the bad value, re-stored it and wrote it back.

⚠️ **It is invisible on every surface but one.** `m_nano`, `m_404` and `m_launchpad` post their own
`disp` rows and theirs land *after* `u_map`'s, so they win; `m_organelle` is the only device file
that posts none (item 242). A dead lookup therefore shows up **only** on the Organelle's own knobs.

**Fix:** ✅ **the key-setter refuses a `mode` that is not two atoms and says `fail u_map bad-mode`**,
the way an unknown *destination* already did — item 297.

⛔ **The guard is BEFORE `[list split 1]`, not after it.** What that object does with a one-atom list
is exactly the behaviour this bug turns on, so testing the length of the whole message is the one
shape that cannot depend on it. `[list length]` → `[select 2]` opens a spigot; anything else raises.

⛔ **And the store is fed from that spigot rather than from its own `[r mode]`**, which is what stops
a bad value surviving a power cycle. The store never sees it, keeps the seed's `compose mode-1`, and
**the auto flush repairs the file on its own** — measured: a `cut-it-auto.txt` holding `mode compose`
came back reading `mode compose mode-1` after one boot, with the knobs mapping correctly throughout.
⚠️ **It is a cord and not a second receive** — two `[r mode]` boxes have no defined order between
them, so a spigot set by one could be read stale by the other.

### `read -c` takes the flag first

⛔ `read cut-it-map.txt -c` warns and then reads the whole file as **one line** — a table that
matches nothing.

**Fix:** `read -c cut-it-map.txt`.

### The `[list trim]` before the destination `route` is load-bearing

⛔ `[list split 1]` emits `symbol og-knob-1`, whose selector is `symbol` rather than the name, and
`route` matches a **selector** (C-6). Without the trim the route never matches, every control takes
the reject, and the Organelle's 0–1 knobs are divided by 127 into nothing.

**Fix:** `[list trim]` between them. Silent in both directions if you forget.

### A duplicate `<mode> <control>` pair silently loses

⚠️ `[text search]` returns only the **first** match, so a second row for the same pair is dead and
nothing says so.

**Fix:** none available in the patch — **the gate's static lint is what catches it**, because a
running instrument cannot.

### A row naming an unknown destination is a real error

⚠️ It goes to `err` as `fail u_map unknown-dest` and emits nothing. **This is the one failure this
design can have that nothing else would catch.**

⛔ **Contrast the `[moses]` miss, which is normal and silent.** Two rejects in this file mean
opposite things: an unmapped *control* is expected, an unmapped *destination* is a bug.

### Renaming or re-balancing the six modes is not cosmetic

⚠️ `u_err` routes on `compose` / `perform` — compose shows every error, perform only `fail`. **A
split weighted toward `perform` makes most mode selections silently quieten the error display.**

**Fix:** the current 3/3 split is a decision, not a placeholder. The mode *names* are placeholders;
the ratio is not.

### A knob's raw position is not a readable parameter row

`m_organelle` used to report every knob to `disp` as well as `param`, so turning knob 1 put
`og-knob-1 0.245` on screen — and ⛔ **`g_oled`'s param layer REPLACES the footer**, so the BPM it
was mapped to disappeared exactly while you were turning it. A 0–1 number where a BPM belongs is not
feedback; it is arithmetic homework.

**Fix:** the knobs no longer report to `disp`. `u_map` reports the **mapped** value instead, because
it is the only file that knows what a control means. An **unmapped** knob now shows nothing, which is
correct: it means nothing. ⚠️ **`og-aux` used to keep a report of its own and no longer exists as a
control at all** — it is the keyboard's modifier, so there is nothing for the map to bind and nothing
to draw. See [organelle.md](../device/organelle.md).

### While pickup holds, one row carries both numbers

`bpm 57 (120)` — the latched tempo still in force, and where the knob is currently pointing. The gap
between them tells you which way to turn.

⛔ **The value must be a float** — `g_oled` runs it through `makefilename %g`, which refuses a
symbol. So the second number rides in the **unit** field, which is a free symbol.

⛔ **A held value never reaches the tempo branch**, because pickup gates the control *name* and the
lookup never runs. The held readout is therefore built inside the pickup machine, which is why the
0–1 → BPM scaling exists twice in `u_map`.

**Fix:** nothing to do here. ⚠️ But when this pattern reaches the other destinations, each scaling
must live **with its destination** — otherwise every destination that gains a held readout duplicates
it again.

### Pickup gates the control NAME, never the value

`[list append]` holds the value in its **cold** inlet. Suppressing the value would leave the
*previous* one parked and the name would still fire it — re-sending a stale BPM for `tempo`, and
firing a **note** on every suppressed step for a knob mapped to `volca-note`, carrying a value that
could have come from another surface entirely.

**Fix:** the spigot sits between the name split and the lookup. Nothing downstream runs when it is
shut.

### An unmapped control is silent on every bus, but not on the screen

⛔ *"An unmapped control must stay silent"* is a rule about the **buses**. Applied to the screen it
produced a control that does nothing and says nothing — indistinguishable from a broken one. The
Organelle's knobs were the case that shipped that way, because `m_organelle` stopped reporting raw
positions when `u_map` took over the row (item 242).

**Fix:** `[text search]` answers `-1` for a name with no row, so `[moses 0]`'s left outlet is the
miss. It reports `<control-name> <raw value>` on `disp` — the **pre-divisor** value, what the device
actually sent.

⛔ **This is why the pickup gate moved below the lookup.** It used to sit on the control NAME, above
`[text search]`: equally safe, and blind — a held knob never reached the lookup, so nothing could tell
an unmapped control from a suppressed one. The lookup is a pure read and now always runs; only the
emission is gated.

⚠️ `m_nano`, `m_404` and `m_launchpad` still post their own rows for the same controls, and theirs
land **after** this one, so they win and nothing about those surfaces changes. `g_oled` updates a row
in place by name, so the duplicate costs nothing.

### A target sitting on a rail can never be crossed

⛔ The release test is a **side flip** — `[<=]` computes `target <= value`, and a knob armed *above*
the target waits for that to go false, which is `value < target`. **With a target of `0` that is
unreachable however far the knob is turned down.** Save with knob 1 at the bottom and master tempo is
dead for the whole session, and nothing reports it (item 241).

**Fix:** release on the flip **or** on `value == target`. Equality can never fire spuriously — a knob
sitting exactly on its stored value *is* in sync, which is the entire definition of pickup.

### An armed knob that is mapped to nothing still had something to say

⛔ The held row is assembled **inside the pickup machine**, because a held value never reaches the
lookup — so it cannot know what the knob maps to, and it is hardcoded to `bpm` and the tempo scaling.
Every armed knob therefore announced itself as a tempo, including the three mapped to nothing:
`bpm 10 (60)` from knob 2 (item 240).

**Fix:** the row is gated on slot 0. Knobs 2–4 are still held, they are just silent about it.
⚠️ That is the *same* tempo-only assumption already carried by the `bpm` prefix and the `× 490 + 10`
beside it — made once more rather than newly, and it goes when the row moves to its destination.

### A boot push is not proof that anything was restored

⛔ mother pushes a knob value at load **whether or not `knobs.txt` exists** — the saved position when
it does, the knob's own live position when it does not. Arming on the push alone latched knobs that
already agreed with the hardware, and they then stayed dead until turned back past where they
started. Reachable on a fresh install and after any `tools/deploy.sh --clean` (item 239).

**Fix:** ask the direct question. `u_map` reads `knobs.txt` into a `[text define]` and takes
`[text size]` — 1 when present, 0 when absent — and on absent it writes every pickup slot to LIVE.

⛔ **Do not answer it from the timing.** The push lands at 100 ms with the file and at ~223 ms
without, and that gap is an artefact of the error path taking longer, not a promised signal.
⛔ **Do not answer it with `[shell]` either.** It forks and replies hundreds of milliseconds later,
it is a do-nothing stub on the Mac, and a gate could then only ever reach one of the two branches. A
`[text]` read behaves identically on both machines, so the gate creates the file or does not and
exercises the real path either way.

⚠️ **The read sits behind `[del 2000]` because a missing file prints three lines**, and `tools/deploy.sh`
fails a check on any output before ~735 ms (C-9). Deferring costs nothing: mother's push is taken by
the virgin branch either way, and a knob turned inside the first two seconds is released the instant
the probe fires.

### The reject is the normal path in the divisor test

⚠️ Opposite of the `route` above the handlers: almost every control in the rig is 0–127, and the five
that are not are the exception being tested for. The `[t b]` in front of anything downstream is still
the reject-outlet rule (C-8) — a reject carries the **data** that failed to match, never a bang.

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

### The six mode keys stay hardcoded, and they come first

They **are** the mode selector, so a mode change can never itself be mode-dependent — and if the
table were empty or broken you could still change mode on a device with no console. Everything the
mode `route` does not match falls out of its reject and goes to the table.

**They are the Launchpad's top row, `lp-cc-91`…`lp-cc-96`** — the six pads `g_grid` already lights
as the mode lamps, so the thing you look at is the thing you press. They were the nanoKONTROL's
transport row until the aux button was wanted as a modifier and PLAY and STOP went back to meaning
play and stop. See [launchpad.md](../device/launchpad.md).

⛔ **Each of the six branches carries a `[select 0]`, and that is not decoration.** A Launchpad CC
button sends **127 on the press and 0 on the release**; the nano transport row it replaced sent only
the press. Ungated, every mode selection fires **twice** — idempotent, so nothing on screen looks
wrong, while every `mode` message, every state-store write and every `g_grid` repaint silently
doubles.

⛔ **The gate cannot go above the route.** That reject is the whole table path, and `og-key-*`
releases are **real note-offs** `volca-key` must act on (item 293) — a value test up there would
swallow every one and hang notes on the Volca. `[select 0]`'s reject carries anything that is not a
release, which is the value the message box wanted anyway (C-8).

### The value is parked and the name does the work

`[list split 1]` fires its **remainder** first, so the value is normalised and stored in `[list
append]`'s right inlet before the name has even started the lookup. The looked-up destination then
arrives on the **left** and picks the parked value back up.

### Arg then value, always — and `[unpack]` gives them in the right order for free

Every branch receives `<arg> <value>` as two floats, and `[unpack]` fires **right to left**: the
value lands in a cold inlet or sets a gate before the arg arrives to trigger. That is the same
guarantee `m_volca`'s `[t b f]` had to be built by hand to get.

### The spigot is one uniform trigger test

A nano button sends 1, a pad sends 127, an Organelle aux sends 1, a 404 pad sends a real velocity —
**all non-zero after normalising, and a release is zero.** So the gate opens on non-zero and the arg
passes through it: one test, not a different threshold per surface.

`volca-prog` uses the value as a gate rather than as data, because a program number is the *arg* —
so a fader release cannot select a patch.

### A file, not `[text define -k]`

The rows live in `cut-it-map.txt` so the map **diffs one row at a time** and can be edited without
opening Pd. The read is relative — no path, no creation argument, nothing absolute — so one file
works on the Mac, on the device and inside the gate's scratch copy (item 229).

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

## Open

- ⬜ **Live re-assignment — editing a mapping from the instrument rather than the file — is v0.4**,
  and it brings its own persistence with it. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **The mode names are placeholders.** `mode-1`…`mode-6` say nothing about what each mode is for,
  and the sound work is what will name them. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **Only `tempo` shows its mapped value.** An *unmapped* control now reports raw (item 242), so
  nothing is silent — but a control mapped to anything **other than tempo** still shows nothing,
  because the mapped row and the held `(n)` bracket both carry the tempo scaling. Making it universal
  is decided and scoped — see [plan-v04.md](../../plan-v04.md) §3.
- ✅ **`u_map` no longer accepts a `mode` it cannot use** — item 297, the Trap above. The key-setter
  refuses anything that is not two atoms, raises `fail u_map bad-mode`, and the state store is fed
  from the same guard so a bad value can no longer survive a power cycle. **The file now repairs
  itself**, where the old note said a mode selection had to be made by hand.
- ⬜ **A mode change does not re-arm pickup**, so a knob mapped to different destinations per mode
  would jump once per change. Not reachable today — `og-knob-1` is `tempo` in all six modes. **It
  closes with live re-assignment above, or not at all**: see [plan-v04.md](../../plan-v04.md) §3.
  ⚠️ Doing it *cheaply* is worse than nothing — re-arming to the knob's last position puts the next
  move on the far side and suppresses until you turn back. Doing it right needs a per-`(mode, knob)`
  value memory, and the arrays widen 4 → 24 with one index term.
