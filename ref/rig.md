<!-- schema: freeform -->
# The rig — boxes, cables and signal flow

**The physical instrument.** What connects to what, why, and the handful of hardware facts that
decide the shape. What each *device* can do is on its own page under [device/](device/); what the
Organelle is as a *computer* — SSH, paths, deploying, wifi — is in
[ref-hardware.md](../ref-hardware.md).

The Organelle is the brains: it runs the patch, hosts every controller over USB, and is **clock
master** for the whole rig. The SP-404MK2 is the sample store and the front end — it holds the drum
and fx samples, takes the mic and any arbitrary input, and feeds **two independent mono streams**
into the Organelle.

⛔ **Two channels through one stereo cable is the trick that makes this work.** The Organelle has a
single 1/4" TRS input jack, so the 404's L and R arrive as the **tip** and the **ring**.

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
                                                     │ (receive only)│
                                                     └───────────────┘
```

**Why no MIDI merge box.** Pd namespaces each input device into its own block of 16 channels, so
**which device a message came from is free information**. A merge box would flatten everything into
one stream and throw that away. `MAXMIDIINDEV` is 16 in Pd — verified in both 0.49 and 0.53 source —
so four devices is nowhere near the limit.

The ALSA wiring, the port map and the channel blocks are on [boot.md](module/boot.md).

**The Launchpad runs over USB.** Its TRS MIDI jacks go unused and the three TRS→DIN adapters in its
box are not needed here. USB gives it its own 16-channel block, keeps Programmer Mode on the
documented path, and means one cable does both power and data — at the cost of hub current, which is
what the powered hub is for.

⚠️ **Disable clock-out on every other device**, particularly the 404's **MIDI Sync Out**, which will
otherwise echo clock back and create a loop.

⚠️ **Keep sending clock — it is not decorative.** The 404's **BPM SYNC time-stretch follows its
tempo**, and the only way it learns the tempo is by measuring incoming clock intervals. Stop the
clock and it stretches to a stale local value.

## Signal flow — audio

```
  [mic] ──────────────► SP-404 MIC/GUITAR IN  (1/4" TRS, mono)
  [arbitrary source] ─► SP-404 LINE IN

                    ┌───────────────────────────────┐
                    │        SP-404MK2              │
                    │  drum samples → pan MONO L    │
                    │  fx samples   → pan MONO R    │
                    │  use BUS 1/2 only             │
                    └────────┬─────────────┬────────┘
                        OUT L│             │OUT R
                      (drums)│             │(fx)
                             ▼             ▼
                    ╔════════ Y-CABLE (2×TS → 1×TRS) ════════╗
                                     │
                    ┌────────────────▼──────────────┐
                    │  ORGANELLE   IN (TRS stereo)  │
                    │    tip  = drums  → [r~ inL]   │
                    │    ring = fx     → [r~ inR]   │
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

**Organelle L/R go to the two MONO channels (1 and 2)**, not a stereo pair, so drums and fx each get
their own 3-band EQ and one-knob compressor.

### The jack asymmetry is why the Y-cable is required

📄 Quoted from the official Organelle 1 manual:

> The single `In`(put) `LR` port is a 1/4" TRS (stereo) jack.
> The `L`(eft) and `R`(ight) `Out`(put) ports are both 1/4" TS (mono) jacks.

**One stereo input jack, two mono output jacks.** The 404's two discrete mono outputs have to merge
into one input; the output side needs only two ordinary patch cables.

### The input split is verified on hardware

✅ The **tip** is `inL` and the **ring** is `inR`, and they are genuinely independent — a mono TS
cable drives the tip to the 90s on `env~`'s scale while the ring stays at the 18–19 noise floor.
Measured with `tools/audio-probe/`; item 11.

Two numbers worth remembering: the **input noise floor is ~18–19** on `env~`'s 0–100 dB scale
(≈ −82 dBFS), so a noise gate belongs around **25–30**; and a **passive bass reaches the 90s**, so
there is ample gain and headroom for instrument-level sources.

⛔ **A patch never touches `adc~` or `dac~`** (C-4). See [audio.md](module/audio.md).

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

⛔ **Do not bus-power the 404.** Roland requires USB-C-to-C at 5V/1.5A for bus power and does not
guarantee operation through hubs. A USB-A→C cable from the hub carries **data only**, which is what
we want — the 404 runs off its own adapter and costs the hub nothing.

## Gear

| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Roland SP-404MK2 | Sample store, mic/line front end, drums + fx source |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Korg nanoKONTROL (mk1) | Continuous control — 9 faders, 9 knobs, 18 buttons, transport |
| Novation Launchpad Pro MK3 | Cut It interface (Programmer Mode) + compose-time sequencing |
| MeeBlip cubit (original) | Kept, unused — see below |
| Arturia BeatStep | **Retired from the plan** — see below |

### The original cubit does not work here

It is a **thru box only**: 1 DIN in → 4 DIN out. Its USB port supplies **power only and carries no
data**, so it cannot act as a USB MIDI interface for the Organelle. That capability came later, in
the cubit *go* and cubit *duo*.

**Keep it.** It becomes useful the moment a second or third DIN-only synth arrives — put it
downstream of the MIDI interface and fan out to four destinations. Today only the Volca needs DIN, so
a 1×1 interface is enough.

### The BeatStep is retired

Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps × 8-note poly vs 16 steps mono), its
16 pads are beaten comprehensively by 64 RGB pressure-sensitive ones, and its CV/Gate outputs are
irrelevant with no modular in the rig.

