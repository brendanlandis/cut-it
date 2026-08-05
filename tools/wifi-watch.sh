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
# ⚠️ ANY PROCESS SCAN MATCHING A STRING ALSO MATCHES THE SSH COMMAND CARRYING IT.
# `pgrep -f wifi-watch` is the famous case, but a hand-rolled scan over /proc/*/cmdline
# has exactly the same flaw and reported "2 instances" when there was one. It is not
# about pgrep -- it is about searching for your own command line. Use the pidfile.
# ⚠️ AND IF THE SWEEP ALSO RELAUNCHES, IT KILLS ITS OWN SHELL: the launch line
# contains this script's path, so the sweep matches itself. Scan and launch in
# SEPARATE commands, and skip $$.
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
# ⚠️ ONLY REMOVE THE PIDFILE IF IT IS STILL OURS. A stop-then-start races: `kill`
# returns immediately, and the dying watcher's EXIT trap ran AFTER the replacement
# had written its own pid -- deleting it. That left a watcher running with no
# pidfile, which silently DISARMS the single-instance guard above, so the next
# launch would have made two. Seen 2026-08-05.
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
# plan-v03.md sends UNRECOVERED straight to the spare-card A/B, on the
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

# ⚠️ THE QUESTION THE LINK PROBE LEAVES OPEN, and it is the one that decides the
# fix: is dhcpcd ASKING and getting no answer, or not asking at all? Those need
# completely different repairs and nothing so far distinguishes them.
#
# `dhcpcd -T` is TEST MODE: it runs a full DHCP exchange and prints the result
# WITHOUT configuring the interface, so it is safe to run in the broken state and
# safe to run beside the real daemon (verified on a healthy device, with the real
# dhcpcd running, 2026-08-05).
#
#   "soliciting a DHCP lease" + "offered X from Y"  -> THE SERVER IS ANSWERING.
#       The running dhcpcd is the problem: it is wedged, not starved. A watchdog
#       that restarts it is then the fix.
#   "soliciting a DHCP lease" and then nothing      -> THE SERVER IS NOT ANSWERING
#       this client. The problem is upstream -- router lease pool, a MAC-based
#       rule, or the AP dropping our DHCP frames -- and no amount of restarting
#       dhcpcd will help.
dhcpprobe() {
    echo "  --- DHCP PROBE (test mode -- asks, but configures nothing) ---"
    timeout 30 dhcpcd -T -t 25 wlan0 2>&1 |
        grep -iE "soliciting|offered|timed out|no useful|carrier|ifssid" |
        sed 's/^/     /'
    # ⚠️ THIS VERDICT USED TO SAY "an OFFER means the daemon is wedged", AND THAT
    # WAS WRONG -- it claimed more than the probe measures. `dhcpcd -T` STOPS AT
    # THE OFFER and never sends a REQUEST, so it only ever exercises the half of
    # the exchange that works. A full debug capture (plan-tests item 184) showed
    # dhcpcd behaving perfectly: carrier lost -> hooks -> carrier acquired ->
    # re-solicit -> DISCOVER with correct backoff, and NO OFFER AT ALL.
    echo "     READ THIS NARROWLY:"
    echo "       an OFFER = the server answers a DISCOVER from this client, and"
    echo "                  nothing more. It does NOT mean the daemon is wedged."
    echo "       no OFFER = nothing is answering this client on this AP right now."
}

# ---------------------------------------------------------------------------
# PREVENTION, not recovery -- and this is the only rung that stops the fault
# happening at all.
#
# WHY. The failures all occur while associated to the SATELLITE. On it, DHCP
# solicitations go unanswered and the association itself is unstable (two
# spontaneous carrier losses observed). On the ROUTER the same radio leases in
# seconds, and the router is also 10 dB STRONGER from the work room -- so
# staying on it costs nothing and is better on both counts. Items 179-184.
#
# ⚠️ IT IS A PREFERENCE, NOT A PIN. If the router is not visible, this does
# nothing and the device is free to use the satellite -- a pinned BSSID would
# strand it if that AP ever went away. Prevention must not become a new
# single point of failure.
#
# ⚠️ `wpa_cli roam` ONLY TARGETS A BSS ALREADY IN THE SCAN CACHE, so the scan
# is required. A bare roam returns FAIL on a fresh supplicant -- and a FAIL
# there looks exactly like a healthy device (item 175).
#
# ⛔ OFF BY DEFAULT, AND THAT IS A DELIBERATE REVERSAL. It was built, tested and
# measured working (satellite -> router in 13 s), and then switched off for two
# reasons that only became clear once it ran:
#
#   1. ⚠️ THE STEER ITSELF DROPS IPv4. A roam is a carrier change, so dhcpcd
#      deconfigures every time it fires. That trades ONE RARE long outage for
#      FREQUENT short ones -- a bad bargain if the fault is fixed.
#   2. ⚠️ IT HIDES THE ANSWER. Keeping the device off the satellite means the
#      fault can never recur, so we could never learn whether the Orbi firmware
#      update (2.7.5.6 -> 2.7.6.6, 2026-08-05) actually fixed it. THE
#      PREVENTION MASKS THE EXPERIMENT.
#
# The reordered ladder is the safety net instead: ~20 s to recover rather than
# the old 2.5 minutes. Re-enable with:
#
#     PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh
#
# ⚠️ If it is ever re-enabled PERMANENTLY, say why in plan-tests -- an unexplained
# steer looks like a fix for a fault that may no longer exist.
PREFER_BSSID=${PREFER_BSSID:-}

