#!/usr/bin/env python3
"""The test runner: every gate, and every bench, in one command.

    ./test/run.sh                    the gates. Mac-only, ~1 min, the default
    ./test/run.sh --all              the gates, then every bench
    ./test/run.sh --bench midi       one bench, no gates
    ./test/run.sh --benches          every bench, no gates
    ./test/run.sh --target mac       run the patch here rather than on the device
    ./test/run.sh --auto-only        no person is watching: judge what a
                                     predicate can judge and SKIP the rest
    ./test/run.sh --from 8           resume a bench part-way
    ./test/run.sh --list             what would run, and how fresh each verdict is

Run bare it does what it always has: the gates, on the Mac, touching nothing on
the Organelle. The benches are behind a flag and never reached from a bare run.

Exactly one line matches "RESULT:"; read it, or the exit status. The per-gate
"--- FAILED:" lines also match `grep -E 'ALL|FAILED'`.
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

# Fifteen seconds to the first marker, five between later ones: nothing within
# fifteen of launch is a bench that never loaded, a gap mid-run is a stall.
LOAD_TIMEOUT = 15.0
STEP_TIMEOUT = 5.0

# The answer to `where` is a print off a [pack]: immediate, or not coming.
WHERE_TIMEOUT = 2.0


def _why(reason):
    """The two stall causes, in words: `silence` is a console that stopped,
    `cap` one still talking that has not answered. Nothing a person does is
    timed."""
    if reason == "cap":
        return ("the patch said %d line(s) without ever answering"
                % stream.LINE_CAP)
    return "the console went silent for %g s" % STEP_TIMEOUT

# The fired line is sent last, which covers anything synchronous, but g_oled
# batches frames and the screen lags ~200 ms, so a window closed at the fired
# line would find the OLED empty. A step can widen this with `wait` in its meta.
SETTLE = 0.4


class Desync(Exception):
    """The runner is recording verdicts against the wrong step. Never recovered
    by guessing: every verdict after the slip would answer a question nobody
    asked, in a file that is believed."""

# The repo root, asserted: every gate is a path relative to it, and a root one
# level off would run nothing and exit ok.
ROOT = os.path.dirname(os.path.dirname(HERE))
if not os.path.exists(os.path.join(ROOT, "AGENTS.md")):
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
    """-> (failed_labels, ran)."""
    failed = gates.run_all()
    return failed, len(gates.GATES)


# ---------------------------------------------------------------------------
# the bench half
# ---------------------------------------------------------------------------
# Why there are only three keys: test/README.md.
HELP = ("[p]ass  [f]ail  [r]epeat")


# A PASS IF is a paragraph; wrapped here, every continuation sits under its own
# label rather than against the margin.
WRAP = 76


def _field(label, text, width=WRAP):
    """`  label   text`, wrapped with the continuations under the text."""
    pad = " " * (2 + len(label) + 1)
    out, line = [], "  %s " % label
    for word in text.split():
        if len(line) + len(word) > width and line.strip() != label:
            out.append(line.rstrip())
            line = pad
        line += word + " "
    out.append(line.rstrip())
    return "\n".join(out)


def describe(bench, step):
    """The header a person reads before doing anything: `need` and `do` come
    before the verdict prompt, never after."""
    tag = "  [HANDS]" if step.hands else ""
    print("\n[%d/%d] %s - %s%s"
          % (step.n, step.of, bench.name, step.title, tag))
    # Three labels, always in this order: what to have, what to do, what to see.
    need = step.meta.get("need", [])
    if need:
        print(_field("NEED:   ", " ".join(need)))
    # A field with nothing to say is left out: filler on every step stops the
    # field being read at all.
    if step.meta.get("do"):
        print(_field("DO:     ", step.meta["do"]))
    print(_field("PASS IF:", step.watch))


def ask(step):
    """The verdict prompt. -> (verdict, note).

    Every path out is something a person typed: a default on empty input would
    be the runner inventing a verdict, so Enter re-prompts. `quit` is what
    running out of scripted input returns (a --keys file shorter than the
    bench); a person leaves with Ctrl-C, which does not come through here.
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
        if c == "r":
            return "repeat", ""
        stream.say("  not one of those. %s" % HELP)


