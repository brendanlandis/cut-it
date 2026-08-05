#!/bin/sh
# wifi-watch -- catch item 81 without anybody sitting there, and find out what
# fixes it.
#
# THE FAULT CANNOT PHONE HOME. When it hits, the Organelle loses its IPv4 lease,
# so nothing on the device can report it over the network. Detection has to be
# local and read back afterwards -- same reasoning as u_err's persistent log.
#
# What item 133 established, and what this is built to test:
#   - the device stays ASSOCIATED; it is the IPv4 LEASE that goes
#   - a restart fixes it first try; a `dhcpcd -n` renew did not
#   - ssh keeps working over IPv6 link-local throughout, which is what made this
#     look mysterious for two phases
#
# There is no syslog and no logread on this device, so dhcpcd's own messages are
# lost. dmesg survives, and is captured on every transition.
#
#   sh wifi-watch.sh            watch, and try to recover
#   sh wifi-watch.sh observe    watch only -- change nothing
#
# Stop it with: pkill -f wifi-watch
LOG=/sdcard/wifi-watch.log
PIDFILE=/sdcard/wifi-watch.pid
STAMP=/sdcard/wifi-watch.alive     # touched every poll -- mtime IS the liveness check
POLL=20
HEARTBEAT=1800          # a liveness line every 30 min, so uptime-to-failure is readable
MODE=${1:-recover}

