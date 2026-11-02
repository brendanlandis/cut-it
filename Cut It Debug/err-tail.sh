#!/bin/sh
# The tail of the error log, flattened for the OLED.
#
# Always exactly four lines, padded with a dash, because main.pd routes them to
# rows by position. Each line is one atom, whitespace turned to dots, since what
# the display does with several OSC arguments is not measured. 21 characters is
# the screen's width, so lines are cut here (C-12).
#
# busybox, not GNU: ash, with busybox tail, tr and cut.
#
# The log is u_err's, left by the instrument. Loading this patch rolls .cur into
# .log, so the session that went wrong is already in .log. ref/module/error.md
LOG=/sdcard/cut-it-err.log

if [ -f "$LOG" ]; then
    tail -n 4 "$LOG" | tr ' \011' '..' | cut -c1-21
else
    echo "no-log-yet"
fi | awk '{ n = n + 1; print } END { while (n < 4) { print "-"; n = n + 1 } }'
