# Cut It — MIDI Reference

Every MIDI message that moves in this rig: what each device accepts, what each device
transmits, and how it lands in Pd.

Companion to [ref-hardware.md](ref-hardware.md) (the boxes and cables),
[ref-software.md](ref-software.md) (what we decided to build) and
[plan-tests.md](plan-tests.md) (how the verified claims were verified).

**Confidence markers** are used throughout, and they matter — several claims in this
project's history turned out wrong when checked:

| | |
|---|---|
| ✅ | Verified on this hardware. Test recorded in [plan-tests.md](plan-tests.md). |
| 📄 | From the manufacturer's own documentation. Not yet confirmed on this unit. |
| ⬜ | Unknown, assumed, or inferred. Do not build on it without checking. |

---

## The addressing model

Two numbering schemes cover the whole rig. Learn these and everything else is detail.

### 1. Device → Pd channel block

Pd namespaces each MIDI input device into its own block of 16 channels. Device *n* occupies
channels `(n-1)*16+1` through `n*16`. `notein`'s right outlet and `ctlin`'s third outlet
report the channel, so **the device a message came from is free information** — no merge box,
no SysEx device IDs, no guessing. **This file owns the addressing model**;
[ref-hardware.md](ref-hardware.md) covers the physical side of the same arrangement.

✅ **"Device *n*" means Pd's INPUT SLOT, not the device's position in the system MIDI list.**
Measured both ways: the nanoKONTROL showed as system device 1, then as device 2 once an audio
interface was plugged in, and opening it with `-midiindev 2` still put it on **channel 1** — because
it was Pd's *first opened* input. On the Organelle the slots come from `/root/.pdsettings`, which is
what fixes the nano at 17. On the Mac, plugging in other gear changes *which system device you pick*
to fill slot 1; it does not change the channel. This is why `m_nano` takes the block as a creation
argument, and why `main.pd` passes 17 while `main-dev.pd` passes 1.

✅ **`ctlin` fires channel, then controller, then value** — right to left, and *measured* rather
than assumed, because this repo has been bitten here before by `polytouchin`. **Cold stores behind
`ctlin` are therefore safe.** The evidence is [plan-tests.md](plan-tests.md) item 23.

| Pd device | Hardware | Channel block | Device's own ch. 1 lands on | |
|---|---|---|---|---|
| 1 | Launchpad Pro MK3 | 1–16 | 1 | ✅ |
| 2 | nanoKONTROL | 17–32 | 17 | ✅ |
| 3 | SP-404MKII | 33–48 | 33 | ✅ |
| 4 | USB→DIN interface → Volca FM | 49–64 | 49 | ⬜ interface not purchased |

`MAXMIDIINDEV` is 16 in Pd, so four devices is nowhere near the ceiling. Pd is configured for
4 in / 4 out in `/root/.pdsettings` with `midiapi: 1`. ✅

**Keep the Launchpad as device 1.** Its lighting modes are MIDI channels 1/2/3, and only at
device 1 do those coincide with Pd channels 1/2/3 — `[noteout 1]` means what Novation's
documentation says it means. Move it to device 2 and every LED message needs +16.

### 2. Control → CC number, by tens

Both hand-operated surfaces address controls as `tens digit = kind, units digit = which`, so
one decode pattern covers both:

```
        [ctlin]
           |
    [t f f]  →  [div 10]  →  what kind of control
           →  [mod 10]  →  which one
```

- **Launchpad grid:** note `r*10+c`, rows and columns both 1–8, so notes 11–88. ✅
- **nanoKONTROL:** CC `kind*10 + channel`, kinds 0–3. ✅

This was deliberate, and the transport buttons extend it — `div 10` = **4** means transport.
See *Transport buttons* under the nanoKONTROL below.

---

## Organelle 1

**The Organelle's own panel is not MIDI.** Keys, knobs, encoder, aux button and the OLED all
arrive as ordinary Pd messages from `mother.pd`, on named sends and receives. Nothing about
the front panel is addressable over MIDI, and no CC number will ever reach it. This is the
single most important thing to know about the device's control surface.

The Organelle 1 is a USB **host** only. It has no USB-device port, so it never appears as a
MIDI device to anything else. All MIDI in this rig is Pd talking to the four attached
controllers.

### mother.pd interface

