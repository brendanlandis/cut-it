# Plan v0.3.1 — the test runner

**One terminal command runs the gates and the benches, ends in a summary you can read at a glance,
and records a pass/fail verdict for every step.** Where a step can be judged by a program it judges
itself; where it needs eyes on the hardware it tells you what to have at hand, what to press and what
to watch for, then waits.

This plan changes **no patch behaviour**. It is entirely `test/`-side, plus one line in
`check-all.sh`.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** Do not suggest any object newer than 0.49.
- ⛔ **Never open or save an Organelle-bound patch in plugdata.** It rewrites `.pd` files into a
  format 0.49 cannot parse.
- **Vanilla objects only** — neither ELSE nor cyclone is on the device.
- ⛔ **Never touch git.** Reading is fine. Brendan commits his own work.
- ⚠️ **Read `check-all.sh`'s `RESULT:` line; do not grep for it.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit the step tables and regenerate; never the `.pd`.
- ⛔ **A gate is not trusted until it has failed.** That applies to this runner as much as to a gate.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`gate`** skill | ⛔ **Invoked, not read** | The scratch-copy pattern, why counts must be exact, the ways a check passes vacuously |
| [plan-v04.md](plan-v04.md) | §3 and §7 in full | What is unresolved, and the seven ways this project has been wrong before |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14` |
| `git log` | **Grep it, never read it** | Git is the journal |
| [test/README.md](test/README.md) | **All of it** | ⚠️ **Six of its claims are stale** — it says the tables are `STEPS3`…`STEPS8` (they are `STEPS_DISPLAY`…`STEPS_MIDI`), that the generator "writes all six" (seven), "any of the four benches" (seven), and lists `lp-monitor.pd`, `lp-step0.pd` and `self-wire.pd` under `test/` when they live in `tools/`. **Fix them as you go** |
| `test/check-all.sh` | **All 109 lines, comments included** | You change one line. Its comments say why exactly one line matches `RESULT:` — a broken patch was committed by grepping |
| `test/bench/bench-gen.py` | **All of it** | You extend it. `check()`, `build()` and the counter block are what you touch |
| `test/bench/bench_steps.py` | **All 107 steps** | The tuple you extend. ⛔ Its docstring forbids rewording hardware-verified prose |
| `test/bench/bench-verify.py`, `test/bench/bench-extract.py` | Both in full — they are short | The round-trip guard, and the marker parser you reuse |
| `test/gate/lib_assert.py` | **All of it** | `parse()`, `windows()` and `require_capture()` are **reused, not rewritten** |
| `test/gate/lib-scratch.sh` | Its function signatures, plus `midi_rewrite` in full | Mac runs need `scratch_make` and `scratch_state_dir`; ⛔ they must **not** call `midi_rewrite` |
| `test/gate/phone-assert.py` | The bind-before-launch section only | The pattern the OSC predicate copies: bind the socket **before** launching Pd |
| `tools/go.sh` | All of it | It becomes a thin wrapper so there is one GO implementation |
| `test/bench/tempo-bench.pd` | **Skim one screen** | To see what the generator emits. ⛔ Never edit it |
| `Cut It/u_mother-stub.pd` | Its OLED-decode subpatch | It already decodes `oscOut` into `cnv` rows — that is what makes an OLED predicate possible |

**Do not read** `ref/device/*` or `ref/module/*` except [ref/module/tempo.md](ref/module/tempo.md)'s
rate-ceiling table.

---

## What is already true

- **`test/check-all.sh` is the gate half and it works.** 9 gates plus 4 structural checks, ~40 s,
  Mac-only, one `RESULT:` line. Its header promises it *"touches NOTHING on the Organelle … safe to
  run at any time, including with the device off."*
- **The benches are generated.** `test/bench/bench-gen.py` reads the tables in
  `test/bench/bench_steps.py` and writes seven `.pd` files: display 14, nanokontrol 18, tempo 15,
  launchpad 25, phone 15, state 6, midi 14 — **107 steps**.
- **The step model is `(title, pass_if, [(message, bus), ...])`.** `pass_if` is prose beginning
  `PASS IF`. There is **no machine-readable expectation and no verdict channel anywhere.**
- **Output markers already exist and are already parsed** by `bench-extract.py`:
  `=== STEP-NN-of-MM === <title>`, `PASS IF: …`, `>>> press GO to run step N of M`,
  `--- step N fired ---`, `=== BENCH COMPLETE ===`.
- **GO** arrives from a `bng`, `[r encbut]`, or `[netreceive 9998 1]`. `tools/go.sh` sends `go;` over
  UDP.
- **Two benches have zero actions in every step** — `state` (6) and `midi` (14). `test/README.md`
  already says a bench with no actions need not be loaded at all.

---

## Three findings that shaped this plan

**1. Removing the END MARKER steps is safe, and it was traced.** In `bench-gen.py` the describe chain
ends with a connection into `done_t`, so a step number matching no `[select N]` falls out of the last
select's right outlet and prints `=== BENCH COMPLETE ===` — on **exactly the same GO press** that
would have described the END MARKER. The `--- step N fired ---` tail text is computed from
`len(steps)`, so the new last step gets "that was the last one" automatically.

**2. `"HANDS" in title.upper()` already misses nine hands-on steps.** Measured: all three
`THE NANO --` steps, both tempo `BY HAND` steps, and four of the six state steps. **That settles the
design question — the hands-on flag must be a field, not a substring test on prose.**

**3. A Mac run *with the GUI* is far more meaningful than a headless one**, because `u_mother-stub`
draws the front panel and decodes the OLED inline.

---

## Design decisions, and why

### `check-all.sh` is called, never extended

Folding benches into it destroys its device-independence guarantee and turns a 40-second pre-commit
reflex into a 20-minute human loop. ⚠️ **A check that costs twenty minutes stops being run**, which
is the same failure `check-all.sh` itself was built to fix.

**One line changes in it**: `echo "${RESULT_LABEL:-RESULT}: PASS -- all gates."` Run bare, its output
is byte-identical to today. The runner sets `RESULT_LABEL=GATES` and emits the only `RESULT:` line
itself, at the bottom.

⛔ **Do not filter check-all's output instead.** `GATES RESULT:` still matches `RESULT:`, so
`grep -c 'RESULT:'` would read 2 and the one rule this project protects hardest would be broken.
**Make `grep -c 'RESULT:' == 1` an assertion in the runner's own self-test.**

### The predicate lives in the step table, never in the `.pd`

The step tuple grows an **optional fourth element, a dict**:

```python
#  ('title', 'PASS IF: ...', [(msg, bus), ...])          <- all 107 today, unchanged
#  ('title', 'PASS IF: ...', [(msg, bus), ...], {...})   <- new, opt-in

def norm(step):
    """A step is 3 or 4 long. The 4th is RUNNER-SIDE ONLY and never reaches a .pd,
    so bench-verify's three-field diff is unaffected."""
    title, pass_if, actions = step[0], step[1], list(step[2])
    return title, pass_if, actions, dict(step[3]) if len(step) > 3 else {}
```

Three call sites unpack exactly three today and must route through `norm()`: `bench-gen.py`'s
`check()` and `build()` (twice), and `bench-verify.py`'s `norm()`. **That is the entire compatibility
cost.**

⛔ **Do not emit predicates into the `.pd`.** It reopens 107 hardware-verified step texts to the
comma/semicolon fragmentation hazard the generator exists to prevent — the same defect that produced
fourteen fragments on the first Phase 6 run — and buys nothing, because with the runner in place the
person reads the runner's terminal, not Pd's console.

Meta keys:

| Key | Is |
|---|---|
| `need` | List of strings — what to have at hand |
| `do` | String — what to press. **Its presence is the authoritative hands-on flag** |
| `watch` | String — what to look for. Defaults to `pass_if` minus the `PASS IF: ` prefix |
| `check` | A predicate spec. **Absent means a human judges** |
| `wait` | Seconds of predicate window |
| `targets` | e.g. `("device",)`. On any other target the runner records **skip with a reason** |

### Predicate kinds — data, not lambdas

Declarative so the vacuity lint can read them and so they survive into the result file:

| Kind | Asserts |
|---|---|
| `print` | A `[print NAME]` line landing in a numeric range |
| `bus` / `bus-count` / `bus-not` | Tap lines present / **exactly** n / absent |
| `oled` | Decoded `/oled/gPrintln` contents, has and has-not |
| `osc` / `osc-rate` | A datagram on a bound port; a rate in Hz over the window |
| `file` | A path's contents, or newer-than |

⛔ **`bus-count` asserts EXACTLY n, never "at least".** A count that has drifted is the failure this
project keeps catching, and "at least" cannot catch it.

The bus and OLED kinds need a new generated **`bench-tap.pd`** in `test/bench/` — emitted by the
generator like everything else, loaded as a fourth patch, pure `[r ...]` → `[print BUS]`, and it
**sends nothing.** C-5 gives `g_oled` sole ownership of `oscOut`, but that governs *writing*; adding
a receiver cannot change delivery. **State that in the file so nobody "fixes" it.** Its print labels
must match `lib_assert.parse()`'s bus regex exactly, so that parser is reused rather than copied.

### The default target is the device

A bench's PASS IFs are claims about an OLED, a Launchpad, a 404, a Volca and an SD card.

| Target | Is | Can judge |
|---|---|---|
| `device` | **Default.** The real rig | Everything |
| `mac-gui` | `main-dev.pd` in Pd with the GUI; the stub draws the OLED and fakes knobs, aux and encoder | Display, nanokontrol, tempo — screen *and* numbers |
| `mac` | `-nogui`, auto predicates only | Counters, bus taps, `oscOut`, OSC datagrams. **Everything else skips** |

⛔ **A step a target cannot judge is recorded as SKIP WITH A REASON, never as a pass.**

Mac runs go through `scratch_make` and `scratch_state_dir` so a previous run's saved mode cannot be
restored mid-bench at ~3.5 s. ⛔ **They must not call `midi_rewrite`** — a bench wants real MIDI out.

### Paper mode

`state` and `midi` have zero actions across every step. The runner detects `all(not s.actions)` and
runs them with **no Pd, no ssh, no `killall pd`, no stranded Launchpad**. That is 20 of 107 steps
working with no device machinery at all, which is why it is Phase A.

---

## The runner loop

```
1  print the header:  [4/14] tempo -- BY HAND -- press the aux button twice
2  need:   "have at hand: the Organelle powered, aux button reachable"
   do:     "press the aux button twice, slowly"
   watch:  meta.watch, else pass_if with "PASS IF: " stripped
3  if there is a `do`:  block on "press enter when you are ready"
   ⛔ NEVER auto-answer this. GO sent before the finger is on the pad judges
      the step against nothing.
4  send GO  (UDP 9998, or the bng on mac-gui)
5  wait for "--- step N fired ---",  timeout 5 s  ->  STALL
   assert the patch's printed "=== STEP-NN-of-MM ===" matches N, and the title
   matches the table                              ->  DESYNC, abort
6  open the predicate window from the fired line
7  with a predicate:  AUTO PASS / AUTO FAIL, printing want vs got, no prompt
   without one:       [p]ass [f]ail [s]kip [r]epeat [u]ndo [?]passif [q]uit
                      f -> optional one-line note
8  append the record and fsync BEFORE the next step, so a crash loses at most
   one verdict
```

⛔ **Desync is fatal and is never recovered by guessing.** A runner recording verdicts against the
wrong step is precisely a gate that lies.

**Waits.** The generator's counter block hardcodes a 10 000 ms window and detects a measure step by a
bus name ending `-zero`. **Both facts would now exist in the runner too** — put them in one place in
the step table module and import from both, or it is a second copy of a number, which is the drift
this project keeps eliminating.

**Stalls come in two shapes and must be distinguished.** No first step marker within 15 s of launch
means the bench never loaded — say so by name, because that is the signature of scp'ing it somewhere
the launch line does not name. GO sent with no fired line in 5 s means stalled mid-run: offer resend,
mark fail, or abort.

**Ctrl-C** marks the current step `interrupted` — not fail, not skip — flushes, tears the target
down, and prints the resume command. ⚠️ On the device it also prints the `tools/lp-live.sh` warning,
because `killall pd` strands the Launchpad in Programmer Mode.

---

## Which steps become machine-checkable

At least eight, and they are the ones a human currently gets wrong:

| Bench / step | Today | Predicate |
|---|---|---|
| **tempo 3** READ THE COUNTS | A human reads three numbers off a console | `print` with all three counts and their ratio — **fully auto** |
| **tempo 11** COUNTS WHILE STOPPED | Same | `print` — fully auto |
| **tempo 7** 5000 sent TWICE | A human counts alert boxes: *"EXACTLY ONE"* | `bus-count` — ⚠️ humans miscount, machines do not |
| **state 3** CONFIRM IT REACHED THE DISK | **Literally instructs the human to run a shell command and read the output** | `file`, with the runner running `tools/fetch-state.sh` |
| **state 4** COMMIT — Storage then Save | A human compares a timestamp | Human presses; `file` newer-than judges |
| **midi 4** press pad 5 on bank A | A human reads `sp-pad` off the OLED — **the** pad that catches the old `47 + n` formula | Human presses; `bus` judges |
| **midi 7** A RELEASE IS NOT A PRESS | *"two updates means the velocity test has gone"* | `bus-count` |
| **display 3** grain 12, no leftover `%` | Its own text says *"this is the one that matters most"* | `oled` has/has-not — a string comparison |

Also convertible: **midi 1** (the footer must read 57, not 120 — the very first thing asked of a
human is reading a two-digit number, and 57-vs-120 is the whole point), **midi 6**, **launchpad 14**.

### ⚠️ The phone is the honest exception

`phone-assert.py` can bind a local port because its *driver* points `u_net` at localhost. In a live
run `u_net` sends to the phone and the Mac cannot see those datagrams. So on the device, a tap
predicate on the phone steps proves what `u_net` was **offered**, not what it **filtered** — and the
filtering is already asserted headlessly by its gate.

Two honest options, and **neither is both**: a Mac run with `u_net` repointed at localhost in the
scratch copy, giving real OSC verdicts and **no phone**; or a device run with a real phone and a
human verdict. ⛔ **Do not let a precondition check masquerade as the step's verdict.**

---

## Results, and freshness

Per-run records go under `test/results/runs/` and are gitignored. A rolled-up `latest.json` beside
them is **committed**, which is what lets `git log` answer *"when did phone step 12 last pass, and on
what code?"*

A verdict is **fresh** only if all four hold: the sha of its title and `pass_if` is unchanged
(reword the step and the old verdict answered a different question); the target matches; it is under
30 days old; and its **dependency sha** is unchanged.

⛔ **Dependencies are per bench, not the whole tree.** Hashing all of `Cut It/` would make every bench
stale on every patch commit, and **a signal that is always red is a signal that gets ignored** — the
mirror image of a gate that lies. Add a `deps` list to the bench table: tempo depends on `u_tempo.pd`
`c_clock.pd` `u_map.pd`; launchpad on `g_grid.pd` `m_launchpad.pd`; display on `g_oled.pd`. Then
staleness is actionable: *"you changed `u_tempo.pd` — the tempo bench's 14 verdicts no longer
apply."*

⚠️ **Freshness must not fail `check-all.sh`.** That would put a red line in front of every commit
whenever hardware had not been touched in a month. It appears in the runner's summary only.

---

## The summary

```
 ok  gates          13 gates                                     41.2s
 ok  tempo          14 steps   12 auto    2 hands   0 failed     2m11s
 FAIL midi          13 steps    5 auto    8 hands   1 failed     4m03s
      step 4  THE PAD THAT BREAKS THE OLD FORMULA
          want  DISP: sp-pad 5      got  DISP: sp-pad 13
 skip phone         14 steps   PdParty not answering
 old  launchpad     24 steps   last passed 2026-04-02; g_grid.pd has changed since

 Benches  3 run, 1 skipped, 1 stale, 2 never run
 Steps    62 passed, 1 failed, 3 skipped, 31 stale, 13 never run
 RESULT: FAIL -- 1 step failed, 3 skipped, 31 stale
```

⛔ **`RESULT: PASS` requires `failed == skipped == stale == 0`** *and* a record for every step in the
selected set. **A skip is never a pass.**

---

## Build order

| | Phase | Ends when |
|---|---|---|
| **A** | **Skeleton, no Pd.** The runner with `--replay`, the prompt loop, the record file, the roll-up, `run.sh` in `test/`, the `RESULT_LABEL` change, and the self-test added to `check-all.sh` | `--bench midi` and `--bench state` work end to end — 20 steps, no device |
| **B** | **Driving Pd.** Target scripts for device and Mac, the stream reader, the GO sender (with `tools/go.sh` reduced to a wrapper), stall/desync/teardown, `--from N` | A bench runs on the device and is resumable |
| **C** | **The tap and `print` predicates.** `bench-tap.pd` emitted by the generator, the `norm()` refactor, the counter window centralised. Convert tempo 3, tempo 11, launchpad 14 | ⚠️ First can-it-fail **on hardware** |
| **D** | **Bus and OLED predicates.** Convert midi 4/6/7, display 3, tempo 7. **Land the vacuity lint here, not later** | The lint refuses to generate a bad predicate |
| **E** | **Instructions and pruning.** Bench-level `rig` lists; `do` and `need` on the ~20 hands steps; the disagreement lint. **Remove the dead steps** | Step counts drop and `bench-verify.py` confirms each |
| **F** | **OSC and file predicates.** One shared OSC decoder extracted from the phone gate; the phone-mirror mode; state 3 and 4 over ssh | The last convertible steps convert |

### The dead steps removed in Phase E

⛔ **Four END MARKERs** — launchpad 25, phone 15, state 6, midi 14. Each says of itself
*"THIS STEP ASSERTS NOTHING."* **Two bookkeeping-only steps** — nanokontrol 18 and tempo 15, both
titled `done -- press Ctrl-C`, whose PASS IF only recites which earlier steps meant what.

⚠️ **Keep display 14.** It is titled `done -- press Ctrl-C` and looks identical to the other two, but
its PASS IF is a **real deferred assertion** — that the screen returned to the meters on its own
during a 35-second wait, which is the 30-second modal safety timeout armed by step 13. **Rename it;
do not delete it.**

`bench-verify.py`'s printed step count is the guard on every drop: 25→24, 15→14, 6→5, 14→13, 18→17,
15→14.

---

## ⛔ How this runner would lie, and what stops it

| Lie | Guard |
|---|---|
| A verdict recorded against the wrong step | Match the patch's printed step number **and** title; abort on mismatch |
| A predicate passing vacuously on an empty stream | **A purely negative predicate is illegal** unless the window also holds an independent liveness witness |
| A tap that is vacuous because the bench itself sourced the traffic | Static lint in the generator: refuse to generate when a predicate names a bus the same step writes |
| Skips or stales counted as passes | All five counts printed; PASS requires all three to be zero |
| The runner reporting PASS having run nothing | Print steps-attempted against table length, **and watch it go up** |

### The runner gets tested by replay

`--replay <transcript>` reads the Pd stream from a file and the verdicts from a scripted keystroke
list. A self-test drives it against fixtures, each asserting an exit code and a summary:

| Fixture | Must produce |
|---|---|
| A clean transcript | PASS, correct step count |
| Truncated at step 7 | STALL, **not** PASS |
| Step numbers out of order | DESYNC abort, **not** a shifted tally |
| An empty file | *"the bench did not load"*, exit non-zero |
| Counters printing `0` | AUTO FAIL on tempo 3 — the DSP-off signature |
| SIGINT at step 5 | 4 verdicts recorded, resume command printed |
| Every verdict `s` | RESULT: FAIL, **never** PASS |

This is Mac-only, headless, and under a second, so it goes into `check-all.sh` without violating that
file's guarantee. **It is the only way the runner's failure paths are ever exercised**, because a
successful hardware run touches none of them.

⚠️ **Then one deliberate can-it-fail on hardware**: set the tempo wrong and watch tempo step 3's
count predicate go red. That is the acceptance test for the whole idea, and this project's history
says budget for it failing to fail on the first attempt.

---

## Verification

```sh
./test/check-all.sh                        # must still print exactly one RESULT: line
./run.sh --gates                      # byte-identical to check-all.sh run bare
./run.sh --bench midi                 # 13 steps, no device
./run.sh --bench state                # 5 steps, no device
python3 test/bench/bench-verify.py         # step counts confirm the six removals
python3 test/gate/docs-check.py -v
```

Plus: the runner with the rig attached, front to back, and the seven replay fixtures green.

---

## Done means

1. One command runs gates and benches and ends in one summary and one `RESULT:` line.
2. Every hands-on step states what to have at hand, what to press and what to watch for.
3. At least eight steps judge themselves, each having been made to fail once.
4. The six assertion-free steps are gone and display 14 is renamed, not deleted.
5. `test/README.md`'s six stale claims are corrected.
6. [CLAUDE.md](CLAUDE.md)'s *The tests* table and `plan-v04.md` §2 name the runner as the entry point.
7. **This file is deleted.**

⛔ **Leave every change in the working tree.** Brendan commits his own work.
