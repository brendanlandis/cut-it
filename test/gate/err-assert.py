#!/usr/bin/env python3
"""The error bus's analyzer -- ref/module/error.md. Reads a capture on stdin.

⛔ WHAT THIS IS FOR: every warn and every fail is drawn, on every page
(Brendan, 2026-11-04). A filter on the screen fails in the direction of silence:
the display would simply go quiet, and the first place anyone would find out is a
venue. Until 2026-11-04 a perform class of modes hid warnings; nothing in u_err
reads the mode now, which the lint below reads off the patch.

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
MARKS = 9

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
    lint_unfiltered(root)
    lint_stamp(root)


def lint_unfiltered(root):
    """Nothing in u_err reads the mode, so no page can hide what it draws.

    Read off the boxes as well as driven below, since a filter keyed to a
    page the driver never chose would pass every window.
    """
    print("\n--- no page filters the screen (static, no Pd) ---")
    path = os.path.join(root, "Cut It", "u_err.pd")
    boxes = [line for line in lib_pd.read(path) if line.startswith("#X obj ")]
    A.check("u_err still has boxes to read", len(boxes) > 5, "%d boxes in %s" % (len(boxes), path))
    reads = [b for b in boxes if re.match(r"^#X obj \d+ \d+ (r|receive) mode;$", b)]
    gates = [b for b in boxes if re.match(r"^#X obj \d+ \d+ spigot( |;)", b)]
    A.check("⛔ u_err reads no mode bus -- every page draws every warning",
            not reads and not gates,
            "found %s -- a page can hide what the screen shows again" % (reads + gates))


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

    # ---- before any page ------------------------------------------------
    print("\n--- before any page has arrived ---")
    A.check("⛔ a warn shows before any page is chosen",
            alerts("DEFAULT") == [["alert", "warn", "u_gate", "before-mode"]],
            "got %s. Quiet here fails in the direction of silence, "
            "which is the failure this file exists to prevent" % alerts("DEFAULT"))

    # ---- every page draws both --------------------------------------------
    print("\n--- every page draws warn and fail ---")
    for page in ("1", "4"):
        for level in ("warn", "fail"):
            k = "PAGE-%s-%s" % (page, level.upper())
            A.check("%spage %s draws a %s" % ("⛔ " if page == "4" else "", page, level),
                    alerts(k) == [["alert", level, "u_gate", "page-%s-%s" % (page, level)]],
                    "got %s" % alerts(k))

    # ---- the old perform shape hides nothing -------------------------------
    # u_map refuses `perform mode-6` as bad-mode, which is drawn too, so only
    # the gate's own alerts are read.
    mine_drawn = [a for a in alerts("OLD-PERFORM") if a[2:3] == ["u_gate"]]
    A.check("⛔ the old `perform mode-6` hides nothing -- the warn draws",
            mine_drawn == [["alert", "warn", "u_gate", "old-perform"]],
            "got %s. The old filter read perform as a reason to drop a warn"
            % alerts("OLD-PERFORM"))

    # ---- info: logged and never drawn -------------------------------------
    print("\n--- info is logged and never drawn ---")
    drew = [a for a in alerts("INFO") if "info-quiet" in " ".join(map(str, a))]
    A.check("⛔ an info NEVER reaches the screen",
            not drew,
            "info drew %s. Its route outlet is meant to be connected to nothing "
            "-- if this is drawing, u_present's eight recovery attempts land on "
            "the OLED during every unplug" % (drew,))

    # Without this witness the check above is vacuous: a dead display also
    # draws nothing.
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

    # ---- the log holds every error ----------------------------------------
    # u_err's [print err] hangs off the trigger before the route.
    print("\n--- the log holds every error ---")
    logged = [ln.strip()[len("err: "):] for ln in cap.splitlines()
              if ln.strip().startswith("err: ")]
    raised = ["warn u_gate before-mode", "warn u_gate page-1-warn",
              "fail u_gate page-1-fail", "warn u_gate page-4-warn",
              "fail u_gate page-4-fail", "warn u_gate old-perform",
              "warn u_gate info-witness", "info u_gate info-quiet",
              "chatty u_gate bad-level"]
    # Exact order and count of the driver's own errors only. The patch can
    # raise its own too, at a point that moves from run to run; those are
    # noted, not asserted.
    mine = [ln for ln in logged if " u_gate " in ln]
    A.check("every error raised reaches the log, in order and on every page",
            mine == raised, "logged %s" % mine)
    others = [ln for ln in logged if " u_gate " not in ln]
    if others:
        A.note("%d error(s) from the patch itself during the run: %s"
               % (len(others), others))

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_lint()
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
