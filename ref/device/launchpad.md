<!-- schema: module -->
# Novation Launchpad Pro MK3

**Files:** `Cut It/m_launchpad.pd`, `Cut It/g_grid.pd` · **Gate:** `tools/phase6-assert.sh`

## What it is

**The only device in the rig that is a genuine blank slate, and the only one Pd can light.** It runs
in **Programmer Mode**, where every built-in behaviour is disabled and each button becomes a note or
CC number the patch defines. 96 button LEDs plus the logo — 97 addressable — painted across an index
span of 1–108.

`m_launchpad.pd` is the only file that talks to it: Programmer Mode, the safe exit, pads and ring
onto `param` and `disp`, pressure onto `param` alone, and the replug watchdog. `g_grid.pd` owns its
LEDs and nothing else does.

The unit is a **MK3** (announced Jan 2020; a 09/2020 build date rules out MK1). Use the MK3
reference — SysEx headers and side-button note numbers differ from MK1. Programmer Mode is
[officially documented](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/LPP3_prog_ref_guide_200415.pdf),
not a hack.

**It is not a text channel.** The Pro MK3 has no text-scrolling SysEx — the word "scroll" appears
nowhere in Novation's reference, and the command summary lists six commands. The Mini MK3 and
Launchpad X have it; this does not. Treat it as 96 RGB pixels of *spatial* state.

## Facts

### Ports and addressing

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Programmer Mode port | 0 — `hw:3,0,0`, seq `28:0` | verified | — |
| Ports 1 and 2 | Carry nothing in either direction | verified | — |
| Pd channel block | 1–16 (input slot 1) | verified | — |
| Grid note formula | Pad at row *r*, column *c* is note `r*10+c`, both digits 1–8, **row 1 at the bottom** | verified | — |
| Pads | Velocity **and** pressure sensitive (polyphonic aftertouch). Not switches | verified | — |

`div 10` and `mod 10` recover the coordinates, so no lookup table is needed.

### Transmits (Launchpad → Pd)

| Event | Message | Evidence | Item |
|-------|---------|----------|------|
| Pad press | Note-on, note `r*10+c`, velocity 1–127. Real velocity — soft presses register as low as 10 | verified | — |
| Pad release | Note-off | verified | — |
| Pad pressure | Polyphonic aftertouch, per pad, simultaneous | verified | — |
| Function buttons | Control change, per the index map below | verified | 82 |
| Device inquiry reply | SysEx — see *Device inquiry* | verified | 98 |

### The Programmer Mode index map

41 perimeter buttons pressed twice, identical both passes. **The documented map was wrong in two
places**, both marked below.

| Buttons | Numbers | Type | Evidence | Item |
|---------|---------|------|----------|------|
| 8×8 grid | 11–88 (`r*10+c`) | Note | verified | — |
| Top-left corner | **CC 90** — absent from the documentation, which starts at 91 | CC | verified | 82 |
| Top row, left→right | CC 91–98 | CC | verified | 82 |
| Logo / top-right corner | **CC 99 — an LED only, never a button.** Lighting it works; pressing it transmits nothing | write-only | verified | 198 |
| Right column (scene launch), top→bottom | CC 89, 79, 69, 59, 49, 39, 29, 19 | CC | verified | 82 |
| Left column, top→bottom | CC 80, 70, 60, 50, 40, 30, 20, 10 | CC | verified | 82 |
| Bottom row, left→right | CC 101–108 | CC | verified | 82 |
| **A second bottom row below it**, left→right | **CC 1–8** — absent from the documentation entirely | CC | verified | 82 |
| Index 0, the Setup button | Outside the span, and a real limit — a valid one-spec frame lights nothing and it transmits nothing | unaddressable | verified | 110 |

`g_grid` paints **indices 1–108**, CC 1–8 included. **That span is a choice, not a limit** — the
apparent cliff at 120 was a broken probe, and a clean 120-spec message paints the whole surface.
Novation documents "up to 106" 📄 and this unit exceeds it.

The reason for the wide span is not that anything wants those buttons: **LED state survives the
Programmer Mode switch**, so an index outside the painted span holds whatever Live Mode last drew
there, forever, in every session.

### Lighting, two ways

Both address pads by the Programmer Mode index above, **always** — even when a different layout is
selected.

**1. Note-on, where velocity is a palette index.** The MIDI *channel* selects the animation:

| Channel | Mode | Pd object | Evidence | Item |
|---------|------|-----------|----------|------|
| 1 | Static | `[noteout 1]` | verified | — |
| 2 | Flashing — alternates the channel-1 and channel-2 colours, so send both | verified | — |
| 3 | Pulsing — one ch3 colour ramped toward black, so it spends real time dim | verified | — |

Velocity indexes a **128-entry colour palette, not brightness** — velocity 64 is a colour, not
half-lit. Velocity 0 turns the pad off. For pulsing, pick a bright palette index or it reads as weak.

