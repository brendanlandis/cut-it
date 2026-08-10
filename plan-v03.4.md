# Plan v0.3.4 — hot-swap

**Unplug anything but the Launchpad and it never comes back.** A replug destroys the ALSA
subscriptions outright, nothing in the patch notices, and the only remedy is a reload. Even the
Launchpad — the one device with a recovery path — **cannot recover if it was absent when the patch
loaded**, because "lost" was built as a transition from present to absent, and never-present is not a
transition.

This plan gives every device that *can* be detected a presence model, makes the bounded re-wire
serve all of them, and closes item 235.

✅ **The two measurements it was blocked on are in** — item 249, 2026-08-08: **all three devices
answer a universal device inquiry**, so every one of them gets *active* polling rather than passive
last-heard detection. ✅ **The `ctlin` stub it was waiting on landed 2026-08-09** —
`test/stubs/t_ctlin.pd`, with `test/gate/nano-assert.sh` already built on it. **Nothing blocks this
plan.**

---

## ⛔ STATUS — most of this plan has LANDED

**Phases 1, 2, 3, 4 and 5 are built, gated, and verified on the hardware 2026-08-10.** Everything
below them is kept for its reasoning only: the facts they produced live on
[ref/module/presence.md](ref/module/presence.md) and the work is in `git log`.

**What remains, and this is all of it:**

| Remaining | State |
|---|---|
| Phase 6 — the eight bench steps | not started |
| Phase 6 — ✅ the headless gate, including the trailing fork | **done** — 21 checks, falsified five ways. Do not rebuild it |
| Phase 6 — the bound asserted by **reaching** it, on a scratch-scaled tick with the counts as shipped | not started |
| Verification — the SP-404 and the Volca never got their own transition runs | the shared machinery beneath both is verified |
| Panic becomes `recover` | **moved out** to [plan-v03.4.1.md](plan-v03.4.1.md) — it is independent of everything here and this file should not wait on it |

**Two claims in this plan turned out FALSE on hardware, and both are corrected in the `ref/` pages
rather than in the prose below:**

- ⛔ *"`wire.sh` itself does not change — no connect or disconnect line moves"*, listed here as
  removing the plan's largest documentation hazard. **The nanoKONTROL had no inbound connection at
  all**, because nothing had ever sent to it, so its device inquiry went into an unconnected port
  forever. One line added; six links became seven. Item 274.
- ⛔ *A bound recovery is enough.* It stopped the instant the last **detectable** device answered,
  which is not the same as the rig being whole — and it stranded the Volca. One trailing fork now
  runs on the transition to nothing-lost. Item 275.

⚠️ **Neither was findable on the Mac.** `[midiout]` and `[sysexin]` are both stubs there, and all 19
gates passed either way.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.**
- ⛔ **Never open or save an Organelle-bound patch in plugdata.**
- **Vanilla objects only.**
- **Commit as you go**, in reviewable batches — a plan's phases are good commit boundaries.
  ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.**
- ⛔ **A GATE IS NOT TRUSTED UNTIL IT HAS FAILED.**
- ⛔ **This plan edits the file that holds the safe exit.** `m_launchpad`'s Live Mode message on
  `quitting` is the one message in this patch worth more than everything around it — a patch that
  dies without sending it strands the device in Programmer Mode. **Every change near it wants its own
  can-it-fail test rather than being bolted onto the end of another change.**

---

## What to read, and how much

⚠️ **This list was rewritten once the first five phases landed.** It is aimed at the three pieces
that are actually left, not at the work that produced them.

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** skill | ⛔ **Invoked, not read** | You are editing tests, and `u_present` if a falsification needs it |
| The **`gate`** skill | ⛔ **Invoked, not read** | Two of the three pieces are tests |
| [ref/module/presence.md](ref/module/presence.md) | **All of it** | ⛔ **The single most important page here.** What was built, what was measured on the hardware, and the four traps. Do not re-derive any of it |
| [plan-v04.md](plan-v04.md) | §3's *What plan-v03.4 still owns* | The index of these three pieces. ⚠️ Its *Launchpad watchdog* section is **gone** — that work landed |
| `test/gate/presence-assert.sh`, `.py`, `-drive-gen.py` | **All three** | You are extending them. The driver's schedule is `u_present`'s arithmetic and the windows straddle events deliberately |
| `test/gate/lib-scratch.sh` | `scratch_state_dir` and `MIDI_EXPECT` | `scratch_scale_present` goes in beside the first, in the same shape |
| `Cut It/u_present.pd` | **All of it, comments included** | The bound, the coalescing and the trailing fork all live here, and each carries the reasoning for its own number |
| `test/bench/bench_steps.py` | ⛔ **ONE `STEPS_` block, for the shape** | It is 50 KB. Reading all of it is a waste of a context window |
| `test/bench/bench-gen.py` | The `BENCHES` dict only | Keyed by output filename; `bench-verify.py` derives its own list from those keys |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only what it links | `C-1`…`C-14` |
| `git log` | **Grep it, never read it** | Git is this project's only journal |

