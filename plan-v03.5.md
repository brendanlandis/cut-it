# Plan v0.3.5 — the venue kit

**Wifi, the phone and laptop-free debugging are one problem, not three.**

At a venue there is no house wifi — so the phone, which is the only thing in the rig with a real
screen and a touch surface, can only be reached if **the Organelle is its own access point**. And AP
mode is **structurally immune** to the roam fault that has been dropping the link for months, because
bringing the AP up kills `wpa_supplicant` and there is no association left to hand off.

So one decision answers three problems: make the AP the performance network.

⛔ **This plan depends on [plan-v03.4.md](plan-v03.4.md)**, which produces the presence data the
diagnostic screen displays. **Do not start it first.**

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.**
- ⛔ **Never open or save an Organelle-bound patch in plugdata.**
- **Vanilla objects only.**
- ⛔ **Never touch git.** Reading is fine. Brendan commits his own work.
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.**
- ⚠️ **Bringing the AP up kills the house link**, and with it your ssh session and every Mac-side
  tool. Plan each AP session to be self-sufficient before you start it.
- ⛔ **Never `pgrep -f wifi-watch`.** The pattern self-matches and kills the ssh session. **Bitten
  three times.**
- ⚠️ **The `critterandguitari/Organelle_OS` repo targets the M and S2, not this device.** Its paths
  are wrong here. Verify against the actual hardware.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** skill | ⛔ **Invoked, not read** | New Pd, in the instrument and in a standalone patch |
