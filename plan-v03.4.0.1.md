# Plan v0.3.4.0.1 — the suite you can run, and the first note path

**`./test/run.sh --all` cannot pass today, and the reasons have nothing to do with the patch.** Two
defects in the runner make a working rig report failures: one auto-fails four steps of the `midi`
bench, and one fires every non-hands step before a person can finish reading what to look at. Until
both are fixed, the bench half of this project's test suite is unrunnable by the person it was
built for.

This plan fixes those, runs the whole suite for the first time, and then builds **the instrument's
first note path** — the Organelle's own keyboard playing the Volca, mode-dependent, meant to be
played live.

⚠️ **Everything here came out of one hands-on rig session on 2026-08-10**, the same session that
finished Phase 6 of the hot-swap work. The facts that session produced are on `ref/` pages as items
281–288; what is left open is below.

---

## ⚠️ Constraints that bind everything

- **Pd vanilla 0.49, permanently.** The Organelle 1 is the end of its line.
- ⛔ **Never open or save an Organelle-bound patch in plugdata.**
- **Vanilla objects only** — no ELSE, no cyclone.
- **Commit as you go**, in reviewable batches. ⛔ **Brendan is the sole author: no `Co-Authored-By`
  trailer and no agent byline.**
- ⚠️ **Read `./test/run.sh`'s `RESULT:` line; never grep for it.** `grep -E 'ALL|FAILED'` also matches
  the per-gate `--- FAILED:` lines, and a broken patch has been committed that way.
- ⛔ **A GATE IS NOT TRUSTED UNTIL IT HAS FAILED.**
- ⛔ **Part 3 is the only thing here that touches `Cut It/`.** Parts 1 and 2 are test tooling and a
  hands-on run; nothing deployable changes until the binding.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`gate`** skill | ⛔ **Invoked, not read** | Part 1 and Part 2 are tests |
| The **`pd`** skill | ⛔ **Invoked, not read** | Part 3 edits three abstractions |
| The **`docs`** skill | ⛔ **Invoked, not read** | Part 3 adds facts to three pages |
| `test/runner/run.py` | `run_bench`, `run_bench_driven`, `describe` | **Both Part 1 defects live in those three** |
| `test/runner/predicates.py` | `_one`, and the `KINDS` list | What a predicate can read, and what it does with an empty window |
| [test/README.md](test/README.md) | *Running everything*, *Nine steps judge themselves*, *Results and freshness* | The runner's contract with a person |
| [ref/module/map.md](ref/module/map.md) | **All of it** | ⛔ **The single most important page for Part 3.** The row format, the destination allowlist, and the one-value rule that shapes the whole design |
| [ref/device/volca.md](ref/device/volca.md) | *Receives*, *Presence*, and every **Trap** | It transmits nothing, so every claim about it is weak evidence — and three traps here were written the day this plan was |
| [ref/device/organelle.md](ref/device/organelle.md) | The keyboard, and what mother sends | `m_organelle` deliberately omits the keyboard and says why |
| `Cut It/u_mother-stub.pd` | The keyboard subpatch only | ⛔ **It already fakes the keyboard**, which is what makes Part 3 gateable with no hardware |
| `Cut It/m_volca.pd` | **All of it, comments included** | One selector-prefixed inlet, and `makenote` is a safety property you are about to bypass |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only what it links | `C-1`…`C-14` |
| `git log` | **Grep it, never read it** | This project's only journal |

**Do not read** `Cut It/g_oled.pd`, `Cut It/u_net.pd`, `Cut It/u_present.pd`, or any `plan-` document
other than this one. The hot-swap work is finished and its facts are on
[ref/module/presence.md](ref/module/presence.md).

---

## Part 1 — the two defects that block a green `--all`

### ⬜ A `bus` predicate in a `paper` bench auto-fails

`run.py`'s paper-mode branch evaluates a predicate against an **empty window**, so `_bus_lines`
returns nothing and the step reports **AUTO FAIL**. `pick_target` sends `midi` to `paper` because
every one of its steps has no actions — and `midi` carries **four** bus predicates.

**So a bare `./test/run.sh --all` fails four steps on a working rig.** Every recorded midi run in
`test/results/runs/` used `--target device`, which is why this has never been hit.

**Fix:** a predicate whose oracle is absent is a **skip with a reason**, never a fail — the rule the
runner already applies to `targets` and to `--auto-only`. Paper mode keeps `file` predicates, which
read the disk and need no console, and skips the rest saying which and why.

⚠️ **That leaves `midi` unable to reach a clean PASS in paper mode, and that is honest** — four of its
steps genuinely cannot be judged without a patch running. ⛔ **Do not "fix" it by making `midi`
non-paper**: `paper` is what lets `state` and `midi` run with no Pd, no ssh, and therefore no
Launchpad stranded in Programmer Mode.

