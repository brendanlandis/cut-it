# Cut It — Rig Plan

Hardware setup plan for the Cut It instrument. Companion to
[README.md](<! v0.1 plans/README.md>), which covers the Pd patch itself.

Target hardware: **Organelle 1** (the original, not M/S/S2).

---

## Overview

**Moved** to [ref/rig.md](ref/rig.md). **This file is now only the Organelle as a COMPUTER** — SSH,
paths, the read-only filesystem, how Pd launches, deploying, and wifi.

⚠️ Its paths are the ones the Organelle cruft cleanup will change. Verify against the device before
relying on them.

## Signal flow

**Moved** to [ref/rig.md](ref/rig.md) — MIDI, audio and power, plus the gear list and the cabling.
The ALSA wiring and the channel blocks are on [ref/module/boot.md](ref/module/boot.md).

⛔ **LOADING ANY PATCH DROPS PD'S ALSA CONNECTIONS — measured, item 228.** After
`oscsend localhost 4001 /loadPatch …`, `Pure Data Midi-Out 4` had **no target at all**, and a probe
patch that assumed the wiring survived reached nothing. The Pd *process* persists across a patch
swap; its port connections do not. ✅ **This is why `u_init` runs `wire.sh`** — Cut It re-wires
itself every load and so never notices. ⚠️ **Any patch that is not Cut It must make its own
`aconnect` call**, or it measures silence — and silence from a MIDI probe reads as *"the device
ignores this message"*, which is the wrong conclusion and the precise shape of item 225.

```sh
aconnect -l | grep -A2 "Midi-Out 4"        # expect: Connecting To: <the Uno's client>:0
```

**Pd only opens the MIDI devices it is told to at launch**, and it reads that from
`/root/.pdsettings`, not command-line flags — mother passes none. The device is configured for
**4 in / 4 out** with `midiapi: 1`, which forces ALSA MIDI; without it Pd falls back to OSS and the
Launchpad's three ports collapse into one. Verified surviving a cold boot. Backup at
`/root/.pdsettings.bak`.

## The device itself

```sh
ssh root@organelle.local        # password: organelle
```

⚠️ **The IPv4 address is DHCP-assigned and NOT stable.** It has been observed as `192.168.1.11`,
`.15`, `.18` and `.20`; a recovery that flushes the interface can come back on a different one.
**Always use `organelle.local`** — mDNS follows it, and every script here defaults to that. The
literal addresses in `HOST=` examples are fallbacks for when mDNS is flaky, and must be re-checked
before use rather than trusted.

### ⚠️ "Cannot reach" after a wifi drop — CHECK IPv6 BEFORE BELIEVING IT

**A successful recovery presents exactly like a continued failure**, because recovery changes the
IP address and **mDNS does not notice for a few minutes.** The device once came back healthy on
`.20` while `organelle.local` still resolved to the dead `.18`, so `wifi-report.sh` reported
*"Cannot reach"* about a device that was completely fine. ⚠️ **A power cycle at that moment would
have destroyed the evidence of a recovery that had already worked.**

```sh
ping organelle.local              # 0% loss over IPv6 == the device is ALIVE
ssh -6 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "root@fe80::<link-local>%en0" # the zone id and BOTH bypasses are required
```

⛔ **Do not trust `ssh`'s own error message, or any tool's, as a reachability check** — both have
now misled this investigation. The cache catches up on its own. Item 172.

| | |
|---|---|
| Home | `/root` (not `/home/music`) |
| Patches | `/sdcard/Patches/` — factory set lives here |
| User patches | `/sdcard/Patches/!/` — `!` sorts to the top of the menu |
| Pd config | `/root/.pdsettings` |
| Externals | `/root/Pd/externals` |
| Scripts | `/root/fw_dir/scripts/` |
| Extra libs | `/sdcard/PdExtraLibs` — already on Pd's search path |
| **Running patch** | **`/tmp/patch` — a SYMLINK to the patch folder**, and Pd's working directory |
| **Instrument data** | **`/sdcard/cut-it-state/`** — what `u_state` writes. Not config, not deployed |
| Error log | `/sdcard/cut-it-err.log` (rolled) and `.cur` (running session) |
| Wifi credentials | `/sdcard/wifi.txt` — plaintext, **never copy into the repo** |
| Transfer | **`scp` only — no rsync installed** |

### Durable device state — three things live outside the patch folder

**`/sdcard` is ext4 and survives a power cycle; `/tmp` is tmpfs and does not.** Everything the
instrument writes for itself is therefore on `/sdcard`, deliberately *outside*
`/sdcard/Patches/!/Cut It/`, so that `./deploy.sh`, `./deploy.sh --clean` and a power cycle cannot
touch any of it:

