# Device configuration backups

Copies of configuration that otherwise **lives only on hardware and has no other backup**.
Nothing here is deployed — these are restore sources, and a record of what was changed from
factory.

| File | Restores to | Notes |
|---|---|---|
| `pdsettings` | `/root/.pdsettings` on the Organelle | Governs MIDI. `/root` is read-only — run `/root/fw_dir/scripts/remount-rw.sh` first, `remount-ro.sh` after. |
| `korg nano kontrol.nktrl_set` | The nanoKONTROL, via Korg Kontrol Editor **2.4.0** | All 24 control assignments plus the CC 41–46 transport map. Korg's own binary format — **not diffable**, so treat it as an opaque blob and re-export after any change. |
| `OS-VERSION` | — | What `/root/fw_dir/version` reported when this was captured. |

## What was changed from factory

`diff` against the device's own `/root/.pdsettings.bak`:

```
> midiapi: 1                      # added — forces ALSA MIDI
< midiindevname1: /dev/midi3      # removed — OSS device node
> midiindev2: 1
> midiindev3: 2
> midiindev4: 3                   # added — 4 ALSA input devices
< midioutdevname1: /dev/midi3     # removed
> midioutdev2: 1
> midioutdev3: 2
> midioutdev4: 3                  # added — 4 ALSA output devices
```

That is the whole change, and it is what the entire MIDI topology depends on. Without
`midiapi: 1` Pd falls back to OSS, where the Launchpad's three ports collapse into one and
Programmer Mode may be unreachable. See *MIDI: OSS vs ALSA* in
[plan-hardware.md](../plan-hardware.md).

## Restoring the nanoKONTROL

`REC + STOP + SCENE` held at power-on performs a factory reset and wipes every assignment. If
that happens, load `korg nano kontrol.nktrl_set` in Kontrol Editor 2.4.0 and write it back.
2.5.0 will not see the device — it dropped first-generation nanoKONTROL support.

The expected result is documented in [plan-midi.md](../plan-midi.md); verify against it after
any restore, ideally by decoding the raw stream rather than trusting the editor.
