#!/usr/bin/env python3
"""The MIDI inventory gate. No Pd, no scratch copy, no device, well under a second.

    python3 test/gate/midi-emitters-assert.py      (run it as midi-emitters-assert.sh)

Asserts that these are all the MIDI objects in the patch. The counts are
MIDI_EXPECT in lib_scratch.py, one inventory shared with every scratch-copy gate.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_scratch as S                                          # noqa: E402

sys.stdout.reconfigure(line_buffering=True)
os.chdir(S.ROOT)
S.require("Cut It", "Cut It Debug")

ok = True

print("=== emitters -- every one has a stub, and every gate rewrites all of them ===")
ok &= S.check_counts("Cut It", S.MIDI_EXPECT)

print()
print("=== inputs -- counted only, because no stub exists for these yet ===")
if S.MIDI_INVENTORY:
    ok &= S.check_counts("Cut It", S.MIDI_INVENTORY)
else:
    print("   none -- every MIDI class in the patch has a stub")

# The two checks above only ask the patch about classes the list names; this
# walks every MIDI class Pd has and asks the list.
print()
print("=== the closed question -- no MIDI class outside the inventory ===")
ok &= S.scan_unknown("Cut It")

# Every count above is scoped to "Cut It", so without this a MIDI object in the
# debug patch would be invisible.
print()
print("=== the debug patch -- its own inventory, and the same closed question ===")
ok &= S.check_counts("Cut It Debug", S.MIDI_DEBUG_EXPECT)
ok &= S.scan_unknown("Cut It Debug", S.MIDI_DEBUG_EXPECT)

print()
if ok:
    print("the MIDI inventory matches: %s %s"
          % (S.spec_text(S.MIDI_EXPECT), S.spec_text(S.MIDI_INVENTORY)))
    print("and the debug patch's: %s" % S.spec_text(S.MIDI_DEBUG_EXPECT))
else:
    for ln in ("THE MIDI INVENTORY HAS CHANGED. Read the counts above, decide whether the",
               "patch or the inventory is wrong, and if it is the inventory, update",
               "MIDI_EXPECT / MIDI_INVENTORY in test/gate/lib_scratch.py -- and give the",
               "new object a gate at the same time."):
        print(ln, file=sys.stderr)
sys.exit(0 if ok else 2)