It does have host-controllable pad LEDs (red, on/off) which the nanoKONTROL mk1 lacks — **the one
axis where it wins.** But the Launchpad covers every state-display need in the rig, and visible knob
position plus a bank of faders is worth more here than a second grid of red lights.

### The pedal jack is deliberately unused

`mother.pd` exposes `fs` / `fsRaw` / `footSwitchPolarity` and `exp` / `expRaw` / `expOverride` on the
1/4" pedal jack — a sustain-style switch **or** an expression pedal, one or the other, not both.
Recorded so it is not rediscovered as news.

## Cabling

**What is still to buy is in [plan-v03.md](../plan-v03.md)** under *Still to acquire*; power supplies
are all covered.

| Cable | Connects |
|---|---|
| **1/4" TRS male → 2× 1/4" TS male** ("insert cable") | 404 OUT L/R → the Organelle's single stereo input. ⚠️ **The critical cable in the rig** — nothing else does this job |
| **USB-A → USB-C** | Hub → SP-404MK2, **data only**. The 404 ships without one |
| **2× 1/4" TS** | Organelle OUT L/R → mixer ch1/ch2 |
| **3.5mm TRS → 2× 1/4" TS** | Volca FM → mixer ch3/4. ⚠️ Its output runs hot — start with channel gain low |
| **XLR female → 1/4" TRS** | Mic → 404 MIC/GUITAR IN. The 404 has no XLR, so a plain mic cable will not do it; an adapter on a normal one works |
| **2× 1/4" TS** | Mixer MAIN OUT → PA |

**Already in the box, do not buy:** the Launchpad ships with USB-C→USB-A *and* USB-C→USB-C cables, a
power adapter and 3× TRS-minijack→DIN MIDI adapters; the nanoKONTROL is bus-powered over its own
cable; the 404 has its PSD adapter.

⚠️ **Label the cables.** With this many identical 1/4" jacks it is worth the ten minutes.

## Open

- ⬜ **The only routing that depends on a menu rather than a cable is on the 404** — ExtIn
  monitoring, bus assignments, input FX. A pre-set checklist for that box is deferred; see
  [plan-v03.md](../plan-v03.md) §4.
- ⬜ **Organelle audio back into the 404 was considered and dropped**, using the mixer's FX send as a
  variable-gain feedback path. It needs no rewiring beyond one cable from FX SEND. See
  [plan-v03.md](../plan-v03.md) §4.
