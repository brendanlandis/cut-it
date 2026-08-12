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
# ⚠️ The reason there were two before is instructive: the old phase 6 gate counted
# [midiout] and the split gates counted the other four, so no single place ever
# said what the patch contained, and phase 6's half drifted from five to six with
# nothing noticing.
#
# THE CHECK THAT NEEDS NO Pd IS THE ONE TO REACH FOR FIRST. This reads .pd files
# as text. No timing, no driver, no capture, nothing to go vacuous.
set -u

cd "$(dirname "$0")/../.."

. test/gate/lib-scratch.sh

scratch_require "Cut It" "Cut It Debug"

rc=0

echo "=== emitters -- every one has a stub, and every gate rewrites all of them ==="
midi_check_counts "Cut It" "$MIDI_EXPECT" || rc=2

echo
echo "=== inputs -- counted only, because no stub exists for these yet ==="
if [ -n "$MIDI_INVENTORY" ]; then
    midi_check_counts "Cut It" "$MIDI_INVENTORY" || rc=2
else
    echo "   none -- every MIDI class in the patch has a stub"
fi

# ⛔ AND THE CLOSED QUESTION, which is the one this gate's header claims to
# answer. The two checks above walk a list WE wrote and ask the patch about each
# entry, so a class nobody thought of is invisible to both -- and when the
# inventory emptied, its arm became a loop over nothing that returned 0. This
# walks every MIDI class Pd has and asks the list.
echo
echo "=== the closed question -- no MIDI class outside the inventory ==="
midi_scan_unknown "Cut It" || rc=2

# ⛔ THE SECOND DEPLOYABLE, AND IT IS NOT A FORMALITY. Every count above is
# scoped to "Cut It", so before this arm existed a [notein] in "Cut It Debug" was
# not merely uncounted -- it was INVISIBLE, and this gate would have gone on
# claiming "these are all the MIDI objects in the patch" while a second patch
# grew ways to talk to the rig that nothing watched. A directory is as good a
# hiding place as an object.
echo
echo "=== the debug patch -- its own inventory, and the same closed question ==="
midi_check_counts "Cut It Debug" "$MIDI_DEBUG_EXPECT" || rc=2
midi_scan_unknown "Cut It Debug" "$MIDI_DEBUG_EXPECT" || rc=2

echo
if [ "$rc" = "0" ]; then
    echo "the MIDI inventory matches: $MIDI_EXPECT $MIDI_INVENTORY"
    echo "and the debug patch's: $MIDI_DEBUG_EXPECT"
else
    echo "THE MIDI INVENTORY HAS CHANGED. Read the counts above, decide whether the" >&2
    echo "patch or the inventory is wrong, and if it is the inventory, update" >&2
    echo "MIDI_EXPECT / MIDI_INVENTORY in test/gate/lib-scratch.sh -- and give the" >&2
    echo "new object a gate at the same time." >&2
fi
exit $rc
