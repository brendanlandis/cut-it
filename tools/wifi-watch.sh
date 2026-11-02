#!/bin/sh
# Catch item 81 with nobody watching. The fault takes the IPv4 lease, so nothing
# can report it over the network: it is logged here and read back afterwards.
# There is no syslog, so dmesg is captured on every transition. What the fault
# is: the Organelle's Reference page, Wifi.
#
#   sh wifi-watch.sh            watch, and try to recover
#   sh wifi-watch.sh observe    watch only -- change nothing
#
# Stop it with:  kill "$(cat /sdcard/wifi-watch.pid)"
#
# ⛔ Never `pkill -f wifi-watch`: it matches the ssh command too and kills the
# session (item 163). The kill takes up to a poll interval, since the TERM trap
# waits for `sleep $POLL` to return; wait, then check the pidfile is gone.
# Stop it before copying a new version over it (tools/README.md).
LOG=/sdcard/wifi-watch.log
PIDFILE=/sdcard/wifi-watch.pid
STAMP=/sdcard/wifi-watch.alive     # touched every poll; its mtime is the liveness check
POLL=20
HEARTBEAT=1800          # a liveness line every 30 min, so uptime-to-failure is readable
MODE=${1:-recover}

ipv4() { ip -4 addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2; }
# with its prefix, so the probe puts back exactly what was there
ipv4cidr() { ip -4 addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*/[0-9]*' | cut -d' ' -f2; }
gateway()  { ip route 2>/dev/null | awk '/^default/{print $3; exit}'; }

# last known good, refreshed on every healthy poll, for the probe to use once
# the system no longer has them
LASTCIDR=$(ipv4cidr)
LASTGW=$(gateway)

# When a rung recovers, LAST is re-read at the bottom of the loop, so no
# `NONE -> ipv4` transition is logged and only this records how long the
# network was down (item 212).
DOWN_AT=""

# Item 215: whether the daemon holding the dead lease is the one that acquired
# it. The same pid points client-side, a new one upstream.
LASTDHCPPID=$(pgrep -nx dhcpcd)

# One instance only: two would run the ladder against each other. A pidfile, not
# a process scan, which matches the ssh command looking for it (tools/README.md).
# The pidfile survives a reboot, holding a pid that may be recycled, so the
# guard checks the cmdline too.
OLD=$(cat "$PIDFILE" 2>/dev/null)
if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null &&
   tr '\0' ' ' < "/proc/$OLD/cmdline" 2>/dev/null | grep -q wifi-watch; then
    echo "wifi-watch already running as $OLD" >&2
    exit 1
fi
rm -f "$PIDFILE"
echo $$ > "$PIDFILE"
# ⛔ Two traps: one `trap ... EXIT INT TERM` runs the handler on TERM without
# exiting, so the watcher drops its pidfile and keeps running. And the pidfile
# goes only if it is still ours: in a stop-then-start, the dying watcher's EXIT
# trap runs after the new one has written its pid.
cleanup() {
    [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] && rm -f "$PIDFILE" "$STAMP"
    return 0
}
trap cleanup EXIT
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
# plan-v04.md sends UNRECOVERED straight to the spare-card A/B, on the
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
    # Cleared first: a probe that returns early must not leave the last
    # failure's verdict for dhcpprobe to read.
    FINE=""
    echo "  --- LINK PROBE (reads the broken state, changes nothing lasting) ---"
    if [ -z "$LASTCIDR" ] || [ -z "$LASTGW" ]; then
        echo "     SKIPPED -- no healthy address/gateway recorded yet this run"
        return
    fi
    # Never on a healthy interface: the cleanup would delete the real address.
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

# Is dhcpcd asking and getting no answer? `dhcpcd -T` configures nothing, so it
# is safe in the broken state and beside the real daemon (verified 2026-08-05).
dhcpprobe() {
    echo "  --- DHCP PROBE (test mode -- asks, but configures nothing) ---"
    timeout 30 dhcpcd -T -t 25 wlan0 2>&1 |
        grep -iE "soliciting|offered|timed out|no useful|carrier|ifssid" |
        sed 's/^/     /'
    # -T stops at the OFFER and never sends a REQUEST (item 184), hence the
    # narrow reading.
    echo "     READ THIS NARROWLY:"
    echo "       an OFFER = the server answers a DISCOVER from this client, and"
    echo "                  nothing more. It does NOT mean the daemon is wedged."
    echo "       no OFFER = nothing is answering this client on this AP right now."

    # -T asks as a fresh client, which is not the thing that is broken (item 215).
    echo "  --- THE RUNNING DAEMON, at the same instant (item 215) ---"
    D=$(pgrep -nx dhcpcd)
    if [ -z "$D" ]; then
        echo "     ⛔ NO dhcpcd RUNNING AT ALL -- that alone explains the missing"
        echo "        lease, and none of the reasoning below applies."
    else
        # A verdict only on a live link (FINE, from linkprobe): on a dead one no
        # daemon could re-acquire.
        if [ "$D" = "$LASTDHCPPID" ]; then
            echo "     dhcpcd pid $D -- SAME PROCESS that held the lease when healthy"
        else
            echo "     dhcpcd pid $D -- CHANGED (was ${LASTDHCPPID:-none} when healthy)"
        fi
        if [ "${FINE:-unknown}" != "yes" ]; then
            echo "     => NO VERDICT: the link probe did not report a healthy link,"
            echo "        so nothing here distinguishes a wedged daemon from a dead"
            echo "        network. Read the LINK PROBE above first."
        elif [ "$D" = "$LASTDHCPPID" ]; then
            echo "     => link is FINE and the incumbent daemon still has no lease."
            echo "        CLIENT-side."
        else
            echo "     => link is FINE and even a restarted daemon has no lease."
            echo "        Points UPSTREAM."
        fi
        # -U prints only `dhcp_dump: No such file or directory`: it reads a lease
        # file, and /var/lib/dhcpcd is on the read-only rootfs. Kept because that
        # line is the evidence. With no lease store dhcpcd cannot rebind after a
        # carrier change, only DISCOVER; --dbdir was ruled out with the expiring-
        # lease model, never on its own merits.
        echo "     dhcpcd -U wlan0:"
        dhcpcd -U wlan0 2>&1 | head -12 | sed 's/^/       /'
    fi
}

# ---------------------------------------------------------------------------
# The preferred-AP steer: prevention rather than recovery, and off. ⛔ Do not
# re-enable it: every roam drops IPv4 itself, and it hides the fault by
# preventing it (ref/wifi.md, If it recurs; item 214). A preference, not a pin:
# with the target not visible it does nothing.
#
#     PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh
PREFER_BSSID=${PREFER_BSSID:-}

curbssid() { iw dev wlan0 link 2>/dev/null | sed -n 's/^Connected to \([0-9a-f:]*\).*/\1/p'; }

prefer_router() {
    [ -n "$PREFER_BSSID" ] || return 0
    CUR=$(curbssid)
    [ -n "$CUR" ] || return 0                    # unassociated: nothing to steer
    [ "$CUR" = "$PREFER_BSSID" ] && return 0     # already where we want to be

    # `wpa_cli roam` only targets a BSS in the scan cache, so scan first (item
    # 175). Then `scan dump`, which reads the cache: a bare `iw scan` contends
    # with the wpa_cli one and reports a strong AP not visible (item 187).
    wpa_cli -i wlan0 scan >/dev/null 2>&1
    sleep 6
    iw dev wlan0 scan dump 2>/dev/null | grep -qi "^BSS $PREFER_BSSID" || {
        echo "  .. on $CUR, but $PREFER_BSSID is not visible -- leaving it alone" >> "$LOG"
        return 0
    }
    {
        echo
        echo "  ~~ PREFERRED-AP STEER: on $CUR, moving to $PREFER_BSSID"
        echo "     (PREFER_BSSID is set, though the steer is meant to stay off: the"
        echo "      roam drops IPv4 itself -- ref/wifi.md, If it recurs; item 214)"
        wpa_cli -i wlan0 roam "$PREFER_BSSID" 2>&1 | sed 's/^/     /'
        sleep 6
        A=$(ipv4); B=$(curbssid)
        echo "     now on: ${B:-unassociated}   ipv4: ${A:-NONE}"
    } >> "$LOG" 2>&1
}

# A lower bound, reported as one: the address was gone up to POLL seconds
# before DOWN_AT was stamped.
outage_report() {
    [ -n "$DOWN_AT" ] || return 0
    NOWS=$(date +%s)
    echo "     ** OUTAGE: about $((NOWS - DOWN_AT))s without ipv4"
    echo "        (lower bound -- add 0 to ${POLL}s for the poll that detected it)"
    DOWN_AT=""
}

try() {   # $1 = description, $2 = command, $3 = seconds to wait
    echo "  >> TRY: $1"
    echo "     cmd: $2"
    sh -c "$2" >/dev/null 2>&1
    sleep "$3"
    NEW=$(ipv4)
    if [ -n "$NEW" ]; then
        echo "     RESULT: RECOVERED -- ipv4 is $NEW after $1"
        outage_report
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
                DOWN_AT=$(date +%s)
                # 60 lines, to reach what precedes `authenticate with <bssid>`:
                # a deauth or beacon-loss line would tell a disconnect from a
                # voluntary roam. With no bgscan configured, it does not hunt
                # for better APs on its own.
                echo "  --- dmesg tail (kernel view of the dongle) ---"
                dmesg 2>/dev/null | tail -60 | sed 's/^/    /'
                echo "  --- arp ---"; sed 's/^/    /' /proc/net/arp 2>/dev/null
                linkprobe
                dhcpprobe
                if [ "$MODE" = "recover" ]; then
                    # Strongest first, the weak rungs kept as a discriminator
                    # (tools/README.md). 90 s because 60 expired before a
                    # recovery that worked landed (item 178), and an
                    # UNRECOVERED must mean it did not come back.
                    echo "  --- RECOVERY LADDER (most effective first) ---"
                    try "full reassociate"         "bash /sdcard/wifi-reassociate.sh"       90 ||
                    try "dhcpcd renew"             "dhcpcd -n wlan0"                        45 ||
                    try "dhcpcd EXIT+restart"      "dhcpcd -b -x wlan0; sleep 2; dhcpcd -b wlan0" 45 ||
                    echo "  >> UNRECOVERED -- every rung failed, INCLUDING the one the front panel uses."
                else
                    echo "  --- observe mode: changing nothing ---"
                fi
            else
                # Back with no rung claiming it: observe mode, or an unaided
                # recovery between polls, which would overturn the record that
                # the lease is not regained.
                outage_report
            fi
        } >> "$LOG" 2>&1
        LAST=$(ipv4); LAST=${LAST:-NONE}
    fi

    # refresh the last-known-good values while they are readable
    if [ "$NOW" != "NONE" ]; then
        C=$(ipv4cidr); [ -n "$C" ] && LASTCIDR=$C
        G=$(gateway);  [ -n "$G" ] && LASTGW=$G
        P=$(pgrep -nx dhcpcd); [ -n "$P" ] && LASTDHCPPID=$P

        # On healthy ticks, and never in observe mode.
        [ "$MODE" = "recover" ] && prefer_router
    fi

    date +%s > "$STAMP"   # the epoch is the stamp, so no date -r needed
    TICK=$((TICK + POLL))
    if [ "$TICK" -ge "$HEARTBEAT" ]; then
        echo "  .. alive $(date '+%Y-%m-%d %H:%M:%S')  ipv4=$NOW" >> "$LOG" 2>&1
        TICK=0
    fi
    sleep "$POLL"
done
