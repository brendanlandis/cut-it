<!-- schema: module -->
# Korg nanoKONTROL (mk1)

**Files:** `Cut It/m_nano.pd` · **Gate:** `test/gate/nano-assert.sh` · **Bench:** `test/bench/nanokontrol-bench.pd`

## What it is

The rig's fader bank: **9 control groups — each 1 knob, 1 slider, 2 buttons — plus 6 transport
buttons and a SCENE button.** 1 IN / 1 OUT, bus powered, ≤100 mA. 📄

**The buttons DO have LEDs, and nothing on the host can light them.** They are driven internally —
a button lights while it is held and goes dark on release — so a dark surface is the *Momentary*
configuration working, not an absence of lamps. There is no LED Mode setting on the mk1; the
Internal/External switch is a nanoKONTROL2 feature. ✅ Tested on this hardware rather than inferred,
item 245. Pd cannot light anything here, which is why every button is momentary and all visible state
lives on the Launchpad or the OLED.

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
| Receives from Pd | **Nothing musical, and no LED.** Sent from the Organelle with `amidi` to `hw:5,0,0`: every button CC on its own channel, every Note On 0–127 on channels 1–2, and the button CCs on **all 16 channels**. No LED responded to any of it, against a control that lights on a physical press | verified | 245 |
| ⛔ **It DOES answer a universal device inquiry** | `F0 7E 7F 06 01 F7` in, `F0 7E 00 06 02 42 04 01 00 00 23 00 00 00 F7` back — manufacturer `42`, KORG. **Its input is not inert**, and "receives nothing" was too strong | verified | 249 |
| The buttons have LEDs, driven **internally** | Press and hold lights one; release puts it out. The lamps exist — only host control is missing | verified | 245 |

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

**`m_nano` treats all six as ordinary momentary buttons** — `xport-1`…`xport-6` on press, no
toggle — and names them by physical position, because what a control *means* is not knowable at the
`m_` layer.

**The row was the mode selector from Phase 6 until the shift key needed the aux button.** Mode moved
to the Launchpad's top row, which was already showing the lit lamp — see
[map.md](../module/map.md). ⚠️ **All six therefore report a raw row on the OLED now**, because they
fall through to the table and miss it: item 242's rule, and correct, since a control that does
nothing and says nothing cannot be told from a broken one.

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

### Presence

`m_nano` registers as `active` on the presence bus and is polled every two seconds with a universal
device inquiry. **The nano answers** — manufacturer byte `42`, KORG, item 249 — so `[c_devid 66]`
inside `m_nano` is what tells its reply apart from the Launchpad's and the 404's on the one
`[sysexin]` the whole patch shares. ⚠️ **The argument is decimal and the byte is hex**: `42` is 66.

Any CC landing in this file's own channel block counts as liveness as well, so a nano being *played*
stays present even if one reply is dropped. The inquiry leaves on **port 2**, derived as
`(17-1)/16+1` from the channel block this file already takes as its one argument rather than passed
in separately. See [presence.md](../module/presence.md).

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

**Fix:** know the combo so you do not hit it by accident. The scene file is backed up in
[device/](../../device/README.md), and restoring it needs Kontrol Editor **2.4.0** — 2.5.0 dropped
first-generation support.

⛔ **What the transport buttons shipped with is UNKNOWABLE, permanently, and that is a stated
limitation rather than an open question — item 267.** They were reconfigured before anything read
the factory values, so the only way to find out is the reset above, which would destroy the scene
that `device/` exists to protect. **The trade is never worth it.** ⚠️ Do not read the MMC /
momentary-only incompatibility under *Facts* as evidence about what the default was; it stayed a
risk, never a finding.

### The CC numbers collide with the Volca's parameter range

The nano's transport row is CC 41–46; the Volca's parameters are CC 40–50.

**Fix:** nothing to do — harmless. The Volca is device 4 on channel 49+, the nano is device 2, and
Pd separates by channel long before a CC number is examined. Recorded so the collision is not
mistaken for a bug.

## Design

### `[ctlin]`'s outlets fire channel, then controller, then value

Right to left, as the convention says — but **measured, because this repo has been bitten here
before**: `polytouchin` emits note before value. Item 23.

**Fix:** trigger off the **value** outlet, which fires last.

### Momentary only — the LEDs are real, and the host cannot reach them

⚠️ **"No host LEDs" does not mean "no LEDs".** The buttons light on press, internally. What the mk1
cannot do is be lit by Pd, and that asymmetry is the whole problem: set a button to **Toggle** and its
LED would *latch*, holding visible state that Pd can neither read nor write. **It would then desync
silently** — the surface believing one thing, the patch another, and nothing able to show the
difference.

So every button is configured momentary and **Pd owns all state**. A momentary LED only ever says
"you are pressing this", which cannot disagree with anything. This is the single decision the whole
nano configuration rests on.

⚠️ **A dark nanoKONTROL is therefore correct and expected**, and it is not evidence of a fault, a
missing wire, or an unfinished feature.

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

**Nothing.** The one long-standing question — what the transport buttons shipped with — is a
**permanent limitation** rather than an unknown, and is stated as one under *A factory reset
destroys the map* in **Traps**. Item 267.
