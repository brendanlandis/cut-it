#!/usr/bin/env python3
"""The runner's own gate. It answers for test/README.md, not a ref/ page.

    python3 test/gate/runner-assert.py        # ~1 s, no Pd, no device
    python3 test/gate/runner-assert.py -v

The only thing that exercises the runner's failure paths (test/README.md). The
fixtures are generated from the real step table, never hand-typed, so they
reword with it; the desync fixtures corrupt a generated one in one known way.
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "test", "runner"))
sys.path.insert(0, HERE)

WORK = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                    "cutit-runner-assert-%d" % os.getpid())
# Every record a fixture writes, run files and roll-up alike, goes to WORK:
# the real ones describe hardware. Set before anything imports records, which
# reads it once, and inherited by every run.py this starts. Check 8 proves the
# real directory was left alone.
os.environ["CUTIT_RESULTS"] = os.path.join(WORK, "results")
REAL_RESULTS = os.path.join(ROOT, "test", "results")

import lib_assert as A                                          # noqa: E402
import lib_pd                                                   # noqa: E402
import steps as S                                               # noqa: E402
import stream                                                   # noqa: E402
# No actions anywhere, so the one table drives both of the runner's loops: the
# driven one and paper mode.
BENCH = "midi"


# ---------------------------------------------------------------------------
def transcript(bench, upto=None, stop_before_fired=False,
               marker_n=None, of=None, retitle=None, fired_n=None):
    """What that bench prints on Pd's console.

    Every line carries Pd's own "print: " prefix, so the runner's regexes cannot
    be anchored at line start and still pass here.

    Each corruption is a separate knob: a fixture that trips two guards at once
    only ever tests the first one to fire.
    """
    out = []
    n = len(bench.steps)
    for step in bench.steps:
        mi = marker_n(step.n) if marker_n else step.n
        title = retitle(step.n, step.title) if retitle else step.title
        out.append("print: " + S.SAY_STEP % (mi, of or n, title))
        out.append("print: " + step.pass_if)
        out.append("print: " + S.SAY_PROMPT % (mi, of or n))
        # The traffic a passing predicate would have seen, so the loop fixtures
        # test the loop. The predicates themselves are _predicates()'s.
        out.extend(_satisfy(step.meta.get("check")))
        if stop_before_fired and upto is not None and step.n >= upto:
            return out                  # GO will be sent and nothing will fire
        fi = fired_n(step.n) if fired_n else step.n
        out.append("print: " + (S.SAY_FIRED % (fi, fi + 1)
                                if step.n < n else S.SAY_FIRED_LAST % fi))
        if upto is not None and step.n >= upto:
            return out
    out.append("print: " + S.SAY_COMPLETE)
    return out


def _satisfy(spec):
    """The console traffic a step whose predicate PASSES would have produced."""
    if not spec:
        return []
    kind = spec.get("kind")
    if kind == "all":
        out = []
        for s in spec["of"]:
            out.extend(_satisfy(s))
        return out
    if kind == "print":
        return ["%s: %g" % (spec["name"], (spec["min"] + spec["max"]) / 2.0)]
    if kind == "ratio":
        return []                       # its operands come from the print specs
    if kind == "bus":
        return ["%s: %s" % (spec["bus"], s) for s in spec["has"]]
    if kind == "bus-count":
        return ["%s: %s" % (spec["bus"], spec["match"])] * spec["n"]
    if kind == "bus-not":
        return []
    if kind == "oled":
        rows = list(spec.get("has_row", [])) + list(spec.get("has", []))
        out = ["OLED: sendtyped /oled/gClear ii 3 1"]
        for r in rows:
            words = r.split()
            out.append("OLED: sendtyped /oled/gPrintln %s 3 2 8 16 1 %s"
                       % ("iiiii" + "s" * len(words), r))
        out.append("OLED: sendtyped /oled/gFlip i 3")
        return out
    raise AssertionError("_satisfy does not know kind %r -- a new predicate "
                         "kind needs a line here, or every loop fixture using "
                         "it silently starts failing" % kind)


def write(name, lines):
    p = os.path.join(WORK, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    return p


def run_paper(keys):
    """Drive a real paper-mode run. -> (exit code, output).

    No transcript: paper mode has no stream. The only fixture that drives
    run_bench rather than run_bench_driven.

    A paper run rolls its verdicts up, so it inherits CUTIT_RESULTS from the
    top of this file like every other run.
    """
    kp = write("paper.keys", keys)
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--target", "paper", "--keys", kp],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def run(transcript_path, keys, auto_only=False):
    """Drive the real runner over a fixture. -> (exit code, output)."""
    kp = write(os.path.basename(transcript_path) + ".keys", keys)
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path, "--keys", kp]
        + (["--auto-only"] if auto_only else []) + [
         # A transcript is a recording of a device run, so it replays as one;
         # otherwise device-only steps are skipped and shift every count.
         "--target", "device"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
def _holds():
    """Which steps may be held on screen.

    The runner re-fires a step while its verdict is open, because g_oled ages a
    parameter row out after ~1.3 s. For a step whose subject is that decay,
    re-firing resets the timer under test. So the exemptions must hold, and at
    least one parameter step must still be held: "nothing holds" would satisfy
    the exemptions on its own.
    """
    print("\n--- which steps may be held on screen ---")
    disp, nano, lp = S.load("display"), S.load("nanokontrol"), S.load("launchpad")
    ALL_BENCHES = [S.load(n) for n in S.names()]

    held = [st for b in (disp, nano, lp) for st in b.steps if st.holds]
    A.check("some step is actually held -- the exemptions have not eaten "
            "everything", len(held) >= 10,
            "%d steps hold. A zero here passes every safety check below while "
            "delivering none of the point" % len(held))

    A.check("⛔ a parameter step IS held -- the case this exists for",
            disp.steps[2].holds and disp.steps[3].holds,
            "display 3 %s / display 4 %s -- these are the OLED rows that "
            "vanish in 1.3 s" % (disp.steps[2].holds, disp.steps[3].holds))

    # Each of these asserts a timeout, which re-firing resets. The numbers are
    # positions and move when a step is inserted above; the third column says
    # which step is meant.
    for b, n, why in ((disp, 10, "about 2 s later it vanishes"),
                      (disp, 13, "recording returns after about 4 s"),
                      (disp, 17, "the 30 s TTL that the step AFTER it judges"),
                      (lp, 14, "clears ITSELF about thirty seconds later"),
                      (lp, 12, "goes back to the mode lamps by itself")):
        st = b.steps[n - 1]
        A.check("⛔ %s step %d is NOT held -- it tests %s" % (b.name, n, why),
                not st.holds,
                "holding it re-sends the message that starts the timer under "
                "test\n     %s" % st.pass_if)

    # `hold: False` is for what the derivation cannot see: actions that are not
    # idempotent, or a timer the next step judges. Found by search, not index.
    refusers = [(b.name, st) for b in ALL_BENCHES for st in b.steps
                if st.meta.get("hold") is False]
    A.check("at least one step still refuses the hold outright -- otherwise "
            "the check below is vacuous", refusers, "found none")
    for name, st in refusers:
        A.check("⛔ %s step %d carries `hold: False` and is not held"
                % (name, st.n),
                not st.holds and st.actions and not st.measure
                and not S.DECAY_RE.search(st.pass_if),
                "holds=%s -- and it must be the meta doing it, not a decay word "
                "that happens to be in the prose" % st.holds)

    # A measure step re-arms or re-reads a beat counter; a step with no actions
    # has nothing to re-send.
    for b in ALL_BENCHES:
        bad = [st.n for st in b.steps if st.holds and (st.measure or not st.actions)]
        A.check("%s: no measure step and no action-less step is held" % b.name,
                not bad, "steps %s" % bad)


class Trickle(stream.Source):
    """A source that says something every `gap` seconds and answers late.

    Proves a stall is silence, not slowness: the deadline is per line, so a
    person sweeping faders before pressing enter cannot outlast it. No replay
    can show this, because a replay hands over its transcript at once.
    """

    realtime = True

    def __init__(self, filler, answer, gap=0.05):
        self.left = list(filler) + [answer]
        self.gap = gap

    def readline(self, timeout):
        if not self.left:
            return None
        # It honors the timeout, or it would pass whatever wait_for did with it.
        if timeout < self.gap:
            time.sleep(max(0.0, timeout))
            return None
        time.sleep(self.gap)
        line = self.left.pop(0)
        self._note(line)
        return line


class Chatter(stream.Source):
    """A patch that says something forever and never answers.

    Endless, so the bound under test is wait_for's line cap. LIMIT is only the
    gate's safety net: reaching it means the cap did nothing.
    """

    realtime = True
    LIMIT = 50000

    def __init__(self):
        self.n = 0

    def readline(self, timeout):
        self.n += 1
        if self.n > self.LIMIT:
            return None
        line = "print: PARAM: slider-3 0.5"
        self._note(line)
        return line


class Fake(stream.Source):
    """The bench's state machine, in Python, on the other end of a fake wire.

    The only thing that exercises GO recovery: a lost datagram cannot be
    provoked on hardware, and a replay cannot answer a question.

    `drop` is a set of GO numbers, counted as the runner counts them; `lose` a
    set of step numbers whose describe line goes missing.
    """

    realtime = False        # so _drain returns at once rather than sleeping
    boot_settle = 0.0

    def __init__(self, bench, drop=(), lose=()):
        self.steps = bench.steps
        self.n, self.phase, self.gos, self.flushes = 1, 0, 0, 0
        self.out = []
        self.drop, self.lose = set(drop), set(lose)
        self.asked = 0
        self._describe()

    # -- the wire ----------------------------------------------------------
    def _say(self, text):
        self.out.append("print: " + text)

    def readline(self, timeout):
        if not self.out:
            return None
        line = self.out.pop(0)
        self._note(line)
        return line

    def pending(self):
        return len(self.out)

    def diagnose(self):
        return "    (fake bench at step %d phase %d)" % (self.n, self.phase)

    # -- the bench ---------------------------------------------------------
    def _describe(self):
        if self.n in self.lose:
            self.lose.discard(self.n)
            return
        self._say(S.SAY_STEP % (self.n, len(self.steps),
                                self.steps[self.n - 1].title))

    def _fire(self):
        self._say(S.SAY_FIRED % (self.n, self.n + 1)
                  if self.n < len(self.steps) else S.SAY_FIRED_LAST % self.n)

    def go(self):
        self.gos += 1
        if self.gos in self.drop:
            return                      # the datagram simply never arrived
        if self.phase == 0:
            self.phase = 1
            self._fire()
        elif self.n < len(self.steps):
            self.phase = 0
            self.n += 1
            self._describe()
        else:
            self._say(S.SAY_COMPLETE)

    def rerun(self):
        self._fire()
        return True

    def where(self):
        self.asked += 1
        self._say("%s: %d %d" % (S.SAY_WHERE, self.n, self.phase))
        return True

    def show(self):
        self._say(S.SAY_STEP % (self.n, len(self.steps),
                                self.steps[self.n - 1].title))
        return True

    def flush(self):
        n, self.out = len(self.out), []
        self.flushes += 1
        return n


JUNK = "print: PARAM: slider-3 0.5"


class Noisy(Fake):
    """A bench with a person in front of it.

    Nothing reads the console except a wait, so a person's own traffic during
    an open verdict piles up, and carried into the next step it burns the wait's
    line cap and lands in that step's predicate window. The backlog is deeper
    than twice the cap, as the real one was (4141 lines against 2000):
    shallower, and GO recovery rescues the run by accident.
    """

    def __init__(self, *a, **kw):
        self.read_junk = 0
        Fake.__init__(self, *a, **kw)

    def readline(self, timeout):
        line = Fake.readline(self, timeout)
        if line == JUNK:
            self.read_junk += 1
        return line

    def _fire(self):
        Fake._fire(self)
        self.out.extend([JUNK] * (stream.LINE_CAP * 2 + 500))


def _stall():
    """A stall is silence; slowness is not a fault."""
    print("\n--- what counts as a stall ---")
    marker = "print: " + S.SAY_FIRED % (7, 8)
    filler = ["print: PARAM: slider-3 0.5"] * 40

    t0 = time.time()
    src = Trickle(filler, marker, gap=0.05)
    # Caught, so a regression fails the check rather than raising a traceback.
    try:
        m, _ = src.wait_for(S.RE_FIRED, 0.5)
    except stream.Stalled:
        m = None
    took = time.time() - t0
    A.check("⛔ 40 lines of chatter then the answer is NOT a stall -- the "
            "deadline is per line",
            m is not None and m.group(1) == "7",
            "wait_for gave up while the patch was still printing. That is the "
            "nanokontrol 15 failure exactly: a person sweeps every fader before "
            "pressing enter and their own traffic outlives a fixed deadline")
    A.check("⛔ and it really did outlive the timeout -- otherwise the check "
            "above proves nothing",
            took > 0.5 * 2,
            "the call took %.2f s against a 0.5 s timeout. Under the old fixed "
            "deadline this could not have returned at all" % took)

    src = Trickle([], None, gap=0.05)
    src.left = []
    try:
        src.wait_for(S.RE_FIRED, 0.2)
        A.check("silence IS a stall", False, "it returned instead of raising")
    except stream.Stalled as e:
        A.check("silence IS a stall -- nothing arriving still ends the wait",
                e.why == "silence",
                "it stalled for %r, and the two causes read nothing alike to "
                "whoever has to act on the report" % e.why)

    # The other end: a patch that prints forever is bounded by the line cap.
    # The source is endless, since any finite fixture stalls at its own end
    # with or without the cap; the check is where it stopped.
    src = Chatter()
    try:
        src.wait_for(S.RE_FIRED, 0.2)
        A.check("⛔ prints forever and never answers IS a stall", False,
                "it returned a match out of a stream that contains none")
    except stream.Stalled as e:
        A.check("⛔ prints forever and never answers IS a stall -- it stopped "
                "at the line cap and not at the gate's own safety net",
                e.why == "cap" and src.n <= stream.LINE_CAP + 1 < Chatter.LIMIT,
                "it read %d lines against a cap of %d. Nothing bounded the wait "
                "but the fixture running out, and a real patch does not"
                % (src.n, stream.LINE_CAP))


def _recovery(bench):
    """A lost GO must not end the session, and must not be guessed at.

    GO is one UDP datagram. A lost one and a dead patch are the same silence and
    want opposite responses, resend or stop; `where` tells them apart.
    """
    print("\n--- recovering a lost GO ---")
    import run as R

    saved_ask = stream.ask_line

    def drive(cls=Fake, start=1, **kw):
        src = cls(bench, **kw)
        stream.use(stream.keystrokes(write("fake.keys", _keys(bench))))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, start, src)
        finally:
            stream.use(saved_ask)
        return src, rows, ok

    try:
        # the control arm: nothing is dropped, and nothing is asked
        src, rows, ok = drive()
        A.check("no loss: every step is judged",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s" % (len(rows), len(bench.steps), ok))
        A.check("⛔ no loss: the bench is never asked where it is -- recovery "
                "must cost nothing on a healthy run",
                src.asked == 0, "asked %d time(s)" % src.asked)

        # The GO that runs step 3: the bench is in phase 0, so resend it. A
        # runner that resent blindly would pass here and fail the next arm.
        src, rows, ok = drive(drop=[5])
        A.check("⛔ a lost GO before a step runs is resent, and the run finishes",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s -- the session ended on a dropped "
                "datagram" % (len(rows), len(bench.steps), ok))

        # The GO that advances: the same silence, but the bench is in phase 1
        # and a second GO would advance it twice.
        src, rows, ok = drive(drop=[6])
        A.check("⛔ a lost GO before an advance is resent, and no step is "
                "skipped", len(rows) == len(bench.steps) and ok
                and [r["step"] for r in rows] == [s.n for s in bench.steps],
                "steps recorded: %s" % [r["step"] for r in rows])

        # The GO landed and its answer did not. Resending GO would advance the
        # bench past the step; `show` recovers without moving anything.
        src, rows, ok = drive(lose=[4])
        A.check("⛔ a lost DESCRIBE line is asked for again rather than "
                "re-driven", len(rows) == len(bench.steps) and ok
                and [r["step"] for r in rows] == [s.n for s in bench.steps],
                "steps recorded: %s" % [r["step"] for r in rows])
        A.check("and it had to ask -- otherwise the check above is vacuous",
                src.asked > 0, "asked %d time(s)" % src.asked)

        # A person's own traffic must not count against the patch.
        src, rows, ok = drive(cls=Noisy)
        A.check("⛔ a backlog from the previous step does not stall the next one",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s -- %d line(s) still queued. The wait is "
                "chewing through console that was already judged, and every "
                "line of it lands in the next step's predicate window too"
                % (len(rows), len(bench.steps), ok, src.pending()))
        # Finishing is the weaker half: a runner could grind through the whole
        # backlog and still finish. Zero lines read is what the flush buys.
        A.check("⛔ and not one line of the previous step's console was read "
                "into this step", src.read_junk == 0,
                "%d stale line(s) reached the step loop, and a predicate window "
                "is built out of exactly those" % src.read_junk)

        # The same backlog against a --from walk, which is a second loop. On
        # the device it showed as an uncaught Stalled that looked intermittent,
        # since whether 2000 lines had piled up by a given step is a race.
        src, rows, ok = drive(cls=Noisy, start=len(bench.steps))
        A.check("⛔ a --from walk survives a backlog the same way the step loop "
                "does", len(rows) == 1 and ok,
                "%d row(s), ok=%s -- the walk is chewing through console the "
                "steps it walked past printed, and blows the line cap"
                % (len(rows), ok))
        A.check("⛔ and the walk read none of it either",
                src.read_junk == 0,
                "%d stale line(s) reached the walk" % src.read_junk)

        # -- and the same losses INSIDE A --from WALK -------------------------
        # A lost GO costs a walk the whole run, not one step. On the device it
        # cannot time out either: the level meters redraw forever, so wait_for
        # sees no silence and burns its 2000-line cap, about eighteen seconds.
        start = 4
        src, rows, ok = drive(start=start, drop=[1])
        A.check("⛔ a GO lost walking PAST a step is resent and the walk "
                "finishes -- the step loop recovered this and the walk did not",
                len(rows) == len(bench.steps) - (start - 1) and ok,
                "%d rows for steps %d..%d, ok=%s -- the run died in the walk"
                % (len(rows), start, len(bench.steps), ok))
        A.check("a lost GO in the walk costs one `where` and no more",
                src.asked == 1, "asked %d time(s)" % src.asked)

        # GO 2 is a different datagram: the one that asks the bench to describe
        # the step after the one just fired.
        src, rows, ok = drive(start=start, drop=[2])
        A.check("⛔ a GO lost between two walked steps is resent too",
                len(rows) == len(bench.steps) - (start - 1) and ok,
                "%d rows for steps %d..%d, ok=%s"
                % (len(rows), start, len(bench.steps), ok))

        # A walk that cannot be recovered still fails, judging nothing.
        class DeafWalk(Fake):
            def go(self):
                self.gos += 1

            def where(self):
                self.asked += 1
                return True

        src = DeafWalk(bench)
        stream.use(stream.keystrokes(write("deafwalk.keys", _keys(bench))))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, start, src)
        finally:
            stream.use(saved_ask)
        A.check("⛔ a walk that cannot be recovered records NOTHING and fails",
                not ok and not rows,
                "%d row(s), ok=%s" % (len(rows), ok))

        # A bench that will not answer is still a stall: recovery must not turn
        # a dead patch into a green run.
        class Deaf(Fake):
            def go(self):
                self.gos += 1

            def where(self):
                self.asked += 1
                return True         # sent, and nothing comes back

        src = Deaf(bench)
        stream.use(stream.keystrokes(write("deaf.keys", _keys(bench))))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, 1, src)
        finally:
            stream.use(saved_ask)
        A.check("⛔ a patch that answers nothing at all still STALLS",
                not ok and len(rows) < len(bench.steps),
                "%d rows of %d, ok=%s" % (len(rows), len(bench.steps), ok))
    finally:
        stream.use(saved_ask)


def _interrupt_before_fire(bench):
    """Ctrl-C must not write a verdict for a step that never ran.

    roll_up is last-write-wins, so `interrupted` replaces whatever that step
    last really answered, and Ctrl-C usually lands on the read prompt of the
    step after the ones a person came to re-run. Two arms, because a runner
    that recorded nothing on any interrupt would lose the second: the step did
    fire and nobody answered. Fake's phase shows where the patch was left, which
    no replay can.
    """
    print("\n--- Ctrl-C before a step runs ---")
    import run as R

    saved_ask = stream.ask_line

    def interrupt_after(keys):
        """A person at a keyboard who answers `keys` and then presses Ctrl-C."""
        pending = list(keys)

        def provider(_prompt=""):
            if not pending:
                raise KeyboardInterrupt
            return pending.pop(0)
        return provider

    # Something is judged before the interrupted step, so a run that recorded
    # nothing at all cannot satisfy these.
    stop = 2
    at = stop + 1
    try:
        # -- arm 1: the interrupt lands on the READ prompt, before GO ---------
        src = Fake(bench)
        stream.use(interrupt_after(_keys(bench, stop_after=stop)))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, 1, src)
        finally:
            stream.use(saved_ask)

        A.check("⛔ Ctrl-C before a step fires records NOTHING against it -- an "
                "interrupted overwrites in latest.json and this step was never "
                "even run",
                not any(r["step"] == at for r in rows),
                "step %d got a row: %s"
                % (at, [r for r in rows if r["step"] == at]))
        A.check("⛔ and the GO never left -- the patch is where it was, "
                "describing the step it did not run",
                src.n == at and src.phase == 0,
                "the fake bench is at step %d phase %d" % (src.n, src.phase))
        A.check("Ctrl-C before firing: the verdicts already given are kept",
                any(r["step"] == stop and r["verdict"] == "pass" for r in rows),
                "%d rows: %s"
                % (len(rows), [(r["step"], r["verdict"]) for r in rows]))
        # ok decides nothing: summarize() counting a step with no row as not
        # run is what keeps the run off PASS, so this asserts on the rows.
        A.check("Ctrl-C before firing: the bench is left unfinished rather than "
                "reported complete",
                len(rows) < len(bench.steps),
                "%d rows of %d, ok=%s" % (len(rows), len(bench.steps), ok))

        # -- arm 2: the interrupt lands on the VERDICT prompt, after GO -------
        # The step ran and nobody answered it, which must still be recorded.
        src = Fake(bench)
        stream.use(interrupt_after(_keys(bench, stop_after=stop) + [""]))
        try:
            rows, _ok = R.run_bench_driven(bench, "device", False, 1, src)
        finally:
            stream.use(saved_ask)

        A.check("⛔ but Ctrl-C AFTER the step fired still records interrupted -- "
                "it ran and nobody judged it",
                any(r["step"] == at and r["verdict"] == "interrupted"
                    for r in rows),
                "step %d rows: %s"
                % (at, [(r["step"], r["verdict"]) for r in rows]))
        A.check("Ctrl-C after firing: the GO did leave, so the two arms differ "
                "in the way `ran` claims they do",
                src.phase == 1, "the fake bench is at phase %d" % src.phase)

        # -- and the four keys that were removed ------------------------------
        # None of these may be a verdict again. The automatic skips are a
        # different thing, checked in section 7c.
        for gone in ("q", "u", "?", "s"):
            src = Fake(bench)
            stream.use(interrupt_after(["", gone, "p"]))
            try:
                rows, _ok = R.run_bench_driven(bench, "device", False, 1, src)
            finally:
                stream.use(saved_ask)
            A.check("⛔ %r is not a verdict any more -- it is refused and the "
                    "prompt asks again" % gone,
                    any(r["step"] == 1 and r["verdict"] == "pass"
                        for r in rows),
                    "step 1 rows: %s"
                    % [(r["step"], r["verdict"]) for r in rows])
        A.check("and the prompt offers exactly the three that are left",
                R.HELP == "[p]ass  [f]ail  [r]epeat", "HELP is %r" % R.HELP)
    finally:
        stream.use(saved_ask)


def _mirror():
    """A predicate needing the OSC mirror is skipped on the device; the step is
    not, since a person watching the phone can judge it.

    Only --target mac repoints u_net at a socket the runner binds, so on the
    device the window carries no OSC and the predicate would be a false AUTO
    FAIL. The phone bench is driven here because midi has no osc predicate.
    """
    print("\n--- a predicate that needs the OSC mirror ---")
    import predicates as P
    import run as R

    # The kind question first, because the runner's behavior rests on it.
    A.check("needs_mirror: an osc predicate needs the mirror",
            P.needs_mirror({"kind": "osc", "addr": "/x"})[0])
    A.check("needs_mirror: a bus predicate does not",
            not P.needs_mirror({"kind": "bus", "bus": "DISP", "has": ["x"]})[0])
    A.check("⛔ needs_mirror: an `all` needs it if ANY leaf does -- phone 8 is "
            "two osc halves and evaluating either against an empty window is a "
            "false failure",
            P.needs_mirror({"kind": "all", "of": [
                {"kind": "bus", "bus": "DISP", "has": ["x"]},
                {"kind": "osc", "addr": "/y"}]})[0])

    bench = S.load("phone")
    mirrored = [s.n for s in bench.steps
                if s.meta.get("check") and P.needs_mirror(s.meta["check"])[0]]
    A.check("the phone bench still has steps whose predicate needs the mirror -- "
            "without one this fixture proves nothing",
            len(mirrored) > 0, "found %s" % mirrored)

    saved_ask = stream.ask_line
    try:
        src = Fake(bench)
        stream.use(stream.keystrokes(write("mirror.keys", _keys(bench))))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, 1, src)
        finally:
            stream.use(saved_ask)

        by_step = {r["step"]: r for r in rows}
        A.check("⛔ every mirrored step is still JUDGED on the device -- the "
                "predicate is what is unavailable there and not the step",
                all(n in by_step and by_step[n]["verdict"] == "pass"
                    for n in mirrored),
                "; ".join("step %d: %s" % (n, by_step.get(n, {}).get("verdict",
                                                                    "no row"))
                          for n in mirrored))
        A.check("⛔ and none of them reports AUTO FAIL out of a window with no "
                "OSC in it",
                all(by_step[n].get("got") is None for n in mirrored
                    if n in by_step),
                "; ".join("step %d got %r" % (n, by_step[n].get("got"))
                          for n in mirrored if n in by_step))
        A.check("mirror: the run finishes rather than skipping its way to the end",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s" % (len(rows), len(bench.steps), ok))
    finally:
        stream.use(saved_ask)


def _boxes(src):
    """Every box in a .pd, in file order, which is what #X connect indexes:
    comments count (C-10)."""
    return [ln.split(" ", 4)[-1].rstrip(";")
            for ln in lib_pd.records(src)
            if ln.startswith(("#X obj ", "#X msg ", "#X text "))]


def _feeds(src, pattern):
    """Every cord landing on a box matching `pattern`. -> [(from, to)] indices."""
    boxes = _boxes(src)
    want = [i for i, b in enumerate(boxes) if re.fullmatch(pattern, b)]
    out = []
    for ln in lib_pd.records(src):
        if not ln.startswith("#X connect "):
            continue
        a, _ao, b, _bi = ln[len("#X connect "):].rstrip(";").split()
        if int(b) in want:
            out.append((int(a), int(b)))
    return out


def _emits_float(box):
    """Can this box's outlet 0 carry a number?"""
    cls = box.split()[0] if box.split() else ""
    return cls in ("f", "float", "i", "int") or box.startswith("t f")


