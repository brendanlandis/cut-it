# Cut It — Build Log

What has been built, phase by phase, and what each phase taught. **This file is history: every
claim here is settled.** Work still open lives in [plan-v03.md](plan-v03.md); the ordered hardware
checklist and its evidence live in [plan-tests.md](plan-tests.md).

It exists because the alternative was worse. Phases 0–4 accumulated their corrections *next to* the
plans they overruled, so the build plan grew into a document where the current design and three
superseded ones sat side by side. Finished work belongs somewhere that states outcomes.

**Read it for the corrections.** Most of them were found by measuring something the plan had
asserted, several contradict what a reasonable person would infer from the documentation, and a
few were found only by a person putting hands on the hardware and doing what a performer would
do. They are the most valuable thing in this file.

| Phase | | Built |
|---|---|---|
| 0 | ✅ | `main.pd`, `main-dev.pd`, `u_root`, `u_mother-stub`, `deploy.sh` |
| 1 | ✅ | audio chain, `u_level`, `g_levels` *(since replaced)* |
| 2 | ✅ | `u_init`, `wire.sh` |
| 3 | ✅ hardware | `g_oled`, `u_err` |
| 4 | ✅ hardware | `m_nano`, the persistent error log, the multi-parameter display |
| 5 | ✅ hardware | `u_tempo`, `c_clock`, `u_map`, `m_organelle`, `g_led`, the `param` bus |
| 6 | ✅ hardware | `m_launchpad`, `g_grid`, the `mode` driver, the first `c_clock` instance |
| 7 | ✅ hardware | `u_net`, the per-name coalescer, the reconnect, the phone scene |
| 8 | ✅ hardware | `u_state`, `u_store`, the `state` bus, the two policies, `fetch-state.sh` |

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

**The transport row is ordinary CC.** It was briefly a mode control *inside `m_nano`*, with LOOP
toggling compose/perform and PLAY/STOP driving the clock — which put meaning in the one layer that
must not have any. All six get momentary treatment like every other button instead:
`xport-1`…`xport-6` on press, no toggle, no transport meaning. CC 41–46 give `div 10` = 4, so it
folded into the decode as a **fifth kind** and deleted a whole subpatch. The row was earmarked for
selecting between whole sets of behaviour — called *scenes* at the time, and **the same idea now
called `mode`**, which is what Phase 6 mapped it to in `u_map`.

Two consequences. **Nothing drove `mode`, `start` or `stop` when this landed** — Phase 5 gave
start/stop a home and Phase 6 gave `mode` one, both in `u_map` and neither in `m_nano`, which is
the point. And the decode is now purely CC-number-based within the block, so CC 41–49 read as
`xport-1`…`xport-9` rather than warning. There is no bounds check on the units digit anywhere —
CC 0 has always read as `slider-0`.

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

### Thirteen corrections — two of them in the measuring rig, and seven that only hands found

**The seven are the point of this list.** The out-of-range verdict, the pulse ceiling, the
late-created `c_clock`, the sticky `panic` footer, the nano/mother CC collision, `midiOutGate` and
the boot race were all invisible to a bench that passed. Each needed a person doing something a
test script had no reason to do: pressing the low button after the high one, asking for a wider
tempo range, opening the bench *after* the patch, or simply pressing aux and reading the screen.

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

- ⚠️ **THE CLOCK SILENTLY LOST PULSES ABOVE ~430 BPM**, and the cause is a Pd detail worth
  carrying forward: **`threshold~` decrements its debounce timer once per DSP *block*, not per
  millisecond.** The plan's `[threshold~ 0.5 2 0.1 2]` therefore burned a whole 1.45 ms block on
  every state change — 17 beats where 25 were due at 500 BPM. With both debounces at **0** the
  same test is exact, and the real limit is two blocks per pulse: **344 Hz, measured, which is
  44100 / 64 / 2 to the digit — 860 BPM.** A `phasor~` is monotonic and cannot bounce, so there
  was never anything for the debounce to protect against. ⚠️ **The original 20–300 BPM range hid
  this completely** — it surfaced only when the range was widened to 10–500 on request. A clamp
  can conceal a defect as easily as it prevents one.
- ⚠️ **The out-of-range warning filtered the verdict instead of the value.** `5000` warned; a `0`
  sent straight after it did not, because the out-of-range *flag* had never changed — so a second
  and quite opposite fault was silent. The `[change]` is on the **value** now: the same bad number
  twice stays quiet, a different one does not. **The bench could not have caught this**, since it
  only ever sent one out-of-range value. It took a person pressing the low button after the high
  one.

