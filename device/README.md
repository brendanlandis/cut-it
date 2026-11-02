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
Programmer Mode may be unreachable. See *MIDI: OSS versus ALSA* on
the Organelle's Reference page (`~/Sites/!reference/critter-guitari-organelle-1.md`).

## The `mount.sh` change

**Why:** the Launchpad Pro MK3 presents a 192 KiB write-protected vfat volume alongside its
MIDI interfaces. `mount.sh` takes the *last* `/dev/sd*` and mounts it on `/usbdrive`;
`AppData::getDefaultUserDir()` then makes that read-only volume `USER_DIR`, and
`wifi_control.py` dies opening a log for writing there — hanging the UI at boot. Full chain in
*Booting with a Launchpad Pro MK3 attached* on the Organelle's Reference page (`~/Sites/!reference/critter-guitari-organelle-1.md`).

**The change** — refuse write-protected volumes, since `USER_DIR` exists to be written to:

```sh
BASE=$(basename "$DEVICE" | sed 's/[0-9]*$//')
if [ "$(cat /sys/block/$BASE/ro 2>/dev/null)" = "1" ]; then
    echo "skipping write-protected device ${DEVICE}"
    exit 1
fi
```

⛔ **`mount.sh` runs on EVERY Reload, not only at boot**, so without the guard this appears
mid-session as readily as at power-on. That is why `tools/deploy.sh` sends `/reloadNoRemount`
rather than running `reload.sh` — otherwise every single deploy would trigger it.

✅ **Verified three ways.** With the Launchpad attached, a full `/reload` no longer mounts anything
and `/tmp/user_dir` stays `/sdcard`; a **cold boot** with the Launchpad attached comes up normally
with wifi connected and `/usbdrive` unmounted; and a full deploy leaves `/usbdrive` clear.
✅ Re-verified **hot** on 2026-08-08, which the cold-boot test could not cover — the drive appeared
live and `/usbdrive` still stayed unmounted with `/sdcard` still `rw`.

⚠️ **The blast radius is wider than wifi.** `USER_DIR` is also where `start-ap.sh` reads `ap.txt`
and where the System menu's save paths hang off, so a bad mount breaks Save and AP mode too — the
wifi log is just the first thing to try writing.

**If it ever recurs:** `umount /usbdrive` clears it, no reboot needed.

**To revert:** `cp /root/fw_dir/scripts/mount.sh.orig /root/fw_dir/scripts/mount.sh` with the
rootfs remounted rw, or scp `mount.sh.orig` from this folder.

**Side effect worth knowing:** a genuinely write-protected USB stick will no longer mount as
`/usbdrive`. That is arguably correct here, but it is a behavior change.

⚠️ **Turning the drive off at the Launchpad instead was considered and declined** — it requires a
firmware update that would invalidate every measured fact on the Launchpad's Reference page
(`~/Sites/!reference/novation-launchpad-pro-mk3.md`). Item 265, reasoning on
[ref/device/launchpad.md](../ref/device/launchpad.md).

## Restoring the nanoKONTROL

`REC + STOP + SCENE` held at power-on performs a factory reset and wipes every assignment. If
that happens, load `korg nano kontrol.nktrl_set` in Kontrol Editor 2.4.0 and write it back.
2.5.0 will not see the device — it dropped first-generation nanoKONTROL support.

The expected result is documented in [ref/device/nanokontrol.md](../ref/device/nanokontrol.md); verify against it after
any restore, ideally by decoding the raw stream rather than trusting the editor.


## `/root/Pd/externals` — factory, and on Reference

⛔ **`path1: /root/Pd/externals` in `.pdsettings` is what makes `[shell]`, `packOSC` and `routeOSC`
resolve in a menu-launched patch.** Without it the instrument does not boot: `wire.sh` never runs, so
no MIDI is connected, and `u_net` never loads.

The folder is **entirely factory**, so it is not backed up here: its manifest (every file, its size
and md5) and the one-line check are under *Externals* on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`). `path1` is factory too, and so is
`flags: -alsamidi`; only `midiapi: 1` and MIDI devices 2–4 were added here — see *What was changed
from factory* above.

Cut It depends on **`shell`** directly, and on **`packOSC`** and **`routeOSC`** through `mother.pd`,
which reaches the OLED and the encoder with them. `u_net` uses vanilla `[netsend]`, `[oscformat]`
and `[oscparse]`; the rest of the folder is factory objects Cut It does not use.