ipv4() { ip -4 addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2; }
# the address WITH its prefix, so the probe below can put back exactly what was
# there rather than assuming /24
ipv4cidr() { ip -4 addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*/[0-9]*' | cut -d' ' -f2; }
gateway()  { ip route 2>/dev/null | awk '/^default/{print $3; exit}'; }

# last known GOOD address and gateway, refreshed on every healthy poll. The probe
# needs them at a moment when they are no longer readable from the system.
LASTCIDR=$(ipv4cidr)
LASTGW=$(gateway)

# ONE INSTANCE ONLY. Two would run the recovery ladder twice against each other,
# which is worse than not watching at all. A pidfile rather than pgrep, because
# `pgrep -f wifi-watch` also matches the ssh command that goes looking for it --
# that self-match cost real time and made a running watcher look dead.
# ⚠️ The pidfile lives on /sdcard and therefore SURVIVES A REBOOT, holding a pid
# that is now dead -- or worse, recycled onto some unrelated process. So the guard
# checks the cmdline too, not just that something with that number exists.
OLD=$(cat "$PIDFILE" 2>/dev/null)
if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null &&
   tr '\0' ' ' < "/proc/$OLD/cmdline" 2>/dev/null | grep -q wifi-watch; then
    echo "wifi-watch already running as $OLD" >&2
    exit 1
fi
rm -f "$PIDFILE"
echo $$ > "$PIDFILE"
# ⚠️ TWO TRAPS, AND THE SPLIT MATTERS. A single `trap ... EXIT INT TERM` runs the
# handler on SIGTERM but does NOT exit -- so `kill` made the watcher delete its own
# pidfile and carry on running, and the next launch, seeing no pidfile, started a
# second. Three accumulated that way, all running the recovery ladder against each
# other, which is worse than not watching at all.
trap 'rm -f "$PIDFILE" "$STAMP"' EXIT
trap 'exit 0' INT TERM

snap() {
    echo "  time:   $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  ipv4:   $(ipv4 || echo NONE)"
    echo "  assoc:  $(iw dev wlan0 link 2>/dev/null | head -2 | tr '\n' ' ' | sed 's/  */ /g')"
    echo "  procs:  wpa_supplicant=$(pgrep -x wpa_supplicant || echo '-') dhcpcd=$(pgrep -x dhcpcd || echo '-')"
    echo "  route:  $(ip route 2>/dev/null | grep '^default' || echo none)"
    echo "  signal: $(iw dev wlan0 link 2>/dev/null | grep -i signal | tr -d '\t')"
}

# ⚠️ THE PROBE THAT SPLITS THE DECISION TREE, and the reason it exists.
# wifi-analysis.md sends UNRECOVERED straight to the spare-card A/B, on the
# reasoning that a different radio proves nothing if the fault is DHCP-side.
# That fork had never actually been TESTED. A static address during the failure
# settles it outright:
#
#   traffic flows  -> the LINK is fine and this is a DHCP fault. A card swap
#                     would prove nothing, and spending it would waste the test.
#   traffic does not -> the link is dead while still reporting "associated",
#                     which is the driver/firmware branch, and the card IS next.
#
# TWO THINGS MAKE IT SAFE TO RUN. It goes BEFORE the recovery ladder, so it reads
# the broken state rather than one the ladder has already disturbed; and it TAKES
# THE ADDRESS BACK OFF afterwards, because ipv4() cannot tell a statically-added
# address from a leased one -- leaving it would make every rung below score a
# false RECOVERED and would corrupt the very datum this script exists to collect.
linkprobe() {
    echo "  --- LINK PROBE (reads the broken state, changes nothing lasting) ---"
    if [ -z "$LASTCIDR" ] || [ -z "$LASTGW" ]; then
        echo "     SKIPPED -- no healthy address/gateway recorded yet this run"
        return
    fi
    # ⚠️ NEVER RUN THIS AGAINST A HEALTHY INTERFACE. The cleanup at the bottom
    # deletes an address and a route; if one was already there, it would delete
    # the REAL one and take the device off the network with nobody watching.
    # Caught while writing this, not in the field -- a measuring rig is code.
    if [ -n "$(ipv4)" ]; then
        echo "     SKIPPED -- wlan0 already has an address; the cleanup would"
        echo "                remove the REAL one. This is a guard, not a failure."
        return
    fi
    echo "     using $LASTCIDR via $LASTGW (last known good)"

    # only ever undo what we actually managed to do
    ADDED_ADDR=no; ADDED_ROUTE=no
    if ip addr add "$LASTCIDR" dev wlan0 2>&1 | sed 's/^/     /'; then :; fi
    if [ -n "$(ipv4)" ]; then ADDED_ADDR=yes; else
        echo "     addr add did not take -- abandoning the probe, changing nothing"
        return
    fi
    if ip route add default via "$LASTGW" dev wlan0 2>&1 | sed 's/^/     /'; then :; fi
    [ -n "$(gateway)" ] && ADDED_ROUTE=yes

    ping -c 3 -W 2 "$LASTGW" 2>&1 | tail -3 | sed 's/^/     /'
    if ping -c 3 -W 2 "$LASTGW" >/dev/null 2>&1; then FINE=yes; else FINE=no; fi
    echo "     arp after probe:"; sed 's/^/       /' /proc/net/arp 2>/dev/null
    if [ "$FINE" = yes ]; then
        echo "     VERDICT: LINK IS FINE -- the fault is DHCP-side."
        echo "              A CARD SWAP WOULD PROVE NOTHING. Look at dhcpcd."
    else
        echo "     VERDICT: LINK IS DEAD despite reporting associated --"
        echo "              driver or dongle firmware. The spare card IS the next test."
    fi

    # put it back exactly as it was found
    [ "$ADDED_ROUTE" = yes ] && ip route del default via "$LASTGW" dev wlan0 2>/dev/null
    [ "$ADDED_ADDR" = yes ] && ip addr del "$LASTCIDR" dev wlan0 2>/dev/null
    STILL=$(ipv4)
    echo "     cleaned up -- ipv4 is now ${STILL:-NONE}"
    [ -n "$STILL" ] && echo "     ⚠️ CLEANUP FAILED -- every RESULT below is now untrustworthy"
    return 0
}

try() {   # $1 = description, $2 = command, $3 = seconds to wait
    echo "  >> TRY: $1"
    echo "     cmd: $2"
    sh -c "$2" >/dev/null 2>&1
    sleep "$3"
    NEW=$(ipv4)
    if [ -n "$NEW" ]; then
        echo "     RESULT: RECOVERED -- ipv4 is $NEW after $1"
        return 0
    fi
    echo "     RESULT: still no ipv4 after ${3}s"
    return 1
}

{
    echo
    echo "=================================================================="
    echo "wifi-watch started $(date '+%Y-%m-%d %H:%M:%S')  mode=$MODE poll=${POLL}s"
    snap
} >> "$LOG" 2>&1

LAST=$(ipv4); LAST=${LAST:-NONE}
TICK=0

while true; do
    NOW=$(ipv4); NOW=${NOW:-NONE}

    if [ "$NOW" != "$LAST" ]; then
        {
            echo
            echo "=================================================================="
            echo "TRANSITION  $LAST  ->  $NOW"
            snap
            if [ "$NOW" = "NONE" ]; then
                echo "  --- dmesg tail (kernel view of the dongle) ---"
                dmesg 2>/dev/null | tail -25 | sed 's/^/    /'
                echo "  --- arp ---"; sed 's/^/    /' /proc/net/arp 2>/dev/null
                linkprobe
                if [ "$MODE" = "recover" ]; then
                    # ⚠️ THE WAITS WERE 15/20/25s AND THAT WAS TOO SHORT TO BE
                    # CONCLUSIVE. Rung 3 kills wpa_supplicant and re-runs
                    # wifi-config.sh: the ASSOCIATION alone took ~8s in the dmesg
                    # of the 2026-08-04 failure, leaving under 17s for a DHCP
                    # exchange that retries. An UNRECOVERED verdict has to mean
                    # "it did not come back", not "we did not wait".
                    echo "  --- RECOVERY LADDER (gentlest first) ---"
                    try "dhcpcd renew"            "dhcpcd -n wlan0"                     45 ||
                    try "dhcpcd release+restart"  "dhcpcd -k wlan0; sleep 2; dhcpcd wlan0" 45 ||
                    try "wpa_supplicant restart"  "killall wpa_supplicant; sleep 2; sh /root/fw_dir/scripts/wifi-config.sh" 60 ||
                    echo "  >> UNRECOVERED -- every rung failed. This is the datum: only a reboot fixes it."
                else
                    echo "  --- observe mode: changing nothing ---"
                fi
            fi
        } >> "$LOG" 2>&1
        LAST=$(ipv4); LAST=${LAST:-NONE}
    fi

    # refresh the last-known-good pair WHILE it is still readable -- the probe
    # above needs it at a moment when the system no longer has it
    if [ "$NOW" != "NONE" ]; then
        C=$(ipv4cidr); [ -n "$C" ] && LASTCIDR=$C
        G=$(gateway);  [ -n "$G" ] && LASTGW=$G
    fi

    date +%s > "$STAMP"   # liveness: the epoch IS the stamp, so no date -r needed
    TICK=$((TICK + POLL))
    if [ "$TICK" -ge "$HEARTBEAT" ]; then
        echo "  .. alive $(date '+%Y-%m-%d %H:%M:%S')  ipv4=$NOW" >> "$LOG" 2>&1
        TICK=0
    fi
    sleep "$POLL"
done