| | Written by | Read back with |
|---|---|---|
| `/sdcard/cut-it-state/` | `u_state`, on a flush or a commit | `tools/fetch-state.sh` |
| `/sdcard/cut-it-err.log` / `.cur` | `u_err`, on a 2 s dirty flag | `tools/fetch-errors.sh` |
| `/sdcard/wifi.txt`, `/sdcard/ap.txt` | the System menu | — |

⚠️ **`/tmp/patch` is a SYMLINK to the patch folder, and it is Pd's working directory.** So a
**relative** `[text write]` from inside a patch does not land in `/tmp/state` and does not wait for
mother's copy — it **mutates the deployed patch immediately**. Item 140. Use absolute paths for
anything meant to persist, which is what `u_state` does and why it needs no Save at all.

Hardware is **i.MX-based** (`imx-spdif`, `imx-hdmi-soc`, `usb-ci_hdrc` in the ALSA card list),
armv7. 495 MB RAM, 3.3 GB free on `/sdcard`.

**The root filesystem is mounted read-only.** Run `/root/fw_dir/scripts/remount-rw.sh` before
writing to `/root`, and `remount-ro.sh` after. `/sdcard` and `/usbdrive` are writable.

**`/root/.pdsettings` is load-bearing device-resident state.** It holds the `midiapi: 1` and
4-in/4-out configuration the whole MIDI topology depends on, plus `path1: /root/Pd/externals`,
which is what makes `[shell]`, `packOSC` and `routeOSC` resolve in the menu-launched patch.
✅ Backed up in [device/](device/), verified current against the hardware.

### ⚠️ The clock, and why device timestamps are not Mac timestamps

**There is no RTC. The device boots at `Sat Oct 17 01:08:30 UTC 2015`** — the image's build date —
and only jumps to the real time once `systemd-timesyncd` reaches the network. Two consequences,
both of which have already misled an investigation:

- **A file written in the first seconds after boot carries a 2015 timestamp.** `ls -l` output from
  a freshly-booted device is not in the order you expect.
- ⚠️ **The device runs UTC; the Mac runs local time.** Comparing a device file mtime against a
  Mac log line without converting produced an apparent **5.5-hour clock jump** that did not exist —
  the real explanation was simply that hours had passed between two `date` calls. **Convert, or
  compare device-to-device only.** `wifi-watch.log` is internally consistent, so uptime-to-failure
  read from *within* it is trustworthy.

### How Pd is launched

Pd is launched by the `mother` binary, not a shell script:

```
/usr/bin/pd -rt -nogui -audiobuf 6 -path /sdcard/PdExtraLibs /root/fw_dir/mother.pd main.pd
```

No `-noprefs` and no MIDI flags, so **`/root/.pdsettings` governs MIDI** and editing it is the
way to add devices. Note `-audiobuf 6` on the command line overrides `audiobuf: 4` in
`.pdsettings` — command-line flags win.

**`-nogui` means there is no Pd console.** Patch errors go to stdout on tty1, so VNC will not
show them either. This is why error reporting to the OLED is treated as an architecture
requirement rather than a debugging convenience — see [ref-conventions.md](ref-conventions.md).

### Measuring the running patch

CPU, load and UDP datagram rate, **without disturbing what is running**. Reads `/proc` rather than
using `top`, so it works on busybox:

```sh
ssh root@organelle.local '
  P=$(pgrep -nx pd)
  col() { awk "/^Udp:/{ if(h==\"\"){h=1; for(i=1;i<=NF;i++) if(\$i==\"OutDatagrams\") c=i; next} print \$c }" /proc/net/snmp; }
  T1=$(awk "{print \$14+\$15}" /proc/$P/stat); C1=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat); U1=$(col)
  sleep 5
  T2=$(awk "{print \$14+\$15}" /proc/$P/stat); C2=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat); U2=$(col)
  awk -v a=$T1 -v b=$T2 -v c=$C1 -v d=$C2 "BEGIN{printf \"pd CPU: %.1f %%\n\", 100*(b-a)/(d-c)}"
  echo "UDP out:  $(( (U2-U1)/5 )) datagrams/sec"
  echo "load:     $(cat /proc/loadavg)"
  aconnect -l | grep -c "Connecting To"
'
```

⚠️ **`pgrep -nx pd`, never `pgrep pd`** — the substring match hits a *kernel thread* on this
device, which is the bug that once had `fetch-errors.sh` reporting pd alive while it was killed.
[plan-tests.md](plan-tests.md) item 36.

**The baselines to compare against**, all on the deployed and idle patch:

