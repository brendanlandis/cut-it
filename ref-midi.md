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
| Function buttons | Control change, see layout below | ✅ |
| **Device inquiry reply** | **SysEx — see below** | ✅ |

Velocity is real — soft presses register as low as 10. ✅

### ⚠️ It answers a device inquiry — and this file used to deny it ✅

**This document previously stated that nothing in the rig transmits SysEx *to* Pd.** That was an
inference from two unrelated measurements — the nanoKONTROL's stream (measured) and Roland's
chart for the 404 — and **it is false.** ✅ Measured with `tools/lp-readback.pd` (the exploratory probe, **since deleted** — every question it was built to answer is closed and recorded in [plan-tests.md](plan-tests.md) items 98–110)
([plan-tests.md](plan-tests.md) items 98–99): `[sysexin]` instantiates *and fires* on this Pd
build, and the Launchpad answers the **universal device inquiry**:

```
send:   F0 7E 7F 06 01 F7
reply:  F0 7E 00 06 02 | 00 20 29 | 23 01 | 00 00 | 00 04 06 05 | F7
                        └ Novation  family  member   firmware
```

| Field | Value |
|---|---|
| Manufacturer | `00 20 29` — Novation. The same three bytes that open every Launchpad SysEx header |
| Family / member | `23 01` / `00 00` |
| Firmware | `00 04 06 05` |

**Why it matters beyond trivia: a device that answers is a device Pd can notice the absence of.**
Poll the inquiry, expect a reply, and a Launchpad that has been unplugged — or bumped out of
Programmer Mode — stops being invisible. ✅ **Phase 6 built exactly that**: `m_launchpad`'s
watchdog polls the inquiry every two seconds, and three missed replies drop surface ownership so
`g_grid` stops painting. It costs one round trip per poll against the 96 ALSA writes a second the
clock already makes. ⚠️ **The poll alone is not enough** — a Mac replug is undetectable this way,
because the device answers the inquiry in *either* mode, so a Programmer Mode heartbeat runs
alongside it. See [ref-display.md](ref-display.md) → *`g_grid`* and
[ref-build-log.md](ref-build-log.md) → *The watchdog*.

⚠️ **Programmer Mode locks out the device's own mode buttons, so they cannot be used to change
mode while Pd owns the surface.** Pressed in Programmer Mode they are ordinary CC — measured:
`176 93 127` then `176 93 0` for the top row. ⬜ Whether the device *announces* a mode change made
by hand in **Live** Mode is still unmeasured; item 100.

**Polyphonic aftertouch must be enabled on the device**, and it is not the default. Hold
`Setup`, press the **third Track Select button**, choose *Polyphonic Aftertouch*; the default
is Channel Pressure, one value for the whole surface. Programmer Mode locks out the Setup
menu, so exit to Live mode first. There is an *Aftertouch Threshold* on that page worth
tuning. ✅

### Programmer Mode layout

The 8×8 grid is **verified**: pad at row *r*, column *c* is note `r*10+c`, both digits 1–8,
row 1 at the bottom. Notes 43, 44, 45, 53, 54, 55 confirmed in position. ✅

✅ **The perimeter is now measured on this unit** — 41 buttons, pressed twice, identical both
passes ([plan-tests.md](plan-tests.md) item 82). **The documented map was wrong in two places:**

| Buttons | Numbers | Type |
|---|---|---|
| 8×8 grid | 11–88 (`r*10+c`) | Note ✅ |
| **Top-left corner** | **CC 90** | CC ✅ — **absent from the documentation**, which starts at 91 |
| Top row, left→right | CC 91–98 | CC ✅ |
| **Logo / top-right corner** | **CC 99** | ⚠️ **NOT A BUTTON — an LED only.** ✅ Measured: pressing it transmits **nothing**, while lighting index 99 works. **Write-only.** Item 198 |
| Right column (scene launch), top→bottom | CC 89, 79, 69, 59, 49, 39, 29, 19 | CC ✅ |
| Left column, top→bottom | CC 80, 70, 60, 50, 40, 30, 20, 10 | CC ✅ |
| Bottom row, left→right | CC 101–108 | CC ✅ |
| **A SECOND bottom row below it**, left→right | **CC 1–8** | CC ✅ — **absent from the documentation entirely** |

⚠️ **The second bottom row changed a decision, then changed it back.**
Counting it, the whole surface is about 106 addressable indices — close to Novation's documented
"up to 106" SysEx limit 📄, which is why `g_grid` originally stopped at index 10. ✅ **It now
paints indices 1–108 and CC 1–8 with them**, because that documented limit is not real on this
unit and an index outside the span can never be cleared.

