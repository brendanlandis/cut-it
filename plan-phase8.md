# Phase 8 — state and presets (`u_state`)

The execution plan. [plan-v02.md](plan-v02.md) keeps the one-paragraph summary and **remains the
only home for open questions** — if something here turns into a question rather than a step, it
moves there.

**Done when:** control state survives Save → reload, and Save New produces a working variant in
the patch menu.

**This is the last phase of v0.2.** After it, the infrastructure is complete and v0.3's four
filter stages have a floor to stand on.

---

## What is already settled, and where

Do not re-derive any of this. It is measured, and most of it was read off the device rather than
inferred.

| | |
|---|---|
| [ref-conventions.md](ref-conventions.md) → *State and persistence* | The mechanism, the `/tmp/state` → `/tmp/patch` direction, the 0.5 s budget |
| [plan-v02.md](plan-v02.md) → *Phase 8* | ⚠️ The Save New `!` bug, already diagnosed |
| [ref-conventions.md](ref-conventions.md) → *How a phase runs* | The six-step shape every phase has used |
| [ref-build-log.md](ref-build-log.md) | Seven phases of corrections. **Read these before writing any Pd** |

**The mechanism in one paragraph.** The System menu's Save runs `save-patch.sh`, which sends OSC
`/saveState 1` to Pd — arriving as `[r saveState]` — then **sleeps 0.5 s** and does
`cp -r /tmp/state/* /tmp/patch`. On load the patch folder is copied to `/tmp/patch/`. So the patch
**writes to `/tmp/state/` and reads from `/tmp/patch/`**, and anything it writes rides along with
mother's own `knobs.txt` for free.

---

## The tension this phase has to resolve, and it is not plumbing

⚠️ **Restoring a control's value cannot move the physical control**, and on this rig the physical
position sometimes wins immediately.

- **Knob 1 is master tempo.** Cut It deliberately ships **without** `knobs.txt` so the physical
  knob position always wins — see [CLAUDE.md](CLAUDE.md). A saved tempo that is overridden a
  second after load is worse than not saving it.
- **`m_organelle` guards every knob with `[change -1]`**, so a knob that has not moved publishes
  nothing. Whether mother *streams* positions or only sends on movement is ⬜ unresolved (item 68),
  and the answer decides whether a restored value survives at all.
- **The nanoKONTROL's faders have the same problem and no guard** — a restored `slider-1` is a lie
  until somebody touches the fader.

**This is the classic parameter-pickup problem** and it is a design decision, not a bug to code
around. The plan must state which of these it does, and Brendan decides:

| Option | Consequence |
|---|---|
| **Save only what has no physical control** — mode, tempo, and anything `u_map` derives | Honest and small. Nothing can be contradicted by a knob. But it saves very little of what a performer would call "the sound" |
| **Save everything, restore everything** | Complete, and immediately wrong for any control whose physical position differs. On the Organelle the knobs will fight it |
| **Save everything, restore into a "pickup" state** | Correct in the way hardware synths solve it: the stored value is shown and used until the physical control passes through it. ⚠️ Real work, and it needs a per-control "has been touched" flag |

**Recommendation: start with the first**, and record the third in [plan-v02.md](plan-v02.md) as
v0.3 work. The Done-when says *control state survives Save → reload*; it does not say every
control.

---

## Step 0 — measurements, before anything is built on them

⚠️ **Every phase so far has had at least one Step 0 assumption turn out wrong**, and Phase 7's
overturned its central design decision. None of the following is verified on this device.

| | Measure | Why it matters |
|---|---|---|
| **S0-1** | **Does `[r saveState]` actually fire?** Put `[r saveState] → [print]` in a scratch patch, load it from the menu, and hit System → Save | The entire phase hangs off it. It is 📄 read from `save-patch.sh`, never seen arrive |
| **S0-2** | **Does `/tmp/state/` exist, or must the patch create it?** `save-patch.sh` copies `/tmp/state/*` — if the directory is absent the copy is a silent no-op | A `[text write]` to a non-existent directory fails silently in Pd |
| **S0-3** | **Is the 0.5 s budget real?** Time `save-patch.sh` and confirm the sleep. Then measure how long `[text write]` of a realistic file actually takes | The budget is the one hard constraint. If writing overruns it, the save is silently partial |
| **S0-4** | **What is Pd's cwd at save time**, and does a relative `[text write]` land where expected? | `/tmp/patch` is the cwd on the device — item 134 found that it does not exist until mother has loaded the patch once |
| **S0-5** | **Reproduce the Save New `!` bug** against a **deploy-loaded** patch, then against a **menu-selected** one | ⚠️ Already diagnosed in plan-v02, never reproduced. Decide then whether `deploy.sh` should repair `/tmp/curpatchname` |
| **S0-6** | **Does `[savestate]` work in a 0.49 abstraction?** Available is verified; *used* is not | It is the alternative to a text file for per-instance values, and would change the design |

