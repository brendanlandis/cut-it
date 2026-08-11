# Plan v0.3.4.1 — panic becomes RECOVER

**Panic's job is not silence.** The mixer's master fader is faster, analogue, and does not depend on
the thing that is misbehaving. Panic's job is **recovery**: silence what is sounding, then reload the
patch, so every device is re-enumerated into Pd and `wire.sh` runs fresh.

**Decided 2026-08-08 with the rig in front of us.** A spur off the hot-swap work, which built the
presence model and landed on 2026-08-10 — see [ref/module/presence.md](ref/module/presence.md). This
is the half that recovers what presence cannot.

---

## ⛔ Why this is NOT redundant now that item 235 is closed

The original text justified this phase as *"closing item 235 the blunt way"* — a brute-force reload
covering the absent-at-load case. **That reason is gone.** Item 235 is fixed properly and verified on
hardware 2026-08-10: a Launchpad that was absent when the patch loaded now recovers on its own, and
comes back re-enumerated, in Programmer Mode, owned and painting.

**The reason that replaces it is stronger, and it is a measurement rather than an argument:**

⛔ **A reload is the only recovery that exists for a device nothing can detect.** `m_volca` registers
`none` because the Volca transmits nothing at all, so it can never be polled, never be declared lost,
and never trigger a re-wire. Its recovery is **parasitic** — it only comes back if a *detectable*
device happened to be missing at the same moment. And on 2026-08-10 that failed in exactly the way
the design allows: pulling the Volca's interface also knocked the SP-404 off the shared USB bus, the
404 answered first, the counter reset, and the Volca sat unreachable until `wire.sh` was run by hand.
Item 275. A trailing fork now narrows that window; **it does not close it.**

So: presence handles every device that can answer for itself, and `recover` is what you reach for
when something cannot — or when the patch itself is wedged and no amount of polling helps. See
[ref/module/presence.md](ref/module/presence.md) and [ref/device/volca.md](ref/device/volca.md).

⚠️ **The Volca-blurt caveat that briefly attached to this phase is WITHDRAWN, not pending.** It was
written when a reload looked like it made the Volca sound three times in four; nine subsequent loads
produced nothing, including one staged immediately after re-enumerating the interface. Do not
reinstate it. The full account is on [ref/device/volca.md](ref/device/volca.md).

---

## ✅ Already decided — do not reopen these

| Decision | |
|---|---|
| **The control is the Launchpad's top-left corner, CC 90** | A verified real button on this unit, absent from Novation's documentation, currently unused, and `g_grid` can light it so the armed state is visible |
| **Two tiers on that one control** | Short press → `panic`, silence only, always safe. Held → `recover`, silence **then** reload |
| **The reload path SKIPS parameter pickup arming** | After an emergency the knobs you are holding are the truth. See *The breadcrumb does double duty* below |
| ✅ **The destructive half is already gone** — item 251 | Panic no longer hands the Launchpad back. That was a bug: it killed the grid until reload and buried Pd's Midi-In 1 under a clock flood (item 250). Both gates were inverted deliberately and made to fail against the old code, and **`launchpad` 24 to 26 confirmed it on the rig on 2026-08-11** — the surface kept, the grid still answering, pads still reaching the OLED |

⚠️ **The page does not yet say what CC 90 does, and the question that used to hold the space is
gone.** *Which control raises panic* left [ref/device/launchpad.md](ref/device/launchpad.md)'s
`Open` section when panic stopped being destructive, and nothing replaced it — so the page documents
CC 90 as a real undocumented button (item 82) and says nothing about Cut It binding it. **Two tiers
on one button is what belongs there**, under `Design`.

---

## ⚠️ Constraints

- **Pd vanilla 0.49, permanently.** Vanilla objects only.
- ⛔ **This edits the file holding the Launchpad's safe exit**, which is the one message in this patch
  worth more than everything around it. It gets **its own can-it-fail test** rather than being bolted
  onto the end of another change.
- ⛔ **Never open or save an Organelle-bound patch in plugdata.**
- **Commit as you go.** ⛔ Brendan is the sole author: no `Co-Authored-By` trailer, no agent byline.

---

## ⛔ What this costs the bench half, and how to spend it once

**All seven benches are fresh as of 2026-08-11** — one hundred steps, every one judged by a person at
the rig. ⚠️ **This plan stales thirty-six of them**, and nothing will stop you or warn you:

