<!-- schema: module -->
# Tempo and clocks

**Files:** `Cut It/u_tempo.pd`, `Cut It/u_tempo.lua`, `Cut It/u_tempo-lua.pd_lua`, `Cut It/cut-it-arrangement-page.txt`, `Cut It/c_clock.pd` · **Gate:** `test/gate/tempo-assert.sh`, `test/gate/clock-assert.sh`, `test/gate/display-assert.sh` · **Checklist:** `test/checklists/tempo.md`, `test/checklists/phone.md`

## What it is

**`u_tempo` is the master REFERENCE, and it is not the clock.** It owns the master BPM, the pulse
oscillator that MIDI clock is cut from, and the transport. Cut It runs **poly-tempo**: every part
that needs a beat owns a `c_clock` instance with its own rate and its own time signature, aligned to
master by a `start`.

`u_root` holds the first instance, `c_clock 1 8` — ratio 1, eight beats to the bar, so its
beat-number outlet indexes the grid's bottom row directly. **Nothing downstream may assume the
global `clock` is its clock**; that instance is the grid's, and the next consumer gets its own:
`c_steps` holds `c_clock 1 4` and cuts its sixteenths from the phase ([sequencer.md](sequencer.md)).

`u_tempo` has no creation arguments. It talks on `tempo`, `clock`, `start`, `stop`, `panic`,
`disp` and `err`, and out of **two** MIDI ports — port 1 carries the clock and the transport, and
port 4 takes `panic`'s STOP alone. **Port 3 gets nothing**: it was the SP-404's, which left the rig
on 2026-11-04 (Brendan). **Its inlet takes what sets the tempo from a pad or a screen** — `tap`,
from `u_map`'s tap pad on page 1, `rush <x> <live>`, knob 4, from its `rush` destination, `tempo <bpm>`, the phone's, from `u_net`, and `fast <1 or 0>`, the
500 BPM repeat, from `c_steps` — and writes the bus itself; **its outlets** hand the master BPM, clamped, to `u_net` for the phone, `tap` to
`g_grid` to flash the pad, and the BPM a tap or the phone set to `u_map`, which holds knob 1 there
(Brendan, 2026-11-04). The tap's rules are Lua, `u_tempo.lua`; the
timer between taps, the clock and the transport are Pd. **The tempo is a part of every section of
the song** ([songs.md](songs.md)): `u_tempo` puts every BPM the bus carries with the section policy,
and takes a section's restore as it takes the phone's tempo.

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
| `start` | 250, on port **1** | verified | — |
| `stop` | 252, on port **1** | verified | — |
| `panic` | 252 on ports **1 and 4**, plus the aux LED. **Note-silencing is each device layer's own** | verified | 231, 295 |

⛔ **`panic` reaches one more port than the transport does, and that asymmetry is the point.** Port 4
is the Volca's DIN interface, and item 279 measured it receiving nothing at all — so a Volca
sequencing through a panic kept sequencing. It is fed from `$0-rt4`, a receive the panic branch is
the **sole writer of**, so no clock byte can reach it however this file is edited later.
⚠️ **Widening the CLOCK to more ports is a different question** and stays in
[plan-v04.md](../../plan-v04.md) §3: the Launchpad ignores incoming clock in Programmer Mode, so the
one port fed is pointless while it is in that mode, and which devices Cut It intends to *drive* is a
v0.4 sound decision. `tempo-assert.py` asserts the clock's port and both STOPs' **exactly**, because
a check for either STOP alone passes over the bug in the other direction, and an exact set is what
keeps port 3 empty.

### How the clock is built

| Stage | Detail | Evidence | Item |
|-------|--------|----------|------|
| BPM ÷ 60 × 24 → `[phasor~]` at the pulse rate | 48 Hz at 120 BPM | verified | 48 |
| `[threshold~ 0.5 0 0.1 0]` → one bang per cycle | The phasor crosses 0.5 once per ramp and falls below 0.1 on the wrap | verified | 48 |
| Every pulse emits 248 and increments a counter | `[mod 24]` = 0 is the beat, published on `clock` | verified | 48 |
| Out on Pd MIDI port **1** | The Launchpad (`Pure Data:4`), in `wire.sh`. Port 3 (`Pure Data:6`) carried it to the SP-404 until the 404 left the rig | verified | — |

