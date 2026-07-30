# Cut It — Visual Feedback

Every channel through which the instrument can show a human what it is doing: the Organelle's
OLED, the Launchpad's grid, and an iPhone running PdParty. What each can actually do, verified
on hardware, and the traps that cost time getting there.

Companion to [ref-hardware.md](ref-hardware.md) (the rig), [ref-midi.md](ref-midi.md) (the
wire format) and [ref-conventions.md](ref-conventions.md) (how the Pd is written).

**Confidence markers:** ✅ verified on this hardware · 📄 from source or documentation ·
⬜ unknown.

---

## The channels, honestly rated

| Channel | Plain English? | Verdict |
|---|---|---|
| **Organelle OLED** | ✅ yes | The primary performance surface. 128×64 graphics, not five text lines. |
| **Organelle aux LED** | ❌ no | One RGB LED, **seven colours and off**. ✅ The only state display that isn't a screen — see *The aux button LED*. |
| **Launchpad Pro MK3** | ❌ no | 96 RGB LEDs. Spatial state only — see *No text on the Launchpad*. |
| **iPhone / PdParty** | ✅ yes | Unlimited size and colour, over WiFi. Development and diagnostics, **not** performance. |
| **nanoKONTROL** | ❌ none | No host-controllable LEDs on the mk1. Confirmed in Kontrol Editor. ✅ |
| **SP-404MKII** | ❌ none | Has the best screen in the rig and **it is permanently unreachable** — no SysEx in either direction. 📄 Don't spend time here. |
| **Volca FM** | ❌ none | Receive-only, nothing to display. 📄 |

---

## Organelle OLED

**128×64 monochrome framebuffer.** ✅ The `mother` binary exposes a full graphics API that
`mother.pd` never surfaces — patches normally see only five text lines, which badly
undersells it.

### Two ways in

**1. Text lines — the simple path.** `[s screenLine1]` … `[s screenLine5]`. ✅
Five lines, **21 characters**, monospace. ✅ measured with a ruler string; `W` and `i` end at
the same column, so the 8px font is fixed-width and column layouts are safe.

**2. Graphics — the real API.** Send OSC to `[s oscOut]`, which `mother.pd` relays to the
`mother` binary. ✅ verified from inside a running patch, not just over the network.

```
[msg sendtyped /oled/gPrintln iiiiii 3 6 18 24 1 $1]  →  [s oscOut]
```

### Graphics commands

Every command takes **screen number as its first argument**. 📄 from `main.cpp` at tag `v4.0`;
`gPrintln`, `gBox`, `gLine`, `gFilledCircle`, `gClear`, `gShowInfoBar` and `gFlip` are ✅.

| Command | Args after screen |
|---|---|
| `gClear` | `1` |
| `gShowInfoBar` | `0` / `1` |
| `gSetPixel` | `x y colour` |
| `gLine` | `x1 y1 x2 y2 colour` |
| `gBox` | `x y w h colour` |
| `gFillArea` | `x y w h colour` |
| `gCircle` / `gFilledCircle` | `x y r colour` |
| `gInvert` / `gInvertArea` | `1` / `x y w h` |
| `gPrintln` | `x y height colour <text…>` |
| `gCharacter` | `x y char colour size` |
| `gWaveform` | 128-byte **blob** — draws 127 connected lines |
| `gFrame` | 1024-byte **blob** — whole framebuffer, `memcpy`'d |
| `gFlip` | *(none)* — pushes to the display |

**Fonts: 8, 16, 24, 32 px.** The `height` argument of `gPrintln` and the `size` argument of
`gCharacter` select among them. The 21-chars-per-line measurement is the 8px font; larger
sizes give proportionally fewer.

**`gPrintln` concatenates mixed atoms** — symbols, floats and ints — separated by spaces. ✅
Read from the handler: only arguments 0–4 (screen, x, y, height, colour) are required to be
ints; everything after is `strcat`'d. So a label and a value go in one message.

