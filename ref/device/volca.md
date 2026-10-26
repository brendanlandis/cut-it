<!-- schema: module -->
# Korg Volca FM

**Files:** `Cut It/m_volca.pd` · **Gate:** `test/gate/volca-assert.sh` · **Bench:** `test/bench/midi-bench.pd`

## What it is

**Receive-only, and the first output-only device layer in the rig.** What the Volca FM is, what it
receives, the Pajen 1.09 firmware, its global settings and its traps are in Reference:
`~/Sites/!reference/korg-volca-fm.md`. This page is how Cut It drives it.

It reaches the rig over DIN through a USB→DIN interface, so **Pd device 4, channel 49** carries the
Volca's own channel 1.

`m_volca.pd` has **one inlet, selector-prefixed** (`notes` / `cc` / `program` / `note`) and **no outlets** —
neither `param` (device-to-map) nor `disp` (display) fits a sounding note, so it is wired from
`u_map` rather than fed by a bus.

## Facts

### Addressing and the interface

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Pd channel block | 49–64 (output slot 4) for the Volca's channel 1 | verified | 229 |
| Interface | `USB Uno MIDI Interface` — an M-Audio Uno, one bidirectional port | verified | 229 |
| `wire.sh` outbound | `Pure Data:7 → USB Uno MIDI Interface:0` | verified | 229 |
| `wire.sh` inbound | `USB Uno MIDI Interface:0 → Pd:3` — exists only because the interface has a DIN IN jack a future device could use. **Nothing Volca can ever arrive on it** | verified | 229 |

### Presence: `none`, and that is a fact rather than a gap

`m_volca` registers as `none` on the presence bus and stops there — no poll, no last-heard clock, no
ageing, and it can never be declared lost or back. **The Volca transmits nothing at all**
(Reference), so there is no evidence of its presence for any amount of code to find, and the
alternative to recording that is a silence that reads as an oversight.

⛔ **THE BOUNDED RECOVERY CANNOT REACH THIS DEVICE ON ITS OWN.** `u_present` re-runs `wire.sh` only
while *some* source is lost — so through that path a replugged Volca comes back **only if a
detectable device is missing at the same time**. Unplug the interface on its own and nothing is
lost, nothing forks. **The re-wire heartbeat is what covers the Volca**: it watches the ALSA client
list and does not care whether anything was lost — see [presence.md](../module/presence.md).

⚠️ **Even the shared path can miss it.** Pulling the interface can knock the SP-404 off the shared
USB bus too, which *does* start a recovery — but the 404 answers first, the lost count hits zero,
the counter resets, and the Volca is left disconnected if the one attempt that ran landed while it
was still enumerating (item 275). `u_present` therefore fires **one trailing `wire.sh` at the moment
the last device returns**, which is the best-informed instant available: a device answering its
inquiry is the signal that enumeration has finished.

⚠️ **Nothing in the patch can confirm the Volca came back.** The heartbeat can say it re-wired —
`info u_present rewire-try` reaches the log — but whether the Volca is *sounding* is still only your
ears, which is why its bench step is judged by ear. See [presence.md](../module/presence.md).

## Traps

Each is a claim and its fix. How any of them was found is in the git history. The device's own traps
(by-ear evidence, local keyboard, program-name display, `PCnot` against `PCMId`, CC 41) are in Reference.

### No MIDI clock reaches this device

`u_tempo`'s `realtime-out` feeds exactly **two** `[midiout]` objects, set at loadbang to ports **1
and 3** — the Launchpad and the SP-404. The Volca is port 4 and the nanoKONTROL is port 2, so
neither receives a clock byte from Cut It. ✅ Measured with `aseqdump` on Pd's Midi-Out 4: five
seconds produce nothing at all, across a patch reload included. Item 279.

⚠️ **So the Volca cannot sync to the instrument**, and anything that assumes it is following the
master tempo is wrong.

**Fix, for the transport half only:** ✅ **`panic`'s realtime STOP reaches port 4**, through a
receive that the panic branch is the sole writer of — item 295. A synthesiser with a sequencer that
keeps running through a panic is the case panic exists for, and the mixer's master fader cannot stop
it. ⛔ **The clock is deliberately NOT widened with it.** Which devices Cut It intends to *drive* is
a v0.4 sound question — the Launchpad ignores incoming clock in Programmer Mode, so one of the two
ports already fed is pointless — and it stays in [plan-v04.md](../../plan-v04.md) §3. Until then,
drive the Volca's timing from its own controls.

📄 **The STOP only lands if this device's `MIDI Clock src` is `Auto`** — see Reference. Set to
Internal it is ignored, and a correct patch looks broken.

### Pd's `pgmout` is 1-based

A Pd fact, in `~/Sites/!reference/pure-data.md`. **Fix here:** `m_volca.pd` carries a `[+ 1]` before
`[pgmout]`, so its `program <n>` inlet means the **wire** number that Korg, Pajen and every other
measurement in this project use.