**2. Per-pad RGB SysEx**, for anything the palette cannot express:

```
F0 00 20 29 02 0E 03  <type> <index> <data...>  F7
```

| Type | Lighting data | Evidence | Item |
|------|---------------|----------|------|
| `00` | Static — 1 byte, palette entry | doc | — |
| `01` | Flashing — 2 bytes, colour B then colour A | doc | — |
| `02` | Pulsing — 1 byte, palette entry | doc | — |
| `03` | RGB — 3 bytes: red, green, blue, each **0–127, not 0–255** | doc | — |

| Measure | Value | Evidence | Item |
|---------|-------|----------|------|
| Specs in one message | 99 works, and so does 120 — the whole surface fits in one message | verified | 83, 105 |
| What `g_grid` sends | 108 specs, indices 1–108 | verified | — |
| The ring | Lit by the same message, same index | verified | 84 |

**Animation is free and tempo-locked.** The device animates flash and pulse itself — no `[metro]` in
Pd — and synchronises to incoming MIDI beat clock, falling back to 120 BPM or the last clock
received. Flashing is one period per beat, pulsing one per two beats. 📄 Since the Organelle is
clock master, LED animation follows the patch's tempo for nothing, confirmed by sweeping knob 1
against three pads lit static / flashing / pulsing.

### Mode control

All share the header `F0 00 20 29 02 0E`. 📄 except as marked.

| Command | Message | Meaning | Evidence | Item |
|---------|---------|---------|----------|------|
| `0E` | `F0 00 20 29 02 0E 0E 01 F7` | Enter Programmer Mode | verified | — |
| `0E` | `F0 00 20 29 02 0E 0E 00 F7` | Return to Live Mode | verified | — |
| `00` | `F0 00 20 29 02 0E 00 <layout> F7` | Select layout — **does nothing on this unit** for ids 0, 4 and 5 | verified | 87 |
| `03` | `F0 00 20 29 02 0E 03 <spec…> F7` | LED lighting | verified | — |
| `10` | `F0 00 20 29 02 0E 10 <mode> F7` | DAW mode (1) / Standalone (0) | doc | — |
| `01` | `F0 00 20 29 02 0E 01 …` | DAW fader bank setup | doc | — |
| `19` | `F0 00 20 29 02 0E 19 <bank> F7` | Stop faders for bank | doc | — |

DAW mode and the fader messages are for Session-view integration and are **not used here** — listed
so they are not mistaken for something missing.

Because layout-select does nothing, **the choice available to Pd is two-valued rather than a layout
table**, and `m_launchpad`'s surface-ownership state keys off exactly that.

### Device inquiry, and why it matters

| Field | Value | Evidence | Item |
|-------|-------|----------|------|
| Send | `F0 7E 7F 06 01 F7` | verified | 98 |
| Reply | `F0 7E 00 06 02 00 20 29 23 01 00 00 00 04 06 05 F7` | verified | 98 |
| Manufacturer | `00 20 29` — Novation, the same three bytes that open every Launchpad SysEx header | verified | 98 |
| Family / member | `23 01` / `00 00` | verified | 98 |
| Firmware | `00 04 06 05` | verified | 98 |

**A device that answers is a device Pd can notice the absence of.** `m_launchpad`'s watchdog polls
the inquiry every two seconds and drops surface ownership after three missed replies, so `g_grid`
stops painting. It costs one round trip per poll against the 96 ALSA writes a second the clock
already makes.

`[sysexin]` instantiates *and fires* on this Pd build.

⚠️ **The recovery re-runs `wire.sh`, which is a FORK, and the bound is what makes that permissible.**
Phase 4's rule is *one fork per load, never per event* — written against error logging, which
cascades without limit. Three forks tied to one cable event cannot.

| | Evidence | Item |
|---|----------|------|
| `wire.sh` costs **133 ms** and is **idempotent** | verified | — |
| Ten forks fired back to back produced **no audio complaint** on Pd's console | verified | — |
| The recovery gives up at about **70 s**, so a device nobody intends to plug back in cannot make Pd fork all night | verified | — |

**All three were measured before the rule was bent**, which is the only reason bending it was
allowed.

### Aftertouch is a device setting

**Polyphonic aftertouch must be enabled on the device, and it is not the default** — the default is
Channel Pressure, one value for the whole surface.

Hold `Setup`, press the **third Track Select button**, choose *Polyphonic Aftertouch*. There is an
*Aftertouch Threshold* on that page worth tuning. Programmer Mode locks out the Setup menu, so exit
to Live Mode first.

### Recovery

| Behaviour | Evidence | Item |
|-----------|----------|------|
| A power cycle rescues a stranded device — unplugged and replugged from Live Mode, it returns in Live Mode | verified | — |
| Live Mode returns to whichever built-in mode was last used, not a fixed default | verified | — |
| LED state survives Programmer → Live → Programmer, bringing the previous colours back | verified | — |