| You edit | Stales | Because |
|---|---|---|
| `Cut It/u_map.pd` | `midi` 18, `tempo` 13 | both name it in `DEPS` (`test/runner/steps.py`) |
| `Cut It/u_init.pd` | `state` 5 | same |
| `Cut It/cut-it-map.txt` | `midi` 18 | same |

**So the rig session at the end of this is not optional and it is not small.** Budget for re-running
`midi`, `tempo` and `state` in full, and read
`python3 test/runner/run.py --list` before and after so the number is a fact rather than a memory.

⛔ **Two other pieces of work touch `u_map.pd`, and doing them apart pays this bill twice.** Land
them in the same pass:

- [plan-v04.md](plan-v04.md) §3's ⬜ **`u_map` accepts a `mode` it cannot use** — the key-setter
  refusing a `mode` that is not two atoms. It was blocked until every bench was fresh; it no longer
  is. Its gate is the interesting half, since nothing yet drives a malformed mode through the restore.
- This plan's own `route` box change and the six `lp-cc-90` rows.

⚠️ **Adding a bench STEP costs nothing** — `step_sha` is the title and the `pass_if`, so a new step
leaves every existing verdict fresh even though every step's `of` count changes in the `.pd`.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** skill | ⛔ **Invoked, not read** | You are editing shipped Pd |
| The **`gate`** skill | ⛔ **Invoked, not read** | The safe exit needs its own failing test |
| `Cut It/u_init.pd` | **All of it** | It owns `[shell]`, the boot sequence, and therefore the reload |
| `Cut It/u_map.pd` | The literal `route` box, and the no-save arming probe | `recover` needs a literal destination; the breadcrumb changes how arming is decided |
| `Cut It/cut-it-map.txt` | All of it | Six new rows, one per mode |
| [ref/module/map.md](ref/module/map.md) | `Facts`, and item 239 | Parameter pickup, which this path deliberately skips |
| [ref/device/launchpad.md](ref/device/launchpad.md) | The safe exit section, items 250 / 251, and CC 90 under `Facts` (item 82) | What panic may and may not do to this device, and the button you are binding |
| [ref/conventions.md](ref/conventions.md) | Item 252 only | ⛔ `/loadPatch` runs `killpatch.sh` first, so `quitting` **does** fire on this path — verified on hardware 2026-08-10. It is defined here and on [ref/device-os.md](ref/device-os.md), not on the Launchpad's page |
| [test/README.md](test/README.md) | *The benches*, and everything under it | You are adding bench steps, and its `wait` section carries what two rig sessions cost to learn |
| [ref/module/state.md](ref/module/state.md) | The file format and the data directory | The breadcrumb is written beside the state files, outside the patch folder |
| `tools/deploy.sh` | Its `/reloadNoRemount` and `/loadPatch` calls | The two-step OSC, and the comment saying why a bare name loads nothing |
| [ref/module/presence.md](ref/module/presence.md) | *Design*, and the `none` kind | Why this phase exists at all |

**Do not read** `Cut It/g_oled.pd`, `Cut It/u_net.pd`, or the five `m_` device layers.

---

## The build

### 1. The control, and the two tiers

Six rows in `Cut It/cut-it-map.txt` for `lp-cc-90`, one per mode, and **`recover` added as a literal
argument to `u_map`'s `route` box**. ⛔ **The allowlist guard is the whole of what makes a table
acceptable** — the table never names a `[send]`, it names a destination that must exist as a literal
on a route box feeding a handler you can see. Skipping it costs nothing visible, which is exactly why
it must not be skipped.

The hold test lives in `u_map` beside the other trigger tests: press starts a `[del]`, release before
it cancels, and only the timer's completion reaches `recover`. **Tier 2 fires `panic` first**, then
its own path.

### 2. The reload, in `u_init`

1. ⛔ **Silence lands BEFORE the reload.** Killing Pd mid-note never sends the note-off, so the 404
   holds it — a panic that *creates* a stuck note. Sequence `panic` (which already reaches `m_404`'s
   all-notes-off loop, `m_volca`'s `makenote` and `u_tempo`'s `252` STOP), then fire the reload behind
   a short `[del]`.
2. ⛔ **The two-step OSC, or it silently does nothing.** `oscsend localhost 4001 /reloadNoRemount i 1`
   **then** `/loadPatch s '!/Cut It'`. A bare name loads nothing at all and says nothing.
3. ⚠️ **It breaks Phase 4's one-fork-per-load rule.** Defensibly — a panic is rare, user-initiated and
   ends the patch — **but it must say so in a comment**, the way `u_present`'s bound and its trailing
   fork already do.

### 3. ⛔ Design for the failure, because it is worse than the fault

