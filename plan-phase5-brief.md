# Phase 5 brief — for a fresh agent

Paste this whole file as your first message to a new agent working in `/Users/brendan/Sites/cut-it`.
Delete it when Phase 5 lands.

---

You are picking up **Phase 5 of "Cut It"**, a cut-up / harsh-noise instrument patch in Pure Data for
the original Critter & Guitari Organelle. Phases 0–4 are built and verified on hardware. Phase 5 is
**clock and transport**.

## Read this first, before anything else

**Never touch git.** Read-only, always. Do not `commit`, `add`, `stash`, `checkout`, `reset` or
`branch`, and do not offer to. This holds even if a plan document lists commits as steps — the plan
files are older than this rule. Brendan commits his own work. `git log` / `git show` / `git diff` for
reading are fine.

**The Pd target is 0.49 vanilla, permanently.** The device runs `Pd-0.49.0` on Organelle OS 4.0, and
**that hardware cannot be upgraded** — 4.1+ are all Organelle M/S/S2. Do not use any object newer
than 0.49. Verify against the local binary rather than trusting your memory of when something landed:

```sh
ls /Applications/Pd-0.49-1.app/Contents/Resources/doc/5.reference/ | grep '^objectname'
strings /Applications/Pd-0.49-1.app/Contents/Resources/bin/pd | grep -x objectname
```

**Never open or save an Organelle-bound patch in plugdata.** It rewrites `.pd` files into a 0.55+
format that Pd 0.49 cannot parse. This has already happened once in this repo.

**Vanilla only.** No ELSE, no cyclone. Pure-Pd abstractions in the patch folder are fine.

## What to read, and how closely

Depth matters here — the docs total ~4,000 lines and reading all of it closely is a waste, but three
of them are load-bearing.

**Read in full:**

| File | Why |
|---|---|
| `CLAUDE.md` | The hard constraints and the repo layout. Short. |
| `ref-conventions.md` | **The most important file.** `$0` discipline, the global-name allowlist, `[trigger]` on every fan-out, the three `route` traps, the banned-constructs list. These are decisions, not suggestions, and most of them exist because breaking them cost real debugging time. |
| `plan-v02.md` — *Phase 5* and *Open questions* | Phase 5 is specified there in detail. That specification is what you are executing. |
| `tools/README.md` | What each diagnostic patch proves and how to run one. |

**Read closely, but only the named sections:**

| File | Sections |
|---|---|
| `ref-build-log.md` | **Phases 3 and 4** — that is the code you are extending. Then *What every phase had in common*. Skim Phases 0–2. |
| `ref-software.md` | *Timing and tempo*, and *Deriving grain timing from a 24 PPQN clock*. These are the design reasoning behind Phase 5. Skim the rest. |
| `ref-midi.md` | *The addressing model*, *MIDI out from Pd*, *Roland SP-404MKII*. Skim Launchpad and Volca. |
| `ref-display.md` | *The aux button LED*, *The display framework*, *Seeing it off-device*. Skim the rest. |
| `ref-hardware.md` | *The device itself*, *Signal flow — MIDI*. Skim the rest. |
| `plan-tests.md` | Skim for the method, then read **Sessions 4b, 4c and 4d closely** — they are the model for how work gets verified in this project, and item 47 is the aux LED. |

**Don't read** `! v0.1 plans/` unless you are chasing musical intent. It predates every convention
here; treat it as reference for *what was wanted*, never as code to lift.

**Patches** — read `Cut It/u_root.pd`, `u_init.pd`, `m_nano.pd` and `u_level.pd` in full; they are the
house style and `u_root.pd` is where your new abstractions get instantiated. Read
`tools/phase4-bench.pd` for the acceptance-bench idiom you will copy. **Skim `Cut It/g_oled.pd`** — it
is 36 KB, verified on hardware, and Phase 5 has no reason to change it.

## How work is done here

