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
The real path is `wifi_setup.py` → `wifi.txt` → `wifi-config.sh`, which builds the config inline
with `wpa_passphrase`.

```sh
ssh root@organelle.local 'printf "SSID\nPASSWORD\n" >> /sdcard/wifi.txt'
```

⚠️ **The passwords are stored in the clear** — that is the device's design, not a choice available
to us. **`wifi.txt` must never be copied into this repo**, and [device/](device/) deliberately does
not back it up.

**Adding a second network is the cheap way to a self-contained stage link**, and much lower risk
than `hostapd`: the Organelle simply joins whichever is present and **SSH survives**, where
bringing up an AP drops it. ⚠️ **An iPhone Personal Hotspot needs cellular**, so it cannot be
combined with airplane mode — the two are mutually exclusive. See [plan-v02.md](plan-v02.md).

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
[plan-v02.md](plan-v02.md).

## The device itself

```sh
ssh root@organelle.local        # 192.168.1.15, password: organelle
```

| | |
|---|---|
| Home | `/root` (not `/home/music`) |
| Patches | `/sdcard/Patches/` — factory set lives here |
| User patches | `/sdcard/Patches/!/` — `!` sorts to the top of the menu |
| Pd config | `/root/.pdsettings` |
| Externals | `/root/Pd/externals` |
| Scripts | `/root/fw_dir/scripts/` |
| Extra libs | `/sdcard/PdExtraLibs` — already on Pd's search path |
| Transfer | **`scp` only — no rsync installed** |

Hardware is **i.MX-based** (`imx-spdif`, `imx-hdmi-soc`, `usb-ci_hdrc` in the ALSA card list),
armv7. 495 MB RAM, 3.3 GB free on `/sdcard`.

**The root filesystem is mounted read-only.** Run `/root/fw_dir/scripts/remount-rw.sh` before
writing to `/root`, and `remount-ro.sh` after. `/sdcard` and `/usbdrive` are writable.

**`/root/.pdsettings` is load-bearing device-resident state.** It holds the `midiapi: 1` and
4-in/4-out configuration the whole MIDI topology depends on, plus `path1: /root/Pd/externals`,
which is what makes `[shell]`, `packOSC` and `routeOSC` resolve in the menu-launched patch.
✅ Backed up in [device/](device/), verified current against the hardware.

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

The datagram rate was the display alone and flat from Phase 3 to 6. **The Phase 5 CPU jump is the
clock** — ~96 ALSA MIDI writes a second rather than the DSP; two extra `c_clock` instances cost
only 0.4 points. Items 21, 37 and 75.

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

### Launchpad Pro MK3 — a genuine blank slate

**Physical layout.** An 8×8 grid of RGB pads, surrounded by large function buttons on the
left, right and top, plus a double row of smaller buttons across the bottom. Left column
selects modes (Session, Note, Chord, Custom, Sequencer, Projects); right column is scene
launch; top row is navigation; bottom rows are track select and Ableton controls. In
Programmer Mode all of that labelling becomes meaningless — every button is just a note
number you define.

The pads are **velocity *and* pressure sensitive** (polyphonic aftertouch). They are not
switches.

