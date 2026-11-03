#!/usr/bin/env python3
"""The error bus's analyzer -- ref/module/error.md. Reads a capture on stdin.

⛔ WHAT THIS IS FOR, AND IT WAS BENCH PROSE UNTIL NOW: perform mode suppresses
`warn` and NEVER suppresses `fail`. u_err's spigot sits on the warn branch only
and the fail branch is unspigoted -- a one-cord distinction that nothing on the
instrument would report if it were wrong. The display would simply go quiet, and
plan-v04.md notes the mode split is weighted toward perform, so the first place
anyone would find out is a venue.

It asserts on what u_err lets through, not on the drawing, which is
display-assert's and oled-assert's.

Two halves, the first with no Pd: a static lint over every error message box,
since C-12's 21-character limit cannot be enforced downstream.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                  # noqa: E402

# The number of windows err-assert-drive-gen.py's SEQ opens.
MARKS = 10

# C-12: <level> <source> <text>, the text one symbol of at most 21 characters,
# because gPrintln does not wrap.
TEXT_LIMIT = 21
# info is logged and never drawn (ref/module/error.md).
LEVELS = ("info", "warn", "fail")
ERR_MSG = re.compile(r"^#X msg \d+ \d+ (%s) (\S+) (\S+);$" % "|".join(LEVELS))


def run_lint():
    """The half that needs no Pd: every error message box in the patch.

    The limit is a call-site rule, since nothing downstream can shorten the
    symbol, and reading the boxes also covers callers the driver never fires.
    """
    print("--- C-12, read straight off the message boxes (no Pd) ---")
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    seen, over, malformed = 0, [], []
    for name in sorted(os.listdir(os.path.join(root, "Cut It"))):
        if not name.endswith(".pd"):
            continue
        for line in lib_pd.read(os.path.join(root, "Cut It", name)):
            if not re.match(r"^#X msg \d+ \d+ (%s) " % "|".join(LEVELS), line):
                continue
            seen += 1
            m = ERR_MSG.match(line)
            if not m:
                malformed.append((name, line[:70]))
                continue
            if len(m.group(3)) > TEXT_LIMIT:
                over.append((name, m.group(3), len(m.group(3))))

    # Asserted, not printed: a lint that stops finding files passes over nothing.
    A.check("the lint found error message boxes to check at all", seen > 0,
            "no `#X msg ... warn|fail ...` anywhere under Cut It/ -- the lint is "
            "asserting nothing")
    A.check("every error message is <level> <source> <text>, three atoms",
            not malformed, "%d malformed: %s" % (len(malformed), malformed[:3]))
    A.check("every error text is one symbol of %d characters or fewer" % TEXT_LIMIT,
            not over, "%d over the limit: %s" % (len(over), over[:3]))
    A.note("%d error message box(es) linted across Cut It/" % seen)
    lint_stamp(root)


def lint_stamp(root):
    """The log's timestamp must reach [text] as a symbol, never as a float:
    a float is written with %g and loses precision from 16 min 40 s
    (ref/module/error.md).

    Static because the fault needs 999999 ms of uptime to show, and a shorter
    run reads clean whatever the wiring. The cord can be read instead: the
    stamp reaching list prepend's right inlet must come from a makefilename,
    not the timer. The console half never sees the stamp, which is added on
    the way to disk.
    """
    print("\n--- the log stamp survives past 16m40s (static, no Pd) ---")
    path = os.path.join(root, "Cut It", "u_err.pd")
    with open(path) as fh:
        body = fh.read()

    # The logfile subpatch, whose box indices the connects below count within.
    sub = body.split("#N canvas", 2)
    A.check("u_err still has a logfile subpatch to lint", len(sub) >= 3,
            "expected a nested #N canvas in %s" % path)
    if len(sub) < 3:
        return
    block = sub[2]
    boxes, connects = [], []
    for line in block.splitlines():
        if line.startswith("#X restore"):
            break
        m = re.match(r"^#X (obj|msg|text|floatatom|symbolatom) \S+ \S+ ?(.*);$",
                     line)
        if m:
            boxes.append(m.group(2))
        c = re.match(r"^#X connect (\d+) (\d+) (\d+) (\d+);$", line)
        if c:
            connects.append(tuple(int(g) for g in c.groups()))

    def index_of(prefix):
        return [i for i, b in enumerate(boxes) if b.startswith(prefix)]

    prepend = index_of("list prepend")
    timer = index_of("timer")
    maker = [i for i, b in enumerate(boxes)
             if b.startswith("makefilename")
             # makefilename %g formats as [text] would: the format is the
             # assertion, not the box.
             and "%g" not in b]
    A.check("the stamp goes through a makefilename with an integer format",
            bool(maker), "makefilename boxes in the logfile subpatch: %s"
            % [boxes[i] for i, b in enumerate(boxes)
               if b.startswith("makefilename")])
    A.check("the logfile subpatch still has a timer and a list prepend to wire",
            bool(prepend) and bool(timer),
            "timer=%s prepend=%s" % (timer, prepend))
    if not (maker and prepend and timer):
        return

    # The stamp is list prepend's cold inlet 1; inlet 0 is the message itself.
    feeds = [c for c in connects if c[2] in prepend and c[3] == 1]
    A.check("something feeds the stamp into list prepend's cold inlet",
            bool(feeds), "no connect into inlet 1 of %s" % prepend)
    from_timer = [c for c in feeds if c[0] in timer]
    A.check("⛔ the RAW timer never reaches the stamp inlet -- %g would cap it "
            "at six significant figures", not from_timer,
            "timer wired straight to the stamp: %s" % (from_timer,))
    from_maker = [c for c in feeds if c[0] in maker]
    A.check("the stamp inlet is fed by the makefilename, so text stores a symbol",
            bool(from_maker),
            "stamp fed by box(es) %s, none of them the makefilename %s"
            % ([boxes[c[0]] for c in feeds], [boxes[i] for i in maker]))


def run_asserts(cap):
    order, by = A.windows(cap, "ERR", MARKS)
    W = lambda k: by.get(k, [])

    # disp carries more than alerts (boot modals, the footer, the meters), so the
    # negative checks below look at the alert selector only.
    def alerts(k):
        return [v for kind, v in W(k) if kind == "DISP" and v[:1] == ["alert"]]

    # ---- the default, and there is no way back to it ----------------------
    print("\n--- before any mode has arrived ---")
    A.check("⛔ the default is VERBOSE -- a warn shows before any mode is set",
            alerts("DEFAULT") == [["alert", "warn", "u_gate", "before-mode"]],
            "got %s. The reverse default fails in the direction of silence, "
            "which is the failure this file exists to prevent" % alerts("DEFAULT"))

    # ---- compose shows everything -----------------------------------------
    print("\n--- compose ---")
    A.check("compose passes a warn",
            alerts("COMPOSE-WARN") == [["alert", "warn", "u_gate", "compose-warn"]],
            "got %s" % alerts("COMPOSE-WARN"))
    A.check("compose passes a fail",
            alerts("COMPOSE-FAIL") == [["alert", "fail", "u_gate", "compose-fail"]],
            "got %s" % alerts("COMPOSE-FAIL"))

    # ---- perform drops warn and must not drop fail ------------------------
    print("\n--- perform ---")
    A.check("perform DROPS a warn", not alerts("PERFORM-WARN"),
            "a warn reached the screen in perform mode: %s" % alerts("PERFORM-WARN"))
    A.check("⛔ perform PASSES a fail -- the whole point of the split",
            alerts("PERFORM-FAIL") == [["alert", "fail", "u_gate", "perform-fail"]],
            "got %s. A fail suppressed in perform means the instrument goes "
            "silent about its own failures at exactly the moment it is least "
            "able to tell you any other way" % alerts("PERFORM-FAIL"))

    # ---- and the filter is reversible -------------------------------------
    # A filter that shut and stayed shut would pass every check above.
    A.check("returning to compose lets warnings through again",
            alerts("BACK-TO-COMPOSE") == [["alert", "warn", "u_gate", "back-warn"]],
            "got %s -- the filter shut and did not reopen" % alerts("BACK-TO-COMPOSE"))

    # ---- the two-atom mode, which is what u_map actually sends -------------
    print("\n--- the two-atom mode form ---")
    A.check("⛔ `perform mode-6` filters exactly as bare `perform` does",
            not alerts("TWO-ATOM-MODE"),
            "a warn got through under the two-atom mode form: %s. route matches "
            "the selector, so the trailing atom must be irrelevant"
            % alerts("TWO-ATOM-MODE"))

    # ---- info: logged and never drawn -------------------------------------
    print("\n--- info is logged and never drawn ---")
    drew = [a for a in alerts("INFO") if "info-quiet" in " ".join(map(str, a))]
    A.check("⛔ an info NEVER reaches the screen, even in compose",
            not drew,
            "info drew %s. Its route outlet is meant to be connected to nothing "
            "-- if this is drawing, u_present's eight recovery attempts land on "
            "the OLED during every unplug" % (drew,))

    # Without this witness the check above is vacuous: a dead display, a shut
    # spigot or a filtering mode also draws nothing.
    witness = [a for a in alerts("INFO") if "info-witness" in " ".join(map(str, a))]
    A.check("...and the screen was demonstrably willing to draw at that moment",
            witness,
            "the warn raised alongside it drew nothing either, so this window "
            "proves nothing about the LEVEL -- alerts seen: %s" % (alerts("INFO"),))

    A.check("⛔ ...but it IS logged, exactly like the other two",
            "err: info u_gate info-quiet" in cap,
            "no `info u_gate info-quiet` on u_err's own [print err]. The logfile "
            "tap hangs off the trigger ABOVE the route, so every level must reach "
            "it whatever the screen does -- and the log is this level's entire "
            "reason for existing")

    # ---- a level that is none of the three ---------------------------------
    print("\n--- a level that is none of the three ---")
    A.check("an unknown level draws nothing", not alerts("BAD-LEVEL"),
            "got %s" % alerts("BAD-LEVEL"))
    A.check("...and is PRINTED rather than swallowed",
            "err-BAD-LEVEL: chatty u_gate bad-level" in cap,
            "no err-BAD-LEVEL line in the capture. Swallowing a malformed error "
            "silently is the exact failure this file exists to prevent")

    # ---- the log is unfiltered; only the screen is filtered ---------------
    # u_err's [print err] hangs off the trigger before the route.
    print("\n--- the log is never filtered, even when the screen is ---")
    logged = [ln.strip()[len("err: "):] for ln in cap.splitlines()
              if ln.strip().startswith("err: ")]
    raised = ["warn u_gate before-mode", "warn u_gate compose-warn",
              "fail u_gate compose-fail", "warn u_gate perform-warn",
              "fail u_gate perform-fail", "warn u_gate back-warn",
              "warn u_gate two-atom", "warn u_gate info-witness",
              "info u_gate info-quiet", "chatty u_gate bad-level"]
    # Exact order and count of the driver's own errors only. The patch can
    # raise its own too, at a point that moves from run to run; those are
    # noted, not asserted.
    mine = [ln for ln in logged if " u_gate " in ln]
    A.check("every error raised reaches the log, in order and whatever the mode",
            mine == raised, "logged %s" % mine)
    others = [ln for ln in logged if " u_gate " not in ln]
    if others:
        A.note("%d error(s) from the patch itself during the run: %s"
               % (len(others), others))
    A.check("⛔ including the two the SCREEN was never shown",
            "warn u_gate perform-warn" in logged and "warn u_gate two-atom" in logged,
            "a suppressed warning was suppressed on the bus as well as on the "
            "screen, so it is gone from the log too")

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_lint()
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
