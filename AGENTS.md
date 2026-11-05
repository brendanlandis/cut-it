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

- **Pd vanilla 0.57, on the device and on the Mac** (from 2026-11-03). The Organelle 1's factory Pd
  is 0.49 and its OS 4.0 is the end of the line for that hardware, so 0.57 is our own build, in
  `/sdcard/pd-0.57-0`: `/usr/bin/pd`, which `mother` launches, is a script that runs it. There is
  no fallback (Brendan, 2026-11-03): if those files go missing, no patch starts until they are
  copied back ([device/README.md](device/README.md), with the rollback). Do not suggest any object
  newer than 0.57.
- **Never save an Organelle-bound patch from plugdata.** It rewrites `.pd` files into its newer
  format. Vanilla 0.57's own version of that format is native, but whether plugdata adds anything
  0.57 cannot read is untested (`~/Sites/!reference/pure-data.md`). It broke a patch here once,
  under 0.49.
- **Vanilla objects, plus `[shell]` and two libraries we build: pdlua and ELSE** (from 2026-11-03).
  The Organelle ships only a dozen factory externals, of which Cut It uses `[shell]` (Reference,
  Organelle page, *Externals*). pdlua 0.12.24 (Lua 5.4.7) runs the sequencer's rules, the map's
  lookup, the synth choice, tap tempo and the decoding in two device layers (the nano, the Organelle's keys), and
  ELSE 1.0-0 rc14 may replace hand-built parts; both are built for 0.57 and live in
  `/sdcard/PdExtraLibs` on the device and `~/Library/Pd` on the Mac
  ([device/README.md](device/README.md), *Lua and ELSE*). The **`pd`** skill has how to use them.

⚠️ **The public `Organelle_OS` repo documents the M and S2, not this device** — verify paths against
the actual device (Reference, Organelle page).


## Where everything is

**[ref/](ref/README.md) is one page per module**, and the directory is the kind. A page holds how Cut It
uses its module and what Cut It chose. ⛔ **What is true of an outside device or program — what it is,
what was measured, what will bite you — lives in Reference** (`~/Sites/!reference/`, one page per thing,
shown on Back Office's /reference page); a `ref/device/` page links to it and keeps only Cut It's side.
**One fact, one place:** a new device fact goes on its Reference page, not here.

| Looking for | Go to |
|---|---|
| **What is OPEN** — every unresolved question, recommendation and purchase | [plan-v04.md](plan-v04.md) — **the standing plan** |
| How the Pd is written — rules `C-1`…`C-14`, cited by ID from patch comments | [ref/conventions.md](ref/conventions.md) |
| How the loop is run — deploy, the SSH console, how a phase runs | [ref/workflow.md](ref/workflow.md) |
| How the modules compose — the diagram, the buses, `u_err`, the `m_` boundary | [ref/architecture.md](ref/architecture.md) |
| What a device **is** — its MIDI, specs, behavior, measured quirks | **Reference**, not this repo: `~/Sites/!reference/` — `novation-launchpad-pro-mk3` `korg-nanokontrol-mk1` `korg-nanokey` `critter-guitari-organelle-1` `korg-volca-fm` `waldorf-streichfett` `pure-data` `touchosc` (and `meeblip-cubit` `arturia-beatstep` `roland-sp-404mkii` `behringer-xenyx-q802usb`). Find a repo's with `grep -l "used_by:.*cut-it" ~/Sites/!reference/*.md` |
| How Cut It **uses** one physical device | [ref/device/](ref/device/) — `launchpad` `nanokey` `nanokontrol` `organelle` `phone` `streichfett` `volca` |
| One instrument concern | [ref/module/](ref/module/) — `audio` `boot` `debug` `display` `error` `map` `presence` `sequencer` `state` `synths` `tempo` |
| Boxes, cables, jacks, power | [ref/rig.md](ref/rig.md) |
| How Cut It lives on the Organelle as a **computer** — its data, measuring, deploying (the Organelle itself: Reference) | [ref/device-os.md](ref/device-os.md) ✅ verified 2026-08-07 |
| The wifi fault — Cut It's watchers and the stage procedure (the fault itself: Reference) | [ref/wifi.md](ref/wifi.md) ⚠️ background, not blocking |
| A cited `item NNN` | `grep` it here **and in `~/Sites/!reference/`** — item numbers are **fact IDs**, not log entries; the device facts moved there |
| **Every test** — the headless gates, the hands-on checklists, the stubs | [test/README.md](test/README.md) |
| What each operational tool and probe does | [tools/README.md](tools/README.md) |

✅ **Both journals are gone.** Phases 0–8 as built and every measurement behind them are in
`git log`; every fact they produced is on a `ref/` page or in Reference. **`item NNN` still resolves** — grep for it, in both.


## The patch

**There are TWO deployable folders**, and a folder's name is what appears in the Organelle menu. An
Organelle patch is a folder containing `main.pd` plus its abstractions.

`Cut It/` is the instrument. ⛔ **`Cut It Debug/` is the second one** — six screens steered from the
keyboard that answer, from the front panel, the questions that otherwise need a laptop and a network.
It deploys to `/sdcard/Patches/! debug/` with `./tools/deploy.sh --debug`, and ⚠️ **selecting it
stops the instrument**, because loading any patch restarts Pd. See
[ref/module/debug.md](ref/module/debug.md).

| Prefix | Is | Files |
|---|---|---|
| `main` | Entry points. `main.pd` is the device's, `main-dev.pd` the Mac's | `main.pd` `main-dev.pd` `u_root.pd` |
| `m_` | One physical device, publishing named controls, or told what to play | `m_nano` `m_launchpad` `m_organelle` `m_volca` `m_streich` `m_nanokey` |
| `u_` | One instrument-wide utility | `u_init` `u_map` `u_tempo` `u_state` `u_store` `u_err` `u_net` `u_level` `u_present` `u_mother-stub` |
| `g_` | One display surface, and its sole owner | `g_oled` `g_grid` `g_led` |
| `c_` | **Instantiable** — there is more than one | `c_clock` `c_presence` `c_devid` `c_mapped` `c_steps` `c_kit` `c_voice` `c_synth` |
| `e_` | An effect stage — **v0.4, none yet** | — |
| `.sh` | Run through `[shell]` — the first five once at load, `recover.sh` only when panic's second tier fires | `wire.sh` `state-dir.sh` `logroll.sh` `phone-ip.sh` `codec-gain.sh` `recover.sh` |
| `.txt` | Read by Pd, so space-separated | `cut-it-map.txt` `cut-it-drum-page.txt` `cut-it-synth-page.txt` `cut-it-arrangement-page.txt` |
| `.lua` `.pd_lua` | An abstraction's rules in plain Lua, and the pdlua class that carries them into Pd, under its name ([ref/conventions.md](ref/conventions.md), *File naming*) | `c_steps.lua` `c_steps-lua.pd_lua` `c_synth.lua` `c_synth-lua.pd_lua` `u_map.lua` `u_map-lua.pd_lua` `u_tempo.lua` `u_tempo-lua.pd_lua` `m_nano.lua` `m_nano-lua.pd_lua` `m_organelle.lua` `m_organelle-lua.pd_lua`, and `lua-face.lua`, what every one of those classes shares |

**The prefix table above is `Cut It/`'s.** `Cut It Debug/` is flat and has no prefixes — one
`main.pd` and three scripts — because it is one screen deep and nothing in it is reused.
⛔ **Its `wire.sh` is a byte-identical COPY of the instrument's** so it does not depend on the other
folder still existing at a venue, and `test/gate/debug-assert.sh` runs `cmp` on the two.

**What each one does is on its module page**, not here. `mac-stubs/` stands in for device-only
externals during the local syntax check and is never deployed.

**The drum samples are not in git**, since this repo is public: `samples/drums/` holds Brendan's, one a
pad, and `tools/samples.sh` converts them into `Cut It/samples/drums/`, which `tools/deploy.sh` runs and
copies with the patch ([ref/module/sequencer.md](ref/module/sequencer.md), *The kit*).

`device/` backs up config that lives only on hardware; `device-state/` backs up what the *instrument*
wrote. Neither is deployed.


## The tests

**`test/` is every test; `tools/` is everything else.** The directory is the kind, exactly as it is
under `ref/`. Nothing in either is deployed.

| Where | Is | Oracle |
|---|---|---|
| `test/run.sh` | **the entry point** — every gate | — |
| `test/runner/` | What `run.sh` is. The gate table | — |
| `test/gate/` | Headless gates. One per module, named for it | a program, unattended |
| `test/gate/lua/` | The Lua halves of gates: rules tested with lua.org's Lua 5.4, no Pd | a program, unattended |
| `test/checklists/` | Hands-on acceptance runs, one Markdown checklist per area | a person, with the rig plugged in |
| `test/stubs/` | `t_*` stand-ins a gate swaps in inside a scratch copy | — |
| `tools/` | Operational scripts and one-off probes — `fetch-*.sh`, the wifi tooling | — |

⛔ **A gate is not trusted until it has failed** — see the **`gate`** skill.

**Twenty-four gates and 1231 checks**, and what each one protects is in
[test/README.md](test/README.md). ✅ **No page declares `Gate: none` any more.** ⛔ **Two of them read
a SIGNAL** — `audio-assert.sh` records `u_root`'s output to a soundfile and `kit-assert.sh` the drums; every other gate in the
project asserts on messages, which is what kept the audio path invisible for so long.


## Working on it

**Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.57 on the Mac and the
whole instrument is *there* — `u_mother-stub` draws the front panel inline and fakes the knobs, keys,
aux and encoder. **Most work should never need the Organelle powered on.**

```sh
./test/run.sh            # every gate, ~1 min, Mac only. RUN IT BEFORE CALLING ANYTHING DONE
lua test/gate/lua/c_steps_test.lua   # the sequencer's rules alone: a second, no Pd
lua test/gate/lua/u_map_test.lua     # the map's, the same way
lua test/gate/lua/m_nano_test.lua    # the nano's decode, the same way
lua test/gate/lua/m_organelle_test.lua   # and the Organelle keyboard's
lua test/gate/lua/c_synth_test.lua       # and the synth choice's
lua test/gate/lua/u_tempo_test.lua       # and tap tempo's
./tools/deploy.sh              # syntax check -> scp BOTH patches -> reload -> load Cut It
./tools/deploy.sh --debug      # the same push, but loads Cut It Debug instead
./tools/tidy.sh                # what has accumulated on the device. --delete to remove it
ssh root@organelle.local # password: organelle. Root fs is read-only -- remount-rw.sh first
```

⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** `grep -E 'ALL|FAILED'` also matches
the per-gate `--- FAILED:` lines, and a broken patch has been committed that way.

⛔ **It is the gates and nothing else** — Mac-only, touching nothing on the Organelle, safe with the
device off. The hands-on checks are [test/checklists/](test/checklists/README.md), read by a person
at the rig and kept out of it on purpose: ⚠️ **a check that costs twenty minutes stops being run**,
which is the failure this command was built to fix.

⛔ **It takes about a minute because the gates run side by side** — measured 2026-11-02, 53 s
against 461 s one after another. Each one is a Pd instance running **DSP in real time** so a `phasor~` clock and a beat
row can actually tick, so the longest gate sets the floor. **A faster machine will not help.** Three consequences:

- ⛔ **Never start a second run while one is in flight.** They contend for CPU and MIDI, every run in
  the window slows down, and the results stop meaning anything. Six were once stacked here by accident
  and two "failures" were nothing but the cleanup kill.
- **Documentation-only changes do not need it.** `python3 test/gate/docs-check.py` covers those and
  returns in under a second. Save the full suite for when a `.pd` actually changed.
- **It is cheap enough to run after each `.pd` change**, but it is still a gate, not a linter.

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
`~/Sites/!reference/critter-guitari-organelle-1.md` under *Saving*.


## How the documentation works

**`ref/` states what IS. What is OPEN lives in `!projects/cut-it`, the repo beside this one, and
in [plan-v04.md](plan-v04.md) until it is moved there.** If you find yourself writing "we should…"
in a `ref/` page, it belongs in a project file or a loosie. If you find yourself writing "and it
works" there, that step should have been ticked.

**A page cites its owner by the form the `!projects` board produces**: `cut-it/<slug>` for a file
under `active/` or `done/`, `cut-it/<slug>#<step>` for one step of it, `cut-it/inbox` for a
loosie. ⚠️ **It works in a `.pd` comment too**, since it needs no link syntax, and
`test/gate/docs-check.py` resolves every one against the filesystem — and fails if `!projects` is
not beside this repo.

⚠️ **A plan is scoped to one piece of work and is DELETED when the work lands** — `plan-v02` and
`plan-v03` both went that way. [plan-v04.md](plan-v04.md) is the exception that persists, because it
is where everything unscoped waits.

✅ **[plan-v04.md](plan-v04.md) is the only plan again**, which is what a scoped plan being deleted
looks like. ⛔ **Every remaining ⬜ either sits inside a `plan-` file, which owns it, names a `cut-it/<slug>`,
says `NO PLAN OWNS THIS` on purpose, or names the version that closes it** — and
`test/gate/docs-check.py` enforces that on every run rather than leaving it to be remembered.

✅ **Plan 0, the test runner, the v0.3.2 cleanup, v0.3.3 coverage, hot-swap, the bench session and
plan-v0.3.4.1 are all gone** — the measurement session ran on 2026-08-08, `test/run.sh` landed on
2026-08-09, the cleanup and the coverage pass landed the same day, hot-swap landed on 2026-08-10,
**all seven benches were run and judged on 2026-08-11**, and panic became `recover` the same day.
The facts are on `ref/` pages and the reasoning is in `git log`.

⛔ **Every ⬜ must name the plan, the `!projects` ref or the version that closes it**, and `check_closers`
enforces it unconditionally — it ran behind `--strict` only while the v0.3.5 batch was in flight.
⚠️ **An open item LEADS with the glyph**; a sentence that merely mentions ⬜ mid-line is read as prose
about the marker, except inside an `## Open` section where the lead test is dropped. `NO PLAN OWNS
THIS` is a legitimate answer and is greppable on purpose.

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
- ⛔ **Before diagnosing a hardware symptom, grep `ref/` and `~/Sites/!reference/` for its literal error string.** A Launchpad
  that would not enumerate — `can't set config #1, error -32` — was diagnosed from scratch across
  five physical tests on 2026-08-08, and [ref/rig.md](ref/rig.md) had already written it up **with
  that exact code in the text**. Symptoms are as greppable as `item NNN`, and cost more to re-derive.
- **Configuration that lives only on a device is one accident from being lost.** The nanoKONTROL
  scene, `/root/.pdsettings` and the `/usr/bin/pd` launcher are backed up in [device/](device/),
  verified current against the hardware, and so is the recipe that builds pdlua and ELSE into
  `/sdcard/PdExtraLibs`. `.pdsettings` is load-bearing: `path1: /root/Pd/externals` is what makes `[shell]`,
  `packOSC` and `routeOSC` resolve in the menu-launched patch.