**Do not read** `Cut It/g_oled.pd` (783 lines), `Cut It/u_net.pd`, the five `m_` device layers — they
are finished — or any other `ref/module/` page.

---

## What is already true

- **`wire.sh` connects seven ALSA links by name**, each with `2>/dev/null || true`, so a device that is
  not plugged in cannot stop the ones that are. It then **undoes mother's own auto-connect**, which
  wires the lowest-numbered MIDI client to Pd's Midi-In 1.
- ⛔ **Loading any patch drops Pd's ALSA connections** (item 228). The Pd *process* survives a patch
  swap; its port connections do not. **That is why `u_init` runs `wire.sh` on every load.**
- **`wire.sh` is idempotent, costs 133 ms, and ten back-to-back forks produced no audio complaint** —
  all measured. That is why the watchdog is allowed to fork at all.
- **`wire.sh` reports a connection count**, which is *"the only way to know from the patch side
  whether anything answered"* — but it counts **all** connections in the system, not the ones it
  made.
- **The Launchpad watchdog has two mechanisms because the two platforms fail differently.** On the
  Mac a replug cannot be detected by polling at all — the device answers a device inquiry in *either*
  mode — so a 2 s heartbeat re-asserts Programmer Mode instead. On the device the replug destroys the
  subscriptions, so a poll detects loss and a bounded re-wire fixes it.
- **`want` is not `own`.** A panic clears `want`, so the watchdog goes silent rather than fighting it.
- **`u_net` has its own link watchdog**, but it detects the **socket**, not a device.

---

## Phase 6 — what is left to build

### ✅ The headless gate exists — do not rebuild it

`test/gate/presence-assert.sh`, **21 checks, ~38 s**. What it covers is on
[ref/module/presence.md](ref/module/presence.md). It has been falsified five ways: a matcher
accepting every byte, a layer that stops registering, the arming gate welded shut, the interval
shortened, and the trailing-fork cord cut. **Each goes red in its own place.**

⚠️ **Read its driver before adding a window.** The schedule is `u_present`'s own arithmetic and the
windows straddle the events rather than sitting after them, deliberately — a gate that only looked at
the end could not tell *fires on the fourth tick* from *fires on every tick*.

### ⬜ The bound, asserted by REACHING it

The one claim the gate still makes by arithmetic. `u_present` takes the settle, the tick and the
give-up as creation arguments **precisely so a scratch copy can scale the two TIMES and leave the
COUNTS as shipped**.

Add `scratch_scale_present` to `test/gate/lib-scratch.sh`, in the shape of `scratch_state_dir` — a
`sed -i ''` on the scratch `u_root.pd` **with the grep guard that asserts the rewrite landed**:

```
u_present 4000 2000 33   ->   u_present 400 200 33
```

⛔ **Only the settle and the tick move. 3 and 33 are the shipped counts**, and a gate that scaled
those would be asserting a different patch.

| At | What happens |
|---|---|
| 400 ms | settle expires; `[metro 200]` starts and fires immediately, so ticks are 400, 600, 800 … |
| 800 ms | third missed tick — every active source lost, recovery counter starts on the same tick |
| 1400 ms | counter 4, the first fork |
| every 800 ms | forks 2 through 8 |
| 7000 ms | counter 32, the eighth and last |
| 7200 ms | counter 33 — `fail u_present rewire-gaveup` |

So a **second Pd run of about 9 s**, alongside the existing one. Assertions, counts exact:

- exactly **8** recovery forks, on top of `u_init`'s boot one
- the give-up reaches `err` exactly **once**
- **zero** forks after it — the bound stops it dead rather than slowing it down

⚠️ **Falsify it with `[moses 33]` → `[moses 9]`**: the give-up arrives early and the fork count
collapses. Both checks must go red, and from one edit.

### ⬜ The eight bench steps

⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py`, then `python3
test/bench/bench-gen.py`, then `python3 test/bench/bench-verify.py`.

⚠️ **Step text takes no `,` `;` or `$`, and a digit followed by a full stop becomes a float.** The
text below is already written to those rules and can be pasted.

Two cases per device, because item 235 is the proof they are not the same test.

| # | Table | need | do | watch |
|---|---|---|---|---|
| 1 | `STEPS_LAUNCHPAD` | the Launchpad connected and the grid lit | unplug the Launchpad USB and leave it out | PASS IF the OLED shows a warn for m_launchpad within 10 seconds and the grid goes dark |
| 2 | `STEPS_LAUNCHPAD` | start with the Launchpad UNPLUGGED and the patch freshly loaded | plug the Launchpad in and wait up to 60 seconds without touching anything else | PASS IF the grid lights and the top row shows one green lamp |
| 3 | `STEPS_NANOKONTROL` | the nanoKONTROL connected | unplug the nanoKONTROL and leave it out | PASS IF the OLED shows a warn for m_nano within 10 seconds |
| 4 | `STEPS_NANOKONTROL` | start with the nanoKONTROL UNPLUGGED and the patch freshly loaded | plug it in and wait 60 seconds then move slider 1 | PASS IF slider 1 moves a value on the OLED |
| 5 | `STEPS_MIDI` | the SP-404 connected | unplug the SP-404 and leave it out | PASS IF the OLED shows a warn for m_404 within 10 seconds |
| 6 | `STEPS_MIDI` | start with the SP-404 UNPLUGGED and the patch freshly loaded | plug it in and wait 60 seconds then press pad 1 | PASS IF the OLED shows an sp-pad row |
| 7 | `STEPS_MIDI` | the Volca sounding and its USB interface connected | unplug the Volca interface AND the nanoKONTROL together then plug both back in | PASS IF the Volca can be played again within 60 seconds — BY EAR |
| 8 | `STEPS_MIDI` | start with the Volca interface UNPLUGGED and the patch freshly loaded | plug it in and wait 60 seconds then play the Volca | PASS IF the Volca sounds — BY EAR |

**Three things in that table are corrections that came out of the hardware session, and none of them
were in this plan's first draft:**

- ⛔ **Step 7 unplugs the nanoKONTROL as well, and it has to.** The Volca registers `none`, so pulling
  it alone loses nothing, forks nothing and recovers nothing — its recovery is **parasitic** on a
  detectable device being missing at the same moment. A step that unplugged only the Volca would fail
  for a reason that has nothing to do with what it tests. See
  [ref/device/volca.md](ref/device/volca.md).
- ⚠️ **The deadlines are 60 seconds and not 10.** A replug is routinely missed by the *first* re-wire
  because the device is still enumerating — the nano needed two attempts on the bench and the
  Launchpad six of its eight. Anything under about 50 s will fail intermittently on correct code.
- ⚠️ **Case 2 needs the patch reloaded between steps**, since *absent at load* is a boot condition.
  It is in the `need` text rather than left for the operator to infer.

⚠️ **Steps 1, 3 and 5 are machine-checkable from the `err` tap** once the human has done the
unplugging — that is the shape `need` / `do` / `watch` was built for. **7 and 8 are not, and must not
pretend to be**: the Volca transmits nothing, so only ears can judge it.

## Verification

```sh
./test/run.sh                        # read the RESULT: line -- do not grep for it
python3 test/gate/docs-check.py -v   # boot.md's two tables are anchored to wire.sh
python3 test/bench/bench-verify.py   # the eight step texts survived generation
./tools/deploy.sh
```

### ✅ Already done on the hardware, 2026-08-10 — do not repeat it

Item 235 in both directions, the give-up reporting, coalescing across two devices, and the safe exit
after the watchdog rewrite. The evidence is in
[ref/module/presence.md](ref/module/presence.md) under *Verified on the hardware*.

⛔ **The `killall pd` test this section used to prescribe is WRONG and has been removed.** `quitting`
comes from mother, not from a shell signal — that is the whole reason `tools/lp-live.sh` exists. The
real test is a patch swap through `/loadPatch`, which is what `tools/deploy.sh` already does.

### ⬜ What still needs the rig

1. **The SP-404 and the Volca never got their own transition runs.** The shared machinery beneath
   both is verified, so this is confirmation rather than discovery.
2. ⚠️ **The Volca cannot be tested alone** — see step 7 of the bench table above.
3. Nothing else. Panic-becomes-`recover` and its hardware steps moved to
   [plan-v03.4.1.md](plan-v03.4.1.md).

---

## Done means

**Struck already:** item 235 fixed and hardware-verified in both directions with its own test; every
detectable device has a presence model and the two that cannot be detected say so on their pages; one
bounded re-wire serves the rig, coalesced; both of [boot.md](ref/module/boot.md)'s `Open` items and
[launchpad.md](ref/device/launchpad.md)'s item-235 item are gone; `plan-v04.md` §3 no longer carries
the *Launchpad watchdog* section.

**Left:**

1. The bound is asserted by **reaching** it, not by arithmetic.
2. Each device has a gate **and** a bench step, covering the transition case and the absent-at-load
   case.
3. **This file is deleted**, and `plan-v04.md` §3's *What plan-v03.4 still owns* subsection goes with
   it.

⛔ **This plan does not hand its open items to `plan-v04.md`.** They are indexed there only so that
the `⬜` pointers from `ref/` pages resolve to something while this file exists.

**Commit as you go** rather than leaving the whole thing in the working tree.
⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**
