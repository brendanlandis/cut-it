<!-- schema: freeform -->
# The Organelle as a computer

**How Cut It lives on the Organelle: where it keeps its data, how it is measured and deployed.** What
the Organelle *is* as a computer — SSH, paths, the read-only filesystem, how Pd launches, the clock,
the OSS/ALSA MIDI question, the boot hang with a Launchpad attached, wifi — is in Reference:
`~/Sites/!reference/critter-guitari-organelle-1.md`. The *boxes and cables* are on [rig.md](rig.md);
the Organelle's own **control surface** — panel, OLED, aux LED — is on
[device/organelle.md](device/organelle.md).

## Signal flow

**On [rig.md](rig.md)** — MIDI, audio and power, plus the gear list and the cabling. The ALSA wiring
and the channel blocks are on [module/boot.md](module/boot.md).

⛔ **Loading any patch drops Pd's ALSA connections** (Reference, item 228): `/loadPatch` replaces the Pd
process outright, so re-wiring is not optional (item 252). ✅ **This is why `u_init` runs `wire.sh`** —
Cut It re-wires itself every load and so never notices. ⚠️ **Any patch that is not Cut It must make its
own `aconnect` call**, or it measures silence (item 225).

`/root/.pdsettings` — the `midiapi: 1` and 4-in/4-out configuration the whole MIDI topology depends on —
is backed up in [device/](../device/), verified current against the hardware; the factory original is
kept as [device/pdsettings.orig](../device/pdsettings.orig).

## The device itself

Cut It's own places on the device (the rest of the layout is in Reference):

| | |
|---|---|
| User patches | `/sdcard/Patches/!/` — **It holds `Cut It` and nothing else.** Anything you might reach for *instead* of playing goes in `! debug` — see [module/debug.md](module/debug.md) |
| **Instrument data** | **`/sdcard/cut-it-state/`** — what `u_state` writes. Not config, not deployed |
| Error log | `/sdcard/cut-it-err.log` (rolled) and `.cur` (running session) |
| Wifi credentials | `/sdcard/wifi.txt` — **never copy into the repo** |

**`test/run.sh` sends its own GO** to the benches (a UDP datagram to the device; see Reference for why it
is never `nc`) and is the normal way to drive a bench; `tools/dsp.sh` does the same for DSP. Nothing
needs to be typed by hand.

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

### Measuring the running patch

CPU, load and UDP datagram rate, **without disturbing what is running**. Reads `/proc` rather than
using `top`, so it works on busybox (the `pgrep -nx pd` caution is in Reference):

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
clock, and it is DSP cost, not MIDI cost** — toggling DSP off drops `pd` to under 5 % while the
MIDI rate leaves it unchanged; see [module/tempo.md](module/tempo.md). Two extra `c_clock`
instances cost only 0.4 points. Items 21, 37 and 75.

⚠️ **Phase 8's row is LOWER than Phase 7's, and that is not evidence `u_state` is free.** The rig
was in a different state — **4 ALSA links rather than 5**, so a controller was unplugged, and the
phone was not up. It bounds the cost as small and nothing more. Item 156. **Compare rows only when
the rig matches**; that is the whole reason each row names its phase rather than a date.

**Phase 7 is the first phase to move the UDP number**, and by a knowable amount: heartbeat 2/s,
repeated alert state 2/s, and the late-join repeat 1/s. ✅ **`u_net` costs about 0.2 CPU points.**
Items 118 and 134.

⛔ **The budget belongs to the newest row that matches your rig, and `tools/display-cpu.sh` holds
it: 12.7 %**, Phase 7's full-rig 11.7 % plus one point. A threshold that stays put while the patch
grows says OVER BUDGET on every run and stops carrying information — **a threshold nobody moves is a
threshold nobody reads. When this table gains a row, move that number and name the row it came from.**

✅ **10.2–10.7 % is the idle baseline — item 254.** Measured on an untouched instrument **1 h 32 m
after the last reload**, with all four devices wired (8 ALSA links) and nobody playing it:
**10.4 %, 10.2 %, 10.7 %** across three five-second readings, UDP out 111–113/s. This is what the
patch costs sitting still.

⛔ **And it is Phase 5's number, which means `g_grid` is free when nothing changes.** Phase 5
measured 10.2 % with no grid code in the patch at all; the grid arrived in Phase 6 and idle still
costs the same. That is the dirty-flag gating working on real hardware — `g_grid` repaints only when
something changed, so with the transport stopped it sends nothing and adds nothing.
`tools/display-cpu.sh`'s own budget check is exactly this test.

⚠️ **The transport state was inferred, not read.** At 120 BPM a running beat row repaints twice a
second and lands on Phase 6's 11.7–12.0 % row; these readings sit a point and a half below it, which
is why they are recorded as idle-and-stopped. **The 11.7 % readings are a different rig state, not a
contradiction** — which is the rule this table already states.

### Deploying

`./tools/deploy.sh` does the whole loop — syntax check, copy, reload the patch list, load the patch —
with no physical interaction. Flags and the reasoning are in
[ref/conventions.md](conventions.md). Because there is **no rsync**, locally-deleted files
linger remotely: use `./tools/deploy.sh --clean` after renaming or removing an abstraction, or a stale
`.pd` will shadow the new one.

**`tools/deploy.sh` verifies the RUN rather than the file.** A successful load restarts Pd, so the
test is whether Pd is younger than the files just pushed — `/proc/<pid>`'s mtime is the process
start time, which needs one `test -nt` and no `ps` flags that differ between busybox and procps.
⚠️ Both sides of that comparison are **device-side**, which is the only safe way to compare
timestamps here — see *The clock* above.

⚠️ **The check cannot be skipped by `NOLOAD=1`** — that flag skips the load itself, so there is
nothing to verify. If you use it, select the patch from the front panel and know that until you do,
the device is running whatever it was running before.

## Booting with the Launchpad attached

The boot hang — a Launchpad's write-protected onboarding drive mounted as `USER_DIR` — is in Reference,
with its chain and signature. ⛔ **It is a USB mass-storage fault, not a wifi fault; do not look for it
on [wifi.md](wifi.md).**

`tools/deploy.sh` sends **`/reloadNoRemount`** rather than running `reload.sh`, which would run
`mount.sh` on every single deploy. ✅ Verified: `/usbdrive` stays clear through a full deploy.

⛔ **The patch itself, the three verifications, the revert and the recovery are in
[device/README.md](../device/README.md)**, which is where the modified `mount.sh` and its factory
original are both kept. Turning the drive off at the Launchpad was considered and declined (item 265,
[device/launchpad.md](device/launchpad.md)).

## Wifi

⛔ **The Organelle's own wifi facts are in Reference; the tools, the stage procedure and the open
questions are on [wifi.md](wifi.md).** ⚠️ **The boot hang above merely looked like a wifi fault and is
a different thing.**

## Device capabilities

One page per device under [ref/device/](device/) for how Cut It uses it, and the devices themselves in
Reference. The gear list, the retired BeatStep, the cubit and the pedal jack are on [ref/rig.md](rig.md).
