# Plan — v0.4, the instrument

**This is the project's standing plan and it is written to be handed to an agent cold.** Read it
first and in full. It says what the project is, what is already true, what is unresolved, and what
gets built next.

⛔ **Read [CLAUDE.md](CLAUDE.md) before writing a single line of Pd**, and invoke the **`pd`** skill.
The target is **Pd vanilla 0.49 permanently** — the hardware cannot be upgraded — and **opening any
device-bound patch in plugdata corrupts it**.

⚠️ **This is no longer the only plan.** Two scoped plans — [plan-v03.4.md](plan-v03.4.md) and
[plan-v03.5.md](plan-v03.5.md) — hold the last batch of infrastructural work before v0.4: hot-swap
and the venue kit. ✅ **The test runner, the v0.3.2 cleanup and the v0.3.3 coverage pass all landed
2026-08-09.** **Read [CLAUDE.md](CLAUDE.md)'s table for the order and the dependencies.**

⛔ **§3 below is being emptied by those two.** Every open question in it is assigned to one of them,
and when they land this section holds **only v0.4 code**. Do not start work on a
§3 item without checking which plan owns it first.

The **testing refactor** moved the gates off the phase axis and out of `tools/`: every one lives in
`test/gate/`, is named for the module it covers, and every module page names a gate whose whole
subject is that page — or `none`, honestly. The **cleanup** took 18 answered probes out of `tools/`,
cleared the Organelle's menu down to `Cut It`, backed up the two device files that had no copy, and
verified `ref/device-os.md` against the hardware.

✅ **Re-confirmed on hardware, 2026-08-07, after the cleanup.** Both devices powered from one
strip — the Launchpad enumerates in a second or two, the Organelle's boot takes far longer to reach
`mount.sh`, so the hazardous ordering is the one that happens. The instrument came up running, the
Launchpad entered Programmer Mode, and the beat row was walking. **Three things at once:** the
`mount.sh` guard held, `m_launchpad`'s boot SysEx fired on real hardware rather than into a stub,
and — see below — item 234's fix was visible in the tempo.

⚠️ **The cheap version needs no power cycle**, because `mount.sh` runs on every Reload: plug the
Launchpad in and run `sh /root/fw_dir/scripts/mount.sh` — expect *"skipping write-protected device
/dev/sda1"* and `/usbdrive` absent from `/proc/mounts`.

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
| **The documentation refactor** | ✅ **Complete.** 10 root files and ~10,300 lines of prose became 2 files and 21 `ref/` pages, held together by `test/gate/docs-check.py` |
| **v0.4** | ⬅ **This document.** The instrument: four filter stages, the drum mode, the sampler, compose-time capture |

**v0.3 was not the sound, and an earlier plan said it was.** The goal was to finish the
infrastructure so this phase can say ***"in Mode A, moving this fader does X"*** and have somewhere
to put the answer. **It can now**: that sentence is one row of `Cut It/cut-it-map.txt`.

---

## 2. What to read, and how much

**Do not read everything.**

| Document | How much | Why |
|---|---|---|
| **[CLAUDE.md](CLAUDE.md)** | **All of it** | The router. Hard constraints, where everything is, working notes |
| **This file** | **§3 in full** | The single place to look for what is unresolved |
| **The `pd` / `docs` / `gate` skills** | Invoked, not read | ⛔ Invoke the matching one before writing Pd, documentation or a test |
| **[ref/README.md](ref/README.md)** | All of it | How `ref/` is organised, the page schema, and the standard for a v0.4 page |
| **[ref/conventions.md](ref/conventions.md)** | The rules table, then the sections it links | `C-1`…`C-14`. **Read before writing Pd** |
| **[ref/workflow.md](ref/workflow.md)** | Only when you are about to run something | The deploy loop, the by-hand SSH console, how a phase runs |
| **[ref/architecture.md](ref/architecture.md)** | All of it | How the modules compose, and the four load-bearing decisions |
| **[ref/device/](ref/device/)**, **[ref/module/](ref/module/)** | **Only the page you are touching** | Everything about one device or one concern, in one place |
| **[ref/device-os.md](ref/device-os.md)** | Only if working on the device | SSH, paths, how Pd launches, the boot hang. ⛔ **Verify-after** — see §5 |
| **[ref/wifi.md](ref/wifi.md)** | ⚠️ Only if the fault recurs | The roam fault and the evidence behind it. **Not blocking anything** |
| **`git log`** | Grep it | **Git is the journal.** Both journals dissolved; the account of every phase is in the commit history from `dca0b04` |

### How this project works

- **Commit as you go**, in reviewable batches. ⛔ **Brendan is the sole author: no `Co-Authored-By`
  trailer and no agent byline.**
- **Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
  whole instrument is there, front panel included.
