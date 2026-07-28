# Cut It — Rig Plan

Hardware setup plan for the Cut It instrument. Companion to [README.md](README.md), which
covers the Pd patch itself.

Target hardware: **Organelle 1** (the original, not M/S/S2).

---

## Overview

The Organelle is the brains. It runs the Cut It patch, acts as USB MIDI host for every
controller, and is the clock master for the whole rig.

The SP-404MK2 is the sample store and the front end. It holds drum samples and fx samples,
takes the mic and any arbitrary audio input, and feeds two independent mono streams into
the Organelle — drums on the left, fx on the right. Cut It captures and mangles what
arrives, and its two outputs go to the mixer.

Two channels through one stereo cable is the trick that makes this work: the Organelle has
a single 1/4" TRS input jack, so the 404's L and R arrive as `adc~ 1` and `adc~ 2`.


## Signal flow — MIDI

Everything is USB. The Organelle is a USB host; all four devices are class compliant.

```
                  ┌──────────────────────────────────┐
                  │  ORGANELLE                       │
                  │  Pd / Cut It — CLOCK MASTER      │
                  └────────────────┬─────────────────┘
                                   │ USB-A
                  ┌────────────────▼─────────────────┐
                  │       POWERED USB HUB            │
                  └──┬─────────┬─────────┬────────┬──┘
          USB-A→C ┌──┘         │         │        └──┐ USB-A
                  ▼            ▼ USB-A   ▼ USB-A→C   ▼
        ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌───────────────┐
        │ LAUNCHPAD    │  │ nano    │  │SP-404MK2 │  │ USB→DIN MIDI  │
        │ PRO MK3      │  │ KONTROL │  │          │  │ INTERFACE     │
        │ ch 1–16      │  │ch 17–32 │  │ ch 33–48 │  │ ch 49–64      │
        └──────────────┘  └─────────┘  └──────────┘  └───────┬───────┘
                                                             │ DIN
                                                             ▼
                                                     ┌───────────────┐
                                                     │  VOLCA FM     │
                                                     │  (receive only)│
                                                     └───────────────┘
```

**Why no MIDI merge box.** Pd namespaces multiple MIDI input devices by channel: device 1
gets channels 1–16, device 2 gets 17–32, and so on. `notein`'s right outlet and `ctlin`'s
channel outlet tell you which device a message came from, for free. A merge box would
flatten everything into one stream and throw that away.

`MAXMIDIINDEV` is 16 in Pd (verified in both 0.49 and 0.53 source), so four devices is
nowhere near the limit.

**Setup task:** Pd only opens the MIDI devices it is told to at launch. The Organelle's Pd
startup flags will need `-midiindev 1,2,3,4` and matching `-midioutdev`.

**Direction:** the Organelle is clock master. Disable clock-out on every other device —
particularly the 404's "MIDI Sync Out", which will otherwise echo clock back and create a
loop.

Note that under the compose/perform split (below), nothing external runs its own sequencer
during a performance, so outgoing MIDI clock is close to decorative. Keep sending it, but
nothing critical should depend on it.

**The Launchpad runs over USB.** Its TRS MIDI jacks go unused, and the three TRS→DIN
adapters in its box aren't needed here. USB gives it its own 16-channel block, keeps
Programmer Mode on the documented path, and means one cable does both power and data — at
the cost of the hub current, which is what the powered hub is for.


## Signal flow — audio

```
  [mic] ──────────────► SP-404 MIC/GUITAR IN  (1/4" TRS, mono)
  [arbitrary source] ─► SP-404 LINE IN

                    ┌───────────────────────────────┐
                    │        SP-404MK2              │
                    │  drum samples → pan MONO L    │
                    │  fx samples   → pan MONO R    │
                    │  use BUS 1/2 only (see below) │
                    └────────┬─────────────┬────────┘
                        OUT L│             │OUT R
                      (drums)│             │(fx)
                             ▼             ▼
                    ╔════════ Y-CABLE (2×TS → 1×TRS) ════════╗
                                     │
                    ┌────────────────▼──────────────┐
                    │  ORGANELLE   IN (TRS stereo)  │
                    │    adc~ 1  = drums  (tip)     │
                    │    adc~ 2  = fx     (ring)    │
                    │  ─────── Cut It ───────       │
                    └───────┬───────────────┬───────┘
                       OUT L│               │OUT R
                            ▼               ▼
                    ┌──────────────────────────────────┐
                    │  XENYX Q802USB                   │
                    │   ch1  Organelle L  (drums)      │
                    │   ch2  Organelle R  (fx)         │
                    │   ch3/4  Volca FM                │
                    │   ch5/6  spare                   │
                    └────────────────┬─────────────────┘
                                     ▼  MAIN OUT
                                   [ PA ]
```