**Counting the pulses rather than running a second oscillator is what makes the beat and the MIDI
pulse the same clock by construction.** Measured under real DSP: 6 beats in 3 s at 120 BPM, 3 in 3 s
at 60.

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Control range | **10–1000 BPM** from knob 1 (Brendan, 2026-11-05), on a curve that gives 50–200 BPM the middle of its turn, 9 o'clock to 3 o'clock (`tempo` in [map.md](map.md)) | verified | — |
| Legal range | **5–1000 BPM**, clamped | verified | — |
| Outgoing jitter | **~1.45 ms** — Pd emits on 64-sample block boundaries, about 7% of a pulse interval at 120 BPM. Not fixable in vanilla Pd | verified | — |
| Start alignment | Within **half a pulse** — `threshold~` fires at phase 0.5, so the first pulse after a start arrives ~10.4 ms later at 120 BPM. A constant offset shared by every clock in the patch | verified | — |
| The port | Set into `[midiout]`'s **cold inlet at load**, `u_init`'s proven pattern. A nonexistent port is silently dropped, so a port the Mac lacks costs nothing and prints nothing | verified | 63 |

The control range and the legal range are **different decisions**, and the legal one is wider at both
ends so a test, a tap tempo or an LFO is not limited by what one knob chose. The tap pad and the
phone use the legal range, and keep to it before anything reaches the bus.

### Tap tempo, and the phone's tempo

| | | Evidence |
|---|---|---|
| The tap pad | Page 1's cell 21, the second row's first pad, above the beat row's first (Brendan, 2026-11-04): `mode-1 pad-21 arrangement 21` in the map, and `21 tap` in `cut-it-arrangement-page.txt`, which `g_grid` paints from and `u_map` reads to know what a press means ([map.md](map.md), [display.md](display.md)). A press sends `tap` to `u_tempo`; a release nothing | unknown |
| A tap | `[timer]` measures the interval since the last, and `u_tempo.lua` takes it. The first tap after load, or one **two seconds** or more after the last, starts the count and sets nothing; every tap after it sets the tempo from the average of the last **four** intervals, whole BPM, clamped to 5–600 (Brendan, 2026-11-04) | unknown |
| Two taps in one instant | Count nothing, and keep the count | unknown |
| The flash | Every tap, the first included, lights the pad full for 120 ms; it sits dim otherwise | unknown |
| The phone's `tempo <bpm>` | Whole BPM within 1–1000 on the bus; anything but a number is `fail u_tempo bad-tempo` and sets nothing. It leaves a count of taps alone | unknown |
| Outlet 1 | Every BPM the bus carries, clamped, from `$0-bpm`: knob 1's, a tap's, the phone's, a Send line's. `u_net` sends it to the phone as `/cutit/tempo`, the tempo's only display at rest (*Design*) | unknown |
| On page 2 | Cell 21 is a drum pad, and taps there set nothing: the map's row is page 1's alone | unknown |
| Outlet 4 | `rush <0-1>`, how far knob 4 is past the handoff, and `rush-off`: to `c_steps`'s inlet (*Knob 4 races the tempo*) | unknown |
| Knob 1 | **Held at the new tempo after a tap or the phone moves it**, until it is turned to or through that tempo (Brendan, 2026-11-04): until then a turn moves nothing and its row reads the tempo in force with the knob's own in brackets, `bpm 150 (105)`. Outlet 3 carries the BPM to `u_map`, whose pickup arms the knob at where its curve puts it (*Design*). A tempo past the knob's 10 to 500 holds it at the end of its turn, so its row reads that end, 10 or 500, not the tempo | unknown |
| Outlet 3 | The BPM a tap, the phone, a section or the 500 BPM repeat set, whole and clamped, after the Lua and before the bus: to `u_map`'s inlet. Knob 1's own tempo, a Send line's and the fallback 120 do not come out of it | unknown |
| `pad-38` under rush | `rush-home`, from `c_steps`, before it asks for the saved tempo: rush is over and both knobs held where the bus is, and the BPM that comes back holds them again (*Knob 4 races the tempo*) | unknown |
| The 500 BPM repeat | `fast 1`, `pad-35` pressed, through `c_steps`: the BPM in force, kept in a box beside the route and added to the message so no BPM of a sweep calls the Lua, is kept and 500 goes out of the Lua as a tap's does, so knob 1 is held at the end of its turn until it reaches 500. `fast 0`, let go: the BPM kept goes out the same way, knob 1 held there, whatever the knob or the phone set meanwhile (Brendan, 2026-11-05). In between nothing the bus carries is put in the section. A section's restore in between changes nothing heard, and becomes the BPM kept | verified |
| A section's tempo | `put section tempo <bpm>` for every BPM the bus carries, clamped; a section's `restore tempo <bpm>`, or the saved tempo's from `pad-38` ([songs.md](songs.md)), goes to the Lua as `restored`, as the phone's tempo does, so it reaches the bus whole and within 5 to 600, holds knob 1, and is put straight back. A restore of the tempo already in force is dropped by a spigot, so a section starting at the same tempo leaves knob 1 alone | unknown |

