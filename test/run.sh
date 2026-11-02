#!/bin/sh
# Every gate, and every bench, in one command.
#
#   ./test/run.sh                 the gates. Mac-only, ~2 min, the default
#   ./test/run.sh --all           the gates, then every bench
#   ./test/run.sh --bench midi    one bench, no gates
#   ./test/run.sh --help          the rest
#
# Read the RESULT: line or the exit status. `grep -E 'ALL|FAILED'` also matches
# the per-gate "--- FAILED:" lines.
#
# A shim, so the gate list lives in one place, test/runner/.
exec python3 "$(dirname "$0")/runner/run.py" "$@"
