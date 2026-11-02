#!/bin/sh
# Device presence and the bounded re-wire -- ref/module/presence.md. No eyes, no
# hardware.
#
#   ./test/gate/presence-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/presence-assert.sh -v       and show the detail behind every check
#   ./test/gate/presence-assert.sh --keep   leave the scratch dirs and captures behind
#
# ⛔ IT IS THE ONLY GATE WHOSE STIMULUS IS A SILENCE. Every other gate here pushes
# something in and reads something out. This one withholds the device-inquiry
# reply and asserts on what the patch does about it -- which is the absent-at-load
# case of item 235, the one the Launchpad watchdog was built unable to handle.
#
# ⛔ AND IT IS TWO Pd RUNS, ONE TALLY. The first is the schedule at the shipped
# tick. The second scales u_present's settle and tick by ten -- and NOT its
# counts -- so the eighth attempt and the give-up actually happen, inside nine
# seconds instead of seventy-two. One analyser reads both captures, because two
# would print two `N checks` lines and that number is what proves no assertion
# went missing.
#
# ⚠️ A SILENCE IS ALSO WHAT A BROKEN SCRATCH COPY PRODUCES, so the analyser opens
# with two liveness witnesses -- u_init's own four shell forks, and the fact that
# anything reached [midiout] at all -- and refuses to score the run without them.
#
# ⚠️ NO DSP. g_grid's frame clock is a plain [metro 20] and every stage of the
# watchdog is a message on a timer, so nothing here needs audio.
exec python3 "$(dirname "$0")/scratch-gates.py" presence "$@"
