<!-- schema: module -->
# The audio chain

**Files:** `Cut It/u_root.pd`, `Cut It/u_level.pd` · **Gate:** none

## What it is

**The audio path is wires, on purpose.** `u_root` holds the whole chain on one canvas, laid out
right to left, so it stays something you can read off the screen instead of tracing through send
names — the opposite of how every control path in this patch works, and a deliberate exception.

⛔ **`adc~` and `dac~` appear nowhere in Cut It and must not.** `mother.pd` owns the sound card; the
patch reads `[r~ inL]` / `[r~ inR]` and writes `[throw~ outL]` / `[throw~ outR]` (C-4).

Today the chain is the two inputs, two `u_level` taps, and the two outputs. **The gap between them
is where v0.4 goes** — `e_chop`, `e_pitch`, `e_trem`, `e_verb`.

`u_level` reports the level of any signal onto the `disp` bus. Tap it off anything you want to
watch: **it has no signal outlet and does not alter the audio.**

## Facts

### The I/O contract

| Patch uses | Carries | Evidence | Item |
|------------|---------|----------|------|
| `[r~ inL]` | Input, the **tip** of the TRS Y-cable — the 404's hard-panned **drums** | verified | 11 |
| `[r~ inR]` | Input, the ring — the 404's hard-panned **fx**. The mic sums to both | verified | 11 |
| `[throw~ outL]`, `[throw~ outR]` | Everything the patch wants heard | verified | — |

```
mother:  [adc~] ─→ [s~ inL] [s~ inR]
patch:   [r~ inL] [r~ inR] ─→ … ─→ [throw~ outL] [throw~ outR]
mother:  [catch~ outL/outR] ─→ [*~ vol²] ← [lop~ 5] ─→ [clip~ -1 1] ─→ [dac~]
```

✅ Read off the device from `mother.pd`'s `pd audioIO`, and cross-checked against **every** stock
effect in `/sdcard/Patches/Effects/` — they all use exactly this.

| Fact | Evidence | Item |
|------|----------|------|
| The output path applies the volume knob — a **square law**, smoothed at 5 Hz — and a `clip~ -1 1` limiter | verified | — |
| `throw~`/`catch~` **sums**, so several stages can feed the output with no mixer | verified | — |
| **mother enables DSP**: `pd init` fires `; pd dsp 1` 200 ms after load. A patch must not | verified | — |
| mother drives the VU meter from `inL`, `inR` and the *post-volume* outputs, via `/oled/vumeter`. A patch never sends it | verified | — |

### `u_level`

| | | Evidence | Item |
|---|---|----------|------|
| Creation arg 1 | The name to report under, e.g. `in-l`. **Required** — without it the bus carries `0` as the name | verified | — |
| Inlet 1 | One signal | verified | — |
| Outlets | **None** | verified | — |
| Scale | `env~` reports **RMS on a 0–100 dB scale**, 100 being full scale | verified | 11 |
| Input noise floor | **18–19** on that scale | verified | 11 |
| A passive bass | Reaches the **90s** | verified | 11 |
| Sampling rate | **10 Hz** — `[metro 100]` banging a stored value | verified | — |
| `[change -1]` | A **steady signal stops reporting** | verified | — |

Two instances in the deployed patch: `u_level in-l` and `u_level in-r`, both on the input side.

`disp` carries them as `in-l <dB>` and `in-r <dB>`, on the **home** layer.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### `dac~` is a real bug; `adc~` merely happens to work

⛔ Writing to `dac~` bypasses **both** the volume knob and the `clip~` limiter — the knob stops
working and the patch can clip the converter. Nothing reports it.

**Fix:** `[throw~ outL]` / `[throw~ outR]`, always (C-4).

### The `[list trim]` in `u_level` is load-bearing

⛔ `[list prepend]` makes a **list**, and `route` with symbol arguments matches the **selector**, not
a list's first element — so without the trim every `disp` message is silently rejected and **the
display just shows zero** (C-6).

**Fix:** `[list trim]` after the prepend. Verified the hard way on the device.

### `env~` is polled, never pushed

⚠️ It reports on its own analysis window, which is both faster than anything can read and unrelated
to when a display wants to redraw.

**Fix:** store into a cold inlet and bang it at a fixed rate. **10 Hz here is the SAMPLING rate** —
rate-limiting the *draw* is the display's job, not this one's.

### A patch must never enable DSP

⚠️ mother's `pd init` fires `; pd dsp 1` 200 ms after load. A second one is at best redundant.

**Fix:** leave it alone. `tools/dsp.sh` turns it off on a running patch, which is how item 75's real
cause was isolated.

## Design

### The audio path is wires and the control path is buses

Every control path in Cut It travels on an allowlisted bus; the audio chain is the one place that
uses cords instead. **A signal chain you can read off the canvas is worth more than the uniformity**,
and the four v0.4 stages go into the gap right to left so it stays that way.

### The level taps need no `[trigger]`

C-3 is about **messages**. A signal fan-out has no firing order to get wrong — signal connections
all run every block — so tapping `u_level` off `[r~ inL]` alongside the main chain is safe as drawn.

### `u_level` alters nothing

No signal outlet, by design. It is a probe you can attach anywhere without thinking about what it
does to the sound, which is the only way a level meter is worth having mid-chain.

### The 404 carries the audio split

Drums hard-panned left, fx hard-panned right — two independent mono streams out of one stereo pair,
with the mic summing to both. **No routing depends on a knob position**: the 404's per-sample pans
save with the project and recall, cables carry the paths, and the mixer's knobs only set levels — a
wrong level is audible immediately rather than failing silently. See
[sp404.md](../device/sp404.md).

### Organelle audio back into the 404 was dropped

Considered and dropped. It would have used the mixer's FX send as a variable-gain feedback path.
Revisit if wanted; it needs no rewiring beyond one cable from FX SEND.

## Open

- ⬜ **There is no DSP yet.** The chain is input → level tap → output, and the four filter stages,
  the drum mode and the sampler are v0.4. See [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **Nothing measures the output side.** Both `u_level` instances are on the input; a tap before
  `throw~` would need the stages to exist first. See [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **No gate covers audio.** Every existing gate asserts on messages, and nothing reads a signal
  back. See [plan-v03.md](../../plan-v03.md) §4.
