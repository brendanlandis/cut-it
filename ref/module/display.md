<!-- schema: module -->
# The display arbiter

**Files:** `Cut It/g_oled.pd`, `Cut It/g_grid.pd`, `Cut It/g_led.pd` · **Gate:** `test/gate/display-assert.sh`, `test/gate/oled-assert.sh`, `test/gate/led-assert.sh` · **Checklist:** `test/checklists/display.md`, `test/checklists/nanokontrol.md`, `test/checklists/launchpad.md`

## What it is

**One bus, three surfaces, and an arbiter rather than a print function.** Most knob turns, fader
moves and button presses want a display for as long as they are moving, so many sources contend for
one screen. Nothing in Cut It draws: everything sends **semantics** to `disp` and does not know or
care how — or whether — it is rendered.

⛔ **One owner per display surface (C-5).** `g_oled` owns `oscOut` and `screenLine1`–`5`; `g_grid`
owns the Launchpad's LEDs; `g_led` owns the aux button. **`u_err` filters and forwards onto `disp`
rather than drawing.**

Two of the surfaces run the **same arbiter shape** — `home < modal < alert`, each layer with a
priority and a time to live, one winner per frame. `g_oled` runs five of them and `g_grid` three,
and `g_grid` deviates in exactly one interesting way: its `home` is a **composite**.

**The phone is not one of them** (Brendan, 2026-11-04). It was the fourth, a mirror of this bus,
until Brendan split the two: the OLED for alerts and warnings, levels and the name of a control as
it moves, the phone for the Launchpad's current page, from each module's state on cords
([phone.md](../device/phone.md)). `u_net` reads nothing on `disp`.

## Facts

### The surfaces, honestly rated

| Surface | Plain English? | Owner | Verdict | Evidence | Item |
|---------|----------------|-------|---------|----------|------|
| Organelle OLED | yes | `g_oled` | The primary performance surface. 128×64 graphics, not five text lines | verified | — |
| Organelle aux LED | no | `g_led` | One RGB LED, **seven colors and off**. The only state display that is not a screen | verified | — |
| Launchpad Pro MK3 | no | `g_grid` | **96 button LEDs + the logo** = 97 addressable, painted across an index span of **1–108**. Spatial state only | verified | — |
| iPhone / TouchOSC | yes | `u_net` | Not on `disp` since 2026-11-04: it controls the Launchpad's current page, from state on cords ([phone.md](../device/phone.md)) | unknown | — |

Two devices in the rig can display nothing at all: the nanoKONTROL mk1 has no host-controllable
LEDs, and the Volca is receive-only. The SP-404, until it left the rig (2026-11-04), had **the best
screen in it and nothing known reached it** (Reference, `~/Sites/!reference/roland-sp-404mkii.md`).

### The `disp` message

**`<name> <value> [unit]`, with the name as the SELECTOR.** `g_oled` routes eight selectors;
**everything else is a parameter by definition** — there is no registration step, so a new control
needs no change to any display.

