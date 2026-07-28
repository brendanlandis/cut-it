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
