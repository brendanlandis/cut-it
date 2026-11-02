#!/bin/sh
# Re-wire the rig only when the set of MIDI devices has changed. Forked by
# u_present on a slow heartbeat, from /tmp/patch.
#
# It exists because u_present's recovery is gated on a loss, and a device
# registered none, the Volca, can never be lost: its interface plugged in after
# boot would sit unsubscribed forever (item 285, ref/module/presence.md).

# The hash covers client names, not subscriptions: all of `aconnect -l` would
# change whenever wire.sh connected anything, and the watcher would re-wire
# forever. With the grep it is byte-identical across a re-wire.
NEW=$(aconnect -l 2>/dev/null | grep '^client' | md5sum)
STATE=/tmp/cut-it-wire-state
OLD=$(cat "$STATE" 2>/dev/null)

if [ "$NEW" = "$OLD" ]; then
    # Silent when nothing changed: this runs every few seconds.
    exit 0
fi

echo "$NEW" > "$STATE"

# The first run always changes, with no state file yet: one harmless re-wire at
# startup, wire.sh being idempotent.
sh wire.sh

# Say how many clients it saw, not just that it fired: an unplug and a plug-in
# look the same otherwise.
echo "wire-watch: device list changed -- $(aconnect -l 2>/dev/null | grep -c '^client') clients"
