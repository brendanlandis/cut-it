# Cut It — Rig Plan

Hardware setup plan for the Cut It instrument. Companion to
[README.md](<! v0.1 plans/README.md>), which covers the Pd patch itself.

Target hardware: **Organelle 1** (the original, not M/S/S2).

---

## Overview

The Organelle is the brains. It runs the Cut It patch, acts as USB MIDI host for every
controller, and is the clock master for the whole rig.

The SP-404MK2 is the sample store and the front end. It holds drum samples and fx samples,
takes the mic and any arbitrary audio input, and feeds two independent mono streams into
the Organelle — drums on the left, fx on the right. Cut It captures and mangles what
arrives, and its two outputs go to the mixer.

Two channels through one stereo cable is the trick that makes this work: the Organelle has
a single 1/4" TRS input jack, so the 404's L and R arrive as the tip and the ring — which the
patch reads as `[r~ inL]` and `[r~ inR]`, never `adc~`. See *Signal flow — audio* below.


## Signal flow — MIDI

Everything is USB. The Organelle is a USB host; all four devices are class compliant.

```
                  ┌──────────────────────────────────┐
                  │  ORGANELLE                       │
                  │  Pd / Cut It — CLOCK MASTER      │
                  └────────────────┬─────────────────┘
                                   │ USB-A
                  ┌────────────────▼─────────────────┐
                  │       POWERED USB HUB            │
                  └──┬─────────┬─────────┬────────┬──┘
          USB-A→C ┌──┘         │         │        └──┐ USB-A
                  ▼            ▼ USB-A   ▼ USB-A→C   ▼
        ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌───────────────┐
        │ LAUNCHPAD    │  │ nano    │  │SP-404MK2 │  │ USB→DIN MIDI  │
        │ PRO MK3      │  │ KONTROL │  │          │  │ INTERFACE     │
        │ ch 1–16      │  │ch 17–32 │  │ ch 33–48 │  │ ch 49–64      │
        └──────────────┘  └─────────┘  └──────────┘  └───────┬───────┘
                                                             │ DIN
                                                             ▼
                                                     ┌───────────────┐
                                                     │  VOLCA FM     │
                                                     │  (receive only)│
                                                     └───────────────┘
```

**Why no MIDI merge box.** Pd namespaces each input device into its own block of 16 channels, so
which device a message came from is free information. A merge box would flatten everything into one
stream and throw that away. **The addressing model, and the trap that "device *n*" means Pd's input
slot rather than the system MIDI list, are in [ref-midi.md](ref-midi.md)** — that file owns the wire
format; this one owns the boxes and cables.

`MAXMIDIINDEV` is 16 in Pd (verified in both 0.49 and 0.53 source), so four devices is
nowhere near the limit.

