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
| `usr-bin-pd` | `/usr/bin/pd` on the Organelle, mode 755 | **Modified from factory** — the launcher that runs Pd 0.57, where the factory 0.49 binary was. That binary is kept on the device as `/usr/bin/pd-0.49`; see below. |
| `wifi_control.py` | — | Not modified; captured because it is the script the modification exists to protect. |
| `OS-VERSION` | — | What `/root/fw_dir/version` reported when this was captured. |
| `pdsettings.orig` | — | The **factory** `/root/.pdsettings`, copied from the device's own `.pdsettings.bak`. The missing half of the `mount.sh` / `mount.sh.orig` pair. |
| `pd-libs/` | `/sdcard/PdExtraLibs/pdlua` and `/sdcard/PdExtraLibs/else` on the Organelle, and `~/Library/Pd` on the Mac | **Added, not factory.** How pdlua and ELSE were built for Pd 0.57 on the device, and the check that a patch still loads beside them; see *Lua and ELSE* below. |

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

## The `/usr/bin/pd` change

**Why:** Cut It runs Pd 0.57 from 2026-11-03, and the `mother` binary launches Pd by a path compiled
into its launch line, `( cd /tmp/patch ; /usr/bin/pd %s "%s" main.pd )&`, so that path is where the
change has to be. 0.57 is installed on the writable card, at `/sdcard/pd-0.57-0`; the factory binary
(`Pd-0.49.0, compiled Oct 9 2018`) was moved to `/usr/bin/pd-0.49`, and `/usr/bin/pd` became
`usr-bin-pd`, a script that execs 0.57 and falls back to the factory 0.49 if the 0.57 binary is
missing. Root is mounted read-only again afterwards. How 0.57 was built, and what it was checked
against, is on Reference (`~/Sites/!reference/pure-data.md`, *Newer versions on the Organelle*).

✅ The script here is the device's, read back after the switch. 0.57 passed a supervised test on the
rig on 2026-11-03: clean audio, screen, grid and MIDI, nothing logged, and 11.2% CPU against 0.49's
12.2% with the drum machine playing.

**The fallback is automatic:** with `/sdcard/pd-0.57-0/bin/pd` missing or not executable, the next
patch load runs 0.49 with no change to `/`.

**To revert** to the factory Pd, which also removes the script:

```sh
/root/fw_dir/scripts/remount-rw.sh
mv /usr/bin/pd-0.49 /usr/bin/pd
/root/fw_dir/scripts/remount-ro.sh
```

The next patch load runs 0.49. To switch again, the same remount around moving `/usr/bin/pd` back to
`/usr/bin/pd-0.49` and copying `usr-bin-pd` in as `/usr/bin/pd`, mode 755. The 0.49 binary itself is
not kept here: an OS 4.0 image restores it.

## Lua and ELSE

**Why:** the sequencer's rules run in Lua inside Pd, through the pdlua external
([ref/module/sequencer.md](../ref/module/sequencer.md)), and ELSE's objects may replace hand-built
parts. The Organelle ships neither, and current builds of both need Pd 0.56 or later, so both are
built on the device against Cut It's 0.57. They live in `/sdcard/PdExtraLibs`, which `mother`'s own
launch line puts on Pd's path (`-path /sdcard/PdExtraLibs`), so a patch finds them with no change to
`/`. What each one is on the device, what it costs and what is missing: the Organelle's Reference
page (`~/Sites/!reference/critter-guitari-organelle-1.md`, *Externals*).

| On the device | What | Built by |
|---|---|---|
| `/sdcard/PdExtraLibs/pdlua/` | pdlua 0.12.24, Lua 5.4.7 compiled in | `pd-libs/build-pdlua.sh`, ~5 min at `nice 19` |
| `/sdcard/PdExtraLibs/else/` | ELSE 1.0-0 rc14: 325 of its 332 externals, its abstractions and help files | `pd-libs/build-else.sh` with `pd-libs/Makefile.else` |

**Sources:**

| File | From |
|---|---|
| `pd-lua-0.12.24.tar.gz` | `github.com/ben-wes/pd-lua/archive/refs/tags/0.12.24.tar.gz`: a fork, since upstream's 0.12.23 fails on 0.57 |
| `lua-v5.4.7-git.tar.gz` | `github.com/lua/lua/archive/refs/tags/v5.4.7.tar.gz`: pdlua's `lua/` submodule, which a GitHub archive leaves empty |
| `lua-5.4.7.tar.gz` | `www.lua.org/ftp/lua-5.4.7.tar.gz`: the `lua` interpreter, for the Lua tests on the Mac |
| `pd-else-rc14.tar.gz` | `github.com/porres/pd-else/archive/refs/tags/v.1.0-rc14.tar.gz` |

