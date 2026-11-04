#!/bin/sh
# Wire this probe's ALSA MIDI links to the SP-404MKII. Run once at load, by main.pd through [shell].
#
# Loading a patch drops Pd's ALSA links (item 228). The 404 only, both ways, as "Cut It/wire.sh"
# wires it: out of Pd's port 3 to trigger pads and move the looper, and into it so a pad struck
# on the 404 selects that pad. Each line may fail without stopping the rest.

aconnect "SP-404MKII":0 "Pure Data":2         2>/dev/null || true
aconnect "Pure Data":6 "SP-404MKII":0         2>/dev/null || true

# Undo mother's autoconnect of the 404 to Midi-In 1.
aconnect -d "SP-404MKII":0 "Pure Data":0      2>/dev/null || true

if aconnect -l | grep -q "SP-404MKII"; then
    echo "404 wired"
else
    echo "no 404 found"
fi