| Selector | Carries | Layer | Evidence | Item |
|----------|---------|-------|----------|------|
| `out-l` `out-r` | `<dB>` from `u_level`: what Cut It sends out, left and right ([audio.md](audio.md)) | home | verified | — |
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
| `home` | 0 | Always active | Never | Two output meters and their 8px readouts, and nothing else | verified | — |
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
| out-l 43        y=0  8 |  | chop-size       y=0  8 |  |+----------------------+|
| ==========      y=10 18|  |                        |  || fail        y=6   16 ||
| ==========             |  |  43 %           y=12 24|  ||                      ||
|                        |  |                        |  || u_init      y=30   8 ||
| out-r 19        y=32 8 |  |                        |  || launchpad-x y=44   8 ||
| ===             y=42 18|  | =========       y=48  5|  |+----------------------+|
| ===                    |  | ====            y=56  5|  +------------------------+
+------------------------+  +------------------------+
```

| | Evidence | Item |
|---|----------|------|
| `env~`'s 0–100 maps to pixels as **× 1.28**, clipped to **1–128** — a zero-width `gFillArea` is untested and silence is the common case | verified | — |
| **No gate marks** since the meters read the output (Brendan, 2026-11-04): they marked the input's noise floor and a gate window over it, item 11, and an output meter has neither (*Design*) | verified | 11 |
| Home is two halves of 32 rows: a readout at y=0 and y=32, its bar 18 px tall at y=10 and y=42, and four blank rows after each bar. **No footer** since 2026-11-04 (*Design*) | verified | — |
| A moving knob shrinks the meters into a **full-width 5 px bottom strip**, not a corner. A corner meter here is ~40×4 px, and 24px text needs the full width anyway | verified | — |

### The param layer is a list, and rows are STABLE

With 18 continuous controls, moving two faders together is ordinary use. The param layer holds **up
to five entries** in `[text define $0-params]`, one line of `<frame-stamp> <name> <value> <unit>`.

| | Evidence | Item |
|---|----------|------|
| A control already on screen is updated **in place** — only its value changes. A new one is appended **below**. A **sixth is refused** until a row frees up | verified | — |
| Aging: each entry records the frame it last moved in, and anything **13 frames** behind is dropped every frame | verified | — |
| The scan walks from the **last index toward 0**, because deleting a line shifts everything below it and going downward makes that harmless. `until`'s own count bounds the loop | verified | — |
| **13 and not 12 is deliberate** — `pd layers` clears `$0-a-param` on a 1200 ms delay, so the store is guaranteed to outlive the flag by a frame. Otherwise a rounding difference leaves the param layer winning with nothing to draw, which looks exactly like a dead patch | verified | — |

**Type size follows how many are moving.** The param area is y=0…46; the meter strips at y=48/56 are
untouched throughout.

| Moving | Layout | Evidence | Item |
|--------|--------|----------|------|
| 1 | Name 8px @ y=0, value+unit **24px** @ y=12 | verified — byte-identical to what Phase 3 shipped | — |
| 2 | Name 8px @ y=0 / value **16px** @ y=8, then name 8px @ y=23 / value 16px @ y=31 | verified | — |
| 3–5 | **8px** rows at y=0, 9, 18, 27, 36, in the order first touched | verified | — |

✅ **All three are legible at playing distance — item 258.** Read off the panel by eye at arm's
length rather than judged from the geometry, one nano slider then two then four to raise each
layout in turn. **Even the 8px five-row case passes.**

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
| One row per source on the presence bus, drawn as `<src> <state>`. The roster is whatever `expect` published at load — today **five**: `m_launchpad`, `m_nano`, `m_organelle`, `m_volca` and `m_streich` (2026-11-04), the most the layer draws. `m_404` went with the SP-404, and `m_nanokey` publishes nothing, since its row would be the sixth ([nanokey.md](../device/nanokey.md)) | verified | 301 |
| ⛔ **`<src>` is the ABSTRACTION's name** — `m_nano`, never "nanoKONTROL". `g_oled` sits below the `m_` boundary, so this is the only name it has. See [presence.md](presence.md) | verified | 301 |
| Four states: `here` · `gone` · `never` · `unchecked`. **`m_volca` registers `none` and reads `unchecked`** — it is never polled and can never be lost, so drawing it as healthy would be a claim nothing has tested | verified | 301 |
| ⛔ **The loop is bounded at FIVE rows, not at the roster size.** A sixth would draw at y=45 and run into the meter strip at y=48 | verified | 301 |
| ⚠️ **`m_launchpad unchecked` is 21 characters** — the whole width of an 8px row. A longer state word or a longer abstraction name clips silently | verified | 301 |
| Summoned by `disp` → `diag`, which carries nothing. Cleared by a retriggered `[del 8000]`, so pressing again while it is up buys another eight seconds | verified | 301 |
| The control is **`og-shift-60` on every page** — hold `aux` and press the lowest key. One row of `cut-it-map.txt` per page | verified | 304 |
| The state lives in a `[text define $0-diag]` as `<src> <code>` — **numbers, not words**, so every transition is a comparison and the words are chosen once, where they are drawn | verified | 301 |

⚠️ **Presence is *last heard*, not *alive*, and the labels are chosen to say so.** A nanoKONTROL
nobody has touched reads `here` and one on the floor reads `here` until the poll misses three times.
No amount of code changes that — the operator supplies it.

✅ **The summoning control is on the one panel that can never be the missing device.** On the
Launchpad it would be dead in exactly the case the roster exists for — a Launchpad that has come
unplugged sends no CC. The aux modifier and its 25 shifted keys are where it lives, beside `stop`
and `recover`. See [organelle.md](../device/organelle.md).

### `g_grid` — the same shape, one link shorter

| Layer | Pri | Raised by | Cleared by | Draws | Evidence | Item |
|-------|-----|-----------|------------|-------|----------|------|
| `home` | 0 | Always active | Never | **Regions** — eight mode lamps down the left column, CC 80 to 10, and the beat row on grid indices 11–18; on page 2 the **drum page** instead of the beat row, on page 3 the **synth pads** above it, and on page 1 the **tap pad** | unknown | — |
| `modal` | 1 | `disp` → `grid modal <palette>` | `grid modal-off`, or a 30 s safety TTL | The whole surface, one color | verified | — |
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
| Every repaint is one SysEx of **108 color specs covering indices 1–108**: 332 bytes when every spec is a palette color, two more for each RGB one (the drum page's, below) | verified | — |
| The frame clock **costs nothing**: it checks the flag rather than painting. 10 Hz and 50 Hz measured identical on the device | verified | 94 |
| Raised from 10 Hz because at 240 BPM a 250 ms beat does not divide into 100 ms, so the beat row swung **±50 ms** | verified | — |
| **Every raise AND every expiry sets the dirty flag** — a layer falling away changes the frame as much as one arriving | verified | — |

### `g_grid`'s drum page, page 2

**One layout table, `Cut It/cut-it-drum-page.txt`, says which cell is which**: a row per cell,
`<index> <role> <n>`, read with `-c` at load by `g_grid` to paint and by `u_map` to know what a
press means, so a press and its lamp cannot disagree. Its 60 rows:

| Rows from the top | Cells | Role | Evidence |
|---|---|---|---|
| 1–4 | 81–88, 71–78, 61–68, 51–58 | `step` 1–8, 9–16, 17–24, 25–32 (Brendan, 2026-11-03: 32 steps) | unknown |
| 5–8, left 4×4 | 41–44, 31–34, 21–24, 11–14 | `pad` 13–16, 9–12, 5–8, 1–4: counted from the bottom left, pad 1 there and four a row upward (Brendan, 2026-11-04) | unknown |
| 5, right half | 45–48 | `rep` 1–4, the repeat pads (Brendan, 2026-11-03) | unknown |
| 6, right half | — | in no row, so dark | unknown |
| 7–8, right half | 25–28, 15–18 | `vel` 1–4, then 5–8 (Brendan, 2026-11-03) | unknown |

**The caller is `c_steps`, on `g_grid`'s third inlet, and it sends meaning, never a cell** (C-5):
`steps <32 levels>` for the selected track, 0 for off, `play <step>` (0 while stopped), `vel <level>`,
`track <pad>` and `last <step>`, the selected track's, `bar <steps>`, a bar of the time signature,
and `rep <pad>`, the repeat pad held, 0 for none. Every message sets the dirty flag.

**A velocity level is a color, and everything that means that level shows it** (Brendan,
2026-11-03): a step lit at a velocity, the button that gives it, and the selected pad while that
button is selected.

| A cell | Paints | Evidence |
|---|---|---|
| A step past the last step | 0, dark, lit or not: its note is kept, unplayed (Brendan, 2026-11-03) | unknown |
| A step that is off | 1, dim; blue, RGB 16, 40, 127, if it starts a bar: step 1, then every `bar` steps (Brendan, from a mockup, 2026-11-04) | unknown |
| A step that is on | Its level, which `c_steps` works out from its velocity ([sequencer.md](sequencer.md)), in that level's RGB color: white for level 1, falling evenly to bright red for level 8 | unknown |
| The playhead's step | 21, green, over whatever the step holds | unknown |
| A velocity button | Its own level's color: full when selected, a quarter otherwise | verified |
| The selected pad | The selected level's color, full | unknown |
| Every other pad | RGB 6, 6, 6: dimmer than any velocity button (Brendan, 2026-11-03: palette 1 read the same as the dimmest button) | unknown |
| A repeat pad | Purple: RGB 20, 8, 32, and 80, 24, 127 while it is held (Brendan, from a mockup, 2026-11-04) | unknown |

**The beat row gives way**, and the right 4×4's second row stays dark. The mode lamps are drawn
as in every mode.

⚠️ **The levels' colors are RGB specs, not palette entries.** The palette is a color table with no
even white-to-red ramp in it (Reference), so `g_grid`'s surface holds 128 + *k* for entry *k* of its
own RGB table, and the paint loop sends those cells as type 3, red, green and blue: red 127, and
green and blue 127, 109, 91, 73, 54, 36, 18, 0 for levels 1 to 8; the quarter is each over four;
6, 6, 6 for a pad not selected; 16, 40, 127 for a bar's first step; and 20, 8, 32 and 80, 24,
127 for a repeat pad and the one held.
✅ On the rig the eight read as eight, white to red (Brendan, 2026-11-03).

### `g_grid`'s synth pads, page 3

**`Cut It/cut-it-synth-page.txt` says which cell is which synth**, `<index> <synth>`, read with `-c`
at load by `g_grid` to paint and by `u_map` to know what a press means, as the drum page's layout is
([synths.md](synths.md)). Cells 21–24, the second row from the bottom on the left, are `fm`, and
25–28 on the right are `strings` (Brendan, 2026-11-04). The beat row stays on row 1 below them, and
the mode lamps are drawn as on every page.

**The caller is `c_synth`, on `g_grid`'s fourth inlet**: `synth fm` or `synth strings`, which
`g_grid` holds as 1 or 2 and which sets the dirty flag. It starts at `fm`, `c_synth`'s own, so the
pads are right even before the first message. Anything else on that inlet is `fail g_grid
bad-selector`.

| A cell | Paints | Evidence |
|---|---|---|
| A synth's pad, that synth chosen | Its color, full: `fm` amber, RGB 127, 56, 0; `strings` cyan, RGB 0, 96, 127 | unknown |
| A synth's pad, the other chosen | The same color at a quarter: 32, 14, 0 and 0, 24, 32, the drum page's full-and-quarter that read as two states on the rig | unknown |

⚠️ **They are RGB specs, 148 to 151 on the surface**: entries 20 to 23 of the RGB table, each
synth's full then its quarter. `pd regions` works a cell's out as 146 + 2*n* + (*n* is not the
choice), *n* 1 for `fm` and 2 for `strings`, so a third synth is two more entries and nothing else.

### `g_grid`'s tap pad, page 1

**`Cut It/cut-it-arrangement-page.txt` says which cell does what on page 1**, `<index> <role>`,
read with `-c` at load by `g_grid` to paint and by `u_map` to know what a press means, as the synth
pads' layout is. Today it is one row, `21 tap`: the second row's first pad, above the beat row's
first, which stays on row 1 as on every page but the drums (Brendan, 2026-11-04). A press taps the
tempo ([tempo.md](tempo.md), *Tap tempo*).

**The caller is `u_tempo`, on `g_grid`'s fifth inlet**: `tap`, on each tap, which lights the pad
full for 120 ms, a `[del]` a tap inside it restarts, and sets the dirty flag as it goes on and off.
Anything else on that inlet is `fail g_grid bad-selector`.

| A cell | Paints | Evidence |
|---|---|---|
| A tap cell | Yellow at a quarter, RGB 32, 24, 0: lit dimly, as Brendan asked | unknown |
| The same, for 120 ms after a tap | Yellow, full, RGB 127, 96, 0 | unknown |

⚠️ **They are RGB specs, 152 and 153 on the surface**: entries 24 and 25 of the RGB table. `pd
regions` paints each row of the layout whose role is `tap` from `[f 152]`, which `$0-tap`, the
flash, raises to 153.

### Seeing it off-device

`u_mother-stub`'s eight screen rows are `cnv` objects whose **label** is the drawn text.
**The screen log** — `open-screen-log` on the dev panel — records every `disp` message except
`out-l`/`out-r`, stamped with the frame number:

```
 0  modal booting      31  modal-off
