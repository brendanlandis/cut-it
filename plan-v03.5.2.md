# Plan v0.3.5.2 — the standalone debug patch

**Every diagnostic tool this project has is driven from the Mac over SSH** — `test/run.sh`,
`fetch-errors.sh`, `display-cpu.sh` — **and SSH needs a network, which is the exact thing that is
missing when it matters.** At a venue, three questions currently require a laptop: what MIDI is
arriving from each device and on what channel, whether each device answers when you fire something at
it, and what the error log says.

This plan builds the patch that answers them **from the front panel**.

⛔ **It is a separate patch, and that is the whole reason it can work.** mother forwards `encbut`
only after a patch sends `/enableEncoder`, and Cut It never does because **C-5 gives `g_oled` sole
ownership of `oscOut`**. A standalone patch is not bound by that — so it gets the encoder **plus**
four knobs, the aux button and 25 keys, where the instrument has everything but the encoder.
**That is the difference between a menu of one screen and a menu you can navigate.**

✅ **The sibling plan has landed** — the phone became interactive on 2026-08-12, and its plan file is
gone. This one **stales no bench**, because it touches nothing under `Cut It/`.

⛔ **This one carries the batch's closing chore** — see *Done means* #5.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** ⛔ **Never open or save an Organelle-bound patch in plugdata.**
  **Vanilla objects only** — the Organelle ships neither ELSE nor cyclone.
- ⛔ **Invoke the `pd` skill before touching a `.pd`, the `docs` skill for the new `ref/` page, and
  the `gate` skill before touching anything under `test/`.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and regenerate.
- ⛔ **A gate is not trusted until it has FAILED.**
- ⚠️ **The `critterandguitari/Organelle_OS` repo targets the M and S2, not this device.** Its paths
  are wrong here (`/home/music`, an `audioinjector-pi-soundcard`). Verify against the hardware.
- **Commit as you go.** ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent
  byline.**

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** / **`docs`** / **`gate`** skills | ⛔ **Invoked, not read** | A new patch, a new page, a new bench |
| [ref/device/organelle.md](ref/device/organelle.md) | **The OLED graphics API and the encoder facts** | ⛔ A standalone menu patch may use the encoder; Cut It may not. The `gPrintln` typetag rules are here |
| [ref/device-os.md](ref/device-os.md) | The Pd launch, the paths, the read-only rootfs | Where the patch goes and how it is started |
| [ref/module/boot.md](ref/module/boot.md) | How `wire.sh` is run and what it does | ⛔ The patch has to do this itself |
| `Cut It/wire.sh` | **All 67 lines** | The `aconnect` calls this patch must make. It is idempotent |
| `tools/stage-patches/AP Probe/main.pd` and `ap-probe.sh` | **Both** | The pattern that **works**: a menu patch that logs to `/sdcard/` and instructs on the OLED |
| `tools/oled-probe/main.pd`, `tools/osc-bridge/main.pd` | **Skim as working references** | ⛔ They were kept in the v0.3.2 cleanup **precisely for this plan** — see [plan-v04.md](plan-v04.md) §5 |
| `test/runner/targets.py` | Its two docstrings | ⛔ Why this patch's bench must be paper |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** [ref/wifi.md](ref/wifi.md), [ref/module/map.md](ref/module/map.md),
[ref/module/state.md](ref/module/state.md) or [ref/module/tempo.md](ref/module/tempo.md).

---

## What is already true

### The device as a computer

- ⛔ **A menu-launched patch has no console.** Pd runs `-nogui` and stdout goes to tty1, which VNC
  will not show. **Every stage patch therefore logs to `/sdcard/` and instructs on the OLED.**
- **Selecting a patch is itself a test**, more often than you would expect — loading one restarts Pd,
  which is what `AP Probe` was built to exploit: the reload *is* the experiment.
- ⛔ **A standalone menu patch may use the encoder and Cut It may not.** See the opening above.
- ⛔ **Loading any patch drops Pd's ALSA connections.** `wire.sh` is what puts them back, and it is
  idempotent — 9 connections, twice in a row, no change (item 292). It costs **~247 ms**, measured
  three times; ⚠️ **not the 133 ms three places in this repo once claimed.**
- ⛔ **`/root/Pd/externals` is what makes `[shell]` resolve** in a menu-launched patch, through
  `path1` in `/root/.pdsettings`. Backed up in [device/](device/).
- ⛔ **Pd 0.49 cannot read `/proc`** — measured, not assumed. procfs reports size 0, Pd `lseek`s, and
  the read fails outright. **Anything wanting kernel state needs a `[shell]` fork.**

### The menu

⛔ **It goes in `/sdcard/Patches/! debug/`, not in `!`.** As of 2026-08-07 the `!` menu holds
**`Cut It` and nothing else** — the four probes that had accumulated there were removed once each was
confirmed byte-identical to its copy in the repo. **At a venue you should scroll past nothing to
reach the instrument**, and a second menu directory is where anything you might reach for *instead
of* playing belongs.

---

## Phase 1 — the patch

**Repo location: a `debug/` folder at the repo root, alongside `Cut It/`.** It is a second
deployable, not a probe — `tools/stage-patches/` is for one-shot probes and this is not one.
⚠️ **The folder name is what appears in the Organelle menu**, so pick it deliberately.

### What it shows, at minimum

| Screen | Answers |
|---|---|
| **MIDI monitor** | What is arriving from each device, and on what channel |
| **Test output** | Fire a message at each device and hear or see it answer |
| **The error log** | The tail of `cut-it-err.log` |
| **Network** | Whether the AP is up, and what address the phone has |
| **Re-wire** | Run `wire.sh` by hand |

