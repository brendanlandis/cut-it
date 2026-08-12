<!-- schema: module -->
# Novation Launchpad Pro MK3

**Files:** `Cut It/m_launchpad.pd`, `Cut It/g_grid.pd` · **Gate:** `test/gate/launchpad-assert.sh` · **Bench:** `test/bench/launchpad-bench.pd`

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
| Ports 1 and 2 | Carry nothing **in Programmer Mode** | verified | — |
| ⛔ In **Live Mode** they are not silent | Port 2 carries the layout announcement, and port 0 carries a continuous **MIDI clock** flood. The old blanket "carry nothing" was measured in Programmer Mode only | verified | 250 |
| Pd channel block | 1–16 (input slot 1) | verified | — |
| Grid note formula | Pad at row *r*, column *c* is note `r*10+c`, both digits 1–8, **row 1 at the bottom** | verified | — |
| Pads | Velocity **and** pressure sensitive (polyphonic aftertouch). Not switches | verified | — |

`div 10` and `mod 10` recover the coordinates, so no lookup table is needed.

⛔ **Four counts are in play and they are four different quantities.** `g_grid.pd` uses all of them,
which is how "the Launchpad's 96 LEDs" sat in its header while it painted 108.

| Count | Is | Evidence | Item |
|---|---|---|---|
| **96** | **Physical buttons** on the device — 64 pads plus 32 edge | verified | — |
| **108** | **Specs sent per frame**, indices 1–108, per the index map below | verified | — |
| **109** | **Array cells** — `[array define $0-surface 109]`, indices 0–108. Cell 0 is allocated and deliberately never written, so an index maps straight to a cell with no arithmetic | verified | — |
| **~96/s** | **ALSA MIDI writes per second** at the frame clock. ⚠️ Unrelated to the first 96 — a rate, not a count, and the number `g_grid`'s dirty-flag gating exists to hold down | verified | 75 |

### The onboarding drive — a USB mass-storage interface that once broke boot

The device presents a vfat volume alongside its audio/MIDI interfaces, and it is the reason the
Organelle needs a patched `mount.sh`.

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Enumerates as | `/dev/sda` + `sda1`, `Novation Onboarding Drive` | verified | — |
| Size | **192 KiB** — `384 512-byte logical blocks`. ⚠️ `df` on a Mac reports 144 KiB, the usable filesystem: a different number for a different thing | verified | — |
| Write protect | **On.** `Write Protect is on`, and this is what broke boot | verified | — |
| Present when hot-plugged | Yes — ✅ re-verified hot 2026-08-08, with `/usbdrive` staying unmounted and `/sdcard` still `rw` | verified | — |

⛔ **Why it mattered:** `mount.sh` mounted it on `/usbdrive`, `USER_DIR` followed it onto a
read-only volume, and the front panel died trying to write there. The chain, and the guard that
stops it, are on [device-os.md](../device-os.md) and [device/README.md](../../device/README.md).
**Switching the drive off at the device is declined** — see *Design*.

### Transmits (Launchpad → Pd)

| Event | Message | Evidence | Item |
|-------|---------|----------|------|
| Pad press | Note-on, note `r*10+c`, velocity 1–127. Real velocity — soft presses register as low as 10 | verified | — |
| Pad release | Note-off | verified | — |
| Pad pressure | Polyphonic aftertouch, per pad, **simultaneous** — two pads held together give independent interleaved streams, which channel pressure cannot do | verified | 86 |
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

**Animation is free, and it is NOT tempo-locked.** The device animates flash and pulse itself — no
`[metro]` in Pd, which is the part that holds — but ⛔ **in Programmer Mode it ignores incoming MIDI
beat clock entirely and runs at its own internal rate.** Item 257, and it replaces a claim on this
page that said the opposite.

| Measured | Result | Evidence | Item |
|----------|--------|----------|------|
| Clock swept **5 → 1000 BPM** | Flash rate never moved | verified | 257 |
| The free-running rate, by null comparison | **≈118 BPM** — our clock tuned until it matched the flash | verified | 257 |
| MIDI **Start** sent at 5 BPM, a 24× difference | No change | verified | 257 |
| Clock delivered to **all three** MIDI ports at once | No change | verified | 257 |
| Clock present on the wire | ✅ `aseqdump` on Pd's out port: `Clock` at exactly 2/s at 5 BPM | verified | 257 |
| **Positive control** — pads lit over the same port, same `[midiout]` | ✅ Working throughout | verified | 257 |

