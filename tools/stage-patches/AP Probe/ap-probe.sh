#!/bin/sh
# Three questions that can only be asked while the access point is up, when a
# Mac joined to it has no internet, so it logs them for reading afterwards:
#
#   Q1  does create_ap survive Pd being reloaded?   <- selecting THIS patch is the reload
#   Q2  where is the dnsmasq lease file, and what is in it?
#   Q3  can the phone's address be extracted from it reliably?
#
# Exactly one line to stdout, the phone's address or "none", for the OLED.
LOG=/sdcard/ap-probe.log

{
  echo "=================================================================="
  echo "ap-probe   $(date)"
  echo
  echo "-- Q1: is create_ap still alive after this patch loaded? ----------"
  if ps w 2>/dev/null | grep -v grep | grep create_ap; then
      echo "   ANSWER: YES -- it survived the Pd reload"
  else
      echo "   ANSWER: NO create_ap PROCESS -- it did NOT survive the reload."
      echo "   That kills the menu-patch approach: the AP has to be started"
      echo "   some other way, or ap-up.sh needs a stronger detach."
  fi
  echo
  echo "-- supporting processes -------------------------------------------"
  ps w 2>/dev/null | grep -v grep | grep -E "hostapd|dnsmasq" || echo "   none found"
  echo
  echo "-- Q2: the lease file, taken from dnsmasq's OWN command line ------"
  LEASE=$(ps w 2>/dev/null | grep -v grep | grep dnsmasq \
          | tr ' ' '\n' | grep -- "--dhcp-leasefile=" | head -n1 | cut -d= -f2)
  echo "   --dhcp-leasefile = [$LEASE]"
  if [ -n "$LEASE" ] && [ -f "$LEASE" ]; then
      echo "   contents:"; sed 's/^/     /' "$LEASE"
  else
      echo "   not found that way. Searching instead:"
      find /tmp /var/run /run -name "*lease*" 2>/dev/null | sed 's/^/     /' | head -20
      echo "   create_ap working dirs:"
      find /tmp -maxdepth 1 -name "*create_ap*" 2>/dev/null | sed 's/^/     /' | head
  fi
  echo
  echo "-- the interface --------------------------------------------------"
  ip addr show wlan0 2>/dev/null | sed 's/^/   /'
  echo
  echo "-- who is associated ----------------------------------------------"
  iw dev wlan0 station dump 2>/dev/null | grep -E "^Station|signal:" | sed 's/^/   /' \
      || echo "   (iw station dump unavailable)"
  echo
  echo "-- arp ------------------------------------------------------------"
  sed 's/^/   /' /proc/net/arp 2>/dev/null
} >> "$LOG" 2>&1

# ---- Q3: extract the phone -------------------------------------------------
# dnsmasq lease lines are: <expiry> <mac> <ip> <hostname> <clientid>
# The AP itself is 192.168.1.15 (device/start-ap.sh; 192.168.12.1 before
# 2026-11-03), so anything else it leased, or that arp saw on wlan0, is a client.
PHONE=""
SELF=192.168.1.15
if [ -n "$LEASE" ] && [ -f "$LEASE" ]; then
    PHONE=$(awk -v self="$SELF" '$3 != self {print $3}' "$LEASE" 2>/dev/null | head -n1)
fi
# then the arp table: dnsmasq may have exited already (item 129)
if [ -z "$PHONE" ]; then
    PHONE=$(awk -v self="$SELF" 'NR>1 && $6 == "wlan0" && $1 != self {print $1}' \
            /proc/net/arp 2>/dev/null | head -n1)
fi
[ -z "$PHONE" ] && PHONE=none

{
  echo
  echo "-- Q3: extracted phone address ------------------------------------"
  echo "   PHONE = $PHONE"
  echo "   (this is the value u_net would need as its creation argument)"
  echo
} >> "$LOG" 2>&1

echo "$PHONE"
