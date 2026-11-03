#!/usr/bin/env python3
"""The test runner: every gate, in one command.

    ./test/run.sh                    the gates. Mac-only, ~1 min

On the Mac, touching nothing on the Organelle. The hands-on half is
test/checklists/, which a person runs at the rig.

Exactly one line matches "RESULT:"; read it, or the exit status. The per-gate
"--- FAILED:" lines also match `grep -E 'ALL|FAILED'`.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gates                                                    # noqa: E402

# The repo root, asserted: every gate is a path relative to it, and a root one
# level off would run nothing and exit ok.
ROOT = os.path.dirname(os.path.dirname(HERE))
if not os.path.exists(os.path.join(ROOT, "AGENTS.md")):
    sys.exit("run.py: %s is not the repo root -- has this file moved?" % ROOT)
os.chdir(ROOT)

os.environ.setdefault("PD", os.path.expanduser(
    "~/Applications/Pd-0.57-0.app/Contents/Resources/bin/pd"))

BAR = "=" * 66


def parse_args(argv):
    # No options: anything else, an old --bench among them, is refused rather
    # than ignored, so nobody believes a bench ran.
    p = argparse.ArgumentParser(
        prog="test/run.sh",
        description="Every gate, in one command. The hands-on checks are "
                    "test/checklists/, run by a person at the rig.")
    return p.parse_args(argv)


def summarize(failed):
    """The one summary, and the one RESULT: line."""
    print()
    if failed:
        print(BAR)
        print("the following gates FAILED:")
        for label in failed:
            print("  - %s" % label)
        print(BAR)
        print("RESULT: FAIL -- %d gate%s failed"
              % (len(failed), "" if len(failed) == 1 else "s"))
        return 1

    print(BAR)
    print("RESULT: PASS -- all gates.")
    print()
    print("⚠️  That is the Mac. It is not the device, and this project's own history")
    print("    says the difference matters: Phase 6 passed 25/25 on the Mac twice and")
    print("    shipped three bugs. Hands on the hardware are still the last word.")
    return 0


def main(argv):
    parse_args(argv)
    return summarize(gates.run_all())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