- **`./tools/deploy.sh` does the whole loop** — syntax check, scp, reload, load. It **gates on output, not
  exit status**, because Pd exits 0 even when objects fail to create.
- **`./test/run.sh` runs every gate in one command**, and `--all` adds the benches. ⚠️ **Run it
  before calling anything done**, and read its `RESULT:` line rather than grepping for one.
- **`item NNN` is a FACT ID, not a log entry.** Grep for it. Never reuse a number.

---

## 3. Open questions

**The single place to look for what is unresolved.** Every `ref/` page's `Open` section points here.

### ✅ Panic, and parameter pickup — both closed, kept only as pointers

**Panic means RECOVER, not silence** — decided 2026-08-08 with the rig present. The mixer's master
fader is the better silence: instant, analogue, independent of whatever is misbehaving. ✅ The
destructive half is already removed (item 251) — panic no longer hands the Launchpad back, which used
to kill the grid until reload and bury Pd's Midi-In 1 under a clock flood. ⬜ **The build and the
control binding are [plan-v03.4.md](plan-v03.4.md) Phase 1b**, because a reload closes item 235 by
brute force.

**Parameter pickup is shipped and hardware-verified.** Items 239–242, on
[ref/module/map.md](ref/module/map.md). ⛔ It found three further bugs on the device after the first
fix landed, and all three are in the gate: the held row drawn for unmapped knobs, a target on a rail
that could never be crossed, and an unmapped control reporting nothing at all.

### Checks that were never run

⬜ **Two left of the four**, carried forward from the dissolved evidence ledger. **Neither blocks
anything**, and they keep their item numbers so the citations still resolve. Both of the others were
struck on 2026-08-08:

- ✅ *Brownouts with the full rig powered* — items 5 and 95. **There is no shared rail for one to
  happen on**; the evidence is on [ref/rig.md](ref/rig.md) as item 255.
- ✅ *The OLED read by eye* — item 39. **All three type-size layouts are legible at playing
  distance**, including the 8px five-row case; on
  [ref/module/display.md](ref/module/display.md) as item 258.

| Item | Check | Why it is still open |
|---|---|---|
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

⬜ **One untried angle, turned up while closing items 5 and 95: the dongle is the only thing on the
Organelle's own rail.** The RT5370 declares **450 mA** and sits on a **separate root bus from the
powered hub** (`2-1`), so it draws from the 9 V 1000 mA adapter rather than the hub's PSU — the one
place in the rig with a shared budget. Item 255, on [ref/rig.md](ref/rig.md). ⚠️ **This is a
hypothesis and nothing more**: `MaxPower` is a declared maximum, the adapter has headroom on paper,
and no drop has ever been correlated with load. ⛔ The obvious test — move the dongle onto the powered
hub — carries a **known hazard**, since that hub has one controller the Launchpad will not configure
on at all (item 256). Worth one deliberate trial **only if the fault recurs**, per the rule above.

### ⬜ Nothing measures the OUTPUT side

✅ **The input side is gated.** `test/gate/audio-assert.sh` records `u_root`'s output to a soundfile
and asserts three things about the passthrough: it is not silent, L and R are not swapped — measured
by **frequency**, because both channels carry the same level and amplitude cannot see a swap — and it
is unity rather than attenuated. It is the first signal-domain gate in the project, which makes the
second one a small addition rather than a new kind of thing.

⬜ **What stays open is output-side metering.** Both `u_level` instances sit on the input; a tap
before `throw~` measures a passthrough and nothing else until there are stages between the two.
**This one genuinely waits for `e_chop`** — see [ref/module/audio.md](ref/module/audio.md).

### ✅ The reference patches under `tools/*/` earn their keep — decided, and kept

`audio-probe/`, `oled-probe/`, `osc-bridge/` and `status-display/` all stay. **[plan-v03.5.md](plan-v03.5.md)
wants two of them as working references within weeks**, which is the "would you run it again" test
answering itself. The reasoning is recorded on [tools/README.md](tools/README.md) so the question
stops recurring.

### ⬜ Debugging the rig with no laptop

**The problem is a venue.** Every diagnostic tool this project has is driven from the Mac over SSH —
`test/run.sh`, `fetch-errors.sh`, `display-cpu.sh` — and SSH needs a network, which is the exact thing that
is missing when it matters. Three probes that looked like the start of an answer were deleted in the
cleanup because they were not: `sp404-send.sh` ran *from* the Mac by design, and its own header said
a message box "needs a hand on the laptop at the same moment".

**The seed is `tools/stage-patches/`**, and it already solved the two hard parts:

- ⛔ **A menu-launched patch has no console** — Pd runs `-nogui` and stdout goes to tty1, which VNC
  will not show. Every stage patch therefore writes its findings to `/sdcard/*.log` and puts
  instructions on the **OLED**. `State Probe` says so in its own header, for exactly this reason.