📄 Novation's documentation describes flash and pulse as synchronising to beat clock and falling back
to 120 BPM. **The fallback is all this unit does.** ⚠️ 📄 is not ✅, and this is the second time in a
week that reading a manufacturer's chart produced a wrong belief — see the SP-404's SysEx row,
item 249.

⛔ **The design consequence: a beat-synced blink must be driven BY THE PATCH.** `g_grid` cannot hand
the tempo to the device and walk away. Nothing in Cut It depends on this today — the grid lights every
pad **static**, on channel 1 — which is exactly why it went unnoticed.

⚠️ **Live Mode is untested.** Every measurement above was taken in Programmer Mode, which is the only
mode Cut It ever uses. Whether the animation follows clock in Live Mode is unknown and, for this
instrument, does not matter.

Flashing is one period per beat and pulsing one per two beats — 📄 relative to *its* rate, not ours.

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

**A device that answers is a device Pd can notice the absence of.** A `c_presence` inside
`m_launchpad` polls the inquiry every two seconds and drops surface ownership after three missed
replies, so `g_grid` stops painting. It costs one round trip per poll against the 96 ALSA writes a
second the clock already makes. The recovery it triggers is not this file's — see
[presence.md](../module/presence.md).

⛔ **AND THE REPLY MUST BE MATCHED, NOT MERELY COUNTED.** This file used to treat *any* SysEx as
proof of its own presence, which was true only while nothing else in the rig transmitted any. All
three detectable devices answer the same inquiry (item 249) and there is exactly one `[sysexin]` box
in the whole patch, so the shortcut reports the Launchpad present whenever the **nano** answers.
`[c_devid 0]` matches byte 5 of the reply — `00`, Novation — and byte 5 discriminates all three.

`[sysexin]` instantiates *and fires* on this Pd build, and has **two outlets on 0.49, byte and
port** — measured by connecting each in turn, with outlet 5 tried first to prove the probe could
fail at all. Pd's own `midi-help.pd` wires outlet 0 only, so it was inconclusive. Item 273. The port
is unused: `c_devid` gates on the manufacturer byte instead, because whether that outlet counts from
0 or from 1 cannot be settled on a Mac.

### Mode changes are announced — on MIDI port 3, which nothing is wired to

✅ **Item 100, closed 2026-08-08.** Pressed by hand in Live Mode, each layout button emits

```
F0 00 20 29 02 0E 00 <layout> 00 00 F7
```

| | | Evidence | Item |
|---|---|---|---|
| Port it arrives on | **`Launchpad Pro MK3 MIDI 3`** — ALSA `40:2` | verified | 250 |
| Layout IDs seen | `02`, `03`, `04` — one per press | verified | 250 |
| ⛔ Cut It cannot see it | `wire.sh` connects **port 0 only**, so as wired today these never reach Pd | verified | 250 |

⛔ **The three ports are not interchangeable, and this is the measurement that proves it.** Watching
port 0 alone — which is what `lp-monitor.pd` did, and what every earlier attempt at item 100 did —
produces a confident *"it announces nothing"*. It announces plenty, two ports away.

### ⛔ In Live Mode it floods port 0 with MIDI clock

Measured in the same run: **5745 `Clock` events and nothing else** on port 0 while in Live Mode — no
notes, no CC, no pad traffic at all (item 250). Programmer Mode is what stops it.

⚠️ **`wire.sh` connects that port to Pd's Midi-In 1**, so a Launchpad left in Live Mode floods Cut
It's primary MIDI input. Today the mode SysEx at load prevents it — which makes that one message
load-bearing for more than the grid, and it fails silently if the device is not yet enumerated.

⛔ **`killall pd` DOES NOT TEST THE SAFE EXIT.** Tried on the device: the Launchpad stayed in
Programmer Mode with a frozen beat row. **Any exit that is not mother's own strands it** — which is
what `tools/lp-live.sh` exists to rescue. Item 96.

⛔ **`$0-want` is not `$0-own`.** `own` says the surface **is** ours; `want` says we still **intend**
it. Without that split, a handback is undone by the heartbeat two seconds later.

⛔ **PANIC NO LONGER HANDS THE DEVICE BACK, and it used to** (item 251). It surrendered the surface
and set `want` 0, so the watchdog stopped re-asserting and **the grid stayed dead until the patch was
reloaded** — during the one moment the instrument is most needed. Worse than was known when it was
written: in Live Mode the device floods MIDI port 1 with clock, and `wire.sh` connects that port to
Pd's Midi-In 1 (item 250), so a panic also buried Cut It's primary MIDI input. **Silencing notes has
nothing to do with surrendering the surface.** `quitting` is now the only handback.

