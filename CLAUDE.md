# Cut It

A cut-up / harsh noise instrument patch for the **original Critter & Guitari Organelle**
(a.k.a. Organelle 1 — *not* the M, S, or S2). Pure Data.

✅ **v0.2 — the infrastructure — is complete and verified on hardware.** The instrument passes
audio, knows what every control is doing, and can tell you about it. **[plan-v03.md](plan-v03.md)
is what remains**: v0.3 is **the blank slate** — every device addressable, every control
assignable — not the sound. The four filter stages are v0.4.
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
                       ownership, which is what makes g_grid go quiet. Also the
                       REPLUG WATCHDOG -- a Programmer Mode heartbeat that fixes
                       the Mac without detecting anything, plus a device-inquiry
                       poll and a bounded wire.sh recovery for the Organelle,
                       where a replug destroys the ALSA links outright
  g_grid.pd            the Launchpad's LEDs and their sole owner -- 96 buttons plus the
                       logo, painted across the full 1-108 index span. Same arbiter
                       shape as g_oled -- home < modal < alert -- but home is a
                       COMPOSITE of regions, and it repaints only when dirty
  m_organelle.pd       the Organelle's own panel: aux and knobs 1-4 onto param and disp
  m_volca.pd           the Korg Volca FM -- the FIRST OUTPUT-ONLY m_ layer, because the
                       Volca transmits nothing at all. ONE inlet, selector-prefixed
                       (notes / cc / program), and no outlets. WIRED from u_map rather
                       than fed by a bus: param is device-to-map and disp is display, and
                       neither fits a sounding note. ⚠️ Needs Pajen 1.09 firmware for
                       velocity and program change, both gated behind undocumented global
                       settings -- see ref-midi.md. ⛔ Pd's pgmout is 1-BASED, so it
                       carries a [+ 1] and its inlet means the WIRE number (item 228)
  m_404.pd             the SP-404MKII, and the FIRST BIDIRECTIONAL device layer. 160 pads
                       -- bank sets the CHANNEL (33-42), pad sets the NOTE (36-51) -- with
                       receive and transmit sharing ONE table. ⛔ 47+n is WRONG and was in
                       this repo's docs; it breaks at pad 5. Ships a HARD RATE LIMIT that
                       DROPS rather than queues, and owns the 404's panic across all ten
                       banks. Every event to param, only a press to disp, as ONE stable
                       name (sp-hit) because 160 names would evict the OLED
  u_map.pd             THE MAP — the only file that says what a control MEANS, and since
                       v0.3 it is TABLE-DRIVEN and MODE-DEPENDENT. ⛔ The table never
                       names a send: it names a destination that must exist as a literal
                       argument on a route box, which is the allowlist guard and the whole
                       of what makes a table acceptable. One outlet per output DEVICE
  cut-it-map.txt       the map's rows, one per mapping, FOUR ATOMS ALWAYS:
                       <mode> <control> <dest> <arg>. A plain file so it diffs a row at a
                       time; read relative, which resolves against the patch folder
  u_tempo.pd           the master reference: BPM, the 24 PPQN pulse MIDI clock is cut from,
                       realtime out on two ports, and the transport
  c_clock.pd           ONE clock — its own rate and time signature, aligned to master by a
                       start. Instantiable, because Cut It runs poly-tempo. u_root holds the
                       first instance, c_clock 1 8, which drives the grid's beat row
  g_oled.pd            the display arbiter — home < param < modal < alert, each with a TTL.
                       Sole owner of oscOut and screenLine*
  g_led.pd             the aux button LED and its sole owner. Callers send a state, never
                       a colour — the one display surface that is not a screen
  u_net.pd             the phone — the FOURTH display surface, and the only file that
                       talks to it. Consumes disp like the g_ arbiters but owns no
                       selector on it, so it cost g_oled's route nothing. Coalesces
                       per NAME at 20 Hz with a guaranteed trailing edge, holds the
                       last alert as STATE and repeats it, and rebuilds its own socket
                       — which a phone leaving the network destroys outright
  u_state.pd           THE DATA STORE -- the only file that says WHEN state is
                       written. Owns two u_store instances and the state bus.
                       auto is flushed on a timer, manual only on a commit.
                       A contributor names its own key and its own policy, so
                       an abstraction written later persists itself with NO
                       change here -- which is the whole point of the phase
  u_store.pd           a keyed line store with one file behind it. Give it a
                       list, it REPLACES the line whose first atom matches.
                       Two instances, which is why it is an abstraction
  state-dir.sh         makes the data directory AND touches both files at load.
                       A text write into a missing directory PRINTS, and a read
                       of a missing file prints three lines -- so without this a
                       fresh install would print six errors before doing
                       anything wrong. touch never truncates
  u_mother-stub.pd     impersonates mother.pd off-device AND is the dev panel — the whole
                       front face (screen, knobs, encoder, volume, keys) laid out like the
                       device and rendered inline on main-dev.pd via graph-on-parent.
                       No cords: every control binds by its iemgui send name. Mac only
  phone-ip.sh          how u_net finds the phone WITHOUT being told: on the Organelle's own
                       access point the Organelle is the DHCP server, so it reads the lease
                       it handed out. Falls back to the creation arg on any other network,
                       so one build works everywhere and no conditional lives in the patch
  wire.sh              aconnect calls, run by u_init via [shell]. Also UNDOES
                       mother's own alsaconnect.sh, which wires the lowest-
                       numbered MIDI client to Pd's Midi-In 1 -- the nano, which
                       put it on m_launchpad's channel block on every boot
