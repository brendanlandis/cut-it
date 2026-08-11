# plan-v03.4.0.1.1 — finish the bench session

**Successor to `plan-v03.4.0.1.md`, which is deleted.** Its Parts 1, 3 and 4 all landed; Part 2 — a
person running all seven benches on the rig — is what is left. **Four benches have now been run, two
are complete, and the one open bug is closed.** What remains is 11 steps to re-run and three benches
that have never run at all.

⚠️ **This plan is written to be handed to a fresh agent cold.** The reading list at the bottom says
what to open and what to skip.


## Where the session got to

`./test/run.sh` is green — **19 gates, 518 checks.** The patch is deployed and the instrument is up.

```sh
python3 test/runner/run.py --list      # what would run, and how fresh each verdict is
```

| Bench | Steps | State |
|---|---|---|
| `display` | 18 | ✅ **18 fresh** |
| `nanokontrol` | 6 | ✅ **6 fresh** |
| `tempo` | 13 | **11 fresh** — steps 3 and 4 corrected and not yet re-run |
| `launchpad` | 26 | **17 fresh** — 9 corrected and not yet re-run |
| `phone` | 14 | not run |
| `midi` | 18 | not run |
| `state` | 5 | not run. ⚠️ **LAST** — its step 5 is a real power cycle |

⚠️ **`--target` is never needed.** Every bench picks its own; only `state` chooses `paper`.

⚠️ **Orphan records exist in `latest.json` and are deliberate** — 19 from `nanokontrol` steps 7–19
and 3 from the `tempo` steps that were cut. The freshness check ignores them and they are the record
of real runs. Brendan was asked about the first set and chose to leave them. **Do not prune either
without asking.**

### The rig's state, which two steps depend on

✅ **`knobs.txt` on the device reads `0.0957967 0 0 0`** — knob 1 parked at 57 BPM and saved through
`Storage → Save` on 2026-08-11. Two steps need it: `tempo` step 2 can only reach the **held** branch
of parameter pickup with a knob saved off the rail, and `midi` step 1 asserts the footer reads
**57 BPM** at boot. ⛔ **A `tools/deploy.sh --clean` deletes it** and both steps then fail on a
working instrument.


## ✅ The open bug is closed — a truncated saved mode killed the whole map

**Observed as a raw `og-knob-1 0` row on the OLED where a BPM belonged.** The cause was
`/sdcard/cut-it-state/cut-it-auto.txt` holding **`mode compose`** with the mode *name* truncated
away: the restore replays it at ~3500 ms, `[list split 1]`'s remainder is empty, the lookup key
falls back to the control name alone, and `[text search]` then hunts for `og-knob-1` in the **mode**
column where it can never match. Every Organelle knob took the raw-row branch.

**Repaired with no code change** — one real mode selection writes all three atoms back. The write
path was sound throughout and is gated.

The full mechanism is a Trap on [ref/module/map.md](ref/module/map.md) (item 294), the reason a bad
value survives every reboot is on [ref/module/state.md](ref/module/state.md), and the hardening —
⬜ `u_map` accepts a mode it cannot use and should refuse it on `err` — is
[plan-v04.md](plan-v04.md) §3. ⛔ **Do not do that hardening until all seven benches are fresh**:
`tempo` and `midi` both depend on `u_map.pd`, so touching it stales them again.


## What remains

**One bench at a time, checking in after each.**

```sh
./test/run.sh --bench tempo --from 3       # judge 3 and 4 then press q -- 5-13 are fresh
./test/run.sh --bench launchpad --from 7   # 7 16 17 19 21 22 24 25 26
./test/run.sh --bench phone
./test/run.sh --bench midi
./test/run.sh --bench state                # LAST
```

| Bench | What has to be in front of you |
|---|---|
| `tempo` | The SP-404 on Pattern Select with a pattern loaded and nothing playing |
| `launchpad` | Eyes on the grid. Three hot-swap steps — you unplug it and watch it come back |
| `phone` | PdParty open on the `CutItRemote` scene **before** step 1. Steps 13–14 close and reopen it |
| `midi` | SP-404 on bank A, nanoKONTROL, Volca audible. ⚠️ **Sweep slider 1 to the top first** — it is Volca CC 41, Velocity, and left at the bottom it silences the device to its own keyboard |
| `state` | **Last in the session.** Step 5 is a real power cycle, and it resets the wifi-fault uptime clock |

⚠️ **`launchpad --from 7` re-walks twenty steps**, which is the case that used to blow the runner's
line cap. It is fixed and gated, but that walk has never run this long on hardware — **if it stalls,
say so rather than assuming the bench is dead.**

Three things to say out loud before the run rather than after:

- **The Volca is by ear and always will be.** It transmits nothing, so there is no readback of any
  kind. The oracle is a Cut It control *changing* the sound, never the sound existing.
- **The two Volca hot-swap steps pull the interface alone**, and no longer need a second device.
- **A `wait: 12` step wants enter pressed as soon as the cable is out**, not after counting to ten —
  the runner starts listening from the press, and a `device-lost` warn is up to 8 s behind.

Each device run `killall pd`s the instrument and **strands the Launchpad in Programmer Mode**.
Restore with `./tools/lp-live.sh` or `./tools/deploy.sh`.

### The landing

