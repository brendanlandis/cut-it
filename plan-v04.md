# Plan — v0.4, the instrument

**This is the project's standing plan and it is written to be handed to an agent cold.** Read it
first and in full. It says what the project is, what is already true, what is unresolved, and what
gets built next.

⛔ **Read [CLAUDE.md](CLAUDE.md) before writing a single line of Pd**, and invoke the **`pd`** skill.
The target is **Pd vanilla 0.49 permanently** — the hardware cannot be upgraded — and **opening any
device-bound patch in plugdata corrupts it**.

⚠️ **Two scoped plans come first, in this order:**

1. **[plan-testing.md](plan-testing.md)** — the gates move from the phase axis to the module axis.
   Mac-side; no device needs plugging in.
2. **[plan-cleanup.md](plan-cleanup.md)** — `tools/` and then the Organelle itself.
3. **This document** — the sound.

**A plan is scoped to one piece of work and is deleted when the work lands.** This one is the
exception that persists, because it is where everything unscoped waits.

---

## 1. What this project is

**Cut It is a cut-up / harsh-noise instrument patch for the original Critter & Guitari Organelle
(Organelle 1 — *not* the M, S or S2), written in Pure Data.** The Organelle is the brains and the
clock master; an SP-404MK2 is the sample store and audio front end; a nanoKONTROL, a Launchpad Pro
MK3 and a Korg Volca FM complete the rig.

| | |
|---|---|
| **v0.2** | ✅ Complete and hardware-verified. Sixteen abstractions, four display surfaces, three headless gates, six benches |
| **v0.3** | ✅ **Complete and hardware-verified.** The *blank slate* — every device addressable, every control assignable |
| **The documentation refactor** | ✅ **Complete.** 10 root files and ~10,300 lines of prose became 2 files and 18 `ref/` pages, held together by `test/gate/docs-check.py` |
| **v0.4** | ⬅ **This document.** The instrument: four filter stages, the drum mode, the sampler, compose-time capture |

**v0.3 was not the sound, and an earlier plan said it was.** The goal was to finish the
infrastructure so this phase can say ***"in Mode A, moving this fader does X"*** and have somewhere
to put the answer. **It can now**: that sentence is one row of `Cut It/cut-it-map.txt`.

---

## 2. What to read, and how much

**Do not read everything.**

| Document | How much | Why |
|---|---|---|
| **[CLAUDE.md](CLAUDE.md)** | **All of it (167 lines)** | The router. Hard constraints, where everything is, working notes |
| **This file** | **§3 in full** | The single place to look for what is unresolved |
| **The `pd` / `docs` / `gate` skills** | Invoked, not read | ⛔ Invoke the matching one before writing Pd, documentation or a test |
| **[ref/README.md](ref/README.md)** | 52 lines | How `ref/` is organised, and the page schema |
| **[ref/conventions.md](ref/conventions.md)** | The rules table, then the sections it links | `C-1`…`C-14`. **Read before writing Pd** |
| **[ref/architecture.md](ref/architecture.md)** | All of it | How the modules compose, and the four load-bearing decisions |
| **[ref/device/](ref/device/)**, **[ref/module/](ref/module/)** | **Only the page you are touching** | Everything about one device or one concern, in one place |
| **[ref/device-os.md](ref/device-os.md)** | Only if working on the device | SSH, paths, how Pd launches, wifi. ⛔ **Verify-after** — see §5 |
| **`git log`** | Grep it | **Git is the journal.** Both journals dissolved; the account of every phase is in the commit history from `dca0b04` |

### How this project works

- ⛔ **Never touch git** unless asked. Brendan commits his own work.
- **Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
  whole instrument is there, front panel included.
- **`./deploy.sh` does the whole loop** — syntax check, scp, reload, load. It **gates on output, not
  exit status**, because Pd exits 0 even when objects fail to create.
