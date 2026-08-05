#!/bin/bash
# Recover wlan0 the way the FRONT PANEL does, because that is the only sequence
# ever observed to work without a reboot.
#
#   bash /sdcard/wifi-reassociate.sh
#
# WHY THIS EXISTS, and it is a correction to our own tooling rather than a new
# idea. wifi-watch.sh's recovery ladder used to end by running
# /root/fw_dir/scripts/wifi-config.sh. ⚠️ THAT FILE IS A STALE FACTORY TEMPLATE:
#
#     ip link set wlan0 up
#     wpa_supplicant -D nl80211,wext -i wlan0 -c <(wpa_passphrase "name" "pass") &
#
# The SSID is literally `name` and the passphrase literally `pass` -- and
# `wpa_passphrase` rejects anything shorter than 8 characters, so it emits
# nothing and the supplicant gets an empty config. The rung therefore KILLED a
# working wpa_supplicant and replaced it with nothing. Every `UNRECOVERED`
# verdict it produced was partly self-inflicted, and "only a reboot fixes it"
# was partly a description of the damage the ladder had just done.
#
# WHAT THE FRONT PANEL ACTUALLY DOES (scripts/wifi_control.py), and the two
# differences that matter:
#
#   1. `dhcpcd -b -x wlan0`   -x EXITS the daemon. The ladder used -k, which
#                             only RELEASES the lease -- so a wedged dhcpcd
#                             stayed wedged and the "restart" restarted nothing.
#   2. real credentials, read from /sdcard/wifi.txt, and a ctrl_interface.
#
# ⚠️ bash, not sh: the process substitution below is a bashism, and the device's
# /bin/sh is busybox ash. wifi_control.py uses bash for the same reason.
set -u

WIFI=${WIFI:-/sdcard/wifi.txt}
[ -r "$WIFI" ] || { echo "no $WIFI -- cannot recover without credentials"; exit 1; }

SSID=$(sed -n 1p "$WIFI")
PW=$(sed -n 2p "$WIFI")
[ -n "$SSID" ] && [ -n "$PW" ] || { echo "$WIFI line 1 must be the SSID and line 2 the passphrase"; exit 1; }

echo "     reassociating with '$SSID'"

# 1. EXIT dhcpcd -- not release. This is the difference from the old rung 2.
dhcpcd -b -x wlan0 2>&1 | sed 's/^/       /'
sleep 1

# 1b. ⚠️ AND FLUSH THE INTERFACE. dhcpcd.conf sets `persistent`, which means
# exiting the daemon DELIBERATELY LEAVES the address configured -- so a fresh
# dhcpcd leases a SECOND one on top and wlan0 ends up with two. Measured while
# testing this script against a healthy device: 192.168.1.15 AND .18 at once.
# It does not arise from the recovery ladder, which only runs when there is no
# address at all -- but it does when the script is run by hand, and two
# addresses break wifi-watch's own ipv4() (it greps every `inet` line).
# Harmless and idempotent in the failure case, where there is nothing to flush.
ip addr flush dev wlan0 2>&1 | sed 's/^/       /'

# 2. a fresh supplicant with the REAL credentials
killall wpa_supplicant 2>/dev/null
sleep 1
ip link set wlan0 up 2>&1 | sed 's/^/       /'
wpa_supplicant -B -D nl80211,wext -i wlan0 \
    -c <(cat <(echo ctrl_interface=/var/run/wpa_supplicant) \
             <(wpa_passphrase "$SSID" "$PW")) 2>&1 | sed 's/^/       /'

# 3. give the association time to complete before asking for an address --
#    measured at ~8 s in the dmesg of the 2026-08-04 failure
sleep 8

# 4. and only now a fresh dhcpcd
dhcpcd -b wlan0 2>&1 | sed 's/^/       /'