| The **`docs`** skill | ⛔ **Invoked, not read** | A new `ref/` page for the debug patch |
| [plan-v04.md](plan-v04.md) | §3 in full, especially *Debugging the rig with no laptop* | **Its design constraints are already written.** This plan answers them |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14`, and **C-5 is central here** |
| `git log` | **Grep it, never read it** | Git is the journal |
| The wifi material — a page of its own after [plan-v03.2.md](plan-v03.2.md), otherwise [ref/device-os.md](ref/device-os.md)'s wifi section | **All of it** | What is known, what was tried, the four wrong turns, the three-second reproduction. ⛔ **Two confident wrong answers are recorded there — read them before forming a third** |
| [ref/device/phone.md](ref/device/phone.md) | **All 288 lines** | The wire format, the rate limiting, the address discovery, and the one-way property you are about to change |
| `Cut It/u_net.pd` | **All of it, comments included** | You are adding an inbound path. Its comments hold the UDP-connect trap and the address-resolution timings |
| `Cut It/phone-ip.sh` | All 34 lines | **It already discovers the phone on the Organelle's own AP.** One build works on both networks |
| `tools/pdparty-scene/CutItRemote/_main.pd` | **All of it** | The scene you are adding buttons to. ⛔ Its staleness detector must stay phone-side |
| `tools/stage-patches/Start AP/main.pd` and `tools/stage-patches/Start AP/ap-up.sh` | **Both in full** | ⛔ **A documented dead end.** `ap-up.sh` opens with *"THIS APPROACH DOES NOT WORK"* and says why. **Read it before proposing `setsid nohup`** |
| `tools/stage-patches/AP Probe/main.pd` and `tools/stage-patches/AP Probe/ap-probe.sh` | Both | The pattern that **works**: a menu patch that logs to `/sdcard/` and instructs on the OLED |
| `Cut It/g_oled.pd` | Its route, the layers, the pick cascade and the text output | You are adding a selector. ⛔ **Add the matching one to `u_net.pd`'s route** or it reaches the phone as a nonsense parameter |
| [ref/device/organelle.md](ref/device/organelle.md) | The OLED graphics API, and the encoder facts | ⛔ A standalone menu patch may use the encoder; Cut It may not |
| [ref/module/display.md](ref/module/display.md) | The priority model and `Design` | The new layer has to fit it |
| `tools/wifi-watch.sh` | The three-rung ladder and the two probes | And its operating traps |
| [tools/README.md](tools/README.md) | The wifi section | The traps, stated more than once for a reason |
| `tools/oled-probe/main.pd`, `tools/osc-bridge/main.pd` | **Skim as working references** | They exist precisely for this |

**Do not read** `test/gate/` except the phone gate, or [ref/module/map.md](ref/module/map.md),
[ref/module/state.md](ref/module/state.md), [ref/module/tempo.md](ref/module/tempo.md).

---

## What is already true

### The wifi fault, narrowed

- ⛔ **The symptom is misnamed.** The device stays **associated** and loses its **IPv4 lease**.
  ⚠️ **SSH keeps working over IPv6 throughout, so a successful login proves nothing.** The check is
  `ip addr show wlan0 | grep "inet "`.
- **The trigger is a roam to a different BSSID**, and it reproduces in three seconds on demand.
- ✅ **`dhcpcd` is exonerated** — caught running through a forced roam: DISCOVER three times, **no
  OFFER, ever**. It detects, deconfigures, re-solicits and backs off correctly.
- ✅ **The link is never the problem** — a static address reaches the gateway with 0 % loss on either
  AP.
- **The outage is ~132 seconds**, measured.
- ✅ **The recovery ladder works unattended**; ⛔ **Orbi firmware 2.7.6.6 did not fix it**; channel 1
  was a real throughput win but **did not separate the two APs**.
- ⛔ **The preferred-AP steer is no longer a safe fallback** — one failure happened *on* the router.
- ⬜ **Why nothing answers a DISCOVER after a roam is NOT established.** That is a router-side
  question.

### The phone

- **One-way in practice.** Four Organelle→phone OSC addresses, none the other way, and the scene has
  no outbound sends. **`u_net` has no `netreceive` at all**, despite the docs claiming the Organelle
  listens on 9001.
- **`u_net` owns no selector on the display bus** — it subscribes and mirrors, which is why adding it
  cost the OLED's route nothing.
- ⚠️ **The staleness detector lives on the phone by necessity.** UDP is fire-and-forget; only the end
  that stops hearing can know. Its default label is `NO-LINK`, not `ok`.
- **The Organelle never waits for the phone.** Phone off, phone crashed, wifi gone — **the instrument
  plays identically.**

### The device as a computer

- ⛔ **A menu-launched patch has no console.** Pd runs `-nogui` and stdout goes to tty1, which VNC
  will not show. Every stage patch therefore logs to `/sdcard/` and instructs on the **OLED**.
- **Selecting a patch is itself a test**, more often than you would expect — loading one restarts Pd.
- ⛔ **A standalone menu patch may use the encoder and Cut It may not.** mother forwards `encbut`
  only after a patch sends `/enableEncoder`, and the instrument never does because **C-5 gives
  `g_oled` sole ownership of `oscOut`.** That is the difference between a menu of one screen and a
  menu you can navigate.
- ✅ **AP mode runs `killall wpa_supplicant`**, so there is no client association to be handed off.

---

## Phase 1 — the AP becomes the performance network

**The house wifi stays the development-time convenience with its existing recovery ladder. The AP
becomes what the rig runs on when it matters.**

### The blocker, and it is known

⛔ `tools/stage-patches/Start AP/` is a **documented dead end**. `create_ap`, `hostapd` and `dnsmasq`
all die with the Pd that spawned them, **even behind `setsid nohup`**. Read `ap-up.sh` before
proposing anything.

Options to evaluate, in rough order of how well they survive a power cycle at a venue:

1. **A boot-time service** — the AP is simply up when the device is on. Strongest, and needs the
   read-only root remounted to install.
2. **A front-panel path** alongside the factory `wifi_control.py`, so it is selectable with no
   laptop.
3. **A true double-fork** that genuinely detaches from Pd.

⚠️ **Probe before choosing.** The dead end above is exactly what happens when this is reasoned rather
than measured.

### What it closes for free

- **Item 45 — AP link quality over a set-length window.** ⚠️ It *"needs an actual set's duration to
  mean anything"*, and this plan's acceptance test is a set's duration. **Closed by construction.**
- **The venue case for the phone**, which the rest of this plan depends on.

⚠️ **AP mode is immunity to one fault, not proof the stage link is solid.** Measure it; do not assume
it.

---

## Phase 2 — the house fault, with a stated stopping point

Everything on the device side is exonerated. **This is a router-side problem**, so attack it from the
router.

Two configuration attacks, in order:

1. **Separate the two APs** so a roam stops being possible — distinct SSIDs, or per-band channel
   separation. ⚠️ **One Orbi setting moves both mesh nodes**, which is why this has not been trivial.
2. **Disable fast roaming / band steering** if the Orbi exposes them.

⛔ **The stopping rule, and it is binding: if two configuration changes do not stop the roam, close
item 81 as won't-fix and let AP mode be the answer.** The requirement was never *"recover fast"* — it
was *"stop dropping"* — and AP mode satisfies it by construction. ⚠️ Continuing past that point has
already produced two confident wrong answers.

⚠️ **Do not re-enable the preferred-AP steer as a fallback.** It drops IPv4 itself on every fire, and
**it hides the answer** by preventing recurrence.

---

## Phase 3 — Tier 1: diagnostics inside Cut It

**The highest-value piece, because it needs nothing plugged in and no mode change.**

A new layer on the OLED, fed by [plan-v03.4.md](plan-v03.4.md)'s presence data: **which device was
last heard, and how long ago.**

- One new selector on `g_oled`'s route, one layer flag and TTL, one link in the pick cascade, one
  draw subpatch writing through the existing text API.
- ⛔ **Add the same selector to `u_net`'s route**, or it reaches the phone as a nonsense parameter.
- ⚠️ **It must fit the existing priority model** — alert above modal above param above home. Decide
  where diag sits and write it on [ref/module/display.md](ref/module/display.md). A diagnostic that
  covers an alert is worse than no diagnostic.
- ⚠️ **Presence is *last heard*, not *alive*.** A nanoKONTROL nobody has touched looks like one on the
  floor. Label it honestly.

---

## Phase 4 — Tier 2: the standalone debug patch

⛔ **It goes in `/sdcard/Patches/! debug/`, not in `!`.** As of 2026-08-07 the `!` menu holds
**`Cut It` and nothing else**. At a venue you should scroll past nothing to reach the instrument, and
a second menu directory is where anything you might reach for *instead* of playing belongs.

**Because it is standalone it may use the encoder**, so it gets a navigable menu rather than one
screen — **plus** four knobs, the aux button and 25 keys.

What it shows, at minimum — the three questions that currently require a laptop and a network:

| Screen | Answers |
|---|---|
| **MIDI monitor** | What is arriving from each device, and on what channel |
| **Test output** | Fire a message at each device and hear or see it answer |
| **The error log** | The tail of `cut-it-err.log` |
| **Network** | Whether the AP is up, and what address the phone has |
| **Re-wire** | Run `wire.sh` by hand |

⛔ **It must make its own `aconnect` call.** Loading any patch drops Pd's ALSA connections, so a
debug patch that does not wire itself measures silence and reports it as *"no MIDI arriving"* —
which is the worst possible lie for this particular tool.

⚠️ **Selecting it restarts Pd**, which means it is for *"the instrument is broken and I am not playing
right now."* Say so on its page.

---

## Phase 5 — Tier 3: the phone becomes interactive

**The largest usability win available**, because the phone is the only thing in the rig with a real
screen and touch.

Add `[netreceive -u 9001]` to `u_net` plus a route, and give the scene buttons: **re-run `wire.sh`,
clear alerts, request a full status dump, fire a test note at a named device.**

### ⛔ One hard rule, written onto [ref/device/phone.md](ref/device/phone.md) BEFORE any of it is built

> **The phone may trigger diagnostics only, never a musical parameter.**

The instrument's stated property is that it plays identically with the phone off, crashed, or the
wifi gone. **Routing any performance control through UDP destroys that**, and UDP jitter is already
visible in the heartbeat counter — *"fine for a readout, unacceptable for note timing."*

⚠️ **An inbound path is also an attack surface on a shared network.** Restrict the vocabulary to a
closed list of diagnostic selectors and **drop everything else silently**, exactly as `u_net`
already swallows reserved selectors outbound.

⚠️ **The staleness detector stays on the phone.** An inbound path does not change that — the
Organelle still cannot know the phone is gone.

---

## Phase 6 — the two open items that are easy to lose

- **Nothing arbitrates the phone.** Today `u_net` mirrors and the phone decides, so the priority
  model stops at the Organelle. **The moment the phone gains buttons and a diag screen it needs
  one.** Give it the same ordering the OLED has, **or decide explicitly that it stays a mirror and
  record why.** Either closes it; a third pass that leaves it unstated does not.
- **Guided Access is not set up**, so a stray swipe can drop you out of the scene mid-set. ⚠️ **Five
  minutes on the phone, and it is exactly the venue failure this plan exists to prevent.** It has
  survived three counts because it is not code. **Do it in the same session as the AP work.**

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v
./tools/deploy.sh
```