**The typetag must match the argument count exactly.** ✅ `oscOut` reaches the display through
mrpeach `[packOSC]`, which validates and, on a mismatch, **drops the message with an error you
cannot see**: *"Tags count 5 doesn't match argument count 6"*. Verified against the real
`packOSC` on the device:

| Message | Result |
|---|---|
| `sendtyped /oled/gPrintln iiiiii 3 6 6 24 1 42` | ✅ packs |
| `sendtyped /oled/gPrintln iiiiisi 3 4 2 24 1 L 42` | ✅ packs — label plus value |
| `sendtyped /oled/gPrintln iiiiisss 3 4 54 8 1 cut it v0.2` | ✅ packs — three symbols |
| `sendtyped /oled/gPrintln iiiii 3 6 34 24 1 99` | ❌ error, message dropped |

Count the atoms after the address and make the typetag the same length. Every space in a
message box is another atom.

### Four screen buffers

```
AUX = 1     MENU = 2     PATCH = 3     ALERT = 4
```

**The argument is the enum index plus one**, and `AUX` is the default for out-of-range values.
✅ **Draw to screen 3.** Sending screen 1 writes to an undisplayed buffer and looks exactly
like a dead API — this cost a debugging round trip.

✅ **All four buffers are writable, and `setscreen` switches between them in both directions** —
measured with `tools/alert-buffer-probe.pd`. `g_oled` nevertheless draws everything to screen 3
and never switches; see *The ALERT buffer works and is unused anyway* below for why.

**Which buffer is *shown* is switched with `/oled/setscreen <n>`.** ✅ Seen in
`save-patch.sh`, which flips to the AUX screen to display "Saving…" and back to PATCH
afterwards. There are matching `/oled/aux/clear` and `/oled/aux/line/N` commands. So the
alert path is: draw into a spare buffer, `setscreen` to it, `setscreen 3` to return — the
performance display underneath is never disturbed.

### Five traps, every one silent

There is **no Pd console on this device**, so each of these fails with no output at all.

1. **Screen numbering is enum+1**, and the default is the invisible `AUX` buffer. ✅
2. **Type strictness.** Every handler checks `msg.isInt()` and discards the message otherwise.
   Pd sends floats by default, so **`sendtyped /oled/gX iiiii …` with explicit int typetags is
   mandatory**. 📄 Plain `send` with floats fails silently.
3. **`gFlip` or nothing.** Draw commands set `newScreen = 0`; only `gFlip` pushes to the
   display. ✅
4. **`mother` repaints after patch load** and restores the info bar. A `gShowInfoBar` sent once
   on `loadbang` gets undone. ✅ Send it on **every redraw**, not at init.
5. **The info bar is the top 8 pixel rows of the 64.** ✅ Read from `OledScreen::drawInfoBar` —
   it clears and owns `pix_buf[0…127]`, one byte per column, so exactly 8 rows. Anything drawn
   there is obscured until it is turned off.

### The info bar, and why it is off

**`gShowInfoBar` is the VU meter toggle** — `main.cpp` says so in a one-line comment next to
the declaration. In those 8 rows mother draws **four 11-segment meters** (in L/R, out L/R) plus
battery/power and wifi, and it drives them itself from `/oled/vumeter`. ✅

**A patch must never send `/oled/vumeter`.** mother computes it in `pd audioIO` from `adc~` and
the post-volume output and sends it every analysis window. A patch sending it would simply
fight.

**Project decision: the info bar is off.** `g_*` owns all 128×64. The four meters are only 11
segments each and Cut It shows its own input levels far more legibly at 24px; battery and wifi
are not worth a permanent eighth of the screen on a device that mostly runs on mains. The cost
is that nothing shows signal presence when the display is doing something else — accepted.

