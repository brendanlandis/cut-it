<!-- schema: module -->
# State and persistence

**Files:** `Cut It/u_state.pd`, `Cut It/u_store.pd`, `Cut It/state-dir.sh` · **Gate:** `tools/phase8-assert.sh` · **Bench:** `tools/phase8-bench.pd`

## What it is

**`u_state` is the data store, and the only file that says WHEN state is written.** It owns two
`u_store` instances and the `state` bus, and **it knows nothing about what any key means**: a
contributor names its own key and declares its own policy, so an abstraction written long after
`u_state` persists itself with no change here. That is the whole point of it.

`u_store` is the layer below — a **keyed line store with one file behind it**. Give it a list and it
replaces the line whose first atom matches, appending if there is none. It knows nothing about
policy, about when to write, or about the bus.

**Two policies, two stores, two files.** `auto` is a running value, flushed on a timer; `manual` is a
committed take, written only when a commit is asked for and therefore abandonable by not saving.

⚠️ **The data does not live in the patch folder.** `u_state` writes to `/sdcard/cut-it-state/`,
outside it, so `deploy.sh`, `deploy.sh --clean` and a power cycle cannot touch it.
`tools/fetch-state.sh` is the other half of that bargain and copies it back into the repo.

## Facts

### The `state` bus

**One name, three selectors, disjoint per side**, so the whole protocol fits in one C-2 allowlist
entry with no loop. Contributors `[route save restore]`; `u_state` routes `put` and rejects its own
traffic into nothing.

| Direction | Message | Meaning | Evidence | Item |
|-----------|---------|---------|----------|------|
| contributor → `u_state` | `put auto <key> <atoms…>` | Store now; flushed on a timer | verified | — |
| `u_state` → all | `save` | Broadcast at a commit — **answer now** | verified | — |
| contributor → `u_state` | `put manual <key> <atoms…>` | The answer to a `save` | verified | — |
| `u_state` → all | `restore <key> <atoms…>` | Replayed at load, one message per line | verified | — |

### `u_state`

| | | Evidence | Item |
|---|---|----------|------|
| Creation arg 1 | The data **directory**, absolute, no trailing slash | verified | — |
| Inlet 1 | A bang meaning **restore now**, wired from `u_init` because startup order is `u_init`'s | verified | — |
| Outlets | **None** — everything leaves on the bus | verified | — |
| Auto flush | A dirty flag and `[metro 2000]`, `u_err`'s shape. Capture is unconditional; only the **write** is rate-limited, so a burst cannot thrash the SD card | verified | — |
| Restore order | **manual first, auto second** — the trigger's right outlet fires first | verified | — |
| The dirty flag | Driven by the **auto** store only. The manual store's `changed` outlet is deliberately unconnected | verified | — |

### `u_store`

| | | Evidence | Item |
|---|---|----------|------|
| Creation arg 1 | The **full path** of its file, absolute | verified | — |
| Inlet 1 | A list to store, or `write`, or `load` | verified | — |
| Outlet 1 | Each stored line, one message per line, replayed by `load` | verified | — |
| Outlet 2 | A bang whenever a line **changed** | verified | — |
| `load` | Reads into a **separate** `[text]` and replays it. **The live store is never wiped by a load** | verified | — |
| Key matching | **Whole atoms, not prefixes** — with lines keyed `mode`, `drums` and `drumkit`, a search for `drums` returns 1, not 2. A key may safely be a prefix of another | verified | — |
| A missing key | `[text search]` returns **-1**, which becomes `[text size]` — one past the end, which **appends** | verified | — |
| An empty or missing file | `[text size]` is 0 and `[until]` with 0 runs **zero times**, so it replays nothing rather than looping forever | verified | — |

### The files

| | | Evidence | Item |
|---|---|----------|------|
| Directory | `/sdcard/cut-it-state/` on the device; `main-dev.pd` passes an existing directory on the Mac | verified | — |
| Files | `cut-it-auto.txt`, `cut-it-manual.txt` | verified | — |
| Format | One line per key, first atom is the key. Written and read with **`-c`** | verified | — |
| Made at load | `state-dir.sh` via `[shell]`, once per load. It **`mkdir -p`s the directory and `touch`es both files** | verified | 143, 147 |
| A write into a missing directory | **Prints `write failed`** — it does not fail silently | verified | 143 |
| A read of a missing file | Prints **three lines** | verified | 147 |