- **`./test/check-all.sh` runs every gate in one command.** ⚠️ **Run it before calling anything
  done**, and read its `RESULT:` line rather than grepping for one.
- **`item NNN` is a FACT ID, not a log entry.** Grep for it. Never reuse a number.

---

## 3. Open questions

**The single place to look for what is unresolved.** Every `ref/` page's `Open` section points here.

### The Launchpad watchdog cannot recover a device that was absent at load

**Item 235, found on hardware, and it is shipped Phase 6 code.** Power on with the Launchpad
unplugged — or with a hub that does not enumerate it in time — and plugging it in afterwards
**never** restores it. Only a patch reload does.

`[r $0-armed]` gates the `[spigot]` in front of the bounded `wire.sh` recovery, and `$0-armed` is set
by exactly one thing: `[sysexin]` receiving a device-inquiry reply. **So the recovery arms only after
the device has answered at least once**, and a device that was never there never answers. The
give-up path sits downstream of the same shut spigot, so it cannot report that it gave up either —
which is why the error log was empty.

**The gap in one sentence: "lost" was built as a TRANSITION from present to absent, and
never-present is not a transition.**

**Likely a one-box change** — arm at load rather than on first reply, letting the existing `moses 33`
bound stop it after eight attempts exactly as it does now. ⚠️ **But it sits beside the safe exit**,
which is the one message in this patch worth more than everything around it, so it wants its own
can-it-fail test rather than being bolted onto the end of another phase.

### Which control, if any, should raise panic

Panic was briefly bound to a nano button in v0.3 and **withdrawn**. `m_launchpad` wires `[r panic]`
straight to the Live Mode SysEx — panic hands the surface back by design — and the watchdog only
re-asserts Programmer Mode while `want` is 1, which panic sets to 0. **So panic kills the grid until
the patch reloads.** A bare button is too easy to brush mid-set on a device with no console.

### Parameter pickup

⛔ **After any `Storage → Save`, every knob is desynced from its value and the first touch jumps** —
measured at **443 BPM** on knob 1, which is master tempo. Nothing on the instrument can detect it:
mother reports position, not whether the position still matches the file. It happens on **every
boot**, not only on a bank switch. See [ref/device/organelle.md](ref/device/organelle.md) under
*Saving*.

### Checks that were never run

⬜ Four, carried forward from the dissolved evidence ledger. **None blocks anything**, and they keep
their item numbers so the citations still resolve.

| Item | Check | Why it is still open |
|---|---|---|
| 5, 95 | **Brownouts with the full rig powered at once** | Partially closed by item 211; never run with every box live simultaneously |
| 39 | **The OLED read by eye** — the three type-size layouts and the ageing | The geometry is verified through `oscOut` on the Mac, but *"is 16px readable at arm's length"* is a judgement only the hardware can settle |
| 45 | **AP link quality over a set-length window** | Needs an actual set's duration to mean anything. ⚠️ Needs the AP up, which kills the house link |
| 81 | **The wifi fault itself** | ⚠️ Narrowed, not solved — see [ref/device-os.md](ref/device-os.md) |

### The wifi fault — background, not blocking

**Requirement, as Brendan states it: the Organelle must stop dropping wifi.** Not "recover fast" — a
dead phone display mid-set is the failure.

⚠️ **Do not spend session time on this unless it recurs.** Everything actionable has shipped: the
recovery ladder works unattended (item 212), Orbi firmware 2.7.6.6 did **not** fix it (item 213), and
channel 1 was a real throughput win but did not separate the two APs (item 221). **The trigger is
untouched** — both APs remain co-channel, and one Orbi setting moves both mesh nodes.

⛔ **The preferred-AP steer is no longer a safe fallback**: one failure happened *on* the router
(item 214). The measurements, the four wrong turns and the reproduction recipe are on
[ref/device-os.md](ref/device-os.md).

### No gate covers audio

