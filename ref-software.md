# Cut It — Design Notes

How the instrument works: architecture, timing model, and the decisions behind them.

Companion to [ref-hardware.md](ref-hardware.md), which covers the physical rig — boxes, cables,
signal flow, and verified device behaviour. The rule of thumb: **if it describes what the
hardware does, it's in the rig plan; if it describes what we decided to build, it's here.**

See also [ref-midi.md](ref-midi.md) for the MIDI message reference,
[ref-conventions.md](ref-conventions.md) for how the Pd is actually written,
[README.md](<! v0.1 plans/README.md>) for musical intent and the v0.1 control layout, and
[CLAUDE.md](CLAUDE.md) for the hard constraints on writing Pd for this device.

---

## Architecture — what the patch is made of

✅ **Current as of v0.2 complete.** Every box below exists on hardware. The allowlist in
[ref-conventions.md](ref-conventions.md) is the authority on which buses exist; this is the
shape they connect.

```
                             main.pd
                          (wiring only)
                                |
                              u_root
                                |
   ┌──────────┬──────────┬──────┴─────┬──────────┬──────────┐
   │          │          │            │          │          │
 u_init    u_tempo     u_err       u_state    u_net      u_level
 startup   clock +     errors      the data   the phone  meters
 order     transport               store         │
   │          │          │            │          │
   └──────────┴────┬─────┴────────────┴──────────┘
                   │
              global buses
  mode · tempo · clock · start/stop · panic · param · err · disp · state
                   │
   ┌───────────────┼───────────────┬───────────────┐
   │               │               │               │
 m_nano       m_launchpad     m_organelle       m_404            ← device mapping,
 ch 17          ch 1          aux + knobs 1-4   ch 33-42            INPUT side
   │               │               │               │
   └───────────────┼───────────────┴───────────────┘
                   │
                 u_map  ←── cut-it-map.txt         ← the ONLY file that says
                   │        <mode> <control>          what a control MEANS.
                   │        <dest> <arg>              Table-driven since v0.3,
                   │                                  guarded by a literal route
       ┌───────────┴───────────┐
       │  CORDS, not a bus     │                   ← output devices are TOLD
    m_404                  m_volca                    what to play. No bus
    ch 33-42               ch 49                      carries that.
    pad <n> <vel>          notes/cc/program
                   │
            (v0.4: e_chop, e_pitch, e_trem, e_verb)
                   │
   ┌───────┬───────┴───────┬───────────┐
 g_oled  g_led          g_grid       u_net         ← the four display surfaces
 OLED    aux LED        Launchpad    phone
```

**Two things the diagram cannot show, and both are load-bearing:**

- **`c_clock` is instantiated, not global.** `u_root` holds `c_clock 1 8` driving the grid's beat
  row, and **nothing downstream may assume the global `clock` is its clock** — Cut It runs
  poly-tempo. See *Timing and tempo* below.
- **`u_state` owns two `u_store` instances**, one per persistence policy.

**The `m_` layer is the load-bearing boundary.** Nothing below it knows a nanoKONTROL exists. A
device publishes a **named control** on `param`; what that control *means* is decided in `u_map`,
above everything it controls. This is what makes the compose/perform split tractable, and it is
the one boundary that is genuinely expensive to retrofit.

### Why the infrastructure was built before any DSP

Three constraints made the usual "get a sound out, then tidy up" approach expensive here, and all
three were borne out:

1. **There is no console.** Errors vanish. Anything not built to report itself is invisible, and
   retrofitting reporting across an existing patch is far worse than designing it in. `u_err`
   exists because of this.
2. **The device mapping layer is the expensive thing to retrofit.** Compose and perform give the
   same physical controls different meanings. If `e_chop` ever learns about the nanoKONTROL, that
   is permanent.
3. **Timing is architectural.** Grain clocks must be audio-domain from the first line, not
   converted later.

---

## Load-bearing decisions

The four that shape everything else. Reasoning for each is further down this file.

- **Grain timing must be audio-domain.** Pd's message clock is quantised to a 64-sample block
  (~1.45 ms), which is ~20% of a 256th note at 120 BPM. Drive grain clocks from `phasor~` and
  envelopes from `vline~` — never `metro` / `line~` at grain rate. ✅ Built in Phase 5:
  `u_tempo` and `c_clock` are `phasor~` from the first line.
- **Pd sequences everything.** Timing rides in note events, not MIDI clock. No external device
  runs its own sequencer during a performance.
