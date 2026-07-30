# Cut It — Build Log

What has been built, phase by phase, and what each phase taught. **This file is history: every
claim here is settled.** Work still open lives in [plan-v02.md](plan-v02.md); the ordered hardware
checklist and its evidence live in [plan-tests.md](plan-tests.md).

It exists because the alternative was worse. Phases 0–4 accumulated their corrections *next to* the
plans they overruled, so the build plan grew into a document where the current design and three
superseded ones sat side by side. Finished work belongs somewhere that states outcomes.

**Read it for the corrections.** Nine of the fourteen below were found by measuring something the
plan had asserted, and several contradict what a reasonable person would infer from the
documentation. They are the most valuable thing in this file.

| Phase | | Built |
|---|---|---|
| 0 | ✅ | `main.pd`, `main-dev.pd`, `u_root`, `u_mother-stub`, `deploy.sh` |
| 1 | ✅ | audio chain, `u_level`, `g_levels` *(since replaced)* |
| 2 | ✅ | `u_init`, `wire.sh` |
| 3 | ✅ hardware | `g_oled`, `u_err` |
| 4 | ✅ hardware | `m_nano`, the persistent error log, the multi-parameter display |

---

## Phase 0 — Skeleton and the off-device shim

Two thin entry points with all content in `u_root` — that is what stops them drifting.
`main-dev.pd` instantiates `u_mother-stub`, the Mac-only stand-in for `mother.pd` and the **one
sanctioned exception** to the reserved-name rule; `main.pd` does not, so the device never sees it.
It has since grown into the full dev panel — see *Seeing it off-device* in
[ref-display.md](ref-display.md).

`deploy.sh` closes the loop: **syntax check → scp → reload → load**, no physical interaction. The
check is blocking and **gates on *output*, since Pd exits 0 even on load errors.**

**Two corrections, both read out of `/root/Organelle_UI/`:**

- `/loadPatch` resolves against the *current* patch directory, so the argument must be `!/Cut It`,
  not `Cut It`. A bare name loads nothing, silently.
- `enc` is `1`/`0` for up/down, **not `±1`** — as are `aux` and `encbut`.

## Phase 1 — Audio path

`[r~ inL]` / `[r~ inR]` straight through to `[throw~ outL]` / `[throw~ outR]`, with a `u_level` tap
on each input reporting onto the `disp` bus. Deliberately first: it proves the whole signal chain
with no DSP to blame. Two things Phase 3 depends on were established here — the `disp` bus, and the
rule that exactly one abstraction owns `oscOut` and `screenLine*`.

✅ Audio is audible, the volume knob controls it, and both OLED meters read the 18–19 noise floor at
rest. Covers [plan-tests.md](plan-tests.md) item 11 through the real patch.

**Three corrections, all read off the device:**

- **Not `adc~`/`dac~`.** `mother.pd` owns the sound card — see *Audio I/O* in
  [ref-conventions.md](ref-conventions.md).
- **Not `/oled/vumeter`.** mother already drives it, and it lives in the info bar, which is off by
  decision.
- **`gShowInfoBar 3 0` belongs here, not in startup**, because mother restores the info bar after
  every patch load, so it must go out on every redraw. That makes it the display's job.

## Phase 2 — Startup sequencing

`loadbang` fires before ALSA connections exist, so rather than scattering `[del]` objects one
abstraction owns the ordered startup: wire `aconnect` via `[shell]` → wait for ALSA → Launchpad into
Programmer Mode by SysEx → clear the grid, because **LED state survives mode switches**.

**Each stage reports to the OLED as it completes.** With no console that is the boot diagnostic — a
patch stuck at stage 3 tells you the Launchpad never answered.

**Also here: panic / safe exit.** `[r panic]` returns the Launchpad to Live mode, fired on
`quitting`, which `mother.pd` sends before waiting **100 ms**. Pd 0.49 has no `closebang`, so that is
the only shutdown hook there is. Without it, a crash in Programmer Mode means power-cycling the
Launchpad.

✅ Verified end to end: `[shell]` runs `wire.sh`, `aconnect -l` shows both directions wired, captured
pads read `r*10+c` with live velocity.

**The lesson here was hardware, not code.** The Launchpad would not configure behind three chained
USB hubs (`can't set config #1, error -32`), and the same topology wedged the wifi dongle at boot.
Plugged directly in, it works first time. Evidence in [ref-hardware.md](ref-hardware.md).

