#!/bin/sh
# Print the phone's address, so u_net does not have to be told it.
#
# On the Organelle's OWN access point there is no discovery problem to solve:
# the Organelle IS the DHCP server, so it already handed the phone its address.
# create_ap puts dnsmasq's lease file in a directory with a random suffix --
# measured as /tmp/create_ap.wlan0.conf.*/dnsmasq.leases -- hence the glob.
#
# IT ALWAYS PRINTS EXACTLY ONE LINE: the discovered address when acting as an
# access point, and $1 -- which u_net passes from its creation argument --
# otherwise. That keeps every conditional out of the patch, which has no good
# way to compare two symbols anyway.
#
# Lease lines are:  <expiry> <mac> <ip> <hostname> <clientid>
DEFAULT="$1"

for f in /tmp/create_ap.wlan0.conf.*/dnsmasq.leases; do
    [ -f "$f" ] || continue
    IP=$(awk '{print $3}' "$f" 2>/dev/null \
         | grep -E '^192\.168\.' | grep -v '^192\.168\.12\.1$' | head -n1)
    [ -n "$IP" ] && { echo "$IP"; exit 0; }
done

# The lease file is written when the address is handed out, so a client that
# rejoined an already-running AP can be missing from it while still being very
# much present. arp knows anything that has actually spoken. This fallback is
# not theoretical -- it is what produced the address in the first probe run,
# where dnsmasq had already exited and the lease file could not be located.
IP=$(awk 'NR>1 && $1 ~ /^192\.168\.12\./ && $1 != "192.168.12.1" {print $1}' \
     /proc/net/arp 2>/dev/null | head -n1)
[ -n "$IP" ] && { echo "$IP"; exit 0; }

echo "$DEFAULT"
