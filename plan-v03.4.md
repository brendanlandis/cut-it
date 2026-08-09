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
last-heard detection. It now depends only on the stub from [plan-v03.3.md](plan-v03.3.md).

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

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** skill | ⛔ **Invoked, not read** | You are editing shipped Pd beside the safe exit |
| The **`gate`** skill | ⛔ **Invoked, not read** | Every change here needs a test that can fail |
| [plan-v04.md](plan-v04.md) | §3 and §7 in full | §3's *Launchpad watchdog* section diagnoses item 235 **down to the box.** Do not re-derive it |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14` |
| `git log` | **Grep it, never read it** | Git is the journal |
| `Cut It/m_launchpad.pd` | **All of it, and the `watchdog` subpatch twice** | The only reconnect logic that exists. Its comments explain **why two mechanisms**, **why the bound is 70 s and not 12**, and **why the arming gate is not removable** |
| `Cut It/wire.sh` | **All 58 lines, comments included** | Idempotent, 133 ms, `\|\| true` on every line. Its comments hold the enumeration-order incident |
| `Cut It/u_init.pd` | All of it | It calls `wire.sh` at 1500 ms and owns the boot stage sequence |
| [ref/module/boot.md](ref/module/boot.md) | **All of it** | **Two of its `Open` items are what this plan closes.** Its two tables are anchored to `wire.sh` by the doc gate — change one and you change both |
| [ref/device/launchpad.md](ref/device/launchpad.md) | All of it | Item 235, plus what the device does and does not announce |
| [ref/device/nanokontrol.md](ref/device/nanokontrol.md), [ref/device/sp404.md](ref/device/sp404.md), [ref/device/volca.md](ref/device/volca.md) | **Their `Facts` sections** | What each device can and cannot transmit |
| `Cut It/m_nano.pd`, `Cut It/m_404.pd`, `Cut It/m_volca.pd`, `Cut It/m_organelle.pd` | **All of them** | Each gains a presence publisher |
| [ref/device-os.md](ref/device-os.md) | The *loading any patch drops Pd's ALSA connections* fact (item 228) | Why `wire.sh` runs on every load rather than at boot |
| `Cut It/g_grid.pd` | Its ownership inlet only | It consumes `m_launchpad`'s ownership outlet |
| [ref/architecture.md](ref/architecture.md) | The `m_` boundary section | ⛔ Nothing outside an `m_` may know which device it is talking to |

**Do not read** `Cut It/g_oled.pd` (783 lines), `Cut It/u_net.pd`, or any `ref/module/` page except
[boot.md](ref/module/boot.md).

---

## What is already true

- **`wire.sh` connects six ALSA links by name**, each with `2>/dev/null || true`, so a device that is
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

## Phase 1 — item 235, on its own

**Power on with the Launchpad unplugged and plugging it in afterwards never restores it.** Only a
reload does.

The arming spigot in front of the bounded re-wire is gated by a flag set by exactly one thing: a
device-inquiry **reply**. So **recovery arms only after the device has answered at least once**, and
a device that was never there never answers. ⛔ **The give-up path sits downstream of the same shut
spigot**, so it cannot report that it gave up either — which is why the error log was empty.

**Likely a one-box change** — arm at load rather than on first reply, letting the existing bound stop
it after eight attempts exactly as it does now.

⛔ **But the arming gate is not simply removable.** The patch records that without it, the headless
assert layer lost every frame six seconds in and **failed 7 of 24 checks**. Understand why before
changing it: the flag exists so that ownership can only be *dropped* once presence has been
established, and the fix must preserve that while still permitting a *never-present* device to
recover.

⚠️ **Its own can-it-fail test.** Boot with the device unplugged, plug it in, and confirm both that it
recovers and that the give-up path can now report. Then boot **with** it plugged in and confirm
nothing regressed.

---

## Phase 1b — panic becomes RECOVER, and it closes item 235 the blunt way

**Decided 2026-08-08, with the rig in front of us.** Panic's job is not silence — the mixer's master
fader is faster, analogue, and does not depend on the thing that is misbehaving. Panic's job is
**recovery**: silence what is sounding, then reload the patch, so every device is re-enumerated into
Pd and `wire.sh` runs fresh. That covers item 235 by brute force, including the never-present case
Phase 1 is picking apart delicately.

✅ **The destructive half is already removed** (item 251): panic no longer hands the Launchpad back.
That was a bug — it killed the grid until reload and buried Pd's Midi-In 1 under a clock flood. Both
gates were inverted deliberately and both were made to fail against the old code.