## Phase 3 — Display and errors

`g_oled` replaced `g_levels`: layers with priority and TTL — `home` < `param` < `modal` < `alert` —
sole owner of `oscOut` and `screenLine*`. Callers send semantics, never layout. Full geometry in
[ref-display.md](ref-display.md).

✅ **Verified on the Organelle**, all fourteen steps of `tools/phase3-bench.pd` — every layer, the
priority order, the mode filter and the 30 s safety TTL. Items 21–21c.

**Throughput is not a problem: 110 UDP datagrams a second at 8.2 % CPU**, load 0.16. That also
cleared the phase's biggest unknown — `packOSC` drops a mismatched typetag *before* `udpsend`, so a
full datagram rate proves the **runtime typetag builder produces tags the real `packOSC` accepts**,
which the Mac could never demonstrate having no `packOSC` at all.

**Errors follow the mode, not a severity guess:** compose is verbose, perform shows only failures.
This is why `err` carries a level. **The bus is unfiltered; only the screen is filtered**, so the
by-hand console sees warnings even in perform mode. Errors **time out** rather than waiting to be
dismissed — a stuck error covering the display mid-set is the worse failure.

**Three corrections:**

- **`u_err` does not draw.** The plan had it writing to the ALERT buffer, which contradicts *two
  writers, one screen*. It filters and forwards onto `disp`.
- **The alert draws to screen 3**, not the ALERT buffer. Nothing underneath needs preserving when
  the frame is rebuilt from state ten times a second. ✅ Buffer 4 has since been proven writable and
  switchable — and is deliberately still unused, because switching is edge-triggered where every
  layer is state-driven.
- **`route`'s remainder trap is wider than documented** — any remainder whose first atom is a symbol
  arrives as a selector, not just a lone symbol. And **`[list split n]` on exactly *n* atoms
  silently never fires its right outlet**, which is what would have made `grain 12` draw as
  `grain 12 %`.

⚠️ Deployed with `./deploy.sh --clean`, because there is no rsync on the device and a plain deploy
would have left the deleted `g_levels.pd` behind to shadow the new display.

## Phase 4 — nanoKONTROL, a persistent error log, a multi-parameter display

Three pieces, in a fixed order: **the error log first, so the other two were debuggable.**

**Why the log.** `u_err` prints every error, but the menu-launched patch sends stdout to tty1 — so in
normal operation an error draws on the OLED for 2–4 s and is then gone forever. Tolerable when the
only inputs were four knobs you were holding; not tolerable with 42 controls attached.

The design is a `[text]` accumulating in memory, flushed to `/sdcard/cut-it-err.cur` on a 2 s dirty
flag and capped at 200 lines, plus **one `[shell] sh logroll.sh` per patch load** that rolls the
previous session onto a durable log behind a `date`-stamped `BOOT` line. Three properties earned it:
one fork per load and **never per error**; a real wall clock without depending on `[shell]`'s return
path; and `deploy.sh`'s gate stays clean, because the check quits before the flush metro fires and
`[shell]` resolves to `mac-stubs/shell.pd` on the Mac. `tools/fetch-errors.sh` reads it back.

✅ **The log survives a power cycle**, which is the only real test of it — verified on the device,
both sessions present under their own `BOOT` lines. Under a plain `[text write]` design the first
session would have been erased by the second's first flush.

**Scope limit, stated honestly:** this captures errors the *patch raises*. Pd's own runtime errors
still go to tty1 and no vanilla 0.49 object can intercept them.

**`m_nano`** decodes CC into named parameters and nothing else — it knows nothing about what it
controls, which is the one boundary that is genuinely expensive to retrofit. The channel block is a
**creation argument**, because ✅ **Pd numbers MIDI channels by its own input SLOT, not by the
device's position in the system MIDI list**: `main.pd` passes 17, `main-dev.pd` passes 1. Names come
from `[makefilename slider-%d]` and friends — **placeholders, deliberately**, since there are no
parameters to name until v0.3, and generated names are honest about that in a way a lookup table
pretending to be a mapping would not be.

### The two design reversals

Both were decided by *using* the thing, and both are the current design — not amendments to it.