**Done:** Pd only opens the MIDI devices it is told to at launch, and it reads that from
`/root/.pdsettings`, not command-line flags — mother passes none. The device is configured for
**4 in / 4 out** with `midiapi: 1` (which forces ALSA MIDI; without it Pd falls back to OSS
and the Launchpad's three ports collapse into one). Verified surviving a cold boot. Backup at
`/root/.pdsettings.bak`.

**Devices are wired to Pd's ports with `aconnect`, by name** — and the patch does this itself
at load time via `[shell]`, because mother's `alsaconnect.sh` only connects one device. See
`tools/wire.sh`.

⛔ **LOADING ANY PATCH DROPS PD'S ALSA CONNECTIONS — measured, item 228.** After
`oscsend localhost 4001 /loadPatch …`, `Pure Data Midi-Out 4` had **no target at all**, and a probe
patch that assumed the wiring survived reached nothing. The Pd *process* persists across a patch
swap, but its port connections do not. ✅ **This is exactly why `u_init` runs `wire.sh`** — Cut It
re-wires itself every load and so never notices. ⚠️ **Any patch that is not Cut It must make its own
`aconnect` call**, or it measures silence — and silence from a MIDI probe reads as *"the device
ignores this message"*, which is the wrong conclusion and the precise shape of item 225. Verify with:

```sh
aconnect -l | grep -A2 "Midi-Out 4"        # expect: Connecting To: <the Uno's client>:0
```

**Direction:** the Organelle is clock master. Disable clock-out on every other device —
particularly the 404's "MIDI Sync Out", which will otherwise echo clock back and create a
loop.

**Keep sending clock — it is not decorative.** An earlier draft of this plan claimed it was,
on the grounds that nothing external runs its own sequencer during a performance. That was
wrong: the 404's **BPM SYNC time-stretch follows its tempo**, and the only way it learns the
tempo is by measuring incoming clock intervals. Stop the clock and it stretches to a stale
local value. See *Time-stretch* in [ref-software.md](ref-software.md).

**The Launchpad runs over USB.** Its TRS MIDI jacks go unused, and the three TRS→DIN
adapters in its box aren't needed here. USB gives it its own 16-channel block, keeps
Programmer Mode on the documented path, and means one cable does both power and data — at
the cost of the hub current, which is what the powered hub is for.


## Signal flow — audio

```
  [mic] ──────────────► SP-404 MIC/GUITAR IN  (1/4" TRS, mono)
  [arbitrary source] ─► SP-404 LINE IN

                    ┌───────────────────────────────┐
                    │        SP-404MK2              │
                    │  drum samples → pan MONO L    │
                    │  fx samples   → pan MONO R    │
                    │  use BUS 1/2 only (see below) │
                    └────────┬─────────────┬────────┘
                        OUT L│             │OUT R
                      (drums)│             │(fx)
                             ▼             ▼
                    ╔════════ Y-CABLE (2×TS → 1×TRS) ════════╗
                                     │
                    ┌────────────────▼──────────────┐
                    │  ORGANELLE   IN (TRS stereo)  │
                    │    adc~ 1  = drums  (tip)     │
                    │    adc~ 2  = fx     (ring)    │
                    │  ─────── Cut It ───────       │
                    └───────┬───────────────┬───────┘
                       OUT L│               │OUT R
                            ▼               ▼
                    ┌──────────────────────────────────┐
                    │  XENYX Q802USB                   │
                    │   ch1  Organelle L  (drums)      │
                    │   ch2  Organelle R  (fx)         │
                    │   ch3/4  Volca FM                │
                    │   ch5/6  spare                   │
                    └────────────────┬─────────────────┘
                                     ▼  MAIN OUT
                                   [ PA ]
```

Organelle L/R go to the two **mono** channels (1 and 2) rather than a stereo pair, so drums
and fx each get their own 3-band EQ and one-knob compressor.

**The Organelle's jack complement**, quoted from the official Organelle 1 manual: 📄

> The single `In`(put) `LR` port is a 1/4" TRS (stereo) jack.
> The `L`(eft) and `R`(ight) `Out`(put) ports are both 1/4" TS (mono) jacks.

So: **one stereo input jack, two mono output jacks.** This asymmetry is why the TRS Y-cable is
required — the 404's two discrete mono outputs have to merge into the Organelle's single input
jack — while the output side needs only two ordinary patch cables.

**A patch never touches `adc~` or `dac~`.** ✅ `mother.pd` owns the sound card and hands the
patch `[r~ inL]` / `[r~ inR]`, taking its output back through `[throw~ outL]` / `[throw~ outR]`
— then applying the volume knob (a square law, smoothed at 5 Hz) and a `clip~ -1 1` limiter
before `dac~`. Writing to `dac~` from a patch bypasses both. Full detail and the reasoning are
in [ref-conventions.md](ref-conventions.md) under *Audio I/O*.

**The input split is verified on hardware.** ✅ `adc~ 1` is the **tip**, `adc~ 2` is the
**ring**, and they are genuinely independent — a mono TS cable drives the tip to the 90s on
`env~`'s scale while the ring stays at the 18–19 noise floor. Measured with
`tools/audio-probe/`; full numbers in [plan-tests.md](plan-tests.md) item 11.

Two numbers worth remembering: the **input noise floor is ~18–19** on `env~`'s 0–100 dB scale
(≈ −82 dBFS), so a noise gate belongs around 25–30; and a **passive bass reaches the 90s**, so
there is ample gain and headroom for instrument-level sources.


## Signal flow — power

```
  power strip
    ├── ORGANELLE ........ 9VDC 1000mA centre-positive   (included)
    ├── SP-404MK2 ........ Roland PSD adapter            (included)
    ├── XENYX Q802USB .... own PSU                       (included)
    ├── POWERED USB HUB .. own PSU                       (comes with hub)
    │     ├── Launchpad Pro MK3
    │     ├── nanoKONTROL
    │     └── USB→DIN MIDI interface
    └── VOLCA FM ......... Korg KA-350 9V (or 6×AA)
```

**Do not bus-power the 404.** Roland requires USB-C-to-C at 5V/1.5A for bus power and does
not guarantee operation through hubs. A USB-A→C cable from the hub carries **data only**,
which is what we want — the 404 runs off its own adapter and costs the hub nothing.

### Booting with the Launchpad attached ✅ root-caused and fixed

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

### Where the wifi credentials actually live ✅

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

### ⚠️ The roam fault — what is known, and how to reproduce it ✅

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

### The Organelle as its own access point ✅

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

## The device itself

```sh
ssh root@organelle.local        # password: organelle
```

⚠️ **The IPv4 address is DHCP-assigned and NOT stable.** It has been observed as `192.168.1.11`,
`.15`, `.18` and `.20`; a recovery that flushes the interface can come back on a different one.
**Always use `organelle.local`** — mDNS follows it, and every script here defaults to that. The
literal addresses in `HOST=` examples are fallbacks for when mDNS is flaky, and must be re-checked
before use rather than trusted.

### ⚠️ "Cannot reach" after a wifi drop — CHECK IPv6 BEFORE BELIEVING IT ✅

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

### Durable device state — three things live outside the patch folder ✅

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


## Device capabilities

What each box can actually do, verified on hardware. What to *build* with it lives in
[ref-software.md](ref-software.md); the message-by-message detail — every CC, note and
SysEx each device accepts and transmits — lives in [ref-midi.md](ref-midi.md).

### Launchpad Pro MK3

**Moved** to [ref/launchpad.md](ref/launchpad.md), which is now the only page about this device.

### nanoKONTROL (mk1)

**Moved** to [ref/nanokontrol.md](ref/nanokontrol.md).

### BeatStep retired

Dropped from the plan. Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps ×
8-note poly vs 16 steps mono), its 16 pads are beaten comprehensively by 64 RGB
pressure-sensitive ones, and its CV/Gate outputs are irrelevant with no modular in the rig.

