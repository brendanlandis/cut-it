# The Organelle S2

Cut It's changes to a factory Organelle S2 on OS 5.1, which replaced the Organelle 1 in November
2026. The changes are the Organelle 1's (`../README.md`), carried over; what the S2 is and how its
OS behaves is on its Reference page, `critter-guitari-organelle-s2`.

Getting in: SSH is off as it ships, and the page's *Getting in with SSH off* says how it was
turned on. After that, `ssh music@<address>`: the user is `music`, with sudo, and the root
filesystem is read-only (`sudo mount -o remount,rw /`, then `ro`).

## Setting one up

From a factory 5.1 card with SSH on, from the Mac:

1. `tools/s2-build.sh <tarball dir> music@<address>` builds Pd 0.57, pdlua and ELSE on the S2
   (`build.sh`, about ten minutes; the log is `/sdcard/build-s2/build.log`).
2. Copy this folder to the S2 and run `setup.sh` there:
   `scp -r device/s2 music@<address>:/sdcard/cut-it-s2 && ssh music@<address> bash /sdcard/cut-it-s2/setup.sh`.
   It's safe to run again, and leaves the factory's files beside their replacements as `.orig`.
3. Copy `/sdcard/ap.txt` (the access point's name, then its password) and `/sdcard/cut-it-state`
   from the old device, and deploy: `HOST=music@<address> tools/deploy.sh`.
4. Give it `192.168.1.15` on the house network (below).

## Its address

**192.168.1.15 on both networks**, so the phone's send host is set once (`ref/device/phone.md`).
On the house network the S2 sets it itself, in its saved `hildegard` connection:

```sh
sudo nmcli connection modify hildegard ipv4.method manual ipv4.addresses 192.168.1.15/24 \
    ipv4.gateway 192.168.1.1 ipv4.dns 192.168.1.1
```

The Orbi also reserves `.15` for its Wi-Fi stick (a D-Link 802.11ac, Realtek RTL8822BU,
`C8:78:7D:94:F4:6D`, Brendan's own; the one that came with the S2 is a Ralink RT5572), which keeps
the address free. The reservation alone didn't do it: the Orbi kept giving out the `.13` it had
already leased that stick, even after a DHCP release. The connection lives on the card, in
`/sdcard/system-connections`, so a reflash or **Forget Saved Nets** loses it.

## What `setup.sh` changes

| File here | On the S2 | Why |
|---|---|---|
| `pdsettings` | `/home/music/.pdsettings` | MIDI devices 2 to 4, in and out, which `wire.sh` connects by name. The factory's has one; ALSA MIDI (`midiapi: 1`) is already factory on the S2. |
| `mount.sh` | `fw_dir/scripts/mount.sh` | The Organelle 1's guard: a write-protected volume (the Launchpad's) is never mounted on `/usbdrive`. The factory script has the same flaw; `../README.md` has the story. |
| `wifi_setup.py` | `fw_dir/scripts/wifi_setup.py` | **Start AP** on the WiFi menu, which 5.1 dropped though its code stayed. The access point takes `192.168.1.15`, the address the house router reserves for the Organelle, so the phone sends to one address on both networks; its name and password are `/sdcard/ap.txt`'s, as on the Organelle 1. |
| `usr-bin-pd` | `/usr/bin/pd` | Runs Pd 0.57 from `/sdcard/pd-0.57-0`; mother launches `/usr/bin/pd`. |
| — | `systemd-timesyncd` enabled | The S2 has no clock that keeps time, and the read-only root keeps fake-hwclock from saving one, so each boot starts at the image's date (2026-03-17). Network time sets it on any network with the internet. |

`Cut It/phone-ip.sh` knows the S2's access point by NetworkManager's `Hotspot` connection being
up, where the Organelle 1's was create_ap's hostapd. `Cut It/codec-gain.sh` sets the S2's WM8731
(the line input at its most gain), and the Organelle 1's SGTL5000 as before.

**To revert** any of the files, between the remounts: copy its `.orig` back. `/usr/bin/pd` was a
link: `sudo ln -sfn /etc/alternatives/pd /usr/bin/pd` puts the Debian package's Pd 0.53 back,
which can't load pdlua, so Cut It starts but doesn't play.

## Built, not copied

Pd, pdlua and ELSE are built from the same sources and scripts as the Organelle 1's (`../README.md`,
*Lua and ELSE*; `../pd-libs`), for the S2's Cortex-A72 with NEON (`-mcpu=cortex-a72
-mfpu=neon-fp-armv8`) rather than Raspberry Pi OS's ARMv6 default, on all four cores. The OS is
32-bit (armhf) on a 64-bit kernel, so the Organelle 1's armhf binaries would load, but built for
the Cortex-A9.