✅ **That span is a CHOICE, not a limit.** The probe that seemed to find a cliff at 120 was
sending illegal bytes; a clean 120-spec message paints the whole surface, CC 1–8 included — see
*lighting* below. Widening the span later costs one SysEx, not two.

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
nothing.

✅ **Confirmed against the real clock:** three pads lit static / flashing / pulsing alongside the
running patch visibly changed rate as knob 1 was swept, so `g_grid` relies on this rather than
driving animation from `clock`. ⚠️ **But it has its own range, ⬜ not pinned down** — past an upper
and a lower limit the animation reverts to a default rate instead of tracking, and a Start makes it
dip briefly before settling. Same shape as the 404's 40–200 window, and almost certainly the same
kind of device-side limit: the pulse stream itself is known good, since the 404 tracks it to the
digit across its whole range. [plan-tests.md](plan-tests.md) item 77.

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

✅ **Measured: 99 colour specs in one message works**, and so does 120. `g_grid` paints **108**,
indices 1–108, which includes the second bottom row at CC 1–8.

✅ **AND SO DOES 120 — the whole surface fits in one message.** This file used to state that 120
specs are "rejected outright". **That was wrong**, and three separate attempts to confirm it were
all broken in two different ways, each producing a plausible answer — [plan-tests.md](plan-tests.md)
items 83 and 105. A clean 368-byte message of 120 specs from index 1 lights **every button
including the second bottom row at CC 1–8**, reproducibly. Novation documents "up to 106" 📄 and
this unit exceeds it.

⚠️ **MIDI data bytes are 7-bit, and that is what the broken probes hit.** Counting LED indices
from 10 reaches index **128** at the 119th spec — `0x80`, a **Note Off status byte** — which cuts
the SysEx short. The tail is then parsed as channel-voice messages, and index 129 is `0x81`,
**Note Off on channel 2: the Launchpad's *flashing* channel**, addressing note **21** — which is
the colour byte in every spec. Hence the reproducible symptom of one pad, always row 2 column 1,
left flashing when every spec sent was static. **Any probe of this must keep every index ≤ 127.**

⚠️ **A malformed SysEx also leaves the pipe dirty**: the next message sent is swallowed closing
it, and only the one after that gets through — measured twice (item 107).

✅ **`g_grid` paints 108 specs at indices 1–108, CC 1–8 included.** Widening it cost one SysEx,
not two. The reason was not that anything wanted those buttons — it is that **LED state survives
the Programmer Mode switch**, so an index outside the painted span holds whatever Live Mode last
drew there, forever, in every session.

✅ **Index 0, the Setup button, is outside the span and that one IS a limit** (item 110). A valid
one-spec frame addressing it lights nothing, and the button transmits nothing in Programmer Mode.

✅ **Index 99 is the opposite case and worth knowing: it LIGHTS but never TRANSMITS.** It is the
Novation logo — an indicator, not a switch (item 198). ⚠️ **`g_grid` already paints it**, since
its span is 1–108, so it currently carries background dim for no reason. **The only non-button LED
on the surface**, which makes it the one place a persistent status light cannot be mistaken for
something pressable — and it costs no extra SysEx, because the byte is already in the frame.

✅ **The same message lights the ring as well as the pads** (item 84), addressed by the same
Programmer-Mode index. [tools/lp-flicker.pd](tools/lp-flicker.pd) still sends one message per pad
and is kept as the per-pad RGB reference.

### Receives (Pd → Launchpad): mode control

All share the header `F0 00 20 29 02 0E`. 📄 except as marked.

| Command | Message | Meaning |
|---|---|---|
| `0E` | `F0 00 20 29 02 0E 0E 01 F7` | Enter **Programmer Mode** ✅ |
| `0E` | `F0 00 20 29 02 0E 0E 00 F7` | Return to **Live Mode** ✅ |
| `00` | `F0 00 20 29 02 0E 00 <layout> F7` | Select layout — ⚠️ **does nothing on this unit** for ids 0, 4 and 5 ✅ tested |
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
a SysEx selecting another layout. Bind "return to Live mode" somewhere reachable — `m_launchpad`
does, on both `panic` and `quitting`. ✅

✅ **A power cycle does rescue you**, measured: unplugged and replugged from Live Mode, it comes
back in Live Mode. ✅ **Live Mode returns to whichever built-in mode was last used** — Note view
here, not a fixed default. ⚠️ **LED state survives the round trip**: Programmer → Live →
Programmer brought the previous colours back, so the clear on entering Programmer Mode is
confirmed mandatory rather than merely prudent.

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