`gShowInfoBar 3 0` therefore goes out on **every** redraw from the display abstraction, per
trap 4 above. It is not an init-time concern and does not belong in `u_init`.

### Cosmetic notes

- `gFilledCircle` at r=8 renders as a rounded diamond, not a circle. ✅ The rasteriser is crude
  at small radii — don't design round meters.
- `gWaveform` and `gFrame` need OSC **blobs**, and whether Pd can produce one through `oscOut`
  is ⬜ **untested**. If it can, drawing the captured buffer becomes possible and choosing a
  playhead position in fresh audio stops being blind. Test before designing around it.

---

## The aux button LED — the only state display that isn't a screen

The leftmost button on the front panel, and the one piece of visible state the OLED does not own.
✅ **Read off the device** — `mother.pd`'s `pd LED` subpatch and the `mother` binary's symbol
table — then swept by eye on the hardware.

**`[s led]` takes one number, 0–7.** `mother.pd` applies `[% 8]`, so any float is legal and 8 wraps
back to off. It reaches `SerialMCU::setLED(unsigned)`, i.e. the same front-panel microcontroller and
the same serial link as the OLED.

| `led` | Colour |
|---|---|
| 0 | off |
| 1 | red |
| 2 | yellow |
| 3 | green |
| 4 | light blue (cyan) |
| 5 | dark blue |
| 6 | pink (magenta) |
| 7 | white |

**Seven colours and off — this is a full RGB LED, not an indicator lamp.** ✅ Verified by sweeping all
eight and reading the button.

**`mother.pd` permutes the value on the way out**, and knowing why makes the table above make sense.
It maps patch-facing `0…7` to hardware `0,4,5,1,3,2,6,7`, and the *hardware* value is a **3-bit RGB
bitmask**: bit 0 = green, bit 1 = blue, bit 2 = red. So raw 1/2/4 are the primaries and 3/5/6/7 are
their mixes. mother is reordering that bitmask into spectrum order so patch authors get
`red → yellow → green → cyan → blue → magenta → white` instead of a bit pattern.

**Design against the patch-facing numbers.** They are the sensible ordering, they are what `[s led]`
takes, and they are stable. The bitmask is only interesting if you ever want to compose a colour from
components — and that needs the raw path, which is `oscOut`, which belongs to `g_oled`.

**mother already sets `led 0` on `quitting`**, so a safe exit needs no LED handling of its own. ✅

⚠️ **There is an undocumented `/led/flash`** — `flashLED(OSCMessage&)` is in the `mother` binary, and
`mother.pd` does not expose it at all. Reaching it means sending raw OSC to `oscOut`. **Deliberately
unused:** only one abstraction may send on `oscOut`, so adopting flash would put a second writer on
that name — the same trade the ALERT buffer lost below. Recorded so it isn't rediscovered as news.

---

## No text on the Launchpad

The Launchpad Pro MK3 has **no text-scrolling SysEx**. The word "scroll" does not appear
anywhere in Novation's programmer reference, and the SysEx command summary lists only six
commands. 📄 The Launchpad Mini MK3 and Launchpad X have text scrolling; the Pro MK3 does not.

Rendering text would mean hand-rolling a font and shifting columns across the grid — slow to
read, and it would consume the entire surface. **Not a text channel.** Treat the Launchpad as
96 RGB pixels of spatial state: which slots are filled, which pattern is queued, where the
playhead is, which filter is selected.

Its LED details are in [ref-midi.md](ref-midi.md).

---

## iPhone / PdParty

An iPhone running PdParty on the same network is an unlimited plain-English display, and —
more valuable — **it solves the missing Pd console**.

**Verified working, both directions.** ✅ Organelle → phone and phone → Organelle, over OSC.

### Why not USB

**iOS will not present itself as a USB MIDI device or network interface to a Linux host.**
Apple's USB MIDI support is host-side only. Personal Hotspot over USB requires cellular, which
defeats airplane mode. `usbmuxd`/`iproxy` could tunnel TCP over Lightning but would mean
installing libimobiledevice on a 2015-vintage Arch ARM with a read-only rootfs. 📄

