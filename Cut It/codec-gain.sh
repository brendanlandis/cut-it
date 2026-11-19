#!/bin/sh
# Set the Organelle's audio chip, the S2's WM8731. Run once per load by u_root
# through [shell].
#
# It has no digital volume to stage against: its one output level, Master, is
# the factory's (-2 dB). The input is the line input with all the gain the chip
# has, Capture 31, +12 dB, which is also the factory's; set rather than assumed,
# so the steps mean the same thing at every load. Mic Boost acts only on the Mic
# input, which the Input Mux does not select. ref/module/audio.md
#
# Every line may fail: a missing control must not stop the boot. Their output
# goes nowhere, since [shell] hands every line to Pd: one echo, at the end, for
# the by-hand console, where a silent run looks like a missing script.
CARD=audioinjectorpi
amixer -c $CARD set 'Input Mux' 'Line In' >/dev/null 2>&1 || true
amixer -c $CARD set Capture 31 >/dev/null 2>&1 || true
m=$(amixer -c $CARD sget Master 2>/dev/null | awk '/Front Left:/ {print $3; exit}')
c=$(amixer -c $CARD sget Capture 2>/dev/null | awk '/Front Left:/ {print $3; exit}')
echo "codec-gain: Master ${m:-?} Capture ${c:-?}"
