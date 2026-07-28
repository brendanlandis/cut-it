# Cut It — Design Notes

How the instrument works: architecture, timing model, and the decisions behind them.

Companion to [rig-plan.md](rig-plan.md), which covers the physical rig — boxes, cables,
signal flow, and verified device behaviour. The rule of thumb: **if it describes what the
hardware does, it's in the rig plan; if it describes what we decided to build, it's here.**

See also [README.md](README.md) for musical intent and the control layout, and
[CLAUDE.md](CLAUDE.md) for the hard constraints on writing Pd for this device.

---

## Interface design

### Launchpad — three tiers, and you only build the top one

Programmer Mode is all-or-nothing: entering it disables every built-in mode. But **Pd can
switch layouts by SysEx** (header `F0 00 20 29 02 0E`, with a layout-select command and a
separate Programmer/Live switch), so modes are something you flip between, not something you
choose once.

| Tier | What | Work | LED control |
|---|---|---|---|
| **Built-in** (Note, Chord, Sequencer, Projects) | Novation's, fully featured | **None** | Device owns them |
| **Custom Modes** — 8 slots, built in Novation Components | Drag-and-drop widgets: scaled keyboards, drum grids, virtual faders. Pads send Note / CC / Program Change | Moderate, no code | Limited — one "on" colour per mode, per-pad "off" colours |
| **Programmer Mode** | Everything from scratch | Most | Full dynamic RGB |

**Do not rebuild these.** Note mode's scale tables, root selection and isomorphic layout
maths are genuinely fiddly in Pd and Novation's are good. Chord mode is worse to replicate.
The Sequencer is 4 tracks × 32 steps × 8-note poly with pattern chaining — a substantial
project on its own, and it is already the compose-time authoring tool. Projects handles
save/recall of that sequencer data.

**The tier 2/3 boundary is dynamic colour.** Custom Modes allow only one "on" colour per
mode, so static colour-coding works but "empty / loaded / queued / playing" as four distinct
states does not. The pattern launcher needs Programmer Mode; a plain CC grid or a scaled
keyboard does not.

Novation Components needs a computer (web app over WebMIDI, or standalone) — you cannot
author Custom Modes from the Organelle, but once written they persist on the device.

**Risk:** entering Programmer Mode *by SysEx* locks out the Settings menu until Pd sends a
SysEx selecting another layout. If Pd dies mid-set you are power-cycling the Launchpad. Bind
a "return to Live mode" message somewhere reachable.

### Grid idioms worth stealing

The conventions grid controllers have converged on, and what each maps to here:

| Idiom | What it is | Use for Cut It |
|---|---|---|
| **Clip launching** (Session) | Columns = tracks, rows = scenes. Blinks when queued, solid when playing. Right column fires a whole row | **The pattern launcher.** Columns = destinations (404 drums, Volca, internal), rows = variations. Inherits the queued/playing visual convention free |
| **Drum rack** | 4×4 quadrants of velocity-sensitive trigger pads | **Four filter quadrants**, arranged right-to-left to match the signal chain. 16 pads per filter vs the 5–7 keys currently on the Organelle keyboard |
| **Isomorphic note layout** | Fixed interval per row, scale-locked | Playing the Volca — use built-in Note mode, don't rebuild |
| **Step sequencing** | Row = track, column = step | Compose-time authoring — use built-in Sequencer |
| **Column-as-fader** | Press higher = higher value. 8 steps of resolution | Coarse parameter control if the nano runs out |
| **X/Y pad** | Pad coordinates set two parameters at once | **Chop Shop's drunkenness + sputter.** A 4×4 block = 16 positions over both. Slapping a corner is a different gesture than turning two knobs |
| **Radio buttons** | A row as exclusive mode select, lit | Filter selection |
| **Pure display** | Grid as output only | Playhead position, which sample slots are filled |

**Pressure is the forgotten input.** Grain size, chop intensity, filter depth — any of these
can ride pad pressure while held. Costs no panel space and is the most expressive control on
the rig.

The README says the controls *"will take some practice and memorization."* The RGB grid is
the direct antidote to half of that: which filters are on, which of the five sample slots are
filled, which pattern is queued, where the playhead is — all visible rather than memorised.

### Division of labour

Nothing overlaps:

- **Launchpad** — pads, grid state, and compose-time sequencing. Anything needing state you
  can see.
- **nanoKONTROL** — continuous control, with position visible on the panel. Momentary
  buttons only.
- **Organelle keyboard** — note entry at compose time; filter control at perform time.


---

## Signal architecture

### Drums and fx split across the 404's L/R
Per-sample pan on the 404 runs from MONO(Left) through to MONO(Right). Hard-pan drum
samples left and fx samples right and you get two independent mono streams out of one
stereo pair.

