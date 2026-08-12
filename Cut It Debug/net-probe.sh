#!/bin/sh
# The three network facts you cannot get at a venue without a laptop.
#
# ⛔ IT ALWAYS EMITS EXACTLY THREE LINES, in this order, one atom each:
#
#   1  this Organelle's OWN IPv4 address     ip-<addr>     or ip-none
#   2  whether it is hosting its access point ap-up        or ap-down
#   3  the phone's address, if there is one   phone-<addr> or phone-none
#
# main.pd routes them to screenLine2, 3 and 4 by POSITION, so a variable line
# count would silently shuffle the display. The same contract as err-tail.sh,
# and for the same reason.
#
# ⛔ LINE 1 IS THE WHOLE POINT OF THIS SCREEN. PdParty will not resolve
# organelle.local -- item 312, measured on the rig -- so its OSC send host has
# to be a literal address, and the lease has been seen at .15, .18 and .6. This
# is the number you type into the phone, and reading it off the Organelle's own
# screen is what removes the last reason this rig needs a laptop to fix the
# phone link. See ref/device/phone.md.
#
# ⚠️ ON THE ACCESS POINT IT IS ALWAYS 192.168.12.1, which is the easy case. It
# is the HOUSE network that moves, so this matters most where the rig is least
# like a gig.
#
# ⚠️ busybox, NOT GNU -- ash, and ip/grep/awk are applets. No --color, no -P.

# ---- 1: our own address ----------------------------------------------------
# ⚠️ NOT `hostname -i`. On this image that answers from /etc/hosts and returns
# a loopback address, which is a plausible-looking number that is no use to the
# phone at all.
IP=$(ip -4 addr show wlan0 2>/dev/null \
     | awk '/inet /{ sub("/.*", "", $2); print $2; exit }')
[ -z "$IP" ] && IP=none
echo "ip-$IP"

# ---- 2: are we hosting the access point? -----------------------------------
# ⚠️ create_ap IS THE VENDOR'S OWN PATH here -- System -> WiFi Setup -> Start AP
# runs it. hostapd and dnsmasq are its children, so any of the three being alive
# means the AP is up. ⛔ An AP cannot be started from a patch: all three die with
# the Pd that spawned them even behind setsid nohup. Item 129, ref/wifi.md.
if ps w 2>/dev/null | grep -v grep | grep -qE "create_ap|hostapd"; then
    echo "ap-up"
else
    echo "ap-down"
fi

# ---- 3: the phone ----------------------------------------------------------
# ⛔ TWO STRATEGIES, AND THE SECOND ONE IS NOT THEORETICAL. The lease file is
# written when the address is handed out, so a client that rejoined an
# already-running AP can be absent from it while very much present -- and in the
# first AP Probe run dnsmasq had already exited and arp was the only thing that
# knew. A single-strategy probe would have returned none and taught us nothing.
# Item 129. Same pair as Cut It/phone-ip.sh, which is u_net's.
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
