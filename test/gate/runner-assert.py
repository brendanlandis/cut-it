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
        if stop_before_fired and upto is not None and step.n >= upto:
            return out                  # GO will be sent and nothing will fire
        fi = fired_n(step.n) if fired_n else step.n
        out.append("print: " + (S.SAY_FIRED % (fi, fi + 1)
                                if step.n < n else S.SAY_FIRED_LAST % fi))
        if upto is not None and step.n >= upto:
            return out
    out.append("print: " + S.SAY_COMPLETE)
    return out


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
         "--bench", BENCH, "--replay", transcript_path, "--keys", kp],
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

    clean = transcript(bench)

    # -- 1. a clean transcript ---------------------------------------------
    rc, out = run(write("clean.txt", clean), ["p"] * n)
    A.check("clean: exits 0", rc == 0, "rc=%d" % rc)
    A.check("clean: every step passed",
            ("%d passed" % n) in out, _tail(out))

    # -- 2. truncated at step 7 --------------------------------------------
    # ⛔ MUST NOT PASS. Seven good verdicts and a console that stops is a run
    # that did not happen, and reporting the seven as a result is the whole
    # failure this fixture exists for.
    rc, out = run(write("truncated.txt", transcript(bench, upto=7)), ["p"] * n)
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
                  ["p"] * n)
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
                  ["p"] * n)
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
                  ["p"] * n)
    A.check("desync by title: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by title: aborts naming the title mismatch",
            "DESYNC" in out and "title" in out, _tail(out))

    # -- 3c. a bench generated from a different table -----------------------
    rc, out = run(write("desync-of.txt", transcript(bench, of=99)), ["p"] * n)
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
                  ["p"] * n)
    A.check("desync by fired line: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("desync by fired line: aborts saying which step actually fired",
            "DESYNC" in out and "fired" in out, _tail(out))
    A.check("desync by fired line: does NOT report a full tally",
            ("%d passed" % n) not in out, _tail(out))

    # -- 4. an empty file ---------------------------------------------------
    rc, out = run(write("empty.txt", []), ["p"] * n)
    A.check("empty: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("empty: names the cause -- the bench never loaded",
            "NEVER LOADED" in out.upper(), _tail(out))

    # -- 5. interrupted part-way -------------------------------------------
    rc, out = run(write("interrupt.txt", clean), ["p", "p", "p", "p", "q"])
    A.check("interrupted: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("interrupted: keeps the 4 verdicts it did get",
            "4 passed" in out, _tail(out))
    A.check("interrupted: prints a resume command with the right step",
            "--from 5" in out, _tail(out))

    # -- 6. every verdict skipped ------------------------------------------
    # ⛔ A SKIP IS NEVER A PASS. It is the absence of a verdict, and a suite
    # that counts absence as success reports green over work nobody checked.
    rc, out = run(write("allskip.txt", clean), _interleave(["s", "no rig here"], n))
    A.check("all skipped: exits non-zero", rc != 0, "rc=%d" % rc)
    A.check("all skipped: RESULT is FAIL, never PASS",
            "RESULT: FAIL" in out and "RESULT: PASS" not in out, _tail(out))

    # -- 7. the runner runs out of scripted answers -------------------------
    # ⚠️ The fixture provider must EXHAUST rather than repeat its last key: a
    # provider that repeated would let a transcript longer than its key list
    # pass by accident, which is a fixture grading itself.
    rc, out = run(write("shortkeys.txt", clean), ["p", "p"])
    A.check("exhausted keys: exits non-zero rather than inventing verdicts",
            rc != 0, "rc=%d" % rc)
    A.check("exhausted keys: keeps the 2 real verdicts", "2 passed" in out,
            _tail(out))

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
            "--from 1" in out, _tail(out))
    A.check("SIGINT: records the step as interrupted, not as a verdict",
            "0 passed" in out and "0 failed" in out, _tail(out))

    # -- 8. and the roll-up was never touched -------------------------------
    # ⛔ latest.json IS COMMITTED AND DESCRIBES HARDWARE. A fixture is a
    # fiction; letting one write there would put invented verdicts in the one
    # file whose entire value is that it contains none.
    import records
    before = len(records.load_latest().get("records", {}))
    run(write("clean2.txt", clean), ["p"] * n)
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


def _sigint(transcript_path):
    """Block the runner at a verdict prompt, then interrupt it. -> (rc, output).

    ⚠️ NO --keys HERE, DELIBERATELY. A scripted key list that runs out raises
    EOF, which the prompt reads as quit -- a different path with a similar
    outcome, and using it would test the wrong branch. An open pipe nobody
    writes to is what actually blocks a person's prompt.
    """
    import signal
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "test", "runner", "run.py"),
         "--bench", BENCH, "--replay", transcript_path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    # Wait for the prompt rather than sleeping a guessed interval: a fixed sleep
    # is a race that passes on a fast machine and fails on a loaded one.
    buf = b""
    deadline = time.time() + 20
    while b"verdict?" not in buf and time.time() < deadline:
        ch = p.stdout.read(1)
        if not ch:
            break
        buf += ch
    p.send_signal(signal.SIGINT)
    try:
        rest, _ = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        rest, _ = p.communicate()
    return p.returncode, (buf + rest).decode("utf-8", "replace")


def _interleave(pair, n):
    out = []
    for _ in range(n):
        out.extend(pair)
    return out


def _tail(out, n=6):
    return " / ".join(l.strip() for l in out.strip().splitlines()[-n:] if l.strip())


if __name__ == "__main__":
    sys.exit(main())
