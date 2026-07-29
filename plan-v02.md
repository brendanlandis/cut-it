# Cut It v0.2 — Infrastructure Plan

The scaffolding the instrument stands on: startup, audio path, controller mapping, display,
state. **No musical DSP.** When this is done, Cut It makes no interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. The four filter
stages are built on top of this, afterwards.

v0.1 is not being extended. Its plans are kept in [! v0.1 plans/](<! v0.1 plans/README.md>) and
the patch itself in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) — **reference for
intent, not code to lift.** All of it predates the conventions; assume it is naive.

Read [plan-conventions.md](plan-conventions.md) first — naming, `$0`, `[trigger]` discipline
and the global allowlist are assumed throughout.

---

## Why infrastructure first

Three constraints make the usual "get a sound out, then tidy up" approach expensive here:

1. **There is no console.** Errors vanish. Anything not built to report itself is invisible,
   and retrofitting reporting across an existing patch is far worse than designing it in.
2. **The device mapping layer is the expensive thing to retrofit.** Compose and perform mode
   give the same physical controls different meanings. If `e_chop` learns about the
   nanoKONTROL, that is permanent.
3. **Timing is architectural.** Grain clocks must be audio-domain from the first line, not
   converted later.

---

## What exists already

Not starting from nothing. These are verified and have working reference implementations in
[tools/](tools/):

| Proven | Reference |
|---|---|
| ALSA MIDI wiring from inside a patch via `[shell]` | `tools/self-wire.pd` + `wire.sh` |
| Launchpad Programmer Mode, LEDs, velocity, poly aftertouch | `tools/lp-monitor.pd`, `lp-modes.pd` |
| OLED graphics API from a patch | `tools/oled-probe/` |
| Bidirectional OSC to the phone, named-parameter protocol | `tools/status-display/`, `tools/pdparty-scene/` |
| nanoKONTROL full CC map incl. transport on Pd ch 18 | [plan-midi.md](plan-midi.md) |
| Deploy + syntax check workflow | [plan-conventions.md](plan-conventions.md) |

**The job is turning these into abstractions that obey the conventions**, not discovering
whether they work.

---

## Architecture

```
                        main.pd
                     (wiring only)
                           |
    ┌──────────┬───────────┼───────────┬──────────┐
    │          │           │           │          │
  u_init    u_tempo      u_err      u_state    u_net
  startup   clock        errors     presets    phone
    │          │           │           │          │
    └──────────┴─────┬─────┴───────────┴──────────┘
                     │
              global buses
      mode · tempo · clock · start/stop · panic · err · disp
                     │
    ┌────────────────┼────────────────┐
    │                │                │
  m_nano        m_launchpad         m_keys          ← device mapping
  ch 17/18        ch 1               mother
    │                │                │
    └────────────────┼────────────────┘
                     │
              (v0.3: e_chop, e_pitch, e_trem, e_verb)
                     │
    ┌────────────────┴────────────────┐
  g_oled                           g_grid           ← display arbiters
  OLED                             Launchpad
```

**The `m_` layer is the load-bearing boundary.** Nothing below it knows a nanoKONTROL exists.
A device sends `mode`, `tempo` or a named parameter onto a bus; what consumes it is decided
elsewhere. This is what makes the compose/perform split tractable and it is the one boundary
that is genuinely expensive to retrofit.

---

## Build phases

Each phase is independently testable and leaves the patch in a working state. **Phases 0 and 1
require no hardware**, which matters because the Organelle is not always on the desk.

### Phase 0 — Skeleton and the off-device shim ✅ **done**

`main.pd`, `main-dev.pd`, `u_root`, `u_mother-stub`, `deploy.sh`

The patch must run in vanilla Pd 0.49 on the Mac, where `mother.pd` does not exist. Without
this, every iteration costs a deploy cycle.

`u_mother-stub` provides `knob1`–`knob4`, `vol`, `notes`, `aux`, `enc` and `encbut` as GUI
controls, and previews `screenLine1`–`5` and `oscOut` (`gPrintln` text and `gClear`; anything
else prints). It is the **one sanctioned exception** to the reserved-name rule in
[plan-conventions.md](plan-conventions.md). `main-dev.pd` instantiates it; `main.pd` does not,
so the device never sees it.

Two entry points, both thin, with all content in `u_root` — that is what stops them drifting.

`deploy.sh` closes the loop: **syntax check → scp → reload → load**, no physical interaction.
The check is blocking and gates on *output*, since Pd exits 0 even on load errors.

**Two things this phase corrected**, both read out of `/root/Organelle_UI/` on the device:
`/loadPatch` resolves against the current patch directory, so the argument must be `!/Cut It`,
not `Cut It`; and `enc` is `1`/`0` for up/down, not `±1` — as are `aux` and `encbut`.

