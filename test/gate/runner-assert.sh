#!/bin/sh
# The test runner's own gate -- test/runner/. No Pd, no device, under a second.
#
#     ./test/gate/runner-assert.sh          # run it
#     ./test/gate/runner-assert.sh -v       # and the detail behind every check
#
# ⛔ IT IS THE ONLY THING THAT EVER EXERCISES THE RUNNER'S FAILURE PATHS. A
# hardware bench run that goes well never stalls, never desyncs, is never
# interrupted and never meets an empty console -- so without this, all four
# branches could be dead code and every run would look identical and green.
#
# ⚠️ IT BELONGS TO NO ref/ PAGE, on purpose, exactly as midi-emitters-assert.sh
# does. Its subject is test/README.md: the runner is not a module of the
# instrument and inventing a page for it would put a claim about test tooling on
# the same shelf as claims about the hardware.
set -e

cd "$(dirname "$0")/../.."

exec python3 test/gate/runner-assert.py "$@"