The files built from on 2026-11-03, as `sha256sum -c` reads them (`build-pdlua.sh` checks its three):

```
7c14cf9cddc7722b33e85dc63862452caef6ed145e1259b6b7694a801ca9d626  pd-lua-0.12.24.tar.gz
5c39111b3fc4c1c9e56671008955a1730f54a15b95e1f1bd0752b868b929d8e3  lua-v5.4.7-git.tar.gz
9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30  lua-5.4.7.tar.gz
ad725a4bc9a50a1b9071cf2f97a30b29910ac22ee5fbc92db999d5fcaaaffd91  pd-else-rc14.tar.gz
```

**One change from upstream pdlua:** `build-pdlua.sh` moves the three lines it prints when it loads
to Pd's `-verbose` level. Cut It's entry points must load in silence, since `tools/deploy.sh` and the
suite take any output as a failure, and those lines would be the only output.

**pdlua on its own, not ELSE's copy.** ELSE carries a modified pdlua 0.12.23 inside its `[else]`
library binary, which works, but loading it loads the whole library: ~35 lines of banner at every
load, a GUI plugin installed, and Cut It's Lua tied to ELSE's release candidates. pdlua alone is one
~400 KB binary that loads quietly once the banner moves.

**ELSE's build:** rc14's own needs CMake 3.15 and OpenSSL 3, which the device lacks, so
`Makefile.else` mirrors its `CMakeLists.txt` target by target and gives every external the
`.pd_linux` suffix any Linux Pd loads. Built 2026-11-03 under `/sdcard/libs-trial`, the paths both
files still name (`T` in the script, the `?=` defaults in the Makefile). Missing, and why: `play.file~`,
`sfload` and `sfinfo` need FFmpeg, and the four abstractions built on them with them (`player~`,
`gran.player~`, `pvoc.player~`, `sample~`); `circuit~`, `pdlink`, `pdlink~` and `sfz~` didn't build
with gcc 5.2.

**Installing on the device**, with the tarballs and `pd-libs/` copied to `/sdcard/libs-build` and the
Pd 0.57 source tree the device was built from in `/sdcard/pd-build`:

```sh
cd /sdcard/libs-build
nohup nice -n 19 ionice -c3 bash build-pdlua.sh /sdcard/libs-build \
    /sdcard/pd-build/pd-0.57-0/src /sdcard/PdExtraLibs > build-pdlua.log 2>&1 &
# ELSE: build-else.sh as above, then
cp -a /sdcard/libs-trial/else /sdcard/PdExtraLibs/else
sh loadcheck.sh "/sdcard/Patches/!/Cut It/main.pd"
```

⚠️ **Both builds cap their own memory** (`ulimit -v`, `oom_score_adj 1000`), as must anything else
run beside the live Pd: one test Pd ran the device out of memory on 2026-11-03.

**`loadcheck.sh`** loads patches in a second Pd beside the live one, isolated from it and capped, and
prints Pd's output; a clean load of Cut It prints only two lines, from `[shell]`'s load-time scripts
not being in its empty working directory. `LIBS= sh loadcheck.sh …` loads without
`/sdcard/PdExtraLibs`, to compare.

**On the Mac** the same two live in `~/Library/Pd`, on Pd's standard path, so Pd's own window finds
them with no preference set: `~/Library/Pd/pdlua` from `build-pdlua.sh` (Pd source:
`~/Applications/Pd-0.57-0.app/Contents/Resources/src`), and `~/Library/Pd/else` from Deken's rc14 build
for the Mac, `else[v1.0-0_rc14-with_live_electronics_tutorial](Darwin-amd64-32)(…).dek` from
`puredata.info/Members/porres/software/else`, a zip. The same `build-pdlua.sh` leaves lua.org's `lua`
in its `build/lua-5.4.7/src`, copied to `~/.local/bin/lua` for the Lua tests. The suite empties
`HOME`, so every Pd it and `tools/deploy.sh` start gets `-path ~/Library/Pd` from the account's real
home; `CUTIT_PD_LIBS=…` points them at another folder, and `LUA=…` at another interpreter.

**To remove** them from the device: `rm -rf /sdcard/PdExtraLibs/pdlua /sdcard/PdExtraLibs/else`.
Cut It's sequencer then fails to create, and says `fail c_steps no-lua` on the screen and in the log.

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