`tempo-assert` taps 400 ms apart through the running instrument and reads 150 on the bus, turns
knob 1 short of 150 and reads nothing and `bpm 150 (105)`, then through it, waits 2.5 s and reads
nothing, and sends the phone's tempo through `u_net`'s socket and finds knob 1 held at it;
`test/gate/lua/u_tempo_test.lua` holds the arithmetic, and reads the `[clip 1 1000]` out of
`u_tempo.pd` so the Lua's range cannot drift from it.

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
| Instant jump | Takes several pulses to propagate. Large ones can make slaved gear **stutter or briefly drop sync** | verified | — |

⚠️ **So internal and external timing diverge under fast modulation.** The Organelle's own grain
clocks are `phasor~`-based — a frequency change is instant and glitch-free, and the phase simply
continues. Slaved gear lags several pulses behind. **Modulate tempo quickly and the Organelle is
somewhere slaved gear has not reached yet.**

### The three rate ceilings

⚠️ **These get confused with each other constantly.** They stack, and the one that bites is whichever
is lowest on the path you are actually using.

| Ceiling | Value | What it limits | Evidence | Item |
|---------|-------|----------------|----------|------|
| `threshold~` pulse | **344 Hz** = 44100/64/2 | The raw 24 PPQN pulse | verified | 58 |
| `c_clock`'s **bang** outlet | **14.3/s** = 344 ÷ 24 | Beat bangs. The ×24 that buys provable alignment costs a factor of 24 in headroom | verified | 58 |
| Pd's own wall | ~689/s | One message per 64-sample scheduler tick, a compile-time constant. **Never reached** — something downstream saturates first | verified | — |

### What the clock actually costs, isolated

⛔ **The clock's cost is DSP, not its ALSA MIDI writes** — 96 a second when this was measured, on two
ports. Toggling DSP on a running
patch settles it:

| | pd CPU | Evidence | Item |
|---|--------|----------|------|
| DSP on | **11.8 / 11.7 / 11.8 %** | verified | 75 |
| DSP off | **4.9 / 4.9 / 4.9 %** | verified | 75 |
| DSP back on | **12.0 / 11.8 %** | verified | 75 |

**So ~7 points are the audio engine and the MIDI rate is not it** — varying tempo moves the MIDI rate
while leaving DSP cost identical. `tools/dsp.sh` is what performs the toggle.

⛔ **No clock-driven path can produce an audio-rate MIDI stream.** At 14.3 bangs/s, `c_clock` is
the lowest ceiling here by a factor of 24. A dense machine-gun trigger stream needs a plain
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
equivalent, so at 1 it holds to about 860 BPM. Above that, up to the 1000 BPM clamp, the MIDI clock's pulses drop (284 a second at 1000, 400 asked for): nothing follows them now, and the steps are cut from `c_steps`' own clock, which keeps up.

### The pulse counter resets to 23, not 0

⛔ The next pulse adds one and lands on 0, which is the beat. **Reset it to 0 and the first beat after
every start is silently skipped** — 24 pulses late, once.

**Fix:** reset to 23.

### Never send 251

⛔ Continue means *resume from a stored position*, and nothing in this rig has Song Position Pointer.
Sending it would be a lie that some future device might believe.

**Fix:** `start` → 250, `stop` → 252, and nothing else.

### The clock must keep running when the transport stops

⛔ Stop the stream and a device following it keeps whatever tempo it **last measured** — so a
stopped clock is a *wrong* tempo rather than no tempo. The Launchpad falls back to a stale animation
rate, as the SP-404 stretched its samples while it was in the rig.

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

