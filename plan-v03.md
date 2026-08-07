# Cut It v0.3 — the blank slate

**This is the only plan document in the project, and it is written to be handed to an agent
cold.** Read this file first and in full. It tells you what the project is, which other documents
to read and how much of each, what is already true, and exactly what is left to do.

---

## 1. What this project is

**Cut It is a cut-up / harsh-noise instrument patch for the original Critter & Guitari Organelle
(Organelle 1 — *not* the M, S or S2), written in Pure Data.** The Organelle is the brains and the
clock master; an SP-404MK2 is the sample store and audio front end; a nanoKONTROL, a Launchpad Pro
MK3 and a Korg Volca FM complete the rig.

**⛔ Read [CLAUDE.md](CLAUDE.md) before writing a single line of Pd.** It carries hard constraints
that are not negotiable and not obvious — chiefly that the target is **Pd vanilla 0.49 permanently**
(the hardware cannot be upgraded), and that **opening any device-bound patch in plugdata corrupts
it** for Pd 0.49.

### Where the version numbers are

| | |
|---|---|
| **v0.2** | ✅ Complete and hardware-verified. Sixteen abstractions, four display surfaces, three headless gates, six benches |
| **v0.3** | ✅ **Complete and hardware-verified.** The *blank slate* — every device addressable, every control assignable. Eighteen abstractions, four headless gates, seven benches |
| **v0.4** | ⬅ **Next.** The instrument: four filter stages, the drum mode, the sampler, compose-time capture. ✅ The documentation refactor that blocked it is **done** — see §10 for what the remaining cleanups inherit |

⚠️ **v0.3 WAS NOT THE SOUND, AND THIS DOCUMENT ONCE SAID IT WAS.** An earlier version planned the
filter stages here. The goal was to finish the infrastructure so the *next* phase can say
***"in Mode A, moving this fader does X"*** and have somewhere to put the answer. **It can now**:
that sentence is one row of `Cut It/cut-it-map.txt`.

---

## 2. What to read, and how much

**Do not read everything.** Read in this order:

| Document | How much | Why |
|---|---|---|
| **[CLAUDE.md](CLAUDE.md)** | **All of it (172 lines)** | The router. Hard constraints, where everything is, working notes. Non-optional |
| **This file** | **§4 in full** | The single place to look for what is unresolved |
| **The `pd` / `docs` / `gate` skills** | Invoked, not read | ⛔ Invoke the matching one before writing Pd, documentation or a gate |
| **[ref/README.md](ref/README.md)** | 52 lines | How `ref/` is organised, and the page schema |
| **[ref/conventions.md](ref/conventions.md)** | The rules table, then the sections it links | How the Pd is written — `C-1`…`C-14`. **Read before writing Pd** |
| **[ref/architecture.md](ref/architecture.md)** | All of it (200 lines) | How the modules compose, and the four load-bearing decisions |
| **[ref/device/](ref/device/)**, **[ref/module/](ref/module/)** | **Only the page you are touching** | Everything about one device or one instrument concern, in one place |
| **[ref-hardware.md](ref-hardware.md)** | Only if working on the device | SSH, paths, how Pd launches, wifi. ⚠️ Verify-after: the cruft cleanup changes these paths |

### How this project works

- **⛔ Never touch git.** Brendan commits his own work. Read-only operations are fine.
- **Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
  whole instrument is there, front panel included.
- **`./deploy.sh` does the whole loop** — syntax check, scp, reload, load. It **gates on output, not
  exit status**, because Pd exits 0 even when objects fail to create.
- **`./tools/check-all.sh` runs every gate in one command.** ⚠️ **Run it before calling anything
  done.** Phase 8 came within one step of shipping without re-running the gates of the phases
  beneath it.
- **A phase runs in a fixed shape** — decisions table, Step 0 measurements, numbered build steps
  each ending with both gates, a generated bench, verification separating Mac from device, then a
  landing checklist. See [ref/conventions.md](ref/conventions.md) → *How a phase runs*.

---

## 3. v0.3 is COMPLETE — what it built, and what it corrected

**All three gaps that defined v0.3 are closed, and the phase ran on the hardware.**

| Gap | |
|---|---|
| The SP-404 has no `m_` layer | **CLOSED.** `m_404`, the first bidirectional device layer. 160 pads, one shared table both directions, a rate limit that drops rather than queues |
| The Volca has no `m_` layer | **CLOSED.** `m_volca` wired in on one selector-prefixed cord |
| `u_map` cannot express a mode-dependent meaning | **CLOSED.** Table-driven with a hardcoded allowlist of destinations |

**The full account is in the git history** — `git log` from `dca0b04`. Evidence is
items 228–235. What follows here is only what is still OPEN.

