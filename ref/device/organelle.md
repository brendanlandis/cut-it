<!-- schema: module -->
# Organelle 1 — the panel, the OLED and the aux LED

**Files:** `Cut It/m_organelle.pd`, `Cut It/g_oled.pd`, `Cut It/g_led.pd`, `Cut It/u_mother-stub.pd` · **Gate:** `tools/phase6-assert.sh`

## What it is

The host device and its own control surface: **four knobs, an encoder, an aux button, a keyboard, a
128×64 monochrome OLED and one RGB LED.**

⛔ **The Organelle's own panel is not MIDI.** Keys, knobs, encoder, aux button and the OLED all
arrive as ordinary Pd messages from `mother.pd`, on named sends and receives. Nothing about the front
panel is addressable over MIDI, and no CC number will ever reach it. **This is the single most
important thing to know about the device's control surface.**

It is a USB **host** only — no USB-device port, so it never appears as a MIDI device to anything
else. All MIDI in this rig is Pd talking to the four attached controllers.

Three abstractions divide it: `m_organelle` reads the panel onto `param` and `disp`, `g_oled` owns
the screen and is the only file allowed to send `oscOut` or `screenLine*`, and `g_led` owns the aux
LED. The display *arbiter* they share with `g_grid` is instrument architecture, not device fact —
see [display.md](../module/display.md).

This page covers the **Organelle 1 only**, not the M, S or S2. Organelle 1 and M differ here, and the
public `Organelle_OS` repo documents the M.

## Facts

### The `mother.pd` interface

The full name list is enumerated from `/root/fw_dir/mother.pd` itself — every `[s]` and `[r]` in the
file — and lives in `ref-conventions.md` under *The global name allowlist*, because those names are
**reserved rather than merely documented**.

| Direction | Names | Evidence | Item |
|-----------|-------|----------|------|
| **In** (mother → patch) | `notes`, `knob1`–`knob4`, `enc`, `encbut`, `aux`, `vol`, `exp`, `fs`, the MIDI-gate names, `quitting` | verified | — |
| **Out** (patch → mother) | `screenLine1`–`5`, `led`, `goHome`, `oscOut`, `enableSubMenu` | verified | — |

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| `enc`, `aux`, `encbut` | Send **`1`/`0`, not `±1`** | verified | — |
| `quitting` | The **only** shutdown hook — Pd 0.49 has no `closebang` | verified | — |
| Knob range | **0–1**, not 0–127 like every MIDI control in the rig | verified | — |
| Pedal jack | `fs` / `fsRaw` / `footSwitchPolarity` and `exp` / `expRaw` / `expOverride` — a sustain switch **or** an expression pedal, not both. Deliberately unused | doc | — |

### The OLED

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Framebuffer | 128×64 monochrome | verified | — |
| Text path | `[s screenLine1]`…`[s screenLine5]` — five lines, **21 characters**, monospace | verified | — |
| Font is fixed-width | `W` and `i` end at the same column, so column layouts are safe | verified | — |
| Graphics path | OSC to `[s oscOut]`, which `mother.pd` relays to the `mother` binary | verified | — |
| Fonts | 8, 16, 24, 32 px. 21 chars/line is the 8px font | verified | — |
| Repaint rate | `g_oled` rebuilds screen 3 at **10 Hz** | verified | — |
| **Latency** | **~200 ms behind the audio** — see *Traps* | verified | 206 |

```
[msg sendtyped /oled/gPrintln iiiiii 3 6 18 24 1 $1]  →  [s oscOut]
```

### Graphics commands

Every command takes **screen number as its first argument**. 📄 from `main.cpp` at tag `v4.0`.

