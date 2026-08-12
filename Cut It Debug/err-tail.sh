#!/bin/sh
# The tail of the error log, flattened for the OLED.
#
# ⛔ IT ALWAYS EMITS EXACTLY FOUR LINES, and that is what lets the patch route
# them by position. main.pd counts the lines coming out of [shell] and sends
# line N to screenLine N+1 -- so a script that emitted three lines on a short
# log and four on a long one would put the newest error on a different row every
# time, which is unreadable at a glance and impossible to assert. Short output
# is padded with a dash.
#
# ⛔ EVERY LINE IS ONE ATOM. Pd splits a message on whitespace and screenLine
# hands the whole message to mother, so a line containing spaces arrives as
# several OSC arguments and what the display does with those is not something
# this project has measured. Whitespace becomes dots here instead. The same rule
# holds in net-probe.sh, and it is why every line this patch draws is a single
# symbol.
#
# ⚠️ 21 CHARACTERS IS THE SCREEN, not a suggestion -- the OLED draws until it
# runs off the right edge and nothing downstream can shorten a line (C-12 makes
# the same point about error text). Truncated here, at the only place that knows.
#
# ⚠️ busybox, NOT GNU. The Organelle's /bin/sh is ash and its tail, tr and cut
# are busybox applets -- so this stays to options all three have had forever.
#
# The log is u_err's, written by the INSTRUMENT and not by this patch, which is
# the whole point: this reads what Cut It left behind after it broke.
#
# ⚠️ .cur IS THE CURRENT SESSION AND .log IS THE DURABLE ONE. logroll.sh rolls
# the first into the second once per load -- and loading THIS patch is a load --
# so by the time anyone reads this the session that went wrong is already in
# .log. See ref/module/error.md.
LOG=/sdcard/cut-it-err.log

if [ -f "$LOG" ]; then
    tail -n 4 "$LOG" | tr ' \011' '..' | cut -c1-21
else
    echo "no-log-yet"
fi | awk '{ n = n + 1; print } END { while (n < 4) { print "-"; n = n + 1 } }'