def run_bench(bench, target, auto_only, start):
    """One bench in paper mode, with no patch to drive: no Pd, no ssh, no
    `killall pd`, no Launchpad stranded in Programmer Mode. -> list of records.
    """
    rec = records.Recorder(bench.name, target, auto_only)
    dsha = records.deps_sha(bench.deps)
    print("\n%s\n%s -- %d steps, target %s%s\n%s"
          % (BAR, bench.name, len(bench.steps), target,
             ", --auto-only" if auto_only else "", BAR))

    i = max(0, (start or 1) - 1)
    try:
        return _paper_loop(bench, target, auto_only, i, rec, dsha)
    except KeyboardInterrupt:
        # Nothing fires in paper mode, so the step on screen has not run, and
        # recording `interrupted` would overwrite what it last answered.
        stream.say("\n  INTERRUPTED. Nothing recorded against the step that was "
                   "on screen.")
        rec.close()
        return rec.rows


def _paper_loop(bench, target, auto_only, i, rec, dsha):
    while i < len(bench.steps):
        step = bench.steps[i]
        started = time.time()
        describe(bench, step)

        # A step whose oracle is absent is a skip with a reason, never a pass:
        # under --auto-only nobody answers a step with no predicate.
        if auto_only and not step.meta.get("check"):
            why = "no predicate, and --auto-only means no person to judge it"
            print("  SKIP   %s" % why)
            rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                            sha=records.step_sha(step.title, step.pass_if),
                            deps_sha=dsha, verdict="skip", auto=True, note=why))
            i += 1
            continue

        # A `file` predicate needs no console: its evidence is on disk.
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
            # A predicate that needs a console cannot be judged here, where
            # there is no window: it would fail a working rig, so it skips and
            # names the kinds.
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
                    stream.prompt("  Press ENTER when you have done that: ")
                except EOFError:
                    break
            ok, w, g, prows = predicates.report(spec, [], {"step_start": started})
            _say_auto(ok, prows)
            # As in the driven loop, the predicate is evidence and the person
            # is the verdict; only --auto-only lets it answer alone.
            if auto_only:
                rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                                sha=records.step_sha(step.title, step.pass_if),
                                deps_sha=dsha, verdict="pass" if ok else "fail",
                                auto=True, note="", want=w, got=g))
                i += 1
                continue
            verdict, note = ask(step)
            if verdict in ("repeat", "quit"):
                # Handled below: paper mode can repeat, since nothing advanced.
                pass
            else:
                if ok != (verdict == "pass"):
                    stream.say("  ⚠️ you said %s and the check said %s -- both "
                               "are recorded" % (verdict, "pass" if ok else "fail"))
                    note = ("%s; the check disagreed and said %s"
                            % (note or "no note",
                               "pass" if ok else "fail")).strip("; ")
                rec.append(dict(bench=bench.name, step=step.n, title=step.title,
                                sha=records.step_sha(step.title, step.pass_if),
                                deps_sha=dsha, verdict=verdict, auto=False,
                                note=note, want=w, got=g))
                i += 1
                continue

        verdict, note = ask(step)

        if verdict == "repeat":
            continue                                    # describe it again
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


def _split(want, got):
    """-> (label, want, got), with the words they open on said once: a `print`
    predicate names its counter in both halves ("BEATS between 19 and 22",
    "BEATS = 20"), and the shared opening becomes the row's label.
    """
    if want == got:
        # Nothing to split: a satisfied `bus` says both halves in the same
        # words, and all but the last token would become a label.
        return "", want, got
    w, g = want.split(), got.split()
    i = 0
    while i < min(len(w), len(g)) - 1 and w[i] == g[i]:
        i += 1
    # A label does not end on an operator, or both halves start mid-expression.
    while i and w[i - 1] in ("=", "/", "+", "-", "is", "reads"):
        i -= 1
    return " ".join(w[:i]), " ".join(w[i:]), " ".join(g[i:])


# Wide enough for a counter's whole name: a name cut short is worse than a wide
# line.
LABEL_MAX = 38
GOT_MAX = 22


