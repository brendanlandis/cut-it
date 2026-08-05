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
| **4** | **`m_404`** | ✅ **Unblocked** — the pad map is settled, and the 404 turns out to be a **160-pad** instrument: note 36–51 × bank-channel 33–42. Still ⬜ on full-load power |
| **5** | **The drum mode** | The first real user of `u_state`'s **`manual`** policy — beats, progressions, kits. ✅ The 404's pattern sequencer transmits, so it can author; ⚠️ but its pads are **fixed at velocity 127**, so nothing captured from them carries dynamics |

**`u_state` is ready for all of it.** A contributor names its own key and declares its own policy;
nothing in `u_state` changes to add one. See [ref-conventions.md](ref-conventions.md) → *`state` —
the persistence bus* for the contract, and ⚠️ **the synchronous-answer rule**, which is the one
part a contributor can break invisibly.

---

## Do this first — it silently corrupts work

✅ **SP-404 pad note range — SETTLED, and it was wrong.** All sixteen pads, both directions:
**the range is 36–51**, ascending from the bottom-left four per row (the standard MPC/GM drum
grid). ⛔ **`47 + n` held only for pads 1–4** — pad 5 is 44, not 52 — which is exactly the silent
corruption this entry warned about. Receive and transmit share one map, and nothing outside 36–51
is addressable. Full detail in [ref-midi.md](ref-midi.md); items 190–194.

⚠️ **And pad velocity is FIXED at 127**, not real — so patterns captured from the 404's pads carry
no dynamics. That is a constraint on the drum mode, not a blocker. Item 193.

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

## The wifi fault — items 81, 133, 146–189

⚠️ **The one fault that could take the phone display down mid-set**, and it has been open since
Phase 6 and misdiagnosed for two of them. **A watcher runs on the device** (`/sdcard/wifi-watch.sh`)
and `tools/wifi-poll.sh` runs on the Mac; between them the next failure is captured without anyone
watching.

### Where this actually stands, 2026-08-05 — narrowed, not solved

**The fault is a ROAM breaking a RUNNING `dhcpcd`.** Items 169–183. ⚠️ **Two tempting conclusions
were reached and then overturned in the same session; both are recorded so neither is
re-derived.**

**What is established:**

- ✅ **The trigger is an association change.** The device roams between the two `hildegard` APs
  and a `dhcpcd` that was running across that change never re-acquires. `dmesg` shows the full
  `CRDA` / authenticate / associate cycle each time.
- ✅ **The link is never the problem.** A static address reaches the gateway with **0% packet
  loss**, on either AP.
- ✅ **A fresh `dhcpcd` on a SETTLED association succeeds — on EITHER AP.** Flush, associate, let
  it settle, then start `dhcpcd`: an address arrives on the first DISCOVER, in seconds. That is
  why only rung 3 ever worked.
- ✅ **The erratic interval** — 2 h 09 m, 3 h 12 m, 13 h 32 m — is *how long until the AP hands the
  device off*. ⛔ **Never a timer, never lease expiry.** Stop asking for the router's lease time.
- ✅ **It reproduces on demand** — see below. This is the single most useful thing gained.

**What is NOT established:** ⬜ **why a running `dhcpcd` cannot re-acquire after a roam.** Say so
plainly rather than filling the gap.

### ⛔ Two dead ends, recorded so they are not walked again

- ⛔ **"The Orbi satellite is broken."** Built on one satellite-fails-then-router-succeeds pair,
  and **overturned thirty minutes later** when a controlled two-arm test leased an address twice
  on the satellite, in seconds. ⚠️ **Concluding from a single success is the same error as
  concluding from a single failure** — this file forbids the second and the first slipped through
  anyway. Item 182.
- ⛔ **`option rapid_commit` and `require dhcp_server_identifier`.** Tested directly: the control
  arm passed with the stock config, so there was nothing for the treatment to fix. Item 182.
- ⛔ **The ARP duplicate-address probe / `noarp`.** The exchange never reaches it.
- ⚠️ **And the "REQUEST is never ACKed" evidence is weaker than it looked** — that capture was cut
  off by my own `timeout 20` with the retry schedule still running, *and* it ran on the router
  after a failed roam. Item 183.