- ⚠️ **A `c_clock` created after startup did not run at all.** `u_tempo` publishes 120 on `tempo`
  exactly once at load and thereafter only stores what it hears — so an instance born later never
  heard a tempo and its phasor sat at 0 Hz. **Fixed in `c_clock`**, which now seeds itself with
  `[f 120]` banged at 300 ms: whatever has arrived, or 120 if nothing has. Fixing it in `u_tempo`
  by re-publishing would have put a second writer on a bus it also reads. Control-measured: **0
  beats without the seed, 12 with it.** **This only surfaced because the bench was opened by hand
  after the patch was already running** — every automated run loaded both from one command line,
  which hid it completely.

- ⚠️ **`status panic` was sticky and nothing cleared it** — found only on the device, and only by
  doing the thing a performer would do. After a panic you could press aux, watch the LED go green
  and the 404 start, and still be told `panic`. The footer is sticky by design and only a *tempo*
  message rewrote it. A start or a stop now bangs the stored BPM back out, so the footer always
  describes the state you are in. **The class of bug is "correct per the code, wrong for the
  user", and no bench step would have caught it** — the bench asserts what each step sends, not
  what the screen still says three steps later.

- ⚠️ **A nanoKONTROL button was toggling the transport, and it was `mother.pd` doing it.** ✅
  mother runs `[ctlin 21]`–`[ctlin 26]` **omni** and maps them to `knob1`–`knob4` and `aux`; the
  nano's top row is CC 21–29 by this project's own by-tens scheme. So `btn-t-5` pressed aux and
  `btn-t-1` slammed the tempo between 500 and 10 BPM. **Phase 5 is what made it dangerous** — the
  collision existed all through Phase 4 and did nothing visible, because aux meant nothing then.
  `u_init` now sends **`midiInGate 0`**, which mother's own comment documents and which gates only
  the MIDI-derived paths, leaving the front panel alone. mother also loads a different patch on any
  program change, which the 404 can send — the same gate closes that too.

- ⚠️ **Two more of mother's defaults had to be switched off, and both needed a delayed send.**
  `midiOutGate 0` as well as `midiInGate 0`: mother echoes the Organelle's keys as MIDI notes and
  its knobs as CC 21–24 to every port, so playing the keyboard lit Launchpad pads and would have
  triggered 404 pads. The design routes the keys to the Volca and nowhere else. **The mother binary
  pushes its own `1` to both gates about half a second after load**, so anything sent at `loadbang`
  is silently overwritten — the first version of this fix did nothing at all and looked deployed.
  Both are sent again at 2 s, verified on the device with an `[r midiInGate]` print.

- ⚠️ **The boot tempo was a race, and is now deterministic.** The patch started at the knob's
  position one day and at 120 the next, depending on whether mother's knob push beat `u_tempo`'s
  `del 200` seed. The seed now sits behind a spigot that any incoming `tempo` closes, so **120 is a
  fallback, not a default** — the same "seed only if unheard" shape `c_clock` needed.

- **A bare `[change]` swallows a control parked at zero.** `m_organelle` guards each knob with
  `[change]`, because ⬜ it is not established whether `mother.pd` streams knob positions
  continuously or only on movement — a control that has not moved should say nothing either way,
  and must not pin four rows onto the display forever. But `[change]` starts life holding **0**,
  so `knob1 0` was filtered as "no change" and the tempo silently stayed at its 120 default
  instead of dropping to 60. It is `[change -1]` now, which is exactly what `u_level` has always
  used. **Found by driving the real chain, not by reading it** — the comment beside the object
  already cited `u_level`'s `change -1` as the precedent while the object itself omitted the -1.

### And one measurement that contradicted the plan

⚠️ **The clock is not free.** ✅ Deployed and idle: **10.2 % CPU, 117 UDP datagrams/second**,
against Phase 4's 5.3 % and 117/s. The display costs exactly what it did; the clock roughly
**doubled** Pd's CPU. Two extra `c_clock` instances add only ~0.4 points on top, so it is **not**
the DSP — the remaining candidate is the 96 ALSA MIDI writes a second, ⬜ not confirmed by
isolation. The plan predicted "almost certainly free"; it was not. Still ample headroom at 10 % and
load 0.5, but v0.3 stacks four filter stages on this, so the baseline matters. Item 75.

