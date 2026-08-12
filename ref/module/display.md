<!-- schema: module -->
# The display arbiter

**Files:** `Cut It/g_oled.pd`, `Cut It/g_grid.pd`, `Cut It/g_led.pd`, `Cut It/u_net.pd` · **Gate:** `test/gate/display-assert.sh`, `test/gate/oled-assert.sh`, `test/gate/led-assert.sh` · **Bench:** `test/bench/display-bench.pd`, `test/bench/nanokontrol-bench.pd`, `test/bench/launchpad-bench.pd`

## What it is

**One bus, four surfaces, and an arbiter rather than a print function.** Most knob turns, fader
moves and button presses want a display for as long as they are moving, so many sources contend for
one screen. Nothing in Cut It draws: everything sends **semantics** to `disp` and does not know or
care how — or whether — it is rendered.

⛔ **One owner per display surface (C-5).** `g_oled` owns `oscOut` and `screenLine1`–`5`; `g_grid`
owns the Launchpad's LEDs; `g_led` owns the aux button. **`u_err` filters and forwards onto `disp`
rather than drawing** — the Phase 4 plan had it writing to the ALERT buffer itself, and where the
two disagreed this rule won.

Two of the surfaces run the **same arbiter shape** — `home < modal < alert`, each layer with a
priority and a time to live, one winner per frame. `g_oled` runs five of them and `g_grid` three,
and `g_grid` deviates in exactly one interesting way: its `home` is a **composite**.

**The fourth surface, the phone, is a mirror rather than a surface with a vocabulary**, and that is
why it cost nothing to add.

## Facts

### The four surfaces, honestly rated

| Surface | Plain English? | Owner | Verdict | Evidence | Item |
|---------|----------------|-------|---------|----------|------|
| Organelle OLED | yes | `g_oled` | The primary performance surface. 128×64 graphics, not five text lines | verified | — |
| Organelle aux LED | no | `g_led` | One RGB LED, **seven colours and off**. The only state display that is not a screen | verified | — |
| Launchpad Pro MK3 | no | `g_grid` | **96 button LEDs + the logo** = 97 addressable, painted across an index span of **1–108**. Spatial state only | verified | — |
| iPhone / PdParty | yes | `u_net` | Unlimited size and colour, over WiFi. Development and diagnostics, **not** performance | verified | — |

Three devices in the rig can display nothing at all: the nanoKONTROL mk1 has no host-controllable
LEDs, the Volca is receive-only, and the SP-404 has **the best screen in the rig and it is
permanently unreachable** — no SysEx in either direction.

### The `disp` message

**`<name> <value> [unit]`, with the name as the SELECTOR.** `g_oled` routes nine selectors;
**everything else is a parameter by definition** — there is no registration step, so a new control
needs no change to any display.

| Selector | Carries | Layer | Evidence | Item |
|----------|---------|-------|----------|------|
| `in-l` `in-r` | `<dB>` from `u_level` | home | verified | — |
| `status` | One symbol, the footer status | home | verified | — |
| `modal` | One symbol — **sticky** until cleared | modal | verified | — |
| `modal-off` | Nothing | clears modal | verified | — |
| `diag` | Nothing — it is a summons, not a value | diag | verified | 301 |
| `alert` | `<level> <source> <text>` — **only `u_err` sends this** | alert | verified | — |
| `led` | One symbol, a **state** — `off` `stopped` `running` `panic` | *not the OLED at all* | verified | — |
| `grid` | The Launchpad's own vocabulary — `grid modal <palette>`, `grid modal-off` | *not the OLED at all* | verified | — |
| *anything else* | `<value> [unit]` | param | verified | — |

⚠️ **`modal` and `alert` text is ONE symbol**, and error text is ≤ 21 characters. `gPrintln` does
not wrap, 16px fits about ten characters across 128 px, and a message box has a fixed typetag.
Write `launchpad-silent`, not `launchpad silent`.

### `g_oled` — five layers, one winner per frame

