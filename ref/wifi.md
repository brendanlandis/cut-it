<!-- schema: freeform -->
# Wifi

**The Organelle drops its wifi on house networks, and this page is everything established about
why.** It is narrowed, not solved. The fault matters because the phone display is the instrument's
second screen — [device/phone.md](device/phone.md) — and a dead display mid-set is the failure
being designed against.

⚠️ **Do not spend session time on this unless it recurs.** Everything actionable has shipped.
What is still open, and what is being waited for, is [plan-v04.md](../plan-v04.md).

**The boot hang that used to look like a wifi fault is not one** — it is a USB mass-storage fault
with wifi as its most visible casualty, and it lives on [device-os.md](device-os.md).

## Where the credentials actually live

**`$USER_DIR/wifi.txt` — plain text, alternating SSID and password lines, two per network.**
Measured on the device in Phase 7. `USER_DIR` resolves to **`/sdcard`** in normal operation, which
is mounted `rw`, so **adding a network is appending two lines and needs no `remount-rw.sh`** — that
is only for the `ro` rootfs.

⚠️ **`/etc/wpa_supplicant/wpa_supplicant.conf` is a red herring.** It is the stock 55 KB example
file dated 2015, still carrying `ssid="example"` and `ssid="eap-sim-test"`. **Nothing reads it.**
The real path is `wifi_setup.py` → `wifi.txt` → the front panel's own `wifi_control.py`, which
builds a `wpa_supplicant` config inline with `wpa_passphrase` from the credentials in `wifi.txt`.

⚠️ **AND `/root/fw_dir/scripts/wifi-config.sh` IS A SECOND RED HERRING — do not call it.** ✅
Measured (item 161): on this device it is a **stale factory template** dated Feb 2020, hardcoded to
`wpa_passphrase "name" "pass"`. The SSID is literally `name`, and the passphrase is 4 characters
where `wpa_passphrase` rejects anything under 8 — so it emits **nothing** and the supplicant gets
an empty config. Running it **kills a working `wpa_supplicant` and puts nothing in its place.**
This repo's own recovery ladder called it for two phases, which is why two `UNRECOVERED` verdicts
were partly self-inflicted. `tools/wifi-reassociate.sh` is the correct sequence — it mirrors what
the front panel does, with the real credentials.

```sh
ssh root@organelle.local 'printf "SSID\nPASSWORD\n" >> /sdcard/wifi.txt'
```

⚠️ **The passwords are stored in the clear** — that is the device's design, not a choice available
to us. **`wifi.txt` must never be copied into this repo**, and [device/](../device/) deliberately does
not back it up.

**Adding a second network is the cheap way to a self-contained stage link**, and much lower risk
than `hostapd`: the Organelle simply joins whichever is present and **SSH survives**, where
bringing up an AP drops it. ⚠️ **An iPhone Personal Hotspot needs cellular**, so it cannot be
combined with airplane mode — the two are mutually exclusive. See [plan-v04.md](../plan-v04.md).

## The tools that watch it

| Tool | Runs on | Does |
|---|---|---|
| `tools/wifi-watch.sh` | **the device** | Polls `wlan0`, and on a failure runs a **link probe** and a **DHCP probe** before a recovery ladder |
| `tools/wifi-poll.sh` | the Mac | Watches from outside, so a device that has gone silent still produces a record |
| `tools/wifi-report.sh` | the Mac | Summarises `wifi-watch.log` |
| `tools/wifi-reassociate.sh` | the device | The recovery rung that mirrors what the front panel does. **The only one that has ever worked** |

⚠️ **`--mark` goes AFTER a finding is written up, never before.** It draws the analysed-to-here line,
so running it first erases the event you were about to read.

⛔ **NEVER `pgrep -f wifi-watch`.** It matches the `ssh` command doing the checking, so a sweep that
scans and relaunches in one command kills its own session. Item 163, and it has bitten three times.

✅ **The watcher starts at boot** — `device/wifi-watch.service`, installed at
`/etc/systemd/system/` and enabled (item 244). ⛔ **Until it existed, every recovery disarmed the
detection for the next failure**, because a reboot is how this fault gets recovered and nothing
restarted the watcher afterwards. That is not hypothetical: three drops on **2026-08-08** produced
**no evidence at all**, the device having come up at 15:15 with nothing watching until 20:54.
`tools/wifi-poll.sh`'s relaunch is now the backstop for a mid-session death rather than the primary
mechanism, and it counts consecutive failed relaunches instead of retrying in silence.

⚠️ **`/root` is read-only** — `remount-rw.sh` before installing or enabling the unit, `remount-ro.sh`
after, because `systemctl enable` writes a symlink into `multi-user.target.wants/`.