✅ **The full name list is enumerated from `/root/fw_dir/mother.pd` itself** — every `[s]` and
`[r]` in the file — and lives in [ref-conventions.md](ref-conventions.md) under *The global
name allowlist*, because those names are reserved rather than merely documented. In summary:
`notes`, `knob1`–`knob4`, `enc`, `encbut`, `aux`, `vol`, `exp`, `fs`, the MIDI-gate names and
`quitting` come **in**; `screenLine1`–`5`, `led`, `goHome`, `oscOut` and `enableSubMenu` go
**out**.

Two things that surprise people: **`enc`, `aux` and `encbut` send `1`/`0`, not `±1`** ✅, and
`quitting` is the only shutdown hook — Pd 0.49 has no `closebang`.

Organelle 1 and Organelle M differ here, and the public `Organelle_OS` repo documents the M, so
that enumeration is the authority rather than the repo.

### MIDI out from Pd

Raw System Real-Time bytes go straight out `[midiout]` as decimal floats ✅ — demonstrated in
v0.1's `midiclock.pd`, archived in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>).
**Reference for which byte went where, not code to lift**; `u_tempo` is a rewrite in Phase 5.

| Message | Decimal | Hex |
|---|---|---|
| Timing Clock | 248 | `F8` |
| Start | 250 | `FA` |
| Continue | 251 | `FB` |
| Stop | 252 | `FC` |

Clock is **24 PPQN** — 24 pulses per quarter note, one every 20.8 ms at 120 BPM.

### How Cut It generates it ✅ built

`u_tempo` owns it, and the construction is worth stating because it is not the obvious one:

| | |
|---|---|
| BPM ÷ 60 × 24 → **`[phasor~]`** at the pulse rate | 48 Hz at 120 BPM |
| **`[threshold~ 0.5 2 0.1 2]`** → one bang per cycle | the phasor crosses 0.5 once per ramp and falls below 0.1 on the wrap |
| every pulse emits **248** and increments a counter | `[mod 24]` = 0 is the beat, published on `clock` |
| **out on Pd MIDI ports 1 and 3** | the Launchpad and the SP-404 — `Pure Data:4` and `Pure Data:6`, already in `wire.sh` |

**Counting the pulses rather than running a second oscillator is what makes the beat and the MIDI
pulse the same clock by construction.** ✅ Measured on the Mac under real DSP: 6 beats in 3 s at
120 BPM, 3 in 3 s at 60 — [plan-tests.md](plan-tests.md) item 48.

⚠️ **Audio-domain does not fix the jitter, and never could.** `threshold~` reports on a 64-sample
block boundary exactly as `metro` fires on one, so the ~1.45 ms below is unchanged. What it buys
is a rate change that is phase-continuous and glitch-free, and **one phase that grain-rate code
reads as a signal**, so MIDI clock and grain timing cannot drift apart. Anyone who reads "audio
domain" as "sample-accurate MIDI" will waste a day.

**The transport bytes:** `start` → 250, `stop` → 252, `panic` → 252 plus All Notes Off.
**Never 251** — nothing in the rig has Song Position Pointer, so a Continue would be a lie.

⚠️ **The clock keeps running when the transport stops**, and that is deliberate: 248 flows
whether or not anything is playing, and only 250/252 mark transport. Stop the stream and the 404
stretches every sample to whatever tempo it last measured, so a stopped clock is a *wrong* tempo
rather than no tempo.

**A start aligns the beat grid to within half a pulse**, not to the instant. `threshold~` fires
at phase 0.5, so the first pulse after a start arrives ~10.4 ms later at 120 BPM. It is a
constant offset shared by every clock in the patch, not an error, and nothing external can see it.

**The Organelle is clock master and every other device's clock output is off.** ✅ The 404's
"MIDI Sync Out" in particular will echo clock back and create a loop if left on.

**Clock is not decorative.** It is how the 404 learns tempo for BPM SYNC time-stretch, and
how the Launchpad paces its own LED flash and pulse animations. Stop sending it and both
fall back to stale values. See *Time-stretch* in [ref-software.md](ref-software.md).

**Outgoing MIDI carries ~1.45 ms of jitter** because Pd emits on 64-sample block boundaries —
about 7% of a pulse interval at 120 BPM. Most gear averages it out. Not fixable in vanilla Pd.

---

## Novation Launchpad Pro MK3

