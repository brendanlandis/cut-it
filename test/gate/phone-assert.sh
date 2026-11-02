#!/bin/sh
# The phone link's headless gate -- ref/device/phone.md. No eyes, no phone, no
# hardware, ~35 s.
#
#   ./test/gate/phone-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/phone-assert.sh -v       and the detail behind every check, and
#                                        every decoded datagram
#   ./test/gate/phone-assert.sh --keep   leave the scratch dir, driver and capture
#
# The driver is generated into the gate's own scratch directory on every run --
# edit phone-assert-drive-gen.py, never a .pd.
#
# THE ORACLE IS A REAL SOCKET, so unlike the MIDI gates there is no copy of the
# patch and nothing is rewritten. [midiout] is a built-in class with no side
# channel, so reading what the patch sent a device means swapping the object out
# in a throwaway copy; u_net already emits to a socket, so this gate simply
# points it at 127.0.0.1 and reads what arrives. "Cut It/" is never touched
# either way.
exec python3 "$(dirname "$0")/phone-assert.py" "$@"