**Done when:** ✅ `main-dev.pd` opens on the Mac with no errors, the stub's knobs produce
values, and `./deploy.sh` alone puts a running patch on the device.

### Phase 1 — Audio path ✅ **done**

`u_root` audio chain, `u_level`, `g_levels`

`[r~ inL]` / `[r~ inR]` straight through to `[throw~ outL]` / `[throw~ outR]`, with a
`u_level` tap on each input reporting onto the `disp` bus, and `g_levels` drawing both at 24px.

Deliberately first: it proves the whole signal chain — including the TRS Y-cable split, once
that cable arrives — with no DSP to blame.

**Three corrections to what this phase originally said**, all read off the device:

- **Not `adc~`/`dac~`.** `mother.pd` owns the sound card. `dac~` from a patch bypasses the
  volume knob and the limiter — see *Audio I/O* in [plan-conventions.md](plan-conventions.md).
- **Not `/oled/vumeter`.** mother already drives it, from `inL`, `inR` and the post-volume
  outputs. And it lives in the info bar, which is now off by decision — see
  [plan-display.md](plan-display.md).
- **`gShowInfoBar 3 0` moved out of Phase 2 into here**, because it must go out on every redraw
  rather than once at init, which makes it the display's job and not startup's.

**Also established here, cheaply, because Phase 3 depends on both:** the `disp` bus, and the
rule that exactly one abstraction owns `oscOut` and `screenLine*`. `g_levels` is a placeholder
with the right *interface* — Phase 3 replaces its insides with the arbiter.

**Done when:** ✅ audio in is audible at the output and the volume knob controls it; both input
levels are on the OLED and read the 18–19 noise floor at rest. Covers
[plan-tests.md](plan-tests.md) item 11 through the real patch. Items 12–13 stay blocked on the
TRS Y-cable.

### Phase 2 — Startup sequencing ✅ **done**

`u_init`, `wire.sh`

**Verified end to end on hardware.** `[shell]` runs `wire.sh` from the patch; `aconnect -l`
shows both directions wired (`28:0 → 128:0` for pads in, `128:4 → 28:0` for LEDs and SysEx
out); and captured pad presses come back as **`r*10+c`** — 64, 65, 34, 24, 43, 63 — which is
the Programmer Mode layout and nothing else. Velocity is live (5 to 127). The OLED status line
tracks each stage.

**Getting there cost a hardware lesson, not a code one.** The Launchpad would not configure
behind three chained USB hubs (`can't set config #1, error -32`) and the same topology wedged
the wifi dongle at boot. Plugged directly into the Organelle it works first time. Full evidence
in [plan-hardware.md](plan-hardware.md); tracked as Session 3b in
[plan-tests.md](plan-tests.md).

`quitting` turned out to already exist — `mother.pd` sends it and gives the patch **100 ms**
before quitting Pd. Pd 0.49 has no `closebang`, so that is the only shutdown hook there is.

`loadbang` fires before ALSA connections exist. Rather than scattering `[del]` objects, one
abstraction owns the ordered startup:

1. wire `aconnect` via `[shell]` (pattern from `tools/wire.sh`)
2. wait for ALSA
3. Launchpad → Programmer Mode by SysEx
4. clear the Launchpad grid — **LED state survives mode switches**

*(`gShowInfoBar` is deliberately not on this list — it moved to Phase 1. mother restores the
info bar after every patch load, so it has to be re-sent on each redraw, which makes it the
display's business rather than startup's.)*

**Each stage reports to the OLED as it completes.** With no console, that is the boot
diagnostic — a patch stuck at stage 3 tells you the Launchpad never answered.

**Also here: panic / safe exit.** `[r panic]` returns the Launchpad to Live mode and clears
everything. Bind it somewhere reachable and fire it on `quitting`; without it, a crash in
Programmer Mode means power-cycling the Launchpad.

**Done when:** cold boot to a working home screen with nothing pre-connected, repeatably.

### Phase 3 — Display and errors ✅ **done, verified on hardware**

`g_oled` (replaces `g_levels`), `u_err`

**Verified on the Organelle**, all fourteen steps of `tools/phase3-bench.pd`: boot stages draw
as 16px modals and hand over to the meters with `v0.2-ready` in the footer; a parameter with a
unit and one without both draw correctly, the second with no `%` inherited from the first; a
modal outranks a parameter; an alert preempts the modal and the modal is still there when it
expires; `warn` is suppressed in perform while `fail` still draws, and the filter releases on
compose; a stuck modal clears itself after 30 s.

