#!/usr/bin/env python3
"""Panic's second tier, analyzed -- ref/module/map.md and ref/module/boot.md.

Three halves, the first with no Pd:

  1. The static lint reads Cut It/recover.sh and proves the two-step OSC is
     well formed and in order. oscsend is fire-and-forget UDP, and no driver
     can reach it, since [shell] is stubbed on a Mac.

  2. Run A, no breadcrumb on disk: a tap raises panic and never reaches
     recover, a hold raises panic and then forks.

  3. Run B boots with a breadcrumb already there: nothing may be held, the
     attempt is reported once, and the file is left cleared.

What it cannot assert, so the recover checklist does: that the reload happened ([shell] is
stubbed), that quitting still fires (u_mother-stub never sends it; this proves
only that the path leaves m_launchpad's ownership alone, item 251), and that
the grid turns red (`grid modal 5` is asserted as a request on disp).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

RECOVER_SH = "Cut It/recover.sh"

MARKS_A = 11
MARKS_B = 6

# The palette index u_init asks for on a panic: red.
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

    # /reloadNoRemount resets mother's patch directory, and /loadPatch's name is
    # relative to it. The other way round, it resolves against wherever the last
    # load left, and nothing reports the miss.
    A.check("⛔ /reloadNoRemount comes FIRST",
            "/reloadNoRemount" in sends[0] and "/loadPatch" in sends[1],
            "the order is %s" % sends)

    A.check("both go to mother's OSC port, 4001",
            all(" 4001 " in s for s in sends), repr(sends))

    # Not /reload, which runs mount.sh (the Organelle's Reference page).
    A.check("⛔ it is /reloadNoRemount and never a bare /reload",
            "/reload " not in body and "/reload\n" not in body,
            "a bare /reload would run mount.sh -- see tools/deploy.sh")

    # Cut It sits in a category folder, so a bare name loads nothing, silently.
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

    # The fork is on no bus, so lib_assert does not bucket it: the stub prints
    # `SHELL: sh <script>`, and a window is the capture between two MARKs.
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
    # The liveness witness for every negative below.
    A.check("the five load-time scripts forked, so the shell stub is live",
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
    # Silence before the reload: killing Pd mid-note sends no note-off. u_init
    # raises panic itself, which is why a hold shows two panics.
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
    # Written before the fork: a reload that does not take leaves no patch to
    # say so, and the breadcrumb is what the next boot reads.
    try:
        left = open(crumb_path).read().strip()
    except OSError as e:
        left = "<unreadable: %s>" % e
    A.check("⛔ the hold wrote a breadcrumb", left.startswith("recover"),
            "the file reads %r. Without it a reload that never landed leaves "
            "nothing behind at all" % left)
    A.check("...and it carries a stamp", len(left.split()) == 2,
            "the file reads %r -- wanted `recover <ms>`" % left)

    # The half of the safe exit a Mac can see: the path never surrenders the
    # surface (item 251). quitting itself never arrives here.
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
    # Deferred to 4500 (ref/module/map.md). Also the run's liveness witness: it
    # appears only if the breadcrumb was read.
    A.check("⛔ the breadcrumb is reported on err",
            "warn u_map recovered" in errs("AFTER-PROBE"),
            "err in AFTER-PROBE: %s" % errs("AFTER-PROBE"))
    A.check("...exactly once", errs("AFTER-PROBE").count("warn u_map recovered") == 1,
            repr(errs("AFTER-PROBE")))
    A.check("...and not again afterwards",
            "warn u_map recovered" not in errs("REPORTED") + errs("KNOB") + errs("DONE"),
            "it repeated: %s" % (errs("REPORTED") + errs("KNOB") + errs("DONE")))

    print("\n--- and NOTHING is held ---")
    # The breadcrumb overrides pickup's arming. That a knob is held without one
    # is map-assert's, against the same knobs.txt. Atoms are strings, hence the
    # float().
    bpm = [float(v[0]) for v in temps("KNOB") if v]
    A.check("⛔ the knob is LIVE, not held -- 0.5 is 125 bpm on knob 1's curve", bpm == [125.0],
            "tempo in KNOB: %s. Held, this window is empty" % temps("KNOB"))

    print("\n--- and the breadcrumb is cleared, so it reports once and never again ---")
    # Cleared by overwriting with a sentinel, never deleted (ref/module/map.md).
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
