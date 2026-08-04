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

**Read [ref-conventions.md](ref-conventions.md) before writing or reviewing any Pd in this
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
  u_err.pd             the err bus; filters by mode, forwards to disp. Never draws.
                       Also keeps a persistent log on /sdcard, so an error raised
                       mid-set can be read back the next day
  logroll.sh           rolls the previous session's error log into the durable one at
                       load, stamped with a real wall clock from `date`
  m_nano.pd            the nanoKONTROL: CC -> named controls on param and disp.
                       Takes its Pd channel block as an argument
  m_launchpad.pd       the Launchpad Pro MK3 and the only file that talks to it:
                       Programmer Mode, the safe exit, pads and ring onto param
                       and disp, pressure onto param alone. Publishes surface
                       ownership, which is what makes g_grid go quiet
  g_grid.pd            the Launchpad's 96 LEDs and their sole owner. Same arbiter
                       shape as g_oled -- home < modal < alert -- but home is a
                       COMPOSITE of regions, and it repaints only when dirty
  m_organelle.pd       the Organelle's own panel: aux and knobs 1-4 onto param and disp
  u_map.pd             THE MAP — the only file that says what a control MEANS. Knob 1 is
                       master tempo, aux is the transport. One route box, one branch each
  u_tempo.pd           the master reference: BPM, the 24 PPQN pulse MIDI clock is cut from,
                       realtime out on two ports, and the transport
  c_clock.pd           ONE clock — its own rate and time signature, aligned to master by a
                       start. Instantiable, because Cut It runs poly-tempo. u_root holds the
                       first instance, c_clock 1 8, which drives the grid's beat row
  g_oled.pd            the display arbiter — home < param < modal < alert, each with a TTL.
                       Sole owner of oscOut and screenLine*
  g_led.pd             the aux button LED and its sole owner. Callers send a state, never
                       a colour — the one display surface that is not a screen
  u_mother-stub.pd     impersonates mother.pd off-device AND is the dev panel — the whole
                       front face (screen, knobs, encoder, volume, keys) laid out like the
                       device and rendered inline on main-dev.pd via graph-on-parent.
                       No cords: every control binds by its iemgui send name. Mac only
  wire.sh              aconnect calls, run by u_init via [shell]
mac-stubs/           stand-ins for device-only externals, for the local syntax check. NOT deployed
deploy.sh            check → scp → reload → load, in one command (there is no rsync on the device)
tools/fetch-errors.sh  pulls the error log back off the device and summarises it
tools/               diagnostic patches, the per-phase benches, and pd-layout-check.py
  README.md            what each one proves, how to run it, and how to run a bench ON the device
  bench-gen.py         GENERATES all four phaseN-bench.pd from bench_steps.py. The benches
                       are stepped BY HAND -- press GO to run the step just described, press
                       GO again to describe the next. Never edit a bench .pd
  bench-verify.py      proves the step text survived the generator, by re-extracting it
  phase6-assert.sh     the headless gate: rewrites [midiout] in a SCRATCH COPY so a run can
                       read back every byte, then asserts on what the grid actually showed
plan-v02.md          the build plan — the phases still to come, and EVERY open question
plan-tests.md        the ordered hardware checks, with every measured number
ref-build-log.md     Phases 0-6 as built: outcomes, and every correction they produced
ref-conventions.md   how the Pd is written — naming, $0, trigger discipline, dev workflow
ref-hardware.md      the rig and the device — wiring, power, SSH, paths, how Pd launches
ref-software.md      how the instrument works — architecture, timing model, decisions
ref-midi.md          every MIDI message each device accepts and transmits, and how Pd sees it
ref-display.md       visual feedback — the OLED graphics API, the Launchpad's limits, PdParty
device/              backups of config that lives only on hardware
! v0.1 plans/        the original v0.1 material, kept for reference
  README.md            musical intent, filter chain, button/knob map
  *.jpg                hand-drawn rig and signal-flow diagrams
  patch/               the v0.1 patch itself — reference for intent, NOT code to lift
```

**`ref-` states what is; `plan-` states what's open.** A `ref-` doc describes the rig, the
device, the message formats and the rules, and marks anything uncertain ⬜ — but it carries no
plans. **Every unresolved question, recommendation and purchase lives in
[plan-v02.md](plan-v02.md)** (or [plan-tests.md](plan-tests.md), for hardware checks). Keep it
that way when editing: if you find yourself writing "we should…" in a `ref-` doc, it belongs in
a `plan-` doc.

**Finished work moves to [ref-build-log.md](ref-build-log.md)** rather than staying in the plan as
a plan. That file is a `ref-` because completed corrections are facts. When a phase lands, its
section leaves `plan-v02.md`; **superseded designs get replaced, not annotated.** Phase 4 changed
its own design twice and recorded both reversals beside the text they overruled, which left the
plan holding the current design and two dead ones at once.

Links to paths containing spaces use the angle-bracket form:
`[README.md](<! v0.1 plans/README.md>)`.

An Organelle patch is a **folder** containing `main.pd` (the entry point) plus its
abstractions, optionally `knobs.txt` and audio assets. ⚠️ **`knobs.txt` is NOT knob labels** — this said so and was
wrong. Two real examples off the device read `0.195503 0.230694 0.134897 0.0136852;` and
`0.521994 1 0.84262 0.723363;`: **four normalised knob positions**, saved state rather than text.
**Cut It deliberately ships without one**, so the physical knob position always wins — knob 1 is
master tempo, and a `knobs.txt` would decide what BPM the patch boots at. The cost is that mother
logs `knobs.txt: can't open` at every boot; that line is expected and harmless.

**Working on the device:** `ssh root@organelle.local` (password `organelle`). The root
filesystem is read-only — `remount-rw.sh` before writing to `/root`. **`./deploy.sh` does the
whole loop** — syntax check, copy, reload the patch list, load the patch — with no physical
interaction. Full details, paths and the `mother`/Pd launch line are in
[ref-hardware.md](ref-hardware.md) under *The device itself*.

**The menu-launched patch has no console** — Pd runs `-nogui` and errors go to tty1, which VNC
will not show. **But you can launch the patch yourself over SSH and get a real console**,
including `[print]` taps on any bus, by loading `mother.pd` and `main.pd` together with output
redirected to a file. This is the highest-value debugging tool on the project and it found a
silent bug in Phase 1 — see *There IS a console* in [ref-conventions.md](ref-conventions.md).

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

Every doc marks claims ✅ verified on this hardware / 📄 manufacturer documentation /
⬜ unknown. **Do not treat 📄 or ⬜ items as settled facts.** [plan-tests.md](plan-tests.md) is
the ordered checklist with results. **The `ref-` docs mark uncertainty ⬜ but never say what to do
about it** — the work to resolve any ⬜ lives in [plan-v02.md](plan-v02.md) under *Open
questions*, which is the single place to look for what is unresolved.


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
