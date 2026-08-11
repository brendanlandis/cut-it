# Cut It

A cut-up / harsh noise instrument patch for the **original Critter & Guitari Organelle**
(a.k.a. Organelle 1 — *not* the M, S, or S2). Pure Data.

**v0.3 — the blank slate — is complete and verified on hardware.** Every device is addressable and
every control assignable: `u_map` looks a control's meaning up **per mode** from a table, and both
output devices are wired in. The instrument can be told *"in Mode A, moving this fader does X"* in
one row of `Cut It/cut-it-map.txt`.

✅ **The documentation refactor is done** — 10 root files and ~10,300 lines of prose became 2 files
and 21 `ref/` pages, held together by `test/gate/docs-check.py`. **v0.4 is the sound**: four filter
stages, the drum mode, the sampler. v0.1 is superseded and kept only for reference.

**This file is a router.** It says where to look, not what is true.


## Before you write anything

| Doing | Invoke |
|---|---|
| Writing, editing or reviewing any Pd | ⛔ the **`pd`** skill |
| Adding or restructuring any documentation | ⛔ the **`docs`** skill |
| Building or changing a test or a gate | ⛔ the **`gate`** skill |

They load on demand, so they cost nothing in a session that does none of those things.

**The three Pd constraints that are not negotiable**, repeated here because they are expensive to
learn late:

- **Pd vanilla 0.49, permanently.** The Organelle 1 runs OS 4.0 and **that is the end of the line
  for this hardware** — 4.1 was Organelle M only, and 4.2 / 4.4 / OS 5 are M/S/S2. Do not suggest
  any object newer than 0.49.
- **Never save an Organelle-bound patch from plugdata.** It is built on Pd 0.55+ and rewrites `.pd`
  files into a format 0.49 cannot parse. This has already happened once here.
- **Vanilla objects only** — the Organelle ships neither ELSE nor cyclone.

⚠️ **The `critterandguitari/Organelle_OS` GitHub repo targets CM3/CM4 hardware — the Organelle M and
S2, not this device.** Its paths are wrong here (`/home/music`, an `audioinjector-pi-soundcard`).
The mechanisms are the same lineage; verify against the actual device before relying on them.


## Where everything is

**[ref/](ref/README.md) is one page per module**, and the directory is the kind. A page holds
everything about its module: what it is, what was measured, what will bite you, and how Cut It
chooses to use it.

| Looking for | Go to |
|---|---|
| **What is OPEN** — every unresolved question, recommendation and purchase | [plan-v04.md](plan-v04.md) — **the standing plan** |
| **What is being BUILT next** — three scoped plans | [plan-v03.4.0.1.md](plan-v03.4.0.1.md), [plan-v03.4.1.md](plan-v03.4.1.md), [plan-v03.5.md](plan-v03.5.md) — see *How the documentation works* |
| How the Pd is written — rules `C-1`…`C-14`, cited by ID from patch comments | [ref/conventions.md](ref/conventions.md) |
| How the loop is run — deploy, the SSH console, how a phase runs | [ref/workflow.md](ref/workflow.md) |
| How the modules compose — the diagram, the buses, `u_err`, the `m_` boundary | [ref/architecture.md](ref/architecture.md) |
| One physical device | [ref/device/](ref/device/) — `launchpad` `nanokontrol` `organelle` `phone` `sp404` `volca` |
| One instrument concern | [ref/module/](ref/module/) — `audio` `boot` `display` `error` `map` `presence` `state` `tempo` |
| Boxes, cables, jacks, power | [ref/rig.md](ref/rig.md) |
| The Organelle as a **computer** — SSH, paths, how Pd launches, the boot hang | [ref/device-os.md](ref/device-os.md) ✅ verified 2026-08-07 |
| The wifi fault — the roam signature, the watchers, AP mode | [ref/wifi.md](ref/wifi.md) ⚠️ background, not blocking |
| A cited `item NNN` | `grep` it — item numbers are **fact IDs**, not log entries |
| **Every test** — the headless gates, the hands-on benches, the stubs | [test/README.md](test/README.md) |
| What each operational tool and probe does | [tools/README.md](tools/README.md) |

✅ **Both journals are gone.** Phases 0–8 as built and every measurement behind them are in
`git log`; every fact they produced is on a `ref/` page. **`item NNN` still resolves** — grep for it.


## The patch

`Cut It/` is the deployable folder — **its name is what appears in the Organelle menu.** An Organelle
patch is a folder containing `main.pd` plus its abstractions.

| Prefix | Is | Files |
|---|---|---|
| `main` | Entry points. `main.pd` is the device's, `main-dev.pd` the Mac's | `main.pd` `main-dev.pd` `u_root.pd` |
| `m_` | One physical device, publishing named controls | `m_nano` `m_launchpad` `m_organelle` `m_404` `m_volca` |
| `u_` | One instrument-wide utility | `u_init` `u_map` `u_tempo` `u_state` `u_store` `u_err` `u_net` `u_level` `u_present` `u_mother-stub` |
| `g_` | One display surface, and its sole owner | `g_oled` `g_grid` `g_led` |
| `c_` | **Instantiable** — there is more than one | `c_clock` `c_presence` `c_devid` |
| `e_` | An effect stage — **v0.4, none yet** | — |
| `.sh` | Run once at load through `[shell]` | `wire.sh` `state-dir.sh` `logroll.sh` `phone-ip.sh` |
| `.txt` | Read by Pd, so space-separated | `cut-it-map.txt` |