The only device in the rig that is a genuine blank slate, and the only one Pd can light.
Runs in **Programmer Mode**, where all built-in behaviour is disabled and every button is a
note or CC number you define.

Programmer Mode is on **port 0** (`hw:3,0,0`, seq `28:0`). Ports 1 and 2 carry nothing in
either direction. ✅

### Transmits (Launchpad → Pd)

| Event | Message | |
|---|---|---|
| Pad press | Note-on, note `r*10+c`, velocity 1–127 | ✅ |
| Pad release | Note-off | ✅ |
| Pad pressure | Polyphonic aftertouch, per pad, simultaneous | ✅ |
| Function buttons | Control change, see layout below | 📄 |

Velocity is real — soft presses register as low as 10. ✅

**Polyphonic aftertouch must be enabled on the device**, and it is not the default. Hold
`Setup`, press the **third Track Select button**, choose *Polyphonic Aftertouch*; the default
is Channel Pressure, one value for the whole surface. Programmer Mode locks out the Setup
menu, so exit to Live mode first. There is an *Aftertouch Threshold* on that page worth
tuning. ✅

### Programmer Mode layout

The 8×8 grid is **verified**: pad at row *r*, column *c* is note `r*10+c`, both digits 1–8,
row 1 at the bottom. Notes 43, 44, 45, 53, 54, 55 confirmed in position. ✅

The perimeter buttons continue the same rule and are **documented but not yet confirmed on
this unit** 📄 — worth ten minutes with [tools/lp-monitor.pd](tools/lp-monitor.pd):

| Buttons | Numbers | Type |
|---|---|---|
| 8×8 grid | 11–88 (`r*10+c`) | Note ✅ |
| Top row, left→right | CC 91–98 | CC 📄 |
| Logo LED | CC 99 | CC 📄 |
| Right column (scene launch), top→bottom | CC 89, 79, 69, 59, 49, 39, 29, 19 | CC 📄 |
| Left column, top→bottom | CC 80, 70, 60, 50, 40, 30, 20, 10 | CC 📄 |
| Bottom row, left→right | CC 101–108 | CC 📄 |

### Receives (Pd → Launchpad): lighting

Two ways to light LEDs. Both address pads by the **Programmer Mode index above, always** —
even when a different layout is selected.

**1. Note-on, where velocity is a palette index.** The MIDI *channel* selects the animation:

| Channel | Mode | Pd object | |
|---|---|---|---|
| 1 | Static | `[noteout 1]` | ✅ |
| 2 | Flashing | `[noteout 2]` | ✅ |
| 3 | Pulsing | `[noteout 3]` | ✅ |

Velocity indexes a **128-entry colour palette, not brightness** — velocity 64 is a colour, not
half-lit. ✅ Velocity 0 turns the pad off.

- **Flashing alternates the channel-1 and channel-2 colours** for that pad, so send both: ch1
  sets colour A, ch2 sets colour B. ✅
- **Pulsing takes a single ch3 colour** and ramps it toward black, so it spends real time dim.
  Pick a bright palette index or it reads as weak. ✅

**Animation is free, and it is tempo-locked.** The device animates flash and pulse itself — no
`[metro]` in Pd — and synchronises them **to incoming MIDI beat clock**, falling back to
120 BPM or the last clock received. Flashing is one period per beat; pulsing is one period per
two beats. 📄 Since the Organelle is clock master, LED animation follows the patch's tempo for
nothing. ✅ for the modes working; ⬜ that they track a *modulated* tempo gracefully.

**2. Per-pad RGB SysEx**, for anything the palette can't express:

```
F0 00 20 29 02 0E 03  <type> <index> <data...>  F7
```

| Type | Lighting data |
|---|---|
| `00` | Static — 1 byte, palette entry |
| `01` | Flashing — 2 bytes, colour B then colour A |
| `02` | Pulsing — 1 byte, palette entry |
| `03` | RGB — 3 bytes: red, green, blue |

**RGB components are 0–127, not 0–255.** 📄

**One message can carry up to 106 colour specs** — the entire surface in a single SysEx. 📄
[tools/lp-flicker.pd](tools/lp-flicker.pd) currently sends one message per pad; batching is
the obvious optimisation if grid refresh ever costs too much.

### Receives (Pd → Launchpad): mode control

All share the header `F0 00 20 29 02 0E`. 📄 except as marked.

