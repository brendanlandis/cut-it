#!/bin/sh
# mic-capture.sh <step>: set the Organelle's line-input gain (Capture, 0-15, 1.5 dB a step) with
# the -6 dB attenuator off, and echo the step the chip reads back and its gain. Run by main.pd through
# [shell]. Loading Cut It puts both back (its codec-gain.sh: attenuator on, Capture 4).
CARD=Codec
amixer -c $CARD set 'Capture Attenuate Switch (-6dB)' off >/dev/null 2>&1 || true
amixer -c $CARD set Capture "$1" >/dev/null 2>&1 || true
step=$(amixer -c $CARD sget Capture 2>/dev/null | awk '/Front Left:/ {print $4; exit}')
# The chip reads back the step, not dB: 1.5 dB a step from 0, with the attenuator off.
echo "${step:-?} +$(awk -v s="${step:-0}" 'BEGIN{printf "%.1f", s * 1.5}')dB"
