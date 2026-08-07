# Device configuration backups

Copies of configuration that otherwise **lives only on hardware and has no other backup**.
Nothing here is deployed — these are restore sources, and a record of what was changed from
factory.

| File | Restores to | Notes |
|---|---|---|
| `pdsettings` | `/root/.pdsettings` on the Organelle | Governs MIDI. `/root` is read-only — run `/root/fw_dir/scripts/remount-rw.sh` first, `remount-ro.sh` after. |
| `korg nano kontrol.nktrl_set` | The nanoKONTROL, via Korg Kontrol Editor **2.4.0** | All 24 control assignments plus the CC 41–46 transport map. Korg's own binary format — **not diffable**, so treat it as an opaque blob and re-export after any change. |
| `mount.sh` | `/root/fw_dir/scripts/mount.sh` | **Modified from factory** — see below. On-device backup also kept at `mount.sh.orig`. |
| `mount.sh.orig` | — | The factory version, for reverting. |
| `wifi_control.py` | — | Not modified; captured because it is the script the modification exists to protect. |
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
[ref-hardware.md](../ref-hardware.md).

## The `mount.sh` change

**Why:** the Launchpad Pro MK3 presents a 192 KiB write-protected vfat volume alongside its
MIDI interfaces. `mount.sh` takes the *last* `/dev/sd*` and mounts it on `/usbdrive`;
`AppData::getDefaultUserDir()` then makes that read-only volume `USER_DIR`, and
`wifi_control.py` dies opening a log for writing there — hanging the UI at boot. Full chain in
[ref-hardware.md](../ref-hardware.md).

**The change** — refuse write-protected volumes, since `USER_DIR` exists to be written to:

```sh
BASE=$(basename "$DEVICE" | sed 's/[0-9]*$//')
if [ "$(cat /sys/block/$BASE/ro 2>/dev/null)" = "1" ]; then
    echo "skipping write-protected device ${DEVICE}"
    exit 1
fi
```

✅ Verified on hardware: with the Launchpad attached, a full `/reload` no longer mounts
anything and `/tmp/user_dir` stays `/sdcard`.

**To revert:** `cp /root/fw_dir/scripts/mount.sh.orig /root/fw_dir/scripts/mount.sh` with the
rootfs remounted rw, or scp `mount.sh.orig` from this folder.

**Side effect worth knowing:** a genuinely write-protected USB stick will no longer mount as
`/usbdrive`. That is arguably correct here, but it is a behaviour change.

## Restoring the nanoKONTROL

`REC + STOP + SCENE` held at power-on performs a factory reset and wipes every assignment. If
that happens, load `korg nano kontrol.nktrl_set` in Kontrol Editor 2.4.0 and write it back.
2.5.0 will not see the device — it dropped first-generation nanoKONTROL support.

The expected result is documented in [ref/device/nanokontrol.md](../ref/device/nanokontrol.md); verify against it after
any restore, ideally by decoding the raw stream rather than trusting the editor.