**Four corrections came out of building it**, and they are the part worth carrying forward:
Pd's `pgmout` is 1-based; `u_tempo`'s panic covered one bank in ten; nothing on the device could
raise panic at all; and the old conventions doc asserted that `u_map` did not use a lookup table.

⚠️ **And one bug that 23 green headless checks could not see.** The instrument booted at 120 BPM
instead of the saved 57, because the map was not ready when mother pushes `knobs.txt` at boot. The
gate's own windows were timed *from the implementation detail that was wrong*, so it could only
test the patch after the race had resolved. **A person reading a number off a screen found it.**
Item 234.

---

## 4. Open questions

**The single place to look for what is unresolved.** Every `ref/` page's `Open` section points here;
the section did not exist until v0.3 and the pointers were dangling.

### The Launchpad watchdog cannot recover a device that was absent at load

**Item 235, found on hardware, and it is shipped Phase 6 code rather than anything v0.3 did.**
Power on with the Launchpad unplugged - or with a hub that does not enumerate it in time - and
plugging it in afterwards **never** restores it. Only a patch reload does.

`[r $0-armed]` gates the `[spigot]` in front of the bounded `wire.sh` recovery, and `$0-armed` is
set by exactly one thing: `[sysexin]` receiving a device-inquiry reply. So the recovery arms only
after the device has answered **at least once**, and a device that was never there never answers.
The give-up path sits downstream of the same shut spigot, so it cannot report that it gave up
either - which is why the error log was empty.

**The gap in one sentence: "lost" was built as a TRANSITION from present to absent, and
never-present is not a transition.**

**Likely a one-box change** - arm at load rather than on first reply, letting the existing
`moses 33` bound stop it after eight attempts exactly as it does now. **But it sits beside the safe
exit**, which is the one message in this patch worth more than everything around it, so it wants
its own can-it-fail test rather than being bolted onto the end of another phase.

### Which control, if any, should raise panic

Panic was briefly bound to a nano button in v0.3 and **withdrawn**. `m_launchpad` wires `[r panic]`
straight to the Live Mode SysEx - panic hands the surface back by design - and the watchdog only
re-asserts Programmer Mode while `want` is 1, which panic sets to 0. **So panic kills the grid until
the patch reloads.** A bare button is too easy to brush mid-set on a device with no console.

The capability is right and proven: `m_404` silences all ten banks when panic arrives, which
`u_tempo` never did. Only the binding is open. A deliberate gesture - a two-control combination, or
a control nothing else uses - is a v0.4 decision.

### Checks that were never run

⬜ Four, carried forward from the dissolved evidence ledger. **None of them blocks anything**, and
they keep their item numbers so the citations still mean something.

| Item | Check | Why it is still open |
|---|---|---|
| 5, 95 | **Brownouts with the full rig powered at once** | Partially closed by item 211; never run with every box live simultaneously |
| 39 | **The OLED read by eye** — the three type-size layouts and the ageing | The geometry is verified through `oscOut` on the Mac, but *"is 16px readable at arm's length"* is a judgement only the hardware can settle. The one-mover 24px layout has been read on the device incidentally |
| 45 | **AP link quality over a set-length window** | Needs an actual set's duration to mean anything |
| 81 | **The wifi fault itself** | ⚠️ Narrowed, not solved — see [ref-hardware.md](ref-hardware.md). Items 43, 44 and 46 were answered by later work |

---

## 5. ⚠️ Constraints that bind what you build

**The four rate ceilings are in [ref/module/tempo.md](ref/module/tempo.md). What they bind here:**

| Constraint | Consequence |
|---|---|
| **`c_clock`'s bang outlet caps at 14.3/s** | ⛔ A dense trigger stream cannot come from `c_clock` — it needs a plain `[metro]` |
| **MIDI triggers cap at ~360–400/s** | `m_404`'s hard rate limit. Overshoot costs seconds of lag |
| **The OLED lags ~200 ms; the Launchpad does not** | Rhythmic feedback goes on the Launchpad |

✅ **The audio-domain path has no ceiling** — `c_clock` outlet 0 is raw phase as a *signal*. **The
ceilings are message-domain only.** ⚠️ If a stage converts that phase to bangs, that is the mistake.

**Other standing risks:**

- **The `m_` boundary is the one genuinely expensive thing to retrofit.** Nothing in `e_*` may know
  a nanoKONTROL exists. v0.3 is when the pressure arrives, because it is when controls start
  meaning things.
- **Timing is architectural** — audio-domain from the first line, and **nothing downstream may
  assume the global `clock` is its clock**. Cut It runs poly-tempo.
- **The DSP is the budget, not the MIDI** — DSP 6.9 points against MIDI's 0.43, measured two ways.