⬜ Every gate asserts on **messages**; nothing reads a signal back. `ref/module/audio.md` declares
`**Gate:** none` and `**Bench:** none`, honestly. A headless audio gate is possible — Pd can write a
soundfile — and it would be the first of its kind here. **It becomes worth building the moment
`e_chop` exists.**

---

## 4. ⚠️ Constraints that bind what you build

**The four rate ceilings are in [ref/module/tempo.md](ref/module/tempo.md). What they bind here:**

| Constraint | Consequence |
|---|---|
| **`c_clock`'s bang outlet caps at 14.3/s** | ⛔ A dense trigger stream cannot come from `c_clock` — it needs a plain `[metro]` |
| **MIDI triggers cap at ~360–400/s** | `m_404`'s hard rate limit. Overshoot costs seconds of lag |
| **The OLED lags ~200 ms; the Launchpad does not** | Rhythmic feedback goes on the Launchpad |

✅ **The audio-domain path has no ceiling** — `c_clock` outlet 0 is raw phase as a *signal*. **The
ceilings are message-domain only.** ⚠️ If a stage converts that phase to bangs, that is the mistake.

**Three standing risks:**

- ⛔ **The `m_` boundary is the one genuinely expensive thing to retrofit.** Nothing in `e_*` may know
  a nanoKONTROL exists. **v0.4 is when the pressure arrives**, because it is when controls start
  meaning things.
- **Timing is architectural** — audio-domain from the first line, and **nothing downstream may assume
  the global `clock` is its clock**. Cut It runs poly-tempo.
- **The DSP is the budget, not the MIDI** — DSP ~7 points against MIDI's fraction of one, measured
  two ways (item 75).

---

## 5. The two cleanups still queued

**Both are planned in [plan-cleanup.md](plan-cleanup.md)** — the `tools/` directory (89 files, and
the decision is which probes are finished) and the Organelle itself (three system files modified
from factory, and a survey nobody has done).

⚠️ **The order is [plan-testing.md](plan-testing.md) → [plan-cleanup.md](plan-cleanup.md) → this
document.** The testing refactor renames ~30 files in `tools/`, so a cleanup that runs first decides
the fate of filenames about to change.

---

## 6. Deliberately not in v0.4

**Recorded so none of it is rediscovered as news.**

| | Why |
|---|---|
| **Footswitch, nanoKONTROL scenes, a 404 pre-set checklist, Save New** | Long-standing deferrals; reasons on [ref/rig.md](ref/rig.md), [ref/device/nanokontrol.md](ref/device/nanokontrol.md) and [ref/module/state.md](ref/module/state.md) |
| **LINE IN R-only, ground loops, 404 latency, CPU headroom** | Upgrade paths and perform-time tuning |
| **Guided Access, a dynamic mic, the Launchpad onboarding drive** | Real wants, none of them next |
| **Items 142, 202, 210** | Step 0 measurements that gate the **sampler** specifically. Batch them next time the rig is up |

---

## 7. ⚠️ How this project gets things wrong

**Read this before trusting your own conclusions. Every one of these cost real time.**

- **Every phase's most valuable output was a correction to something a plan asserted.** The channel
  block, `enc`'s polarity, `route`'s remainder rule, `[list split n]`, `pgrep`, the reject-outlet
  rule, the 404 pad map — none came from reading documentation and several contradict it.
- ⛔ **A reject, left, or non-matching outlet carries DATA, not a bang.** Four instances, every one
  silent. Put a `[t b]` in front of anything behind one (C-8).
- ⚠️ **Prove the probe before believing the silence.** A null result is worthless until the channel is
  proven. "No pad lit" meant "receive and transmit differ" for half an hour, until it turned out the
  404 lights only the *selected* bank.
- ⚠️ **A measuring rig is code and gets the same scrutiny.** Phase 5 had two bugs in its own probes;
  Phase 6's bench had an assertion nothing ever drove; `state-assert.sh` passed a broken patch 15/15.