### ✅ The repro — the thing that makes the rest tractable

```sh
wpa_cli -i wlan0 scan ; sleep 4      # ⚠️ required: roam only targets a cached BSS
wpa_cli -i wlan0 roam <other-bssid>  # IPv4 gone within 3 s
```

⚠️ **Needs a supplicant started with a `ctrl_interface`**, which `wifi-reassociate.sh` writes and
a boot-started one may not. ⬜ Unverified after a power cycle.

⚠️ **`dhcpcd -T` is weaker evidence than the watcher's wording claims.** Test mode **stops at the
OFFER** and never sends a REQUEST, so it exercises only the half that works. Its verdict *"the
server answers, so the daemon is wedged"* overstates what it measured and should be reworded.

⛔ **The spare USB wifi card stays off the table** — the same radio leases fine on both APs.

### ✅ `dhcpcd` IS EXONERATED — it behaves correctly and nothing answers it

Caught in full with `-d` running **through** a roam (item 184) — the observation nobody had made,
because ⚠️ **`syslogd` is not running on this device and `dhcpcd`'s diagnostics had gone nowhere
for the entire investigation:**

```
soliciting a DHCP lease
sending DISCOVER ×3    (4.5s, 7.1s, 15.7s)     <- no OFFER, ever
carrier lost  ->  NOCARRIER  ->  EXPIRE         <- correctly deconfigures
carrier acquired
sending DISCOVER ×5    (4.1 … 64.4s)           <- no OFFER, ever
```

It detects the carrier going, deconfigures through its own hooks, detects re-acquisition,
re-solicits at once, and backs off correctly. **It is not wedged, confused or misconfigured.**
⚠️ **And the failure is at DISCOVER, not REQUEST** — which also retires item 180's framing.

### ⚠️ A successful recovery presents exactly like a continued failure

**Recovery changes the IP address**, and the Mac does not notice. The device came back healthy on
`.20` while mDNS still resolved `organelle.local` to the dead `.18` — so `wifi-report.sh` reported
*"Cannot reach"* about a device that was completely fine, and a power cycle at that moment would
have destroyed the live evidence.

**During a recovery window, check IPv6 before believing anything:**

```sh
ping organelle.local                  # 0% loss over IPv6 == the device is ALIVE
ssh -6 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "root@fe80::<link-local>%en0"     # the zone id and the bypass are both required
```

The cache catches up within a few minutes on its own. Item 172.

### The requirement: ZERO drops during a set, and seconds — not minutes — in development

**A wifi drop mid-set is not acceptable at any recovery speed.** Even a perfect 20-second recovery
is twenty seconds of a dead phone display in front of an audience, and the display is what tells
you the instrument is alive. **The target is that it does not happen, not that it heals.**

### ✅ Why the stage is already structurally immune — and it is not mitigation, it is absence

**On stage the Organelle HOSTS the network. It is not a wifi client at all.**

`start-ap.sh` runs **`killall wpa_supplicant`** and then `create_ap --no-virt -n wlan0`. The radio
becomes an access point, the Organelle becomes the **DHCP server**, and the phone is the client.

| Fault requires | Present in AP mode? |
|---|---|
| A client association that can be handed off | ❌ no association — the radio *is* the AP |
| Another BSSID to roam to | ❌ nothing to roam to |
| `dhcpcd` acquiring a lease | ❌ the Organelle **serves** leases; it does not request one |

⛔ **Every link in the chain is absent, so the fault cannot occur in the venue configuration.**
That is why hosting the network was the right call for reasons beyond airplane mode.

⚠️ **The immunity is to THIS fault, not to all wifi trouble.** AP-mode stability over a
set-length window is still ⬜ **unmeasured** — item 45, and it is the one stage-readiness count
left. **Do not read "immune to the roam fault" as "the stage link is proven."**

⚠️ **And it only holds if the venue sequence is actually followed.** Running a set on house wifi
puts the Organelle back in client mode and the fault back on the table, with **no fix that makes
it impossible.** If that is ever unavoidable, pin the BSSID first.

### ✅ The Orbi firmware was a release behind — now updated