`tools/lp-live.sh` rescues a Launchpad stranded in Programmer Mode with no Pd and no power cycle.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### Entering Programmer Mode by SysEx locks out the Settings menu

⚠️ Novation documents the layout-select command as the escape, and **that command does nothing at
all on this unit.** If Pd dies mid-set without sending the Live Mode SysEx, the surface is stranded.

**Fix:** bind "return to Live Mode" somewhere reachable. `m_launchpad` does, on both `panic` and
`quitting`, and it is the only file allowed to. Out of band, `tools/lp-live.sh` does it without Pd.

### `loadbang` fires before ALSA connections exist

⛔ Init SysEx sent on `loadbang` goes nowhere, silently.

**Fix:** `[loadbang]` → `[del 2000]` or longer.

### LED state survives mode switches

⛔ Entering Programmer Mode does not blank the grid, so an index the patch never paints holds
whatever Live Mode last drew there — forever, in every session.

**Fix:** clear the whole span on init, and paint the full 1–108 rather than a subset.

### `polytouchin` emits note before value

⛔ Wiring it straight to `[noteout]` lights a pad with the *previous* event's pressure.

**Fix:** `[trigger]` to force the order, per the project's fan-out rule.

### MIDI data bytes are 7-bit, and LED indices can exceed them

⛔ Counting LED indices from 10 reaches index **128** at the 119th spec — `0x80`, a **Note Off
status byte** — which cuts the SysEx short. The tail is then parsed as channel-voice messages, and
index 129 is `0x81`, Note Off on channel 2, the Launchpad's *flashing* channel, addressing note 21 —
the colour byte in every spec. The symptom is one pad, always row 2 column 1, left flashing when
every spec sent was static.

**Fix:** keep every index ≤ 127 in any probe or paint.

### A malformed SysEx leaves the pipe dirty

⛔ The next message sent is swallowed closing it, and only the one after that gets through.

**Fix:** after any malformed frame, send one throwaway message before trusting the next.

### Programmer Mode locks out the device's own mode buttons

⚠️ They cannot be used to change mode while Pd owns the surface. Pressed in Programmer Mode they are
ordinary CC — `176 93 127` then `176 93 0` for the top row.

**Fix:** treat mode as something the patch owns, not the performer.

### The inquiry poll alone cannot detect a Mac replug

⚠️ The device answers the inquiry in *either* mode, so a replug that drops it back to Live Mode is
invisible to the poll.

**Fix:** run a Programmer Mode heartbeat alongside the poll, which fixes the state without needing to
detect anything. `m_launchpad` does both.

## Design

### Three tiers, and Cut It only builds the top one

Programmer Mode is all-or-nothing: entering it disables every built-in mode, and Pd flips between
Programmer and Live by SysEx. **Which world the surface is in is something the patch decides at
runtime rather than once.**

| Tier | What | Work | LED control |
|------|------|------|-------------|
| **Built-in** (Note, Chord, Sequencer, Projects) | Novation's, fully featured | None | Device owns them |
| **Custom Modes** — 8 slots, built in Novation Components | Drag-and-drop widgets: scaled keyboards, drum grids, virtual faders. Pads send Note / CC / Program Change | Moderate, no code | Limited — one "on" colour per mode, per-pad "off" colours |
| **Programmer Mode** | Everything from scratch | Most | Full dynamic RGB |

**Do not rebuild the built-ins.** Note mode's scale tables, root selection and isomorphic layout
maths are genuinely fiddly in Pd and Novation's are good. Chord mode is worse to replicate. The
Sequencer is 4 tracks × 32 steps × 8-note poly with pattern chaining — a substantial project on its
own, and it is already the compose-time authoring tool. Projects handles save/recall of that data.

**The tier 2/3 boundary is dynamic colour.** Custom Modes allow only one "on" colour per mode, so
static colour-coding works but "empty / loaded / queued / playing" as four distinct states does not.
Anything needing that needs Programmer Mode; a plain CC grid or a scaled keyboard does not.

Novation Components needs a computer — you cannot author Custom Modes from the Organelle, but once
written they persist on the device.

### Pressure is the forgotten input

The pads are polyphonic-aftertouch sensitive, and that channel is free panel space: any continuous
parameter can ride pad pressure while a pad is held. It is the most expressive control on the rig
and costs no buttons.

## Open

- ⬜ **The watchdog cannot recover a device that was absent at load.** A replug destroys the ALSA
  links outright on the Organelle, and the bounded `wire.sh` recovery does not cover the
  never-connected case. Item 235 — see [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **The animation rate has its own range, not pinned down.** Past an upper and a lower limit the
  device reverts to a default rate instead of tracking, and a Start makes it dip briefly before
  settling — the same shape as the 404's 40–200 window. The pulse stream itself is known good. Item
  77 — see [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **Whether the device announces a mode change made by hand in Live Mode** is unmeasured. Item
  100 — see [plan-v03.md](../../plan-v03.md) §4.
