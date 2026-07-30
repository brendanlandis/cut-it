#!/bin/sh
# Roll the previous session's error log into the durable one, and open a new
# session with a wall-clock stamp.
#
# Run ONCE PER PATCH LOAD by u_err via [shell] — one fork per load, never per
# error, so nothing shells out while the instrument is being played.
#
# WHY A SHELL SCRIPT AND NOT JUST [text write]. Pd's text write rewrites the
# WHOLE file, so u_err on its own can only ever hold the current session: the
# next patch load would truncate away the last one. That is exactly the wrong
# property when the point is to read back a set the following day. Appending is
# native here. And `date` runs in-process, so every session gets a real wall
# clock without Pd needing a clock it does not have (0.49 vanilla has none) and
# without depending on [shell]'s return path, which is unverified.
#
# THE SPLIT: u_err writes only the CURRENT session, to $CUR. This carries the
# previous one into $LOG. tools/fetch-errors.sh reads BOTH, so a fetch is
# correct even before a roll has happened — which is the normal case, since
# power-cycling the Organelle does not reload the patch.
#
# /sdcard is writable with no remount and survives reboot; /tmp is wiped.
#
# Every step tolerates failure. A full or missing SD card must not stop the
# patch booting, exactly as in wire.sh.

LOG=/sdcard/cut-it-err.log
CUR=/sdcard/cut-it-err.cur

# Carry the last session across BEFORE stamping this one, so each BOOT line
# sits above the errors that belong to it.
carried=0
if [ -s "$CUR" ]; then
    carried=$(wc -l < "$CUR" 2>/dev/null | tr -d ' ')
    cat "$CUR" >> "$LOG" 2>/dev/null || true
fi
: > "$CUR" 2>/dev/null || true

printf 'BOOT %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG" 2>/dev/null || true

# Bounded, because this file outlives every session that writes to it. u_err
# bounds $CUR separately, at 200 lines, from inside the patch.
lines=$(wc -l < "$LOG" 2>/dev/null | tr -d ' ')
if [ "${lines:-0}" -gt 400 ]; then
    tail -n 300 "$LOG" > "$LOG.t" 2>/dev/null && mv "$LOG.t" "$LOG" 2>/dev/null || true
fi

# One line per boot to the by-hand SSH console. Nothing else reports that the
# roll happened, and a silent roll is indistinguishable from a missing script.
echo "logroll: carried ${carried:-0} line(s) from the previous session"
