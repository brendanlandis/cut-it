---
name: gate
description: Building or changing a test for Cut It — a headless gate, a hardware bench, or a measurement on the device. Carries the scratch-copy and stub-rewrite pattern, why counts must be exact rather than non-zero, the ways a gate passes vacuously, and the rule that a gate is not trusted until it has been made to fail. Use before writing any phaseN-assert, docs-check or bench.
---

# Building a gate for Cut It

## The one rule

⛔ **A GATE IS NOT TRUSTED UNTIL IT HAS FAILED.** Reintroduce the bug, watch it go red, revert.

This is not caution. `state-assert.sh` **passed the broken patch 15/15** on its first can-it-fail
run, because the driver's timing did not reproduce the real ordering. `docs-check.py`'s first shape
check reported every table's last row as a header, because `set('')` is a subset of everything. Both
looked correct and green.

⚠️ **Budget for the gate failing to fail on the first try**, and reintroduce **more than one** bug —
a gate can be right about one fault and blind to another.

## The four ways a gate passes vacuously

Every one of these has happened here.

**1. It rewrites the wrong thing.** `phase6-assert.sh` rewrites `[midiout]` only. `m_volca` and
`m_404` emit through `noteout` / `ctlout` / `pgmout`, so phase 6's rewrite finds nothing in them and
every assertion about them would pass silently.

**2. Its regex is anchored so arguments are skipped.** `'^#X obj [0-9]* [0-9]* midiout;$'` requires
the class name to end the line, so `[ctlout 123 33]` is invisible to it.

**3. It asserts non-zero instead of exact.** `phase6-assert.sh` checks its rewrite count is not zero,
and its own comment claims five boxes where the patch has six. **The count drifted and nothing
noticed.** Assert an EXACT count per class:

```sh
EXPECT="noteout:2 ctlout:2 pgmout:1 notein:2"
```

A lower count means assertions have gone vacuous; a higher one means a new emitter the gate does not
know about. Update it deliberately, never silently.

**4. It stops seeing files.** `docs-check.py` globbed `ref/*.md`; when subdirectories appeared, seven
of nine pages stopped being checked **and the run still said ok**. Print the count of things checked
and watch it go **up**, never down.

## The shape of a headless gate

```
scratch-copy "Cut It/"  →  rewrite objects to printing stubs  →  drive it  →  assert in Python
```

⚠️ **`Cut It/` is never touched.** A built-in class has no side channel and Pd resolves the class
table before it looks for a file, so the only way to read back what a patch emitted is to swap the
object out in a copy.

Stubs live in `tools/test-stubs/`. Each must match its real object's inlet arity and cold-inlet
semantics, and must tolerate creation arguments.

⚠️ **A bus is not enough stimulus.** Anything behind `[notein]` / `[ctlin]` has no bus in front of
it, so a receive path goes untested. Rewrite the **inputs** too: `t_notein` is `[r t-notein]` →
`[unpack f f f]` with outlets wired 2→2, 1→1, 0→0, so it emits channel, velocity, pitch — the order
`notein` documents.

⚠️ **`t-notein` is a bare global name outside the allowlist, and that is fine** — it exists only in
the scratch copy. State it, so nobody "fixes" it.

## Three things that have cost real time

⛔ **OWN YOUR STATE DIRECTORY.** `main-dev.pd` passes `/tmp`, which every run on the machine shares.
A previous test that changed mode leaves it in that file, `u_init` restores it mid-run at ~3.5 s,
and every assertion keyed to another mode stops matching from that instant. That produced a **wrong
diagnosis** once — item 232: a driver firing seventeen pads 250 ms apart emitted exactly five, all
before ~3.5 s, and the same seventeen at 60 ms spacing emitted all seventeen. **Repoint the scratch
copy at a private directory and assert the repoint worked.**

⛔ **CHECK THE GENERATOR SUCCEEDED.** If a driver generator errors unchecked, the driver is never
written, Pd loads a file that does not exist, the `; pd quit` inside it never fires, and **the gate
hangs forever instead of failing.** A gate that hangs is worse than one that fails. Status-check it
and put a watchdog on every headless run.

⛔ **TIME THE WINDOWS FROM BEHAVIOUR, NOT FROM THE IMPLEMENTATION.** Phase 9's gate had 23 green
checks and missed a boot-time race, because its windows started at 2400 ms *for the reason the code
read its table at 2000*. **A test whose schedule is derived from the implementation cannot falsify
it.** Add a window that runs before the thing you are assuming.

⚠️ **`[del 0]` still defers to the next tick.** A burst fired in one logical instant proves
*drops-not-queues* and nothing about an interval. Test an interval with two events a real
millisecond or two apart.

## Two ways a measurement lies

⚠️ **A stepped sweep with short holds is structurally blind to an effect that takes seconds to
appear — and it reports a confident wrong number rather than nothing.** An automated rate sweep held
each step ~6 s and declared 500/s clean. A **hand** sweep on a knob, hunting around the transition,
found saturation at ~362. **The hand beat the script, and the script's failure was not a bug — it was
the shape of the test.**

⛔ **Concluding from a single SUCCESS is the same error as concluding from a single failure.** This
project forbids the second in writing, and the first still slipped through: one
satellite-fails-then-router-succeeds pair became "the satellite is broken", overturned thirty
minutes later by a controlled two-arm test.

⚠️ **Check which of two sources you are actually testing.** A starvation test aimed at `u_tempo`'s
clock was aimed at the smaller of the two emitters **by a factor of seven** — `g_grid` puts out
3320 bytes/s against the clock's 480. Nobody noticed until the arithmetic was done afterwards.

## Prefer the check that needs no Pd

The strongest half of `phase9-assert` is a **static lint**: it reads `u_map`'s literal `route` box
and the map's rows and proves every destination a row can name exists on that route. No Pd, no
timing, ~200 ms, and it enforces the allowlist guard by reading.

`docs-check.py` is the same idea — the fact exists twice in machine-readable form, so parse both and
compare. **Reach for that before reaching for a driver.**

## Benches

Hands-on hardware steps, and they are **generated**:

```sh
python3 tools/bench-gen.py        # from tools/bench_steps.py, run from the repo root
python3 tools/bench-verify.py     # re-extracts the text to prove it survived
```

⛔ **Never edit a bench `.pd` — it is an output.** Add `STEPS<N>` to `bench_steps.py`, a `PHASES`
entry to `bench-gen.py`, and **the phase number to `bench-verify.py`'s hardcoded tuple** — miss that
last one and the bench is generated but never fidelity-checked.

Step text: no `,` `;` or `$`; every `pass_if` starts with `PASS IF`; include the steps whose correct
result is that **nothing happens**.

⚠️ **On the device, `tools/go.sh` advances a bench.** The encoder does not, and netcat does not work
on macOS.

## Running everything

```sh
./tools/check-all.sh
```

⚠️ **Read the result; do not grep for it.** Exactly one line matches `RESULT:`, and the exit status
is trustworthy. `grep -E 'ALL|FAILED'` also matches the per-gate `--- FAILED:` lines — a broken
patch has been committed that way.

⚠️ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.