**Airplane mode is not the obstacle it appears to be.** Enabling airplane mode and then
re-enabling WiFi is standard iOS behaviour — cellular stays off, WiFi works, and the setting
persists. So WiFi is available in performance conditions.

**And the Organelle can host the network itself.** `hostapd` and `dnsmasq` are already
installed, `wlan0` exists, and `iw list` reports **AP** among supported interface modes. ✅
present — ⬜ never actually configured or tested. That would make the link self-contained: no
venue WiFi, no cellular, no internet.

### Addresses and ports

| Device | Address | Notes |
|---|---|---|
| Organelle | `192.168.1.15` | listens on **9001** |
| iPhone | `192.168.1.5` | OSC receive **8000**, WebDAV **9000** |
| Mac | `192.168.1.16` | dev machine |

**Do not use 9000 for OSC** — it is PdParty's WebDAV server (`GCDWebDAVServer`). ✅
**Do not use 4001–4003** — those belong to `mother`. ✅

### The four PdParty rules that cost the most time

1. **`[s #osc-out]` takes raw OSC bytes from `[oscformat]`.** ✅
   ```
   [r $0-fader-out]  →  [oscformat cutit fader]  →  [s #osc-out]
   ```
   A message with the address as selector — `[list prepend /cutit/fader] → [list trim]` — sends
   **nothing at all**, silently. PdParty's own `tests/pdparty/Osc` scene is the reference; the
   message boxes in it that resemble the wrong approach are labelled "test that sending other
   message types doesn't crash pdparty".

2. **`[r #osc-in]` delivers the address as bare symbols, no slashes.** ✅ `/cutit/hb 210`
   arrives as `cutit hb 210`, so routing is `[route cutit]` → `[route hb]`, never
   `[route /cutit/hb]`.

3. **PdParty only renders iemguis that have send/receive names.** ✅ With `empty` or `-` they
   parse, instantiate, participate in the patch — and are **invisible**. This is documented
   nowhere; it was found by diffing against PdParty's bundled `tests/all_pd_guis.pd`, where
   every GUI object has both names, `$0-` prefixed. Symptom is a scene showing only comments.

4. **`[print]` is transmitted as `/pdparty/print` OSC.** ✅ Accidentally a free remote console —
   and accidentally a flood. A single `[print]` on a 2 Hz message stream produced 138 packets
   in the time it took to drag a fader once. Don't leave prints in a running scene.

### Scene structure and layout

A PdParty scene is a **folder containing `_main.pd`**. 📄 A bare `.pd` file also works as a
"patch scene" but without background image support.

**Orientation is inferred from the canvas aspect ratio** — a canvas wider than it is tall gives
landscape, and PdParty locks the device to match. 📄 There is no `info.json` key for it; the
only keys are *author*, *description*, *name* and *category*.

**Match the canvas to the target device's point dimensions.** The iPhone 11 is **896×414
points** in landscape. A canvas of **448×207** — exactly half — fills the screen edge to edge
with no letterboxing, and everything renders at **2×**, so a 56pt font in the patch appears at
about 112pt on screen. ✅ Verified filling the screen on the actual device.

**Non-GUI objects still occupy canvas space and render as nothing.** A column of `[r]`,
`[route]` and `[unpack]` objects down the left of the canvas produces a large empty region on
the phone and pushes the visible content downward. ✅ **Keep the main canvas GUI-only and put
all plumbing in a `[pd guts]` subpatch** — which is exactly what PdParty's own bundled scenes
do. Long comments do the same thing horizontally and get clipped.

**iOS 14+ requires Settings → Privacy → Local Network permission**, and the entry only appears
after the app first attempts an outbound local connection. 📄 Until granted, OSC fails
silently.

### What it is and isn't for