mac-stubs/           stand-ins for device-only externals, for the local syntax check. NOT deployed
deploy.sh            check → scp → reload → load, in one command (there is no rsync on the device)
tools/fetch-errors.sh  pulls the error log back off the device and summarises it
tools/fetch-state.sh   backs the instrument's SAVED DATA up into device-state/.
                       The other half of the bargain for keeping state outside
                       the patch folder: safe from deploys, and therefore in
                       exactly one place on one SD card
tools/go.sh            the ONLY way to advance a bench on the device -- the encoder
                       does not work there, and netcat does not work on macOS
tools/lp-live.sh       rescues a Launchpad stranded in Programmer Mode, with no Pd
                       and no power cycle. Any exit that is not mother's strands it
tools/dsp.sh           turns the audio engine off on a running patch, which is how
                       item 75's real cause was finally isolated
tools/               diagnostic patches, the per-phase benches, and pd-layout-check.py
  README.md            what each one proves, how to run it, and how to run a bench ON the device
  bench-gen.py         GENERATES all six phaseN-bench.pd from bench_steps.py. The benches
                       are stepped BY HAND -- press GO to run the step just described, press
                       GO again to describe the next. Never edit a bench .pd
  bench-verify.py      proves the step text survived the generator, by re-extracting it
  check-all.sh         EVERY GATE IN ONE COMMAND — layout, both entry points, the bench
                       text, and the phase 6/7/8 gates. ~40 s, Mac only, touches no
                       device. RUN IT BEFORE CALLING ANYTHING DONE. Phase 8 edited
                       u_map, u_init and u_root and came within one step of shipping
                       without re-running the gates of the phases resting on them:
                       a gate you must REMEMBER to run is one that eventually doesn't
  phase6-assert.sh     the headless gate: rewrites [midiout] in a SCRATCH COPY so a run can
                       read back every byte, then asserts on what the grid actually showed
  phase7-assert.sh     the same idea and much cheaper — u_net already emits to a socket,
                       so it binds the port and reads real datagrams. Nothing is rewritten
  phase8-assert.sh     the cheapest of the three — u_state writes a FILE, so it reads what
                       landed on disk. ⚠️ It PASSED THE BROKEN PATCH on its first
                       can-it-fail run, because the driver's timing did not reproduce the
                       real ordering. The 3600 ms in its driver is load-bearing
  stage-patches/       Organelle menu patches: AP Probe records what can only be seen while
                       the access point is up, which is exactly when a Mac joined to it has
                       no internet and nobody can watch. PGM Probe proved pgmout is 1-based,
                       and is the pattern for any Pd-side MIDI probe -- a menu patch needs no
                       killall pd, so it cannot strand the Launchpad. ⚠️ A patch load DROPS
                       Pd's aconnect links, so such a probe must re-wire its own output
  wifi-watch.sh        THE OPEN FAULT. Runs ON the device: polls wlan0, and on a failure
                       runs a LINK PROBE and a DHCP PROBE before a recovery ladder.
                       The link probe has already decided the branch -- the radio is
                       fine and the fault is DHCP-side. wifi-poll.sh watches from the
                       Mac, wifi-report.sh summarises (⚠️ --mark AFTER a finding is
                       written up, never before -- it draws the analysed-to-here
                       line, so running it first erases the event you are reading), and
                       wifi-reassociate.sh is the rung that mirrors the front panel.
                       ⚠️ NEVER pgrep -f wifi-watch: it matches the ssh doing the
                       checking, and a sweep that scans and relaunches in ONE command
                       kills its own session
