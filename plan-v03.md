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
| **v0.3** | ⬅ **You are here.** The *blank slate* — every device addressable, every control assignable |
| **v0.4** | The instrument: four filter stages, the drum mode, the sampler, compose-time capture |

⚠️ **v0.3 IS NOT THE SOUND, AND THIS DOCUMENT USED TO SAY IT WAS.** An earlier version planned the
filter stages here. The goal now is to finish the infrastructure so the *next* phase can say
***"in Mode A, moving this fader does X"*** and have somewhere to put the answer.

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

## 3. What v0.3 is, and what is already done

Three gaps defined v0.3. **One is closed.**

| Gap | State |
|---|---|
| **The SP-404 has no `m_` layer** | ⬜ **Open — `m_404` is the main remaining build** |
| **The Volca has no `m_` layer** | ✅ **CLOSED.** `m_volca` is wired in — one selector-prefixed cord from `u_map`, `$5` verified arriving as 49. ⬜ Nothing drives the outlet until the mode table lands |
| **`u_map` cannot express a mode-dependent meaning** | ✅ **CLOSED.** Table-driven with a hardcoded allowlist of destinations — `cut-it-map.txt`, `<mode> <control> <dest> <arg>`. Guard proven: a bad destination errors and emits nothing (item 230) |

### ✅ Closed during the last session — do not redo these

- **The USB→DIN interface is owned, attached and wired.** It enumerates as
  **`USB Uno MIDI Interface`**, and `wire.sh` connects it both ways. **Pd slot 4 (channels 49–64) is
  live** for the first time in the project.
- **The Volca is fully characterised** — notes, CC 40–50, **Program Change** and **velocity** all
  confirmed working. Items 223–227.
- **`Cut It/m_volca.pd` is written**, passes the layout check with 0 problems and loads silently.
  ⚠️ **Nothing instantiates it yet**, so it is inert.
- **⛔ `pgmout` is 1-BASED, measured both directions — item 228.** `pgmout N` puts wire value `N-1`
  on the cable, so the bare `[pgmout]` `m_volca` shipped with would have selected **one patch below**
  the number asked for, silently. ✅ **Fixed** — `m_volca` now carries a `[+ 1]`, and its inlet means
  the *wire* number. ⚠️ Two mechanism findings came with it: **loading any patch drops Pd's ALSA
  output connections** (which is why `u_init` runs `wire.sh` — a probe patch must make its own
  `aconnect` or it measures silence and looks like a negative result), and **a menu patch loaded by
  `oscsend /loadPatch` is the cheap way to run Pd-side MIDI probes**, because it needs no
  `killall pd` and so cannot strand the Launchpad. Probe kept at `tools/stage-patches/PGM Probe/`.
- **The wifi fault is instrumented** — see §6.

---

## 4. What remains in this phase

**In order.** The measurement that gated all of it is closed — see §3.

### 4.1 Wire `m_volca` in

| File | Change |
|---|---|
| `Cut It/u_root.pd` | Instantiate `m_volca $5`; add the cord from `u_map`'s new outlet |
| `Cut It/u_map.pd` | ⚠️ It has **no outlets today**. Add one per output device — this is the decided design, see [ref-conventions.md](ref-conventions.md) → *Output devices are WIRED from `u_map`* |
| `Cut It/main.pd` + `main-dev.pd` | Pass the Volca channel block (**49**) as `$5`. ⚠️ These two files may **only** disagree about creation arguments |

⚠️ **`u_root` currently takes three creation args** (`$1` nano channel, `$2` Launchpad channel,
`$3` state dir). `m_404` takes `$4` and `m_volca` `$5`. That was Brendan's decision — straight
extension of the existing precedent rather than a restructure.

### 4.2 Build `m_404`

**Bidirectional, and the largest remaining piece.**

- **In:** `[notein]` on channels base…base+9 → bank + pad. ✅ **160 pads: bank sets the CHANNEL
  (33–42), pad sets the NOTE (36–51).** One formula, no special cases.
