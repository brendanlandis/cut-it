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
| **Launchpad Pro MK3** | ❌ no | **96 button LEDs + the logo** = 97 addressable, painted across an index span of **1–108**. Spatial state only — see *No text on the Launchpad*. |
| **iPhone / PdParty** | ✅ yes | Unlimited size and colour, over WiFi. Development and diagnostics, **not** performance. |
| **nanoKONTROL** | ❌ none | No host-controllable LEDs on the mk1. Confirmed in Kontrol Editor. ✅ |
| **SP-404MKII** | ❌ none | Has the best screen in the rig and **it is permanently unreachable** — no SysEx in either direction. 📄 Don't spend time here. |
| **Volca FM** | ❌ none | Receive-only, nothing to display. 📄 |

---

## Organelle OLED and the aux button LED

**Moved** to **[ref/organelle.md](ref/organelle.md)** — the graphics command table, the four screen
buffers, the fonts, every silent trap, the ~200 ms lag and the LED colour table.

⚠️ **The display *arbiter* stayed here** — `home < modal < alert`, the `disp` bus and the layer
model are shared by `g_oled` and `g_grid`, so they are instrument architecture rather than facts
about either device. They move to `ref/architecture.md` when that page is written.

---

## No text on the Launchpad

**Moved** to [ref/launchpad.md](ref/launchpad.md). Short version: the Pro MK3 has no text-scrolling
SysEx, so it is 96 RGB pixels of spatial state and not a text channel. `g_grid`'s arbiter is below.

---

## iPhone / PdParty, and the performance status protocol

**Moved** to **[ref/phone.md](ref/phone.md)** — addresses and ports, the wire format, the
Organelle-hosted access point, the PdParty scene rules, the notch, and the three protocol rules
(send state never events; the display must show its own staleness; the Organelle never waits).

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

### `g_grid` — the same shape, across the 1–108 index span ✅ built

Phase 6. Three layers instead of four, and the cascade is `g_oled`'s `pd pick` one link shorter:

| Layer | Pri | Raised by | Cleared by | Draws |
|---|---|---|---|---|
| `home` | 0 | always active | never | **regions** — six mode lamps on CC 91–96, the beat row on grid indices 11–18 |
| `modal` | 1 | `disp` → `grid modal <palette>` | `grid modal-off`, or a 30 s safety TTL | the whole surface, one colour |
| `alert` | 2 | `disp` → `alert …`, **`fail` only** | 2 s | the whole surface, red |

**One deliberate deviation, and it is the interesting one: `home` is a composite.** Whole-surface
arbitration is right for a 128×64 screen and wrong for a grid, where the natural idiom is
*regions* — so the mode lamps and the beat row coexist inside the layer that never expires, while
`modal` and `alert` still take everything. The cascade is untouched; the composition happens
below it.

**A `warn` never reaches the grid.** Only `fail` is worth the whole surface. The grid is visible
from much further away than the OLED, which is what makes a failure turning it red the most
valuable thing these pads can say in a venue — and `u_err` needed no change, because two
consumers of one `disp` selector is fine. The rule is one owner per *surface*.

**`m_launchpad` owns the Programmer/Live switch; `g_grid` owns the LEDs.** Different surfaces,
one writer each. That is what let the old 89-note clear loop be deleted outright: **the first
frame after ownership rises IS the clear.**

⚠️ **And one place it must NOT copy `g_oled`: the repaint is conditional.** The OLED redraws
unconditionally at 10 Hz because its frames are cheap local UDP. These are ALSA MIDI writes, and
~96 of those a second is the standing suspect for the clock doubling Pd's CPU in Phase 5. The
frame clock runs at **50 Hz**, but it paints only when a dirty flag is set — **nothing at all
when idle, about two frames a second at 120 BPM.** Every repaint is one SysEx of **108 colour
specs covering indices 1–108**, 332 bytes. ✅ **The frame clock costs nothing**: it checks the
flag rather than painting, so the frame count is bounded by the beat rate and never by the
metro — 10 Hz and 50 Hz measured identical on the device (item 94). It was raised from 10 Hz
because at 240 BPM a 250 ms beat does not divide into 100 ms, so the row swung ±50 ms. See
[ref-midi.md](ref-midi.md).

**THE GRID CAN GO DARK ON ITS OWN, AND THAT IS THE WATCHDOG RATHER THAN A FAULT.** `m_launchpad`
polls the Launchpad with a universal device inquiry every two seconds. Three missed replies —
**about six seconds** — mean the device is gone, ownership drops and `g_grid` stops painting
entirely. Unplug the Launchpad on the Organelle and this is what you see. Recovery is automatic: it
re-runs `wire.sh`, first about 14 s after the cable goes and then every 8 s, so a replug brings the
grid back **within roughly eight seconds, in the correct state** — mode lamp, beat row and all,
because the arbiter repaints from live state rather than restoring a frame.

⚠️ **It gives up at about 70 seconds** and writes `fail m_launchpad grid-lost` to `err`. After that
a replug will *not* recover the grid and the patch must be reloaded — the bound is deliberate, so a
device nobody intends to plug back in cannot make Pd fork all night.

**A dark grid is therefore three different things**, and the OLED is what tells them apart: nothing
is wrong and nothing has changed (the dirty flag simply has no work); the surface was handed back by
a panic; or the device is gone and the watchdog has said so.

⚠️ **A panic blanks the Launchpad until the patch is reloaded, and that is deliberate.** Ownership
drops and nothing repaints. ✅ **Currently harmless — nothing on the Organelle sends `panic`**, so
it is unreachable in normal use. **The escape hatch is worth more than the display**; revisit only
if a panic ever becomes performer-reachable.

**Every raise and every expiry sets the dirty flag.** A layer falling away changes the frame just
as much as one arriving — and the first build got this wrong, which would have left an expired
alert red permanently ([ref-build-log.md](ref-build-log.md)).

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