def _wrapping():
    """A PASS IF runs past two hundred characters, so it is wrapped and
    indented rather than left to the terminal to fold."""
    print("\n--- how a step's prose is laid out ---")
    import run as R

    long = ("Touch nothing and the bench moves knob 1 to the bottom for you. "
            "You get one of two screens and both of them are correct in their "
            "own way depending on where the knob was when it was last saved.")
    out = R._field("PASS IF:", long).splitlines()
    A.check("a long field wraps rather than running off the line",
            len(out) > 1, "%d line(s) for %d characters" % (len(out), len(long)))
    A.check("no wrapped line is longer than the wrap width",
            max(len(x) for x in out) <= R.WRAP,
            "longest is %d against a width of %d" % (max(len(x) for x in out),
                                                     R.WRAP))
    # Under the text, not the label: at the margin it reads as the next field.
    col = out[0].index("Touch")
    A.check("⛔ every continuation is indented under the text it continues",
            all(x.startswith(" " * col) and x[col:col + 1] != " "
                for x in out[1:]),
            "continuations start at %s, text starts at %d"
            % ([len(x) - len(x.lstrip()) for x in out[1:]], col))
    A.check("the words survive the wrap exactly",
            " ".join(" ".join(out).split()) == "PASS IF: " + long,
            "\n".join(out))
    A.check("a short field stays on one line",
            len(R._field("do      ", "Press pad 1.").splitlines()) == 1)