- **Master FX break this.** BUS 3/4 are master effects applied to the whole mix and will
  bleed across the split. Use per-sample BUS 1/2 effects only.
- **Both channels are mono.** Stereo samples fold down. Acceptable; a future "stereo mode"
  in the patch could drop drums and process fx in stereo instead.

### Mic goes into the 404, and bleeds into both channels
The 404's MIC/GUITAR IN is a mono input and sums to **both** outputs. There is no pan
control for the external input. So live vocals appear on the drums channel as well as the
fx channel.

This is accepted deliberately — the alternative was splitting the mic through the mixer's
FX send, which is more cables and more unlabelled knob state to get wrong mid-set.

Consequences:
- **Upside:** the vocal arrives dry via the drums path and mangled via the fx path at the
  same time. That is the standard dry/wet vocal setup, for free.
- **Watch:** the vocal will also be captured into any drums-channel sampler. Sing while
  Cut It grabs a drum buffer and your voice is baked into it. Handle at capture time — a
  "don't record into drum buffers" toggle, or just don't arm drum capture while the mic is
  hot. Cheap now, annoying to retrofit.
- Once a vocal is **sampled** to a pad it behaves like any other sample and can be panned
  hard right. Only live passthrough bleeds.

### No routing depends on a knob position
Deliberate. The 404's per-sample pans are saved with the project and recall. Cables carry
the signal paths. The mixer's knobs only set levels — and a wrong level is audible
immediately rather than failing silently.

The remaining hidden state is all on the 404 (ExtIn monitoring, bus assignments, input FX),
which lives in menus. **Build a pre-set checklist for that box specifically.**

### Organelle audio back into the 404 — dropped
Considered and dropped for now. Would have used the mixer's FX send as a variable-gain
feedback path. Revisit later if wanted; it needs no rewiring beyond one cable from FX SEND.


---

## Timing and tempo

### Tempo is freely modulable, but propagates unevenly
Because the Organelle *generates* the clock, tempo is just a float in the patch.
[midiclock.pd](midiclock.pd) already has the plumbing (`r tempo` → `tempo $1 permin` →
`metro`). Route any CC to `s tempo` and a nanoKONTROL knob becomes tempo control. Tap
tempo, an LFO, a pad — all the same.

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
tempo. See the correction in [rig-plan.md](rig-plan.md) under *Signal flow — MIDI*.

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

**Three storage decisions worth making early:**

1. **Normalise to one device-agnostic event format.** Sources have wildly different shapes
   (Launchpad 4×32 at 8-note poly, keyboard free-played). Capture everything as
   `time, note, velocity, duration` and nothing downstream cares what authored it.
2. **Decouple capture source from playback destination.** Channel offsets tell you what a
   pattern was recorded *from*; that should not determine where it plays *to*. Bake it in and
   you have permanently made something "a Launchpad pattern".
3. **Store as plain text files in the repo.** `text define` + `text write` in vanilla Pd. The
   payoff is patterns that are git-diffable and editable in a text editor alongside the patch.


---


## Patch development notes

- **Organelle 1 runs Pd 0.49.** Develop in **vanilla Pd 0.49**, not the latest.
- **OS history for Organelle 1:** OS 4.0 brought Organelle M features back to the original and
  is what updated its Pd to 0.49 (before that it was on 0.46 under OS 3.x). **4.1 is the last
  version for Organelle 1** — 4.2 is M/S only, and OS v5 supports M/S/S2 only. **This unit
  reports OS 4.0**, so 4.1 is available as an upgrade if ever needed.
- Pd is 0.49 on every Organelle-1-compatible OS from 4.0 onward, so the target doesn't move.
- **Do not save Organelle-bound patches from plugdata.** plugdata is based on Pd 0.55+ and
  writes hex iemgui colours (`#fcfcfc`) that Pd 0.49 cannot parse. The `cut-it 2` working
  copy already has `main.pd` rewritten into this format — revert it before use on hardware.
- Nothing in the patch currently needs anything newer than Pd 0.43, so 0.49 costs nothing.
- **Grain timing must be audio-domain.** At 256th notes (~7.8ms at 120 BPM) Pd's message
  clock is quantised to a 64-sample block (~1.45ms), which is ~20% jitter per grain. Drive
  grain clocks from `phasor~` and envelopes from `vline~`, not `metro`/`line~`.
- **MIDI clock is 24 PPQN** — a pulse every 20.8ms at 120 BPM, coarser than a 256th note.
  You cannot count pulses to get there. Estimate tempo from the clock, run a free-wheeling
  audio-domain oscillator at the derived frequency, and resync phase per beat or bar.
- BPM-mode and MS-mode are a *units* choice, not two clock engines. Normalise both to Hz
  (`bpm/60 × subdivisions` or `1000/ms`) and feed one `phasor~`.
