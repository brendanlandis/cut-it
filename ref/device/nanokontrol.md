<!-- schema: module -->
# Korg nanoKONTROL (mk1)

**Files:** `Cut It/m_nano.pd` · **Gate:** `tools/phase6-assert.sh`

## What it is

The rig's fader bank: **9 control groups — each 1 knob, 1 slider, 2 buttons — plus 6 transport
buttons and a SCENE button.** 1 IN / 1 OUT, bus powered, ≤100 mA. 📄

**Nothing on it is host-controllable.** There is no LED Mode setting on the mk1 — confirmed in Korg
Kontrol Editor rather than inferred. Pd cannot light anything here, which is why every button is
momentary and all visible state lives on the Launchpad or the OLED.

`m_nano.pd` takes its Pd channel block as a creation argument and decodes every control onto `param`
and `disp`.

## Facts

### Transmits (nano → Pd), as configured

| Control | CC | Pd channel | `div 10` | `mod 10` | Evidence | Item |
|---------|----|------------|----------|----------|----------|------|
| Sliders 1–9 | 1–9 | 17 | 0 | channel | verified | 31 |
| Knobs 1–9 | 11–19 | 17 | 1 | channel | verified | 31 |
| Buttons, top row 1–9 | 21–29 | 17 | 2 | channel | verified | 31 |
| Buttons, bottom row 1–9 | 31–39 | 17 | 3 | channel | verified | 31 |
| Transport ×6 | 41–46 | **18** | 4 | button, left to right | verified | 31 |

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Button behaviour | **Momentary** throughout — 127 on press, 0 on release. Pd owns all toggle state | verified | 31 |
| Slider / knob range | Full 0–127. *Upper Value* / *Right Value* are not clipped | verified | — |
| SysEx | **None anywhere in the stream** — nothing emits MMC | verified | — |
| Receives from Pd | **Nothing musical.** The MIDI OUT port exists solely for Korg Kontrol Editor to read and write configuration | doc | — |

Verified end to end off the wire, then re-confirmed through the real patch: slider 1 → CC 1, slider 9
→ CC 9, knob 1 → CC 11, a top-row button → CC 23, a bottom-row one → CC 36, all on channel 1;
PLAY → CC 42 and LOOP → CC 44 on channel 2.

### Transport buttons

Six buttons moved off their factory assignment, in physical reading order.

| Position | Label | CC | Evidence | Item |
|----------|-------|----|----------|------|
| 1st–6th | REW · PLAY · FF · LOOP · STOP · REC | **41 · 42 · 43 · 44 · 45 · 46** | verified | 31 |

All six: Assign Type **Control Change**, Button Behavior **Momentary**, Transport MIDI Channel **2**,
arriving as Pd channel 18. The control groups stay on the nano's channel 1 → Pd channel 17.

**The labels are lies.** `m_nano` treats all six as ordinary momentary buttons — `xport-1`…`xport-6`
on press, no toggle — and names them by physical position, because what a control *means* is not
knowable at the `m_` layer. Since Phase 6 the row is the **mode selector**, mapped in `u_map` and
shown as a lit lamp on the Launchpad's top row.

Because CC 41–46 give `div 10` = 4, `m_nano` folds the row in as a **fifth control kind** and reads
both channels through one path. A separate channel therefore no longer isolates anything — it is
inherited configuration, harmless, and not worth reflashing the device to undo.

### Configuration

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Editor | **Korg Kontrol Editor 2.4.0** — 2.5.0 dropped first-generation nanoKONTROL support | verified | — |
| Where the map lives | Written to the device, not to a file on the host | verified | — |
| Factory reset | **REC + STOP + SCENE held at power-on** — destroys the map | doc | — |
| Scenes | Four, switched locally by the SCENE button. Only scene 1 is configured | verified | — |

The scene is written to the device, so the configuration is backed up in `device/` — it is one
accident from being lost otherwise.

Per-button, Korg Kontrol Editor exposes: 📄

| Setting | Options | Evidence | Item |
|---------|---------|----------|------|
| Assign Type | **Control Change** / **MMC** / No Assign | doc | — |
| Button Behavior | Momentary / Toggle — *unavailable when Assign Type is MMC* | doc | — |
| Control Change Number | 0–127 | doc | — |
| MMC Command | Stop, Play, Deferred Play, Fast Forward, Rewind, Record Strobe, Record Exit, Record Pause, Pause, Eject, Chase, Command Error Reset, MMC Reset | doc | — |
| MMC Device ID | 0–127 (127 = all devices) | doc | — |
| Transport MIDI Channel | 1–16, **or** "Scene MIDI Channel" — set independently of the control groups | doc | — |

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### The SCENE button is hidden state

⚠️ The device switches scene locally and **Pd is never told.** Four scenes exist; the patch cannot
know which is live.

**Fix:** if scenes are ever used, assign **distinct CC numbers per scene** so Pd infers the active
scene from which CCs arrive. Only scene 1 is configured today, so nothing depends on this yet.

### A factory reset destroys the map, and it is a three-key combo

⚠️ REC + STOP + SCENE at power-on wipes the configuration back to the factory layout, which put
sliders on CC 2–12 and was not regular.

**Fix:** know the combo so you do not hit it by accident. The scene file is backed up in `device/`.

### The CC numbers collide with the Volca's parameter range

The nano's transport row is CC 41–46; the Volca's parameters are CC 40–50.

**Fix:** nothing to do — harmless. The Volca is device 4 on channel 49+, the nano is device 2, and
Pd separates by channel long before a CC number is examined. Recorded so the collision is not
mistaken for a bug.

## Design

### Momentary only, because the device has no host LEDs

The mk1 cannot be lit by Pd at all. **Device-side toggle state would therefore desync silently** —
the surface would believe one thing, the patch another, and nothing could show the difference.

So every button is configured momentary and **Pd owns all state**. This is the single decision the
whole nano configuration rests on.

### Moved off the factory map, and MMC is why

Two reasons that still hold:

1. **The factory assignment might have been MMC, and MMC is SysEx.** Reading it needs `[sysexin]`
   plus a byte-matching state machine, where `[ctlin]` hands you value, controller and channel
   already split.
2. **MMC has no release event** — Korg's manual is explicit that Button Behavior is unavailable when
   Assign Type is MMC, which is incompatible with momentary-only.

The regular CC layout (sliders 1–9, knobs 11–19, buttons 21–29 and 31–39) is what makes `div 10` /
`mod 10` decode the entire surface with no lookup table.

## Open

- ⬜ **The factory transport assignment was never captured.** The buttons were reconfigured before
  anything read what they shipped with, so whether they defaulted to MMC or CC is unknowable without
  a factory reset. Reason 1 above stayed a risk rather than a finding — do not read it as evidence
  about the default. See [plan-v03.md](../../plan-v03.md) §4.