def _auto_format():
    """A predicate's evidence reads one line per leaf, a number beside its
    bound, rather than the whole conjunction on each of two lines."""
    print("\n--- how a predicate's evidence reads ---")
    import run as R

    rows = [(True, "M-BEATS = 20", "M-BEATS between 19 and 22"),
            (False, "C1-BEATS-ratio-1 = 0", "C1-BEATS-ratio-1 between 19 and 22"),
            (True, "C2-BEATS-ratio-1.5 / C1-BEATS-ratio-1 = 30 / 20 = 1.500",
             "C2-BEATS-ratio-1.5 / C1-BEATS-ratio-1 = 1.5 +/- 0.15")]
    out = _capture(R._say_auto, False, rows)
    body = [ln for ln in out.splitlines() if ln.strip()][1:]
    A.check("a multi-leaf predicate gets one line per thing it asserted",
            len(body) == len(rows),
            "%d line(s) for %d leaves:\n%s" % (len(body), len(rows), out))
    A.check("⛔ and the failing leaf is the marked one",
            body[1].endswith("<-- FAIL")
            and not body[0].endswith("<-- FAIL")
            and not body[2].endswith("<-- FAIL"),
            "the mark is on the rows that are fine, which hides the one that is "
            "not:\n%s" % out)

    # Both halves of a `print` predicate open on the name; it is said once.
    A.check("a counter's name appears once on its row, not twice",
            body[0].count("M-BEATS") == 1, body[0])

    # A ratio's shared run is `C2 / C1 =`; the label stops before the `=`.
    label, _w, _g = R._split("A / B = 1.5 +/- 0.15", "A / B = 30 / 20 = 1.500")
    A.check("a label does not end on an operator", label == "A / B",
            "label is %r" % label)

    # A satisfied single assertion has want and got identical: say it once.
    same = "DISP carries 'sp-pad 5'"
    out = _capture(R._say_auto, True, [(True, same, same)])
    body = [ln.strip() for ln in out.splitlines() if ln.strip()][1:]
    A.check("⛔ a single predicate that got what it wanted says it once",
            body == [same], "%r" % body)

    out = _capture(R._say_auto, False,
                   [(False, "missing 'sp-pad 5'", "DISP carries 'sp-pad 5'")])
    body = [ln.strip() for ln in out.splitlines() if ln.strip()][1:]
    A.check("a single predicate that did not keeps want and got apart",
            len(body) == 2 and body[0].startswith("want")
            and body[1].startswith("got"), "%r" % body)