---

## Phase 6 — the Launchpad and the grid

`m_launchpad`, `g_grid`, the `mode` bus finally getting a driver, and the first `c_clock`
instance in the deployed patch.

⚠️ **Verified on the Mac, not yet on the Organelle.** Nothing here has been deployed. The
Launchpad was plugged into the Mac for the whole phase, which is new for this project and is what
made an off-device build possible at all — `plan-tests.md` items 94–97 are what remain.

**Step 0 paid for itself immediately.** Six measurements before any code, and two of them
changed the design:

- **The documented ring map was wrong twice** — a whole second bottom row at **CC 1–8** that no
  documentation mentions, and **CC 90** at the top-left corner where the docs start at 91.
- ⚠️ **"A SysEx of 120 colour specs is rejected outright" — RECORDED AS MEASURED, AND FALSE.**
  It came from three broken probes: one addressed index 128, which is `0x80`, a status byte that
  cut its own SysEx short; one sent a bare count and painted zero specs, so an empty message read
  as a rejection; and one painted the second frame the same colour as the first, so a successful
  repaint was invisible. ✅ A clean 120-spec message paints the whole surface (items 105, 109).
  **`g_grid` now paints indices 1–108**, 108 specs, 332 bytes — not for the extra buttons but
  because LED state survives the Programmer Mode switch, so anything outside the span keeps
  whatever Live Mode drew there and no repaint can reach it.
- **The layout-select command does nothing on this unit**, so surface ownership keys off the
  proven Programmer/Live toggle instead of a layout table. Simpler than planned, and measured.

### The shape of it

**`m_launchpad` owns the Programmer/Live switch; `g_grid` owns the LEDs.** Different surfaces, one
writer each — which is the rule, and it is what let the 89-note clear loop be deleted outright:
**the first frame after ownership rises *is* the clear.** No second blanking step to keep in step
with anything.

**`g_grid` rides `disp` under one reserved selector, `grid`** — two lines in `g_oled`, exactly
what `led` cost in Phase 5. `mode` is read directly off its own bus, because one send from
`u_map` should reach every surface and let each decide what a mode looks like.

**One deliberate deviation from `g_oled`: `home` is a composite of regions.** Whole-surface
arbitration is right for a 128×64 screen and wrong for a grid, where the idiom is regions — so
the mode lamps and the beat row coexist in the layer that never expires, while `modal` and
`alert` still take everything. The cascade is unchanged.

**And one place it must NOT copy `g_oled`: the repaint is conditional.** The OLED redraws
unconditionally at 10 Hz because its frames are cheap local UDP. These are ALSA MIDI writes, and
~96 of those a second is the standing suspect for the clock doubling Pd's CPU in Phase 5. So the
frame clock runs at 10 Hz but only paints when a dirty flag is set: **nothing at all when idle,
~2 frames a second at 120 BPM.**

### Six corrections, and four of them were invisible to reading

- ⚠️ **`c_clock`'s beat-number outlet is ONE-BASED — 1 to 8, measured.** Built against a 0-based
  assumption, beat 8 landed on index 19: a right-column **ring button** lit white while the beat
  row went dark, once per bar. **Seven beats out of eight looked perfect.** It took decoding the
  painted SysEx frames rather than watching the surface.
- ⚠️ **Both layer TTLs lowered their flag without setting the dirty flag**, so an expired alert
  would have left the grid **red permanently** — the display simply stopping. The comment in that
  subpatch already claimed every expiry set it. **Prose describing intent is not evidence.**
- ⚠️ **Pd processes `.pd` records strictly in order, so a `#X connect` that appears before its
  target box is defined fails at load.** Appending boxes is the documented rule; the *connects*
  have to move with them. It printed `connection failed` six times and `deploy.sh`'s output gate
  caught it — twice, in two different files.
- ⚠️ **`$1` in a message box is the incoming message, not the creation argument.** The port for
  `[midiout]` needs `[f $1]` in an *object* box. The message-box form resolves to 0 — a different
  port, and a silent one.
- ⚠️ **A comma in a message box splits it however it is escaped in the file.** `\,` satisfies the
  *parser*; the message box still treats the comma atom as a separator. Fourteen fragments in the
  first bench run, in the file whose own header warns about it. **`phase6-bench.pd` is generated,
  and the generator now asserts against commas and semicolons.**
