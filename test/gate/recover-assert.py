#!/usr/bin/env python3
"""Panic's second tier, analysed -- ref/module/map.md and ref/module/boot.md.

Three halves, and the FIRST NEEDS NO Pd AT ALL.

  1. THE STATIC LINT reads Cut It/recover.sh and proves the two-step OSC is
     well formed and in the right order. That is the half most likely to be
     silently wrong -- oscsend is fire-and-forget UDP and a bare /loadPatch
     name loads nothing and says nothing -- and it is also the half no driver
     could ever reach, because [shell] is stubbed on a Mac.

  2. RUN A drives the button with no breadcrumb on disk: a tap must raise panic
     and reach recover NOT AT ALL, a hold must raise panic and then fork.

  3. RUN B boots with a breadcrumb already there, which is the state the next
     boot after a real recover is in: nothing may be held, the attempt must be
     reported once, and the file must be left cleared.

⛔ WHAT THIS GATE CANNOT DO, stated here rather than implied away.

  - IT CANNOT ASSERT THE RELOAD HAPPENED. [shell] is stubbed, so no OSC leaves
    the process and no patch is loaded. It proves the command was FORMED and
    forked, in order, behind the silence. The reload is a bench step.

  - IT CANNOT ASSERT quitting STILL FIRES. quitting comes from mother.pd, and
    u_mother-stub deliberately never sends it, so on the Mac neither receiver
    ever runs. What it proves instead is the half that would break it -- that
    this path never touches m_launchpad's ownership, so the safe exit is still
    there to run when mother does send it. Item 251, and the bench is the
    oracle for the rest.

  - IT CANNOT SEE THE GRID. `grid modal 5` is asserted as a REQUEST on disp;
    whether the surface turns red is launchpad-bench's, and the palette index
    is a thing only eyes can confirm.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

RECOVER_SH = "Cut It/recover.sh"

MARKS_A = 11
MARKS_B = 6

# The palette index u_init asks for on a panic. Red, in the same 128-entry
# palette where 21 is green and 45 is blue.
RED = 5

_SHELL = re.compile(r"^SHELL:\s+sh\s+(\S+)")


# ------------------------------------------------------- 1. the static lint
def static_lint():
    """The two-step OSC, proved by READING. No Pd, no timing, no scratch copy."""
    print("\n=== A. recover.sh, checked by READING -- no Pd involved ===")
    try:
        body = open(RECOVER_SH).read()
    except OSError as e:
        A.check("recover.sh exists and is readable", False, str(e))
        return
    lines = [ln.strip() for ln in body.splitlines()]
    sends = [ln for ln in lines if ln.startswith("oscsend")]

    A.check("recover.sh sends exactly two OSC commands", len(sends) == 2,
            "found %d: %s" % (len(sends), sends))
    if len(sends) != 2:
        return

    # ⛔ ORDER IS THE WHOLE THING. /reloadNoRemount resets mother's current patch
    # directory to the default; /loadPatch then takes a name relative to it. The
    # other way round, the name is resolved against whatever directory the last
    # load left behind, and nothing reports the miss.
    A.check("⛔ /reloadNoRemount comes FIRST",
            "/reloadNoRemount" in sends[0] and "/loadPatch" in sends[1],
            "the order is %s" % sends)

    A.check("both go to mother's OSC port, 4001",
            all(" 4001 " in s for s in sends), repr(sends))

    # ⛔ NOT /reload. That one runs mount.sh, which with a Launchpad attached
    # mounts its write-protected onboarding drive and takes USER_DIR with it.
    A.check("⛔ it is /reloadNoRemount and never a bare /reload",
            "/reload " not in body and "/reload\n" not in body,
            "a bare /reload would run mount.sh -- see tools/deploy.sh")

    # ⛔ A BARE NAME LOADS NOTHING AND SAYS NOTHING. /loadPatch resolves against
    # mother's patch directory and Cut It lives in a category folder under it,
    # so the argument has to carry that folder.
    m = re.search(r"/loadPatch\s+s\s+'([^']*)'", sends[1])
    A.check("the /loadPatch argument is quoted, so the space survives",
            m is not None, "could not find a single-quoted argument in %r" % sends[1])
    if m:
        arg = m.group(1)
        A.check("⛔ ...and it is NOT a bare patch name", "/" in arg,
                "the argument is %r. A name with no category folder loads "
                "nothing at all and reports nothing" % arg)
        A.note("loads %r" % arg)


# ------------------------------------------------------- 2. run A, the tiers
def run_a(cap, crumb_path):
    print("\n=== B. the two tiers, driven ===")
    lines = [ln.strip() for ln in cap.splitlines()]
    order, by = A.windows(cap, "REC", MARKS_A)
    W = lambda k: by.get(k, [])

    def disp(k, want):
        return [v for lb, v in W(k) if lb == "DISP" and " ".join(v) == want]

    # ⚠️ THE FORK IS NOT ON A BUS, so lib_assert does not bucket it. The shell
    # stub prints `SHELL: sh <script>` as plain text, and a window is located by
    # slicing the capture between its MARK and the next one.
    marks = [i for i, ln in enumerate(lines) if ln.startswith("REC: MARK ")]
    names = [ln.split("MARK ", 1)[1].strip() for ln in lines if ln.startswith("REC: MARK ")]

    def span(k):
        i = names.index(k)
        lo = marks[i]
        hi = marks[i + 1] if i + 1 < len(marks) else len(lines)
        return lines[lo:hi]

    def sh_in(k, script):
        return [ln for ln in span(k)
                if (_SHELL.match(ln) or [None]) and _SHELL.match(ln)
                and _SHELL.match(ln).group(1) == script]

    print("\n--- a boot on its own never recovers ---")
    # ⚠️ THE LIVENESS WITNESS FOR EVERY NEGATIVE BELOW. An empty window is also
    # what a driver that died looks like, and A.windows only proves the MARK
    # landed -- not that the run reached this far with a working patch.
    A.check("the four load-time scripts forked, so the shell stub is live",
            sorted(set(_SHELL.match(ln).group(1) for ln in lines if _SHELL.match(ln)
                       )) [:4] != [],
            "no SHELL: lines at all -- the counting stub is not installed")
    A.check("⛔ recover.sh is NOT one of them", not sh_in("EARLY", "recover.sh"),
            "a boot forked recover.sh on its own: %s" % sh_in("EARLY", "recover.sh"))

    print("\n--- tier 1: a tap raises panic, on the PRESS ---")
    A.check("⛔ the press raises panic at once", len(disp("TAP-DOWN", "led panic")) == 1,
            "led panic in TAP-DOWN: %d. It must fire on the press, not the "
            "release -- that is what makes the hold threshold free"
            % len(disp("TAP-DOWN", "led panic")))
    A.check("⛔ ...and the grid is asked for red", len(disp("TAP-DOWN", "grid modal %d" % RED)) == 1,
            "grid modal %d in TAP-DOWN: %s" % (RED, disp("TAP-DOWN", "grid modal %d" % RED)))
    A.check("...and it clears itself rather than waiting out the 30 s TTL",
            len(disp("TAP-UP", "grid modal-off")) == 1,
            "grid modal-off in TAP-UP: %s" % disp("TAP-UP", "grid modal-off"))
    A.check("⛔ a tap reaches recover NOT AT ALL", not sh_in("TAP-DOWN", "recover.sh"),
            repr(sh_in("TAP-DOWN", "recover.sh")))

    print("\n--- ...and the release CANCELS the timer ---")
    # ⛔ THE ONE THAT MATTERS. The tap armed a 2000 ms timer at 5000, which would
    # fire at 7000 -- inside AFTER-TAP. Cut the release cord and two recovers
    # come out of a run with one hold in it.
    A.check("⛔ the tap's timer expires with NOTHING behind it",
            not sh_in("AFTER-TAP", "recover.sh"),
            "recover.sh forked at about 7000 ms, 2000 ms after a press that "
            "was released at 5300. The release did not stop the del")
    A.check("...still nothing a second later", not sh_in("TAP-EXPIRED", "recover.sh"),
            repr(sh_in("TAP-EXPIRED", "recover.sh")))

    print("\n--- tier 2: a hold reaches the reload, behind the silence ---")
    A.check("the hold's press raises panic too",
            len(disp("HOLD-PRESS", "led panic")) == 1,
            "led panic in HOLD-PRESS: %s" % disp("HOLD-PRESS", "led panic"))
    A.check("⛔ recover forks recover.sh, exactly once",
            len(sh_in("HOLD-WAIT", "recover.sh")) == 1,
            "recover.sh in HOLD-WAIT: %s" % sh_in("HOLD-WAIT", "recover.sh"))
    # ⛔ SILENCE LANDS BEFORE THE RELOAD. Killing Pd mid-note never sends the
    # note-off, so a reload with no panic in front of it CREATES a stuck note on
    # the 404. u_init raises panic itself so recover is self-contained whatever
    # reaches it -- which is why a hold shows TWO panics and a tap shows one.
    A.check("⛔ ...and panic is raised again FIRST, in the same window",
            len(disp("HOLD-WAIT", "led panic")) == 1,
            "led panic in HOLD-WAIT: %s. recover must silence before it "
            "reloads" % disp("HOLD-WAIT", "led panic"))
    hw = span("HOLD-WAIT")
    i_panic = next((i for i, ln in enumerate(hw) if ln == "DISP: led panic"), None)
    i_fork = next((i for i, ln in enumerate(hw) if _SHELL.match(ln)
                   and _SHELL.match(ln).group(1) == "recover.sh"), None)
    A.check("⛔ ...and STRICTLY before it, in the capture",
            i_panic is not None and i_fork is not None and i_panic < i_fork,
            "panic at line %s, fork at line %s of the window" % (i_panic, i_fork))

    print("\n--- and it happens once, not once per event ---")
    allf = [ln for ln in lines if _SHELL.match(ln) and _SHELL.match(ln).group(1) == "recover.sh"]
    A.check("⛔ EXACTLY ONE fork across the whole run", len(allf) == 1,
            "%d forks: %s" % (len(allf), allf))
    A.check("...and the release after a completed hold adds nothing",
            not sh_in("HOLD-UP", "recover.sh") and not sh_in("DONE", "recover.sh"),
            "%s %s" % (sh_in("HOLD-UP", "recover.sh"), sh_in("DONE", "recover.sh")))

    print("\n--- and the breadcrumb is on disk BEFORE the fork ---")
    # ⛔ DESIGN FOR THE FAILURE, BECAUSE IT IS WORSE THAN THE FAULT. If the load
    # does not take there is no patch at all, and the patch cannot verify its own
    # reload because it is dead by then. The breadcrumb is the only thing that
    # survives to say an attempt was made -- so it is written first, and a
    # recover that never completed is visible on the next boot instead of being
    # a silent brick.
    try:
        left = open(crumb_path).read().strip()
    except OSError as e:
        left = "<unreadable: %s>" % e
    A.check("⛔ the hold wrote a breadcrumb", left.startswith("recover"),
            "the file reads %r. Without it a reload that never landed leaves "
            "nothing behind at all" % left)
    A.check("...and it carries a stamp", len(left.split()) == 2,
            "the file reads %r -- wanted `recover <ms>`" % left)

    # ⛔ THE SAFE EXIT'S HALF THAT A MAC CAN SEE. quitting comes from mother and
    # u_mother-stub never sends it, so the handback itself is unreachable here.
    # What is reachable is the thing that used to break it: panic surrendering
    # the surface. Item 251.
    print("\n--- the surface is never handed back on this path ---")
    A.check("⛔ nothing on the recover path asks the Launchpad for Live Mode",
            not [ln for ln in lines if "grid own" in ln or "want 0" in ln],
            "something on this path touched ownership -- item 251 was reopened")


# --------------------------------------------- 3. run B, the boot after one
def run_b(cap, crumb_path):
    print("\n=== C. the boot AFTER a recover ===")
    lines = [ln.strip() for ln in cap.splitlines()]
    order, by = A.windows(cap, "REC", MARKS_B)
    W = lambda k: by.get(k, [])
    errs = lambda k: [" ".join(v) for lb, v in W(k) if lb == "ERR"]
    temps = lambda k: [v for lb, v in W(k) if lb == "TEMPO"]

    print("\n--- the attempt is reported, late enough to be seen ---")
    # ⛔ DEFERRED TO 4500 ON PURPOSE. A warn raised during the boot stages is
    # buried by modal launchpad at 3000 and the footer hand-over at 4000, so it
    # waits until both are done. It is also the liveness witness for the whole
    # run: it can only appear if the breadcrumb was read.
    A.check("⛔ the breadcrumb is reported on err",
            "warn u_map recovered" in errs("AFTER-PROBE"),
            "err in AFTER-PROBE: %s" % errs("AFTER-PROBE"))
    A.check("...exactly once", errs("AFTER-PROBE").count("warn u_map recovered") == 1,
            repr(errs("AFTER-PROBE")))
    A.check("...and not again afterwards",
            "warn u_map recovered" not in errs("REPORTED") + errs("KNOB") + errs("DONE"),
            "it repeated: %s" % (errs("REPORTED") + errs("KNOB") + errs("DONE")))

    print("\n--- and NOTHING is held ---")
    # ⛔ AFTER AN EMERGENCY THE KNOBS YOU ARE HOLDING ARE THE TRUTH. mother
    # replayed a saved position inside the boot window, which normally arms
    # pickup and holds the knob until it crosses. The breadcrumb overrides that.
    # ⚠️ THE NEGATIVE HALF -- that a knob IS held without a breadcrumb -- is
    # map-assert's, run against the same knobs.txt. This run only proves the
    # override, and the warn above proves the run got far enough to make it.
    # ⚠️ A CAPTURE IS TEXT. lib_assert hands back the atoms as strings, so a
    # comparison against the number 255 is quietly false however right the patch
    # is -- which is exactly how this check failed on its first run.
    bpm = [float(v[0]) for v in temps("KNOB") if v]
    A.check("⛔ the knob is LIVE, not held -- 0.5 is 255 bpm", bpm == [255.0],
            "tempo in KNOB: %s. Held, this window is empty" % temps("KNOB"))

    print("\n--- and the breadcrumb is cleared, so it reports once and never again ---")
    # ⛔ CLEARED BY OVERWRITING, NEVER DELETED. Vanilla Pd cannot delete a file,
    # [shell] forks and is stubbed here, and how [text] writes an empty table has
    # never been measured. A sentinel makes the read decide on CONTENT.
    try:
        left = open(crumb_path).read().strip()
    except OSError as e:
        left = "<unreadable: %s>" % e
    A.check("⛔ the file is left saying none", left == "none",
            "the breadcrumb reads %r after the run. Left armed, every boot "
            "from here on reports a recover that already happened" % left)


def main():
    argv = [a for a in sys.argv[1:]]
    crumb = None
    crumb_a = None
    if "--crumb-a" in argv:
        i = argv.index("--crumb-a")
        crumb_a = argv[i + 1]
        del argv[i:i + 2]
    if "--crumb" in argv:
        i = argv.index("--crumb")
        crumb = argv[i + 1]
        del argv[i:i + 2]
    cap_b = None
    if "--runb" in argv:
        i = argv.index("--runb")
        cap_b = open(argv[i + 1]).read()
        del argv[i:i + 2]

    cap_a = sys.stdin.read()
    A.require_capture(cap_a)

    static_lint()
    run_a(cap_a, crumb_a)
    if cap_b is not None:
        A.require_capture(cap_b)
        run_b(cap_b, crumb)

    sys.exit(1 if A.report() else 0)


if __name__ == "__main__":
    main()