**Navigation is the encoder** — `enc` sends `1`/`0`, not `±1`, and `encbut` arrives only after
`/enableEncoder`. Four knobs, the aux button and 25 keys are all available too.

### ⛔ It must make its own `aconnect` call

**Loading this patch drops Pd's ALSA connections**, so a debug patch that does not wire itself
**measures silence and reports it as "no MIDI arriving"** — which is the worst possible lie for this
particular tool. Run `wire.sh`, or the same calls, at load.

⚠️ **Do not assume the device numbering.** ALSA renumbers clients across a replug and `wire.sh`
connects **by name** for exactly that reason — item 287, where the SP-404 and the Volca's interface
swapped client numbers and everything still landed correctly.

### ⚠️ What it costs to load

**Selecting it restarts Pd**, which means it is for *"the instrument is broken and I am not playing
right now."* ⚠️ **Say so on its page.** It also means:

- ⛔ **The Launchpad is left in Programmer Mode** if the instrument was killed rather than exited
  cleanly, and its own Settings menu is locked out in that state. `./tools/lp-live.sh` restores it
  and needs no Pd.
- **Whatever `u_state` wrote is safe** — it lives in `/sdcard/cut-it-state/`, outside the patch
  folder, precisely so a reload cannot touch it.

---

## Phase 2 — the page and the bench

### The `ref/` page

A new page under `ref/module/`, `module` schema, **added to [ref/README.md](ref/README.md)'s
index** — ⛔ **the gate asserts the index lists exactly what exists**, and it could not see top-level
pages for its whole life until two were added and it still said "matches".

⛔ **It must name a `Gate` and a `Bench`, or `none` honestly**, and every path on that line must
exist. ⚠️ **`Design` holds what is DECIDED, not what is planned.**

### ⛔ The bench is a PAPER bench, and the precedent is `recover`

**A driven bench runs as a THIRD PATCH inside the instrument's own Pd** — `test/runner/targets.py`
launches `mother.pd`, `main.pd` and the bench together over one `ssh`. ⛔ **Anything that reloads or
kills Pd takes the bench with it**, and *loading this patch is a Pd restart*. That is exactly why
`test/bench/recover` is a paper bench, and the same reasoning applies here.

**Paper mode needs no Pd, no ssh and no `killall pd`**, so it also strands no Launchpad. Steps are
judged by a person with the device in front of them and recorded through the runner.

⚠️ **A `file` predicate still works in paper mode** — the evidence is on disk — so anything this
patch writes to `/sdcard/` can be machine-checked even with no console.

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v
```

Then, on the device: **the debug patch loads from the `! debug` menu, wires itself, and shows MIDI
arriving.**

⚠️ **Prove the probe before believing the silence.** If the MIDI monitor shows nothing, establish
that the monitor works — with a device you know is transmitting — before concluding the device is
dead. ⛔ **This is the one tool where that mistake is most likely and most expensive**, because
reporting silence is its whole job.

⛔ **Before calling a hardware symptom an instrument fault, check the patch comments, the `ref/` page
and the gates first**, and `grep ref/` for the literal error string — a Launchpad that would not
enumerate was diagnosed from scratch across five physical tests when
[ref/rig.md](ref/rig.md) had already written it up **with that exact error code in the text**.

---

## Done means

1. The patch exists in `/sdcard/Patches/! debug/`, **wires itself**, and answers the three laptop
   questions from the front panel.
2. It has a `ref/` page, listed in [ref/README.md](ref/README.md)'s index, naming a gate and a bench.
3. Its bench exists as a **paper** bench, generated from `test/bench/bench_steps.py`.
4. [plan-v04.md](plan-v04.md) §3's *Debugging the rig with no laptop* is **deleted outright**, and
   [tools/README.md](tools/README.md)'s ⬜ about where the debug system lives is struck.
5. ⛔ **`check_closers` in `test/gate/docs-check.py` loses its `--strict` flag and becomes
   unconditional.** It is written and tested already, and gated off only because this batch had not
   landed. **This is the last plan of the batch to land, so the condition goes with it.** Run
   `python3 test/gate/docs-check.py --strict` to see what is left. ⚠️ **It is not only a flag
   deletion** — measured 2026-08-11, it reports 20 problems in four distinct kinds:

   | Where | What they are |
   |---|---|
   | `plan-v04.md` | v0.4 items **inside the v0.4 plan**. `CLOSER` wants a literal `v0.4` in the window, so satisfying it there is tautological. ⛔ **Better: treat a ⬜ inside a `plan-` file as owned by that file** |
   | `CLAUDE.md` | Prose *about* the ⬜ marker, not open items — `_is_marker_gloss` misses them |
   | `tools/README.md` | A real open item that genuinely needs a closer |
   | *the plan names* | ⛔ **`CLOSER` is `plan-v0[34](?:\.\d)?\.md` — one decimal group, so it matches neither `plan-v03.5.1.md` nor `plan-v03.5.2.md`.** Widen it |

   ⛔ **And `DOCNAME` cannot see these filenames at all.** Its name class is `[a-zA-Z0-9_-]+` — no
   dot — and its lookbehind rejects the one inside `v03.5`, so a bare `plan-v03.5.N.md` in a `.pd`,
   `.sh` or `.py` is invisible to `check_dangling_docs` while a bare `plan-v04.md` is caught.
   **Worth fixing while you are in there; it is why this batch's Pd-comment references had to be
   found by grep.**

   ⛔ **Prove every changed check fails before trusting it.**
6. **This file is deleted.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
