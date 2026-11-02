#!/bin/sh
# Make u_state's data directory, and make sure all three of its files exist.
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
