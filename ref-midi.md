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
| 4 | **USB Uno MIDI Interface** → Volca FM | 49–64 | 49 | ✅ wired, slot 4 live |

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

### ⚠️ mother.pd maps MIDI onto the front panel itself — and Cut It turns that off ✅

**`mother.pd` runs `[ctlin 21]` through `[ctlin 26]` with no channel argument, so they are OMNI**,
and routes them onto the Organelle's own controls. It also loads a **new patch on any program
change**. Read out of `/root/fw_dir/mother.pd`:

| Incoming | mother does |
|---|---|
| CC 21–24, any channel | sets `knob1`–`knob4` |
| CC 25 | presses **`aux`** |
| CC 26, CC 64 | encoder / footswitch |
| Program change | **loads a different patch** |
| Note on/off | sends `notes` |

**This collides head-on with the nanoKONTROL**, whose top button row is CC 21–29 by this
project's own by-tens scheme. ✅ Measured on the device: `btn-t-5` **pressed aux and toggled the
transport**, and `btn-t-1`…`btn-t-4` slammed knobs 1–4 — so a single button press jerked the
tempo to 500 BPM and back to 10 on release. Phase 5 is what made it dangerous; before aux drove
the transport, CC 25 did nothing.

**`u_init` sends `midiInGate 0` at load and again at 2 s.** mother's own comment states the
contract: *"All MIDI output and input can be suppressed by sending a 0 to `midiOutGate` and
`midiInGate`."* Each gated path runs through a `[spigot 1]` fed by `[r midiInGate]`.

⚠️ **The second send is the one that matters.** ✅ The mother **binary** pushes its own
`midiInGate 1` over OSC — mother.pd has `routeOSC /midiInGate` — roughly half a second after the
patch loads, so a value sent at `loadbang` is silently overwritten. Measured on the device with an
`[r midiInGate]` print: `0` (ours), `1` (the binary), then `0` again at 2 s, and nothing further
out to twelve seconds. **Anything a patch sets on mother's MIDI settings at load needs the same
treatment.** `/sdcard/MIDI-Config.txt` stores only the channel, so there is no persistent setting
for this.

✅ **It gates only the MIDI-derived paths.** mother has *two* `s notes` — one fed by `oscIn`, which
is the physical keyboard, and one behind the gate, which is `notein`. Same split for the knobs.
So the front panel keeps working and only mother's interpretation of incoming MIDI stops.
Cut It's own `[ctlin]` objects read Pd's MIDI system directly and are unaffected.

*(This means `midiInGate` is a name the patch **sends**, despite being listed among the ones
mother sends to the patch — it is `[r midiInGate]` inside mother.)*

✅ **Entering mother's *MIDI Config* page mid-session does NOT re-open the gates — it is safe to
visit during a set.** The worry was that leaving the page would re-push `midiInGate 1` and
resurrect the CC 21–26 collision above. Opened, left, returned, then `btn-t-5` pressed on the nano:
**BPM unchanged**, on the OLED and the Launchpad both. Item 201.

⚠️ **The precondition is what makes that a result rather than a guess.** Had returning from the
menu **reloaded** the patch, `u_init` would have re-closed the gates at 2 s and the test would have
proven nothing while looking like a pass. ✅ **The evidence is that the OLED did not replay
`booting` → `wiring` → `launchpad`** — a surviving pid is *not* enough, because `/loadPatch` loads
a patch inside the running Pd.

### MIDI out from Pd

Raw System Real-Time bytes go straight out `[midiout]` as decimal floats ✅ — demonstrated in
v0.1's `midiclock.pd`, archived in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>).

