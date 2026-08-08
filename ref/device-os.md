<!-- schema: freeform -->
# The Organelle as a computer

**SSH, paths, the read-only filesystem, how Pd launches, deploying, and wifi.** The *boxes and
cables* are on [rig.md](rig.md); the Organelle's own **control surface** — panel, OLED, aux LED — is
on [device/organelle.md](device/organelle.md).

✅ **Every path on this page was verified against the device on 2026-08-07**, after the cruft
cleanup. Two claims were wrong and are corrected below; the rest held.

## Signal flow

**On [rig.md](rig.md)** — MIDI, audio and power, plus the gear list and the cabling. The ALSA wiring
and the channel blocks are on [module/boot.md](module/boot.md).

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
| User patches | `/sdcard/Patches/!/` — `!` sorts to the top of the menu. ✅ **It holds `Cut It` and nothing else** since 2026-08-07. Anything you might reach for *instead* of playing goes in `! debug` — see [plan-v04.md](../plan-v04.md) |
| Pd config | `/root/.pdsettings` |
| Externals | `/root/Pd/externals` |
| Scripts | `/root/fw_dir/scripts/` |
| Extra libs | `/sdcard/PdExtraLibs` — **on Pd's search path but NOT PRESENT.** ⚠️ The path is passed on the command line by `mother` itself (`-path /sdcard/PdExtraLibs`, seen in the live `ps` line), *not* through `.pdsettings`, whose `npath: 1` points only at `/root/Pd/externals`. So the directory does not exist, and creating it would work — anything dropped in resolves. Verified 2026-08-07 |
| **Running patch** | **`/tmp/patch` — a SYMLINK to the patch folder**, and Pd's working directory. ⚠️ It exists only *while a patch is loaded*; mother creates it on load. Verified absent with none running |
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
✅ Backed up in [device/](../device/), verified current against the hardware.

⚠️ **Only `midiapi: 1` and MIDI devices 2–4 were added here.** `path1` and `flags: -alsamidi` are
**factory** — measured 2026-08-07 by diffing against the device's own `.pdsettings.bak`, which is
now kept as [device/pdsettings.orig](../device/pdsettings.orig). `path1` is still the thing the
instrument cannot boot without; it is simply not something this project set.

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
requirement rather than a debugging convenience — see [ref/architecture.md](architecture.md).

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
item 36.

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
`tools/display-cpu.sh` reports OVER BUDGET against it, which is the script being stale rather than
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
[ref/conventions.md](conventions.md). Because there is **no rsync**, locally-deleted files
linger remotely: use `./deploy.sh --clean` after renaming or removing an abstraction, or a stale
`.pd` will shadow the new one.

Patch storage falls back from `/usbdrive` to `/sdcard` based on whether `/usbdrive` is
*mounted*, not whether it holds patches. An empty mounted USB drive yields an empty patch
menu; Storage → Eject unmounts it without physical removal.

⛔ **A deploy can land the files and leave the OLD patch running, and nothing anywhere says so.**
The copy and the load are separate steps — a wifi drop between them is enough — and `oscsend` is
fire-and-forget UDP, so a clean exit from it proves only that a packet left the Mac. The result is
the worst shape available: **the deployed file greps as the current build while the instrument
behaves like the previous one**, and the two cannot be told apart from the Mac. It cost a whole
debugging session, in which a fix was hunted in code that was correct and already on the device
(item 243).

**`deploy.sh` now verifies the RUN rather than the file.** A successful load restarts Pd, so the
test is whether Pd is younger than the files just pushed — `/proc/<pid>`'s mtime is the process
start time, which needs one `test -nt` and no `ps` flags that differ between busybox and procps.
⚠️ Both sides of that comparison are **device-side**, which is the only safe way to compare
timestamps here — see *The clock* above.

⚠️ **The check cannot be skipped by `NOLOAD=1`** — that flag skips the load itself, so there is
nothing to verify. If you use it, select the patch from the front panel and know that until you do,
the device is running whatever it was running before.


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
to us. **`wifi.txt` must never be copied into this repo**, and [device/](../device/) deliberately does
not back it up.

**Adding a second network is the cheap way to a self-contained stage link**, and much lower risk
than `hostapd`: the Organelle simply joins whichever is present and **SSH survives**, where
bringing up an AP drops it. ⚠️ **An iPhone Personal Hotspot needs cellular**, so it cannot be
combined with airplane mode — the two are mutually exclusive. See [plan-v04.md](../plan-v04.md).

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

✅ **The watcher starts at boot** — `device/wifi-watch.service`, installed at
`/etc/systemd/system/` and enabled (item 244). ⛔ **Until it existed, every recovery disarmed the
detection for the next failure**, because a reboot is how this fault gets recovered and nothing
restarted the watcher afterwards. That is not hypothetical: three drops on **2026-08-08** produced
**no evidence at all**, the device having come up at 15:15 with nothing watching until 20:54.
`tools/wifi-poll.sh`'s relaunch is now the backstop for a mid-session death rather than the primary
mechanism, and it counts consecutive failed relaunches instead of retrying in silence.

