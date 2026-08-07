<!-- schema: module -->
# Tempo and clocks

**Files:** `Cut It/u_tempo.pd`, `Cut It/c_clock.pd` · **Gate:** `tools/phase6-assert.sh` · **Bench:** `tools/phase5-bench.pd`

## What it is

**`u_tempo` is the master REFERENCE, and it is not the clock.** It owns the master BPM, the pulse
oscillator that MIDI clock is cut from, and the transport. Cut It runs **poly-tempo**: every part
that needs a beat owns a `c_clock` instance with its own rate and its own time signature, aligned to
master by a `start`.

`u_root` holds the first instance, `c_clock 1 8` — ratio 1, eight beats to the bar, so its
beat-number outlet indexes the grid's bottom row directly. **Nothing downstream may assume the
global `clock` is its clock**; that instance is the grid's, and the next consumer gets its own.

`u_tempo` has no creation arguments, no inlets and no outlets. It talks on `tempo`, `clock`, `start`,
`stop`, `panic`, `disp` and `err`, and out of two MIDI ports.

## Facts

### The System Real-Time bytes

| Message | Decimal | Hex | Evidence | Item |
|---------|---------|-----|----------|------|
| Timing Clock | 248 | `F8` | verified | 63 |
| Start | 250 | `FA` | verified | — |
| Continue | 251 | `FB` | **never sent** — see *Traps* | verified | — |
| Stop | 252 | `FC` | verified | — |

Clock is **24 PPQN** — 24 pulses per quarter note, one every 20.8 ms at 120 BPM.

| Transport event | Sends | Evidence | Item |
|-----------------|-------|----------|------|
| `start` | 250 | verified | — |
| `stop` | 252 | verified | — |
| `panic` | 252 on every port, plus the aux LED. **Note-silencing is each device layer's own** | verified | 231 |

### How the clock is built

| Stage | Detail | Evidence | Item |
|-------|--------|----------|------|
| BPM ÷ 60 × 24 → `[phasor~]` at the pulse rate | 48 Hz at 120 BPM | verified | 48 |
| `[threshold~ 0.5 0 0.1 0]` → one bang per cycle | The phasor crosses 0.5 once per ramp and falls below 0.1 on the wrap | verified | 48 |
| Every pulse emits 248 and increments a counter | `[mod 24]` = 0 is the beat, published on `clock` | verified | 48 |
| Out on Pd MIDI ports **1 and 3** | The Launchpad (`Pure Data:4`) and the SP-404 (`Pure Data:6`), already in `wire.sh` | verified | — |

**Counting the pulses rather than running a second oscillator is what makes the beat and the MIDI
pulse the same clock by construction.** Measured under real DSP: 6 beats in 3 s at 120 BPM, 3 in 3 s
at 60.

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Control range | **10–500 BPM** from knob 1 | verified | — |
| Legal range | **5–600 BPM**, clamped | verified | — |
| Outgoing jitter | **~1.45 ms** — Pd emits on 64-sample block boundaries, about 7% of a pulse interval at 120 BPM. Not fixable in vanilla Pd | verified | — |
| Start alignment | Within **half a pulse** — `threshold~` fires at phase 0.5, so the first pulse after a start arrives ~10.4 ms later at 120 BPM. A constant offset shared by every clock in the patch | verified | — |
| The port | Set into `[midiout]`'s **cold inlet at load**, `u_init`'s proven pattern. A nonexistent port is silently dropped, so port 3 on the Mac costs nothing and prints nothing | verified | 63 |

The control range and the legal range are **different decisions**, and the legal one is wider at both
ends so a bench, a tap tempo or an LFO is not limited by what one knob chose.

### `c_clock`

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Creation arg 1 | Ratio to master tempo — 1 follows it, 1.5 runs half again as fast | verified | — |
| Creation arg 2 | Beats per bar | verified | — |
| Bad arguments | Corrected to 1 and 4 **immediately**, reported on `err` at 2 s | verified | — |
| Outlet 0 | The raw beat phase, **as a signal** | verified | — |
| Alignment | `start` resets. **`stop` does not halt** — a running phasor nobody reads is silent, and halting it is the consumer's business | verified | — |