⛔ **`[midiout]` needs no port creation argument, and this is settled rather than unknown.**
`u_tempo` uses the proven **cold-inlet** pattern — port into the right inlet, byte into the left —
and item 63 fired a real 404 pad through it. ⚠️ **The obvious experiment is invalid**: Pd 0.49 does
not warn about extra creation arguments at all, so a clean syntax check proves nothing either way.
**Nothing needs the answer** — recorded so the question is not reopened.
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
| **`[threshold~ 0.5 0 0.1 0]`** → one bang per cycle | the phasor crosses 0.5 once per ramp and falls below 0.1 on the wrap |
| every pulse emits **248** and increments a counter | `[mod 24]` = 0 is the beat, published on `clock` |
| **out on Pd MIDI ports 1 and 3** | the Launchpad and the SP-404 — `Pure Data:4` and `Pure Data:6`, already in `wire.sh` |

**Counting the pulses rather than running a second oscillator is what makes the beat and the MIDI
pulse the same clock by construction.** ✅ Measured on the Mac under real DSP: 6 beats in 3 s at
120 BPM, 3 in 3 s at 60 — [plan-tests.md](plan-tests.md) item 48.

**Range: 10–500 BPM from knob 1, clamped to 5–600.** The control range and the legal range are
different decisions, and the legal one is wider at both ends so a bench, a tap tempo or an LFO is
not limited by what one knob chose.

⚠️ **Both `threshold~` debounces are ZERO, and that is load-bearing.** ✅ `threshold~` decrements
its dead time **once per DSP block, not per millisecond**, so any non-zero debounce burns a whole
1.45 ms block on every state change. With the obvious-looking `2 ms` the clock **silently lost
pulses above about 430 BPM** — 17 beats where 25 were due at 500 BPM. At zero the floor is two
blocks per pulse: **344 Hz measured, which is 44100 / 64 / 2 exactly, or 860 BPM.** A `phasor~` is
monotonic and cannot bounce, so there was never anything for a debounce to protect against.
[plan-tests.md](plan-tests.md) item 58.

⚠️ **A `c_clock`'s ratio multiplies that ceiling**: `ratio × tempo` must stay under ~860 BPM
equivalent, so at the 600 BPM clamp the highest safe ratio is about 1.4.

### The four rate ceilings, and they are different numbers ✅ measured

⚠️ **These get confused with each other constantly.** They stack, and the one that bites is
whichever is lowest on the path you are actually using.

| Ceiling | Value | What it limits |
|---|---|---|
| **`threshold~` pulse** | **344 Hz** = 44100/64/2 | The raw 24 PPQN pulse. Item 58 |
| **`c_clock`'s BANG outlet** | **14.3/s** = 344 ÷ 24 | ⛔ **Beat bangs.** The ×24 that buys provable alignment with `u_tempo` costs a factor of 24 in headroom |
| **MIDI triggers to the 404** | **~360–400/s** | Note-on/off pairs. Perceptual, not a hard edge. Items 208–209 |
| **Pd's own wall** | **~689/s** | One message per 64-sample scheduler tick, a compile-time constant. ⛔ **Never reached** — something downstream saturates first |

⛔ **NO CLOCK-DRIVEN PATH CAN PRODUCE AN AUDIO-RATE MIDI STREAM.** At 14.3 bangs/s, `c_clock` is
two orders of magnitude below the trigger ceiling. A dense machine-gun trigger stream needs a plain
`[metro]`, not a clock ratio — **this was measured by trying, and the clock ran out first.**

✅ **But the AUDIO-DOMAIN path has no ceiling at all.** `c_clock` outlet 0 is the raw phase as a
**signal**; a filter stage reads it and drives `vline~` envelopes and table reads directly. **Every
number above applies only to the message domain.** ⚠️ **If a filter stage ever converts that phase
to bangs, that is the mistake — not the ceiling.**

⚠️ **Exceeding the trigger ceiling costs more than dropped notes.** Turning the rate *down* after
overshooting takes **seconds** to become audible, and the delay grows with how long the high rate
was held — while a *stop* is instant. ⛔ **It is not a queue in Pd** (tested directly, item 209);
the 404's voice pool is the leading guess and is not established. **Either way `m_404` needs a hard
rate limit.**

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

