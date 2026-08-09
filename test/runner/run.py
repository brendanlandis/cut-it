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
import records                                                  # noqa: E402
import steps as S                                               # noqa: E402

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


# ---------------------------------------------------------------------------
# the bench half
# ---------------------------------------------------------------------------
HELP = ("[p]ass  [f]ail  [s]kip  [r]epeat  [u]ndo  [?]the full PASS IF  [q]uit")


def describe(bench, step):
    """The header a person reads before doing anything.

    ⚠️ `need` AND `do` COME BEFORE THE VERDICT PROMPT, never after. A step that
    tells you what to have at hand only once you are already being asked to
    judge it has told you too late.
    """
    tag = " -- HANDS" if step.hands else ""
    print("\n[%d/%d] %s%s" % (step.n, step.of, bench.name, tag))
    print("       %s" % step.title)
    for line in step.meta.get("need", []):
        print("  need   %s" % line)
    if step.meta.get("do"):
        print("  do     %s" % step.meta["do"])
    print("  watch  %s" % step.watch)


def ask(step, allow_undo):
    """The verdict prompt. -> (verdict, note).

    ⛔ NOTHING HERE MAY GUESS. Every path out of this function is something a
    person typed: the one failure mode that would make the whole runner
    worthless is a verdict it invented, and a default-on-empty-input is exactly
    that. Enter re-prompts.
    """
    while True:
        try:
            c = input("  verdict? %s : " % HELP).strip().lower()
        except EOFError:
            return "quit", "stdin closed"
        if c == "p":
            return "pass", ""
        if c == "f":
            return "fail", input("  what went wrong (one line, optional): ").strip()
        if c == "s":
            return "skip", input("  why skip it (one line): ").strip() or "no reason given"
        if c == "r":
            return "repeat", ""
        if c == "u":
            if allow_undo:
                return "undo", ""
            print("  nothing to undo -- this is the first step of the run")
            continue
        if c == "?":
            print("  %s" % step.pass_if)
            continue
        if c == "q":
            return "quit", ""
        print("  not one of those. %s" % HELP)


def run_bench(bench, target, auto_only, start):
    """One bench, start to finish. -> list of records.

    PAPER MODE, and it is why `state` and `midi` were the first two working:
    every step has no actions, so there is nothing to drive. No Pd, no ssh, no
    `killall pd`, and no Launchpad left stranded in Programmer Mode.
    """
    rec = records.Recorder(bench.name, target, auto_only)
    dsha = records.deps_sha(bench.deps)
    print("\n%s\n%s -- %d steps, target %s%s\n%s"
          % (BAR, bench.name, len(bench.steps), target,
             ", --auto-only" if auto_only else "", BAR))

    i = max(0, (start or 1) - 1)
    while i < len(bench.steps):
        step = bench.steps[i]
        describe(bench, step)

        # ⛔ A STEP WHOSE ORACLE IS ABSENT IS A SKIP WITH A REASON, NEVER A PASS.
        # Under --auto-only there is no person, so a step with no predicate has
        # nobody to answer it. Counting that as a pass is how a suite comes to
        # report green over work nothing checked.
        if auto_only and not step.meta.get("check"):
            why = "no predicate, and --auto-only means no person to judge it"
            print("  SKIP   %s" % why)
            rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                            sha=records.step_sha(step.title, step.pass_if),
                            deps_sha=dsha, verdict="skip", auto=True, note=why))
            i += 1
            continue

        verdict, note = ask(step, allow_undo=i > 0)

        if verdict == "repeat":
            continue                                    # describe it again
        if verdict == "undo":
            prev = bench.steps[i - 1]
            rec.append(dict(bench=bench.name, step=prev.n, title=prev.title,
                            sha=records.step_sha(prev.title, prev.pass_if),
                            deps_sha=dsha, verdict="undone", auto=False,
                            note="withdrawn by the person running it"))
            i -= 1
            continue
        if verdict == "quit":
            rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                            sha=records.step_sha(step.title, step.pass_if),
                            deps_sha=dsha, verdict="interrupted", auto=False,
                            note=note))
            print("\n  stopped at step %d. Resume with:" % step.n)
            print("      ./test/run.sh --bench %s --target %s --from %d"
                  % (bench.name, target, step.n))
            break

        rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                        sha=records.step_sha(step.title, step.pass_if),
                        deps_sha=dsha, verdict=verdict, auto=False, note=note))
        i += 1

    rec.close()
    return rec.rows