| | CPU | UDP out |
|---|---|---|
| Phase 3 — home frame only | 8.2 % | 110/s |
| Phase 4 — multi-parameter display | 5.3 % | 117/s |
| Phase 5 — clock on two MIDI ports | **10.2 %** | 117/s |
| Phase 6 — Launchpad grid | **11.7–12.0 %** | 120/s |
| Phase 7 — phone status link | **11.7 %** | **122–126/s** |
| Phase 8 — the data store | 10.4–10.7 % | 115–116/s | ⚠️ **not comparable** — see below |

The datagram rate was the display alone and flat from Phase 3 to 6. **The Phase 5 CPU jump is the
clock** — ~96 ALSA MIDI writes a second rather than the DSP; two extra `c_clock` instances cost
only 0.4 points. Items 21, 37 and 75.

⚠️ **Phase 8's row is LOWER than Phase 7's, and that is not evidence `u_state` is free.** The rig
was in a different state — **4 ALSA links rather than 5**, so a controller was unplugged, and the
phone was not up. It bounds the cost as small and nothing more. Item 156. **Compare rows only when
the rig matches**; that is the whole reason each row names its phase rather than a date.

**Phase 7 is the first phase to move the UDP number**, and by a knowable amount: heartbeat 2/s,
repeated alert state 2/s, and the late-join repeat 1/s. ✅ **`u_net` costs about 0.2 CPU points.**
Items 118 and 134.

⚠️ **The 11.2 % budget the tooling still prints is Phase 5's, and Phase 6 already exceeded it.**
`tools/phase6-cpu.sh` reports OVER BUDGET against it, which is the script being stale rather than
a regression. Compare against the row above instead.

⬜ **One set of readings is unexplained**: 10.2–10.5 % during Phase 7's session, taken shortly
after patch reloads, against 11.7 % under controlled conditions minutes later. Recorded rather
than rationalised — item 134.

### MIDI: OSS vs ALSA

Out of the box, Pd here runs on **OSS MIDI**, not ALSA — `.pdsettings` has `flags: -alsamidi`
but **no `midiapi:` line**, and the `flags:` preference is not applied under `-nogui`. Under
OSS, devices appear as `/dev/midiN` where N tracks the ALSA card number, one node per card —
so the Launchpad's three separate ports collapse into one and Programmer Mode may be
unreachable.

ALSA MIDI *does* work on this build (`pd -alsamidi` registers a `Pure Data` client with in/out
ports). The fix is adding `midiapi: 1` to `/root/.pdsettings`. Under ALSA, Pd creates its own
virtual ports and hardware is wired to them with `aconnect` **by name**, which also solves
USB-enumeration-order drift across reboots.

### Deploying

`./deploy.sh` does the whole loop — syntax check, copy, reload the patch list, load the patch —
with no physical interaction. Flags and the reasoning are in
[ref-conventions.md](ref-conventions.md). Because there is **no rsync**, locally-deleted files
linger remotely: use `./deploy.sh --clean` after renaming or removing an abstraction, or a stale
`.pd` will shadow the new one.

Patch storage falls back from `/usbdrive` to `/sdcard` based on whether `/usbdrive` is
*mounted*, not whether it holds patches. An empty mounted USB drive yields an empty patch
menu; Storage → Eject unmounts it without physical removal.


## Wifi, and the boot hang

### Booting with the Launchpad attached — root-caused and fixed

It used to hang the Organelle on "loading…" forever. Not power, and not the hub — swapping
hubs, ports and cables changed nothing, because none of those was the cause.

**The Launchpad Pro MK3 presents a USB mass-storage interface** alongside its audio/MIDI ones:
a 192 KiB **write-protected** vfat volume, Novation's "Onboarding Drive". That is enough to
break boot, in four steps:

1. `mount.sh` takes **the last** `/dev/sd*` — with the Launchpad attached that is `/dev/sda1`.
2. `blkid` reports vfat, so the script mounts it on **`/usbdrive`**. It *succeeds* — this is not
   a failure path, which is why nothing errors.
3. `AppData::getDefaultUserDir()` returns `/usbdrive` whenever it is in `/proc/mounts`, so
   **`USER_DIR` becomes the Launchpad's read-only drive.**
4. `wifi_control.py` opens `$USER_DIR/wifi_log.txt` for **writing**. On a write-protected volume
   that fails, the script dies, and the UI never finishes loading.

**Every observation fits:** independent of hub, port and cable; broken when the Launchpad is
present at boot; fine when hot-plugged afterwards, because `mount.sh` has already run.

### Where the wifi credentials actually live

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
to us. **`wifi.txt` must never be copied into this repo**, and [device/](device/) deliberately does
not back it up.

**Adding a second network is the cheap way to a self-contained stage link**, and much lower risk
than `hostapd`: the Organelle simply joins whichever is present and **SSH survives**, where
bringing up an AP drops it. ⚠️ **An iPhone Personal Hotspot needs cellular**, so it cannot be
combined with airplane mode — the two are mutually exclusive. See [plan-v03.md](plan-v03.md).

