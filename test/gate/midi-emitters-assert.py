#!/usr/bin/env python3
"""The MIDI inventory gate. No Pd, no scratch copy, no device, well under a second.

    python3 test/gate/midi-emitters-assert.py      (run it as midi-emitters-assert.sh)

WHAT IT PROVES, and it is the only structural claim in the suite: THESE ARE ALL
THE MIDI OBJECTS IN THE PATCH. Every other gate asserts what one module does;
this one asserts that no module has grown a way to talk to a device that no gate
is watching.

The count lives in MIDI_EXPECT in lib_scratch.py, shared with every gate that
makes a scratch copy, so there is one inventory rather than one per gate. ⚠️ The
reason there were two before is instructive: the old phase 6 gate counted
[midiout] and the split gates counted the other four, so no single place ever
said what the patch contained, and phase 6's half drifted from five to six with
nothing noticing.

It reads the .pd files by record through lib_pd -- no timing, no driver, no
capture, nothing to go vacuous.
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

# ⛔ AND THE CLOSED QUESTION, which is the one this gate's header claims to
# answer. The two checks above walk a list WE wrote and ask the patch about each
# entry, so a class nobody thought of is invisible to both -- and when the
# inventory emptied, its arm became a loop over nothing that returned 0. This
# walks every MIDI class Pd has and asks the list.
print()
print("=== the closed question -- no MIDI class outside the inventory ===")
ok &= S.scan_unknown("Cut It")

# ⛔ THE SECOND DEPLOYABLE, AND IT IS NOT A FORMALITY. Every count above is
# scoped to "Cut It", so before this arm existed a [notein] in "Cut It Debug" was
# not merely uncounted -- it was INVISIBLE, and this gate would have gone on
# claiming "these are all the MIDI objects in the patch" while a second patch
# grew ways to talk to the rig that nothing watched. A directory is as good a
# hiding place as an object.
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