**What each one does is on its module page**, not here. `mac-stubs/` stands in for device-only
externals during the local syntax check and is never deployed.

`device/` backs up config that lives only on hardware; `device-state/` backs up what the *instrument*
wrote. Neither is deployed.


## The tests

**`test/` is every test; `tools/` is everything else.** The directory is the kind, exactly as it is
under `ref/`. Nothing in either is deployed.

| Where | Is | Oracle |
|---|---|---|
| `test/run.sh` | **the entry point** — the gates bare, the benches with `--all` | — |
| `test/runner/` | What `run.sh` is. The gate table, the bench loop, the verdict record | — |
| `test/gate/` | Headless gates. One per module, named for it | a program, unattended |
| `test/bench/` | Hands-on acceptance runs, and the three scripts that **generate** them | a person, with the rig plugged in |
| `test/stubs/` | `t_*` stand-ins a gate swaps in inside a scratch copy | — |
| `tools/` | Operational scripts and one-off probes — `fetch-*.sh`, the wifi tooling | — |

⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and regenerate; never the `.pd`.
⛔ **A gate is not trusted until it has failed** — see the **`gate`** skill.

**Nineteen gates and 461 checks**, and what each one protects is in
[test/README.md](test/README.md). ✅ **No page declares `Gate: none` any more.** ⛔ **One of them reads
a SIGNAL** — `audio-assert.sh` records `u_root`'s output to a soundfile; every other gate in the
project asserts on messages, which is what kept the audio path invisible for so long.


## Working on it

⛔ **This project's git rule OVERRIDES the global one, which says never touch git.** Here you
**commit as you go**, in reviewable batches — a plan's phases are good commit boundaries, and
`git log` is this project's only journal, so work that never lands in it is work whose reasoning is
lost. ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**

**Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
whole instrument is *there* — `u_mother-stub` draws the front panel inline and fakes the knobs, keys,
aux and encoder. **Most work should never need the Organelle powered on.**

```sh
./test/run.sh            # every gate, ~5 min, Mac only. RUN IT BEFORE CALLING ANYTHING DONE
./test/run.sh --all      # and then the benches -- needs the rig, and a person
./tools/deploy.sh              # syntax check -> scp -> reload -> load, in one command
ssh root@organelle.local # password: organelle. Root fs is read-only -- remount-rw.sh first
```

⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** `grep -E 'ALL|FAILED'` also matches
the per-gate `--- FAILED:` lines, and a broken patch has been committed that way.

⛔ **Run bare it is the gate half and nothing else** — Mac-only, touching nothing on the Organelle,
safe with the device off. The benches are behind `--all` / `--bench` on purpose: ⚠️ **a check that
costs twenty minutes stops being run**, which is the failure this command was built to fix.

⛔ **It takes ~5 minutes and only about a minute of that is computation** — measured, 302.7 s real
against 64.5 s user+sys. The rest is Pd instances running **DSP in real time** so a `phasor~` clock and a beat
row can actually tick. **A faster machine will not help.** Three consequences:

- ⛔ **Never start a second run while one is in flight.** They contend for CPU and MIDI, every run in
  the window slows down, and the results stop meaning anything. Six were once stacked here by accident
  and two "failures" were nothing but the cleanup kill.
- **Documentation-only changes do not need it.** `python3 test/gate/docs-check.py` covers those and
  returns in under a second. Save the full suite for when a `.pd` actually changed.
- **Run it once per batch of work, not after every edit.** It is a gate, not a linter.

**Nothing reports itself unless the patch reports it.** Two things make that survivable:

- **The menu-launched patch has no console** — Pd runs `-nogui` and errors go to tty1, which VNC will
  not show. **But you can launch the patch yourself over SSH and get a real console**, including
  `[print]` taps on any bus. It found a silent bug in Phase 1 — see *There IS a console* in
  [ref/workflow.md](ref/workflow.md).
- **Nothing has to be caught live.** The dev panel's `open-screen-log` opens a running history of
  every `disp` message except the level reports, stamped with the frame number — so a boot sequence
  that finishes in four seconds can be read afterwards instead of watched.

⚠️ **The instrument's own data does NOT live in the patch folder.** `u_state` writes to
`/sdcard/cut-it-state/`, outside it, precisely so `tools/deploy.sh`, `tools/deploy.sh --clean` and a power cycle
cannot touch it. `tools/fetch-state.sh` copies it back. See [ref/module/state.md](ref/module/state.md).

