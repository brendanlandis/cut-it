# Cut It v0.3 — the blank slate

**This is the only plan document in the project.** Every open question, unverified claim and
deferred decision lives here. The `ref-*` documents state what *is* and mark uncertainty ⬜, but
they carry no plans — when something there is unverified, the work to resolve it is below.
[plan-tests.md](plan-tests.md) is the evidence ledger: numbered checks with their measured results,
cited bare as "item 133" across the whole project.

✅ **v0.2 is complete.** Sixteen deployed abstractions, four display surfaces, three headless gates
and six benches, all verified on hardware. The instrument passes audio, knows what every control is
doing, and can tell you about it.

⚠️ **v0.3 IS NOT THE SOUND, AND THIS DOCUMENT USED TO SAY IT WAS.** The previous version planned
four filter stages, a drum mode and compose-mode capture. **v0.3 is now the blank slate**: make
every device in the rig addressable, and make every control *assignable*, so that the next phase
can say ***"in Mode A, moving this fader does X"*** and have somewhere to put the answer.
**v0.4 is the instrument.**

Read [ref-conventions.md](ref-conventions.md) before writing any Pd, and
[ref-build-log.md](ref-build-log.md)'s corrections before trusting any plan — including this one.
Every phase so far produced at least one correction to something a plan asserted.

---

## What is actually missing

Three gaps, and they are the whole of v0.3.

| Gap | |
|---|---|
| **The SP-404 has no `m_` layer** | Every other attached device has one. ✅ The device is characterised in both directions and fully unblocked |
| **The Volca has no `m_` layer** | ✅ **Newly unblocked — the USB→DIN cable is now owned.** It was the last device with no path into the rig |
| **`u_map` cannot express a mode-dependent meaning** | ⚠️ It **publishes** `mode` and never **consults** it. Three `route` branches exist — `og-knob-1`/`og-aux` and the six `xport-*` keys — and the nanoKONTROL's other 42 controls, the Launchpad's 64 pads and the Organelle's knobs 2–4 all publish to `param` and land nowhere |

---

## ⚠️ Do this first — the wifi

**The requirement, stated plainly: the Organelle must stop dropping wifi.** Not "recover quickly" —
even a perfect 20-second recovery is twenty seconds of a dead phone display in front of an audience,
and the display is what tells you the instrument is alive. **The target is that it does not happen.**

**It is first for a second reason that is not the stage.** The house network carries `deploy.sh`,
`tools/fetch-errors.sh`, `tools/fetch-state.sh`, `tools/go.sh` and the by-hand SSH console —
**every device-side item below needs the device reachable for hours at a stretch.** And item 45 is
blocked on it outright.

✅ **On stage the fault is structurally absent** — the Organelle *hosts* the network, so there is no
association to hand off and no lease to acquire. ⚠️ **But immunity to this fault is not proof the
stage link is solid** (item 45), and it only holds if the venue sequence is actually followed.

**What is known, the repro, the ruled-out branches and how to operate the watcher are all in
[ref-hardware.md](ref-hardware.md)** → *The roam fault*. Only the open work is here.

### ✅ The wait is over — captured 2026-08-06, and the answer is the negative one

**Session 16, items 212–215.** The watcher was verified armed before the log was read: **recover
mode, steer OFF, no reboot across either failure** — so this is the clean experiment the steer was
being kept off to allow.

| | |
|---|---|
| ✅ **The ladder works** | Two real failures, **both RECOVERED on rung 1** (`wifi-reassociate.sh`), first try, unattended. The two demoted `dhcpcd` rungs were never reached. **Item 161's ⬜ closes and the reorder is vindicated** |
| ⛔ **2.7.6.6 did NOT fix it** | Twice in 15 hours, **7 h 33 m apart** — squarely inside the pre-update family of 2 h 09 m / 3 h 12 m / 13 h 32 m. **There is no improvement to read** |
| ⚠️ **A failure happened on the ROUTER** | Not only the satellite. **This overturns the premise the steer is built on** — see below |
| ⚠️ **The two DHCP probes disagreed** | Satellite: **no offer at all**. Router: **`offered 192.168.1.11 from 192.168.1.1`** instantly, while the running `dhcpcd` had nothing. ⬜ Possibly two different faults — written as a hypothesis, not a finding |

