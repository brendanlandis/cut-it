# Plan v0.3.3 — coverage

**Six of the nine modules that "nine gates, one per module" implies have no behavioural gate at
all.** One of them — `g_led` — is referenced by **zero files** anywhere under `test/`. This plan
closes the worst of that, fixes three real defects in the gates that do exist, and builds the first
signal-domain gate in the project.

It runs after [plan-v03.1.md](plan-v03.1.md), because the new bench steps want the runner, and before
[plan-v03.4.md](plan-v03.4.md), which needs the stub this plan adds.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.**
- ⛔ **Never open or save an Organelle-bound patch in plugdata.**
- **Vanilla objects only.**
- ⛔ **Never touch git.** Reading is fine. Brendan commits his own work.
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit the step table and regenerate.
- ⛔ **A GATE IS NOT TRUSTED UNTIL IT HAS FAILED.** Every gate below gets a deliberate can-it-fail
  run, and this project's history says budget for it failing to fail on the first attempt.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`gate`** skill | ⛔ **Invoked before writing a line** | The scratch-copy and stub-rewrite pattern, why counts must be exact rather than non-zero, the ways a gate passes vacuously |
| The **`pd`** skill | ⛔ **Invoked** if you touch a patch | You will at least add a stub |
| [plan-v04.md](plan-v04.md) | §3 and §7 in full | §7 is a list of the ways this project's own measuring rigs have been wrong |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14` |
| `git log` | **Grep it, never read it** | Git is the journal |
| [test/README.md](test/README.md) | **All of it** | What every existing gate protects |
| `test/gate/lib-scratch.sh` | **All of it** | `MIDI_EXPECT`, `MIDI_INVENTORY`, `midi_rewrite`, `scratch_drive`, `scratch_run`. ⚠️ **It already names the missing `ctlin` stub as the blocker for a nano gate** |
| `test/gate/lib_assert.py`, `test/gate/lib_drive.py` | Both in full | Every new gate is built from these |
| `test/stubs/` | **Every file** | You are adding one. ⚠️ [test/README.md](test/README.md) explains why the `mac-stubs/` path trick cannot work here — `ctlin` is a **built-in class**, and Pd resolves the class table before it looks for a file, so **the object box has to be rewritten** |
| `test/gate/sp404-assert.sh` and `test/gate/sp404-assert.py` | **In full, as the model** | The richest gate — both directions, 17 checks, exact counts |
| `test/gate/volca-assert.sh` and `test/gate/volca-assert.py` | In full, as the small model | Six checks. The floor for what a gate looks like |
| `test/gate/launchpad-assert.py`, `test/gate/display-assert.py` | **In full** | You are fixing real vacuity holes in both |
| `test/gate/pd-layout-check.py` | Its `main()` tail only | One line is wrong |
| The `ref/` page for **each module you gate** | **In full, before writing its gate** | ⛔ **That page's `Facts` section is the assertion list.** Writing a gate without it invents assertions |
| The `Cut It/*.pd` for **each module you gate** | **In full** | You cannot assert on a bus you have not read |

**Do not read** the modules you are not gating this pass, [ref/device-os.md](ref/device-os.md), or
[ref/rig.md](ref/rig.md).

---

## What is already true

- **Every abstraction already gets a does-it-create check**, because six gates load the whole patch
  through `main-dev.pd` → `u_root`, and `pd-layout-check.py` runs over every `.pd`.
- **Nine gates exist** and each is named for the module it covers. `test/run.sh` runs them plus four
  structural checks.
- **The scratch-copy pattern**: a gate copies the patch to a temp dir, rewrites MIDI object boxes to
  `t_*` stand-ins, hard-fails on an exact-count mismatch, hand-creates the state files because
  `[shell]` is stubbed on the Mac, then drives windows and asserts on a capture.
- ⛔ **`lib_assert.windows()` exists specifically to stop vacuous passes** — it adds "the driver
  reached every window", so a `not X` assertion cannot be answered by an empty list.

---

## Phase 1 — three defects in the gates that already exist

Do these first. They are small, and two of them mean a currently-green gate is greener than it
should be.