1. Delete `plan-v03.4.0.1.1.md`.
2. Remove its row from `CLAUDE.md`'s plan table and its entry in the *What is being BUILT next* row.
3. Point `plan-v04.md` §3's bench item at whatever is still open, or delete it.
4. `python3 test/gate/docs-check.py -v`.


## ⛔ What this session already learned, so it is not learned again

**Every bench text defect below was found by a person at the rig and could not have been found any
other way.** ⚠️ **Nine failures across four benches produced zero instrument bugs** — every one was
the bench asserting something the instrument does not do, or something nobody can see. `git log
1df905c..HEAD` is the record.

| | |
|---|---|
| **A fix reaches one of two identical paths** | The console flush landed in the step loop and not in the `--from` walk, so a resume blew the 2000-line cap and died as an uncaught `Stalled` — a traceback with no verdict and no resume line. ⚠️ **It looked intermittent because it is a race.** The `hold`/`hands` bug before it had the same shape: the fix reached hands steps only, because those are the ones anybody tested by hand |
| **A gate and a bench asserting OPPOSITE claims** | Three `launchpad` steps said a panic hands the surface back; `display-assert` has asserted *"the grid SURVIVES a panic"* all along, and `m_launchpad` forbids the old wiring in capitals (item 250). Neither noticed the other for months |
| **A PASS IF that asks for the footer** | Three times, in two benches: the param layer **replaces** home, so a step that sends a `disp` row and then asserts the footer has hidden the thing it is judging |
| **A number only a predicate can display** | A counter reaches Pd's console and the runner shows one *only* through a predicate. Two steps asked a person to read a `BEATS` count that appeared nowhere at all. The generator refuses the reverse case and cannot catch this one |
| **A step the step before it made unjudgeable** | `u_err` shows every error in compose and only `fail` in perform, and `launchpad` 20 leaves the rig on mode-6. The warn at 21 was correctly invisible. **Every step sets up its own preconditions, and a mode is one** |
| **A `reload` step reboots the instrument** | So the rig comes back *restored* — the beat row runs at the 57 BPM in `knobs.txt`, not the tempo the earlier steps set. A correct observation read as a fault |
| **Hardware disproves prose that round-trips perfectly** | `bench-verify.py` proves the text survives generation, which is a different question from whether the text is TRUE. Five `tempo` steps asserted things the hardware does not do, and four were unreachable until the map was repaired |
| **A step that duplicates a gate is worse than no step** | Three `tempo` steps asserted what `clock-assert` and `tempo-assert` already own, touched no device, and printed their numbers only to the runner's terminal. One claim judged twice under two names makes `latest.json` report more coverage than exists |

⛔ **Every runner defect has a gate check that was proved red by mutation.** `runner-assert.py` went
138 → 142 over this session. **Do not add one without proving it fails** — see the **`gate`** skill.


## Reading list

**Read these, in this order:**

| | How much |
|---|---|
| `CLAUDE.md` | All of it. It is a router; it says where to look, not what is true |
| this file | All of it |
| `test/README.md` | *Running everything*, *The benches* and everything under it. **Skip the per-gate sections** unless a gate fails |
| `test/bench/bench_steps.py` | The module docstring and the table for whichever bench is being run. **Do not read all 800 lines** |

**Open only if the work reaches them:**

| | When |
|---|---|
| `test/runner/run.py` | A stall or a desync — `run_bench_driven` and the four helpers above it |
| `ref/module/map.md` | A pickup or lookup failure — *Parameter pickup*, items 236 to 242 and 294 |
| `ref/device/sp404.md` | Any 404 step. ⛔ It follows clock only between **40 and 200 BPM** |
| `ref/device/launchpad.md` | Any grid or panic step — item 250 |
| `ref/workflow.md` | *There IS a console* — how to get a real Pd console over ssh |

⛔ **Do not open** `plan-v03.4.1.md` or `plan-v03.5.md`. They are the next two pieces of work and
neither gates this one. `plan-v04.md` only to update its bench item at the landing.

**Invoke the `gate` skill** before touching any test, the `pd` skill before any `.pd`, and the
`docs` skill before any page under `ref/`.


## The rules that are not negotiable

- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and run `bench-gen.py`.
- ⛔ **Changing a `title` or a `pass_if` stales that step's verdict** — `step_sha` is built from
  those two. `need`, `do` and `watch` are free, and never reach the `.pd`.
- ⛔ **No comma and no semicolon in a `title` or a `pass_if`**, and never end a sentence on a bare
  number — Pd parses `500.` as a float and the stop vanishes. `need` and `do` take ordinary commas.
- ⛔ **A gate is not trusted until it has failed.** Reintroduce the bug, watch it go red, revert.
- ⚠️ **Read `run.sh`'s `RESULT:` line; never grep for it.**
- ⚠️ **One suite run at a time**, and never while a bench is running on the device.
- ⛔ **This project commits as you go**, in reviewable batches, and **Brendan is the sole author** —
  no `Co-Authored-By` and no agent byline. Imperative subject lines.
- ⛔ **Pd vanilla 0.49 for ever**, vanilla objects only, and **never save a patch from plugdata**.
- ⚠️ **Before any bulk delete or overwrite of Brendan's data, print the count, a sample and the
  evidence, then ask.**
