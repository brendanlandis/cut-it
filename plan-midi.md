# Cut It — MIDI Reference

Every MIDI message that moves in this rig: what each device accepts, what each device
transmits, and how it lands in Pd.

Companion to [plan-hardware.md](plan-hardware.md) (the boxes and cables),
[plan-software.md](plan-software.md) (what we decided to build) and
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
no SysEx device IDs, no guessing.

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

This was deliberate, and the transport buttons should extend it — see
[Recommendation](#recommendation-change-the-transport-ccs) at the end.

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

Confirmed by use in this repo's existing patches: ✅

| Direction | Name | Carries |
|---|---|---|
| `[r notes]` | in | Keyboard note events |
| `[r knob1]` … `[r knob4]` | in | The four knobs |
| `[s screenLine1]` … `[s screenLine4]` | out | OLED text lines |

Other names exist in `mother.pd` (volume, expression pedal, encoder, encoder button, aux
button, aux LED) but are not used by any patch here and are **not yet confirmed against this
device's firmware**. ⬜ Read `/root/fw_dir/mother.pd` before relying on any of them —
Organelle 1 and Organelle M differ, and the public `Organelle_OS` repo documents the M.

### MIDI out from Pd

Raw System Real-Time bytes go straight out `[midiout]` as decimal floats. Already implemented
in [Cut It/midiclock.pd](<Cut It/midiclock.pd>): ✅

| Message | Decimal | Hex |
|---|---|---|
| Timing Clock | 248 | `F8` |
| Start | 250 | `FA` |
| Continue | 251 | `FB` |
| Stop | 252 | `FC` |

Clock is **24 PPQN** — 24 pulses per quarter note, one every 20.8 ms at 120 BPM.

**The Organelle is clock master and every other device's clock output is off.** ✅ The 404's
"MIDI Sync Out" in particular will echo clock back and create a loop if left on.

**Clock is not decorative.** It is how the 404 learns tempo for BPM SYNC time-stretch, and
how the Launchpad paces its own LED flash and pulse animations. Stop sending it and both
fall back to stale values. See *Time-stretch* in [plan-software.md](plan-software.md).

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

### Transport buttons — the master mode control

Six buttons: **REW, PLAY, FF, LOOP, STOP, REC**, reassigned to CC 41–46 on the nano's channel
2 and **verified on the wire** ✅. Reasoning in
[Recommendation](#recommendation-change-the-transport-ccs); this is what the editor exposes,
kept for when the scene is rebuilt.

Per-button, Korg Kontrol Editor exposes: 📄

| Setting | Options |
|---|---|
| Assign Type | **Control Change** / **MMC** / No Assign |
| Button Behavior | Momentary / Toggle — *unavailable when Assign Type is MMC* |
| Control Change Number | 0–127 |
| MMC Command | Stop, Play, Deferred Play, Fast Forward, Rewind, Record Strobe, Record Exit, Record Pause, Pause, Eject, Chase, Command Error Reset, MMC Reset |
| MMC Device ID | 0–127 (127 = all devices) |
| **Transport MIDI Channel** | 1–16, **or** "Scene MIDI Channel" — *set independently of the control groups* |

**The factory assignment was never captured** — the buttons were reconfigured before anything
read what they shipped with, so whether they defaulted to MMC or to CC is now unknowable
without a factory reset. ⬜ It no longer matters, but don't let the recommendation below be
read as evidence about the default.

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
inference. This is the whole reason [plan-software.md](plan-software.md) concludes that Pd
should sequence the 404 with note events rather than let it follow clock.

### Note-range discrepancy — resolve before building ⬜

The repo's hardware finding and Roland's chart disagree:

- **Verified here:** bank A pad *n* = note 47 + *n* (pad 1 = 48, pad 2 = 49), established
  empirically. Only pads 1 and 2 were actually checked. ✅
- **Roland's chart:** MIDI mode A note range is **35–51**. 📄 Sixteen pads starting at 48 would
  run to 63, well outside that.

One of these is wrong, or "MIDI mode A" means something narrower than assumed. Sweep all 16
pads with [tools/midi-drive.pd](tools/midi-drive.pd) and record the real range before any
sequencing code depends on it.

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

## Recommendation: change the transport CCs

**Adopted, configured and verified on the wire.** ✅ The settings are in *Concrete settings*
below; the reasoning is kept here because it is the argument for keeping them this way.

**Yes — change them, and do it before writing any mode-switching code.** Four reasons, in
descending order of how much they will hurt.

**1. The factory assignment might have been MMC, and MMC is SysEx.** A transport strip exists
to drive a DAW, and MMC is what DAWs expect — though the factory default was overwritten
before anyone read it, so this stayed a risk rather than a finding. MMC messages are
`F0 7F <deviceID> 06 <command> F7` — to read them, Pd needs `[sysexin]` and a byte-matching
state machine, versus `[ctlin]` handing you value, controller and channel already split. Every
other control in this rig decodes through `ctlin` or `notein`. One control needing a SysEx
parser is a wart on the most important control in the instrument.

**2. MMC has no release event.** Korg's manual is explicit: Button Behavior cannot be set when
Assign Type is MMC — a command goes out on each press, and nothing comes back on release. The
whole nanoKONTROL configuration was built on *momentary buttons only, Pd owns all state*,
precisely because the mk1 has no host-controllable LEDs and device-side state can silently
desync. MMC breaks that rule for the master mode selector, which is the worst possible place
to break it.

**3. The existing decode idiom extends for free.** Assign CC **41–46** and `div 10` = 4 means
"transport", `mod 10` = 1–6 says which button. One `[div 10]` / `[mod 10]` pair then covers
every control on the surface:

| `div 10` | Kind |
|---|---|
| 0 | Slider |
| 1 | Knob |
| 2 | Button, top row |
| 3 | Button, bottom row |
| **4** | **Transport** |

Number them **by physical position on the panel, in reading order** (top-left to
bottom-right) — the whole reason this controller was chosen over the BeatStep is that physical
position is legible, and the CC numbers should read the same way.

**4. Put them on their own MIDI channel.** *Transport MIDI Channel* is a separate setting from
the control groups' channel, so the transport can transmit on the nano's channel 2 while
everything else stays on channel 1 — arriving in Pd as **channel 18** against **channel 17**.
Then `[route 18]` isolates every mode change before any CC decoding happens, and a mode switch
can never be confused with a performance control even if the CC map is revised later. It costs
nothing: channel 18 is already inside device 2's block.

### Concrete settings

In Korg Kontrol Editor. Assign the CC numbers by physical position; Korg's manual lists the
buttons as REW, PLAY, FF, LOOP, STOP, REC, which suggests a 3×2 block — confirm against the
panel.

| Position | Likely label | CC |
|---|---|---|
| 1st | REW | **41** |
| 2nd | PLAY | **42** |
| 3rd | FF | **43** |
| 4th | LOOP | **44** |
| 5th | STOP | **45** |
| 6th | REC | **46** |

All six share the rest:

| Setting | Value |
|---|---|
| Assign Type | **Control Change** |
| Button Behavior | **Momentary** |
| Transport MIDI Channel | **2** — the nano's own channel number, arriving as **Pd channel 18** |

The control groups stay on the nano's channel 1 → Pd channel 17. Only the transport moves.

Then **re-export the scene file and commit it to this repo.** The nano's configuration is
device-resident state with no backup, and REC + STOP + SCENE at power-on wipes it.

### Two caveats

**The CC numbers collide numerically with the Volca FM's parameter CCs** (40–50). Harmless,
and not a reason to change the plan: the Volca is device 4 on channel 49+, the nano is device 2
on channels 17/18, and Pd separates by channel long before a CC number is examined.

**Honour STOP and PLAY.** Six buttons is more than a compose/perform toggle needs, but
[Cut It/midiclock.pd](<Cut It/midiclock.pd>) already listens on `r start`, and STOP/PLAY have
an obvious meaning that a performer's hands will assume under pressure. Spending them on
arbitrary modes is a trap. Suggested split, though the allocation is a UX decision, not a
MIDI one: **PLAY/STOP** drive the clock, **REC** arms capture, **LOOP/REW/FF** select mode.

---

## Open questions

| # | Question | Blocked on |
|---|---|---|
| 1 | ~~What do the transport buttons transmit?~~ | **Resolved** — CC 41–46 on Pd channel 18, momentary, no SysEx. Verified on the wire. ✅ |
| 2 | SP-404 pad note range — 47+*n* or 35–51? | Sweeping all 16 pads on hardware |
| 3 | Do the Launchpad's perimeter CC numbers match the documented layout? | 10 min with `tools/lp-monitor.pd` |
| 4 | Does the 404's *pattern playback* actually transmit notes? | Running a pattern and capturing |
| 5 | Do flashing/pulsing LEDs track a *modulated* tempo, or only a steady one? | A patch that sweeps tempo |
| 6 | Full `mother.pd` message list for Organelle 1 | Reading `/root/fw_dir/mother.pd` on the device |
| 7 | ~~Does `[sysexin]` work on this Pd build over ALSA?~~ | **Moot** — nothing in the rig transmits SysEx *to* Pd now. Pd only ever *sends* SysEx, to the Launchpad, which works. ✅ |

Question 2 is the one that can silently corrupt work: sequencing code written against the
wrong pad note range will look correct and trigger the wrong pads.
