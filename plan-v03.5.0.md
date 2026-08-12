# Plan v0.3.5.0 — the venue network

**At a venue there is no house wifi.** The phone is the only thing in the rig with a real screen and
a touch surface, and it can only be reached if **the Organelle is its own access point**. AP mode is
also **structurally immune** to the roam fault that has been dropping the link for months, because
`start-ap.sh` runs `killall wpa_supplicant` first and there is no association left to hand off.

**This plan is almost entirely not code.** It is a router, a front panel, a phone setting, and one
measurement that needs a real set's duration to mean anything.

✅ **And the hard part is already built, by the vendor.** `Start AP` lives in the Organelle's own
System → WiFi Setup menu, and the venue sequence is verified end to end — see
[ref/wifi.md](ref/wifi.md) under *The Organelle as its own access point*. ⛔ **There is no boot-time
service to write.** Brendan's decision, 2026-08-11: **neither the AP nor the house network connects
automatically, and a couple of clicks each is fine.** Nothing here should try to change that.

**Two sibling plans came out of the same batch** — [plan-v03.5.1.md](plan-v03.5.1.md), diagnostics
inside the instrument, and [plan-v03.5.2.md](plan-v03.5.2.md), the standalone debug patch. They are
independent of this one. ⚠️ **But run 5.1 first** — see *Where this sits in the order*.

---

## ⚠️ Constraints that bind everything below

- ⚠️ **Bringing the AP up kills the house link**, and with it the ssh session and every Mac-side
  tool. **Plan each AP session to be self-sufficient before you start it.**
- ⛔ **Never `pgrep -f wifi-watch`.** The pattern self-matches and kills the ssh session doing the
  checking. Item 163, and it has **bitten three times**.
- ⚠️ **The `critterandguitari/Organelle_OS` repo targets the M and S2, not this device.** Its paths
  are wrong here. Verify against the actual hardware.
- **Commit as you go**, in reviewable batches. ⛔ **Brendan is the sole author: no `Co-Authored-By`
  trailer and no agent byline.**
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** ⚠️ Nothing in this plan changes a
  `.pd`, so `./test/run.sh` is not part of its loop — `python3 test/gate/docs-check.py -v` is.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`docs`** skill | ⛔ **Invoked, not read** | Every deliverable here is a `ref/` edit |
| [ref/wifi.md](ref/wifi.md) | **All of it** | What is known, what was tried, the reproduction. ⛔ **Two confident wrong answers and six wrong turns are recorded there — read them before forming a third** |
| [ref/device/phone.md](ref/device/phone.md) | *The network*, *Traps*, and `Open` | The AP subnet, airplane mode, and the Guided Access item this plan closes |
| `tools/stage-patches/Start AP/ap-up.sh` | **All 26 lines** | ⛔ **A documented dead end.** It opens with *"THIS APPROACH DOES NOT WORK"* and says why |
| `tools/stage-patches/AP Probe/ap-probe.sh` | Skim | The pattern that **works**: log to `/sdcard/`, instruct on the OLED, read it afterwards |
| `tools/wifi-watch.sh`, [tools/README.md](tools/README.md) | The wifi sections | The three-rung ladder and its operating traps |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** any gate, `test/runner/`, or any `ref/module/` page. Nothing here touches them.

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
  AP. **The outage is ~132 seconds**, measured.
- ✅ **The recovery ladder works unattended**; ⛔ **Orbi firmware 2.7.6.6 did not fix it**; channel 1
  was a real throughput win but **did not separate the two APs**.
- ⛔ **The preferred-AP steer is no longer a safe fallback** — one failure happened *on* the router.
- ⬜ **Why nothing answers a DISCOVER after a roam is NOT established.** That is a router-side
  question, and it is what Phase B attacks. See [ref/wifi.md](ref/wifi.md).

### The access point

- ✅ **`Start AP` is the vendor's own path and it is already in the System menu.** `start-ap.sh`
  reads `$USER_DIR/ap.txt` and calls `create_ap --no-virt`; this rig uses `organelle`, and the phone
  leases `192.168.12.109` from it.
- ⛔ **A patch cannot start it.** `create_ap`, `hostapd` and `dnsmasq` are children of the Pd that
  spawned them and die when the next patch loads — **even behind `setsid nohup`**, measured, item
  129. `tools/stage-patches/Start AP/` is kept only as the record of why.
- ✅ **It removes the roam fault outright**, because there is no client association at all.
  ⚠️ **That is immunity to one fault, not proof the stage link is solid.**
- ⚠️ **The AP has no internet** — `create_ap -n`, and one radio cannot be both AP and client. **A Mac
  joined to it is offline.** Prepare everything on the house wifi first.
