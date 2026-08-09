#!/bin/sh
# Wire this probe's own ALSA MIDI links. Run once at load, by main.pd through [shell].
#
# ⛔ LOADING ANY PATCH DROPS PD'S ALSA CONNECTIONS -- item 228, measured. Loading a
# patch REPLACES THE PD PROCESS: runPatch runs killpatch.sh, which SIGTERMs and then
# SIGKILLs every pd before the new instance starts, so nothing about the old one's
# subscriptions can survive (item 252). A probe that assumes the wiring survived
# measures SILENCE, and silence here reads as "the Launchpad stopped tracking the
# clock" -- which is the exact wrong answer to item 77.
#
# ⚠️ THE PROBE IS OUTPUT-ONLY. It sends mode SysEx, note-on and MIDI clock, and
# listens to nothing at all -- the oracle is a pair of human eyes on the pads. So
# there is exactly one link to make, and the failure is loud: no link means no pad
# lights, which is visible in the first second rather than mistakable for a result.
#
# Pd port map, matching /root/.pdsettings -- 4 in, 4 out:
#   Pure Data:0..3  = Midi-In  1..4
#   Pure Data:4..7  = Midi-Out 1..4
#
# ⚠️ ALWAYS BY NAME, NEVER BY CLIENT NUMBER. They move: after a power cycle on
# 2026-08-06 the order became Launchpad 28, SP-404 32, USB Uno 36, nanoKONTROL 40
# -- the nano had been 32 and the 404 36. See "Cut It/wire.sh".

# --- Launchpad Pro MK3 -- Pd out 1. The only device this probe talks to. -------
aconnect "Pure Data":4 "Launchpad Pro MK3":0  2>/dev/null || true

# ⚠️ mother's own alsaconnect.sh wires the LOWEST-NUMBERED client to Midi-In 1.
# This probe reads nothing, so an unwanted input link cannot corrupt a reading --
# but in Live Mode the Launchpad FLOODS its port with clock (item 250), and that
# is a needless load on a patch whose whole job is to emit clock on time.
aconnect -d "Launchpad Pro MK3":0 "Pure Data":0      2>/dev/null || true
aconnect -d "nanoKONTROL":0 "Pure Data":0            2>/dev/null || true
aconnect -d "SP-404MKII":0 "Pure Data":0             2>/dev/null || true
aconnect -d "USB Uno MIDI Interface":0 "Pure Data":0 2>/dev/null || true

# The count is the only thing the patch can learn from here: it says HOW MANY
# links exist, never WHICH devices answered.
echo "wired-$(aconnect -l | grep -c "Connecting To")"
