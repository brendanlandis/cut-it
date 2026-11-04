#!/bin/sh
# Wire this probe's ALSA MIDI links to the SP-404MKII. Run once at load, by main.pd through [shell].
#
# Loading a patch drops Pd's ALSA links (item 228). Out of Pd's port 3 to the 404, as
# "Cut It/wire.sh" wires it, to trigger the pad and move the looper. Each line may fail without
# stopping the rest.

aconnect "Pure Data":6 "SP-404MKII":0         2>/dev/null || true

# Undo mother's autoconnect of the 404 to Midi-In 1: its pads would reach the patch as keys.
aconnect -d "SP-404MKII":0 "Pure Data":0      2>/dev/null || true

if aconnect -l | grep -q "SP-404MKII"; then
    echo "404 wired"
else
    echo "no 404 found"
fi