| Layer | Pri | Raised by | Cleared by | Draws | Evidence | Item |
|-------|-----|-----------|------------|-------|----------|------|
| `home` | 0 | Always active | Never | Two meters, 8px readouts, gate marks, footer | verified | — |
| `param` | 1 | Any unreserved `disp` selector | `[del 1200]` | **Up to five rows that hold their positions** | verified | — |
| `modal` | 2 | `disp` → `modal <word>` | `modal-off`, or a 30 s safety TTL | Word 16px + shrunk meters | verified | — |
| `diag` | 3 | `disp` → `diag` | `[del 8000]` | **One 8px row per device, and the shrunk meters** | verified | 301 |
| `alert` | 4 | `disp` → `alert …`, from `u_err` only | 2 s `warn`, 4 s `fail` | Border, level 16px, source and text 8px | verified | — |

**Priority is a `[select 1]` cascade rather than arithmetic**, so it reads top to bottom in exactly
priority order. **TTL is one retriggered `[delay]` per layer**, so a moving control keeps `param`
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
| v0.3-ready      y=54  8|  | ====            y=56  5|  +------------------------+
+------------------------+  +------------------------+
```

| | Evidence | Item |
|---|----------|------|
| `env~`'s 0–100 maps to pixels as **× 1.28**, clipped to **1–128** — a zero-width `gFillArea` is untested and silence is the common case | verified | — |
| The gate marks are **one `gBox` per meter**, spanning the noise floor to the top of the gate window — x 23 to x 38. One message instead of two ticks, and it reads as a zone. The levels those pixels come from are item 11, on [audio.md](audio.md) | verified | 11 |
| A moving knob shrinks the meters into a **full-width 5 px bottom strip**, not a corner. A corner meter here is ~40×4 px, and 24px text needs the full width anyway | verified | — |

### The param layer is a list, and rows are STABLE

With 18 continuous controls, moving two faders together is ordinary use. The param layer holds **up
to five entries** in `[text define $0-params]`, one line of `<frame-stamp> <name> <value> <unit>`.

| | Evidence | Item |
|---|----------|------|
| A control already on screen is updated **in place** — only its value changes. A new one is appended **below**. A **sixth is refused** until a row frees up | verified | — |
| Ageing: each entry records the frame it last moved in, and anything **13 frames** behind is dropped every frame | verified | — |
| The scan walks from the **last index toward 0**, because deleting a line shifts everything below it and going downward makes that harmless. `until`'s own count bounds the loop | verified | — |
| **13 and not 12 is deliberate** — `pd layers` clears `$0-a-param` on a 1200 ms delay, so the store is guaranteed to outlive the flag by a frame. Otherwise a rounding difference leaves the param layer winning with nothing to draw, which looks exactly like a dead patch | verified | — |

**Type size follows how many are moving.** The param area is y=0…46; the meter strips at y=48/56 are
untouched throughout.

| Moving | Layout | Evidence | Item |
|--------|--------|----------|------|
| 1 | Name 8px @ y=0, value+unit **24px** @ y=12 | verified — byte-identical to what Phase 3 shipped | — |
| 2 | Name 8px @ y=0 / value **16px** @ y=8, then name 8px @ y=23 / value 16px @ y=31 | verified | — |
| 3–5 | **8px** rows at y=0, 9, 18, 27, 36, in the order first touched | verified | — |

✅ **All three are legible at playing distance — item 258, item 39 closed.** Read off the panel by
eye at arm's length rather than judged from the geometry, one nano slider then two then four to
raise each layout in turn. **Even the 8px five-row case passes.**

⛔ **So the two-mover layout's weakness is CLIPPING, not size.** 16px fits about ten characters
across 128 px and silently truncates — `slider-1 43` becomes `slider-1 4`. That is the one to design
against, and it would not be helped by a larger font.

### The diag layer — what the rig is doing, on the instrument

**When a controller stops working mid-set, this is what says which one.** The presence layer has
always known; all it surfaced was a two-second `warn`. `diag` is the question *"what is the rig's
state right now"* asked deliberately, and it reuses the 3–5-mover geometry exactly: **8px rows at
y = 0, 9, 18, 27, 36**, one per source, plus the shrunk meter strip.

| | Evidence | Item |
|---|----------|------|
| One row per source on the presence bus, drawn as `<src> <state>`. The roster is whatever `expect` published at load — today **five** | verified | 301 |
| ⛔ **`<src>` is the ABSTRACTION's name** — `m_nano`, never "nanoKONTROL". `g_oled` sits below the `m_` boundary, so this is the only name it has. See [presence.md](presence.md) | verified | 301 |
| Four states: `here` · `gone` · `never` · `unchecked`. **`m_volca` registers `none` and reads `unchecked`** — it is never polled and can never be lost, so drawing it as healthy would be a claim nothing has tested | verified | 301 |
| ⛔ **The loop is bounded at FIVE rows, not at the roster size.** A sixth would draw at y=45 and run into the meter strip at y=48 | verified | 301 |
| ⚠️ **`m_launchpad unchecked` is 21 characters** — the whole width of an 8px row. A longer state word or a longer abstraction name clips silently | verified | 301 |
| Summoned by `disp` → `diag`, which carries nothing. Cleared by a retriggered `[del 8000]`, so pressing again while it is up buys another eight seconds | verified | 301 |
| The control is **`lp-cc-80` in all six modes** — the Launchpad's left column, top button, directly below the CC 90 corner that `recover` uses. One row of `cut-it-map.txt` per mode | verified | 304 |
| The state lives in a `[text define $0-diag]` as `<src> <code>` — **numbers, not words**, so every transition is a comparison and the words are chosen once, where they are drawn | verified | 301 |

⚠️ **Presence is *last heard*, not *alive*, and the labels are chosen to say so.** A nanoKONTROL
nobody has touched reads `here` and one on the floor reads `here` until the poll misses three times.
No amount of code changes that — the operator supplies it.

⛔ **The summoning control is on the device most likely to be the answer, and that is a known
cost.** A Launchpad that has come unplugged cannot summon the screen that would say so — the button
is dead in exactly the case the roster is most wanted. **Only the Organelle itself can never be the
missing device**, and its 25 keys and four knobs are already spoken for. ⚠️ **The failure is at least
unambiguous rather than silent**: a Launchpad that is gone is also dark, and `warn m_launchpad
device-lost` has already been on the screen for two seconds. See
[launchpad.md](../device/launchpad.md).

### `g_grid` — the same shape, one link shorter

| Layer | Pri | Raised by | Cleared by | Draws | Evidence | Item |
|-------|-----|-----------|------------|-------|----------|------|
| `home` | 0 | Always active | Never | **Regions** — six mode lamps on CC 91–96, the beat row on grid indices 11–18 | verified | — |
| `modal` | 1 | `disp` → `grid modal <palette>` | `grid modal-off`, or a 30 s safety TTL | The whole surface, one colour | verified | — |
| `alert` | 2 | `disp` → `alert …`, **`fail` only** | 2 s | The whole surface, red | verified | — |

**`panic` raises `modal` with palette 5, red, and clears it with an explicit `grid modal-off` one
second later** — `u_init`'s `panic-display` subpatch, item 296. ⛔ **The `[del]` owns the duration
and the 30 s TTL is never leaned on.** Half a minute of dead grid during the one moment the
instrument is most needed is item 251's failure in a different costume. ⚠️ **It changes no
ownership** — `g_grid` owns the LEDs and `disp` is how a caller asks (C-5); `m_launchpad` is not
addressed at all, so panic still never hands the surface back.

| | Evidence | Item |
|---|----------|------|
| The frame clock runs at **50 Hz** but paints only when a **dirty flag** is set — nothing at all when idle, about two frames a second at 120 BPM | verified | 94 |
| Every repaint is one SysEx of **108 colour specs covering indices 1–108**, 332 bytes | verified | — |
| The frame clock **costs nothing**: it checks the flag rather than painting. 10 Hz and 50 Hz measured identical on the device | verified | 94 |
| Raised from 10 Hz because at 240 BPM a 250 ms beat does not divide into 100 ms, so the beat row swung **±50 ms** | verified | — |
| **Every raise AND every expiry sets the dirty flag** — a layer falling away changes the frame as much as one arriving | verified | — |

### Seeing it off-device

`u_mother-stub`'s eight screen rows are `cnv` objects whose **label** is the drawn text.
**The screen log** — `open-screen-log` on the dev panel — records every `disp` message except
`in-l`/`in-r`, stamped with the frame number:

```
 0  modal booting      31  modal-off
