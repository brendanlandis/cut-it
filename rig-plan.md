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
                  ▼            ▼ mini-USB▼ USB-A→C   ▼
        ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌───────────────┐
        │ LAUNCHPAD    │  │BEATSTEP │  │SP-404MK2 │  │ USB→DIN MIDI  │
        │ PRO MK3      │  │         │  │          │  │ INTERFACE     │
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
loop. Set BeatStep to Ext Sync.

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
    │     ├── BeatStep
    │     └── USB→DIN MIDI interface
    └── VOLCA FM ......... Korg KA-350 9V (or 6×AA)
```

**Do not bus-power the 404.** Roland requires USB-C-to-C at 5V/1.5A for bus power and does
not guarantee operation through hubs. A USB-A→C cable from the hub carries **data only**,
which is what we want — the 404 runs off its own adapter and costs the hub nothing.


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


## Patch development notes

- **Organelle 1 runs Pd 0.49** (OS 3.1, its final OS — C&G dropped Organelle 1 from OS v5).
  Develop in **vanilla Pd 0.49**, not the latest.
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


## Gear

### Owned
| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Roland SP-404MK2 | Sample store, mic/line front end, drums + fx source |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Arturia BeatStep | Knobs + drum sequencing |
| Novation Launchpad Pro MK3 | Custom Cut It interface (Programmer Mode) |
| MeeBlip cubit (original) | **See below — does not do what we need** |

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
| 1 | **Powered USB hub**, 4+ USB-A ports, own PSU | Not optional. The Launchpad Pro MK3 is a real power draw; bus-powering it plus the BeatStep off the Organelle will brown out, and it presents as intermittent MIDI dropouts rather than an obvious failure. |
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
- **BeatStep**: its mini-USB cable.
- **SP-404MK2**: PSD AC adapter (but no USB cable — see item 5).

### Optional / probably eventually
- **MeeBlip cubit duo** — replaces item 2 *and* your original cubit in one box (USB MIDI
  interface + 4-port thru, switchable, class compliant, tight timing). Worth it if you
  expect to add more DIN synths; overkill for one Volca.
- **Ground loop isolator** — five separately-powered devices tied together by unbalanced
  cables makes 50/60Hz hum likely. Don't buy pre-emptively, but know this is the cause if it
  appears, rather than chasing a "bad cable".
- **Cable labels or tape.** With this many identical 1/4" cables, worth the ten minutes.
