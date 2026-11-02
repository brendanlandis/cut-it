#!/bin/sh
# Has the Organelle's wifi dropped since you started watching? Leave it in a
# terminal; it rings and notifies when it finds something.
#
#   ./tools/wifi-poll.sh              check every 60s
#   POLL=30 ./tools/wifi-poll.sh      faster
#   HOST=root@192.168.1.15 ./tools/wifi-poll.sh
#
# It counts TRANSITION lines in the device watcher's log rather than trusting
# reachability, since a drop can recover between two polls (tools/README.md),
# so it says loudly when that watcher is dead. Findings go to
# ~/cut-it-wifi-findings.log.
set -u

HOST=${HOST:-root@organelle.local}
POLL=${POLL:-60}
FIND="$HOME/cut-it-wifi-findings.log"
STARTED=$(date '+%Y-%m-%d %H:%M:%S')
START_EPOCH=$(date +%s)

LAST_TRANS=""
BASELINE=""
REPORTED_DOWN=""
FOUND=0
LAST_EVENT="-"
DOWN_SINCE=""
RELAUNCHED=""

note() {   # a macOS notification, best effort -- never fatal
    osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true
}

hms() {    # seconds -> compact duration
    s=$1; d=$((s/86400)); h=$(((s%86400)/3600)); m=$(((s%3600)/60))
    [ "$d" -gt 0 ] && printf "%dd %dh" "$d" "$h" && return
    [ "$h" -gt 0 ] && printf "%dh %dm" "$h" "$m" && return
    printf "%dm" "$m"
}

probe() {  # one ssh round trip; prints "ipv4|transitions|stampage" or nothing
    # No `|| echo 0` after grep -c: it exits non-zero on a zero count and prints
    # the 0 anyway, so the fallback would make it "0\n0".
    ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" '
        IP=$(ip -4 addr show wlan0 2>/dev/null | grep -o "inet [0-9.]*" | cut -d" " -f2 | head -1)
        T=$(grep -c TRANSITION /sdcard/wifi-watch.log 2>/dev/null); T=$(echo "$T" | head -1)
        S=$(cat /sdcard/wifi-watch.alive 2>/dev/null | head -1)
        if [ -n "$S" ]; then A=$(( $(date +%s) - S )); else A=99999; fi
        echo "${IP:-NONE}|${T:-0}|${A}"
    ' 2>/dev/null | head -1
}

trap 'printf "\n"; exit 0' INT TERM

while true; do
    NOW=$(date '+%H:%M:%S')
    RAW=$(probe)

    if [ -n "$RAW" ]; then
        IP=$(echo "$RAW" | cut -d"|" -f1)
        TRANS=$(echo "$RAW" | cut -d"|" -f2)
        STAMP=$(echo "$RAW" | cut -d"|" -f3)
        REACH=yes
        DOWN_SINCE=""
        REPORTED_DOWN=""
    else
        IP=NONE; TRANS=""; STAMP=""; REACH=no
        [ -z "$DOWN_SINCE" ] && DOWN_SINCE=$(date +%s)
    fi

    # --- the actual detection -------------------------------------------------
    if [ -n "$TRANS" ]; then
        if [ -z "$LAST_TRANS" ]; then
            # What is already in the log is the baseline, not a find.
            LAST_TRANS=$TRANS
            BASELINE=$TRANS
            [ "$TRANS" -gt 0 ] && LAST_EVENT="baseline: $TRANS transition(s) already logged before this run"
        elif [ "$TRANS" -gt "$LAST_TRANS" ]; then
            FOUND=1
            LAST_EVENT="$(date '+%H:%M:%S') -- device logged a new transition (total $TRANS)"
            printf "\007"
            note "Cut It: wifi DROP detected" "The Organelle logged a transition. Run: ./tools/wifi-report.sh"
            echo "$(date '+%Y-%m-%d %H:%M:%S')  DROP -- transitions $LAST_TRANS -> $TRANS" >> "$FIND"
            LAST_TRANS=$TRANS
        fi
    fi

    # Once per outage, not once per run.
    if [ "$REACH" = no ] && [ -z "$REPORTED_DOWN" ]; then
        REPORTED_DOWN=1
        FOUND=1
        LAST_EVENT="$(date '+%H:%M:%S') -- UNREACHABLE from the Mac"
        printf "\007"
        note "Cut It: Organelle unreachable" "No ssh response. Could be the wifi fault, or powered off."
        echo "$(date '+%Y-%m-%d %H:%M:%S')  UNREACHABLE from the Mac" >> "$FIND"
    fi

    # --- the glanceable block -------------------------------------------------
    UP=$(hms $(( $(date +%s) - START_EPOCH )))
    clear 2>/dev/null || true
    echo "  cut-it wifi watch     started $STARTED     checking every ${POLL}s"
    echo "  ------------------------------------------------------------------"
    if [ "$REACH" = yes ]; then
        echo "  organelle      UP          $IP"
    else
        D=$(hms $(( $(date +%s) - ${DOWN_SINCE:-$(date +%s)} )))
        echo "  organelle      UNREACHABLE   for $D"
    fi
    # The backstop for a watcher that died mid-session; systemd starts it at
    # boot (ref/wifi.md, item 244). It counts consecutive tries and says when
    # they are not taking: on 2026-08-08 a relaunch did nothing for five and a
    # half hours, for a reason still not known.
    if [ "$REACH" = yes ] && [ -n "$STAMP" ] && [ "$STAMP" -gt 120 ]; then
        ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" \
            'setsid sh /sdcard/wifi-watch.sh recover >/dev/null 2>&1 </dev/null &' 2>/dev/null
        TRIES=$(( ${TRIES:-0} + 1 ))
        echo "$(date '+%Y-%m-%d %H:%M:%S')  watcher was dead -- relaunched (try $TRIES)" >> "$FIND"
        RELAUNCHED="$(date '+%H:%M:%S')"
    fi
    # A fresh tick means the last relaunch took.
    [ -n "$STAMP" ] && [ "$STAMP" -lt 60 ] && TRIES=0

    if [ -n "$STAMP" ]; then
        if [ "$STAMP" -lt 60 ]; then
            echo "  device watcher alive       last tick ${STAMP}s ago"
        else
            echo "  device watcher ** DEAD **  no tick for ${STAMP}s -- restart it, see below"
        fi
    else
        echo "  device watcher unknown     (device unreachable)"
    fi
    echo "  drops logged   ${TRANS:-?}"
    echo "  watching for   $UP"
    echo "  last check     $NOW"
    [ -n "$RELAUNCHED" ] && echo "  note           device watcher was dead -- relaunched at $RELAUNCHED"
    if [ "${TRIES:-0}" -ge 3 ]; then
        echo "  ⛔ RELAUNCH IS NOT TAKING  $TRIES consecutive tries, still no tick."
        echo "                 systemd should own it -- check on the device:"
        echo "                 systemctl status wifi-watch.service"
    fi
    echo "  ------------------------------------------------------------------"
    if [ "$FOUND" = 1 ]; then
        echo "  ANYTHING NEW?     *** YES *** (since this run started)"
        echo "  $LAST_EVENT"
        echo
        echo "  next:  ./tools/wifi-report.sh      (pulls the evidence off the device)"
        echo "  log:   $FIND"
    else
        echo "  ANYTHING NEW?     no (baseline: ${BASELINE:-0} already in the log)"
    fi
    echo
    echo "  ctrl-c to stop"

    sleep "$POLL"
done
