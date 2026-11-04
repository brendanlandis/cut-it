#!/bin/sh
# Wire the rig's MIDI devices to Pd's ALSA ports. Run through [shell] from
# /tmp/patch: by u_init at load, and again by any re-wire.
#
# By NAME, never by client number, because the numbers move between boots
# (Reference, critter-guitari-organelle-1, mother's autoconnect).
#
# Pd port map (matches /root/.pdsettings, 4 in / 4 out):
#   Pure Data:0..3  = Midi-In  1..4   -> Pd channels 1-16, 17-32, 33-48, 49-64
#   Pure Data:4..7  = Midi-Out 1..4
#
# Every line may fail: a device that is not plugged in must not stop the others
# or the boot.

# The nanoKONTROL output carries only the device inquiry, which is how m_nano
# tells an unplugged nano from an untouched one. Without it m_nano is declared
# lost a few seconds into every boot (item 274, ref/module/boot.md).
#
# The Launchpad's third port carries one thing in Programmer Mode: the layout
# announcement a tap on Setup makes, which m_launchpad reads as lp-setup
# (ref/device/launchpad.md). It shares Midi-In 1 with the first.
aconnect "Launchpad Pro MK3":0 "Pure Data":0 2>/dev/null || true  # -> Pd ch 1-16
aconnect "Launchpad Pro MK3":2 "Pure Data":0 2>/dev/null || true  # Setup's announcement
aconnect "Pure Data":4 "Launchpad Pro MK3":0 2>/dev/null || true  # LEDs + SysEx out
aconnect "nanoKONTROL":0 "Pure Data":1       2>/dev/null || true  # -> Pd ch 17-32
aconnect "Pure Data":5 "nanoKONTROL":0       2>/dev/null || true  # device inquiry out

# Pd's port 3 is the Waldorf Streichfett's (2026-11-04; the SP-404's until it
# left the rig): its replies and panel come in, notes and SysEx go out.
aconnect "Streichfett":0 "Pure Data":2       2>/dev/null || true  # -> Pd ch 33-48
aconnect "Pure Data":6 "Streichfett":0       2>/dev/null || true  # notes, CC, SysEx out

# The USB->DIN interface is one bidirectional port. The Volca behind it only
# receives; the input is for whatever the interface's DIN IN may carry later.
aconnect "USB Uno MIDI Interface":0 "Pure Data":3 2>/dev/null || true  # -> Pd ch 49-64
aconnect "Pure Data":7 "USB Uno MIDI Interface":0 2>/dev/null || true  # notes + CC to the Volca
# The nanoKEY shares Midi-In 4, whose DIN IN carries nothing: its keys arrive
# on Pd ch 49-64. Address it by client name and port number: its port's name
# ends in two spaces (Reference, korg-nanokey).
aconnect "nanoKEY":0 "Pure Data":3           2>/dev/null || true  # -> Pd ch 49-64

# Undo mother's own autoconnect, which puts the lowest-numbered client on Pd's
# Midi-In 1, m_launchpad's channel block, whichever device that is. Every device
# that is not the Launchpad, because the order moves between boots
# (ref/module/boot.md, Traps).
aconnect -d "nanoKONTROL":0 "Pure Data":0    2>/dev/null || true
aconnect -d "Streichfett":0 "Pure Data":0    2>/dev/null || true
aconnect -d "nanoKEY":0 "Pure Data":0        2>/dev/null || true
aconnect -d "USB Uno MIDI Interface":0 "Pure Data":0 2>/dev/null || true

# Report what actually connected, for the run-it-by-hand console.
echo "wire.sh: $(aconnect -l | grep -c "Connecting To") connections"
