# Cut It — MIDI Reference

Every MIDI message that moves in this rig: what each device accepts, what each device
transmits, and how it lands in Pd.

Companion to [ref-hardware.md](ref-hardware.md) (the boxes and cables),
[ref-software.md](ref-software.md) (what we decided to build) and
the git history (how the verified claims were verified).

**Confidence markers** are used throughout, and they matter — several claims in this
project's history turned out wrong when checked:

| | |
|---|---|
| ✅ | Verified on this hardware. |
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
`ctlin` are therefore safe.** The evidence is item 23.

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

**The panel, the OLED and the aux LED have MOVED** to **[ref/device/organelle.md](ref/device/organelle.md)** — the
`mother.pd` interface, the OMNI CC 21–26 collision and the `midiInGate` double-send, the OLED
graphics API and its four buffers, and the LED colour table.

⛔ **The one thing to carry away: the Organelle's own panel is not MIDI.** No CC number will ever
reach it.

What remains below is Pd generating MIDI *out*, which belongs to `u_tempo` rather than to the panel.

### MIDI out from Pd

**Moved** to **[ref/module/tempo.md](ref/module/tempo.md)** — the System Real-Time byte table, how `u_tempo` cuts
the 24 PPQN pulse from a `phasor~`, the four rate ceilings and why they get confused with each
other, and the `threshold~` debounce that must be zero.

---

## Novation Launchpad Pro MK3

**Moved.** Ports, the Programmer Mode index map, both lighting paths, mode control, the device
inquiry, every trap and the three-tier design decision now live on one page:
**[ref/device/launchpad.md](ref/device/launchpad.md)**.

It used to be spread across this file, `ref-display.md`, `ref-hardware.md` and `ref-software.md` —
416 lines in four places, the most fragmented device in the repo.

---

## Korg nanoKONTROL (mk1)

**Moved.** The full CC map, the transport reassignment, the Kontrol Editor settings and the
momentary-only decision now live on one page: **[ref/device/nanokontrol.md](ref/device/nanokontrol.md)**.

---

## Roland SP-404MKII

**Moved.** Everything about this device — addressing, the pad note map, what it transmits and
receives, velocity, the trigger ceiling, clock following, its audio role, its device settings and
every trap it carries — now lives on one page: **[ref/device/sp404.md](ref/device/sp404.md)**.

It used to be spread across this file, `ref-hardware.md` and `ref-software.md`, which is how the
`47 + n` error survived in three places at once.

---

## Korg Volca FM

**Moved.** The interface, every CC it accepts, the Pajen 1.09 firmware and the four global settings
it adds, the `pgmout` correction and the `PCnot`/`PCMId` trap now live on one page:
**[ref/device/volca.md](ref/device/volca.md)**.

---

Anything above marked ⬜ is unresolved, and the work to resolve it is in
[plan-v03.md](plan-v03.md) under *Open questions*. One note that belongs nowhere else:

✅ **`[sysexin]` is NOT moot, and this file used to say it was.** The Launchpad answers a device
inquiry — see *It answers a device inquiry* under the Launchpad above. The nanoKONTROL and the
404 still send none, so the corrected statement is narrower: **the Launchpad is the one device in
the rig that can talk back to Pd**, and it is also the only one Pd can light.