⚠️ The Organelle is clock master. A device that sends clock of its own — a **MIDI Sync Out** left
on — echoes it back and makes a loop.

### `[midiout]` needs no port creation argument

`u_tempo` uses the cold-inlet pattern — port into the right inlet, byte into the left — and item 63
fired a real 404 pad through it.

⚠️ **The obvious experiment is invalid:** Pd does not warn about extra creation arguments at all,
0.49 or 0.57, so `[midiout 7]` loads silently and a clean syntax check proves nothing either way. Recorded so
the question is not reopened.

## Design

### Tap tempo is `u_tempo`'s, in Lua

**The tempo's owner takes the taps**, the way it takes the bus: a pad's taps mean a tempo, and only
`u_tempo` holds the legal range and writes what follows. `u_map` says which pad taps, from a layout
file `g_grid` paints from, as the synth pads do; `u_tempo` turns the taps into a BPM. **The
arithmetic is Lua** — the last four intervals, a gap that starts over, the clamp — a dozen lines
tested without Pd, where Pd would need a list kept by hand; a tap is a few a second, so the 0.1 ms a
call costs on the Organelle is nothing. The interval stays Pd, a `[timer]` on logical time, so the
Lua never asks Pd the time. A Lua that never loads says `fail u_tempo no-lua`, and the clock, the
clamp and the transport, which are Pd, run on.

**The phone's tempo comes in on the same inlet** and goes out on the bus from `u_tempo`, so nothing
from the phone writes a bus by itself ([phone.md](../device/phone.md)), and the one clamp the bus
sees from a screen is the Lua's, the same as a tap's.

### Knob 1 waits for a tapped or phoned tempo