**Status display, diagnostics and remote console — not performance control.** UDP over WiFi
arrives unevenly, visibly so in the heartbeat counter. Fine for a readout, unacceptable for
note timing.

---

## The performance status protocol

Working, verified end to end on hardware. ✅ Reference implementation:
`tools/status-display/` (Organelle) and `tools/pdparty-scene/CutItRemote/` (phone).

### Three rules, and they are not optional

**1. Send state, never events.** Every message carries the complete current value —
`chop-size is 43`, never `chop-size +1`. A dropped packet then self-corrects on the next send
instead of leaving the display permanently and silently wrong. UDP will drop packets; the
protocol has to not care.

**2. The display must show its own staleness.** A frozen display looks exactly like a working
one, and mid-performance you will read it and act on it. The phone restarts a 1500 ms timer on
every incoming message; if it ever fires, the display says **`NO-LINK`** instead of continuing
to present a stale value as current. ✅ Verified: loading the Organelle patch flips it to `ok`,
quitting flips it back to `NO-LINK`.

**The default label is `NO-LINK`, not `ok`.** It must assume the worst until traffic proves
otherwise, or a scene opened before the Organelle is running looks connected when it isn't.

**3. The Organelle never waits for the phone.** Fire and forget over `[netsend -u]`. Phone
off, phone crashed, WiFi gone — the instrument plays identically.

### Wire format

```
/cutit/param  <name> <value>     the parameter that just changed
/cutit/hb     <counter>          heartbeat, every 500 ms
```

**One address for all parameters.** Adding a parameter costs one `[list prepend <name>]` on the
Organelle and nothing at all on the phone. This scales to the nanoKONTROL's 18 continuous
controls without redesign.

**The name is the parameter, not the control.** Knob 2 sends `grain`, not `knob2`. The display
says what changed rather than which physical control moved — so the same knob can mean
different things in different modes without the display lying.

**The heartbeat must keep flowing even when nothing is happening**, because it is the only
thing distinguishing "idle" from "dead".

⬜ **The link is not yet stage-worthy**, on four counts — no rate limiting on the wire, no
Organelle-hosted access point, phone hardening unfinished, and the value drawn as an `nbx` with
box chrome. All four are tracked in [plan-v02.md](plan-v02.md) under *Open questions*.

---

## The display framework — built ✅

`g_oled`, Phase 3. Most knob turns, fader moves and button presses want the screen for the
duration they are moving, so many sources contend for one surface. **It is an arbiter, not a
print function.**

### Four layers, one winner per frame

| Layer | Pri | Raised by | Cleared by | Draws |
|---|---|---|---|---|
| `home` | 0 | always active | never | two meters, 8px readouts, gate marks, footer |
| `param` | 1 | any unreserved `disp` selector | `[del 1200]` | **up to five rows that hold their positions** — see *Several at once* |
| `modal` | 2 | `disp` → `modal <word>` | `modal-off`, or a 30 s safety TTL | word 16px + shrunk meters |
| `alert` | 3 | `disp` → `alert …`, from `u_err` only | 2 s `warn`, 4 s `fail` | border, level 16px, source and text 8px |

Priority is a `[select 1]` cascade rather than arithmetic, so it reads top to bottom in exactly
priority order. TTL is one retriggered `[delay]` per layer, so a moving control keeps `param`
alive and the screen clears 1.2 s after your hands stop rather than after they start.

### Geometry, as built

```
home                              param                    alert
+------------------------+  +------------------------+  +------------------------+
| L 43            y=0  8 |  | chop-size       y=0  8 |  |+----------------------+|
| ==========      y=10 12|  |                        |  || fail        y=6   16 ||
|      |==|       y=23  3|  |  43 %           y=12 24|  ||                      ||
| R 19            y=27 8 |  |                        |  || u_init      y=30   8 ||
| ===             y=37 12|  |                        |  || launchpad-x y=44   8 ||
|      |==|       y=50  3|  | =========       y=48  5|  |+----------------------+|
| v0.2-ready      y=54  8|  | ====            y=56  5|  +------------------------+
+------------------------+  +------------------------+
```