| Command | Message | Meaning |
|---|---|---|
| `0E` | `F0 00 20 29 02 0E 0E 01 F7` | Enter **Programmer Mode** ✅ |
| `0E` | `F0 00 20 29 02 0E 0E 00 F7` | Return to **Live Mode** ✅ |
| `00` | `F0 00 20 29 02 0E 00 <layout> F7` | Select layout |
| `03` | `F0 00 20 29 02 0E 03 <spec…> F7` | LED lighting (above) ✅ |
| `10` | `F0 00 20 29 02 0E 10 <mode> F7` | DAW mode (1) / Standalone (0) |
| `01` | `F0 00 20 29 02 0E 01 …` | DAW fader bank setup |
| `19` | `F0 00 20 29 02 0E 19 <bank> F7` | Stop faders for bank |

DAW mode and the fader messages are for Session-view integration and are **not used here** —
listed so they aren't mistaken for something missing.

### Three gotchas that have already cost time ✅

- **`loadbang` fires before ALSA connections exist.** Init SysEx sent on `loadbang` goes
  nowhere. Use `[loadbang] → [del 2000]` or longer.
- **LED state survives mode switches.** Entering Programmer Mode does not blank the grid. The
  patch must clear it on init.
- **`polytouchin` emits note before value**, so wiring it straight to `[noteout]` lights a pad
  with the *previous* event's pressure.

**Escape hatch:** entering Programmer Mode by SysEx locks out the Settings menu until Pd sends
a SysEx selecting another layout. If Pd dies mid-set you are power-cycling the Launchpad.
Bind "return to Live mode" somewhere reachable. ✅

---

## Korg nanoKONTROL (mk1)

9 control groups — each 1 knob, 1 slider, 2 buttons — plus 6 transport buttons and a SCENE
button. 1 IN / 1 OUT. Bus powered, ≤100 mA. 📄

**Nothing here is host-controllable.** No LED Mode setting exists on the mk1 — confirmed in
Korg Kontrol Editor, not inferred. ✅ Pd cannot light anything on this device, which is why
every button is momentary and all visible state lives on the Launchpad.

Configured with **Korg Kontrol Editor 2.4.0** — 2.5.0 dropped first-generation nanoKONTROL
support. ✅

### Transmits (nano → Pd), as configured ✅

| Control | CC | Pd channel | `div 10` | `mod 10` |
|---|---|---|---|---|
| Sliders 1–9 | 1–9 | 17 | 0 | channel |
| Knobs 1–9 | 11–19 | 17 | 1 | channel |
| Buttons, top row 1–9 | 21–29 | 17 | 2 | channel |
| Buttons, bottom row 1–9 | 31–39 | 17 | 3 | channel |
| **Transport ×6** | **41–46** | **18** | 4 | button, left to right |

All buttons are **momentary**: 127 on press, 0 on release. Pd owns all toggle state. ✅

Sliders and knobs reach a **full 0–127** — *Upper Value* / *Right Value* are not clipped. ✅

**Verified end to end**, every control decoded off the wire: all six transport buttons on
CC 41–46 in physical order on channel 18, no gaps and no reordering; control groups on
channel 17; momentary 127/0 throughout; and **no SysEx anywhere in the stream**, so nothing
emits MMC. ✅

✅ **Re-confirmed through the real patch** in Phase 4, on the Mac where the nano is slot 1:
slider 1 → CC 1, slider 9 → CC 9, knob 1 → CC 11, a top-row button → CC 23 and a bottom-row one →
CC 36, all on channel 1; PLAY → CC 42 and LOOP → CC 44 on channel 2. Momentary 127 then 0
throughout. `m_nano` decodes all of it — see [plan-tests.md](plan-tests.md) item 31.

This is a rewrite of the factory map (which put sliders on CC 2–12 and was not regular). It is
written to the device, so a factory reset destroys it — **that is REC + STOP + SCENE held at
power-on**, worth knowing so you don't do it by accident. 📄

### Receives (Pd → nano)

**Nothing musical.** The MIDI OUT port exists solely for Korg Kontrol Editor to read and write
configuration. There is no message Pd can send that changes anything visible or audible. 📄

### Scenes

Four scenes, switched locally by the SCENE button. **This is hidden state** — the device
switches and Pd is not told. If scenes are ever used, assign **distinct CC numbers per scene**
so Pd infers the active scene from which CCs arrive. Currently only scene 1 is configured. ⬜