| Defect | Why it matters |
|---|---|
| **`launchpad-assert.py`'s fifth check is inside `if live:`.** If the panic never fires, the check is **silently not run** and the tally drops 5→4 with nothing asserting the total | The gate has **no `A.windows()` bookkeeping at all**, so its own guard only requires *some* SysEx frame |
| **`display-assert.py` has no window bookkeeping either.** It groups frames by mark with `setdefault`, so **a missing mark is indistinguishable from an empty one** | Two of its assertions are negative — *"the grid stops repainting"* and *"after a panic the grid paints nothing"* — and both pass vacuously if the driver died early |
| **`pd-layout-check.py` returns `True` on an empty argument list** (`all([])`) | A glob that stops matching reads as a pass. This is the exact shape of the failure `docs-check.py`'s printed count exists to prevent |

⚠️ **Each fix needs its own can-it-fail run**: break the driver so a window never arrives, and confirm
the gate now goes red where it used to go green.

---

## Phase 2 — the missing gates, in priority order

**Priority is by risk, not by ease.** Each gate's assertions come from its `ref/` page's `Facts`
section, and each new gate must be added to `test/runner/gates.py`'s table --
which asserts its own length, so adding one means bumping `EXPECT` deliberately.

### 1. `m_nano` — the main control surface, with no headless coverage at all

⛔ **Blocked on a new `ctlin` stub**, which `lib-scratch.sh` already names as the reason a nano gate
cannot exist. Build the stub first; it unblocks this gate and is reused by
[plan-v03.4.md](plan-v03.4.md).

What to assert, from [ref/device/nanokontrol.md](ref/device/nanokontrol.md): the channel gate admits
Pd channels 17 and 18 and **nothing else**; `div 10` / `mod 10` decoding produces the five name
families; buttons emit **on press only**; an unmapped CC raises `warn m_nano cc-N-unmapped`; and the
channel outlet fires before the value, which is why the gate is set before it is read.

### 2. `u_err` — untested as a module, and its central behaviour is load-bearing

**Nothing headless asserts that perform mode suppresses `warn` but never `fail`.** That is entirely
bench prose today — and `plan-v04.md` notes that a mode split weighted toward `perform` **silently
quietens the error display**, which is a failure you would only discover at a venue.

Assert: `warn` passes the verbose spigot in compose and is dropped in perform; **`fail` passes in
both**; an unknown level prints the bad-level marker; every error reaches the log regardless of mode;
and the 21-character text limit.

### 3. `g_led` — zero references anywhere under `test/`

The cheapest gate in the plan and the largest relative gain. Four states map to four mother values;
an unknown state raises `warn g_led unknown-led-state`. ⚠️ Assert that `stopped` is **lit, not
dark** — the whole point is that a stopped patch and a dead patch must not look identical.

### 4. `c_clock` — the ratio argument is only ever human-read off a bench print

Assert the ratio and beats-per-bar arguments produce the right beat rate against a known tempo, that
a bad ratio and bad beats each raise their warning, and that the four outlets carry what they claim.

### 5. `u_init` — boot ordering, and it is load-bearing enough to force `scratch_state_dir`

Assert the stage sequence and its order, that `wire.sh` is invoked once, that mother's MIDI mapping
is shut off at load **and again later**, and that the restore stage fires after the state directory
exists.

### 6. `g_oled` — the densest module in the project, and 100 % human-judged today

Its gate only checks that the file exists. **A tap on `oscOut` makes a real gate possible** —
`u_mother-stub` already decodes that stream, so the decoder exists. Assert the layer priority
(alert > modal > param > home), the param TTL, the five-row store refusing a sixth control, rows
updating **in place** rather than reordering, and the ageing threshold.

### 7. `m_organelle` — zero references in any gate

Assert that each knob is `[change]`-filtered, that `og-` names reach `param` and `disp`, and that the
aux button publishes.

---

## Phase 3 — the audio gate, which does not have to wait for `e_chop`

`plan-v04.md` says an audio gate *"becomes worth building the moment `e_chop` exists."* **Half of
that is closeable now.**

The audio path today is a straight stereo passthrough with two level taps — a handful of `#X connect`
lines at the end of `u_root.pd` — and **nothing asserts it**. A broken rewiring there is silent and
would surface as no sound at a venue.

A headless gate can drive the stub's oscillators into the input sends, write a soundfile, and assert
three things:

1. **The output is not silent.**
2. **L and R are not swapped** — the TRS Y-cable makes L drums and R fx, and `adc~ 1` is the tip
   (item 11).