def bench_summary(name, rows, total):
    """One line per bench, and the counts that PASS depends on."""
    tally = {}
    for row in rows:                      # append-only, so the last one wins
        if row["verdict"] != "undone":
            tally[row["step"]] = row["verdict"]
    counts = {v: sum(1 for x in tally.values() if x == v)
              for v in ("pass", "fail", "skip", "interrupted")}
    counts["never"] = total - len(tally)
    bad = counts["fail"] or counts["skip"] or counts["interrupted"] or counts["never"]
    print(" %-4s %-12s %2d steps   %2d passed  %2d failed  %2d skipped  %2d not run"
          % ("FAIL" if bad else "ok", name, total, counts["pass"],
             counts["fail"], counts["skip"],
             counts["interrupted"] + counts["never"]))
    return counts


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

    if bench_rows:
        print(BAR)
        total = {"pass": 0, "fail": 0, "skip": 0, "interrupted": 0, "never": 0}
        for name, rows, n in bench_rows:
            for k, v in bench_summary(name, rows, n).items():
                total[k] += v
        print()
        print(" Steps    %d passed, %d failed, %d skipped, %d not run"
              % (total["pass"], total["fail"], total["skip"],
                 total["interrupted"] + total["never"]))
        for label, n in (("failed", total["fail"]), ("skipped", total["skip"]),
                         ("not run", total["interrupted"] + total["never"])):
            if n:
                problems.append("%d step%s %s" % (n, "" if n == 1 else "s", label))

    if problems:
        print("RESULT: FAIL -- %s" % ", ".join(problems))
        return 1

    print(BAR)
    if bench_rows:
        print("RESULT: PASS -- every gate, and every step of every bench selected.")
        return 0
    print("RESULT: PASS -- all gates.")
    print()
    print("⚠️  That is the Mac. It is not the device, and this project's own history")
    print("    says the difference matters: Phase 6 passed 25/25 on the Mac twice and")
    print("    shipped three bugs. Hands on the hardware are still the last word.")
    return 0


def pick_target(bench, asked):
    """-> (target, why). ⚠️ A bench with no actions needs no patch at all."""
    if asked:
        return asked, "asked for"
    if bench.paper:
        return "paper", "every step has no actions, so nothing has to be driven"
    return "device", "the PASS IFs are claims about the real rig"


def do_list():
    """What would run, and how fresh each verdict is. Costs nothing."""
    doc = records.load_latest()
    for name in S.names():
        b = S.load(name)
        dsha = records.deps_sha(b.deps)
        target, _ = pick_target(b, None)
        fresh = sum(1 for s in b.steps
                    if records.freshness(doc, name, s.n, target,
                                         records.step_sha(s.title, s.pass_if),
                                         dsha)[0])
        why = ""
        if fresh < len(b.steps):
            _, why = records.freshness(
                doc, name, b.steps[0].n, target,
                records.step_sha(b.steps[0].title, b.steps[0].pass_if), dsha)
        print(" %-12s %2d steps  target %-6s  %2d fresh%s"
              % (name, len(b.steps), target, fresh,
                 "   -- " + why if why else ""))
    return 0


def main(argv):
    a = parse_args(argv)
    problems = S.check_inventory()
    if problems:
        sys.exit("run.py: " + "; ".join(problems))

    if a.list:
        return do_list()

    if a.bench and a.bench not in S.names():
        sys.exit("run.py: no bench called %r. There are: %s"
                 % (a.bench, ", ".join(S.names())))

    want = [a.bench] if a.bench else (S.names() if (a.all or a.benches) else [])
    gate_failed, gate_ran = ([], 0)
    if not want or a.all:
        gate_failed, gate_ran = gate_half()

    bench_rows = []
    for name in want:
        b = S.load(name)
        target, why = pick_target(b, a.target)
        if target != "paper":
            # Phase B territory. ⛔ SAY SO rather than reporting an empty pass:
            # a bench that silently ran nothing is the single worst thing this
            # runner could do, so it refuses instead.
            sys.exit("run.py: target %r is not built yet -- only `paper` runs "
                     "today, which covers the benches whose every step has no "
                     "actions (%s). %s wants %s: %s"
                     % (target, ", ".join(n for n in S.names() if S.load(n).paper),
                        name, target, why))
        rows = run_bench(b, target, a.auto_only, a.start)
        records.roll_up(rows)
        bench_rows.append((name, rows, len(b.steps)))

    return summarise(gate_failed, gate_ran, bench_rows)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