def _say_auto(ok, rows):
    """Print a predicate's evidence, one row per thing it asserted."""
    if len(rows) < 2:
        # One assertion is not a table: two lines, or one where a pass says
        # both halves in the same words.
        _rok, got, want = rows[0]
        stream.say("  %s" % ("AUTO PASS" if ok else "AUTO FAIL"))
        if want == got:
            stream.say("      %s" % want)
        else:
            stream.say("      want  %s\n      got   %s" % (want, got))
        return

    stream.say("  %s   %d checks" % ("AUTO PASS" if ok else "AUTO FAIL",
                                     len(rows)))
    split = [_split(w, g) for _ok, g, w in rows]
    lw = min(LABEL_MAX, max([len(x[0]) for x in split] + [0]))
    gw = min(GOT_MAX, max([len(x[2]) for x in split] + [0]))
    for (rok, _g, _w), (label, want, got) in zip(rows, split):
        # Only a failing row is marked, so the eye lands on it.
        head = ("%-*s  " % (lw, label)) if lw else ""
        stream.say("      %s%-*s  want %s%s"
                   % (head, gw, got, want, "" if rok else "   <-- FAIL"))


def _drain(src, window, seconds):
    """Keep reading for `seconds`, into the predicate window. It drains rather
    than sleeps, or the lines would be read as the next step's window."""
    if not src.realtime:
        # A recording has nothing to wait for, and a wall-clock drain would
        # consume steps not yet described.
        return
    end = time.time() + seconds
    while True:
        left = end - time.time()
        if left <= 0:
            return
        line = src.readline(min(0.2, left))
        if line is not None:
            window.append(line)


# ---------------------------------------------------------------------------
# GO is one UDP datagram over wifi, and a lost one is as silent as a dead patch.
# It cannot simply be resent: GO runs a step in phase 0 and advances in phase 1,
# so a second GO to a bench that heard the first desyncs it. The runner asks
# `where` first, which moves nothing, and acts on the answer.
def _ask_where(src):
    """Where the bench says it is. -> (step, phase), or None if it will not say.
    It flushes first: anything queued predates the question, and a stall is
    when the queue is deepest."""
    src.flush()
    if not src.where():
        return None
    try:
        m, _ = src.wait_for(S.RE_WHERE, WHERE_TIMEOUT)
    except stream.Stalled:
        return None
    return int(m.group(1)), int(m.group(2))


def _regain_fired(src, n, window):
    """A GO was sent to run step `n` and no fired line came. -> (m, line) or None.
    The window is cleared when the step re-runs: half of one attempt plus all
    of another is evidence about neither."""
    at = _ask_where(src)
    if at is None or at[0] != n:
        return None
    if at[1] == 0:
        stream.say("  ... the bench never heard that GO -- it is still waiting "
                   "on step %d. Sending it again." % n)
        del window[:]
        src.flush()
        src.go()
    else:
        stream.say("  ... step %d had already run and its fired line was missed. "
                   "Running it again." % n)
        del window[:]
        if not src.rerun():
            return None
    try:
        return src.wait_for(S.RE_FIRED, STEP_TIMEOUT, collect=window)
    except stream.Stalled:
        return None


def _next_step(src, want, prev):
    """GO, then wait for step `want` to be described. -> (m, line) or None.

    `prev` is the step just judged -- the one the bench is on if the GO was lost.
    """
    src.flush()
    src.go()
    try:
        return src.wait_for(S.RE_STEP, STEP_TIMEOUT)
    except stream.Stalled:
        pass
    at = _ask_where(src)
    if at is None:
        return None
    if at[0] == want:
        stream.say("  ... step %d was described and the line was missed -- "
                   "asking the bench to say it again." % want)
        if not src.show():
            return None
    elif at == (prev, 1):
        stream.say("  ... the bench never heard the GO after step %d. Sending "
                   "it again." % prev)
        src.flush()
        src.go()
    else:
        # Not recovered: a guess from here writes verdicts against the wrong steps.
        stream.say("  ... the bench says step %d phase %d, which is neither %d "
                   "nor %d -- not recoverable." % (at[0], at[1], prev, want))
        return None
    try:
        return src.wait_for(S.RE_STEP, STEP_TIMEOUT)
    except stream.Stalled:
        return None


