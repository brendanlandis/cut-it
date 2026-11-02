#!/bin/sh
# The MIDI inventory gate. No Pd, no scratch copy, no device, ~200 ms.
#
#   ./test/gate/midi-emitters-assert.sh
#
# Asserts that these are all the MIDI objects in the patch, so no module grows a
# way to talk to a device that no gate watches. It belongs to no device on
# purpose (test/README.md). The counts are MIDI_EXPECT in lib_scratch.py.
exec python3 "$(dirname "$0")/midi-emitters-assert.py" "$@"
