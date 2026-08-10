<!-- schema: module -->
# Korg Volca FM

**Files:** `Cut It/m_volca.pd` · **Gate:** `test/gate/volca-assert.sh` · **Bench:** `test/bench/midi-bench.pd`

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
| ⛔ **Nothing here can ever be read back off the wire** | The device is write-only, so the strongest evidence class available for this page is a controlled A/B **by ear**. **A structural limitation, not a gap** — no future session can close it, and `verified` on this page will never mean *read back* | unknown | 268 |

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

### Presence: `none`, and that is a fact rather than a gap

`m_volca` registers as `none` on the presence bus and stops there — no poll, no last-heard clock, no
ageing, and it can never be declared lost or back. **The Volca transmits nothing at all**, so there
is no evidence of its presence for any amount of code to find, and the alternative to recording that
is a silence that reads as an oversight.

⛔ **ITS RECOVERY IS PARASITIC, AND THAT IS SHARPER THAN IT FIRST READS.** `u_present` re-runs
`wire.sh` whenever *any* source is lost — so a replugged Volca comes back **only if a detectable
device happened to be missing at the same time**. Unplug the interface on its own and nothing is
lost, nothing forks, and the Volca is silently unreachable until the patch is reloaded.

⚠️ **And it was worse than that until 2026-08-10.** Pulling the interface also knocked the SP-404 off
the shared USB bus, which *did* start a recovery — but the 404 answered first, the lost count hit
zero, the counter reset, and the Volca was left disconnected because the one attempt that ran had
landed while it was still enumerating. Measured, item 275. `u_present` now fires **one trailing
`wire.sh` at the moment the last device returns**, which is the best-informed instant available: a
device answering its inquiry is the signal that enumeration has finished.

⚠️ **Nothing in the patch can confirm the Volca came back.** Only your ears can, which is why its
bench step is judged by ear. See [presence.md](../module/presence.md).

## Traps

### No MIDI clock or transport reaches this device, and the patch used to claim otherwise

`u_tempo`'s `realtime-out` holds exactly **two** `[midiout]` objects, set at loadbang to ports **1
and 3** — the Launchpad and the SP-404. The Volca is port 4 and the nanoKONTROL is port 2, so
neither has ever received a clock byte from Cut It. ✅ Measured with `aseqdump` on Pd's Midi-Out 4:
five seconds produced nothing at all, and a capture across a patch reload produced nothing at either
end. Item 279.

⚠️ **So the Volca cannot sync to the instrument**, and anything that assumes it is following the
master tempo is wrong. `m_volca.pd` carried the sentence *"clock and transport … already reach every
port"* until this was measured.

**Fix:** none yet — this is a gap rather than a decision, and widening `realtime-out` is
[plan-v04.md](../../plan-v04.md) §3's. Until then, drive the Volca's timing from its own controls.


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

### ⛔ "The Volca sounds" proves NOTHING — it is a synth with its own keyboard

The obvious by-ear test for *"is Pd reaching this device"* is to play it and listen. It cannot work.
The Volca's keys are local: it sounds whenever it is powered, with or without a MIDI cable.
✅ **Measured 2026-08-10** — the interface sat enumerated and completely unsubscribed for two minutes
and the keys played normally throughout.

**Fix:** the oracle is **a Cut It control changing the sound**, never the sound existing. Hold a key
and sweep `slider-1`. That is the only mapping there is — `mode-1 slider-1 volca-cc 41` — so it is
also the only audible evidence of the link that exists. ⚠️ **A bench step in this repo asserted
`PASS IF the Volca sounds` and would have passed with the cable out**; it came verbatim from a plan
that had checked its text against the punctuation rules and not against this page.

### ⛔ Cut It can silence this device from `slider-1`, and it looks exactly like a dead link

`mode-1 slider-1 volca-cc 41` and **CC 41 is Velocity** — a global parameter on this device, not a
per-note value. Leave the fader at the bottom and the Volca goes silent **to its own keyboard**, so
every symptom points at MIDI, USB or the interface, and none of them is at fault. Seen on the rig
2026-08-10: the device was silent to its own keys, then began sounding again when the fader moved,
with its screen showing the incoming parameter.

**Fix:** before diagnosing silence, **sweep `slider-1` to the top**. It costs one gesture and it
removes the most misleading state this instrument can put the Volca into.

| | Value | Evidence | Item |
|---|---|---|---|
| `slider-1` in mode 1 | Volca **CC 41 — Velocity**, global, silences the device at 0 | verified | 284 |

### ⛔ Absent at load, this device is never wired — not in sixty seconds, not ever

A `none` device has no clock, so it cannot be lost; and `u_present`'s recovery is gated on
*something* being lost. Boot the instrument with the Volca's interface unplugged and every pollable
layer answers, nothing is lost, the spigot stays shut, the counter never starts, and **no `wire.sh`
fork is ever scheduled**. `u_init`'s boot fork ran before the cable went in. ✅ **Measured** — plugged
into a clean session, enumerated within a second, and still holding **zero subscriptions** two
minutes later with an empty error log.

⚠️ **This is the likelier direction in a room**, and it is not the one
[presence.md](../module/presence.md) frames the gap around: you power the rig up, *then* plug the
Volca in. There is no warning, because nothing is wrong from the instrument's point of view.

**Fix:** `u_present` forks **`wire-watch.sh`** on a heartbeat — every 8 ticks, so ~16 s. It hashes
the ALSA **client names** and runs `wire.sh` only when they change, so a device appearing is wired
whether or not anything was ever lost. ⚠️ **The hot-swap bench steps still pull the nanoKONTROL
alongside the interface**, because they were written to test the *recovery*, and that path is
unchanged.

| | Behaviour | Evidence | Item |
|---|---|---|---|
| `none` device absent at load | enumerated, unsubscribed, never re-wired — 120 s observed | verified | 285 |
| …and seen again, unprompted | `USB Uno MIDI Interface` bare on a session up **1 day 21 h** — no `Connecting To`, no `Connected From`, both Pd ports unattached | verified | 285 |
| The heartbeat closes it | `wire-watch.sh` fires while **nothing** is lost, which no other fork in `u_present` can do | verified | 292 |

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

- ⬜ **The Volca made a sound three times on 2026-08-10 and it has never been reproduced.** See
  [plan-v04.md](../../plan-v04.md) §3. All three fell inside one window, while hands were on the
  cables; **nine subsequent patch loads produced nothing**, including one deliberately staged
  immediately after re-enumerating the interface, which was the predicted trigger. Everything in the
  software path is excluded by direct measurement: `start`, `stop` and `panic` never fire at load;
  `aseqdump` on Pd's Midi-Out 4 caught nothing as the old Pd shut down; a loopback monitor living
  inside the patch caught nothing as the new one loaded; no clock reaches the port at all (item 279
  above), so Pd sends this device nothing but one CC in mode-1; and `dmesg` logged no USB event
  alongside any of the three. ⚠️ **The leading explanation needs no software at all** — handling a
  DIN cable can inject noise into an opto-isolated input, which fits the three positives and all
  nine negatives. ⛔ **It is recorded rather than closed** because three occurrences are not nothing,
  and because the only observer that could settle it is a MIDI monitor on the DIN wire, which this
  rig does not have. A reload does **not** reliably cause it, so nothing that re-runs `wire.sh`
  needs a caveat on this account — including the bounded re-wire, which forks it up to eight times.

**Nothing.** That nothing here can be read back off the wire is a **permanent limitation, not an
unknown** — it is stated in **Facts** as item 268, with `unknown` as its evidence value, so it
cannot be rediscovered as news.
