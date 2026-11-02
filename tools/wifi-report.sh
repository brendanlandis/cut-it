#!/bin/sh
# Pull the wifi watcher's evidence off the device once wifi-poll.sh has found
# something, and summarize it.
#
#   ./tools/wifi-report.sh              summary of everything SINCE THE LAST MARK
#   ./tools/wifi-report.sh --all        the whole log, marks ignored
#   ./tools/wifi-report.sh --mark       draw a line: everything above is analyzed
#   ./tools/wifi-report.sh --full       and the raw log
#
# The log accumulates, so a mark is what lets a report answer "again, since I
# last looked?". What each outcome means is on the Organelle's Reference page,
# Wifi.
set -u
HOST=${HOST:-root@organelle.local}
LOG=/sdcard/wifi-watch.log
MARK="=== ANALYZED UP TO HERE"
SINCE=1
case "${1:-}" in
    --all)  SINCE=0 ;;
    --mark) MARK_ONLY=1 ;;
    --full) ;;
    "")     ;;
esac

if [ "${MARK_ONLY:-0}" = 1 ]; then
    ssh -o ConnectTimeout=8 "$HOST" \
        "echo '$MARK $(date '+%Y-%m-%d %H:%M:%S') (by wifi-report.sh --mark) ===' >> $LOG" \
        && echo "marked. The next ./tools/wifi-report.sh starts from here." \
        || { echo "could not reach $HOST to write the mark" >&2; exit 1; }
    exit 0
fi

if ! ssh -o ConnectTimeout=8 "$HOST" true 2>/dev/null; then
    echo "Cannot reach $HOST."
    echo
    echo "⚠️  That is not proof of anything on its own -- and note the trap from item 133:"
    echo "    ssh can KEEP WORKING over IPv6 link-local while IPv4 is entirely gone."
    echo "    If ssh works but nothing else does, check:  ip addr show wlan0 | grep 'inet '"
    echo
    echo "If the device is genuinely off the network, the log survives on /sdcard."
    echo "Power-cycle it, wait for it to rejoin, then run this again -- nothing is lost."
    exit 1
fi

# Sliced on the device, so every grep below reads the slice unchanged.
if [ "$SINCE" = 1 ]; then
    if ssh "$HOST" "grep -q '^$MARK' $LOG" 2>/dev/null; then
        ssh "$HOST" "awk '/^$MARK/{buf=\"\"; next} {buf = buf \$0 ORS} END{printf \"%s\", buf}' $LOG > /tmp/wifi-slice.log"
        LOG=/tmp/wifi-slice.log
        echo "(showing everything SINCE THE LAST MARK -- use --all for the whole log)"
    else
        echo "(no mark in the log yet -- showing everything. Use --mark when you have written a finding up)"
    fi
fi

echo "=== summary ======================================================="
ssh "$HOST" "
    if [ ! -f $LOG ]; then echo '  no $LOG -- was the watcher ever started?'; exit 0; fi
    echo \"  watcher started : \$(grep -c 'wifi-watch started' $LOG) time(s)\"
    echo \"  transitions     : \$(grep -c TRANSITION $LOG)\"
    echo \"  recovered by    :\"
    grep 'RESULT: RECOVERED' $LOG | sed 's/^/     /' || echo '     (none recorded)'
    echo \"  unrecovered     : \$(grep -c UNRECOVERED $LOG)\"
    echo
    echo '  --- every transition, with the time it happened ---'
    grep -A1 '^TRANSITION' $LOG | grep -E 'TRANSITION|time:' | sed 's/^/     /'
    echo
    echo '  --- was it still associated when IPv4 went? (the crux) ---'
    grep -A4 '^TRANSITION' $LOG | grep -E 'assoc:' | sed 's/^/     /'
    echo
    echo '  --- liveness heartbeats: FIRST THREE, then LAST THREE ---'
    echo '  ⚠️ THE MIDDLE IS ELIDED -- these two groups are NOT contiguous. Heartbeats'
    echo '     are 30 min apart, so the count below tells you how much is hidden.'
    echo '     ALSO CHECK THE WALL CLOCK before calling any span anomalous: a long'
    echo '     gap here is usually just time passing while nobody was watching.'
    echo '     Total heartbeats in the log:'
    grep -c '\.\. alive' $LOG | sed 's/^/       /'
    echo '     --- first ---'
    grep '\.\. alive' $LOG | head -3 | sed 's/^/     /'
    echo '     --- last ---'
    grep '\.\. alive' $LOG | tail -3 | sed 's/^/     /'
"

echo
echo "=== current state ================================================="
ssh "$HOST" '
    echo "  ipv4      : $(ip -4 addr show wlan0 2>/dev/null | grep -o "inet [0-9.]*" || echo NONE)"
    echo "  assoc     : $(iw dev wlan0 link 2>/dev/null | head -2 | tr "\n" " ")"
    echo "  procs     : wpa_supplicant=$(pgrep -x wpa_supplicant || echo -) dhcpcd=$(pgrep -x dhcpcd || echo -)"
    echo "  uptime    : $(cut -d. -f1 /proc/uptime)s"
    P=$(cat /sdcard/wifi-watch.pid 2>/dev/null)
    if kill -0 "$P" 2>/dev/null; then echo "  watcher   : alive (pid $P)"; else echo "  watcher   : NOT RUNNING -- restart before the next attempt"; fi
'

if [ "${1:-}" = "--full" ]; then
    echo
    echo "=== raw log ======================================================="
    ssh "$HOST" "cat $LOG"
fi

echo
echo "Next: hand this to an agent along with plan-v04.md, which says"
echo "what each outcome means and what to do about it."