- **Aftertouch publishes to `param` only, never `disp`** — a deliberate break with `m_nano`'s
  both-off-one-trigger rule. Polyphonic pressure is a continuous stream per held pad, and a
  four-finger chord would fill the OLED's five param rows for as long as it was held.

### Two things about process

- **Deleting or inserting boxes mid-list silently rewires the file**, and it bit three times.
  `pd-layout-check.py` reports it as *"indices are probably off by one"*, which is how it was
  caught each time — the check earns its place as a graph checker, not just a layout one.
- **`u_root` was re-laid out**, coordinates only. The audio chain did not move. The old three
  ragged columns had no route for a new cord that did not pass through a comment.

### What Phase 6 leaves behind

**A panic blanks the grid until the patch is reloaded.** Panic returns the Launchpad to Live
Mode, and nothing re-enters Programmer Mode except `u_init`'s boot. Deliberate — the escape hatch
is worth more than the display — and currently harmless, since nothing on the device sends
`panic`. Tracked in [plan-v03.md](plan-v03.md).

**The mode names are placeholders.** Six message boxes in `u_map`, three `compose` and three
`perform`. The split is arbitrary but the *ratio* is not: `u_err` routes on those words, so one
compose and five perform would mean almost any mode selection silently made the error display
quiet.

## Phase 6 on the hardware — the acceptance run, and what it cost to trust it

Everything above was Mac-verified. This is what happened when it was deployed, and it is the
strongest evidence in the project that **a green Mac bench does not mean a phase is done**.

### The bench had to be rebuilt before it could be believed

The four benches were self-driving on a ten-second timer, so the console text and the hardware
moved at the same instant — you cannot read one while watching the other. They are now **stepped by
hand**: press GO to run the step just described, press GO again to describe the next. One control,
because the device has only one to spare. `tools/bench-gen.py` generates all four from
`bench_steps.py`, and `bench-verify.py` re-extracts the step text from the generated files and
diffs it against the table — the three hardware-verified benches had to survive conversion
**verbatim**, and that gate is the only reason converting them was safe.

⚠️ **Four of the first run's five failures were in the bench, not the patch.** The modal chain
(steps 7–10) silently expired under manual stepping because the 30-second TTL is wall-clock and a
human takes longer than that to judge a step; step 12 could not distinguish the grid filter working
from `u_err` being quiet in perform mode; step 19 asserted the opposite of what became true; and
step 24 tested nothing at all, because the replug ran *after* the panic had already dropped
ownership legitimately. **A bench that lies is worse than no bench**, and none of these were
visible by reading.

### Three bugs that shipped, all invisible on the Mac

- ⚠️ **A phantom `lp-cc-N` on every nanoKONTROL movement.** `mother`'s own
  `alsaconnect.sh` wires the **lowest-numbered** MIDI client to Pd's Midi-In 1, and the nano
  enumerates below the Launchpad — so every boot put the nano on `m_launchpad`'s channel block, and
  one fader move published both `slider-1` and a phantom `lp-cc-1`. **No Pd-side fix exists**: once
  two devices share Midi-In 1 they are both genuinely channel 1, and `m_launchpad`'s channel test is
  correct and powerless. Fixed with two `aconnect -d` lines in `wire.sh`, costing no extra fork.
  Invisible on the Mac, which has explicit device slots and no `mother`.
- ⚠️ **A replug fails differently on each platform.** On the Mac the device returns in Live Mode
  with input still flowing under stale ownership; on the Organelle the ALSA subscriptions are
  **destroyed outright**, so the surface simply vanishes and `wire.sh` only runs at boot. One
  detector cannot cover both. See *The watchdog* below.
- ⚠️ **`killall pd` strands the Launchpad in Programmer Mode**, with the device's own Settings menu
  locked out. The safe exit hooks `[r quitting]`, which only `mother.pd` sends; Pd 0.49 has no
  `closebang`, so a signal from the shell produces nothing. **The by-hand console workflow had been
  doing this all along.** `tools/lp-live.sh` recovers it with `amidi` and no power cycle.
  `deploy.sh` was never affected — it loads through `/loadPatch`, so `quitting` fires normally.

### Two claims recorded as measured, and false

