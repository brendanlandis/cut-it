#!/bin/sh
# The test runner's own gate -- test/runner/. No Pd, no device, under a second.
#
#     ./test/gate/runner-assert.sh          # run it
#     ./test/gate/runner-assert.sh -v       # and the detail behind every check
#
# The only thing that exercises the runner's failure paths; why it answers for
# no ref/ page is in test/README.md.
set -e

cd "$(dirname "$0")/../.."

exec python3 test/gate/runner-assert.py "$@"