plan-v03.md          THE ONLY PLAN DOCUMENT. What v0.3 builds, every open question,
                     the wifi decision tree, purchases, and what is deferred and why
plan-tests.md        THE EVIDENCE LEDGER — numbered checks with their measured
                     results, cited bare as "item 133" everywhere. It accumulates
                     findings; it does not plan
ref-build-log.md     Phases 0-8 as built: outcomes, and every correction they produced
ref-conventions.md   how the Pd is written — naming, $0, trigger discipline, dev workflow
ref-hardware.md      the rig and the device — wiring, power, SSH, paths, how Pd launches
ref-software.md      how the instrument works — architecture, timing model, decisions
ref-midi.md          every MIDI message each device accepts and transmits, and how Pd sees it
ref-display.md       visual feedback — the OLED graphics API, the Launchpad's limits, PdParty
device/              backups of config that lives only on hardware
device-state/        backups of the instrument's own saved data, pulled off
                     /sdcard/cut-it-state/ by tools/fetch-state.sh. NOT config
                     and not deployed -- this is what the instrument wrote
! v0.1 plans/        the original v0.1 material, kept for reference
  README.md            musical intent, filter chain, button/knob map
  *.jpg                hand-drawn rig and signal-flow diagrams
  patch/               the v0.1 patch itself — reference for intent, NOT code to lift
```

**`ref-` states what is; `plan-` states what's open. There is exactly ONE plan document.** A `ref-` doc describes the rig, the
device, the message formats and the rules, and marks anything uncertain ⬜ — but it carries no
plans. **Every unresolved question, recommendation and purchase lives in
[plan-v03.md](plan-v03.md).** [plan-tests.md](plan-tests.md) is the *evidence ledger* — numbered
checks with their measured results, cited bare as "item 133" across the project. It accumulates
findings; it does not plan. Keep it
that way when editing: if you find yourself writing "we should…" in a `ref-` doc, it belongs in
a `plan-` doc.

**Finished work moves to [ref-build-log.md](ref-build-log.md)** rather than staying in the plan as
a plan. ✅ All eight v0.2 phases have now done this, and `plan-v02.md` was dissolved when the last
one landed — its architecture diagram went to [ref-software.md](ref-software.md) and its open
questions to `plan-v03.md`. That file is a `ref-` because completed corrections are facts. When a phase lands, its
section leaves `plan-v03.md`; **superseded designs get replaced, not annotated.** Phase 4 changed
its own design twice and recorded both reversals beside the text they overruled, which left the
plan holding the current design and two dead ones at once.

Links to paths containing spaces use the angle-bracket form:
`[README.md](<! v0.1 plans/README.md>)`.

An Organelle patch is a **folder** containing `main.pd` (the entry point) plus its
abstractions, optionally `knobs.txt` and audio assets. ⚠️ **`knobs.txt` is NOT knob labels** — this said so and was
wrong. Two real examples off the device read `0.195503 0.230694 0.134897 0.0136852;` and
`0.521994 1 0.84262 0.723363;`: **four normalised knob positions**, saved state rather than text.

**Cut It ships without one, and `Storage → Save` creates it.** ✅ Measured in Phase 8 (item 139):
`mother.pd` writes `/tmp/state/knobs.txt` on every save, so the file appears the first time you
commit and the patch boots at the saved knob positions from then on — knob 1 being master tempo.
**That is a deliberate decision, not a leak**: a preset that restores the knobs is what a performer
wants. Until the first Save, mother logs `knobs.txt: can't open` at boot; that line is expected and
harmless. An ordinary `./deploy.sh` will not remove the file once it exists — `--clean` will.

✅ **And the saved file BEATS the physical knob — measured, item 200.** Knob 1 turned fully
clockwise, patch reloaded, and it booted at the file's **57 BPM** rather than the knob's 500.
⚠️ **So after any Save every knob is desynced from its value, and the first touch jumps** — up to
the full range. Nothing on the instrument can detect this: mother reports position, not whether the
position still matches the file. **That is the concrete case for parameter pickup** in
[plan-v03.md](plan-v03.md), and it happens on every boot rather than only on a bank switch.

⚠️ **The instrument's own data does NOT live in the patch folder.** `u_state` writes to
`/sdcard/cut-it-state/`, outside it, precisely so that `deploy.sh`, `deploy.sh --clean` and a power
cycle cannot touch it. `tools/fetch-state.sh` copies it back into the repo.

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
about it** — the work to resolve any ⬜ lives in [plan-v03.md](plan-v03.md) under *Open
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