**Throughput is not a problem.** Measured on the running device: **110 UDP datagrams a second**
— the home frame is 10 OSC messages at 10 Hz, against 6 for Phase 1 — at **8.2 % CPU** and a
load average of 0.16. That also clears the phase's biggest unknown: `packOSC` drops a
mismatched typetag *before* `udpsend`, so a full datagram rate proves the **runtime typetag
builder produces tags the real `packOSC` accepts**, which the Mac could never demonstrate
having no `packOSC` at all.

**Three things this phase corrected:**

- **`u_err` does not draw.** This section used to say it writes to the ALERT buffer, which
  contradicts *Banned* in [plan-conventions.md](plan-conventions.md) — two writers, one screen.
  It filters and forwards onto `disp`; `g_oled` renders.
- **The alert draws to screen 3**, not the ALERT buffer. Nothing underneath needs preserving
  when the frame is rebuilt from state ten times a second, and buffer 4 remains ⬜ untested.
  See [plan-display.md](plan-display.md).
- **`route`'s remainder trap is wider than documented** — any remainder whose first atom is a
  symbol arrives as a selector, not just a lone symbol. And `[list split n]` on exactly *n*
  atoms silently never fires its right outlet, which is what would have made `grain 12` draw as
  `grain 12 %`. Both are now in [plan-conventions.md](plan-conventions.md).

The arbiter described in [plan-display.md](plan-display.md): layers with priority and TTL,
`home` < `param` < `modal` < `err`; sole owner of `oscOut` and `screenLine*`. Callers send
semantics, never layout — `[s disp]` with `chop-size 43 %`. **Big fonts for the active
parameter**: 24px is readable at arm's length, 8px is context.

**`g_levels` from Phase 1 was what got replaced.** Its interface was already right — consume
`disp`, own the screen, redraw on a fixed clock — so this phase swapped the insides and deleted
the file. Nothing upstream changed. ⚠️ **Deploy this phase with `./deploy.sh --clean`**: there
is no rsync on the device, so a plain deploy would leave `g_levels.pd` behind.

#### Layout decisions, settled

- **The home screen is the two level meters.** `gFillArea` bars, not numbers: `env~`'s 0–100
  maps straight onto 128 px. Keep a small 8px numeric readout so the meters stay calibratable,
  and draw the two measured reference marks — noise floor **18–19**, gate threshold **25–30**
  (item 11).
- **A moving knob shrinks the meters into a corner** and gives the parameter the rest of the
  screen at 24px. The meters never disappear entirely — signal presence is always visible.
- **A parameter readout lingers ~1.2 s** after the last change, then the meters expand back.
  One number, expected to be tuned by living with it.

#### Errors follow the mode, not a severity guess

**Two error behaviours, chosen by the existing `mode` bus** rather than a new concept:

| `mode` | Shows |
|---|---|
| compose | **verbose** — every error reaches the screen |
| perform | **quiet** — only failures; warnings stay on the bus |

This is why `err` carries a level: **`<level> <source> <text>`**, level ∈ `warn` `fail`.
`u_err` routes on it and consults `[r mode]`. Nothing drives `mode` until Phase 4, so
**default to verbose** — during development that is the useful default, and it degrades safely.

Errors **time out** rather than waiting to be dismissed; a stuck error covering the display
mid-set is the worse failure. They stay recoverable on the bus for the by-hand console and, in
Phase 7, the phone.

`u_err` **forwards onto `disp`** as `alert <level> <source> <text>`; `g_oled` owns the drawing,
because [plan-conventions.md](plan-conventions.md) allows exactly one sender on `oscOut`. The
alert is the top-priority layer on the ordinary patch screen — the ALERT buffer is ⬜ untested
and buys nothing under a state-driven redraw.

**The bus is unfiltered; only the screen is filtered.** `u_err` prints every error
unconditionally, so the by-hand SSH console sees warnings even in perform mode.

**This does not catch Pd's own runtime errors.** Those still go to tty1; the answer for those
is the by-hand console in [plan-conventions.md](plan-conventions.md).

**Done when:** ✅ two sources competing for the display resolve by priority, a parameter readout
decays back to the meters after ~1.2 s, an error preempts and restores what was underneath, and
bus traffic far above the redraw rate still draws at the fixed rate. **Outstanding:** the same
on hardware, via `./deploy.sh --clean`.

### Phase 4 — nanoKONTROL

`m_nano`

The simplest controller: CC only, no LEDs, no SysEx. Pd channel 17 for controls, **channel 18
for transport**, so `[route 18]` separates mode changes before any CC decoding.

Decode with `[div 10]` / `[mod 10]`. Emits named parameters onto `disp` and mode changes onto
`mode`. Knows nothing about what it controls.

**Done when:** every slider, knob and button is identified and displayed by name, and the
transport buttons change `mode` visibly.

