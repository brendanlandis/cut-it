#!/bin/sh
# wifi-poll -- leave this running in a terminal and forget about it.
#
# Answers ONE question at a glance: has the Organelle's wifi dropped since you
# started watching? It redraws a small block every minute, and when it finds
# something it rings the bell and raises a macOS notification, so you do not have
# to keep tabbing over.
#
#   ./tools/wifi-poll.sh              check every 60s
#   POLL=30 ./tools/wifi-poll.sh      faster
#   HOST=root@192.168.1.15 ./tools/wifi-poll.sh
#
# ⚠️ IT DOES NOT RELY ON REACHABILITY ALONE. The fault (items 81/133) can drop
# and recover between two polls, and the Mac would never see it. So this reads
# the TRANSITION COUNT out of the device-side watcher's log -- any increase means
# a drop happened, whether or not this script was looking at the time.
#
# It therefore needs /sdcard/wifi-watch.sh running on the Organelle. It says so
# loudly if that is not true, because a quiet "no drops" from a dead watcher is
# the worst possible output.
#
# Findings are appended to ~/cut-it-wifi-findings.log so nothing is lost when the
# terminal scrolls or the session ends.
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
    # ⚠️ grep -c EXITS NON-ZERO when the count is zero, so `|| echo 0` fires as
    # well as the count and you get "0\n0" -- which broke the arithmetic below
    # and printed stray digits into the display. No fallbacks here for that reason.
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
            # ⚠️ TRANSITIONS ALREADY IN THE LOG ARE A BASELINE, NOT A FIND.
            # This used to set FOUND=1 immediately, so once the log had ever
            # recorded anything the display read "*** YES ***" forever and could
            # never answer the only question being asked: did it happen AGAIN?
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

    # ⚠️ ONCE PER OUTAGE, NOT ONCE EVER. The guard used to be [ "$FOUND" = 0 ],
    # so the first event of the run silenced every one after it -- and a fault
    # you are characterising across repeated occurrences is exactly the thing
    # that needs each one recorded.
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
    # THE WATCHER DOES NOT SURVIVE A REBOOT, and a reboot is how this very fault
    # gets recovered -- so recovering used to disarm the detection for the NEXT
    # failure. ✅ SINCE ITEM 244 THAT IS SYSTEMD'S JOB: device/wifi-watch.service
    # starts it at boot. This relaunch is now the BACKSTOP for a watcher that
    # died mid-session, not the primary mechanism.
    #
    # ⛔ AND IT COUNTS ITS OWN FAILURES, because it silently did nothing for five
    # and a half hours on 2026-08-08 while three drops went unrecorded, and the
    # only reason anybody noticed was a six-hour hole in the log read back
    # afterwards. A relaunch that does not take now says so on the screen instead
    # of being retried forever in silence. ⚠️ Why it did nothing that day is
    # STILL NOT ESTABLISHED -- this makes the next occurrence visible, it does
    # not explain the last one.
    if [ "$REACH" = yes ] && [ -n "$STAMP" ] && [ "$STAMP" -gt 120 ]; then
        ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" \
            'setsid sh /sdcard/wifi-watch.sh recover >/dev/null 2>&1 </dev/null &' 2>/dev/null
        TRIES=$(( ${TRIES:-0} + 1 ))
        echo "$(date '+%Y-%m-%d %H:%M:%S')  watcher was dead -- relaunched (try $TRIES)" >> "$FIND"
        RELAUNCHED="$(date '+%H:%M:%S')"
    fi
    # A fresh tick means the last relaunch took. Reset, so TRIES only ever counts
    # CONSECUTIVE failures rather than a lifetime total.
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