✅ Both link probes were clean — **0 % loss to the gateway** — so *the fault is DHCP-side* is
confirmed twice more, and a card swap would still prove nothing.

### What that leaves open

⛔ **The steer is no longer a safe fallback, and this is the change.** It was held in reserve as the
mitigation of last resort. **Failure 2 was a roam *to* the router**, which is exactly where the
steer parks the device — so parking there would not have prevented it. ⚠️ **Do not enable it on the
assumption that the router is safe.** Item 214. *(It remains true that it also drops IPv4 on every
fire, and that keeping it off is what allowed this measurement — item 189.)*

```
the fault RECURS post-update  ->  take the Orbi admin UI branch:
   ├─ the satellite's BACKHAUL HEALTH
   └─ the router's 2.4 GHz AUTO-CHANNEL behaviour -- a channel change is a
      re-association event for every 2.4 GHz client, the same trigger class
   ⚠️ Neither is visible from the instrument; both need the Orbi UI
```

✅ **Both instrument-side improvements are SHIPPED and running** (items 212, 215, 216) — the watcher
now measures the outage and captures the dhcpcd pid at the failure, so the **next** event answers
both questions by itself:

| Now recorded at every failure | Answers |
|---|---|
| **Outage duration**, as a lower bound | How long the phone display is actually dead — the number the requirement is about |
| **dhcpcd pid vs the last healthy pid** | Same pid = the incumbent cannot re-acquire (**client-side**); changed = it restarted and still cannot (**upstream**) |

⚠️ **`dhcpcd -U` is useless on this device and now we know why** — it reads a lease file, and
`/var/lib/dhcpcd` is on the **read-only rootfs**, so one has never been written (item 216).
⬜ **That reopens `--dbdir /sdcard/dhcpcd`**, which sits in the ruled-out list but was dismissed
inside a batch aimed at *"the lease expires"* — a model item 172 overturned. **A lead, not a fix.**

### What is left, and it needs the Orbi UI

⛔ **Both remaining levers need the admin UI, so they are one visit:**

| | |
|---|---|
| **Are the two APs really co-channel?** | ⚠️ **Measured: both on 2427 MHz (ch 4), 2–4 dB apart** — a textbook roam-churn setup, and corroborated by a poor **14.4 MBit/s MCS 1** rate at −41 dBm. Split them (1 / 11), or at minimum **pin the channel off auto**, which also kills the auto-channel changes already listed as a trigger. ⬜ Orbi may not expose per-node channels |
| **Backhaul and fast roaming** | Satellite backhaul health; disable 802.11r/k/v or band steering if exposed. ⚠️ **Confirm the backhaul is 5 GHz before touching 2.4** |
| **The DHCP pool range** | Needed either way — a fallback static address must sit outside it. Observed leases: .11, .15, .18, .20 |

**On the device fallback (`ssid hildegard` scoped):** ✅ **it cannot affect the stage AP** —
`start-ap.sh` runs `killall dhcpcd` before `create_ap`, so dhcpcd is not running in AP mode. And
scoped to the house SSID it does nothing on any other network.

⛔ **BUT THE RESERVATION ROUTE IS CLOSED, and for a practical reason rather than a theoretical
one: saving an Address Reservation on this Orbi takes the whole network down temporarily.**
Measured the hard way — two saves, two long outages, both machines off the air, and a router,
modem and computer restart to get back. **The reservation was the collision-safety half of the
fallback plan**, so a static address now needs a gap **outside the DHCP pool** instead.

✅ **Reading the pool is safe** — *Advanced → Setup → LAN Setup*, Starting/Ending IP. **Reading
changes nothing; it is only SAVING that causes the outage.**

### Where this actually stands

