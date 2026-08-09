#!/usr/bin/env python3
"""The device-presence analyser -- ref/module/presence.md. Reads a capture on stdin.

⛔ THE CLAIM: A DEVICE THAT WAS NEVER THERE STILL GETS RECOVERED. The run it reads
never delivers a device-inquiry reply, so the Launchpad it describes is one that
was absent when the patch loaded. Item 235 is that this case was unreachable --
the bounded wire.sh recovery sat behind a [spigot] armed only by a reply, and so
did the give-up, which is why the error log was empty when it happened.

FOUR THINGS, AND THEY FAIL DIFFERENTLY:

  the re-wire happens at all      item 235. Nothing forked before the fix
  it waits for the fourth tick    the interval, which is half of what the bound
                                  is made of -- fire every tick and eight
                                  attempts over 70 s becomes thirty-four
  it does not fire early          a re-wire before the threshold means the loss
                                  test has gone, not that recovery is eager
  ownership is NOT dropped        ⛔ the invariant the arming gate protects. The
                                  fix splits that gate rather than removing it,
                                  and removing it is the plausible wrong answer

⚠️ EVERY SHELL ASSERTION HERE IS A COUNT WITHIN A WINDOW, never a total. u_init
forks wire.sh once at boot as well, so a total of "at least one" is satisfied by
the boot fork alone and says nothing whatever about recovery.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

MARKS = ("BOOT", "BEFORE-LOSS", "AFTER-LOSS", "WAITING", "AFTER-REWIRE",
         "FOREIGN", "STILL-LOST", "OWN-REPLY", "RECOVERED")

MARK_RE = re.compile(r"^PRES:\s+MARK\s+(\S+)\s*$")
# ⚠️ THE TRAILING ARGUMENTS ARE NOT OPTIONAL IN THIS REGEX -- two of the four
# scripts carry one. u_state forks `sh state-dir.sh <dir>` and u_net forks
# `sh phone-ip.sh <fallback>`, so an end-anchored pattern matches logroll.sh and
# wire.sh only and silently reports the other two as never having run. Same
# shape as the anchored [midiout] regex that made phase 6's gate blind to
# [ctlout 123], and found the same way -- by the count being wrong.
SHELL_RE = re.compile(r"^SHELL:\s+sh\s+(\S+)")


def shell_by_window(cap):
    """-> {mark: [script, ...]} for every [shell] invocation the stub reported."""
    by, cur = {"PRE": []}, "PRE"
    for line in cap.splitlines():
        line = line.strip()
        m = MARK_RE.match(line)
        if m:
            cur = m.group(1)
            by.setdefault(cur, [])
            continue
        m = SHELL_RE.match(line)
        if m:
            by.setdefault(cur, []).append(m.group(1))
    return by


def wire_in(by, *marks):
    return sum(by.get(m, []).count("wire.sh") for m in marks)


def main():
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "PRES")
    by = shell_by_window(cap)

    A.windows(cap, "PRES", len(MARKS))

    # ⛔ THE LIVENESS WITNESS, AND EVERY "NOTHING FORKED" CHECK BELOW DEPENDS ON
    # IT. A scratch copy whose shell stub never got installed reports no forks at
    # all, which satisfies three of the four assertions here for entirely the
    # wrong reason.
    #
    # ⚠️ THE OTHER THREE SCRIPTS FIRE AT loadbang, WHICH IS BEFORE THE FIRST MARK.
    # u_state, u_err and u_net each fork one at load, so they land in the capture
    # ahead of the BOOT mark and belong to no window -- only wire.sh, at u_init's
    # 1500 ms wiring stage, arrives late enough to be inside one. That is why
    # this is two checks: the three prove the STUB, and wire.sh proves the
    # WINDOWING as well.
    quiet = sorted(s for v in by.values() for s in v if s != "wire.sh")
    if not A.check("⛔ the shell stub is installed -- the three loadbang scripts fired",
                   quiet == ["logroll.sh", "phone-ip.sh", "state-dir.sh"],
                   "saw %s, wanted one each of logroll.sh, phone-ip.sh and "
                   "state-dir.sh. Without a working [shell] stub every count "
                   "below is answered by silence rather than by a fact" % (quiet,)):
        return A.report()

    if not A.check("⛔ u_init's own boot wire.sh lands in the BOOT window",
                   wire_in(by, "BOOT") == 1,
                   "%d in BOOT, wanted 1. The marks and the capture have come out "
                   "of step, so every window count below is reading the wrong "
                   "stretch of the run" % wire_in(by, "BOOT")):
        return A.report()

    # ⛔ AND THE OTHER HALF OF LIVENESS: the patch is actually talking to the
    # device. Without SysEx at all, "the grid is still painted" is unanswerable.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    # --- the recovery is not eager ------------------------------------------
    A.check("no re-wire before the loss is declared",
            wire_in(by, "BEFORE-LOSS") == 0,
            "%d wire.sh fork(s) in BEFORE-LOSS. The three-missed-poll test has "
            "gone -- a single dropped reply now forks Pd"
            % wire_in(by, "BEFORE-LOSS"))

    # ⛔ THE INTERVAL. Ticks 1 and 2 of the recovery counter land in this window
    # and mod 4 must swallow both.
    A.check("⛔ no re-wire on the first ticks after the loss -- it waits for the fourth",
            wire_in(by, "AFTER-LOSS") == 0,
            "%d wire.sh fork(s) in AFTER-LOSS. Firing every tick turns eight "
            "attempts over 70 s into thirty-four, and the bound is what makes "
            "forking permissible at all" % wire_in(by, "AFTER-LOSS"))

    # --- ⛔ ITEM 235 ---------------------------------------------------------
    A.check("⛔ a device that NEVER answered still gets re-wired -- exactly once, "
            "on the fourth tick",
            wire_in(by, "WAITING") == 1,
            "%d wire.sh fork(s) in WAITING, wanted exactly 1. Zero is item 235 "
            "itself: the recovery armed only on a device-inquiry REPLY, so a "
            "device absent at load never armed it and only a reload brought the "
            "surface back" % wire_in(by, "WAITING"))

    # --- ⛔ THE INVARIANT THE ARMING GATE PROTECTS ---------------------------
    # g_grid paints only while it owns the surface, so a lighting frame after the
    # loss was declared is proof that ownership survived a detector which has
    # never once seen a reply.
    late = [f for f in frames
            if f.is_lighting and f.mark in ("AFTER-REWIRE", "FOREIGN")]
    A.check("⛔ ownership is NOT dropped by a detector that never saw a reply",
            bool(late),
            "no lighting frame after the re-wire. The arming gate has been "
            "REMOVED rather than split: the grid now blanks six seconds into "
            "every run on any platform without a Launchpad, which is how this "
            "was found the first time -- 7 of 24 checks")

    # --- ⛔ CROSS-TALK: ANOTHER DEVICE'S REPLY IS NOT THIS DEVICE'S ----------
    # A KORG reply landed in FOREIGN. If m_launchpad counted it, the miss counter
    # zeroed, moses went left, the recovery counter was reset -- and the re-wire
    # due at 21000 never comes.
    A.check("⛔ a nanoKONTROL reply does NOT mark the Launchpad present",
            wire_in(by, "STILL-LOST") == 1,
            "%d wire.sh fork(s) in STILL-LOST, wanted exactly 1. A KORG reply "
            "(manufacturer byte 66) was accepted as this device's. That is item "
            "235 un-fixed in the worst direction -- the watchdog believing a "
            "device that is gone -- and it is what 'ANY SysEx counts as "
            "presence' becomes the moment more than one device answers"
            % wire_in(by, "STILL-LOST"))

    # ⛔ THE POSITIVE CONTROL FOR THE CHECK ABOVE, AND WITHOUT IT THAT CHECK IS
    # WORTHLESS: a c_devid that matches nothing at all ignores the nano's reply
    # for entirely the wrong reason and passes. The Launchpad's OWN reply landed
    # in OWN-REPLY, so the re-wire due at 29000 must NOT happen.
    A.check("⛔ ...but the Launchpad's OWN reply is honoured -- recovery stops",
            wire_in(by, "RECOVERED") == 0,
            "%d wire.sh fork(s) in RECOVERED, wanted 0. The device answered and "
            "the watchdog kept forking anyway, so c_devid matches nothing at "
            "all -- which also makes the cross-talk check above vacuous"
            % wire_in(by, "RECOVERED"))

    # ⛔ AND THE LIVENESS WITNESS FOR *THAT* ONE. "No fork in RECOVERED" is also
    # what a Pd that died at 25 s produces. The Programmer Mode heartbeat rides
    # $0-want and keeps going regardless of presence, so a mode frame in the last
    # window is proof the run was still alive to have forked if it wanted to.
    alive = [f for f in frames if f.is_mode and f.mark == "RECOVERED"]
    A.check("the run is still alive in the last window",
            bool(alive),
            "no heartbeat frame in RECOVERED -- Pd died before the third re-wire "
            "was due, so 'recovery stopped' is unproven")

    total = sum(v.count("wire.sh") for v in by.values())
    A.check("exactly three wire.sh forks in the whole run",
            total == 3,
            "saw %d, wanted u_init's boot fork plus two recoveries. More means "
            "the interval or the loss test has gone" % total)

    A.note("wire.sh by window: %s"
           % " ".join("%s=%d" % (m, wire_in(by, m)) for m in MARKS))
    A.note("%d lighting frame(s), %d mode frame(s)"
           % (len([f for f in frames if f.is_lighting]),
              len([f for f in frames if f.is_mode])))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