---

## Build steps, each ending with both gates

Every step ends with these two before the next begins — no exceptions:

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio -nomidi \
    -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"     # silence == pass
```

**Step 1 — `Cut It/u_state.pd`.** Hooks `[r saveState]`, writes a plain-text file to
`/tmp/state/`, reads it from `/tmp/patch/` at load. `$0-` on every internal name; no global sends
outside the allowlist; `[trigger]` on every fan-out.

⚠️ **`saveState` is one of `mother.pd`'s reserved names** — [ref-conventions.md](ref-conventions.md)
lists it. `u_state` receives it; nothing sends it.

⚠️ **Every `[print]` behind `[del 2000]`.** `deploy.sh` gates on output.

**Step 2 — what gets saved.** Per the decision above. Whatever it is, it is written **once per
save**, not on a timer — the budget is 0.5 s and there is no reason to hold the file open.

**Step 3 — restore at load.** ⚠️ Ordering matters and `u_init` already owns startup order. A
restore that fires before the `m_` layers exist publishes into nothing; one that fires after
mother has pushed the knob positions is immediately overwritten. **Decide the stage and put it in
`u_init`'s sequence**, not in a `[del]` invented locally.

**Step 4 — hook into `u_root.pd`.** ⚠️ One appended object box, **before the connect block** —
`#X connect` indexes boxes by file position and inserting mid-list silently rewires every later
cord. `pd-layout-check.py` catches it. It bit four times in Phase 6 and once in Phase 7.

**Step 5 — the bench.** `tools/phase8-bench.pd`, generated by adding `STEPS8` to
`tools/bench_steps.py` and a `phase8` entry to `bench-gen.py`. **Never hand-edit a bench `.pd`.**
`bench-verify.py` must pass after every regeneration.

- ⚠️ **No commas or semicolons in step text** — a message box splits on them regardless of
  escaping, and `bench-gen.py` asserts against it.
- ⚠️ **A digit followed by a full stop becomes a float and the stop vanishes** — item 122.
  `bench-gen.py` warns rather than failing.
- ⚠️ **On the device GO is `./tools/go.sh`, never the encoder and never netcat.**

**Step 6 — a headless gate, if one is cheap.** Judge before building. Phase 7's was cheap because
`u_net` emits to a socket; Phase 6's needed a scratch copy. **`u_state` writes a FILE**, which is
the easiest of the three to assert on — a run that saves, reloads and diffs the file needs no
hardware at all. Probably worth it.

---

## Verification

**Mac first, then the device.** ⚠️ Phase 7 did it the other way round and the Mac run then found
two faults the device pass had gone straight past — including one that printed an error on every
boot. **The order exists for a reason.**

**Device pass:**

1. ⚠️ **Verify against a MENU-SELECTED patch, not a deploy-loaded one.** `deploy.sh` passes
   `!/Cut It`, which is what breaks Save New. This is the single most important instruction in the
   phase's verification.
2. Save → reload → confirm state survived.
3. Save New → confirm a working variant appears in the menu under the right name.
4. `tools/phase6-cpu.sh -n 3`. The Phase 7 baseline is **11.7 % / 122–126 UDP per second**;
   ⚠️ the script's printed 11.2 % budget is Phase 5's and stale.
5. ⚠️ **Check `ip addr show wlan0 | grep "inet "` before debugging anything network-shaped** —
   item 133. SSH answering is *not* evidence the network is up.

---

## The landing checklist

Not optional — [ref-conventions.md](ref-conventions.md), *How a phase runs*, step 6.

- Phase 8's section **leaves** [plan-v02.md](plan-v02.md).
- [ref-build-log.md](ref-build-log.md) gains Phase 8, **including every correction Step 0 produced**.
- A new [plan-tests.md](plan-tests.md) session, items numbered **after the last used number** —
  currently **134**. Numbers are cited bare across documents, so **never reuse one**.
- Superseded designs are **replaced, not annotated beside their replacement**.
- Anything unresolved moves to *Open questions* in [plan-v02.md](plan-v02.md).
- This file is deleted.

---

## Explicitly NOT in this phase

- **Pattern capture.** The `time, note, velocity, duration` event format is decided
  ([ref-software.md](ref-software.md)) but capture needs the mode system exercised first.
- **Parameter pickup**, unless the decision above chooses it.
- **The four filter stages.** v0.3.
