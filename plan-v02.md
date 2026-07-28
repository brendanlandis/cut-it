# Cut It v0.2 — Infrastructure Plan

The scaffolding the instrument stands on: startup, audio path, controller mapping, display,
state. **No musical DSP.** When this is done, Cut It makes no interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. The four filter
stages are built on top of this, afterwards.

v0.1 is not being extended. It is kept for reference in
[! v0.1 plans/](<! v0.1 plans/README.md>) and superseded here.

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

### Phase 0 — Skeleton and the off-device shim

`main.pd`, `u_mother-stub`

The patch must run in vanilla Pd 0.49 on the Mac, where `mother.pd` does not exist. Without
this, every iteration costs a deploy cycle.

`u_mother-stub` provides `knob1`–`knob4`, `notes`, `aux`, `enc` as GUI controls and swallows
`screenLine*` / `oscOut`, printing them instead. Loaded only when `mother.pd` is absent.

**Done when:** `main.pd` opens on the Mac with no errors and the stub's knobs produce values.

### Phase 1 — Audio path

`main.pd` audio section

`adc~ 1` and `adc~ 2` straight to `dac~`, with `/oled/vumeter` fed from both.

Deliberately first: it proves the whole signal chain — including the TRS Y-cable split, once
that cable arrives — with no DSP to blame.

**Done when:** audio in is audible at the output, drums and fx are independently visible on the
meter. Covers [plan-tests.md](plan-tests.md) items 11–12.

### Phase 2 — Startup sequencing

`u_init`

`loadbang` fires before ALSA connections exist. Rather than scattering `[del]` objects, one
abstraction owns the ordered startup:

1. wire `aconnect` via `[shell]` (pattern from `tools/wire.sh`)
2. wait for ALSA
3. Launchpad → Programmer Mode by SysEx
4. clear the Launchpad grid — **LED state survives mode switches**
5. `gShowInfoBar 3 0`, clear the OLED, draw the home screen

**Each stage reports to the OLED as it completes.** With no console, that is the boot
diagnostic — a patch stuck at stage 3 tells you the Launchpad never answered.

**Also here: panic / safe exit.** `[r panic]` returns the Launchpad to Live mode and clears
everything. Bind it somewhere reachable and fire it on `quitting`; without it, a crash in
Programmer Mode means power-cycling the Launchpad.

**Done when:** cold boot to a working home screen with nothing pre-connected, repeatably.

### Phase 3 — Display and errors

`g_oled`, `u_err`

The arbiter described in [plan-display.md](plan-display.md): layers with priority and TTL,
`home` < `param` < `modal` < `err`; rate-limited to ~20 Hz **with a guaranteed trailing edge**;
sole owner of `oscOut` and `screenLine*`.

Callers send semantics, not layout — `[s disp]` with `chop-size 43 %`.

`u_err` owns `[r err]`, formats, and routes to the ALERT buffer via `/oled/setscreen`, so an
error never destroys what was on screen.

**Big fonts for the active parameter** — 24px is readable at arm's length, 8px is context.

**Done when:** two sources competing for the display resolve by priority, a parameter readout
decays back to home, and an error preempts and restores.

### Phase 4 — nanoKONTROL

`m_nano`

The simplest controller: CC only, no LEDs, no SysEx. Pd channel 17 for controls, **channel 18
for transport**, so `[route 18]` separates mode changes before any CC decoding.

Decode with `[div 10]` / `[mod 10]`. Emits named parameters onto `disp` and mode changes onto
`mode`. Knows nothing about what it controls.

**Done when:** every slider, knob and button is identified and displayed by name, and the
transport buttons change `mode` visibly.

### Phase 5 — Clock and transport

`u_tempo`

Rebuild of v0.1's `midiclock.pd` to convention. Owns `tempo`, `clock`, `start`/`stop`; emits
MIDI realtime (248/250/251/252).

**Audio-domain from the start** — `phasor~`-derived, with the message-rate clock only for
things that genuinely tolerate it. Normalise BPM and ms to Hz at the edge.

**Done when:** tempo is settable from the nano, the 404 follows, and grain-rate timing derives
from `phasor~` rather than `metro`.

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