⚠️ **`/root` is read-only** — `remount-rw.sh` before installing or enabling the unit, `remount-ro.sh`
after, because `systemctl enable` writes a symlink into `multi-user.target.wants/`.

### ⬜ 2026-08-08 — three drops that did NOT look like the roam fault

**Recorded here because it contradicts the signature below, and a future session will otherwise
re-derive it.** What was actually observed, and nothing more:

| | |
|---|---|
| From the Mac | `ssh` failed at **name resolution** (`Could not resolve hostname`), and `find-organelle.sh` returned **ABSENT** — no IPv4, and no IPv6 neighbour either, while it happily found another host at `.14` |
| On the device, afterwards | Associated, `192.168.1.9` held, −31 to −41 dBm, and **uptime unbroken across all three drops** — so no reboot |
| Roaming | Both radios appear in the log: `a6:40:a0:5e:a2:01` (36) and `…c9:25` (8) |

⛔ **This is NOT the documented signature.** Item 81 leaves the device associated and reachable over
IPv6 link-local throughout — that is what made it mysterious for two phases — and here **nothing
answered on either protocol**.

⬜ **Whether the lease was lost is not established**, and neither is anything else about these three:
the watcher was not running, and the device was reconnected by hand rather than recovering on its
own, so the recovery proves nothing either. ⚠️ **Do not fold these into the roam fault below without
new evidence.** This investigation has already produced two confident wrong answers; the honest
position is that item 244 now exists so the *next* one is recorded. See
[plan-v04.md](../plan-v04.md).

### ⚠️ The roam fault — what is known, and how to reproduce it

**On house wifi the device loses its IPv4 lease and does not get it back.** Open since Phase 6 and
misdiagnosed for two of them. ⚠️ **It is narrowed, not solved** — what remains open, and what is
being waited for, is in [plan-v04.md](../plan-v04.md). The measurements are in *The evidence, item by
item* below.

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

**And the one-line check for whether the fault is present right now:**

```sh
ssh root@organelle.local 'ip addr show wlan0 | grep "inet "'   # NO OUTPUT == this fault
```

⚠️ The device is still **associated** when this returns nothing — that is the whole point. "Drops its
wifi" describes the symptom and misdescribes the cause.

### The evidence, item by item

Every measurement the investigation rests on, and the four that turned out to be wrong. **The tools
cite these numbers by bare item — `wifi-watch.sh` alone names seven.**

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

**Four wrong turns, kept so nobody walks them again:**

| Item | Was claimed | Overturned by |
|------|-------------|---------------|
| 179 | *"The Organelle cannot get a lease on the satellite"* | **Item 182**, thirty minutes later — a controlled two-arm test **on the satellite** leased twice, in seconds, on the first DISCOVER. ⛔ **Over-claimed from a single A/B** |
| 178 | `UNRECOVERED` in the watcher's log | A **false negative** — the rung worked and the timeout was too short. The device had an address shortly afterwards |
| 161 | The recovery ladder's own verdict | ⚠️ **Two faults in our own measuring rig.** Rung 3 ran `/root/fw_dir/scripts/wifi-config.sh`, a **stale factory template** dated Feb 2020 hardcoded to `wpa_passphrase "name" "pass"` |
| 167 | The watcher's single-instance guard | ⚠️ **Only as good as the pidfile, and deleting it by hand disarms it.** Twice in one session two watchers ran, both times after a manual pidfile removal, because `wifi-poll.sh` relaunches whenever the stamp goes stale |
| 187 | The AP-visibility guard in the steer | ⚠️ **A sixth defect in the measuring rig: `iw scan` is not `iw scan dump`.** `iw dev wlan0 scan` **triggers a new scan**, so run right after a `wpa_cli scan` the two contend — and it reported NOT VISIBLE for an AP sitting at **−47 dBm** |
| 163 | A rewritten self-match check | ⛔ **The self-match trap bit a THIRD time, through a check written to avoid it.** A `/proc/*/cmdline` scan and a `case` pattern have the same flaw — **any** check whose own command line contains the string matches itself |

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
link is solid** — AP-mode stability over a set-length window is still ⬜ unmeasured, item 45. And
it only holds if the AP is actually started: **a set run on house wifi is a client again.**

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
`/root/fw_dir/scripts/mount.sh.orig` and in [device/](../device/). The rootfs is read-only, so
`remount-rw.sh` before and `remount-ro.sh` after.

**If it ever recurs:** `umount /usbdrive` clears it, no reboot needed. ⬜ Whether Novation
Components can disable the onboarding drive on the Launchpad itself is untried and tracked in
[plan-v04.md](../plan-v04.md).


## Device capabilities

**Moved.** One page per device under [ref/device/](device/) — the Launchpad, the nanoKONTROL,
the SP-404, the Volca, the Organelle's own panel and the phone. The gear list, the retired
BeatStep, the cubit and the pedal jack are on [ref/rig.md](rig.md).

