#!/bin/sh
# Wire the rig's MIDI devices to Pd's ALSA ports.
# Called from inside the patch via [shell] — see tools/self-wire.pd.
#
# ALWAYS connect by NAME. Client numbers shift as devices come and go:
# client 28 was the Launchpad, then became the SP-404 when they were swapped.
#
# Pd port map (matches /root/.pdsettings, 4 in / 4 out):
#   Pure Data:0..3  = Midi-In  1..4   -> Pd channels 1-16, 17-32, 33-48, 49-64
#   Pure Data:4..7  = Midi-Out 1..4

aconnect "Launchpad Pro MK3":0 "Pure Data":0    # -> Pd channels 1-16
aconnect "Pure Data":4 "Launchpad Pro MK3":0    # LEDs + SysEx back out
aconnect "nanoKONTROL":0 "Pure Data":1          # -> Pd channels 17-32
aconnect "SP-404MKII":0 "Pure Data":2           # -> Pd channels 33-48
aconnect "Pure Data":6 "SP-404MKII":0           # pad triggers out
