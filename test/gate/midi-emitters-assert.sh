#!/bin/sh
# The MIDI inventory gate. No Pd, no scratch copy, no device, ~200 ms.
#
#   ./test/gate/midi-emitters-assert.sh
#
# WHAT IT PROVES, and it is the only structural claim in the suite: THESE ARE ALL
# THE MIDI OBJECTS IN THE PATCH. Every other gate asserts what one module does;
# this one asserts that no module has grown a way to talk to a device that no
# gate is watching.
#
# ⛔ IT BELONGS TO NO DEVICE, which is why it is its own gate rather than a line
# inside sp404-assert or volca-assert. A new [noteout] in some future e_ stage is
# not the SP-404's business and not the Volca's, but it is very much the
# instrument's -- and the moment it appears, this goes red and names it.
#
# The count itself lives in MIDI_EXPECT in lib-scratch.sh, shared with every gate
# that makes a scratch copy, so there is one inventory rather than one per gate.
# ⚠️ The reason there were two before is instructive: phase6-assert.sh counted
# [midiout] and phase9-assert.sh counted the other four, so no single place ever
# said what the patch contained, and phase 6's half drifted from five to six with
# nothing noticing.
#
# THE CHECK THAT NEEDS NO Pd IS THE ONE TO REACH FOR FIRST. This reads .pd files
# as text. No timing, no driver, no capture, nothing to go vacuous.
set -u

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

scratch_require "Cut It"

rc=0

echo "=== emitters -- every one has a stub, and every gate rewrites all of them ==="
midi_check_counts "Cut It" "$MIDI_EXPECT" || rc=2

echo
echo "=== inputs -- counted only, because no stub exists for these yet ==="
midi_check_counts "Cut It" "$MIDI_INVENTORY" || rc=2

echo
if [ "$rc" = "0" ]; then
    echo "the MIDI inventory matches: $MIDI_EXPECT $MIDI_INVENTORY"
else
    echo "THE MIDI INVENTORY HAS CHANGED. Read the counts above, decide whether the" >&2
    echo "patch or the inventory is wrong, and if it is the inventory, update" >&2
    echo "MIDI_EXPECT / MIDI_INVENTORY in test/gate/lib-scratch.sh -- and give the" >&2
    echo "new object a gate at the same time." >&2
fi
exit $rc
