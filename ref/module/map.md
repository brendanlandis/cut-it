<!-- schema: module -->
# The map

**Files:** `Cut It/u_map.pd`, `Cut It/cut-it-map.txt` · **Gate:** `tools/phase9-assert.sh` · **Bench:** `tools/phase9-bench.pd`

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
| `<dest>` | One of the nine below, and **only** those | verified | 229 |
| `<arg>` | A float the handler interprets. `0` where the handler has no use for one | verified | — |

**A row with any other width is a lint failure**, not a runtime one — `phase9-assert.py` reads the
file and rejects it before Pd ever does.

### The destinations — the allowlist, in order

<!-- check: pd-route "Cut It/u_map.pd" tempo -->

| Destination | `<arg>` means | Value means | Evidence | Item |
|-------------|---------------|-------------|----------|------|
| `tempo` | unused | Scaled over **10–500 BPM**, rounded | verified | — |
| `transport` | unused | Non-zero **toggles** start/stop | verified | — |
| `start` | unused | Non-zero fires; a release does nothing | verified | — |
| `stop` | unused | Non-zero fires | verified | — |
| `panic` | unused | Non-zero fires | verified | — |
| `volca-note` | The note number | Velocity. Duration is a fixed **200 ms** | verified | — |
| `volca-cc` | The CC number | The CC value | verified | — |
| `volca-prog` | The program number | A **gate only** — it decides whether the press counts | verified | — |
| `404-pad` | The pad number | Velocity | verified | — |

This table is checked against the literal `route` box, so a destination added to the patch and not
to this page fails the doc gate. `phase9-assert.py` checks the same box against the map's rows.

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

**An unmapped control is the normal state of most controls and must stay silent.** Six modes × 42
controls is 252 possible rows and the shipped file has thirteen.

### What happens at load

| ~Time | Event | Evidence | Item |
|-------|-------|----------|------|
| 0 ms | The table is read, and the lookup key's mode is set to `mode-1` **synchronously** | verified | 234 |
| before 500 ms | mother pushes `knobs.txt`, if a Save has ever happened | verified | 139, 200 |
| 500 ms | The `mode` seed fires — `compose mode-1` — behind a spigot any real mode has already closed | verified | — |
| ~3500 ms | `u_state` restores, and a saved `mode` arrives as a real selection | verified | — |

⛔ **Both the read and the key-seed used to be later than mother's push, and both broke the same
thing.** See *Traps*.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### The map must be read at `loadbang` with no delay

⛔ The read sat behind `[del 2000]`, to keep a missing file's error clear of `deploy.sh`'s 735 ms
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
checked from three sides — `phase9-assert.py` against the map's rows, `docs-check.py` against the
table on this page, and a runtime `unknown-dest` on `err`.

### The six transport keys stay hardcoded, and they come first

They **are** the mode selector, so a mode change can never itself be mode-dependent — and if the
table were empty or broken you could still change mode on a device with no console. Everything the
transport `route` does not match falls out of its reject and goes to the table.

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
  and it brings its own persistence with it. See [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **The mode names are placeholders.** `mode-1`…`mode-6` say nothing about what each mode is for,
  and the sound work is what will name them. See [plan-v03.md](../../plan-v03.md) §4.
