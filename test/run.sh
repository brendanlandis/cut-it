#!/bin/sh
# Every gate, and every bench, in one command. Run it before calling a phase done.
#
#   ./test/run.sh                 the gates. Mac-only, ~5 min, the default
#   ./test/run.sh --all           the gates, then every bench
#   ./test/run.sh --bench midi    one bench, no gates
#   ./test/run.sh --help          the rest
#
# ⚠️ READ THE RESULT: LINE. DO NOT GREP FOR IT. Exactly one line matches, and the
# exit status is trustworthy on its own. `grep -E 'ALL|FAILED'` also matches the
# per-gate "--- FAILED:" lines -- a broken patch has been committed that way.
#
# ⛔ THIS FILE IS A SHIM AND STAYS ONE. It exists so the command and PD=... keep
# working exactly as they did when this was 109 lines of sh named check-all.sh.
# Everything real is in test/runner/. Adding logic here would put the gate list
# in two places, which is the drift this project keeps removing.
exec python3 "$(dirname "$0")/runner/run.py" "$@"
