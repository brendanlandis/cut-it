# Cut It v0.3 — the instrument itself

**This is the only plan document in the project.** Every open question, unverified claim,
purchase and deferred decision lives here. The `ref-*` documents state what *is* and mark
uncertainty ⬜, but they carry no plans — when something there is unverified, the work to resolve
it is below. [plan-tests.md](plan-tests.md) is the evidence ledger: numbered checks with their
measured results, cited bare as "item 133" across the whole project.

✅ **v0.2 is complete.** Nine abstractions, four display surfaces, three headless gates and six
benches, all verified on hardware. What it does *not* do is make an interesting sound — it passes
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
| **4** | **`m_404`** | Blocked on the pad-note-range sweep below, and on power |
| **5** | **The drum mode** | The first real user of `u_state`'s **`manual`** policy — beats, progressions, kits |

**`u_state` is ready for all of it.** A contributor names its own key and declares its own policy;
nothing in `u_state` changes to add one. See [ref-conventions.md](ref-conventions.md) → *`state` —
the persistence bus* for the contract, and ⚠️ **the synchronous-answer rule**, which is the one
part a contributor can break invisibly.

---

## Do this first — it silently corrupts work

**SP-404 pad note range.** Measured 47+*n* here; Roland's chart says 35–51. **Only pads 1 and 2
were ever checked.** Sequencing code written against the wrong range *looks correct* and triggers
the wrong pads — there is no error, just wrong drums. **Sweep all 16 with `tools/midi-drive.pd`
before writing a line of `m_404`.** Items 5 and 95.

**Full-load power.** ✅ Two controllers plus the wifi dongle held up across two sessions, a 25-step
bench, a hot replug and sustained 500 BPM. ⬜ **The SP-404 has never been powered alongside them.**
⚠️ A marginal hub presents as *intermittent MIDI dropouts*, not an obvious failure — **suspect
power before code.** Blocked by the cable shortage below.

### The last thing that could force a redesign

**How the 404 places external input in the stereo field.** ✅ The Organelle's own TRS split is
verified — `inL` is the tip, `inR` the ring, genuinely independent — but the 404's *internal*
routing of its external input is not, and no amount of Mac testing reaches it. Blocked on the TRS
Y-cable. Procedure: [plan-tests.md](plan-tests.md) Session 3, items 12–13.

---

## The wifi fault — items 81, 133, 146–149

⚠️ **The one fault that could take the phone display down mid-set**, and it has been open since
Phase 6 and misdiagnosed for two of them. **A watcher runs on the device** (`/sdcard/wifi-watch.sh`)
and `tools/wifi-poll.sh` runs on the Mac; between them the next failure is captured without anyone
watching.

### Established — do not re-derive, and do not contradict without evidence

- ⚠️ **The device stays ASSOCIATED.** Same BSSID, and **−35 dBm** when it failed. *"The Organelle
  drops its wifi"* is the wrong mental model and sent this at the dongle for two phases.
- ⚠️ **What it loses is the IPv4 lease.** No address, no default route, **empty ARP table** — while
  the patch ran on happily for six hours with the meters moving.
- ⚠️ **SSH KEEPS WORKING** over IPv6 link-local via mDNS. **A successful login is not evidence the
  network is up.** The check is `ip addr show wlan0 | grep "inet "`.
- ⚠️ **`dmesg` gives the trigger and it is not lease expiry**: `cfg80211: Calling CRDA` then a full
  authenticate/associate cycle immediately before the address goes. **The link re-associated and
  never re-acquired an address.**
- ✅ **`dhcpcd` cannot persist a lease here** — the rootfs is read-only, `/var/lib/dhcpcd/` is
  unwritable, and there is **no lease file for the current SSID**. `dhcpcd` is **6.9.3** (2015),
  with `option rapid_commit` and `noipv4ll`.
- ⚠️ **All three recovery rungs failed.** Only a reboot clears it.

**And one thing that is NOT established: the cause.** Item 81 has blamed the dongle, power, the
access point and `wifi_control.py` at various times, on no evidence. **Do not add a fifth guess.**

### The decision tree — read the probe's verdict first

`wifi-watch.sh` now runs a **link probe before the recovery ladder**: it assigns the last-known-good
address and route and pings the gateway. That test is what splits the tree, and it had never been
run.