- **Two independent input channels.** `inL` = drums (the tip), `inR` = fx (the ring), arriving
  from the SP-404's hard-panned L/R via a TRS Y-cable into the Organelle's single stereo input
  jack. ✅ Verified. A patch never touches `adc~` — `mother.pd` owns the sound card. The v0.1
  README still describes a single serial chain over one input; that predates this decision.
- **Compose mode and perform mode are separate.** Both the Launchpad and the Organelle's own
  keyboard serve different roles in each, so this shapes the top level of the patch.

---

## Interface design

### The Launchpad

**Moved** to [ref/device/launchpad.md](ref/device/launchpad.md) — the three-tier decision and how Cut It uses the
surface are in that page's *Design* section. The grid idioms it would enable are v0.4 intent and
live in [plan-v03.md](plan-v03.md) §7.

### Division of labour

Nothing overlaps:

- **Launchpad** — pads, grid state, and compose-time sequencing. Anything needing state you
  can see.
- **nanoKONTROL** — continuous control, with position visible on the panel. Momentary
  buttons only.
- **Organelle keyboard** — note entry at compose time; filter control at perform time.


---

## Signal architecture

### The 404 carries the audio split

Drums hard-panned left, fx hard-panned right — two independent mono streams out of one stereo
pair, and the mic sums to both. **The measurements, the hardware path for setting the pan and the
traps around it are on [ref/device/sp404.md](ref/device/sp404.md)**; what follows is the design consequence.

### No routing depends on a knob position
Deliberate. The 404's per-sample pans are saved with the project and recall. Cables carry
the signal paths. The mixer's knobs only set levels — and a wrong level is audible
immediately rather than failing silently.

The remaining hidden state is all on the 404 (ExtIn monitoring, bus assignments, input FX),
which lives in menus — the one "wrong knob" risk left in the rig. A pre-set checklist for that
box is deferred in [plan-v03.md](plan-v03.md).

### Organelle audio back into the 404 — dropped
Considered and dropped for now. Would have used the mixer's FX send as a variable-gain
feedback path. Revisit later if wanted; it needs no rewiring beyond one cable from FX SEND.


---

## Timing and tempo

### Tempo is freely modulable, but propagates unevenly
Because the Organelle *generates* the clock, tempo is just a float in the patch. ✅ Anything may
write the `tempo` bus — a knob, a tap tempo, an LFO, a pad — and `u_tempo` consumes it. **Which
control does the writing is a `u_map` decision and lives in exactly one route branch**; today it is
the Organelle's own knob 1. (v0.1's `midiclock.pd` did this with `r tempo` → `tempo $1 permin` →
`metro`; Phase 5 rewrote it audio-domain. Reference for intent, not code to lift.)

**But MIDI clock has no tempo message.** You change the *rate* of the 24 PPQN pulse stream,
and slaved devices infer tempo by measuring pulse intervals, most averaging over several
pulses. So:

- Gradual changes track fine everywhere.
- Instant jumps take several pulses to propagate; large ones can make the 404 or Volca
  stutter or briefly drop sync.

**Consequence: internal and external timing diverge under fast modulation.** The Organelle's
own grain clocks are `phasor~`-based — changing frequency is instant and glitch-free, phase
simply continues. Slaved gear lags several pulses behind. Modulate tempo quickly and the
Organelle is somewhere the 404 hasn't reached yet.

For this instrument that is arguably a feature — controlled drift between sampler and drums
is a real effect. But know which you are building:

- **Tempo knob** — gradual, everything follows.
- **Per-grain tempo chaos** — Organelle-only, external gear will not follow.

Keep changes gradual, or quantise them to bar boundaries, when tight sync matters.

**Related limitation:** Pd sends MIDI on block boundaries, so outgoing clock carries ~1.45ms
of jitter — about 7% of a pulse interval at 120 BPM. Most gear averages it away. If the
Volca ever feels loose against the Organelle's internal timing, that is why, and it is not
readily fixable in vanilla Pd.

**Largely moot under the compose/perform split.** If nothing external runs its own sequencer
during a performance, there is nothing to propagate to and tempo is completely free. This
section matters mainly at compose time, where quantise-on-capture handles it anyway.

### Grain timing is cut from the same phase as the MIDI clock ✅ built

**24 PPQN is far too coarse to count grains from** — a pulse every 20.8 ms at 120 BPM, coarser
than a 256th note. An earlier draft of this file proposed the receiver's solution: estimate tempo
from the pulse stream, free-wheel an oscillator at the derived frequency, resync per beat. **That
is not this rig's problem.** The Organelle *is* the master, so there is nothing to estimate.