**The ×24 and the `wrap~` are the alignment mechanism.** A threshold at 0.5 of the *beat* phasor
would fire half a beat away from `u_tempo`'s beat, because `u_tempo`'s pulses fire at 0.5 of a
*pulse*. One phasor, two uses: the signal outlet carries beat phase for sample-accurate grain work,
and the events are cut from the same ramp. A second oscillator at 24× would drift from the first —
slowly, and only under a long take.

### Tempo propagates unevenly, because MIDI clock has no tempo message

Because the Organelle *generates* the clock, tempo is just a float in the patch and anything may
write the `tempo` bus. **But you cannot send a BPM.** You change the *rate* of the 24 PPQN pulse
stream, and slaved devices infer tempo by measuring pulse intervals — most averaging over several
pulses.

| Change | What slaved gear does | Evidence | Item |
|--------|-----------------------|----------|------|
| Gradual | Tracks fine everywhere | verified | — |
| Instant jump | Takes several pulses to propagate. Large ones can make the 404 or Volca **stutter or briefly drop sync** | verified | — |

⚠️ **So internal and external timing diverge under fast modulation.** The Organelle's own grain
clocks are `phasor~`-based — a frequency change is instant and glitch-free, and the phase simply
continues. Slaved gear lags several pulses behind. **Modulate tempo quickly and the Organelle is
somewhere the 404 has not reached yet.**

### The four rate ceilings

⚠️ **These get confused with each other constantly.** They stack, and the one that bites is whichever
is lowest on the path you are actually using.

| Ceiling | Value | What it limits | Evidence | Item |
|---------|-------|----------------|----------|------|
| `threshold~` pulse | **344 Hz** = 44100/64/2 | The raw 24 PPQN pulse | verified | 58 |
| `c_clock`'s **bang** outlet | **14.3/s** = 344 ÷ 24 | Beat bangs. The ×24 that buys provable alignment costs a factor of 24 in headroom | verified | 58 |
| MIDI triggers to the 404 | ~360–400/s | Note-on/off pairs. Perceptual, not a hard edge | verified | 208, 209 |
| Pd's own wall | ~689/s | One message per 64-sample scheduler tick, a compile-time constant. **Never reached** — something downstream saturates first | verified | — |

### What the clock actually costs, isolated

⛔ **The clock is not the CPU cost, and this was recorded wrongly once.** The original measurement
blamed the 96 ALSA MIDI writes a second. Toggling DSP on a running patch settles it:

| | pd CPU | Evidence | Item |
|---|--------|----------|------|
| DSP on | **11.8 / 11.7 / 11.8 %** | verified | 75 |
| DSP off | **4.9 / 4.9 / 4.9 %** | verified | 75 |
| DSP back on | **12.0 / 11.8 %** | verified | 75 |

**So ~7 points are the audio engine and the MIDI rate is not it** — varying tempo moves the MIDI rate
while leaving DSP cost identical. `tools/dsp.sh` is what performs the toggle.

⛔ **No clock-driven path can produce an audio-rate MIDI stream.** At 14.3 bangs/s, `c_clock` is two
orders of magnitude below the trigger ceiling. A dense machine-gun trigger stream needs a plain
`[metro]`, not a clock ratio — **measured by trying, and the clock ran out first.**

**But the audio-domain path has no ceiling at all.** `c_clock` outlet 0 is the raw phase as a
*signal*; a filter stage reads it and drives `vline~` envelopes and table reads directly. **Every
number above applies only to the message domain.**

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### Both `threshold~` debounces must be ZERO

⛔ `threshold~` decrements its dead time **once per DSP block, not per millisecond**, so any non-zero
debounce burns a whole 1.45 ms block on every state change. With the obvious-looking `2 ms` the clock
**silently lost pulses above about 430 BPM** — 17 beats where 25 were due at 500 BPM.

**Fix:** zero, both of them. At zero the floor is two blocks per pulse: **344 Hz, which is
44100 / 64 / 2 exactly**, or 860 BPM. A `phasor~` is monotonic and cannot bounce, so there was never
anything for a debounce to protect against.

⚠️ **A `c_clock`'s ratio multiplies that ceiling** — `ratio × tempo` must stay under ~860 BPM
equivalent, so at the 600 BPM clamp the highest safe ratio is about **1.4**.

