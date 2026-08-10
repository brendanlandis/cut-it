---
name: gate
description: Building or changing a test for Cut It — a headless gate, a hardware bench, or a measurement on the device. Carries the scratch-copy and stub-rewrite pattern, why counts must be exact rather than non-zero, the ways a gate passes vacuously, and the rule that a gate is not trusted until it has been made to fail. Use before writing anything under test/.
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

Every one of these has happened here, and the first three were all in one gate — the phase 6 grid
gate, since split into `display-assert` and `launchpad-assert`.

**1. It rewrote the wrong thing.** It rewrote `[midiout]` only. `m_volca` and `m_404` emit through
`noteout` / `ctlout` / `pgmout`, so it found nothing in them and every assertion about them would
have passed silently.

**2. Its regex was anchored so arguments were skipped.** `'^#X obj [0-9]* [0-9]* midiout;$'` requires
the class name to end the line, so `[ctlout 123]` is invisible to it — and measured on this patch,
that regex finds **one** `ctlout` where there are **two**.

**3. It asserted non-zero instead of exact.** Its comment claimed five `[midiout]` where the patch
has six. **The count drifted and nothing noticed**, because "not zero" cannot notice. There is one
`MIDI_EXPECT` now, in `test/gate/lib-scratch.sh`, and every gate that makes a scratch copy enforces
all of it:

```sh
MIDI_EXPECT="midiout:6 noteout:2 ctlout:2 pgmout:1 notein:2 ctlin:3"
```

A lower count means assertions have gone vacuous; a higher one means a new emitter the gate does not
know about. `test/gate/midi-emitters-assert.sh` asserts it on its own without Pd, so the claim has an
owner that belongs to no device. Update it deliberately, never to make a red run green.

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

Stubs live in `test/stubs/`. Each must match its real object's inlet arity and cold-inlet
semantics, and must tolerate creation arguments.

⚠️ **A bus is not enough stimulus.** Anything behind `[notein]` / `[ctlin]` has no bus in front of
it, so a receive path goes untested. Rewrite the **inputs** too: `t_notein` is `[r t-notein]` →
`[unpack f f f]` with outlets wired 2→2, 1→1, 0→0, so it emits channel, velocity, pitch — the order
`notein` documents. `t_ctlin` is the same shape for channel, controller, value.

⚠️ **`t-notein` and `t-ctlin` are bare global names outside the allowlist, and that is fine** — they
exist only in the scratch copy. State it, so nobody "fixes" it.

⚠️ **One receive name reaches every rewritten box of its class.** All three `[ctlin]` become
`[t_ctlin]`, so a driver aimed at the nano's channel block is also offered to `m_404` and
`m_launchpad`. That is not a leak to work around — it makes **cross-talk between the three channel
gates something a gate can assert** rather than assume.

## `-noaudio` does not turn DSP off

⚠️ **It disables the audio DEVICE, not the graph.** Pd falls back to its internal scheduler and
`phasor~`, `threshold~` and `writesf~` all keep working. Two gates carried comments asserting the
reverse — *"NO -noaudio, the subject is a signal"* and *"without DSP nothing ticks and every count
comes back 0"* — and both produced **byte-identical output** with and without it, peaks and counts
included. Item 280, measured both ways.

**Pass it.** A gate that opens a Mac audio device it has no use for is slower and can collide with
whatever else is using the interface. ⛔ **But do not read this as "DSP is free"** — the suite still
takes ~5 minutes because the graph runs in REAL TIME, and that is what a `phasor~` clock needs. A
faster machine will not help.

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

⛔ **TIME THE WINDOWS FROM BEHAVIOUR, NOT FROM THE IMPLEMENTATION.** The old map gate had 23 green
checks and missed a boot-time race, because its windows started at 2400 ms *for the reason the code
read its table at 2000*. **A test whose schedule is derived from the implementation cannot falsify
it**, and item 234 was found by hardware instead. Every driver in `test/gate/` now opens a window
**before** the thing it is assuming — `map-assert` at 300 ms, `sp404-assert` at 300 and 700 in both
directions, `display-assert` at 300 with a mode nothing else in the run sets.

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

The strongest half of `map-assert` is a **static lint**: it reads `u_map`'s literal `route` box
and the map's rows and proves every destination a row can name exists on that route. No Pd, no
timing, ~200 ms, and it enforces the allowlist guard by reading.

`docs-check.py` is the same idea — the fact exists twice in machine-readable form, so parse both and
compare. **Reach for that before reaching for a driver.**

## Benches

Hands-on hardware steps, and they are **generated**:

```sh
python3 test/bench/bench-gen.py        # from test/bench/bench_steps.py, run from the repo root
python3 test/bench/bench-verify.py     # re-extracts the text to prove it survived
```

⛔ **Never edit a bench `.pd` — it is an output.** Add `STEPS_<MODULE>` to `bench_steps.py` and a
`BENCHES` entry to `bench-gen.py`, keyed by the output filename. **That is the whole list** —
`bench-verify.py` derives its own from those keys, so a bench that can be generated is a bench that
gets verified. It used to carry a hand-typed tuple as well, and missing it meant a bench was
generated but never fidelity-checked.

Step text: no `,` `;` or `$`; every `pass_if` starts with `PASS IF:`; include the steps whose correct
result is that **nothing happens**.

⛔ **A `title` and a `pass_if` are rendered into Pd message boxes and a `need` / `do` / `watch` is
not**, so only the first two carry those restrictions — the rest take ordinary commas. Write short
sentences with capitals and full stops, joined by ` -- ` where a comma would normally go, and
**never end a sentence on a bare number**: Pd reads `40.` as the float 40 and the stop vanishes
(item 122, asserted since 2026-08-10).

⚠️ **On the device, `./test/run.sh --bench <name>` drives a bench** — it sends GO itself. The
encoder does not advance one, and netcat does not work on macOS.

## Running everything

```sh
./test/run.sh
```

⚠️ **Read the result; do not grep for it.** Exactly one line matches `RESULT:`, and the exit status
is trustworthy. `grep -E 'ALL|FAILED'` also matches the per-gate `--- FAILED:` lines — a broken
patch has been committed that way.

⚠️ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.