⛔ **`After=network.target` is far too weak here, and the unit waits for an address instead.**
Measured on the first real boot: the watcher came up with the clock still at 2015, `assoc: Not
connected` and `wpa_supplicant=- dhcpcd=-`. It ran **no** recovery, so nothing fought with the boot —
but its first sample was `NONE`, so the ordinary boot-time DHCP acquisition was logged as
`TRANSITION NONE -> 192.168.1.9`. **`wifi-poll.sh` counts `TRANSITION` lines as drops**, so every
boot would have added a phantom one and tripped *ANYTHING NEW?*. The unit now polls for an IPv4 in
`ExecStartPre`, **bounded at 120 s and starting anyway when that expires** — a device that never gets
an address is exactly when the watcher is wanted. `TimeoutStartSec` has to exceed the bound; the
systemd default of 90 s does not.

⚠️ **One phantom `TRANSITION NONE -> …` already exists in the log**, stamped `2026-08-08 21:34:27`.
It is a boot artefact, not a drop.

✅ **Verified across a real reboot 2026-08-08**: the service comes up `active`, its opening block
carries a populated `ipv4:` and the SSID, and **no `TRANSITION` is logged at boot**. The header is
still stamped `2015`, which is the expected proof that it starts before the clock is corrected.

## ⚠️ The roam fault — what is known, and how to reproduce it

**On house wifi the device loses its IPv4 lease and does not get it back.** Open since Phase 6 and
misdiagnosed for two of them.

✅ **The fault is a ROAM breaking a RUNNING `dhcpcd`.** The device roams between the two AP radios,
and a `dhcpcd` running across that association change never re-acquires.

✅ **`dhcpcd` is EXONERATED** — caught in full with `-d` running *through* a roam. It detects the
carrier going, deconfigures through its own hooks, detects re-acquisition, re-solicits at once and
backs off correctly. **It sends DISCOVER and nothing ever answers.** ⚠️ **The diagnostics had gone
nowhere for the entire investigation because `syslogd` is not running on this device.**

| Established | |
|---|---|
| **The link is never the problem** | A static address reaches the gateway with **0% loss**, on either AP |
| **A fresh `dhcpcd` on a SETTLED association succeeds** | On *either* AP, first DISCOVER, in seconds. That is why only the reassociate rung ever worked |
| ⛔ **The interval was never a timer or a lease expiry** | 2 h 09 m, 3 h 12 m, 13 h 32 m — it is *how long until the AP hands the device off*. **Stop asking for the router's lease time** |

**Why nothing answers a DISCOVER after a roam is not established** — see *Open* below.

**The repro — three seconds, no waiting:**

```sh
wpa_cli -i wlan0 scan ; sleep 4      # ⚠️ required: roam only targets a cached BSS
wpa_cli -i wlan0 roam <other-bssid>  # IPv4 gone within 3 s
```

**And the one-line check for whether the fault is present right now:**

```sh
ssh root@organelle.local 'ip addr show wlan0 | grep "inet "'   # NO OUTPUT == this fault
```

⚠️ The device is still **associated** when this returns nothing — that is the whole point. "Drops its
wifi" describes the symptom and misdescribes the cause.

## The evidence, item by item

Every measurement the investigation rests on, and the six that turned out to be wrong. ⛔ **The tools
cite these numbers by bare item — `wifi-watch.sh` alone names seven — and `grep item N` is the only
thing that resolves them. Never delete a row; never reuse a number.**

