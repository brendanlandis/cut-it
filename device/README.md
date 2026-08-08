# Device configuration backups

Copies of configuration that otherwise **lives only on hardware and has no other backup**.
Nothing here is deployed — these are restore sources, and a record of what was changed from
factory.

| File | Restores to | Notes |
|---|---|---|
| `pdsettings` | `/root/.pdsettings` on the Organelle | Governs MIDI. `/root` is read-only — run `/root/fw_dir/scripts/remount-rw.sh` first, `remount-ro.sh` after. |
| `korg nano kontrol.nktrl_set` | The nanoKONTROL, via Korg Kontrol Editor **2.4.0** | All 24 control assignments plus the CC 41–46 transport map. Korg's own binary format — **not diffable**, so treat it as an opaque blob and re-export after any change. |
| `wifi-watch.service` | `/etc/systemd/system/wifi-watch.service`, then `systemctl daemon-reload && systemctl enable wifi-watch.service` | **Added, not factory.** Starts the wifi watcher at boot so a recovery stops disarming the detection for the next failure (item 244). `/` is read-only — `remount-rw.sh` first, `remount-ro.sh` after, because `enable` writes a symlink. |
| `mount.sh` | `/root/fw_dir/scripts/mount.sh` | **Modified from factory** — see below. On-device backup also kept at `mount.sh.orig`. |
| `mount.sh.orig` | — | The factory version, for reverting. |
| `wifi_control.py` | — | Not modified; captured because it is the script the modification exists to protect. |
| `OS-VERSION` | — | What `/root/fw_dir/version` reported when this was captured. |
| `pdsettings.orig` | — | The **factory** `/root/.pdsettings`, copied from the device's own `.pdsettings.bak`. The missing half of the `mount.sh` / `mount.sh.orig` pair. |

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
[ref/device-os.md](../ref/device-os.md).

## The `mount.sh` change

**Why:** the Launchpad Pro MK3 presents a 192 KiB write-protected vfat volume alongside its
MIDI interfaces. `mount.sh` takes the *last* `/dev/sd*` and mounts it on `/usbdrive`;
`AppData::getDefaultUserDir()` then makes that read-only volume `USER_DIR`, and
`wifi_control.py` dies opening a log for writing there — hanging the UI at boot. Full chain in
[ref/device-os.md](../ref/device-os.md).

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


## `/root/Pd/externals` — a manifest, not a copy

⛔ **`path1: /root/Pd/externals` in `.pdsettings` is what makes `[shell]`, `packOSC` and `routeOSC`
resolve in a menu-launched patch.** Without it the instrument does not boot: `wire.sh` never runs, so
no MIDI is connected, and `u_net` never loads.

⚠️ **It is entirely FACTORY.** Every file is dated 12 Feb 2020 and nothing in this project added to
it — so what is recorded here is a manifest rather than 900 KB of binaries, half of which is one
shared library. If the card is ever rebuilt, an OS 4.0 image restores these; this table is how you
check that it did, and that nothing has quietly changed underneath the patch.

⚠️ **`path1` is factory too**, and so is `flags: -alsamidi`. Only `midiapi: 1` and MIDI devices 2–4
were added here — see *What was changed from factory* above.

```sh
ssh root@organelle.local 'cd /root/Pd/externals && md5sum * | sort -k2'
```

| File | Bytes | md5 |
|---|---|---|
| `abl_link~.pd_linux` | 36452 | `193e6e847a051bcf4ace41b234346d72` |
| `libabl_link~.so` | 536588 | `04ffd8e36326d4553da44a95ec1b9660` |
| `override.pd` | 1390 | `b5f173272640603fdede5152c2d1d3b7` |
| `override2.pd` | 2205 | `b5353c17cfc838d5026744b66b1c6d6d` |
| `packOSC-help.pd` | 3870 | `53c0084acff46652d5dabe33074bf808` |
| `packOSC.pd_linux` | 67432 | `cbf159c7d10e9b074bafe526b0d223d9` |
| `pvu~-help.pd` | 3755 | `12771216e2054331380a5b9386eb1019` |
| `pvu~.pd_linux` | 16568 | `9452a48977a4da46792e2fb90a418c90` |
| `routeOSC-help.pd` | 3737 | `bab0dfe82a12bbf16f9ef5904d3d526a` |
| `routeOSC.pd_linux` | 28600 | `c3850945014d4735884c85a64fe530a3` |
| `shell-help.pd` | 1744 | `fdedd5e5e0d95390e6ede5f3a7934d80` |
| `shell.pd_linux` | 26032 | `2ddd98417e34bd99aafe526595c7ec0d` |
| `slipdec-help.pd` | 2771 | `8125dd5970d70c1cd6bcbb2f51b17520` |
| `slipdec.pd_linux` | 6484 | `0198580ade8529c6bd4b8d92bce69091` |
| `slipenc-help.pd` | 3272 | `bf9278a3552670249ec215406b90041b` |
| `slipenc.pd_linux` | 4704 | `6d6462f5c65f7f36abd28c049f3bf4bd` |
| `tb_peakcomp~-help.pd` | 2482 | `8ab5aacdb3d8c0e312561a24b18f242d` |
| `tb_peakcomp~.pd_linux` | 18500 | `5de930bab644e0b18b128f8f68d88689` |
| `udpreceive-help.pd` | 2001 | `a6916551543399609081be4be49bd4b1` |
| `udpreceive.pd_linux` | 26024 | `f7f9cf926c3bf4c868d2333b0a1d542c` |
| `udpsend-help.pd` | 2410 | `ee1037f363c5754e39ffed47f7a4ee2e` |
| `udpsend.pd_linux` | 32116 | `8c8317a48312dae4e891b95c697c8b94` |
| `unpackOSC-help.pd` | 1915 | `f0ceb02230084f623880e382d6b9c58e` |
| `unpackOSC.pd_linux` | 33724 | `731ad548c147ff7bd4d05c91702b4b07` |

`abl_link~` and `libabl_link~.so` are Ableton Link, `pvu~` a VU meter, `tb_peakcomp~` a compressor —
factory objects Cut It does not use. The four this instrument depends on are **`shell`**,
**`packOSC`**, **`routeOSC`** and, through `u_net`, **`udpsend`**.