def _capture(fn, *a):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a)
    return buf.getvalue()


def _where_wiring():
    """Every generated bench answers `where` and `show`, or GO recovery talks
    to nobody."""
    print("\n--- where and show, in the generated benches ---")
    m = S.RE_WHERE.search("print: %s: 16 1" % S.SAY_WHERE)
    A.check("protocol: the where regex reads what [print %s] writes" % S.SAY_WHERE,
            bool(m) and m.groups() == ("16", "1"),
            "groups %s" % str(m.groups() if m else None))

    import glob
    files = sorted(glob.glob(os.path.join(ROOT, "test/bench/*-bench.pd")))
    # Exact, like EXPECT and MIDI_EXPECT, so a bench that stops being generated
    # cannot leave this checking fewer files. Change it deliberately.
    A.check("every bench file is checked -- %d of them" % len(files),
            len(files) == 9, "found %d" % len(files))
    for path in files:
        src = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        A.check("%s routes go rerun where show" % name,
                "route go rerun where show" in src,
                "the runner can ask this bench nothing, so a lost GO ends the "
                "session exactly as it did before")
        A.check("%s prints its position" % name,
                "print %s" % S.SAY_WHERE in src)
        # $0-do-show carries the step number: the describe chain is one
        # [select N] per step, so a bang matches none and the re-describe is a
        # silent no-op.
        bad = [_boxes(src)[a] for a, b in _feeds(src, r"s \\\$0-do-show")
               if not _emits_float(_boxes(src)[a])]
        A.check("%s feeds $0-do-show a float and never a bang" % name,
                not bad, "fed by %s -- a bang matches no [select N] and the "
                         "step is silently not re-described" % bad)