If the load does not take there is **no patch at all**, and the patch cannot verify its own reload
because it is dead by then. Item 243's shape exactly.

**Write a breadcrumb to `/sdcard/cut-it-state/` before firing**, so the *next* boot can say *"a
recover was attempted at frame N"* on the OLED. A recover that never completed is then visible after
the fact instead of being a silent brick.

### 4. The breadcrumb does double duty

`u_map`'s no-save probe already decides arming by reading `knobs.txt` synchronously with `text size`.
**Add a second read of the breadcrumb**: when it is present, write every slot straight to **4, LIVE**
and delete it. After an emergency the knobs you are holding are the truth. Record it on
[ref/module/map.md](ref/module/map.md) beside item 239.

---

## Testing it honestly

⚠️ **Its core is untestable on the Mac.** `[shell]` is stubbed, so a gate can assert:

- the **silence sequence** happens, and happens **strictly before** the reload message
- **both OSC commands are well formed and in the right order** — `t_shell.pd` prints the command, so
  the two-step is fully assertable as text
- the breadcrumb is written before the reload fires
- ⛔ **`quitting` still fires**, because `/loadPatch` runs `killpatch.sh` first (item 252), so the
  Launchpad's safe exit still runs on this path

**It can never assert that the reload happened.** ⛔ **Say so in the gate's header** rather than
implying coverage that does not exist.

⛔ **A gate is not trusted until it has failed.** Reintroduce each fault — reversed ordering, a bare
`/loadPatch` name, a missing breadcrumb — and watch the right check go red, one at a time.

---

## Verification, on hardware

⛔ **THESE ARE BENCH STEPS, NOT A CHECKLIST.** This project's standard for a hardware claim is a
recorded verdict in `test/results/latest.json` against a known `step_sha` — that is what makes *"when
did this last pass, and against what code?"* a `git log` question. A list of things to try by hand
leaves nothing behind. **Add them to `STEPS_LAUNCHPAD` in `test/bench/bench_steps.py`**, since CC 90
is a Launchpad control, and regenerate:

```sh
python3 test/bench/bench-gen.py && python3 test/bench/bench-verify.py
```

| | The step |
|---|---|
| 1 | **Short-press CC 90** — everything goes quiet, the patch is still running, the grid is still lit |
| 2 | **Hold CC 90** — silence, then the patch reloads and comes back with every device re-enumerated |
| 3 | **The knobs are live immediately**, not held |
| 4 | ⛔ **Break it deliberately** — rename the patch folder, hold CC 90, and the breadcrumb explains what happened on the next manual load |
| 5 | **The safe exit still works** — the Launchpad returns to Live Mode and its Setup button responds |

⚠️ **Do 5 through `/loadPatch`, never `killall pd`**: `quitting` comes from mother rather than from a
shell signal, which is the entire reason `tools/lp-live.sh` exists. That script rescues a stranded
Launchpad if anything goes wrong, but the point is that it should not be needed.

⛔ **Three things about writing these that cost two rig sessions each to learn**, all of them in
[test/README.md](test/README.md) under *The benches* — read it rather than rediscovering them:

- **A predicate whose traffic a PERSON makes needs `press enter first` AND a `wait`.** The window
  opens at GO and closes 0.4 s later by default, which is shut before a hand has crossed the desk.
  Steps 2 and 4 here both need one.
- **Anything late and brief has to say where to look and when.** A step judged by eye against a
  ~2 s alert that fires seconds after the action is unjudgeable unless it says so.
- **A step sets up its own preconditions, and a mode is one.** Step 4 leaves the rig with no patch;
  whatever follows it must not assume otherwise.

---

## Done means

1. CC 90 raises `panic` on a short press and `recover` on a hold, in all six modes.
2. The reload is the two-step OSC, in order, behind the silence.
3. The breadcrumb is written before the reload and read on the next boot.
4. The reload path skips parameter pickup arming.
5. `quitting` still fires and the Launchpad still returns to Live Mode — **asserted**, not assumed.
6. `ref/device/launchpad.md` says under `Design` what Cut It binds CC 90 to, and what each tier does.
7. **The five verification steps are in `STEPS_LAUNCHPAD` and hold fresh passes** in
   `test/results/latest.json`.
8. **`midi`, `tempo` and `state` are fresh again** — `python3 test/runner/run.py --list` shows seven
   benches fully fresh, as it did before this plan started.
9. `./test/run.sh` reports `RESULT: PASS`. ⚠️ Read that line; never grep for it.
10. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.**
