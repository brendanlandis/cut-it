# Plan — the testing refactor

**This document is written to be handed to an agent cold. Read it first and in full.** It says what
the job is, what is already true, what to do in what order, and how to know each step worked.

⛔ **Invoke the `gate` skill before writing or changing any test here**, and the `pd` skill before
touching any `.pd`. They carry the rules this plan assumes.

⚠️ **Everything in this plan is Mac-side. No device needs to be plugged in for any of it.** All four
headless gates run Pd against a scratch copy with objects rewritten to printing stubs; `check-all.sh`
runs the whole suite in ~40 s with no `ssh`, no `scp` and no hardware. The **benches** are hands-on,
but they are *generated*, and their acceptance test — `bench-verify.py` — is also Mac-side.

---

## 1. The job in one sentence

**The gates are named and organised by PHASE, which is a time axis; move them onto the MODULE axis
the documentation now uses, splitting and merging where the phase boundary cut across a concern.**

This is not a rename. Two of the four gates are each doing several unrelated jobs, and one job is
split across two gates. The renaming falls out of fixing that.

---

## 2. What is already true

✅ **The documentation refactor is done and the taxonomy is settled.** A module is a physical device
or one instrument concern, the directory is the kind, and **these are the names the gates adopt**:

```
ref/device/   launchpad  nanokontrol  organelle  phone  sp404  volca
ref/module/   audio  boot  display  map  state  tempo
ref/          architecture  conventions  device-os  rig
```

✅ **Every module page already declares its coverage**, and `test/gate/docs-check.py` fails if a named
file does not exist:

```markdown
**Files:** `Cut It/m_404.pd` · **Gate:** `test/gate/phase9-assert.sh` · **Bench:** `test/bench/phase9-bench.pd`
```

⛔ **So renaming a gate is not free — every page naming it goes red until its header moves too.**
That coupling is deliberate and it is the safety net for this whole job. **Do not weaken it.**

### What claims what today

| Page | Gate | Bench |
|---|---|---|
| `device/launchpad` | `phase6-assert.sh` | `phase6-bench.pd` |
| `device/nanokontrol` | `phase6-assert.sh` ⛔ **false — it tests nothing about the nano** | `phase4-bench.pd` |
| `device/organelle` | `phase6-assert.sh` ⛔ **false — it tests nothing about the OLED** | `phase3-bench.pd` |
| `device/phone` | `phase7-assert.sh` | `phase7-bench.pd` |
| `device/sp404` | `phase9-assert.sh` | `phase9-bench.pd` |
| `device/volca` | `phase9-assert.sh` | `phase9-bench.pd` |
| `module/audio` | **none** | **none** |
| `module/boot` | `check-all.sh` | `phase3-bench.pd` |
| `module/display` | `phase6-assert.sh` | `phase3` + `phase4` + `phase6-bench.pd` |
| `module/map` | `phase9-assert.sh` | `phase9-bench.pd` |
| `module/state` | `phase8-assert.sh` | `phase8-bench.pd` |
| `module/tempo` | `phase6-assert.sh` | `phase5-bench.pd` |

**Five pages claim `phase6-assert.sh` and two of those claims are false.** That is the concrete cost
of the phase axis, and it is why this job is worth doing rather than tidying.

---

## 3. The target

**All of these live in `tools/`**, alongside the ones they replace. They are named without the
prefix here because they do not exist yet, and `docs-check.py` rightly fails a document that points
at a file that is not there.

⛔ **Do not trust an ordinal — get the list yourself.** The groupings below were derived by reading
the assertion strings in order, and **an ordinal is positional in the source**: edit an assert and
every number after it shifts. Regenerate before splitting anything:

```sh
python3 - <<'EOF'
import re, pathlib
for n in (6, 9):
    t = pathlib.Path(f'tools/phase{n}-assert.py').read_text()
    for i, c in enumerate(re.findall(r'check\(\s*"([^"]*)"', t), 1):
        print(f'phase{n} {i:>2}. {c}')
EOF
```

### `phase6`'s 23 checks

