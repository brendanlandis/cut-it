#!/bin/sh
# The phone link's headless gate -- ref/device/phone.md. No eyes, no phone, no
# hardware, ~35 s.
#
#   ./test/gate/phone-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/phone-assert.sh -v       and the detail behind every check, and
#                                        every decoded datagram
#   ./test/gate/phone-assert.sh --keep   leave the scratch dir, driver and capture
#
# The oracle is a real socket: u_net already emits to one, so the gate points it
# at 127.0.0.1 and reads what arrives. No scratch copy, nothing rewritten.
exec python3 "$(dirname "$0")/phone-assert.py" "$@"