⚠️ **The give-up bound is 70 s because 12 s was useless in a room.** The first build gave up twelve
seconds after the unplug, which reads as perfectly reasonable in source — **nobody reseats a cable
that fast**, and the very first hardware test missed the window entirely.

⚠️ **The recovery re-runs `wire.sh`, which is a FORK, and the bound is what makes that permissible.**
Phase 4's rule is *one fork per load, never per event* — written against error logging, which
cascades without limit. Three forks tied to one cable event cannot.

| | Evidence | Item |
|---|----------|------|
| `wire.sh` costs **~247 ms** and is **idempotent** — ⚠️ this row said **133 ms** until it was re-measured; see [presence.md](../module/presence.md) | verified | 292 |
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

**A power cycle is not the only rescue** — `tools/lp-live.sh` does it with no Pd running, item 96
above and the *stranded in Programmer Mode* Trap below.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### Entering Programmer Mode by SysEx locks out the Settings menu

⚠️ Novation documents the layout-select command as the escape, and **that command does nothing at
all on this unit.** If Pd dies mid-set without sending the Live Mode SysEx, the surface is stranded.

**Fix:** bind "return to Live Mode" somewhere reachable. `m_launchpad` does it on **`quitting`**,
and it is the only file allowed to. ⚠️ **On `quitting` only, since item 251** — panic used to do it
too, and that made `quitting` untested by accident, because the gate's Live Mode frame came from the
panic path. The gate now drives both. Out of band, `tools/lp-live.sh` does it without Pd —
⚠️ **but only once Pd is gone**: `amidi` cannot open the device while Pd holds it (`Device or
resource busy`), so it is a post-mortem tool, not a live one.

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

### CC 90 is the panic button, and it has two tiers

**The top-left corner — item 82, a real button this unit sends and Novation does not document,
whose numbering starts at 91.** It was unused, and `g_grid` can light it, so the armed state is
visible on the surface itself.

| Gesture | Raises | What happens |
|---------|--------|--------------|
| **Short press** | `panic` | All Notes Off to the SP-404 on all ten channels and to the Volca; realtime STOP on ports 1, 3 and 4; the aux LED goes red; the whole grid flashes red for a second; the OLED footer reads `panic` |
| **Held 2000 ms** | `recover` | `panic` again, then the patch **reloads** — every device re-enumerated and `wire.sh` run fresh |

⛔ **`panic` fires on the PRESS, not the release, and that is what makes the hold length free.** You
are already silent while you hold for the reload, so 2000 ms costs nothing and nothing reaches it by
accident. A hold therefore raises `panic` twice — once from `u_map`, once from `u_init` before the
reload — deliberately, so `recover` is self-contained whatever reaches it.

⚠️ **This is the *only* recovery for a device nothing can detect.** `m_volca` registers `none`, so it
can never be polled or declared lost, and it comes back only if a detectable device happened to fail
beside it — which failed on the bench exactly as the design allows, item 275. See
[presence.md](../module/presence.md) and [volca.md](volca.md).

⛔ **The map row names `recover` and never `panic`.** A control bound to `panic` in the table would
let a finger on a fader silence the instrument mid-set, and `map-assert.py` refuses one; the tiers
are the *handler's* business. The mechanism is on [map.md](../module/map.md), the reload on
[boot.md](../module/boot.md).

⚠️ **The reload does not surrender the surface.** It touches no ownership, and `quitting` still fires
on the way out because `/loadPatch` runs `killpatch.sh` first (item 252) — so the safe exit below
still returns the device to Live Mode. Item 251 stays closed.

### CC 91–96 are the mode selector, and they are the lamps

**The first six of the top row**, and `g_grid` has lit them as the mode lamps since Phase 6 — so
this is one surface rather than press-here-look-there. Pressing one selects that mode; the lamp it
paints is the confirmation.

⛔ **`u_map` gates each of the six on the press.** A CC button here sends **127 then 0**, where the
nanoKONTROL transport row this replaced sent only the press — so an ungated branch would select the
same mode twice per push. Idempotent, therefore invisible. The mechanism is on
[map.md](../module/map.md).

⚠️ **Mode selection is now on a device that can be unplugged**, which the nano equally was. It is a
lateral move rather than a regression, and it is not a control you need in a hurry.

### CC 80 is free

**The left column's top button**, one row under the CC 90 corner. It held the diagnostic screen for
part of a day and gave it up: ⛔ **a Launchpad that has come unplugged sends no CC**, so the control
that would name the missing device was dead in exactly the case the screen exists for. `diag` moved
to the Organelle's own keyboard, under the aux modifier — see [organelle.md](organelle.md).

