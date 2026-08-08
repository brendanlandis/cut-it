#!/bin/sh
# Where is the Organelle, and WHICH failure is this? Run from the Mac.
#
#   ./tools/find-organelle.sh          the whole ladder, then a named verdict
#   ./tools/find-organelle.sh -q       the verdict line only
#
# WHY IT EXISTS. ⚠️ "Cannot reach it" is the single most misread observation in
# this project, and ref/device-os.md says so in three places. Four different
# states all present as a failed ssh, they want opposite responses, and telling
# them apart by hand takes five commands nobody remembers under pressure:
#
#   REACHABLE            it is fine and mDNS was just slow
#   ASSOCIATED-NO-LEASE  ⛔ THE DOCUMENTED FAULT -- item 81. Still on the wifi,
#                        IPv4 lease gone, and SSH STILL WORKS OVER IPv6
#   AP-MODE              it is running its own access point -- join that network
#   ABSENT               nothing anywhere: powered off, adapter down, or on
#                        another network. NOT the documented fault
#
# ⛔ THE DIFFERENCE THAT COSTS THE MOST. The documented fault leaves the device
# ASSOCIATED, so ssh over IPv6 link-local keeps working throughout -- which means
# a successful login proves nothing about IPv4, and a failed *name* lookup proves
# nothing about the device. Item 172 adds the other half: a RECOVERY presents
# exactly like a continued failure, because the address changes and mDNS lags
# minutes behind. ⚠️ A POWER CYCLE AT THAT MOMENT DESTROYS THE EVIDENCE.
#
# It changes nothing on the device and needs no credentials -- it only looks.
set -u

QUIET=0
[ "${1:-}" = "-q" ] && QUIET=1
IFACE=${IFACE:-en0}
# ⚠️ THE IDENTITY SIGNAL IS THE SSH BANNER, and it is a heuristic rather than a
# proof. Organelle OS 4.0 is a 2018 image and ships OpenSSH 7.1; every other host
# on this network answers 8.2 or newer. ⛔ The first version tried mother's OSC
# port 4001 instead -- and `nc -z` tests TCP while 4001 is UDP, so it found the
# Organelle at .9 and dismissed it. Override if the image is ever updated.
ORG_BANNER=${ORG_BANNER:-OpenSSH_7.1}
say() { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; }

VERDICT=ABSENT
WHERE=""

say "=== 1. mDNS ============================================================="
# -t is dns-sd's own timeout; macOS has no timeout(1), which is why nothing here
# pipes through one.
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
# ⛔ This is the rung that distinguishes item 81 from a dead device. With no IPv4
# lease the host is invisible to every check above and still answers here.
ping6 -c 3 -i 0.4 "ff02::1%$IFACE" >/dev/null 2>&1
# ⛔ A NEIGHBOUR THAT ALREADY HAS IPv4 IS NOT THIS FAULT, and skipping this test
# is not a nuance -- the first version reported a NAS with ssh open as the
# documented fault, because it probed every fe80 neighbour and believed whichever
# answered first. A lying diagnostic is worse than none.
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
[ "$VERDICT" = ABSENT ] && say "  no IPv4-less IPv6 neighbour looks like the Organelle."
fi

if [ "$VERDICT" = ABSENT ]; then
say "=== 4. is it running its own access point? =============================="
if system_profiler SPAirPortDataType 2>/dev/null | grep -qi organelle; then
    VERDICT=AP-MODE
    say "  an Organelle-like SSID is visible. Join it -- the device is 192.168.12.1 there."
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
    echo "      ssh root@$WHERE 'sh /sdcard/wifi-reassociate.sh'   # rung 1, the one that works" ;;
AP-MODE)
    echo "VERDICT: AP-MODE"
    echo "  Join the Organelle's own network. It is 192.168.12.1 there, and that"
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