What Phase 5 built instead runs the derivation the other way. One `phasor~` at BPM ÷ 60 × 24 is the
pulse train; the MIDI byte and the beat are both **cut from that one phase** by counting, so they
cannot drift apart by construction. Grain-rate code reads the same phase as a *signal* rather than
being handed beat events. Each grain clock, sequencer or sampler owns a `c_clock` instance at its
own ratio, rebuilt from the identical arithmetic so equal rates land in the same logical instant —
✅ measured at **0.000000 ms** worst-case difference against master over a whole run.

⚠️ **Audio-domain does not mean sample-accurate MIDI.** `threshold~` reports on a 64-sample block
boundary exactly as `metro` fires on one, so the ~1.45 ms jitter above is unchanged. What it buys is
glitch-free phase-continuous rate changes and one shared phase. The full construction, the pulse
ceiling and the debounce trap are in [ref-midi.md](ref-midi.md).

### Timing rides in note events, not in clock
MIDI clock's weakness is structural: it transmits a *rate* the receiver must infer by
measuring intervals. A note-on needs no inferring — it is an event at a moment.

So **Pd sequences everything.** Drive note-outs from the same `phasor~` that drives the grain
clocks, and the 404 never needs to know the tempo at all. Drum timing becomes exactly as
accurate as internal timing, including tempo modulation that provably cannot work over clock.

| Approach | Tempo behaviour |
|---|---|
| **Pd sequences, sends notes** | Tight. Modulate as violently as you like |
| **Device sequencers synced to clock** | Must infer tempo. Lag and drift under modulation |

✅ **Now measured, and the numbers argue the same way.** The SP-404 will only follow an external
clock between **40 and 200 BPM** — sweep past either end and it pins there while the Organelle
carries on. Cut It's own range is 10–500. So clock-following cannot cover the instrument's range
even in principle, and anything outside 40–200 has to arrive as note events or not at all.
[plan-tests.md](plan-tests.md) item 65.

Pd's note output still carries the ~1.45ms block quantisation, so this is not sample
accurate. But it is fixed absolute jitter rather than compounding inference lag, and it is
inaudible at trigger rates. The fastest timing — grain chopping — never leaves the Organelle
anyway, since it happens to audio already captured.

### Time-stretch: two engines, and when each wins

A sample tagged 92 BPM can be played at 70 or 112. Two mechanisms can do that, and they fail
in opposite directions.

**The 404's BPM SYNC** stretches playback to match the bank/project tempo. It is a per-sample
toggle and works on any triggered pad — the sequencer does not need to be running, because it
references a stored tempo value rather than a playing pattern.

Its limitation is how it learns the tempo. The SP-404MK2 has **no SysEx at all** (Roland's
MIDI implementation chart marks System Exclusive `x` in both directions) and no Song Position
Pointer. Clock ticks are the only channel, so tempo is always *inferred* from pulse intervals
and always lags by several pulses. That lag is structural — there is no message that would
let you skip the inference.

**Pd's granulator** stretches by decoupling grain rate from grain playback rate, which is the
defining property of granular synthesis. No inference, no lag, and it follows tempo modulation
sample-accurately.

Its limitation is that **it can only stretch what it has already captured.** You cannot
compress a bar you have not finished hearing. A 92 BPM loop played at 112 must be heard once
at 92 before it can be fitted into a shorter bar — one pass of warmup, inherent to real-time
capture, the same property every hardware looper has.

| Situation | Engine | Warmup |
|---|---|---|
| Tempo set and left there (92 → 70, 92 → 112) | **404 BPM SYNC** | None — it has the file on disk |
| Tempo drifting gradually | **404 BPM SYNC** | None; tracks clock with a few pulses' lag |
| Tempo modulating faster than clock inference can follow | **Pd granulator** on captured fragments | One pass |

So the split is by **how fast the tempo moves**, not by loop-versus-fragment. Pd's stretch
earns its keep only in the third row — where the 404 physically cannot follow, and where you
are chopping fragments rather than playing coherent bars, so a pass of warmup costs little.

**Samples stay on the 404.** Cut It granulates *captured audio*, never sample files, so
nothing has to be duplicated onto the Organelle. And only the sampler stage captures at all —
the filter, tremolo and reverb stages process live audio passing through, so a loop playing
out of the 404 with BPM SYNC never needs recording.

