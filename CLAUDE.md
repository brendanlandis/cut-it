# Cut It

A cut-up / harsh noise instrument patch for the **original Critter & Guitari Organelle**
(a.k.a. Organelle 1 — *not* the M, S, or S2). Pure Data.

Being rewritten from scratch as **v0.2**. The build sequence is [plan-v02.md](plan-v02.md);
v0.1 is superseded and kept only for reference.


## Hard constraints — read before writing any Pd

**Target is Pd vanilla 0.49, permanently.** Verified on the device:
`Pd-0.49.0, compiled Oct 9 2018`. The Organelle 1 runs OS 4.0.

**OS 4.0 is the end of the line for this hardware — there is no upgrade and the Pd target
cannot move.** 4.1 was Organelle M only; 4.2 / 4.4 / OS 5 are M/S/S2. Confirmed three ways: the
official Organelle 1 manual names `OG1-4.0` as the current release, C&G staff state "OS 4.0 is
the highest version currently available for the Organelle 1", and on C&G's own image host only
`OG1-v4.0.img.zip` exists — `OG1-v4.1`, `4.2`, `4.4` and `5.0` all 404. **Do not suggest
objects newer than 0.49.**

**Never save an Organelle-bound patch from plugdata.** plugdata is built on Pd 0.55+ and
rewrites `.pd` files into a newer format — iemgui colours become hex (`#fcfcfc` instead of
`-262144`), floatatoms gain a trailing arg. Pd 0.49 cannot parse that. This has already
happened once in this repo. Edit with **vanilla Pd 0.49** for anything that ships to hardware.

**Vanilla by default.** The Organelle ships neither ELSE nor cyclone. Bundling them is
*possible* — the device is **armv7** and armv7 builds exist — but current ELSE requires Pd
0.56+, so you would need a ~2019-vintage release. Pd 0.49 also expects the `.pd_linux`
extension, not the newer `.l_arm` naming. Pure-Pd abstractions can simply be dropped in the
patch folder with no such concerns. Prefer vanilla unless there is a specific object worth the
dependency.

**The `critterandguitari/Organelle_OS` GitHub repo targets CM3/CM4 hardware — that is the
Organelle M and S2, not this device.** Its paths are wrong here (it uses `/home/music`, an
`audioinjector-pi-soundcard`). The mechanisms are the same lineage, but verify paths against
the actual device before relying on them.

**Read [plan-conventions.md](plan-conventions.md) before writing or reviewing any Pd in this
repo.** It carries the naming scheme, the `$0` rule, the global-send allowlist, `[trigger]`
discipline and the banned-constructs list. Those are project decisions, not suggestions, and
they are not reproducible from reading the existing patch — most of it predates them.


## Layout

```
Cut It/              the deployable patch — folder name is what appears in the Organelle menu
  main.pd              device entry point; mother.pd loads this by name. Instantiates u_root
  main-dev.pd          Mac entry point; adds u_mother-stub. The device never loads it
  u_root.pd            the actual root — the audio chain, and where every phase hangs its work
  u_init.pd            ordered startup: MIDI wiring, Launchpad mode, panic and safe exit
  u_level.pd           signal → a named level on the disp bus
  u_err.pd             the err bus; filters by mode, forwards to disp. Never draws
  g_oled.pd            the display arbiter — home < param < modal < alert, each with a TTL.
                       Sole owner of oscOut and screenLine*
  u_mother-stub.pd     impersonates mother.pd off-device AND is the dev panel — the whole
                       front face (screen, knobs, encoder, volume, keys) laid out like the
                       device and rendered inline on main-dev.pd via graph-on-parent.
                       No cords: every control binds by its iemgui send name. Mac only
  wire.sh              aconnect calls, run by u_init via [shell]
mac-stubs/           stand-ins for device-only externals, for the local syntax check. NOT deployed
deploy.sh            check → scp → reload → load, in one command (there is no rsync on the device)
tools/               diagnostic patches, plus pd-layout-check.py
plan-v02.md          the current build plan — infrastructure phases, in order
plan-conventions.md  how the Pd is written — naming, $0, trigger discipline, dev workflow
plan-hardware.md     the rig, and the device itself — wiring, power, SSH, paths, how Pd launches
plan-software.md     how the instrument works — architecture, timing model, decisions
plan-midi.md         every MIDI message each device accepts and transmits, and how Pd sees it
plan-display.md      visual feedback — the OLED graphics API, the Launchpad's limits, PdParty
plan-tests.md        ordered hardware checks, with results
device/              backups of config that lives only on hardware
! v0.1 plans/        the original v0.1 material, kept for reference
  README.md            musical intent, filter chain, button/knob map
  *.jpg                hand-drawn rig and signal-flow diagrams
  patch/               the v0.1 patch itself — reference for intent, NOT code to lift
```

Planning docs are named `plan-<topic>.md`. Links to paths containing spaces use the
angle-bracket form: `[README.md](<! v0.1 plans/README.md>)`.

An Organelle patch is a **folder** containing `main.pd` (the entry point) plus its
abstractions, optionally `knobs.txt` (OLED knob labels) and audio assets.

**Working on the device:** `ssh root@organelle.local` (password `organelle`). The root
filesystem is read-only — `remount-rw.sh` before writing to `/root`. **`./deploy.sh` does the
whole loop** — syntax check, copy, reload the patch list, load the patch — with no physical
interaction. Full details, paths and the `mother`/Pd launch line are in
[plan-hardware.md](plan-hardware.md) under *The device itself*.

**The menu-launched patch has no console** — Pd runs `-nogui` and errors go to tty1, which VNC
will not show. **But you can launch the patch yourself over SSH and get a real console**,
including `[print]` taps on any bus, by loading `mother.pd` and `main.pd` together with output
redirected to a file. This is the highest-value debugging tool on the project and it found a
silent bug in Phase 1 — see *There IS a console* in [plan-conventions.md](plan-conventions.md).

Still assume nothing reports itself unless the patch reports it. **`deploy.sh` syntax-checks in
local Pd 0.49 and refuses to deploy on any output**, so that rule is automatic rather than
remembered.

**Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and
the whole instrument is *there* — `u_mother-stub` draws the front panel inline, fakes the knobs,
keys, aux and encoder, and previews whatever the patch writes to `oscOut`. Most work should
never need the Organelle powered on.

**Nothing has to be caught live.** The panel's `open-screen-log` button opens a running history
of every `disp` message except the level reports, stamped with the frame number — so a boot
sequence that finishes in four seconds can be read afterwards instead of watched.


## Verified vs assumed

Every plan doc marks claims ✅ verified on this hardware / 📄 manufacturer documentation /
⬜ unknown. **Do not treat 📄 or ⬜ items as settled facts.** [plan-tests.md](plan-tests.md) is
the ordered checklist with results; [plan-hardware.md](plan-hardware.md) and
[plan-midi.md](plan-midi.md) each carry their own open questions.


## Working notes

- Before any bulk delete or overwrite on Brendan's data, print the count, a sample, and the
  evidence that the targets are what you claim — then ask. Verifying privately is not enough.
- When a fact matters (a Pd version, a device capability, a file format), check it against the
  device or the source rather than inferring from documentation. Several claims in this
  project's history turned out wrong that way — including two corrected in these files.
- Configuration that lives only on a device is one accident from being lost. The nanoKONTROL
  scene and `/root/.pdsettings` are both backed up in [device/](device/) — verified current
  against the hardware. `.pdsettings` is load-bearing: `path1: /root/Pd/externals` is what makes
  `[shell]`, `packOSC` and `routeOSC` resolve in the menu-launched patch.