| Command | Args after screen | Evidence | Item |
|---------|-------------------|----------|------|
| `gClear` | `1` | verified | — |
| `gShowInfoBar` | `0` / `1` | verified | — |
| `gSetPixel` | `x y colour` | doc | — |
| `gLine` | `x1 y1 x2 y2 colour` | verified | — |
| `gBox` | `x y w h colour` | verified | — |
| `gFillArea` | `x y w h colour` | doc | — |
| `gCircle` / `gFilledCircle` | `x y r colour` | verified | — |
| `gInvert` / `gInvertArea` | `1` / `x y w h` | doc | — |
| `gPrintln` | `x y height colour <text…>` | verified | — |
| `gCharacter` | `x y char colour size` | doc | — |
| `gWaveform` | 128-byte **blob** — draws 127 connected lines | verified | 202 |
| `gFrame` | 1024-byte **blob** — whole framebuffer, `memcpy`'d | doc | — |
| `gFlip` | *(none)* — pushes to the display | verified | — |

**`gPrintln` concatenates mixed atoms** — symbols, floats and ints, separated by spaces. Only
arguments 0–4 (screen, x, y, height, colour) must be ints; everything after is `strcat`'d, so a
label and a value go in one message.

### The four screen buffers

```
AUX = 1     MENU = 2     PATCH = 3     ALERT = 4
```

| Fact | Evidence | Item |
|------|----------|------|
| The argument is the enum index **plus one**, and `AUX` is the default for out-of-range values | verified | — |
| **Draw to screen 3.** Screen 1 is an undisplayed buffer | verified | — |
| All four buffers are writable, and `/oled/setscreen <n>` switches between them **in both directions** | verified | — |
| `save-patch.sh` flips to AUX for "Saving…" and back, so the alert path is: draw into a spare buffer, `setscreen` to it, `setscreen 3` to return | verified | — |

There are matching `/oled/aux/clear` and `/oled/aux/line/N` commands.

### The aux button LED

**`[s led]` takes one number, 0–7.** `mother.pd` applies `[% 8]`, so any float is legal and 8 wraps
back to off. It reaches `SerialMCU::setLED(unsigned)` — the same front-panel microcontroller and the
same serial link as the OLED.

| `led` | Colour | Evidence | Item |
|-------|--------|----------|------|
| 0 | off | verified | — |
| 1 | red | verified | — |
| 2 | yellow | verified | — |
| 3 | green | verified | — |
| 4 | light blue (cyan) | verified | — |
| 5 | dark blue | verified | — |
| 6 | pink (magenta) | verified | — |
| 7 | white | verified | — |

**Seven colours and off — a full RGB LED, not an indicator lamp.**

`mother.pd` **permutes the value on the way out**, mapping patch-facing `0…7` to hardware
`0,4,5,1,3,2,6,7`, and the *hardware* value is a **3-bit RGB bitmask**: bit 0 = green, bit 1 = blue,
bit 2 = red. Raw 1/2/4 are the primaries and 3/5/6/7 their mixes. mother is reordering that bitmask
into spectrum order so patch authors get `red → yellow → green → cyan → blue → magenta → white`.

**mother already sets `led 0` on `quitting`**, so a safe exit needs no LED handling of its own.

To re-read the colours by eye — five seconds each, in **hardware** order, which is why the list looks
scrambled:

```sh
ssh root@organelle.local 'for r in 0 4 5 1 3 2 6 7; do
  oscsend localhost 4001 /led i $r; echo "raw $r"; sleep 5; done
  oscsend localhost 4001 /led i 0'
```

### What Cut It puts on the LED

`g_led` owns `led`, and callers send a **state** on the `disp` bus — `led running` — never a colour.

| State | `led` | Colour | Means | Evidence | Item |
|-------|-------|--------|-------|----------|------|
| `off` | 0 | off | Nothing claims it | verified | — |
| `stopped` | 5 | dark blue | Patch up, transport stopped | verified | — |
| `running` | 3 | green | Transport running | verified | — |
| `panic` | 1 | red | Panic raised — cleared by the next start or stop | verified | — |

Anything `g_led` does not recognise raises `warn g_led unknown-led-state` and **leaves the LED
alone**, so a typo cannot silently blank the only non-screen indicator in the rig.

### `mother.pd` maps MIDI onto the front panel

`mother.pd` runs `[ctlin 21]` through `[ctlin 26]` **with no channel argument, so they are OMNI**,
and routes them onto the Organelle's own controls. Read out of `/root/fw_dir/mother.pd`:

