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
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "test", "runner"))
sys.path.insert(0, HERE)

import lib_assert as A                                          # noqa: E402
import steps as S                                               # noqa: E402

WORK = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                    "cutit-runner-assert-%d" % os.getpid())
BENCH = "midi"          # 14 steps, no actions -- the cheapest table to recite


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


def run(transcript_path, keys):
    """Drive the real runner over a fixture. -> (exit code, output)."""
    kp = write(os.path.basename(transcript_path) + ".keys", keys)
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path, "--keys", kp,
         # ⚠️ A TRANSCRIPT IS A RECORDING OF A DEVICE RUN, so it is replayed as
         # one. Without this, every step carrying `targets: ('device',)` is
         # skipped -- correctly -- and each one shifts the counts these fixtures
         # assert, so adding a device-only predicate would break them all.
         "--target", "device"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
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

    _predicates()

    clean = transcript(bench)

    # -- 1. a clean transcript ---------------------------------------------
    rc, out = run(write("clean.txt", clean), _keys(bench))
    A.check("clean: exits 0", rc == 0, "rc=%d" % rc)
    A.check("clean: every step passed",
            ("%d passed" % n) in out, _tail(out))

    # -- 2. truncated at step 7 --------------------------------------------
    # ⛔ MUST NOT PASS. Seven good verdicts and a console that stops is a run
    # that did not happen, and reporting the seven as a result is the whole
    # failure this fixture exists for.
    rc, out = run(write("truncated.txt", transcript(bench, upto=7)), _keys(bench))
    A.check("truncated: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("truncated: says STALLED rather than reporting a pass",
            "STALLED" in out and "RESULT: PASS" not in out, _tail(out))

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

    # -- 8. and the roll-up was never touched -------------------------------
    # ⛔ latest.json IS COMMITTED AND DESCRIBES HARDWARE. A fixture is a
    # fiction; letting one write there would put invented verdicts in the one
    # file whose entire value is that it contains none.
    import records
    before = len(records.load_latest().get("records", {}))
    run(write("clean2.txt", clean), _keys(bench))
    after = len(records.load_latest().get("records", {}))
    A.check("a replay never writes to the committed latest.json",
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
    while not (b"verdict?" in buf or b"press enter" in buf):
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
    consumes depends on the step: one with a predicate asks nothing, one with a
    `do` asks TWICE -- once for "press enter when you are ready" and once for the
    verdict. A flat ["p"] * n was right only while every step was judged by hand,
    and the moment the hands-on steps gained instructions it ran short and four
    fixtures reported "not run" over nothing at all.
    """
    out = []
    for step in bench.steps:
        if stop_after is not None and step.n > stop_after:
            break
        # ⚠️ THE TWO QUESTIONS ARE INDEPENDENT. A step with a `do` asks "press
        # enter when you are ready" WHATEVER judges it -- the finger has to be on
        # the pad before GO goes out, or the predicate reads an empty console --
        # and only then does a predicate answer for it or a person. midi 4, 6
        # and 7 are both at once, and treating "has a predicate" as "asks
        # nothing" left exactly those three short.
        if step.hands:
            out.append("")               # "press enter when you are ready"
        if step.meta.get("check"):
            continue                     # a predicate gives the verdict
        out.append(verdict)
        if note is not None:
            out.append(note)
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