3. **The passthrough is unity**, not attenuated.

**This is the first signal-domain gate in the project**, which makes the second one — the real one,
when `e_chop` lands — a small addition rather than a new kind of thing.

⚠️ **Strike `Gate: none` in all five places it is written**: [ref/module/audio.md](ref/module/audio.md)'s
header and its `Open` section, [plan-v04.md](plan-v04.md), [CLAUDE.md](CLAUDE.md), and
[test/README.md](test/README.md). ⛔ **Otherwise [plan-v03.2.md](plan-v03.2.md)'s dedupe pass has
nothing to converge on.**

**What stays open is output-side metering**, which genuinely needs stages to exist. Say so.

---

## Phase 4 — the pickup gate ✅ LANDED 2026-08-08, ahead of this plan

**It was built with the feature rather than after it**, because the pickup bugs were being found on
hardware faster than a later gate could have caught them. `test/gate/map-assert.py` carries it —
a `parameter pickup` section, and ⛔ **the whole drive runs TWICE**, the two scratch copies differing
only in whether `knobs.txt` exists, so each branch tests its own half.

What it asserts, and all of it was made to fail: a restored value is published; a control moving
**away** from the target changes nothing; **passing through** it takes authority; it tracks normally
afterwards; state is **per knob**; a button never picks up; an unmapped knob draws no held row
(item 240); a target on a rail still releases (item 241); and ⚠️ **the restore itself still works** —
item 234's symptom was the instrument coming up at `u_tempo`'s own 120 instead of the saved tempo,
and **the restore working is precisely what creates the desync pickup solves.**

**Nothing is owed here.** Left in place because the reasoning for *why* the gate is shaped this way
is worth reading before touching it.

---

## Phase 5 — the `.sh` scripts, honestly declared

Four shell scripts ship inside the patch folder and **none is ever executed by a test**:

| Script | Today |
|---|---|
| `Cut It/wire.sh` | **Statically parsed only.** `docs-check.py` reads its connect/disconnect lines against two anchored tables. Never run |
| `Cut It/state-dir.sh` | **Untested.** The gates *work around* it by hand-creating the two state files |
| `Cut It/logroll.sh` | **Untested** |
| `Cut It/phone-ip.sh` | **Zero references anywhere under `test/`** |

⚠️ **They cannot be tested on the Mac**, because `[shell]` is a do-nothing stub there. **Do not invent
a fake pass.** Either add a bench step that runs each on the device and reads its output, or state
`Gate: none` for them on [ref/module/boot.md](ref/module/boot.md) **as honestly as
[ref/module/audio.md](ref/module/audio.md) did** — and say which. An untested script that nobody has
declared untested is the worse of the two.

---

## Verification

```sh
./test/run.sh                              # its check count must go UP, and be watched going up
python3 test/gate/docs-check.py -v
```

- ⛔ **Every new gate is made to fail before it is trusted.** Break the thing it covers, watch it go
  red, put it back. **A gate that has only ever passed has not been tested.**
- ⚠️ **A measuring rig is code and gets the same scrutiny.** Phase 5 had two bugs in its own probes,
  Phase 6's bench had an assertion nothing ever drove, and `state-assert.sh` once passed a broken
  patch 15 out of 15.
- **Each module page's `Gate:` line names its new gate**, and the path must exist or the doc gate
  fails.
- **Counts must be exact, never "at least".**

---

## Done means

1. `m_nano`, `u_err`, `g_led`, `c_clock`, `u_init`, `g_oled` and `m_organelle` each have a gate whose
   whole subject is that module, named on its page.
2. The three existing-gate defects are fixed, each with a can-it-fail run.
3. The audio passthrough gate exists and `Gate: none` is struck in all five places.
4. Pickup has a gate.
5. The four shell scripts are either covered or **declared uncovered on a page**.
6. [test/README.md](test/README.md) and [CLAUDE.md](CLAUDE.md) state the real gate count, and
   [CLAUDE.md](CLAUDE.md) no longer says `module/audio` is the only page declaring `Gate: none`.
7. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.** Output-side metering is the one thing
that legitimately stays, because it needs DSP stages that do not exist.

⛔ **Leave every change in the working tree.** Brendan commits his own work.