**A tap or the phone sets the tempo, and knob 1 is held there until it is turned through it**
(Brendan, 2026-11-04), as `c_steps` holds knob 2 when the phone sets the last step
([sequencer.md](sequencer.md)). Without it the knob's next turn jumped the tempo back to
wherever the knob happened to sit. The hold is `u_map`'s pickup, which already holds a restored
knob until it crosses: `u_tempo` hands the BPM out of its Lua, before the bus, on a cord to
`u_map`, and the Lua arms every knob the page maps to `tempo` at the BPM's place on the curve
(`R.tempo_position`, the curve's inverse). Armed, the knob's first value decides the side it waits
on, and the held row is `c_mapped`'s, as for a restore. **It is a cord and not the bus** because
the bus cannot say who wrote a tempo, and knob 1's own tempo must not hold knob 1; nothing on the
cord reaches the bus, so there is no loop.

### Knob 4 races the tempo, off the record

**Rush** (Brendan, 2026-11-05) is `u_tempo.lua`'s `R.rush`: an absolute rate over the knob's whole turn,
`330000 ^ x` BPM, 1 BPM at the bottom, 330000 being 22 kHz as a one-step loop's BPM. It has no neutral
spot, and `pad-38` is the way home. **Below the handoff, 1000 BPM, it is the tempo**, as the 500 BPM
repeat's is: not put in the section's draft, so the lamps stay as they are, but out a Lua outlet of its own
straight to the bus. **Past the handoff** the bus stays at 1000, so the next step, which ends the loop, is
at most 15 ms off, and how far past goes to `c_steps` instead ([sequencer.md](sequencer.md), *Rush*). Coming
back it hands over at 980, so a knob resting on the handoff does not capture over and over, a place on the
knob being 1.2% of rate.

**The latch is knob 1's rule.** Knob 4 is held until turned to or through where the tempo in force stands
on its curve, and held at load, at `u_tempo`'s own 120, whatever `knobs.txt` says and after a recover too;
its row reads `rush 120 (574)`, the tempo with the knob's own rate in brackets, in thousands past four
figures. **Whichever knob moved last wins and the other doesn't jump:** a knob 4 move holds knob 1 at that
tempo, or at 1000 past the handoff, and knob 1 going live holds knob 4 at its tempo, and `u_map` tells rush
it is over before knob 1's BPM goes, so that BPM is put. **Anything else that sets the tempo ends rush and
holds both knobs there**: a tap, the phone, a section's restore, `pad-35` pressed or let go, and `pad-38`,
which tells `u_tempo` before it asks for the saved tempo, so it ends rush even if the restore that follows
is of the tempo on the bus, which the spigot drops. The loop stops, the put opens, and then the tempo goes,
so that one is in the draft as ever. Under `pad-35` the put stays shut until it is let go.

### `u_tempo` is a reference, `c_clock` is a clock

The split exists so that poly-tempo is possible at all. `u_tempo` publishes one master BPM and one
pulse stream; anything needing a beat instantiates its own `c_clock` with its own ratio and time
signature, and a `start` is the only thing aligning instances to each other.

**It stores what it hears and never re-emits**, so there is no loop between `u_tempo` and the bus.
Anything may write `tempo`; only `u_tempo` owns what happens next. What it writes itself is the
fallback 120, a tap's BPM and the phone's, each once, and each heard back as any writer's is.

**Cut It runs multiple simultaneous tempi**, and this is the page that says what that commits every
other module to. Sequencers and samplers may deviate from master — a different BPM, or ms-based
timing instead of beat-based — and different parts of a drum sequence may run different time
signatures. **The `clock` bus in C-2's allowlist must not be read as implying one tempo and one
beat.**

- **`tempo` and `clock` are the master reference**: what MIDI clock out is derived from, and what
  parts *may* choose to follow. Nothing is obliged to.
- ⛔ **Timing is per-instance, and nothing downstream may assume the global `clock` is its clock.**
  Each grain clock, sequencer and sampler owns a `c_clock` with its own rate, optionally slaved to
  master by a ratio.
- **Time signature is a `c_clock` concern** — bar length, accent pattern — not a global.
- *Normalize BPM and ms to Hz at the edge, feed one `phasor~`* generalizes cleanly: N clocks is
  N `phasor~` objects, and ms-based versus beat-based parts stop being a special case (C-11).

**MIDI clock carries exactly one tempo**, so a device that follows it always follows master. Poly-tempo
is internal-only for anything leaving the box — which reinforces rather than contradicts the "Pd
sequences everything, timing rides in note events" decision in
[architecture.md](../architecture.md).

⛔ **So `u_tempo` must be a master reference *plus* an instantiable `c_clock`, never a singleton.**
The cost of getting that wrong is tracked as a standing risk in [plan-v04.md](../../plan-v04.md).

### The 120 is a fallback, and with nothing Saved the tempo

After a Save, mother pushes knob 1's saved position at load, so knob 1 usually sets the tempo before
the fallback fires — but **which arrives first is a race**, and it has been seen going both ways. A
spigot makes the fallback publish only if nothing else already has.

**With nothing Saved, the 120 is the tempo** (Brendan, 2026-11-04): `u_map` holds knob 1 at 120
until it is turned through it, so nothing else writes `tempo` and the fallback fills the silence
([map.md](map.md), *Parameter pickup*). The hold's 120 and this one are the same number in two
files, `u_map.lua`'s `R.UNSAVED` and `u_tempo.pd`'s message box, and `u_map_test.lua` checks they
agree.

### Note-silencing is each device layer's own

An All Notes Off from here could only ever reach the channels this file knows about — one channel of
a device's several, say — and which channels a device has is its owner's business. The device's
owner owns its panic.

⚠️ **`u_tempo` owns the 252**, the realtime STOP, and nothing per-device. Which ports it reaches is
counted under *Transport* above.

### The tempo is the phone's to show

**The tempo lives on the phone** (Brendan, 2026-11-04): its arrangement screen draws outlet 1's BPM,
and the OLED draws the tempo only as knob 1's row, `bpm 120`, while the knob moves
([display.md](display.md), *Nothing at rest but the levels*). So `u_tempo` writes nothing on `disp`
but the aux LED's states. It drew the BPM into `g_oled`'s footer until then, redrawn at every start
and stop so a `panic` there would not outlive a restart, and handed over from `u_init`'s ready line
by a 4000 ms delay coupled to the boot's stages; all three went with the footer.

### Clock is not decorative

It is how the Launchpad paces its own LED flash and pulse animations, as it was how the SP-404 learned
tempo for BPM SYNC time-stretch while it was in the rig. Stop sending it and it falls back to stale
values.

## Open

- ⬜ **Nothing consumes a beat for musical purposes yet.** `u_root`'s `c_clock 1 8` drives the grid's
  bottom row and nothing else; the filter stages, drum mode and sampler that would use the audio-rate
  phase outlet are v0.4. See [plan-v04.md](../../plan-v04.md) §3.
