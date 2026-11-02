#!/bin/sh
# The three network facts you cannot get at a venue without a laptop. Always
# exactly three lines, in this order, one atom each, because main.pd routes them
# to screenLine2, 3 and 4 by position:
#
#   1  this Organelle's own IPv4 address     ip-<addr>     or ip-none
#   2  whether it is hosting its access point ap-up        or ap-down
#   3  the phone's address, if there is one   phone-<addr> or phone-none
#
# Line 1 is the point: PdParty will not resolve organelle.local (item 312), so
# the phone needs a literal address, and on the house network the lease moves
# (the addresses seen are on the Organelle's Reference page, Reaching it). On
# the access point it is always 192.168.12.1.
# ref/module/debug.md
#
# busybox, not GNU: ash, and ip, grep and awk are applets.

# ---- 1: our own address ----------------------------------------------------
# Not `hostname -i`, which answers a loopback address from /etc/hosts here.
IP=$(ip -4 addr show wlan0 2>/dev/null \
     | awk '/inet /{ sub("/.*", "", $2); print $2; exit }')
[ -z "$IP" ] && IP=none
echo "ip-$IP"

# ---- 2: are we hosting the access point? -----------------------------------
# create_ap is the system menu's AP, with hostapd and dnsmasq as its children,
# so any of them alive means the AP is up (item 129, ref/wifi.md).
if ps w 2>/dev/null | grep -v grep | grep -qE "create_ap|hostapd"; then
    echo "ap-up"
else
    echo "ap-down"
fi

# ---- 3: the phone ----------------------------------------------------------
# The lease file, then arp, as in Cut It/phone-ip.sh: a client that rejoined a
# running AP can be missing from the lease file (item 129).
PHONE=""
for f in /tmp/create_ap.wlan0.conf.*/dnsmasq.leases; do
    [ -f "$f" ] || continue
    PHONE=$(awk '{print $3}' "$f" 2>/dev/null \
            | grep -E '^192\.168\.' | grep -v '^192\.168\.12\.1$' | head -n1)
    [ -n "$PHONE" ] && break
done
if [ -z "$PHONE" ]; then
    PHONE=$(awk 'NR>1 && $1 ~ /^192\.168\.12\./ && $1 != "192.168.12.1" {print $1}' \
            /proc/net/arp 2>/dev/null | head -n1)
fi
[ -z "$PHONE" ] && PHONE=none
echo "phone-$PHONE"