| Incoming | mother does | Evidence | Item |
|----------|-------------|----------|------|
| CC 21–24, any channel | Sets `knob1`–`knob4` | verified | — |
| CC 25 | Presses **`aux`** | verified | — |
| CC 26, CC 64 | Encoder / footswitch | verified | — |
| Program change | **Loads a different patch** | verified | — |
| Note on/off | Sends `notes` | verified | — |

`u_init` sends `midiInGate 0` at load **and again at 2 s** to shut all of this off. mother's own
comment states the contract: *"All MIDI output and input can be suppressed by sending a 0 to
`midiOutGate` and `midiInGate`."*

| Fact | Evidence | Item |
|------|----------|------|
| The gate covers only **MIDI-derived** paths. mother has *two* `s notes` — one fed by `oscIn`, the physical keyboard, and one behind the gate, which is `notein`. Same split for the knobs | verified | — |
| So the front panel keeps working and only mother's *interpretation of incoming MIDI* stops. Cut It's own `[ctlin]` objects read Pd's MIDI system directly and are unaffected | verified | — |
| `midiInGate` is a name the patch **sends**, despite being listed among the ones mother sends to the patch — it is `[r midiInGate]` inside mother | verified | — |
| `/sdcard/MIDI-Config.txt` stores only the channel, so there is **no persistent setting** for this | verified | — |
| Entering mother's *MIDI Config* page mid-session does **not** re-open the gates — safe to visit during a set | verified | 201 |

### Saving

✅ **Verified end to end.** `Storage → Save` runs `save-patch.sh`, which does three things:

| Step | What happens | Evidence | Item |
|------|--------------|----------|------|
| 1 | Sends OSC `/saveState 1` to Pd on port 4000, arriving in the patch as `[r saveState]` | verified | — |
| 2 | **Sleeps**, to let the patch write whatever it wants into `/tmp/state/` | verified | 135 |
| 3 | `cp -r /tmp/state/*` — everything written lands in the **patch folder** | verified | — |

| Fact | Evidence | Item |
|------|----------|------|
| ⚠️ **`saveState` arrives as a BANG, not as `1`.** mother routes the OSC message through a `[t b b b]`, so the float is discarded — a `[route 1]` or `[select 1]` on it never fires | verified | 137 |
| ⚠️ **The budget is 250 ms, not 500.** `save-patch.sh` sleeps `.5` but `save-new-patch.sh` sleeps `.25` | verified | 135 |
| ⚠️ **`Storage` is a TOP-LEVEL menu**, not a System submenu | verified | 136 |
| On load the patch folder is copied to `/tmp/patch/`, so **write to `/tmp/state/`, read from `/tmp/patch/`**. `/tmp/state/` already exists — created *and cleared* at patch load | verified | — |
| ⛔ **`/tmp/patch` is a SYMLINK to the patch folder**, and it is Pd's working directory — so a **relative** `[text write]` bypasses `/tmp/state` and the copy entirely and mutates the deployed patch immediately | verified | 140 |
| `/tmp` is **tmpfs**; the SD card is only touched by mother's `cp`, after the sleep. A 2000-line write costs **~16 ms** either way, because the cost is Pd's serialisation rather than the storage | verified | 141 |
| mother uses this for the four knob positions, so **every Save creates `knobs.txt`** — a patch cannot opt out by shipping without one | verified | 139 |
| ⛔ **The saved file BEATS the physical knob.** Knob 1 fully clockwise, patch reloaded, and it booted at the file's **57 BPM** rather than the knob's 500 | verified | 200 |

⚠️ **`knobs.txt` is four normalised knob positions, not knob labels** — two real files off the device
read `0.195503 0.230694 0.134897 0.0136852;` and `0.521994 1 0.84262 0.723363;`. Cut It ships without
one and `Storage → Save` creates it; until then mother logs `knobs.txt: can't open` at boot, which is
expected and harmless. `./deploy.sh` will not remove it once it exists — `--clean` will.