11  modal wiring       31  status v0.3-ready
26  modal launchpad    46  chop-size 43 %
```

✅ **The OSC rate has ample headroom, measured on the running device** (item 21): `pd` at **8.2%
CPU**, load 0.16, **110 UDP datagrams/second** to `127.0.0.1:4001`. The home frame is ten OSC
messages at 10 Hz, so 110/s is the frame clock keeping up with room to spare.

⚠️ **Hands off the device, the OLED sits on the meters and the footer** — no `og-knob-*` rows persist,
so nothing pins the param layer open (item 68). **This does not distinguish "mother does not stream
knob positions" from "the `[change -1]` guard filters them"**, and it cannot without removing the
guard. The outcome is right either way.

**Gaps read directly as tenths of a second** (11, 15, 5 = `u_init`'s 1500/1500/500 ms). It exists
because the boot sequence finishes before you can get to the window.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### `[route]` matches a SELECTOR, not a list's first element

⛔ `[route in-l]` does not match a `list` whose first element is `in-l`, and `[list prepend in-l]`
produces exactly that. Without a trim **every `disp` message is silently rejected and the display
just shows zero** (C-6).

**Fix:** finish assembled `disp` messages with `[list trim]`. A message box typed `in-l 42 dB` is
already the right shape and needs nothing.

### A new selector on `disp` costs one `route` argument in every consumer that has a fallthrough

⚠️ Everything a consumer does not recognise is a **parameter by definition**, so a selector with no
branch falls out of the reject and is drawn as a nonsense parameter row. `led` had to be added to
`g_oled`'s `route` and left unconnected; `grid` cost the same two lines.

**Fix:** when adding a selector, visit every consumer with a fallthrough — today `g_oled` and
`u_net`. **A second surface costs one route argument in the first one.** Cheap, but not free.

⛔ **And APPEND it, because the reject renumbers.** An argument slotted in beside the other layer
names shifts every outlet after it — **including the reject**, which in both files is the entire
parameter path. `diag` went on the end of both boxes and both rejects moved from outlet 8 to 9.

⛔ **A selector carrying NO arguments does not leak, and that makes the trap worse rather than
better.** `diag` alone reaches `u_net`'s reject as two atoms after the mandatory dash, dies on
`[list split 3]`'s too-short outlet, and never reaches the wire — so removing its route argument
altogether was measured against `phone-assert.sh`'s reserved window and **every datagram check still
passed.** The property is asserted where it lives instead: the gate parses both `route` boxes and
requires them to carry exactly the same selectors.

### `text get` errors if you ask for more fields than a line holds

⛔ Measured: `text get x 1 3` on a two-field line gives `field request (1 3) out of range` — and it
prints.

**Fix:** the draw path never requests fields. It takes the whole line and strips the stamp with
`[list split 1]`, which is safe because every stored line has at least three atoms.

### The param layer must NOT reorder by recency

⛔ An earlier version pushed the most-recently-moved row to the front, which is what the Phase 4 plan
asked for and was **wrong in the hand**: two faders moving together swapped places several times a
second and were unreadable.

**Fix:** rows hold their positions. The cost is honest — move nine faders and you see the five you
touched first, not the five most recent — and it is the right trade, because a display you cannot
read is worth nothing.

### Two movers are NOT two 16px lines

⛔ 16px fits about ten characters across 128 px, so `slider-1 43` clips to `slider-1 4` — **a silent
failure that looks like a working display.** Real names like `chop-size` are no shorter.

**Fix:** a small name over a mid-size value. It clips nothing and generalises.

### `g_grid` must not copy `g_oled`'s unconditional repaint

⛔ The OLED redraws at 10 Hz because its frames are cheap local UDP. **The grid's are ALSA MIDI
writes**, and ~96 of those a second is the standing suspect for the clock doubling Pd's CPU in
Phase 5.

**Fix:** a dirty flag. The frame clock checks it rather than painting, so the frame count is bounded
by the beat rate and never by the metro.

### A dark grid is two different things

⚠️ Nothing is wrong and nothing has changed (the dirty flag has no work); or the device is gone and
the **watchdog** has said so. **The OLED is what tells them apart.**

⛔ **A panic is no longer one of them.** It used to blank the Launchpad until the patch was reloaded;
`m_launchpad` does not see `panic` at all now, so the surface survives it — item 250, on
[launchpad.md](../device/launchpad.md). `display-assert.sh` asserts the grid keeps painting across
one. **Since item 296 a panic is unmistakable in the other direction**: the whole surface goes red
for a second and then returns to `home`.

⚠️ **The watchdog gives up at about 70 seconds** and writes `fail m_launchpad grid-lost` to `err`.
After that a replug will not recover the grid. See [launchpad.md](../device/launchpad.md).

## Design

### Callers send semantics, never layout

Nothing outside a `g_` file knows a pixel, a colour or a layer. A caller sends `led running`, not a
number; `modal wiring`, not a font size. **That is what makes the arbiter replaceable** and what lets
a new control appear on screen with no change to any display file.

*(judgment call)* **Reserved-names-plus-fallthrough was chosen over tagging each message with its
layer.** The cost is that a mistyped `disp` name becomes a nonsense parameter on screen rather than
an error — which is the better failure, because you can see it.

### Layers hold STATE, not draw calls

**This is why rate limiting needed no code.** The last value written is what the next frame draws,
so a burst coalesces for free and the trailing edge is guaranteed. ✅ Measured: **877 `disp` messages
in five seconds → exactly 51 frames**, the value advancing 20 per frame.

⚠️ **It is also why the ALERT buffer is not used** — see below. Buffer switching is
**edge-triggered**, and every layer here is state-driven.

### `g_led` has no layers, and does not need any — decided

**It takes the last state sent, and that is the whole design.** There are four states, exactly one
caller can be right at a time, and **no caller has ever needed a TTL** because nothing sends a
transient LED state — an LED here reports a condition, not an event.

**Rejected:** giving it the layer stack `g_oled` and `g_grid` share, for symmetry. Layers exist to
arbitrate between callers that disagree; one lamp with four mutually exclusive meanings has nothing
to arbitrate, and the stack would be structure with no question to answer.

⚠️ **What would reopen it** is a caller that wants the LED to flash for a moment and then go back —
that is an event, needs a TTL, and is the case this decision does not cover.

### `g_grid`'s `home` is a composite, and that is the one deliberate deviation

Whole-surface arbitration is right for a 128×64 screen and **wrong for a grid**, where the natural
idiom is *regions*. So the mode lamps and the beat row coexist inside the layer that never expires,
while `modal` and `alert` still take everything. **The cascade is untouched; the composition happens
below it.**

### A `warn` never reaches the grid

Only `fail` is worth the whole surface. **The grid is visible from much further away than the OLED**,
which makes a failure turning it red the most valuable thing these pads can say in a venue. `u_err`
needed no change — two consumers of one `disp` selector is fine. **The rule is one owner per
SURFACE.**

### One text renderer builds its own typetag

Every line on the OLED goes through `pd text-out`, which counts the words and picks `iiiiis` …
`iiiiissss` to match. **Hand-typed typetags are the single most repeated silent failure in this
API**; this makes an arity mistake impossible rather than merely unlikely. Values are stringified
with `[makefilename %g]`, because `packOSC` will not accept a float under an `s` tag.

### The stale-unit trap is structurally impossible in the param path

Each line is stored **whole**, so `chop-size 43 %` followed by `grain 12` cannot inherit the `%`.
There is no longer an optional field being written separately (C-7).

### The fourth surface cost nothing, and that is the shape to reach for

`u_net` **owns no selector on `disp`.** It subscribes, routes the reserved names into nothing, and
forwards the rest — so `g_oled`'s `route` is untouched and no reject connection moved. **The flat
two-line price is the cost of a surface with its own vocabulary, not the cost of a surface.** A
consumer that *mirrors* the bus is free, and that is the cheaper shape when the thing being added is
a readout rather than a device with commands of its own.

### diag goes above `modal` and below `alert`, and both halves are load-bearing

⛔ **Above `modal`, because a modal is STICKY** — cleared by `modal-off` or by a 30 s safety TTL. A
diag underneath a live modal would draw nothing at all, **which looks exactly like a dead patch**,
and the one moment you reach for a diagnostic is the moment the instrument is already misbehaving.

⛔ **Below `alert`, because a diagnostic that covers an alert is worse than no diagnostic.** That is
the direction a positive test cannot check: a layer that always wins draws its rows in every window
you look at. `oled-assert.sh` raises an alert over a live diag and asserts the roster is **gone**,
then that it comes back when the alert's TTL fires and diag's own is still running.

**It is a summons on a TTL rather than a sticky layer**, and that is the same argument as
`g_grid`'s panic paint: a readout you asked for should go away on its own, because the failure mode
of *stuck* is a screen you cannot get back on a device with no console.

### One bus for every surface, so the log reads as one sequence

The dev panel's screen log records all four interleaved, stamped with **one** frame number — so an
interaction spanning the OLED, the aux LED and the pads reads as a single sequence rather than three
that have to be correlated.

### The first frame after ownership rises IS the clear

`m_launchpad` owns the Programmer/Live switch; `g_grid` owns the LEDs. Different surfaces, one writer
each — which is what let the old 89-note clear loop be deleted outright. **The arbiter repaints from
live state**, so a replug brings the grid back in the correct state rather than restoring a frame.

### The ALERT buffer works and is unused anyway

✅ **Measured, not inferred.** `tools/alert-buffer-probe.pd` drew into buffer 4 while `g_oled` carried
on redrawing screen 3 underneath, `setscreen 4` displayed it, and `setscreen 3` brought the live
meters back. Drawing off-screen, `gFlip`-ing and switching both directions all work.

**`g_oled` still draws everything to screen 3 and never switches**, for two reasons a passing probe
does not change:

- **There is nothing to optimise.** `g_oled` clears and rebuilds screen 3 from stored state ten times
  a second, so nothing needs preserving and restore is automatic on the next frame. The saving would
  be an alert dropping from ~70 messages/second to about five, for a 2–4 second event, against a home
  screen that sustains that rate continuously.
- **Writable is not the same as safe.** A lost `setscreen 3` strands the display on a stale alert on
  a device with no console; a dropped frame today self-corrects in 100 ms. **Trading a self-healing
  design for a saving that does not matter is the wrong trade**, and it would make the alert the one
  layer that behaves differently from the other three.

### The phone stays a MIRROR, and gets no arbiter — decided

**`u_net` subscribes to `disp` and forwards; the phone decides what to show.** The priority model
therefore stops at the Organelle, and that is the answer rather than a gap.

**An arbiter exists to resolve scarcity, and the phone has none.** 128×64 pixels can show one thing
at a time, which is the whole reason `g_oled` has a cascade; the phone has a full screen and gives
every OSC address **its own row**, so parameter, status, heartbeat and alert are all visible at once
and none of them displaces another. Ordering them would be arbitration with nothing to arbitrate.

⚠️ **The diag layer sharpens this rather than weakening it.** It is the first `disp` selector that is
matched in `u_net` and deliberately **left unconnected** — the roster is a five-row screen for a
128-pixel display, and a phone that wanted the same information would ask the presence bus directly
rather than mirror a layout built for the OLED.

**What would reopen it** is the phone gaining a vocabulary of its own — a screen it draws rather than
mirrors, or state it owns. That is the case this decision does not cover.

## Open