| Item | Finding | Evidence |
|------|---------|----------|
| 81 | **The Organelle drops its wifi after a while.** The original observation. ⚠️ Its framing was wrong — it read as a radio fault | verified |
| 133 | **Item 81 caught in the act, and it is NOT the radio dropping the network.** `iw dev wlan0 link` stayed associated throughout | verified |
| 169 | ⛔ **The trigger is a roam to a DIFFERENT BSSID**, and "same BSSID" was wrong. Thirteen hours of healthy heartbeats on `…a2:01`; the transition record reads `…c9:25` | verified |
| 175 | ✅ **The fault reproduces on demand in three seconds.** `hildegard` is served by two APs; forcing a handoff reproduces it exactly | verified |
| 180 | **Where DHCP stops.** ⚠️ **`syslogd` is NOT running on this device**, so `dhcpcd` logged into a void for the whole investigation. Its "the REQUEST is never ACKed" is **weaker than it looks** — see below | verified |
| 159 | ✅ **The fault is DHCP-side, so a card swap would prove nothing.** The link probe assigned the last-known-good address and route and reached the gateway. ⚠️ Second occurrence at **2 h 09 m** after boot against the first at ~3 h 12 m — **not a fixed interval** | verified |
| 184 | ✅✅ **`dhcpcd` is EXONERATED.** Caught with `-d -B` running *through* a forced roam on a 150 s budget: DISCOVER ×3, **no OFFER, ever**. It detects, deconfigures, re-solicits and backs off correctly | verified |
| 214 | ⚠️ **A failure happened on the ROUTER, not the satellite** — which overturns the standing claim `wifi-watch.sh`'s own comment is built on | verified |
| 215 | ⚠️ **The two DHCP probes gave OPPOSITE answers** seven hours apart, same script, same client, same SSID. Nothing in the record predicted it | verified |
| 220 | ✅ **The outage is ~132 seconds, measured** — and the "~20 s" in `wifi-watch.sh`'s own comment is **wrong** | verified |
| 212 | ✅ **The ladder fired on two real failures and recovered both**, rung 1, first try, no other rung attempted | verified |
| 213 | ⛔ **The fault SURVIVED firmware 2.7.6.6 — twice in 15 hours.** This is the answer the leave-it-running task was waiting for, and it is the negative one | verified |
| 221 | ✅ **Channel 1 took, and helped throughput enormously** — 14.4 MBit/s MCS 1 → **72.2 MBit/s MCS 7**. But it did **not** separate the two APs, exactly as predicted | verified |

**Six wrong turns, kept so nobody walks them again.** ⚠️ **Four of them are defects in this
project's own measuring rig, not in the device** — which is the pattern worth carrying away.

| Item | Was claimed | Overturned by |
|------|-------------|---------------|
| 179 | *"The Organelle cannot get a lease on the satellite"* | **Item 182**, thirty minutes later — a controlled two-arm test **on the satellite** leased twice, in seconds, on the first DISCOVER. ⛔ **Over-claimed from a single A/B** |
| 178 | `UNRECOVERED` in the watcher's log | A **false negative** — the rung worked and the timeout was too short. The device had an address shortly afterwards |
| 161 | The recovery ladder's own verdict | ⚠️ **Two faults in our own measuring rig.** Rung 3 ran `/root/fw_dir/scripts/wifi-config.sh`, a **stale factory template** — see *Where the credentials actually live* above |
| 167 | The watcher's single-instance guard | ⚠️ **Only as good as the pidfile, and deleting it by hand disarms it.** Twice in one session two watchers ran, both times after a manual pidfile removal, because `wifi-poll.sh` relaunches whenever the stamp goes stale |
| 187 | The AP-visibility guard in the steer | ⚠️ **A sixth defect in the measuring rig: `iw scan` is not `iw scan dump`.** `iw dev wlan0 scan` **triggers a new scan**, so run right after a `wpa_cli scan` the two contend — and it reported NOT VISIBLE for an AP sitting at **−47 dBm** |
| 163 | A rewritten self-match check | ⛔ **The self-match trap bit a THIRD time, through a check written to avoid it.** A `/proc/*/cmdline` scan and a `case` pattern have the same flaw — **any** check whose own command line contains the string matches itself |

✅ **A boot-started `wpa_supplicant` DOES have a working `ctrl_interface`** — item 246, measured
after a real power cycle rather than assumed. The supplicant comes up **29 s after boot** as
`wpa_supplicant -B -D nl80211,wext -i wlan0 -c /dev/fd/63`, the socket exists at
`/var/run/wpa_supplicant/wlan0`, and `wpa_cli -i wlan0 status` answers with the live BSSID and SSID.

⛔ **So the roam repro needs no special setup and restarts nothing.** `wpa_cli -i wlan0 scan` then
`wpa_cli -i wlan0 roam <other-bssid>` can be run against the supplicant the device booted with, which
is the only version of the fault worth reproducing — a hand-started supplicant is a different
configuration and was always the weaker test.

⛔ **Ruled out, so nobody walks them again:** the Orbi satellite being at fault (overturned by a
two-arm test 30 minutes later — item 182), `option rapid_commit`, `require dhcp_server_identifier`,
the ARP duplicate-address probe / `noarp`, swapping the wifi card (two link probes, 0% loss), and
`--dbdir /sdcard/dhcpcd`. ⚠️ **All were queued to explain a lease that expires, and the lease does
not expire** — the association changes underneath it.

⚠️ **Two pieces of evidence are weaker than they look.** Item 180's *"the REQUEST is never ACKed"*
came from a capture cut off by a `timeout 20` with the retry schedule still running — the failure
is at **DISCOVER**. And **`dhcpcd -T` stops at the OFFER** and never sends a REQUEST, so it
exercises only the half that works.