### The tools that watch it

| Tool | Runs on | Does |
|---|---|---|
| `tools/wifi-watch.sh` | **the device** | Polls `wlan0`, and on a failure runs a **link probe** and a **DHCP probe** before a recovery ladder |
| `tools/wifi-poll.sh` | the Mac | Watches from outside, so a device that has gone silent still produces a record |
| `tools/wifi-report.sh` | the Mac | Summarises `wifi-watch.log` |
| `tools/wifi-reassociate.sh` | the device | The recovery rung that mirrors what the front panel does. **The only one that has ever worked** |

⚠️ **`--mark` goes AFTER a finding is written up, never before.** It draws the analysed-to-here line,
so running it first erases the event you were about to read.

⛔ **NEVER `pgrep -f wifi-watch`.** It matches the `ssh` command doing the checking, so a sweep that
scans and relaunches in one command kills its own session.

### ⚠️ The roam fault — what is known, and how to reproduce it

**On house wifi the device loses its IPv4 lease and does not get it back.** Open since Phase 6 and
misdiagnosed for two of them. ⚠️ **It is narrowed, not solved** — what remains open, and what is
being waited for, is in [plan-v03.md](plan-v03.md). Evidence: [plan-tests.md](plan-tests.md)
Session 14, items 169–189.

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
| ⬜ **Why nothing answers a DISCOVER after a roam** | **NOT established.** ⚠️ Say so plainly — this investigation has already produced two confident wrong answers |

**The repro — three seconds, no waiting:**

```sh
wpa_cli -i wlan0 scan ; sleep 4      # ⚠️ required: roam only targets a cached BSS
wpa_cli -i wlan0 roam <other-bssid>  # IPv4 gone within 3 s
```

⚠️ **Needs a supplicant started with a `ctrl_interface`**, which `wifi-reassociate.sh` writes and a
boot-started one may not. ⬜ Unverified after a power cycle — check `ls /var/run/wpa_supplicant/`.

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

### The Organelle as its own access point

**This is the stage configuration**, and it is the vendor's own path rather than a `hostapd`
project. `start-ap.sh` reads `$USER_DIR/ap.txt` — first line network, last line password — and
calls `create_ap --no-virt -n wlan0 $NET $PW`, defaulting to `Organelle` / `coolmusic`. This rig
uses **`organelle` / `definitelycutit`**, and the phone leases **192.168.12.109** from it.

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
link is solid** — AP-mode stability over a set-length window is still ⬜ unmeasured, item 45. And
it only holds if the AP is actually started: **a set run on house wifi is a client again.**

⚠️ **Start the AP from the SYSTEM MENU, not from a patch.** A patch that launches `start-ap.sh`
loses it the moment the next patch loads — `create_ap`, `hostapd` and `dnsmasq` all die with the
Pd that spawned them, **even behind `setsid nohup`**. Measured; [plan-tests.md](plan-tests.md)
item 129.

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

**Beware the wider blast radius.** `USER_DIR` is not only wifi — `start-ap.sh` reads
`$USER_DIR/ap.txt` and the System menu's save paths hang off it. And `mount.sh` runs on **every
Reload**, so this can appear mid-session, not just at boot. That is why `deploy.sh` sends
**`/reloadNoRemount`** rather than running `reload.sh`, which would trigger it on every single
deploy. ✅ Verified: `/usbdrive` stays clear through a full deploy.

**The fix is one guard in `mount.sh`** — refuse write-protected volumes, since the whole point
of `USER_DIR` is writing to it:

```sh
BASE=$(basename "$DEVICE" | sed 's/[0-9]*$//')
if [ "$(cat /sys/block/$BASE/ro 2>/dev/null)" = "1" ]; then
    echo "skipping write-protected device $DEVICE"; exit 1
fi
```

✅ Installed, and **verified by cold boot with the Launchpad attached**: boots normally, wifi
connects, `/usbdrive` stays unmounted. Factory version kept at
`/root/fw_dir/scripts/mount.sh.orig` and in [device/](device/). The rootfs is read-only, so
`remount-rw.sh` before and `remount-ro.sh` after.

**If it ever recurs:** `umount /usbdrive` clears it, no reboot needed. ⬜ Whether Novation
Components can disable the onboarding drive on the Launchpad itself is untried and tracked in
[plan-v03.md](plan-v03.md).


## Device capabilities

**Moved.** One page per device under [ref/device/](ref/device/) — the Launchpad, the nanoKONTROL,
the SP-404, the Volca, the Organelle's own panel and the phone. The gear list, the retired
BeatStep, the cubit and the pedal jack are on [ref/rig.md](ref/rig.md).

