#!/bin/sh
# Wire this probe's own ALSA MIDI links. Run once at load, by main.pd through [shell].
#
# Loading a patch drops Pd's ALSA links (item 228), and an unwired probe reads
# as a device that ignores the inquiry. Every device in and out, by name, as
# "Cut It/wire.sh" does; each line may fail without stopping the rest.

# --- Launchpad Pro MK3 -- Pd in/out 1. THE CONTROL: it is known to answer. ------
aconnect "Launchpad Pro MK3":0 "Pure Data":0  2>/dev/null || true
aconnect "Pure Data":4 "Launchpad Pro MK3":0  2>/dev/null || true

# --- nanoKONTROL -- Pd in/out 2 ------------------------------------------------
aconnect "nanoKONTROL":0 "Pure Data":1        2>/dev/null || true
aconnect "Pure Data":5 "nanoKONTROL":0        2>/dev/null || true

# --- SP-404MKII -- Pd in/out 3 -------------------------------------------------
aconnect "SP-404MKII":0 "Pure Data":2         2>/dev/null || true
aconnect "Pure Data":6 "SP-404MKII":0         2>/dev/null || true

# Undo mother's autoconnect to Midi-In 1, the Launchpad's channel block, for
# every device that is not the Launchpad, since the numbers move.
aconnect -d "nanoKONTROL":0 "Pure Data":0     2>/dev/null || true
aconnect -d "SP-404MKII":0 "Pure Data":0      2>/dev/null || true
aconnect -d "USB Uno MIDI Interface":0 "Pure Data":0 2>/dev/null || true

# How many links exist, not which.
echo "wired-$(aconnect -l | grep -c "Connecting To")"
