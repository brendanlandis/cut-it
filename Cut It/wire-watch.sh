#!/bin/sh
# Re-wire the rig only when its MIDI devices or their connections have changed.
# Forked by u_present on a slow heartbeat, from /tmp/patch.
#
# It exists because u_present's recovery is gated on a loss, and a device
# registered none, the FM-1, can never be lost: plugged in after
# boot, it would sit unsubscribed forever (item 285, ref/module/presence.md).

# The hash covers all of `aconnect -l`, the clients and what each is connected
# to. The names alone miss a device that comes back inside one heartbeat: an
# FM-1 switched off and on returns under the same name and client number with
# its connections gone, and stayed unwired (measured 2026-11-24).
STATE=/tmp/cut-it-wire-state
NEW=$(aconnect -l 2>/dev/null | md5sum)
OLD=$(cat "$STATE" 2>/dev/null)

if [ "$NEW" = "$OLD" ]; then
    # Silent when nothing changed: this runs every few seconds.
    exit 0
fi

# The first run always changes, with no state file yet: one harmless re-wire at
# startup, wire.sh being idempotent.
sh wire.sh

# Kept as wire.sh left it, never as it was found: wire.sh changes the
# connections, and the next heartbeat would take that for a change and re-wire
# again, forever (item 292).
aconnect -l 2>/dev/null | md5sum > "$STATE"

# Say how many clients it saw, not just that it fired: an unplug and a plug-in
# look the same otherwise.
echo "wire-watch: devices or connections changed -- $(aconnect -l 2>/dev/null | grep -c '^client') clients"
