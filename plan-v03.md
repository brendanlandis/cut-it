# Cut It v0.3 — the instrument itself

**This is the only plan document in the project.** Every open question, unverified claim,
purchase and deferred decision lives here. The `ref-*` documents state what *is* and mark
uncertainty ⬜, but they carry no plans — when something there is unverified, the work to resolve
it is below. [plan-tests.md](plan-tests.md) is the evidence ledger: numbered checks with their
measured results, cited bare as "item 133" across the whole project.

✅ **v0.2 is complete.** Sixteen deployed abstractions (plus `u_mother-stub`, which is Mac-only),
four display surfaces, three headless gates and six benches, all verified on hardware. What it does *not* do is make an interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. **v0.3 is the sound.**

Read [ref-conventions.md](ref-conventions.md) before writing any Pd, and
[ref-build-log.md](ref-build-log.md)'s corrections before trusting any plan — including this one.
Every phase so far produced at least one correction to something a plan asserted.

---

## The shape of v0.3

| | What | Notes |
|---|---|---|
| **1** | **The four filter stages** — `e_chop`, `e_pitch`, `e_trem`, `e_verb` | They go in the gap in `u_root`, right to left, wired not sent. ⚠️ **Grain timing is audio-domain from the first line** — `phasor~` and `vline~`, never `metro`/`line~`. Retrofitting that is the expensive mistake v0.2 exists to prevent |
| **2** | **`u_map` gives the controls meanings** | 42 controls are published and mapped to nothing. This is where that changes, and it is the only file allowed to decide it |
| **3** | **Compose-mode capture** | The `time, note, velocity, duration` event format is decided ([ref-software.md](ref-software.md)). Needs the mode system exercised first, which Phase 6 delivered |
| **4** | **`m_404`** | ✅ **Fully unblocked** — the device is characterised in [ref-midi.md](ref-midi.md), both directions. ⚠️ **Ships with a hard rate limit**, not as a later fix |
| **5** | **The drum mode** | The first real user of `u_state`'s **`manual`** policy — beats, progressions, kits. ✅ The 404 can author dynamics end to end, so capture can fill every field of `time, note, velocity, duration` |

### ⚠️ Three measured constraints that bind what gets built

**The devices are characterised and nothing built needs changing** — `u_tempo`, `c_clock` and
`g_grid` were all stress-tested and are right. **The four rate ceilings are in
[ref-midi.md](ref-midi.md)** → *The four rate ceilings*; what they bind on the work still to do:

| Constraint | Consequence for v0.3 |
|---|---|
| **`c_clock`'s BANG outlet caps at 14.3/s** | ⛔ **A dense trigger stream cannot come from `c_clock` as built** — it needs a plain `[metro]`. Decide this per part *before* wiring the drum mode to the clock |
| **MIDI triggers cap at ~360–400/s** | **`m_404` ships with a hard rate limit**, not as a later fix. Overshoot costs seconds of lag that outlive the gesture |
| **The OLED lags ~200 ms; the Launchpad does not** | **Rhythmic feedback goes on the Launchpad.** This rules out a moving playhead on the OLED, which the display work below would otherwise reach for |

✅ **And the audio-rate path has no ceiling at all** — `e_chop` reads `c_clock`'s phase as a signal
and never converts it to bangs. **The ceilings are message-domain only.**

⬜ **One thing left unmeasured:** whether the MIDI limit is **per-device or aggregate**. `g_grid`
emits ~3320 bytes/s at 600 BPM against the clock's 480, so at extreme tempos the grid and the
triggers may contend — or may not, if each device has its own budget. Item 210.
⚠️ **The isolating test needs the Launchpad unplugged**, which triggers `m_launchpad`'s watchdog
and its `wire.sh` recovery — adding forks and noise to the very thing being measured. **Nothing
currently depends on the answer**; it matters only if the drum mode ever runs dense triggers and a
live grid together.

**`u_state` is ready for all of it.** A contributor names its own key and declares its own policy;
nothing in `u_state` changes to add one. See [ref-conventions.md](ref-conventions.md) → *`state` —
the persistence bus* for the contract, and ⚠️ **the synchronous-answer rule**, which is the one
part a contributor can break invisibly.

---

## The wifi fault — what is still open

⚠️ **The one fault that could take the phone display down mid-set.** ⏳ **Everything actionable has
shipped; what remains is time.**

**What is known, the repro, the ruled-out branches and how to operate the watcher are all in
[ref-hardware.md](ref-hardware.md)** → *The roam fault*. Only the open work is here.

### The requirement: ZERO drops during a set

**A wifi drop mid-set is not acceptable at any recovery speed.** Even a perfect 20-second recovery
is twenty seconds of a dead phone display in front of an audience, and the display is what tells
you the instrument is alive. **The target is that it does not happen, not that it heals.**

