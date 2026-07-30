# Cut It v0.2 — Infrastructure Plan

The scaffolding the instrument stands on: startup, audio path, controller mapping, display,
state. **No musical DSP.** When this is done, Cut It makes no interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. The four filter
stages are built on top of this, afterwards.

v0.1 is not being extended. Its plans are kept in [! v0.1 plans/](<! v0.1 plans/README.md>) and
the patch itself in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) — **reference for
intent, not code to lift.** All of it predates the conventions; assume it is naive.

Read [ref-conventions.md](ref-conventions.md) first — naming, `$0`, `[trigger]` discipline
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
| nanoKONTROL full CC map incl. transport on Pd ch 18 | [ref-midi.md](ref-midi.md) |
| Deploy + syntax check workflow | [ref-conventions.md](ref-conventions.md) |

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

Two thin entry points with all content in `u_root` — that is what stops them drifting.
`main-dev.pd` instantiates `u_mother-stub`, the Mac-only stand-in for `mother.pd` and the
**one sanctioned exception** to the reserved-name rule; `main.pd` does not, so the device never
sees it. It has since grown into the full dev panel — see *Seeing it off-device* in
[ref-display.md](ref-display.md).

`deploy.sh` closes the loop: **syntax check → scp → reload → load**, no physical interaction.
The check is blocking and gates on *output*, since Pd exits 0 even on load errors.

**Two corrections, both read out of `/root/Organelle_UI/`:** `/loadPatch` resolves against the
current patch directory, so the argument must be `!/Cut It`, not `Cut It`; and `enc` is `1`/`0`
for up/down, not `±1` — as are `aux` and `encbut`.

### Phase 1 — Audio path ✅ **done**

`u_root` audio chain, `u_level`, `g_levels`

`[r~ inL]` / `[r~ inR]` straight through to `[throw~ outL]` / `[throw~ outR]`, with a
`u_level` tap on each input reporting onto the `disp` bus. Deliberately first: it proves the
whole signal chain with no DSP to blame. Also established here because Phase 3 depends on both:
the `disp` bus, and the rule that exactly one abstraction owns `oscOut` and `screenLine*`.

**Three corrections, all read off the device:**

- **Not `adc~`/`dac~`.** `mother.pd` owns the sound card — see *Audio I/O* in
  [ref-conventions.md](ref-conventions.md).
- **Not `/oled/vumeter`.** mother already drives it, and it lives in the info bar, which is now
  off by decision — see [ref-display.md](ref-display.md).
- **`gShowInfoBar 3 0` moved out of Phase 2 into here**, because it must go out on every redraw
  rather than once at init, which makes it the display's job and not startup's.

**Done when:** ✅ audio is audible and the volume knob controls it; both levels on the OLED read
the 18–19 noise floor at rest. Covers [plan-tests.md](plan-tests.md) item 11 through the real
patch; items 12–13 stay blocked on the TRS Y-cable.

### Phase 2 — Startup sequencing ✅ **done**

`u_init`, `wire.sh`

**Verified end to end on hardware** — `[shell]` runs `wire.sh`, `aconnect -l` shows both
directions wired, and captured pads read `r*10+c` with live velocity.

`loadbang` fires before ALSA connections exist, so rather than scattering `[del]` objects one
abstraction owns the ordered startup:

1. wire `aconnect` via `[shell]` (pattern from `tools/wire.sh`)
2. wait for ALSA
3. Launchpad → Programmer Mode by SysEx
4. clear the Launchpad grid — **LED state survives mode switches**

*(`gShowInfoBar` is deliberately not on this list — it moved to Phase 1, because mother
restores the info bar after every patch load, so it must be re-sent on each redraw.)*

**Each stage reports to the OLED as it completes.** With no console, that is the boot
diagnostic — a patch stuck at stage 3 tells you the Launchpad never answered.

**Also here: panic / safe exit.** `[r panic]` returns the Launchpad to Live mode and clears
everything, fired on `quitting` — which `mother.pd` sends, giving the patch **100 ms**. Pd 0.49
has no `closebang`, so that is the only shutdown hook there is. Without it, a crash in
Programmer Mode means power-cycling the Launchpad.

**The lesson here was hardware, not code.** The Launchpad would not configure behind three
chained USB hubs (`can't set config #1, error -32`) and the same topology wedged the wifi
dongle at boot; plugged directly in, it works first time. Evidence in
[ref-hardware.md](ref-hardware.md), tracked as Session 3b in [plan-tests.md](plan-tests.md).

### Phase 3 — Display and errors ✅ **done, verified on hardware**

`g_oled` (replaces `g_levels`), `u_err`