def _walk_to(src, m, line, want, why):
    """Walk the patch forward to step `want` without judging. -> (m, line) or None.

    `line` comes back untouched when there is nothing to walk (`--from 1`): it
    belongs to the marker the caller already read. It flushes before every GO,
    as the step loop does, or wait_for's line cap is spent on the walked steps'
    backlog (~110 lines a second on the device). A stall here judged nothing,
    so nothing is recorded.
    """
    while int(m.group(1)) < want:
        n = int(m.group(1))
        stream.say("  ... walking past step %s unjudged (--from %d)"
                   % (m.group(1), want))
        src.flush()
        src.go()
        walked = []
        try:
            src.wait_for(S.RE_FIRED, STEP_TIMEOUT, collect=walked)
        except stream.Stalled as e:
            # Ask before giving up, as the step loop does: on the device the
            # meters never let the console go silent, so a lost GO would burn
            # the whole line cap (~18 s) over a bench sitting on step 1.
            if _regain_fired(src, n, walked) is None:
                stream.say(
                    "\n  STALLED walking to step %d -- %s.\n"
                    "  Nothing was judged so nothing is recorded. %s\n%s"
                    % (want, _why(e.why), why, src.diagnose()))
                return None
        nxt = _next_step(src, n + 1, n)
        if nxt is None:
            stream.say(
                "\n  STALLED walking to step %d -- nothing described step %d.\n"
                "  Nothing was judged so nothing is recorded. %s\n%s"
                % (want, n + 1, why, src.diagnose()))
            return None
        m, line = nxt
    return m, line


def check_marker(m, line, expect, bench):
    """The patch's own step number and title, both, against the table: a bench
    regenerated from a reordered table still counts 1, 2, 3."""
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