Organelle L/R go to the two **mono** channels (1 and 2) rather than a stereo pair, so drums
and fx each get their own 3-band EQ and one-knob compressor.


## Signal flow — power

```
  power strip
    ├── ORGANELLE ........ 9VDC 1000mA centre-positive   (included)
    ├── SP-404MK2 ........ Roland PSD adapter            (included)
    ├── XENYX Q802USB .... own PSU                       (included)
    ├── POWERED USB HUB .. own PSU                       (comes with hub)
    │     ├── Launchpad Pro MK3
    │     ├── nanoKONTROL
    │     └── USB→DIN MIDI interface
    └── VOLCA FM ......... Korg KA-350 9V (or 6×AA)
```

**Do not bus-power the 404.** Roland requires USB-C-to-C at 5V/1.5A for bus power and does
not guarantee operation through hubs. A USB-A→C cable from the hub carries **data only**,
which is what we want — the 404 runs off its own adapter and costs the hub nothing.


## Control surfaces

The two controllers have very different capabilities, and the difference should drive which
functions live where.

### Launchpad Pro MK3 — a genuine blank slate

**Physical layout.** An 8×8 grid of RGB pads, surrounded by large function buttons on the
left, right and top, plus a double row of smaller buttons across the bottom. Left column
selects modes (Session, Note, Chord, Custom, Sequencer, Projects); right column is scene
launch; top row is navigation; bottom rows are track select and Ableton controls. In
Programmer Mode all of that labelling becomes meaningless — every button is just a note
number you define.

The pads are **velocity *and* pressure sensitive** (polyphonic aftertouch). They are not
switches.