The arbiter: layers with priority and TTL, `home` < `param` < `modal` < `alert`, sole owner of
`oscOut` and `screenLine*`. Callers send semantics, never layout — `[s disp]` with
`chop-size 43 %`. Full description and geometry in [ref-display.md](ref-display.md).

**Verified on the Organelle**, all fourteen steps of `tools/phase3-bench.pd` — every layer, the
priority order, the mode filter and the 30 s safety TTL. Details in
[plan-tests.md](plan-tests.md) items 21–21c.

**Throughput is not a problem:** **110 UDP datagrams a second** at **8.2 % CPU**, load 0.16.
That also clears the phase's biggest unknown — `packOSC` drops a mismatched typetag *before*
`udpsend`, so a full datagram rate proves the **runtime typetag builder produces tags the real
`packOSC` accepts**, which the Mac could never demonstrate having no `packOSC` at all.

**Three corrections**, all now in [ref-conventions.md](ref-conventions.md):

- **`u_err` does not draw.** This section used to say it writes to the ALERT buffer, which
  contradicts *Banned* — two writers, one screen. It filters and forwards onto `disp`.
- **The alert draws to screen 3**, not the ALERT buffer. Nothing underneath needs preserving
  when the frame is rebuilt from state ten times a second. ✅ Buffer 4 has since been proven
  writable and switchable — and deliberately still isn't used, because it would make the alert
  the one edge-triggered layer in a state-driven arbiter.
- **`route`'s remainder trap is wider than documented** — any remainder whose first atom is a
  symbol arrives as a selector, not just a lone symbol. And `[list split n]` on exactly *n*
  atoms silently never fires its right outlet, which is what would have made `grain 12` draw as
  `grain 12 %`.

⚠️ **Deploy this phase with `./deploy.sh --clean`** — there is no rsync on the device, so a
plain deploy would leave the deleted `g_levels.pd` behind to shadow the new display.

#### Layout decisions, settled

- **The home screen is the two level meters** — `gFillArea` bars, not numbers, with a small 8px
  readout so they stay calibratable and the measured reference marks drawn in: noise floor
  **18–19**, gate threshold **25–30**.
- **A moving knob shrinks the meters** and gives the parameter the rest of the screen at 24px,
  readable at arm's length. The meters never vanish — signal presence is always visible.
- **A parameter readout lingers ~1.2 s**, then the meters expand back. Expected to be tuned by
  living with it.

#### Errors follow the mode, not a severity guess

| `mode` | Shows |
|---|---|
| compose | **verbose** — every error reaches the screen |
| perform | **quiet** — only failures; warnings stay on the bus |

This is why `err` carries a level: **`<level> <source> <text>`**, level ∈ `warn` `fail`.
Nothing drives `mode` until Phase 4, so **default to verbose** — it degrades safely.

Errors **time out** rather than waiting to be dismissed; a stuck error covering the display
mid-set is the worse failure. **The bus is unfiltered; only the screen is filtered**, so the
by-hand console sees warnings even in perform mode. This does not catch Pd's *own* runtime
errors — those still go to tty1.

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
in [ref-conventions.md](ref-conventions.md). Build `c_clock` as a separately instantiable
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

## Open questions

**Every unresolved question in the project lives here or in [plan-tests.md](plan-tests.md).**
The `ref-*` documents state what is known and mark uncertainty with ⬜, but they carry no plans —
when something there is unverified, the work to resolve it is listed below.

### Blocking a v0.2 phase

| Question | Blocks | Where it stands |
|---|---|---|
| **SP-404 pad note range** — measured 47+*n* here, Roland's chart says 35–51 | Phase 5, and v0.3's `m_404` | Only pads 1 and 2 were ever checked. **This is the one that silently corrupts work** — sequencing code written against the wrong range looks correct and triggers the wrong pads. Sweep all 16 with `tools/midi-drive.pd` |
| **Launchpad perimeter CC numbers** | Phase 6 | Documented 📄, never confirmed on this unit. Ten minutes with `tools/lp-monitor.pd` |
| **Do flashing / pulsing LEDs track a *modulated* tempo?** | Phase 6 | The modes work ✅; tracking a sweeping tempo is ⬜. Needs a patch that sweeps tempo |
| **Full-load power** | Phase 6 | Never run with three controllers plus the wifi dongle — the cable shortage. Presents as intermittent MIDI dropouts rather than an obvious failure, so if Phase 6 produces flaky Launchpad behaviour, **suspect the hub before the code**. [plan-tests.md](plan-tests.md) item 5 |
| **Save New in a category folder** | Phase 8 | ⚠️ Already diagnosed — see the Phase 8 note above. Verify against a menu-selected patch, not a deploy-loaded one |