The kit is an **Orbi RBK40**: RBR40 router + RBS40 satellite. ✅ Read with **no credentials** from
`http://192.168.1.1/currentsetting.htm` and `http://192.168.1.2/currentsetting.htm`, which return
model, firmware, device mode and uptime in plain text — the satellite is **192.168.1.2**.

⚠️ **The router's own updater reported "No new firmware version available" while 2.7.6.6 existed.**
Both units were on **2.7.5.6**; 2.7.6.6 (January 2026) had to be fetched from Netgear's KB and
applied by hand, per unit. ⚠️ **The satellite went flaky mid-update and needed removing and
re-adding.** Both now on **2.7.6.6**.

**Post-update, the satellite leased in 20 s.** ⛔ **That is one data point, not a fix** — the same
node leased fine before the update too (item 182). **The fault was already intermittent, so a
single success cannot separate "fixed" from "currently working."** Item 188.

### ⏳ THE CURRENT STATE: waiting, deliberately

**Everything actionable has shipped. What remains is time.**

| | |
|---|---|
| **Ladder reordered**, `wifi-reassociate.sh` first at 90 s | ✅ deployed |
| The two `dhcpcd` rungs demoted, not deleted | ✅ deployed |
| DHCP-probe verdict reworded | ✅ deployed |
| **Preferred-AP steer** — built, measured working (13 s) | ⛔ **deployed but OFF by default** |
| Orbi firmware 2.7.5.6 → 2.7.6.6 | ✅ done |

⛔ **The steer is off ON PURPOSE, and this is the subtle part.** It works, but it drops IPv4 every
time it fires — trading one rare long outage for frequent short ones — **and it keeps the device
off the satellite, so the fault could never recur and the firmware update could never be
evaluated. The prevention masks the experiment.** Item 189. Re-enable with:

```sh
PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh
```

**So: leave the watcher running and let days pass.** If `transitions` stays at 0 across normal
roaming, that is real evidence 2.7.6.6 fixed it. If one appears, the report names the rung that
recovered it and how fast. ⚠️ **A quiet day is NOT proof** — the pre-update capture went **13 h 32 m**
before firing, and the interval has been 2 h 09 m, 3 h 12 m and 13 h 32 m. It was never periodic.

⬜ **Still unmeasured: whether the repro survives a reboot.** `wpa_cli` needs a supplicant started
with a `ctrl_interface`; the one running now is `wifi-reassociate.sh`'s, not a boot-started one.
Check `ls /var/run/wpa_supplicant/` after the next restart.

⬜ **And still unexplained: why nothing answers a DISCOVER on the satellite.** Intermittent, and
invisible from the Organelle. If it recurs post-update, the next place to look is the satellite's
**backhaul health** and the router's **2.4 GHz auto-channel** behaviour — a channel change is a
re-association event for every 2.4 GHz client, which is the same trigger class. ⚠️ Both need the
Orbi admin UI; neither is visible from the instrument.

⛔ **What is NOT worth doing any more:** `--dbdir /sdcard/dhcpcd`, disabling `rapid_commit`,
`noarp`, swapping the wifi card, and chasing the router's lease time. All were queued to explain a
lease that expires. **The lease does not expire — the association changes underneath it**, the
server answers, `dhcpcd` behaves correctly, and a non-periodic trigger cannot be a lease time.
That whole branch is deleted by measurement.

### Do not

- **Do not swap the wifi card.** Two link probes, 0% loss.
- **Do not power-cycle on a "cannot reach"** — check IPv6 first, or you destroy the evidence of a
  recovery that already worked.
- **Do not trust `ssh` or a tool's own error message as a reachability check.** Both have now
  misled this investigation.
- **Run `./tools/wifi-report.sh --mark` once a finding is written up**, or the report reads the
  same before and after the next failure.
- **Do not run two watchers.** Use the pidfile, or `ls -l /sdcard/wifi-watch.alive`. ⚠️ **Never
  `pgrep -f wifi-watch`**, and never let one command both scan and relaunch — that self-match
  kills the ssh session doing the sweeping. Item 163.

---

## Open questions

### From Phase 8, and cheap to close

