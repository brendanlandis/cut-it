<!-- schema: module -->
# The audio chain

**Files:** `Cut It/u_root.pd`, `Cut It/codec-gain.sh` · **Gate:** `test/gate/audio-assert.sh` · **Checklist:** `test/checklists/linecheck.md`

## What it is

**The audio path is wires, on purpose.** `u_root` holds the whole chain on one canvas, laid out
right to left, so it stays something you can read off the screen instead of tracing through send
names — the opposite of how every control path in this patch works, and a deliberate exception.

⛔ **`adc~` and `dac~` appear nowhere in Cut It and must not.** `mother.pd` owns the sound card; the
patch reads `[r~ inL]` / `[r~ inR]` and writes `[throw~ outL]` / `[throw~ outR]` (C-4).

**The drums are alone on one output, and the mic is with the synths and everything else on the
other** (Brendan, 2026-11-14): `c_kit`'s drums on the left, the mixer's channel 1; on the right,
its channel 2, the two inputs, a `[+~]` that sums them, and a second that adds the Pd voices.
**The gap between the inputs and the sum is where v0.4 goes** — `e_chop`, `e_pitch`, `e_trem`,
`e_verb`.

**The levels are mother's** (Brendan, 2026-11-04): the OLED's info bar shows the input and the
output, left and right, as the Organelle does by default, read by mother off the sound card and off
her own `catch~` after the volume knob. Cut It meters nothing itself, and reports no level on
`disp`.

**The audio chip's own gains are Cut It's too.** The factory stages them backwards for noise and
restores that at every boot, so `u_root` re-stages them at every load through `codec-gain.sh`: the
DAC at full scale, the headphone amp down to match, the line input 12 dB quieter.

## Facts

### The I/O contract

