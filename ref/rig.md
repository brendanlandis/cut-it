<!-- schema: freeform -->
# The rig — boxes, cables and signal flow

**The physical instrument.** What connects to what, why, and the handful of hardware facts that
decide the shape. What each *device* can do is in Reference (`~/Sites/!reference/`); how Cut It uses it is on its page under [device/](device/); what the
Organelle is as a *computer* — SSH, paths, deploying, wifi — is in
[device-os.md](device-os.md).

The Organelle is the brains: it runs the patch, **plays the drums** (`c_kit`,
[module/sequencer.md](module/sequencer.md)), hosts every controller over USB, and is **clock
master** for the whole rig. **The mic goes straight into its one input jack**, on the tip, with no
preamp (2026-11-04). **The SP-404MK2 has left the rig** (Brendan, 2026-11-04) — see below.


## Signal flow — audio

```
  [SM58] ── XLR → TS ──► ORGANELLE IN  (1/4" TRS: a TS plug is the tip)

                    ┌───────────────────────────────┐
                    │  ORGANELLE   IN (TRS stereo)  │
                    │    tip  = mic   → [r~ inL]    │
                    │    ring = none  → [r~ inR]    │
                    │  ─────── Cut It ───────       │
                    │  input passed through         │
                    │  c_kit: the drums → outL      │
                    └───────┬───────────────┬───────┘
                PHONES L (tip)│               │PHONES R (ring)
                            ▼               ▼
                    ┌──────────────────────────────────┐
                    │  XENYX Q802USB                   │
                    │   ch1  Organelle L (drums, mic)  │
                    │   ch2  Organelle R               │
                    │   ch3/4  Volca FM                │
                    │   ch5/6  spare                   │
                    └────────────────┬─────────────────┘
                                     ▼  MAIN OUT
                                   [ PA ]
```

**Organelle L/R go to the two MONO channels (1 and 2)**, not a stereo pair, so each gets its own
3-band EQ and one-knob compressor. Today the drums and the mic share channel 1.

⛔ **They leave by the Organelle's ⅛" headphone jack, split to two TS plugs, not by its 1/4" outs.**
Into the mixer's line input, the 1/4" L out sounded far thinner, with harsh transients when turned
up; the headphone jack sounded about as good as the 404's own headphone jack into the same channel
(by ear, 2026-11-02). It matches a forum report about the Organelle's line outs; see the Organelle's
Reference page. A single stereo plug into one mono channel would not do: that channel is mono, and its
balanced TRS input would hear left minus right.