### Transport buttons — reassigned, and ordinary CC ✅

Six buttons moved off their factory assignment, in physical reading order, **verified on the wire**:

| Position | Label | CC |
|---|---|---|
| 1st–6th | REW · PLAY · FF · LOOP · STOP · REC | **41 · 42 · 43 · 44 · 45 · 46** |

All six: Assign Type **Control Change**, Button Behavior **Momentary**, Transport MIDI Channel **2**
→ arriving as **Pd channel 18**. The control groups stay on the nano's channel 1 → Pd channel 17.

**They carry no transport meaning.** `m_nano` treats all six as ordinary momentary buttons —
`xport-1`…`xport-6` on press, no toggle — because the row is earmarked for **scene selection**, which
makes "play" and "loop" lies. Named by physical position, like every other control on the surface.
The reassignment was decided by playing with it; the reasoning is in
[ref-build-log.md](ref-build-log.md).

**One consequence for the decode:** since CC 41–46 give `div 10` = 4, `m_nano` folds the row in as a
**fifth control kind** and reads both channels through one path. So a separate channel no longer
isolates anything — it is inherited configuration, harmless, and not worth reflashing the device to
undo.

**Why they were moved off the factory map at all.** Two reasons that still hold:

1. **The factory assignment might have been MMC, and MMC is SysEx.** Reading it needs `[sysexin]`
   plus a byte-matching state machine, where `[ctlin]` hands you value, controller and channel
   already split.
2. **MMC has no release event** — Korg's manual is explicit that Button Behavior is unavailable when
   Assign Type is MMC. The whole nano configuration rests on *momentary only, Pd owns all state*,
   because the mk1 has no host LEDs and device-side state silently desyncs.

⬜ **The factory assignment was never captured** — the buttons were reconfigured before anything read
what they shipped with, so whether they defaulted to MMC or CC is unknowable without a factory reset.
Reason 1 stayed a risk rather than a finding; don't read it as evidence about the default.

**The CC numbers collide numerically with the Volca FM's parameter CCs (40–50).** Harmless: the Volca
is device 4 on channel 49+, the nano is device 2, and Pd separates by channel long before a CC number
is examined.

Per-button, Korg Kontrol Editor exposes: 📄

| Setting | Options |
|---|---|
| Assign Type | **Control Change** / **MMC** / No Assign |
| Button Behavior | Momentary / Toggle — *unavailable when Assign Type is MMC* |
| Control Change Number | 0–127 |
| MMC Command | Stop, Play, Deferred Play, Fast Forward, Rewind, Record Strobe, Record Exit, Record Pause, Pause, Eject, Chase, Command Error Reset, MMC Reset |
| MMC Device ID | 0–127 (127 = all devices) |
| **Transport MIDI Channel** | 1–16, **or** "Scene MIDI Channel" — *set independently of the control groups* |

---

## Roland SP-404MKII

Verified working in both directions with **no settings changes** — the factory MIDI config is
already correct for this rig. ✅ Arrives on **Pd channel 33**. ✅

### Transmits (404 → Pd)

| Event | Message | |
|---|---|---|
| Pad press | Note-on with velocity | ✅ |
| Pattern sequencer | Note-on with velocity | ⬜ setting is on, never captured |
| CTRL knobs | CC 16 and 17 | ✅ |
| Volume slider | CC 7 | 📄 |
| X-FADE crossfader | CC 8 | 📄 |
| Play / Cue / Sync / Bend / BPM buttons | CC 20–27 | 📄 |
| Clock | **Off** — MIDI Sync Out disabled deliberately | ✅ |

### Receives (Pd → 404)

| Message | Effect | |
|---|---|---|
| Note-on | Triggers a pad. **Bank A pad *n* = note 47 + *n***, so pad 1 = 48 | ✅ |
| CC 16–19, 80–83 | BUS 1–4 effect controls | 📄 |
| CC 7 / CC 8 | Volume / crossfader | 📄 |
| Program Change 0–15 | Selects patterns 1–16 | 📄 |
| Pitch bend | Only when INPUT FX is Vocoder, on MIDI ch 11 | 📄 |
| Clock, Start/Stop/Continue | Drives BPM SYNC tempo | ✅ |

Velocity 100 works for triggering; `[makenote]` handles the note-offs. ✅

### Two hard limits