**Programmer Mode** is officially documented (Novation publishes a
[Programmer's Reference Manual](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/LPP3_prog_ref_guide_200415.pdf)),
not a hack. In it:

- All built-in modes are disabled. The firmware gets out of the way completely; every pad
  just sends note-on/note-off.
- You drive every LED yourself. Note-on to a pad's note number, velocity selects from a
  128-colour palette. SysEx gives full RGB.
- Static / flashing / pulsing are MIDI channels 1 / 2 / 3 — so blinking a pad costs one
  message, no timing logic in Pd.
- Note layout is row/column encoded: pad at row *r*, column *c* is note `r*10+c` (11–88).
  `div 10` and `mod 10` gets you coordinates, no lookup table.
- Entering it is either a button combo (hold SETUP, press the bottom Scene Launch) or a
  SysEx message. Documented gotcha: entering via SysEx locks out the Settings menu until
  you send a SysEx selecting a different layout.

Unit is a **MK3** (MK3 announced Jan 2020; a 09/2020 build date rules out MK1). Use the MK3
reference — SysEx headers and side-button note numbers differ from MK1.

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

### nanoKONTROL (mk1) — visible position, no host LEDs

Replaces the BeatStep (see *BeatStep retired*, below). 9 channels, each with **1 fader,
1 knob, 2 buttons**, plus a transport section and 4 on-device scenes. Class compliant,
USB bus-powered.

**The fit is good:** 9 knobs + 9 faders = 18 continuous controls against Cut It's 16.
**Two channels per filter** gives 2 knobs + 2 faders — exactly the four per filter — across
8 channels, leaving **one channel spare** for global volume or master tempo.

**The win over endless encoders is visible position.** A knob's physical position *is* the
display, which is the legibility problem the BeatStep could never solve.

**The cost is parameter pickup.** Any control serving two parameters stops matching its
stored value on a bank switch. The primary layer avoids this entirely via the 1:1 mapping,
but the shift layer still doubles up. Options are jump (snaps, jarring), pickup (dead until
it crosses the old value) or scaled. **Use jump** — a sudden parameter jolt is entirely on
brand here, so the usual reason to avoid absolute controllers mostly does not apply.

**No host-controllable LEDs.** External LED mode is a nanoKONTROL2-only feature; on the mk1
the button LEDs reflect local state only and Pd cannot drive them.

**Therefore: set every button to momentary** in Korg Kontrol Editor, and let Pd own all
toggle state, displayed on the Launchpad. A toggle button with no host LED control keeps its
own state, and that state can silently desync from Pd's — exactly the invisible-failure mode
the FX-send routing was rejected over. Momentary buttons are pure events with no state to
desync.

**On the four scenes:** useful for multiplying control count, but they are hidden state — the
device switches locally and Pd has no idea. Assign **distinct CC numbers per scene** so Pd
infers the active scene from which CCs arrive. Do that and scene switching self-announces;
don't, and it is the unlabelled-knob problem in a worse form.

**Risk:** Korg Kontrol Editor is 2008-era software and you need it for the momentary setting
and CC assignments. Verify it runs on your machine before committing — legacy Korg editors
have been rough on recent macOS. If it won't run, the nano is stuck with whatever is
currently written to it.

### BeatStep retired

Dropped from the plan. Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps ×
8-note poly vs 16 steps mono), its 16 pads are beaten comprehensively by 64 RGB
pressure-sensitive ones, and its CV/Gate outputs are irrelevant with no modular in the rig.

It does have host-controllable pad LEDs (red, on/off) which the nanoKONTROL mk1 lacks — the
one axis where it wins. But the Launchpad covers every state-display need in the rig, and
visible knob position plus a bank of faders is worth more here than a second grid of red
lights.

### Division of labour

Nothing overlaps:

- **Launchpad** — pads, grid state, and compose-time sequencing. Anything needing state you
  can see.
- **nanoKONTROL** — continuous control, with position visible on the panel. Momentary
  buttons only.
- **Organelle keyboard** — note entry at compose time; filter control at perform time.


## Design decisions and their consequences

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

### SP-404 MIDI — verified working, both directions
Confirmed on hardware, no settings changes required. The 404's factory MIDI config is
already correct for this rig.

**Receive (404 → Pd):** pad presses and knob moves arrive on **Pd channel 33** (device 3).
Pads transmit notes, CTRL knobs transmit CC 16 and 17.

**Send (Pd → 404):** `[noteout 33]` triggers pads. **Pad *n* on bank A = note 47 + *n***
(pad 1 = 48, pad 2 = 49), established empirically. Velocity 100 works; `[makenote]` handles
note-offs.

**Relevant device settings, all already correct:**

| Setting | Value | Why |
|---|---|---|
| MIDI Sync Out | Off | No clock echoed back to the Organelle |
| Soft Through | Off | No MIDI echo loop |
| USB-MIDI Thru | Off | Same |
| PAD Note Out | On | Pads transmit |
| SEQ Note Out | On | Pattern sequencer transmits — enables compose-time capture |
| MIDI Mode | A | Bank A receives on MIDI channel 1 |

**Cable warning:** the 404 needs a genuine **data** USB cable. Charge-only USB-A→C cables are
visually identical and extremely common; two were tried before one worked. If the device does
not appear in `lsusb`, suspect the cable before anything else.

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


## Open questions to verify on the hardware

1. **Organelle's actual Pd version** — `pd -version` on the device, or via the Pd console.
2. **Pd startup flags** — where the Organelle OS sets them, to add `-midiindev`.
3. **USB enumeration stability.** Pd assigns device numbers in enumeration order and the
   channel offsets follow. If order shifts between reboots, every `route` silently rotates.
   Either pin with udev rules or have the patch identify devices by message signature.
   Test this early.
4. **How the 404 places external input in the stereo field — and whether it can be pinned
   to one side.** This is the load-bearing unknown for the whole drums/fx split. The claim
   that a mono input sums to both sides comes from user documentation, not Roland's spec
   sheet, and nothing I could find documents whether it can be constrained.

   One test session answers it. Monitor the 404's L and R outputs separately (headphones,
   or the mixer with one channel at a time), play a sample panned hard MONO(Left), and:

   - **a.** Feed the **MIC/GUITAR IN**. Does the mic appear on the L output alongside the
     drum sample? Expected: yes, it sums to both. If it doesn't, the accepted bleed
     compromise is unnecessary and the design gets simpler.
   - **b.** Look for **any pan or routing control for the external input** — input FX
     settings, bus assignment, anything that shifts it off centre.
   - **c.** Feed **LINE IN R only**, nothing in L/MONO. Does the signal stay on the right,
     or sum to both? Its partner jack being labelled L/MONO is suggestive but not
     conclusive. A "stays right" result opens up the mic → mixer preamp → LINE IN R path,
     which would give hard-panned live vocals through the 404's input FX.

   Outcome (a) confirms the plan as written. Outcomes (b) or (c) would be upgrades, not
   requirements — the rig works either way.

