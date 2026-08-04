#!/bin/sh
# Wire the rig's MIDI devices to Pd's ALSA ports.
# Run from inside the patch by u_init via [shell], from /tmp/patch.
#
# ALWAYS connect by NAME. Client numbers shift as devices come and go:
# client 28 was the Launchpad, then became the SP-404 when they were swapped.
#
# Pd port map (matches /root/.pdsettings, 4 in / 4 out):
#   Pure Data:0..3  = Midi-In  1..4   -> Pd channels 1-16, 17-32, 33-48, 49-64
#   Pure Data:4..7  = Midi-Out 1..4
#
# Every line is allowed to fail. A device that is not plugged in must not stop
# the ones that are, and must not stop the patch booting -- 2>/dev/null || true
# on each. u_init reports progress to the OLED either way; it cannot tell from
# here which devices answered.

aconnect "Launchpad Pro MK3":0 "Pure Data":0 2>/dev/null || true  # -> Pd ch 1-16
aconnect "Pure Data":4 "Launchpad Pro MK3":0 2>/dev/null || true  # LEDs + SysEx out
aconnect "nanoKONTROL":0 "Pure Data":1       2>/dev/null || true  # -> Pd ch 17-32
aconnect "SP-404MKII":0 "Pure Data":2        2>/dev/null || true  # -> Pd ch 33-48
aconnect "Pure Data":6 "SP-404MKII":0        2>/dev/null || true  # pad triggers out

# UNDO mother's OWN AUTO-CONNECT, which is not ours and is actively wrong.
# /root/fw_dir/scripts/alsaconnect.sh wires the LOWEST-NUMBERED MIDI client to
# Pd's Midi-In 1 -- and the nanoKONTROL enumerates below the Launchpad (client
# 28 vs 32), so mother puts the nano on m_launchpad's channel block.
#
# MEASURED 2026-08-03, and it is a real fault in every session on the device:
# one fader move published BOTH slider-1 and a phantom lp-cc-1 to param and disp.
# NOTHING IN Pd CAN FIX IT. Once two devices share Midi-In 1 they are both
# genuinely "channel 1" -- m_launchpad's channel test is correct and powerless.
# It has to be undone here, at the ALSA level.
#
# Invisible on the Mac, which has explicit device slots and no mother, which is
# why Phase 6 shipped without catching it.
#
# Costs no extra fork: wire.sh already runs once per load.
aconnect -d "nanoKONTROL":0 "Pure Data":0    2>/dev/null || true
aconnect -d "SP-404MKII":0 "Pure Data":0     2>/dev/null || true

# Report what actually connected, for the run-it-by-hand console.
echo "wire.sh: $(aconnect -l | grep -c "Connecting To") connections"