| Patch uses | Carries | Evidence | Item |
|------------|---------|----------|------|
| `[r~ inL]` | Input, the **tip** of the input jack: the **mic**, an SM58 on an XLR-to-TS cable, since 2026-11-04 (the Organelle's Reference page) | verified | 11 |
| `[r~ inR]` | Input, the ring: nothing, with a TS plug in the jack | verified | 11 |
| `[throw~ outL]`, `[throw~ outR]` | Everything the patch wants heard, **once each, in `u_root`**: `c_kit`'s drums alone on the left ([sequencer.md](sequencer.md), *The kit*); on the right the input passed through, both contacts summed, with `c_melody`'s Pd voices ([synths.md](synths.md), *The generator*). Proven by `audio-assert.sh`, not yet heard on the rig | unknown | — |

What `mother.pd` does on the other side of those names (its own `adc~` and `dac~`, the volume knob's
square law, the limiter, turning DSP on, the VU meter) is on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`, under *Audio*). Every `throw~` into one
`catch~` is summed (Pure Data, in Reference), so a second stage could throw to `outL` from its own
file with no mixer, and mother's meter would read it, but the chain would stop being one canvas
(*Design*).

### The codec's gains

`codec-gain.sh` sets the S2's WM8731 at every load and echoes what the chip reads back. The chip and
its controls are on the S2's Reference page (`critter-guitari-organelle-s2`).

| Control | Cut It sets | Evidence |
|---------|-------------|----------|
| `Master` | left at the factory's, -2 dB: the chip has no digital volume to stage against | verified |
| `Input Mux` | `Line In`; `Mic Boost` acts only on the Mic input, which this doesn't select | verified |
| `Capture` | 31, its top: +12 dB, the factory's too, set rather than assumed | verified |

Whether a voice has enough level at +12 dB is *Open*.

### At rest

What Cut It sends out with nothing playing, from the code and the Organelle's Reference page:

| Out | At rest | Evidence |
|---|---|---|
| Left | Nothing: `c_kit` adds nothing at rest, since each voice's `switch~` keeps its DSP off except while it sounds, and nothing else reaches the left | unknown |
| Right | Both of the input's contacts passed through at unity: the mic's tip, the input's own hiss (not measured on the S2), and whatever sound reaches the open mic; and the ring, the noise floor of a contact a TS plug grounds | unknown |

Nothing else in the patch makes a sound: there is no oscillator, no stage and no synth inside it,
and the FM-1 and the Streichfett reach the mixer on cables of their own ([rig.md](../rig.md)).
Whether that hiss lights mother's output meter is *Open*.

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### `dac~` is a real bug; `adc~` merely happens to work

⛔ Writing to `dac~` bypasses **both** the volume knob and mother's limiter, and nothing reports it
(the Organelle, in Reference).

**Fix:** `[throw~ outL]` / `[throw~ outR]`, always (C-4).

### A patch must never enable DSP

⚠️ mother turns DSP on itself, just after load (the Organelle, in Reference). A second one is at
best redundant.

**Fix:** leave it alone. `tools/dsp.sh` turns it off on a running patch, for measuring what the
audio engine costs (item 75).

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

### The output is summed in `u_root`, on cords

**Everything Cut It sends out passes `u_root`'s two `throw~`**: `c_kit` hands its drums up an
`outlet~` straight to `throw~ outL`, alone; on the right a `[+~]` sums the input's tip and ring, a
second adds the Pd voices, and that feeds `throw~ outR`. It keeps the audio path something read off
one canvas, and `audio-assert.sh` counts the `throw~` boxes in every file. A private `catch~` of Cut
It's own was the alternative: every stage would throw to it with no cords, at the cost of each one
learning `u_root`'s `$0` as a creation argument, and of the chain no longer being visible as wires.
A stage added later joins the right's sum the way the Pd voices do; the left is the drums' alone.

### The drums are alone on the left, and the mic is with the synths

**Brendan, 2026-11-14: "Drums should be alone and vocals should be with synths and everything
else."** The drums and the mic shared the left output and the mixer's channel 1 until then. Which
side is which was a choice made without him, and his to overrule: the drums stay on the left and
channel 1, where they already were, and the mic moved to the right and channel 2, the Fx channel,
where the Pd voices already were. Each of the mixer's two mono channels has its own EQ and
compressor ([rig.md](../rig.md)), so the drums and the voice now get one each.

### The levels are mother's info bar, and Cut It meters nothing

**Brendan, 2026-11-04: "It should show the output the way the organelle usually shows it by
default, on a single line, and with levels at 0 when nothing is playing."** So the info bar is on
([display.md](display.md)), and its four meters are the levels: in L and R off the sound card, out L
and R off mother's `catch~` after the volume knob, which hears every `throw~` there is. Cut It's
own two bars went, and `u_level` with them, which nothing else used. They were the input's until
that day and the output's for the rest of it, and the gate marks under them, the input's noise
floor and a gate window over it, had gone with the input. **The out meters read after the volume
knob**: turned down, they read less than Cut It sends, as the PA hears it.

### The mic goes straight in, and the drums are Pd's

The mic is the input's tip, with no preamp in front of it: the Organelle 1's own input gain, turned
all the way up, was enough for a voice (its Reference page); on the S2 that is unmeasured (*The
codec's gains*). The drums no longer come
in at all: `c_kit` plays them and `u_root` sends them out the left output, where the 404's
hard-panned drums used to arrive ([sequencer.md](sequencer.md)), and the mic out the right. **No routing depends on a knob position**: cables carry the
paths, and the mixer's knobs only set levels.

### Organelle audio back into the 404 was scrapped

It would have used the mixer's FX SEND as a variable-gain feedback path. Scrapped outright, not
deferred — item 264. The SP-404 has since left the rig altogether (Brendan, 2026-11-04;
[rig.md](../rig.md)).

## Open

- ⬜ **There is no DSP yet.** The chain is input → the sum → output, and the four filter stages,
  the drum mode and the sampler are v0.4. See [plan-v04.md](../../plan-v04.md) §3.
- ⬜ **Whether the mic straight in has enough level on the S2**
  (`cut-it/inbox#check-the-mic-straight-into-the-s2`). On the Organelle 1 an SM58 sung close peaked
  about 3 dB under full scale with +22.5 dB of gain (its Reference page,
  `critter-guitari-organelle-1`, *SGTL5000*); the S2's line input tops out at +12 dB.
- ⬜ **Whether the mic's hiss lights mother's out R meter at rest has not been looked at on the
  device** (`cut-it/inbox#check-the-mic-straight-into-the-s2`): watch the info bar with the mic in
  and the room quiet. By Organelle_OS's `fw_dir/mother.pd` at tag `v4.0`, the Organelle 1's, each
  out meter is `env~ 8192 4096` less 40, over 60, times 11, as a whole number, so its first segment
  needs −54.5 dBFS RMS, 16.5 dB above the Organelle 1's hiss at −71: at rest it should have read 0
  there, and only sound reaching the open mic lit it. The S2's `mother.pd` and its hiss are not read yet.