⛔ **So after any Save every knob is desynced from its value, and the first touch jumps** — up to the
full range, and knob 1 is master tempo. **Measured, that is a 443 BPM lurch**: a jump that is
defensible on a fader you are already holding and much weaker at boot, on a control nobody has
touched. **Nothing on the instrument can detect this**: mother reports
position, not whether the position still matches the file. It happens on every boot rather than only
on a bank switch, and it is the concrete case for parameter pickup in
[plan-v03.md](../../plan-v03.md) §4.

⚠️ **Cut It does not deliver its data this way.** `u_state` writes straight to `/sdcard` with an
absolute path, so nothing it does has to finish inside the sleep. The only part that reaches the
patch is that `saveState` triggers a `manual` commit — see [state.md](../module/state.md). The 250 ms
still binds anything that writes into `/tmp/state/` and relies on the copy, which today is only
`knobs.txt`.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### The OLED lags the audio by ~200 ms

⛔ **It is not a rhythmic display.** The audio, the Launchpad's beat row and the footer BPM all
agree; the OLED trails by roughly a 16th note at 74 BPM.

| Surface | Path | Result |
|---------|------|--------|
| Launchpad | `g_grid` → ALSA MIDI, repaints at 50 Hz when dirty | tight |
| OLED | `g_oled` → `oscOut` → UDP → the `mother` binary → **serial to the front-panel MCU**, redrawn at 10 Hz | **~200 ms behind** |

The 10 Hz frame clock alone is up to 100 ms of it, before the OSC hop and the serial link. **Not
fixable by tuning** — raising the frame rate spends UDP and CPU on a transport that still ends at a
serial MCU.

**Fix:** anything that must agree with what you *hear* — a playhead, a beat indicator, step position
— belongs on **the Launchpad**. The OLED is for state, values and text, where 200 ms is invisible.

### mother's OMNI CC 21–26 collide head-on with the nanoKONTROL

⛔ The nano's top button row is CC 21–29 by this project's by-tens scheme, and mother's `[ctlin 21]`
through `[ctlin 26]` take **any channel**. Measured on the device: `btn-t-5` **pressed aux and
toggled the transport**, and `btn-t-1`…`btn-t-4` slammed knobs 1–4 — so a single button press jerked
the tempo to 500 BPM and back to 10 on release. A program change loads a different patch outright.

**Fix:** `u_init` sends `midiInGate 0`.

### `midiInGate` must be sent twice, and the second send is the one that matters

⛔ **The mother *binary* pushes its own `midiInGate 1` over OSC** — `mother.pd` has
`routeOSC /midiInGate` — roughly half a second after the patch loads, so a value sent at `loadbang`
is **silently overwritten**. Measured with an `[r midiInGate]` print: `0` (ours), `1` (the binary),
then `0` again at 2 s, and nothing further out to twelve seconds.

**Fix:** send it at load **and** again at 2 s. Anything a patch sets on mother's MIDI settings at
load needs the same treatment.

### Screen numbering is enum+1, and the default is an invisible buffer

⛔ Sending screen 1 writes to `AUX`, which is not displayed, and looks **exactly like a dead API**.

**Fix:** draw to screen 3.

### Every OLED handler discards non-int arguments

⛔ Each checks `msg.isInt()` and drops the message otherwise. **Pd sends floats by default**, so
plain `send` fails silently.

**Fix:** `sendtyped /oled/gX iiiii …` with explicit int typetags is mandatory.

### The typetag must match the argument count exactly

⛔ `oscOut` reaches the display through mrpeach `[packOSC]`, which validates and, on a mismatch,
**drops the message with an error you cannot see**: *"Tags count 5 doesn't match argument count 6"*.

| Message | Result |
|---------|--------|
| `sendtyped /oled/gPrintln iiiiii 3 6 6 24 1 42` | packs |
| `sendtyped /oled/gPrintln iiiiisi 3 4 2 24 1 L 42` | packs — label plus value |
| `sendtyped /oled/gPrintln iiiiisss 3 4 54 8 1 cut it v0.2` | packs — three symbols |
| `sendtyped /oled/gPrintln iiiii 3 6 34 24 1 99` | **dropped** |