**No System Exclusive at all** — Roland's implementation chart marks SysEx `x` in both
directions. 📄 There is no patch-dump, no remote configuration, no deep parameter access. What
the CC list exposes is what you get.

**No Song Position Pointer.** 📄 Combined with the above, **clock ticks are the only channel
through which the 404 can learn tempo**, so BPM SYNC always infers it from pulse intervals and
always lags by several pulses. That lag is structural — no message exists that would skip the
inference. This is the whole reason [ref-software.md](ref-software.md) concludes that Pd
should sequence the 404 with note events rather than let it follow clock.

### Note-range discrepancy ⬜ — do not build on either number

The repo's hardware finding and Roland's chart disagree:

- **Verified here:** bank A pad *n* = note 47 + *n* (pad 1 = 48, pad 2 = 49), established
  empirically. Only pads 1 and 2 were actually checked. ✅
- **Roland's chart:** MIDI mode A note range is **35–51**. 📄 Sixteen pads starting at 48 would
  run to 63, well outside that.

One of these is wrong, or "MIDI mode A" means something narrower than assumed. Resolving it is
tracked in [plan-v02.md](plan-v02.md) — it is the unknown that can silently corrupt work, since
sequencing code written against the wrong range looks correct and triggers the wrong pads.

### Relevant device settings, all already correct ✅

| Setting | Value | Why |
|---|---|---|
| MIDI Sync Out | Off | No clock echoed back to the Organelle |
| Soft Through | Off | No MIDI echo loop |
| USB-MIDI Thru | Off | Same |
| PAD Note Out | On | Pads transmit |
| SEQ Note Out | On | Pattern sequencer transmits — enables compose-time capture |
| MIDI Mode | A | Bank A receives on MIDI channel 1 |

---

## Korg Volca FM

**Receive only.** The original Volca FM has no MIDI out at all — its sequencer cannot be
captured, and it can never tell Pd anything. 📄 (The FM2 added MIDI out; this is not an FM2.)
Reaches the rig over DIN through the USB→DIN interface, so **Pd device 4, channel 49** for the
Volca's own channel 1. ⬜ interface not yet purchased.

Basic channel 1–16, default 1–16, memorised. Mode 3 (OMNI OFF, POLY). 📄

### Receives (Pd → Volca)

| Message | Notes | |
|---|---|---|
| Note-on | Note 0–127, velocity 1–127 | 📄 |
| Note-off | | 📄 |
| **CC 40** | Transpose | 📄 |
| **CC 41** | Velocity | 📄 |
| **CC 42** | Modulator Attack | 📄 |
| **CC 43** | Modulator Decay | 📄 |
| **CC 44** | Carrier Attack | 📄 |
| **CC 45** | Carrier Decay | 📄 |
| **CC 46** | LFO Rate | 📄 |
| **CC 47** | LFO Pitch Depth | 📄 |
| **CC 48** | Algorithm | 📄 |
| **CC 49** | Arpeggiator Type | 📄 |
| **CC 50** | Arpeggiator Division | 📄 |
| CC 123–127 | All Notes Off | 📄 |
| Clock, Start/Stop/Continue | Only when *MIDI Clock src* = **Auto** | 📄 |
| SysEx | **Yamaha DX7 bulk patch data only** | 📄 |

**Transmits: nothing.** Every column on the transmitted side of Korg's chart is empty. 📄

### Three settings that will silently break things ⬜

1. **`MIDI RX ShortMessage` must be ON** or **none of CC 40–50 is received**. Every parameter
   CC in the table above is gated behind this one global. If Volca CCs appear to do nothing,
   check this before debugging Pd.
2. **`MIDI Clock src` must be Auto**, not Internal, or clock and start/stop are ignored.
3. Aftertouch, pitch bend and program change are all unsupported — don't route them.

**DX7 SysEx is a real capability worth remembering.** The Volca FM accepts Yamaha DX7 bulk
dumps, so its entire patch bank is loadable from Pd if that ever becomes interesting. It is
the only SysEx it understands.

---

Anything above marked ⬜ is unresolved, and the work to resolve it is in
[plan-v02.md](plan-v02.md) under *Open questions*. One note that belongs nowhere else:
**`[sysexin]` on this Pd build is moot** — nothing in the rig transmits SysEx *to* Pd. Pd only
ever sends it, to the Launchpad, which works ✅.