- **Selecting the patch is itself the test**, in more cases than you would expect. Loading one
  restarts Pd, which is how `AP Probe` proves the access point survives a patch change.

⛔ **A standalone menu patch may use the ENCODER, and Cut It may not.** mother forwards `encbut` only
after a patch sends `/enableEncoder`, and the instrument never does because C-5 gives `g_oled` sole
ownership of `oscOut`. A separate debug patch is not bound by that — so it has the encoder **plus**
four knobs, the aux button and 25 keys, where the instrument has everything but the encoder. That is
the difference between a menu of one screen and a menu you can navigate.

⬜ **Not designed yet.** What it should show, at minimum: what MIDI is arriving from each device and
on what channel, a way to fire test output at each device, and the tail of `cut-it-err.log` — the
three questions that currently require a laptop and a network.

⛔ **It goes in `/sdcard/Patches/! debug/`, not in `!`.** As of 2026-08-07 the `!` menu holds
**`Cut It` and nothing else** — the four probes that had accumulated there were removed once every
one was confirmed byte-identical to its copy in the repo. At a venue you should scroll past nothing
to reach the instrument, and a second menu directory is where anything you might reach for *instead*
of playing belongs.

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

## 5. ✅ The two cleanups, done

`tools/` went from 89 files to **28**, all of them run by a person. The tests are in `test/`. The
device menu holds **`Cut It` alone**, and the three factory-modified system files are all backed up
in [device/](device/) now that `pdsettings.orig` is there too.

⚠️ **The survey corrected the plan that asked for it**, which is the usual pattern here:
`/root/Pd/externals` turned out to be entirely factory stock rather than something this project
modified, `/root` held no debugging debris at all, and the four stage patches on the device were a
different four from the ones in the repo.

⚠️ **And one correction was itself wrong.** `/sdcard/PdExtraLibs` does not exist, so the page's claim
that it was "already on Pd's search path" looked doubly wrong and was rewritten to say so. Loading a
patch showed the path **is** on the search path — `mother` passes `-path /sdcard/PdExtraLibs` on the
command line, not through `.pdsettings`. Only the directory is missing. Corrected again, and worth
remembering as the shape of the mistake: *absent* and *unconfigured* are not the same finding.

✅ **Nothing from the cleanup is outstanding.** The boot test is done — see §1.

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

### ⬜ The 404 is a live effects processor, and v0.4 has not budgeted for it

**Found 2026-08-08 while chasing an unrelated negative — item 262.** The SP-404 is the audio front
end for the whole rig; every sound passes through it. Its effects turn out to be **sweepable from Pd
in real time over CC**, confirmed one CC at a time against a looping pad with the resonator on.

⚠️ **Nothing above assumes this**, because until it was measured nobody knew it was possible. It is
the only DSP in the rig that is not `e_`-shaped and not written by us, and it is free.

Two pieces of work, in order:

1. ⬜ **Map it.** Which CC moves which parameter, whether the set changes per effect, and CC 17, 19,
   81–83, which are untried. ⛔ **The next test must name the bus** — one effect on BUS 1 only,
   nothing on 3/4 — because BUS 3/4 are master FX over the whole mix, so a master effect and a
   per-sample one cannot be told apart by ear. **An afternoon with a looping pad and an ear.**
2. ⬜ **Decide what plays it.** A nano fader is the obvious first answer; ⛔ **pad pressure is the
   more interesting one**, since *Pressure is the forgotten input* below applies exactly here — a
   held pad sweeping a resonator on the drum bus is a gesture the rig cannot currently make.

⚠️ **Read [ref/device/sp404.md](ref/device/sp404.md) before designing against this.** 📄 Roland's
chart is wrong in both directions on this device — it denies SysEx the device answers (item 249) and
promises a CC 7 and Program Change that do nothing (item 260). **Treat every unexercised row as
unlikely rather than unknown.**

### ⬜ `MIDI EXT SRC` — a note that opens and closes the mic

**Item 261, and untested.** The 404's MIDI menu carries `MIDI EXT SRC`, with values
**GATE / TOGGLE / THROUGH**, governing how MIDI drives its **external audio input** — the mic and the
arbitrary line source. It is set to `GATE` today and none of the three has been exercised.

⚠️ **For a cut-up instrument this is a playable feature, not a setting.** The rig's front end is a
live mic; *"a note opens the input"* makes the mic a gated source under sequencer control, and the
three values are three different instruments. ⛔ **It also interacts with the mic-bleed capture guard
above** — a gate that can close the input is a way to make capture safe rather than merely warned
about.

⬜ **What is not known: which note, and on which channel.** That is the whole measurement, and it is
minutes with a mic and a looping pad.

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