### The pulse counter resets to 23, not 0

⛔ The next pulse adds one and lands on 0, which is the beat. **Reset it to 0 and the first beat after
every start is silently skipped** — 24 pulses late, once.

**Fix:** reset to 23.

### Never send 251

⛔ Continue means *resume from a stored position*, and nothing in this rig has Song Position Pointer.
Sending it would be a lie that some future device might believe.

**Fix:** `start` → 250, `stop` → 252, and nothing else.

### The clock must keep running when the transport stops

⛔ Stop the stream and the 404 stretches every sample to whatever tempo it **last measured** — so a
stopped clock is a *wrong* tempo rather than no tempo. The Launchpad likewise falls back to a stale
animation rate.

**Fix:** 248 flows whether or not anything is playing; only 250 and 252 mark transport. `panic` sends
252 and leaves the clock running.

### "Audio domain" does not mean sample-accurate MIDI

⚠️ `threshold~` reports on a 64-sample block boundary exactly as `metro` fires on one, so the
~1.45 ms of jitter is unchanged and is not fixable in vanilla Pd. **Anyone who reads "audio domain"
as "sample-accurate MIDI" will waste a day.**

**What it does buy:** a rate change that is phase-continuous and glitch-free, and **one phase that
grain-rate code reads as a signal**, so MIDI clock and grain timing cannot drift apart.

⚠️ **If a filter stage ever converts that phase to bangs, that is the mistake — not the ceiling.**

### A `c_clock` born late is silent unless it seeds itself

⛔ `u_tempo` publishes 120 on the `tempo` bus exactly **once** at load and afterwards only *stores*
what it hears. An instance created later never hears a tempo, and its phasor sits at zero.

**Fix:** `c_clock` seeds its own tempo at load.

### Every other device's clock output must be off

⚠️ The Organelle is clock master. The 404's **MIDI Sync Out** in particular will echo clock back and
create a loop if left on.

### `[midiout]` needs no port creation argument

The question is settled rather than open. `u_tempo` uses the cold-inlet pattern — port into the right
inlet, byte into the left — and item 63 fired a real 404 pad through it.

⚠️ **The obvious experiment is invalid:** Pd 0.49 does not warn about extra creation arguments at
all, so `[midiout 7]` loads silently and a clean syntax check proves nothing either way. Recorded so
the question is not reopened.

## Design

### `u_tempo` is a reference, `c_clock` is a clock

The split exists so that poly-tempo is possible at all. `u_tempo` publishes one master BPM and one
pulse stream; anything needing a beat instantiates its own `c_clock` with its own ratio and time
signature, and a `start` is the only thing aligning instances to each other.

**It stores what it hears and never re-emits**, so there is no loop between `u_tempo` and the bus.
Anything may write `tempo`; only `u_tempo` owns what happens next.

### The 120 is a fallback, not a default

mother pushes the real knob positions at load, so knob 1 usually sets the tempo before the fallback
fires — but **which arrives first is a race**, and it has been seen going both ways. A spigot makes
the fallback publish only if nothing else already has.

### Note-silencing left this file in v0.3

`u_tempo` used to send All Notes Off on channel 33 alone — bank A, **one tenth of the instrument** —
because it was written before any file owned the 404. The device's owner owns its panic.

⚠️ **`u_tempo` still owns the 252**, which is the realtime STOP and reaches every port. What left is
only the note-silencing, which is per-device and per-channel and was never this file's to know about.

### The footer is redrawn on every transport change

`status` is **sticky**, so `panic` sat in the footer until the next tempo message — you could start
the transport, watch the LED go green and the 404 start, and still be told PANIC. Redrawing on every
transport change is not cosmetic.

### Clock is not decorative

It is how the 404 learns tempo for BPM SYNC time-stretch, and how the Launchpad paces its own LED
flash and pulse animations. Stop sending it and both fall back to stale values.

## Open

- ⬜ **Nothing consumes a beat for musical purposes yet.** `u_root`'s `c_clock 1 8` drives the grid's
  bottom row and nothing else; the filter stages, drum mode and sampler that would use the audio-rate
  phase outlet are v0.4. See [plan-v03.md](../../plan-v03.md) §4.