`env~`'s 0–100 maps to pixels as `× 1.28`, clipped to 1–128 — a zero-width `gFillArea` is
untested and silence is the common case. The gate marks are **one `gBox` per meter** spanning
the measured noise floor (18–19 → x 23) to the top of the gate window (25–30 → x 38): one
message instead of two ticks, and it reads as a zone.

### Several at once — the param layer is a list ✅ built

With 18 continuous controls, moving two faders together is ordinary use, so the param layer holds
**up to five entries** in `[text define $0-params]`: one line of
`<frame-stamp> <name> <value> <unit>`.

**Rows are stable.** A control already on screen is updated **in place** — only its value changes —
and a new one is appended below. A **sixth is refused** until a row frees up. ⚠️ An earlier version
pushed the most-recently-moved to the front, which is what the Phase 4 plan asked for and was
**wrong in the hand** ([ref-build-log.md](ref-build-log.md)): two faders moving together swapped
places several times a second and were unreadable.
The cost of stability is honest — move nine faders and you see the five you touched first, not the
five most recent — and it is the right trade, because a display you cannot read is worth nothing.

**Ageing costs nothing, because the frame clock already runs.** Each entry records the frame it
last moved in, and every frame anything **13 frames** behind is dropped. Because rows hold their
positions, expired entries can be anywhere in the list, so this **scans** — walking from the last
index toward 0, because deleting a line shifts everything below it and going downward is what makes
that harmless. `until`'s own count bounds the loop, so an empty store runs it zero times and
`text get` is never handed a line that does not exist. 13 and not 12 is deliberate:
`pd layers` still clears `$0-a-param` on a 1200 ms delay, so the store is guaranteed to outlive the
flag by a frame — otherwise a rounding difference could leave the param layer winning with nothing
to draw, which looks exactly like a dead patch.

**Type size follows how many are moving.** The settled "24px is readable at arm's length" is kept
for the common case and degrades rather than being abandoned. The param area is y=0…46; the meter
strips at y=48/56 are untouched throughout.

| Moving | Layout | Measured |
|---|---|---|
| 1 | name 8px @ y=0, value+unit **24px** @ y=12 | ✅ byte-identical to what Phase 3 shipped |
| 2 | name 8px @ y=0 / value **16px** @ y=8, then name 8px @ y=23 / value 16px @ y=31 | ✅ |
| 3–5 | **8px** rows at y=0, 9, 18, 27, 36, in the order first touched | ✅ |

**Two movers are NOT two 16px lines**, which is what the plan first called for. 16px fits about ten
characters across 128 px, so `slider-1 43` would clip to `slider-1 4` — a silent failure that looks
like a working display — and real v0.3 names like `chop-size` are no shorter. A small name over a
mid-size value clips nothing and generalises.

**A side effect worth knowing: the stale-unit trap is now structurally impossible** in the param
path. Each line is stored whole, so `chop-size 43 %` followed by `grain 12` cannot inherit the `%` —
there is no longer an optional field being written separately.

⚠️ **`text get` errors, and prints, if you ask for more fields than a line holds.** Measured:
`text get x 1 3` on a two-field line gives `field request (1 3) out of range`. So the draw path
never requests fields — it takes the whole line and strips the stamp with `[list split 1]`, which is
safe because every stored line has at least three atoms.

**Deviation from the original sketch:** a moving knob shrinks the meters into a **full-width
5 px bottom strip**, not a corner. A corner meter at 128×64 is ~40 px wide and 4 px tall, and
24px text is ~18 px per character so the value needs the full width anyway. Intent is kept —
the meters never vanish.

### Seeing it off-device