- ✅ **Recovery is a power cycle.** `createap.service` is `disabled`, so the device comes back on the
  house network by itself. **Nothing about this is sticky.**

---

## Phase A — the AP is the performance network

**The house wifi stays the development-time convenience with its existing recovery ladder. The AP
becomes what the rig runs on when it matters.** ⛔ **There is nothing to build.**

### ✅ A1 — the venue sequence is the operating procedure. Done 2026-08-12

On [ref/wifi.md](ref/wifi.md), under *The Organelle as its own access point*. It states that neither
network connects automatically and that this is a choice rather than a gap, that **no boot-time
service should be added**, and it carries the two consequences that read as faults — the phantom
`TRANSITION` (item 299) and a set run without step 1 being a client on house wifi again.

### A2 — ⬜ item 45, AP link quality over a set-length window

**The one thing nothing has ever measured.** ⚠️ It *"needs an actual set's duration to mean
anything"*, and this plan's acceptance test is a set's duration — so it closes by construction, and
only if the test is actually run.

⚠️ **Every AP session must be self-sufficient before it starts.** Staged on the device beforehand:

- `/sdcard/ap.txt`, with an **8–63 character** passphrase. ⚠️ `create_ap` rejects anything shorter
  and `start-ap.sh` runs `killall wpa_supplicant` *before* calling it — **a rejected passphrase
  leaves the device with no wifi and no AP, recoverable only by power cycle.** ⚠️ `$NET` and `$PW`
  are passed unquoted, so keep the AP name one word.
- The instrument deployed and loaded, and the phone's scene open.
- Anything the session wants to record written to `/sdcard/` — the `AP Probe` pattern. **Nothing has
  to be caught live.**

**Verdict:** Brendan's, in the room. Record it on [ref/wifi.md](ref/wifi.md) and strike item 45 from
its `Open`.

---

## Phase B — the house fault, with a stated stopping point

## ⏸ PAUSED 2026-08-12, and nothing here should be started without asking

**Brendan's call: the Organelle has been behaving, so this waits a couple of weeks and comes back
only if it becomes a problem again.** ⚠️ **That is this repo's own standing rule, not a departure
from it** — [ref/wifi.md](ref/wifi.md) already says *"do not spend session time on this unless it
recurs"*, and [plan-v04.md](plan-v04.md) §3 says the same.

⛔ **The pause is NOT the stopping rule being invoked.** Item 81 is **parked, not closed** — no
configuration change has been tried, so neither outcome in *Done means* #3 has happened yet. **Do
not close it as won't-fix on the strength of a quiet fortnight**, and do not start B1 without asking.

**Everything needed to resume is already captured**, which is the whole point of having taken it
before pausing: the baseline is **item 300**, the constraint that kills per-band separation is
**item 298**, and the log-reading caveat is **item 299**. ⛔ **Re-take the baseline before acting on
it** — it is a scan cache and a fortnight old by then.

⚠️ **What the pause costs:** this plan cannot reach *Done means* and be deleted while item 81 is
open, and [plan-v03.5.2.md](plan-v03.5.2.md) is written as **the last of the three**. If 5.2 becomes
ready first, either resolve item 81 or move the closing chore — **do not let 5.2 land silently out of
order.**

---

Everything on the device side is exonerated. **This is a router-side problem**, so attack it from the
router. ⛔ **Read [ref/wifi.md](ref/wifi.md) in full first.**

### ✅ B0 — the baseline, measured 2026-08-12

**Item 300.** Both `hildegard` BSSIDs are on **freq 2412 — channel 1, co-channel**:
`a6:40:a0:5e:a2:01` at −31 dBm and `a6:40:a0:5e:c9:25` at −43 dBm, **12 dB apart**. The device held
`192.168.1.9` throughout, so the fault was not present when this was taken.

⚠️ **The second BSS appears only after an active scan.** `iw dev wlan0 scan dump` alone shows just
the associated one, which is not enough to tell whether a change separated them. Run
`wpa_cli -i wlan0 scan`, wait, then dump. ✅ **The scan is the harmless half of the repro** — it was
run and the lease survived it; only the `roam` drops the address.

### ⛔ Item 298 removes one of the two attacks before you start

**The dongle is 2.4 GHz only** — `iw phy` lists Band 1 and nothing else, zero 5 GHz channels. So
**per-band separation cannot work here**: both radios the Organelle can reach are on 2.4 GHz by
necessity, and moving one to 5 GHz does not separate the pair, it makes one **invisible**. What is
left is a difference the device can still see on 2.4 GHz — **a distinct SSID, a distinct channel per
node, or one node's 2.4 GHz radio switched off.**

