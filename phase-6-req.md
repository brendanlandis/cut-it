# Cut It — Phase 6 (Launchpad) — planning brief

You are picking up a Pure Data instrument project mid-build. **Your job this session is to
produce a Phase 6 plan and get it agreed. Do not write any Pd until Brendan has signed off on
the plan.**

Working directory: `/Users/brendan/Sites/cut-it`

---

## Rules that override everything

- **Never touch git.** Read-only, always. No `commit`, `add`, `stash`, `checkout`, `reset`,
  `branch`, and do not offer to. This holds even if a plan document lists commits as steps —
  the plan files predate the rule. Brendan commits his own work. `git log` / `show` / `diff`
  for reading are fine.
- **The Pd target is 0.49 vanilla, permanently.** The device can never be upgraded. Verify any
  object you are not certain about against the local 0.49 binary before putting it in a plan.
- **Never open or save an Organelle-bound patch in plugdata.** It rewrites the file format and
  0.49 cannot parse the result.
- **Vanilla only.** No ELSE, no cyclone.
- Brendan prefers terse answers. Skip preamble.

---

## Read these, in this order, to these depths

**Thoroughly — these are the rulebook and the state of the world:**

1. `CLAUDE.md` — hard constraints, repo layout, the doc-hygiene rules (`ref-` states what is,
   `plan-` states what's open). Short.
2. `ref-conventions.md` — the whole file. Naming, `$0`, the global-name allowlist, `[trigger]`
   discipline, the three `route` traps, the display-bus ownership rule, banned constructs, the
   dev workflow and the by-hand console. **This is the file Phase 6 is most likely to need
   amended**, so know it before you propose an amendment.
3. `plan-v02.md` — the whole file, but especially *Architecture*, *Phase 6*, and *Open
   questions*. It is short and it is where your finished plan's leftovers must land.
4. `ref-build-log.md` — the whole file, and **read it for the corrections specifically**. Most
   were found by measuring something a plan asserted. Several will bite Phase 6 directly.

**Sections only:**

5. `ref-midi.md` — read *Novation Launchpad Pro MK3* thoroughly (transmit map, Programmer Mode
   layout, both lighting paths, the mode-control SysEx table, the three gotchas). Read *The
   addressing model* thoroughly. Skim the SP-404, nanoKONTROL and Volca sections — know they
   exist, don't study them.
6. `ref-display.md` — read *The display framework* thoroughly (this is `g_oled`, the arbiter
   whose shape `g_grid` is meant to copy), plus *No text on the Launchpad* and *The aux button
   LED*. Skim the OLED graphics API and PdParty sections.
7. `ref-software.md` — read *Launchpad — three tiers, and you only build the top one*, *Grid
   idioms worth stealing*, *Division of labour*, and *Compose time and perform time are
   separate modes*. Skim the timing sections — that work is done.
8. `ref-hardware.md` — read *Booting with the Launchpad attached*, *Launchpad Pro MK3 — a
   genuine blank slate*, *The device itself*, and *Measuring the running patch*. Skim audio
   flow, power and cabling.
9. `tools/README.md` — thoroughly. It is short, and `lp-monitor.pd`, `lp-modes.pd` and
   `lp-flicker.pd` are working references for everything Phase 6 needs to drive.

**Do not read in full — 1,051 lines:**

10. `plan-tests.md` — read the numbering warning at the top, **Session 2 (items 6–10)** which is
    the Launchpad's proving session, **Session 3b** (why the Launchpad wedged the boot), and
    **items 5, 39, 77 and 81**. Grep it for anything else you need. It is the evidence archive,
    not a narrative.

**Read the code that Phase 6 extends or copies:**

- `Cut It/g_oled.pd` — the arbiter you are asked to reproduce for 64 pads.
- `Cut It/g_led.pd` — the smallest possible display owner; read it first, it is the pattern in
  miniature.
- `Cut It/m_nano.pd` — the shape every `m_` layer follows.
- `Cut It/u_init.pd` — specifically `pd launchpad-init` and `pd safe-exit`. **Phase 6 lifts
  `launchpad-init` wholesale into `m_launchpad`**, and safe-exit's return-to-Live-mode is
  load-bearing.
- `Cut It/u_map.pd` — the only file that says what a control means. Phase 6 adds branches here,
  not elsewhere.

---

## What Phase 6 is

`m_launchpad` and `g_grid`. From `plan-v02.md`:

> Pad input on Pd channel 1 with `r*10+c` decode and polyphonic aftertouch. `g_grid` is the same
> arbiter shape as `g_oled` — playhead, slot state, mode and meters all contend for 64 pads.
> Batch LED updates: one SysEx can carry up to 106 colour specs. Flash and pulse are synced to
> MIDI beat clock, so animation follows `u_tempo` for free. **This is also where `mode` finally
> gets a driver.**
>
> **Done when:** pads report position, velocity and pressure; the grid shows mode state; a full
> repaint is one message.

Treat that as the spec and the `plan-v02.md` text as authoritative over this summary.

---

## Things the plan must decide, and should ask Brendan about

Raise these **before** finalising, not after. Each changes the shape of the work.

1. **Does `g_grid` ride the `disp` bus, or get its own?** `ref-conventions.md` records that a
   second display surface cost one `route` argument in `g_oled`, and says explicitly it is
   "worth knowing before adding a third." **Phase 6 is the third.** Adding a bus is a deliberate
   edit to the allowlist in `ref-conventions.md`; so is not adding one. Decide it on purpose.
2. **What actually drives `mode`, and what are the modes?** The bus has had no writer since
   Phase 4 and degrades safely today. Phase 6 is where it gets one. Which pad or button, and
   does the grid show mode as colour, as a lit row, or both?
3. **What does the grid show in v0.2, given there is no musical DSP yet?** There are no sample
   slots, no patterns and no playhead to display. The arbiter may need a deliberately thin set
   of real layers plus a test layer, or the phase risks building an arbiter with nothing to
   arbitrate.
4. **Is `c_clock` instantiated for the first time here?** There are still no instances anywhere
   in the deployed patch. A beat-driven grid animation would be the first consumer. If so, say
   so — it is a real milestone and it needs a `c_clock` verification step.
5. **Repaint budget.** See the CPU warning below — this may need a decision about repaint rate
   before any code exists.

---

## Traps that will bite this specific phase

All of these are recorded, all cost time before:

- **`polytouchin` emits note before value.** Wiring it straight to `[noteout]` lights a pad with
  the *previous* event's pressure.
- **A reject / left / non-matching outlet carries DATA, not a bang.** Three separate instances in
  this repo's history. Anything behind one that expects a bang needs `[t b]` in front.
- **LED state survives a mode switch.** Entering Programmer Mode does not blank the grid; the
  clear is not optional.
- **`loadbang` fires before ALSA connections exist.** Init SysEx sent at `loadbang` goes nowhere.
- **Programmer Mode locks out the Launchpad's Settings menu** until Pd sends a SysEx selecting
  another layout. If Pd dies mid-set that is a power cycle. `u_init`'s safe exit handles this and
  must keep handling it after the lift.
- **`[random]` takes a bang, not a float.** At grid-refresh rates a float produced 2,500
  errors/second.
- **A `[print]` at `loadbang` breaks `deploy.sh`,** which gates on output. Put diagnostics behind
  `[del 2000]`.
- **A comma or semicolon in a message box is a message separator.**
- **Inserting boxes mid-list in a `.pd` file shifts every later index** and silently rewires
  `#X connect`. Append at the end, and honour `#N canvas` / `#X restore` nesting — top-level
  objects go before the first connect *at depth 1*.
- **Use `./deploy.sh --clean`** if anything is renamed or deleted. There is no rsync on the
  device and a stale `.pd` will shadow the new one.
- ⚠️ **CPU is the live risk.** The deployed patch idles at **10.2 %** — Phase 5's clock roughly
  doubled it, and the candidate is ~96 ALSA MIDI writes a second, not DSP. A grid that repaints
  frequently adds to exactly that cost. **The plan should state a repaint budget and a way to
  measure it**, using `ref-hardware.md` → *Measuring the running patch*. "One SysEx per repaint"
  is the phase's own mitigation; treat it as a requirement, not an optimisation.

---

## Prerequisites to check before planning around hardware

- ⚠️ **The Launchpad has not been attached alongside the other controllers.** Phase 5's device
  run reported only 3 ALSA connections — nano in, 404 in and out — because of a cable shortage.
  **Ask Brendan whether the Launchpad can actually be plugged in**, and whether the full rig
  (three controllers plus the wifi dongle) can be powered at once. That is `plan-tests.md` item 5
  and it has never been tested. A marginal hub presents as intermittent dropouts, not an obvious
  failure, so **if Phase 6 produces flaky behaviour, suspect the hub before the code.**
- **The Launchpad's perimeter CC numbers are 📄 documented but never confirmed on this unit.**
  Ten minutes with `tools/lp-monitor.pd`. If the plan uses any perimeter button, confirming these
  is a Step 0 measurement, not an assumption.
- **The animation tempo range is ⬜ unpinned.** Flash and pulse *do* track a swept tempo, but past
  an upper and lower limit they revert to a default rate. Only matters if animation must stay
  locked at extreme tempi. Item 77.

---

## How to shape the plan

Follow the shape the last five phases used — `ref-build-log.md` shows what landed and
`plan-v02.md` shows the level of detail expected.

- **A "Decisions taken with Brendan" table** up front, with the consequence of each.
- **A Step 0 of measurements** — anything the rest of the plan depends on that is currently 📄 or
  ⬜. Measure it before anything is built on it. Every phase so far has had at least one
  assumption turn out wrong here.
- **Numbered build steps**, each ending with both gates before the next begins:

  ```sh
  python3 tools/pd-layout-check.py "Cut It"/*.pd
  /Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio \
      -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"     # silence == pass
  ```

- **A `tools/phase6-bench.pd`**, matching `phase5-bench.pd`: self-driving, ten seconds a step,
  a printed `PASS IF` before every step *including the ones whose correct result is that nothing
  happens*. Note honestly which steps need hands on hardware — a bench proves the cases it
  contains and nothing else. Two of Phase 5's worst bugs were invisible to a bench that passed.
- **A verification section** separating what can be measured on the Mac from what genuinely needs
  the device.
- **A landing checklist** — which docs get edited when the phase is done. The conventions:
  finished work moves to `ref-build-log.md`; the Phase 6 section *leaves* `plan-v02.md` rather
  than being annotated; superseded designs get replaced, not annotated beside their replacement;
  anything unresolved moves to *Open questions*; a new `plan-tests.md` session is added with
  items **numbered from 82** (81 is the last used, and numbers are cited by bare number across
  files, so **never reuse one**).
- **The final step of the phase is handing Brendan a test procedure for both machines** — a
  procedure, not a summary, with the expected result stated *before* each action. Copy the shape
  of `plan-tests.md` → *The Phase 5 procedure, in order*. It goes into `plan-tests.md` **and**
  into chat, because chat is where it gets used.

---

## How the work actually gets done

- **Off-device is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the whole
  instrument is there — `u_mother-stub` draws the front panel inline. ⚠️ **But the Launchpad is
  real hardware with no stub**, so more of Phase 6 needs the device than any phase so far. Say in
  the plan which parts those are.
- **There IS a console** — launch `mother.pd` and `main.pd` together over SSH and tap any bus
  with `[print]` from a third patch. See `ref-conventions.md` → *There IS a console*. This is the
  highest-value debugging tool on the project.
- `./deploy.sh` does check → scp → reload → load in one command.
- **Assume nothing reports itself unless the patch reports it**, and treat a measuring rig as
  code — Phase 5 had two bugs in its own probes, one of which produced a confident wrong answer
  about the clock.

Start by reading. Then ask Brendan the open design questions above. Then write the plan.
