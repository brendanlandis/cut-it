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
| `alert-buffer-probe.pd` | Answers the last ⬜ in [plan-display.md](../plan-display.md): draws into the ALERT buffer (screen 4), `setscreen 4`, waits, `setscreen 3`. Only `setscreen` itself is documented; drawing into buffer 4 is inferred. |

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

Findings from all three are written up in [../plan-display.md](../plan-display.md).

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

- **`loadbang` fires before ALSA connections exist.** Initialisation SysEx sent on `loadbang`
  goes nowhere. Use `[loadbang] → [del 2000]` or longer.
- **`aconnect` by name, never by client number.** Client 28 was the Launchpad, then became the
  SP-404 when devices were swapped. Names are stable, numbers are not.
- **`amidi` and Pd cannot both hold a port.** Once ALSA seq has subscribed a device,
  `amidi -p hw:x,y,z` fails with "Device or resource busy". Use `aseqdump` instead, which
  coexists.
- **`[random]` takes a bang, not a float.** Feeding it a float errors once per event, which at
  grid-refresh rates produced 2,500 errors/sec.
- **`polytouchin` emits note before value**, so wiring it straight to `[noteout]` lights a pad
  with the previous event's pressure.
- **Launchpad LED state survives mode switches.** Entering Programmer Mode does not blank the
  grid; the patch has to clear it.
- **Velocity indexes a 128-entry colour palette, not brightness.** For real greyscale or
  arbitrary colour, use the per-pad RGB SysEx: `F0 00 20 29 02 0E 03 03 <pad> <r> <g> <b> F7`.
- **LED animation is free.** Static / flashing / pulsing are MIDI channels 1 / 2 / 3, animated
  by the device — no `[metro]` in Pd. Flashing alternates the ch1 and ch2 colours, so send
  both. Pulsing ramps toward zero, so use a bright palette index or it reads as weak.
- **A patch can wire its own `aconnect` calls** via `[shell]`, but put the commands in a shell
  script — Pd message boxes and shell quoting do not mix well.
- **Syntax-check before deploying.** Pd 0.49-1 is installed on the Mac — the same version the
  Organelle runs. `pd -nogui -noaudio -send "pd quit" main.pd` prints nothing if the patch
  parsed and every object instantiated. `deploy.sh` now does this automatically and refuses to
  copy on any output.
- **There IS a console — launch the patch by hand.** Only the *menu-launched* patch loses its
  stdout to tty1. Running `pd -nogui /root/fw_dir/mother.pd main.pd /tmp/diag.pd` over SSH with
  output redirected gives a real console, live audio on `inL`/`inR`, and lets a throwaway
  `diag.pd` tap any bus with `[print]` without editing the deployed patch. See *Development
  workflow* in [../plan-conventions.md](../plan-conventions.md).
- **`[route]` with symbol arguments matches the SELECTOR, not a list's first element.**
  `[list prepend foo]` produces `list foo …`, which `route foo` rejects — out of the rightmost
  outlet, which is usually connected to nothing. Finish with `[list trim]`. A message box typed
  `foo 42` is already the right shape; anything assembled with `[list …]` is not.
- **`route` emits a lone remaining symbol as a SELECTOR, not a `symbol` message.** Feeding it
  to `[symbol]` errors with `inlet: expected 'symbol' but got 'wiring'`. `[list append]`
  converts it back. This is the mirror of the `[list trim]` rule above — same underlying fact.
- **`route` passes the matched message's ARGUMENTS on, and they are rarely what you want next.**
  `route /oled/gClear` emits `ii 3 1` — the typetag and its args. Feeding that to a float inlet
  prints `float: no method for 'ii'` on every message, which at a 10 Hz redraw is an endless
  console scroll. Put `[t b]` in between when you only care that the message happened.
- **`quitting` is the only shutdown hook.** `mother.pd` sends it and gives the patch 100 ms.
  Pd 0.49 has no `closebang` or `initbang` — both fail to create.
- **`sendtyped` typetags must match the argument count exactly**, or mrpeach `packOSC` drops the
  message with an error. Mixed tags work: `iiiiisi` sends five ints, a label and a value in one
  `gPrintln`.
