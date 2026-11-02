#!/bin/sh
# The nanoKONTROL's headless gate -- ref/device/nanokontrol.md. No eyes, no
# hardware, ~17 s.
#
#   ./test/gate/nano-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/nano-assert.sh -v       and show the detail behind every check
#   ./test/gate/nano-assert.sh --keep   leave the scratch dir and capture behind
#
# ⛔ IT IS THE FIRST GATE THAT COULD NOT EXIST BEFORE t_ctlin. m_nano is the main
# control surface of the instrument and it had no headless coverage at all,
# because every one of its paths sits behind [ctlin] and there is no bus behind a
# MIDI input. The shell scratch harness, lib-scratch.sh then, carried a ⬜
# naming that stub as the blocker.
#
# ⚠️ NO DSP. Nothing here needs a clock: every assertion is about decoding a
# controller number into a name, putting it on param, and the ONE row u_map
# draws for it.
exec python3 "$(dirname "$0")/scratch-gates.py" nano "$@"
