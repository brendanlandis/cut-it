#!/usr/bin/env python3
"""THE TEST RUNNER -- every gate, and every bench, in one command.

    ./test/run.sh                    the gates. Mac-only, ~5 min, the default
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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gates                                                    # noqa: E402
import predicates                                               # noqa: E402
import records                                                  # noqa: E402
import steps as S                                               # noqa: E402
import stream                                                   # noqa: E402

# ⚠️ FIFTEEN TO SEE THE FIRST MARKER, FIVE FOR EVERY ONE AFTER IT, and the
# difference is diagnostic rather than arbitrary. Nothing at all within fifteen
# seconds of launch means the bench never loaded -- the signature of scp'ing it
# somewhere the launch line does not name -- and that wants naming by its cause.
# A gap mid-run is a stall, and a stall is recoverable by resending GO.
LOAD_TIMEOUT = 15.0
STEP_TIMEOUT = 5.0

# ⛔ THE FIRED LINE IS NOT THE END OF THE EVIDENCE. bench-gen sends it last so it
# cannot arrive before the actions it describes, which is true for anything
# SYNCHRONOUS -- a bus tap sees its message immediately. The OLED does not:
# g_oled batches into frames and the screen lags about 200 ms, so a window that
# closed at the fired line would ask what the screen showed before it had been
# drawn, and get "nothing". Measured that way first: display 3's predicate
# reported an empty screen while the patch was working perfectly.
# ⚠️ A step can widen this with `wait` in its meta.
SETTLE = 0.4


class Desync(Exception):
    """⛔ THE RUNNER IS RECORDING VERDICTS AGAINST THE WRONG STEP.

    This is never recovered by guessing. A runner that shrugs and carries on
    writes a tally in which every verdict after the slip answers a question
    nobody asked -- which is precisely a gate that lies, and worse than no
    runner at all, because the file it leaves behind is believed.
    """

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
            c = stream.prompt("  verdict? %s : " % HELP).strip().lower()
        except EOFError:
            return "quit", "stdin closed"
        if c == "p":
            return "pass", ""
        if c == "f":
            return "fail", stream.prompt("  what went wrong (one line, optional): ").strip()
        if c == "s":
            return "skip", stream.prompt("  why skip it (one line): ").strip() or "no reason given"
        if c == "r":
            return "repeat", ""
        if c == "u":
            if allow_undo:
                return "undo", ""
            print("  nothing to undo -- this is the first step of the run")
            continue
        if c == "?":
            stream.say("  %s" % step.pass_if)
            continue
        if c == "q":
            return "quit", ""
        stream.say("  not one of those. %s" % HELP)


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
        started = time.time()
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

        # ⛔ PAPER MODE JUDGES WHAT IT CAN. A `file` predicate needs no console
        # and no Pd -- the evidence is on disk -- so the two steps that read the
        # data store are machine-checkable even here, where there is no stream
        # at all. Without this they would still be a person running a shell
        # command and comparing output by eye.
        spec = step.meta.get("check")
        want_targets = step.meta.get("targets")
        if want_targets and target not in want_targets:
            why = "this step only means something on %s" % " or ".join(want_targets)
            stream.say("  SKIP   %s" % why)
            rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                            sha=records.step_sha(step.title, step.pass_if),
                            deps_sha=dsha, verdict="skip", auto=True, note=why))
            i += 1
            continue
        if spec:
            # ⛔ A PREDICATE THAT NEEDS A CONSOLE CANNOT BE JUDGED HERE, AND
            # ASKING IT ANYWAY IS A FALSE FAILURE. There is no Pd in paper mode
            # and therefore no window, so `evaluate(spec, [])` hands every bus
            # kind an empty list: _bus_lines finds nothing, `has` finds nothing,
            # and the step reports AUTO FAIL on a rig that is working perfectly.
            # midi carries FOUR of those, so a bare `./test/run.sh --all` failed
            # four steps of a passing bench -- and every recorded midi run used
            # `--target device`, which is why nobody had met it.
            #
            # ⚠️ THIS LEAVES midi UNABLE TO REACH A CLEAN PASS IN PAPER MODE, AND
            # THAT IS HONEST. Four of its steps genuinely cannot be judged
            # without a patch running, and a skip says so where a fail lied.
            # ⛔ Do not "fix" it by making midi non-paper: paper is what lets
            # state and midi run with no Pd, no ssh, and therefore no Launchpad
            # stranded in Programmer Mode.
            judgeable, needs_console = predicates.offline(spec)
            if not judgeable:
                why = ("%s reads the console and paper mode has none -- "
                       "no Pd is running to produce a window"
                       % " and ".join("`%s`" % k for k in needs_console))
                stream.say("  SKIP   %s" % why)
                rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                                sha=records.step_sha(step.title, step.pass_if),
                                deps_sha=dsha, verdict="skip", auto=True,
                                note=why))
                i += 1
                continue
            if step.hands:
                try:
                    stream.prompt("  press enter when you have done that: ")
                except EOFError:
                    break
            ok, w, g = predicates.evaluate(spec, [], {"step_start": started})
            stream.say("  %s   want %s\n         got  %s"
                       % ("AUTO PASS" if ok else "AUTO FAIL", w, g))
            rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                            sha=records.step_sha(step.title, step.pass_if),
                            deps_sha=dsha, verdict="pass" if ok else "fail",
                            auto=True, note="", want=w, got=g))
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


def _drain(src, window, seconds):
    """Keep reading for `seconds`, appending everything to the predicate window.

    ⚠️ IT DRAINS RATHER THAN SLEEPS. A plain sleep would leave the lines sitting
    in the queue, and they would then be read as the NEXT step's window -- which
    is how a predicate comes to be answered by the previous step's traffic.
    """
    if not src.realtime:
        # Nothing to wait for: the whole stream already exists, and draining it
        # on a wall clock would consume steps that have not been described yet.
        return
    end = time.time() + seconds
    while True:
        left = end - time.time()
        if left <= 0:
            return
        line = src.readline(min(0.2, left))
        if line is not None:
            window.append(line)


def check_marker(m, line, expect, bench):
    """⛔ THE PATCH'S OWN STEP NUMBER AND TITLE, BOTH, AGAINST THE TABLE.

    The number alone is not enough: a bench regenerated from a reordered table
    still counts 1, 2, 3 while every title has moved, and a runner checking only
    the count would record a full set of verdicts against the wrong questions
    and report PASS.
    """
    got_n, got_of, got_title = int(m.group(1)), int(m.group(2)), m.group(3).strip()
    if got_n != expect.n:
        raise Desync("the patch announced step %d where the table expects %d\n"
                     "  line: %s" % (got_n, expect.n, line.strip()))
    if got_of != expect.of:
        raise Desync("the patch says %d steps where the table holds %d -- the "
                     "bench on the other end was generated from a different "
                     "table\n  line: %s" % (got_of, expect.of, line.strip()))
    if got_title != expect.title.strip():
        raise Desync("step %d's title does not match the table\n"
                     "  table: %s\n  patch: %s"
                     % (expect.n, expect.title.strip(), got_title))


def run_bench_driven(bench, target, auto_only, start, src):
    """A bench with a patch on the other end. -> (rows, ok).

    THE INTERACTION, and it is the bench's, not ours. Each step takes TWO GOs:
    one runs the step that was just described, the next describes the following
    one. That is what keeps the PASS IF on screen and STILL while it is read,
    and it is why the loop below sends GO twice per step rather than once.
    """
    rec = records.Recorder(bench.name, target, auto_only)
    dsha = records.deps_sha(bench.deps)
    stream.say("\n%s\n%s -- %d steps, target %s%s\n%s"
               % (BAR, bench.name, len(bench.steps), target,
                  ", --auto-only" if auto_only else "", BAR))

    def record(step, verdict, note, auto=False, want=None, got=None):
        return rec.append(dict(
            bench=bench.name, step=step.n, title=step.title,
            sha=records.step_sha(step.title, step.pass_if), deps_sha=dsha,
            verdict=verdict, auto=auto, note=note, want=want, got=got))

    try:
        # -- the bench has to announce itself before anything else is true ---
        try:
            m, line = src.wait_for(S.RE_STEP, LOAD_TIMEOUT)
        except stream.Stalled:
            stream.say(
                "\n  THE BENCH NEVER LOADED. Nothing announced itself in %g s.\n"
                "  That is not a stalled run -- it is a bench that is not there.\n"
                "  The usual cause is the file having been copied somewhere the\n"
                "  launch line does not name. /tmp is wiped on reboot, which is\n"
                "  why the benches live on /sdcard." % LOAD_TIMEOUT)
            rec.close()
            # ⚠️ THE False HERE IS REDUNDANT AND KNOWINGLY SO. With no records
            # at all the summary already reports every step as not run and
            # fails, so flipping this to True changes nothing observable --
            # confirmed by mutation. It stays because "reported PASS having run
            # nothing" is the worst thing this runner could do, and one
            # unnecessary guard on that is cheaper than finding out the summary
            # was refactored.
            return [], False

        # ⛔ LET THE INSTRUMENT FINISH BOOTING BEFORE THE FIRST GO. Everything
        # collected during the wait joins nothing -- it is thrown away on
        # purpose, because it belongs to the boot rather than to any step.
        if src.boot_settle:
            stream.say("  ... letting the patch finish booting (%g s)"
                       % src.boot_settle)
            _drain(src, [], src.boot_settle)

        # --from: walk the PATCH forward to meet us, because a bench always
        # starts at step 1 however far in we want to resume.
        # ⛔ RECORD NOTHING FOR THE STEPS WALKED PAST. They were not run, and a
        # resumed run that quietly filled them in would turn "I checked the
        # second half" into a claim about the whole bench.
        i = max(0, (start or 1) - 1)
        while int(m.group(1)) < i + 1:
            stream.say("  ... walking past step %s unjudged (--from %d)"
                       % (m.group(1), i + 1))
            src.go()
            src.wait_for(S.RE_FIRED, STEP_TIMEOUT)
            src.go()
            m, line = src.wait_for(S.RE_STEP, STEP_TIMEOUT)

        while True:
            step = bench.steps[i]
            check_marker(m, line, step, bench)
            describe(bench, step)

            if not auto_only:
                # ⛔ NEVER AUTO-ANSWER THIS. GO sent before the finger is on the
                # pad judges the step against nothing at all, and the verdict
                # that comes back is about an empty console.
                #
                # ⛔ AND IT IS UNCONDITIONAL, WHICH IT DID NOT USED TO BE. The
                # guard read `step.hands and not auto_only`, so a step carrying a
                # `do` waited for you and EVERY OTHER STEP called go() on the
                # line after describe() printed its watch text -- the thing you
                # are told to look at had already happened by the time you
                # finished the sentence telling you to look at it. launchpad 1-17
                # are all non-hands and all visual, so that was seventeen steps of
                # one bench. ⚠️ THIS IS THE EXACT FAILURE THE MANUAL-STEPPING
                # REWRITE EXISTED TO REMOVE -- the old timer-driven shape "put the
                # console text and the physical device in motion at the same
                # moment, so you could read one or watch the other and not both"
                # -- and the fix reached hands steps only, because hands steps are
                # the ones anybody tested by hand. A STEP THAT REQUIRES NOTHING TO
                # BE DONE STILL REQUIRES TO BE READ.
                #
                # ⚠️ BOTH WORDINGS CARRY THE LITERAL "press enter".
                # runner-assert's SIGINT fixture waits on that substring to know
                # the child has blocked on a person; reword past it and that
                # fixture waits out its whole deadline instead.
                try:
                    stream.prompt("  press enter when you are ready: "
                                  if step.hands else
                                  "  press enter when you have read this: ")
                except EOFError:
                    # Input ran out where a person was expected. That is the end
                    # of the run, not permission to carry on without one.
                    record(step, "interrupted", "input ended before the step ran")
                    stream.say("\n  stopped at step %d. Resume with:" % step.n)
                    stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                               % (bench.name, target, step.n))
                    break

            src.go()
            window = []
            try:
                fm, fline = src.wait_for(S.RE_FIRED, STEP_TIMEOUT, collect=window)
            except stream.Stalled:
                stream.say("\n  STALLED at step %d -- GO was sent and nothing "
                           "fired within %g s." % (step.n, STEP_TIMEOUT))
                record(step, "interrupted", "stalled mid-run: GO sent, no fired line")
                rec.close()
                return rec.rows, False
            if int(fm.group(1)) != step.n:
                raise Desync("step %d was described but step %s fired\n  line: %s"
                             % (step.n, fm.group(1), fline.strip()))

            # ⚠️ A MEASURE STEP ARMS A TIMED COUNT AND THE NUMBER MEANS NOTHING
            # UNTIL THE WINDOW CLOSES. The latch starts at -1 so an early read
            # says so instead of lying, but reading -1 and calling it a failure
            # would be this runner's own impatience reported as a bug in the
            # clock. Wait it out.
            if step.measure:
                stream.say("  ... %g s measurement window is running"
                           % (S.WINDOW_MS / 1000.0))
                _drain(src, window, S.WINDOW_MS / 1000.0 + 0.5)
            else:
                _drain(src, window, step.meta.get("wait", SETTLE))

            # ⛔ A STEP ITS TARGET CANNOT JUDGE IS A SKIP WITH A REASON. midi 1
            # wants 57 BPM, which comes from knobs.txt -- a file mother reads at
            # boot and no Mac has. On a Mac that step legitimately reads 120, so
            # asserting there would be asserting the absence of hardware.
            want_targets = step.meta.get("targets")
            if want_targets and target not in want_targets:
                why = "this step only means something on %s" % " or ".join(want_targets)
                stream.say("  SKIP   %s" % why)
                record(step, "skip", why, auto=True)
                i += 1
                src.go()
                if i >= len(bench.steps):
                    break
                try:
                    m, line = src.wait_for(S.RE_STEP, STEP_TIMEOUT)
                except stream.Stalled:
                    stream.say("\n  STALLED after step %d." % step.n)
                    rec.close()
                    return rec.rows, False
                continue

            spec = step.meta.get("check")
            if spec:
                ok, want, got = predicates.evaluate(spec, window)
                stream.say("  %s   want %s\n         got  %s"
                           % ("AUTO PASS" if ok else "AUTO FAIL", want, got))
                record(step, "pass" if ok else "fail", "", auto=True,
                       want=want, got=got)
                i += 1
                src.go()
                if i >= len(bench.steps):
                    break
                try:
                    m, line = src.wait_for(S.RE_STEP, STEP_TIMEOUT)
                except stream.Stalled:
                    stream.say("\n  STALLED after step %d." % step.n)
                    rec.close()
                    return rec.rows, False
                continue

            # ⛔ NO PREDICATE AND NOBODY WATCHING IS A SKIP WITH A REASON. The
            # GO above still had to be sent -- the bench has to advance whether
            # or not anyone is judging -- but nothing here saw the result, and
            # calling that a pass is how a suite reports green over work nothing
            # checked.
            if auto_only and not step.meta.get("check"):
                why = "no predicate, and --auto-only means no person to judge it"
                stream.say("  SKIP   %s" % why)
                verdict, note = "skip", why
                record(step, verdict, note, auto=True)
            else:
                verdict, note = ask(step, allow_undo=False)
            if verdict == "quit":
                record(step, "interrupted", note)
                stream.say("\n  stopped at step %d. Resume with:" % step.n)
                stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                           % (bench.name, target, step.n))
                break
            if verdict in ("repeat", "undo"):
                # ⚠️ Neither is available with a patch on the other end: the
                # bench has already moved, and pretending otherwise would put
                # the runner and the patch on different steps. Say so.
                stream.say("  not while a bench is running -- it has already "
                           "advanced. Judge what you saw.")
                continue
            record(step, verdict, note)

            i += 1
            src.go()
            if i >= len(bench.steps):
                break
            try:
                m, line = src.wait_for(S.RE_STEP, STEP_TIMEOUT)
            except stream.Stalled:
                stream.say("\n  STALLED after step %d -- nothing described "
                           "step %d within %g s."
                           % (step.n, i + 1, STEP_TIMEOUT))
                rec.close()
                return rec.rows, False
    except KeyboardInterrupt:
        # ⛔ INTERRUPTED IS NOT FAIL AND IT IS NOT SKIP. Nobody judged this step
        # and nothing about it is known -- calling it a failure would put a red
        # mark against working code, and calling it a skip would claim somebody
        # decided to pass over it. It is the absence of an answer, recorded as
        # one, and the summary counts it as not run.
        stream.say("\n  INTERRUPTED at step %d." % step.n)
        record(step, "interrupted", "Ctrl-C")
        stream.say("  Resume with:")
        stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                   % (bench.name, target, step.n))
        rec.close()
        return rec.rows, False
    except Desync as e:
        # ⛔ ABORT. Not "skip the step", not "resync" -- every verdict already
        # written is still good, and every one that would follow a guess is not.
        stream.say("\n  DESYNC -- %s" % e)
        stream.say("  Aborting. Verdicts already recorded stand; nothing after "
                   "this point would have meant anything.")
        rec.close()
        return rec.rows, False

    rec.close()
    return rec.rows, True


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

    if a.keys:
        stream.use(stream.keystrokes(a.keys))

    if a.replay:
        # ⛔ REPLAY NEVER TOUCHES latest.json. The committed roll-up is a record
        # of what hardware was seen to do; a fixture is a recording of a fiction
        # written to exercise a failure path, and letting one write there would
        # put invented verdicts in the file whose whole value is that it does not
        # contain any.
        if not a.bench:
            sys.exit("run.py: --replay needs --bench, so the transcript can be "
                     "checked against a step table")
        b = S.load(a.bench)
        src = stream.Replay(a.replay)
        rows, ok = run_bench_driven(b, a.target or "replay", a.auto_only,
                                    a.start, src)
        rc = summarise([], 0, [(a.bench, rows, len(b.steps))])
        # ⚠️ `ok` is belt AND braces. A stall or a desync already shows up in the
        # summary as steps not run, so rc is normally enough -- but a failure
        # path that produced a full set of records and still went wrong must not
        # be able to exit 0, and this is what makes that impossible.
        return rc or (0 if ok else 1)

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
        if target == "paper":
            rows = run_bench(b, target, a.auto_only, a.start)
        else:
            import targets
            src = targets.open_target(target, name, a.auto_only)
            try:
                rows, _ok = run_bench_driven(b, target, a.auto_only, a.start, src)
            finally:
                # ⛔ TEARDOWN HAPPENS WHATEVER HAPPENED. A desync, a stall, a
                # Ctrl-C: every one of them still leaves a Pd running and, on
                # the device, a Launchpad stranded in Programmer Mode.
                src.close()
        records.roll_up(rows)
        bench_rows.append((name, rows, len(b.steps)))

    return summarise(gate_failed, gate_ran, bench_rows)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
