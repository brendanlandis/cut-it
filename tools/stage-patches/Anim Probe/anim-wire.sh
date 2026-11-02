#!/bin/sh
# Wire this probe's own ALSA MIDI links. Run once at load, by main.pd through [shell].
#
# Loading a patch drops Pd's ALSA links (item 228), and unwired this probe would
# read as a Launchpad that stopped tracking the clock. It only sends, so one link
# is enough, and without it no pad lights. By name, as "Cut It/wire.sh" does.

# --- Launchpad Pro MK3 -- Pd out 1. The only device this probe talks to. -------
aconnect "Pure Data":4 "Launchpad Pro MK3":0  2>/dev/null || true

# Undo mother's autoconnect to Midi-In 1: nothing here reads it, but in Live
# Mode the Launchpad floods it with clock (item 250), load on a patch whose job
# is emitting clock on time.
aconnect -d "Launchpad Pro MK3":0 "Pure Data":0      2>/dev/null || true
aconnect -d "nanoKONTROL":0 "Pure Data":0            2>/dev/null || true
aconnect -d "SP-404MKII":0 "Pure Data":0             2>/dev/null || true
aconnect -d "USB Uno MIDI Interface":0 "Pure Data":0 2>/dev/null || true

# How many links exist, not which.
echo "wired-$(aconnect -l | grep -c "Connecting To")"