| Probe verdict | Meaning | Do next |
|---|---|---|
| **LINK IS FINE** | traffic flows on a static address — radio, association and path all healthy; only *address acquisition* is broken | ⚠️ **A card swap would prove nothing.** Go at `dhcpcd`: check 6.9.3's known renewal bugs, try `--dbdir /sdcard/dhcpcd` so a lease can persist, and try disabling `rapid_commit` |
| **LINK IS DEAD** | associated, but nothing passes even with addressing removed from the question | ✅ **Now** swap the spare USB wifi card. This is the driver/firmware branch it was reserved for |
| **SKIPPED** | the guard fired, or no good address was recorded yet | Inconclusive — say so rather than reading anything into it |

Rung-by-rung, if the ladder *does* recover it: **rung 1 (renew)** means the lease expired and
renewal never fired — compare uptime-to-failure against the router's lease time, and ⚠️ note it
contradicts item 133, where a hand-run renew did *not* work. **Rung 2 (`dhcpcd -k` + restart)**
means `dhcpcd` was wedged, and a watchdog that restarts it on loss of IPv4 is a real, small fix.
**Rung 3 (`wpa_supplicant` restart)** means the association was stale while *looking* healthy —
⚠️ that partly contradicts item 133's headline, so re-check the evidence before concluding.

### Regardless of branch

- **Compare uptime-to-failure against the router's DHCP lease time.** A match is close to
  conclusive; a mismatch rules lease expiry out. The log's 30-minute heartbeats give the timing.
- **Check whether it clusters around heavy USB activity.** Item 95 (full-load power) is still open,
  and if the two correlate they may be one item.
- ⬜ **One observation, unexplained:** the device needed a retry to rejoin wifi after the Phase 8
  power cycle. One occurrence, no evidence attached — recorded so it is not misremembered.

### Do not

- **Do not swap the wifi card first** — it is the last test, for the reason above.
- **Do not conclude from a single failure.** One data point cannot separate "the lease expired"
  from "`dhcpcd` wedged once".
- **Do not trust `ssh` as a reachability check.**
- **Do not run two watchers.** Use the pidfile, or `ls -l /sdcard/wifi-watch.alive`. ⚠️ **Never
  `pgrep -f wifi-watch`** — it matches the ssh command doing the checking, and a `/proc` scan has
  exactly the same flaw. That has now cost time twice.

### Recording it

New items in [plan-tests.md](plan-tests.md) **after the last used number**, and **items 81 and 133
updated in place** rather than a third entry saying something slightly different. ⬜ **That in-place
merge is still outstanding.** If it is fixed, [ref-hardware.md](ref-hardware.md) gains the mechanism
and this section goes. ⚠️ **If it is NOT fixed, say so plainly and leave it open** — a wrong
confident answer costs more than an open question, which is exactly how this ran for two phases.

---

## Open questions

### From Phase 8, and cheap to close

| Question | Where it stands |
|---|---|
| **Does a saved `knobs.txt` beat the PHYSICAL knob position at boot?** | ⬜ Both are pushed at load and which wins was never measured. Knob 1 is master tempo, so this decides what BPM the patch boots at once a Save has happened. **Cheap:** Save, move knob 1 well away, reload, read the footer |
| **Can a captured sample be written without glitching the audio?** | ⬜ Measured **without DSP**: 2 s = 6.1 ms, 10 s = 29 ms, 30 s = 85 ms. An 85 ms *synchronous* `soundfiler` write sits on Pd's message thread with audio live and would very likely glitch. `writesf~` writes from a helper thread; or capture writes at capture time. **Gates the sampler.** Item 142 |
| **The `manual` policy has no in-patch user** | Proven by the gate and a synthetic contributor, but nothing on the instrument drives it. The drum mode is the first. Not a fault — stated so it is not mistaken for tested-in-anger |
| **Parameter pickup** | ⬜ Left Phase 8 when state was reframed as *content*. The stored value is shown and used until the physical control passes through it. **Design it together with the OLED tick below** — both need the same per-control "value at first touch" |

### Display and UI — v0.3 design work

Phase 4 made the display *correct*; it is not yet *good*.