curbssid() { iw dev wlan0 link 2>/dev/null | sed -n 's/^Connected to \([0-9a-f:]*\).*/\1/p'; }

prefer_router() {
    [ -n "$PREFER_BSSID" ] || return 0
    CUR=$(curbssid)
    [ -n "$CUR" ] || return 0                    # unassociated: nothing to steer
    [ "$CUR" = "$PREFER_BSSID" ] && return 0     # already where we want to be

    # ⚠️ `scan dump` READS THE CACHE; a bare `iw ... scan` TRIGGERS A NEW ONE.
    # The first version of this guard used the bare form immediately after a
    # `wpa_cli scan`, so the two contended and it returned NOT VISIBLE for an
    # AP sitting at -47 dBm. A false negative here is silent and total: the
    # steer would simply never fire, and the prevention would look installed
    # while doing nothing. Measured 2026-08-05.
    wpa_cli -i wlan0 scan >/dev/null 2>&1
    sleep 6
    iw dev wlan0 scan dump 2>/dev/null | grep -qi "^BSS $PREFER_BSSID" || {
        echo "  .. on $CUR, but $PREFER_BSSID is not visible -- leaving it alone" >> "$LOG"
        return 0
    }
    {
        echo
        echo "  ~~ PREFERRED-AP STEER: on $CUR, moving to $PREFER_BSSID"
        echo "     (the satellite is where every observed failure happened; the"
        echo "      router is stronger AND reliable -- items 179-184)"
        wpa_cli -i wlan0 roam "$PREFER_BSSID" 2>&1 | sed 's/^/     /'
        sleep 6
        A=$(ipv4); B=$(curbssid)
        echo "     now on: ${B:-unassociated}   ipv4: ${A:-NONE}"
    } >> "$LOG" 2>&1
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
                dhcpprobe
                if [ "$MODE" = "recover" ]; then
                    # ⚠️ TWO CORRECTIONS TO THIS LADDER, BOTH FROM REAL FAILURES.
                    #
                    # 1. THE WAITS WERE 15/20/25s AND TOO SHORT TO BE CONCLUSIVE.
                    #    The association alone took ~8s in the 2026-08-04 dmesg.
                    #    An UNRECOVERED verdict must mean "it did not come back",
                    #    not "we did not wait".
                    #
                    # 2. ⚠️ RUNG 2 USED `dhcpcd -k`, WHICH ONLY RELEASES THE LEASE
                    #    -- a wedged daemon stayed wedged and the "restart"
                    #    restarted nothing. `-x` EXITS it. And rung 3 ran
                    #    scripts/wifi-config.sh, WHICH IS A STALE FACTORY TEMPLATE
                    #    HARDCODED TO SSID "name" / PASSPHRASE "pass" -- so it
                    #    killed a working supplicant and put nothing in its place.
                    #    Both verdicts it produced were partly self-inflicted.
                    #    The ladder now ends with the sequence the FRONT PANEL
                    #    uses, which is the only one observed to work without a
                    #    reboot (2026-08-05).
                    # ⚠️ THIRD CORRECTION, 2026-08-05: THE ORDER IS NOW
                    # STRONGEST-FIRST, NOT GENTLEST-FIRST, AND THAT IS
                    # DELIBERATE. Rungs 1 and 2 have now been measured failing
                    # on this fault FOUR times, at 45s each, before the rung
                    # that works -- over two and a half minutes of dead network
                    # to reach the only thing that has ever helped. Neither of
                    # them changes which AP you are on, and that is what has to
                    # change (items 179-184).
                    #
                    # ⚠️ AND THE OLD 60s WAIT ON RUNG 3 WAS TOO SHORT: it
                    # expired BEFORE the recovery it was waiting for landed and
                    # printed UNRECOVERED about a rung that had just worked
                    # (item 178). A generous wait is free when it goes first.
                    #
                    # The weak rungs are KEPT, just demoted. A future fault with
                    # a different cause may well be fixed by them, and deleting
                    # them would discard the discriminator that made these
                    # captures readable in the first place.
                    echo "  --- RECOVERY LADDER (most effective first) ---"
                    try "full reassociate"         "bash /sdcard/wifi-reassociate.sh"       90 ||
                    try "dhcpcd renew"             "dhcpcd -n wlan0"                        45 ||
                    try "dhcpcd EXIT+restart"      "dhcpcd -b -x wlan0; sleep 2; dhcpcd -b wlan0" 45 ||
                    echo "  >> UNRECOVERED -- every rung failed, INCLUDING the one the front panel uses."
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

        # PREVENTION runs on HEALTHY ticks, which is the whole point: steering
        # back while the network still works costs one roam and no downtime,
        # where waiting for the address to vanish costs the ladder. Only in
        # recover mode -- observe mode must change nothing.
        [ "$MODE" = "recover" ] && prefer_router
    fi

    date +%s > "$STAMP"   # liveness: the epoch IS the stamp, so no date -r needed
    TICK=$((TICK + POLL))
    if [ "$TICK" -ge "$HEARTBEAT" ]; then
        echo "  .. alive $(date '+%Y-%m-%d %H:%M:%S')  ipv4=$NOW" >> "$LOG" 2>&1
        TICK=0
    fi
    sleep "$POLL"
done
