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
                if [ "$MODE" = "recover" ]; then
                    echo "  --- RECOVERY LADDER (gentlest first) ---"
                    try "dhcpcd renew"            "dhcpcd -n wlan0"                     15 ||
                    try "dhcpcd release+restart"  "dhcpcd -k wlan0; sleep 2; dhcpcd wlan0" 20 ||
                    try "wpa_supplicant restart"  "killall wpa_supplicant; sleep 2; sh /root/fw_dir/scripts/wifi-config.sh" 25 ||
                    echo "  >> UNRECOVERED -- every rung failed. This is the datum: only a reboot fixes it."
                else
                    echo "  --- observe mode: changing nothing ---"
                fi
            fi
        } >> "$LOG" 2>&1
        LAST=$(ipv4); LAST=${LAST:-NONE}
    fi

    date +%s > "$STAMP"   # liveness: the epoch IS the stamp, so no date -r needed
    TICK=$((TICK + POLL))
    if [ "$TICK" -ge "$HEARTBEAT" ]; then
        echo "  .. alive $(date '+%Y-%m-%d %H:%M:%S')  ipv4=$NOW" >> "$LOG" 2>&1
        TICK=0
    fi
    sleep "$POLL"
done