| | |
|---|---|
| ✅ **Channel 1 is a real win** | 14.4 → **72.2 MBit/s** at the same signal (item 221) |
| ⛔ **The trigger is untouched** | Both APs still co-channel at −39/−41, satellite back online. One Orbi channel setting moves both nodes |
| ✅ **Observability is transformed** | Outage duration, link-vs-DHCP discrimination, 60-line dmesg, gated verdicts. The next spontaneous event will be far better documented than any so far |
| ⚠️ **Recovery is 132 s, not 20 s** | And ~60 s of that is diagnostics running *before* the rung that works — item 220 |

---

## The shape of v0.3

| | What | Notes |
|---|---|---|
| **1** | **`m_404`** | Both directions. ✅ **160 pads** — bank sets the **channel** (33–42), pad sets the **note** (36–51), one formula, no special cases. ⚠️ **Ships with a hard rate limit**, not as a later fix |
| **2** | **`m_volca`** | Pd device 4, channel 49. ⚠️ **Output-only** — the Volca transmits nothing at all, which makes this the first `m_` file with no device events to map. `m_launchpad` already drives its own device, so the precedent exists, but a purely-outbound `m_` file is new and the convention needs a decision |
| **3** | **`u_map` becomes mode-aware** | **The centrepiece.** See below |
| **4** | **Parameter pickup, and the value-at-first-touch tick** | Designed together — both need the same stored *value when the control was grabbed*. ⚠️ Item 200 made this a boot-time fact, not a hypothesis |
| **5** | **Bar meters on the param layer** | A bar reads faster than a number. `gFillArea` already draws the home meters, so the drawing is solved; what is not is how a bar and a name share 128 px, and what five stacked ones look like |
| **6** | **CC 99 — a status light on the Launchpad logo** | ✅ CC 99 is an LED, not a button (item 198), and `g_grid` already paints it — its span is 1–108 — so it carries background dim today for nothing. **The only non-button LED on the surface**: an indicator there cannot be mistaken for something pressable, and it costs **one region branch and no extra SysEx** |

### `u_map`, and the one convention this phase bends

**Decided: a hybrid — table-driven lookup, with a hardcoded allowlist of destination sends.**

This reverses the deferral in the old plan, whose own condition was *"revisit when the count passes
about ten"*. It has: 42 nano controls × six modes is well past the point where explicit `route`
branches stay readable.

⚠️ **But the reason for the deferral is real and does not go away.** A data-driven `[send]` can
write **any** global name with no evidence of it on the canvas, which defeats an allowlist that is
audited by reading. **The allowlist guard is what buys that back**: the table selects *among*
destination names that exist as literal objects on the canvas, and cannot invent one. ⛔ **Skip the
guard and the audit-by-reading property is gone silently** — nothing will fail, and no test will
notice.

---

## ⚠️ Three measured constraints that bind what gets built

**The devices are characterised and nothing already built needs changing.** The four rate ceilings
are in [ref-midi.md](ref-midi.md) → *The four rate ceilings*; what they bind on the work still to do:

| Constraint | Consequence for v0.3 |
|---|---|
| **`c_clock`'s BANG outlet caps at 14.3/s** | ⛔ **A dense trigger stream cannot come from `c_clock` as built** — it needs a plain `[metro]`. Decide this per part *before* wiring anything to the clock |
| **MIDI triggers cap at ~360–400/s** | **`m_404` ships with a hard rate limit**, not as a later fix. Overshoot costs seconds of lag that outlive the gesture — and ⛔ it is **not** a queue in Pd (item 209) |
| **The OLED lags ~200 ms; the Launchpad does not** | **Rhythmic feedback goes on the Launchpad.** ✅ A bar meter and a first-touch tick are both fine; a moving playhead is not |

✅ **The audio-rate path has no ceiling at all.** `c_clock` outlet 0 is the raw phase as a *signal*.
**The ceilings are message-domain only.** ⚠️ If a stage ever converts that phase to bangs, that is
the mistake — not the ceiling.

---

## Step 0 — measure before building

