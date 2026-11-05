<!-- schema: module -->
# The audio chain

**Files:** `Cut It/u_root.pd`, `Cut It/u_level.pd`, `Cut It/codec-gain.sh` · **Gate:** `test/gate/audio-assert.sh` · **Checklist:** `test/checklists/linecheck.md`

## What it is

**The audio path is wires, on purpose.** `u_root` holds the whole chain on one canvas, laid out
right to left, so it stays something you can read off the screen instead of tracing through send
names — the opposite of how every control path in this patch works, and a deliberate exception.

⛔ **`adc~` and `dac~` appear nowhere in Cut It and must not.** `mother.pd` owns the sound card; the
patch reads `[r~ inL]` / `[r~ inR]` and writes `[throw~ outL]` / `[throw~ outR]` (C-4).

Today the chain is the two inputs, a `[+~]` that sums the left with `c_kit`'s drums, the two
outputs, and a `u_level` on each output. **The gap between the inputs and the sum is where v0.4
goes** — `e_chop`, `e_pitch`, `e_trem`, `e_verb`.

**The meters read what Cut It sends out, not the input** (Brendan, 2026-11-04). Everything the
patch wants heard leaves through `u_root`'s two `throw~`, and each `u_level` is fed exactly what its
`throw~` is, so the OLED's two meters are the output, left and right: the mic passed through, and on
the left the drums.

`u_level` reports the level of any signal onto the `disp` bus. Tap it off anything you want to
watch: **it has no signal outlet and does not alter the audio.**

**The audio chip's own gains are Cut It's too.** The factory stages them backwards for noise and
restores that at every boot, so `u_root` re-stages them at every load through `codec-gain.sh`: the
DAC at full scale, the headphone amp down to match, the line input 12 dB quieter.

## Facts

### The I/O contract

| Patch uses | Carries | Evidence | Item |
|------------|---------|----------|------|
| `[r~ inL]` | Input, the **tip** of the input jack: the **mic**, an SM58 on an XLR-to-TS cable, since 2026-11-04 (the Organelle's Reference page) | verified | 11 |
| `[r~ inR]` | Input, the ring: nothing, with a TS plug in the jack | verified | 11 |
| `[throw~ outL]`, `[throw~ outR]` | Everything the patch wants heard, **once each, in `u_root`**: the input passed through, with `c_kit`'s drums summed into the left ([sequencer.md](sequencer.md), *The kit*) | verified | — |

What `mother.pd` does on the other side of those names (its own `adc~` and `dac~`, the volume knob's
square law, the limiter, turning DSP on, the VU meter) is on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`, under *Audio*). Every `throw~` into one
`catch~` is summed (Pure Data, in Reference), so a second stage could throw to `outL` from its own
file with no mixer, but no meter in `u_root` would then see it (*Traps*).

### The codec's gains

`codec-gain.sh` sets four of the SGTL5000's controls and echoes what the chip reads back. The chip,
its dB scales, the factory's values and the hiss are on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`, *SGTL5000*).

| Control | Cut It sets | Evidence |
|---------|-------------|----------|
| `Headphone` | 105, +1 dB | verified |
| `PCM` | 192, 0 dB | verified |
| `Capture Attenuate Switch (-6dB)` | off, so the mic gets the chip's whole gain | verified |
| `Capture` | 15, its top: +22.5 dB with the attenuator off. A dynamic mic sung close peaks about 3 dB under full scale, against the input's hiss at −71 dBFS (2026-11-04) | verified |

`Headphone` and `PCM` verified by ear on 2026-11-03, set by hand with `amixer`: the hiss goes, at
the same overall level. `Capture` measured with the Mic Probe (`tools/stage-patches/Mic Probe/`).

### `u_level`

| | | Evidence | Item |
|---|---|----------|------|
| Creation arg 1 | The name to report under, e.g. `out-l`. **Required** — without it the bus carries `0` as the name | verified | — |
| Inlet 1 | One signal | verified | — |
| Outlets | **None** | verified | — |
| Scale | `env~` reports **RMS on a 0–100 dB scale**, 100 being full scale | verified | 11 |
| Input noise floor | **18–19** on that scale, at the factory's input gain | verified | 11 |
| A passive bass | Reaches the **90s**, at the factory's input gain | verified | 11 |
| Sampling rate | **10 Hz** — `[metro 100]` banging a stored value | verified | — |
| `[change -1]` | A **steady signal stops reporting** | verified | — |

Two instances in the deployed patch: `u_level out-l` and `u_level out-r`, fed what `throw~ outL`
and `throw~ outR` are, so 100 is Cut It's output at full scale. The noise floor and the bass above
are the input's, read before the meters moved to the output; the input passes through at unity, so
a source on the input alone reads the same on the output's meter.

`disp` carries them as `out-l <dB>` and `out-r <dB>`, on the **home** layer.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### A `throw~` outside `u_root` is out of the meters' sight

⛔ mother's `catch~ outL` sums every `throw~ outL` in the patch, wherever it is, so a stage that
throws from its own file is heard and never metered: `c_kit`'s drums did until 2026-11-04, and the
OLED read the input beside them. A second `catch~` of the name to meter it is a load error, since
the name is mother's.

**Fix:** a stage gives its sound to `u_root` on an `outlet~`, as `c_kit` does, and `u_root` sums it
before its one `throw~` per side, where the meter taps. `audio-assert.sh` counts the `throw~` boxes
in every file and requires each meter's cords to equal its `throw~`'s.