### The last thing that could force a redesign

**How the 404 places external input in the stereo field.** ✅ The Organelle's own TRS split is
verified — `adc~ 1` is the tip and the channels are independent — but the 404's *internal*
routing of its external input is not, and no cable will answer it. Blocked on the TRS Y-cable;
procedure in [plan-tests.md](plan-tests.md) Session 3, items 12–13.

### Not blocking anything, but worth knowing

| Question | Where it stands |
|---|---|
| **Can Pd emit an OSC blob?** | Gates `gWaveform` and `gFrame` — so it gates ever drawing the captured buffer, which is what would stop playhead placement being blind. Untested ⬜ |
| **Does the 404's *pattern playback* transmit notes?** | `SEQ Note Out` is On and pad presses transmit, but no pattern has been captured. Determines whether the 404 is a compose-time authoring surface. Watch for the reported stray continuous C |
| **Can Novation Components disable the onboarding drive?** | A cleaner fix than the `mount.sh` guard, since it changes nothing on the Organelle. Untried |

### Stage-readiness — the phone link

Everything about the PdParty display works ✅ except what makes it trustworthy in a venue.
Phase 7 or later:

- **Organelle as its own access point.** `hostapd` and `dnsmasq` are installed and the chip
  supports AP mode ✅, but it has never been configured ⬜. It removes the venue-WiFi dependency
  and is the last thing between the phone display and being stage-worthy.
  [plan-tests.md](plan-tests.md) Session 5 — read its warning first, since bringing up an AP
  drops SSH.
- **Rate limiting on the wire.** Every CC change currently sends a packet, so a fast fader sweep
  floods. Needs coalescing to ~20 Hz with a guaranteed trailing edge. The OLED gets this free
  because layers hold state; the phone link does not.
- **Phone hardening.** Auto-Lock Never ✅; Do Not Disturb and Guided Access still to set.
- **Cosmetic.** The value is an `nbx`, which draws box chrome around the number; a `cnv` label
  through `[makefilename %g]` would be pure text. Dynamic labels are proven ✅.

### Still to acquire

| Item | For |
|---|---|
| **1/4" TRS male → 2× 1/4" TS male** (insert cable) | ⚠️ **The critical cable in the rig** — nothing else merges the 404's two outs into the Organelle's single input jack. Blocks Session 3 |
| **Class-compliant USB→DIN MIDI interface** | The Volca FM. Roland UM-ONE mk2 in its class-compliant "TAB" position, iConnectivity mio, or similar |
| **Dynamic microphone** | Dynamic rather than condenser — better SPL handling and far better feedback behaviour in a rig where a mic feeds a processor that feeds the PA |

Ordinary cables — USB-A→C for the 404, TS patch cables, 3.5mm TRS→2× TS for the Volca,
XLR→1/4" for the mic — are probably already in the box; the full list is in
[ref-hardware.md](ref-hardware.md). **Optional:** a *MeeBlip cubit duo* replaces the MIDI
interface and the original cubit in one box, worth it only if more DIN synths arrive. Don't buy
a ground-loop isolator pre-emptively — but know it is the cause if hum appears, rather than
chasing a bad cable.

### Deliberately deferred

| Deferred | Why |
|---|---|
| **The four filter stages** | v0.3 — this plan is the floor they stand on |
| **Footswitch / expression pedal** | `mother.pd` exposes `fs` and `exp` on the pedal jack, one or the other, not both. Noted so it isn't rediscovered as news; it stays the obvious control to reach for when both hands are busy |
| **SP-404 and Volca mapping** | `m_404` and the DIN interface, which isn't bought |
| **Compose-mode capture** | Needs the mode system working first |
| **nanoKONTROL scenes** | Four scenes exist but switch locally, so Pd is never told — hidden state. If they are ever used, assign **distinct CC numbers per scene** so Pd infers the active one from which CCs arrive |
| **A pre-set checklist for the 404** | Its hidden menu state — ExtIn monitoring, bus assignments, input FX — is the remaining "wrong knob" risk in the rig |

---

## Risks

**The `m_` layer is the one boundary that is genuinely expensive to retrofit.** If `e_chop` ever
learns that a nanoKONTROL exists, that is permanent.

**The display arbiter was the piece most likely to be wrong first time** — contention, TTL and
rate limiting are easy to describe and fiddly to tune. Built early (Phase 3) precisely so there
was time to live with it; now verified on hardware.

**Timing is architectural.** Grain clocks must be audio-domain from the first line, and
`u_tempo` must be a master reference *plus* an instantiable `c_clock`, not a singleton.
Retrofitting either once Phases 6–8 depend on them is the expensive mistake this plan exists to
avoid.
