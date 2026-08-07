<!-- schema: module -->
# Korg Volca FM

**Files:** `Cut It/m_volca.pd` · **Gate:** `tools/phase9-assert.sh`

## What it is

**Receive-only, and the first output-only device layer in the rig.** The original Volca FM has no
MIDI out at all — its sequencer cannot be captured, and it can never tell Pd anything. 📄 (The FM2
added MIDI out; this is not an FM2.)

It reaches the rig over DIN through a USB→DIN interface, so **Pd device 4, channel 49** carries the
Volca's own channel 1.

`m_volca.pd` has **one inlet, selector-prefixed** (`notes` / `cc` / `program`) and **no outlets** —
neither `param` (device-to-map) nor `disp` (display) fits a sounding note, so it is wired from
`u_map` rather than fed by a bus.

⚠️ **This unit runs Pajen 1.09, not stock firmware**, which is what makes velocity and program
change work at all.

## Facts

### Addressing and the interface

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Pd channel block | 49–64 (output slot 4) for the Volca's channel 1 | verified | 229 |
| Interface | `USB Uno MIDI Interface` — an M-Audio Uno, one bidirectional port | verified | 229 |
| `wire.sh` outbound | `Pure Data:7 → USB Uno MIDI Interface:0` | verified | 229 |
| `wire.sh` inbound | `USB Uno MIDI Interface:0 → Pure Data:3` — exists only because the interface has a DIN IN jack a future device could use. **Nothing Volca can ever arrive on it** | verified | 229 |
| Basic channel | 1–16, default 1–16, memorised. Mode 3 (OMNI OFF, POLY) | doc | — |
| Transmits | **Nothing.** Every column on the transmitted side of Korg's chart is empty | doc | — |

### Receives (Pd → Volca)

| Message | Notes | Evidence | Item |
|---------|-------|----------|------|
| Note-on | Note 0–127, velocity 1–127 | doc | — |
| Note-off | | doc | — |
| **CC 40** | Transpose | doc | — |
| **CC 41** | Velocity | doc | — |
| CC 42 / 43 | Modulator Attack / Decay | doc | — |
| CC 44 / 45 | Carrier Attack / Decay | doc | — |
| CC 46 / 47 | LFO Rate / Pitch Depth | doc | — |
| CC 48 | Algorithm | doc | — |
| CC 49 / 50 | Arpeggiator Type / Division | doc | — |
| CC 123–127 | All Notes Off | doc | — |
| Clock, Start/Stop/Continue | Only when *MIDI Clock src* = **Auto** | doc | — |
| SysEx | **Yamaha DX7 bulk patch data only** | doc | — |
| Aftertouch, pitch bend | Unsupported — do not route them | doc | — |

**DX7 SysEx is a real capability worth remembering.** The Volca FM accepts Yamaha DX7 bulk dumps, so
its entire patch bank is loadable from Pd if that becomes interesting. It is the only SysEx it
understands.

### Pajen 1.09 firmware

Flashed 2026-08-06 — audio into SYNC IN; verify with `REC` held at power-on, which shows `Main 109`.
**Two capabilities the stock firmware does not have:**

| | Stock | Pajen 1.09 | Evidence | Item |
|---|-------|------------|----------|------|
| Program Change | Ignored | **Selects patches** — measured A B A B across PC 0/20 | verified | 226 |
| Velocity | Ignored | **Received** — 100/100/10/127 read as medium/medium/low/high | verified | 226 |

**Velocity is the one that matters most here**: the capture format is `time, note, velocity,
duration`, and the Volca was the only destination that would have discarded a field. It no longer is.

### The global settings that gate them

Pajen extends the settings block from the stock 8 to 12. Enter with **`FUNC` at power-on**, save with
**`REC`**.

| Key | Display | Meaning | Required | Evidence | Item |
|-----|---------|---------|----------|----------|------|
| 9 | `Md UEL` | MIDI velocity | **On** | verified | 226 |
| 10 | `MdSYSX` | SysEx — Yamaha vs Korg patch import/export | Off | verified | 226 |
| 11 | `PCnot` | PC **per-note** (multitimbral) | **Off** | verified | 227 |
| 12 | `PCMId` | **PC over MIDI — the master enable** | **On** | verified | 227 |

| Other setting | Value | Why | Evidence | Item |
|---------------|-------|-----|----------|------|
| `MIDI RX ShortMessage` | **On** on this unit | Gates every parameter CC 40–50. Notes are **not** gated by it | verified | 223 |
| `MIDI Clock src` | **Auto**, not Internal | Clock and start/stop are ignored otherwise | doc | — |

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### Pd's `pgmout` is 1-based

⛔ **`pgmout N` puts wire value `N-1` on the cable, and nothing reports it** (item 228). A bare `[pgmout n]`
selects the patch one *below* the number asked for — the `47 + n` shape exactly.

| Sent | Volca selected | Evidence |
|------|----------------|----------|
| raw `0xC0 19` | LilChorus | verified |
| raw `0xC0 20` | Mouthlead | verified |
| `pgmout 20` | **LilChorus** — i.e. wire 19 | verified |
| `pgmout 21` | **Mouthlead**, and it held through three raw `0xC0 20` interleaves | verified |

**Fix:** `m_volca.pd` carries a `[+ 1]` before `[pgmout]`, so its `program <n>` inlet means the
**wire** number that Korg, Pajen and every other measurement in this project use.

### `PCnot` and `PCMId` are adjacent, and the wrong one is indistinguishable from the fault

⛔ Both start with "PC", both are booleans, they sit next to each other — and enabling per-note mode
binds a program change to the *next note* while deliberately leaving the current program **and the
display** unchanged. That looks exactly like program change not working at all. Four separate test
runs failed this way.

**Fix:** `PCnot` **off**, `PCMId` **on**. Confirm both before concluding anything about program
change.

### The Volca displays a program NAME, not a number

⚠️ A name is a fine readout, but two adjacent slots must be confirmed to read *differently* before
any comparison based on it can be trusted.

**Fix:** establish the two names first, then run the comparison.

### Everything about this device is by ear

⚠️ **It transmits nothing, so there is never a readback.** Every claim on this page about what the
Volca *did* is a permanently weaker evidence class than anything measured off the wire.

**Fix:** build a control into the test rather than trusting a single impression. The A/B that proved
`MIDI RX ShortMessage` used three events, all MIDI note 48, differing only in CC 40 — centre, centre,
127. The duplicated control note is what made it evidence rather than an impression, and it is what
ruled out an accidental trigger.

## Design

### One selector-prefixed inlet, not one inlet per capability

`u_map` reaches the Volca on **one cord** carrying `notes 48 100 200`, `cc 41 64` or `program 3`,
routed inside the device layer. The alternative — one outlet per inlet — makes `u_map`'s outlet count
the sum of every device's capabilities, and crosses the "revisit past about four output devices"
threshold with two devices.

⛔ **An unrecognised selector is a real error**, reported as `fail m_volca bad-selector` on `err`. It
means `u_map` and this file disagree about the interface, and nothing else would notice.

### `makenote` is safe here, and only here

The Volca has **one** channel, set cold at load, so `[makenote]` → `[noteout]` cannot send a note-off
to the wrong place. **The SP-404 has ten and cannot use this** — see
[ref/device/sp404.md](sp404.md) → *Traps*.

## Open

- ⬜ **Nothing on this page has ever been read back off the wire, and nothing ever can be.** The
  strongest available evidence class for this device is a controlled A/B by ear. That is recorded
  here as a permanent limitation rather than as work to do — see [plan-v03.md](../../plan-v03.md) §4.