def _bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _real_results():
    """-> (latest.json's bytes, the run files' names) in the real test/results."""
    try:
        runs = sorted(os.listdir(os.path.join(REAL_RESULTS, "runs")))
    except OSError:
        runs = []
    return _bytes(os.path.join(REAL_RESULTS, "latest.json")), runs


def main():
    os.makedirs(WORK, exist_ok=True)
    os.chdir(ROOT)
    real_before = _real_results()
    bench = S.load(BENCH)
    n = len(bench.steps)

    # -- the protocol's two halves must agree ------------------------------
    # The generator's format strings and the runner's regexes are one
    # agreement; drift reads as a stall on a working bench.
    m = S.RE_STEP.search("print: " + S.SAY_STEP % (3, 14, "a title"))
    A.check("protocol: the step regex reads what the step format writes",
            bool(m) and m.group(1) == "03" and m.group(2) == "14"
            and m.group(3) == "a title",
            "groups %s" % str(m.groups() if m else None))
    m = S.RE_FIRED.search("print: " + S.SAY_FIRED % (3, 4))
    A.check("protocol: the fired regex reads what the fired format writes",
            bool(m) and m.group(1) == "3", "groups %s" % str(m.groups() if m else None))
    m = S.RE_FIRED.search("print: " + S.SAY_FIRED_LAST % 14)
    A.check("protocol: and the LAST-step wording too -- different text, same "
            "marker", bool(m) and m.group(1) == "14",
            "groups %s" % str(m.groups() if m else None))
    A.check("protocol: the complete regex reads what the complete format writes",
            bool(S.RE_COMPLETE.search("print: " + S.SAY_COMPLETE)))

    _where_wiring()
    _auto_format()
    _wrapping()
    _stall()
    _recovery(bench)
    _interrupt_before_fire(bench)
    _mirror()

    # The child must not inherit stdin: ssh reads it greedily, so the runner's
    # prompt and the ssh child race for every keystroke. Static, because only a
    # real subprocess shows it and a live check would need the rig.
    tsrc = open(os.path.join(ROOT, "test/runner/targets.py"), encoding="utf-8").read()
    A.check("⛔ the launched child gets stdin=DEVNULL -- ssh must not eat the "
            "runner's keystrokes",
            "stdin=subprocess.DEVNULL" in tsrc,
            "targets.py's Popen does not close the child's stdin. With ssh on "
            "the other end that makes a device bench unsteppable by a person, "
            "and it reports as a stall rather than as anything to do with input")

    _holds()
    _predicates()

    clean = transcript(bench)

    # -- 1. a clean transcript ---------------------------------------------
    rc, out = run(write("clean.txt", clean), _keys(bench))
    A.check("clean: exits 0", rc == 0, "rc=%d" % rc)
    A.check("clean: every step passed",
            ("%d passed" % n) in out, _tail(out))

    # Every step is read before it is run, including one with nothing to do,
    # or GO fires before its watch text is read. Counted against the step
    # table, and anchored at line start, since a step's own `do` text can say
    # "press enter".
    prompts = len(re.findall(r"(?m)^  Press ENTER", out))
    A.check("clean: every step gets a read prompt before GO -- not just hands "
            "steps", prompts == n, "%d prompts for %d steps" % (prompts, n))

    # [r]epeat asks again and advances nothing: it fires the current step a
    # second time so a person can read an OLED row that ages out in ~1.3 s.
    # Against a replay nothing fires again and the run must carry on. The step
    # count is the assertion: a repeat that consumed a GO would desync. The "r"
    # goes to the first prompt that asks a person; a read prompt would swallow
    # it as an enter.
    rkeys, done = [], False
    for step in bench.steps:
        rkeys.append("")
        if not done:
            rkeys.append("r")
            done = True
        rkeys.append("p")
    assert done, "runner-assert: no step in %s is judged by a person" % BENCH
    rc, out = run(write("clean.txt", clean), rkeys)
    A.check("repeat: asks again rather than advancing the bench",
            rc == 0 and ("%d passed" % n) in out and "DESYNC" not in out,
            "rc=%d -- %s" % (rc, _tail(out)))
    A.check("repeat: still describes each step exactly once",
            len(re.findall(r"(?m)^  Press ENTER", out)) == n,
            "%d prompts for %d steps -- a repeat re-described its step"
            % (len(re.findall(r"(?m)^  Press ENTER", out)), n))
    A.check("repeat: says so plainly when the source cannot fire again",
            out.count("not available against a recorded console") == 1,
            _tail(out))

    # A predicate is evidence and a person is the verdict: the predicate reads a
    # bus, the PASS IF describes a screen, and the two can disagree.
    checks = [st for st in bench.steps if st.meta.get("check")]
    A.check("this bench still has predicate steps to prove it with",
            len(checks) >= 3, "%d steps carry a check" % len(checks))
    rc, out = run(write("clean.txt", clean), _keys(bench, verdict="f", note="x"))
    A.check("⛔ a person's FAIL stands over a passing predicate",
            rc != 0 and ("%d failed" % n) in out,
            "rc=%d -- every step should be the person's fail, not the "
            "predicate's pass\n%s" % (rc, _tail(out)))
    A.check("⛔ and the disagreement is reported rather than buried",
            out.count("the bus said") >= len(checks),
            "%d disagreements reported for %d predicate steps"
            % (out.count("the bus said"), len(checks)))

    # --auto-only is the unattended run, where the predicate is the verdict.
    rc, out = run(write("clean.txt", clean), [], auto_only=True)
    A.check("--auto-only: a predicate still answers with nobody in the room",
            ("%d passed" % len(checks)) in out, _tail(out))
    A.check("--auto-only: a step with no predicate is SKIPPED and never passed",
            "no predicate, and --auto-only" in out, _tail(out))

    # -- 2. truncated at step 7 --------------------------------------------
    # Must not pass: seven good verdicts and a console that stops is not a run.
    rc, out = run(write("truncated.txt", transcript(bench, upto=7)), _keys(bench))
    A.check("truncated: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("truncated: says STALLED rather than reporting a pass",
            "STALLED" in out and "RESULT: PASS" not in out, _tail(out))
    # A bare "STALLED" is a report nobody can act on; three facts tell the
    # causes apart.
    A.check("truncated: the stall says whether GO was sent",
            "GO sent" in out, _tail(out, 12))
    A.check("truncated: ...and how far behind the reader was",
            "waiting unread" in out, _tail(out, 12))
    A.check("truncated: ...and shows the last lines it did see",
            "the last" in out and "line(s) seen:" in out, _tail(out, 12))

    # -- 2b. GO sent and nothing fires -------------------------------------
    # A different handler from the one above: this stalls waiting for the step
    # to fire, not for the next description.
    rc, out = run(write("nofire.txt",
                        transcript(bench, upto=7, stop_before_fired=True)),
                  _keys(bench))
    A.check("no fired line: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("no fired line: says STALLED and does not pass the step",
            "STALLED" in out and "RESULT: PASS" not in out, _tail(out))
    A.check("no fired line: the 6 steps that did fire are kept",
            "6 passed" in out, _tail(out))

    # -- 3. step numbers out of order --------------------------------------
    # Must abort, not shift: a silent resync records every later verdict
    # against the wrong question. Only the marker is renumbered, so only
    # check_marker can catch it.
    rc, out = run(write("desync-marker.txt",
                        transcript(bench, marker_n=lambda i: i + 1 if i > 1 else i)),
                  _keys(bench))
    A.check("desync by step number: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by step number: aborts and says so", "DESYNC" in out, _tail(out))
    A.check("desync by step number: does NOT report a full tally",
            ("%d passed" % n) not in out, _tail(out))

    # -- 3b. the right number, the wrong question --------------------------
    # A bench regenerated from a reordered table still counts 1, 2, 3; only
    # the title catches it.
    rc, out = run(write("desync-title.txt",
                        transcript(bench, retitle=lambda i, t:
                                   "a step that is not in the table" if i == 4 else t)),
                  _keys(bench))
    A.check("desync by title: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by title: aborts naming the title mismatch",
            "DESYNC" in out and "title" in out, _tail(out))

    # -- 3c. a bench generated from a different table -----------------------
    rc, out = run(write("desync-of.txt", transcript(bench, of=99)), _keys(bench))
    A.check("desync by step count: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by step count: says the tables differ",
            "DESYNC" in out, _tail(out))

    # -- 3d. the step described is not the step that ran --------------------
    # Every fixture above corrupts the description, so all are caught before
    # the fired line is compared. This one describes step N and fires N+1.
    rc, out = run(write("desync-fired.txt",
                        transcript(bench, fired_n=lambda i: i + 1 if i > 1 else i)),
                  _keys(bench))
    A.check("desync by fired line: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by fired line: aborts saying which step actually fired",
            "DESYNC" in out and "fired" in out, _tail(out))
    A.check("desync by fired line: does NOT report a full tally",
            ("%d passed" % n) not in out, _tail(out))

    # -- 4. an empty file ---------------------------------------------------
    rc, out = run(write("empty.txt", []), _keys(bench))
    A.check("empty: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("empty: names the cause -- the bench never loaded",
            "NEVER LOADED" in out.upper(), _tail(out))
    # "Never loaded" is inferred from a timeout; nothing read at all is the
    # direct evidence for it.
    A.check("empty: the report says nothing was read at all, rather than "
            "showing a tail of lines that do not exist",
            "NOTHING has been read" in out, _tail(out, 12))

    # -- 5. interrupted part-way -------------------------------------------
    # These assert properties, not arithmetic, so a step becoming
    # machine-checkable cannot break them. The run ends on the keys running
    # out; "q" is no longer a key.
    rc, out = run(write("interrupt.txt", clean), _keys(bench, stop_after=4))
    A.check("interrupted: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("interrupted: keeps the verdicts it did get rather than discarding",
            _tally(out)["pass"] > 0, _tail(out))
    A.check("interrupted: does not silently finish the bench",
            _tally(out)["notrun"] > 0, _tail(out))
    A.check("interrupted: prints a resume command for the step it stopped on",
            _resumes_at_last_step(out), _tail(out))

    # -- 6. every verdict failed --------------------------------------------
    # A bench of failures must never come out green. That a skip is never a
    # pass is section 7c's.
    rc, out = run(write("allfail.txt", clean), _keys(bench, "f", "x"))
    A.check("all failed: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("all failed: RESULT is FAIL, never PASS",
            "RESULT: FAIL" in out and "RESULT: PASS" not in out, _tail(out))

    # -- 7. the runner runs out of scripted answers -------------------------
    # The provider exhausts rather than repeating its last key, or a transcript
    # longer than its key list would pass by accident.
    rc, out = run(write("shortkeys.txt", clean), _keys(bench, stop_after=2))
    A.check("exhausted keys: exits non-zero rather than inventing verdicts",
            rc != 0, "rc=%d" % rc)
    A.check("exhausted keys: keeps the real verdicts and finishes nothing else",
            _tally(out)["pass"] > 0 and _tally(out)["notrun"] > 0, _tail(out))

    # -- 7b. a real SIGINT, at a real prompt --------------------------------
    # Ctrl-C is neither quit nor fail: the step in flight has no verdict. It is
    # sent by pid, not pkill -f, whose pattern also matches the harness.
    rc, out = _sigint(write("sigint.txt", clean))
    A.check("SIGINT: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("SIGINT: says INTERRUPTED rather than quit or fail",
            "INTERRUPTED" in out, _tail(out))
    A.check("SIGINT: prints a resume command for the step in flight",
            _resumes_at_last_step(out), _tail(out))
    A.check("SIGINT: records no failure for the step nobody judged",
            _tally(out)["fail"] == 0 and _tally(out)["notrun"] > 0, _tail(out))

    # -- 7c. paper mode: an absent oracle is a SKIP, never a FAIL -----------
    # There is no Pd in paper mode, so a predicate needing a console has an
    # empty window and must be skipped, not failed.
    import predicates as P
    console = [s for s in bench.steps
               if s.meta.get("check")
               and not P.offline(s.meta["check"])[0]
               and "paper" in (s.meta.get("targets") or ("paper",))]
    rc, out = run_paper(_paper_keys(bench))
    A.check("paper: a predicate needing a console is SKIPPED, not failed",
            out.count("reads the console") == len(console),
            "%d skips for %d console predicates -- %s"
            % (out.count("reads the console"), len(console), _tail(out)))
    # A skip and a fail both keep RESULT off PASS, so counting skips alone
    # would stay green if the empty-window failure came back beside them.
    A.check("paper: nothing reports AUTO FAIL out of an empty window",
            "AUTO FAIL" not in out, _tail(out))
    A.check("paper: the reason names the kind that could not be judged",
            "`bus`" in out or "`bus-count`" in out, _tail(out))
    # And a skip is still not a pass: those steps remain unjudged.
    A.check("paper: skips keep RESULT off PASS", rc != 0 and "RESULT: PASS"
            not in out, "rc=%d / %s" % (rc, _tail(out)))

    # -- 8. and the real results were never touched --------------------------
    # latest.json is committed and the run files beside it are the benches'
    # record; both describe hardware. With the scratch roll-up removed, a
    # replay must leave it absent and a paper run must write it. By presence,
    # not content: two runs in one second write identical bytes.
    import records
    if os.path.exists(records.LATEST):
        os.remove(records.LATEST)
    run(write("clean2.txt", clean), _keys(bench))
    after_replay = os.path.exists(records.LATEST)
    run_paper(_paper_keys(bench))
    after_paper = os.path.exists(records.LATEST)
    A.check("a replay rolls nothing up", not after_replay,
            "%s was written by a replay" % records.LATEST)
    runs = os.listdir(records.RUNS) if os.path.isdir(records.RUNS) else []
    A.check("...and the fixtures' records went to scratch: run files, and the "
            "paper run's roll-up",
            bool(runs) and after_paper,
            "%d run file(s) in %s, and the paper run %s the roll-up there. "
            "Nothing written at all also passes the two checks below"
            % (len(runs), records.RUNS,
               "wrote" if after_paper else "did not write"))
    real_after = _real_results()
    A.check("⛔ the committed latest.json is byte for byte what it was",
            real_after[0] == real_before[0],
            "%s/latest.json changed while this gate ran" % REAL_RESULTS)
    leaked = sorted(set(real_after[1]) - set(real_before[1]))
    gone = sorted(set(real_before[1]) - set(real_after[1]))
    A.check("⛔ test/results/runs/ holds exactly the files it held before",
            not leaked and not gone,
            "%d new run file(s), %s; %d gone. A fixture's invented verdicts "
            "are now beside the benches' real ones"
            % (len(leaked), leaked[:3], len(gone)))

    print()
    rc = A.report()
    if not rc:
        import shutil
        shutil.rmtree(WORK, ignore_errors=True)
    else:
        print("fixtures kept at %s" % WORK)
    return rc