- **Out:** trigger a pad. ⚠️ **Ships with a hard rate limit, not as a later fix.**

```
pads              notes            note = 36 + (3 - (pad-1)/4)*4 + (pad-1) % 4
 1  2  3  4       48 49 50 51        (integer division)
 5  6  7  8       44 45 46 47
 9 10 11 12       40 41 42 43      receive and transmit share ONE map
13 14 15 16       36 37 38 39
```

⛔ **`47 + n` is WRONG and was in this repo's docs.** It holds for pads 1–4 and breaks at pad 5.
**Assert all sixteen in the gate, not a sample.**

**Two decisions to settle before building:**

| Decision | Recommendation |
|---|---|
| **Does a playing 404 pattern flood the OLED?** | The 404's sequencer transmits notes, and five dense note-ons would fill `g_oled`'s five param rows. **Follow `m_launchpad`'s aftertouch precedent: pad presses to `param` AND `disp`, sequencer-rate traffic to `param` only** |
| **How does the rate limit behave at the ceiling?** | ⛔ **Drop, never queue.** Item 209 proved there is no queue between Pd and the 404; adding one recreates the exact symptom — overshoot costs *seconds* of lag that outlive the gesture, while a stop is instant |

### 4.3 Make `u_map` mode-aware

**The centrepiece of the phase, and the thing that makes v0.4 possible.**

Today `u_map` holds three `route` branches — `og-knob-1`/`og-aux`, and the six `xport-*` keys — and
sends `mode`, `start`, `stop`, `tempo`, `state`. **It publishes `mode` and never consults it.**

✅ **Decided: a hybrid — table-driven lookup with a hardcoded allowlist of destination sends.** This
reverses the old *"`u_map` as a `[text]` table"* deferral, whose own condition was "revisit past
about ten mappings"; 42 nanoKONTROL controls × six modes is well past it.

⚠️ **The allowlist guard is the whole of what makes this acceptable.** A data-driven `[send]` can
write **any** global name with no evidence on the canvas, which defeats an allowlist audited by
reading. The table selects *among* destination names that exist as literal objects. ⛔ **Skip the
guard and the property is gone silently — nothing fails and no test notices.**

**Also settle:** whether the mapping table is persisted via `u_state` (it would be the first real
in-patch user of the `manual` policy — ⚠️ **the synchronous-answer rule is the part a contributor
can break invisibly**), and the six mode names, whose `compose`/`perform` **ratio is load-bearing**
because `u_err` routes on those words.

### 4.4 The gate, the bench, and landing

- **`tools/phase9-assert.sh`** — reuse `phase6-assert.sh`'s shape: it rewrites `[midiout]` in a
  **scratch copy** so a headless run reads back every byte. Exactly right for two MIDI-emitting
  abstractions. `Cut It/` is never touched.
- ⚠️ **Prove the gate can fail.** `phase8-assert.sh` passed the broken patch 15/15 on its first
  can-it-fail run. Reintroduce a real bug — a `47 + n` pad map is the obvious one.
- **`tools/bench_steps.py`** then `bench-gen.py`. ⛔ **Never edit a bench `.pd`.**
- **Add the Phase 9 gate to `tools/check-all.sh`.**
- **Landing:** finished work moves to [ref-build-log.md](ref-build-log.md); this section *leaves*
  this file rather than being annotated; a new [plan-tests.md](plan-tests.md) session is added with
  items numbered **after the last used number** — currently **227**. ⛔ **Never reuse an item
  number.**

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

## 9. Repo hygiene, noted not done

Sitting in the repo root, none of it mine to move: two firmware `.wav`s (~11 MB), ten Volca
settings photographs (~25 MB — ⚠️ **these are the primary evidence for item 226 and deserve a home
like `device/volca-settings/` rather than deletion**), and a stray screenshot.
