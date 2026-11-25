#!/bin/sh
# Make u_state's data directory, make sure all three of its files exist, and have
# the card under it keep a write within a second.
#
#   sh state-dir.sh /sdcard/cut-it-state
#
# Run once at load by u_state through [shell]. cut-it-recover.txt is the recover
# breadcrumb u_init writes and u_map reads, kept here for the same reason as the
# state: outside the patch folder. The files are touched because they are read
# at every boot and a missing file prints three lines (items 143 and 147,
# ref/module/state.md). touch never truncates, so it is safe at every load.
#
# On the Mac [shell] is a stub, so main-dev.pd passes a directory that exists.
set -eu

DIR=${1:?usage: state-dir.sh <data-directory>}

mkdir -p "$DIR"
touch "$DIR/cut-it-auto.txt" "$DIR/cut-it-manual.txt" "$DIR/cut-it-recover.txt"

# The card commits its journal every second, not every five. A file here is
# written whole and renamed into place (u_song) or truncated and written
# (u_state), and ext4 holds either in its journal until the next commit: until
# then a power cut gives back the file as it was. A sync after each write would
# close the gap too, but it forks from Pd's thread, 1.5 ms on the S2, which the
# audio hears (Reference, critter-guitari-organelle-s2). The setting lasts until
# the Organelle restarts, so it is made at every load. It may fail, and must not
# stop the boot: the echo, to the console, says what the card reads back. Never
# the root's own card, and nothing off the device, where /proc/mounts is absent.
if [ -r /proc/mounts ]; then
    MNT=$(df -P "$DIR" 2>/dev/null | awk 'NR == 2 { print $6 }')
    if [ -n "$MNT" ] && [ "$MNT" != / ]; then
        sudo -n mount -o remount,commit=1 "$MNT" >/dev/null 2>&1 || true
        echo "state-dir: $MNT $(awk -v m="$MNT" '$2 == m { print $4 }' /proc/mounts)"
    fi
fi