def _predicates():
    """Every predicate kind, against a synthetic window, each one both ways: a
    predicate never seen to fail is not a check. The hardware run asks the
    separate question of whether the stream is real.
    """
    import predicates as P

    # what a screen redraw actually looks like: gClear, rows, gFlip
    def frame(*rows):
        out = ["OLED: sendtyped /oled/gClear ii 3 1"]
        for r in rows:
            words = r.split()
            tag = "iiiii" + "s" * len(words)
            out.append("OLED: sendtyped /oled/gPrintln %s 3 2 8 16 1 %s" % (tag, r))
        out.append("OLED: sendtyped /oled/gFlip i 3")
        return out

    good = frame("grain", "12")
    stale = frame("grain", "12 %")            # the bug: the unit survived

    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["grain", "12"]}, good)
    A.check("oled: a clean value row passes", ok, got)
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["grain", "12"]}, stale)
    A.check("oled: THE STALE UNIT FAILS -- a row of '12 %' is not a row of '12'",
            not ok, got)
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["grain"]}, [])
    A.check("oled: an empty window FAILS rather than passing vacuously",
            not ok, got)

    # The last complete frame: a window spans a repaint, so earlier frames
    # still show what was there before the step.
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["12"], },
                            frame("chop-size", "43 %") + good)
    A.check("oled: judged on the LAST frame, not on every frame in the window",
            ok, got)
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["43 %"]},
                            frame("chop-size", "43 %") + good)
    A.check("oled: and an earlier frame's content does NOT count",
            not ok, got)

    # `8` and `16` are the font size and y in every line above, not text.
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["16"]}, good)
    A.check("oled: a font size or coordinate never satisfies a text assertion",
            not ok, got)

    bus = ["DISP: sp-pad 5", "DISP: sp-bank 1", "ERR: warn u_tempo bpm-out-of-range"]
    ok, _, got = P.evaluate({"kind": "bus", "bus": "DISP", "has": ["sp-pad 5"]}, bus)
    A.check("bus: finds what is there", ok, got)
    ok, _, got = P.evaluate({"kind": "bus", "bus": "DISP", "has": ["sp-pad 13"]}, bus)
    A.check("bus: THE OLD 47+n FORMULA FAILS -- pad 5 reading 13", not ok, got)

    ok, _, got = P.evaluate(
        {"kind": "bus-count", "bus": "ERR", "match": "u_tempo", "n": 1}, bus)
    A.check("bus-count: exactly one is one", ok, got)
    ok, _, got = P.evaluate(
        {"kind": "bus-count", "bus": "ERR", "match": "u_tempo", "n": 1},
        bus + ["ERR: warn u_tempo bpm-out-of-range"])
    A.check("bus-count: A SECOND ALERT FAILS -- which 'at least one' could not "
            "catch", not ok, got)
    ok, _, got = P.evaluate(
        {"kind": "bus-count", "bus": "ERR", "match": "u_tempo", "n": 1}, [])
    A.check("bus-count: nothing at all also fails", not ok, got)

    counts = ["M-BEATS: 20", "C1-BEATS-ratio-1: 20", "C2-BEATS-ratio-1.5: 30"]
    ok, _, got = P.evaluate({"kind": "print", "name": "M-BEATS",
                             "min": 19, "max": 22}, counts)
    A.check("print: a count in range passes", ok, got)
    ok, _, got = P.evaluate({"kind": "print", "name": "M-BEATS",
                             "min": 19, "max": 22}, ["M-BEATS: 0"])
    A.check("print: ZERO FAILS -- the dead-clock and DSP-off signature",
            not ok, got)
    ok, _, got = P.evaluate({"kind": "print", "name": "M-BEATS",
                             "min": 19, "max": 22}, [])
    A.check("print: a counter that never printed fails rather than passing "
            "vacuously", not ok, got)
    # `BEATS` is a substring of all three names above.
    ok, _, got = P.evaluate({"kind": "print", "name": "BEATS",
                             "min": 19, "max": 22}, counts)
    A.check("print: the label is anchored -- BEATS does not match M-BEATS",
            not ok, got)

    ok, _, got = P.evaluate({"kind": "ratio", "a": "C2-BEATS-ratio-1.5",
                             "b": "C1-BEATS-ratio-1", "want": 1.5}, counts)
    A.check("ratio: 30 over 20 is 1.5", ok, got)
    ok, _, got = P.evaluate({"kind": "ratio", "a": "C2-BEATS-ratio-1.5",
                             "b": "C1-BEATS-ratio-1", "want": 1.5},
                            ["C1-BEATS-ratio-1: 0", "C2-BEATS-ratio-1.5: 0"])
    A.check("ratio: a zero denominator fails rather than raising", not ok, got)

    osc = ["OSC: /cutit/hb 41", "OSC: /cutit/param grain 12"]
    ok, _, got = P.evaluate({"kind": "osc", "addr": "/cutit/param",
                             "has": ["grain"]}, osc)
    A.check("osc: finds a parameter on the wire", ok, got)
    ok, _, got = P.evaluate({"kind": "osc", "addr": "/cutit/param",
                             "has": ["grain"]}, [])
    A.check("osc: silence FAILS where traffic was asserted -- a dead u_net "
            "looks exactly like this", not ok, got)
    # A purely negative spec is satisfied by silence, which is safe only
    # because the lint refuses a bare has_not: its witness is a sibling.
    ok, _, got = P.evaluate({"kind": "osc", "addr": "/cutit/param",
                             "has_not": ["in-l"]}, [])
    A.check("osc: silence SATISFIES a purely negative spec", ok, got)
    ok, _, got = P.evaluate({"kind": "osc", "addr": "/cutit/param",
                             "has_not": ["grain"]}, osc)
    A.check("osc: and a forbidden name still fails", not ok, got)

    try:
        P.evaluate({"kind": "buscount", "bus": "ERR"}, [])
        A.check("an unknown kind is a failure, not a silent pass", False,
                "it returned instead of raising")
    except P.BadSpec:
        A.check("an unknown kind is a failure, not a silent pass", True)


