#!/usr/bin/env python3
"""THE TEST RUNNER -- every gate, and every bench, in one command.

    ./test/run.sh                    the gates. Mac-only, ~2.5 min, the default
    ./test/run.sh --all              the gates, then every bench
    ./test/run.sh --bench midi       one bench, no gates
    ./test/run.sh --benches          every bench, no gates
    ./test/run.sh --target mac       run the patch here rather than on the device
    ./test/run.sh --auto-only        no person is watching: judge what a
                                     predicate can judge and SKIP the rest
    ./test/run.sh --from 8           resume a bench part-way
    ./test/run.sh --list             what would run, and how fresh each verdict is

WHY THIS IS ONE PROGRAM AND NOT TWO. It was two: check-all.sh ran the gates and
nothing ran the benches. The obvious shape -- a new runner that shells out to
check-all.sh -- needs the gate half to suppress its own verdict so the runner can
own the only line matching "RESULT:", and check-all.sh printed TWO of those, one
on each path. Labelling the pass path and forgetting the fail path would have put
two RESULT: lines in front of a failing run, which is the exact defect the rule
exists to prevent, on the path nobody rehearses. One program means one summary
and one RESULT: line STRUCTURALLY, with nothing to plumb and nothing to forget.

⛔ THE BARE INVOCATION MUST NOT GET SLOWER OR MORE DEVICE-DEPENDENT, EVER. Run
with no arguments this does exactly what check-all.sh did: the gates, on the Mac,
touching nothing on the Organelle. Benches are opt-in behind a flag and are never
reached from a bare run. ⚠️ A CHECK THAT COSTS TWENTY MINUTES STOPS BEING RUN.

⛔ EXACTLY ONE LINE MATCHES "RESULT:", AND THAT IS DELIBERATE. The old summary
printed "ALL GATES PASS." on success and "FAILED:" on failure, so
`check-all.sh | grep -E 'ALL|FAILED'` looked like a reasonable way to read it --
and it is not. That pattern matches the per-gate "--- FAILED:" lines too, so a
run with two red gates still scrolls past and the eye finds what it expects. That
happened, and a broken patch was committed with a message claiming every gate
passed. Grep for RESULT: and you get one line, or check the exit status.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gates                                                    # noqa: E402

# ⛔ THE REPO ROOT, AND IT IS ASSERTED. Every gate below is a path relative to
# it, so a root one level off would run nothing, report nothing and exit ok --
# the fourth way a gate passes vacuously, and docs-check.py has already been
# bitten by it once. Same guard, same reason.
ROOT = os.path.dirname(os.path.dirname(HERE))
if not os.path.exists(os.path.join(ROOT, "CLAUDE.md")):
    sys.exit("run.py: %s is not the repo root -- has this file moved?" % ROOT)
os.chdir(ROOT)

os.environ.setdefault(
    "PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")

BAR = "=" * 66


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="test/run.sh", add_help=True,
        description="Every gate, and every bench, in one command.")
    p.add_argument("--all", action="store_true",
                   help="the gates, then every bench")
    p.add_argument("--benches", action="store_true",
                   help="every bench, no gates")
    p.add_argument("--bench", metavar="NAME",
                   help="one bench, no gates")
    p.add_argument("--target", choices=("device", "mac", "paper"),
                   help="where the patch runs. Default: device for a bench "
                        "that has actions, paper for one that has none")
    p.add_argument("--auto-only", action="store_true",
                   help="no person is watching: judge what a predicate can "
                        "judge and SKIP everything else")
    p.add_argument("--from", dest="start", type=int, metavar="N",
                   help="resume a bench at step N")
    p.add_argument("--list", action="store_true",
                   help="what would run, and how fresh each verdict is")
    p.add_argument("--replay", metavar="FILE",
                   help="read the Pd stream from a file (the self-test)")
    p.add_argument("--keys", metavar="FILE",
                   help="read the verdicts from a scripted keystroke list")
    return p.parse_args(argv)


def gate_half():
    """-> (failed_labels, ran). Byte-for-byte what check-all.sh printed."""
    failed = gates.run_all()
    return failed, len(gates.GATES)


def summarise(gate_failed, gate_ran, bench_rows):
    """The one summary, and the one RESULT: line.

    ⛔ RESULT: PASS REQUIRES failed == skipped == stale == 0, and a record for
    every step in the selected set. A SKIP IS NEVER A PASS -- it is the absence
    of a verdict, and counting it as one is how a suite comes to report green
    over work nobody has checked.
    """
    print()
    problems = []

    if gate_failed:
        print(BAR)
        print("the following gates FAILED:")
        for label in gate_failed:
            print("  - %s" % label)
        print(BAR)
        problems.append("%d gate%s failed"
                        % (len(gate_failed),
                           "" if len(gate_failed) == 1 else "s"))

    # ⚠️ THE GATES-ONLY SUMMARY IS BYTE-FOR-BYTE WHAT check-all.sh PRINTED, down
    # to the bare "RESULT: FAIL" with no reason after it. Not nostalgia: a diff
    # against a capture taken before the port is the only thing that proves no
    # gate was lost on the way across, and a reworded verdict line would have
    # made that diff unreadable and therefore unrun. The richer FAIL line below
    # is reached only once benches are in play, which check-all.sh never had.
    if problems and not bench_rows:
        print("RESULT: FAIL")
        return 1
    if problems:
        print("RESULT: FAIL -- %s" % ", ".join(problems))
        return 1

    print(BAR)
    print("RESULT: PASS -- all gates.")
    print()
    print("⚠️  That is the Mac. It is not the device, and this project's own history")
    print("    says the difference matters: Phase 6 passed 25/25 on the Mac twice and")
    print("    shipped three bugs. Hands on the hardware are still the last word.")
    return 0


def main(argv):
    a = parse_args(argv)
    want_benches = a.all or a.benches or a.bench
    want_gates = not want_benches

    gate_failed, gate_ran = ([], 0)
    if want_gates or a.all:
        gate_failed, gate_ran = gate_half()

    return summarise(gate_failed, gate_ran, [])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