### Phase 5 — Clock and transport

`u_tempo`, `c_clock`

A **rewrite**, not a port. v0.1's `midiclock.pd` is archived in
[! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) and is worth reading for *which MIDI
realtime bytes went where*, nothing more — it predates every convention in this project.

`u_tempo` owns `tempo`, `clock`, `start`/`stop`; emits MIDI realtime (248/250/251/252).

**Audio-domain from the start** — `phasor~`-derived, with the message-rate clock only for
things that genuinely tolerate it. Normalise BPM and ms to Hz at the edge.

**`u_tempo` is a master reference, not the clock.** Cut It runs poly-tempo — see *Poly-tempo*
in [plan-conventions.md](plan-conventions.md). Build `c_clock` as a separately instantiable
abstraction in this phase, owning its own rate and time signature and optionally slaved to
master by a ratio. **Do not build a clock singleton**; retrofitting once Phases 6–8 depend on
one is the expensive mistake this plan is trying to avoid.

**Done when:** tempo is settable from the nano, the 404 follows, grain-rate timing derives from
`phasor~` rather than `metro`, and two `c_clock` instances run at different rates at once.

### Phase 6 — Launchpad

`m_launchpad`, `g_grid`

The most complex piece, deliberately late. Pad input on Pd channel 1 with `r*10+c` decode and
polyphonic aftertouch. `g_grid` is the same arbiter shape as `g_oled` — playhead, slot state,
mode and meters all contend for 64 pads.

Batch LED updates: **one SysEx can carry up to 106 colour specs**, so a full-grid repaint is
one message, not 64.

Flash and pulse are **synced to MIDI beat clock**, so animation follows `u_tempo` for free.

**Done when:** pads report position, velocity and pressure; the grid shows mode state; a full
repaint is one message.

### Phase 7 — Phone status link

`u_net`

Promotion of `tools/status-display/` to an abstraction. Subscribes to `disp` and forwards over
`[netsend -u]`, plus the heartbeat.

**State never events; fire and forget; the Organelle never waits.** Rate limiting lives here,
not in the callers.

**Done when:** every parameter shown on the OLED also reaches the phone, and pulling the plug
shows `NO-LINK` within 1.5 s.

### Phase 8 — State and presets

`u_state`

Hooks `[r saveState]`, writes to `/tmp/state/` within the **0.5 s budget**, reads from
`/tmp/patch/` on load. Plain text via `[text]`, git-diffable.

Gets Save and Save New from the Organelle's own menu for free.

⚠️ **Save New is broken for patches in a category folder, and `deploy.sh` makes it worse.**
`save-new-patch.sh` derives the name with `ls /tmp/curpatchname`, and mother records whatever
name it was given. A `deploy.sh` load passes `!/Cut It`, so that becomes `/tmp/curpatchname/!/Cut It`
and the script reads back `!` — Save New then creates a folder called `! 2`. Selecting the
patch from the menu leaves the correct `Cut It`. Plain Save is unaffected; it works off the
`/tmp/patch` symlink. **Verify this phase against a menu-selected patch, not a deploy-loaded
one**, and decide then whether to have `deploy.sh` repair `/tmp/curpatchname`.

**Done when:** control state survives Save → reload, and Save New produces a working variant in
the patch menu.

---

## Deferred to v0.3+

| Deferred | Why |
|---|---|
| **The four filter stages** | This plan is the floor they stand on |
| **Footswitch / expression pedal** | Deliberate — see [plan-hardware.md](plan-hardware.md) |
| **SP-404 and Volca mapping** | `m_404` and the DIN interface; the interface isn't bought |
| **Compose-mode capture** | Needs the mode system working first |
| **`gWaveform` display** | Blocked on whether Pd can emit an OSC blob — untested |
| **Organelle as access point** | [plan-tests.md](plan-tests.md) Session 5 |

---

## Risks

**The audio topology is partly unproven.** The 404 has discrete L/R jacks, so two independent
signals certainly leave it. What remains unverified is the **Organelle's** TRS input splitting
into `adc~ 1` / `adc~ 2` (low risk, and partly testable with an ordinary mono cable — see
[plan-tests.md](plan-tests.md) item 11) and, more importantly, **how the 404 routes external
input internally**. That last one could still change the design and no cable will answer it.
Phase 1 is built to surface all of it early.

**Full-load power is untested.** Three controllers plus the wifi dongle have never run at once.
It presents as intermittent MIDI dropouts, not an obvious failure — so if Phase 6 produces
flaky Launchpad behaviour, suspect the hub before the code.

**The display arbiter is the piece most likely to be wrong first time.** Contention, TTL and
rate limiting are easy to describe and fiddly to tune. Build it early (Phase 3) precisely so
there is time to live with it.
