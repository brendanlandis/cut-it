#!/bin/sh
# Wire this probe's own ALSA MIDI links. Run once at load, by main.pd through [shell].
#
# ⛔ LOADING ANY PATCH DROPS PD'S ALSA CONNECTIONS -- item 228, measured. Loading a
# patch REPLACES THE PD PROCESS: runPatch runs killpatch.sh, which SIGTERMs and then
# SIGKILLs every pd before the new instance starts (item 252). A probe that assumes
# the wiring survived measures SILENCE, and silence from a MIDI probe reads as
# "the device ignores this message" -- which is the wrong conclusion and the exact
# shape of item 225.
#
# ⛔ THE THIRD LINE HAS NEVER EXISTED ANYWHERE IN THIS PROJECT. Cut It's wire.sh
# wires an INPUT from the nanoKONTROL and no output to it, because the nano is a
# control surface and Cut It never has anything to say to it. Asking it a question
# means creating that link for the first time. If the nano turns out to answer a
# device inquiry, the hot-swap detector needs this line in wire.sh too.
#
# ⛔ IT DID ANSWER, AND THE LINE WENT IN. Cut It's wire.sh wires seven links now,
# not six -- item 274. The hot-swap plan had said in writing that "wire.sh itself
# does not change, no connect or disconnect line moves", which was the largest
# documentation hazard it thought it was removing, and it was measurably false:
# the nano's inquiry went out into an unconnected port forever. ⚠️ NOTHING ON THE
# MAC COULD HAVE FOUND IT -- [midiout] and [sysexin] are both stubs there and all
# nineteen gates passed either way.
#
# Pd port map, matching /root/.pdsettings -- 4 in, 4 out:
#   Pure Data:0..3  = Midi-In  1..4
#   Pure Data:4..7  = Midi-Out 1..4
#
# ⚠️ ALWAYS BY NAME, NEVER BY CLIENT NUMBER. They move: after a power cycle on
# 2026-08-06 the order became Launchpad 28, SP-404 32, USB Uno 36, nanoKONTROL 40
# -- the nano had been 32 and the 404 36. See "Cut It/wire.sh".
#
# Every line may fail. A device that is not plugged in must not stop the ones that
# are, and must not stop the probe.

# --- Launchpad Pro MK3 -- Pd in/out 1. THE CONTROL: it is known to answer. ------
aconnect "Launchpad Pro MK3":0 "Pure Data":0  2>/dev/null || true
aconnect "Pure Data":4 "Launchpad Pro MK3":0  2>/dev/null || true

# --- nanoKONTROL -- Pd in/out 2 ------------------------------------------------
aconnect "nanoKONTROL":0 "Pure Data":1        2>/dev/null || true
aconnect "Pure Data":5 "nanoKONTROL":0        2>/dev/null || true

# --- SP-404MKII -- Pd in/out 3 -------------------------------------------------
aconnect "SP-404MKII":0 "Pure Data":2         2>/dev/null || true
aconnect "Pure Data":6 "SP-404MKII":0         2>/dev/null || true

# ⚠️ mother's own alsaconnect.sh wires the LOWEST-NUMBERED client to Midi-In 1,
# which puts whatever enumerated first on the Launchpad's channel block and makes
# one surface publish as two. Undo it defensively -- the client numbers move, so
# every non-Launchpad device gets a line.
aconnect -d "nanoKONTROL":0 "Pure Data":0     2>/dev/null || true
aconnect -d "SP-404MKII":0 "Pure Data":0      2>/dev/null || true
aconnect -d "USB Uno MIDI Interface":0 "Pure Data":0 2>/dev/null || true

# The count is the only thing the patch can learn from here: it says HOW MANY
# links exist, never WHICH devices answered.
echo "wired-$(aconnect -l | grep -c "Connecting To")"