**Moved.** Ports, the Programmer Mode index map, both lighting paths, mode control, the device
inquiry, every trap and the three-tier design decision now live on one page:
**[ref/launchpad.md](ref/launchpad.md)**.

It used to be spread across this file, `ref-display.md`, `ref-hardware.md` and `ref-software.md` —
416 lines in four places, the most fragmented device in the repo.

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
`xport-1`…`xport-6` on press, no toggle — and names them by physical position, like every other
control on the surface, because what a control *means* is not knowable at the `m_` layer.
✅ **Since Phase 6 the row is the mode selector**, mapped in `u_map` and shown as a lit lamp on the
Launchpad's top row — which is what makes "play" and "loop" lies and why the labels are ignored.
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

**Moved.** Everything about this device — addressing, the pad note map, what it transmits and
receives, velocity, the trigger ceiling, clock following, its audio role, its device settings and
every trap it carries — now lives on one page: **[ref/sp404.md](ref/sp404.md)**.

It used to be spread across this file, `ref-hardware.md` and `ref-software.md`, which is how the
`47 + n` error survived in three places at once.

---

## Korg Volca FM

**Receive only.** The original Volca FM has no MIDI out at all — its sequencer cannot be
captured, and it can never tell Pd anything. 📄 (The FM2 added MIDI out; this is not an FM2.)
Reaches the rig over DIN through the USB→DIN interface, so **Pd device 4, channel 49** for the
Volca's own channel 1.

✅ **The interface is owned, attached and wired** (2026-08-06). It enumerates as
**`USB Uno MIDI Interface`** — an M-Audio Uno — with **one bidirectional port**, confirmed present
in both `aconnect -i` and `aconnect -o`. `wire.sh` connects it both ways:
`USB Uno MIDI Interface:0 → Pure Data:3` (in, ch 49–64) and `Pure Data:7 → USB Uno MIDI Interface:0`
(out). ⚠️ **Only the outbound line can ever carry Volca traffic**; the inbound one exists because
the interface has a DIN IN jack a future device could use.

⚠️ **ALSA CLIENT NUMBERS MOVE, AND THEY MOVED WHEN THIS WAS ADDED.** After a power cycle the order
became Launchpad 28, SP-404 32, Uno 36, nanoKONTROL 40 — the nano had been 32 and the 404 36.
✅ **Nothing broke, because `wire.sh` connects by NAME** and Pd's channel block follows which
`Pure Data` port a device is joined to, not enumeration order. **This is the payoff for the
connect-by-name rule.** `wire.sh`'s `aconnect -d` block now covers the Uno too, since whichever
device enumerates lowest is the one mother's `alsaconnect.sh` grabs for Midi-In 1.

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

### Three settings that will silently break things

1. ✅ **`MIDI RX ShortMessage` is ON on this unit — verified 2026-08-06, and it did not have to be
   found in a menu.** Every parameter CC 40–50 is gated behind this one global **and notes are
   not**, which makes notes a built-in control: notes + CC working proves it is on, notes alone
   proves it is off, and silence from both is cabling rather than a setting. ⚠️ **Diagnose it with
   the test instead of setting it first.** Item 223.

   **The A/B that proves it:** three events, all MIDI note 48, differing only in CC 40 —
   centre, centre, 127. The first two must sound identical; the third came back **a couple of
   octaves up**. ⛔ **The duplicated control note is what makes it evidence** rather than an
   impression, and it is what ruled out an accidental trigger.

   ⚠️ **This claim is BY EAR, not off the wire, and it always will be** — the Volca transmits
   nothing, so there is no readback to check it against. That is a weaker evidence class than
   everything else in this file.
2. **`MIDI Clock src` must be Auto**, not Internal, or clock and start/stop are ignored.
3. Aftertouch and pitch bend are unsupported — don't route them. ⛔ **Program change WAS on this
   list and is not any more — see below.**