### ⬜ Non-hands steps fire before a person can read them

`run_bench_driven` guards its `press enter when you are ready` prompt with `if step.hands and not
auto_only`. A step carrying a `do` waits for you; **every other step calls `src.go()` on the line
after `describe()` prints its `watch` text.**

`STEPS_LAUNCHPAD` steps 1–17 are all non-hands and all visual, so the thing you are told to look at
has already happened by the time you finish the sentence telling you to look at it.

⚠️ **This is the exact failure the manual-stepping rewrite existed to remove.** [test/README.md](test/README.md)
says the old timer-driven shape *"put the console text and the physical device in motion at the same
moment, so you could read one or watch the other and not both."* The fix reached hands steps only,
and nobody noticed because hands steps are the ones anybody tested by hand.

**Fix:** the prompt is unconditional whenever a person is present — drop `step.hands` from the guard
and keep `not auto_only`. A step that requires nothing to be *done* still requires to be *read*.

⛔ **`test/gate/runner-assert.sh` is the can-it-fail harness for both of these** — 58 checks, replay
fixtures that drive this exact loop, and the only thing that ever exercises the runner's failure
paths. Any fixture encoding the old prompt behaviour is updated **deliberately, never to make a red
run green**.

---

## Part 2 — run the whole suite, gates and benches

The gate half is green at **410 checks**. The bench half has never been run through the runner at all.

⚠️ **`test/results/latest.json` holds `{"records": {}}`** — not one bench verdict has ever been
recorded, so every step reads `never run`. This is also the first real exercise of the freshness
machinery: the per-bench dependency sha, the 30-day window, and the title/`pass_if` hash.

| Bench | Steps | Note |
|---|---|---|
| `launchpad` | 25 | ⛔ Includes the two hot-swap steps added 2026-08-10 — **never run**, and they need eyes on the grid |
| `midi` | 17 | ⛔ The Volca's two steps were **rewritten after** the rig session and have never been executed as written |
| `nanokontrol` | 19 | Two hot-swap steps, verified by hand over `ssh` but never through the runner |
| `display` `tempo` `phone` `state` | 14 / 15 / 14 / 5 | Never run through the runner |

⚠️ **The `midi` bench needs `--target device` until Part 1 lands.**

---

## Part 3 — the Organelle's keyboard plays the Volca

⛔ **This is a real performance binding**, played live in certain modes. That rules out fixed velocity,
a fixed duration, and anything that skips the map.

### What already exists

- mother publishes the physical keyboard on **`s notes`** as a two-float list — **pitch then
  velocity**. The Organelle's lowest key is **note 60**, so the 25 keys are **60–84**. Release is
  **velocity 0**.
- ⛔ **`Cut It/u_mother-stub.pd` already fakes it.** The dev panel's 25-cell radio *is* the keyboard
  (`$0-key + 60`, velocity defaulting to 100, and an all-off that walks 25 keys at velocity 0).
  **The whole path is gateable headlessly, note-on and note-off, before the Organelle is powered.**
- `Cut It/m_volca.pd` takes **one selector-prefixed inlet**: `notes <note> <vel> <dur>`, `cc`,
  `program`.
- `Cut It/m_organelle.pd` deliberately omits the keyboard, and its own comment says why: *"none of
  the others has anything to drive yet. They belong in THIS file when they do."* This is the when.

### ⛔ Why the existing `volca-note` destination cannot do it

[ref/module/map.md](ref/module/map.md) is explicit:

| Destination | `<arg>` means | Value means |
|---|---|---|
| `volca-note` | **The note number** | **Velocity.** Duration is a fixed **200 ms** |

**Both halves are wrong for a keyboard.** The row supplies the pitch — fixed, one per row — but on a
keyboard the *key* is the pitch. And a fixed 200 ms duration means **a held key releases itself**.

⚠️ **The map carries exactly one value per control, normalised 0–1**, and every destination, the
divisor table and the whole of parameter pickup rest on that. A note needs pitch, velocity **and** a
release.

### The shape

**One control per key, and one new destination.**

- `m_organelle` gains a keyboard decode publishing **`og-key-60` … `og-key-84`** on `param`, each
  carrying its own velocity as the value. 25 distinct control names is what the one-value rule wants,
  and it makes *"these eight keys play the Volca and those two fire 404 pads"* expressible.
- A new destination **`volca-key`**: `<arg>` is the note number, exactly like `volca-note`, but the
  handler emits a real **note-on / note-off** pair — value above zero is a note-on at that velocity,
  value zero is a note-off.
- `m_volca` gains a **`note`** selector beside `notes`, bypassing `makenote`.
- Map rows in `Cut It/cut-it-map.txt`: 25 per mode you want it in.