The measurement that found it, `tools/stage-patches/PGM Probe/` on this Volca (its display names the
program; [tools/README.md](../../tools/README.md) says how the probe runs):

| Sent | Volca selected | Evidence | Item |
|------|----------------|----------|------|
| raw `0xC0 19` | LilChorus | verified | 228 |
| raw `0xC0 20` | Mouthlead | verified | 228 |
| `pgmout 20` | **LilChorus** — i.e. wire 19 | verified | 228 |
| `pgmout 21` | **Mouthlead**, and it held through three raw `0xC0 20` interleaves | verified | 228 |

### `slider-1` is CC 41, and it can silence the device

`mode-1 slider-1 volca-cc 41`, and CC 41 is Velocity, a global parameter (Reference, item 284). Leave
the fader at the bottom and the Volca goes silent to its own keyboard, which looks exactly like a
dead link. **Fix:** before diagnosing silence, **sweep `slider-1` to the top**. It is also the only
mapping there is, so it is the only audible evidence of the link: the oracle is the fader changing the
sound, never the sound existing. ⚠️ **A bench step reading `PASS IF the Volca sounds` passes with the
cable out.**

| | Value | Evidence | Item |
|---|---|---|---|
| `slider-1` in mode 1 | Volca **CC 41 — Velocity**, global, silences the device at 0 | verified | 284 |

### ⛔ Absent at load, only the heartbeat ever wires this device

A `none` device has no clock, so it cannot be lost; and `u_present`'s bounded recovery is gated on
*something* being lost. Boot the instrument with the Volca's interface unplugged and every pollable
layer answers, nothing is lost, the spigot stays shut, the counter never starts, and **no scheduled
`wire.sh` fork ever runs**; `u_init`'s boot fork ran before the cable went in. ✅ **Measured** —
plugged into a clean session, enumerated within a second, and still holding **zero subscriptions**
two minutes later with an empty error log.

⚠️ **This is the likelier direction in a room**: you power the rig up, *then* plug the Volca in.
There is no warning, because nothing is wrong from the instrument's point of view.

**Fix:** `u_present` forks **`wire-watch.sh`** on a heartbeat — every 8 ticks, so ~16 s. It hashes
the ALSA **client names** and runs `wire.sh` only when they change, so a device appearing is wired
whether or not anything was ever lost. ✅ **So the bench steps pull the interface ALONE** — pulling a
detectable device alongside it goes through the loss path and proves nothing about the heartbeat.

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

### The `note` selector bypasses `makenote`, and pays for it with a panic

⛔ **A keyboard cannot use `makenote`.** Its duration is fixed, so a **held key would release
itself** — which is also why the map's `volca-note` destination cannot drive one. The `note`
selector goes straight to the same `[noteout]`, and the note-off comes from the key as velocity 0.

| | | Evidence | Item |
|---|---|---|---|
| `note <pitch> <velocity>` | a real note-on; velocity **0 is a real note-off** | verified | 293 |
| It reuses the **same** `[noteout]` | one channel, one object, so `MIDI_EXPECT` stays at `noteout:2` | verified | 293 |
| `panic` → **CC 123**, All Notes Off | `[ctlout 123]`, channel cold from the loadbang chain | verified | 293 |

⛔ **The panic belongs with the `note` inlet, not after it.** `makenote` owns the note-offs, which is
what stops a dropped cord or a reload leaving the Volca droning; bypassing it brings that risk back,
and All Notes Off is what replaces it. `m_404` has the same box for the same reason.

⚠️ **`[ctlout 123]`'s creation argument is the CONTROLLER, so the channel goes to inlet 2.** Wired
to inlet 1 it sets the controller instead — the device receives `CC 49` on channel 1 and panic
silently does nothing. `volca-assert.sh` asserts the channel.

## Open

- ⬜ **The Volca made a sound three times on 2026-08-10 and it has never been reproduced.** See
  [plan-v04.md](../../plan-v04.md) §3. All three fell inside one window, while hands were on the
  cables; nine patch loads since have produced nothing, including one staged immediately after
  re-enumerating the interface. Everything in the software path is excluded by direct measurement:
  `start`, `stop` and `panic` never fire at load; `aseqdump` on Pd's Midi-Out 4 and a loopback
  monitor inside the patch both caught nothing across a reload; no clock reaches the port (item 279),
  so Pd sends this device nothing but one CC in mode-1; and `dmesg` logged no USB event alongside any
  of the three. ⚠️ **The leading explanation needs no software at all** — handling a DIN cable can
  inject noise into an opto-isolated input. ⛔ **It is recorded rather than closed** because three
  occurrences are not nothing, and because the only observer that could settle it is a MIDI monitor
  on the DIN wire, which this rig does not have. A reload does **not** reliably cause it, so nothing
  that re-runs `wire.sh` needs a caveat on this account.

That nothing here can be read back off the wire is a **permanent limitation, not an unknown** — it
is stated in Reference as item 268, with `unknown` as its evidence value, so it cannot be
rediscovered as news.