11  modal wiring       46  chop-size 43 %
26  modal launchpad
```

✅ **The OSC rate has ample headroom, measured on the running device** (item 21): `pd` at **8.2%
CPU**, load 0.16, **110 UDP datagrams/second** to `127.0.0.1:4001`. The home frame was ten OSC
messages then, so 110/s was the frame clock keeping up with room to spare; it is seven since the
footer and the gate marks went.

⚠️ **Hands off the device, the OLED sits on the meters** — no `og-knob-*` rows persist,
so nothing pins the param layer open (item 68). **This does not distinguish "mother does not stream
knob positions" from "the `[change -1]` guard filters them"**, and it cannot without removing the
guard. The outcome is right either way.

**Gaps read directly as tenths of a second** (11, 15, 5 = `u_init`'s 1500/1500/500 ms). It exists
because the boot sequence finishes before you can get to the window.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### `[route]` matches a SELECTOR, not a list's first element

⛔ `[route out-l]` does not match a `list` whose first element is `out-l`, and `[list prepend out-l]`
produces exactly that. Without a trim **every `disp` message is silently rejected and the display
just shows zero** (C-6).

**Fix:** finish assembled `disp` messages with `[list trim]`. A message box typed `out-l 42 dB` is
already the right shape and needs nothing.

### A new selector on `disp` costs one `route` argument in every consumer that has a fallthrough

⚠️ Everything a consumer does not recognize is a **parameter by definition**, so a selector with no
branch falls out of the reject and is drawn as a nonsense parameter row. `led` had to be added to
`g_oled`'s `route` and left unconnected; `grid` cost the same two lines.

**Fix:** when adding a selector, visit every consumer with a fallthrough — today `g_oled` alone,
since `u_net` stopped reading `disp` (2026-11-04). **A second surface costs one route argument in
the first one.** Cheap, but not free.

⛔ **And APPEND it, because the reject renumbers.** An argument slotted in beside the other layer
names shifts every outlet after it — **including the reject**, which is the entire parameter path.
`diag` went on the end of the box and the reject moved from outlet 8 to 9; taking `status` out of
the middle (2026-11-04) moved it back to 8, and every layer's cord after it with it.

### `text get` errors if you ask for more fields than a line holds

⛔ It prints an error rather than handing on the fields there are (Pure Data, in Reference).

**Fix:** the draw path never requests fields. It takes the whole line and strips the stamp with
`[list split 1]`, which is safe because every stored line has at least three atoms.

### The param layer must NOT reorder by recency

⛔ Pushing the most-recently-moved row to the front reads well on paper and is **wrong in the
hand**: two faders moving together swap places several times a second and are unreadable.

**Fix:** rows hold their positions. The cost is honest — move nine faders and you see the five you
touched first, not the five most recent — and it is the right trade, because a display you cannot
read is worth nothing.

### Two movers are NOT two 16px lines

⛔ 16px fits about ten characters across 128 px, so `slider-1 43` clips to `slider-1 4` — **a silent
failure that looks like a working display.** Real names like `chop-size` are no shorter.

**Fix:** a small name over a mid-size value. It clips nothing and generalizes.

### `g_grid` must not copy `g_oled`'s unconditional repaint

⛔ The OLED redraws at 10 Hz because its frames are cheap local UDP. **The grid's are ALSA MIDI
writes** — a SysEx of 332 bytes or more per frame — and nothing about the grid needs one when nothing changed.

**Fix:** a dirty flag. The frame clock checks it rather than painting, so the frame count is bounded
by the beat rate and never by the metro.

### A dark grid is two different things

⚠️ Nothing is wrong and nothing has changed (the dirty flag has no work); or the device is gone and
the **watchdog** has said so. **The OLED is what tells them apart.**

⛔ **A panic is not one of them.** `m_launchpad` does not see `panic` at all, so the surface survives
it — item 251, on [launchpad.md](../device/launchpad.md) — and `display-assert.sh` asserts the grid
keeps painting across one. **A panic is unmistakable in the other direction**: the whole surface goes
red for a second and then returns to `home` (item 296).

⚠️ **The watchdog gives up at about 70 seconds** and writes `fail m_launchpad grid-lost` to `err`.
After that a replug will not recover the grid. See [launchpad.md](../device/launchpad.md).

## Design

### The meters are the output, and nothing on them marks the input

**The OLED is for alerts and warnings, the output's levels and the name of a control as it moves**
(Brendan, 2026-11-04), so home's two meters are what Cut It sends out, left and right, read where
`u_root` throws them ([audio.md](audio.md), *The output is summed in `u_root`, and metered there*).
The readouts say so, `out-l` and `out-r`, and the screen log and the bus use the same names.

**The gate marks went with the input.** They were a box under each meter from the input's noise
floor to where a noise gate on the input would sit — a guide to setting a gate on what came in. An
output meter has no gate behind it and no fixed floor: what it shows is how near the output is to
full scale, and full scale is the bar's right edge.

### Nothing at rest but the levels: the footer went

**The footer showed the tempo, and the tempo is the phone's** (Brendan, 2026-11-04): the phone's
arrangement screen draws it, and on the OLED it is a control's name, `bpm 120`, while knob 1 moves.
The footer's other two words went with it, judged against the same rule:

| It carried | Why it went | What says it now |
|---|---|---|
| The BPM, from `u_tempo` | The tempo lives on the phone | The phone; knob 1's row while it turns |
| `panic`, from `u_init` | Neither an alert nor a warning: a person pressed it, and nothing is wrong | The aux LED, red until the transport moves, and the whole grid red for a second |
| `v0.3-ready`, from `u_init`, for half a second before the BPM took over | A version is none of the three | The boot's last modal clearing to the meters ([boot.md](boot.md)) |

**So `status` left the bus**, and `g_oled`'s route lost it. Home is the two meters, given the whole
screen in two equal halves, and the boot's modals are still the boot's: they are what a stuck boot
shows. A `status` sent now is a parameter row by the fallthrough, which is the visible failure that
rule chose.

### Callers send semantics, never layout

Nothing outside a `g_` file knows a pixel, a color or a layer. A caller sends `led running`, not a
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
below it.** The drum page is one more region, chosen by the mode, so a panic or a `fail` still takes
the whole surface over it.

### The drum page's state rides a cord, not `disp`

The playhead moves sixteen times a bar, and on `disp` every move would land in the dev panel's screen
log, which records the whole bus. `c_clock`'s beat row is the precedent: a cord into `g_grid`, from
the one file that has the state, and the bus stays for requests a person would want to read back.

### The layout is a file both sides read

**A press and its lamp come from one table.** `u_map` turns `pad-81` into *step 1* and `g_grid`
lights step 1 at index 81 from the same row, so moving the velocity row is one edit and cannot
leave a button lit in one place and acting in another. `c_steps` never reads it: it knows steps,
velocities and pads, never where they are.

### A `warn` never reaches the grid

Only `fail` is worth the whole surface. **The grid is visible from much further away than the OLED**,
which makes a failure turning it red the most valuable thing these pads can say in a venue. `u_err`
needed no change — two consumers of one `disp` selector is fine. **The rule is one owner per
SURFACE.**

### One text renderer builds its own typetag

Every line on the OLED goes through `pd text-out`, which counts the words and picks `iiiiis` …
`iiiiissss` to match. **Hand-typed typetags are the single most repeated silent failure in this
API**; this makes an arity mistake impossible rather than merely unlikely. Values are stringified
with `[makefilename %g]`, because `packOSC` refuses a float under an `s` tag (Reference,
`~/Sites/!reference/critter-guitari-organelle-1.md`, *The typetag must match the argument count
exactly*).

### The stale-unit trap is structurally impossible in the param path

Each line is stored **whole**, so `chop-size 43 %` followed by `grain 12` cannot inherit the `%`.
There is no longer an optional field being written separately (C-7).

### A mirror is free, and the phone stopped being one

A consumer that owns no selector on `disp` and forwards the rest costs `g_oled`'s `route` nothing:
that was the phone until 2026-11-04, and it is the cheaper shape when the thing being added is a
readout. **The phone became a device with commands of its own** — the Launchpad's page, the tempo,
the sequencer's settings — and a mirror of the OLED's rows is the wrong vocabulary for that, so it
reads each module's state on cords instead ([phone.md](../device/phone.md)).

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

The dev panel's screen log records all three interleaved, stamped with **one** frame number — so an
interaction spanning the OLED, the aux LED and the pads reads as a single sequence rather than three
that have to be correlated.

### The first frame after ownership rises IS the clear

`m_launchpad` owns the Programmer/Live switch; `g_grid` owns the LEDs. Different surfaces, one writer
each, and no clear loop anywhere. **The arbiter repaints from live state**, so a replug brings the
grid back in the correct state rather than restoring a frame.

### The ALERT buffer works and is unused anyway

✅ **Measured, not inferred.** `tools/alert-buffer-probe.pd` drew into buffer 4 while `g_oled` carried
on redrawing screen 3 underneath, `setscreen 4` displayed it, and `setscreen 3` brought the live
meters back. Drawing off-screen, `gFlip`-ing and switching both directions all work.

**`g_oled` still draws everything to screen 3 and never switches**, for two reasons a passing probe
does not change:

- **There is nothing to optimize.** `g_oled` clears and rebuilds screen 3 from stored state ten times
  a second, so nothing needs preserving and restore is automatic on the next frame. The saving would
  be an alert dropping from ~70 messages/second to about five, for a 2–4 second event, against a home
  screen that sustains that rate continuously.
- **Writable is not the same as safe.** A lost `setscreen 3` strands the display on a stale alert on
  a device with no console; a dropped frame today self-corrects in 100 ms. **Trading a self-healing
  design for a saving that does not matter is the wrong trade**, and it would make the alert the one
  layer that behaves differently from the other three.

### The phone was a mirror, and Brendan's split reversed it

**Decided until 2026-11-04: `u_net` subscribed to `disp` and forwarded, and the phone decided what
to show**, with no arbiter, since the phone had a row for every address and nothing to arbitrate.
The case that decision said it did not cover — the phone gaining a vocabulary of its own, a screen
it draws rather than mirrors, or state it owns — is what came: **Brendan split the two that day**,
the OLED for alerts and warnings, levels and the name of a control as it moves, the phone for the
Launchpad's current page. So the phone reads nothing on `disp`, the priority model still stops at
the Organelle, and the phone's screens are its own ([phone.md](../device/phone.md), *The phone
controls the page, and does not copy the OLED*).

## Open