**The transport row is ordinary CC.** It was briefly a mode control, with LOOP toggling
compose/perform and PLAY/STOP driving the clock. The row is better spent on **scene selection**, so
all six now get momentary treatment like every other button: `xport-1`…`xport-6` on press, no
toggle, no transport meaning. CC 41–46 give `div 10` = 4, so it folded into the decode as a **fifth
kind** and deleted a whole subpatch.

Two consequences, both live: **nothing drives `mode`, `start` or `stop`** ([plan-v02.md](plan-v02.md)
tracks finding them a home); and the decode is now purely CC-number-based within the block, so
CC 41–49 read as `xport-1`…`xport-9` rather than warning. There is no bounds check on the units digit
anywhere — CC 0 has always read as `slider-0`.

**Display rows hold their positions.** The plan called for a most-recently-used list, newest first.
That was **wrong in the hand**: two faders moving together swapped places several times a second and
could not be read. A control already on screen is now updated **in place**, a new one is appended
below, and a **sixth is refused** rather than rotated in. The cost is honest — move nine faders and
you see the five you touched first, not the five most recent — and it is the right trade, because a
display you cannot read is worth nothing.

Type size still follows how many are moving (24px for one, 8px name over 16px value for two, 8px rows
for three to five). ✅ The two-mover case is a deliberate deviation from the plan's "two 16px lines":
16px fits about ten characters, so `slider-1 43` would clip to `slider-1 4` — a silent failure that
looks like a working display.

Side benefit: **the stale-unit trap is structurally impossible** in the new path, because each line
is stored whole rather than field by field.

### Four bugs, all found by measuring rather than reading

- **A reject / left / non-matching outlet carries DATA, not a bang.** Three separate instances.
  `[select 1 2 3 4 5 6]`'s reject emits `cc − 40`, which landed on an `[f]`'s *hot* inlet and
  overwrote the stored CC, so an unknown CC 47 reported itself as `cc-7`. Then `moses`'s left outlet
  carried the `-1` that `text search` returns for an unseen name, and `text size` passed the float
  straight through to `text set` as a line number: `line number (-1) < 0`, seventeen times in one
  run. **Anything behind such an outlet that expects a bang needs a `[t b]` in front of it.**
- **A `[print]` at `loadbang` breaks `deploy.sh`**, which gates on output rather than exit status.
  `m_nano`'s channel diagnostic sits behind `[del 2000]`: the check quits at load and never sees it,
  while the by-hand console still does. **Any new `[print]` in a deployed abstraction needs the same
  treatment.**
- **`pgrep pd` matches substrings** — on this device a kernel thread — so `fetch-errors.sh` reported
  pd running while it was killed. `pgrep -nx pd`.
- **An uninitialised awk variable is `""` as a subscript, not `0`**, which silently dropped every
  log line before the first `BOOT`. Fixed with `BEGIN { n = 0 }`.

### Two process lessons worth more than the code

- **Inserting a comment mid-list in a `.pd` file shifts every later box index** and silently rewires
  `#X connect`. Append at the end instead.
- **A comma in a message box is a message separator.** It splits the message and the remainder goes
  somewhere unhelpful.

✅ **The rewrite costs nothing measurable:** 117 UDP datagrams/second at 5.3 % CPU, in line with the
110/s Phase 3 measured for the simpler home frame.

Renamed in a commit of its own, with no behaviour change: the `disp` selector **`boot` → `status`**,
because the footer is shared between `u_init` and anything reporting persistent state.

---

## Phase 5 — Clock and transport

`u_tempo`, `c_clock`, `u_map`, `m_organelle`, `g_led`, and the `param` bus.

Master BPM, a 24 PPQN pulse cut from a `phasor~`, MIDI realtime out on two ports, the transport,
and the first mapping layer that can make a control *do* something. Before this phase `m_nano`
published only to `disp` — a display bus — so no control could drive anything at all.

**The construction, because it is not the obvious one.** BPM ÷ 60 × 24 drives a `phasor~`;
`[threshold~ 0.5 2 0.1 2]` gives one bang per ramp; every pulse emits 248 and increments a
counter whose `[mod 24]` = 0 *is* the beat. **Counting the pulses rather than running a second
oscillator makes the beat and the MIDI pulse the same clock by construction** — there is no
second thing to drift.

