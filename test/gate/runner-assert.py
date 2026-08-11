#!/usr/bin/env python3
"""THE RUNNER'S OWN GATE -- ref/module/... none; it answers for test/README.md.

    python3 test/gate/runner-assert.py        # ~1 s, no Pd, no device
    python3 test/gate/runner-assert.py -v

⛔ THIS IS THE ONLY THING THAT EVER EXERCISES THE RUNNER'S FAILURE PATHS. A
successful hardware bench run never stalls, never desyncs, is never interrupted
and never meets an empty console -- so on hardware alone every one of those
branches could be dead code and every run would look exactly the same, green.
That is the shape of a gate that lies, and this project has shipped it twice.

⛔ THE FIXTURES ARE GENERATED FROM THE REAL STEP TABLE, never hand-typed. A
hand-written transcript is a guess at what a bench prints, and a guess that
drifts makes this gate assert the runner agrees with a fiction. Generating from
bench_steps means the day somebody rewords a step, these fixtures reword with it
-- and the one fixture that must NOT match (the desync) is built by deliberately
corrupting a generated one, so it stays wrong in exactly one known way.

⚠️ IT IS MAC-ONLY, HEADLESS AND UNDER A SECOND, which is what lets it sit in the
gate table without costing the bare `./test/run.sh` its guarantee.
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

import lib_assert as A                                          # noqa: E402
import steps as S                                               # noqa: E402
import stream                                                   # noqa: E402

WORK = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                    "cutit-runner-assert-%d" % os.getpid())
# ⚠️ 18 steps, no actions anywhere -- the cheapest table to recite, and the only
# one that is ALSO a paper bench, which is what lets the fixtures below drive
# both of the runner's two loops from one step table. (This comment said 14 for
# as long as it took three hot-swap steps to be added above it, and 17 for as
# long as it took the fourth.)
BENCH = "midi"


# ---------------------------------------------------------------------------
def transcript(bench, upto=None, stop_before_fired=False,
               marker_n=None, of=None, retitle=None, fired_n=None):
    """What that bench prints on Pd's console.

    ⚠️ EVERY LINE CARRIES Pd's OWN "print: " PREFIX, because the bench says
    everything through a bare [print]. Leaving it off would let the runner's
    regexes be anchored at the start of a line and still pass here, then fail on
    real hardware -- a fixture that is easier than reality is worse than none.

    ⛔ THE CORRUPTIONS ARE SEPARATE KNOBS, and that is the lesson of the first
    mutation run. One combined "desync" fixture renumbered the marker AND the
    fired line together, so it was always caught by the fired-line check and the
    marker check underneath it was never exercised at all -- deleting that check
    outright left this gate fully green. A fixture that trips two guards at once
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
        # ⛔ A STEP WITH A PREDICATE NEEDS TRAFFIC TO JUDGE, or the loop fixtures
        # stop being about the loop and start failing on the absence of a bus.
        # These emit the stream a PASSING step would have produced -- which is
        # circular as a test OF the predicate, and is not one: _predicates()
        # tests those directly, both ways, against synthetic windows. Here the
        # question is only whether the loop records what the predicate said.
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
    """Drive a real PAPER-mode run. -> (exit code, output).

    ⛔ NO TRANSCRIPT, BECAUSE PAPER MODE HAS NO STREAM. That is the whole point
    of it: `midi` and `state` have no actions anywhere, so nothing has to be
    driven -- no Pd, no ssh, and no Launchpad left stranded in Programmer Mode.
    This is the only fixture here that exercises run_bench rather than
    run_bench_driven, and until it existed that loop had no gate at all.

    ⛔ CUTIT_RESULTS IS NOT OPTIONAL. Paper mode is a NORMAL run, so run.py rolls
    its verdicts up into latest.json -- and latest.json is committed and
    describes hardware. A fixture writing invented verdicts there would destroy
    the one property that file has. The replay path refuses to roll up at all;
    this one is redirected instead, and check 8 proves the redirect held.
    """
    kp = write("paper.keys", keys)
    env = dict(os.environ, CUTIT_RESULTS=os.path.join(WORK, "results"))
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--target", "paper", "--keys", kp],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def run(transcript_path, keys, auto_only=False):
    """Drive the real runner over a fixture. -> (exit code, output)."""
    kp = write(os.path.basename(transcript_path) + ".keys", keys)
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path, "--keys", kp]
        + (["--auto-only"] if auto_only else []) + [
         # ⚠️ A TRANSCRIPT IS A RECORDING OF A DEVICE RUN, so it is replayed as
         # one. Without this, every step carrying `targets: ('device',)` is
         # skipped -- correctly -- and each one shifts the counts these fixtures
         # assert, so adding a device-only predicate would break them all.
         "--target", "device"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
def _holds():
    """⛔ WHICH STEPS MAY BE HELD ON SCREEN, and the direction of every error.

    The runner re-fires a step while its verdict is open, because g_oled ages a
    parameter row out after ~1.3 s and a person cannot read one in that. For a
    step whose subject IS that decay, re-firing resets the timer under test and
    the step can never fail again -- so this asserts the exemptions hold, and
    that at least one real parameter step still gets its hold. Both halves are
    needed: "nothing holds" would satisfy the safety check on its own.
    """
    print("\n--- which steps may be held on screen ---")
    disp, nano, lp = S.load("display"), S.load("nanokontrol"), S.load("launchpad")

    held = [st for b in (disp, nano, lp) for st in b.steps if st.holds]
    A.check("some step is actually held -- the exemptions have not eaten "
            "everything", len(held) >= 10,
            "%d steps hold. A zero here passes every safety check below while "
            "delivering none of the point" % len(held))

    A.check("⛔ a parameter step IS held -- the case this exists for",
            disp.steps[2].holds and disp.steps[3].holds,
            "display 3 %s / display 4 %s -- these are the OLED rows that "
            "vanish in 1.3 s" % (disp.steps[2].holds, disp.steps[3].holds))

    # ⛔ EACH OF THESE ASSERTS A TIMEOUT. Re-firing resets it.
    # ⚠️ ALL THREE USED TO NAME nanokontrol OR A LOWER display NUMBER. The OLED
    # steps that had been copied into the nanokontrol bench were folded back
    # into display, which is what they were always about -- see test/README.md.
    for b, n, why in ((disp, 10, "about 2 s later it vanishes"),
                      (disp, 13, "recording returns after about 4 s"),
                      (disp, 17, "clears itself after 30 s"),
                      (lp, 13, "clears ITSELF about thirty seconds later"),
                      (lp, 11, "goes back to the mode lamps by itself")):
        st = b.steps[n - 1]
        A.check("⛔ %s step %d is NOT held -- it tests %s" % (b.name, n, why),
                not st.holds,
                "holding it re-sends the message that starts the timer under "
                "test\n     %s" % st.pass_if)

    # ⛔ STRUCTURAL, NOT PROSE. A measure step re-arms or re-reads a beat
    # counter; a step with no actions has nothing to re-send in the first place.
    for b in (disp, nano, lp, S.load("tempo"), S.load("phone"),
              S.load("state"), S.load("midi")):
        bad = [st.n for st in b.steps if st.holds and (st.measure or not st.actions)]
        A.check("%s: no measure step and no action-less step is held" % b.name,
                not bad, "steps %s" % bad)


class Trickle(stream.Source):
    """A source that says something every `gap` seconds and answers late.

    ⛔ IT EXISTS TO PROVE A STALL IS SILENCE AND NOT SLOWNESS. wait_for used to
    fix its deadline before the loop, so `timeout` was the total time the call
    could take however much the patch was saying -- and that ended a hands-on
    bench session on nanokontrol 15, which asks a person to sweep every fader
    BEFORE pressing enter. Each CC is three console lines and the device's
    console was measured at about 98 lines a second, so the fired line arrived
    behind five seconds of the person's own traffic and the runner called a
    working bench a stall.

    ⚠️ NO REPLAY CAN SHOW THIS. Replay hands over its whole transcript at once,
    so every deadline in it is met trivially; the defect only exists where lines
    arrive over TIME, which is every real target and no fixture until this one.
    """

    realtime = True

    def __init__(self, filler, answer, gap=0.05):
        self.left = list(filler) + [answer]
        self.gap = gap

    def readline(self, timeout):
        if not self.left:
            return None
        # ⚠️ IT HONOURS THE TIMEOUT. A source that always returned a line would
        # pass whatever wait_for did with its clock, which is the whole subject.
        if timeout < self.gap:
            time.sleep(max(0.0, timeout))
            return None
        time.sleep(self.gap)
        line = self.left.pop(0)
        self._note(line)
        return line


class Chatter(stream.Source):
    """A patch that says something forever and never answers.

    ⛔ IT HAS NO END, which is the point: the bound under test is wait_for's,
    not the fixture's. LIMIT is the GATE's safety net -- reaching it means the
    cap did nothing and the check reports that rather than hanging.
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

    ⛔ THIS IS THE ONLY THING THAT EVER EXERCISES GO RECOVERY. A lost datagram
    cannot be provoked on demand on real hardware, and a replay cannot answer a
    question at all -- so `where`, `show`, _ask_where, _regain_fired and
    _next_step would every one of them be dead code that no run could
    distinguish from working code.

    ⚠️ `drop` IS A SET OF GO NUMBERS, counted the way the runner counts them, so
    a fixture can say "the third datagram never arrived" and mean it.
    ⚠️ `lose` IS A SET OF STEP NUMBERS whose DESCRIBE line goes missing -- the
    other half, where the GO did land and the answer to it did not.
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
    """A bench with a PERSON in front of it, which is the case that broke.

    ⛔ NOTHING READS THE CONSOLE EXCEPT A WAIT, so everything the instrument
    says while a verdict is open piles up in the queue. On a hands step that is
    the person's own doing -- a sweep of nine faders is three lines per CC at
    about 98 lines a second -- and it was 4141 lines deep after two steps of a
    real run. Carried into the next step it does two things: the wait burns its
    line cap on console that was already judged, and every one of those lines
    lands in the next step's PREDICATE WINDOW.

    ⚠️ THE BACKLOG IS DEEPER THAN TWICE THE CAP ON PURPOSE. Shallower and the
    GO-recovery path rescues the run by accident -- `where` gets asked and
    answered from under the pile -- which is luck, not the flush working, and a
    fixture that passes on luck proves nothing. The real one was 4141 against a
    cap of 2000 and the recovery drowned in it too.
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
    """⛔ A STALL IS SILENCE. Slowness is not a fault and must not be reported
    as one."""
    print("\n--- what counts as a stall ---")
    marker = "print: " + S.SAY_FIRED % (7, 8)
    filler = ["print: PARAM: slider-3 0.5"] * 40

    t0 = time.time()
    src = Trickle(filler, marker, gap=0.05)
    # ⚠️ CAUGHT RATHER THAN LET FLY. Reverting the fix makes this raise, and an
    # uncaught Stalled ends the gate with a traceback -- red, but red in a way
    # that names a Python line instead of the property that broke.
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

    # ⛔ AND THE OTHER END OF IT. A patch that prints forever and never answers
    # would wait all night on silence alone, so the cap is what bounds it -- and
    # it counts LINES, which is the only bound a replay can be made to hit.
    # ⛔ AND THE OTHER END OF IT. A patch that prints forever and never answers
    # would wait all night on silence alone, so the cap is what bounds it -- and
    # it counts LINES, which is the only bound a replay can be made to hit.
    # ⚠️ THE SOURCE IS ENDLESS ON PURPOSE. Any finite fixture stalls at its own
    # end whether or not the cap exists, so asserting Stalled against one would
    # be green with the bound deleted. Chatter has only the gate's own safety
    # net, far above LINE_CAP, and the check is WHERE it stopped.
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
    """⛔ A LOST GO MUST NOT END THE SESSION, and must not be guessed at either.

    GO travels as one UDP datagram and UDP guarantees nothing. A lost one and a
    dead patch produce identical silence, and the two want opposite responses --
    resend, or stop. `where` is what separates them, and these are the only
    checks that ever run that path.
    """
    print("\n--- recovering a lost GO ---")
    import records
    import run as R

    saved_runs, saved_ask = records.RUNS, stream.ask_line
    records.RUNS = os.path.join(WORK, "runs")

    def drive(cls=Fake, **kw):
        src = cls(bench, **kw)
        stream.use(stream.keystrokes(write("fake.keys", _keys(bench))))
        try:
            rows, ok = R.run_bench_driven(bench, "device", False, 1, src)
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

        # ⛔ THE GO THAT RUNS STEP 3. The bench is left in phase 0, so the
        # recovery is to send it again -- and a runner that sent GO blindly
        # would be right here and catastrophically wrong in the arm below.
        src, rows, ok = drive(drop=[5])
        A.check("⛔ a lost GO before a step runs is resent, and the run finishes",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s -- the session ended on a dropped "
                "datagram" % (len(rows), len(bench.steps), ok))

        # ⛔ THE GO THAT ADVANCES. Identical silence, opposite cause: the bench
        # is in phase 1 and a second GO would advance it TWICE.
        src, rows, ok = drive(drop=[6])
        A.check("⛔ a lost GO before an advance is resent, and no step is "
                "skipped", len(rows) == len(bench.steps) and ok
                and [r["step"] for r in rows] == [s.n for s in bench.steps],
                "steps recorded: %s" % [r["step"] for r in rows])

        # ⛔ THE OTHER HALF: the GO landed and its ANSWER did not. Resending GO
        # here would advance a bench that is already where it should be, and
        # every verdict after it would answer the wrong question. `show` is what
        # makes that recoverable without moving anything.
        src, rows, ok = drive(lose=[4])
        A.check("⛔ a lost DESCRIBE line is asked for again rather than "
                "re-driven", len(rows) == len(bench.steps) and ok
                and [r["step"] for r in rows] == [s.n for s in bench.steps],
                "steps recorded: %s" % [r["step"] for r in rows])
        A.check("and it had to ask -- otherwise the check above is vacuous",
                src.asked > 0, "asked %d time(s)" % src.asked)

        # ⛔ A PERSON'S OWN TRAFFIC MUST NOT COUNT AGAINST THE PATCH. This is
        # the failure exactly as it happened: two hands-on steps, 4141 lines
        # queued, and the wait spent its whole line cap on a backlog that was
        # already judged.
        src, rows, ok = drive(cls=Noisy)
        A.check("⛔ a backlog from the previous step does not stall the next one",
                len(rows) == len(bench.steps) and ok,
                "%d rows of %d, ok=%s -- %d line(s) still queued. The wait is "
                "chewing through console that was already judged, and every "
                "line of it lands in the next step's predicate window too"
                % (len(rows), len(bench.steps), ok, src.pending()))
        # ⛔ AND NOT ONE LINE OF IT WAS READ. Completing is the weaker half:
        # the runner could grind through the whole backlog and still finish,
        # having put every stale line in a predicate window on the way. Zero is
        # the claim that matters, and it is what the flush buys.
        A.check("⛔ and not one line of the previous step's console was read "
                "into this step", src.read_junk == 0,
                "%d stale line(s) reached the step loop, and a predicate window "
                "is built out of exactly those" % src.read_junk)

        # ⛔ A BENCH THAT WILL NOT ANSWER IS STILL A STALL. Recovery must not
        # turn a dead patch into a green run, which is the failure mode of every
        # retry ever written.
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
        records.RUNS = saved_runs
        stream.use(saved_ask)


def _boxes(src):
    """Every box in a .pd, in file order -- which is what #X connect indexes.

    ⚠️ COMMENTS COUNT AND #X connect DOES NOT. Same rule as C-10 and as
    pd-layout-check.py, and getting it wrong here would silently read the wrong
    box for every cord.
    """
    return [ln.split(" ", 4)[-1].rstrip(";")
            for ln in src.splitlines()
            if ln.startswith(("#X obj ", "#X msg ", "#X text "))]


def _feeds(src, pattern):
    """Every cord landing on a box matching `pattern`. -> [(from, to)] indices."""
    boxes = _boxes(src)
    want = [i for i, b in enumerate(boxes) if re.fullmatch(pattern, b)]
    out = []
    for ln in src.splitlines():
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


def _where_wiring():
    """⛔ THE QUERY HAS TO BE IN THE PATCH, in every bench, or the recovery above
    is a conversation with nobody."""
    print("\n--- where and show, in the generated benches ---")
    m = S.RE_WHERE.search("print: %s: 16 1" % S.SAY_WHERE)
    A.check("protocol: the where regex reads what [print %s] writes" % S.SAY_WHERE,
            bool(m) and m.groups() == ("16", "1"),
            "groups %s" % str(m.groups() if m else None))

    import glob
    files = sorted(glob.glob(os.path.join(ROOT, "test/bench/*-bench.pd")))
    A.check("every bench file is checked -- %d of them" % len(files),
            len(files) == 7, "found %d" % len(files))
    for path in files:
        src = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        A.check("%s routes go rerun where show" % name,
                "route go rerun where show" in src,
                "the runner can ask this bench nothing, so a lost GO ends the "
                "session exactly as it did before")
        A.check("%s prints its position" % name,
                "print %s" % S.SAY_WHERE in src)
        # ⛔ $0-do-show CARRIES THE STEP NUMBER, NOT A BANG. The describe chain
        # is one [select N] per step, so a bang matches none of them and the
        # re-describe is a silent no-op -- indistinguishable from a step whose
        # text is already on screen, which is why the encoder's repeat was dead
        # from the day it was written and nothing noticed. `show` inherited the
        # same wire and a probe against real Pd caught it.
        bad = [_boxes(src)[a] for a, b in _feeds(src, r"s \\\$0-do-show")
               if not _emits_float(_boxes(src)[a])]
        A.check("%s feeds $0-do-show a float and never a bang" % name,
                not bad, "fed by %s -- a bang matches no [select N] and the "
                         "step is silently not re-described" % bad)


def main():
    os.makedirs(WORK, exist_ok=True)
    os.chdir(ROOT)
    bench = S.load(BENCH)
    n = len(bench.steps)

    # -- the protocol's two halves must agree ------------------------------
    # ⛔ THE GENERATOR'S FORMAT STRINGS AND THE RUNNER'S REGEXES ARE ONE
    # AGREEMENT. Drift makes the runner stop recognising a step, call it a
    # stall, and be wrong about a bench that is working perfectly.
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
    _stall()
    _recovery(bench)

    # ⛔ THE CHILD MUST NEVER INHERIT stdin, AND NO REPLAY FIXTURE CAN SEE THIS.
    # Every check in this file drives stream.Replay, which launches nothing --
    # so the one thing that only a real subprocess does went unguarded, and it
    # broke the device target completely: Popen inherits stdin by default and
    # `ssh` reads it greedily to forward to the remote command, so the runner's
    # own prompt and the ssh child raced for every keystroke. Down a pipe the
    # first prompt gets EOF; at a terminal the Enter that should send GO is
    # eaten by a Pd with no use for it. It is a static check because making it a
    # live one would need the rig.
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

    # ⛔ EVERY STEP IS READ BEFORE IT IS RUN, INCLUDING THE ONES WITH NOTHING TO
    # DO. The prompt used to be guarded on `step.hands`, so a step carrying no
    # `do` had GO sent on the line after its watch text printed -- you were told
    # what to look at after it had happened. launchpad 1-17 are all like that.
    # ⚠️ COUNTED AGAINST THE STEP TABLE, NOT A LITERAL. A hardcoded 17 would go
    # red the day somebody adds a step, which is not a defect; restoring the
    # guard IS one, and that is what this catches.
    # ⚠️ ANCHORED AT THE START OF A LINE, NOT SEARCHED LOOSELY -- and it had to
    # be. A bare out.count("press enter") read 18 for 17 steps, because midi
    # step 14's own `do` text says "then press enter straight away" and
    # describe() prints it. Same shape as the BEATS-inside-M-BEATS anchor in
    # predicates.py: a loose match answered by prose instead of by a prompt.
    prompts = len(re.findall(r"(?m)^  Press ENTER", out))
    A.check("clean: every step gets a read prompt before GO -- not just hands "
            "steps", prompts == n, "%d prompts for %d steps" % (prompts, n))

    # ⛔ [r]epeat MUST ASK AGAIN AND ADVANCE NOTHING. It fires the current step a
    # second time so a person can actually read an OLED that ages a row out in
    # ~1.3 s. The first implementation looped the whole STEP rather than the
    # verdict prompt, so it re-described the step AND sent a second GO -- the
    # patch moved on while the runner still thought it was here, and the only
    # thing that noticed was the desync guard. Against a replay there is nothing
    # to fire again, and the run must carry on regardless rather than desync.
    # ⚠️ THE STEP COUNT IS THE ASSERTION. If a repeat consumed a GO, the marker
    # for step 2 would be read as step 1's fire and the run would abort.
    # ⚠️ INJECTED AT THE FIRST PROMPT THAT ACTUALLY ASKS A PERSON. Dropping "r"
    # at a fixed index put it on a READ prompt instead -- midi step 1 is judged
    # by a predicate and never asks for a verdict, so the key was swallowed as
    # an enter and the fixture tested nothing while looking green.
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

    # ⛔ A PREDICATE IS EVIDENCE AND A PERSON IS THE VERDICT. The predicate reads
    # a BUS; the PASS IF beside it describes a SCREEN. `warn m_nano` can be on
    # err while the OLED shows nothing at all -- a display bug, and exactly what
    # a bench exists to catch -- so a green predicate must not close the step.
    # ⚠️ IT ALSO SWALLOWED A KEYSTROKE: with no verdict prompt on a predicate
    # step, the key a person typed anyway was eaten by the NEXT step's read
    # prompt and fired that step without them.
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

    # ⛔ --auto-only IS THE UNATTENDED RUN and there the predicate IS the verdict,
    # because nobody is there to give one. Without this, "the person decides"
    # would have quietly broken the one mode that has no person.
    rc, out = run(write("clean.txt", clean), [], auto_only=True)
    A.check("--auto-only: a predicate still answers with nobody in the room",
            ("%d passed" % len(checks)) in out, _tail(out))
    A.check("--auto-only: a step with no predicate is SKIPPED and never passed",
            "no predicate, and --auto-only" in out, _tail(out))

    # -- 2. truncated at step 7 --------------------------------------------
    # ⛔ MUST NOT PASS. Seven good verdicts and a console that stops is a run
    # that did not happen, and reporting the seven as a result is the whole
    # failure this fixture exists for.
    rc, out = run(write("truncated.txt", transcript(bench, upto=7)), _keys(bench))
    A.check("truncated: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("truncated: says STALLED rather than reporting a pass",
            "STALLED" in out and "RESULT: PASS" not in out, _tail(out))
    # ⛔ A STALL THAT SAYS ONLY "STALLED" IS A REPORT NOBODY CAN ACT ON. The only
    # bench verdict this project has ever recorded is a launchpad step-1 stall
    # whose note read "GO sent, no fired line" -- true, and naming nothing that
    # would let anyone work out why. Three causes, told apart by three facts.
    A.check("truncated: the stall says whether GO was sent",
            "GO sent" in out, _tail(out, 12))
    A.check("truncated: ...and how far behind the reader was",
            "waiting unread" in out, _tail(out, 12))
    A.check("truncated: ...and shows the last lines it did see",
            "the last" in out and "line(s) seen:" in out, _tail(out, 12))

    # -- 2b. GO sent and nothing fires -------------------------------------
    # ⛔ A DIFFERENT STALL FROM THE ONE ABOVE, and it took a mutation to notice.
    # Truncating after a fired line stalls waiting for the NEXT description;
    # truncating before one stalls waiting for the step to fire. Two handlers,
    # and with only the first fixture the second could be -- and was -- changed
    # to report success with this gate staying green.
    rc, out = run(write("nofire.txt",
                        transcript(bench, upto=7, stop_before_fired=True)),
                  _keys(bench))
    A.check("no fired line: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("no fired line: says STALLED and does not pass the step",
            "STALLED" in out and "RESULT: PASS" not in out, _tail(out))
    A.check("no fired line: the 6 steps that did fire are kept",
            "6 passed" in out, _tail(out))

    # -- 3. step numbers out of order --------------------------------------
    # ⛔ MUST ABORT, NOT SHIFT. A runner that resyncs silently records every
    # later verdict against the wrong question and still says PASS.
    #
    # ⚠️ THE MARKER ALONE IS RENUMBERED HERE. The fired lines stay correct, so
    # the ONLY guard that can catch this is the step-number check in
    # check_marker -- which is the point. The previous version of this fixture
    # renumbered both and was caught downstream, leaving check_marker untested.
    rc, out = run(write("desync-marker.txt",
                        transcript(bench, marker_n=lambda i: i + 1 if i > 1 else i)),
                  _keys(bench))
    A.check("desync by step number: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by step number: aborts and says so", "DESYNC" in out, _tail(out))
    A.check("desync by step number: does NOT report a full tally",
            ("%d passed" % n) not in out, _tail(out))

    # -- 3b. the right number, the wrong question --------------------------
    # ⛔ THE NUMBER IS NOT ENOUGH. A bench regenerated from a REORDERED table
    # still counts 1, 2, 3 while every title has moved, so a runner checking
    # only the count records a full set of verdicts against the wrong questions
    # and reports PASS. Nothing but the title can catch that.
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
    # ⛔ THE OTHER HALF OF THE MARKER CHECK, and also found by mutation. Every
    # fixture above corrupts the DESCRIPTION, so all of them are caught before
    # the fired line is ever compared -- deleting that comparison left this gate
    # green. This one describes step N correctly and then fires step N+1, which
    # is the shape of a bench whose run branch and describe branch disagree.
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
    # ⛔ AN EMPTY TAIL IS THE MOST DIAGNOSTIC CASE THERE IS, and it is a
    # different claim from "the bench never loaded" -- that one is inferred from
    # a timeout, this one is the direct evidence for it. Nothing was read on the
    # stream at any point, so this is not a stall in a running bench.
    A.check("empty: the report says nothing was read at all, rather than "
            "showing a tail of lines that do not exist",
            "NOTHING has been read" in out, _tail(out, 12))

    # -- 5. interrupted part-way -------------------------------------------
    # ⚠️ THESE ASSERT PROPERTIES, NOT ARITHMETIC. An earlier version hardcoded
    # "4 passed" and "--from 5", which was only true while every step needed a
    # keystroke -- the moment midi 1, 4, 6 and 7 gained predicates and stopped
    # consuming keys, four fixtures went red over nothing at all. A loop fixture
    # must not break when a step becomes machine-checkable.
    rc, out = run(write("interrupt.txt", clean), _keys(bench, stop_after=4) + ["q"])
    A.check("interrupted: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("interrupted: keeps the verdicts it did get rather than discarding",
            _tally(out)["pass"] > 0, _tail(out))
    A.check("interrupted: does not silently finish the bench",
            _tally(out)["notrun"] > 0, _tail(out))
    A.check("interrupted: prints a resume command for the step it stopped on",
            _resumes_at_last_step(out), _tail(out))

    # -- 6. every verdict skipped ------------------------------------------
    # ⛔ A SKIP IS NEVER A PASS. It is the absence of a verdict, and a suite
    # that counts absence as success reports green over work nobody checked.
    rc, out = run(write("allskip.txt", clean), _keys(bench, "s", "no rig here"))
    A.check("all skipped: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("all skipped: RESULT is FAIL, never PASS",
            "RESULT: FAIL" in out and "RESULT: PASS" not in out, _tail(out))

    # -- 7. the runner runs out of scripted answers -------------------------
    # ⚠️ The fixture provider must EXHAUST rather than repeat its last key: a
    # provider that repeated would let a transcript longer than its key list
    # pass by accident, which is a fixture grading itself.
    rc, out = run(write("shortkeys.txt", clean), _keys(bench, stop_after=2))
    A.check("exhausted keys: exits non-zero rather than inventing verdicts",
            rc != 0, "rc=%d" % rc)
    A.check("exhausted keys: keeps the real verdicts and finishes nothing else",
            _tally(out)["pass"] > 0 and _tally(out)["notrun"] > 0, _tail(out))

    # -- 7b. a real SIGINT, at a real prompt --------------------------------
    # ⛔ Ctrl-C IS NOT quit AND IT IS NOT fail. It arrives while a person is
    # looking at hardware and deciding, so the step in flight has no verdict --
    # recording a failure would put a red mark against working code, and a skip
    # would claim somebody decided to pass over it.
    #
    # ⚠️ IT IS DRIVEN BY PID, NOT BY pkill. Trying this from the shell first,
    # `pkill -INT -f "runner/run.py"` matched the harness script running it --
    # the pattern appears in the script's own text -- which tore down the pipe
    # and produced an EOF the runner correctly read as quit. The measurement was
    # of the harness, not the runner. Popen hands back the exact pid.
    rc, out = _sigint(write("sigint.txt", clean))
    A.check("SIGINT: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("SIGINT: says INTERRUPTED rather than quit or fail",
            "INTERRUPTED" in out, _tail(out))
    A.check("SIGINT: prints a resume command for the step in flight",
            _resumes_at_last_step(out), _tail(out))
    A.check("SIGINT: records no failure for the step nobody judged",
            _tally(out)["fail"] == 0 and _tally(out)["notrun"] > 0, _tail(out))

    # -- 7c. paper mode: an absent oracle is a SKIP, never a FAIL -----------
    # ⛔ THIS IS THE ONLY FIXTURE THAT DRIVES run_bench, and until it existed
    # that loop was ungated -- which is how it came to evaluate every predicate
    # against an EMPTY WINDOW and report AUTO FAIL. There is no Pd in paper mode,
    # so _bus_lines finds nothing, `has` finds nothing, and four steps of a
    # working `midi` bench failed. Every recorded midi run had used
    # `--target device`, so nobody had met it.
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
    # ⛔ THE NEGATIVE HALF, AND IT IS THE ONE THAT REGRESSES. A skip and a fail
    # both keep RESULT off PASS, so counting skips alone would stay green if the
    # empty-window evaluation came back beside it.
    A.check("paper: nothing reports AUTO FAIL out of an empty window",
            "AUTO FAIL" not in out, _tail(out))
    A.check("paper: the reason names the kind that could not be judged",
            "`bus`" in out or "`bus-count`" in out, _tail(out))
    # ⛔ AND A SKIP IS STILL NOT A PASS. Turning four false failures into four
    # skips must not turn the run green -- those steps remain unjudged, and a
    # suite that reported PASS over them would be the exact disease this fix was
    # meant to cure, one level up.
    A.check("paper: skips keep RESULT off PASS", rc != 0 and "RESULT: PASS"
            not in out, "rc=%d / %s" % (rc, _tail(out)))

    # -- 8. and the roll-up was never touched -------------------------------
    # ⛔ latest.json IS COMMITTED AND DESCRIBES HARDWARE. A fixture is a
    # fiction; letting one write there would put invented verdicts in the one
    # file whose entire value is that it contains none.
    # ⚠️ THE PAPER RUN ABOVE IS THE REASON THIS NOW MATTERS TWICE. A replay
    # refuses to roll up at all, but paper mode is a normal run and DOES -- it is
    # redirected with CUTIT_RESULTS instead, and this is what proves the redirect
    # held rather than merely being passed.
    import records
    before = len(records.load_latest().get("records", {}))
    run(write("clean2.txt", clean), _keys(bench))
    run_paper(_paper_keys(bench))
    after = len(records.load_latest().get("records", {}))
    A.check("neither a replay nor a redirected paper run writes to the "
            "committed latest.json",
            before == after, "%d records before, %d after" % (before, after))

    print()
    rc = A.report()
    if not rc:
        import shutil
        shutil.rmtree(WORK, ignore_errors=True)
    else:
        print("fixtures kept at %s" % WORK)
    return rc


def _predicates():
    """Every predicate kind, against a synthetic window. Each one BOTH ways.

    ⛔ A PREDICATE THAT HAS NEVER BEEN SEEN TO FAIL IS NOT A CHECK. Proving these
    on hardware costs a rig session each and reintroducing a real bug to do it;
    proving them here costs a millisecond, and it is the same question -- given
    this stream, does the predicate say yes or no. The hardware run then asks
    the different and equally necessary question of whether the stream is real.
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

    # ⛔ THE LAST COMPLETE FRAME, NOT THE WHOLE WINDOW. A window spans a repaint,
    # so the frames before a step still show what was there.
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["12"], },
                            frame("chop-size", "43 %") + good)
    A.check("oled: judged on the LAST frame, not on every frame in the window",
            ok, got)
    ok, _, got = P.evaluate({"kind": "oled", "has_row": ["43 %"]},
                            frame("chop-size", "43 %") + good)
    A.check("oled: and an earlier frame's content does NOT count",
            not ok, got)

    # ⛔ THE GEOMETRY IS NOT THE TEXT. `8` and `16` are the font size and the y
    # coordinate in every line above -- a predicate satisfied by those would
    # pass against a screen showing nothing of the sort.
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
    # ⚠️ `BEATS` is a substring of all three names above. A loose match would
    # read the tempo bench's three counters as the Launchpad bench's one.
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
    # ⛔ THE ASYMMETRY IS DELIBERATE AND IS THE SUBTLE PART. A purely negative
    # spec is SATISFIED by silence -- "the meters never reach the phone" is
    # answered correctly by an address that carried nothing -- and that is only
    # safe because the lint refuses a bare has_not. Its witness is a sibling.
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

    ⚠️ NO --keys HERE, DELIBERATELY. A scripted key list that runs out raises
    EOF, which the prompt reads as quit -- a different path with a similar
    outcome, and using it would test the wrong branch. An open pipe nobody
    writes to is what actually blocks a person's prompt.
    """
    import selectors
    import signal
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path, "--target", "device"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

    # Wait for whichever prompt comes first rather than sleeping a guessed
    # interval -- a fixed sleep is a race that passes on a fast machine and
    # fails on a loaded one.
    #
    # ⛔ AND THE READ MUST BE ABLE TO TIME OUT. This was a blocking read(1) in a
    # `while ... time.time() < deadline` loop, which cannot work: with the child
    # blocked on a prompt there is no byte to return, read() waits forever, and
    # the deadline is never evaluated. The whole suite hung -- and A GATE THAT
    # HANGS IS WORSE THAN ONE THAT FAILS, because a failure is at least a
    # verdict. selectors gives the wait a real deadline.
    #
    # ⚠️ IT WATCHES FOR BOTH PROMPTS. Waiting only for "verdict?" broke the day
    # the hands-on steps gained a `do`, because the runner then asks "press
    # enter when you are ready" first and never reaches the other one.
    # ⚠️ os.read ON THE RAW fd, NEVER p.stdout.read(). select() answers about the
    # FILE DESCRIPTOR while a buffered reader keeps its own buffer in front of
    # it -- so bytes that have already arrived sit unseen in Python while select
    # reports nothing new, and the loop waits out its whole deadline for a
    # prompt that was delivered immediately. That cost this fixture 20 s a run.
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
    """The summary line's counts, so a fixture can assert a property of the run
    rather than an arithmetic that shifts whenever a step becomes automatic."""
    import re
    m = re.search(r"Steps\s+(\d+) passed, (\d+) failed, (\d+) skipped, "
                  r"(\d+) not run", out)
    if not m:
        return {"pass": -1, "fail": -1, "skip": -1, "notrun": -1}
    return dict(zip(("pass", "fail", "skip", "notrun"),
                    (int(g) for g in m.groups())))


def _resumes_at_last_step(out):
    """The resume command must name the step the runner said it stopped on.

    ⚠️ AGAINST THE RUNNER'S OWN STATEMENT, not against the last header it
    printed. Those are usually the same and are not always: a step is described,
    then interrupted at its prompt, and whether its header reached the pipe
    before the signal did is a buffering question rather than a correctness one.
    What must be true is that "stopped at step N" and "--from N" agree -- a
    resume command pointing anywhere else is the actual defect.
    """
    import re
    m = re.findall(r"(?:INTERRUPTED at step|stopped at step) (\d+)", out)
    return bool(m) and ("--from %s" % m[-1]) in out


def _keys(bench, verdict="p", note=None, stop_after=None):
    """The keystrokes a person would type to give every step `verdict`.

    ⛔ IT IS DERIVED FROM THE BENCH, NOT A FLAT LIST OF n. How many inputs a step
    consumes depends on the step: one with a predicate asks nothing more after
    the read prompt, one judged by a person asks again for the verdict. A flat
    ["p"] * n was right only while every step was judged by hand, and the moment
    the hands-on steps gained instructions it ran short and four fixtures
    reported "not run" over nothing at all.

    ⛔ EVERY STEP CONSUMES A READ PROMPT NOW, AND THIS LINE IS THE FIXTURE THAT
    ENCODED THE OLD BEHAVIOUR. It used to be `if step.hands`, matching a runner
    that prompted only for steps carrying a `do` -- and that was the defect:
    every other step fired GO on the line after its watch text printed, so the
    thing you were told to look at had already happened. The guard is gone from
    run.py and it is gone from here, deliberately, because the runner now asks
    every step to be READ before it is run. ⚠️ Changed to follow a fix, never to
    turn a red run green: the prompt-count check in main() is what would go red
    if that guard came back, and it is asserted against the step table rather
    than against this list.
    """
    out = []
    for step in bench.steps:
        if stop_after is not None and step.n > stop_after:
            break
        # ⚠️ THE TWO QUESTIONS ARE INDEPENDENT. Every step asks "press enter"
        # before GO -- a step with a `do` because the finger has to be on the pad
        # or the predicate reads an empty console, a step without one because it
        # still has to be read -- and only then does a predicate answer for it or
        # a person. midi 4, 6 and 7 are both at once, and treating "has a
        # predicate" as "asks nothing" left exactly those three short.
        out.append("")                   # the read prompt, every step
        # ⛔ EVERY STEP ASKS A PERSON NOW, PREDICATE OR NOT. This used to skip
        # the verdict key for a step carrying a `check`, matching a runner where
        # the predicate recorded its own verdict and never asked -- and that was
        # the defect: the predicate reads a BUS while the PASS IF beside it
        # describes a SCREEN, and the keystroke a person typed anyway was
        # swallowed by the next step's read prompt. The predicate is evidence
        # now and the person answers, so every step consumes both keys.
        out.append(verdict)
        if note is not None:
            out.append(note)
    return out


def _paper_keys(bench, verdict="p"):
    """The keystrokes a paper-mode run of `bench` consumes.

    ⛔ A DIFFERENT SHAPE FROM _keys, BECAUSE run_bench IS A DIFFERENT LOOP. There
    is no GO and nothing to fire, so there is no read prompt: a step is either
    skipped outright (its target, or a predicate needing a console), judged from
    disk by a `file` predicate, or asked of a person. Only the last consumes a
    key, and deriving that from the table is what stops this list going stale the
    day a step gains a predicate.
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