**Operating the watcher:**

- **Run `./tools/wifi-report.sh --mark`** once a finding is written up, or the report reads the
  same before and after the next failure.
- **Do not run two watchers.** Use the pidfile, or `ls -l /sdcard/wifi-watch.alive`.
- ⚠️ **NEVER `pgrep -f wifi-watch`**, and never let one command both scan and relaunch — that
  self-match kills the ssh session doing the sweeping. Item 163.

## The Organelle as its own access point

**This is the stage configuration**, and it is the vendor's own path rather than a `hostapd`
project. `start-ap.sh` reads `$USER_DIR/ap.txt` — first line network, last line password — and
calls `create_ap --no-virt -n wlan0 $NET $PW`, defaulting to `Organelle` / `coolmusic`. This rig
uses **`organelle`**, with the password in `/sdcard/ap.txt` on the device, and the phone leases **192.168.12.109** from it.

**The venue sequence — no laptop, no venue wifi, phone in airplane mode:**

1. Organelle: **System → WiFi Setup → Start AP**
2. Phone: airplane mode on, wifi back on, join **`organelle`**
3. Organelle: load **Cut It** — `phone-ip.sh` finds the phone's address from the DHCP lease

✅ Verified end to end. Airplane mode is what makes this worth doing: a phone *hotspot* needs
cellular, an AP the Organelle hosts does not.

✅ **And it removes the roaming fault outright, which is a second reason to host the network.**
`start-ap.sh` runs `killall wpa_supplicant` before `create_ap`, so in AP mode the Organelle has
**no client association at all** — it serves DHCP rather than requesting it. The fault that drops
the IPv4 lease (items 169–172) requires a client association being handed off to another BSSID,
and **none of that exists here.** ⚠️ **That is immunity to that one fault, not proof the stage
link is solid** — see *Open*. And it only holds if the AP is actually started: **a set run on
house wifi is a client again.**

⚠️ **Start the AP from the SYSTEM MENU, not from a patch.** A patch that launches `start-ap.sh`
loses it the moment the next patch loads — `create_ap`, `hostapd` and `dnsmasq` all die with the
Pd that spawned them, **even behind `setsid nohup`**. Measured; item 129.

⚠️ **The passphrase must be 8–63 characters.** `create_ap` rejects anything shorter — and
`start-ap.sh` runs `killall wpa_supplicant` *before* calling it, so a rejected passphrase leaves
the device with **no wifi and no AP**, recoverable only by power cycle.

⚠️ **`$NET` and `$PW` are passed unquoted**, so an AP name with spaces breaks — unlike `wifi.txt`,
which handles them. Keep the AP name one word.

⚠️ **The AP has no internet** — `create_ap` is called with `-n`, and one radio cannot be both AP
and client. **A Mac joined to it is offline**, so an AP session cannot be driven from a laptop that
needs a network. Prepare everything on the house wifi first.

✅ **Recovery is a power cycle.** `createap.service` is `disabled`, so the device comes back on the
house network by itself. Nothing about this is sticky.

## Open

⬜ **Why nothing answers a DISCOVER after a roam.** **Not established**, and the one thing that
would turn the roam fault from narrowed into solved. ⚠️ Say so plainly — this investigation has
already produced two confident wrong answers. [plan-v04.md](../plan-v04.md) §3.

⬜ **AP-mode link quality over a set-length window — item 45.** AP mode is immune to the roam fault
by construction, but nothing has measured whether the stage link *holds* for the length of an
actual set. ⚠️ Measuring it needs the AP up, which kills the house link.
[plan-v04.md](../plan-v04.md) §3.

⬜ **Three drops on 2026-08-08 that did NOT match the roam signature.** Recorded because they
contradict it, and a future session will otherwise re-derive them. From the Mac, `ssh` failed at
**name resolution** and `find-organelle.sh` returned **ABSENT** — no IPv4 and no IPv6 neighbour,
while it found another host at `.14` happily. On the device afterwards: associated, `192.168.1.9`
held, −31 to −41 dBm, **uptime unbroken across all three**, and both radios in the log.
⛔ **That is not the documented signature** — item 81 leaves the device reachable over IPv6
link-local throughout, and here nothing answered on either protocol. Whether the lease was lost is
not established: the watcher was not running, and the device was reconnected by hand, so the
recovery proves nothing either. ⚠️ **Do not fold these into the roam fault without new evidence.**
Item 244 now exists so the *next* one is recorded. [plan-v04.md](../plan-v04.md) §3.