✅ **On stage that is already true structurally** — the Organelle *hosts* the network, so there is
no association to hand off and no lease to acquire. ⚠️ **But immunity to this fault is not proof
the stage link is solid**: AP-mode stability over a set-length window is still ⬜ unmeasured
(item 45), and it only holds if the venue sequence is actually followed.

### ⏳ Shipped, and now waiting on evidence

| | |
|---|---|
| **Ladder reordered**, `wifi-reassociate.sh` first at 90 s | ✅ deployed |
| The two `dhcpcd` rungs demoted, not deleted | ✅ deployed |
| DHCP-probe verdict reworded | ✅ deployed |
| Orbi firmware 2.7.5.6 → 2.7.6.6 on both units | ✅ done |
| **Preferred-AP steer** — built, measured firing in 13 s | ⛔ **deployed but OFF by default** |

⛔ **The steer is off ON PURPOSE, and this is the subtle part.** It works, but it drops IPv4 every
time it fires — trading one rare long outage for frequent short ones — **and it keeps the device
off the satellite, so the fault could never recur and the firmware update could never be evaluated.
The prevention masks the experiment.** Item 189. Re-enable with:

```sh
PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh
```

**The open task is to leave the watcher running and let days pass.** If `transitions` stays at 0
across normal roaming, that is real evidence 2.7.6.6 fixed it. ⚠️ **A quiet day is NOT proof** —
the pre-update capture went **13 h 32 m** before firing. It was never periodic.

⬜ **If it recurs post-update**, the next places to look are the satellite's **backhaul health** and
the router's **2.4 GHz auto-channel** behaviour — a channel change is a re-association event for
every 2.4 GHz client, the same trigger class. ⚠️ Both need the Orbi admin UI; neither is visible
from the instrument.

⬜ **And whether the repro survives a reboot is unverified** — `wpa_cli` needs a supplicant started
with a `ctrl_interface`, and the one running now is `wifi-reassociate.sh`'s.


## Open questions

### From Phase 8, and cheap to close

| Question | Where it stands |
|---|---|
| **Parameter pickup** | ⚠️ **No longer hypothetical — item 200 made it a boot-time fact.** A saved `knobs.txt` **beats the physical knob**, so after any Save every knob is desynced from its value and **the first touch jumps by up to the full range** — measured as a 443 BPM lurch. **Nothing on the instrument can detect it**: mother reports position, not whether the position still matches the file. The stored value is shown and used until the control passes through it. **Design it with the OLED tick below** — same per-control "value at first touch". ⚠️ `ref-hardware.md` settles **jump** for the nano's shift layer; defensible for a fader in your hand, much weaker for a boot-time lurch. **Two cases, decide separately** |
| **Can a captured sample be written without glitching the audio?** | ⬜ Measured **without DSP**: 2 s = 6.1 ms, 10 s = 29 ms, 30 s = 85 ms. An 85 ms *synchronous* `soundfiler` write sits on Pd's message thread with audio live and would very likely glitch. `writesf~` writes from a helper thread; or capture writes at capture time. **Gates the sampler.** Item 142 |

### Display and UI — v0.3 design work

Phase 4 made the display *correct*; it is not yet *good*.

| Wanted | Note |
|---|---|
| **Sliders instead of numbers** | A bar reads faster than a number. `gFillArea` already draws the meters, so the drawing is solved — what is not is how a bar and a name share 128 px, and what five stacked ones look like |
| **Show where the control was when the edit began** | A tick at the value the fader held when you first touched it. Needs a per-control "value at first touch" — cheap, since the param store already keys by name |
| **Are the 16px and 8px rows legible at arm's length?** | ⬜ A judgement, not a test, and the last undecided thing about the display. All three layouts have been *rendered* on the device (item 80) but watched for correctness rather than read. Item 39 |
| **Buttons should not display `1`** | The `1` is a placeholder for "pressed". Not independent work — it resolves itself once `u_map` gives buttons meanings, so it rides with that rather than being tracked separately |

### Hardware and device behaviour

| Question | Where it stands |
|---|---|
| **Why does bank B send a flat 127?** | ⬜ **The one loose end from the 404 work, and nothing depends on it.** Every channel-2 (bank B) event was exactly 127 while bank A varied 3–104. ⛔ **"Fixed velocity is per-bank" is ruled out — the setting is global**, tested directly. So a global toggle was OFF and one bank was still flat, and it predates the toggle. **Cheap check: press bank-B pads by hand, no pattern involved.** Varying = stale sequencer data; flat = something bank-specific. Item 205 |
| **Does drawing the captured buffer work from inside Cut It?** | ⬜ Both halves are proven separately — `packOSC` emits a valid blob and `gWaveform` renders one (item 202) — but they have never been run as one path through `g_oled`. ⚠️ **Draw to a spare screen**: `g_oled` rebuilds screen 3 every 100 ms and would wipe it |
| **Can Novation Components disable the onboarding drive?** | ⬜ Untried. A cleaner fix than the `mount.sh` guard, since it changes nothing on the Organelle |
| **A status light on the Launchpad's logo** | ✅ **CC 99 is an LED, not a button** (item 198), and ⚠️ **`g_grid` already paints it** — its span is 1–108 — so it carries background dim today for nothing. **The only non-button LED on the surface**: an indicator there cannot be mistaken for something pressable, and it costs **one region branch and no extra SysEx**. Cheap candidate, not a question |