| Question | Where it stands |
|---|---|
| **Does a saved `knobs.txt` beat the PHYSICAL knob position at boot?** | ⬜ Both are pushed at load and which wins was never measured. Knob 1 is master tempo, so this decides what BPM the patch boots at once a Save has happened. **Cheap:** Save, move knob 1 well away, reload, read the footer |
| **Can a captured sample be written without glitching the audio?** | ⬜ Measured **without DSP**: 2 s = 6.1 ms, 10 s = 29 ms, 30 s = 85 ms. An 85 ms *synchronous* `soundfiler` write sits on Pd's message thread with audio live and would very likely glitch. `writesf~` writes from a helper thread; or capture writes at capture time. **Gates the sampler.** Item 142 |
| **Parameter pickup** | ⬜ Left Phase 8 when state was reframed as *content*. The stored value is shown and used until the physical control passes through it. **Design it together with the OLED tick below** — both need the same per-control "value at first touch" |

**Not a question, recorded here so it is not mistaken for one:** the **`manual` policy has no
in-patch user**. It is proven by `phase8-assert.sh` and a synthetic contributor, but nothing on the
instrument drives it — the first will be compose-mode capture, where a captured pattern is exactly
a committed take. **A status, not a fault**, and it closes with no change to `u_state`.

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
| **Does the MIDI Config page re-open mother's MIDI gates?** | ⬜ `u_init` closes both gates 2 s after load, beating mother's own push. Entering *MIDI Config* mid-session may push them again — reopening the CC 21–26 collision that made a nano button toggle the transport (item 76). **Cheap: open the page, leave it, press `btn-t-5`** |
| **Can the 404's sequencer carry VELOCITY?** | ✅ Pattern playback transmits — 199 events, all in 36–51, so the 404 **is** a compose-time authoring surface (item 197). ⚠️ But every velocity was **127**, and that proves nothing: the pattern was recorded by *playing the pads*, which are themselves fixed at 127. ⬜ **TR-REC's per-step velocity is the untested thing** and decides whether the 404 can author dynamics at all |
| **Can the 404's pads be made velocity-sensitive?** | ⬜ Fixed at 127 as configured — a firm press and a deliberately soft one both reported 127 (item 193). Roland's pads are velocity-capable, so a device setting probably exists; **it was never looked for.** One look in the 404's menus |
| **Can Pd emit an OSC blob?** | ⬜ Gates `gWaveform` and `gFrame`, and therefore gates ever drawing the captured buffer — which is what would stop playhead placement being blind |
| **Can Novation Components disable the onboarding drive?** | Untried. A cleaner fix than the `mount.sh` guard, since it changes nothing on the Organelle |
| **A status light on the Launchpad's logo** | ✅ **CC 99 is not a button — it is an LED**, write-only (item 198). ⚠️ **`g_grid` already paints it**, since its span is 1–108, so it carries background dim today for nothing. **The only non-button LED on the surface**: a persistent indicator there cannot be mistaken for something pressable, and it costs **one region branch and no extra SysEx**. Cheap candidate |

### Settled, and recorded so they are not reopened

- ✅ **Does mother stream knob positions, or send on movement?** **Moot** — the `[change -1]` guard
  is staying either way, and no test can separate the two through it. Item 68.
- ✅ **`/led/flash`** exists in the `mother` binary and is unreachable through `mother.pd`.
  Deliberately unused: it needs raw `oscOut`, and `g_oled` is that name's sole owner.
- ✅ **`g_grid` lighting LED index 10 before the first beat is FIXED**, and this was listed as open
  long after it stopped being true. The beat store is seeded at 1 (`g_grid.pd`, `[f 1]` feeding
  `[+ 10]`), and `phase6-assert.sh` reports **29 checks, 0 failed, 0 notes**. The NOTE that found
  it no longer fires.
- ⬜ **`[midiout]`'s port creation argument is UNNEEDED, not open.** `u_tempo` uses the proven
  cold-inlet pattern and item 63 fired a real 404 pad through it. ⚠️ **The obvious experiment is
  invalid** — Pd 0.49 does not warn about extra creation arguments at all, so a clean syntax check
  proves nothing either way. Nothing needs the answer; it is here so the question is not reopened.
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
