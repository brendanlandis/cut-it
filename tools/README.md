# Diagnostic patches

Standalone Pd patches for testing the rig. **Not** Organelle patches — they don't use
`mother.pd` and aren't meant to be loaded from the device menu. They run manually over SSH so
that `print` output is visible, which matters because the Organelle launches Pd with `-nogui`
and there is no console otherwise.

All authored by hand in Pd 0.49 format. Do not open them in plugdata — see
[../CLAUDE.md](../CLAUDE.md).

| Patch | What it does |
|---|---|
| `midi-monitor.pd` | Prints incoming notes and CCs with their Pd channel. Use to confirm device channel offsets (device *n* → channel `(n-1)*16+1`). |
| `midi-drive.pd` | Sweeps notes 47–62 on channel 33 to trigger SP-404 pads, and monitors incoming. |
| `lp-monitor.pd` | Puts the Launchpad in Programmer Mode, echoes pad presses back as LEDs, prints velocity and polyphonic aftertouch. |
| `lp-flicker.pd` | Fills the Launchpad with random monochrome noise via per-pad RGB SysEx. Press any pad to toggle grey ↔ blue. Demo, but a working reference for RGB SysEx and `until` loops. |
| `lp-modes.pd` | Lights three pads static / flashing / pulsing — the device's three LED animation modes. |
| `self-wire.pd` + `wire.sh` | **The pattern the real patch needs.** Shows a patch wiring its own ALSA MIDI connections at load time via `[shell]`. |

## Phase 3 — testing the display on hardware

These three load **alongside** a running `mother.pd` + `main.pd` (see *Running one* below).
None of them touches the deployed patch: they only read `oscOut` or push onto `disp`, `err`
and `mode`, exactly as a controller would.

| Patch | What it does |
|---|---|
| `phase3-bench.pd` | **The acceptance run, self-driving.** Fourteen steps, 10 s apart, ~3 minutes. Each prints what it is sending and a **PASS IF** line *before* the screen moves — including the steps whose correct result is that nothing happens, which are otherwise impossible to mark off. Run it in the **foreground** and watch the OLED. |
| `phase3-diag.pd` | Counts rather than dumps. `FRAMES` and `MESSAGES` are cumulative totals printed once a second, so the rate is the gap between lines — expect +10 and +100. Printing every OSC message instead would slow down the thing being measured. |
| `alert-buffer-probe.pd` | ✅ **Answered:** draws into the ALERT buffer (screen 4), `setscreen 4`, waits six seconds, `setscreen 3`. All of it works — but `g_oled` still doesn't use buffer 4, for the reasons in [ref-display.md](../ref-display.md). Keep it as the re-check if that ever gets revisited. |

## `pd-layout-check.py`

Not a patch — a static check on `.pd` files:

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd
```

Reports overlapping boxes, **connections drawn through unrelated boxes**, and content that
extends past the saved canvas size. Exits non-zero on any of them.

Layout is the only structural documentation Pd has, and the failure it was written for is
specific: a comment placed between the logic and a message column gets cords drawn straight
through it, which is invisible until you open the patch. Box sizes are estimated from the text
rather than measured, so it is a smell detector, not a renderer.

The diagnostic patches above predate it and do not pass — they are working references, not
examples of layout.

## Organelle patches

These three **are** Organelle patches — they load `mother.pd` and run from the device menu,
unlike everything above. Deploy with `scp` to `/sdcard/Patches/!/<name>/main.pd`.

| Patch | What it proves |
|---|---|
| `oled-probe/` | The OLED **graphics** API is reachable from a patch via `[s oscOut]`. Measures the font (21 chars, monospace, 8px) and redraws live from knob 1. |
| `osc-bridge/` | Bidirectional OSC between Organelle and an iPhone running PdParty. Sends a heartbeat and `knob1`; draws whatever arrives on `/cutit/fader` big on the OLED. |
| `status-display/` | The performance status protocol: four knobs sending **named parameters** (`chop-size`, `grain`, `speed`, `drunk`) plus a heartbeat. |
| `audio-probe/` | `env~` levels for `adc~ 1` and `adc~ 2` drawn large on the OLED. Used to verify the TRS input split; still the quickest way to check what is arriving at the inputs. |
| `pdparty-scene/CutItRemote/` | The phone side — landscape, big text, link-loss detection. **Not** an Organelle patch: deploy over WebDAV with `curl -T http://<phone>:9000/CutItRemote/_main.pd`. |