**Without the touch, a fresh install would print six error lines at every boot before doing anything
wrong** — the same class of noise as mother's own `knobs.txt: can't open`.

⚠️ **`touch` never truncates**, which is what makes it safe at every load. Creating the files with
`>` would destroy every previous session's state, before anything had a chance to read them.

### Contributors today

| Key | Policy | Written by | Evidence | Item |
|-----|--------|------------|----------|------|
| `mode` | `auto` | `u_map` — a running value, pushed whenever it changes | verified | — |

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### A FAILED write reports a fast time

⛔ A `[text write]` into a directory that does not exist came back in **0.183 ms** — faster than any
successful write, because nothing was written. **A write time cannot tell you a write happened**, and
timing one is exactly the sort of check that looks like verification and is not.

**Fix:** read the file back, or watch for the `write failed` print. See *The files* above.

### A `manual` answer must be SYNCHRONOUS

⛔ **This is the one rule a contributor can break invisibly.** Pd is eager, synchronous and
depth-first, so by the time the `save` broadcast returns, every honest answer is already stored —
which is why the write sits on the trigger's **left** outlet and needs no settle timer at all.

**A contributor answering from behind a `[del]` is simply not in the file**, and the failure is a
short file rather than an error.

**Fix:** answer during the broadcast. Say so in the contributor, not only here.
`tools/phase8-assert.sh` asserts it with a deliberately-late contributor, because a rule nothing
tests is a rule that quietly stops being true.

### `u_state` must never write a file it has not yet read

⛔ The auto flush is armed **by the restore**, not by a `loadbang`. The first build armed it at 3 s
while `u_init` restores at ~3.5 s, so **every boot overwrote the previous session with its own
defaults** — and the file looked entirely plausible throughout (item 152).

**Fix:** arm the flush from the restore. Found on the Mac before it reached hardware.

### The commit is right-to-left, and that is the whole mechanism

⛔ The trigger broadcasts `save` from its **right** outlet, every contributor answers during that
send, and only then does the **left** outlet write the file. **Reverse them and the file is always
one commit stale.**

**Fix:** `save` right, write left.

### `read -c` and `write -c` must match

⛔ A file written with `-c` and read back **without** it comes back as **one line** — `text size` 1 —
because Pd is hunting for semicolons that are not there.

**Fix:** `-c` on both. It is what keeps the file greppable *and* what makes it readable again.

### `[list append]` before the store is not decoration

⛔ It forces the selector to `list`, so a contributor whose key happened to be `write` or `load`
cannot be mistaken for a **command** by `u_store`. Without it the key namespace and the command
namespace are the same namespace.

**Fix:** `[list append]` between the bus and the store.

⚠️ The same trap one level down: `[text set]` and `[text search]` both answer a bare selector with
"no method for `mode`". A message box typed `mode compose mode-1` carries `mode` as its **selector**,
not as data. Seen twice in this repo — in `u_err` first, and again while building `u_store`.

### A `[text search]` miss reaches the wrong inlet as -1

⛔ `[moses]`'s **left** outlet carries the -1 rather than a bang (C-8). Without a `[t b]` it reaches
`[text set]`'s line-number inlet as -1 and Pd answers `line number (-1) < 0` — the exact bug `moses`
caused in `u_err`'s log.

**Fix:** `[t b]`, so a miss becomes `[text size]` instead — one past the end, which appends.

### The path is a creation argument captured into a `[symbol]`

⛔ **In a MESSAGE box `$1` is the incoming message, not the creation argument.** That trap has
already cost this project a silent MIDI port and a `soundfiler` write to a table called `0-a0`.

**Fix:** `[symbol $1]` in an *object* box holds the path, and the message box below substitutes it
in.

### Two files, because they have different lifecycles

⚠️ `[text write]` rewrites the **whole file** every time, so a shared file would let an auto flush
corrupt a committed take. Same split, same reason, as `u_err`'s `.cur` and `.log`.

## Design

### `u_state` owns the *when*, contributors own the *what*

Nothing in `u_state` names a key or knows what one means. A contributor sends `put auto <key> …` or
answers a `save` with `put manual <key> …`, and an abstraction written in v0.4 persists itself with
**no change to this file**. That is the whole point of the phase, and it is why the bus carries a
policy word rather than `u_state` holding a policy table.

### `u_store` is an abstraction because there are two of it

`auto` and `manual` are the same store with different write policies, and C-13 says anything you
would copy is an abstraction rather than a duplicated subpatch — **two copies are two codebases that
diverge silently.**

### The reject outlet is the normal path in `u_store`

`route` matches `write` and `load` by selector, and a list whose first atom is a symbol is neither —
so everything **to be stored** falls out of the reject. That is the normal path here rather than an
error path, which is the opposite of how a reject usually reads.

### Restore is manual first, auto second

A key should live in exactly one policy. **But if one ever appears in both, the last replay wins**,
and the running value is the more useful of the two.

### One fork per load, never per event

`state-dir.sh` runs once at load through `[shell]` — Phase 4's rule, and the same pattern as
`wire.sh` and `logroll.sh`. On the Mac `[shell]` is stubbed by `mac-stubs/shell.pd` and nothing is
created, which is why `main-dev.pd` passes a directory that already exists.

### The print is behind `[del 2000]`

`deploy.sh` gates on **output** and its syntax check quits at about 735 ms (C-9). The by-hand SSH
console still sees the line, which is where you look when the data directory is wrong.

### `[savestate]` was evaluated and not used

⚠️ **It is available in 0.49-0** — `savestate-help.pd` is present at tag `0.49-0` and absent at
`0.47-0`. A widely-repeated forum claim that it arrived in 0.49.1 is **wrong**; do not let it talk
you out of using it later.

But it writes into the **parent patch file** and needs a `menusave` that nothing on the device
triggers (item 145). It is **orthogonal** to the `state` bus rather than an alternative to it: it
saves per-*instance* parameters, which is a different problem from a keyed store.

### The instrument's data is not delivered by the Organelle's own save mechanism

`u_state` writes straight to `/sdcard` with an **absolute** path, so nothing it does has to finish
inside mother's sleep. What `Storage → Save` actually does — and the `saveState` bang, the sleep
budget and `knobs.txt` — is on [organelle.md](../device/organelle.md); the only part that reaches
this file is that `saveState` is what triggers a `manual` commit.

⛔ **`Storage → Save New` is dropped and is not part of this design.** It duplicates the entire patch
folder under a numbered name, making preset variants separate menu entries — the wrong paradigm here,
where a preset is a **record inside the store**. Recorded so it is not rediscovered as an option; see
[plan-v03.md](../../plan-v03.md) *Deliberately deferred*, and item 144 for what it does.

### A sample can be written inside mother's budget, but not unboundedly

`soundfiler` write, mono 44.1 kHz, into `/tmp/state` (item 142):

| Length | Cost |
|---|---|
| 2 s | 6.1 ms |
| 10 s | 29 ms |
| 30 s (2.6 MB) | 85 ms |

⚠️ **mother's own `cp` of 2.6 MB to the SD card costs 45 ms and is OUTSIDE the patch's budget**, so
the ceiling is roughly **3 × 30 s or 8 × 10 s** per save. `u_state` sidesteps this entirely by writing
absolute paths to `/sdcard`, but anything that ever writes into `/tmp/state` inherits it.

### Three decisions about captured patterns, made early on purpose

None of these is built. All three are cheap now and expensive later, which is why they are recorded
as decisions rather than left to whoever writes the capture.

1. **One device-agnostic event format.** Sources have wildly different shapes — the Launchpad is
   4×32 at 8-note poly, the keyboard is free-played. Capture everything as
   `time, note, velocity, duration` and **nothing downstream cares what authored it.**
2. ⛔ **Decouple the capture SOURCE from the playback DESTINATION.** Channel offsets tell you what a
   pattern was recorded *from*; that must not determine where it plays *to*. **Bake it in and you
   have permanently made something "a Launchpad pattern."**
3. **Plain text files** — `[text define]` + `[text write]`, git-diffable and editable outside Pd.

## Open

- ⬜ **Only one key is stored today.** `mode`, from `u_map`. The pattern store, the presets and the
  filter-stage parameters are v0.4, and each brings its own key and its own policy. See
  [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **Nothing uses the `manual` policy yet.** It is proven by the gate and by a deliberately-late
  test contributor, not by a real one. See [plan-v03.md](../../plan-v03.md) §4.
