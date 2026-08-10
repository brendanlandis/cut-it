#!/bin/sh
# Re-wire the rig ONLY when the set of MIDI devices has changed.
# Forked by u_present on a slow heartbeat, from /tmp/patch.
#
# ⛔ WHY THIS EXISTS: A DEVICE THAT WAS NEVER LOST IS NEVER RECOVERED.
# u_present's bounded recovery is gated on something being LOST, and a device
# registered `none` -- the Volca, which transmits nothing and can never be
# polled -- has no clock, so it can never be lost. Boot the instrument with the
# Volca's interface unplugged and every pollable layer answers, nothing is lost,
# the spigot stays shut, the counter never starts, and no wire.sh fork is ever
# scheduled. Plug the interface in afterwards and it enumerates within a second
# and sits COMPLETELY UNSUBSCRIBED, forever. Item 285.
#
# ✅ Observed on the rig 2026-08-10, not reconstructed: 'USB Uno MIDI Interface'
# enumerated with no `Connecting To` and no `Connected From`, on a session that
# had been up 1 day 21 hours.
#
# ⚠️ AND IT IS THE LIKELIER DIRECTION IN A ROOM. You power the rig up, then plug
# the Volca in. Nothing is wrong from the instrument's point of view, so nothing
# warns -- the remedy was a reload, or unplugging a DETECTABLE device to trick
# the recovery into running, which nobody would guess.

# ⛔ THE HASH COVERS CLIENT NAMES AND NOT SUBSCRIPTIONS, AND THAT IS THE WHOLE
# TRICK. `aconnect -l` prints "Connecting To:" lines under each client, so
# hashing the lot would change the moment wire.sh connected anything -- the
# watcher would see its own work as a change and re-wire again on the next tick,
# forever. ✅ Measured both ways on the device: with the grep the hash is
# BYTE-IDENTICAL before and after a wire.sh run, so one device event costs one
# re-wire.
NEW=$(aconnect -l 2>/dev/null | grep '^client' | md5sum)
STATE=/tmp/cut-it-wire-state
OLD=$(cat "$STATE" 2>/dev/null)

if [ "$NEW" = "$OLD" ]; then
    # ⚠️ SILENT ON THE QUIET PATH, deliberately. This runs every few seconds for
    # the whole life of the patch; a line per tick would bury the error log it
    # shares, and u_present has nothing to report when nothing happened.
    exit 0
fi

echo "$NEW" > "$STATE"

# ⛔ THE FIRST RUN ALWAYS "CHANGES", because there is no state file yet -- so it
# re-wires once at startup. That is harmless (wire.sh is idempotent, ✅ measured:
# 9 connections twice in a row) and it is one extra fork per load, not per tick.
sh wire.sh

# ⚠️ IT SAYS WHICH DEVICES IT SAW, not just that it fired. A re-wire that
# happened because the SP-404 was unplugged looks identical to one caused by a
# Volca being plugged in, and the difference is the whole diagnosis.
echo "wire-watch: device list changed -- $(aconnect -l 2>/dev/null | grep -c '^client') clients"
