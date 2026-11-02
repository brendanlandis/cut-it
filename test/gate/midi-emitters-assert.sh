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
# The count itself lives in MIDI_EXPECT in test/gate/lib_scratch.py, shared with
# every gate that makes a scratch copy, so there is one inventory rather than one
# per gate -- see midi-emitters-assert.py.
#
# THE CHECK THAT NEEDS NO Pd IS THE ONE TO REACH FOR FIRST. This reads .pd files
# by record. No timing, no driver, no capture, nothing to go vacuous.
exec python3 "$(dirname "$0")/midi-emitters-assert.py" "$@"