**Off-device is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the whole
instrument is there — `u_mother-stub` draws the Organelle's front panel inline and previews everything
the patch writes to the OLED. Reach for the hardware only when the thing you are testing *is* the
hardware.

**After every single patch edit, both of these:**

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio \
    -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"     # silence == pass
```

Any output at all from the second command is a failure — `deploy.sh` refuses to deploy on it, because
**Pd exits 0 even when objects fail to create**, so output is the only usable gate.

**`./deploy.sh`** does syntax check → scp → reload → load with no physical interaction. If
`organelle.local` does not resolve from your shell, use `HOST=root@192.168.1.15`. Password is
`organelle`.

**There is a real console** — launch the patch by hand over SSH with `mother.pd`, `main.pd` and a
throwaway diag patch, output redirected to a file. `ref-conventions.md`, *There IS a console*. This is
the highest-value debugging tool in the project.

**`./tools/fetch-errors.sh`** reads the persistent error log back off the device.

## Traps that have already cost this project time

Every one of these is a real bug that happened. They will recur.

- **A reject / left / non-matching outlet carries DATA, not a bang.** Three separate instances in
  Phase 4 alone — `select`'s reject emits the value it didn't match, `moses`'s left outlet the value
  below the split, `text search` returns `-1`. Anything behind such an outlet that expects a bang
  needs a `[t b]` in front of it.
- **A `[print]` at `loadbang` breaks `deploy.sh`.** Put diagnostics behind `[del 2000]`; the syntax
  check quits at load and never sees them, while the by-hand console still does.
- **Inserting a box mid-file shifts every later index** and silently rewires `#X connect`. Append at
  the end. Comment-only text substitution inside an existing `#X text` line is safe.
- **A comma or semicolon in a message box is a message separator.** It splits the message and the
  remainder lands somewhere unhelpful.
- **`[list trim]` before sending an assembled message**, and **`[list append]` after a `route`** —
  `route` matches a *selector*, and its remainder arrives as a selector whenever the first atom is a
  symbol.
- **`[list split n]` on exactly *n* atoms never fires its right outlet.** Silent non-event.
- **`text get` errors and prints** if you request more fields than a line holds.
- **`gShowInfoBar` must go out on every OLED redraw**, not once at load — mother restores the info bar
  after every patch load.
- **On the Mac, signal objects do nothing until DSP is on.** Phase 5 is full of `phasor~` and
  `threshold~`, so an unchecked *Compute Audio* looks exactly like a broken patch.

## Where results go

- **A fact goes in a `ref-` file.** Mark it ✅ verified on this hardware / 📄 manufacturer docs /
  ⬜ unknown. Never write "we should…" in a `ref-` file.
- **Evidence goes in `plan-tests.md`** as a new session, with unique item numbers — other files cite
  items by bare number, so never reuse one.
- **Anything still open goes in `plan-v02.md`** under *Open questions*.
- **When Phase 5 lands, its section moves out of `plan-v02.md` into `ref-build-log.md`** as an
  outcome. Replace superseded designs rather than annotating them; Phase 4 annotated and the plan
  ended up holding three designs at once.

## Two habits this project runs on

**Measure, don't infer.** Several claims in this repo's history turned out wrong when checked against
the device — the MIDI channel block, `enc`'s polarity, `/loadPatch`'s argument, `route`'s remainder
rule, `pgrep`'s substring matching. When a fact matters, check it against the hardware or the source.
`ref-build-log.md` lists all of them; it is the best single argument for this habit.

**Nothing reports itself unless the patch reports it.** The device runs Pd with `-nogui` and errors go
to a tty you cannot see. Anything that can fail should say so on the `err` bus.

## Finally

Phase 5's last step is **Step 5: hand Brendan a detailed test procedure for both machines** — Mac
steps first with one cable move, expected result stated before each action, including the steps whose
correct result is that nothing happens. Do not skip it and do not reduce it to a summary of what you
built. Phase 4's equivalent is in `plan-tests.md` under *The procedure, in order*; copy that shape.
