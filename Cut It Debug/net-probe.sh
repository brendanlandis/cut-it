#!/bin/sh
# The three network facts you cannot get at a venue without a laptop. Always
# exactly three lines, in this order, one atom each, because main.pd routes them
# to screenLine2, 3 and 4 by position:
#
#   1  this Organelle's own IPv4 address     ip-<addr>     or ip-none
#   2  whether it is hosting its access point ap-up        or ap-down
#   3  the phone's address, if there is one   phone-<addr> or phone-none
#
# Line 1 is the point: the phone sends to a literal address (item 312), so
# the phone needs a literal address, and on the house network the lease moves
# unless the router reserves it: this Organelle's is 192.168.1.15, and its own
# access point takes the same address (device/s2/wifi_setup.py).
# ref/module/debug.md

# ---- 1: our own address ----------------------------------------------------
# Not `hostname -i`, which answers a loopback address from /etc/hosts here.
IP=$(ip -4 addr show wlan0 2>/dev/null \
     | awk '/inet /{ sub("/.*", "", $2); print $2; exit }')
[ -z "$IP" ] && IP=none
echo "ip-$IP"

# ---- 2: are we hosting the access point? -----------------------------------
# NetworkManager's Hotspot connection, which the WiFi menu's Start AP brings up.
AP=down
nmcli -t -f NAME connection show --active 2>/dev/null | grep -qx Hotspot && AP=up
echo "ap-$AP"

# ---- 3: the phone ----------------------------------------------------------
# On the access point only, as in Cut It/phone-ip.sh: the lease file, then arp,
# since a client that rejoined a running AP can be missing from the lease file
# (item 129). The house network shares the AP's subnet, so arp there would name
# whatever else is on it.
PHONE=""
SELF=192.168.1.15
if [ "$AP" = up ]; then
    PHONE=$(awk -v self="$SELF" '$3 != self {print $3}' \
        /var/lib/NetworkManager/dnsmasq-wlan0.leases 2>/dev/null | head -n1)
    [ -z "$PHONE" ] && PHONE=$(awk -v self="$SELF" 'NR>1 && $6 == "wlan0" && $1 != self {print $1}' \
        /proc/net/arp 2>/dev/null | head -n1)
fi
[ -z "$PHONE" ] && PHONE=none
echo "phone-$PHONE"