- **"A SysEx of 120 colour specs is rejected outright."** It came from **three broken probes**: one
  addressed index 128 — `0x80`, a status byte that cut its own SysEx short; one sent a bare count
  and painted zero specs, so an empty message read as a rejection; one painted the second frame the
  same colour as the first, so a successful repaint was invisible. A clean 120-spec message paints
  the whole surface. **`g_grid` now spans 1–108**, and the reason is not the extra buttons: **LED
  state survives the Programmer Mode switch**, so an index outside the span keeps whatever Live Mode
  drew there forever. Seen twice — the row was green one run and dark the next with nothing in Cut
  It touching it.
- **"The clock roughly doubled Pd's CPU, and it is the 96 ALSA MIDI writes a second."** Item 75 said
  so and marked it ⬜ *not confirmed by isolation*. Isolated now, two ways. A **tempo sweep** across
  a 50× range puts the MIDI at **≈0.48 points per 100 writes/s** — so 96 writes cost about **0.43
  points**, not five. Then `tools/dsp-toggle.pd` turned the audio engine off on the running patch:
  **DSP on 11.8 %, DSP off 4.9 %.** ✅ **The DSP costs 6.9 points and the MIDI 0.43** — wrong by a
  factor of sixteen. Within the DSP, a marginal `c_clock` is **0.43 points**, measured against a
  scratch copy with two extra instances, so **poly-tempo is cheap and the base graph is where the
  budget went**. That matters for v0.3, which stacks four filter stages on this baseline.

### The watchdog — two mechanisms, because one detector cannot work

`m_launchpad` → `pd watchdog`. A **heartbeat** re-asserts Programmer Mode every two seconds, which
fixes the Mac without detecting anything — the device answers a universal device inquiry in *either*
mode, so a Mac replug is undetectable by polling. An **inquiry poll** detects loss on the Organelle,
where three missed replies drop ownership and `g_grid` goes silent. Recovery re-runs `wire.sh`:
first attempt ~14 s after the cable goes, then every 8 s, stopping at ~70 s.

- **`$0-want` is not `$0-own`.** `own` says the surface *is* ours; `want` says we still *intend* it.
  Without the split, a panic hands the device back and the heartbeat grabs it again two seconds later.
- ⚠️ **The arming gate is load-bearing.** The first build let three missed polls drop ownership
  unconditionally, so on any machine with no Launchpad — including the headless gate — the grid went
  dark six seconds in. Ownership can now only be *dropped* after a reply has actually been seen: **a
  detector that has never proven it works can never blank the grid.**
- ⚠️ **The bound on forking is what makes this permissible at all.** Phase 4's rule is *one fork per
  load, never per event*, written against error logging, which cascades without limit. Three forks
  tied to one cable event cannot. `wire.sh` costs **133 ms**, is idempotent, and ten forks fired back
  to back produced no audio complaint on Pd's console — all measured before the rule was bent.

### Three layers of testing, and each caught what the others could not

This is the part worth carrying into Phase 7.

- **The headless assert layer** found the arming gate — 7 of 24 checks. **No hands-on bench could
  have**: the failure only exists when the hardware is *absent*.
- **The hardware** found the recovery cadence. The first version gave up **12 seconds** after the
  unplug, which reads as perfectly reasonable in source and is useless in a room — nobody reseats a
  cable that fast, and the very first test missed the window.
- **Hands** found the phantom `lp-cc` and the stranded Launchpad. Both needed somebody to do an
  ordinary thing — move a fader, quit the patch — and look at what happened.

## Phase 7 — the phone status link

`u_net`, the fourth display surface. Promotion of `tools/status-display/` to an abstraction that
obeys the conventions: a consumer of `disp`, sole owner of the phone, rate-limited internally so
no `m_` layer and no `u_map` branch learns a phone exists.

**Built, deployed and verified on hardware in one session.** 28 headless checks, a 15-step bench
that passed 15/15 on the device, and a cost of **0.2 CPU points and about 4 UDP datagrams a
second**.

### Step 0 changed the design, as it has in every phase

⚠️ **A UDP `connect` to a host that is up with nothing listening SUCCEEDS, delivers exactly one
datagram, and is then destroyed by the ICMP port-unreachable that comes back** — after which every
`send` is discarded in silence. The first build had no reconnect, which would have left the link
dead for a whole set with three lines on a console the device does not have. **The reconnect is the
feature, not a nicety.**

Two smaller ones, both of which would have cost time later:

- **`oscformat`'s two spellings are identical.** The prototype used `[oscformat /cutit/hb]` *and*
  `[oscformat cutit param]` in one file, and since the help patch shows args being joined with
  slashes, the first looked like it had to be producing `//cutit/hb`. Byte-for-byte it is not — Pd
  splits the args itself. **The inconsistency is cosmetic; do not "fix" it expecting a change.**
