#!/bin/sh
# Every gate this project has, in one command. Run it before calling a phase done.
#
#   ./test/check-all.sh          run everything, exit non-zero if anything fails
#
# WHY IT EXISTS, and it is a process fix rather than a new test. Phase 8 edited
# u_map, u_init and u_root -- files that Phases 5, 6 and 7 all rest on -- and
# came within one step of shipping without ever re-running THEIR gates. Nothing
# prompted it. The gates were all there, all passing, and all unused.
#
# ⚠️ A GATE YOU HAVE TO REMEMBER TO RUN IS A GATE THAT EVENTUALLY DOES NOT RUN.
# That is the same lesson as `wire.sh` being run by u_init rather than by hand,
# and as deploy.sh doing the syntax check rather than trusting anyone to.
#
# All of this is Mac-side and touches NOTHING on the Organelle: no ssh, no
# deploy, no device. Safe to run at any time, including with the device off.
set -u

cd "$(dirname "$0")/.."

PD=${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}
export PD

FAILED=""
run() {   # $1 = label, rest = command
    label=$1; shift
    printf '\n=== %s\n' "$label"
    if "$@"; then
        echo "--- ok: $label"
    else
        echo "--- FAILED: $label"
        FAILED="$FAILED\n  - $label"
    fi
}

# --- 1. structure -----------------------------------------------------------
# pd-layout-check separates PROBLEM (structural -- a cord onto a comment means
# indices are off by one, which is how every one of the five silent rewirings in
# this project was caught) from note (cosmetic -- crossed cords). Only PROBLEMs
# exit non-zero, so the status is trustworthy on its own.
run "layout and graph structure" python3 test/gate/pd-layout-check.py "Cut It"/*.pd

# --- 1b. the documentation -------------------------------------------------
# The docs restate the same fact in up to ten files and nothing connected the
# copies, so a correction landed in one and the rest went stale. docs-check ties
# them together mechanically: an anchored markdown table must equal the array
# the patch actually plays from, and every pointer to a document must resolve.
# Reintroduce `47 + n` and it goes red AT PAD 5 -- before deploy, before the
# device, in ~200 ms.
run "documentation matches the patch" python3 test/gate/docs-check.py

# --- 2. the deploy gate -----------------------------------------------------
# Pd exits 0 even when objects fail to create, so the gate is OUTPUT, not status.
syntax() {
    rc=0
    for f in "Cut It/main.pd" "Cut It/main-dev.pd"; do
        out=$("$PD" -nogui -noaudio -nomidi -path mac-stubs -send "pd quit" "$f" 2>&1)
        if [ -n "$out" ]; then echo "  $f produced output:"; echo "$out"; rc=1
        else echo "  silent: $f"; fi
    done
    return $rc
}
run "both entry points load in silence (deploy.sh's own gate)" syntax

# --- 3. the benches are generated, not hand-written -------------------------
run "bench step text survived generation" python3 test/bench/bench-verify.py

# --- 4. every phase gate ----------------------------------------------------
# In phase order, because a failure in an early one explains failures after it.
run "Phase 6 gate -- the Launchpad grid"   ./test/gate/phase6-assert.sh
run "the phone link"                       ./test/gate/phone-assert.sh
run "the data store"                       ./test/gate/state-assert.sh
run "Phase 9 gate -- the map and the output devices" ./test/gate/phase9-assert.sh

# ---------------------------------------------------------------------------
# ⛔ EXACTLY ONE LINE MATCHES "RESULT:", AND THAT IS DELIBERATE.
# The old summary printed "ALL GATES PASS." on success and "FAILED:" on failure,
# so `check-all.sh | grep -E 'ALL|FAILED'` looked like a reasonable way to read
# it -- and it is not. That pattern matches the per-gate "--- FAILED:" lines too,
# so a run with two red gates still scrolls past and the eye finds what it
# expects. That happened, and a broken patch was committed with a message
# claiming every gate passed.
#
# Grep for RESULT: and you get one line, or check the exit status. Both are now
# impossible to misread.
echo
if [ -n "$FAILED" ]; then
    echo "=================================================================="
    printf 'the following gates FAILED:%b\n' "$FAILED"
    echo "=================================================================="
    echo "RESULT: FAIL"
    exit 1
fi
echo "=================================================================="
echo "RESULT: PASS -- all gates."
echo
echo "⚠️  That is the Mac. It is not the device, and this project's own history"
echo "    says the difference matters: Phase 6 passed 25/25 on the Mac twice and"
echo "    shipped three bugs. Hands on the hardware are still the last word."