### B1 and B2 — the two changes

**Brendan does the router configuration; this plan records the result.** Two attacks, in order:

1. **Separate the two APs** so a roam stops being possible — ⛔ **not per-band**, see item 298.
   ⚠️ **One Orbi setting moves both mesh nodes**, which is why this has not been trivial.
2. **Disable fast roaming / band steering** if the Orbi exposes them.

**Verification is the three-second repro**, against the supplicant the device booted with — item 246
established that a boot-started `wpa_supplicant` has a working `ctrl_interface`, so this needs no
special setup and restarts nothing:

```sh
wpa_cli -i wlan0 scan ; sleep 4      # ⚠️ required: roam only targets a cached BSS
wpa_cli -i wlan0 roam <other-bssid>  # IPv4 gone within 3 s
ip addr show wlan0 | grep "inet "    # NO OUTPUT == the fault is present
```

⛔ **The stopping rule, and it is binding: if two configuration changes do not stop the roam, close
item 81 as won't-fix and let AP mode be the answer.** The requirement was never *"recover fast"* — it
was *"stop dropping"* — and AP mode satisfies it by construction. ⚠️ **Continuing past that point has
already produced two confident wrong answers.**

⚠️ **Do not re-enable the preferred-AP steer as a fallback.** It drops IPv4 itself on every fire, and
**it hides the answer** by preventing recurrence.

⚠️ **`--mark` goes AFTER a finding is written up, never before.** It draws the analysed-to-here line,
so running it first erases the event you were about to read.

⛔ **Discount the first `TRANSITION` of every session before reading the log as evidence** — item
299. The device is joined by hand, so the lease lands after `ExecStartPre`'s 120 s bound and the
connect itself is logged as a transition. **`wifi-poll.sh` counts those as drops**, so a phantom one
is the normal outcome of a hand-connected boot. Credit a router change with stopping the fault only
against transitions that are not the session's first.

---

## Phase C — Guided Access

⬜ **Guided Access is not set up**, so a stray swipe can drop you out of the scene mid-set.
⚠️ **Five minutes on the phone, and it is exactly the venue failure this plan exists to prevent.** It
has survived three counts because it is not code.

**Brendan does it. Do it in the same session as the AP work**, and record it on
[ref/device/phone.md](ref/device/phone.md), striking the ⬜ in its `Open`.

---

## Where this sits in the order

⚠️ **Run [plan-v03.5.1.md](plan-v03.5.1.md) before this plan's rig session, not after.** 5.1 edits
`g_oled.pd` and `u_net.pd`, and `test/runner/steps.py`'s `DEPS` table stales every bench verdict that
depends on them — display, midi, nanokontrol and phone. ⛔ **A rig session run first would be
wasted**, because those verdicts would go stale again the moment 5.1 landed.

**So the one rig session runs in this order**, because the bench runner needs a network the AP takes
away:

1. **On house wifi:** `./test/run.sh --benches`, clearing the whole stale backlog at once.
   ⚠️ **Afterwards read `test/results/latest.json`** rather than asking Brendan to retype failures.
2. **Then switch to the AP** and run the venue test below.

---

## Verification

```sh
python3 test/gate/docs-check.py -v
```

⚠️ **`./test/run.sh` is not part of this plan's loop** — nothing here changes a `.pd`.

Then, and this is the real test:

**A full set's duration, on the AP, with the phone as the only display, and no laptop in the room.**

During it, confirm: the AP stays up; the phone repopulates within a few seconds of being backgrounded
and returned; and ⚠️ **the instrument keeps playing identically when the phone is switched off
entirely.**

⚠️ **Prove the probe before believing the silence.** A null result is worthless until the channel is
proven. ⛔ **And before calling a hardware symptom an instrument fault, check the patch comments, the
`ref/` page and the gates first** — `grep ref/` for the literal error string, because symptoms are as
greppable as `item NNN` and cost more to re-derive.

---

## Done means

1. The venue sequence is the stated operating procedure on [ref/wifi.md](ref/wifi.md), including
   that neither network is automatic and that this is deliberate.
2. **Item 45 is measured over a real set** and struck from [ref/wifi.md](ref/wifi.md)'s `Open`.
3. The house fault is either fixed by configuration or **closed as won't-fix under the stated
   stopping rule** — not left open.
4. **Guided Access is on**, and the ⬜ on [ref/device/phone.md](ref/device/phone.md) is struck.
5. [plan-v04.md](plan-v04.md) §3 no longer carries *The wifi fault — background, not blocking* or
   item 45's row in *Checks that were never run*.
6. **This file is deleted.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
