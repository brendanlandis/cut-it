# plan-v03.4.0.1.1 — finish the bench session

**Successor to `plan-v03.4.0.1.md`, which is deleted.** Its Parts 1, 3 and 4 all landed; Part 2 — a
person running all seven benches on the rig — is what is left, and running it turned up eight
defects in the runner and the step text that no gate could have found. Those are fixed. **Two of the
seven benches are complete, one is three steps in, and there is one open bug on the device.**

⚠️ **This plan is written to be handed to a fresh agent cold.** The reading list at the bottom says
what to open and what to skip.


## Where the session got to

`./test/run.sh` is green — **19 gates, 514 checks.** The patch is deployed and the instrument is up.

```sh
python3 test/runner/run.py --list      # what would run, and how fresh each verdict is
```

| Bench | Steps | State |
|---|---|---|
| `nanokontrol` | 6 | ✅ **6 fresh** — every step passed on the device |
| `display` | 18 | ✅ **18 fresh** — every step passed on the device |
| `tempo` | 16 | ⛔ **3 fresh.** Step 4 recorded a **fail**; see the open bug below |
| `launchpad` | 26 | not run. One stale `interrupted` from a 2026-08-10 stall |
| `phone` | 14 | not run |
| `midi` | 18 | not run |
| `state` | 5 | not run. ⚠️ **LAST** — its step 5 is a real power cycle |

⚠️ **`--target` is never needed any more.** Every bench picks its own; only `state` chooses `paper`.

⚠️ **Nineteen `nanokontrol/N` records for steps 7–19 are orphans** left by the regroup below. The
freshness check reports every one as reworded so nothing counts them as coverage, and they are the
record of a real run. Brendan was asked and chose to leave them. **Do not prune them without asking.**


## ⛔ THE OPEN BUG — a raw `og-knob-1` row on the device, and it is not reproducible on the Mac

**Observed 2026-08-11 on `tempo` step 4 (`Knob pickup on the first touch`), recorded as a fail with
the note:** *"saw correct info for 1 second, then og-knob-1: 0"*.

The step's PASS IF says the row must **never** read `og-knob-1` and never a raw 0-to-1 decimal —
that is item 238, and `m_organelle`'s comment says the knobs no longer report to `disp` at all.

**Half of it is explained and fixed.** `4b4aca2`: the runner re-fires a step every 0.8 s while its
verdict is open, and this step sends `120` to `tempo` **and** a knob that maps to `tempo`, so every
re-fire walked the footer from 120 back down to 10. Measured on the Mac at six full round trips in
five seconds, which is exactly what *"correct for a second and then something else"* looks like. The
step now carries `hold: False`.

⛔ **The raw row itself is NOT explained.** Measured on the Mac, three ways, all clean:

| Arm | Result |
|---|---|
| `param og-knob-1 0` against `main-dev.pd` | `DISP: status 10-bpm` then `DISP: bpm 10`. No raw row |
| the same in a scratch copy carrying `knobs.txt` of `0.5 0 0 0` | identical |
| the step's two actions re-fired every 0.8 s, six times | the 120 ↔ 10 flicker, and still no raw row |

**Start here, and measure before diagnosing:**

1. **Ask Brendan what the OLED actually showed** — a name row, a value row, where on the screen, and
   whether the `bpm` row was still there beside it. His note is four words and the shape of the row
   decides which file is responsible.
2. `og-knob-1` is mapped to `tempo` in **all six modes** (`Cut It/cut-it-map.txt`, rows 1–6), so an
   unmapped-control raw report should be unreachable. Confirm the instrument's live mode anyway.
3. ⛔ **The Mac cannot exercise the HELD branch of pickup at all**, which was found while chasing
   this and is worth writing up wherever pickup is documented: arming needs mother's push at load to
   store a target, and `u_mother-stub` does not push knob values. A scratch copy with a `knobs.txt`
   of `0.5 0 0 0` still released immediately. So *(a)* in that step's PASS IF is device-only.
4. ⚠️ **Brendan's `knobs.txt` reads `0 0 0 0`** — knob 1 saved at the bottom, which is the item 241
   rail case. With the equality release that is benign, but it means his run always takes branch
   *(b)* and the held branch goes unverified. Parking knob 1 mid-travel and doing a Storage Save
   first is the only way to cover *(a)* on this rig.


## What remains

**One bench at a time, checking in after each.** Nothing needs `--target`.

```sh
./test/run.sh --bench tempo          # restart it -- steps 2, 3 and 4 were reworded
./test/run.sh --bench launchpad
./test/run.sh --bench phone
./test/run.sh --bench midi
./test/run.sh --bench state          # LAST
```

| Bench | What has to be in front of you |
|---|---|
| `tempo` | The Organelle in reach. Steps 15 and 16 want the real aux button and knob 1 |
| `launchpad` | Eyes on the grid. Includes three hot-swap steps — you unplug it and watch it come back |
| `phone` | PdParty open on the `CutItRemote` scene **before** step 1. Steps 13–14 close and reopen it |
| `midi` | SP-404 on bank A, nanoKONTROL, Volca audible. ⚠️ **Sweep slider 1 to the top first** — it is Volca CC 41, Velocity, and left at the bottom it silences the device to its own keyboard |
| `state` | **Last in the session.** Step 5 is a real power cycle, and it resets the wifi-fault uptime clock |

Three things to say out loud before the run rather than after:

- **The Volca is by ear and always will be.** It transmits nothing, so there is no readback of any
  kind. The oracle is a Cut It control *changing* the sound, never the sound existing.