Findings from all three are written up in [../ref-display.md](../ref-display.md).

## Running one

```sh
scp tools/lp-flicker.pd root@organelle.local:/tmp/

ssh root@organelle.local
  killall pd 2>/dev/null; sleep 1
  cd /tmp
  nohup pd -alsamidi -midiindev 1,2,3,4 -midioutdev 1,2,3,4 \
        -nogui -noaudio /tmp/lp-flicker.pd > /tmp/out.txt 2>&1 &
  sleep 2
  aconnect 'Launchpad Pro MK3':0 'Pure Data':0    # -> Pd device 1, channels 1-16
  aconnect 'Pure Data':4 'Launchpad Pro MK3':0    # LEDs and SysEx back out
  cat /tmp/out.txt
```

Stop with `killall pd`.

## Things these patches taught us

Findings specific to working *in this folder*. The Launchpad's own behaviour — palette,
animation modes, LED state, `polytouchin` ordering — is catalogued in
[../ref-midi.md](../ref-midi.md). Pd message-discipline traps (`[list trim]`, `route`'s
selector rules, `sendtyped` arity, `quitting`) are in
[../ref-conventions.md](../ref-conventions.md), and the OSC ones in
[../ref-display.md](../ref-display.md).

- **`loadbang` fires before ALSA connections exist.** Initialisation SysEx sent on `loadbang`
  goes nowhere. Use `[loadbang] → [del 2000]` or longer. Repeated here because every patch in
  this folder has to obey it.
- **`aconnect` by name, never by client number.** Client 28 was the Launchpad, then became the
  SP-404 when devices were swapped. Names are stable, numbers are not.
- **`amidi` and Pd cannot both hold a port.** Once ALSA seq has subscribed a device,
  `amidi -p hw:x,y,z` fails with "Device or resource busy". Use `aseqdump`, which coexists.
- **`[random]` takes a bang, not a float.** Feeding it a float errors once per event, which at
  grid-refresh rates produced 2,500 errors/sec.
- **A patch can wire its own `aconnect` calls** via `[shell]`, but put the commands in a shell
  script — Pd message boxes and shell quoting do not mix well.
- **`route` passes the matched message's ARGUMENTS on, and they are rarely what you want next.**
  `route /oled/gClear` emits `ii 3 1` — the typetag and its args. Feeding that to a float inlet
  prints `float: no method for 'ii'` on every message, which at a 10 Hz redraw is an endless
  console scroll. Put `[t b]` in between when you only care that the message happened.

## Phase 4

### `phase4-bench.pd` — the Phase 4 acceptance run

Same shape as `phase3-bench.pd`: self-driving, ten seconds a step, and a printed `PASS IF` for
every step **including the ones whose correct result is that nothing happens**. Load it as a third
patch after `mother.pd` and `main.pd`. Steps 1–14 drive themselves off the `disp`, `err` and `mode`
buses; **15–17 need your hands on the nanoKONTROL**, because nothing but the real controller can
exercise `[ctlin]`.

Step 2 and step 6 are the regression gate on the display rewrite. Steps 7–14 are `phase3-bench`'s
assertions, re-run because the param layer they sit next to was rewritten.

⚠️ **No commas or semicolons in a message box** — both are message separators, so a comma in a
`PASS IF` string splits it and the remainder goes somewhere unhelpful (`canvas: no method for
'then'`). `phase3-bench.pd` says so and it caught this one out too.

## Phase 5

### `phase5-bench.pd` — the Phase 5 acceptance run

Same shape again: self-driving, ten seconds a step, a printed `PASS IF` before each one. Fourteen
steps covering the clock, the transport, the map and the aux LED. **Steps 1–11 drive themselves;
12 and 13 need your hands on the Organelle itself** — the aux button and knob 1 are the only
controls involved, and neither exists on a laptop.

