# Cut It

A cut-up / harsh noise instrument patch for the **original Critter & Guitari Organelle**
(a.k.a. Organelle 1 — *not* the M, S, or S2). Pure Data.

Early design stage. Most of it is not built yet, and a rewrite from scratch is on the table.
See [README.md](README.md) for the musical intent and control layout.


## Hard constraints — read before writing any Pd

**Target is Pd vanilla 0.49.** Verified on the device: `Pd-0.49.0, compiled Oct 9 2018`.
The Organelle 1 runs OS 4.0, which is the release that brought its Pd up from 0.46. OS 4.1
is the last version for this hardware; 4.2 and OS 5 are M/S/S2 only. Do not suggest objects
newer than 0.49.

**Never save an Organelle-bound patch from plugdata.** plugdata is built on Pd 0.55+ and
rewrites `.pd` files into a newer format — iemgui colours become hex (`#fcfcfc` instead of
`-262144`), floatatoms gain a trailing arg. Pd 0.49 cannot parse that. This has already
happened once in this repo. Edit with **vanilla Pd 0.49** for anything that ships to hardware.

**Vanilla by default.** The Organelle ships neither ELSE nor cyclone. Bundling them is
*possible* — the device is **armv7** and armv7 builds exist — but current ELSE requires
Pd 0.56+, so you would need a ~2019-vintage release. Pd 0.49 also expects the `.pd_linux`
extension, not the newer `.l_arm` naming. Pure-Pd abstractions can simply be dropped in the
patch folder with no such concerns. Prefer vanilla unless there is a specific object worth
the dependency.

**The `critterandguitari/Organelle_OS` GitHub repo targets CM3/CM4 hardware — that is the
Organelle M and S2, not this device.** Its paths are wrong here (it uses `/home/music`, an
`audioinjector-pi-soundcard`). The mechanisms are the same lineage, but verify paths against
the actual device before relying on them.


## Layout

```
Cut It/            the deployable patch — folder name is what appears in the Organelle menu
deploy.sh          scp-based deploy (there is no rsync on the device)
rig-plan.md        the physical rig — wiring, MIDI/audio/power, verified device behaviour
design-notes.md    how the instrument works — architecture, timing model, decisions
pre-flight-tests.md  ordered hardware checks to run before UI/UX work
README.md          musical intent, filter chain, button/knob map
```

An Organelle patch is a **folder** containing `main.pd` (the entry point) plus its
abstractions, optionally `knobs.txt` (OLED knob labels) and audio assets.


## The device

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

**The root filesystem is mounted read-only.** Run `/root/fw_dir/scripts/remount-rw.sh`
before writing to `/root`, and `remount-ro.sh` after. `/sdcard` and `/usbdrive` are writable.

Pd is launched by the `mother` binary, not a shell script. The actual invocation is:

```
/usr/bin/pd -rt -nogui -audiobuf 6 -path /sdcard/PdExtraLibs /root/fw_dir/mother.pd main.pd
```

No `-noprefs` and no MIDI flags, so **`/root/.pdsettings` governs MIDI** and editing it is
the way to add devices. Note `-audiobuf 6` on the command line overrides the `audiobuf: 4`
in `.pdsettings` — command-line flags win.

`-nogui` means there is **no Pd console**. Patch errors go to stdout on tty1, so VNC will not
show them. Getting error output somewhere visible is an unsolved part of the workflow.

### MIDI: OSS vs ALSA

The hardware is **i.MX-based** (`imx-spdif`, `imx-hdmi-soc`, `usb-ci_hdrc` in the ALSA card
list), armv7. 495MB RAM, 3.3GB free on `/sdcard`.

Out of the box, Pd here runs on **OSS MIDI**, not ALSA — `.pdsettings` has `flags: -alsamidi`
but **no `midiapi:` line**, and the `flags:` preference is not applied under `-nogui`. Under
OSS, devices appear as `/dev/midiN` where N tracks the ALSA card number, one node per card —
so the Launchpad's three separate ports collapse into one and Programmer Mode may be
unreachable.

ALSA MIDI *does* work on this build (`pd -alsamidi` registers a `Pure Data` client with
in/out ports). The fix is adding `midiapi: 1` to `/root/.pdsettings`. Under ALSA, Pd creates
its own virtual ports and hardware is wired to them with `aconnect` **by name**, which also
solves USB-enumeration-order drift across reboots.

Patch storage falls back from `/usbdrive` to `/sdcard` based on whether `/usbdrive` is
*mounted*, not whether it holds patches. An empty mounted USB drive yields an empty patch
menu; Storage → Eject unmounts it without physical removal.

Deploy with `./deploy.sh`, then press **Storage → Reload** on the device. Because there is no
rsync, locally-deleted files linger remotely — use `./deploy.sh --clean` after renaming or
removing an abstraction, or a stale `.pd` will shadow the new one.


## Architecture decisions already made

Full reasoning in [design-notes.md](design-notes.md). The load-bearing ones:

- **Grain timing must be audio-domain.** Pd's message clock is quantised to a 64-sample
  block (~1.45ms), which is ~20% of a 256th note at 120 BPM. Drive grain clocks from
  `phasor~` and envelopes from `vline~` — never `metro` / `line~` for anything at grain rate.
- **Pd sequences everything.** Timing rides in note events, not MIDI clock. No external
  device runs its own sequencer during a performance.
- **Two independent input channels.** `adc~ 1` = drums, `adc~ 2` = fx, arriving from the
  SP-404's hard-panned L/R via a TRS Y-cable into the Organelle's single stereo input jack.
  Note the README still describes a single serial chain over one input — that predates this
  decision and has not been reconciled.
- **Compose mode and perform mode are separate.** Both the Launchpad and the Organelle's own
  keyboard serve different roles in each, so this shapes the top level of the patch.


## Verified vs assumed

`rig-plan.md` has an *Open questions* section listing what is still untested on hardware, and
`pre-flight-tests.md` is the ordered checklist with results. **Do not treat open items as
settled facts.**

The two tests that could have forced a redesign have both **passed**: Pd can drive the
Launchpad's Programmer Mode over SysEx (LEDs, velocity, polyphonic aftertouch), and Pd's
per-device channel offsets work with multiple controllers at once. What remains is
cable-blocked — the audio topology (Session 3) and full-rig power draw — plus the
[tools/](tools/) patches, which are working references for the techniques involved.


## Working notes

- Before any bulk delete or overwrite on Brendan's data, print the count, a sample, and the
  evidence that the targets are what you claim — then ask. Verifying privately is not enough.
- When a fact matters (a Pd version, a device capability, a file format), check it against the
  device or the source rather than inferring from documentation. Several claims in this
  project's history turned out wrong that way.