---

## 6. The wifi fault — background, not blocking

**Requirement, as Brendan states it: the Organelle must stop dropping wifi.** Not "recover fast" —
a dead phone display mid-set is the failure.

**Do not spend session time on this unless it recurs.** Everything actionable has shipped:

| | |
|---|---|
| ✅ **The recovery ladder works** | Two real failures, both recovered on rung 1, unattended (item 212) |
| ⛔ **Orbi firmware 2.7.6.6 did NOT fix it** | Twice in 15 hours (item 213) |
| ✅ **Channel 1 was a real win** | 14.4 → **72.2 MBit/s** at the same signal (item 221) |
| ⛔ **The trigger is untouched** | Both APs remain co-channel at −39/−41 dBm. One Orbi setting moves both mesh nodes |
| ⚠️ **Recovery takes ~132 s, not the 20 s the script claims** | ~60 s of it is diagnostics running *before* the rung that works (item 220) |

**The watcher now records what was missing** — outage duration, and a dhcpcd-pid discriminator that
separates "the incumbent daemon cannot re-acquire" from "upstream is not answering". **The next
spontaneous event answers both questions by itself.**

⛔ **The preferred-AP steer is no longer a safe fallback**: one failure happened *on* the router,
which is where the steer parks the device (item 214).

**Open, and Brendan's to do:** read the Orbi DHCP pool (⚠️ **reading is safe — only *saving* caused
outages, twice**), and check satellite backhaul health.

⚠️ **Operating the watcher:** never `pgrep -f wifi-watch` — it matches the ssh carrying it (item
163). Use the pidfile. And `wifi-report.sh --mark` goes **after** a write-up, never before.

---

## 7. Deliberately not in this phase

**Recorded so none of it is rediscovered as news.**

| | Why |
|---|---|
| **The four filter stages** — `e_chop`, `e_pitch`, `e_trem`, `e_verb` | v0.4. ⚠️ **Grain timing must be audio-domain from the first line** when they land — `phasor~` and `vline~`, never `metro`/`line~` |
| **The drum mode, compose-mode capture, the sampler** | v0.4. The `time, note, velocity, duration` format is decided and every device can now fill all four fields |
| **The mic-bleed capture guard** | v0.4, with capture. ⚠️ A live vocal bakes into any drums-channel buffer sampled while the mic is hot |
| **Items 142, 202, 210** | Step 0 measurements that gate the **v0.4 sampler**, not this phase. Batch them next time the rig is up |
| **Footswitch, nanoKONTROL scenes, a 404 pre-set checklist, Save New** | Long-standing deferrals; reasons on [ref/rig.md](ref/rig.md), [ref/device/nanokontrol.md](ref/device/nanokontrol.md) and [ref/module/state.md](ref/module/state.md) |
| **LINE IN R-only, ground loops, 404 latency, CPU headroom** | Upgrade paths and perform-time tuning |
| **Guided Access, a dynamic mic, OLED legibility (item 39), the Launchpad onboarding drive** | Real wants, none of them this phase |
| **AP link quality over a set-length window (item 45)** | The last outstanding measurement. ⚠️ Needs the AP up, which kills the house link |

---

### Grid idioms, and what each would map to

Moved out of the old design-notes file during the documentation refactor. **Every row below describes a
feature that does not exist yet** — the pattern launcher, the four filter quadrants, Chop Shop's
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

---

## 8. ⚠️ How this project gets things wrong

**Read this before trusting your own conclusions. Every one of these cost real time.**

- **Every phase's most valuable output was a correction to something a plan asserted.** The channel
  block, `enc`'s polarity, `route`'s remainder rule, `[list split n]`, `pgrep`, the reject-outlet
  rule, the 404 pad map — none came from reading documentation and several contradict it.
- ⛔ **A reject, left, or non-matching outlet carries DATA, not a bang.** Four instances, every one
  silent. Put a `[t b]` in front of anything behind one.
- ⚠️ **Prove the probe before believing the silence.** A null result is worthless until the channel
  is proven. "No pad lit" meant "receive and transmit differ" for half an hour, until it turned out
  the 404 lights only the *selected* bank.
- ⚠️ **A measuring rig is code and gets the same scrutiny.** Phase 5 had two bugs in its own probes;
  Phase 6's bench had an assertion nothing ever drove; `phase8-assert.sh` passed a broken patch.
- ⚠️ **Wait for the whole measurement.** Three confident wrong answers in this project came from
  acting on a partial result — items 182, 209, 210, and again in item 225.
- ⚠️ **When a device has a settings menu, read the menu.** The Volca's Program Change turned out to
  be gated behind **two adjacent, undocumented global settings**. Three reasoned hypotheses failed;
  photographs of the menu solved it in one step (item 226).