`u_mother-stub` is the Organelle's front panel: **AUX → knobs 1–4 → OLED → selector encoder →
volume**, keys underneath, in that order because that is the order on the real face
([manual](https://docs.critterandguitari.com/Organelle/og1/)). It renders **inline on
`main-dev.pd`** through graph-on-parent, so opening the entry point shows the instrument rather
than a door to it.

The eight screen rows are `cnv` objects whose **label** is the drawn text. That forces one thing
worth knowing: a label is a *single symbol*, so `pd oled-decode` joins each row's words into one
atom (`[list fromsymbol]` → append 32 → `[list tosymbol]`, looped) before it can be shown. Bars
render as 21 fixed-width characters, `=` then `-`, so the two channels can be compared at a
glance.

**The screen log** — `open-screen-log` on the panel — records every `disp` message except
`in-l`/`in-r`, stamped with the frame number:

```
 0  modal booting      31  modal-off
11  modal wiring       31  status v0.2-ready
26  modal launchpad    46  chop-size 43 %
```

Gaps read directly as tenths of a second (11, 15, 5 = u_init's 1500/1500/500 ms). This exists
because the boot sequence finishes before you can get to the window.

### What made it work

- **Rate limiting needed no code.** Layers hold state, not draw calls, so the last value written
  is what the next frame draws. ✅ 877 `disp` messages in five seconds → exactly 51 frames, the
  value advancing 20 per frame. The guaranteed trailing edge is free.
- **One text renderer builds its own typetag.** Every line on the screen goes through
  `pd text-out`, which counts the words and picks `iiiiis` … `iiiiissss` to match. Hand-typed
  typetags are the single most repeated silent failure in this API; this makes an arity mistake
  impossible rather than merely unlikely. Values are stringified with `[makefilename %g]`
  because packOSC will not accept a float under an `s` tag.
- **Single owner, enforced.** Only `g_oled` sends on `oscOut`. `u_err` forwards onto `disp`.

**Two controls at once no longer alternate.** That limitation is gone — see *Several at once*
above.

**The same arbiter shape applies to `g_grid`** on the Launchpad — playhead, slot state, mode
and meters all contend for the same 64 pads. Build the pattern once, instantiate it twice.

### The ALERT buffer works ✅ and is unused anyway

**Measured, not inferred.** `tools/alert-buffer-probe.pd` drew a box and two lines of text into
buffer 4 while `g_oled` carried on redrawing screen 3 underneath, `setscreen 4` displayed it,
and `setscreen 3` brought the live meters back six seconds later. Drawing into an off-screen
buffer, `gFlip`-ing it and switching in both directions all work.

**`g_oled` still draws everything to screen 3 and never switches**, for two reasons that a
passing probe does not change:

- **There is nothing to optimise.** The original benefit — "the performance display underneath
  is never disturbed" — does not exist here, because `g_oled` clears and rebuilds screen 3 from
  stored state ten times a second, so nothing needs preserving and restore is automatic on the
  next frame. The saving would be an alert dropping from ~70 messages/second to about five, for
  a 2–4 second event, against a home screen that sustains that same rate continuously.
- **Writable is not the same as safe.** Buffer switching is **edge-triggered**, where every
  layer in the arbiter is state-driven. A lost `setscreen 3` strands the display on a stale
  alert on a device with no console; a dropped frame today self-corrects in 100 ms. Trading a
  self-healing design for a saving that doesn't matter is the wrong trade.

Worth knowing the capability exists — `setscreen` is how `save-patch.sh` shows "Saving…" — but
using it would make the alert the one layer that behaves differently from the other three.

---

## Reference patches

Every claim above has a working reference in [tools/](tools/) — `oled-probe/` for the graphics
API and font measurement, `osc-bridge/` and `status-display/` for the phone protocol,
`pdparty-scene/CutItRemote/` for the phone side. What each proves and how to run it is in
[tools/README.md](tools/README.md).