Verified working in both directions with **no settings changes** — the factory MIDI config is
already correct for this rig. ✅ **Bank A** arrives on **Pd channel 33**; banks B–J follow on
34–42 — see *160 pads, not 16* below, which is the thing to read first about this device. ✅

### Transmits (404 → Pd)

| Event | Message | |
|---|---|---|
| Pad press | Note-on with **real velocity** — but only if *fixed velocity* is OFF. See below | ✅ |
| **Pattern sequencer** | **Note-on — it DOES transmit.** 199 events captured from a playing pattern, all within 36–51, on the bank's own channel | ✅ |
| CTRL knobs | CC 16 and 17 | ✅ |
| Volume slider | CC 7 | 📄 |
| X-FADE crossfader | CC 8 | 📄 |
| Play / Cue / Sync / Bend / BPM buttons | CC 20–27 | 📄 |
| Clock | **Off** — MIDI Sync Out disabled deliberately | ✅ |

### Receives (Pd → 404)

| Message | Effect | |
|---|---|---|
| Note-on | Triggers a pad. **Bank A is notes 36–51** — see *The pad note map* below. ⛔ NOT `47 + n` | ✅ |
| CC 16–19, 80–83 | BUS 1–4 effect controls | 📄 |
| CC 7 / CC 8 | Volume / crossfader | 📄 |
| Program Change 0–15 | Selects patterns 1–16 | 📄 |
| Pitch bend | Only when INPUT FX is Vocoder, on MIDI ch 11 | 📄 |
| Clock, Start/Stop/Continue | Drives BPM SYNC tempo | ✅ |
| Start (250) | **Starts the pattern sequencer on its own** | ✅ |
| Stop (252) | Stops it | ✅ |

Velocity 100 works for triggering; `[makenote]` handles the note-offs. ✅

### ⚠️ PAD VELOCITY IS A SETTING — `[SHIFT]` + a pad toggles it ✅

**With *fixed velocity* ON, every pad transmits 127** regardless of how hard it is struck — a firm
press and a deliberately soft one both reported 127, as did all sixteen pads in a sweep (item 193).

✅ **With it OFF, velocity is real:** nine presses gave **6, 10, 14, 15, 24, 27, 29, 74, 89** and no
127 at all (item 204). **So the 404 can author dynamics**, and any claim that it cannot is wrong.

⚠️ **Check this setting before trusting any velocity measurement from this device** — a flat wall
of 127s is a *configuration*, not a capability limit, and it looks identical to one.

⚠️ **And hearing is not measuring.** The 404 responds to strike force *internally* — the sample
plays louder — **while fixed velocity is still on and the wire still carries 127.** Only reading
the MIDI stream separates the two.

✅ **And the SEQUENCER records and transmits them too** — a pattern recorded with varied strength
played back **27 distinct velocities, 3 to 104** (item 205). ⛔ **So the 404 is a full authoring
surface**: it can fill every field of `time, note, velocity, duration`, not just perform dynamics
live. ⚠️ **3–104 is the range PLAYED, not the device's range** — nothing suggests a ceiling below
127.

⚠️ **One unexplained residue, and it is recorded so it is not rediscovered as a mystery:** in that
same capture every **channel 2** (bank B) event was exactly 127 while channel 1 varied.
⛔ **"Fixed velocity is per-bank" is ruled out — the setting is global**, tested directly. Stale
pattern data is the leading guess; it predates the toggle. **Cheap check if it ever matters: press
bank-B pads by hand, no pattern involved.**

### ⚠️ Where the external tempo actually shows — read this before debugging sync ✅

**The BPM number beside a pad is that SAMPLE's tempo, not the sync tempo.** Pad 1 reads 150 and
pad 2 reads 160 on this unit, and neither number moves when the 404 is following an external
clock. Watching it is the natural thing to do and it is the wrong number entirely — it cost an
afternoon.

**The external tempo lives on the Pattern Select screen, as `EXT nnn`.** Measured against a
hand-rolled clock from `tools/midiout-probe.pd`:

| Pulse interval sent | Implied BPM | 404 displayed |
|---|---|---|
| 20.833 ms | 120.0 | **`EXT 120`** ✅ |
| 30.833 ms | 81.1 | **`EXT 81`** ✅ |

So the 404 infers tempo from pulse intervals correctly and to the digit.