**It finds `c_clock` itself**, through `#X declare -path ../Cut\ It` — the escaped space survives
Pd's parser ✅ — so opening it straight from Pd's File menu works and no `-path` is needed. If the
console ever says `c_clock ... couldn't create`, the two `c_clock` counts will read **0** and mean
nothing, which looks like a dead clock rather than a missing search path.

⚠️ **On the Mac, tick the panel's `enable-DSP` toggle first.** `threshold~` is a signal object,
so with DSP off the beat counters read **0** — which looks exactly like a broken clock. On the
device `mother.pd` turns DSP on 200 ms after load and this does not arise.

Three steps carry the load:

| Step | Proves |
|---|---|
| **3** | 24 PPQN is right, and `c_clock` at ratios 1 and 1.5 gives 20 and 30 beats in 10 s at 120 BPM |
| **9–10** | **the clock keeps running when the transport stops.** A zero here is the bug the step exists for — stop the pulse stream and the 404 stretches to a stale tempo |
| **7** | out-of-range clamps to the 5–600 legal range and warns **once per distinct value** — press the same button twice and the second press must be silent |

### `panic-poke.pd` — the only way to raise a panic on the device

**Nothing on the Organelle sends `panic`.** It has consumers — `u_init`'s safe exit and
`u_tempo` — but the only writers are the bench and the Mac dev panel, so there is no way to
provoke one by hand. This fires `panic` every 25 s as a third patch, and prints what the OLED is
being told (`FOOTER` and `LED`) so the console and the screen can be compared directly.

Written to retest one specific bug: **the footer used to stay on `panic` after the transport had
visibly restarted**. Press aux after a poke — the button must go green *and* the footer must
return to the BPM.

### `midiout-probe.pd` — which half of the MIDI path is broken

Written when the 404 appeared not to follow the clock. It talks straight to the MIDI ports and
touches no Cut It code, so it splits "is Pd emitting?" from "is the device listening?":

| Group | Answers |
|---|---|
| **A** | raw bytes out of `[midiout]` with the port in the cold inlet — **`u_tempo`'s exact mechanism** |
| **B** | the same pad via `[noteout 1]`, which reaches the port by *channel* instead. A dead + B alive = the port inlet is the fault |
| **C** | the same bytes on port 3, which must stay **silent** on a one-output Mac. If it fires, the port inlet is ignored and every byte goes everywhere |
| **D** | a hand-rolled 24 PPQN clock from `[metro]`, sharing no code with `u_tempo`, plus Start and Stop |

✅ **It closed the `[midiout]` port question** (item 63) and then showed the 404 had been following
all along — the wrong number was being read (item 64). **`250` on its own starting the pattern
sequencer is the unambiguous "is it listening" test**; a tempo display is not.

### `fetch-errors.sh` — read the error log back off the device

`u_err` now keeps a persistent log, so an error raised mid-set can be read the next day:

```sh
./tools/fetch-errors.sh              # summary, then detail, newest session first
./tools/fetch-errors.sh --follow     # poll the live session
./tools/fetch-errors.sh --clear      # read it, then truncate (asks first)
HOST=root@192.168.1.15 ./tools/fetch-errors.sh
```

It reads **both** `/sdcard/cut-it-err.log` (every rolled session) and `/sdcard/cut-it-err.cur` (the
one running now, or the last one if the patch has not been reloaded since — the normal case, because
power-cycling the Organelle does not reload the patch). It also md5-compares the deployed patch
against the repo and says so loudly if they differ, because an error from a build you no longer have
is a trap.

### Re-running `m_nano`'s decode test without the hardware

`m_nano`'s decode was verified by swapping `[ctlin]` for a three-outlet stand-in driven by
`nano-ch`, `nano-cc`, `nano-val` **in that order** — which is `ctlin`'s measured firing order made
explicit. To repeat it: copy `Cut It/` aside, replace the `ctlin` line in `m_nano.pd` with a
stand-in abstraction of that shape, and drive it. All 21 cases and the bug it found are recorded in
[plan-tests.md](../plan-tests.md) item 31. The firing order itself is item 23 and needs the real
device.