def _sigint(transcript_path):
    """Block the runner at a verdict prompt, then interrupt it. -> (rc, output).

    No --keys: a key list that runs out raises EOF, a different branch. An
    open pipe nobody writes to is what blocks a person's prompt.
    """
    import selectors
    import signal
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path, "--target", "device"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

    # Wait for whichever prompt comes first, not a guessed sleep. The read must
    # time out, or a blocked child hangs the suite; and it reads the raw fd with
    # os.read, since a buffered reader hides bytes select() has already seen.
    sel = selectors.DefaultSelector()
    sel.register(p.stdout.fileno(), selectors.EVENT_READ)
    buf = b""
    deadline = time.time() + 20
    while not (b"verdict?" in buf or b"Press ENTER" in buf):
        if time.time() >= deadline:
            break
        if not sel.select(timeout=0.25):
            continue
        chunk = os.read(p.stdout.fileno(), 4096)
        if not chunk:
            break
        buf += chunk
    sel.close()
    p.send_signal(signal.SIGINT)
    try:
        rest, _ = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        rest, _ = p.communicate()
    return p.returncode, (buf + rest).decode("utf-8", "replace")


def _tally(out):
    """The summary line's counts, so a fixture asserts a property of the run."""
    import re
    m = re.search(r"Steps\s+(\d+) passed, (\d+) failed, (\d+) skipped, "
                  r"(\d+) not run", out)
    if not m:
        return {"pass": -1, "fail": -1, "skip": -1, "notrun": -1}
    return dict(zip(("pass", "fail", "skip", "notrun"),
                    (int(g) for g in m.groups())))