- ⚠️ **Toggles are hazardous.** Pressing a setting that is already correct turns it *off*. Re-use a
  known-good prior result as a probe for device state.

---

## 9. Repo hygiene

**The root is clean.** The firmware `.wav`s, the Volca settings photographs and the stray
screenshot are all gone. Nothing is left to move.

One thing to be aware of rather than to act on: **the Volca settings photographs were the primary
evidence for item 226** and are no longer in the repo. The finding itself survives in full on
[ref/device/volca.md](ref/device/volca.md) — the key 9–12 table and the `PCnot`/`PCMId` trap — so
nothing operational is lost.
If those photographs still exist outside the repo, `device/volca-settings/` is where they belong.

---

## 10. The documentation refactor — DONE

**Landed 2026-08-06.** Per this project's own rule a completed phase leaves the plan, and **git is
now the journal**, so the account of what was built and why is in the commit log from `91c68f4`
onward. What stays here is only what still binds work that has not happened.

| | Before | After |
|---|---|---|
| Root `.md` | **10 files, 10,300 lines** | **3 files, 1,176** |
| `ref/` | — | **17 pages, 4,268 lines** |
| Total prose | ~10,300 | **5,444** |
| Journals | 5,112 lines, never read start to finish | **0 — dissolved** |

**The three root files are `CLAUDE.md` (the router), this file (the only plan), and
`ref-hardware.md`** — the Organelle as a computer, which becomes `ref/device-os.md` as the **last
step of the Organelle cruft cleanup**, because that cleanup changes the paths it documents.

### What the next three jobs inherit

⚠️ **The taxonomy is settled and the tests will adopt it.** A module is a physical device or one
instrument concern, the directory is the kind, and the page names are the gate names:

```
ref/device/   launchpad  nanokontrol  organelle  phone  sp404  volca
ref/module/   audio  boot  display  map  state  tempo
ref/          architecture  conventions  rig
```

| Job | What it inherits |
|---|---|
| **Testing, by module instead of phase** | **The same axis, and the names above.** The gates are still named by *phase* — four `phaseN-assert.sh`, four drive-gens, `bench_steps.py`'s `STEPS3`…`STEPS9`. Phase is a *time* axis, and the cost is already visible: `phase9-assert` exists partly because `phase6-assert` rewrote only `[midiout]` and would have passed vacuously over `noteout`/`ctlout`/`pgmout`. On a module axis that is **one** MIDI-emission gate, not two. ⚠️ Every module page's `**Gate:**` line already names its gate — **rename the gates and those lines must move with them**, and `docs-check.py` will say so |
| **Tool cleanup** | `tools/README.md` is 46 KB describing ~40 files, many one-off probes from July. ⛔ **`tools/wire.sh` is a Phase 1 ancestor of `Cut It/wire.sh`** — 59 lines behind, no autoconnect undo, no `\|\| true` — and is a delete candidate. ✅ Five scripts of 42 are named in no document at all, and **that is fine** (Brendan, 2026-08-06); `docs-check.py` is mention-driven by design and will never look for them |
| **Organelle cruft cleanup** | `ref-hardware.md` is entirely about the device as a computer, and its paths are the ones that change. **Do not invest there before the cleanup; rename it to `ref/device-os.md` after** |

### The rules that outlived the refactor

**None of these has to be remembered — `tools/docs-check.py` enforces what can be enforced, and the
`docs` skill carries the rest.** Listed only so a reader knows the constraints exist.

- **A fact appears once in full; everywhere else it is a citation.** `item NNN` is a **fact ID**, not
  a log entry. Never reuse a number.
- ⛔ **A check mark never means "built."** An evidence marker never rots; a completion marker
  silently becomes false. The gate fails on a `✅` in any heading.
- ⛔ **The `.pd` comments cite `C-NN`**, because a comment has no link syntax and a path rots. Where
  no rule covers it, they name a `ref/` page.
- ⛔ **A section is not what its heading says.** Read what is under it before deleting from one
  heading to the next, and probe distinctive strings afterwards. That caught a real deletion twice
  here — twelve facts out of the design notes, and four `###` subsections filed under *Signal
  flow — power* that had nothing to do with power.
- ⚠️ **The line count goes UP per page and that is expected.** The reduction was entirely in the
  journals. Do not compress the module pages chasing it.

### Still open

- ⬜ **What `docs-check.py` structurally cannot do.** It is **mention-driven**: it proves every
  mention resolves, and can say nothing about a file nobody mentions, nor about a mention that
  resolves to the *wrong* file. `ref-hardware.md` pointed at `tools/wire.sh` for months and the check
  had nothing to say. **Found by reading, and there is no gate for it.**
