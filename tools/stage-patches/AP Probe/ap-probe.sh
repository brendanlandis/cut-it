#!/bin/sh
# AP PROBE -- answers the three questions that can only be asked while the
# access point is running, which is exactly when nobody can watch.
#
# A Mac joined to this AP has no internet (create_ap is called with -n), so the
# session that would answer these is the session with no assistance in it. So
# the probe records itself: run it once from the menu, reconnect to the house
# wifi afterwards, and read the log at leisure. Same reasoning as u_err's
# persistent log -- nothing has to be caught live.
#
#   Q1  does create_ap survive Pd being reloaded?   <- selecting THIS patch is the reload
#   Q2  where is the dnsmasq lease file, and what is in it?
#   Q3  can the phone's address be extracted from it reliably?
#
# Everything goes to the log. EXACTLY ONE LINE goes to stdout -- the phone's
# address, or "none" -- because the patch puts that on the OLED.
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
# The AP itself is 192.168.12.1, so anything else on that subnet is a client.
PHONE=""
if [ -n "$LEASE" ] && [ -f "$LEASE" ]; then
    PHONE=$(awk '{print $3}' "$LEASE" 2>/dev/null \
            | grep -E '^192\.168\.' | grep -v '^192\.168\.12\.1$' | head -n1)
fi
# fall back to the arp table, which knows anything that has actually talked
if [ -z "$PHONE" ]; then
    PHONE=$(awk 'NR>1 && $1 ~ /^192\.168\.12\./ && $1 != "192.168.12.1" {print $1}' \
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