**What is left to build, and the four things that make it non-trivial:**

1. ⛔ **Silence must land BEFORE the reload.** Killing Pd mid-note never sends the note-off, so the
   404 holds it — a panic that *creates* a stuck note. Sequence the existing note-off loop and the
   `252` STOP, then fire the reload behind a short delay.
2. ⛔ **The two-step OSC, or it silently does nothing.** `oscsend localhost 4001 /reloadNoRemount i 1`
   **then** `/loadPatch s '!/Cut It'`. A bare name loads nothing at all and says nothing —
   `tools/deploy.sh` documents this, and it still caught us on 2026-08-08.
3. ⛔ **The failure mode is worse than the fault.** If the load does not take, there is no patch at
   all, and the patch cannot verify its own reload because it is dead by then. This is item 243's
   shape exactly. Design for it rather than discovering it.
4. ⚠️ **Its core is untestable on the Mac.** `[shell]` is stubbed, so a gate can assert the silence
   sequence and that the message is well formed, and can never assert that the reload happened. Say
   so in the gate rather than implying coverage that does not exist.

⚠️ **It breaks the one-fork-per-load rule** (Phase 4's). Defensibly — a panic is rare, user-initiated
and ends the patch — but it must say so in a comment, the way `m_launchpad`'s bounded recovery does.

⚠️ **Knobs come back latched.** mother re-pushes `knobs.txt`, pickup arms, and every knob is held
until swept through its stored value (item 239). Correct on a normal boot; possibly wrong right after
an emergency. ⬜ Decide whether the reload path should skip arming.

⚠️ **Two tiers, so the meanings stay separate**: a short press silences only and is always safe; a
held combination silences **and** reloads. That is also the answer to *"which control raises panic"*
on [ref/device/launchpad.md](ref/device/launchpad.md) as item 251 — the question was unanswerable
while panic was destructive.

---

## Phase 2 — Step 0, and why the model cannot be uniform

✅ **Both questions this phase was built on are answered — item 249, and both answers are yes.**

| Device | Can it be detected? |
|---|---|
| **Launchpad Pro MK3** | ✅ **Actively** — it answers a universal device inquiry in either mode. Already polled |
| **nanoKONTROL** | ✅ **Actively.** `F0 7E 00 06 02 42 04 01 00 00 23 00 00 00 F7` — `42` is KORG. ⛔ Nobody had ever asked; its input had been recorded as inert. See [ref/device/nanokontrol.md](ref/device/nanokontrol.md) |
| **SP-404MK2** | ✅ **Actively.** `F0 7E 10 06 02 41 08 04 00 00 00 03 00 00 F7` — ⛔ **contradicting Roland's own chart**, which marks SysEx `x` in both directions |
| **Volca FM** | ⛔ **Never.** It transmits nothing, ever. Structurally impossible, and that is a fact rather than a gap |
| **Organelle panel** | Not MIDI — mother's own receives |
| **Phone** | Only at the phone end. UDP is fire-and-forget, so **only the end that stops hearing can know** |

⚠️ **Prove the probe before believing the silence.** Send the inquiry to the Launchpad first, which is
known to answer, and only then trust a silence from the other two.

---

## Phase 3 — the presence model

### Passive: last-heard, for every device that ever speaks

**Every `m_` publishes on a presence bus whenever it decodes anything**, and a new abstraction keeps
a last-heard clock per device. That costs about one box per `m_`, works for every device that
transmits at all, and needs no polling.

⛔ **The `m_` boundary still holds.** An `m_` publishes *"I heard from my device"*; it does not
publish *"the nanoKONTROL is alive."* **Nothing outside an `m_` may know which device it is talking
to** — that boundary is the one genuinely expensive thing to retrofit, and v0.4 is when the pressure
arrives.

⚠️ **Passive presence cannot distinguish "unplugged" from "not touched."** A nanoKONTROL nobody has
moved for ten minutes looks identical to one on the floor. **Say that on the page rather than
pretending otherwise** — the readout is *last heard*, and the operator supplies the rest.

### Active: polling, only where a device answers

Decided by Step 0. If the 404 or the nano answers an inquiry, it gets the same treatment the
Launchpad has. If not, **do not invent a heartbeat it cannot answer.**

---

## Phase 4 — one bounded re-wire, serving every device

**Today only `m_launchpad` can trigger `wire.sh`.** Move that out into a shared owner so any device's
loss can trigger it.

⚠️ **Keep the bound.** Eight attempts over ~70 s, because **12 seconds was useless in a room** —
nobody reseats a cable that fast. The bound is also *why forking is permitted at all*.

⚠️ **One shared re-wire means one shared bound.** Two devices lost at once must not double the fork
rate. Coalesce: a re-wire serves whoever is missing.

### The quieter bug this also fixes

`wire.sh`'s three `aconnect -d` lines undo mother's auto-connect — but **that undo has already run**
by the time a device enumerates late. So **a device plugged in after boot can land on the Launchpad's
channel block**, which is exactly the phantom-control incident the script's own comments record.
Nothing today notices. Re-running `wire.sh` fixes it, and that is an argument for the shared owner
rather than a per-device one.

### What this closes

- [ref/module/boot.md](ref/module/boot.md) — *nothing detects a device that failed to wire.* A stage
  name means the sequence reached that point, **not that hardware answered**.
- [ref/module/boot.md](ref/module/boot.md) — *a replug after boot destroys the ALSA links and only
  the Launchpad has a recovery path.*
- [ref/device/launchpad.md](ref/device/launchpad.md) and `plan-v04.md` §3 — item 235.

⚠️ **If you change `wire.sh`'s connect or disconnect lines, two anchored tables in
[ref/module/boot.md](ref/module/boot.md) must change with them**, and `docs-check.py` compares them
mechanically. That is a feature — it is what makes the rename impossible to half-finish.

---

## Phase 5 — surfacing it

**Presence data with no readout is not a feature.** The minimum: a device that has been silent past
its threshold raises a `warn` naming the device, and the give-up path raises a `fail`.

⛔ **Do not build the diagnostic screen here.** [plan-v03.5.md](plan-v03.5.md) owns it, and it is
built on exactly this data. **This plan's job is to produce the data and get it onto the error bus;
that plan's job is to display it.**

⚠️ **A dark grid is already three different things** — nothing changed, panic handed the surface
back, or the watchdog gave up — and only the OLED tells them apart. **Do not add a fourth ambiguous
state.**

---

## Phase 6 — making it testable

**Per device, two oracles**, because a gate and a bench answer different questions and neither
substitutes for the other:

### Headless gates

Simulate loss by stopping the stub's output, then assert: the presence flag drops **after** the
threshold and not before, the re-wire fires, it fires **at the stated interval**, and it **stops at
the bound** rather than running forever. ⛔ **Counts exact, never "at least."**

⚠️ **Assert the bound by letting it be reached**, not by reading the number out of the patch. A gate
that asserts what the code says is not a test.

### Bench steps

One per device: **unplug, count to five, replug, confirm recovery within the deadline.** These are
exactly the shape the runner's `need` / `do` / `watch` step fields were built for, and
**the recovery deadline is machine-checkable from a tap** — so these steps can be auto-judged after
the human does the unplugging.

⛔ **Two cases that are not the same test, and item 235 is the proof:**

1. **Present at load, then unplugged** — the transition case, which has always worked.
2. **Absent at load, then plugged in** — the case that never worked and was never tested.

**Both get a step, for every device.**

⚠️ **The Volca's step is the honest exception.** It transmits nothing, so its recovery can only be
verified by ear — a note is sent and either sounds or does not. **Put that in the step's `watch` text
rather than pretending a machine judged it.**

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v   # the two boot.md tables are anchored to wire.sh
./tools/deploy.sh
```

Then, on hardware, for **each** of the Launchpad, nanoKONTROL and SP-404:

1. Unplug mid-run; confirm the warning appears and recovery happens within the bound.
2. **Boot with it unplugged**, then plug it in — the case item 235 never covered.
3. Leave it unplugged past the bound; confirm the give-up **reports** rather than going quiet.

⚠️ **Then confirm the safe exit still works**: `killall pd` and check the Launchpad returns to Live
Mode. If it does not, `tools/lp-live.sh` rescues it — but the point is that it should not need to.

---

## Done means

1. Item 235 is fixed and hardware-verified in **both** directions, with its own test.
2. Every device that can be detected has a presence model, and the ones that cannot are **stated as
   such on their pages** rather than left silent.
3. One bounded re-wire serves every device, with the bound intact and coalesced.
4. Both of [ref/module/boot.md](ref/module/boot.md)'s `Open` items are struck, and
   [ref/device/launchpad.md](ref/device/launchpad.md)'s item-235 item with them.
5. Each device has a gate **and** a bench step, covering both the transition case and the
   absent-at-load case.
6. `plan-v04.md` §3 no longer carries the Launchpad watchdog section.
7. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.**

**Commit each phase as it lands** rather than leaving the whole plan in the working tree.
⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**