### ⚠️ THIS UNIT RUNS PAJEN 1.09, NOT STOCK FIRMWARE ✅

**Flashed 2026-08-06** (audio into SYNC IN; verify with `REC` held at power-on → `Main 109`). It
changes what this device can do, and **two capabilities the rest of this file called impossible are
now real**:

| | Stock | Pajen 1.09 |
|---|---|---|
| **Program Change** | ⛔ ignored | ✅ **selects patches** — measured A B A B across PC 0/20 |
| **Velocity** | ⛔ ignored | ✅ **received** — 100/100/10/127 read as medium/medium/low/high |

✅ **Velocity is the one that matters most to this project**: the capture format is
`time, note, velocity, duration`, and the Volca was the only destination that would have discarded
a field. It no longer is.

⛔ **BOTH ARE GATED BY GLOBAL SETTINGS, AND NEITHER IS DOCUMENTED IN ANY SECONDARY SOURCE.** Pajen
extends the settings block from the stock 8 (item 227) to 12. Enter with **`FUNC` at power-on**,
**`REC` to save**:

| Key | Display | Meaning | Required |
|---|---|---|---|
| 9 | `Md UEL` | MIDI velocity | **On** |
| 10 | `MdSYSX` | SysEx — Yamaha vs Korg patch import/export | Off |
| 11 | `PCnot` | PC **per-note** (multitimbral) | **Off** |
| 12 | **`PCMId`** | **PC over MIDI — the master enable** | **On** |

⚠️ **`PCnot` and `PCMId` ARE A TRAP.** Both start with "PC", both are booleans, they are adjacent —
and enabling the wrong one gives a symptom **indistinguishable from the fault**: per-note mode binds
a program change to the next note and deliberately leaves the current program *and the display*
unchanged. **Four separate test runs failed this way.** Items 226–227.

### ⛔ Pd's `pgmout` is 1-BASED — `pgmout N` sends wire value `N-1` ✅

**Measured both directions on the hardware, item 228.** Every earlier Program Change test in this
project sent **raw `0xC0` bytes** — wire numbers — so nothing had ever exercised Pd's own object.

| Sent | Volca selected |
|---|---|
| raw `0xC0 19` | LilChorus |
| raw `0xC0 20` | Mouthlead |
| `pgmout 20` | **LilChorus** — i.e. wire 19 |
| `pgmout 21` | **Mouthlead** — i.e. wire 20, and it held through three raw `0xC0 20` interleaves |

⛔ **So a bare `[pgmout n]` selects the patch one BELOW `n`, and nothing reports it** — the `47 + n`
shape exactly (item 190). ✅ **`Cut It/m_volca.pd` carries a `[+ 1]` before `[pgmout]`**, so its
`program <n>` inlet means the **wire** number that Korg, Pajen and every other measurement here use.

⚠️ **The Volca displays a program NAME, not a number** — the wording in item 225 is imprecise. A
name is still a fine readout, but two adjacent slots must be confirmed to read *differently* before
any comparison based on it can be trusted.

⚠️ **Everything about this device is BY EAR.** It transmits nothing, so there is never a readback —
a permanently weaker evidence class than the rest of this file. Item 223.

**DX7 SysEx is a real capability worth remembering.** The Volca FM accepts Yamaha DX7 bulk
dumps, so its entire patch bank is loadable from Pd if that ever becomes interesting. It is
the only SysEx it understands.

---

Anything above marked ⬜ is unresolved, and the work to resolve it is in
[plan-v03.md](plan-v03.md) under *Open questions*. One note that belongs nowhere else:

✅ **`[sysexin]` is NOT moot, and this file used to say it was.** The Launchpad answers a device
inquiry — see *It answers a device inquiry* under the Launchpad above. The nanoKONTROL and the
404 still send none, so the corrected statement is narrower: **the Launchpad is the one device in
the rig that can talk back to Pd**, and it is also the only one Pd can light.