⛔ **`makenote` is a safety property and bypassing it costs something.** `m_volca`'s own comment:
*"makenote owns the note-offs, which is what stops a dropped cord or a reload leaving the Volca
droning."* A real note path reintroduces that risk, so it ships with **panic → All Notes Off (CC
123)**, which the device supports and which `m_404` already has a precedent for.

⚠️ **`notes` is one of mother's names, not a C-2 allowlist name.** Reading it in `m_organelle` is the
same legitimate move `lib_drive.TAP_LABELS` documents for `led` and `oscOut`. **State it in the patch
comment** so nobody "fixes" it.

⚠️ **25 rows per mode is the visible cost**, against 13 rows in the whole map today.

### Three things already enforce this, and none needs writing

- ⛔ **[ref/module/map.md](ref/module/map.md)'s destination table is anchored to the literal `route`
  box.** Adding `volca-key` to `u_map` without documenting what its `<arg>` and value mean **fails
  `test/gate/docs-check.py`**.
- **`test/gate/map-assert.py`'s static lint** proves every destination a row names exists on that
  route, and catches a **duplicate `(mode, control)` pair** — which `text search` resolves to the
  first match only, so a repeat is dead and silent. With 25 near-identical rows per mode that check
  stops being theoretical.
- **`u_mother-stub`'s 25-cell radio** drives the path with no hardware, so the gate asserts note-on
  *and* note-off before anything is deployed.

⚠️ **Part 3 will hit the `none`-device gap below** the first time the rig boots with the Volca's
interface unplugged.

---

## The smaller items

⬜ **The error log's timestamps rot after 16 minutes 40 seconds.** `u_err` stamps each line from
`[timer]` — milliseconds as a float — and `[text]` writes floats with `%g`, which caps at six
significant figures. Observed both sides: `387600` exact, `2104000` written as `2.104e+06`. That is
1-second precision in the second hour and 10-second beyond about three. **The log is the only record
of when anything happened on this instrument, and a set runs for hours.** Fix: `makefilename` on the
stamp so `[text]` stores a symbol it cannot reformat, or log tenths of a second, which stays exact
for eleven days. ⛔ It changes the log format, so `test/gate/err-assert.sh` moves with it.

⬜ **Step numbers are written inside step text.** Four `need` lines in `test/bench/bench_steps.py` say
*"resume this bench with `--from 22`"*. Insert one step above them and every number is silently
wrong. Self-inflicted on 2026-08-10. **A lint asserting each `--from N` matches its own step's index**
is a few lines and belongs beside the vacuity lint in `bench-gen.py`.

⬜ **The stall has no diagnostics.** Reported once on the launchpad bench, never reproduced — the
identical sequence fires in 0.01 s, the bench announces step 1 at 627 ms, and the device console runs
at ~98 lines/s. A stall that cannot be reproduced and says nothing about *why* should report whether
GO was sent, what the last lines seen were, and how far behind the queue had fallen.

⬜ **A `none` device absent at load is unreachable forever** — item 285. Nothing is lost, so
`u_present`'s spigot stays shut, the counter never starts, and no `wire.sh` fork is ever scheduled.
Measured: enumerated in under a second, **zero subscriptions two minutes later**, empty error log.
Candidates — a manual re-wire control, `wire.sh` on a slow heartbeat, or surface it and accept it.
⚠️ **The remedy today is a reload**, or unplugging a detectable device to trick the recovery into
running, which nobody would guess.

⬜ **The recovery is invisible on the instrument.** Eight `wire.sh` attempts happen in total silence;
only the give-up reaches `err`. It is why a trailing fork could not be told from a scheduled one on
the hardware. See [plan-v03.5.md](plan-v03.5.md), whose diagnostic screen is the consumer.

---

## Verification

```sh
./test/run.sh                        # ⚠️ read the RESULT: line -- never grep for it
./test/run.sh --all                  # gates then benches -- the point of Part 1
./test/gate/runner-assert.sh         # 58 checks -- Part 1's harness
python3 test/gate/docs-check.py -v
python3 test/bench/bench-verify.py
./tools/deploy.sh                    # Part 3 only
```

⚠️ **One run at a time.** The suite takes ~5 minutes and only about a minute of that is computation —
the rest is Pd running DSP in real time. Six were once stacked here by accident and two "failures"
were nothing but the cleanup kill.

⛔ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.

---

## Done means

1. `./test/run.sh --all` passes, or every non-pass is a **skip with a stated reason**.
2. A person can run a bench and **read each step before it fires**.
3. Every bench has been run once and its verdicts are in `test/results/latest.json`.
4. The Organelle's keyboard plays the Volca in at least one mode, with real note-offs, a panic that
   silences it, and a gate that proves both without hardware.
5. The five `⬜` above are closed or have moved to [plan-v04.md](plan-v04.md) §3 with a reason.
6. **This file is deleted**, and its entry in [CLAUDE.md](CLAUDE.md)'s plan table goes with it.

⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**