⛔ **`knobs.txt` is four saved knob positions, not knob labels**, and **the saved file beats the
physical knob** — so after any Save the first touch of a knob jumps, up to the full range, and knob 1
is master tempo. Nothing on the instrument can detect it. See
[ref/device/organelle.md](ref/device/organelle.md) under *Saving*.


## How the documentation works

**`ref/` states what IS. A `plan-` document states what is OPEN.** If you find yourself writing "we
should…" in a `ref/` page, it belongs in a plan. If you find yourself writing "and it works" in a
plan, that section should have left the file.

⚠️ **A plan is scoped to one piece of work and is DELETED when the work lands** — `plan-v02` and
`plan-v03` both went that way. [plan-v04.md](plan-v04.md) is the exception that persists, because it
is where everything unscoped waits.

**Three scoped plans stand between here and v0.4**, and each one is written to be handed to a fresh
agent cold — it carries its own reading list, saying how much of each file to read and what to skip.
⛔ **Every ⬜ in the repository is closed by one of them, or is one of the nine items that genuinely
need the sound to exist.**

| | Plan | Needs |
|---|---|---|
| 1 | [plan-v03.4.0.1.md](plan-v03.4.0.1.md) — the runnable suite, and the first note path | — |
| 2 | [plan-v03.4.1.md](plan-v03.4.1.md) — panic becomes `recover` | — |
| 3 | [plan-v03.5.md](plan-v03.5.md) — the venue kit | — |

⚠️ **1 is the one to do first, and not because anything depends on it.** `./test/run.sh --all`
cannot pass today for two reasons that have nothing to do with the patch, so until it lands the
bench half of this suite cannot verify anything the other two build.

✅ **Plan 0, the test runner, the v0.3.2 cleanup, v0.3.3 coverage and hot-swap are all gone** — the
measurement session ran on 2026-08-08, `test/run.sh` landed on 2026-08-09, the cleanup and the
coverage pass landed the same day, and hot-swap landed on 2026-08-10. The facts are on `ref/` pages
and the reasoning is in `git log`. **Neither of the two left gates the other**: 1 recovers what
presence structurally cannot, and 2's diagnostic screen reads presence data that now exists — see
[ref/module/presence.md](ref/module/presence.md).

⛔ **`check_closers` in `docs-check.py` is written but gated behind `--strict`**, because most
remaining ⬜ are owned by the three plans above. **plan-v03.5.md's landing checklist removes the
flag** — see it before adding a ⬜ anywhere.

**A fact appears once in full; everywhere else it is a citation.** `test/gate/docs-check.py` enforces
what can be enforced — run it rather than trying to remember it:

```sh
python3 test/gate/docs-check.py -v
```

**Five markers, and no other emoji anywhere in this repo:**

| | |
|---|---|
| ✅ | Verified on this hardware |
| 📄 | Manufacturer documentation |
| ⬜ | Unknown or unverified — **only inside an `Open` section** |
| ⛔ | A trap: ignoring it breaks something **silently** |
| ⚠️ | An operational rule: never do this to the rig or the device |

⛔ **A check mark never means "built."** An evidence marker never rots; a completion marker silently
becomes false — which is how the old conventions doc came to assert `u_map` used no lookup table and
kept saying it until Phase 9 contradicted it. **Do not treat 📄 or ⬜ items as settled facts.**

Links to paths containing spaces use the angle-bracket form:
`[README.md](<! v0.1 plans/README.md>)`.


## Working notes

- **Before any bulk delete or overwrite on Brendan's data, print the count, a sample, and the
  evidence that the targets are what you claim — then ask.** Verifying privately is not enough.
- ⛔ **A section is not what its heading says.** Read what is under it before deleting from one
  heading to the next, and probe distinctive strings afterwards. That has caught a real deletion
  twice in this refactor.
- **When a fact matters — a Pd version, a device capability, a file format — check it against the
  device or the source** rather than inferring from documentation. Several claims in this project's
  history turned out wrong that way, including two corrected in these files.
- **"Needs the rig" and "needs the device powered" are different, and conflating them parks work
  that could have been done today.** Items 173 and 134 sat in a hands-on measurement batch; both
  turned out to be pure `ssh` reads, and both closed with the Organelle simply *up* — a better
  condition than a rig session, because nobody was perturbing it. **Before booking a measurement
  against a session with hands on the hardware, ask what it actually needs**: eyes, fingers, a
  cable, or only a reachable device.
- ⛔ **Before diagnosing a hardware symptom, grep `ref/` for its literal error string.** A Launchpad
  that would not enumerate — `can't set config #1, error -32` — was diagnosed from scratch across
  five physical tests on 2026-08-08, and [ref/rig.md](ref/rig.md) had already written it up **with
  that exact code in the text**. Symptoms are as greppable as `item NNN`, and cost more to re-derive.
- **Configuration that lives only on a device is one accident from being lost.** The nanoKONTROL
  scene and `/root/.pdsettings` are both backed up in [device/](device/), verified current against
  the hardware. `.pdsettings` is load-bearing: `path1: /root/Pd/externals` is what makes `[shell]`,
  `packOSC` and `routeOSC` resolve in the menu-launched patch.
