#!/bin/sh
# Re-stage the Organelle's audio chip (an SGTL5000) against its hiss. Run once
# per load by u_root through [shell].
#
# The factory's setup.sh cuts the DAC digitally (PCM 170, -11 dB) and makes it
# up in the headphone amp (127, +12 dB, its maximum), which turns the
# converter's own noise up with it. Re-staged, the hiss went at the same overall
# level, by ear on the rig (2026-11-03). They last until a reboot, when setup.sh puts the factory's
# back, hence every load. The chip's scales and the measurements: Reference,
# critter-guitari-organelle-1, under SGTL5000. ref/module/audio.md
#
# Every line may fail: a missing control must not stop the boot. Their output
# goes nowhere, since [shell] hands every line to Pd: one echo, at the end.

# The on-board codec by its ALSA id, not the default card.
CARD=Codec

# PCM goes up only once Headphone has come down: raised alone it is 11 dB
# louder than the factory's, so the step between them, or a failure, is quieter.
amixer -c $CARD set Headphone 105 >/dev/null 2>&1 \
    && amixer -c $CARD set PCM 192 >/dev/null 2>&1 || true   # +1 dB, then 0 dB

# The input is a dynamic mic with no preamp (2026-11-04), so it gets all the
# gain the chip has: the -6 dB attenuator off and Capture 15, +22.5 dB. Sung
# close, an SM58 peaked about 3 dB under full scale against hiss at -71 dBFS
# (Reference, critter-guitari-organelle-1). Set rather than assumed, so the
# steps mean the same thing at every load.
amixer -c $CARD set 'Capture Attenuate Switch (-6dB)' off >/dev/null 2>&1 || true
amixer -c $CARD set Capture 15 >/dev/null 2>&1 || true

# What the chip reads back, for the by-hand console: a silent run looks like a
# missing script, and a failed one like the factory's numbers.
level() { amixer -c $CARD sget "$1" 2>/dev/null | awk '/Front Left:/ {print $4; exit}'; }
pcm=$(level PCM)
hp=$(level Headphone)
cap=$(level Capture)
att=$(amixer -c $CARD sget 'Capture Attenuate Switch (-6dB)' 2>/dev/null \
      | awk '/Mono:/ {print $NF; exit}' | tr -d '[]')
echo "codec-gain: PCM ${pcm:-?} Headphone ${hp:-?} Capture ${cap:-?} attenuate ${att:-?}"