Per [ref-conventions.md](ref-conventions.md) → *How a phase runs*. **Every phase so far has had at
least one assumption turn out wrong here.**

| | Measurement | Why it comes first |
|---|---|---|
| **The Volca, end to end** | Notes, **CC 40–50**, and presets. ⚠️ **`MIDI RX ShortMessage` must be ON or none of CC 40–50 is received** — every parameter CC is gated behind that one global — and **`MIDI Clock src` must be Auto**. ⚠️ **Korg's chart marks Program Change UNSUPPORTED 📄, so "change presets" may not be reachable at all**; the only patch channel is DX7 bulk SysEx. **Measure, don't assume** | Everything `m_volca` can do depends on it. It is also the first traffic ever sent to Pd MIDI slot 4 |
| **Item 142** | Can a captured sample be written without glitching the audio? ⬜ Measured **without DSP**: 2 s = 6.1 ms, 10 s = 29 ms, **30 s = 85 ms**. An 85 ms *synchronous* `soundfiler` write sits on Pd's message thread with audio live. Alternatives: `writesf~`, which writes from a helper thread, or writing at capture time | **Gates the sampler**, which is v0.4's first real user |
| **Item 202** | ⬜ Does `gWaveform` work **from inside Cut It**? Both halves are proven separately — `packOSC` emits a valid `b`-typetag blob and `gWaveform` renders one — but they have never been run as one path through `g_oled`. ⚠️ **Draw to a spare screen**: `g_oled` rebuilds screen 3 every 100 ms and would wipe it | Structurally matching halves are strong evidence and are not one run |
| **Item 210** | ⬜ Is the MIDI limit **per-device or aggregate**? `g_grid` emits ~3320 bytes/s at 600 BPM against the clock's 480. ⚠️ **The isolating test needs the Launchpad unplugged**, which fires `m_launchpad`'s watchdog and its `wire.sh` recovery, adding forks and noise to the very thing being measured | A dense `m_404` trigger stream alongside a live grid is exactly the case that makes it matter |

---

## Stage-readiness

⬜ **One item, and it is the last measurement of any kind still outstanding: AP link quality over a
set-length window.** The AP works and the display runs over it, but nobody has watched the heartbeat
for gaps long enough to trust it. **Item 45.**

⚠️ **Blocked by the wifi section above** — it needs the access point up, which kills the
house-network link the roam capture depends on. It is the one piece of work that has to wait for
that capture to be spent.

---

## Open design questions the phase must settle

Not open questions in the old sense — decisions `u_map`'s new shape forces.

| Question | |
|---|---|
| **Is the mapping table persisted?** | "Author what a fader means" implies data, which implies `u_state` — and it would be the **first real in-patch user of the `manual` policy**, which today ships exercised only by a gate and a synthetic contributor. ⚠️ **The synchronous-answer rule is the one part a contributor can break invisibly**: an answer from behind a `[del]` is silently absent from the file, and the failure is a short file rather than an error |
| **The six mode names are placeholders, and their ratio is load-bearing** | `u_err` routes on `compose` / `perform`, so **a split weighted toward `perform` would make most mode selections silently quieten the error display.** Making the modes real means deciding this deliberately, not cosmetically |
| **What does CC 99 show?** | Cheap to build, and undecided. Candidates: transport state, link health, record-armed |
| **Is a purely-outbound file still an `m_` file?** | `m_` is defined as *device events → named controls*, and the Volca has no events. The prefix still reads correctly as "the file that owns this device"; state the answer rather than letting it drift |

---

## Risks carried into v0.3

**The `m_` layer is the one boundary genuinely expensive to retrofit.** ✅ `u_map` keeps it honest
today — and **v0.3 is exactly where the pressure to break it arrives**, because it is when controls
start meaning things.

⚠️ **Table-driven mapping is the one place this plan bends a convention**, and the allowlist guard
is the whole of what buys it back. Losing it is silent.