⚠️ **The mic needs the input's whole gain**, and Cut It sets it at every load: `Capture` 15 with the
−6 dB attenuator off ([audio.md](module/audio.md), *The codec's gains*). **Until Cut It has loaded
once after a power-on, the input has the factory's gain**, 10.5 dB lower, so a patch loaded first
hears the mic that much quieter.

### The input split is verified on hardware

✅ The **tip** is `inL` and the **ring** is `inR`, and they are genuinely independent (the measurement, taken with
`tools/audio-probe/`, is in Reference, item 11).

The noise floor and the gate window that follows from it are on
[module/audio.md](module/audio.md), item 11 — one place, because three pages used to write the
number out.

⛔ **A patch never touches `adc~` or `dac~`** (C-4). See [audio.md](module/audio.md).

## Signal flow — power

```
  power strip
    ├── ORGANELLE ........ 9VDC 1000mA center-positive   (included)
    ├── XENYX Q802USB .... own PSU                       (included)
    ├── POWERED USB HUB .. own PSU                       (comes with hub)
    │     ├── Launchpad Pro MK3
    │     ├── nanoKONTROL
    │     └── USB→DIN MIDI interface
    └── VOLCA FM ......... Korg KA-350 9V (or 6×AA)
```

### There is no shared rail for a brownout to happen on — items 5 and 95

✅ **Read off the device rather than reasoned about** — item 255. Every box has its own mains supply
(the tree above), and the powered hub is self-powered, so it draws nothing from the Organelle. Each
device's declared `MaxPower` is on its Reference page, the hub's on
`~/Sites/!reference/powered-usb-hub.md`, and the wifi dongle's (450 mA, on its own root bus) on the
Organelle's.

**~700 mA through one self-powered hub is not a budget problem**, and item 248 had already
exonerated power empirically from the other direction: the Launchpad failed to configure *with almost
nothing attached* and configured *with the entire rig live*, so it was never a current ceiling.

⚠️ **The one genuine shared rail is the Organelle's own supply, and the wifi dongle is on it.** The
dongle sits on a **separate root bus from the powered hub**, so its declared 450 mA comes out of the
9 V 1000 mA adapter rather than the hub's PSU. **Whether that contributes to the wifi fault is
untested — see *Open* below.**

### ⛔ There is one physical hub, and `lsusb` makes it look like three

**Item 256.** The hub holds three hub controllers in one box, and the SP-404 added one of its own
while it was in the rig, so `lsusb -t` shows a chain that is not on the desk. How to tell them apart, and which controller each
socket hangs off, is on `~/Sites/!reference/powered-usb-hub.md`. ⛔ **So the Launchpad's fault is NOT
depth and NOT chaining**: the socket that fails and the one that works are on the same box.

### The Launchpad goes in the lock-icon socket

⛔ **`can't set config #1, error -32`, and it is per-socket** — what it looks like and what was ruled
out are on `~/Sites/!reference/novation-launchpad-pro-mk3.md` (item 248), and which sockets are which
on the hub's page. On this rig the Launchpad works in **the bottommost socket, the one with the lock
icon**, on the hub's Realtek controller.

⚠️ **The fix is a labeled socket, not a topology rule.** Put the Launchpad in the lock-icon port and
mark it, because nothing in the patch can tell a half-enumerated Launchpad from an absent one.

⛔ **A Launchpad that half-enumerates is invisible to the patch.** `lsusb` lists it but no ALSA port
is ever created, so `m_launchpad`'s recovery runs `wire.sh` and gives up after ~70 s, because there
is nothing to wire to. From inside Cut It it is indistinguishable from a Launchpad that was never
plugged in. ⚠️ **This is a venue failure mode**, and the only thing that distinguishes it from a dead
patch is the OLED.

## Gear

| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Powered USB hub | Connects the controllers, on its own supply (`~/Sites/!reference/powered-usb-hub.md`) |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB (`~/Sites/!reference/behringer-xenyx-q802usb.md`) |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Korg nanoKONTROL (mk1) | Continuous control — 9 faders, 9 knobs, 18 buttons, transport |
| Novation Launchpad Pro MK3 | Cut It interface (Programmer Mode): the pages, and the drum page's sequencing |
| MeeBlip cubit (original) | Kept, unused — see below |
| Roland SP-404MK2 | **Left the rig on 2026-11-04** — see below |
| Arturia BeatStep | **Retired from the plan** — see below |

### The original cubit does not work here

It is a thru box only with no USB data (Reference: `~/Sites/!reference/meeblip-cubit.md`), so it cannot
act as a USB MIDI interface for the Organelle.

**Keep it.** It becomes useful the moment a second or third DIN-only synth arrives — put it
downstream of the MIDI interface and fan out to four destinations. Today only the Volca needs DIN, so
a 1×1 interface is enough.

### The SP-404 has left the rig

Brendan took it out on 2026-11-04. It had been the rig's drum machine and its audio front end; that
day the drums moved into Pd, `c_kit` playing the sequencer's samples
([module/sequencer.md](module/sequencer.md)), and the mic went straight into the Organelle, so nothing
in Cut It needs it. Its layer, `m_404`, went with it, along with its map destination, the phone's
test 404 button and its presence on the diag roster. What it is: `~/Sites/!reference/roland-sp-404mkii.md`.

**Its MIDI slot, Pd's port 3 (channels 33–48), is wired to nothing**, and reserved for the Waldorf
Streichfett ([module/boot.md](module/boot.md), *The ALSA wiring*).

### The BeatStep is retired

Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps × 8-note poly vs 16 steps mono), its
16 pads are beaten comprehensively by 64 RGB pressure-sensitive ones, and its CV/Gate outputs are
irrelevant with no modular in the rig. What it is: `~/Sites/!reference/arturia-beatstep.md`.

Its one win is host-controllable pad LEDs, which the nanoKONTROL mk1 lacks. But the Launchpad covers
every state-display need in the rig, and visible knob position plus a bank of faders is worth more here
than a second grid of red lights.

### The pedal jack is deliberately unused

The Organelle's pedal jack (Reference) takes a sustain-style switch **or** an expression pedal, one or
the other, not both. Recorded so it is not rediscovered as news.

## Cabling

**What is still to buy is in [plan-v04.md](../plan-v04.md)** under *Still to acquire*; power supplies
are all covered.

| Cable | Connects |
|---|---|
| **⅛" TRS male → 2× 1/4" TS male** | Organelle headphone jack → mixer ch1 (tip: the drums and the mic) and ch2 (ring). Not the 1/4" outs: see above |
| **3.5mm TRS → 2× 1/4" TS** | Volca FM → mixer ch3/4. ⚠️ Its output runs hot — start with channel gain low |
| **XLR female → 1/4" TS** | The SM58 → the Organelle's input, on the tip. Unbalanced, so keep it short |
| **2× 1/4" TS** | Mixer MAIN OUT → PA |

**Already in the box, do not buy:** what each device ships with is on its Reference page — the
Launchpad's cables and adapters, the nanoKONTROL's own cable.

⚠️ **Label the cables.** With this many identical 1/4" jacks it is worth the ten minutes.

## Open

- ⬜ **Whether the wifi dongle's draw contributes to the wifi fault — item 255.** A step on
  `cut-it/wifi-roam-fault`, to be taken only if the fault recurs. It is the only thing on the
  Organelle's own 9 V 1000 mA rail, declaring 450 mA on a separate root bus from the powered hub.
  ⚠️ **A hypothesis and nothing more**: `MaxPower` is a declared maximum, the adapter has headroom
  on paper, and no drop has ever been correlated with load. The one trial worth making — the dongle
  on the powered hub — carries item 256's hazard.
