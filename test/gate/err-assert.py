#!/usr/bin/env python3
"""The error bus's analyser -- ref/module/error.md. Reads a capture on stdin.

⛔ WHAT THIS IS FOR, AND IT WAS BENCH PROSE UNTIL NOW: perform mode suppresses
`warn` and NEVER suppresses `fail`. u_err's spigot sits on the warn branch only
and the fail branch is unspigoted -- a one-cord distinction that nothing on the
instrument would report if it were wrong. The display would simply go quiet, and
plan-v04.md notes the mode split is weighted toward perform, so the first place
anyone would find out is a venue.

⚠️ IT ASSERTS ON THE FILTER, NOT ON THE DRAWING. Whether an alert outranks a
modal, how long it stays and what colour it is are display-assert's and
oled-assert's; this one is only about what u_err lets THROUGH.

TWO HALVES, and the first needs no Pd at all: a static lint over every error
message box in the patch, which is where C-12's 21-character limit actually lives
-- u_err cannot enforce it, because nothing downstream can shorten a symbol.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS err-assert-drive-gen.py's SEQ OPENS.
MARKS = 9

# C-12: <level> <source> <text>, text ONE symbol of at most 21 characters,
# because gPrintln does not wrap -- it draws until it runs off the screen.
TEXT_LIMIT = 21
ERR_MSG = re.compile(r"^#X msg \d+ \d+ (warn|fail) (\S+) (\S+);$")


def run_lint():
    """The half that needs no Pd: every error message box in the patch.

    ⛔ THE LIMIT CANNOT BE CHECKED AT RUNTIME BY u_err. The text arrives as one
    symbol and nothing downstream can shorten it, so the rule is a call-site rule
    -- which makes it exactly the kind of claim a static lint owns. Reading the
    message boxes is also the only way to cover the callers this driver does not
    happen to exercise.
    """
    print("--- C-12, read straight off the message boxes (no Pd) ---")
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    seen, over, malformed = 0, [], []
    for name in sorted(os.listdir(os.path.join(root, "Cut It"))):
        if not name.endswith(".pd"):
            continue
        with open(os.path.join(root, "Cut It", name)) as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not re.match(r"^#X msg \d+ \d+ (warn|fail) ", line):
                    continue
                seen += 1
                m = ERR_MSG.match(line)
                if not m:
                    malformed.append((name, line[:70]))
                    continue
                if len(m.group(3)) > TEXT_LIMIT:
                    over.append((name, m.group(3), len(m.group(3))))

    # ⛔ AND THE COUNT IS ASSERTED, not merely printed. A lint that stops finding
    # files reports a clean sweep over nothing -- the fourth way a gate passes
    # vacuously, and the one that cost docs-check seven of nine pages.
    A.check("the lint found error message boxes to check at all", seen > 0,
            "no `#X msg ... warn|fail ...` anywhere under Cut It/ -- the lint is "
            "asserting nothing")
    A.check("every error message is <level> <source> <text>, three atoms",
            not malformed, "%d malformed: %s" % (len(malformed), malformed[:3]))
    A.check("every error text is one symbol of %d characters or fewer" % TEXT_LIMIT,
            not over, "%d over the limit: %s" % (len(over), over[:3]))
    A.note("%d error message box(es) linted across Cut It/" % seen)


def run_asserts(cap):
    order, by = A.windows(cap, "ERR", MARKS)
    W = lambda k: by.get(k, [])

    # ⚠️ disp CARRIES MORE THAN ALERTS -- u_init's modal stages, u_tempo's footer
    # and the level meters all share it. Filtering to the alert selector is what
    # keeps the negative assertions below about u_err rather than about whatever
    # else happened to be quiet in that window.
    def alerts(k):
        return [v for kind, v in W(k) if kind == "DISP" and v[:1] == ["alert"]]

    # ---- the default, and there is no way back to it ----------------------
    # ⛔ THE ONLY WINDOW IN THE RUN THAT CAN TEST THIS. Nothing can put u_err back
    # into "no mode has ever arrived", and that is the state the instrument boots
    # in -- so a verbose default is what makes an undriven mode safe.
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

    # ---- ⛔ perform drops warn and MUST NOT drop fail ----------------------
    print("\n--- perform ---")
    A.check("perform DROPS a warn", not alerts("PERFORM-WARN"),
            "a warn reached the screen in perform mode: %s" % alerts("PERFORM-WARN"))
    A.check("⛔ perform PASSES a fail -- the whole point of the split",
            alerts("PERFORM-FAIL") == [["alert", "fail", "u_gate", "perform-fail"]],
            "got %s. A fail suppressed in perform means the instrument goes "
            "silent about its own failures at exactly the moment it is least "
            "able to tell you any other way" % alerts("PERFORM-FAIL"))

    # ---- and the filter is reversible -------------------------------------
    # ⚠️ NOT A FORMALITY. The spigot is set by a route on the mode bus with no
    # latch anywhere, so a filter that shut and stayed shut would pass every
    # check above and lose every warning for the rest of the session.
    A.check("returning to compose lets warnings through again",
            alerts("BACK-TO-COMPOSE") == [["alert", "warn", "u_gate", "back-warn"]],
            "got %s -- the filter shut and did not reopen" % alerts("BACK-TO-COMPOSE"))

    # ---- the two-atom mode, which is what u_map actually sends -------------
    # route matches on the SELECTOR, so `perform mode-6` must filter exactly as a
    # bare `perform` does. u_map has sent the two-atom form since Phase 6 and the
    # filter was never changed for it -- which was a claim until something drove
    # both forms in one run.
    print("\n--- the two-atom mode form ---")
    A.check("⛔ `perform mode-6` filters exactly as bare `perform` does",
            not alerts("TWO-ATOM-MODE"),
            "a warn got through under the two-atom mode form: %s. route matches "
            "the selector, so the trailing atom must be irrelevant"
            % alerts("TWO-ATOM-MODE"))

    # ---- a level that is neither ------------------------------------------
    print("\n--- a level that is neither warn nor fail ---")
    A.check("an unknown level draws nothing", not alerts("BAD-LEVEL"),
            "got %s" % alerts("BAD-LEVEL"))
    A.check("...and is PRINTED rather than swallowed",
            "err-BAD-LEVEL: chatty u_gate bad-level" in cap,
            "no err-BAD-LEVEL line in the capture. Swallowing a malformed error "
            "silently is the exact failure this file exists to prevent")

    # ---- ⛔ THE BUS IS UNFILTERED; ONLY THE SCREEN IS FILTERED -------------
    # u_err's own [print err] hangs off the trigger BEFORE the route, so it fires
    # on every error whatever the mode. That is what makes the by-hand SSH
    # console -- and the durable log behind it -- see everything even when the
    # OLED is deliberately showing nothing.
    print("\n--- the log is never filtered, even when the screen is ---")
    logged = [ln.strip()[len("err: "):] for ln in cap.splitlines()
              if ln.strip().startswith("err: ")]
    raised = ["warn u_gate before-mode", "warn u_gate compose-warn",
              "fail u_gate compose-fail", "warn u_gate perform-warn",
              "fail u_gate perform-fail", "warn u_gate back-warn",
              "warn u_gate two-atom", "chatty u_gate bad-level"]
    # ⛔ THE DRIVER'S OWN ERRORS ONLY, AND THE FILTER IS THE FIX FOR A REAL
    # FRAGILITY. This compared the whole log against `raised` by equality, which
    # quietly asserted a SECOND claim it was never meant to make: that the patch
    # itself raises nothing during the run. It does -- u_net's link watchdog says
    # `warn u_net net-link-down` on any machine with no phone answering, which is
    # correct behaviour and not this gate's business. The check passed only
    # because that watchdog happened to fire just outside the window, and it
    # moved inside as soon as an unrelated change shifted the load by a few
    # milliseconds. Worse, it moved to a DIFFERENT position on different runs, so
    # the failure looked like an ordering bug in u_err.
    #
    # ⚠️ THE ORDER IS STILL EXACT, and so is the count -- just of u_gate's own
    # lines. Anything else the patch raises is reported as a note below rather
    # than silently folded in, because an error nobody expected is worth seeing.
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