### `dac~` is a real bug; `adc~` merely happens to work

⛔ Writing to `dac~` bypasses **both** the volume knob and mother's limiter, and nothing reports it
(the Organelle, in Reference).

**Fix:** `[throw~ outL]` / `[throw~ outR]`, always (C-4).

### The `[list trim]` in `u_level` is load-bearing

⛔ `[list prepend]` makes a **list**, and `route` with symbol arguments matches the **selector**, not
a list's first element — so without the trim every `disp` message is silently rejected and **the
display just shows zero** (C-6).

**Fix:** `[list trim]` after the prepend.

### `env~` is polled, never pushed

⚠️ It reports on its own analysis window, which is both faster than anything can read and unrelated
to when a display wants to redraw.

**Fix:** store into a cold inlet and bang it at a fixed rate. **10 Hz here is the SAMPLING rate** —
rate-limiting the *draw* is the display's job, not this one's.

### A patch must never enable DSP

⚠️ mother turns DSP on itself, just after load (the Organelle, in Reference). A second one is at
best redundant.

**Fix:** leave it alone. `tools/dsp.sh` turns it off on a running patch, for measuring what the
audio engine costs (item 75).

### `PCM` raised before `Headphone` comes down is 11 dB louder

⚠️ The factory's overall level is -11 dB at the DAC and +12 dB in the amp. Raise `PCM` first and,
on the first load after a boot, the output is 11 dB louder than either end until `Headphone` follows,
and for good if that second `amixer` fails.

**Fix:** `Headphone` first, and `PCM` only if that succeeded (`&&`), so the step between them and
any failure are quieter instead.

## Design

### The audio path is wires and the control path is buses

Every control path in Cut It travels on an allowlisted bus; the audio chain is the one place that
uses cords instead. **A signal chain you can read off the canvas is worth more than the uniformity**,
and the four v0.4 stages go into the gap right to left so it stays that way.

### The codec is set from `u_root`, at `loadbang`

`u_root` holds the audio chain, and the codec's gains are its two analog ends, so the invocation
sits beside `[r~ inL]` and `[throw~ outL]`: the file that owns a concern runs its script at load,
as `u_err` runs `logroll.sh` and `u_state` runs `state-dir.sh`. **No `u_init` stage is needed**:
the factory's `setup.sh` has finished before Pd starts, and a patch load leaves the mixer alone
(the Organelle, in Reference). It runs at every load because a reboot undoes it. `setup.sh` itself
stays as the factory shipped it, on the read-only root and outside anything Cut It deploys.

### The level taps need no `[trigger]`

C-3 is about **messages**. A signal fan-out has no firing order to get wrong — signal connections
all run every block — so tapping `u_level` off the sum alongside `throw~ outL` is safe as drawn.

### The output is summed in `u_root`, and metered there

The meters read Cut It's output (Brendan, 2026-11-04), so everything Cut It sends out has to pass
one point a meter can tap before it reaches mother's `catch~`. **That point is `u_root`, on
cords**: `c_kit` hands its drums up an `outlet~`, a `[+~]` sums them with the input's tip, and the
sum feeds both `throw~ outL` and `u_level out-l`. On the right the input's ring is all there is, and
it feeds `throw~ outR` and `u_level out-r` the same way. It keeps the audio path something read off
one canvas. A private `catch~` of Cut It's own was the alternative: every stage would throw to it
with no cords, at the cost of each one learning `u_root`'s `$0` as a creation argument, and of the
chain no longer being visible as wires. A stage added later joins the sum the way the drums do, and
a stage on the right gets a `[+~]` of its own.

### The gate marks went with the input meters

The marks were a box under each meter from the input's noise floor to where a noise gate on the
input would sit, item 11's numbers, for setting a gate on what came in. **An output meter has
neither**: nothing gates the output, and its floor is whatever the stages and the drums leave.
What an output meter needs marked is full scale, and that is the bar's right edge. So they went
([display.md](display.md)).

### `u_level` alters nothing

No signal outlet, by design. It is a probe you can attach anywhere without thinking about what it
does to the sound, which is the only way a level meter is worth having mid-chain.

### The mic goes straight in, and the drums are Pd's

The mic is the input's tip, with no preamp in front of it: the Organelle's own input gain, turned
all the way up, is enough for a voice (the Organelle's Reference page). The drums no longer come
in at all: `c_kit` plays them and `u_root` sums them into the left output, where the 404's
hard-panned drums used to arrive ([sequencer.md](sequencer.md)). **No routing depends on a knob position**: cables carry the
paths, and the mixer's knobs only set levels.

### Organelle audio back into the 404 was scrapped

It would have used the mixer's FX SEND as a variable-gain feedback path. Scrapped outright, not
deferred — item 264. The SP-404 has since left the rig altogether (Brendan, 2026-11-04;
[rig.md](../rig.md)).

## Open

- ⬜ **There is no DSP yet.** The chain is input → the sum → output, metered there, and the four filter stages,
  the drum mode and the sampler are v0.4. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **The input levels above were measured at the factory's input gain.** The noise floor and the
  passive bass are item 11's, taken before `Capture` came down 12 dB. Re-measure with
  `tools/audio-probe/`. `cut-it/inbox`.