It does have host-controllable pad LEDs (red, on/off) which the nanoKONTROL mk1 lacks — the
one axis where it wins. But the Launchpad covers every state-display need in the rig, and
visible knob position plus a bank of faders is worth more here than a second grid of red
lights.

### SP-404 MIDI

**Moved** to [ref/sp404.md](ref/sp404.md), which is now the only page about this device.

---


### The pedal jack

`mother.pd` exposes `fs` / `fsRaw` / `footSwitchPolarity` and `exp` / `expRaw` / `expOverride`
on the 1/4" pedal jack — a sustain-style switch **or** an expression pedal, one or the other,
not both. Deliberately unused in v0.2, and recorded here so it isn't rediscovered as news.


## Gear

### Owned
| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Roland SP-404MK2 | Sample store, mic/line front end, drums + fx source |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Korg nanoKONTROL (mk1) | Continuous control — 9 faders, 9 knobs, 18 buttons, transport |
| Novation Launchpad Pro MK3 | Cut It interface (Programmer Mode) + compose-time sequencing |
| MeeBlip cubit (original) | **See below — does not do what we need** |
| Arturia BeatStep | **Retired from the plan** — see *BeatStep retired* above |

### The original cubit does not work here
The original cubit is a **thru box only**: 1 DIN in → 4 DIN out. Its USB port supplies
**power only and carries no data**, so it cannot act as a USB MIDI interface for the
Organelle. (That capability came later, in the cubit *go* and cubit *duo*.)

Keep it. It becomes useful the moment you add a second or third DIN-only synth — put it
downstream of the MIDI interface and fan out to four destinations. For now only the Volca
FM needs DIN, so a 1×1 interface is enough.


## Cabling

What physically connects to what. **What is still to buy is in [plan-v03.md](plan-v03.md)**
under *Still to acquire*; power supplies are all covered.

| Cable | Connects |
|---|---|
| **1/4" TRS male → 2× 1/4" TS male** ("insert cable") | 404 OUT L/R → the Organelle's single stereo input. ⚠️ The critical cable in the rig — nothing else does this job |
| **USB-A → USB-C** | Hub → SP-404MK2, **data only**. The 404 ships without one |
| **2× 1/4" TS** | Organelle OUT L/R → mixer ch1/ch2 |
| **3.5mm TRS → 2× 1/4" TS** | Volca FM → mixer ch3/4. Its output runs hot — start with channel gain low |
| **XLR female → 1/4" TRS** | Mic → 404 MIC/GUITAR IN. The 404 has no XLR, so a plain mic cable won't do it; an adapter on a normal one works |
| **2× 1/4" TS** | Mixer MAIN OUT → PA |

**Already in the box, don't buy:** the Launchpad ships with USB-C→USB-A *and* USB-C→USB-C
cables, a power adapter and 3× TRS-minijack→DIN MIDI adapters; the nanoKONTROL is bus-powered
over its own cable; the 404 has its PSD adapter.

**Label the cables.** With this many identical 1/4" jacks it is worth the ten minutes.