**Fix:** count the atoms after the address and make the typetag the same length. **Every space in a
message box is another atom.**

### `gFlip` or nothing

⛔ Draw commands set `newScreen = 0`; only `gFlip` pushes to the display.

**Fix:** end every redraw with it.

### mother repaints after a patch load and restores the info bar

⛔ A `gShowInfoBar` sent once on `loadbang` gets undone. The info bar is **the top 8 pixel rows of
the 64** — `OledScreen::drawInfoBar` clears and owns `pix_buf[0…127]`, one byte per column — so
anything drawn there is obscured.

**Fix:** send `gShowInfoBar 3 0` on **every** redraw, not at init. It does not belong in `u_init`.

### A blob needs no count argument and no `blob` keyword

⛔ That form errors with `packOSC_blob: all values must be floats`. `packOSC` accepts the **`b`
typetag** and takes the remaining floats as bytes, prefixing the length itself:

```
sendtyped /oled/gWaveform ib 4 10 20 30 40
  ->  "/oled/gWaveform\0"  ",ib\0"  0 0 0 4  0 0 0 4  10 20 30 40
                                    screen   bloblen  payload
```

⚠️ **Draw a blob to a spare buffer, not screen 3** — `g_oled` rebuilds screen 3 ten times a second
and wipes anything else within 100 ms.

⚠️ **`oscsend` cannot help here**: its type list is `i h f d s S c m T F N I`, with **no blob**.
Anything testing this outside Pd has to build the packet by hand.

### A patch must never send `/oled/vumeter`

⚠️ mother computes it in `pd audioIO` from `adc~` and the post-volume output and sends it every
analysis window. A patch sending it would simply fight.

**Fix:** leave it alone. `gShowInfoBar` is the only control a patch has over that region.

### `gFilledCircle` is a diamond at small radii

At r=8 it renders as a rounded diamond, not a circle — the rasteriser is crude there.

**Fix:** do not design round meters.

## Design

### The info bar is off, and `g_*` owns all 128×64

`gShowInfoBar` is the **VU meter toggle** — `main.cpp` says so in a one-line comment next to the
declaration. In those 8 rows mother draws four 11-segment meters (in L/R, out L/R) plus battery,
power and wifi, driven from `/oled/vumeter`.

**Cut It turns it off.** The four meters are only 11 segments each and Cut It shows its own input
levels far more legibly at 24 px; battery and wifi are not worth a permanent eighth of the screen on
a device that mostly runs on mains. **The cost is that nothing shows signal presence when the display
is doing something else — accepted.**

### `stopped` is lit rather than dark

*(judgment call)* A stopped patch and a dead patch look identical if `stopped` is `off` — and on a
dark stage that is the difference between a pause and a problem.

### Design against the patch-facing LED numbers, not the bitmask

They are the sensible ordering, they are what `[s led]` takes, and they are stable. The bitmask is
only interesting for composing a colour from components, and that needs the raw path — `oscOut` —
which belongs to `g_oled`.

### `/led/flash` is deliberately unused

`flashLED(OSCMessage&)` is in the `mother` binary and `mother.pd` does not expose it at all. Reaching
it means sending raw OSC to `oscOut`, and **only one abstraction may send on that name** — adopting
flash would put a second writer on it. Recorded so it is not rediscovered as news.

### The LED was deliberately not claimed for mode or for saving

Phase 6 put mode on the Launchpad's top row instead — the surface with six lamps rather than one.
Phase 8 considered a "save in progress" state and did not build it: `Storage → Save` already flips
the OLED to mother's own "Saving…" screen, so the confirmation exists for free.

It remains the cheapest candidate if a *performable* commit is ever added — one row in the state
table and nothing else, since a commit from a Launchpad pad would have no screen of its own.

## Open

- ⬜ **Whether the serial overruns and the OLED lag share a cause is unmeasured.** `dmesg` carries
  continuous `imx-uart 2020000.serial: Rx FIFO overrun` on **the same serial link to the front
  panel**. Recorded rather than asserted. Item 173 — see [plan-v03.md](../../plan-v03.md) §4.
