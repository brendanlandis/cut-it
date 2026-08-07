# Plan — the tool and device cleanup

**This document is written to be handed to an agent cold. Read it first and in full.**

**Two jobs, in this order:** the `tools/` directory, then the Organelle itself. They are in one
document because both are *"decide what survives"* rather than *"build something"*, and both end by
rewriting a document that describes what is left.

⚠️ **Do this AFTER [plan-testing.md](plan-testing.md).** The testing refactor renames roughly 30
files in `tools/`, so a cleanup that runs first is deciding the fate of filenames that are about to
change — and `tools/README.md` describes the gates by their **phase** names, so rewriting it before
the rename means rewriting it twice.

**Then [plan-v04.md](plan-v04.md)**, which is the sound.

---

## Job 1 — the `tools/` cleanup

**89 files. Some are load-bearing, some answered a question in July and have not been opened since.**
Nothing here is deployed to the device except `stage-patches/`.

⛔ **Before deleting anything, print the count, a sample and the evidence that the targets are what
you claim — then ask.** That is a standing rule in [CLAUDE.md](CLAUDE.md) and this job is exactly
what it is for.

### The six categories, and what each is worth

| Category | Files | Disposition |
|---|---|---|
| **Gate machinery** | `check-all.sh` `docs-check.py` `pd-layout-check.py` `*-assert*` `bench-gen.py` `bench-verify.py` `bench-extract.py` `bench_steps.py` `test-stubs/` | ⛔ **Keep all.** These run on every commit |
| **Benches** — generated outputs | `phase*-bench.pd` | ⛔ **Keep, never edit.** Regenerated from `bench_steps.py` |
| **Operational** — used by a person, not a gate | `fetch-errors.sh` `fetch-state.sh` `go.sh` `lp-live.sh` `dsp.sh` `wifi-*.sh` `phase6-cpu.sh` | **Keep.** ⚠️ Being unused by a gate is not evidence against a tool — `go.sh` is the only way to advance a bench on the device, and `lp-live.sh` rescues a stranded Launchpad |
| **Reference patches** — worked examples for a technique | `audio-probe/` `oled-probe/` `osc-bridge/` `status-display/` `pdparty-scene/` | **Keep, probably.** Each is the working proof behind a `ref/` claim |
| **Stage patches** — deployed to the device's menu | `stage-patches/` | **See Job 2** — these live on the device too |
| **One-off probes** — answered, and the answer is now in `ref/` | the rest, below | ⬅ **This is the decision** |

### The probes, with what each answered

**The test is not "is it used" — it is "would you run it again."** A probe whose answer is now a row
on a `ref/` page and whose question cannot recur is finished.

| File | Answered | Still worth keeping? |
|---|---|---|
| `alert-buffer-probe.pd` | The ALERT buffer works and is deliberately unused | ⬜ `tools/README.md` calls it *"the re-check if that ever gets revisited"* |
| `lp-step0.pd` | Phase 6 Step 0 — items 82–87, the whole index map | ⬜ Re-runnable if a Launchpad is ever swapped |
| `lp-cc-probe.pd` `lp-flicker.pd` `lp-modes.pd` `lp-monitor.pd` | The CC map, per-pad RGB, the three animations, pad echo | ⬜ Four patches, overlapping. **Probably one survivor** |
| `404-accel.pd` `404-clock-contention.pd` `404-contend.sh` `404-drive.pd` `404-knob-rate.pd` `404-rate-sweep.pd` `404-rate.sh` | The trigger ceiling (~362/s), that it drops rather than queues, that the clock does not starve it | ⬜ **Seven files for one finding.** The finding is on `ref/device/sp404.md` |
| `midi-monitor.pd` `midi-drive.pd` `midiout-probe.pd` | Channel blocks, `[ctlin]` firing order, `[midiout]`'s port inlet | ⬜ **July. Superseded by `m_` layers that do this for real** |
| `panic-poke.pd` | Panic reaches the devices | ⬜ July |
| `self-wire.pd` + `tools/wire.sh` | That a patch can wire its own ALSA MIDI at load | ⛔ **`tools/wire.sh` is a DELETE** — see below |
| `phase3-diag.pd` | A real console for the display arbiter | **Keep** — the by-hand console pattern |
| `volca-probe.pd` `sp404-notes.pd` | Volca CC reachability; 404 note reference | ⬜ |
| `dsp-toggle.pd` | Paired with `dsp.sh` | **Keep** — how item 75 was isolated |

⛔ **`tools/wire.sh` is not a probe, it is a hazard.** It is a Phase 1 ancestor of `Cut It/wire.sh`,
**59 lines behind**, with no autoconnect undo and no `|| true` on any line. `ref-hardware.md` pointed
at it for months. **It is the only same-basename pair in the repo** — swept every `.sh` / `.py` /
`.pd` / `.txt`, and the nine `main.pd` copies are all legitimate Organelle patch folders.