def _resumes_at_last_step(out):
    """The resume command must name the step the runner said it stopped on,
    not the last header printed: whether that reached the pipe before the
    signal is a buffering question."""
    import re
    m = re.findall(r"(?:INTERRUPTED at step|stopped at step|stopped before "
                   r"step) (\d+)", out)
    return bool(m) and ("--from %s" % m[-1]) in out


def _keys(bench, verdict="p", note=None, stop_after=None):
    """The keystrokes a person would type to give every step `verdict`,
    derived from the bench: every step takes a read prompt, then a verdict.
    The prompt-count check in main() is what guards the read prompt, against
    the step table rather than this list.
    """
    out = []
    for step in bench.steps:
        if stop_after is not None and step.n > stop_after:
            break
        out.append("")                   # the read prompt, every step
        # A person answers every step; a predicate is evidence.
        out.append(verdict)
        if note is not None:
            out.append(note)
    return out


def _paper_keys(bench, verdict="p"):
    """The keystrokes a paper-mode run of `bench` consumes. run_bench has no GO
    and so no read prompt: a step is skipped, judged by a predicate, or asked
    of a person, and only the last takes a key.
    """
    import predicates as P
    out = []
    for step in bench.steps:
        want = step.meta.get("targets")
        if want and "paper" not in want:
            continue                     # skipped: this target cannot judge it
        spec = step.meta.get("check")
        if spec:
            continue                     # skipped for want of a console, or auto
        out.append(verdict)
    return out


def _interleave(pair, n):
    out = []
    for _ in range(n):
        out.extend(pair)
    return out


def _tail(out, n=6):
    return " / ".join(l.strip() for l in out.strip().splitlines()[-n:] if l.strip())


if __name__ == "__main__":
    sys.exit(main())