**Known limit:** a loop that must follow violent tempo movement *from bar one* can't be done
either way — the 404 can't track it and Pd hasn't heard it yet. That case would force sample
files onto the Organelle. Noted rather than designed around, since it is a narrower want than
it first appears.

**Consequence for the rig:** MIDI clock must keep flowing, because it is how the 404 learns
tempo. See the correction in [ref-hardware.md](ref-hardware.md) under *Signal flow — MIDI*.

### Author on hardware, commit to Pd
Device sequencers stay useful as *authoring* tools. Record their MIDI output into Pd, then
play it back from Pd's clock.

Vanilla Pd has `seq` for this (records raw MIDI with timestamps, reads/writes MIDI files),
but a custom recorder on `text` is probably better — it lets you store note, velocity, step
and source separately, and edit them afterward.

**Quantise on capture.** The device sequencer runs off the slightly-loose MIDI clock while
authoring, but that does not matter: you are capturing *which step*, not exact microtiming.
Snap incoming events to the grid on the way in and the sloppy authoring clock becomes
irrelevant. Playback is then Pd's timing.

| Source | Capturable? | Notes |
|---|---|---|
| **Launchpad** | ✅ | 4 tracks, 32 steps, 8-note poly. Built-in Sequencer mode |
| **Organelle keyboard** | ✅ | Free-played note entry |
| **SP-404MK2** | ✅ | `SEQ Note Out: On` in the device's MIDI settings makes the pattern sequencer transmit notes. `PAD Note Out: On` transmits pad presses. Both verified arriving in Pd |
| **Volca FM** | ❌ | **MIDI IN only — no MIDI out at all.** Its sequencer output cannot be captured. The FM2 added MIDI out; the original did not have it |

Author Volca parts on the Launchpad and have Pd play them into the Volca — which is what the
plan does anyway. You just don't get its own step buttons as an authoring surface.

**The upside:** once a pattern lives in Pd it stops being locked inside a device. It becomes
data, subject to the same drunkenness, sputter and chop parameters as everything else. A
captured loop played back at a wandering tempo with random step-skipping is a more
interesting object than the device sequencer could produce alone.

### Compose time and perform time are separate modes
Sequences get built and saved *before* a performance; the performance refers back to them.
This dissolves three problems at once:

- **The Launchpad mode conflict evaporates.** Authoring uses Note/Chord/Sequencer; performance
  uses Programmer Mode. They never coexist, so no mid-set SysEx flipping.
- **Tempo propagation stops mattering** — see above.
- **The 404's murky MIDI out becomes low-stakes.** A stray continuous C is an offline
  annoyance you filter on capture, not a live failure.

**What it forces: the patch needs explicit compose and perform modes.** Both the Launchpad
*and* the Organelle's own keyboard are double-booked — the keyboard is four filter groups
during performance and a note-entry surface during composition. Design this in from the
start; it is much easier than retrofitting once the filter logic exists.

⚠️ **The six modes in `u_map` are placeholders, but their RATIO is not arbitrary.** `u_err` routes
on `compose` / `perform`, so **a split weighted toward `perform` would make most mode selections
silently quieten the error display.** Anyone renaming or re-balancing them needs to know that
before they start — it is the kind of change that looks cosmetic and is not.

**Three storage decisions worth making early:**

1. **Normalise to one device-agnostic event format.** Sources have wildly different shapes
   (Launchpad 4×32 at 8-note poly, keyboard free-played). Capture everything as
   `time, note, velocity, duration` and nothing downstream cares what authored it.
2. **Decouple capture source from playback destination.** Channel offsets tell you what a
   pattern was recorded *from*; that should not determine where it plays *to*. Bake it in and
   you have permanently made something "a Launchpad pattern".
3. **Store as plain text files.** `text define` + `text write` in vanilla Pd, so patterns stay
   git-diffable and editable in a text editor. ⚠️ **They do not live in the repo, and this point
   used to say they did.** ✅ Phase 8 settled where: `/sdcard/cut-it-state/` on the device,
   *outside* the patch folder, with `tools/fetch-state.sh` copying it back here. The instrument
   writes to somewhere a deploy cannot erase; the repo gets a backup, not the original.


---

The hard constraints on writing Pd for this device — the permanently-0.49 target, the plugdata
hazard, vanilla-only — are in [CLAUDE.md](CLAUDE.md). How the Pd is actually written is in
[ref-conventions.md](ref-conventions.md).
