#!/bin/bash
# Applies Cut It's changes to a factory Organelle S2 on OS 5.1, as music, from a copy of this
# folder on the device. Safe to run again: each step puts the same file in place, and keeps the
# factory's as .orig the first time. README.md here says what each change is for.
set -eu
K=$(cd "$(dirname "$0")" && pwd)
S=/home/music/fw_dir/scripts

sudo mount -o remount,rw /
trap 'sync; sudo mount -o remount,ro /' EXIT

keep() { [ -e "$1.orig" ] || cp -p "$1" "$1.orig"; }

# MIDI: four ALSA devices in and out, for wire.sh to connect by name
keep /home/music/.pdsettings
install -m 644 "$K/pdsettings" /home/music/.pdsettings

# USB: never mount a write-protected volume as /usbdrive (the Launchpad's)
keep $S/mount.sh
install -m 755 "$K/mount.sh" $S/mount.sh

# Wi-Fi: Start AP on the menu, at 192.168.1.15, named by /sdcard/ap.txt
keep $S/wifi_setup.py
install -m 755 "$K/wifi_setup.py" $S/wifi_setup.py

# The clock: no RTC, and fake-hwclock can't save to a read-only root, so every boot starts at the
# image's date (2026-03-17), which breaks make and stamps files months back. Network time fixes
# it on any network with the internet; the factory had it off.
sudo systemctl enable --now systemd-timesyncd

# Pd: /usr/bin/pd runs 0.57, once it's built
if [ -x /sdcard/pd-0.57-0/bin/pd ]; then
    sudo install -m 755 "$K/usr-bin-pd" /usr/bin/pd.cut-it
    sudo mv -f /usr/bin/pd.cut-it /usr/bin/pd
    echo "pd: $(/usr/bin/pd -version 2>&1 | head -1)"
else
    echo "pd: 0.57 not built yet, /usr/bin/pd left as it is"
fi
echo setup done