⚠️ **`self-wire.pd` names it**, so decide them together: either both go, or `self-wire.pd` is
repointed at `Cut It/wire.sh`.

### What is settled and should not be re-litigated

- ✅ **A script mentioned in no document is FINE** (Brendan, 2026-08-06). Five of 42 are:
  `404-contend.sh`, `404-rate.sh`, `state-assert.py`, and both stage-patch shell scripts.
  `docs-check.py` is mention-driven by design and will never look for them. **Do not raise it.**
- ⚠️ **`state-assert.py` is LIVE** — `state-assert.sh` execs it. It is unmentioned, not unused.

### Then, and only then, `tools/README.md`

765 lines describing ~40 files. ⚠️ **Rewrite it last**, after both the testing rename and the
deletions, or it documents things that are about to change name or disappear.

**Done when:** every file in `tools/` is either used by a gate, used by a person, or a reference
patch someone would open again — and `README.md` says which, in one line each.

---

## Job 2 — the Organelle cruft cleanup

⛔ **This one needs the device.** Everything above is Mac-side; this is not.

### What is already known to be on it

**Three system files are modified from factory**, and they are the reason this job carries risk:

| File | State | Backed up |
|---|---|---|
| `/root/.pdsettings` | **Modified** — `midiapi: 1` plus four ALSA in/out devices. **The entire MIDI topology depends on it** | `device/pdsettings` |
| `/root/fw_dir/scripts/mount.sh` | **Modified** — refuses write-protected volumes, which is what stops the Launchpad's onboarding drive hanging the boot | `device/mount.sh`, factory at `device/mount.sh.orig` |
| `/root/Pd/externals` | Holds `[shell]`, `packOSC`, `routeOSC` — `path1` in `.pdsettings` is what makes them resolve in a menu-launched patch | ⬜ **NOT backed up** |

⛔ **A cleanup that reverts any of these breaks the instrument silently.** `mount.sh` reverting means
the device hangs at boot with the Launchpad attached; `.pdsettings` reverting means Pd falls back to
OSS and the Launchpad's three ports collapse into one.

### What to survey

| Where | Looking for |
|---|---|
| `/sdcard/Patches/!/` | Old copies of `Cut It`, and the four **stage patches** — `AP Probe`, `PGM Probe`, `Start AP`, `State Probe`. ⚠️ Two of those have answered their question |
| `/sdcard/cut-it-err.log` and `.cur` | Size. `u_err` rolls one into the other at load and nothing prunes |
| `/sdcard/cut-it-state/` | Two files. ⛔ **This is the instrument's own saved data — back it up with `tools/fetch-state.sh` before touching anything** |
| `/sdcard/PdExtraLibs` | On Pd's search path. What is actually in it? |
| `/root` | Anything dropped there during eight phases of debugging |
| `/sdcard/Patches/` | The factory patch set. **Leave it** unless space is a problem — 3.3 GB free at last check |

⬜ **The survey has not been done.** Nothing here says what is actually cluttered, only where to
look — because that answer needs the device powered on, and this plan was written without it.

### Two things to capture while there

- ⬜ **Back up `/root/Pd/externals`** into `device/`. It is load-bearing and has no copy.
- ⬜ **Record what `/root/fw_dir/version` says**, and compare against `device/OS-VERSION`.

### Then verify `ref/device-os.md`

⛔ **That page is 461 lines and is the only documentation deliberately left stale.** Its paths are
what this job changes. **Verify each against the device, correct what moved, and delete the
verify-after banner at the top** — the banner is what tells a reader the staleness is intentional,
and leaving it after the check would be worse than never having written it.

**Done when:** the banner is gone, every path in the table has been confirmed on the device, and
anything modified from factory that is not yet in `device/` is.

---

## How to know the whole thing worked

```sh
./tools/check-all.sh              # every gate, ~40 s, Mac only. Read RESULT:, do not grep for it
python3 tools/docs-check.py -v    # every path named in documentation resolves
```

- **No gate lost.** `check-all.sh` runs the same number of gates it ran before, and each still fails
  when made to.
- **`tools/README.md` describes only files that exist**, and every file that exists is described or
  deliberately not.
- ⛔ **The instrument still boots with the Launchpad attached**, which is the one-line test that
  `mount.sh` survived.
- **`ref/device-os.md` has no verify-after banner.**

---

## Open

- ⬜ **Whether the four stage patches stay on the device.** `PGM Probe` proved `pgmout` is 1-based
  and `AP Probe` recorded what can only be seen while the access point is up. Both answered. **But a
  menu patch costs nothing but a menu row**, and re-creating one is not free — this is a judgement
  call, not a rule.
- ⬜ **Whether the reference patches under `tools/*/` earn their keep.** Each is the working proof
  behind a `ref/` claim, which argues for keeping them; none has been opened since its phase, which
  argues the claim is now the artefact and the patch is not.