⚠️ **The same objection applies to everything else on this surface**, `recover` on CC 90 included.
What changed is not that the Launchpad became reliable but that there is now somewhere better for
the controls you reach for when a device has died. Anything put on CC 80 should be something you
would not miss if the Launchpad were the thing that went.

### Pressure is the forgotten input

The pads are polyphonic-aftertouch sensitive, and that channel is free panel space: any continuous
parameter can ride pad pressure while a pad is held. It is the most expressive control on the rig
and costs no buttons.

### The firmware update is DECLINED, and the onboarding drive stays on

✅ **Item 265.** Novation Components can perhaps switch the onboarding drive off, but Components
refuses to open the Launchpad at all until a **firmware update** is accepted. ⛔ **That would change
the firmware every `verified` fact on this page was measured against** — including item 257, that
the device ignores incoming MIDI clock — on the one device in the rig with a known enumeration
quirk (item 248).

**The changelog was read before deciding, rather than left as an unknown.** 📄 Novation's V1.2 /
V1.2.1 addendum lists everything the update adds:

| V1.2 / V1.2.1 / V1.2.2 | Bears on this rig? |
|---|---|
| Unquantised recording | No — it belongs to the **Launchpad's own** sequencer, and ⛔ **Programmer Mode bypasses that entirely**: the patch owns the surface |
| Performance Velocity, Probability and Mutation | No — same, and ⚠️ **v0.4 is building sequencing, probability and mutation in Pd on purpose.** The firmware's versions are not merely unused, they are the thing being replaced |
| **Pad Trigger Threshold** (new setting) | ⚠️ **Yes** — a threshold change can move measured velocity |
| Legacy Mode brought in line with Launchpad X / Mini MK3 | No |
| **Aftertouch threshold fix** | ⚠️ **Yes** — `m_launchpad`'s `pressure` subpatch depends on aftertouch behaviour |
| Crash fix, multiple Novation devices connected then disconnected | No — one Novation device here |

⛔ **Nothing in it touches MIDI clock, tempo sync or LED animation**, so it would not be expected to
fix item 257 — the device ignoring incoming clock — which is the only Launchpad behaviour this
project actually wants changed. **The update offers nothing needed and risks two things measured**
(items 193 and 204, velocity and aftertouch).

**So the trade is bad and the decision is to stop asking.** The drive is neutralised on the device
side instead, by a guard in `mount.sh` — see [device/README.md](../../device/README.md).
⚠️ **Revisit only if an update is being done for another reason** — then re-measure velocity and
aftertouch afterwards rather than trusting the old numbers.

## Open

- ✅ **Item 235 is closed, and verified on this hardware 2026-08-10.** Booted with the Launchpad
  unplugged and plugged it in after: five `wire.sh` attempts missed it, the sixth caught it, and it
  came back **completely** — re-enumerated, Programmer Mode re-asserted by the watchdog heartbeat at
  a device the init SysEx had never reached, ownership restored, `g_grid` repainting the mode lamp.
  No `warn` was raised while it had never answered, which is the arming gate holding, and the safe
  exit still returns it to Live Mode through `/loadPatch`. See
  [presence.md](../module/presence.md).
- ⬜ **`[polytouchin]` has no stub, so the pressure path is uncovered.** See
  [plan-v04.md](../../plan-v04.md) §3. It was in neither MIDI
  inventory list in `test/gate/lib-scratch.sh` until a closed-question scan found it, and this
  page's own text calls aftertouch the most expressive control on the rig. A `t_polytouchin` would
  be the same shape as `t_ctlin`.
- ✅ **Item 77 is closed, and the question turned out not to apply.** It asked where the animation
  rate stops tracking, above and below. There is no tracking to lose: in Programmer Mode the device
  ignores incoming clock at any tempo. Measured with `tools/stage-patches/Anim Probe/` — item 257,
  under **Facts**.
- ⬜ **What every layout ID means.** `02`, `03` and `04` were seen; the full set and their names are
  not established. See [plan-v04.md](../../plan-v04.md) §3. ✅ *That it announces at all* is now
  answered — item 100 is closed, see *Mode changes are announced* under **Facts**.
- ⬜ **What firmware version this unit is on, in Novation's terms.** Item 98, and
  [plan-v04.md](../../plan-v04.md) §3. The device inquiry returns firmware bytes `00 04 06 05`
  and nothing published maps that to a marketing version, so *how far behind* this unit is cannot
  be stated. ⚠️ **It does not change the decision** to decline the update — see *The firmware
  update is DECLINED* under **Design**.