| Wanted | Note |
|---|---|
| **Sliders instead of numbers** | A bar reads faster than a number. `gFillArea` already draws the meters, so the drawing is solved — what is not is how a bar and a name share 128 px, and what five stacked ones look like |
| **Show where the control was when the edit began** | A tick at the value the fader held when you first touched it. Needs a per-control "value at first touch" — cheap, since the param store already keys by name |
| **Are the 16px and 8px rows legible at arm's length?** | ⬜ A judgement, not a test, and the last undecided thing about the display. All three layouts have been *rendered* on the device (item 80) but watched for correctness rather than read. Item 39 |
| **Buttons should not display `1`** | The `1` is a placeholder for "pressed". Resolves itself once `u_map` gives buttons meanings |
| **`g_grid` lights LED index 10 before the first beat** | ⬜ The beat store starts at 0 and `0 + 10` is a ring button, so the first painted frame carries a stray white light. **Cosmetic and Mac-only** — on the device beats flow long before ownership rises. **One box to fix: seed the store at 1.** Found by `phase6-assert.sh`, which reports it as a NOTE |

### Hardware and device behaviour

| Question | Where it stands |
|---|---|
| **Does the MIDI Config page re-open mother's MIDI gates?** | ⬜ `u_init` closes both gates 2 s after load, beating mother's own push. Entering *MIDI Config* mid-session may push them again — reopening the CC 21–26 collision that made a nano button toggle the transport (item 76). **Cheap: open the page, leave it, press `btn-t-5`** |
| **Does the 404's *pattern playback* transmit notes?** | `SEQ Note Out` is on and pad presses transmit, but no pattern has been captured. Determines whether the 404 is a compose-time authoring surface. Watch for the reported stray continuous C |
| **Can Pd emit an OSC blob?** | ⬜ Gates `gWaveform` and `gFrame`, and therefore gates ever drawing the captured buffer — which is what would stop playhead placement being blind |
| **`[midiout]`'s port creation argument** | ⬜ and **unneeded** — `u_tempo` uses the proven cold-inlet pattern and item 63 fired a real 404 pad through it. ⚠️ **The obvious experiment is invalid**: Pd 0.49 does not warn about extra creation arguments at all, so a clean syntax check proves nothing |
| **Can Novation Components disable the onboarding drive?** | Untried. A cleaner fix than the `mount.sh` guard, since it changes nothing on the Organelle |
| **CC 99, the Launchpad's top-right corner** | ⬜ The one ring button never pressed. Nothing needs it |

### Settled, and recorded so they are not reopened

- ✅ **Does mother stream knob positions, or send on movement?** **Moot** — the `[change -1]` guard
  is staying either way, and no test can separate the two through it. Item 68.
- ✅ **`/led/flash`** exists in the `mother` binary and is unreachable through `mother.pd`.
  Deliberately unused: it needs raw `oscOut`, and `g_oled` is that name's sole owner.
- ⚠️ **A panic blanks the Launchpad until reload.** Deliberate and currently harmless — nothing on
  the Organelle sends `panic`. Revisit only if it becomes performer-reachable; the escape hatch is
  worth more than the display.
- **The six modes are placeholders.** Six message boxes in `u_map`. ⚠️ The **ratio** is not
  arbitrary: `u_err` routes on `compose`/`perform`, so a split weighted toward `perform` would make
  most mode selections silently quieten the error display.

---

## Stage-readiness

✅ **Three of four counts are closed.** Rate limiting and the `nbx` chrome went with Phase 7; the
Organelle-hosted access point is configured and proven end to end — the venue sequence is in
[ref-hardware.md](ref-hardware.md).

**One thing left, and it is not code: phone hardening.** Auto-Lock Never ✅. **Guided Access still
to set** — it pins the phone to one app and kills the home gesture, so a stray swipe cannot drop
you out of the scene mid-set. That is the real risk on a phone lying on an amp.
⚠️ **Do Not Disturb is no longer needed** — the access point lets the phone sit in **airplane
mode**, which suppresses notifications at the source. A phone *hotspot* could not have done this,
which is why hosting the network on the Organelle was the right call.

**And an untested one:** ⬜ AP link quality over a *set-length* window. The AP works and the display
runs over it, but nobody has watched the heartbeat for gaps long enough to trust it. Item 45.

---

## Still to acquire

| Item | For |
|---|---|
| **1/4" TRS male → 2× 1/4" TS male** (insert cable) | ⚠️ **The critical cable in the rig** — nothing else merges the 404's two outs into the Organelle's single input jack. **Blocks Session 3, which is the last thing that could force a redesign** |
| **Class-compliant USB→DIN MIDI interface** | The Volca FM. Roland UM-ONE mk2 in its class-compliant "TAB" position, iConnectivity mio, or similar. Phase 5 makes it worth buying — clock and note-out have somewhere to go once it exists |
| **Dynamic microphone** | Dynamic rather than condenser: better SPL handling and far better feedback behaviour where a mic feeds a processor that feeds the PA |

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