| Goes to | Checks |
|---|---|
| `display-assert` | 1–5 frame shape (byte count, terminator, static type, the 1–108 span) · 6 *DSP off and idle: the grid stops repainting* · 7–9 the home layer · 10–12 modal, and that a `warn` changes nothing · 13–17 alert and its expiry back to the modal underneath · 18–20 the beat row walking |
| `launchpad-assert` | 22 *enters Programmer Mode at boot* · 23 *returns to Live Mode on panic* |
| ⬜ **Decide** | 21 *after a panic the grid paints nothing at all* — this is the **arbiter's** response to losing ownership, and equally the **device's** panic behaviour. It reads either way |

### `phase9`'s 29 checks — and they split THREE ways, not two

⚠️ **This corrects an earlier draft of this plan**, which said checks 6–29 all went to one MIDI gate.
Reading the assertions shows otherwise: nine of them are about the **404's receive path**, which is a
device concern, not an emission one.

| Goes to | Checks |
|---|---|
| `map-assert` | 1–5 the **static lint** — literal route box, four-atom rows, ⛔ the guard, valid modes, no duplicate pair. **No Pd, ~200 ms** |
| `map-assert` (runtime) | 7 ⛔ *a control moved at 300 ms ALREADY MAPS* · 8 a mapped control reaches its destination · 9 ⛔ *the SAME control in another mode does NOTHING* · 10–11 ⛔ an unknown destination emits no MIDI and reports `unknown-dest` |
| `midi-out-assert` | 12–14 the Volca — CC, note on channel 49, ⛔ `pgmout` arg+1 · 15–18 the 404 transmit side — all sixteen bank-A pads, bank-sets-channel, matched note-offs · 19–20 ⛔ the rate limit drops rather than queues, and the interval is real · 28 ⛔ panic covers all ten banks |
| **the 404's receive side** | 21–27 a pad press names bank and pad, two stable `disp` rows, a release reaches `param` but not `disp`, a different bank, ⛔ a channel outside the ten is ignored |
| — | 6 and 29 are driver bookkeeping. Keep whichever gate owns the driver |

⬜ **So where do 21–27 go?** Two defensible answers, and **this is the plan's one real open
decision:**

- **`sp404-assert`** — the 404 is one device with one page, and its gate covering both directions
  matches the module axis exactly. But then `midi-out-assert` loses the 404's transmit half too, and
  becomes just the Volca.
- **Keep emission together and give receive its own gate.** The argument for one emission gate is not
  the assertions — it is the **`EXPECT` count**, which is a repo-wide structural invariant: *these
  are all the MIDI emitters in the patch, and a new one must be declared*. That does not belong to
  any device.

**Recommendation: split the two jobs rather than the two directions.** One `midi-emitters-assert`
whose only job is the rewrite and the exact `EXPECT` count, and per-device gates — `sp404-assert`,
`volca-assert` — for behaviour. ⚠️ **But confirm with Brendan before building it**, because it is
three gates where this plan originally promised one.

**Benches follow the same axis**, generated from `bench_steps.py` as they are now.

---

## 4. Order of work

**One commit per step. Every step ends with `./test/check-all.sh` green.**

⚠️ **"One commit per step" describes the SHAPE of the work — one logical change, reviewable and
revertable on its own — not who runs `git commit`.** [plan-v04.md](plan-v04.md) says *never touch
git; Brendan commits his own work*. **If that still holds, leave each step in the working tree and
describe what changed.** Ask if unsure; do not assume from this line that committing is authorised.

### Step 0 — measure before moving anything

Record, in the commit message:

- the check count each gate reports today (`phase6` 23, `phase9` 29, and whatever `phase7`/`phase8`
  print)
- `phase9-assert.sh`'s `EXPECT="noteout:2 ctlout:2 pgmout:1 notein:2"`
- the box counts `pd-layout-check.py` gives for all 21 patches

⛔ **These are the numbers every later step is checked against.** A gate that comes out of this with
fewer assertions than it went in with has lost coverage, and nothing else will say so.

### Step 1 — the two pure renames

`phase7-assert` → `phone-assert`, `phase8-assert` → `state-assert`. Each is `git mv` on four files
(`.sh`, `.py`, `-drive-gen.py`, `-drive.pd`), plus `check-all.sh` and the `**Gate:**` line on
`device/phone.md` and `module/state.md`.

**Done when:** `check-all.sh` green, same check counts as Step 0, `docs-check.py` green.

⚠️ **Then prove each still fails.** Reintroduce one bug per gate, watch red, revert. A rename is
exactly the kind of change that silently disconnects a driver.

### Step 2 — split `phase9` at the seam it already has