---

## Stage-readiness

✅ **Rate limiting, the `nbx` chrome and the Organelle-hosted access point are all done** — the
venue sequence is in [ref-hardware.md](ref-hardware.md). **Two things remain, neither of them
code:**

- ⬜ **Guided Access on the phone.** It pins the phone to one app and kills the home gesture, so a
  stray swipe cannot drop you out of the scene mid-set — **the real risk on a phone lying on an
  amp**. Auto-Lock Never is already set. ⚠️ Do Not Disturb is *not* needed: the access point lets
  the phone sit in **airplane mode**, which suppresses notifications at the source.
- ⬜ **AP link quality over a set-length window.** The AP works and the display runs over it, but
  nobody has watched the heartbeat for gaps long enough to trust it. **Item 45, and the last
  measurement of any kind still outstanding.**

⚠️ **Both need the access point up, which kills the house-network connection the wifi capture
depends on** — so they are the one piece of work that has to wait for the capture to be spent.

---

## Still to acquire

| Item | For |
|---|---|
| **Class-compliant USB→DIN MIDI interface** | ⚠️ **The only thing still blocking a device.** The Volca FM has no other path in — Roland UM-ONE mk2 in its class-compliant "TAB" position, iConnectivity mio, or similar. Everything the Volca needs is written and waiting: clock, transport and note-out all exist |
| **Dynamic microphone** | Dynamic rather than condenser: better SPL handling and far better feedback behaviour where a mic feeds a processor that feeds the PA. ⚠️ A mic was borrowed for item 13, so the *path* is proven — this is for owning one |

Ordinary cables — USB-A→C for the 404, TS patch cables, 3.5 mm TRS→2× TS for the Volca, XLR→1/4"
for the mic — are probably already in the box; the full list is in
[ref-hardware.md](ref-hardware.md). **Optional:** a *MeeBlip cubit duo* replaces the MIDI interface
and the original cubit in one box, worth it only if more DIN synths arrive. **Don't buy a
ground-loop isolator pre-emptively** — but know it is the cause if hum appears, rather than chasing
a bad cable.

---

## Deliberately deferred

| Deferred | Why |
|---|---|
| **Footswitch / expression pedal** | `mother.pd` exposes `fs` and `exp` on the pedal jack, one or the other, not both. Noted so it is not rediscovered as news; still the obvious control to reach for when both hands are busy |
| **nanoKONTROL scenes** | Four scenes exist but switch locally, so Pd is never told — hidden state. If ever used, assign **distinct CC numbers per scene** so Pd infers the active one from which CCs arrive |
| **A pre-set checklist for the 404** | Its hidden menu state — ExtIn monitoring, bus assignments, input FX — is the remaining "wrong knob" risk in the rig |
| **`u_map` as a `[text]` table** | The route-branch form is statically auditable and there are two mappings. ⚠️ A data-driven `[send]` could write any global name with no evidence on the canvas, which defeats an allowlist audited by reading. Revisit when the count passes about ten |
| **Save New** | ⛔ Dropped in Phase 8. Presets are records inside the store, not duplicate patch folders. This also deleted the `/tmp/curpatchname` problem, `! 2` folders and any `deploy.sh` change |
| **LINE IN R-only behaviour** | An upgrade path, not a requirement |
| **Ground loops** | Deal with hum if and when you hear it |
| **404 round-trip latency** | Perform-time tuning; needs a working patch first |
| **CPU headroom** | Not a real risk at this scale — but see *Risks* below, because v0.3 is the first thing to actually spend it |

---

## Risks carried into v0.3

**The `m_` layer is the one boundary genuinely expensive to retrofit.** If `e_chop` ever learns
that a nanoKONTROL exists, that is permanent. ✅ `u_map` keeps it honest today — v0.3 is where the
pressure to break it arrives, because that is when controls start meaning things.

**Timing is architectural.** Grain clocks must be audio-domain from the first line. ⚠️ And
**nothing downstream may assume the global `clock` is its clock** — Cut It runs poly-tempo, and
each part owns a `c_clock` instance. Retrofitting either is the expensive mistake v0.2 exists to
avoid.

**The DSP budget is where the headroom went, not the MIDI.** ✅ Isolated two ways: DSP on 11.8 %,
DSP off 4.9 % — the DSP costs **6.9 points** and the MIDI **0.43**, wrong by a factor of sixteen.
A marginal `c_clock` is 0.43 points, so **poly-tempo is cheap and the base graph is not**. v0.3
stacks four filter stages on that baseline. Item 75 and the Phase 6 correction.
