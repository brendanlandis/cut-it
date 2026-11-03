#!/bin/sh
# Every gate, in one command. Mac-only, ~1 min. The hands-on checks are
# test/checklists/, run by a person at the rig.
#
# Read the RESULT: line or the exit status. `grep -E 'ALL|FAILED'` also matches
# the per-gate "--- FAILED:" lines.
#
# A shim, so the gate list lives in one place, test/runner/.
exec python3 "$(dirname "$0")/runner/run.py" "$@"
