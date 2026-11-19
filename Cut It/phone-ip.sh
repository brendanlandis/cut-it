#!/bin/sh
# Print the phone's address, so u_net does not have to be told it.
#
# Always exactly one line: on the Organelle's own access point, the address it
# leased the phone; anywhere else $1, u_net's creation argument. That keeps every
# conditional out of the patch. ref/device/phone.md
#
# The access point and the house network share one subnet and one address for
# the Organelle, 192.168.1.15 (device/s2/README.md), so the subnet cannot tell
# them apart. What means the access point is NetworkManager's Hotspot connection
# being up. Its dnsmasq keeps the leases in /var/lib/NetworkManager, a link to
# /var/run. Lease lines are:  <expiry> <mac> <ip> <hostname> <clientid>
DEFAULT="$1"
SELF=192.168.1.15

nmcli -t -f NAME connection show --active 2>/dev/null | grep -qx Hotspot \
    || { echo "$DEFAULT"; exit 0; }

IP=$(awk -v self="$SELF" '$3 != self {print $3}' \
     /var/lib/NetworkManager/dnsmasq-wlan0.leases 2>/dev/null | head -n1)
[ -n "$IP" ] && { echo "$IP"; exit 0; }

# A client that rejoined a running AP can be missing from the lease file while
# present, and arp knows anything that has spoken (item 129).
IP=$(awk -v self="$SELF" 'NR>1 && $6 == "wlan0" && $1 != self {print $1}' \
     /proc/net/arp 2>/dev/null | head -n1)
[ -n "$IP" ] && { echo "$IP"; exit 0; }

echo "$DEFAULT"
