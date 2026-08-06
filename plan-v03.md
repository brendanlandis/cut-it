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
| **v0.4** | ⬅ **Next.** The instrument: four filter stages, the drum mode, the sampler, compose-time capture. ⚠️ **But the documentation refactor comes first — see §10** |

⚠️ **v0.3 WAS NOT THE SOUND, AND THIS DOCUMENT ONCE SAID IT WAS.** An earlier version planned the
filter stages here. The goal was to finish the infrastructure so the *next* phase can say
***"in Mode A, moving this fader does X"*** and have somewhere to put the answer. **It can now**:
that sentence is one row of `Cut It/cut-it-map.txt`.

---

## 2. What to read, and how much

**Do not read everything.** The reference docs total ~4000 lines. Read in this order:

| Document | How much | Why |
|---|---|---|
| **[CLAUDE.md](CLAUDE.md)** | **All of it (~280 lines)** | Hard constraints, the file layout, working notes. Non-optional |
| **[ref-conventions.md](ref-conventions.md)** | **"The rules, in one screen" table, then the sections it links** | How the Pd is written. `$0`, the global allowlist, `[trigger]` discipline, the four `route` traps, the banned list. **Read before writing Pd** |
| **[ref-midi.md](ref-midi.md)** | **The addressing model + the section for the device you are touching** | Every CC, note and SysEx each device accepts. Skip the devices you are not working on |
| **[ref-software.md](ref-software.md)** | **Architecture + Load-bearing decisions (~100 lines)** | What the patch is made of and why. The rest is v0.4 design |
| **[ref-hardware.md](ref-hardware.md)** | **"The device itself" + whatever rig section applies** | SSH, paths, how Pd launches, how to measure the running patch |
| **[ref-build-log.md](ref-build-log.md)** | **The corrections in each phase section** | ⚠️ **Every phase produced at least one correction to something a plan asserted.** This is the highest-value-per-line document in the repo |
| **[ref-display.md](ref-display.md)** | Only if touching a display surface | OLED, Launchpad LEDs, aux LED, phone |
| **[plan-tests.md](plan-tests.md)** | **Never read start to finish (~3500 lines).** Grep for the item number you were cited | The evidence ledger. Items are cited bare as "item 133" across every document |

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
  landing checklist. See [ref-conventions.md](ref-conventions.md) → *How a phase runs*.

---

## 3. v0.3 is COMPLETE — what it built, and what it corrected

**All three gaps that defined v0.3 are closed, and the phase ran on the hardware.**

| Gap | |
|---|---|
| The SP-404 has no `m_` layer | **CLOSED.** `m_404`, the first bidirectional device layer. 160 pads, one shared table both directions, a rate limit that drops rather than queues |
| The Volca has no `m_` layer | **CLOSED.** `m_volca` wired in on one selector-prefixed cord |
| `u_map` cannot express a mode-dependent meaning | **CLOSED.** Table-driven with a hardcoded allowlist of destinations |

**The full account is in [ref-build-log.md](ref-build-log.md) under *Phase 9*.** Evidence is
items 228–235. What follows here is only what is still OPEN.

**Four corrections came out of building it**, and they are the part worth carrying forward:
Pd's `pgmout` is 1-based; `u_tempo`'s panic covered one bank in ten; nothing on the device could
raise panic at all; and `ref-conventions.md` asserted that `u_map` did not use a lookup table.

⚠️ **And one bug that 23 green headless checks could not see.** The instrument booted at 120 BPM
instead of the saved 57, because the map was not ready when mother pushes `knobs.txt` at boot. The
gate's own windows were timed *from the implementation detail that was wrong*, so it could only
test the patch after the race had resolved. **A person reading a number off a screen found it.**
Item 234.

---

## 4. Open questions

**The single place to look for what is unresolved.** CLAUDE.md, ref-conventions.md and ref-midi.md
all point here; the section did not exist until v0.3 and the pointers were dangling.

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

### Still unticked in plan-tests.md

Eight checks have never been run. They are **not** v0.3 work and none of them block it, but this is
where to look for them: **item 5 / 95** brownouts with the full rig powered at once, **item 39** the
OLED read by eye, **item 45** AP link quality over a set-length window, **item 81** the wifi fault
itself, and **43/44/46** struck through as answered by later work.

---

## 5. ⚠️ Constraints that bind what you build

**The four rate ceilings are in [ref-midi.md](ref-midi.md). What they bind here:**

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
| **Footswitch, nanoKONTROL scenes, a 404 pre-set checklist, Save New** | Long-standing deferrals; reasons in [ref-build-log.md](ref-build-log.md) and [ref-hardware.md](ref-hardware.md) |
| **LINE IN R-only, ground loops, 404 latency, CPU headroom** | Upgrade paths and perform-time tuning |
| **Guided Access, a dynamic mic, OLED legibility (item 39), the Launchpad onboarding drive** | Real wants, none of them this phase |
| **AP link quality over a set-length window (item 45)** | The last outstanding measurement. ⚠️ Needs the AP up, which kills the house link |

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
evidence for item 226** and are no longer in the repo. The finding itself survives in full in
plan-tests.md — the key 9–12 table and the `PCnot`/`PCMId` trap — so nothing operational is lost.
If those photographs still exist outside the repo, `device/volca-settings/` is where they belong.

---

## 10. NEXT: the documentation refactor

**Agreed as the work that follows v0.3, and it is a real problem rather than tidying.**

| | Lines |
|---|---|
| `plan-tests.md` | **4,131** — 249 items, append-only, and the single largest file in the project |
| `ref-` docs (six files) | ~4,550 |
| `CLAUDE.md` | 309 |
| `tools/README.md` | 765 |
| **Total** | **~10,050** |

That is roughly 400 lines of prose per `.pd` file in `Cut It/`. CLAUDE.md tells a cold reader "do
not read everything", which is an admission that the volume has already outgrown its usefulness.

**What the refactor has to do, at minimum:**

- **Collect every remaining TODO into one place.** Right now open work is spread across
  plan-v03 §4 *Open questions*, eight unticked items in plan-tests.md, and prose scattered through
  the `ref-` docs. §4 was itself only created in v0.3, despite three documents having pointed at it
  for months — so a pointer existing is no guarantee the target does.
- **Decide what plan-tests.md is for.** At 4,131 lines it is never read start to finish, by its own
  instruction. Items are cited by number from everywhere, so the numbering must survive any change.
  Splitting by session, archiving closed sessions, or extracting a findings index are all options.
- **Find the claims that are now false.** v0.3 alone falsified three: `ref-conventions.md` said
  `u_map` used route branches "rather than a lookup table"; `ref-midi.md` implied `pgmout` needed no
  correction; `u_tempo`'s own comment described a panic covering one bank as if it covered the
  instrument. Nothing systematically looks for these.
- **Deduplicate.** The same facts — the `47 + n` pad map, the `[del 2000]` print rule, the
  reject-outlet rule — are restated in CLAUDE.md, the `ref-` docs, the `.pd` comments and the commit
  history. Some of that repetition is deliberate and load-bearing; some is drift waiting to happen.

⚠️ **The `.pd` comments are documentation too**, and they are not counted above. They are also the
only copy that a person editing the patch in Pd can actually see, which is an argument for keeping
them rich even as the prose files shrink.
