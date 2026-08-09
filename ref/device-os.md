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
patch that assumed the wiring survived reached nothing. ⛔ **The reason is that `/loadPatch` replaces
the Pd process outright** — `MainMenu::runPatch` runs `killpatch.sh` before it launches anything, and
that script SIGTERMs and then SIGKILLs every `pd` — so no subscription of the old process can survive
and re-wiring is not optional (item 252). ✅ **This is why `u_init` runs `wire.sh`** — Cut It re-wires
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

### ⚠️ Sending the device a UDP datagram — never with netcat

Several patches here bind a UDP port and wait to be poked: a bench's GO on 9998, `lp-monitor.pd` on
9996, `dsp-toggle.pd` on 9997. **`nc` cannot do it from a Mac and does not exist on the device.**

| | |
|---|---|
| **BSD `nc -u -w0`** | ✅ Measured to send **nothing**. It exits before the datagram is flushed |
| **`nc -u -w1`** | ✅ Measured to fail here too |
| **On the device** | ✅ busybox has **no `nc` at all**, so "from an SSH window on the device" never worked |

⛔ **It looks exactly like a dead patch.** The port *is* bound — `netstat -lun` on the device shows
it — so the failure is entirely on the sending side, and every symptom points at the patch. Use a
socket send, which is deterministic:

```python
import socket
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"go;\n", ("organelle.local", 9998))
```

⛔ **The trailing newline is required.** `b'live ;'` — a space and no newline — is accepted by the
socket and **dropped by `netreceive`**, which is the same silent nothing as above. Item 250.

**`test/run.sh` sends its own GO** and is the normal way to drive a bench; `tools/dsp.sh` does the
same for DSP. Nothing needs to be typed by hand.

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
`/sdcard/Patches/!/Cut It/`, so that `./tools/deploy.sh`, `./tools/deploy.sh --clean` and a power cycle cannot
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
- ⚠️ **A timestamp WRITTEN before the jump and READ after it looks ancient.** `wifi-watch` stamps
  its liveness file with `date +%s`, so a stamp written during boot reads as **~11 years stale** for
  the few seconds until its next tick rewrites it. `wifi-poll.sh` therefore fires one spurious
  *"watcher was dead — relaunched"* per boot; the one-instance guard refuses it and the next tick
  clears it. ⚠️ **Left alone deliberately** — a rule that ignored implausibly old stamps would also
  mask a genuinely long-dead watcher.
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

⛔ **The budget belongs to the newest row that matches your rig, and `tools/display-cpu.sh` tracks
it from here.** It printed Phase 5's 11.2 % for three phases after Phase 6 exceeded it, so every
run said OVER BUDGET and the verdict stopped carrying information — **a threshold nobody moves is a
threshold nobody reads.** It now reads **12.7 %**, Phase 7's full-rig 11.7 % plus one point.
**When this table gains a row, move that number and name the row it came from.**

✅ **10.2–10.5 % is the idle baseline, not an artefact — item 134 closed, item 254.** Those
readings had been held open on the suspicion that they were taken *shortly after patch reloads*.
Re-measured on an untouched instrument **1 h 32 m after the last reload**, with all four devices
wired (8 ALSA links) and nobody playing it: **10.4 %, 10.2 %, 10.7 %** across three five-second
readings, UDP out 111–113/s. Proximity to a reload was never the explanation — this simply *is* what
the patch costs sitting still.

⛔ **And it is Phase 5's number, which means `g_grid` is free when nothing changes.** Phase 5
measured 10.2 % with no grid code in the patch at all; the grid arrived in Phase 6 and idle still
costs the same. That is the dirty-flag gating working on real hardware — `g_grid` repaints only when
something changed, so with the transport stopped it sends nothing and adds nothing.
`tools/display-cpu.sh`'s own budget check is exactly this test.

⚠️ **The transport state was inferred, not read.** At 120 BPM a running beat row repaints twice a
second and lands on Phase 6's 11.7–12.0 % row; these readings sit a point and a half below it, which
is why they are recorded as idle-and-stopped. **The 11.7 % readings are a different rig state, not a
contradiction** — which is the rule this table already states.

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

`./tools/deploy.sh` does the whole loop — syntax check, copy, reload the patch list, load the patch —
with no physical interaction. Flags and the reasoning are in
[ref/conventions.md](conventions.md). Because there is **no rsync**, locally-deleted files
linger remotely: use `./tools/deploy.sh --clean` after renaming or removing an abstraction, or a stale
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

**`tools/deploy.sh` now verifies the RUN rather than the file.** A successful load restarts Pd, so the
test is whether Pd is younger than the files just pushed — `/proc/<pid>`'s mtime is the process
start time, which needs one `test -nt` and no `ps` flags that differ between busybox and procps.
⚠️ Both sides of that comparison are **device-side**, which is the only safe way to compare
timestamps here — see *The clock* above.

⚠️ **The check cannot be skipped by `NOLOAD=1`** — that flag skips the load itself, so there is
nothing to verify. If you use it, select the patch from the front panel and know that until you do,
the device is running whatever it was running before.


## Booting with the Launchpad attached — root-caused and fixed

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

⛔ **This is a USB mass-storage fault, not a wifi fault.** Wifi is only the first thing that tries
to write to `USER_DIR`, and therefore the first thing to die. **Do not look for it on
[wifi.md](wifi.md).**

⛔ **`mount.sh` runs on every Reload, so it can appear mid-session and not only at boot.** That is
why `tools/deploy.sh` sends **`/reloadNoRemount`** rather than running `reload.sh`, which would
trigger it on every single deploy. ✅ Verified: `/usbdrive` stays clear through a full deploy.

⚠️ **`USER_DIR` is not only wifi.** `start-ap.sh` reads `$USER_DIR/ap.txt` and the System menu's
save paths hang off it, so a bad mount breaks Save and AP mode too.

**The fix is one guard in `mount.sh`** — refuse write-protected volumes, since the whole point of
`USER_DIR` is writing to it. ⛔ **The patch itself, the three verifications, the revert and the
recovery are in [device/README.md](../device/README.md)**, which is where the modified file and
its factory original are both kept. The drive is described on
[device/launchpad.md](device/launchpad.md), and turning it off at the Launchpad was considered and
declined there (item 265).

## Wifi

**Moved.** The credentials, the watchers, the roam fault, the evidence ledger and the Organelle as
its own access point are on [wifi.md](wifi.md). The boot hang above merely looked like a wifi
fault and is a different thing.

## Device capabilities

**Moved.** One page per device under [ref/device/](device/) — the Launchpad, the nanoKONTROL,
the SP-404, the Volca, the Organelle's own panel and the phone. The gear list, the retired
BeatStep, the cubit and the pedal jack are on [ref/rig.md](rig.md).