- **`disp` is silent at rest and 402 messages a second under one moving knob** — half of them
  `status`, because knob 1 is master tempo and `u_tempo` writes the BPM into the footer. **So
  `status` needed its own rate limit**, which the plan had not called for.

### The gate got its can-it-fail proof for free

`phase6-assert.sh` had to demonstrate it could fail by reintroducing a real bug afterwards. This one
did not: **`u_net` was built plumbing-first with no coalescer**, and that build failed **exactly the
three rate ceilings** — 401, 802 and 401 packets — while every shape check passed. The per-name
store took those to 42, 84 and 42.

It is also much cheaper than Phase 6's. `[midiout]` is a built-in class with no side channel, so
that gate rewrites boxes in a scratch copy. **`u_net` already emits to a socket**, so the gate
points it at `127.0.0.1` and reads real datagrams. Nothing is rewritten and `Cut It/` is never
touched.

### Four things the device found that the Mac could not

- ✅ **The ICMP teardown holds on Linux/ARM** — errno **111**, where macOS gave 61 — **and the
  reconnect recovers the link unaided**: 12 attempts, 11 refusals, the 12th stuck, with nothing
  touched on the Organelle. `net-link-down` was raised **once** across the whole outage rather than
  once per retry, which is Phase 4's one-fork-per-load rule holding.
- ✅ **The alert about the outage survived the outage.** On reconnect the phone displayed `warn` /
  `net-link-down` — an error raised while it was switched off, delivered afterwards because the
  alert is held as state and repeated on every heartbeat. **Sent as an event it would have been lost
  forever.** This is the clearest demonstration in the project of why *state, never events* is not a
  stylistic preference.
- ⚠️ **A phone joining mid-session saw blanks.** Parameters and status were sent only on change, so
  a scene opened later showed empty rows until something moved. The alert never had this problem;
  the OLED never had it either, because it redraws held state every frame. **`u_net` was the only
  surface where a late viewer saw nothing.** Fixed with a 2 s repeat of the last parameter and
  status, below the noise floor at 124/s.
- ⚠️ **The iPhone's notch covers the edge of the scene and PdParty does not inset for it.** About 44
  points — 22 canvas units — in landscape, silently. Fixed by insetting **one** side, since turning
  the phone chooses which edge it lands on.

### Two corrections to the phase's own plan, both from arithmetic

- **`NO-LINK` needed no work at all.** The phone restarts a 1500 ms timer on every datagram and the
  heartbeat is 500 ms, so the last packet is at most half a second old when the link drops:
  `NO-LINK` lands 1.0–1.5 s later. The prototype already met the spec.
- ⚠️ **"If `u_net` moves the 117/s UDP figure, rate limiting is not working" was not a usable
  gate** — the heartbeat alone is +2/s. The real target was ~121–124/s idle, and the measurement
  landed at 121–125.

### The lesson about measuring rigs, again

⚠️ **The late-join fix broke 7 of the gate's 25 checks, and every one was asserting *zero packets
in an idle window*.** Those were **proxies** — what they were really standing in for is that no
reserved selector ever becomes a parameter. They were rewritten to assert that property directly
rather than relaxed to accommodate the new traffic. **The gate came out of the change stronger than
it went in**, at 28 checks.

⚠️ **And a conclusion was drawn too early mid-session.** With PdParty apparently closed, the socket
stayed `ESTABLISHED` and no teardown appeared — recorded briefly as "Linux does not behave like
macOS". It was wrong: iOS was still running the app in the background with the port bound, so the
case had simply never been tested. **Backgrounding an iOS app is not closing it**, and the orange
pill in the status bar is the tell.

### Where the phone lives: three answers, and the first two were wrong

The address started as a literal in `u_root`, which is correct on exactly one network and dead on
the others. Two attempts to fix that, and the failure of the second is the more instructive:

- ❌ **A subnet broadcast** (`192.168.1.255`) is no less network-specific than a host address.
- ❌ **A limited broadcast** (`255.255.255.255`) is genuinely network-agnostic, Linux permits it,
  PdParty accepts it, and **19–20 of 20 datagrams arrive against a unicast control managing 18**.
  Everything checked out except the property nobody measured. ⚠️ **Wifi access points buffer
  broadcast frames and release them on beacon boundaries**: unicast arrived every 200 ms as sent,
  broadcast arrived **in bursts of three or four separated by up to 819 ms**. Throughput identical,
  latency not — which is exactly why a delivery test saw nothing wrong and **a person moving a knob
  noticed within seconds**. It also eats the phone's 1500 ms `NO-LINK` margin.