Then, and this is the real test:

**A full set's duration, on the AP, with the phone as the only display, and no laptop in the room.**

During it, confirm: the AP stays up; the phone repopulates within a few seconds of being backgrounded
and returned; ⚠️ the instrument keeps playing identically when the phone is switched off entirely;
the diag layer names a device you deliberately unplug; and the debug patch loads from the menu, wires
itself, and shows MIDI arriving.

⚠️ **Prove the probe before believing the silence.** If the debug patch's MIDI monitor shows nothing,
establish that the monitor works — with a device you know is transmitting — before concluding the
device is dead.

---

## Done means

1. The AP comes up without a laptop and survives a power cycle, and item 45 is measured over a real
   set.
2. The house fault is either fixed by configuration or **closed as won't-fix under the stated
   stopping rule** — not left open.
3. The diag layer names every device's last-heard state on the OLED and on the phone.
4. The debug patch exists in `! debug/`, wires itself, and answers the three laptop questions. It has
   a `ref/` page.
5. The phone has buttons, a closed diagnostic vocabulary, and the hard rule written on its page.
6. Phone arbitration is decided, and Guided Access is on.
7. `plan-v04.md` §3 no longer carries the wifi section, the never-run AP check, or *Debugging the rig
   with no laptop* — and [tools/README.md](tools/README.md)'s ⬜ about where the debug system lives is
   struck.
8. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.**

⛔ **Leave every change in the working tree.** Brendan commits his own work.