`c_clock` rebuilds the same construction off its own beat-rate phasor via `[*~ 24] → [wrap~]`,
and that is the alignment mechanism: a threshold at 0.5 of a *beat* phasor would fire half a beat
away from master. ✅ **Measured: master and a ratio-1 `c_clock` bang at bit-identical logical
times for a whole run — worst difference 0.000000 ms** — and ratio 1.5 gives exactly half again
as many beats. Item 49.

**Two buses, deliberately.** `param` carries a control that *changed*; `disp` a request to *show*
it. `m_nano` and the new `m_organelle` publish to both off one `[t a a]`, action first, report
second — duplicating the data where teaching `g_oled` to listen on `param` would not. Not
touching a hardware-verified display file won that trade.

**Tempo is the Organelle's knob 1, not the nano's knob 9** — a change of mind about the plan, and
a good one: the dev panel already sends `knob1`, so the entire clock is drivable on the Mac with
no MIDI configured at all. `m_organelle` is the new home for mother's own controls, replacing the
`m_keys` box in the architecture diagram; it is named for the device, like `m_nano`.

**Every controller-function designation now lives in `u_map`, and nowhere else** — explicit
`route` branches rather than a table, because a data-driven `[send]` could write any global name
with no evidence of it on the canvas. The aux toggle in it **holds no state of its own**: it
reads back `start`/`stop` from whoever caused them, so nothing can leave the button pressing the
wrong way.

### Six corrections, and one of them was the measuring rig

- **Pd 0.49 does not warn about extra creation arguments.** `[loadbang 7]` loads in silence, so
  the syntax check *cannot* answer whether `[midiout 3]` reaches port 3 — a silent creation
  proves nothing either way. The question stays ⬜ and `u_init`'s proven pattern is used instead:
  the port goes into the cold inlet at load. **The interesting part is that the obvious
  experiment was invalid**, not the answer.
- **A second display surface on `disp` costs one `route` argument in the first one.** `g_oled`
  treats everything it does not recognise as a parameter, so `led running` would have drawn as a
  nonsense parameter row. Two lines inside `pd disp-in`: `led` appended to the route, and the
  reject connection moved from outlet 6 to 7. Worth knowing before a third surface arrives.
- **The pulse counter resets to 23, not 0.** The next pulse adds one and lands on 0, which is the
  beat. Reset it to 0 and the first beat after every start is silently skipped — one beat, once,
  which is exactly the kind of thing nobody notices until a pattern is a bar out.
- **On the Mac the beat counters read 0 and the patch looks broken.** Nothing turns DSP on there;
  `mother.pd` does it on the device 200 ms after load. Predicted in the plan, and it still cost a
  confused minute when the first bench run printed three zeros. The bench now says so in the step
  that would show it.
- ⚠️ **The first measurement said the clock ran at double speed, and the clock was innocent.**
  The probe patch had a `[t b b]` with *both* outlets wired into one counter. **A measuring rig
  is code and gets the same scrutiny as the thing it measures** — the correct reading, 6 beats in
  3 s at 120 BPM, came out of fixing the probe, not the patch. `phase5-bench.pd` had a matching
  bug of its own: `[r $0-say]` was never connected to its `[print]`, so every step ran silently.

- **A bare `[change]` swallows a control parked at zero.** `m_organelle` guards each knob with
  `[change]`, because ⬜ it is not established whether `mother.pd` streams knob positions
  continuously or only on movement — a control that has not moved should say nothing either way,
  and must not pin four rows onto the display forever. But `[change]` starts life holding **0**,
  so `knob1 0` was filtered as "no change" and the tempo silently stayed at its 120 default
  instead of dropping to 60. It is `[change -1]` now, which is exactly what `u_level` has always
  used. **Found by driving the real chain, not by reading it** — the comment beside the object
  already cited `u_level`'s `change -1` as the precedent while the object itself omitted the -1.

---

## What every phase had in common

Worth stating once, because it is the pattern rather than a coincidence:

**Every phase's most valuable output was a correction to something the plan asserted.** The channel
block, `enc`'s polarity, `/loadPatch`'s argument, `route`'s remainder rule, `[list split n]`,
`pgrep`, `text get`'s field range, the reject-outlet rule, MRU ordering — none of these came from
reading documentation, and several contradict it. That is why
[plan-tests.md](plan-tests.md) marks every claim ✅ / 📄 / ⬜ and why *measure it on the device*
is the first working note in [CLAUDE.md](CLAUDE.md).