- ✅ **Discovery.** `phone-ip.sh` reads the DHCP lease the Organelle itself handed out when acting
  as an access point, and falls back to the creation argument anywhere else — so it always prints
  one line and no conditional lives in the patch. **There was never a discovery problem to solve;
  the Organelle already knew the answer.**

⚠️ **`[netreceive]` in 0.49 cannot tell you who sent a datagram**, which is why the phone announcing
itself was not an option. Checked before designing around it.

### The access point, and a probe that killed its own design

The venue sequence — Start AP, join the phone, load Cut It — needed the AP startable without a
laptop. The first answer was a `Start AP` menu patch. ⚠️ **It does not work**: `create_ap`,
`hostapd` and `dnsmasq` are all children of the Pd that spawned them and die when the next patch
loads, **even behind `setsid nohup`**. The Organelle's own System → WiFi Setup → **Start AP**
predates the whole idea and is not a child of a patch.

**The probe that found this was built to be run without help**, because a Mac joined to the AP has
no internet — `create_ap` runs with `-n` and one radio cannot be both AP and client. So the session
that answers those questions is the session with nobody watching. It recorded itself to
`/sdcard/ap-probe.log`, and ✅ **its second extraction strategy is what saved the run**: dnsmasq had
already exited, so the address came from `arp` rather than the lease file.

### The Mac bench, which this phase had skipped

Running the bench on the Mac *before* the device is the convention, and Phase 7 went device-first.
Doing it afterwards found two things the device run had passed straight over:

- ⚠️ **`[metro]` fires the instant it is started.** The reconnect metro, armed at 1600 ms, banged
  the address store **before the address had resolved** — `connect` with an empty host, and
  `bad host?` on the console at **every boot**. New with discovery: before it, the store was
  `[f $2]` and an early bang produced a valid address. Fixed by arming at 3000 ms.
- ⚠️ **TWO INSTRUMENTS WILL FIGHT OVER ONE PHONE.** With the Organelle running Cut It and
  `main-dev.pd` running on the Mac, both were connected to the same phone and the status row
  **fluttered between two values**. The bus was innocent — a `[r disp]` tap showed four messages
  and no repeats. **`u_net` is the sole owner of the phone WITHIN an instrument; nothing arbitrates
  ACROSS machines**, and the symptom looks nothing like contention. It will recur during off-device
  development with the device still powered.

### And item 81 finally showed its face

The wifi drop interrupted the device re-run between steps 11 and 12, and for several minutes looked
exactly like a `u_net` fault — which its own entry had predicted for two phases. What was actually
true: **still associated**, `wpa_supplicant` and `dhcpcd` both running, and **no IPv4 address at
all**. ⚠️ **SSH kept working over IPv6 link-local throughout**, so *"check ssh before debugging
code"* — this project's own rule — **was not a sufficient test**. The check is
`ip addr show wlan0 | grep "inet "`.

**So it is the IPv4 lease that is lost, not the network**, and a restart fixes it first try where a
`dhcpcd` renew does not. That points at DHCP renewal rather than the dongle, the power or the AP.
[plan-tests.md](plan-tests.md) item 133; the investigation is in [plan-v03.md](plan-v03.md).

## Phase 8 — the data store

`u_state`, `u_store`, the `state` bus and the two persistence policies. **The last phase of
v0.2.**

**The phase was reframed twice, both times by Brendan, and the second reframe deleted more work
than it added.** The plan treated state as a *control snapshot*, which made parameter pickup the
central problem. It is not that: state here is **content** — beats, kits, melodies, samples —
almost none of which exists yet. Then the sharper correction: this is a **frontend-to-database**
paradigm, *the patch persisting its own data*, and **not** the Organelle's "Save New duplicates
the patch folder" idiom.

⛔ **Dropping Save New deleted a whole cluster of problems unasked** — `/tmp/curpatchname`
returning `!`, variants landing at the top level of `Patches`, and whether `deploy.sh` should
repair any of it. All of it existed only to serve Save New. **Presets became records inside the
store instead**, and `deploy.sh` was not modified at all.

### The design, and the one thing that makes it cheap