The static lint and the runtime assertions are already separate functions in `phase9-assert.py`
(`static_lint()` and the rest). Split into `map-assert` and `midi-out-assert`.

**Done when:** the two gates' check counts **sum to 29**, and `module/map.md` and the two output
device pages name the right one.

### Step 3 — merge `phase6`'s `[midiout]` half into `midi-out-assert`

`phase6-assert.sh` rewrites `[midiout]` only; `phase9-assert.sh` rewrites `noteout`/`ctlout`/
`pgmout`/`notein` only. **One gate should rewrite all five with one `EXPECT` line.**

⛔ **`EXPECT` asserts an EXACT count per class, and it must stay that way.** A lower count means
assertions have gone vacuous; a higher one means a new emitter the gate does not know about.
`phase6`'s own comment drifted from five boxes to six with nothing noticing, which is the failure
this line exists to prevent.

**Done when:** `EXPECT` covers every emitter in `Cut It/*.pd`, and removing any one emitter from the
patch makes the gate red.

### Step 4 — split what is left of `phase6` into `display-assert` and `launchpad-assert`

The 23 checks divide as in §3. This is the step with real work in it: two drivers where there was
one, and the timings have to be rebuilt.

⛔ **TIME THE NEW WINDOWS FROM BEHAVIOUR, NOT FROM THE IMPLEMENTATION.** Phase 9's gate had 23 green
checks and missed a boot-time race because its windows started at 2400 ms *for the reason the code
read its table at 2000*. **A test whose schedule is derived from the implementation cannot falsify
it.** Since the drivers are being rewritten anyway, this is the moment to add a window that runs
*before* the thing being assumed.

**Done when:** the two gates' check counts sum to **at least 23**, and `device/launchpad.md`,
`device/nanokontrol.md`, `device/organelle.md`, `module/display.md` and `module/tempo.md` all name a
gate that actually tests them — **or `none`, honestly, if none does.**

⚠️ **`nanokontrol` and `organelle` will probably end up at `none`**, and that is the correct outcome
rather than a failure of this job. Their claim on `phase6-assert.sh` is false today; saying `none` is
an improvement over saying something untrue.

### Step 5 — the benches

Rename `STEPS3`…`STEPS9` in `bench_steps.py` onto module names, and update:

1. `test/bench/bench-gen.py`'s `PHASES` table
2. ⛔ **`test/bench/bench-verify.py`'s hardcoded tuple `(3, 4, 5, 6, 7, 8, 9)`** — miss this and a bench
   is generated but never fidelity-checked
3. every `**Bench:**` line

⛔ **Never edit a bench `.pd` — it is an output.** Regenerate.

**Done when:** `bench-verify.py` re-extracts every step's text and it matches, and no step's *text*
has changed at all. **This job does not touch what a bench asks a person to do.**

### Step 6 — `check-all.sh`, `tools/README.md`, and the plan

Update the gate list and the `run` labels. ⚠️ `tools/README.md` is 765 lines and the **tool cleanup**
will delete some of what it describes — touch only the gate names here and leave the rest.

---

## 5. How to know it worked

```sh
./test/check-all.sh              # every gate, ~40 s, Mac only. Read RESULT:, do not grep for it
python3 test/gate/docs-check.py -v    # the **Gate:**/**Bench:** lines resolve
```

- **No gate has fewer checks than Step 0 recorded**, and the totals reconcile.
- **Every gate has been made to fail** since it was touched. ⛔ *A gate is not trusted until it has
  failed* — `phase8-assert.sh` passed the broken patch **15/15** on its first can-it-fail run.
- **Every module page names a gate that tests it, or `none`.**
- `git diff --stat "Cut It"` shows **nothing**. This job does not touch the patch.

---

## 6. Open, and worth deciding while in here

- ⬜ **`module/audio.md` has no gate and no bench**, because every gate asserts on messages and
  nothing reads a signal back. A headless audio gate is possible — Pd can write a soundfile — and it
  would be the first. **Out of scope here; decide whether it becomes its own job.**
- ⬜ **`module/boot.md`'s gate is `check-all.sh`**, which is a suite rather than a gate. The boot
  sequence's stage timings are asserted by nothing.
- ⬜ **Nothing runs the benches.** `check-all.sh` verifies their *text* survived generation and stops
  there, which is correct — a person is the oracle — but there is no record of *when* each bench was
  last actually run, or against which commit.