**Programmer Mode** is officially documented (Novation publishes a
[Programmer's Reference Manual](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/LPP3_prog_ref_guide_200415.pdf)),
not a hack. In it:

- All built-in modes are disabled. The firmware gets out of the way completely; every pad
  just sends note-on/note-off.
- You drive every LED yourself. Note-on to a pad's note number, velocity selects from a
  128-colour palette. SysEx gives full RGB.
- Static / flashing / pulsing are MIDI channels 1 / 2 / 3 — so blinking a pad costs one
  message, no timing logic in Pd.
- Note layout is row/column encoded: pad at row *r*, column *c* is note `r*10+c` (11–88).
  `div 10` and `mod 10` gets you coordinates, no lookup table.
- Entering it is either a button combo (hold SETUP, press the bottom Scene Launch) or a
  SysEx message. ⚠️ **Entering via SysEx locks out the Settings menu**, and the only way back
  is the **Live Mode** SysEx — Novation documents a layout-select command as the escape, and
  ✅ that command does nothing at all on this unit. See [ref-midi.md](ref-midi.md).

Unit is a **MK3** (MK3 announced Jan 2020; a 09/2020 build date rules out MK1). Use the MK3
reference — SysEx headers and side-button note numbers differ from MK1.

### nanoKONTROL (mk1) — visible position, no host LEDs

Replaces the BeatStep (see *BeatStep retired*, below). 9 channels, each with **1 fader,
1 knob, 2 buttons**, plus a transport section and 4 on-device scenes. Class compliant,
USB bus-powered.

**The fit is good:** 9 knobs + 9 faders = 18 continuous controls against Cut It's 16.
**Two channels per filter** gives 2 knobs + 2 faders — exactly the four per filter — across
8 channels, leaving **one channel spare**.

⚠️ **That spare channel is not master tempo.** An earlier draft reserved it "for global volume or
master tempo"; Phase 5 put tempo on the **Organelle's own knob 1** instead, so the whole clock is
drivable on the Mac with no MIDI configured at all. The spare is genuinely spare. What any control
means is decided in `u_map` and nowhere else — see [ref-conventions.md](ref-conventions.md).

**The win over endless encoders is visible position.** A knob's physical position *is* the
display, which is the legibility problem the BeatStep could never solve.

**The cost is parameter pickup.** Any control serving two parameters stops matching its
stored value on a bank switch. The primary layer avoids this entirely via the 1:1 mapping,
but the shift layer still doubles up. Options are jump (snaps, jarring), pickup (dead until
it crosses the old value) or scaled. **Use jump** — a sudden parameter jolt is entirely on
brand here, so the usual reason to avoid absolute controllers mostly does not apply.

**No host-controllable LEDs.** External LED mode is a nanoKONTROL2-only feature; on the mk1
the button LEDs reflect local state only and Pd cannot drive them.

**Therefore: every button is momentary**, and Pd owns all toggle state. A toggle button with no host
LED control keeps its own state, and that state can silently desync from Pd's — exactly the
invisible-failure mode the FX-send routing was rejected over. Momentary buttons are pure events with
nothing to desync. **This is the reason the device is configured the way it is**, which is why it is
here rather than in [ref-midi.md](ref-midi.md) — that file has the CC map, the transport
reassignment and the Kontrol Editor settings.

**On the four scenes:** useful for multiplying control count, but they are hidden state — the
device switches locally and Pd has no idea. Assign **distinct CC numbers per scene** so Pd
infers the active scene from which CCs arrive. Do that and scene switching self-announces;
don't, and it is the unlabelled-knob problem in a worse form.

✅ Configured and verified on hardware. Arrives on **Pd channel 17**, transport on 18. The scene
file — device-resident state that a factory reset wipes — is backed up in [device/](device/).

### BeatStep retired

Dropped from the plan. Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps ×
8-note poly vs 16 steps mono), its 16 pads are beaten comprehensively by 64 RGB
pressure-sensitive ones, and its CV/Gate outputs are irrelevant with no modular in the rig.

It does have host-controllable pad LEDs (red, on/off) which the nanoKONTROL mk1 lacks — the
one axis where it wins. But the Launchpad covers every state-display need in the rig, and
visible knob position plus a bank of faders is worth more here than a second grid of red
lights.

### SP-404 MIDI — verified working, both directions
Confirmed on hardware with **no settings changes required** — the 404's factory MIDI config is
already correct for this rig. Arrives on **Pd channel 33** (device 3). The full message map and
the device settings that matter are in [ref-midi.md](ref-midi.md).

⬜ **One unresolved discrepancy:** pad *n* on bank A was measured here as note 47 + *n*, but
Roland's chart says the mode-A range is 35–51, and only pads 1 and 2 were ever checked. Detail in
[ref-midi.md](ref-midi.md); resolving it is tracked in [plan-v02.md](plan-v02.md), where it is the
open question most able to corrupt work silently.

**Cable warning:** the 404 needs a genuine **data** USB cable. Charge-only USB-A→C cables are
visually identical and extremely common; two were tried before one worked. If the device does
not appear in `lsusb`, suspect the cable before anything else.


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

What physically connects to what. **What is still to buy is in [plan-v02.md](plan-v02.md)**
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
