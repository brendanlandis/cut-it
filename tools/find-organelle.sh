#!/bin/sh
# Where is the Organelle, and WHICH failure is this? Run from the Mac.
#
#   ./tools/find-organelle.sh          the whole ladder, then a named verdict
#   ./tools/find-organelle.sh -q       the verdict line only
#
# Four states present as a failed ssh and want opposite responses: REACHABLE,
# ASSOCIATED-NO-LEASE (the documented fault, item 81: ssh still works over IPv6),
# AP-MODE and ABSENT. tools/README.md has what each means. It only looks.
set -u

QUIET=0
[ "${1:-}" = "-q" ] && QUIET=1
IFACE=${IFACE:-en0}
# The ssh banner is the identity, a heuristic: OS 4.0 ships OpenSSH 7.1 and the
# rest of this network 8.2 or newer. Not mother's port 4001, which is UDP where
# `nc -z` tests TCP. Override if the image is ever updated.
ORG_BANNER=${ORG_BANNER:-OpenSSH_7.1}
say() { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; }

VERDICT=ABSENT
WHERE=""

say "=== 1. mDNS ============================================================="
# -t is dns-sd's own timeout; macOS has no timeout(1).
MDNS=$(dns-sd -t 4 -G v4v6 organelle.local 2>/dev/null \
       | awk '/organelle/ {print $6}' | grep -v '^$' | head -2)
if [ -n "$MDNS" ]; then
    say "  resolves to: $(echo "$MDNS" | tr '\n' ' ')"
else
    say "  no answer. ⚠️ Proves nothing on its own -- mDNS lags a recovery by minutes."
fi

say "=== 2. IPv4 on this subnet =============================================="
MY=$(ipconfig getifaddr "$IFACE" 2>/dev/null)
if [ -z "$MY" ]; then
    say "  ⚠️ $IFACE has no address. Fix the MAC's own network before reading anything below."
else
    NET=$(echo "$MY" | cut -d. -f1-3)
    say "  sweeping ${NET}.1-254 from $MY ..."
    i=1
    while [ $i -le 254 ]; do ping -c 1 -W 250 "${NET}.$i" >/dev/null 2>&1 & i=$((i+1)); done
    sleep 7
    HOSTS=$(arp -a -n 2>/dev/null | grep -v 'incomplete\|permanent\|(22[4-9]\|(23[0-9]')
    say "  $(echo "$HOSTS" | grep -c .) hosts answered"
    for a in $(echo "$HOSTS" | sed -n 's/.*(\([0-9.]*\)).*/\1/p'); do
        if nc -z -G 2 -w 2 "$a" 22 >/dev/null 2>&1; then
            BAN=$(nc -w 3 "$a" 22 </dev/null 2>/dev/null | head -1 | tr -d '\r')
            case "$BAN" in
            *$ORG_BANNER*) VERDICT=REACHABLE; WHERE="$a"
                say "  ✓ $a  $BAN   <- the Organelle" ;;
            *)  say "    $a  $BAN   (some other host)" ;;
            esac
        fi
    done
fi

if [ "$VERDICT" = ABSENT ]; then
say "=== 3. IPv6 link-local -- WHERE THE DOCUMENTED FAULT HIDES ==============="
# With no IPv4 lease the device is invisible above and still answers here.
ping6 -c 3 -i 0.4 "ff02::1%$IFACE" >/dev/null 2>&1
# A neighbor that already has IPv4 is not this fault; without the skip, any host
# with ssh open (a NAS, once) is reported as it.
V4MACS=$(arp -a -n 2>/dev/null | sed -n 's/.* at \([0-9a-f:]*\) .*/\1/p' | tr 'A-Z' 'a-z')
for a in $(ndp -an 2>/dev/null | awk -v i="$IFACE" '$3==i && $1 ~ /^fe80/ {print $1}'); do
    MAC=$(ndp -an 2>/dev/null | awk -v A="$a" '$1==A {print $2; exit}' | tr 'A-Z' 'a-z')
    if [ -n "$MAC" ] && echo "$V4MACS" | grep -qx "$MAC"; then continue; fi
    nc -z -G 3 -w 3 -6 "$a" 22 >/dev/null 2>&1 || continue
    BAN=$(nc -w 3 -6 "$a" 22 </dev/null 2>/dev/null | head -1 | tr -d '\r')
    case "$BAN" in
    *$ORG_BANNER*) VERDICT=ASSOCIATED-NO-LEASE; WHERE="$a"
        say "  ⛔ $a answers ssh over IPv6 and has NO IPv4 address.  $BAN"
        break ;;
    *)  say "    $a has ssh but is not the Organelle:  $BAN" ;;
    esac
done
[ "$VERDICT" = ABSENT ] && say "  no IPv4-less IPv6 neighbor looks like the Organelle."
fi

if [ "$VERDICT" = ABSENT ]; then
say "=== 4. is it running its own access point? =============================="
if system_profiler SPAirPortDataType 2>/dev/null | grep -qi organelle; then
    VERDICT=AP-MODE
    say "  an Organelle-like SSID is visible. Join it -- the device is 192.168.1.15 there."
else
    say "  no Organelle-like SSID among $(system_profiler SPAirPortDataType 2>/dev/null \
         | grep -c 'PHY Mode') visible networks."
fi
fi

echo
case "$VERDICT" in
REACHABLE)
    echo "VERDICT: REACHABLE at $WHERE"
    echo "  ⚠️ ssh answering is NOT the same as having a lease. The real check is:"
    echo "      ssh root@$WHERE 'ip addr show wlan0 | grep \"inet \"'" ;;
ASSOCIATED-NO-LEASE)
    echo "VERDICT: ASSOCIATED-NO-LEASE at $WHERE"
    echo "  ⛔ THIS IS THE DOCUMENTED FAULT -- item 81. Do NOT power cycle: that"
    echo "     destroys the evidence, and item 172 says a recovery looks identical"
    echo "     to a continued failure. Capture first, then recover:"
    echo "      ssh root@$WHERE 'ip addr show wlan0; wpa_cli -i wlan0 status; dmesg | tail -40'"
    echo "      ./tools/wifi-report.sh"
    echo "      ssh root@$WHERE 'bash /sdcard/wifi-reassociate.sh' # rung 1, the one that works" ;;
AP-MODE)
    echo "VERDICT: AP-MODE"
    echo "  Join the Organelle's own network. It is 192.168.1.15 there, and that"
    echo "  network has no internet -- item 129." ;;
*)
    echo "VERDICT: ABSENT -- not on this network in any form"
    echo "  ⛔ THIS IS NOT THE DOCUMENTED FAULT. Item 81 leaves the device"
    echo "     ASSOCIATED, so ssh over IPv6 keeps working -- and nothing answered."
    echo "  Check, in this order:"
    echo "    1. is it powered on, and did it finish booting"
    echo "    2. ⚠️ is the Launchpad plugged in -- a boot with it attached can hang"
    echo "       on mount.sh forever. ref/device-os.md, the boot hang"
    echo "    3. the front panel: System -> WiFi Setup, and whether the dongle is seated"
    echo "    4. whether it joined a different SSID than this Mac is on" ;;
esac
