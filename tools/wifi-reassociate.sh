#!/bin/bash
# Recover wlan0 the way the front panel's wifi_control.py does, the only
# sequence seen to work without a reboot:
#
#   bash /sdcard/wifi-reassociate.sh
#
# Not /root/fw_dir/scripts/wifi-config.sh, a stale template that kills a working
# wpa_supplicant (item 161, the Organelle's Reference page).
#
# bash, not sh: the process substitution below is a bashism, and /bin/sh is
# busybox ash.
set -u

WIFI=${WIFI:-/sdcard/wifi.txt}
[ -r "$WIFI" ] || { echo "no $WIFI -- cannot recover without credentials"; exit 1; }

SSID=$(sed -n 1p "$WIFI")
PW=$(sed -n 2p "$WIFI")
[ -n "$SSID" ] && [ -n "$PW" ] || { echo "$WIFI line 1 must be the SSID and line 2 the passphrase"; exit 1; }

echo "     reassociating with '$SSID'"

# 1. -x exits dhcpcd; -k only releases the lease and leaves a wedged one wedged.
dhcpcd -b -x wlan0 2>&1 | sed 's/^/       /'
sleep 1

# 1b. Flush too: an exited dhcpcd leaves its address and a fresh one adds a
# second (Reference, critter-guitari-organelle-1, wpa_supplicant and dhcpcd),
# which breaks wifi-watch's ipv4(). Only a run by hand on a healthy device hits it.
ip addr flush dev wlan0 2>&1 | sed 's/^/       /'

# 2. a fresh supplicant with the real credentials and a ctrl_interface
killall wpa_supplicant 2>/dev/null
sleep 1
ip link set wlan0 up 2>&1 | sed 's/^/       /'
wpa_supplicant -B -D nl80211,wext -i wlan0 \
    -c <(cat <(echo ctrl_interface=/var/run/wpa_supplicant) \
             <(wpa_passphrase "$SSID" "$PW")) 2>&1 | sed 's/^/       /'

# 3. wait out the association (Reference, critter-guitari-organelle-1,
#    wpa_supplicant and dhcpcd)
sleep 8

# 4. and only now a fresh dhcpcd
dhcpcd -b wlan0 2>&1 | sed 's/^/       /'
