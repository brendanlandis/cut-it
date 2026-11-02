#!/bin/sh
# Roll the previous session's error log into the durable one, and open a new
# session with a wall-clock stamp. Run once per load by u_err through [shell].
#
# A script because Pd's text write rewrites the whole file, so u_err can hold
# only the current session ($CUR); appending is native here, and `date` gives
# the wall clock Pd 0.49 lacks. tools/fetch-errors.sh reads both files, so a
# fetch is right even before a roll. ref/module/error.md
#
# Every step tolerates failure: a full or missing SD card must not stop the boot.

LOG=/sdcard/cut-it-err.log
CUR=/sdcard/cut-it-err.cur

# Carry the last session across before stamping this one, so each BOOT line
# sits above its own errors.
carried=0
if [ -s "$CUR" ]; then
    carried=$(wc -l < "$CUR" 2>/dev/null | tr -d ' ')
    cat "$CUR" >> "$LOG" 2>/dev/null || true
fi
: > "$CUR" 2>/dev/null || true

printf 'BOOT %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG" 2>/dev/null || true

# Bounded, since this file outlives every session. u_err bounds $CUR itself.
lines=$(wc -l < "$LOG" 2>/dev/null | tr -d ' ')
if [ "${lines:-0}" -gt 400 ]; then
    tail -n 300 "$LOG" > "$LOG.t" 2>/dev/null && mv "$LOG.t" "$LOG" 2>/dev/null || true
fi

# One line per boot for the by-hand console: a silent roll looks like a missing
# script.
echo "logroll: carried ${carried:-0} line(s) from the previous session"