**One new global name, `state`, three selectors, disjoint per side.** A contributor names its own
key and declares its own policy — `auto` for a running value, `manual` for a committed take — so
an abstraction written long after `u_state` persists itself with no change to `u_state`. That was
the actual deliverable.

⚠️ **The `manual` answer is SYNCHRONOUS, and that is the whole mechanism.** Pd is depth-first, so
by the time the `save` broadcast returns every honest answer is already stored and the file can be
written immediately — no settle timer, no `[del]`. It also made the 250 ms budget irrelevant:
writing straight to `/sdcard` with an absolute path never depended on mother's `cp`.

**A registry table was designed and then dropped.** Pull semantics survive without one: a
broadcast reaches every contributor with nobody bookkeeping who exists, and it avoids a
**data-driven send**, which is the construct `ref-conventions.md` refuses in `u_map`.

### Two bugs, both invisible, both caught on the Mac

- ⚠️ **The auto store wrote before it ever read.** Seed at 500 ms, flush at 3000 ms, restore at
  3500 ms — so **every boot overwrote the previous session with its own defaults**, and the file
  looked entirely plausible throughout. Fixed with an invariant, not a timing tweak: **the flush is
  armed by the restore.** Item 152.
- ⚠️ **`text read` of an empty file wiped the live store**, discarding puts that arrived before the
  restore. It self-healed on the first real change, which is precisely why nobody would have
  noticed. Fixed by reading into a separate text and replaying from that. Item 153.

**Running the Mac pass first is what caught both**, and Phase 7's reversal of that order is why
the convention exists at all.

### The gate lied on its first can-it-fail run ⚠️

Phase 6's rule is that a measuring rig must be proven able to fail. **This one was not, and it
passed the broken patch 15/15.** Two faults, both already named in this file for other phases:

- **the driver's timing did not reproduce the real ordering** — it banged the restore at 600 ms,
  long before the 3000 ms flush that causes the bug. It uses **3600 ms** now, and that number is
  load-bearing.
- **the final check could not fail** — it asserted against `mode compose mode-1`, a value only
  `u_map`'s seed produces, in a driver that has no seed. *"An assertion that nothing ever drove"*,
  for the second time in three phases.

Rewritten to assert the real property — *did the restore replay what was on disk at boot?* — it
now fails 2 checks with the bug present and passes 15/15 without it. **Had the proof been skipped,
Phase 8 would have shipped with a green gate protecting nothing.**

### What Step 0 corrected before any of it was built

Six of eleven measurements contradicted a document. The load-bearing ones: **the budget is 250 ms,
not 500** (the two save scripts disagree and only one had been read); **`saveState` arrives as a
BANG, not `1`**, so a `[route 1]` on it never fires; **`[text write]` to a missing directory
PRINTS** rather than failing silently; and **the menu path is `Storage → Save`** — there is no Save
under System, and the doc that said so cost a wasted trip to the device.

✅ And one hypothesis of this phase's own died on contact: `save-new-patch.sh` defaults `PATCH_DIR`
to an unmounted `/usbdrive`, which predicted Save New writing nowhere. mother sets it at runtime
and it works. `/proc/<pid>/environ` shows the *initial* environment and is not updated by
`setenv`, which is what made the reasoning look sound.

### What Phase 8 leaves behind

**Data lives outside the patch folder** — `/sdcard/cut-it-state/` — so `deploy.sh`, `--clean` and a
power cycle cannot touch it, with `tools/fetch-state.sh` as the other half of that bargain.
**`knobs.txt` now appears on the first `Storage → Save`** and the patch boots at saved knob
positions from then on; deliberate, and CLAUDE.md was rewritten to say so. **The `manual` path
ships with no in-patch user** — the first will be v0.3's drum mode — so it is exercised by the gate
and a synthetic contributor rather than by anything deployed, and that is stated plainly rather
than papered over.

## What every phase had in common

Worth stating once, because it is the pattern rather than a coincidence:

**Every phase's most valuable output was a correction to something the plan asserted.** The channel
block, `enc`'s polarity, `/loadPatch`'s argument, `route`'s remainder rule, `[list split n]`,
`pgrep`, `text get`'s field range, the reject-outlet rule, MRU ordering — none of these came from
reading documentation, and several contradict it. That is why
[plan-tests.md](plan-tests.md) marks every claim ✅ / 📄 / ⬜ and why *measure it on the device*
is the first working note in [CLAUDE.md](CLAUDE.md).
