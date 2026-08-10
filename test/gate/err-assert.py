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
MARKS = 10

# C-12: <level> <source> <text>, text ONE symbol of at most 21 characters,
# because gPrintln does not wrap -- it draws until it runs off the screen.
TEXT_LIMIT = 21
# ⛔ THREE LEVELS, AND info IS THE ONE THAT NEVER DRAWS. It is logged like the
# other two -- u_err's logfile tap hangs off the trigger ABOVE the route -- and
# its route outlet is deliberately connected to nothing. It exists because
# diagnostic detail and operator alerts are not the same thing: u_present forks
# wire.sh up to eight times per episode, and nine alerts on a 21-character
# screen mid-set is noise where the log wants every one of them.
LEVELS = ("info", "warn", "fail")
ERR_MSG = re.compile(r"^#X msg \d+ \d+ (%s) (\S+) (\S+);$" % "|".join(LEVELS))


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
                if not re.match(r"^#X msg \d+ \d+ (%s) " % "|".join(LEVELS), line):
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
    lint_stamp(root)


def lint_stamp(root):
    """⛔ THE LOG'S TIMESTAMP MUST REACH [text] AS A SYMBOL, NEVER AS A FLOAT.

    [timer] reports milliseconds as a float and [text] writes a float with %g,
    which caps at SIX SIGNIFICANT FIGURES and switches to exponential above
    999999 -- so 16 minutes 40 seconds into a session every stamp starts losing
    precision. Measured in Pd 0.49 both ways: the symbol path writes
    `2104000 warn ...`, the float path writes `2.104e+06 warn ...`, and the
    device's own cut-it-err.log carries exactly that second form beside exact
    six-digit stamps.

    ⛔ AND IT HAS TO BE A STATIC LINT, WHICH IS NOT A COMPROMISE. The rot needs
    999999 ms of uptime to appear, so a runtime check would have to run the gate
    for seventeen minutes -- and a shorter run reads clean whatever the wiring
    does, which is a check that cannot fail. What CAN be read cheaply is the
    cord: the stamp reaching `list prepend`'s right inlet must come from a
    makefilename, not from the timer.

    ⚠️ NOTHING READ THIS FILE'S FORMAT UNTIL NOW, which is why the rot shipped.
    err-assert's other half reads u_err's [print err] on the console, and the
    console never sees the stamp -- it is added downstream, on the way to disk.
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
             # ⚠️ %g IS THE BUG WEARING THE FIX'S CLOTHES. makefilename %g
             # reformats exactly as [text] would, so the box being present
             # proves nothing -- the FORMAT is the assertion.
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

    # ⛔ THE RIGHT INLET IS THE STAMP. list prepend holds what to prepend in its
    # COLD inlet, so inlet 1 is the one that carries the timestamp -- inlet 0 is
    # the error message itself, and asserting on that would pass whatever the
    # stamp did.
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

    # ---- ⛔ info: LOGGED AND NEVER DRAWN -----------------------------------
    # The third level exists because diagnostic detail and operator alerts are
    # not the same thing. u_present forks wire.sh up to eight times per episode
    # and every one of them belongs in the log; nine alerts on a 21-character
    # screen mid-set does not. It was `warn` first and oled-assert caught it
    # drawing over a modal within one run.
    print("\n--- info is logged and never drawn ---")
    drew = [a for a in alerts("INFO") if "info-quiet" in " ".join(map(str, a))]
    A.check("⛔ an info NEVER reaches the screen, even in compose",
            not drew,
            "info drew %s. Its route outlet is meant to be connected to nothing "
            "-- if this is drawing, u_present's eight recovery attempts land on "
            "the OLED during every unplug" % (drew,))

    # ⛔ THE LIVENESS WITNESS, AND WITHOUT IT THE CHECK ABOVE IS VACUOUS. "The
    # screen drew nothing" is satisfied just as well by a dead display, a shut
    # spigot or a mode that filters everything -- so the same window raises a
    # `warn` that MUST draw, in compose, one action earlier.
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

    # ---- ⛔ THE BUS IS UNFILTERED; ONLY THE SCREEN IS FILTERED -------------
    # u_err's own [print err] hangs off the trigger BEFORE the route, so it fires
    # on every error whatever the mode. That is what makes the by-hand SSH
    # console -- and the durable log behind it -- see everything even when the
    # OLED is deliberately showing nothing.
    print("\n--- the log is never filtered, even when the screen is ---")
    logged = [ln.strip()[len("err: "):] for ln in cap.splitlines()
              if ln.strip().startswith("err: ")]
    # ⛔ info IS IN THIS LIST AND THAT IS THE POINT OF PUTTING IT HERE. The claim
    # is that the LOG is unfiltered while the SCREEN is -- and info is the level
    # the screen never draws at all, so its presence in this exact ordered
    # sequence is the strongest form that claim can take.
    raised = ["warn u_gate before-mode", "warn u_gate compose-warn",
              "fail u_gate compose-fail", "warn u_gate perform-warn",
              "fail u_gate perform-fail", "warn u_gate back-warn",
              "warn u_gate two-atom", "warn u_gate info-witness",
              "info u_gate info-quiet", "chatty u_gate bad-level"]
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