- ⚠️ **Wait for the whole measurement.** Three confident wrong answers came from acting on a partial
  result — items 182, 209, 210, and again in 225.
- ⚠️ **Concluding from a single SUCCESS is the same error as concluding from a single failure.** This
  project forbids the second in writing and the first still got through (item 182).
- ⚠️ **When a device has a settings menu, read the menu.** The Volca's Program Change was gated behind
  **two adjacent, undocumented global settings**. Three reasoned hypotheses failed; photographs of
  the menu solved it in one step (item 226).
- ⚠️ **Toggles are hazardous.** Pressing a setting that is already correct turns it *off*. Re-use a
  known-good prior result as a probe for device state.
- ⛔ **A section is not what its heading says.** Read what is under it before deleting from one heading
  to the next. That caught a real deletion twice during the documentation refactor.

---

## 8. What v0.4 builds

⬜ **Not planned in detail yet — this section is the next thing to write.** What is decided:

| | |
|---|---|
| **The four filter stages** — `e_chop`, `e_pitch`, `e_trem`, `e_verb` | ⛔ **Grain timing must be audio-domain from the first line** — `phasor~` and `vline~`, never `metro`/`line~` (C-11) |
| **The drum mode, compose-mode capture, the sampler** | The `time, note, velocity, duration` format is decided and **every device can now fill all four fields** |
| **The mic-bleed capture guard** | ⚠️ A live vocal bakes into any drums-channel buffer sampled while the mic is hot |
| **Where each lands** | `e_` pages under `ref/module/`, one per stage. **`ref/module/` is what v0.4 grows** — the device set is fixed by the hardware |
| **How a control reaches it** | One row of `Cut It/cut-it-map.txt`, and a destination on `u_map`'s literal `route` box. ⛔ **The allowlist guard is not optional** — see [ref/module/map.md](ref/module/map.md) |

### Grid idioms, and what each would map to

⚠️ **Every row below describes a feature that does not exist yet** — the pattern launcher, the four filter quadrants, Chop Shop's
drunkenness — so it is intent rather than reference, and `ref-` states what is.

| Idiom | What it is | Use for Cut It |
|---|---|---|
| **Clip launching** (Session) | Columns = tracks, rows = scenes. Blinks when queued, solid when playing. Right column fires a whole row | **The pattern launcher.** Columns = destinations (404 drums, Volca, internal), rows = variations. Inherits the queued/playing visual convention free |
| **Drum rack** | 4×4 quadrants of velocity-sensitive trigger pads | **Four filter quadrants**, arranged right-to-left to match the signal chain. 16 pads per filter vs the 5–7 keys currently on the Organelle keyboard |
| **Isomorphic note layout** | Fixed interval per row, scale-locked | Playing the Volca — use built-in Note mode, don't rebuild |
| **Step sequencing** | Row = track, column = step | Compose-time authoring — use built-in Sequencer |
| **Column-as-fader** | Press higher = higher value. 8 steps of resolution | Coarse parameter control if the nano runs out |
| **X/Y pad** | Pad coordinates set two parameters at once | **Chop Shop's drunkenness + sputter.** A 4×4 block = 16 positions over both. Slapping a corner is a different gesture than turning two knobs |
| **Radio buttons** | A row as exclusive mode select, lit | Filter selection |
| **Pure display** | Grid as output only | Playhead position, which sample slots are filled |

**Pressure is the forgotten input.** Grain size, chop intensity, filter depth — any of these
can ride pad pressure while held. Costs no panel space and is the most expressive control on
the rig.

The README says the controls *"will take some practice and memorization."* The RGB grid is
the direct antidote to half of that: which filters are on, which of the five sample slots are
filled, which pattern is queued, where the playhead is — all visible rather than memorised.

⚠️ **The six modes are placeholders but their 3/3 ratio is not.** `u_err` routes on
`compose`/`perform`, so a split weighted toward `perform` silently quietens the error display.
**The sound work is what will name them.**