def run_bench_driven(bench, target, auto_only, start, src, reopen=None):
    """A bench with a patch on the other end. -> (rows, ok).

    Each step takes two GOs, the bench's protocol: one runs the step just
    described, the next describes the following one, so the PASS IF stays on
    screen while it is read.
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

    # Bound before the try: Ctrl-C in the load wait or the --from walk reaches
    # the handler with no step started.
    ran = False

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
                "  why the benches live on /sdcard.\n%s"
                % (LOAD_TIMEOUT, src.diagnose()))
            rec.close()
            # Redundant, since with no records the summary fails anyway; kept
            # because PASS having run nothing is the worst thing this could say.
            return [], False

        # Let the instrument finish booting; what it prints meanwhile belongs
        # to no step.
        if src.boot_settle:
            stream.say("  ... letting the patch finish booting (%g s)"
                       % src.boot_settle)
            _drain(src, [], src.boot_settle)

        # --from walks the patch forward, since a bench always starts at step 1,
        # and records nothing for the steps it walks past.
        i = max(0, (start or 1) - 1)
        walked = _walk_to(src, m, line, i + 1,
                          "Try again -- or run the bench from step 1.")
        if walked is None:
            rec.close()
            return [], False
        m, line = walked

        while True:
            step = bench.steps[i]
            # Did this step run? Ctrl-C most often arrives at the read prompt of
            # the step after the ones a person came to do, and roll_up is last
            # write wins: `interrupted` for a step that never fired would
            # overwrite what it last really answered.
            ran = False

            # A `reload` step needs the patch booted without its device, which
            # is already out from the step before. The runner launched the
            # process, so it reloads it.
            if step.meta.get("reload") and reopen and not step.meta.get("_done"):
                step.meta["_done"] = True
                stream.say("\n  ... reloading the patch with the device still "
                           "unplugged -- this is what the step needs and the "
                           "runner owns it")
                src = reopen()
                m, line = src.wait_for(S.RE_STEP, LOAD_TIMEOUT)
                if src.boot_settle:
                    _drain(src, [], src.boot_settle)
                walked = _walk_to(src, m, line, step.n,
                                  "The patch was reloaded and the walk back to "
                                  "this step did not finish.")
                if walked is None:
                    rec.close()
                    return rec.rows, False
                m, line = walked
                stream.say("  ... reloaded and back at step %d" % step.n)

            check_marker(m, line, step, bench)
            describe(bench, step)

            if not auto_only:
                # Never auto-answered, on any step: a GO sent before the person
                # has read the step shows the result before they know to look.
                # runner-assert's fixtures match the "  Press ENTER" prefix.
                try:
                    stream.prompt("  Press ENTER to run the test: ")
                except EOFError:
                    # Input ran out where a person was expected. That is the end
                    # of the run, not permission to carry on without one.
                    record(step, "interrupted", "input ended before the step ran")
                    stream.say("\n  stopped at step %d. Resume with:" % step.n)
                    stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                               % (bench.name, target, step.n))
                    break

            # Flush before GO: what is queued is the console of what came
            # before, and `window` is what this step is judged against.
            src.flush()
            src.go()
            ran = True
            window = []
            fired = None
            fired_why = "silence"
            try:
                fired = src.wait_for(S.RE_FIRED, STEP_TIMEOUT, collect=window)
            except stream.Stalled as e:
                fired_why = e.why
                # Ask before giving up: see _regain_fired.
                fired = _regain_fired(src, step.n, window)
            if fired is not None:
                fm, fline = fired
            else:
                # Those seconds are how long the patch gets to answer a GO
                # (~50 ms on the device); nothing a person does is timed.
                stream.say("\n  STALLED at step %d -- %s, and it did not say "
                           "where it was when asked.\n  (nothing you do is "
                           "timed -- see below)\n%s"
                           % (step.n, _why(fired_why), src.diagnose()))
                # The note survives into latest.json, so it carries the counts
                # and not only the symptom.
                record(step, "interrupted",
                       "stalled mid-run: %d GO(s) sent, %s line(s) queued, "
                       "%d line(s) seen"
                       % (src.gos, src.pending(),
                          len(getattr(src, "seen", None) or ())))
                rec.close()
                return rec.rows, False
            if int(fm.group(1)) != step.n:
                raise Desync("step %d was described but step %s fired\n  line: %s"
                             % (step.n, fm.group(1), fline.strip()))

            # A measure step's number means nothing until its window closes
            # (the latch reads -1 before then), so wait it out.
            if step.measure:
                stream.say("  ... %g s measurement window is running"
                           % (S.WINDOW_MS / 1000.0))
                _drain(src, window, S.WINDOW_MS / 1000.0 + 0.5)
            else:
                _drain(src, window, step.meta.get("wait", SETTLE))

            # A step its target cannot judge is a skip with a reason: 57 BPM
            # restored from knobs.txt is a device fact, and a Mac reads 120.
            want_targets = step.meta.get("targets")
            if want_targets and target not in want_targets:
                why = "this step only means something on %s" % " or ".join(want_targets)
                stream.say("  SKIP   %s" % why)
                record(step, "skip", why, auto=True)
                i += 1
                if i >= len(bench.steps):
                    src.go()
                    break
                nxt = _next_step(src, i + 1, step.n)
                if nxt is None:
                    stream.say("\n  STALLED after step %d.\n%s"
                               % (step.n, src.diagnose()))
                    rec.close()
                    return rec.rows, False
                m, line = nxt
                continue

            # The predicate is evidence and the person in the room is the
            # verdict: the bus can carry `warn m_nano` while the screen the PASS
            # IF names shows nothing, which is the bug a bench exists to catch.
            spec = step.meta.get("check")
            # A predicate that needs the OSC mirror cannot be read off the
            # device, whose datagrams go to the phone: it is dropped, and the
            # person watching the phone judges the step.
            if spec and target != "mac":
                needs, kinds = predicates.needs_mirror(spec)
                if needs:
                    stream.say(
                        "  ... %s reads the OSC mirror and only --target mac has "
                        "one -- your eyes on the phone are the oracle here"
                        % " and ".join("`%s`" % k for k in kinds))
                    spec = None
            auto = None
            if spec:
                ok, want, got, rows = predicates.report(spec, window)
                _say_auto(ok, rows)
                auto = (ok, want, got)

            # With nobody watching the predicate is all there is, and a step
            # without one is a skip with a reason, never a pass.
            if auto_only:
                if auto:
                    ok, want, got = auto
                    record(step, "pass" if ok else "fail", "", auto=True,
                           want=want, got=got)
                else:
                    why = "no predicate, and --auto-only means no person to judge it"
                    stream.say("  SKIP   %s" % why)
                    record(step, "skip", why, auto=True)
                i += 1
                if i >= len(bench.steps):
                    src.go()
                    break
                nxt = _next_step(src, i + 1, step.n)
                if nxt is None:
                    stream.say("\n  STALLED after step %d.\n%s"
                               % (step.n, src.diagnose()))
                    rec.close()
                    return rec.rows, False
                m, line = nxt
                continue

            if True:
                # The repeat loop is here, not around the step: asking again
                # must neither re-describe the step nor send another GO, which
                # would advance the patch while the runner thinks it is here.
                # The hold keeps a visual step's row up while the verdict is
                # open; step.holds exempts steps whose subject is the decay.
                src.hold(step.holds)
                while True:
                    verdict, note = ask(step)
                    if verdict != "repeat":
                        break
                    # Fires the current step again and advances nothing, for a
                    # row that aged out (~1.3 s) before it was read.
                    if src.rerun():
                        stream.say("  fired again -- look as long as you need")
                    else:
                        stream.say("  not available against a recorded console")
                # Stopped before the verdict is recorded: a hold still running
                # would re-fire into the next step.
                src.hold(False)
            if verdict == "quit":
                record(step, "interrupted", note)
                stream.say("\n  stopped at step %d. Resume with:" % step.n)
                stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                           % (bench.name, target, step.n))
                break
            # When the two oracles disagree, record that they did: which one is
            # wrong is the whole question.
            if auto is not None:
                ok, want, got = auto
                agreed = ok == (verdict == "pass")
                if not agreed:
                    stream.say("  ⚠️ you said %s and the bus said %s -- both are "
                               "recorded" % (verdict, "pass" if ok else "fail"))
                    note = ("%s; the bus disagreed and said %s"
                            % (note or "no note", "pass" if ok else "fail")).strip("; ")
                record(step, verdict, note, want=want, got=got)
            else:
                record(step, verdict, note)

            i += 1
            if i >= len(bench.steps):
                src.go()
                break
            nxt = _next_step(src, i + 1, step.n)
            if nxt is None:
                stream.say("\n  STALLED after step %d -- nothing described step "
                           "%d, and the bench would not say where it was.\n%s"
                           % (step.n, i + 1, src.diagnose()))
                rec.close()
                return rec.rows, False
            m, line = nxt
    except KeyboardInterrupt:
        # Interrupted, neither fail nor skip, since nobody judged the step;
        # and only if it ran (see `ran`).
        stream.say("\n  INTERRUPTED at step %d." % step.n)
        if ran:
            record(step, "interrupted", "Ctrl-C")
        else:
            stream.say("  It had not run yet -- nothing recorded against it.")
        stream.say("  Resume with:")
        stream.say("      ./test/run.sh --bench %s --target %s --from %d"
                   % (bench.name, target, step.n))
        rec.close()
        return rec.rows, False
    except Desync as e:
        # Abort: verdicts already written stand, and any after a guess would not.
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


def summarize(gate_failed, gate_ran, bench_rows):
    """The one summary, and the one RESULT: line.

    PASS needs no failed, skipped or interrupted step and a record for every
    step selected: a skip is the absence of a verdict, never a pass.
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
    """-> (target, why). A paper bench needs no patch at all."""
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
        # Replay never touches latest.json: a fixture's verdicts are invented.
        if not a.bench:
            sys.exit("run.py: --replay needs --bench, so the transcript can be "
                     "checked against a step table")
        b = S.load(a.bench)
        src = stream.Replay(a.replay)
        rows, ok = run_bench_driven(b, a.target or "replay", a.auto_only,
                                    a.start, src)
        rc = summarize([], 0, [(a.bench, rows, len(b.steps))])
        # `ok` too: a failure path that left a full set of records must still
        # not exit 0.
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
            # The runner launched the patch, so it reloads it for a `reload`
            # step.
            holder = [src]

            def reopen(_t=target, _n=name, _a=a.auto_only, _h=holder):
                _h[0].close(quiet=True)
                _h[0] = targets.open_target(_t, _n, _a)
                return _h[0]
            try:
                rows, _ok = run_bench_driven(b, target, a.auto_only, a.start,
                                             src, reopen)
            finally:
                src = holder[0]
                # Torn down whatever happened: a Pd is still running and, on
                # the device, a Launchpad is stranded in Programmer Mode.
                src.close()
        records.roll_up(rows)
        bench_rows.append((name, rows, len(b.steps)))

    return summarize(gate_failed, gate_ran, bench_rows)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