⚠️ **The 404 only follows between 40 and 200 BPM.** ✅ Measured by sweeping `u_tempo` across its
full 10–500 range: `EXT` slides down to **40** and stops, and up to **200** and stops. Outside that
window the 404 is pinned and simply no longer agrees with the Organelle. Nothing is broken — it is
a device limit, and it is one of the reasons the design does not rely on clock for anything that
has to be tight.

**Three behaviours worth knowing, all ✅ measured:**

- **It slides into a tempo it has not seen** — `EXT` ramps gradually from the old value to the
  new one, which is the several-pulse averaging made visible. It **snaps** instantly to a tempo it
  has already learned. So a slow slide is the inference working, not a fault.
- ⚠️ **When the clock stops, it does not hold the last external tempo — it reverts to its own
  internal one.** The display changes from `EXT 81` back to `BPM 125`. This is the concrete form
  of *a stopped clock is a wrong tempo rather than no tempo*, and it is why `u_tempo` keeps
  sending 248 whether or not the transport is running.
- **Start alone drives the sequencer.** 250 starts the pattern, 252 stops it, with no clock
  needed to make that happen — which makes Start the unambiguous test of whether the 404 is
  listening at all. A tempo display is not: it may simply be showing you a sample's BPM.

### Two hard limits

**No System Exclusive at all** — Roland's implementation chart marks SysEx `x` in both
directions. 📄 There is no patch-dump, no remote configuration, no deep parameter access. What
the CC list exposes is what you get.

**No Song Position Pointer.** 📄 Combined with the above, **clock ticks are the only channel
through which the 404 can learn tempo**, so BPM SYNC always infers it from pulse intervals and
always lags by several pulses. That lag is structural — no message exists that would skip the
inference. This is the whole reason [ref-software.md](ref-software.md) concludes that Pd
should sequence the 404 with note events rather than let it follow clock.

### ✅✅ 160 PADS, NOT 16 — bank sets the CHANNEL, pad sets the NOTE

**The single most useful thing measured about this device**, and it was not known until Session 15.
Pad 1 pressed on each bank in turn reports **note 48 every time**, with only the channel moving:

| Bank | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **404's own channel** | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| **Pd channel on the Organelle** | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 | 41 | 42 |

✅ **Receive mirrors transmit** — note 48 on channel 2 lights **B1**, on channel 3 lights **C1**.
So the whole instrument is **note 36–51 × channel 1–10 = 160 pads**, one formula, no special cases.

✅ **It fits the Organelle's block with room spare.** Device 3 owns channels 33–48; the ten banks
use 33–42 and leave 43–48 unused. Items 195–196.

⚠️ **A receive test MUST state which bank is selected.** The 404 lights only the *currently
selected* bank, so a pad firing on any other is invisible — that produced a false "channel 3 does
nothing" reading and nearly recorded a constraint that does not exist. Item 196.

### ✅ The pad note map — SETTLED, and `47 + n` was wrong

All sixteen pads measured in **both directions**, items 190–192. **The range is 36–51**, and it is
the same on every bank.

```
pads              notes
 1  2  3  4       48 49 50 51     <- top row
 5  6  7  8       44 45 46 47
 9 10 11 12       40 41 42 43
13 14 15 16       36 37 38 39     <- bottom row
```

**Pad 1 is top-left; notes ascend from the BOTTOM-left, four per row** — the standard MPC / General
MIDI drum-grid convention. The 404 is entirely conventional here.

```
note = 36 + (3 - (pad-1)/4) * 4 + (pad-1) % 4        integer division
```

⛔ **`47 + n` — which this file asserted — is WRONG.** It holds for pads 1–4 and then breaks: pad 5
is **44**, not 52. It was derived from **pads 1 and 2 only**, which sit inside the single block
where the formula happens to work. ⚠️ **Sequencing code written against it looks correct and
triggers the wrong drums with no error** — which is precisely why this was flagged as the open
question most able to corrupt work silently.

⚠️ **Roland's chart (35–51 📄) was CLOSER than our own measurement**, off by one at the bottom.
Worth remembering the next time a repo finding and a manufacturer document disagree.

✅ **Receive and transmit use the SAME map**, verified at both ends — note 36 fires pad 13, note 51
fires pad 4. **One table, not two.**

✅ **Nothing outside 36–51 is addressable.** Notes 35, 52 and 63 fire nothing, forty attempts each.

✅ **A 4×4 Launchpad quadrant maps on with no vertical flip**, because the Launchpad also numbers
its grid from the bottom row up (`r*10+c`, row 1 at the bottom).

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