5. **Does the 404's pattern playback emit MIDI notes?** It has MIDI out and can sequence
   external gear, but whether pattern playback transmits note data for its own pads is
   undocumented, and there are reports of a stray continuous C-note when external input is
   on. Determines whether the 404 is usable as a compose-time authoring surface. Low stakes
   — filter the stray note on capture if needed.

6. **Does Korg Kontrol Editor still run on your machine?** Needed to set the nanoKONTROL's
   buttons to momentary and assign per-scene CCs. 2008-era software; legacy Korg editors
   have been rough on recent macOS. If it won't run, the nano is stuck with whatever is
   currently written to it.


## Gear

### Owned
| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Roland SP-404MK2 | Sample store, mic/line front end, drums + fx source |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Korg nanoKONTROL (mk1) | Continuous control — 9 faders, 9 knobs, 18 buttons, transport |
| Novation Launchpad Pro MK3 | Cut It interface (Programmer Mode) + compose-time sequencing |
| MeeBlip cubit (original) | **See below — does not do what we need** |
| Arturia BeatStep | **Retired from the plan** — see *BeatStep retired* above |

### The original cubit does not work here
The original cubit is a **thru box only**: 1 DIN in → 4 DIN out. Its USB port supplies
**power only and carries no data**, so it cannot act as a USB MIDI interface for the
Organelle. (That capability came later, in the cubit *go* and cubit *duo*.)

Keep it. It becomes useful the moment you add a second or third DIN-only synth — put it
downstream of the MIDI interface and fan out to four destinations. For now only the Volca
FM needs DIN, so a 1×1 interface is enough.


## Shopping list

Power supplies are all assumed covered. Everything below is either a box you don't own or a
cable to dig for first.

### Definitely buy — hardware you don't have

| # | Item | Notes |
|---|---|---|
| 1 | **Powered USB hub**, 4+ USB-A ports, own PSU | Not optional. The Launchpad Pro MK3 is a real power draw; bus-powering it plus the other USB devices off the Organelle will brown out, and it presents as intermittent MIDI dropouts rather than an obvious failure. |
| 2 | **Class-compliant USB→DIN MIDI interface** | For the Volca FM. Roland UM-ONE mk2 (set to the class-compliant "TAB" position), iConnectivity mio, or similar. |
| 3 | **Dynamic microphone** | SM58 or equivalent. Dynamic rather than condenser — better SPL handling and far better feedback behaviour, and you're building a rig where a mic feeds a processor that feeds the PA. |

### Cables — check the cable box first

Most of these are ordinary. Item 4 is the one you probably don't already have.

| # | Cable | For | Likely already own? |
|---|---|---|---|
| 4 | **1/4" TRS male → 2× 1/4" TS male** ("insert cable") | 404 OUT L/R → Organelle's single stereo input | ⚠️ **Unlikely.** The critical cable in the whole rig — nothing else does this job. |
| 5 | **USB-A → USB-C** | Hub → SP-404MK2 (data only) | Probably. The 404 ships with no USB cable, but these are everywhere now. |
| 6 | **2× 1/4" TS patch cables** | Organelle OUT L/R → mixer ch1/ch2 | Probably |
| 7 | **3.5mm TRS → 2× 1/4" TS** | Volca FM → mixer ch3/4 | Maybe. Volca's output runs hot — start with channel gain low. |
| 8 | **XLR female → 1/4" TRS** | Mic → 404 MIC/GUITAR IN | Maybe. The 404 has no XLR, so a plain mic cable won't do it. An XLR→1/4" adapter on a normal mic cable also works. |
| 9 | **2× 1/4" TS** | Mixer MAIN OUT → PA | Probably. Length to suit the venue. |

### Already in the box with gear you own — don't buy
- **Launchpad Pro MK3**: USB-C→USB-A *and* USB-C→USB-C cables, a USB-A power adapter, and
  3× TRS-minijack→DIN MIDI adapters.
- **nanoKONTROL**: bus-powered over its own USB cable — check which connector the mk1 uses
  before assuming you have a spare.
- **SP-404MK2**: PSD AC adapter (but no USB cable — see item 5).

### Optional / probably eventually
- **MeeBlip cubit duo** — replaces item 2 *and* your original cubit in one box (USB MIDI
  interface + 4-port thru, switchable, class compliant, tight timing). Worth it if you
  expect to add more DIN synths; overkill for one Volca.
- **Ground loop isolator** — five separately-powered devices tied together by unbalanced
  cables makes 50/60Hz hum likely. Don't buy pre-emptively, but know this is the cause if it
  appears, rather than chasing a "bad cable".
- **Cable labels or tape.** With this many identical 1/4" cables, worth the ten minutes.