**Timing is architectural.** Grain clocks must be audio-domain from the first line, and ⚠️ **nothing
downstream may assume the global `clock` is its clock** — Cut It runs poly-tempo, and each part owns
a `c_clock` instance.

**The DSP budget is where the headroom went, not the MIDI.** ✅ Isolated two ways: DSP on 11.8 %,
DSP off 4.9 % — the DSP costs **6.9 points** and the MIDI **0.43**, wrong by a factor of sixteen. A
marginal `c_clock` is 0.43 points, so **poly-tempo is cheap and the base graph is not.** Less binding
now the filter stages are deferred, but it is the baseline v0.4 stacks four stages onto. Item 75.

---

## Corrections owed to the docs

**Recorded here; the edits belong to the documentation refactor that follows this plan.**

| Correction | |
|---|---|
| ⛔ **Bank B's flat 127 is FALSE, not unexplained** | **All banks send real velocity once velocity is enabled.** [ref-midi.md](ref-midi.md) and [plan-tests.md](plan-tests.md) item 205 both still record it as an unexplained residue with a "cheap next test if it ever matters". **It has been checked. Close it** |
| ⚠️ **[CLAUDE.md](CLAUDE.md) says `wifi-report.sh (--mark FIRST)`** | The script's own header and [ref-hardware.md](ref-hardware.md) both say to run `--mark` **after** a finding is written up. **The script wins**; CLAUDE.md is wrong and would silently defeat the mark's whole purpose |
| ⚠️ **[plan-tests.md](plan-tests.md) item 13 links to *"Do this first"* in this file** | That section did not exist. It does now, and it is about the wifi — so the link resolves to the wrong thing and should be re-pointed at [ref-software.md](ref-software.md)'s *Mic goes into the 404* |
| ⚠️ **CLAUDE.md describes this file as "the four filter stages, and every open question"** | Stale as of this rewrite |

---

## What this plan deliberately does not carry

**Recorded so none of it is rediscovered as news.**

| | Why |
|---|---|
| **The four filter stages** — `e_chop`, `e_pitch`, `e_trem`, `e_verb` | v0.4. They are the instrument, not the blank slate. ⚠️ **Grain timing is audio-domain from the first line** when they do land — `phasor~` and `vline~`, never `metro`/`line~`. Retrofitting that is the expensive mistake v0.2 exists to prevent |
| **The drum mode**, and compose-mode capture | v0.4. ✅ The `time, note, velocity, duration` format is already decided ([ref-software.md](ref-software.md)) and the 404 can fill every field of it (item 205), so neither is blocked — they are simply not this phase |
| **The mic-bleed capture guard** | v0.4, with capture. ⚠️ A live vocal is baked into any drums-channel buffer sampled while the mic is hot. Cheap then, annoying later |
| **Footswitch / expression pedal** | `mother.pd` exposes `fs` and `exp`, one or the other, not both. Still the obvious control to reach for when both hands are busy |
| **nanoKONTROL scenes** | Four scenes exist but switch locally, so Pd is never told — hidden state. If ever used, assign **distinct CC numbers per scene** so Pd infers the active one |
| **A pre-set checklist for the 404** | Its hidden menu state — ExtIn monitoring, bus assignments, input FX — is the remaining "wrong knob" risk in the rig |
| **Save New** | ⛔ Dropped in Phase 8. Presets are records inside the store, not duplicate patch folders |
| **Guided Access on the phone**, a dynamic microphone, OLED legibility at arm's length (item 39), Novation Components' onboarding drive | Real wants, none of them this phase. The `mount.sh` guard already handles the onboarding drive and is verified across a cold boot |
| **LINE IN R-only behaviour**, **ground loops**, **404 round-trip latency** | An upgrade path, not a requirement; deal with hum if and when you hear it; and latency is perform-time tuning that needs a working patch first. ⚠️ **Don't buy a ground-loop isolator pre-emptively** — but know it is the cause if hum appears, rather than chasing a bad cable |
| **CPU headroom** | Not a real risk at this scale — but see *Risks* above, because v0.4 is the first thing to actually spend it |