- **The two Volca hot-swap steps pull the nanoKONTROL out alongside the interface**, and have to: a
  `none` device's recovery rides a detectable device being missing in the same moment.
- **A `wait: 12` step wants enter pressed as soon as the cable is out**, not after counting to ten —
  the runner starts listening from the press, and a `device-lost` warn is up to 8 s behind.

Each device run `killall pd`s the instrument and **strands the Launchpad in Programmer Mode** — its
own Settings menu is locked out in that state. Restore with `./tools/lp-live.sh` or
`./tools/deploy.sh`.

### The landing

1. Delete `plan-v03.4.0.1.1.md`.
2. Remove its row from `CLAUDE.md`'s plan table and its entry in the *What is being BUILT next* row.
3. Point `plan-v04.md` §3's bench item at whatever is still open, or delete it.


## ⛔ What this session already learned, so it is not learned again

**Eight defects came out of one person running one bench.** Every one of them is committed with its
reasoning; `git log 1df905c..HEAD` is the record. The ones that will bite a fresh agent:

| | |
|---|---|
| **A stall is SILENCE, not slowness** | `wait_for` fixed its deadline before the loop, so `timeout` was the total time the call could take however much the patch was saying. Per line now, with a line cap for *prints forever and never answers* (`9d5bb9a`) |
| **GO is one UDP datagram and nothing retried it** | A lost one and a dead patch make identical silence, and GO has no safe blind resend — it means *run* in phase 0 and *advance* in phase 1. The benches gained `where` (prints step and phase) and `show` (re-describes, moves nothing) so the runner establishes which case it is in before acting (`9d5bb9a`) |
| **Nothing reads the console except a wait** | So a person's own traffic piles up — 4141 lines after two hands-on steps — and the next wait burned its whole cap on it. Worse, every stale line landed in the next step's predicate window. Flushed before every GO now (`3dbdfc1`) |
| **`$0-do-show` takes the step NUMBER, not a bang** | The encoder's `[r]epeat` had therefore never worked. Found by probing real Pd 0.49, not a fixture (`da37249`) |
| **A bench belongs to whatever its steps TOUCH** | `nanokontrol` carried fourteen steps that never touched the nanoKONTROL and nine that duplicated `display` exactly. The same OLED claim was being judged twice under two names, so `latest.json` reported more coverage than existed (`cfe65e0`) |
| **`Bench.paper` asked the wrong question** | *No actions* was a proxy for *no patch needed*. A predicate that reads a console and a `reload` step need one too (`cfe65e0`) |
| **A PASS IF must describe what the person can SEE** | Two tempo steps asked for numbers that live only on Pd's console, and one branched on whether `knobs.txt` exists — a fact the reader cannot check. The generator now refuses a step judged on a `print` or `ratio` predicate whose prose never mentions the number being printed (`76bd882`, `5f84a2d`) |
| **Evidence has to be readable** | A four-leaf predicate printed as two joined lines. It is a table now, one row per assertion, the counter's name said once, and only failing rows marked (`30257f6`). `need`, `do` and `PASS IF` wrap at 76 (`b33822c`) |

⛔ **Every one of those has a gate check that was proved red by mutation.** `runner-assert.py` went
90 → 138 checks over the session. **Do not add one without proving it fails** — see the **`gate`**
skill.


## Reading list

**Read these, in this order:**

| | How much |
|---|---|
| `CLAUDE.md` | All of it. It is a router; it says where to look, not what is true |
| this file | All of it |
| `test/README.md` | *Running everything*, *The benches* and everything under it. **Skip the per-gate sections** unless a gate fails |
| `test/runner/run.py` | `run_bench_driven` and the four helpers above it — `_ask_where`, `_regain_fired`, `_next_step`, `_say_auto`. The comments are the design document |
| `test/bench/bench_steps.py` | The module docstring and `STEPS_TEMPO`. **Do not read all 800 lines** |

**Open only if the work reaches them:**

| | When |
|---|---|
| `ref/module/map.md` | The open bug — *Parameter pickup* and everything under it, items 238 to 242 |
| `ref/device/organelle.md` | The open bug — *Saving*, and the knob decode |
| `ref/module/tempo.md` | If a tempo step fails for a reason that is not the runner's |
| `ref/workflow.md` | *There IS a console* — how to get a real Pd console over ssh |
| `test/runner/stream.py` | Only if a stall reappears |

⛔ **Do not open** `plan-v03.4.1.md` or `plan-v03.5.md`. They are the next two pieces of work and
neither gates this one. `plan-v04.md` only to update its bench item at the landing.

**Invoke the `gate` skill** before touching any test, the `pd` skill before any `.pd`, and the
`docs` skill before any page under `ref/`.


## The rules that are not negotiable

- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and run `bench-gen.py`.
- ⛔ **A gate is not trusted until it has failed.** Reintroduce the bug, watch it go red, revert.
- ⚠️ **Read `run.sh`'s `RESULT:` line; never grep for it.** `grep -E 'ALL|FAILED'` also matches the
  per-gate `--- FAILED:` lines, and a broken patch has been committed that way.
- ⚠️ **One suite run at a time**, ~5 minutes, and only about a minute of it is computation.
- ⛔ **This project commits as you go**, in reviewable batches, and **Brendan is the sole author** —
  no `Co-Authored-By` and no agent byline. Imperative subject lines.
- ⛔ **Pd vanilla 0.49 for ever**, vanilla objects only, and **never save a patch from plugdata**.
- ⚠️ **Before any bulk delete or overwrite of Brendan's data, print the count, a sample and the
  evidence, then ask.**
